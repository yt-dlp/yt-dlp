# AniStream — streaming local propulsé par yt-dlp

Serveur web personnel, pensé pour tourner sur ton PC, qui permet de se constituer une
bibliothèque d'animés/séries en local et de la regarder dans le navigateur, façon
Netflix. Le téléchargement s'appuie sur les sources yt-dlp de ce dépôt : tous les sites
supportés par yt-dlp (~1800) fonctionnent.

> **Limites** : les plateformes protégées par DRM (Crunchyroll, Netflix, ADN…) ne sont
> pas prises en charge — yt-dlp ne contourne pas les DRM. À utiliser uniquement avec des
> contenus auxquels vous avez légalement accès.

## Installation

```bash
pip install -r webapp/requirements.txt
```

`ffmpeg` est fortement recommandé (fusion vidéo+audio en mp4, conversion des sous-titres
en VTT pour le lecteur, miniatures) :

```bash
sudo apt install ffmpeg        # Debian/Ubuntu
winget install ffmpeg          # Windows
brew install ffmpeg            # macOS
```

## Lancement

Depuis la racine du dépôt :

```bash
python3 webapp/app.py
```

Puis ouvrir <http://127.0.0.1:8000> dans ton navigateur. Tout reste sur ta machine :
les fichiers sont enregistrés dans `webapp/media/` (modifiable, voir Configuration).

## Utilisation

### 1. Rechercher un animé ou une série (onglet Recherche)

Tape un titre (par exemple `one piece vostfr`) et AniStream interroge en parallèle
plusieurs moteurs de recherche vidéo :

| Moteur       | Couverture                                                        |
|--------------|-------------------------------------------------------------------|
| YouTube      | vidéos et, en mode « Playlists », saisons/playlists entières      |
| Google Vidéo | méta-moteur : trouve des vidéos hébergées sur de très nombreux sites |
| Yahoo Vidéo  | méta-moteur, idem                                                 |
| BiliBili     | beaucoup d'animés asiatiques                                      |
| NicoNico     | idem                                                              |

Les résultats indiquent automatiquement **sur quel site** la vidéo est disponible
(domaine affiché sous le titre). Un clic sur **Télécharger** pré-remplit le nom de la
série (dossier de la bibliothèque) et lance le téléchargement via yt-dlp depuis le site
trouvé.

Deux modes :

- **Vidéos / épisodes** : cherche des vidéos individuelles sur tous les moteurs.
- **Playlists YouTube** : cherche des playlists (pratique pour récupérer une saison
  complète d'un coup — chaque épisode est numéroté automatiquement).

> Note d'honnêteté : il n'existe pas de recherche universelle sur les ~1800 sites —
> seuls les sites exposant un moteur de recherche sont interrogeables directement. Les
> méta-moteurs (Google/Yahoo Vidéo) comblent l'essentiel du reste. Pour un site précis
> non couvert, copie simplement l'URL de l'épisode ou de la playlist dans l'onglet
> Téléchargements : yt-dlp saura presque toujours la télécharger.

### 2. Télécharger par URL (onglet Téléchargements)

Coller n'importe quelle URL supportée par yt-dlp :

- une **vidéo individuelle** (YouTube ou autre) ;
- une **playlist YouTube** ou une page de saison : tous les épisodes sont téléchargés
  et numérotés (`01 - …`, `02 - …`) ;
- indiquer le nom de la série et éventuellement le numéro de saison pour le rangement.

La progression s'affiche en direct (2 téléchargements en parallèle maximum).

### 3. Regarder (onglet Bibliothèque)

Les séries apparaissent en grille ; clique pour voir les épisodes par saison, puis lire
dans le lecteur intégré : sous-titres, reprise de lecture là où tu t'étais arrêté,
enchaînement automatique de l'épisode suivant, marquage « vu », suppression d'épisode.

Les fichiers sont rangés dans `webapp/media/<Série>/<Saison XX>/…` — le dossier peut
aussi être alimenté à la main avec des vidéos existantes, elles apparaîtront dans la
bibliothèque au prochain rechargement.

## Configuration (variables d'environnement)

| Variable          | Défaut         | Rôle                                    |
|-------------------|----------------|-----------------------------------------|
| `ANISTREAM_MEDIA` | `webapp/media` | Dossier de la bibliothèque              |
| `ANISTREAM_HOST`  | `127.0.0.1`    | Interface d'écoute                      |
| `ANISTREAM_PORT`  | `8000`         | Port                                    |
| `ANISTREAM_LANGS` | `fr,en`        | Langues de sous-titres à récupérer      |

Exemple pour stocker la bibliothèque dans tes Vidéos :

```bash
ANISTREAM_MEDIA=~/Videos/Animes python3 webapp/app.py
```

> Le serveur n'a pas d'authentification : garde l'écoute sur `127.0.0.1` (défaut),
> c'est-à-dire accessible uniquement depuis ton PC.

## Notes techniques

- Backend FastAPI dans `app.py` :
  - recherche : extracteurs `SearchInfoExtractor` de yt-dlp interrogés en parallèle
    (extraction « flat », 30 s maximum) ; le mode playlists utilise la page de
    résultats YouTube filtrée sur les playlists ;
  - téléchargements : file yt-dlp avec hooks de progression ;
  - bibliothèque : scan du dossier média (séries → saisons → épisodes, sous-titres et
    miniatures associés) ;
  - streaming HTTP avec support des requêtes `Range` (indispensable pour se déplacer
    dans la vidéo).
- Frontend sans dépendance dans `static/` (HTML/CSS/JS pur, routeur par hash).
- Les vidéos sont téléchargées en mp4/h264 en priorité pour la lecture native dans le
  navigateur ; le mkv est servi mais sa lecture dépend des codecs du navigateur.
