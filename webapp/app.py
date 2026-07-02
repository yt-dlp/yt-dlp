"""AniStream — serveur de streaming local propulsé par yt-dlp.

Lancement depuis la racine du dépôt :

    python3 webapp/app.py

Variables d'environnement :
    ANISTREAM_MEDIA   dossier de la bibliothèque (défaut : webapp/media)
    ANISTREAM_HOST    interface d'écoute (défaut : 127.0.0.1)
    ANISTREAM_PORT    port (défaut : 8000)
    ANISTREAM_LANGS   langues de sous-titres, séparées par des virgules (défaut : fr,en)
"""

import mimetypes
import os
import re
import shutil
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path
from urllib.parse import urlencode, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yt_dlp  # noqa: E402  (importé depuis les sources du dépôt)

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.responses import FileResponse, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

WEBAPP_DIR = Path(__file__).resolve().parent
MEDIA_DIR = Path(os.environ.get('ANISTREAM_MEDIA', WEBAPP_DIR / 'media')).resolve()
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

SUB_LANGS = [x.strip() for x in os.environ.get('ANISTREAM_LANGS', 'fr,en').split(',') if x.strip()]
HAS_FFMPEG = bool(shutil.which('ffmpeg'))

VIDEO_EXTS = {'.mp4', '.mkv', '.webm', '.m4v', '.mov'}
THUMB_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
STREAM_CHUNK = 1024 * 1024

app = FastAPI(title='AniStream')


# ---------------------------------------------------------------------------
# Gestionnaire de téléchargements
# ---------------------------------------------------------------------------

jobs = {}
jobs_lock = threading.Lock()
download_slots = threading.Semaphore(2)


class DownloadRequest(BaseModel):
    url: str
    series: str
    season: int | None = None


