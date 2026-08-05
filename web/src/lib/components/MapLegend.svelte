<script lang="ts">
    import { mergeSurfaces } from "$lib/core/surfaces";
    import type { ColourMode, Route } from "$lib/core/types";


    interface Props
    {
        route: Route | null;
        mode: ColourMode;
        showCanopy: boolean;
        showLandmarks: boolean;
    }


    let { route, mode = $bindable(), showCanopy = $bindable(),
          showLandmarks = $bindable() }: Props = $props();


    // oly the surfaces actually walked deserv a swatch, not the whole actalogue
    const slices = $derived(route ? mergeSurfaces(route.surfaces) : []);
</script>

<div class="bar">
    <div class="modes" role="group" aria-label="Ce que montrent les couleurs">
        <button
            type="button"
            aria-pressed={mode === "exposure"}
            onclick={() => { mode = "exposure"; }}
        >
            Exposition
        </button>
        <button
            type="button"
            aria-pressed={mode === "surface"}
            onclick={() => { mode = "surface"; }}
        >
            Revêtement
        </button> 
    </div>

    <ul class="keys">
        {#if mode === "exposure"}
            <li><i style="background: var(--colour-success)"></i>Sous couvert</li>
            <li><i style="background: var(--colour-warning)"></i>Au soleil</li>
        {:else}
            {#each slices as slice (slice.label)}
                <li><i style="background: {slice.token}"></i>{slice.label}</li>
            {/each}
        {/if}   
    </ul>

    <label class="canopy">
        <input type="checkbox" bind:checked={showCanopy} />
        Forêt
    </label>

    <label class="canopy">
        <input type="checkbox" bind:checked={showLandmarks} />
        Repères
    </label>
</div>

{#if mode === "surface"}
    <p class="note">
        Le bitume est souvent sous les arbres : il apparaît vert en mode Exposition, c'est
        pour ça qu'il faut ce second mode pour le voir.
    </p>
{/if}


<style>
    .bar
    {
        display: flex; 
        flex-wrap: wrap;
        align-items: center;
        gap: var(--spacing-md) var(--spacing-lg);
        padding: var(--spacing-md) var(--spacing-base);  
        border: var(--border-width) solid var(--colour-border);
        border-radius: var(--radius-lg);
        background: var(--colour-bg-surface);
    } 


    .modes
    {
        display: flex;
        gap: var(--spacing-2xs);
        padding: var(--spacing-2xs);
        border: var(--border-width) solid var(--colour-border);
        border-radius: var(--radius-md);
        background: var(--colour-bg-primary);
    }


    .modes button
    {
        padding: var(--spacing-sm) var(--spacing-base);
        font-family: var(--font-sans);
        font-size: var(--font-size-xs);
        font-weight: var(--font-weight-medium);
        color: var(--colour-text-secondary);
        background: transparent; 
        border: 0;
        border-radius: var(--radius-sm);
        cursor: pointer;
        transition: background var(--transition-fast), color var(--transition-fast);
    }


    .modes button:hover
    {
        color: var(--colour-text-primary);
    }


    .modes button[aria-pressed="true"]
    {
        background: var(--colour-accent);
        color: var(--colour-text-primary);
    }


    .modes button:focus-visible
    {
        outline: var(--border-width-thick) solid var(--colour-border-focus);
        outline-offset: 2px;
    }


    .keys
    {
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-sm) var(--spacing-base); 
        margin: 0;
        padding: 0;
        list-style: none;
        font-size: var(--font-size-xs);
        color: var(--colour-text-secondary);
    }


    .keys li
    {
        display: inline-flex;
        align-items: center;
        gap: var(--spacing-sm);
    }


    .keys i
    {
        width: 1.1rem;
        height: 0.35rem;
        border-radius: var(--radius-sm);
    }


    .canopy
    {
        display: inline-flex;
        align-items: center;
        gap: var(--spacing-sm);
        margin-left: auto;
        font-size: var(--font-size-xs);
        color: var(--colour-text-secondary);
        cursor: pointer;
    }

    .canopy input
    {
        accent-color: var(--colour-accent);
    }


    .note
    {
        margin: var(--spacing-sm) 0 0;
        font-size: var(--font-size-xs);
        line-height: var(--line-height-normal);
        color: var(--colour-text-muted);
    }
</style>
