<script lang="ts">  
    import "$lib/styles/reset.css";
    import "$lib/styles/tokens.css";   
    import "leaflet/dist/leaflet.css";
    import "../app.css";

    let { children } = $props();
</script>

{@render children()}
