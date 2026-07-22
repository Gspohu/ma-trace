// Presets are referecne dat, they live in data/ and are read once at load

import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";  
import { fileURLToPath } from "node:url";
import type { PageServerLoad } from "./$types";
import type { Preset, Waypoint } from "$lib/core/types";


const HERE = dirname(fileURLToPath(import.meta.url));
const PRESETS = resolve(HERE, "../../..", "data", "presets.json");


function readWaypoints(raw: unknown): Waypoint[]
{
    if (!Array.isArray(raw))
    {
        return [];
    }

    const out: Waypoint[] = [];
    for (const entry of raw)
    {
        const point = entry as Record<string, unknown>;
        if (typeof point?.lat !== "number" || typeof point?.lon !== "number")
        {
            continue;
        }
        out.push({
            name: typeof point.name === "string" ? point.name : "Point",
            lat: point.lat,
            lon: point.lon
        });
    }
    return out;
}


// a hand editd presets file with one bad entry should cost that entry, not the page
export const load: PageServerLoad = async () =>
{
    let raw: unknown;
    try
    {
        raw = JSON.parse(await readFile(PRESETS, "utf-8"));
    }
    catch (cause)
    {
        console.error(`presets illisibles : ${cause instanceof Error ? cause.message : cause}`);
        return { presets: [] as Preset[] };  
    }


    if (!raw || typeof raw !== "object")
    {
        return { presets: [] as Preset[] };
    }

    const presets: Preset[] = [];
    for (const [key, value] of Object.entries(raw as Record<string, unknown>))
    {
        const entry = value as Record<string, unknown>;
        const waypoints = readWaypoints(entry?.waypoints);
        if (waypoints.length === 0)
        {
            continue;
        }
        presets.push({
            key,
            label: typeof entry.label === "string" ? entry.label : key,
            waypoints
        });
    }


    return { presets };
};
