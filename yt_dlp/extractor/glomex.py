# coding: utf-8
from __future__ import unicode_literals

import re
from urllib.parse import (
    urlencode,
    urlparse,
)

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    smuggle_url,
    try_get,
    unescapeHTML,
    unsmuggle_url,
)


class GlomexBaseIE(InfoExtractor):
    _DEFAULT_ORIGIN_URL = 'https://player.glomex.com/'
    _API_URL = 'https://integration-cloudfront-eu-west-1.mes.glomex.cloud/'

    @staticmethod
    def _smuggle_origin_url(url, origin_url):
        return smuggle_url(url, {'origin': origin_url})

    @classmethod
    def _unsmuggle_origin_url(cls, url, fallback_origin_url=None):
        defaults = {'origin': fallback_origin_url or cls._DEFAULT_ORIGIN_URL}
        unsmuggled_url, data = unsmuggle_url(url, default=defaults)
        return unsmuggled_url, data['origin']

    def _get_videoid_type(self, video_id):
        _VIDEOID_TYPES = {
            'v': 'video',
            'pl': 'playlist',
            'rl': 'related videos playlist',
            'cl': 'curated playlist',
        }
        prefix = video_id.split('-')[0]
        return _VIDEOID_TYPES.get(prefix, 'unknown type')

    def _download_api_data(self, video_id, integration, current_url=None):
        query = {
            'integration_id': integration,
            'playlist_id': video_id,
            'current_url': current_url or self._DEFAULT_ORIGIN_URL,
        }
        video_id_type = self._get_videoid_type(video_id)
        return self._download_json(
            self._API_URL,
            video_id, 'Downloading %s JSON' % video_id_type,
            'Unable to download %s JSON' % video_id_type,
            query=query)

    def _download_and_extract_api_data(self, video_id, integration, current_url):
        api_data = self._download_api_data(video_id, integration, current_url)
        videos = api_data['videos']
        if not videos:
            raise ExtractorError('no videos found for %s' % video_id)
        if len(videos) == 1:
            return self._extract_api_data(videos[0], video_id)
        # assume some kind of playlist
        videos = [
            self._extract_api_data(video, video_id)
            for video in videos
        ]
        return self.playlist_result(videos, video_id)

    def _extract_api_data(self, video, video_id):
        if video.get('error_code') == 'contentGeoblocked':
            self.raise_geo_restricted(countries=video['geo_locations'])
        info = self._extract_info(video, video_id)
        info['formats'] = self._extract_formats(video, video_id)
        return info

    @staticmethod
    def _extract_info(video, video_id=None, require_title=True):
        title = video['title'] if require_title else video.get('title')

        def append_image_url(url, default='profile:player-960x540'):
            if url:
                return '%s/%s' % (url, default)
        thumbnail = append_image_url(try_get(video,
                                             lambda x: x['image']['url']))
        thumbnails = [
            dict(width=960, height=540,
                 **{k: append_image_url(v) if k == 'url' else v
                    for k, v in image.items() if k in ('id', 'url')})
            for image in video.get('images', [])
        ] or None

        return {
            'id': video.get('clip_id') or video_id,
            'title': title,
            'description': video.get('description'),
            'thumbnail': thumbnail,
            'thumbnails': thumbnails,
            'duration': int_or_none(video.get('clip_duration')),
            'timestamp': video.get('created_at'),
        }

    def _extract_formats(self, options, video_id):
        formats = []
        for format_id, format_url in options['source'].items():
            ext = determine_ext(format_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', m3u8_id=format_id,
                    fatal=False))
            else:
                formats.append({
                    'url': format_url,
                    'format_id': format_id,
                })
        if options.get('language'):
            for format in formats:
                format['language'] = options.get('language')
        self._sort_formats(formats)
        return formats