def sanitize_name(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip() or 'Sans titre'


def progress_hook(job_id):
    def hook(d):
        with jobs_lock:
            job = jobs.get(job_id)
            if job is None:
                return
            info = d.get('info_dict') or {}
            if info.get('title'):
                job['title'] = info['title']
            if d['status'] == 'downloading':
                job['status'] = 'downloading'
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                if total:
                    job['progress'] = round(d.get('downloaded_bytes', 0) / total * 100, 1)
                job['speed'] = d.get('speed')
                job['eta'] = d.get('eta')
            elif d['status'] == 'finished':
                job['status'] = 'processing'
                job['progress'] = 100.0
                job['speed'] = None
                job['eta'] = None
    return hook


def build_ydl_opts(req: DownloadRequest, job_id):
    dest = MEDIA_DIR / sanitize_name(req.series)
    if req.season is not None:
        dest = dest / f'Saison {req.season:02d}'
    opts = {
        'outtmpl': str(dest / '%(playlist_index&{} - |)s%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook(job_id)],
        'ignoreerrors': 'only_download',
        'noprogress': True,
        'writethumbnail': True,
        'writesubtitles': True,
        'subtitleslangs': SUB_LANGS,
        'restrictfilenames': False,
        'windowsfilenames': True,
    }
    if HAS_FFMPEG:
        # mp4/h264 en priorité pour la lecture native dans le navigateur
        opts['format'] = 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b'
        opts['merge_output_format'] = 'mp4'
        opts['postprocessors'] = [
            {'key': 'FFmpegSubtitlesConvertor', 'format': 'vtt'},
            {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
        ]
    else:
        # sans ffmpeg : pas de fusion possible, on prend le meilleur fichier unique
        opts['format'] = 'b[ext=mp4]/b'
    return opts


def run_download(job_id, req: DownloadRequest):
    with download_slots:
        with jobs_lock:
            jobs[job_id]['status'] = 'downloading'
        try:
            with yt_dlp.YoutubeDL(build_ydl_opts(req, job_id)) as ydl:
                retcode = ydl.download([req.url])
            with jobs_lock:
                job = jobs[job_id]
                if retcode == 0:
                    job['status'] = 'done'
                    job['progress'] = 100.0
                else:
                    job['status'] = 'error'
                    job['error'] = 'Certains éléments ont échoué (voir les logs du serveur)'
        except Exception as e:
            with jobs_lock:
                jobs[job_id]['status'] = 'error'
                jobs[job_id]['error'] = str(e)


@app.post('/api/download')
def start_download(req: DownloadRequest):
    if not req.url.strip():
        raise HTTPException(400, 'URL manquante')
    if not req.series.strip():
        raise HTTPException(400, 'Nom de série manquant')
    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {
            'id': job_id,
            'url': req.url,
            'series': sanitize_name(req.series),
            'season': req.season,
            'title': None,
            'status': 'queued',
            'progress': 0.0,
            'speed': None,
            'eta': None,
            'error': None,
        }
    threading.Thread(target=run_download, args=(job_id, req), daemon=True).start()
    return jobs[job_id]


@app.get('/api/downloads')
def list_downloads():
    with jobs_lock:
        return sorted(jobs.values(), key=lambda j: j['id'])


@app.post('/api/downloads/clear')
def clear_downloads():
    with jobs_lock:
        for jid in [j['id'] for j in jobs.values() if j['status'] in ('done', 'error')]:
            del jobs[jid]
    return {'ok': True}


# ---------------------------------------------------------------------------
# Recherche multi-sites
# ---------------------------------------------------------------------------

# Extracteurs de recherche yt-dlp interrogés en parallèle. Google Vidéo et
# Yahoo sont des méta-moteurs : ils remontent des vidéos hébergées sur de
# nombreux sites, que yt-dlp sait ensuite télécharger.
SEARCH_SOURCES = [
    ('ytsearch', 'YouTube'),
    ('gvsearch', 'Google Vidéo'),
    ('yvsearch', 'Yahoo Vidéo'),
    ('bilisearch', 'BiliBili'),
    ('nicosearch', 'NicoNico'),
]
SEARCH_TIMEOUT = 30


def flat_extract(query):
    opts = {
        'quiet': True,
        'noprogress': True,
        'extract_flat': True,
        'skip_download': True,
        'ignoreerrors': True,
        'socket_timeout': 15,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(query, download=False)


def entry_to_result(entry, site):
    url = entry.get('url') or entry.get('webpage_url')
    if not url or not url.startswith('http'):
        return None
    return {
        'site': site,
        'source': urlparse(url).netloc.removeprefix('www.') or site,
        'title': entry.get('title') or url,
        'url': url,
        'duration': entry.get('duration'),
        'uploader': entry.get('uploader') or entry.get('channel'),
        'is_playlist': entry.get('_type') == 'playlist' or 'list=' in url,
    }


def search_source(key, label, q, count):
    info = flat_extract(f'{key}{count}:{q}') or {}
    results = []
    for entry in info.get('entries') or []:
        if entry and (r := entry_to_result(entry, label)):
            results.append(r)
    return results


def search_youtube_playlists(q, count):
    # page de résultats YouTube filtrée sur les playlists (sp=EgIQAw==)
    url = 'https://www.youtube.com/results?' + urlencode({'search_query': q, 'sp': 'EgIQAw=='})
    info = flat_extract(url) or {}
    results = []
    for entry in (info.get('entries') or [])[:count]:
        if entry and (r := entry_to_result(entry, 'YouTube')):
            r['is_playlist'] = True
            results.append(r)
    return results


@app.get('/api/search')
def search(q: str, mode: str = 'videos', count: int = 8):
    q = q.strip()
    if not q:
        raise HTTPException(400, 'Recherche vide')
    count = max(1, min(count, 20))

    executor = ThreadPoolExecutor(max_workers=len(SEARCH_SOURCES))
    try:
        if mode == 'playlists':
            futures = {executor.submit(search_youtube_playlists, q, count): 'YouTube'}
        else:
            futures = {
                executor.submit(search_source, key, label, q, count): label
                for key, label in SEARCH_SOURCES
            }
        done, not_done = wait(futures, timeout=SEARCH_TIMEOUT)
        results, failed = [], [futures[f] for f in not_done]
        for fut in done:
            try:
                results.extend(fut.result())
            except Exception:
                failed.append(futures[fut])
        return {'query': q, 'results': results, 'failed_sources': sorted(failed)}
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


# ---------------------------------------------------------------------------
# Bibliothèque
# ---------------------------------------------------------------------------

def find_siblings(video: Path):
    """Sous-titres .vtt et miniature associés à un fichier vidéo."""
    subs, thumb = [], None
    prefix = video.stem + '.'
    for f in video.parent.iterdir():
        if not f.name.startswith(prefix) or f == video:
            continue
        if f.suffix == '.vtt':
            middle = f.name[len(prefix):-len('.vtt')]
            subs.append({'lang': middle or 'und', 'path': str(f.relative_to(MEDIA_DIR))})
        elif f.suffix.lower() in THUMB_EXTS and thumb is None:
            thumb = str(f.relative_to(MEDIA_DIR))
    return subs, thumb


@app.get('/api/library')
def library():
    series_list = []
    for sdir in sorted(MEDIA_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not sdir.is_dir():
            continue
        episodes = []
        for f in sorted(sdir.rglob('*'), key=lambda p: str(p).lower()):
            if not (f.is_file() and f.suffix.lower() in VIDEO_EXTS):
                continue
            subs, thumb = find_siblings(f)
            episodes.append({
                'title': f.stem,
                'path': str(f.relative_to(MEDIA_DIR)),
                'season': f.parent.name if f.parent != sdir else None,
                'subs': subs,
                'thumb': thumb,
            })
        if episodes:
            series_list.append({
                'name': sdir.name,
                'cover': next((e['thumb'] for e in episodes if e['thumb']), None),
                'episodes': episodes,
            })
    return series_list


def safe_media_path(rel_path):
    target = (MEDIA_DIR / rel_path).resolve()
    if not target.is_relative_to(MEDIA_DIR) or not target.is_file():
        raise HTTPException(404, 'Fichier introuvable')
    return target


@app.delete('/api/media/{rel_path:path}')
def delete_episode(rel_path: str):
    video = safe_media_path(rel_path)
    prefix = video.stem + '.'
    for f in list(video.parent.iterdir()):
        if f == video or f.name.startswith(prefix):
            f.unlink()
    # supprime les dossiers devenus vides (saison puis série)
    parent = video.parent
    while parent != MEDIA_DIR and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent
    return {'ok': True}


# ---------------------------------------------------------------------------
# Streaming avec support des requêtes Range
# ---------------------------------------------------------------------------

@app.get('/api/stream/{rel_path:path}')
def stream(rel_path: str, request: Request):
    file = safe_media_path(rel_path)
    size = file.stat().st_size
    content_type = {
        '.mkv': 'video/x-matroska',
        '.vtt': 'text/vtt',
    }.get(file.suffix.lower()) or mimetypes.guess_type(file.name)[0] or 'application/octet-stream'

    start, end, status = 0, size - 1, 200
    m = re.match(r'bytes=(\d*)-(\d*)$', request.headers.get('range', ''))
    if m and (m.group(1) or m.group(2)):
        if m.group(1):
            start = int(m.group(1))
            if m.group(2):
                end = min(int(m.group(2)), size - 1)
        else:  # suffixe : bytes=-N (les N derniers octets)
            start = max(size - int(m.group(2)), 0)
        if start >= size:
            raise HTTPException(416, 'Range invalide')
        status = 206

    def iter_file():
        with open(file, 'rb') as fh:
            fh.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = fh.read(min(STREAM_CHUNK, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {'Accept-Ranges': 'bytes', 'Content-Length': str(end - start + 1)}
    if status == 206:
        headers['Content-Range'] = f'bytes {start}-{end}/{size}'
    return StreamingResponse(iter_file(), status_code=status, headers=headers, media_type=content_type)


# ---------------------------------------------------------------------------
# Frontend statique
# ---------------------------------------------------------------------------

@app.get('/')
def index():
    return FileResponse(WEBAPP_DIR / 'static' / 'index.html')


app.mount('/static', StaticFiles(directory=WEBAPP_DIR / 'static'), name='static')


if __name__ == '__main__':
    import uvicorn

    host = os.environ.get('ANISTREAM_HOST', '127.0.0.1')
    port = int(os.environ.get('ANISTREAM_PORT', '8000'))
    print(f'AniStream : http://{host}:{port}  (bibliothèque : {MEDIA_DIR})')
    if not HAS_FFMPEG:
        print('ATTENTION : ffmpeg introuvable — qualité limitée, pas de conversion de sous-titres.')
    uvicorn.run(app, host=host, port=port)
