# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    urlencode_postdata,
)


class RoosterTeethIE(InfoExtractor):
    _VALID_URL = r'https?://(?:.+?\.)?roosterteeth\.com/(?:episode|watch)/(?P<id>[^/?#&]+)'
    _NETRC_MACHINE = 'roosterteeth'
    _TESTS = [{
        'url': 'http://roosterteeth.com/episode/million-dollars-but-season-2-million-dollars-but-the-game-announcement',
        'md5': 'e2bd7764732d785ef797700a2489f212',
        'info_dict': {
            'id': '9156',
            'display_id': 'million-dollars-but-season-2-million-dollars-but-the-game-announcement',
            'ext': 'mp4',
            'title': 'Million Dollars, But... The Game Announcement',
            'description': 'md5:168a54b40e228e79f4ddb141e89fe4f5',
            'thumbnail': r're:^https?://.*\.png$',
            'series': 'Million Dollars, But...',
            'episode': 'Million Dollars, But... The Game Announcement',
        },
    }, {
        'url': 'https://roosterteeth.com/watch/rwby-bonus-25',
        'md5': 'fe8d9d976b272c18a24fe7f1f5830084',
        'info_dict': {
            'id': '31',
            'display_id': 'rwby-bonus-25',
            'title': 'Volume 2, World of Remnant 3',
            'description': 'md5:8d58d3270292ea11da00ea712bbfb009',
            'episode': 'Volume 2, World of Remnant 3',
            'channel_id': 'fab60c1c-29cb-43bc-9383-5c3538d9e246',
            'thumbnail': r're:^https?://.*\.(png|jpe?g)$',
            'ext': 'mp4',
        },
    }, {
        'url': 'http://achievementhunter.roosterteeth.com/episode/off-topic-the-achievement-hunter-podcast-2016-i-didn-t-think-it-would-pass-31',
        'only_matching': True,
    }, {
        'url': 'http://funhaus.roosterteeth.com/episode/funhaus-shorts-2016-austin-sucks-funhaus-shorts',
        'only_matching': True,
    }, {
        'url': 'http://screwattack.roosterteeth.com/episode/death-battle-season-3-mewtwo-vs-shadow',
        'only_matching': True,
    }, {
        'url': 'http://theknow.roosterteeth.com/episode/the-know-game-news-season-1-boring-steam-sales-are-better',
        'only_matching': True,
    }, {
        # only available for FIRST members
        'url': 'http://roosterteeth.com/episode/rt-docs-the-world-s-greatest-head-massage-the-world-s-greatest-head-massage-an-asmr-journey-part-one',
        'only_matching': True,
    }, {
        'url': 'https://roosterteeth.com/watch/million-dollars-but-season-2-million-dollars-but-the-game-announcement',
        'only_matching': True,
    }]
    _EPISODE_BASE_URL = 'https://svod-be.roosterteeth.com/api/v1/watch/'

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return

        try:
            self._download_json(
                'https://auth.roosterteeth.com/oauth/token',
                None, 'Logging in', data=urlencode_postdata({
                    'client_id': '4338d2b4bdc8db1239360f28e72f0d9ddb1fd01e7a38fbb07b4b1f4ba4564cc5',
                    'grant_type': 'password',
                    'username': username,
                    'password': password,
                }))
        except ExtractorError as e:
            msg = 'Unable to login'
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                resp = self._parse_json(e.cause.read().decode(), None, fatal=False)
                if resp:
                    error = resp.get('extra_info') or resp.get('error_description') or resp.get('error')
                    if error:
                        msg += ': ' + error
            self.report_warning(msg)

    def _real_initialize(self):
        if self._get_cookies(self._EPISODE_BASE_URL).get('rt_access_token'):
            return
        self._login()

    def _real_extract(self, url):
        display_id = self._match_id(url)
        api_episode_url = self._EPISODE_BASE_URL + display_id

        try:
            video_data = self._download_json(
                api_episode_url + '/videos', display_id,
                'Downloading video JSON metadata')['data'][0]
            m3u8_url = video_data['attributes']['url']
            subtitle_m3u8_url = video_data['links']['download']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                if self._parse_json(e.cause.read().decode(), display_id).get('access') is False:
                    self.raise_login_required(
                        '%s is only available for FIRST members' % display_id)
            raise

        formats = self._extract_m3u8_formats(
            m3u8_url, display_id, 'mp4', 'm3u8_native', m3u8_id='hls')
        self._sort_formats(formats)

        episode = self._download_json(
            api_episode_url, display_id,
            'Downloading episode JSON metadata')['data'][0]
        attributes = episode['attributes']
        title = attributes.get('title') or attributes['display_title']
        video_id = compat_str(episode['id'])

        thumbnails = []
        for image in episode.get('included', {}).get('images', []):
            if image.get('type') in ('episode_image', 'bonus_feature_image'):
                img_attributes = image.get('attributes') or {}
                for k in ('thumb', 'small', 'medium', 'large'):
                    img_url = img_attributes.get(k)
                    if img_url:
                        thumbnails.append({
                            'id': k,
                            'url': img_url,
                        })

        subtitles = {}
        res = self._download_webpage_handle(
            subtitle_m3u8_url, display_id,
            'Downloading m3u8 information',
            'Failed to download m3u8 information',
            fatal=True, data=None, headers={}, query={})
        if res is not False:
            subtitle_m3u8_doc, _ = res
            for line in subtitle_m3u8_doc.split('\n'):
                if 'EXT-X-MEDIA:TYPE=SUBTITLES' in line:
                    parts = line.split(',')
                    for part in parts:
                        if 'LANGUAGE' in part:
                            lang = part[part.index('=') + 2:-1]
                        elif 'URI' in part:
                            uri = part[part.index('=') + 2:-1]
                    res = self._download_webpage_handle(
                        uri, display_id,
                        'Downloading m3u8 information',
                        'Failed to download m3u8 information',
                        fatal=True, data=None, headers={}, query={})
                    doc, _ = res
                    for l in doc.split('\n'):
                        if not l.startswith('#'):
                            subtitles[lang] = [{'url': uri[:-uri[::-1].index('/')] + l}]
                            break

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': attributes.get('description') or attributes.get('caption'),
            'thumbnails': thumbnails,
            'series': attributes.get('show_title'),
            'season_number': int_or_none(attributes.get('season_number')),
            'season_id': attributes.get('season_id'),
            'episode': title,
            'episode_number': int_or_none(attributes.get('number')),
            'episode_id': str_or_none(episode.get('uuid')),
            'formats': formats,
            'channel_id': attributes.get('channel_id'),
            'duration': int_or_none(attributes.get('length')),
            'subtitles': subtitles
        }
