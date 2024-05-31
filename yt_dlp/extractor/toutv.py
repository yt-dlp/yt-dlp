import json

from .radiocanada import RadioCanadaIE
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    merge_dicts,
)


class TouTvIE(RadioCanadaIE):  # XXX: Do not subclass from concrete IE
    _NETRC_MACHINE = 'toutv'
    IE_NAME = 'tou.tv'
    _VALID_URL = r'https?://ici\.tou\.tv/(?P<id>[a-zA-Z0-9_-]+(?:/S[0-9]+[EC][0-9]+)?)'

    _TESTS = [{
        'url': 'http://ici.tou.tv/garfield-tout-court/S2015E17',
        'info_dict': {
            'id': '122017',
            'ext': 'mp4',
            'title': 'Saison 2015 Épisode 17',
            'description': 'La photo de famille 2',
            'upload_date': '20100717',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': '404 Not Found',
    }, {
        'url': 'http://ici.tou.tv/hackers',
        'only_matching': True,
    }, {
        'url': 'https://ici.tou.tv/l-age-adulte/S01C501',
        'only_matching': True,
    }]
    _CLIENT_KEY = '90505c8d-9c34-4f34-8da1-3a85bdc6d4f4'

    def _perform_login(self, username, password):
        try:
            self._access_token = self._download_json(
                'https://services.radio-canada.ca/toutv/profiling/accounts/login',
                None, 'Logging in', data=json.dumps({
                    'ClientId': self._CLIENT_KEY,
                    'ClientSecret': '34026772-244b-49b6-8b06-317b30ac9a20',
                    'Email': username,
                    'Password': password,
                    'Scope': 'id.write media-validation.read',
                }).encode(), headers={
                    'Authorization': 'client-key ' + self._CLIENT_KEY,
                    'Content-Type': 'application/json;charset=utf-8',
                })['access_token']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                error = self._parse_json(e.cause.response.read().decode(), None)['Message']
                raise ExtractorError(error, expected=True)
            raise
        self._claims = self._call_api('validation/v2/getClaims')['claims']

    def _real_extract(self, url):
        path = self._match_id(url)
        metadata = self._download_json(
            'https://services.radio-canada.ca/toutv/presentation/%s' % path, path, query={
                'client_key': self._CLIENT_KEY,
                'device': 'web',
                'version': 4,
            })
        # IsDrm does not necessarily mean the video is DRM protected (see
        # https://github.com/ytdl-org/youtube-dl/issues/13994).
        if not self.get_param('allow_unplayable_formats') and metadata.get('IsDrm'):
            self.report_warning('This video is probably DRM protected.', path)
        video_id = metadata['IdMedia']
        details = metadata['Details']

        return merge_dicts({
            'id': video_id,
            'title': details.get('OriginalTitle'),
            'description': details.get('Description'),
            'thumbnail': details.get('ImageUrl'),
            'duration': int_or_none(details.get('LengthInSeconds')),
            'series': metadata.get('ProgramTitle'),
            'season_number': int_or_none(metadata.get('SeasonNumber')),
            'season': metadata.get('SeasonTitle'),
            'episode_number': int_or_none(metadata.get('EpisodeNumber')),
            'episode': metadata.get('EpisodeTitle'),
        }, self._extract_info(metadata.get('AppCode', 'toutv'), video_id))
