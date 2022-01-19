# coding: utf-8
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    try_get,
    url_or_none,
    urlencode_postdata,
)


class HiDiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hidive\.com/stream/(?P<id>(?P<title>[^/]+)/(?P<key>[^/?#&]+))'
    # Using X-Forwarded-For results in 403 HTTP error for HLS fragments,
    # so disabling geo bypass completely
    _GEO_BYPASS = False
    _NETRC_MACHINE = 'hidive'
    _LOGIN_URL = 'https://www.hidive.com/account/login'

    _TESTS = [{
        'url': 'https://www.hidive.com/stream/the-comic-artist-and-his-assistants/s01e001',
        'info_dict': {
            'id': 'the-comic-artist-and-his-assistants/s01e001',
            'ext': 'mp4',
            'title': 'the-comic-artist-and-his-assistants/s01e001',
            'series': 'the-comic-artist-and-his-assistants',
            'season_number': 1,
            'episode_number': 1,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires Authentication',
    }]

    def _real_initialize(self):
        email, password = self._get_login_info()
        if email is None:
            return

        webpage = self._download_webpage(self._LOGIN_URL, None)
        form = self._search_regex(
            r'(?s)<form[^>]+action="/account/login"[^>]*>(.+?)</form>',
            webpage, 'login form')
        data = self._hidden_inputs(form)
        data.update({
            'Email': email,
            'Password': password,
        })
        self._download_webpage(
            self._LOGIN_URL, None, 'Logging in', data=urlencode_postdata(data))

    def _call_api(self, video_id, title, key, data={}, **kwargs):
        data = {
            **data,
            'Title': title,
            'Key': key,
            'PlayerId': 'f4f895ce1ca713ba263b91caeb1daa2d08904783',
        }
        return self._download_json(
            'https://www.hidive.com/play/settings', video_id,
            data=urlencode_postdata(data), **kwargs) or {}

    def _extract_subtitles_from_rendition(self, rendition, subtitles, parsed_urls):
        for cc_file in rendition.get('ccFiles', []):
            cc_url = url_or_none(try_get(cc_file, lambda x: x[2]))
            # name is used since we cant distinguish subs with same language code
            cc_lang = try_get(cc_file, (lambda x: x[1].replace(' ', '-').lower(), lambda x: x[0]), str)
            if cc_url not in parsed_urls and cc_lang:
                parsed_urls.add(cc_url)
                subtitles.setdefault(cc_lang, []).append({'url': cc_url})

    def _get_subtitles(self, url, video_id, title, key, parsed_urls):
        webpage = self._download_webpage(url, video_id, fatal=False) or ''
        subtitles = {}
        for caption in set(re.findall(r'data-captions=\"([^\"]+)\"', webpage)):
            renditions = self._call_api(
                video_id, title, key, {'Captions': caption}, fatal=False,
                note=f'Downloading {caption} subtitle information').get('renditions') or {}
            for rendition_id, rendition in renditions.items():
                self._extract_subtitles_from_rendition(rendition, subtitles, parsed_urls)
        return subtitles

    def _real_extract(self, url):
        video_id, title, key = self._match_valid_url(url).group('id', 'title', 'key')
        settings = self._call_api(video_id, title, key)

        restriction = settings.get('restrictionReason')
        if restriction == 'RegionRestricted':
            self.raise_geo_restricted()
        if restriction and restriction != 'None':
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, restriction), expected=True)

        formats, parsed_urls = [], {None}
        for rendition_id, rendition in settings['renditions'].items():
            audio, version, extra = rendition_id.split('_')
            m3u8_url = url_or_none(try_get(rendition, lambda x: x['bitrates']['hls']))
            if m3u8_url not in parsed_urls:
                parsed_urls.add(m3u8_url)
                frmt = self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id=rendition_id, fatal=False)
                for f in frmt:
                    f['language'] = audio
                    f['format_note'] = f'{version}, {extra}'
                formats.extend(frmt)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_id,
            'subtitles': self.extract_subtitles(url, video_id, title, key, parsed_urls),
            'formats': formats,
            'series': title,
            'season_number': int_or_none(
                self._search_regex(r's(\d+)', key, 'season number', default=None)),
            'episode_number': int_or_none(
                self._search_regex(r'e(\d+)', key, 'episode number', default=None)),
            'http_headers': {'Referer': url}
        }
