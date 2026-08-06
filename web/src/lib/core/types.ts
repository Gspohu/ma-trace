// Shapes exchanged with the python engine. Nothing hee knows baou the DOM

export interface Waypoint
{
    name: string;
    lat: number;
    lon: number;
}


export interface TrackPoint
{
    lat: number;
    lon: number;
    ele: number;
    km: number;
}


export interface Landmark
{
    name: string;
    // castle, drinking_water, spring, well, water, rock or parking
    kind: string;
    lat: number;
    lon: number;
    fee: string | null;
    // null when osm makes no claim, which on a spring means carry the bottle full
    drinkable: boolean | null;
}


export interface CanopyRing
{
    outer: [number, number][];
    holes: [number, number][][];
}


export interface RouteStats
{
    km: number;
    shade_pct: number;
    // share of full sun actually received, weighted by what each canopy lets through
    exposure_pct: number;
    sun_metres: number;
    road_metres: number;
    off_network_metres: number;
    // metres of sentier osm calls hard to follow, and the steepest declared gradient
    faint_metres: number;
    steepest_pct: number | null;
    max_sac: number;
    // false when nothing measured the ground, which leaves up, down and hours at zero
    has_elevation: boolean;
    up: number;
    down: number;
    // tobler, walked at pace_factor. Both come from core, never recomputed here
    hours: number;
    pace_factor: number;
    min_ele: number;
    max_ele: number;
    nodes: number;
    edges: number;
    clearings: number;
}


export interface SurfaceShare
{
    key: string;
    metres: number;
}

export interface BoundingBox
{
    minlat: number;  
    minlon: number;
    maxlat: number;
    maxlon: number;
}


export interface Route
{
    name: string;
    bbox: BoundingBox;
    waypoints: Waypoint[];
    landmarks: Landmark[];
    points: TrackPoint[];
    // one entry per segment. Their lenght is points.length - 1
    shade: number[];
    seg_surface: string[];
    canopy: CanopyRing[];
    stats: RouteStats;
    surfaces: SurfaceShare[];
    highways: SurfaceShare[];
    covers: SurfaceShare[];
    gpx: string;
}


/** What the tracé colours stand for on the map */  
export type ColourMode = "exposure" | "surface";

export interface Preset
{
    key: string;
    label: string;
    waypoints: Waypoint[];
}


export interface RouteRequest
{
    waypoints: Waypoint[];
    sunPenalty: number;
    roadPenalty: number;
    paceFactor: number;
    maxSac: number;
    withElevation: boolean;
}


/** Reading a trace somebody else drew. No waypoints, the fichier carries its own */
export interface AnalyseRequest
{
    gpx: string;
    paceFactor: number;
    withElevation: boolean;
}
