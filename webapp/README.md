# AniStream — streaming local propulsé par yt-dlp

Petit serveur web personnel pour se constituer une bibliothèque d'animés/séries en local
et la regarder dans le navigateur, façon Netflix. Le téléchargement s'appuie sur les
sources yt-dlp de ce dépôt : tous les sites supportés par yt-dlp (~1800) fonctionnent.

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
brew install ffmpeg            # macOS
```

## Lancement

Depuis la racine du dépôt :

```bash
python3 webapp/app.py
```

Puis ouvrir <http://127.0.0.1:8000>.

## Utilisation

1. Onglet **Téléchargements** : coller l'URL d'un épisode (ou d'une playlist/saison
   entière), indiquer le nom de la série et éventuellement le numéro de saison.
2. La progression s'affiche en direct (2 téléchargements en parallèle maximum).
3. Onglet **Bibliothèque** : les séries apparaissent en grille ; cliquer pour voir les
   épisodes par saison, puis lire dans le lecteur intégré (sous-titres, reprise de
   lecture là où on s'était arrêté, enchaînement automatique de l'épisode suivant,
   marquage « vu »).

Les fichiers sont rangés dans `webapp/media/<Série>/<Saison XX>/…` — le dossier peut
aussi être alimenté à la main avec des vidéos existantes, elles apparaîtront dans la
bibliothèque au prochain rechargement.

## Configuration (variables d'environnement)

| Variable          | Défaut         | Rôle                                    |
|-------------------|----------------|-----------------------------------------|
| `ANISTREAM_MEDIA` | `webapp/media` | Dossier de la bibliothèque              |
| `ANISTREAM_HOST`  | `127.0.0.1`    | Interface d'écoute (`0.0.0.0` pour le réseau local) |
| `ANISTREAM_PORT`  | `8000`         | Port                                    |
| `ANISTREAM_LANGS` | `fr,en`        | Langues de sous-titres à récupérer      |

Exemple pour y accéder depuis une TV ou un téléphone sur le réseau local :

```bash
ANISTREAM_HOST=0.0.0.0 ANISTREAM_MEDIA=~/Videos/Animes python3 webapp/app.py
```

> Le serveur n'a pas d'authentification : ne l'exposez pas au-delà de votre réseau
> local de confiance.

## Notes techniques

- Backend FastAPI dans `app.py` : file de téléchargements yt-dlp avec hooks de
  progression, scan de la bibliothèque, streaming HTTP avec support des requêtes
  `Range` (indispensable pour se déplacer dans la vidéo).
- Frontend sans dépendance dans `static/` (HTML/CSS/JS pur, routeur par hash).
- Les vidéos sont téléchargées en mp4/h264 en priorité pour la lecture native dans le
  navigateur ; le mkv est servi mais sa lecture dépend des codecs du navigateur.
