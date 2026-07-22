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


export interface CanopyRing
{ 
    outer: [number, number][];
    holes: [number, number][][];
}


export interface RouteStats
{
    km: number;
    shade_pct: number;
    sun_metres: number;
    road_metres: number;
    off_network_metres: number;
    up: number;
    down: number;
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
    points: TrackPoint[];
    // one entry per segment. Their lenght is points.length - 1
    shade: number[];
    seg_surface: string[];
    canopy: CanopyRing[];
    stats: RouteStats;
    surfaces: SurfaceShare[];
    highways: SurfaceShare[];
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
    withElevation: boolean;
}
