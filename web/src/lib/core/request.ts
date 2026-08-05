// Validation of what arrives on the wire, before any of it reaches the engine
// A cast is a promise to the compiler. It is not a check, the body is whatever was posted

import type { AnalyseRequest, RouteRequest, Waypoint } from "$lib/core/types";


// the engine refuses anything past this too, checking here only saves the round trip
const MAX_GPX_BYTES = 8 * 1024 * 1024;


const MIN_WAYPOINTS = 2;


// a wlak with a thousand points is not a walk, it is someone probing the moteur
const MAX_WAYPOINTS = 200;


const PENALTY_FLOOR = 1;
const PENALTY_CEILING = 50;


// half tobler's pace is already a crawl, twice it is a run. Outside that the estimate
// says nothing about anyone
const PACE_FLOOR = 0.5;
const PACE_CEILING = 2.5;


// the swiss alpine club scale runs T1 to T6, and asking for more than exists is
// how a typo turns a walk into a scramble
const SAC_FLOOR = 1;
const SAC_CEILING = 6;


function number(value: unknown, low: number, high: number): number | null
{
    if (typeof value !== "number" || !Number.isFinite(value))
    {
        return null;
    }
    else if (value < low || value > high)
    {
        return null;
    }
    else
    {
        return value;
    }
}


function waypoint(raw: unknown): Waypoint | null
{
    if (!raw || typeof raw !== "object")
    {
        return null;
    }


    const candidate = raw as Record<string, unknown>;
    const lat = number(candidate.lat, -90, 90);
    const lon = number(candidate.lon, -180, 180);

    if (lat === null || lon === null)
    {
        return null;
    }


    // the name is shown back to the walker and writen into the gpx, it gets trimmed
    // to something sane
    const name = typeof candidate.name === "string" ? candidate.name.slice(0, 120) : "Point";
    return { name, lat, lon };
}


/** A gpx to read, not a boucle to draw. The parsing itself belongs to core */
export function parseAnalyseRequest(raw: unknown): { value: AnalyseRequest } | { error: string }
{
    if (!raw || typeof raw !== "object")
    {
        return { error: "Requête illisible" };
    }


    const body = raw as Record<string, unknown>;
    if (typeof body.gpx !== "string" || body.gpx.trim() === "")
    {
        return { error: "Aucun fichier à lire" };
    }
    if (body.gpx.length > MAX_GPX_BYTES)
    {
        return { error: "Ce fichier GPX est trop gros" };
    }


    return {
        value: {
            gpx: body.gpx,
            paceFactor: number(body.paceFactor, PACE_FLOOR, PACE_CEILING) ?? 1,
            withElevation: body.withElevation !== false
        }
    };
}


/** Returns a clean request, or a message saying what was wrong with it */
export function parseRouteRequest(raw: unknown): { value: RouteRequest } | { error: string }
{
    if (!raw || typeof raw !== "object")
    {
        return { error: "Requête illisible" };
    }


    const body = raw as Record<string, unknown>;
    if (!Array.isArray(body.waypoints))
    {
        return { error: "Il faut au moins deux points de passage" };   
    }
    if (body.waypoints.length > MAX_WAYPOINTS)
    {
        return { error: `Pas plus de ${MAX_WAYPOINTS} points de passage` };
    }

    const waypoints: Waypoint[] = [];
    for (const entry of body.waypoints)
    {
        const parsed = waypoint(entry);
        if (parsed === null)
        {
            return { error: "Un point de passage porte des coordonnées invalides" };
        }
        waypoints.push(parsed);
    }

    if (waypoints.length < MIN_WAYPOINTS)
    {
        return { error: "Il faut au moins deux points de passage" };
    }


    return {
        value: {
            waypoints,
            sunPenalty: number(body.sunPenalty, PENALTY_FLOOR, PENALTY_CEILING) ?? 4,
            roadPenalty: number(body.roadPenalty, PENALTY_FLOOR, PENALTY_CEILING) ?? 2.2,
            paceFactor: number(body.paceFactor, PACE_FLOOR, PACE_CEILING) ?? 1,
            maxSac: Math.round(number(body.maxSac, SAC_FLOOR, SAC_CEILING) ?? 2),
            withElevation: body.withElevation !== false
        } 
    };
}
