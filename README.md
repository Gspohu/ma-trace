# Ma trace

Traceur de randonnée qui route **en privilégiant l'ombre**. Chaque mètre marché hors
couvert forestier coûte plus cher au routeur qu'un mètre sous les arbres, donc il
accepte volontiers un détour pour rester au frais.

Né d'un besoin très concret : marcher dans les Vosges du Nord un jour à 34 °C.

Il récupère le réseau piéton et le couvert forestier depuis OpenStreetMap, pondère
chaque arête du graphe par son exposition au soleil, route un Dijkstra à travers les
points de passage et referme la boucle. En sortie : le pourcentage réel passé sous
couvert, le mélange des revêtements, l'altimétrie et un GPX.

## Architecture

Séparation stricte. `core/` ignore jusqu'à l'existence d'une interface.

```
core/       le moteur, logique métier pure
  overpass.py   client Overpass, bascule entre miroirs
  extract.py    source locale, lit un extrait Geofabrik (le chemin rapide)
  library.py    catalogue des index construits, choisit celui qui couvre la zone
  canopy.py     assemblage des polygones forestiers, clairières comprises
  graph.py      graphe piéton, règles d'accès OSM, pondération par l'ombre
  router.py     Dijkstra, statistiques
  elevation.py  altimétrie EU-DEM, lissage, dénivelé
  dem_cache.py  mémo disque des altitudes déjà interrogées
  gpx.py        écriture GPX 1.1
  pipeline.py   orchestration

cli/        adaptateurs ligne de commande, minces par contrat
  generate.py    trace une boucle
  build_index.py prépare l'index OSM local
  bridge.py      pont JSON pour le front, un process par tracé
  serve.py       moteur résident, garde les index en mémoire

data/       données de référence (presets, index généré)
web/        SvelteKit, interface uniquement
```

## Mise en route

```bash
pip install -e .          # router : requests et shapely suffisent
pip install -e ".[index]" # en plus, construire ses propres index (osmium)
cd web && npm install
```

## Pourquoi un index local

Le profilage a été sans appel. Sur une boucle de 13 km :

| Étape | Temps | Part |
|---|---|---|
| Overpass (réseau + forêt) | 447,6 s | **99,8 %** |
| Tout le calcul (GEOS, Dijkstra, stats) | 0,86 s | 0,2 % |

Le Dijkstra prend **30 ms**. Optimiser le calcul ne sert donc strictement à rien, le
coût est entièrement dans l'attente d'un serveur distant. Réécrire le moteur en Rust
ferait gagner, au mieux, quelques dizaines de millisecondes sur 448 secondes.

La vraie réponse est de télécharger les données une fois et de les interroger en local.

```bash
mkdir -p extracts && cd extracts
curl -O https://download.geofabrik.de/europe/france/alsace-latest.osm.pbf
curl -O https://download.geofabrik.de/europe/france/lorraine-latest.osm.pbf
# vérifier les .md5 fournis par geofabrik avant d'aller plus loin
cd .. && python3 -m cli.build_index --name vosges --label "Vosges du Nord"  
```

Trois minutes, une seule fois. Résultat : **448 s devient 1,2 s**, soit un facteur 370,
pour des tracés identiques au mètre près. Et plus aucun appel réseau pour router, donc
ça marche hors ligne.

Sans `--bbox`, la zone est déduite de ce que les extraits déclarent eux-mêmes dans leur
en-tête. Il faut ici les deux extraits parce que les Vosges du Nord chevauchent la
Moselle et le Bas-Rhin.

Plusieurs index cohabitent dans `data/index/`, un par massif. Chacun porte un
`.meta.json` qui annonce sa portée, donc choisir le bon ne demande pas d'ouvrir les
vingt mégaoctets des autres. Le routeur prend le plus petit index qui couvre
entièrement la sortie, et repasse par Overpass quand aucun ne convient.

```bash
python3 -m cli.build_index --list
```

## Utilisation

L'interface web, où les points de passage se posent au clic sur la carte : 

```bash
cd web && npm run dev
```

Facultatif mais recommandé, dans un autre terminal, le moteur résident :

```bash
python3 -m cli.serve
```

Sans lui, chaque tracé relance un interpréteur Python et recharge les 20 Mo d'index :
2,4 s perdus à chaque clic. Le front le détecte tout seul et retombe sur l'ancien mode
s'il n'est pas lancé, donc rien ne casse si vous l'oubliez.

| | tracé de 13 km avec altimétrie |
|---|---|
| process jetable, altimétrie froide | 15,1 s |
| process jetable, altimétrie en cache | 5,5 s |
| moteur résident, altimétrie en cache | **1,3 s** |

Les altitudes déjà interrogées sont mémorisées dans `data/cache/`, donc déplacer un seul
point de passage ne rachète pas le relief de la partie inchangée.

Ou en ligne de commande :

```bash
python3 -m cli.generate --preset hanau-courte -o boucle
python3 -m cli.generate -w 49.008,7.535,Depart -w 49.005,7.565,Falkenstein -o perso
python3 -m cli.generate --list-presets
```

Le réglage qui compte est `--sun-penalty`. À 1 l'ombre est ignorée et on obtient le plus
court chemin. À 4, la valeur par défaut, le routeur détourne volontiers de 200 m pour
rester couvert.

## À lire avant de partir marcher

**Le balisage ne suit pas le GPX.** Le tracé emprunte le réseau OSM, pas forcément un
itinéraire balisé. Naviguez au GPS, pas aux marques peintes sur les arbres.

**L'ombre est une approximation.** Elle vient des polygones forestiers d'OSM, pas d'une
densité de canopée ni de la course du soleil. Une futaie de hêtres et une coupe rase
comptent pareil.

**Le dénivelé est estimé.** EU-DEM 25 m. Le tracé est d'abord rééchantillonné tous les
20 m *le long du chemin*, sinon le D+ dépendrait de la finesse avec laquelle un
contributeur a dessiné tel sentier : sur une boucle réelle, l'espacement des nœuds OSM
va de 0,7 m à 208 m. Vient ensuite un filtre gaussien de 25 m d'écart-type, puis le
comptage des montées avec un seuil de 1,5 m et un suivi des points de retournement.

Le suivi des retournements n'est pas un détail : ancrer la référence sur le dernier
point mesuré plutôt que sur le sommet atteint rabotait 10 % du D+, et cassait
l'identité qu'une boucle fermée doit vérifier, D+ = D-.

**Le dénivelé est estimé là où EU-DEM est le moins bon.** Sa précision se dégrade quand
la pente augmente et quand le couvert forestier s'épaissit. Or ce routeur cherche
précisément le sous-bois : les chiffres de D+ sont donc produits dans les conditions les
moins favorables au modèle de terrain. La spécification annonce 7 m de RMSE, le rapport
de validation en mesure 2,9 m en moyenne, et aucun des deux ne décrit une hêtraie en
dévers.

## Un piège qui a coûté cher

Les règles d'accès OSM ne se laissent pas écrire dans un filtre Overpass. Les escaliers
du château de Waldeck portent `access=no` **et** `foot=yes` : interdits aux véhicules,
ouverts aux piétons. Un filtre naïf sur `access` les jetait, un filtre trop laxiste
laissait passer de vraies voies privées.

Le tri se fait donc en Python, dans `graph.is_walkable`, où la règle peut être exprimée
correctement : le tag `foot` l'emporte toujours sur le tag `access` générique.

## Données

OpenStreetMap (ODbL) pour le réseau, la forêt et le fond de carte. EU-DEM via
OpenTopoData pour l'altimétrie.
