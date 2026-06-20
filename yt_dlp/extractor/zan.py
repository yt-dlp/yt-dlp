from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    int_or_none,
    parse_iso8601,
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
            ('isFinished', False, 'Video is no longer available'),
            ('canPlay', True, 'Ticket has expired'),
        ):
            if traverse_obj(result, (key, {bool})) is not required:
                raise ExtractorError(error_message, expected=True)

        is_live = not traverse_obj(result, ('isVod', {bool}))
        release_timestamp = parse_iso8601(self._html_search_meta('open-live-date', webpage))
        if is_live and traverse_obj(status, ('srvTime', {int_or_none})) < release_timestamp:
            self.raise_no_formats(
                f'This stream is scheduled to start at {release_timestamp} UTC', expected=True)

            return {
                'id': video_id,
                'live_status': 'is_upcoming',
                'release_timestamp': release_timestamp,
            }

        m3u8_url = self._html_search_meta('live-url', webpage, fatal=True)
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')

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
