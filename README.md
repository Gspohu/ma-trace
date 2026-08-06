# Ma trace

Traceur de randonnée qui route **en privilégiant l'ombre**. Chaque mètre marché hors
couvert forestier coûte plus cher au routeur qu'un mètre sous les arbres, donc il
accepte volontiers un détour pour rester au frais.

Né d'un besoin très concret : marcher dans les Vosges du Nord un jour à 34 °C.

Il récupère le réseau piéton et le couvert forestier depuis OpenStreetMap, pondère
chaque arête du graphe par son exposition au soleil, route un Dijkstra à travers les
points de passage et referme la boucle. En sortie : le pourcentage réel passé sous
couvert, le mélange des revêtements, l'altimétrie et un GPX.

## Ce qu'il y a dans le dépôt

Séparation stricte. `core/` ignore jusqu'à l'existence d'une interface.

```
core/       le moteur, logique métier pure
  overpass.py   client Overpass, bascule entre miroirs
  extract.py    source locale, lit un extrait Geofabrik (le chemin rapide)
  library.py    catalogue des index construits, choisit celui qui couvre la zone
  canopy.py     assemblage des polygones forestiers, clairières comprises
  graph.py      graphe piéton, règles d'accès OSM, pondération par l'ombre
  router.py     Dijkstra, statistiques
  matching.py   remet une trace importée sur le réseau OSM qui passe dessous
  elevation.py  altimétrie EU-DEM, lissage, dénivelé
  dem_cache.py  mémo disque des altitudes déjà interrogées
  pace.py       fonction de Tobler, durée de marche, allure personnelle
  landmarks.py  ce qui compte comme repère, partagé par les deux sources
  geometry.py   distances, boîtes englobantes, rééchantillonnage
  gpx.py        écriture GPX 1.1
  pipeline.py   orchestration

cli/        adaptateurs ligne de commande, minces par contrat
  generate.py    trace une boucle
  analyse.py     lit un GPX venu d'ailleurs et dit ce qu'il traverse
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

## Le même moteur dans un navigateur

Le site publié fait tourner `core/` tel quel, compilé en WebAssembly, sans rien à
installer et sans serveur derrière. Le réseau et le couvert viennent d'Overpass, le
Dijkstra tourne dans un worker, et le GPX se télécharge à la fin. C'est le même code
qu'en ligne de commande, monté dans un système de fichiers virtuel : deux
implémentations qui divergent sont exactement ce qu'on voulait éviter.

Une chose y manque, et c'est délibéré : **ni dénivelé ni durée**. Les deux demandent un
modèle de terrain, et aucun de ceux qu'un navigateur peut interroger n'en est un. Ceux
qui sont ouverts mesurent la cime des arbres, pas le sol. Mesuré sur une boucle des
Vosges du Nord, le D+ passait de 293 à 480 m, et l'erreur grandit à mesure que le
routeur réussit à passer sous le couvert. Un chiffre faux vaut moins que pas de
chiffre, donc l'interface le dit et renvoie à la ligne de commande.

```bash
cd web && npm run build    # recupere le runtime, recopie core/ et cli/, construit
```

## Tracer une boucle

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

`--pace-factor` ne change pas le tracé, seulement le temps annoncé : au-dessus de 1 si
vous marchez moins vite que la référence.

`--max-sac` est un garde-fou et pas une préférence : aucun raccourcis ne rend acceptable
de proposer une cotation alpine à qui a demandé une balade. Par defaut T2, sur l'échelle
T1 à T6 du Club alpin suisse que porte le tag `sac_scale`. Au dessus, les chemins sont
simplement absent du graphe.

## Analyser une trace qu'on n'a pas tracée

Le même moteur sait lire un GPX venu d'ailleur et dire ce qu'il traverse : le couvert,
les revêtements, le dénivelé, la durée. Aucune différence de traitement, c'est le même
code qui répond, et les chiffres sont donc directement comparable.

```bash
python3 -m cli.analyse rando.gpx
python3 -m cli.analyse rando.gpx --no-elevation -o analyse
```

L'interface web accèpte le même fichier, par le bouton *Ouvrir un GPX*.

Rien n'est recalculé ni redressé : la trace est prise telle quelle, et chaque segment
est racroché au chemin OSM qui passe dessous, à 25 m près. Au dela le segment est
compté **hors réseau** plutôt que rattaché de force au chemin le plus proche, parmis
tous ceux qui traînent autour.

Deux détails qui comptent :

**L'ombre est lue sur le sol effectivement parcouru**, jamais sur le chemin reconnu
dessous. Quel chemin passe sous une trace est une suposition, ou passe la trace n'en
est pas une. La nuance parait mince, elle ne l'est pas sur un sentier qui longe une
lisiere.

**Le réseau est chargé sans filtre de dificulté.** Une trace peut très bien franchir un
passage coté T4, malgrés tout, et c'est justement ce qu'on veut apprendre en l'ouvrant.

Les altitudes que porte le fichier sont ignorés au profit d'EU-DEM. Un baromètre et un
modèle de terrain ne mesurent pas la même chose, et les mélangers rendrait deux traces
incomparables.

## À lire avant de partir marcher

**Le balisage ne suit pas le GPX.** Le tracé emprunte le réseau OSM, pas forcément un
itinéraire balisé. Naviguez au GPS, pas aux marques peintes sur les arbres.

**L'ombre est une approximation.** Elle vient des polygones forestiers d'OSM et de leur
tag `leaf_type`, pas d'une mesure de densité ni de la course du soleil. La course du
soleil est volontairement exclue : une trace calée sur une heure et une date serait
périssable, or un GPX doit rester rejouable n'importe quel jour.

Ce qui est pris en compte, c'est ce qu'un couvert laisse passer en pleine feuillaison,
sous peuplement fermé : **8 % sous résineux**, **16 % sous feuillus**, 12 % en foret
mixte. Le cout d'un mètre au soleil est payé au prorata, donc le routeur préfère une
plantation d'épicéas à une chênaie claire, ce qu'un marcheur sens avant de le lire.

Ces deux chiffres valent donc pour la saison où l'on marche au soleil, de mai à
septembre. Un feuillu sans ses feuilles n'abrite quasiment plus, et le tracé rendu en
janvier reste celui d'un mois de juillet : c'est la limite du modèle.

> [Cescatti A. (1998)](https://doi.org/10.1051/forest:19980106), *Effects of needle
> clumping in shoots and crowns on the radiative regime of a Norway spruce canopy*,
> Annales des Sciences Forestières **55**, 89-102 : 4,9 % du rayonnement direct et
> 10,9 % du diffus sous un peuplement fermé de LAI 7,84.
>
> [Sercu B.K. *et al.* (2017)](https://doi.org/10.1002/ece3.3528), *How tree species
> identity and diversity affect light transmittance to the understory in mature
> temperate forests*, Ecology and Evolution **7**(24), 10861-10870 : après
> feuillaison, 15 % sous hêtre, 16 % sous chêne pédonculé, 19 % sous chêne rouge.

Un massif tagué `leaf_type=leafless` n'est pas compté comme couvert du tout : du bois nu
n'abrite personne, et lui préter l'ombre d'une chênaie serait promettre ce qui n'existe
pas. Un massif sans tag recoit la valeur des feuillus, la plus prudente des deux.

D'où deux chiffres au lieu d'un : **sous couvert** dit quelle part du trajet passe sous
les arbres, **exposition** dit quelle part du plein soleil vous recevez vraiement. Sur
la boucle de Hanau, 94 % sous couvert mais 21 % d'exposition.

**Le dénivelé est estimé.** EU-DEM 25 m. Le tracé est d'abord rééchantillonné tous les
20 m *le long du chemin*, sinon le D+ dépendrait de la finesse avec laquelle un
contributeur a dessiné tel sentier : sur une boucle réelle, l'espacement des nœuds OSM
va de 0,7 m à 208 m. Vient ensuite un filtre gaussien de 25 m d'écart-type, puis le
comptage des montées avec un seuil de 1,5 m et un suivi des points de retournement.

Le suivi des retournements n'est pas un détail : ancrer la référence sur le dernier
point mesuré plutôt que sur le sommet atteint rabotait 10 % du D+, et cassait
l'identité qu'une boucle fermée doit vérifier, D+ = D-.

Les deux bouts de la dernière montée sont versés à la fermeture, et pas seulement
celui qui pointe dans le sens de la marche. Sans ca le résidu resté sous le seuil
disparaissait d'un seul coté : `[10, 8, 11, 10]` rendait 3 m de D+ contre 2 m de D-.
L'écart était borné par le seuil, donc trop petit pour se voir sur un total, et
suffisant pour casser l'identité. `D+ - D-` vaut maintenant exactement la différence
d'altitude entre le premier point et le dernier, à 1e-9 m près.

**La durée est celle de Tobler, pas la vôtre.** La vitesse est lue sur la pente tous
les 25 m, `V = 6 exp(-3,5 |S + 0,05|)` km/h, ajustée par Waldo Tobler sur les relevés
de terrain d'Eduard Imhof. Ca donne 5,0 km/h à plat, et non les 4 km/h d'un Naismith.
Aucune pause n'est comptée, Tobler a mesuré des gens qui marchaient. Le curseur
d'allure multiplie l'estimation. `core.pace.calibrate` sait déduire ce facteur de
sorties réelles à partir de trois, mais rien ne stocke encore l'historique.

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

## D'où viennent les données

OpenStreetMap (ODbL) pour le réseau, la forêt et le fond de carte. EU-DEM via
OpenTopoData pour l'altimétrie.
