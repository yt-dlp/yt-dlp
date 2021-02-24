# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    try_get,
)


class ImgGamingBaseIE(InfoExtractor):
    _API_BASE = 'https://dce-frontoffice.imggaming.com/api/v2/'
    _API_KEY = '857a1e5d-e35e-4fdf-805b-a87b6f8364bf'
    _HEADERS = None
    _MANIFEST_HEADERS = {'Accept-Encoding': 'identity'}
    _REALM = None
    _VALID_URL_TEMPL = r'https?://(?P<domain>%s)/(?P<type>live|playlist|video)/(?P<id>\d+)(?:\?.*?\bplaylistId=(?P<playlist_id>\d+))?'

    def _real_initialize(self):
        self._HEADERS = {
            'Realm': 'dce.' + self._REALM,
            'x-api-key': self._API_KEY,
        }

        email, password = self._get_login_info()
        if email is None:
            self.raise_login_required()

        p_headers = self._HEADERS.copy()
        p_headers['Content-Type'] = 'application/json'
        self._HEADERS['Authorization'] = 'Bearer ' + self._download_json(
            self._API_BASE + 'login',
            None, 'Logging in', data=json.dumps({
                'id': email,
                'secret': password,
            }).encode(), headers=p_headers)['authorisationToken']

    def _call_api(self, path, media_id):
        return self._download_json(
            self._API_BASE + path + media_id, media_id, headers=self._HEADERS)

    def _extract_dve_api_url(self, media_id, media_type):
        stream_path = 'stream'
        if media_type == 'video':
            stream_path += '/vod/'
        else:
            stream_path += '?eventId='
        try:
            return self._call_api(
                stream_path, media_id)['playerUrlCallback']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                raise ExtractorError(
                    self._parse_json(e.cause.read().decode(), media_id)['messages'][0],
                    expected=True)
            raise

    def _real_extract(self, url):
        domain, media_type, media_id, playlist_id = re.match(self._VALID_URL, url).groups()

        if playlist_id:
            if self._downloader.params.get('noplaylist'):
                self.to_screen('Downloading just video %s because of --no-playlist' % media_id)
            else:
                self.to_screen('Downloading playlist %s - add --no-playlist to just download video' % playlist_id)
                media_type, media_id = 'playlist', playlist_id

        if media_type == 'playlist':
            playlist = self._call_api('vod/playlist/', media_id)
            entries = []
            for video in try_get(playlist, lambda x: x['videos']['vods']) or []:
                video_id = str_or_none(video.get('id'))
                if not video_id:
                    continue
                entries.append(self.url_result(
                    'https://%s/video/%s' % (domain, video_id),
                    self.ie_key(), video_id))
            return self.playlist_result(
                entries, media_id, playlist.get('title'),
                playlist.get('description'))

        dve_api_url = self._extract_dve_api_url(media_id, media_type)
        video_data = self._download_json(dve_api_url, media_id)
        is_live = media_type == 'live'
        if is_live:
            title = self._live_title(self._call_api('event/', media_id)['title'])
        else:
            title = video_data['name']

        formats = []
        for proto in ('hls', 'dash'):
            media_url = video_data.get(proto + 'Url') or try_get(video_data, lambda x: x[proto]['url'])
            if not media_url:
                continue
            if proto == 'hls':
                m3u8_formats = self._extract_m3u8_formats(
                    media_url, media_id, 'mp4', 'm3u8' if is_live else 'm3u8_native',
                    m3u8_id='hls', fatal=False, headers=self._MANIFEST_HEADERS)
                for f in m3u8_formats:
                    f.setdefault('http_headers', {}).update(self._MANIFEST_HEADERS)
                    formats.append(f)
            else:
                formats.extend(self._extract_mpd_formats(
                    media_url, media_id, mpd_id='dash', fatal=False,
                    headers=self._MANIFEST_HEADERS))
        self._sort_formats(formats)

        subtitles = {}
        for subtitle in video_data.get('subtitles', []):
            subtitle_url = subtitle.get('url')
            if not subtitle_url:
                continue
            subtitles.setdefault(subtitle.get('lang', 'en_US'), []).append({
                'url': subtitle_url,
            })

        return {
            'id': media_id,
            'title': title,
            'formats': formats,
            'thumbnail': video_data.get('thumbnailUrl'),
            'description': video_data.get('description'),
            'duration': int_or_none(video_data.get('duration')),
            'tags': video_data.get('tags'),
            'is_live': is_live,
            'subtitles': subtitles,
        }
