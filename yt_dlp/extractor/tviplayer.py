import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    filter_dict,
    int_or_none,
    js_to_json,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class TVIPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://tviplayer\.iol\.pt(?:/programa/[\w-]+/[a-f0-9]+)?/\w+/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://tviplayer.iol.pt/programa/jornal-das-8/53c6b3903004dc006243d0cf/video/61c8e8b90cf2c7ea0f0f71a9',
        'info_dict': {
            'id': '61c8e8b90cf2c7ea0f0f71a9',
            'ext': 'mp4',
            'duration': 4167,
            'title': 'Jornal das 8 - 26 de dezembro de 2021',
            'thumbnail': 'https://img.iol.pt/image/id/61c8ee630cf2cc58e7d98d9f/',
            'description': 'Com José Alberto Carvalho',
            'series': 'Jornal das 8',
            'season_id': '5fec9ae70cf28e704d9f883b',
            'episode': 'Jornal das 8 - 26 de dezembro de 2021',
            'timestamp': 1640548620,
            'upload_date': '20211226',
        },
    }, {
        # no /programa/
        'url': 'https://tviplayer.iol.pt/video/62c4131c0cf2f9a86eac06bb',
        'info_dict': {
            'id': '62c4131c0cf2f9a86eac06bb',
            'ext': 'mp4',
            'title': 'David e Mickael Carreira respondem: «Qual é o próximo a ser pai?»',
            'thumbnail': 'https://img.iol.pt/image/id/62c416490cf2ea367d4433fd/',
            'duration': 148,
            'description': 'No «Dois às 10», colocámos Mickael e David Carreira à prova.',
            'series': 'Dois às 10',
            'season_id': '61d2ec990cf2cc58e7dabfb7',
            'timestamp': 1657017060,
            'upload_date': '20220705',
        },
    }, {
        # episodio url
        'url': 'https://tviplayer.iol.pt/programa/para-sempre/61716c360cf2365a5ed894c4/episodio/t1e187',
        'info_dict': {
            'id': 't1e187',
            'ext': 'mp4',
            'title': 'Quem denunciou Pedro?',
            'thumbnail': 'https://img.iol.pt/image/id/62eda30b0cf2ea367d48973b/',
            'duration': 1250,
            'description': 'Episódio 187.',
            'series': 'Para Sempre',
            'season_id': '6179bdcd0cf290553bc01c3a',
            'episode': 'Quem denunciou Pedro?',
            'episode_number': 187,
            'timestamp': 1659738120,
            'upload_date': '20220805',
        },
    }]

    _wms_auth_sign_token = None

    def _real_initialize(self):
        if TVIPlayerIE._wms_auth_sign_token is None:
            TVIPlayerIE._wms_auth_sign_token = self._download_webpage(
                'https://services.iol.pt/matrix?userId=', 'wmsAuthSign',
                note='Downloading wmsAuthSign token')

    @staticmethod
    def _construct_video_url(video_id, suffix_len=4):
        """Construct a streaming URL from a hex video ID.

        The streaming server path uses trailing hex characters of the
        video ID as individual path segments, e.g. for *suffix_len=4* and
        video ID ``69dd70230cf27f6588a68e86`` the path becomes ``/8/e/8/6/``.
        """
        hex_suffix = video_id[-suffix_len:]
        path = '/'.join(hex_suffix)
        return f'https://streaming-vod1.iol.pt/vod/{path}/smil:{video_id}-L.smil/playlist.m3u8'

    def _extract_from_constructed_url(self, video_id):
        """Try constructing streaming URLs with varying path lengths (4 first, then 1-10)."""
        tried = set()
        for suffix_len in [4, *range(1, 11)]:
            if suffix_len in tried:
                continue
            tried.add(suffix_len)
            video_url = self._construct_video_url(video_id, suffix_len)
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                video_url, video_id, 'mp4', fatal=False,
                query=filter_dict({'wmsAuthSign': TVIPlayerIE._wms_auth_sign_token}))
            if formats:
                return formats, subtitles
        return [], {}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_data = self._search_json(
            r'(?<!-)\bvideo\s*:\s*\[', webpage, 'json_data', video_id,
            transform_source=js_to_json, fatal=False, default=None)

        if json_data is None:
            json_data = self._search_json(
                r'<script>\s*jsonData\s*=', webpage, 'json_data', video_id,
                fatal=False, default={})

        video_url = traverse_obj(json_data, ('videoUrl', {url_or_none}))

        if video_url:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                video_url, video_id, 'mp4',
                query=filter_dict({'wmsAuthSign': TVIPlayerIE._wms_auth_sign_token}))
        elif re.fullmatch(r'[a-f0-9]{24}', video_id):
            formats, subtitles = self._extract_from_constructed_url(video_id)
        else:
            formats, subtitles = [], {}

        if not formats:
            self.raise_no_formats('No playable formats found', video_id=video_id)

        info = self._search_json_ld(webpage, video_id, default={})
        info.pop('url', None)

        return {
            **info,
            'id': video_id,
            **traverse_obj(json_data, {
                'duration': ('duration', {int_or_none}),
                'series': ('programTitle', {str}),
                'season_number': ('program', 'seasonNum', {int_or_none}),
                'season_id': ('program', 'season', {str}),
                'episode_number': ('episodeNum', {int_or_none}),
                'timestamp': ('pubDate', {int_or_none(scale=1000)}),
                'description': ('description', {str}, {urllib.parse.unquote}),
            }),
            'title': (traverse_obj(json_data, ('title', {str}))
                      or info.get('title')
                      or self._og_search_title(webpage, default=None)),
            'thumbnail': (traverse_obj(json_data, (('cover', 'thumbnail'), {url_or_none}, any))
                          or info.get('thumbnail')
                          or self._og_search_thumbnail(webpage, default=None)),
            'formats': formats,
            'subtitles': subtitles,
        }
