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
        },
    }]

    def _get_page_data(self, webpage, video_id):
        return self._search_json(
            r'window\.__data__\s*=', webpage, 'data', video_id,
            transform_source=js_to_json, default={},
        )

    def _get_real_webpage(self, url, base_url, video_id, url_type):
        webpage = self._download_webpage(url, video_id, note=f'Downloading {url_type} webpage')
        data = self._get_page_data(webpage, video_id)

        requires_password = (
            data.get('componentName') == 'need-password'
            or self._search_regex(r'<input[^>]+type=(["\'])password\1', webpage, 'password input', default=None)
            or 'id="password_form"' in webpage
            or (self.get_param('videopassword') and any(x in webpage.lower() for x in ('password', 'passcode')))
        )

        if not requires_password:
            return webpage

        password = self.get_param('videopassword')
        if not password:
            raise ExtractorError(
                'This video is protected by a passcode, use the --video-password option', expected=True,
            )

        validation_id = data.get('meetingId') or data.get('fileId')
        if not validation_id:
            try:
                form = self._form_hidden_inputs('password_form', webpage)
                validation_id = form.get('meetId') or form.get('fileId')
            except ExtractorError:
                pass

        if not validation_id:
            validation_id = self._search_regex(
                r'(?:name|id)=["\'](?:meetId|fileId)["\'][^>]+value=["\']([^"\']+)["\']',
                webpage, 'validation id', default=video_id)

        is_meeting = data.get('accessLevel') == 'meeting' or 'meeting' in url

        val_url = f"{base_url}nws/recording/1.0/validate-{'meeting' if is_meeting else 'passwd'}-passwd"
        validation = self._download_json(
            val_url,
            video_id,
            note='Validating passcode',
            errnote=False,
            data=urlencode_postdata(
                {
                    'id': validation_id,
                    'passwd': password,
                    'action': data.get('action', 'viewdetailpage'),
                },
            ),
            fatal=False,
        )

        # Fallback to legacy validation if new one fails
        if not validation or not validation.get('status'):
            legacy_val_url = base_url + 'rec/validate%s_passwd' % ('_meet' if is_meeting else '')
            validation = self._download_json(
                legacy_val_url,
                video_id,
                'Validating passcode (legacy fallback)',
                'Wrong passcode',
                data=urlencode_postdata(
                    {
                        'id': validation_id,
                        'passwd': password,
                        'action': 'viewdetailpage',
                    },
                ),
            )

        if not validation.get('status'):
            raise ExtractorError(validation.get('errorMessage', 'Wrong passcode'), expected=True)
        return self._download_webpage(url, video_id, note=f'Re-downloading {url_type} webpage')

    def _real_extract(self, url):
        base_url, url_type, video_id = self._match_valid_url(url).group('base_url', 'type', 'id')
        start_params = traverse_obj(url, {'startTime': ({parse_qs}, 'startTime', -1)})
        query = {}
        share_data = {}

        if url_type == 'share':
            webpage = self._get_real_webpage(url, base_url, video_id, 'share')
            data = self._get_page_data(webpage, video_id)
            share_data = data
            meeting_id = data.get('meetingId')

            if meeting_id:
                share_info = self._download_json(
                    f'{base_url}nws/recording/1.0/play/share-info/{meeting_id}',
                    video_id,
                    note='Downloading share info JSON',
                    query={'originDomain': base_url.strip('/'), 'accessLevel': 'meeting'},
                    fatal=False,
                ) or {}

                redirect_path = share_info.get('result', {}).get('redirectUrl')
                if redirect_path:
                    url = update_url_query(urljoin(base_url, redirect_path), start_params)
                    base_url, url_type, _ = self._match_valid_url(url).group('base_url', 'type', 'id')

        webpage = self._get_real_webpage(url, base_url, video_id, url_type)
        data = self._get_page_data(webpage, video_id)

        file_id = data.get('fileId') or share_data.get('fileId')

        if not file_id:
            # When things go wrong, file_id can be empty string
            raise ExtractorError('Unable to extract file ID')

        query.update(
            {
                'accessLevel': data.get('accessLevel', share_data.get('accessLevel', 'meeting')),
                'canPlayFromShare': 'true',
                'from': 'share_recording_detail',
                'continueMode': 'true',
                'componentName': 'rec-play',
                'originRequestUrl': url,
                'originDomain': base_url.strip('/'),
            },
        )
        query.update(start_params)

        play_info_response = self._download_json(
            f'{base_url}nws/recording/1.0/play/info/{file_id}',
            video_id,
            query=query,
            note='Downloading play info JSON',
            expected_status=(200, 400, 401, 403, 404),
        )

        data = share_data.copy()
        data.update(data)
        if play_info_response and play_info_response.get('result'):
            data.update(play_info_response['result'])
        elif play_info_response and play_info_response.get('errorMessage'):
            raise ExtractorError(play_info_response['errorMessage'], expected=True)

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

        if not formats:
            raise ExtractorError('No video formats found.', expected=True)

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
