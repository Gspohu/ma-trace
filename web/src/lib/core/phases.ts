// Reads the notes core/ writes as it works, and turns them into a place on a bar
// The engine talks in french prose, and matching on it is presentation, which is why
// thi lives here and not in the worker
export interface Phase
{
    key: string;
    label: string;
}

export const PHASES: Phase[] = [
    { key: "runtime", label: "Interpréteur" },
    { key: "network", label: "Réseau piéton" },
    { key: "canopy", label: "Couvert forestier" },
    { key: "landmarks", label: "Repères" },
    { key: "assembly", label: "Assemblage" },
    { key: "graph", label: "Graphe" },
    { key: "route", label: "Itinéraire" },
];

// each note the engine writes, against the phase it announces
const MARKERS: Array<{ pattern: RegExp, key: string }> = [
    { pattern: /reseau pietonnier|reseau local/i, key: "network" },
    { pattern: /chemins?$/i, key: "network" },
    { pattern: /couvert forestier|foret locale/i, key: "canopy" },
    { pattern: /polygones|massifs/i, key: "canopy" },
    { pattern: /points remarquables|reperes/i, key: "landmarks" },
    { pattern: /^Canopee/i, key: "assembly" },
    { pattern: /^Graphe/i, key: "graph" },
    { pattern: /^\s*->/, key: "route" },
    { pattern: /^Boucle|^Trace /i, key: "route" },
];


export function phaseOf(note: string): string | null
{
    for (const { pattern, key } of MARKERS)
    {
        if (pattern.test(note))
        {
            return key;
        }
    }

    return null;
}


export function indexOf(key: string | null): number
{
    if (!key)
    {
        return 0;
    }

    return PHASES.findIndex(phase =>
    {
        return phase.key === key;
    });
}


// a mirror giving way is the usual reason a trace takes minutes, and saying so beats
// a bar that seems stuck
export function isSetback(note: string): boolean
{
    return /miroir indisponible|nouvelle tentative|ATTENTION/i.test(note);
}


export function readable(note: string): string
{
    const clean = note.trim().replace(/^->\s*/, "");
    if (/miroir indisponible/i.test(clean))
    {
        return "un serveur OpenStreetMap ne répond pas, on passe au suivant";
    }

    if (/deja en memoire/i.test(clean))
    {
        return "zone déjà chargée, rien à redemander";
    }

    return clean;
}
