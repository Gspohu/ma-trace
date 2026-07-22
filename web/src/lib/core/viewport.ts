// Where the map was left last time. It reopens ther and not on a forest
// that used to be the only one this tool knew about

export interface Viewport
{
    lat: number;
    lon: number;
    zoom: number;
}


// mainland France, wide. The honest view when we have never been told better
export const DEFAULT_VIEW: Viewport = { lat: 46.6, lon: 2.5, zoom: 6 };


const KEY = "ma-trace:viewport";


// leaflet refuses anything outside its own tile pyramid, these are the sane bounds
const MIN_ZOOM = 2;
const MAX_ZOOM = 19;


function sane(value: unknown, low: number, high: number): value is number
{
    if (typeof value !== "number" || !Number.isFinite(value))
    {
        return false; 
    }
    else
    {
        return value >= low && value <= high;
    }
}


/** Reads a stored view back, refusing anything that would throw leaflet off */
export function parseViewport(raw: string | null): Viewport | null
{
    if (!raw)
    {
        return null;
    }

    let value: unknown;
    try
    {
        value = JSON.parse(raw);
    }
    catch (cause)
    {
        console.warn("vue enregistree illisible", cause);
        return null;
    }


    const stored = (value ?? {}) as Record<string, unknown>;
    const lat = stored.lat;
    const lon = stored.lon;
    const zoom = stored.zoom;

    if (sane(lat, -90, 90) && sane(lon, -180, 180) && sane(zoom, MIN_ZOOM, MAX_ZOOM))
    {
        return { lat, lon, zoom };
    }
    else
    {
        return null;
    }
}


// localStrage throws outright in a few privacy modes. A map that will not open
// is a far worse outcoem than a map that forgot where it was
export function loadViewport(): Viewport
{
    try
    {
        return parseViewport(localStorage.getItem(KEY)) ?? DEFAULT_VIEW;
    }
    catch (cause)
    {
        console.warn("localStorage indisponible", cause);
        return DEFAULT_VIEW;
    }
}


export function saveViewport(view: Viewport): void
{
    try
    {
        localStorage.setItem(KEY, JSON.stringify(view));
    }
    catch (cause)
    {
        // a viewport is a convenience, never a reason to interrupt the walker
        console.warn("vue non enregistree", cause);
    }
}
