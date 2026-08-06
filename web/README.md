# L'interface

Adaptateur mince, par contrat : elle pose des points sur une carte, envoie la demande au
moteur et dessine ce qu'il rend. Aucune règle de routage ne vit ici, `core/` les tient
toutes.

Le moteur tourne dans le navigateur, en WebAssembly. `npm run stage` recopie `core/` et
`cli/` dans `static/engine/` et récupère l'interpréteur dans `static/runtime/`. Le
worker les monte ensuite dans un système de fichiers virtuel et appelle
`cli.engine.handle_request`, exactement comme le fait la ligne de commande. Deux
implémentations qui divergent, c'est le piège qu'on évite ainsi.

```bash
npm install
npm run dev       # recupere le runtime au passage
npm run build     # site statique dans build/
npm run check     # types, et rien d'autre ne doit passer
```

Le dénivelé et la durée n'apparaissent pas en ligne. Ils demandent un modèle de terrain,
et ceux qu'un navigateur peut interroger mesurent la cime des arbres : sur une trace
sous couvert, le D+ ressortait majoré de moitié. Le README à la racine détaille la
mesure, et la ligne de commande donne ces deux chiffres.

## Ce qui vit où

    src/lib/components   la carte, le panneau, les graphiques
    src/lib/core         le pont vers le moteur, les formats, les couleurs de surface
    src/routes           une seule page, prerendue
    scripts              recuperation du runtime et recopie du moteur
    static/runtime       l'interpreteur, servi depuis notre propre origine
