<script lang="ts">
    import MapView from "$lib/components/MapView.svelte"; 
    import MapLegend from "$lib/components/MapLegend.svelte";
    import RoutePanel from "$lib/components/RoutePanel.svelte";
    import StatGrid from "$lib/components/StatGrid.svelte";
    import SurfaceMix from "$lib/components/SurfaceMix.svelte";
    import ElevationProfile from "$lib/components/ElevationProfile.svelte";
    import type { PageData } from "./$types";
    import type { ColourMode, Route, Waypoint } from "$lib/core/types";


    let { data }: { data: PageData } = $props();

    let waypoints = $state<Waypoint[]>([]);
    let sunPenalty = $state(4);
    let roadPenalty = $state(2.2);
    let paceFactor = $state(1);
    let maxSac = $state(2);
    let withElevation = $state(true);
    let showCanopy = $state(false);
    let showLandmarks = $state(false);
    let mode = $state<ColourMode>("exposure");


    let route = $state<Route | null>(null);
    let hovered = $state<number | null>(null); 
    let busy = $state(false);
    let failure = $state<string | null>(null);


    // an ojbect url is a resource, not a value. A plain $derived would mint a fresh one
    // on every recompute and never hand any of htme back, which leaks the whole gpx each time
    let gpxHref = $state<string | null>(null);


    $effect(() =>
    {
        const current = route;
        if (!current)
        {
            gpxHref = null;
            return;
        }


        const url = URL.createObjectURL(new Blob([current.gpx], { type: "application/gpx+xml" }));
        gpxHref = url;


        return () =>
        {
            URL.revokeObjectURL(url);
        }; 
    });


    const slug = $derived(
        (route?.name ?? "boucle")
            .toLowerCase()
            .normalize("NFD")
            .replace(/\p{Diacritic}/gu, "")  
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-|-$/g, "")
    );


    function addWaypoint(lat: number, lon: number, name?: string)
    {
        // a repere brings its own name, a bare click on the map does not
        waypoints.push({ name: name || `Point ${waypoints.length + 1}`, lat, lon });
    }


    async function importTrace(document: string)
    {
        // the uploaded fichier carries its own points and its own name, the engine
        // dispatches on the gpx field alone
        await send({ gpx: document, paceFactor, withElevation });
    }


    async function trace()
    {
        await send({ waypoints, sunPenalty, roadPenalty, paceFactor, maxSac,
                     withElevation });
    }


    async function send(payload: Record<string, unknown>)
    {
        busy = true;
        failure = null;
        hovered = null;


        try
        {
            const response = await fetch("/api/route", {
                method: "POST",
                headers: { "content-type": "application/json" },
                body: JSON.stringify(payload)
            });


            if (!response.ok)
            {
                // sveltekit wraps endpoint errors as {"message": ...}, the walker
                // should read the message and never the json around it
                const raw = await response.text();
                try
                {
                    failure = (JSON.parse(raw) as { message?: string }).message ?? raw;
                }
                catch
                {
                    failure = raw;
                }
                route = null;
                return;
            }


            route = (await response.json()) as Route;
        }
        catch (cause)
        {
            failure = cause instanceof Error ? cause.message : "le moteur est injoignable";
            route = null;
        }
        finally
        {
            busy = false;
        }
    }
</script>

<svelte:head>
    <title>Ma trace, routage pondéré par l'ombre</title>
</svelte:head>

