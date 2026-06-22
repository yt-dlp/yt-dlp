"""TikTok provider routes — replaces TikAPI using yt-dlp's TikTok extractor.

Maps to TikAPI semantics where possible:
- get_user(username) -> GET /tiktok/user?username=
- get_posts(sec_uid, count) -> GET /tiktok/posts?username= or ?sec_uid=
- hashtag posts by name -> GET /tiktok/hashtag/posts?name= (see TikTokTagIE)
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from yt_dlp import YoutubeDL
from yt_dlp.extractor.tiktok import TikTokUserIE, TikTokBaseIE

from api import service

router = APIRouter()


def _get_hashtag_posts_from_web(tag: str) -> list[dict[str, Any]] | None:
    """Fetch TikTok tag page and return itemList from __UNIVERSAL_DATA_FOR_REHYDRATION__ if present. Tag pages do not embed itemList (only app-context, biz-context, etc.), so this usually returns None and we fall back to mobile API."""
    opts = {
        'skip_download': True,
        'quiet': True,
        'logger': service.YTDLP_LOGGER,
        'ignore_no_formats_error': True,
    }
    with YoutubeDL(opts) as ydl:
        ie = TikTokUserIE(ydl)
        url = f'https://www.tiktok.com/tag/{tag}'
        webpage = ie._download_webpage(
            url, tag,
            note='Downloading tag webpage',
            errnote='Unable to download tag webpage',
            fatal=False,
            impersonate=True,
        )
    if not webpage:
        return None
    universal = ie._get_universal_data(webpage, tag)
    for scope_value in (universal or {}).values():
        if isinstance(scope_value, dict) and 'itemList' in scope_value:
            raw_list = scope_value.get('itemList') or []
            return [_web_item_to_tikapi_post(i) for i in raw_list if isinstance(i, dict)]
    return None


def _get_user_info_by_username(username: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Fetch TikTok user page; return (userInfo dict or None, webapp.user-detail dict for status)."""
    opts = {
        'skip_download': True,
        'quiet': True,
        'logger': service.YTDLP_LOGGER,
        'ignore_no_formats_error': True,
    }
    with YoutubeDL(opts) as ydl:
        ie = TikTokUserIE(ydl)
        url = ie._UPLOADER_URL_FORMAT % username
        webpage = ie._download_webpage(
            url, username,
            note='Downloading user webpage',
            errnote='Unable to download user webpage',
            fatal=False,
            impersonate=True,
        )
    if not webpage:
        return None, {}
    universal = ie._get_universal_data(webpage, username)
    detail = universal.get('webapp.user-detail') or {}
    user_info = detail.get('userInfo')
    return user_info, detail


def _user_info_to_tikapi_shape(user_info: dict[str, Any]) -> dict[str, Any]:
    """Shape TikTok userInfo to TikAPI TikUserProfileResponse style."""
    user = user_info.get('user') or {}
    stats = (user_info.get('statsV2') or user_info.get('stats')) or {}
    return {
        'userInfo': {
            'statsV2': {
                'followerCount': _str_or_int(stats.get('followerCount')),
                'heartCount': _str_or_int(stats.get('heartCount')),
            },
            'user': {
                'uniqueId': user.get('uniqueId') or '',
                'nickname': user.get('nickname') or '',
                'signature': user.get('signature') or '',
                'avatarLarger': user.get('avatarLarger') or '',
                'secUid': user.get('secUid') or '',
            },
        },
    }


def _str_or_int(v: Any) -> int | str:
    if v is None:
        return 0
    if isinstance(v, str) and v.isdigit():
        return int(v)
    if isinstance(v, int):
        return v
    return v


def _hashtags_from_desc(desc: str) -> list[dict[str, Any]]:
    if not desc:
        return []
    return [{'hashtagName': m[1]} for m in re.finditer(r'#(\w+)', desc)]


def _web_item_to_tikapi_post(item: dict[str, Any]) -> dict[str, Any]:
    """Map TikTok web itemList entry (id, desc, createTime, stats, video, author) to TikAPI TikPost shape."""
    stats = item.get('stats') or item.get('statsV2') or {}
    video = item.get('video') or {}
    author = item.get('author') or item.get('authorInfo') or {}
    desc = item.get('desc') or ''
    cover = video.get('cover')
    if isinstance(cover, dict):
        cover = (cover.get('urlList') or cover.get('url_list') or [None])[0]
    if not isinstance(cover, str):
        cover = ''
    return {
        'id': str(item.get('id') or ''),
        'desc': desc,
        'createTime': item.get('createTime') or 0,
        'statsV2': {
            'playCount': _str_or_int(stats.get('playCount')),
            'diggCount': _str_or_int(stats.get('diggCount')),
            'commentCount': _str_or_int(stats.get('commentCount')),
        },
        'video': {
            'cover': cover,
            'duration': video.get('duration') or 0,
        },
        'textExtra': _hashtags_from_desc(desc),
        'author': {
            'uniqueId': author.get('uniqueId') or '',
            'nickname': author.get('nickname') or '',
            'secUid': author.get('secUid') or '',
        },
    }


