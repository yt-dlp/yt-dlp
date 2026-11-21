from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    parse_filesize,
    parse_qs,
    parse_resolution,
    str_or_none,
    update_url_query,
    url_basename,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import traverse_obj


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
        # share URL with password
        'url': 'https://zoom.us/rec/share/BfYDK9KwcqUVsp_szMpkywfiLfllnzdikJ_09vgiWFnbvHsZK4sbydbYCpQ_yFwY.YW8AHjTIrFV48zhK',
        'md5': '957699fc702ea07b8399803caeb8c66c',
        'info_dict': {
            'id': 'BfYDK9KwcqUVsp_szMpkywfiLfllnzdikJ_09vgiWFnbvHsZK4sbydbYCpQ_yFwY.YW8AHjTIrFV48zhK',
            'ext': 'mp4',
            'title': 'yt-dlp test meeting',
            'duration': 21,
        },
        'params': {
            'videopassword': 'yt-dlp-2026',
        },
    }, {
        # play URL with password
        'url': 'https://us02web.zoom.us/rec/play/x32Pf03n6zWUsEIQ00ocSanVsGL81WcRlG3RRtxyGyrhiBY4eIEHbc80D-3nG5FeK9tib6t4OVT7EFjh.IKIi0NuqvQZvNpzf',
        'md5': '957699fc702ea07b8399803caeb8c66c',
        'info_dict': {
            'id': 'x32Pf03n6zWUsEIQ00ocSanVsGL81WcRlG3RRtxyGyrhiBY4eIEHbc80D-3nG5FeK9tib6t4OVT7EFjh.IKIi0NuqvQZvNpzf',
            'ext': 'mp4',
            'title': 'yt-dlp test meeting',
            'duration': 21,
        },
        'params': {
            'videopassword': 'yt-dlp-2026',
        },
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
            'subtitles': 'mincount:2',
        },
    }, {
        # play URL without password
        'url': 'https://zoom.us/rec/play/PwINh_436YaRUJvmttj4sR0ChhoTkSCtSsmc1XdmlecrfT_YyzKpbAi2Ne0z-9eYqpvKEtB6qiuPhBeZ.TgTGV-F5AebxsiCh',
        'md5': 'a8ac4cb7b9a1940ed6207670a6682e26',
        'info_dict': {
            'id': 'PwINh_436YaRUJvmttj4sR0ChhoTkSCtSsmc1XdmlecrfT_YyzKpbAi2Ne0z-9eYqpvKEtB6qiuPhBeZ.TgTGV-F5AebxsiCh',
            'ext': 'mp4',
            'title': 'yt-dlp test meeting 2',
            'duration': 17,
        },
    }, {
        # recording URL spelling
        'url': 'https://zoom.us/recording/share/BfYDK9KwcqUVsp_szMpkywfiLfllnzdikJ_09vgiWFnbvHsZK4sbydbYCpQ_yFwY.YW8AHjTIrFV48zhK',
        'only_matching': True,
    }]

    def _get_page_data(self, webpage, video_id):
        return self._search_json(
            r'window\.__data__\s*=', webpage, 'data', video_id, transform_source=js_to_json)

    def _validate_password(self, base_url, video_id, endpoint_type, validation_id, action):
        password = self.get_param('videopassword')
        if not password:
            raise ExtractorError(
                'This video is protected by a passcode, use the --video-password option', expected=True)

        validation = self._download_json(
            f'{base_url}nws/recording/1.0/validate-{endpoint_type or "meeting"}-passwd', video_id,
            note='Validating passcode', errnote='Wrong passcode',
            data=urlencode_postdata({
                'id': validation_id,
                'passwd': password,
                'action': action or 'viewdetailpage',
            }))

        if not validation.get('status'):
            raise ExtractorError(validation.get('errorMessage') or 'Wrong passcode', expected=True)

    def _check_component_error(self, result):
        component_name = result.get('componentName')
        if component_name:
            message = result.get('message')
            if component_name == 'vanity-url-check' and not message:
                message = 'Recording requires email authentication to access'
            raise ExtractorError(message or f'Zoom returned: {component_name}', expected=True)

    def _real_extract(self, url):
        base_url, url_type, video_id = self._match_valid_url(url).group('base_url', 'type', 'id')
        is_share = url_type == 'share'
        start_params = traverse_obj(url, {'startTime': ({parse_qs}, 'startTime', -1)})
        share_data = {}

        webpage = self._download_webpage(url, video_id, note=f'Downloading {url_type} webpage')
        data = self._get_page_data(webpage, video_id)

        if is_share:
            share_data = data
            meeting_id = data.get('meetingId')

            if meeting_id:
                share_info = self._download_json(
                    f'{base_url}nws/recording/1.0/play/share-info/{meeting_id}', video_id,
                    note='Downloading share info JSON',
                    query={'originDomain': base_url.rstrip('/'), 'accessLevel': 'meeting'},
                    fatal=False) or {}

                result = share_info.get('result') or {}

                if result.get('componentName') == 'need-password':
                    self._validate_password(
                        base_url, video_id, result.get('useWhichPasswd'),
                        result.get('meetingId') or meeting_id, result.get('action'))

                    # Authenticated, re-fetch the share-info payload to get real media data
                    share_info = self._download_json(
                        f'{base_url}nws/recording/1.0/play/share-info/{meeting_id}', video_id,
                        note='Downloading share info JSON (authenticated)',
                        query={'originDomain': base_url.rstrip('/'), 'accessLevel': 'meeting'},
                        fatal=False) or {}
                    result = share_info.get('result') or {}

                share_data = result or share_data
                redirect_path = result.get('redirectUrl')

                if redirect_path:
                    redirect_url = urljoin(base_url, redirect_path)
                    parsed_url = self._match_valid_url(redirect_url)
                    if parsed_url:
                        url = update_url_query(redirect_url, start_params)
                        base_url, url_type = parsed_url.group('base_url', 'type')
                        # Do not overwrite video_id here, preserving the original share ID
                        webpage = self._download_webpage(url, video_id, note=f'Downloading {url_type} webpage')
                        data = self._get_page_data(webpage, video_id)
                    else:
                        self._check_component_error(result)

        file_id = data.get('fileId') or share_data.get('fileId')

        # When things go wrong, file_id can be empty string
        if not file_id:
            raise ExtractorError('Unable to extract file ID')

        query = start_params.copy()
        if is_share:
            query['continueMode'] = 'true'

        play_info_response = self._download_json(
            f'{base_url}nws/recording/1.0/play/info/{file_id}', video_id,
            query=query, note='Downloading play info JSON')

        # Detect the API-side password wall or unplayable component states
        play_result = traverse_obj(play_info_response, ('result', {dict})) or {}
        if play_result.get('componentName') == 'need-password':
            validation_id = (
                play_result.get('meetingId')
                or play_result.get('fileId')
                or data.get('meetingId')
                or data.get('fileId')
                or video_id)
            endpoint_type = play_result.get('useWhichPasswd') or data.get('useWhichPasswd')
            action = play_result.get('action') or data.get('action')

            self._validate_password(base_url, video_id, endpoint_type, validation_id, action)

            play_info_response = self._download_json(
                f'{base_url}nws/recording/1.0/play/info/{file_id}', video_id,
                query=query, note='Downloading play info JSON (authenticated)')
            play_result = traverse_obj(play_info_response, ('result', {dict})) or {}

        # Handle non-playable states by surfacing Zoom's human-readable message
        self._check_component_error(play_result)

        if play_info_response and play_info_response.get('errorMessage'):
            raise ExtractorError(play_info_response['errorMessage'], expected=True)

        data = play_result

        subtitles = {}
        for _type in ('transcript', 'cc', 'chapter'):
            if data.get(f'{_type}Url'):
                subtitles[_type] = [{
                    'url': urljoin(base_url, data[f'{_type}Url']),
                    'ext': 'vtt',
                }]

        formats = []

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


