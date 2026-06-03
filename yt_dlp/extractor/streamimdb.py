import re
from urllib.parse import parse_qs, urlparse

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    traverse_obj,
    url_or_none,
    urljoin,
)


class StreamIMDbIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamimdb\.ru/embed/(?P<media_type>movie|tv|anime)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://streamimdb.ru/embed/movie/tt15940132',
        'info_dict': {
            'id': 'tt15940132',
            'ext': 'mp4',
            'title': 'War Machine 2026',
            'thumbnail': r're:https?://.+\.jpg',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _extract_player_config(self, webpage, video_id):
        if not webpage:
            return {}
        return self._search_json(
            r'\bconst\s+CONFIG\s*=',
            webpage, 'player config', video_id, default={})

    def _extract_iframe_url(self, webpage, url):
        for iframe in re.finditer(r'(?s)<iframe\b[^>]*>', webpage):
            iframe_url = urljoin(url, extract_attributes(iframe.group(0)).get('src'))
            if url_or_none(iframe_url):
                return iframe_url

    def _extract_subtitles(self, stream_data):
        subtitles = {}
        for sub in traverse_obj(stream_data, (
                ('subtitles', 'default_subs', 'subs'), ..., {dict})):
            sub_url = url_or_none(sub.get('file') or sub.get('url'))
            if not sub_url:
                continue
            subtitles.setdefault(sub.get('lang') or sub.get('language') or 'en', []).append({
                'url': sub_url,
                'name': sub.get('label') or sub.get('name'),
            })
        return subtitles

    def _real_extract(self, url):
        media_type, video_id = self._match_valid_url(url).group('media_type', 'id')
        url_query = parse_qs(urlparse(url).query)
        url_season = (url_query.get('season') or [None])[0]
        url_episode = (url_query.get('episode') or [None])[0]
        webpage = self._download_webpage(url, video_id)
        player_url = self._extract_iframe_url(webpage, url)

        player_webpage = None
        config = self._extract_player_config(webpage, video_id)
        if player_url:
            player_webpage = self._download_webpage(
                player_url, video_id, note='Downloading player webpage', fatal=False,
                headers={'Referer': url})
            config = self._extract_player_config(player_webpage, video_id) or config

        stream_api_url = config.get('streamDataApiUrl') or 'https://streamdata.vaplayer.ru/api.php'
        api_video_id = config.get('mediaId') or video_id
        api_media_type = config.get('mediaType') or media_type
        player_headers = {'Referer': player_url or url}
        stream_data = self._download_json(
            stream_api_url, video_id, note='Downloading stream metadata',
            headers=player_headers,
            query={
                'imdb' if str(api_video_id).startswith('tt') else 'tmdb': api_video_id,
                'type': api_media_type,
                **({'season': config.get('season') or url_season} if config.get('season') or url_season else {}),
                **({'episode': config.get('episode') or url_episode} if config.get('episode') or url_episode else {}),
            })

        data = stream_data.get('data') or {}
        formats = []
        for stream_url in traverse_obj(data, ('stream_urls', ..., {url_or_none})):
            ext = determine_ext(stream_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    stream_url, video_id, 'mp4', m3u8_id='hls', fatal=False,
                    headers=player_headers))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    stream_url, video_id, mpd_id='dash', fatal=False))
            else:
                formats.append({'url': stream_url, 'http_headers': player_headers})

        for fmt in formats:
            fmt.setdefault('http_headers', {}).update(player_headers)

        return {
            'id': video_id,
            'title': data.get('title') or self._html_extract_title(player_webpage or webpage),
            'thumbnail': url_or_none(data.get('backdrop')) or url_or_none(config.get('poster')),
            'formats': formats,
            'subtitles': self._extract_subtitles(stream_data),
            'thumbnails': [{
                'url': thumbnails_url,
            }] if (thumbnails_url := url_or_none(stream_data.get('thumbnails_url'))) else None,
        }
