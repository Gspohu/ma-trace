// Thin adapter : takes the http request, hands it to the python engine, returns the sjon
// No routing knowledge lives here, core/ owns all of it

import { spawn } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { error, json } from "@sveltejs/kit";
import type { RequestHandler } from "./$types";
import type { RouteRequest } from "$lib/core/types";
import { parseRouteRequest } from "$lib/core/request";


const HERE = dirname(fileURLToPath(import.meta.url));
const PROJECT = resolve(HERE, "../../../../..");
const BRIDGE = resolve(PROJECT, "cli", "bridge.py");


// overpass plus the elevation api on a long tracé geniunely take a while
const TIMEOUT_MS = 300_000;


// the resident engine, when it is running. It holds the index in memory, which is
// worth about four seconds a trace over spawning a fresh interpreter every time
const ENGINE_HOST = process.env.ENGINE_HOST ?? "127.0.0.1";
const ENGINE_PORT = process.env.ENGINE_PORT ?? "8765";
const ENGINE = process.env.ENGINE_URL ??
               `http://${ENGINE_HOST}:${ENGINE_PORT}`;


// long enough to notice it is there, short enough not to stall a walker who never
// started it
const PROBE_MS = 300;


async function runResident(payload: RouteRequest): Promise<unknown | null>
{
    let alive: Response;
    try
    {
        alive = await fetch(`${ENGINE}/health`, {
            signal: AbortSignal.timeout(PROBE_MS)
        });
    }
    catch
    {
        // not running is the normal case, the throwaway process takes over
        return null;
    }


    if (!alive.ok)  
    { 
        return null;
    }

    const answer = await fetch(`${ENGINE}/route`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(TIMEOUT_MS) 
    });


    return answer.json();
}

interface EngineFailure
{
    error: string;
}   


function runEngine(payload: RouteRequest): Promise<unknown>
{
    return new Promise((accept, reject) =>
    {
        const child = spawn("python3", [BRIDGE], { cwd: PROJECT });


        let out = "";
        let log = "";
        let settled = false;

        const timer = setTimeout(() =>
        {
            settled = true;
            child.kill("SIGKILL");
            reject(new Error("le moteur a depasse le temps imparti"));
        }, TIMEOUT_MS);


        child.stdout.on("data", (chunk) => { out += chunk; });
        child.stderr.on("data", (chunk) =>
        {
            log += chunk;
            process.stdout.write(`[moteur] ${chunk}`);
        });


        child.on("error", (cause) =>
        {
            clearTimeout(timer);
            if (!settled)
            {
                reject(new Error(`python3 introuvable : ${cause.message}`));
            }
        });


        child.on("close", (code) =>
        {
            clearTimeout(timer);
            if (settled)
            {
                return;
            }
            if (code !== 0 && out.trim() === "")
            {
                reject(new Error(log.trim() || `le moteur a quitte avec le code ${code}`));
                return;
            }
            try
            {
                accept(JSON.parse(out));
            }
            catch
            {
                reject(new Error("le moteur n'a pas renvoye du json"));
            }
        });


        child.stdin.write(JSON.stringify(payload));
        child.stdin.end();
    }); 
}


export const POST: RequestHandler = async ({ request }) =>
{
    let body: unknown;
    try
    {
        body = await request.json();
    }
    catch
    {
        error(400, "Requête illisible");
    }


    const parsed = parseRouteRequest(body);
    if ("error" in parsed)
    {
        error(400, parsed.error);
    }


    const payload = parsed.value;


    let result: unknown;
    try
    {
        // the resident engine when it answers, a throwaway process otherwise. Nobody
        // is obliged to start a daemon just to drw one walk
        result = (await runResident(payload)) ?? (await runEngine(payload));
    }
    catch (cause)
    {
        error(500, cause instanceof Error ? cause.message : "le moteur a echoue");
    }


    const failure = result as EngineFailure;
    if (failure?.error)
    {
        error(422, failure.error);
    }

    return json(result);
};
