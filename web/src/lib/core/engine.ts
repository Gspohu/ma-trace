// The page talks to the python engine through here, and never touches the worker
// directly. Same contract the http endpoint usde to honour : a payload in, a route out
import { base } from "$app/paths";

type Progress = (stage: string, detail?: string) => void;

let worker: Worker | null = null;
let ticket = 0;

interface Pending
{
    settle: (value: unknown) => void;
    fail: (cause: Error) => void;
    watch?: Progress;
}

const waiting: Record<number, Pending> = {};


function spawn()
{
    if (worker)
    {
        return worker;
    }

    worker = new Worker(new URL("./engine.worker.ts", import.meta.url), { type: "module" });

    worker.onmessage = (event: MessageEvent) =>
    {
        const { id, kind, result, error, stage, detail } = event.data ?? {};

        if (kind === "progress")
        {
            for (const pending of Object.values(waiting))
            {
                pending.watch?.(stage, detail);
            }
            return;
        }

        const pending = waiting[id];
        if (!pending)
        {
            return;
        }

        delete waiting[id];
        if (kind === "done")
        {
            pending.settle(result);
        }
        else
        {
            pending.fail(new Error(error || "le moteur a renonce"));
        }
    };

    // a worker that dies takes every pending answer with it, and a page left waiting
    // on a promise nobody will ever settle looks exactly like a slow trace
    worker.onerror = (event: ErrorEvent) =>
    {
        const cause = new Error(event.message || "le moteur n'a pas demarre");
        for (const [id, pending] of Object.entries(waiting))
        {
            pending.fail(cause);
            delete waiting[Number(id)];
        }

        worker = null;
    };

    return worker;
}


export function ask(payload: Record<string, unknown>, watch?: Progress): Promise<unknown>
{
    const engine = spawn();
    const id = ++ticket;

    // waypoints arrive as a reactive proxy, and structuredClone refuses to copy one
    // A round trip through json hands the worker plain data, which is all it wants
    const plain = JSON.parse(JSON.stringify(payload));

    return new Promise((settle, fail) =>
    {
        waiting[id] = { settle, fail, watch };
        engine.postMessage({ id, base: `${base}/`.replace(/\/+$/, "/"), payload: plain });
    });
}
