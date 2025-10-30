from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    parse_filesize,
    parse_resolution,
    str_or_none,
    traverse_obj,
    update_url,
    url_basename,
    urlencode_postdata,
    urljoin,
)


class ZoomIE(InfoExtractor):
    IE_NAME = 'zoom'
    _VALID_URL = r'(?P<base_url>https?://(?:[^.]+\.)?zoom\.us/)rec(?:ording)?/(?P<type>play|share)/(?P<id>[\w.-]+)'
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
        'skip': 'This recording has expired',
    }, {
        # share URL
        'url': 'https://us02web.zoom.us/rec/share/hkUk5Zxcga0nkyNGhVCRfzkA2gX_mzgS3LpTxEEWJz9Y_QpIQ4mZFOUx7KZRZDQA.9LGQBdqmDAYgiZ_8',
        'md5': '90fdc7cfcaee5d52d1c817fc03c43c9b',
        'info_dict': {
            'id': 'hkUk5Zxcga0nkyNGhVCRfzkA2gX_mzgS3LpTxEEWJz9Y_QpIQ4mZFOUx7KZRZDQA.9LGQBdqmDAYgiZ_8',
            'ext': 'mp4',
            'title': 'Timea Andrea Lelik\'s Personal Meeting Room',
        },
        'skip': 'This recording has expired',
    }, {
        # view_with_share URL
        'url': 'https://cityofdetroit.zoom.us/rec/share/VjE-5kW3xmgbEYqR5KzRgZ1OFZvtMtiXk5HyRJo5kK4m5PYE6RF4rF_oiiO_9qaM.UTAg1MI7JSnF3ZjX',
        'md5': 'bdc7867a5934c151957fb81321b3c024',
        'info_dict': {
            'id': 'VjE-5kW3xmgbEYqR5KzRgZ1OFZvtMtiXk5HyRJo5kK4m5PYE6RF4rF_oiiO_9qaM.UTAg1MI7JSnF3ZjX',
            'ext': 'mp4',
            'title': 'February 2022 Detroit Revenue Estimating Conference',
            'duration': 7299,
            'formats': 'mincount:3',
        },
    }]

    def _get_page_data(self, webpage, video_id):
        return self._search_json(
            r'window\.__data__\s*=', webpage, 'data', video_id, transform_source=js_to_json)

    def _try_login(self, url, base_url, video_id, form):
        # This will most likely only work for password-protected meetings
        password = self.get_param('videopassword')
        if not password:
            raise ExtractorError(
                'This video is protected by a passcode, use the --video-password option', expected=True)

        is_meeting = form.get('useWhichPasswd') == 'meeting'
        validation = self._download_json(
            base_url + 'nws/recording/1.0/validate%s-passwd' % ('-meeting' if is_meeting else ''),
            video_id, 'Validating passcode', 'Wrong passcode', data=urlencode_postdata({
                'id': form[('meeting' if is_meeting else 'file') + '_id'],
                'passwd': password,
                'action': form.get('action'),
            }))

        if not validation.get('status'):
            raise ExtractorError(validation['errorMessage'], expected=True)

    def _get_real_webpage(self, url, base_url, video_id, url_type):
        webpage = self._download_webpage(url, video_id, note=f'Downloading {url_type} webpage')

        data = self._get_page_data(webpage, video_id)
        if data.get('componentName') != 'need-password':  # not password protected
            return webpage

        # Password-protected:
        self._try_login(url, base_url, video_id, form=data)
        # Return the new HTML document
        new_url = f"{base_url}rec/share/{data['meeting_id']}"
        return self._download_webpage(new_url, video_id, note=f'Re-downloading {url_type} webpage')

    def _get_share_redirect_url(self, url, base_url, video_id):
        """Converts a `/rec/share` url to the corresponding `/rec/play` url, performs login if necessary"""
        webpage = self._get_real_webpage(url, base_url, video_id, 'share')
        meeting_id = self._get_page_data(webpage, video_id)['meetingId']
        redirect_dict = self._download_json(
            f'{base_url}nws/recording/1.0/play/share-info/{meeting_id}',
            video_id, note='Downloading share info JSON')['result']
        redirect_path = redirect_dict.pop('redirectUrl')
        url = update_url(urljoin(base_url, redirect_path), query_update=redirect_dict)

        if redirect_dict.get('componentName') == 'need-password':
            # First login, then return redirection URL
            return self._get_share_redirect_url(url, base_url, video_id)

        return url

    def _real_extract(self, url):
        base_url, url_type, video_id = self._match_valid_url(url).group('base_url', 'type', 'id')

        if url_type == 'share':
            url = self._get_share_redirect_url(url, base_url, video_id)

        webpage = self._get_real_webpage(url, base_url, video_id, 'play')
        file_id = self._get_page_data(webpage, video_id)['fileId']
        if not file_id:
            # When things go wrong, file_id can be empty string
            raise ExtractorError('Unable to extract file ID')

        data = self._download_json(
            f'{base_url}nws/recording/1.0/play/info/{file_id}', video_id, query={
                'continueMode': 'true',  # Makes this return value include interpreter audio information
            },
            note='Downloading play info JSON')['result']
        subtitles = {}
        # XXX: Would be more appropriate to parse chapters separate from subtitles
        for _type in ('transcript', 'cc', 'chapter'):
            if data.get(f'{_type}Url'):
                subtitles[_type] = [{
                    'url': urljoin(base_url, data[f'{_type}Url']),
                    'ext': 'vtt',
                }]

        formats = []

        if data.get('interpreterAudioList'):
            for audio in data.get('interpreterAudioList'):
                formats.append({
                    'format_note': f'Intepreter: {audio["languageText"]}',
                    'url': audio['audioUrl'],
                    'format_id': f'interpreter-{ audio["icon"].lower()}',
                    'ext': 'm4a',
                    # There doesn't seem to be an explicit field for a standardized language code,
                    # sometimes the `language` field may be more accurate than `icon`
                    'language': audio['icon'].lower(),
                    'vcodec': 'none',
                })

        if data.get('viewMp4Url'):
            formats.append({
                'format_note': 'Camera stream',
                'url': data['viewMp4Url'],
                'width': int_or_none(traverse_obj(data, ('viewResolvtions', 0))),
                'height': int_or_none(traverse_obj(data, ('viewResolvtions', 1))),
                'format_id': 'view',
                'ext': 'mp4',
                'filesize_approx': parse_filesize(str_or_none(traverse_obj(data, ('recording', 'fileSizeInMB')))),
                'preference': 0,
            })

        if data.get('shareMp4Url'):
            formats.append({
                'format_note': 'Screen share stream',
                'url': data['shareMp4Url'],
                'width': int_or_none(traverse_obj(data, ('shareResolvtions', 0))),
                'height': int_or_none(traverse_obj(data, ('shareResolvtions', 1))),
                'format_id': 'share',
                'ext': 'mp4',
                'preference': -1,
            })

        view_with_share_url = data.get('viewMp4WithshareUrl')
        if view_with_share_url:
            formats.append({
                **parse_resolution(self._search_regex(
                    r'_(\d+x\d+)\.mp4', url_basename(view_with_share_url), 'resolution', default=None)),
                'format_note': 'Screen share with camera',
                'url': view_with_share_url,
                'format_id': 'view_with_share',
                'ext': 'mp4',
                'preference': 1,
            })

        return {
            'id': video_id,
            'title': str_or_none(traverse_obj(data, ('meet', 'topic'))),
            'duration': int_or_none(data.get('duration')),
            'subtitles': subtitles,
            'formats': formats,
            'http_headers': {
                'Referer': base_url,
            },
        }
