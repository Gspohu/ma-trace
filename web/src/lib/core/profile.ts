// Turns a tracé into the geometry an elevation chart needs. Pure maths, no svg here

import type { Route } from "./types";

export interface ProfileBand
{
    x: number;
    width: number;
    top: number;
    shaded: boolean; 
}

export interface ProfileGeometry
{
    width: number;
    height: number;
    pad: number;
    baseline: number;
    bands: ProfileBand[];
    line: string; 
    ticks: { y: number; label: number }[];
    /** maps a fraction of the horizontal ais back onto a tracé index */
    indexAt: (fraction: number) => number;
}


const WIDTH = 1000;
const HEIGHT = 220;
const PAD = 26;


export function buildProfile(route: Route): ProfileGeometry
{
    const points = route.points;
    const totalKm = points[points.length - 1].km;


    const heights = points.map((p) => { return p.ele; });
    const low = Math.min(...heights);
    const high = Math.max(...heights);
    const span = Math.max(high - low, 1);


    const baseline = HEIGHT - PAD;
    const usable = HEIGHT - 2 * PAD;


    const x = (km: number) => { return PAD + (km / totalKm) * (WIDTH - 2 * PAD); };
    const y = (ele: number) => { return baseline - ((ele - low) / span) * usable; };


    const bands: ProfileBand[] = [];
    for (let i = 0; i < points.length - 1; i++)
    {
        const x1 = x(points[i].km);
        const x2 = x(points[i + 1].km);
        bands.push({
            x: x1,
            width: Math.max(x2 - x1 + 0.7, 0.9),
            top: y(points[i].ele),
            shaded: route.shade[i] === 1
        });
    }


    const line = "M" + points
        .map((p) => { return `${x(p.km).toFixed(1)} ${y(p.ele).toFixed(1)}`; })
        .join("L");


    const ticks = [];
    for (let i = 0; i <= 4; i++)
    {
        const ele = low + (span * i) / 4;
        ticks.push({ y: y(ele), label: Math.round(ele) });
    }


    const indexAt = (fraction: number): number =>
    {
        const km = Math.min(Math.max(fraction, 0), 1) * totalKm;
        let lo = 0;
        let hi = points.length - 1;


        // the km array is sortde. A bisection beats scanning it on every mouseove
        while (lo < hi)
        {
            const mid = (lo + hi) >> 1;
            if (points[mid].km < km)
            {
                lo = mid + 1;  
            }
            else 
            {
                hi = mid;
            }
        }
        return lo;
    };


    return { width: WIDTH, height: HEIGHT, pad: PAD, baseline, bands, line, ticks, indexAt };
}
