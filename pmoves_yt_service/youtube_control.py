"""Minimal YouTube Data API helpers for owned-channel control actions."""

from __future__ import annotations

from typing import Any

import requests


TOKEN_URL = 'https://oauth2.googleapis.com/token'
YOUTUBE_API_BASE = 'https://www.googleapis.com/youtube/v3'


class YouTubeControlError(RuntimeError):
    """Raised when the YouTube Data API control plane responds with an error."""


def _check_response(response: requests.Response, action: str) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise YouTubeControlError(f'{action} returned non-JSON response') from exc
    if response.status_code >= 400 or 'error' in data:
        raise YouTubeControlError(f'{action} failed: {data}')
    return data


def refresh_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        },
        timeout=30,
    )
    data = _check_response(response, 'refresh_access_token')
    access_token = data.get('access_token')
    if not isinstance(access_token, str) or not access_token:
        raise YouTubeControlError('refresh_access_token returned no access_token')
    return access_token


def insert_playlist_item(
    *,
    access_token: str,
    playlist_id: str,
    video_id: str,
    position: int | None = None,
) -> dict[str, Any]:
    snippet: dict[str, Any] = {
        'playlistId': playlist_id,
        'resourceId': {
            'kind': 'youtube#video',
            'videoId': video_id,
        },
    }
    if position is not None:
        snippet['position'] = position
    response = requests.post(
        f'{YOUTUBE_API_BASE}/playlistItems',
        params={'part': 'snippet'},
        headers={'Authorization': f'Bearer {access_token}'},
        json={'snippet': snippet},
        timeout=30,
    )
    return _check_response(response, 'insert_playlist_item')


def create_playlist(
    *,
    access_token: str,
    title: str,
    description: str | None = None,
    privacy_status: str = 'private',
    default_language: str | None = None,
) -> dict[str, Any]:
    snippet: dict[str, Any] = {
        'title': title,
    }
    if description:
        snippet['description'] = description
    if default_language:
        snippet['defaultLanguage'] = default_language
    response = requests.post(
        f'{YOUTUBE_API_BASE}/playlists',
        params={'part': 'snippet,status'},
        headers={'Authorization': f'Bearer {access_token}'},
        json={
            'snippet': snippet,
            'status': {'privacyStatus': privacy_status},
        },
        timeout=30,
    )
    return _check_response(response, 'create_playlist')


def update_playlist(
    *,
    access_token: str,
    playlist_id: str,
    title: str | None = None,
    description: str | None = None,
    privacy_status: str | None = None,
    default_language: str | None = None,
) -> dict[str, Any]:
    snippet: dict[str, Any] = {}
    status: dict[str, Any] = {}
    if title is not None:
        snippet['title'] = title
    if description is not None:
        snippet['description'] = description
    if default_language is not None:
        snippet['defaultLanguage'] = default_language
    if privacy_status is not None:
        status['privacyStatus'] = privacy_status
    if not snippet and not status:
        raise YouTubeControlError('update_playlist requires at least one mutable field')
    payload: dict[str, Any] = {'id': playlist_id}
    parts: list[str] = []
    if snippet:
        payload['snippet'] = snippet
        parts.append('snippet')
    if status:
        payload['status'] = status
        parts.append('status')
    response = requests.put(
        f'{YOUTUBE_API_BASE}/playlists',
        params={'part': ','.join(parts)},
        headers={'Authorization': f'Bearer {access_token}'},
        json=payload,
        timeout=30,
    )
    return _check_response(response, 'update_playlist')


def delete_playlist(
    *,
    access_token: str,
    playlist_id: str,
) -> dict[str, Any]:
    response = requests.delete(
        f'{YOUTUBE_API_BASE}/playlists',
        params={'id': playlist_id},
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=30,
    )
    if response.status_code >= 400:
        _check_response(response, 'delete_playlist')
    return {'id': playlist_id, 'deleted': True}


def delete_playlist_item(
    *,
    access_token: str,
    playlist_item_id: str,
) -> dict[str, Any]:
    response = requests.delete(
        f'{YOUTUBE_API_BASE}/playlistItems',
        params={'id': playlist_item_id},
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=30,
    )
    if response.status_code >= 400:
        _check_response(response, 'delete_playlist_item')
    return {'id': playlist_item_id, 'deleted': True}


def update_playlist_item_position(
    *,
    access_token: str,
    playlist_item_id: str,
    playlist_id: str,
    video_id: str,
    position: int,
) -> dict[str, Any]:
    response = requests.put(
        f'{YOUTUBE_API_BASE}/playlistItems',
        params={'part': 'snippet'},
        headers={'Authorization': f'Bearer {access_token}'},
        json={
            'id': playlist_item_id,
            'snippet': {
                'playlistId': playlist_id,
                'position': position,
                'resourceId': {
                    'kind': 'youtube#video',
                    'videoId': video_id,
                },
            },
        },
        timeout=30,
    )
    return _check_response(response, 'update_playlist_item_position')


def insert_comment(
    *,
    access_token: str,
    video_id: str,
    text: str,
    parent_comment_id: str | None = None,
) -> dict[str, Any]:
    if parent_comment_id:
        endpoint = 'comments'
        payload = {
            'snippet': {
                'parentId': parent_comment_id,
                'textOriginal': text,
            },
        }
    else:
        endpoint = 'commentThreads'
        payload = {
            'snippet': {
                'videoId': video_id,
                'topLevelComment': {
                    'snippet': {
                        'textOriginal': text,
                    },
                },
            },
        }
    response = requests.post(
        f'{YOUTUBE_API_BASE}/{endpoint}',
        params={'part': 'snippet'},
        headers={'Authorization': f'Bearer {access_token}'},
        json=payload,
        timeout=30,
    )
    return _check_response(response, 'insert_comment')


def delete_comment(
    *,
    access_token: str,
    comment_id: str,
) -> dict[str, Any]:
    response = requests.delete(
        f'{YOUTUBE_API_BASE}/comments',
        params={'id': comment_id},
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=30,
    )
    if response.status_code >= 400:
        _check_response(response, 'delete_comment')
    return {'id': comment_id, 'deleted': True}
