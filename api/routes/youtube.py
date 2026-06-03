"""YouTube provider routes."""

from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query

from api import service

router = APIRouter()


def _is_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().lstrip('www.')
        if netloc == 'youtube.com' or netloc.endswith('.youtube.com'):
            return True
        if netloc == 'youtu.be':
            return True
        return False
    except Exception:
        return False


@router.get('/channel/videos')
def channel_videos(
    url: str = Query(..., description='YouTube channel or playlist URL (e.g. .../channel/UC.../recent)'),
    limit: int | None = Query(None, ge=1, description='Max number of videos to return (caps extraction; unbounded if omitted)'),
):
    """Return flat list of videos for a channel/playlist (same shape as yt-dlp --flat-playlist -j)."""
    if not _is_youtube_url(url):
        raise HTTPException(status_code=400, detail='URL must be a YouTube channel or playlist URL')
    try:
        result = service.extract(url, 'playlist_flat', limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=404, detail='No data extracted')
    return result


@router.get('/video')
def video(url: str = Query(..., description='YouTube video URL (e.g. .../watch?v=ID)')):
    """Return full video metadata, including game engagement panel when present."""
    if not _is_youtube_url(url):
        raise HTTPException(status_code=400, detail='URL must be a YouTube video URL')
    try:
        result = service.extract(url, 'video')
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=404, detail='No data extracted')
    return result