class ZoomClipsIE(InfoExtractor):
    IE_NAME = 'zoom:clips'
    _VALID_URL = r'https?://(?:[^.]+\.)?zoom\.us/clips/share/(?P<id>[\w.-]+)'
    _TESTS = [{
        'url': 'https://zoom.us/clips/share/6YEG4i_qS0eiT7UH9zPeYw',
        'md5': '1431f67d2e74a3ff3fec4feadb984777',
        'info_dict': {
            'id': '6YEG4i_qS0eiT7UH9zPeYw',
            'ext': 'mp4',
            'title': 'Test Clip',
            'uploader': 'Hans Müller',
            'duration': 1,
            'release_timestamp': 1781866637,
            'release_date': '20260619',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        clip_id = self._match_id(url)
        # The API response sets cloudfront cookies necessary for access to the m3u8 format
        result = self._download_json(
            f'https://zoomclips.zoom.us/nws/marvel/2.0/clips/share/{clip_id}',
            clip_id, note='Downloading share info JSON')['result']
        media_info = result['mediaInfo']

        return {
            'id': clip_id,
            **traverse_obj(media_info, {
                'title': ('mediaTopic', {str}),
                'uploader': ('ownerName', {str}),
                'release_timestamp': ('createdTime', {int_or_none(scale=1000)}),
                'duration': ('mediaDuration', {int_or_none}),
            }),
            'view_count': traverse_obj(result, ('statisticsInfo', 'count', {int_or_none})),
            'formats': [{
                'url': media_info['playUrl'],
                'protocol': 'm3u8_native',
                'ext': 'mp4',
            }],
        }
