import json

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
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

    def _initialize_pre_login(self):
        self._HEADERS = {
            'Realm': 'dce.' + self._REALM,
            'x-api-key': self._API_KEY,
        }

    def _perform_login(self, username, password):
        p_headers = self._HEADERS.copy()
        p_headers['Content-Type'] = 'application/json'
        self._HEADERS['Authorization'] = 'Bearer ' + self._download_json(
            self._API_BASE + 'login',
            None, 'Logging in', data=json.dumps({
                'id': username,
                'secret': password,
            }).encode(), headers=p_headers)['authorisationToken']

    def _real_initialize(self):
        if not self._HEADERS.get('Authorization'):
            self.raise_login_required(method='password')

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
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                raise ExtractorError(
                    self._parse_json(e.cause.response.read().decode(), media_id)['messages'][0],
                    expected=True)
            raise

    def _real_extract(self, url):
        domain, media_type, media_id, playlist_id = self._match_valid_url(url).groups()

        if playlist_id:
            if self._yes_playlist(playlist_id, media_id):
                media_type, media_id = 'playlist', playlist_id

        if media_type == 'playlist':
            playlist = self._call_api('vod/playlist/', media_id)
            entries = []
            for video in try_get(playlist, lambda x: x['videos']['vods']) or []:
                video_id = str_or_none(video.get('id'))
                if not video_id:
                    continue
                entries.append(self.url_result(
                    f'https://{domain}/video/{video_id}',
                    self.ie_key(), video_id))
            return self.playlist_result(
                entries, media_id, playlist.get('title'),
                playlist.get('description'))

        dve_api_url = self._extract_dve_api_url(media_id, media_type)
        video_data = self._download_json(dve_api_url, media_id)
        is_live = media_type == 'live'
        if is_live:
            title = self._call_api('event/', media_id)['title']
        else:
            title = video_data['name']

        formats = []
        for proto in ('hls', 'dash'):
            media_url = video_data.get(proto + 'Url') or try_get(video_data, lambda x: x[proto]['url'])
            if not media_url:
                continue
            if proto == 'hls':
                m3u8_formats = self._extract_m3u8_formats(
                    media_url, media_id, 'mp4', live=is_live,
                    m3u8_id='hls', fatal=False, headers=self._MANIFEST_HEADERS)
                for f in m3u8_formats:
                    f.setdefault('http_headers', {}).update(self._MANIFEST_HEADERS)
                    formats.append(f)
            else:
                formats.extend(self._extract_mpd_formats(
                    media_url, media_id, mpd_id='dash', fatal=False,
                    headers=self._MANIFEST_HEADERS))

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
