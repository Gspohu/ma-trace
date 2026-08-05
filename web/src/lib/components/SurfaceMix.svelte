<script lang="ts">
    import { mergeSurfaces, coverLabel, highwayLabel } from "$lib/core/surfaces";
    import { decimal } from "$lib/core/format";
    import type { Route } from "$lib/core/types";


    interface Props
    {
        route: Route;
    }

    let { route }: Props = $props();


    const slices = $derived(mergeSurfaces(route.surfaces));
    const totalHighway = $derived(route.highways
                                       .reduce((sum, h) => { return sum + h.metres; }, 0));
    const totalCover = $derived(route.covers
                                     .reduce((sum, c) => { return sum + c.metres; }, 0));
</script>

<section class="panel">
    <h2>Sous les pieds</h2>

    <div class="bar" role="img" aria-label="Repartition des revetements"> 
        {#each slices as slice (slice.label)}
            <span style="width: {slice.share}%; background: {slice.token}" title={slice.label}></span>
        {/each}
    </div>

    <ul class="legend">
        {#each slices as slice (slice.label)}
            <li>
                <i style="background: {slice.token}"></i>
                <span>{slice.label}</span>
                <b>{decimal(slice.metres / 1000, 2)} km</b>
            </li>
        {/each}
    </ul>

    <h2 class="second">Types de voies</h2>
    <ul class="ways">
        {#each route.highways as way (way.key)}
            <li>
                <span>{highwayLabel(way.key)}</span>
                <b>{decimal((100 * way.metres) / totalHighway, 1)} %</b>
            </li>
        {/each}
    </ul>

    <h2 class="second">Au-dessus de la tête</h2>
    <ul class="ways">
        {#each route.covers as cover (cover.key)}
            <li>
                <span>{coverLabel(cover.key)}</span>
                <b>{decimal((100 * cover.metres) / totalCover, 1)} %</b>
            </li>
        {/each}
    </ul>
</section>

<style>
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


    .bar
    {
        display: flex;
        height: 1.6rem;
        border-radius: var(--radius-md);
        overflow: hidden;
        border: var(--border-width) solid var(--colour-border);
    }


    .bar span { display: block; }


    .legend,
    .ways
    {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-sm);
        margin: 0;
        padding: 0;
        list-style: none;
    }

    .legend li
    {
        display: grid;   
        grid-template-columns: 0.85rem 1fr auto;
        gap: var(--spacing-md);
        align-items: center;
        font-size: var(--font-size-sm);  
    }


    .ways li
    {
        display: flex;
        justify-content: space-between;
        gap: var(--spacing-md);
        font-size: var(--font-size-sm);
    }


    .legend i
    {
        width: 0.85rem;
        height: 0.85rem;
        border-radius: var(--radius-sm);
    }


    b
    {
        font-family: var(--font-mono);
        font-weight: var(--font-weight-regular);
        font-variant-numeric: tabular-nums;
        color: var(--colour-text-muted);
    }
</style>
