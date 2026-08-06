// Reference data, read once at build time. A hand edited fichier with one bad point
// costs that boucle and never the whole page
import raw from "./presets.json";
import type { Preset, Waypoint } from "./types";


function readWaypoints(entries: unknown): Waypoint[]
{
    if (!Array.isArray(entries))
    {
        return [];
    }

    const out: Waypoint[] = [];
    for (const entry of entries)
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


export const presets: Preset[] = Object.entries(raw as Record<string, unknown>)
    .map(([key, value]) =>
    {
        const entry = value as Record<string, unknown>;
        return {
            key,
            label: typeof entry?.label === "string" ? entry.label : key,
            waypoints: readWaypoints(entry?.waypoints)
        };
    })
    .filter(preset =>
    {
        return preset.waypoints.length > 0;
    });
