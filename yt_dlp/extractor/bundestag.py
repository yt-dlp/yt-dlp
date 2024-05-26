import functools
import re

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    bug_reports_message,
    clean_html,
    format_field,
    get_element_text_and_html_by_tag,
    int_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class BundestagIE(InfoExtractor):
    _VALID_URL = [
        r'https?://dbtg\.tv/[cf]vid/(?P<id>\d+)',
        r'https?://www\.bundestag\.de/mediathek/?\?(?:[^#]+&)?videoid=(?P<id>\d+)',
    ]
    _TESTS = [{
        'url': 'https://dbtg.tv/cvid/7605304',
        'info_dict': {
            'id': '7605304',
            'ext': 'mp4',
            'title': '145. Sitzung vom 15.12.2023, TOP 24 Barrierefreiheit',
            'description': 'md5:321a9dc6bdad201264c0045efc371561',
        },
    }, {
        'url': 'https://www.bundestag.de/mediathek?videoid=7602120&url=L21lZGlhdGhla292ZXJsYXk=&mod=mediathek',
        'info_dict': {
            'id': '7602120',
            'ext': 'mp4',
            'title': '130. Sitzung vom 18.10.2023, TOP 1 Befragung der Bundesregierung',
            'description': 'Befragung der Bundesregierung',
        },
    }, {
        'url': 'https://www.bundestag.de/mediathek?videoid=7604941#url=L21lZGlhdGhla292ZXJsYXk/dmlkZW9pZD03NjA0OTQx&mod=mediathek',
        'only_matching': True,
    }, {
        'url': 'http://dbtg.tv/fvid/3594346',
        'only_matching': True,
    }]

    _OVERLAY_URL = 'https://www.bundestag.de/mediathekoverlay'
    _INSTANCE_FORMAT = 'https://cldf-wzw-od.r53.cdn.tv1.eu/13014bundestagod/_definst_/13014bundestag/ondemand/3777parlamentsfernsehen/archiv/app144277506/145293313/{0}/{0}_playlist.smil/playlist.m3u8'

    _SHARE_URL = 'https://webtv.bundestag.de/player/macros/_x_s-144277506/shareData.json?contentId='
    _SHARE_AUDIO_REGEX = r'/\d+_(?P<codec>\w+)_(?P<bitrate>\d+)kb_(?P<channels>\w+)_\w+_\d+\.(?P<ext>\w+)'
    _SHARE_VIDEO_REGEX = r'/\d+_(?P<codec>\w+)_(?P<width>\w+)_(?P<height>\w+)_(?P<bitrate>\d+)kb_\w+_\w+_\d+\.(?P<ext>\w+)'

    def _bt_extract_share_formats(self, video_id):
        share_data = self._download_json(
            f'{self._SHARE_URL}{video_id}', video_id, note='Downloading share format JSON')
        if traverse_obj(share_data, ('status', 'code', {int})) != 1:
            self.report_warning(format_field(
                share_data, [('status', 'message', {str})],
                'Share API response: %s', default='Unknown Share API Error')
                + bug_reports_message())
            return

        for name, url in share_data.items():
            if not isinstance(name, str) or not url_or_none(url):
                continue

            elif name.startswith('audio'):
                match = re.search(self._SHARE_AUDIO_REGEX, url)
                yield {
                    'format_id': name,
                    'url': url,
                    'vcodec': 'none',
                    **traverse_obj(match, {
                        'acodec': 'codec',
                        'audio_channels': ('channels', {{'mono': 1, 'stereo': 2}.get}),
                        'abr': ('bitrate', {int_or_none}),
                        'ext': 'ext',
                    }),
                }

            elif name.startswith('download'):
                match = re.search(self._SHARE_VIDEO_REGEX, url)
                yield {
                    'format_id': name,
                    'url': url,
                    **traverse_obj(match, {
                        'vcodec': 'codec',
                        'tbr': ('bitrate', {int_or_none}),
                        'width': ('width', {int_or_none}),
                        'height': ('height', {int_or_none}),
                        'ext': 'ext',
                    }),
                }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats = []
        result = {'id': video_id, 'formats': formats}

        try:
            formats.extend(self._extract_m3u8_formats(
                self._INSTANCE_FORMAT.format(video_id), video_id, m3u8_id='instance'))
        except ExtractorError as error:
            if isinstance(error.cause, HTTPError) and error.cause.status == 404:
                raise ExtractorError('Could not find video id', expected=True)
            self.report_warning(f'Error extracting hls formats: {error}', video_id)
        formats.extend(self._bt_extract_share_formats(video_id))
        if not formats:
            self.raise_no_formats('Could not find suitable formats', video_id=video_id)

        result.update(traverse_obj(self._download_webpage(
            self._OVERLAY_URL, video_id,
            query={'videoid': video_id, 'view': 'main'},
            note='Downloading metadata overlay', fatal=False,
        ), {
            'title': (
                {functools.partial(get_element_text_and_html_by_tag, 'h3')}, 0,
                {functools.partial(re.sub, r'<span[^>]*>[^<]+</span>', '')}, {clean_html}),
            'description': ({functools.partial(get_element_text_and_html_by_tag, 'p')}, 0, {clean_html}),
        }))

        return result
