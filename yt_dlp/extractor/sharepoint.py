import json
import urllib.parse

from .common import InfoExtractor
from ..utils import determine_ext, int_or_none, url_or_none
from ..utils.traversal import traverse_obj


class SharePointIE(InfoExtractor):
    _BASE_URL_RE = r'https?://[\w-]+\.sharepoint\.com/'
    _VALID_URL = [
        rf'{_BASE_URL_RE}:v:/[a-z]/(?:[^/?#]+/)*(?P<id>[^/?#]{{46}})/?(?:$|[?#])',
        rf'{_BASE_URL_RE}(?!:v:)(?:[^/?#]+/)*stream\.aspx\?(?:[^#]+&)?id=(?P<id>[^&#]+)',
    ]
    _TESTS = [{
        'url': 'https://lut-my.sharepoint.com/:v:/g/personal/juha_eerola_student_lab_fi/EUrAmrktb4ZMhUcY9J2PqMEBD_9x_l0DyYWVgAvp-TTOMw?e=ZpQOOw',
        'md5': '2950821d0d4937a0a76373782093b435',
        'info_dict': {
            'id': '01EQRS7EKKYCNLSLLPQZGIKRYY6SOY7KGB',
            'display_id': 'EUrAmrktb4ZMhUcY9J2PqMEBD_9x_l0DyYWVgAvp-TTOMw',
            'ext': 'mp4',
            'title': 'CmvpJST',
            'duration': 54.567,
            'thumbnail': r're:https://.+/thumbnail',
            'uploader_id': '8dcec565-a956-4b91-95e5-bacfb8bc015f',
        },
    }, {
        'url': 'https://greaternyace.sharepoint.com/:v:/s/acementornydrive/ETski5eAfNVEoPRZUAyy1wEBpLgVFYWso5bjbZjfBLlPUg?e=PQUfVb',
        'md5': 'c496a01644223273bff12e93e501afd1',
        'info_dict': {
            'id': '01QI4AVTZ3ESFZPAD42VCKB5CZKAGLFVYB',
            'display_id': 'ETski5eAfNVEoPRZUAyy1wEBpLgVFYWso5bjbZjfBLlPUg',
            'ext': 'mp4',
            'title': '930103681233985536',
            'duration': 3797.326,
            'thumbnail': r're:https://.+/thumbnail',
        },
    }, {
        'url': 'https://lut-my.sharepoint.com/personal/juha_eerola_student_lab_fi/_layouts/15/stream.aspx?id=%2Fpersonal%2Fjuha_eerola_student_lab_fi%2FDocuments%2FM-DL%2FCmvpJST.mp4&ga=1&referrer=StreamWebApp.Web&referrerScenario=AddressBarCopied.view',
        'info_dict': {
            'id': '01EQRS7EKKYCNLSLLPQZGIKRYY6SOY7KGB',
            'display_id': '/personal/juha_eerola_student_lab_fi/Documents/M-DL/CmvpJST.mp4',
            'ext': 'mp4',
            'title': 'CmvpJST',
            'duration': 54.567,
            'thumbnail': r're:https://.+/thumbnail',
            'uploader_id': '8dcec565-a956-4b91-95e5-bacfb8bc015f',
        },
        'skip': 'Session cookies needed',
    }, {
        'url': 'https://izoobasisschool.sharepoint.com/:v:/g/Eaqleq8COVBIvIPvod0U27oBypC6aWOkk8ptuDpmJ6arHw',
        'only_matching': True,
    }, {
        'url': 'https://uskudaredutr-my.sharepoint.com/:v:/g/personal/songul_turkaydin_uskudar_edu_tr/EbTf-VRUIbtGuIN73tx1MuwBCHBOmNcWNqSLw61Fd2_o0g?e=n5Vkof',
        'only_matching': True,
    }, {
        'url': 'https://epam-my.sharepoint.com/:v:/p/dzmitry_tamashevich/Ec4ZOs-rATZHjFYZWVxjczEB649FCoYFKDV_x3RxZiWAGA?e=4hswgA',
        'only_matching': True,
    }, {
        'url': 'https://microsoft.sharepoint.com/:v:/t/MicrosoftSPARKRecordings-MSFTInternal/EWCyeqByVWBAt8wDvNZdV-UB0BvU5YVbKm0UHgdrUlI6dg?e=QbPck6',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = urllib.parse.unquote(self._match_id(url))
        webpage, urlh = self._download_webpage_handle(url, display_id)
        if urllib.parse.urlparse(urlh.url).hostname == 'login.microsoftonline.com':
            self.raise_login_required(
                'Session cookies are required for this URL and can be passed '
                'with the --cookies option. The --cookies-from-browser option will not work', method=None)

        video_data = self._search_json(r'g_fileInfo\s*=', webpage, 'player config', display_id)
        video_id = video_data['VroomItemId']

        parsed_url = urllib.parse.urlparse(video_data['.transformUrl'])
        base_media_url = urllib.parse.urlunparse(parsed_url._replace(
            path=urllib.parse.urljoin(f'{parsed_url.path}/', '../videomanifest'),
            query=urllib.parse.urlencode({
                **urllib.parse.parse_qs(parsed_url.query),
                'cTag': video_data['.ctag'],
                'action': 'Access',
                'part': 'index',
            }, doseq=True)))

        # Web player adds more params to the format URLs but we still get all formats without them
        formats = self._extract_mpd_formats(
            base_media_url, video_id, mpd_id='dash', query={'format': 'dash'}, fatal=False)
        for hls_type in ('hls', 'hls-vnext'):
            formats.extend(self._extract_m3u8_formats(
                base_media_url, video_id, 'mp4', m3u8_id=hls_type,
                query={'format': hls_type}, fatal=False, quality=-2))

        if video_url := traverse_obj(video_data, ('downloadUrl', {url_or_none})):
            formats.append({
                'url': video_url,
                'ext': determine_ext(video_data.get('extension') or video_data.get('name')),
                'quality': 1,
                'format_id': 'source',
                'filesize': int_or_none(video_data.get('size')),
                'vcodec': 'none' if video_data.get('isAudio') is True else None,
            })

        return {
            'id': video_id,
            'formats': formats,
            'title': video_data.get('title') or video_data.get('displayName'),
            'display_id': display_id,
            'uploader_id': video_data.get('authorId'),
            'duration': traverse_obj(video_data, (
                'MediaServiceFastMetadata', {json.loads}, 'media', 'duration', {lambda x: x / 10000000})),
            'thumbnail': url_or_none(video_data.get('thumbnailUrl')),
        }
