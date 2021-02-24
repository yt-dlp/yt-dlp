# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    js_to_json,
)


class OnDemandKoreaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ondemandkorea\.com/(?P<id>[^/]+)\.html'
    _GEO_COUNTRIES = ['US', 'CA']
    _TESTS = [{
        'url': 'https://www.ondemandkorea.com/ask-us-anything-e43.html',
        'info_dict': {
            'id': 'ask-us-anything-e43',
            'ext': 'mp4',
            'title': 'Ask Us Anything : Gain, Ji Soo - 09/24/2016',
            'description': 'A talk show/game show with a school theme where celebrity guests appear as “transfer students.”',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {
            'skip_download': 'm3u8 download'
        }
    }, {
        'url': 'https://www.ondemandkorea.com/confession-e01-1.html',
        'info_dict': {
            'id': 'confession-e01-1',
            'ext': 'mp4',
            'title': 'Confession : E01',
            'description': 'Choi Do-hyun, a criminal attorney, is the son of a death row convict. Ever since Choi Pil-su got arrested for murder, Do-hyun has wanted to solve his ',
            'thumbnail': r're:^https?://.*\.jpg$',
            'subtitles': {
                'English': 'mincount:1',
            },
        },
        'params': {
            'skip_download': 'm3u8 download'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, fatal=False)

        if not webpage:
            # Page sometimes returns captcha page with HTTP 403
            raise ExtractorError(
                'Unable to access page. You may have been blocked.',
                expected=True)

        if 'msg_block_01.png' in webpage:
            self.raise_geo_restricted(
                msg='This content is not available in your region',
                countries=self._GEO_COUNTRIES)

        if 'This video is only available to ODK PLUS members.' in webpage:
            raise ExtractorError(
                'This video is only available to ODK PLUS members.',
                expected=True)

        if 'ODK PREMIUM Members Only' in webpage:
            raise ExtractorError(
                'This video is only available to ODK PREMIUM members.',
                expected=True)

        title = self._search_regex(
            r'class=["\']episode_title["\'][^>]*>([^<]+)',
            webpage, 'episode_title', fatal=False) or self._og_search_title(webpage)

        jw_config = self._parse_json(
            self._search_regex(
                r'(?s)odkPlayer\.init.*?(?P<options>{[^;]+}).*?;',
                webpage, 'jw config', group='options'),
            video_id, transform_source=js_to_json)
        info = self._parse_jwplayer_data(
            jw_config, video_id, require_title=False, m3u8_id='hls',
            base_url=url)

        info.update({
            'title': title,
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage)
        })
        return info
