// Human labels for OSM surface values, maped onto the design ssytem chart tokens

import type { SurfaceShare } from "./types";


interface SurfaceStyle
{
    label: string;
    token: string;
}


const CATALOGUE: Record<string, SurfaceStyle> = {
    ground: { label: "Terre battue", token: "var(--colour-chart-2)" },
    dirt: { label: "Terre", token: "var(--colour-chart-2)" },
    earth: { label: "Terre", token: "var(--colour-chart-2)" },
    grass: { label: "Herbe", token: "var(--colour-chart-2)" },
    sand: { label: "Sable", token: "var(--colour-chart-3)" },
    "dirt;sand": { label: "Terre et sable", token: "var(--colour-chart-3)" },
    gravel: { label: "Gravier", token: "var(--colour-chart-5)" },
    fine_gravel: { label: "Gravier fin", token: "var(--colour-chart-5)" },
    compacted: { label: "Compacte", token: "var(--colour-chart-5)" },
    unpaved: { label: "Non revetu", token: "var(--colour-chart-4)" },
    wood: { label: "Platelage bois", token: "var(--colour-chart-4)" },
    rock: { label: "Rocher", token: "var(--colour-chart-4)" },
    asphalt: { label: "Bitume", token: "var(--colour-chart-6)" },
    paved: { label: "Revetu", token: "var(--colour-chart-6)" }, 
    concrete: { label: "Beton", token: "var(--colour-chart-6)" },
    non_renseigne: { label: "Non renseigne", token: "var(--colour-chart-1)" }   
};


const FALLBACK: SurfaceStyle = { label: "Non renseigne", token: "var(--colour-chart-1)" };

/** The css custom proprety carrying the colour of one OSM surface value */
export function surfaceToken(key: string): string
{
    return (CATALOGUE[key] ?? FALLBACK).token;
}


export function surfaceLabel(key: string): string
{
    return (CATALOGUE[key] ?? FALLBACK).label;
}


export interface SurfaceSlice
{
    label: string;
    token: string;
    metres: number;
    share: number;
}


/** Several OSM keys collapse onto the same label. Merging happens before charting */
export function mergeSurfaces(shares: SurfaceShare[]): SurfaceSlice[]
{
    const total = shares.reduce((sum, s) => { return sum + s.metres; }, 0);
    if (total === 0)
    {
        return [];
    }


    const merged = new Map<string, SurfaceSlice>();
    for (const share of shares)
    {
        const style = CATALOGUE[share.key] ?? FALLBACK;
        const existing = merged.get(style.label);


        if (existing)
        {
            existing.metres += share.metres;   
        }
        else
        {
            merged.set(style.label, {
                label: style.label,
                token: style.token,
                metres: share.metres,
                share: 0
            });
        }
    }

    const slices = [...merged.values()];
    for (const slice of slices)
    {
        slice.share = (100 * slice.metres) / total;
    }


    slices.sort((a, b) => { return b.metres - a.metres; });
    return slices;
}


const HIGHWAY_LABELS: Record<string, string> = {
    path: "Sentier",
    track: "Piste forestiere",
    footway: "Chemin pieton",
    steps: "Marches",
    bridleway: "Chemin cavalier",
    cycleway: "Voie cyclable", 
    unclassified: "Petite route",
    residential: "Rue",
    service: "Voie de service",
    tertiary: "Route",
    secondary: "Route", 
    primary: "Route",
    living_street: "Zone de rencontre"
};


export function highwayLabel(key: string): string
{
    return HIGHWAY_LABELS[key] ?? key;
}
