import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    extract_attributes,
    int_or_none,
    parse_qs,
    smuggle_url,
    unescapeHTML,
    unsmuggle_url,
)


class GlomexBaseIE(InfoExtractor):
    _DEFAULT_ORIGIN_URL = 'https://player.glomex.com/'
    _API_URL = 'https://integration-cloudfront-eu-west-1.mes.glomex.cloud/'

    @staticmethod
    def _smuggle_origin_url(url, origin_url):
        if origin_url is None:
            return url
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
            video_id, f'Downloading {video_id_type} JSON',
            f'Unable to download {video_id_type} JSON',
            query=query)

    def _download_and_extract_api_data(self, video_id, integration, current_url):
        api_data = self._download_api_data(video_id, integration, current_url)
        videos = api_data['videos']
        if not videos:
            raise ExtractorError(f'no videos found for {video_id}')
        videos = [self._extract_api_data(video, video_id) for video in videos]
        return videos[0] if len(videos) == 1 else self.playlist_result(videos, video_id)

    def _extract_api_data(self, video, video_id):
        if video.get('error_code') == 'contentGeoblocked':
            self.raise_geo_restricted(countries=video['geo_locations'])

        formats, subs = [], {}
        for format_id, format_url in video['source'].items():
            ext = determine_ext(format_url)
            if ext == 'm3u8':
                formats_, subs_ = self._extract_m3u8_formats_and_subtitles(
                    format_url, video_id, 'mp4', m3u8_id=format_id,
                    fatal=False)
                formats.extend(formats_)
                self._merge_subtitles(subs_, target=subs)
            else:
                formats.append({
                    'url': format_url,
                    'format_id': format_id,
                })
        if video.get('language'):
            for fmt in formats:
                fmt['language'] = video['language']

        images = (video.get('images') or []) + [video.get('image') or {}]
        thumbnails = [{
            'id': image.get('id'),
            'url': f'{image["url"]}/profile:player-960x540',
            'width': 960,
            'height': 540,
        } for image in images if image.get('url')]
        self._remove_duplicate_formats(thumbnails)

        return {
            'id': video.get('clip_id') or video_id,
            'title': video.get('title'),
            'description': video.get('description'),
            'thumbnails': thumbnails,
            'duration': int_or_none(video.get('clip_duration')),
            'timestamp': video.get('created_at'),
            'formats': formats,
            'subtitles': subs,
        }


