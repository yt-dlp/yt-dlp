import json

from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj, try_call, url_or_none


class KanopyIE(InfoExtractor):
    _API_BASE_URL = 'https://www.kanopy.com/kapi/'
    _NETRC_MACHINE = 'kanopy'
    _VALID_URL = r'https?://(?:www\.)?kanopy.com/(?P<lang>\w{2})/(?P<institution>.*?)/watch/video/(?P<id>[0-9]+)'
    _TESTS = [
        {
            'url': 'https://www.kanopy.com/en/pleasantvalley/watch/video/114603',
            'info_dict': {
                'id': '114603',
                'ext': 'mp4',
                'title': 'The Blue Kite',
                'description': 'md5:6163af52ae92627ae7c58906991d3792',
            },
        },
    ]
    _LOGIN_REQUIRED = True
    _ACCESS_TOKEN = None
    _USER_ID = None

    headers = {
        'content-type': 'application/json',
        'x-version': 'web/prod/4.3.0/2024-01-08-15-13-05',
    }

    def _match_membership(self, memberships, matcher):
        return next((d for d in memberships if d['subdomain'] == matcher), None)

    def _real_initialize(self):
        if not self._ACCESS_TOKEN and not self._USER_ID:
            self.raise_login_required()

    def _perform_login(self, username, password):
        self.report_login()
        try:
            access_json = self._download_json(
                self._API_BASE_URL + 'login',
                None,
                'Logging in to site using credentials',
                'Unable to log in',
                fatal=False,
                headers=self.headers,
                data=json.dumps(
                    {
                        'credentialType': 'email',
                        'emailUser': {'email': username, 'password': password},
                    }
                ).encode(),
            )
            self._ACCESS_TOKEN = try_call(lambda: access_json['jwt'])
            if self._ACCESS_TOKEN is None:
                self.report_warning('Failed to get Access token')
            else:
                self.headers.update({'Authorization': 'Bearer %s' % self._ACCESS_TOKEN})
                self._USER_ID = try_call(lambda: access_json['userId'])
        except ExtractorError as e:
            self.report_warning(e)

    def _real_extract(self, url):
        lang, institution, video_id = self._match_valid_url(url).groups()

        memberships = traverse_obj(
            self._download_json(
                self._API_BASE_URL + f'memberships?userId={self._USER_ID}',
                None,
                headers=self.headers,
            ),
            ('list'),
            list,
        )

        domain_id = try_call(
            lambda: self._match_membership(memberships, institution)['domainId']
        )
        if not domain_id:
            raise ExtractorError(f'Could not match {institution} to a membership')

        video_info = self._download_json(
            self._API_BASE_URL + f'videos/{video_id}?domainId={domain_id}',
            video_id,
            headers=self.headers,
        )

        streams = self._download_json(
            self._API_BASE_URL + 'plays',
            video_id,
            headers=self.headers,
            data=json.dumps(
                {
                    'domainId': domain_id,
                    'userId': self._USER_ID,
                    'videoId': video_id,
                }
            ).encode(),
        )

        formats, subtitles = [], {}
        for manifest in traverse_obj(
            streams, ('manifests', lambda _, v: url_or_none(v['url']))
        ):
            manifest_type = manifest.get('manifestType')
            if manifest_type == 'hls':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    manifest['url'], video_id, m3u8_id='hls', fatal=False
                )
            elif manifest_type == 'dash':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    manifest['url'], video_id, mpd_id='dash', fatal=False
                )
            else:
                self.report_warning(f'Unsupported manifest type: {manifest_type!r}')
                continue
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'title': video_info['video']['title'],
            'description': video_info['video']['descriptionHtml'],
            'formats': formats,
            'subtitles': subtitles,
        }
