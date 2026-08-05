<script lang="ts">
    import { coordinate, decimal } from "$lib/core/format";
    import type { Preset, Waypoint } from "$lib/core/types";


    interface Props
    {
        presets: Preset[];
        waypoints: Waypoint[];
        sunPenalty: number;
        roadPenalty: number;
        paceFactor: number;
        maxSac: number;
        withElevation: boolean;
        busy: boolean;
        onsubmit: () => void;
        onimport: (document: string) => void;
    }


    // waypoints is bonud, htis component owns its edits. Passing callbcks back up
    // to mutate the very array we already hold a two way binding to would be daft
    let {
        presets,
        waypoints = $bindable(),
        sunPenalty = $bindable(),
        roadPenalty = $bindable(),
        paceFactor = $bindable(),
        maxSac = $bindable(),
        withElevation = $bindable(),
        busy,
        onsubmit,
        onimport
    }: Props = $props();


    async function pickFile(event: Event)
    {
        const input = event.currentTarget as HTMLInputElement;
        const chosen = input.files?.[0];
        if (!chosen)
        {
            return;
        }

        const document = await chosen.text();
        // picking the same fichier twice in a row fires no change event without this
        input.value = "";
        onimport(document);
    }

    const ready = $derived(waypoints.length >= 2 && !busy);

    // the swiss alpine club scale, which is what osm's sac_scale spells out
    const SAC_LABELS = [
        "Randonnée",
        "Montagne",
        "Montagne exigeante",
        "Alpin",
        "Alpin exigeant",
        "Alpin difficile"
    ];

    const sacLabel = $derived(SAC_LABELS[maxSac - 1] ?? "");


    function usePreset(preset: Preset)
    {
        waypoints = preset.waypoints.map((w) => { return { ...w }; });
    }


    function remove(index: number)
    {
        waypoints = waypoints.filter((_, i) => { return i !== index; });
    }

    function rename(index: number, name: string)
    {
        waypoints[index].name = name;
    }
</script>

