import datetime as dt
import itertools
import math

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    float_or_none,
    int_or_none,
    merge_dicts,
    parse_iso8601,
    parse_m3u8_attributes,
    parse_resolution,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import find_element, traverse_obj


class ZanIE(InfoExtractor):
    IE_NAME = 'zan'
    IE_DESC = 'Z-aN'

    _BASE_URL = 'https://www.zan-live.com'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['JP']
    _VALID_URL = r'https?://(www\.)?zan-live\.com/[^/?#]+/live/play/\d+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.zan-live.com/en/live/play/1797/663',
        'info_dict': {
            'id': '663',
            'ext': 'mp4',
            'title': 'The sample video page',
            'alt_title': 'こちらはサンプル動画の再生テストページとなります。',
            'description': 'md5:12ba331396215fe345b9362c56f3da86',
            'release_date': '20220228',
            'release_timestamp': 1646060400,
            'thumbnail': r're:https?://storage\.zan-live\.com/image/.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://www.zan-live.com/ja/live/play/6910/4268',
        'info_dict': {
            'id': '4268',
            'ext': 'mp4',
            'title': '縁結びのゆかり様1stイベント 結び、結ばれ、桃源郷',
            'alt_title': '縁結びのゆかり様1stイベント 結び、結ばれ、桃源郷 昼公演[アーカイブ]',
            'description': 'md5:f53156a49ce5b45265d07966679ab494',
            'release_date': '20260614',
            'release_timestamp': 1781419500,
            'thumbnail': r're:https?://storage\.zan-live\.com/image/.+\.(?:jpe?g|png)',
        },
    }]

    @staticmethod
    def _fixup_m3u8_formats(formats, m3u8_doc, m3u8_url):
        for stream_inf, media_url in itertools.pairwise(
            map(str.strip, m3u8_doc.splitlines()),
        ):
            if not stream_inf.startswith('#EXT-X-STREAM-INF:') or not media_url:
                continue

            res = traverse_obj(stream_inf, (
                {parse_m3u8_attributes}, 'DISPLAY-NAME', {parse_resolution}))
            if not res:
                continue

            format_url = urljoin(m3u8_url, media_url)
            for fmt in traverse_obj(formats, (
                lambda _, v: v.get('url') == format_url,
            )):
                fmt.update(merge_dicts(fmt, res))

    @staticmethod
    def _get_multiangle_layout(ma_type, ma_number):
        # Z-aN packs all angles into one video frame
        # Square divisions use an n x n grid
        # 6 divisions use a 3 x 3 grid where angle 1 covers a 2 x 2 block
        # https://static.zan-live.com/static/js/live/shaka_multiangle.js

        divisions = int_or_none(ma_type.partition('_')[0]) or 0
        if divisions <= 0:
            return None, None

        unit = math.isqrt(divisions)
        if unit ** 2 == divisions:
            areas = [(i % unit, i // unit, 1, 1) for i in range(divisions)]
        elif divisions == 6:
            unit = 3
            areas = [
                (0, 0, 2, 2),
                *[(2, i, 1, 1) for i in range(2)],
                *[(i, 2, 1, 1) for i in range(3)],
            ]
        else:
            return None, None

        if not (ma_number and 1 <= ma_number <= len(areas)):
            ma_number = len(areas)

        return unit, areas[:ma_number]

    @staticmethod
    def _multiangle_crop(x, y, w, h, unit, margin_y):
        margin_x = margin_y * 9 / 16

        return (
            f'crop='
            f'trunc((iw*{w}/{unit}-{margin_x * 2:g})/2)*2:'
            f'trunc((ih*{h}/{unit}-{margin_y * 2:g})/2)*2:'
            f'trunc(iw*{x}/{unit}+{margin_x:g}):'
            f'trunc(ih*{y}/{unit}+{margin_y:g})'
        )

    def _multiangle_formats(self, formats, ma_type, ma_number, ma_margin):
        if self._configuration_arg('split_angles', ['false'])[0] == 'false':
            self.to_screen(
                'Multi-angle formats are available. Use --extractor-args '
                '"zan:split_angles=true" to extract separate angle formats')
            return formats

        unit, areas = self._get_multiangle_layout(ma_type, ma_number)
        if areas is None:
            self.report_warning(f'Unsupported multiangle type: {ma_type}')
            return formats

        angle_formats = []
        for fmt in formats:
            if fmt.get('vcodec') == 'none':
                continue

            height = traverse_obj(fmt, ('height', {int_or_none}))
            for i, (x, y, w, h) in enumerate(areas, 1):
                angle_formats.append({
                    **fmt,
                    'downloader_options': {
                        'ffmpeg_args_out': [
                            '-vf', self._multiangle_crop(x, y, w, h, unit, ma_margin),
                            '-c:v', 'libx264',
                            '-c:a', 'copy',
                        ],
                    },
                    'format_id': f'{fmt["format_id"]}-angle{i}',
                    'height': int_or_none(
                        (height * h / unit - ma_margin * 2) // 2 * 2) if height else None,
                    'protocol': 'm3u8',
                    'source_preference': -i,
                })

        return angle_formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        if error_msg := traverse_obj(webpage, (
            {find_element(cls='p-common_message__headline--error')}, {clean_html}, filter,
        )):
            self.raise_geo_restricted(error_msg, countries=self._GEO_COUNTRIES)

        csrf_token = self._html_search_meta('csrf-token', webpage, default=None)
        pct = self._html_search_meta('vod-pct', webpage, default=None)
        token = self._html_search_meta('live-player-token', webpage, default=None)
        if not all((csrf_token, pct, token)):
            self.raise_login_required()

        status = self._download_json(
            f'{self._BASE_URL}/api/live/{video_id}/getLiveStatus', video_id, headers={
                'X-Csrf-Token': csrf_token,
            }, data=urlencode_postdata({
                'pct': pct,
                'token': token,
            }))
        if not traverse_obj(status, ('isSuccess', {bool})):
            raise ExtractorError('Unexpected error')

        result = traverse_obj(status, ('result', {dict}))
        for key, required, error_message in (
            ('isFinished', False, 'This video is no longer available'),
            ('canPlay', True, 'Ticket has expired'),
        ):
            if traverse_obj(result, (key, {bool})) is not required:
                raise ExtractorError(error_message, expected=True)

        is_live = not traverse_obj(result, ('isVod', {bool}))
        release_timestamp = parse_iso8601(self._html_search_meta('open-live-date', webpage))
        srv_time = traverse_obj(status, ('srvTime', {int_or_none}), default=0)

        if is_live and release_timestamp and srv_time < release_timestamp:
            start_time = dt.datetime.fromtimestamp(
                release_timestamp, dt.timezone.utc,
            ).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
            self.raise_no_formats(
                f'This livestream is scheduled to start at {start_time}', expected=True)

            return {
                'id': video_id,
                'live_status': 'is_upcoming',
                'release_timestamp': release_timestamp,
            }

        m3u8_url = self._html_search_meta('live-url', webpage, fatal=True)
        m3u8_doc, urlh = self._download_webpage_handle(
            m3u8_url, video_id, note='Downloading m3u8 information')
        m3u8_url = urlh.url

        formats, _ = self._parse_m3u8_formats_and_subtitles(m3u8_doc, m3u8_url, 'mp4')
        self._fixup_m3u8_formats(formats, m3u8_doc, m3u8_url)

        if ma_type := self._html_search_meta('multiangle-type', webpage, default=None):
            ma_number = int_or_none(self._html_search_meta(
                'multiangle-number', webpage, default=None))
            ma_margin = float_or_none(self._html_search_meta(
                'multiangle-margin', webpage, default=None), default=0)
            formats = self._multiangle_formats(formats, ma_type, ma_number, ma_margin)

        detail_url = traverse_obj(webpage, (
            {find_element(cls='linkTxt')},
            {find_element(cls='d-flex align-items-center', html=True)},
            {extract_attributes}, 'href', {urljoin(f'{self._BASE_URL}/')}))
        detail = self._download_webpage(detail_url, video_id, fatal=False) or ''

        return {
            'id': video_id,
            'alt_title': traverse_obj(webpage, (
                {self._og_search_title}, {clean_html}, filter)),
            'formats': formats,
            'is_live': is_live,
            'release_timestamp': release_timestamp,
            'thumbnail': self._og_search_thumbnail(detail),
            **traverse_obj(detail, {
                'title': ({self._og_search_title}, {clean_html}, filter),
                'description': ((
                    {find_element(cls='p-eventinfo__detail')},
                    {find_element(cls='groupDetail')},
                ), {clean_html}, filter, any),
            }),
        }