<main>
    <div class="grid">
        <RoutePanel
            presets={data.presets}
            bind:waypoints
            bind:sunPenalty
            bind:roadPenalty
            bind:paceFactor
            bind:maxSac
            bind:withElevation
            {busy}
            onsubmit={trace}
            onimport={importTrace}
        />

        <div class="stage">
            <MapView {route} {waypoints} {hovered} {showCanopy} {showLandmarks} {mode}
                     onpick={addWaypoint} />

            {#if route}
                <MapLegend {route} bind:mode bind:showCanopy bind:showLandmarks />
            {/if}


            {#if failure}
                <p class="failure">{failure}</p>
            {/if}

            {#if route}
                <StatGrid stats={route.stats} />
                <ElevationProfile {route} {hovered} onhover={(i) => (hovered = i)} />

                <div class="tail">   
                    <SurfaceMix {route} />

                    <section class="panel">
                        <h2>Emporter</h2>
                        {#if gpxHref}
                            <a class="download" href={gpxHref} download="{slug}.gpx">
                                Télécharger le GPX
                                <small>{route.points.length} points</small>
                            </a>
                        {/if}


                        <h2 class="second">À savoir</h2>
                        <ul class="notes">
                            <li>
                                <strong>Le balisage ne suit pas le GPX</strong>
                                <span>Le tracé emprunte le réseau OpenStreetMap, pas
                                      forcément un itinéraire balisé. Naviguez au GPS.</span>
                            </li>
                            <li>
                                <strong>L'ombre est une approximation</strong>
                                <span>Elle vient des polygones forestiers d'OSM, pas d'une densité de canopée ni de la course du soleil. Une futaie et une coupe rase comptent pareil.</span>
                            </li>
                            <li>
                                <strong>Le dénivelé est estimé</strong>
                                <span>Modèle de terrain EU-DEM 25 m, dont la précision se dégrade justement sous couvert dense et en forte pente, là où ce tracé vous emmène. Comptez une marge de l'ordre de 10 %.</span>
                            </li>
                            <li>
                                <strong>Graphe</strong>
                                <span>{route.stats.nodes.toLocaleString("fr-FR")} nœuds, {route.stats.edges.toLocaleString("fr-FR")} arêtes, {route.stats.clearings} clairières découpées dans la canopée.</span>
                            </li>
                        </ul>
                    </section>
                </div>
            {/if}
        </div>
    </div>
</main>

<style>
    main
    {
        max-width: 1500px;
        margin: 0 auto;
        padding: var(--spacing-xl) var(--spacing-lg) var(--spacing-3xl);
    }


    .grid
    {
        display: grid; 
        grid-template-columns: minmax(300px, 380px) 1fr;
        gap: var(--spacing-lg);
        align-items: start;
    }


    @media (max-width: 1000px)
    {
        .grid
        {
            grid-template-columns: 1fr;
        }
    }


    .stage
    {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-lg);
        min-width: 0;
    }


    .tail
    {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: var(--spacing-lg);
        align-items: start;
    }


    .panel
    {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-md);  
        padding: var(--spacing-lg);
        border: var(--border-width) solid var(--colour-border);
        border-radius: var(--radius-lg);
        background: var(--colour-bg-surface);
    }


    h2
    {
        margin: 0;
        font-size: var(--font-size-sm);
        font-weight: var(--font-weight-semibold);
        letter-spacing: var(--letter-spacing-wide);
        text-transform: uppercase;
        color: var(--colour-text-secondary);
    }


    h2.second
    {
        margin-top: var(--spacing-sm);
        padding-top: var(--spacing-md);
        border-top: var(--border-width) solid var(--colour-border);
    }


    .download
    {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: var(--spacing-md);
        padding: var(--spacing-base);
        text-decoration: none;
        font-weight: var(--font-weight-semibold);
        font-size: var(--font-size-sm);
        color: var(--colour-text-inverse);
        background: var(--colour-success);
        border-radius: var(--radius-md);
        transition: filter var(--transition-fast);
    }


    .download:hover
    {
        filter: brightness(1.1);
    }


    .download small
    {
        font-family: var(--font-mono);
        font-weight: var(--font-weight-regular);
        opacity: 0.8;
    }


    .notes
    {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-md);
        margin: 0;
        padding: 0;
        list-style: none;
    }


    .notes li
    {
        padding-left: var(--spacing-md);
        border-left: var(--border-width-thick) solid var(--colour-border);
    }


    .notes strong
    {
        display: block;
        font-size: var(--font-size-sm);
        color: var(--colour-text-primary);
    }


    .notes span
    {
        font-size: var(--font-size-xs);
        line-height: var(--line-height-normal);
        color: var(--colour-text-muted);
    } 


    .failure
    {
        margin: 0;
        padding: var(--spacing-base);
        border-left: var(--border-width-thick) solid var(--colour-danger);
        background: var(--colour-danger-muted);
        border-radius: var(--radius-md);
        font-size: var(--font-size-sm);
        color: var(--colour-text-primary); 
    }
</style>