class GlomexIE(GlomexBaseIE):
    IE_NAME = 'glomex'
    IE_DESC = 'Glomex videos'
    _VALID_URL = r'https?://video\.glomex\.com/[^/]+/(?P<id>v-[^-]+)'
    # Hard-coded integration ID for video.glomex.com
    _INTEGRATION_ID = '19syy24xjn1oqlpc'

    _TEST = {
        'url': 'https://video.glomex.com/sport/v-cb24uwg77hgh-nach-2-0-sieg-guardiola-mit-mancity-vor-naechstem-titel',
        'md5': 'cec33a943c4240c9cb33abea8c26242e',
        'info_dict': {
            'id': 'v-cb24uwg77hgh',
            'ext': 'mp4',
            'title': 'md5:38a90cedcfadd72982c81acf13556e0c',
            'description': 'md5:1ea6b6caff1443fcbbba159e432eedb8',
            'duration': 29600,
            'timestamp': 1619895017,
            'upload_date': '20210501',
            'age_limit': None,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # Defer to glomex:embed IE: Build and return a player URL using the
        # matched video ID and the hard-coded integration ID
        return self.url_result(
            GlomexEmbedIE.build_player_url(video_id, self._INTEGRATION_ID,
                                           url),
            GlomexEmbedIE.ie_key(),
            video_id
        )


class GlomexEmbedIE(GlomexBaseIE):
    IE_NAME = 'glomex:embed'
    IE_DESC = 'Glomex embedded videos'
    _BASE_PLAYER_URL = 'https://player.glomex.com/integration/1/iframe-player.html'
    _VALID_URL = r'''(?x)https?://player\.glomex\.com/integration/[^/]+/iframe-player\.html
        \?(?:(?:integrationId=(?P<integration>[^&#]+)|playlistId=(?P<id>[^&#]+)|[^&=#]+=[^&#]+)&?)+'''

    _TESTS = [{
        'url': 'https://player.glomex.com/integration/1/iframe-player.html?integrationId=4059a013k56vb2yd&playlistId=v-cfa6lye0dkdd-sf',
        'info_dict': {
            'id': 'v-cfa6lye0dkdd-sf',
            'ext': 'mp4',
            'timestamp': 1635337199,
            'duration': 133080,
            'upload_date': '20211027',
            'description': 'md5:e741185fc309310ff5d0c789b437be66',
            'title': 'md5:35647293513a6c92363817a0fb0a7961',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://player.glomex.com/integration/1/iframe-player.html?origin=fullpage&integrationId=19syy24xjn1oqlpc&playlistId=rl-vcb49w1fb592p&playlistIndex=0',
        'info_dict': {
            'id': 'rl-vcb49w1fb592p',
        },
        'playlist_count': 100,
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://player.glomex.com/integration/1/iframe-player.html?playlistId=cl-bgqaata6aw8x&integrationId=19syy24xjn1oqlpc',
        'info_dict': {
            'id': 'cl-bgqaata6aw8x',
        },
        'playlist_mincount': 2,
        'params': {
            'skip_download': True,
        },
    }]

    @classmethod
    def build_player_url(cls, video_id, integration, origin_url=None):
        query_string = urlencode({
            'playlistId': video_id,
            'integrationId': integration,
        })
        player_url = '%s?%s' % (cls._BASE_PLAYER_URL, query_string)
        if origin_url is not None:
            player_url = cls._smuggle_origin_url(player_url, origin_url)
        return player_url

    @classmethod
    def _extract_urls(cls, webpage, origin_url):
        # make the scheme in _VALID_URL optional
        _URL_RE = r'(?:https?:)?//' + cls._VALID_URL.split('://', 1)[1]
        # simplify the query string part of _VALID_URL; after extracting iframe
        # src, the URL will be matched again
        _URL_RE = _URL_RE.split(r'\?', 1)[0] + r'\?(?:(?!(?P=_q1)).)+'
        # https://docs.glomex.com/publisher/video-player-integration/javascript-api/
        EMBED_RE = r'''(?x)
        (?:
            <iframe[^>]+?src=(?P<_q1>%(quot_re)s)
                (?P<url>%(url_re)s)(?P=_q1)|
            <(?P<html_tag>glomex-player|div)(?:
                data-integration-id=(?P<_q2>%(quot_re)s)(?P<integration_html>(?:(?!(?P=_q2)).)+)(?P=_q2)|
                data-playlist-id=(?P<_q3>%(quot_re)s)(?P<id_html>(?:(?!(?P=_q3)).)+)(?P=_q3)|
                data-glomex-player=(?P<_q4>%(quot_re)s)(?P<glomex_player>true)(?P=_q4)|
                [^>]*?
            )+>|
            # naive parsing of inline scripts for hard-coded integration parameters
            <(?P<script_tag>script)[^<]*?>(?:
                (?P<_stjs1>dataset\.)?integrationId\s*(?(_stjs1)=|:)\s*
                    (?P<_q5>%(quot_re)s)(?P<integration_js>(?:(?!(?P=_q5)).)+)(?P=_q5)\s*(?(_stjs1);|,)?|
                (?P<_stjs2>dataset\.)?playlistId\s*(?(_stjs2)=|:)\s*
                    (?P<_q6>%(quot_re)s)(?P<id_js>(?:(?!(?P=_q6)).)+)(?P=_q6)\s*(?(_stjs2);|,)?|
                (?:\s|.)*?
            )+</script>
        )
        ''' % {'quot_re': r'["\']', 'url_re': _URL_RE}
        for mobj in re.finditer(EMBED_RE, webpage):
            url, html_tag, video_id_html, integration_html, glomex_player, \
                script_tag, video_id_js, integration_js = \
                mobj.group('url', 'html_tag', 'id_html',
                           'integration_html', 'glomex_player', 'script_tag',
                           'id_js', 'integration_js')
            if url:
                url = unescapeHTML(url)
                if url.startswith('//'):
                    scheme = urlparse(origin_url).scheme \
                        if origin_url else 'https'
                    url = '%s:%s' % (scheme, url)
                if not cls.suitable(url):
                    continue
                yield cls._smuggle_origin_url(url, origin_url)
            elif html_tag:
                if html_tag == "div" and not glomex_player:
                    continue
                if not video_id_html or not integration_html:
                    continue
                yield cls.build_player_url(video_id_html, integration_html,
                                           origin_url)
            elif script_tag:
                if not video_id_js or not integration_js:
                    continue
                yield cls.build_player_url(video_id_js, integration_js,
                                           origin_url)

    def _real_extract(self, url):
        url, origin_url = self._unsmuggle_origin_url(url)
        # must return a valid match since it was already tested when selecting the IE
        try:
            matches = self._VALID_URL_RE.match(url).groupdict()
        except AttributeError:
            matches = re.match(self._VALID_URL, url).groupdict()
        # id is not enforced in the pattern, so do it now; ditto integration
        video_id = matches['id']
        integration = matches['integration']
        return self._download_and_extract_api_data(video_id, integration,
                                                   origin_url)