<aside class="panel">
    <header>
        <h1>Ma trace</h1>
        <p>Routage pondéré par l'ombre. Chaque mètre au soleil coûte plus cher
           qu'un mètre sous les arbres.</p>
    </header>

    <section>
        <h2>Parcours prêts</h2>
        <div class="presets">
            {#each presets as preset (preset.key)}
                <button type="button" class="ghost" onclick={() => usePreset(preset)} disabled={busy}>
                    {preset.label}
                </button>
            {/each}
        </div>
    </section>

    <section>
        <div class="rowhead">
            <h2>Points de passage</h2> 
            {#if waypoints.length > 0}
                <button type="button" class="link" onclick={() => (waypoints = [])} disabled={busy}>
                    tout effacer
                </button>
            {/if}
        </div>

        {#if waypoints.length === 0}
            <p class="hint">Cliquez sur la carte pour poser un premier point. La boucle se referme automatiquement sur le point de départ.</p>
        {:else}
            <ol class="waypoints">
                {#each waypoints as waypoint, index (index)}
                    <li>
                        <span class="rank">{index + 1}</span>
                        <label class="grow">
                            <span class="sr">Nom du point {index + 1}</span>
                            <input
                                type="text" 
                                value={waypoint.name} 
                                oninput={(e) => { rename(index, e.currentTarget.value); }}
                                disabled={busy} 
                            />
                            <small>{coordinate(waypoint.lat, waypoint.lon)}</small>
                        </label>
                        <button
                            type="button"
                            class="drop"
                            onclick={() => { remove(index); }}
                            disabled={busy}
                            aria-label="Retirer le point {index + 1}"
                        >
                            &times;
                        </button>
                    </li>
                {/each}
            </ol>
        {/if}
    </section>

    <section>
        <h2>Réglages</h2>

        <label class="slider">
            <span>Coût d'un mètre au soleil</span>
            <input type="range" min="1" max="8" step="0.5" bind:value={sunPenalty} disabled={busy} />
            <b>&times;{sunPenalty}</b>
        </label>
        <p class="hint">À 1, l'ombre est ignorée et le tracé devient le plus court. Plus haut, le routeur accepte des détours pour rester couvert.</p>

        <label class="slider">
            <span>Surcoût du bitume</span>
            <input type="range" min="1" max="5" step="0.2" bind:value={roadPenalty} disabled={busy} />
            <b>&times;{roadPenalty}</b>
        </label>

        <!-- TODO the walker sets this by hand while pace.calibrate already knows how to
             read it off past outings, nothing records them yet -->
        <label class="slider">
            <span>Allure</span>
            <input type="range" min="0.6" max="2" step="0.05" bind:value={paceFactor} disabled={busy} />
            <b>&times;{decimal(paceFactor, 2)}</b>
        </label>
        <p class="hint">Au-dessus de 1 si vous marchez moins vite que la référence, qui ne compte aucune pause.</p>

        <label class="slider">
            <span>Difficulté maximale</span>
            <input type="range" min="1" max="6" step="1" bind:value={maxSac} disabled={busy} />
            <b>T{maxSac}</b>
        </label>
        <p class="hint">{sacLabel}. Les chemins que l'OSM annonce au-dessus sont écartés du tracé.</p>

        <label class="check">
            <input type="checkbox" bind:checked={withElevation} disabled={busy} />
            <span>Altimétrie <small>(plus lent, une seconde par centaine de points)</small></span>
        </label>
    </section>

    <button type="button" class="go" onclick={onsubmit} disabled={!ready}>
        {#if busy}
            Calcul en cours...
        {:else}
            Tracer la boucle
        {/if}
    </button>

    <section>
        <h2>Analyser une trace</h2>
        <label class="import">
            <input type="file" accept=".gpx,application/gpx+xml" onchange={pickFile}
                   disabled={busy} />
            <span>Ouvrir un GPX</span>
        </label>
        <p class="hint">Ombre, revêtements et dénivelé d'une trace déjà tracée, la vôtre ou celle d'un autre.</p>
    </section>
</aside>

<style>
    .panel
    {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-lg);
        padding: var(--spacing-lg);
        border: var(--border-width) solid var(--colour-border);
        border-radius: var(--radius-lg);
        background: var(--colour-bg-surface);
    }  


    h1
    {
        margin: 0 0 var(--spacing-xs);
        font-size: var(--font-size-xl);
        font-weight: var(--font-weight-bold);
        letter-spacing: var(--letter-spacing-tight);
        color: var(--colour-text-primary);
    }


    header p
    {
        margin: 0;
        font-size: var(--font-size-sm);
        color: var(--colour-text-secondary);
        line-height: var(--line-height-normal);
    }


    h2
    {
        margin: 0 0 var(--spacing-md);
        font-size: var(--font-size-xs);
        font-weight: var(--font-weight-semibold);
        letter-spacing: var(--letter-spacing-wider);
        text-transform: uppercase;
        color: var(--colour-text-muted);
    }

    .rowhead
    {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: var(--spacing-sm);
    }


    .presets
    {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-sm);
    }


    button
    {
        font-family: var(--font-sans);
        cursor: pointer;
        transition: background var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
    }


    button:disabled
    {
        opacity: 0.5;
        cursor: not-allowed;
    }


    button:focus-visible
    {
        outline: var(--border-width-thick) solid var(--colour-border-focus);
        outline-offset: 2px;
    }


    .ghost
    {
        padding: var(--spacing-md) var(--spacing-base);
        text-align: left;
        font-size: var(--font-size-sm);
        color: var(--colour-text-primary);
        background: var(--colour-bg-surface-raised);
        border: var(--border-width) solid var(--colour-border);  
        border-radius: var(--radius-md);
    }


    .ghost:hover:not(:disabled)
    {
        background: var(--colour-bg-surface-hover);
        border-color: var(--colour-border-hover);
    }


    .link
    {
        padding: 0;
        border: 0;
        background: none;
        color: var(--colour-accent); 
        font-size: var(--font-size-xs);
        text-decoration: underline;
    }


    .waypoints
    {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-sm);
        margin: 0;
        padding: 0; 
        list-style: none;
    }


    .waypoints li
    {
        display: flex;
        align-items: center;
        gap: var(--spacing-md);
    } 


    .rank
    {
        flex: 0 0 auto;
        width: 1.7rem;
        height: 1.7rem;
        display: grid;
        place-items: center;
        border-radius: var(--radius-circle);
        background: var(--colour-accent-muted);
        color: var(--colour-accent);
        font-family: var(--font-mono);
        font-size: var(--font-size-xs);
    }


    .grow
    {
        flex: 1 1 auto;
        display: flex;
        flex-direction: column;
        gap: var(--spacing-2xs);
        min-width: 0;
    }


    input[type="text"]
    {
        width: 100%;
        padding: var(--spacing-sm) var(--spacing-md);
        font-family: var(--font-sans);
        font-size: var(--font-size-sm);
        color: var(--colour-text-primary);
        background: var(--colour-bg-primary);
        border: var(--border-width) solid var(--colour-border);
        border-radius: var(--radius-md);
    }


    input[type="text"]:focus
    {
        outline: none;
        border-color: var(--colour-border-focus); 
        box-shadow: 0 0 0 3px var(--colour-focus-ring);
    }


    small
    {
        font-family: var(--font-mono);
        font-size: var(--font-size-xs);
        color: var(--colour-text-muted);
    }


    .drop
    {
        flex: 0 0 auto;
        width: 1.9rem;
        height: 1.9rem;
        display: grid;
        place-items: center;
        font-size: var(--font-size-md);
        line-height: 1;
        color: var(--colour-text-muted);
        background: none;
        border: var(--border-width) solid var(--colour-border);
        border-radius: var(--radius-md);
    }


    .drop:hover:not(:disabled)
    {
        color: var(--colour-danger);
        border-color: var(--colour-danger);
    }

    .hint
    {
        margin: var(--spacing-sm) 0 0;
        font-size: var(--font-size-xs);
        line-height: var(--line-height-normal);
        color: var(--colour-text-muted);
    }


    .slider
    {
        display: grid;
        grid-template-columns: 1fr auto;
        align-items: center;
        gap: var(--spacing-sm) var(--spacing-md);
        margin-top: var(--spacing-md);
        font-size: var(--font-size-sm);
        color: var(--colour-text-secondary);
    }


    .slider span { grid-column: 1 / -1; }


    .slider input[type="range"]
    {
        width: 100%;
        accent-color: var(--colour-accent);
    }


    .slider b
    {
        font-family: var(--font-mono);
        font-weight: var(--font-weight-regular);
        font-variant-numeric: tabular-nums;
        color: var(--colour-text-primary);
    }


    .check
    {
        display: flex;
        align-items: flex-start;
        gap: var(--spacing-md);
        margin-top: var(--spacing-md);
        font-size: var(--font-size-sm);
        color: var(--colour-text-secondary);
    }


    .check input
    {
        margin-top: 0.25rem;
        accent-color: var(--colour-accent);
    } 


    .go
    {
        padding: var(--spacing-base);
        font-size: var(--font-size-sm);
        font-weight: var(--font-weight-semibold);
        color: var(--colour-text-primary);
        background: var(--colour-accent);
        border: 0;
        border-radius: var(--radius-md);
    }


    .go:hover:not(:disabled) { background: var(--colour-accent-hover); }


    /* the native file input is unstylable across browsers, the label wears the button
       look and the input itself only has to stay reachable by keyboard and by reader */
    .import
    {
        display: block;
        position: relative;
        overflow: hidden;
    }


    .import input
    {
        position: absolute;
        inset: 0;
        opacity: 0;
        width: 100%;
        cursor: pointer;
    }


    .import span
    {
        display: block;
        padding: var(--spacing-md);
        font-size: var(--font-size-sm);
        text-align: center;
        color: var(--colour-text-primary);
        border: var(--border-width) dashed var(--colour-border);
        border-radius: var(--radius-md);
    }


    .import:hover span { border-color: var(--colour-accent); }
    .import:focus-within span { border-color: var(--colour-accent); }


    .sr
    {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip-path: inset(50%);
        white-space: nowrap;
    }
</style>
