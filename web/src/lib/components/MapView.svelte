<script lang="ts">
    import { onMount } from "svelte";
    import type { Map as LeafletMap, LayerGroup, Polyline, CircleMarker } from "leaflet";
    import { surfaceToken } from "$lib/core/surfaces";
    import { loadViewport, saveViewport } from "$lib/core/viewport";
    import type { Route, Waypoint, ColourMode } from "$lib/core/types";


    interface Props
    {
        route: Route | null;   
        waypoints: Waypoint[];
        hovered: number | null;
        showCanopy: boolean;
        mode: ColourMode;
        onpick: (lat: number, lon: number) => void;
    }


    let { route, waypoints, hovered, showCanopy, mode, onpick }: Props = $props();


    let host: HTMLDivElement;
    let L: typeof import("leaflet") | null = $state(null);
    let map: LeafletMap | null = null; 


    let canopyLayer: LayerGroup | null = null;
    let trackLayer: LayerGroup | null = null;
    let markerLayer: LayerGroup | null = null;
    let cursor: CircleMarker | null = null;


    // read straight off the design system, a token change lands here for free
    // leaflet wants a real colour, it cannot swallow a var() the way css does
    function token(name: string): string
    {
        const property = name.startsWith("var(") ? name.slice(4, -1).trim() : name;
        return getComputedStyle(document.documentElement).getPropertyValue(property).trim();
    }

    onMount(() =>
    {
        let dropped = false;

        // leaflet touches window on import. It only ever loads in the browser
        // onMount refuses a cleanup from an async body. The inner promise works around it
        void (async () =>
        {
            const leaflet = (await import("leaflet")).default;
            if (dropped)
            {
                return;
            }

            const opening = loadViewport();  
            const instance = leaflet.map(host, { zoomControl: true, attributionControl: true })  
                .setView([opening.lat, opening.lon], opening.zoom);


            // leaflet drives its own panning, there is no reactive state to observe here
            // One listener is the only way to learn the map moved
            instance.on("moveend", () =>
            {
                const centre = instance.getCenter();
                saveViewport({ lat: centre.lat, lon: centre.lng, zoom: instance.getZoom() });
            }); 


            leaflet.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 18,
                attribution: "&copy; contributeurs OpenStreetMap"
            }).addTo(instance);


            canopyLayer = leaflet.layerGroup().addTo(instance);
            trackLayer = leaflet.layerGroup().addTo(instance);
            markerLayer = leaflet.layerGroup().addTo(instance);

            instance.on("click", (event) =>
            {
                onpick(event.latlng.lat, event.latlng.lng);
            });


            map = instance;
            // assigning L last is what wakes the effects up, everything they need exists by then
            L = leaflet;
        })();

        return () =>
        {
            dropped = true;
            map?.remove();
            map = null;
            L = null;
        };
    });

    // the tracé is redrawn whenever the engine answers, never on a mousemove
    $effect(() =>
    {
        const leaflet = L;
        const instance = map;
        const layer = trackLayer;
        if (!leaflet || !instance || !layer)
        {
            return;
        }


        layer.clearLayers();
        const current = route;
        if (!current)
        {
            return;
        }


        const shade = token("--colour-success");
        const sun = token("--colour-warning");
        const points = current.points;
        const count = current.shade.length;


        // exposure answers "will i cook", surface answers "what is underfoot"
        // they are independent : a tarmac lane under the canopy is shaded and sealed
        const classOf = (i: number) =>
        {
            return mode === "surface" ? current.seg_surface[i] : String(current.shade[i]);
        };


        // one polyline per run of identical class, far fewer layers than one per segment
        let start = 0;
        for (let i = 1; i <= count; i++)   
        {
            if (i < count && classOf(i) === classOf(start))
            {
                continue;
            }

            const slice = points.slice(start, i + 1)
                .map((p) => { return [p.lat, p.lon] as [number, number]; });
            const exposed = current.shade[start] === 0;
            const colour = mode === "surface"
                ? token(surfaceToken(current.seg_surface[start]))
                : (exposed ? sun : shade);


            leaflet.polyline(slice, {  
                color: colour,
                weight: mode === "surface" ? 5 : (exposed ? 7 : 4),
                opacity: 0.95,
                lineCap: "round",
                lineJoin: "round"
            }).addTo(layer);

            start = i;
        }


        instance.fitBounds([[current.bbox.minlat, current.bbox.minlon],
                            [current.bbox.maxlat, current.bbox.maxlon]],
                           { padding: [24, 24] });
    });


    $effect(() =>
    {
        const leaflet = L;
        const layer = canopyLayer;
        if (!leaflet || !layer)
        {
            return;
        }


        layer.clearLayers();
        const current = route;
        if (!current || !showCanopy)
        {
            return;
        }   


        const green = token("--colour-success");
        for (const ring of current.canopy)
        {
            // leaflet reads the fisrt ring as the shell and the rest as claireires
            leaflet.polygon([ring.outer, ...ring.holes] as [number, number][][], {
                color: green,
                weight: 1,
                opacity: 0.35,
                fillColor: green,
                fillOpacity: 0.12,
                interactive: false
            }).addTo(layer);
        }
    });


    $effect(() =>
    {
        const leaflet = L;
        const layer = markerLayer;
        if (!leaflet || !layer)
        {
            return;
        }


        layer.clearLayers();
        const accent = token("--colour-accent");
        const surface = token("--colour-bg-surface");

        waypoints.forEach((waypoint, index) =>
        {
            const first = index === 0;
            leaflet.circleMarker([waypoint.lat, waypoint.lon], {
                radius: first ? 9 : 6,
                color: accent,
                weight: 3,
                fillColor: surface,
                fillOpacity: 1
            })
                .bindTooltip(`${index + 1}. ${waypoint.name}`, { direction: "top" })
                .addTo(layer);
        });
    });


    // hovering the elevation chart moves a dot along the tracé
    $effect(() =>
    {
        const leaflet = L;
        const instance = map;
        if (!leaflet || !instance)
        {
            return;
        }

        cursor?.remove();
        cursor = null;


        const current = route;
        if (current === null || hovered === null)
        {
            return;
        }


        const point = current.points[hovered]; 
        if (!point)
        {
            return;
        }


        const accent = token("--colour-accent");
        cursor = leaflet.circleMarker([point.lat, point.lon], {
            radius: 8,
            color: accent,
            weight: 3,
            fillColor: accent,
            fillOpacity: 0.5,
            interactive: false
        }).addTo(instance);
    });
</script>

<div class="map" bind:this={host} aria-label="Carte du tracé"></div>

<style>
    .map
    {  
        width: 100%;
        height: clamp(360px, 52vh, 620px);
        border: var(--border-width) solid var(--colour-border);
        border-radius: var(--radius-lg);
        background: var(--colour-bg-surface);
        cursor: crosshair;
    }


    .map :global(.leaflet-container)
    {
        background: var(--colour-bg-surface);
        font-family: var(--font-sans);
    }


    .map :global(.leaflet-control-attribution)
    {
        background: var(--colour-bg-surface);
        color: var(--colour-text-muted);
        font-size: var(--font-size-xs);
    }


    .map :global(.leaflet-control-attribution a)
    {
        color: var(--colour-accent);
    }
</style>
