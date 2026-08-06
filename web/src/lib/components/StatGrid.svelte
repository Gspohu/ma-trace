<script lang="ts">
    import { decimal, hoursAndMinutes, integer } from "$lib/core/format";
    import type { RouteStats } from "$lib/core/types";


    interface Props
    {
        stats: RouteStats;
    }

    let { stats }: Props = $props();


    interface Figure
    {
        label: string; 
        value: string;
        unit: string;
        tone: "shade" | "sun" | "plain";
    }


    // denivele and duration only exist when the ground was measured, and both are
    // dropped rather than shown at zero when it was not
    const figures = $derived<Figure[]>([
        { label: "Distance", value: decimal(stats.km, 2), unit: "km", tone: "plain" },
        { label: "Sous couvert", value: decimal(stats.shade_pct, 1), unit: "%", tone: "shade" },
        { label: "Exposition", value: decimal(stats.exposure_pct, 1), unit: "%", tone: "sun" },
        { label: "Au soleil", value: integer(stats.sun_metres), unit: "m", tone: "sun" },
        ...(stats.has_elevation
            ? [{ label: "Denivele", value: "+" + integer(stats.up), unit: "m",
                 tone: "plain" as const }]
            : []),
        { label: "Sur route", value: integer(stats.road_metres), unit: "m", tone: "plain" },
        ...(stats.has_elevation
            ? [{ label: "Temps estime", value: hoursAndMinutes(stats.hours), unit: "",
                 tone: "plain" as const }]
            : [])
    ]);
</script>

<dl class="figures">
    {#each figures as figure (figure.label)}
        <div class="fig">
            <dt>{figure.label}</dt>
            <dd class="tone-{figure.tone}">
                {figure.value}{#if figure.unit}<span class="unit">{figure.unit}</span>{/if}
            </dd>
        </div>
    {/each}
</dl>

{#if stats.off_network_metres > 0}
    <p class="alarm">
        {integer(stats.off_network_metres)} m du tracé sortent du réseau OSM. Ne suivez pas ce GPX tel quel.
    </p>
{/if}


<style>
    .figures
    {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: var(--border-width);
        margin: 0;
        background: var(--colour-border);
        border: var(--border-width) solid var(--colour-border);
        border-radius: var(--radius-lg);
        overflow: hidden;
    }


    .fig
    {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-xs);
        padding: var(--spacing-base) var(--spacing-base) var(--spacing-md);
        background: var(--colour-bg-surface);
    }


    dt
    {
        font-family: var(--font-mono);
        font-size: var(--font-size-xs);
        letter-spacing: var(--letter-spacing-wide);
        text-transform: uppercase;
        color: var(--colour-text-muted);   
    }


    dd
    {
        margin: 0;
        font-family: var(--font-mono);  
        font-size: var(--font-size-xl);
        line-height: var(--line-height-tight);
        font-variant-numeric: tabular-nums;
        color: var(--colour-text-primary);
    }


    .tone-shade { color: var(--colour-success); }
    .tone-sun { color: var(--colour-warning); }


    .unit
    {
        margin-left: var(--spacing-2xs);
        font-size: var(--font-size-xs);
        color: var(--colour-text-muted);
    }

    .alarm
    {
        margin: var(--spacing-base) 0 0;
        padding: var(--spacing-md) var(--spacing-base);
        border-left: var(--border-width-thick) solid var(--colour-danger);
        background: var(--colour-danger-muted);
        color: var(--colour-text-primary);
        font-size: var(--font-size-sm);
        border-radius: var(--radius-md);
    }
</style>
