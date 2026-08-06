// Browser side twin of cli/bridge.py : takes the request a front sends, hands it to
// the python engine, posts the answer back. All the routing knowledge stays in core/
//
// It runs off the main thread because a dijkstra over sixteen thousand nodes would
// otherwise freeze the map while it walks

/// <reference lib="webworker" />

declare const self: DedicatedWorkerGlobalScope;

interface Manifest
{
    [pkg: string]: string[];
}


interface Wheels
{
    version: string;
    wheels: string[];
}


// where the engine is mounted inside the emscripten filesystem, which lives in this
// tab and nowhere on disk
const ROOT = "/projet";

let engine: any = null;
let booting: Promise<any> | null = null;


function tell(stage: string, detail?: string)
{
    self.postMessage({ kind: "progress", stage, detail });
}


async function jsonOf(url: string)
{
    const answer = await fetch(url);
    if (!answer.ok)
    {
        throw new Error(`${url} a repondu ${answer.status}`);
    }

    return answer.json();
}


async function boot(base: string)
{
    tell("runtime", "demarrage de l'interpreteur");

    const runtime = `${base}runtime/`;

    // a module worker cannot importScripts, and vite must keep its hands off a url
    // that only exists once the site is served
    const { loadPyodide } = await import(/* @vite-ignore */ `${runtime}pyodide.mjs`);
    const py = await loadPyodide({ indexURL: runtime });

    tell("paquets", "chargement de shapely");
    const { wheels } = (await jsonOf(`${runtime}wheels.json`)) as Wheels;

    // the distribution wheels come first, micropip then installs what pyodide does not
    // ship. Loading them off our own origin means no cdn in the critical path
    const shipped: string[] = [];
    const extra: string[] = [];
    for (const name of wheels)
    {
        (name.startsWith("defusedxml") ? extra : shipped).push(runtime + name);
    }

    await py.loadPackage(shipped);

    const micropip = py.pyimport("micropip");
    await Promise.all(extra.map(url =>
    {
        return micropip.install(url);
    }));

    tell("moteur", "mise en place du moteur");
    const manifest = (await jsonOf(`${base}engine/manifest.json`)) as Manifest;

    // every module at once, they are small and the round trips dominate
    const wanted = Object.entries(manifest).flatMap(([pkg, modules]) =>
    {
        return modules.map(module =>
        {
            return { pkg, module };
        });
    });

    const fetched = await Promise.all(wanted.map(async ({ pkg, module }) =>
    {
        const answer = await fetch(`${base}engine/${pkg}/${module}`);
        return { pkg, module, bytes: new Uint8Array(await answer.arrayBuffer()) };
    }));

    py.FS.mkdir(ROOT);
    for (const pkg of Object.keys(manifest))
    {
        py.FS.mkdir(`${ROOT}/${pkg}`);
    }

    for (const { pkg, module, bytes } of fetched)
    {
        py.FS.writeFile(`${ROOT}/${pkg}/${module}`, bytes);
    }

    py.runPython(`
import json
import sys
sys.path.insert(0, ${JSON.stringify(ROOT)})

from cli.engine import EXPECTED, handle_request


def answer(payload, log):
    """Same split the bridge makes : a bad request is a message, a bug is a crash"""
    try:
        return json.dumps(handle_request(json.loads(payload), log=log))
    except EXPECTED as exc:
        return json.dumps({"error": str(exc)})
`);

    tell("pret");
    return py;
}


async function ready(base: string)
{
    if (engine)
    {
        return engine;
    }

    if (!booting)
    {
        booting = boot(base).then(py =>
        {
            engine = py;
            return py;
        });

        // a failed boot must not stick : leaving the rejected promise in place would
        // make every later trace fail with the first error, forever
        booting.catch(() =>
        {
            booting = null;
        });
    }

    return booting;
}


self.onmessage = async (event: MessageEvent) =>
{
    const { id, base, payload } = event.data ?? {};

    try
    {
        const py = await ready(base);

        // the notes core/ writes go straight to the page, a trace takes a while and a
        // silent wait reads as a hang
        const notes = (line: string) =>
        {
            tell("calcul", line);
        };
        py.globals.set("_notes", notes);
        py.globals.set("_payload", JSON.stringify(payload));

        const raw = await py.runPythonAsync("answer(_payload, _notes)");
        const result = JSON.parse(raw);

        if (result && typeof result.error === "string")
        {
            self.postMessage({ id, kind: "failed", error: result.error });
            return;
        }

        self.postMessage({ id, kind: "done", result });
    }
    catch (cause)
    {
        const message = cause instanceof Error ? cause.message : String(cause);
        self.postMessage({ id, kind: "failed", error: message });
    }
};

export {};
