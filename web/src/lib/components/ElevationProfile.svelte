<script lang="ts">
    import { buildProfile } from "$lib/core/profile";
    import { decimal, integer } from "$lib/core/format";
    import type { Route } from "$lib/core/types";


    interface Props
    {
        route: Route;
        hovered: number | null;
        onhover: (index: number | null) => void; 
    }


    let { route, hovered, onhover }: Props = $props();


    const geometry = $derived(buildProfile(route));
    const reading = $derived(hovered === null ? null
                                              : route.points[hovered]);

    // N points carry N-1 segments, the last point reads the shade of the segment
    // arriving into it, there is none past the end
    const segment = $derived(hovered === null ? null
                                              : Math.min(hovered, route.shade.length - 1));
    const cursorX = $derived.by(() =>
    {
        if (hovered === null || !reading)
        {
            return null;
        }
        const total = route.points[route.points.length - 1].km;
        return geometry.pad + (reading.km / total) * (geometry.width - 2 * geometry.pad);
    });


    let svg: SVGSVGElement;


    function track(event: PointerEvent)
    {
        const box = svg.getBoundingClientRect();
        const fraction = (event.clientX - box.left) / box.width;
        const local = (fraction * geometry.width - geometry.pad) / (geometry.width - 2 * geometry.pad);
        onhover(geometry.indexAt(local));
    }   
</script>

<figure class="plate">
    <figcaption class="head">
        <h2>Profil altimétrique</h2>
        <span class="reading">
            {#if reading}
                {decimal(reading.km, 2)} km &middot; {integer(reading.ele)} m &middot;
                <span class:shaded={route.shade[segment!] === 1} class:exposed={route.shade[segment!] === 0}>
                    {route.shade[segment!] === 1 ? "sous couvert" : "au soleil"}
                </span>
            {:else}
                survolez pour situer le point sur la carte
            {/if}
        </span>
    </figcaption>

    <svg
        bind:this={svg}
        viewBox="0 0 {geometry.width} {geometry.height}"
        preserveAspectRatio="none"
        role="img" 
        aria-label="Profil altimétrique du tracé" 
        onpointermove={track}
        onpointerleave={() => { onhover(null); }}
    >
        {#each geometry.ticks as tick (tick.label)}
            <line
                x1={geometry.pad}
                y1={tick.y}
                x2={geometry.width - geometry.pad}
                y2={tick.y}
                class="grid"
            />
            <text x="2" y={tick.y - 4} class="tick">{tick.label}</text>
        {/each}


        {#each geometry.bands as band, i (i)}
            <rect
                x={band.x}
                y={band.top}
                width={band.width}
                height={Math.max(geometry.baseline - band.top, 0)}
                class={band.shaded ? "band-shade" : "band-sun"}
            />
        {/each}


        <path d={geometry.line} class="ridge" />

        {#if cursorX !== null}
            <line x1={cursorX} y1={geometry.pad - 12} x2={cursorX} y2={geometry.baseline} class="cursor" />
        {/if}
    </svg>
</figure> 

<style>
    .plate
    {
        margin: 0;
        border: var(--border-width) solid var(--colour-border);
        border-radius: var(--radius-lg);
        background: var(--colour-bg-surface);
        overflow: hidden;
    }

    .head
    {
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-sm) var(--spacing-base);
        align-items: baseline;
        justify-content: space-between;
        padding: var(--spacing-md) var(--spacing-base);
        border-bottom: var(--border-width) solid var(--colour-border);
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


    .reading
    {
        font-family: var(--font-mono);
        font-size: var(--font-size-xs);
        color: var(--colour-text-muted);
        font-variant-numeric: tabular-nums;
    }


    .reading .shaded { color: var(--colour-success); }
    .reading .exposed { color: var(--colour-warning); }


    svg 
    {
        display: block;
        width: 100%;
        height: 220px;
        touch-action: none;
        cursor: crosshair;
    }


    .grid
    {
        stroke: var(--colour-border);
        stroke-width: 1;
    }


    .tick
    {
        fill: var(--colour-text-muted);
        font-family: var(--font-mono);
        font-size: 11px;  
    }


    .band-shade
    {
        fill: var(--colour-success);
        opacity: 0.22;
    }


    .band-sun
    {
        fill: var(--colour-warning);
        opacity: 0.85;
    }


    .ridge
    {
        fill: none;
        stroke: var(--colour-success);
        stroke-width: 1.8;
        vector-effect: non-scaling-stroke;
    }


    .cursor
    {
        stroke: var(--colour-accent);   
        stroke-width: 1.6;
        vector-effect: non-scaling-stroke;
    }
</style>
