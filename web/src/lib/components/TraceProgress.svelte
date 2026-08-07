<script lang="ts">
    import { PHASES, indexOf, isSetback, phaseOf, readable } from "$lib/core/phases";

    interface Props
    {
        notes: string[];
    }

    let { notes }: Props = $props();


    // the furthest phase any note has announced. Never walked back, a late note about
    // an earlier step must not make the bar retreat
    const reached = $derived.by(() =>
    {
        let best = 0;
        for (const note of notes)
        {
            const at = indexOf(phaseOf(note));
            if (at > best)
            {
                best = at;
            }
        }

        return best;
    });

    const last = $derived(notes.length ? notes[notes.length - 1] : "");
    const stalled = $derived(last ? isSetback(last) : false);
    const detail = $derived(last ? readable(last) : "démarrage de l'interpréteur");
    const here = $derived(PHASES[reached]?.label ?? "");
</script>

<section class="progress" aria-live="polite">
    <ol class="steps">
        {#each PHASES as phase, at (phase.key)}
            <li class:done={at < reached} class:current={at === reached}>
                <span class="bar"></span>
                <span class="name">{phase.label}</span>
            </li>
        {/each}
    </ol>

    <p class="where">{here} <span class="rank">{reached + 1} sur {PHASES.length}</span></p>
    <p class="detail" class:stalled>{detail}</p>
</section>

<style>
    .progress
    {
        padding: var(--spacing-base);
        background: var(--colour-bg-surface-raised);
        border-radius: var(--radius-md);
    }

    .steps
    {
        display: flex;
        gap: var(--spacing-xs);
        margin: 0 0 var(--spacing-md);
        padding: 0;
        list-style: none;
    }

    .steps li
    {
        flex: 1;
        min-width: 0;
    }

    .bar
    {
        display: block;
        height: 0.375rem;
        border-radius: var(--radius-pill);
        background: var(--colour-border);
        transition: background var(--transition-base);
    }

    .done .bar
    {
        background: var(--colour-accent);
    }

    /* the one under way breathes, which is the whole point : a still bar reads as a
       hung page, and overpass can take minutes to answer */
    .current .bar
    {
        background: var(--colour-accent-muted);
        animation: working 1.4s ease-in-out infinite;
    }

    /* the labels never get to widen the panel : cut off before they push the page into
       a sideways scroll, which is what they did on a phone */
    .name
    {
        display: block;
        margin-top: var(--spacing-xs);
        font-size: var(--font-size-xs);
        color: var(--colour-text-secondary);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .current .name
    {
        color: var(--colour-text-primary);
        font-weight: var(--font-weight-medium);
    }

    .where
    {
        display: none;
        margin: 0 0 var(--spacing-xs);
        font-size: var(--font-size-sm);
        font-weight: var(--font-weight-medium);
        color: var(--colour-text-primary);
    }

    .rank
    {
        margin-left: var(--spacing-xs);
        font-weight: var(--font-weight-regular);
        color: var(--colour-text-secondary);
    }

    .detail
    {
        margin: 0;
        font-size: var(--font-size-sm);
        font-family: var(--font-mono);
        color: var(--colour-text-secondary);
        overflow-wrap: anywhere;
    }

    /* too narrow for seven labels. The bar keeps its segments and the step is spelled
       out once underneath */
    @media (max-width: 30rem)
    {
        .name
        {
            display: none;
        }

        .where
        {
            display: block;
        }
    }

    .detail.stalled
    {
        color: var(--colour-warning);
    }

    @keyframes working
    {
        0%, 100% { opacity: 0.35; }
        50% { opacity: 1; }
    }

    @media (prefers-reduced-motion: reduce)
    {
        .current .bar
        {
            animation: none;
        }
    }
</style>