class GlomexIE(GlomexBaseIE):
    IE_NAME = 'glomex'
    IE_DESC = 'Glomex videos'
    _VALID_URL = r'https?://video\.glomex\.com/[^/]+/(?P<id>v-[^-]+)'
    _INTEGRATION_ID = '19syy24xjn1oqlpc'

    _TESTS = [{
        'url': 'https://video.glomex.com/sport/v-cb24uwg77hgh-nach-2-0-sieg-guardiola-mit-mancity-vor-naechstem-titel',
        'info_dict': {
            'id': 'v-cb24uwg77hgh',
            'ext': 'mp4',
            'title': 'Nach 2:0-Sieg: Guardiola mit ManCity vor nächstem Titel',
            'description': 'md5:1ea6b6caff1443fcbbba159e432eedb8',
            'duration': 29600,
            'thumbnail': r're:https?://i[a-z0-9]thumbs\.glomex\.com/.+',
            'timestamp': 1619895017,
            'upload_date': '20210501',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            GlomexEmbedIE.build_player_url(video_id, self._INTEGRATION_ID, url),
            GlomexEmbedIE.ie_key(), video_id)


class GlomexEmbedIE(GlomexBaseIE):
    IE_NAME = 'glomex:embed'
    IE_DESC = 'Glomex embedded videos'
    _BASE_PLAYER_URL = '//player.glomex.com/integration/1/iframe-player.html'
    _BASE_PLAYER_URL_RE = re.escape(_BASE_PLAYER_URL).replace('/1/', r'/[^/]/')
    _VALID_URL = rf'https?:{_BASE_PLAYER_URL_RE}\?([^#]+&)?playlistId=(?P<id>[^#&]+)'

    _TESTS = [{
        'url': 'https://player.glomex.com/integration/1/iframe-player.html?integrationId=4059a013k56vb2yd&playlistId=v-cfa6lye0dkdd-sf',
        'info_dict': {
            'id': 'v-cfa6lye0dkdd-sf',
            'ext': 'mp4',
            'title': 'Φώφη Γεννηματά: Ο επικήδειος λόγος του 17χρονου γιου της, Γιώργου',
            'thumbnail': r're:https?://i[a-z0-9]thumbs\.glomex\.com/.+',
            'timestamp': 1635337199,
            'duration': 133080,
            'upload_date': '20211027',
            'description': 'md5:e741185fc309310ff5d0c789b437be66',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://player.glomex.com/integration/1/iframe-player.html?origin=fullpage&integrationId=19syy24xjn1oqlpc&playlistId=rl-vcb49w1fb592p&playlistIndex=0',
        'info_dict': {
            'id': 'rl-vcb49w1fb592p',
        },
        'playlist_count': 100,
    }, {
        # Geo-restricted
        'url': 'https://player.glomex.com/integration/1/iframe-player.html?playlistId=cl-bgqaata6aw8x&integrationId=19syy24xjn1oqlpc',
        'info_dict': {
            'id': 'cl-bgqaata6aw8x',
        },
        'playlist_mincount': 2,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.skai.gr/news/world/iatrikos-syllogos-tourkias-to-turkovac-aplo-dialyma-erntogan-eiste-apateones-kai-pseytes',
        'info_dict': {
            'id': 'v-ch2nkhcirwc9-sf',
            'ext': 'mp4',
            'title': 'Ιατρικός Σύλλογος Τουρκίας: Το Turkovac είναι ένα απλό διάλυμα –Ερντογάν: Είστε απατεώνες και ψεύτες',
            'description': 'md5:8b517a61d577efe7e36fde72fd535995',
            'duration': 460000,
            'thumbnail': r're:https?://i[a-z0-9]thumbs\.glomex\.com/.+',
            'timestamp': 1641885019,
            'upload_date': '20220111',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    @classmethod
    def build_player_url(cls, video_id, integration, origin_url=None):
        query_string = urllib.parse.urlencode({
            'playlistId': video_id,
            'integrationId': integration,
        })
        return cls._smuggle_origin_url(f'https:{cls._BASE_PLAYER_URL}?{query_string}', origin_url)

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        # https://docs.glomex.com/publisher/video-player-integration/javascript-api/
        quot_re = r'["\']'

        regex = fr'''(?x)
            <iframe[^>]+?src=(?P<q>{quot_re})(?P<url>
                (?:https?:)?{cls._BASE_PLAYER_URL_RE}\?(?:(?!(?P=q)).)+
            )(?P=q)'''
        for mobj in re.finditer(regex, webpage):
            embed_url = unescapeHTML(mobj.group('url'))
            if cls.suitable(embed_url):
                yield cls._smuggle_origin_url(embed_url, url)

        regex = fr'''(?x)
            <glomex-player [^>]+?>|
            <div[^>]* data-glomex-player=(?P<q>{quot_re})true(?P=q)[^>]*>'''
        for mobj in re.finditer(regex, webpage):
            attrs = extract_attributes(mobj.group(0))
            if attrs.get('data-integration-id') and attrs.get('data-playlist-id'):
                yield cls.build_player_url(attrs['data-playlist-id'], attrs['data-integration-id'], url)

        # naive parsing of inline scripts for hard-coded integration parameters
        regex = fr'''(?x)
            (?P<is_js>dataset\.)?%s\s*(?(is_js)=|:)\s*
            (?P<q>{quot_re})(?P<id>(?:(?!(?P=q)).)+)(?P=q)\s'''
        for mobj in re.finditer(r'(?x)<script[^<]*>.+?</script>', webpage):
            script = mobj.group(0)
            integration_id = re.search(regex % 'integrationId', script)
            if not integration_id:
                continue
            playlist_id = re.search(regex % 'playlistId', script)
            if playlist_id:
                yield cls.build_player_url(playlist_id, integration_id, url)

    def _real_extract(self, url):
        url, origin_url = self._unsmuggle_origin_url(url)
        playlist_id = self._match_id(url)
        integration = parse_qs(url).get('integrationId', [None])[0]
        if not integration:
            raise ExtractorError('No integrationId in URL', expected=True)
        return self._download_and_extract_api_data(playlist_id, integration, origin_url)
