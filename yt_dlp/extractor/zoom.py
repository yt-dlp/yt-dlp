from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    js_to_json,
    parse_filesize,
    traverse_obj,
    urlencode_postdata,
    urljoin,
)


class ZoomIE(InfoExtractor):
    IE_NAME = 'zoom'
    _VALID_URL = r'(?P<base_url>https?://(?:[^.]+\.)?zoom.us/)rec(?:ording)?/(?P<type>play|share)/(?P<id>[A-Za-z0-9_.-]+)'
    _TESTS = [{
        'url': 'https://economist.zoom.us/rec/play/dUk_CNBETmZ5VA2BwEl-jjakPpJ3M1pcfVYAPRsoIbEByGsLjUZtaa4yCATQuOL3der8BlTwxQePl_j0.EImBkXzTIaPvdZO5',
        'md5': 'ab445e8c911fddc4f9adc842c2c5d434',
        'info_dict': {
            'id': 'dUk_CNBETmZ5VA2BwEl-jjakPpJ3M1pcfVYAPRsoIbEByGsLjUZtaa4yCATQuOL3der8BlTwxQePl_j0.EImBkXzTIaPvdZO5',
            'ext': 'mp4',
            'title': 'China\'s "two sessions" and the new five-year plan',
        },
        'skip': 'Recording requires email authentication to access',
    }, {
        # play URL
        'url': 'https://ffgolf.zoom.us/rec/play/qhEhXbrxq1Zoucx8CMtHzq1Z_2YZRPVCqWK_K-2FkEGRsSLDeOX8Tu4P6jtjZcRry8QhIbvKZdtr4UNo.QcPn2debFskI9whJ',
        'md5': '2c4b1c4e5213ebf9db293e88d9385bee',
        'info_dict': {
            'id': 'qhEhXbrxq1Zoucx8CMtHzq1Z_2YZRPVCqWK_K-2FkEGRsSLDeOX8Tu4P6jtjZcRry8QhIbvKZdtr4UNo.QcPn2debFskI9whJ',
            'ext': 'mp4',
            'title': 'Prépa AF2023 - Séance 5 du 11 avril - R20/VM/GO',
        },
    }, {
        # share URL
        'url': 'https://us02web.zoom.us/rec/share/hkUk5Zxcga0nkyNGhVCRfzkA2gX_mzgS3LpTxEEWJz9Y_QpIQ4mZFOUx7KZRZDQA.9LGQBdqmDAYgiZ_8',
        'md5': '90fdc7cfcaee5d52d1c817fc03c43c9b',
        'info_dict': {
            'id': 'hkUk5Zxcga0nkyNGhVCRfzkA2gX_mzgS3LpTxEEWJz9Y_QpIQ4mZFOUx7KZRZDQA.9LGQBdqmDAYgiZ_8',
            'ext': 'mp4',
            'title': 'Timea Andrea Lelik\'s Personal Meeting Room',
        },
    }]

    def _get_page_data(self, webpage, video_id):
        return self._search_json(
            r'window\.__data__\s*=', webpage, 'data', video_id, transform_source=js_to_json)

    def _get_real_webpage(self, url, base_url, video_id, url_type):
        webpage = self._download_webpage(url, video_id, note=f'Downloading {url_type} webpage')
        try:
            form = self._form_hidden_inputs('password_form', webpage)
        except ExtractorError:
            return webpage

        password = self.get_param('videopassword')
        if not password:
            raise ExtractorError(
                'This video is protected by a passcode, use the --video-password option', expected=True)
        is_meeting = form.get('useWhichPasswd') == 'meeting'
        validation = self._download_json(
            base_url + 'rec/validate%s_passwd' % ('_meet' if is_meeting else ''),
            video_id, 'Validating passcode', 'Wrong passcode', data=urlencode_postdata({
                'id': form[('meet' if is_meeting else 'file') + 'Id'],
                'passwd': password,
                'action': form.get('action'),
            }))
        if not validation.get('status'):
            raise ExtractorError(validation['errorMessage'], expected=True)
        return self._download_webpage(url, video_id, note=f'Re-downloading {url_type} webpage')

    def _real_extract(self, url):
        base_url, url_type, video_id = self._match_valid_url(url).group('base_url', 'type', 'id')

        if url_type == 'share':
            webpage = self._get_real_webpage(url, base_url, video_id, 'share')
            meeting_id = self._get_page_data(webpage, video_id)['meetingId']
            redirect_path = self._download_json(
                f'{base_url}nws/recording/1.0/play/share-info/{meeting_id}',
                video_id, note='Downloading share info JSON')['result']['redirectUrl']
            url = urljoin(base_url, redirect_path)

        webpage = self._get_real_webpage(url, base_url, video_id, 'play')
        file_id = self._get_page_data(webpage, video_id)['fileId']
        if not file_id:
            # When things go wrong, file_id can be empty string
            raise ExtractorError('Unable to extract file ID')

        data = self._download_json(
            f'{base_url}nws/recording/1.0/play/info/{file_id}', video_id,
            note='Downloading play info JSON')['result']

        subtitles = {}
        for _type in ('transcript', 'cc', 'chapter'):
            if data.get('%sUrl' % _type):
                subtitles[_type] = [{
                    'url': urljoin(base_url, data['%sUrl' % _type]),
                    'ext': 'vtt',
                }]

        formats = []

        if data.get('viewMp4Url'):
            formats.append({
                'format_note': 'Camera stream',
                'url': str_or_none(data.get('viewMp4Url')),
                'width': int_or_none(traverse_obj(data, ('viewResolvtions', 0))),
                'height': int_or_none(traverse_obj(data, ('viewResolvtions', 1))),
                'format_id': str_or_none(traverse_obj(data, ('recording', 'id'))),
                'ext': 'mp4',
                'filesize_approx': parse_filesize(str_or_none(traverse_obj(data, ('recording', 'fileSizeInMB')))),
                'preference': 0
            })

        if data.get('shareMp4Url'):
            formats.append({
                'format_note': 'Screen share stream',
                'url': str_or_none(data.get('shareMp4Url')),
                'width': int_or_none(traverse_obj(data, ('shareResolvtions', 0))),
                'height': int_or_none(traverse_obj(data, ('shareResolvtions', 1))),
                'format_id': str_or_none(traverse_obj(data, ('shareVideo', 'id'))),
                'ext': 'mp4',
                'preference': -1
            })

        return {
            'id': video_id,
            'title': str_or_none(traverse_obj(data, ('meet', 'topic'))),
            'subtitles': subtitles,
            'formats': formats,
            'http_headers': {
                'Referer': base_url,
            },
        }