def _entry_to_tikapi_post(entry: dict[str, Any]) -> dict[str, Any]:
    """Map yt-dlp playlist entry (from _parse_aweme_video_web flat) to TikAPI TikPost shape."""
    thumb = (entry.get('thumbnails') or [{}])[0]
    thumb_url = thumb.get('url') if isinstance(thumb, dict) else None
    desc = entry.get('title') or entry.get('description') or ''
    return {
        'id': entry.get('id') or '',
        'desc': desc,
        'createTime': entry.get('timestamp') or 0,
        'statsV2': {
            'playCount': entry.get('view_count'),
            'diggCount': entry.get('like_count'),
            'commentCount': entry.get('comment_count'),
        },
        'video': {
            'cover': thumb_url or '',
            'duration': entry.get('duration') or 0,
        },
        'textExtra': _hashtags_from_desc(desc),
        'author': {
            'uniqueId': entry.get('uploader') or '',
            'nickname': entry.get('channel') or entry.get('uploader') or '',
            'secUid': entry.get('channel_id') or '',
        },
    }


@router.get('/user')
def user_profile(username: str = Query(..., description='TikTok username (e.g. khaby.lame)')):
    """Return user profile in TikAPI TikUserProfileResponse shape (userInfo with user + statsV2)."""
    if not username.strip():
        raise HTTPException(status_code=400, detail='username is required')
    user_info, detail = _get_user_info_by_username(username.strip())
    if not user_info:
        status_code = detail.get('statusCode')
        status_msg = detail.get('statusMsg') or ''
        if status_code == 10222:
            raise HTTPException(status_code=403, detail='This user\'s account is private')
        msg = status_msg.strip() or 'User not found or page unavailable'
        raise HTTPException(status_code=404, detail=msg)
    return _user_info_to_tikapi_shape(user_info)


@router.get('/user/posts')
def user_posts(
    username: str | None = Query(None, description='TikTok username'),
    sec_uid: str | None = Query(None, description='TikTok sec_uid (e.g. MS4wLjABAAAA...)'),
    count: int = Query(30, ge=1, le=100, description='Max number of posts to return'),
):
    """Return user posts in TikAPI TikPostsResponse shape (itemList). Uses yt-dlp playlist extraction."""
    if not username and not sec_uid:
        raise HTTPException(status_code=400, detail='Provide either username or sec_uid')
    if username and sec_uid:
        raise HTTPException(status_code=400, detail='Provide only one of username or sec_uid')
    url = f'https://www.tiktok.com/@{username}' if username else f'tiktokuser:{sec_uid}'
    try:
        result, _ = service.extract(url, 'playlist_flat', limit=count)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if not result:
        raise HTTPException(status_code=404, detail='No data extracted')
    entries = result.get('entries') or []
    items = [_entry_to_tikapi_post(e) for e in entries if isinstance(e, dict)][:count]
    return {'itemList': items}


@router.get('/hashtag/posts')
def hashtag_posts(
    name: str = Query(..., description='Hashtag name (e.g. comedy)'),
    count: int = Query(30, ge=1, le=100, description='Max number of posts'),
):
    """Return posts for a hashtag by name. Tries tag page embedded data first (no mobile API); falls back to yt-dlp TikTokTagIE."""
    tag = name.strip().lstrip('#')
    web_items = _get_hashtag_posts_from_web(tag)
    if web_items is not None:
        return {'itemList': web_items[:count]}
    url = f'https://www.tiktok.com/tag/{tag}'
    try:
        result, _ = service.extract(url, 'playlist_flat', limit=count)
    except Exception as e:
        msg = str(e)
        if 'No working app info' in msg or 'marked as broken' in msg:
            raise HTTPException(
                status_code=503,
                detail='Hashtag posts require the TikTok mobile API. Set TIKTOK_DEVICE_ID in the environment to enable (see api/README.md). User profile and user posts work without it.',
            ) from e
        if 'Failed to parse JSON' in msg or 'Expecting value' in msg or 'empty response' in msg or 'signature may be required' in msg:
            raise HTTPException(
                status_code=503,
                detail='TikTok mobile API returned an empty or invalid response (signature required). Hashtag posts are not supported without valid X-Gorgon/signature. See api/README.md.',
            ) from e
        raise HTTPException(status_code=502, detail=msg) from e
    if not result:
        raise HTTPException(status_code=404, detail='No data extracted')
    entries = result.get('entries') or []
    items = [_entry_to_tikapi_post(e) for e in entries if isinstance(e, dict)][:count]
    return {'itemList': items}
