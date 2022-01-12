from __future__ import unicode_literals

import re
import base64
import json

from .common import InfoExtractor
from .adobepass import AdobePassIE
from .once import OnceIE
from ..compat import (
    compat_str,
    compat_urllib_parse_quote_plus
)
from ..utils import (
    determine_ext,
    dict_get,
    ExtractorError,
    int_or_none,
    unified_strdate,
    unified_timestamp,
)


class ESPNIE(OnceIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:
                                (?:
                                    (?:(?:\w+\.)+)?espn\.go|
                                    (?:www\.)?espn
                                )\.com/
                                (?:
                                    (?:
                                        video/(?:clip|iframe/twitter)|
                                    )
                                    (?:
                                        .*?\?.*?\bid=|
                                        /_/id/
                                    )|
                                    [^/]+/video/
                                )
                            )|
                            (?:www\.)espnfc\.(?:com|us)/(?:video/)?[^/]+/\d+/video/
                        )
                        (?P<id>\d+)
                    '''

    _TESTS = [{
        'url': 'http://espn.go.com/video/clip?id=10365079',
        'info_dict': {
            'id': '10365079',
            'ext': 'mp4',
            'title': '30 for 30 Shorts: Judging Jewell',
            'description': 'md5:39370c2e016cb4ecf498ffe75bef7f0f',
            'timestamp': 1390936111,
            'upload_date': '20140128',
            'duration': 1302,
            'thumbnail': 'md5:328b04abedca5cc2a55d76d613759de1',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://broadband.espn.go.com/video/clip?id=18910086',
        'info_dict': {
            'id': '18910086',
            'ext': 'mp4',
            'title': 'Kyrie spins around defender for two',
            'description': 'md5:2b0f5bae9616d26fba8808350f0d2b9b',
            'timestamp': 1489539155,
            'upload_date': '20170315',
        },
        'params': {
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'http://nonredline.sports.espn.go.com/video/clip?id=19744672',
        'only_matching': True,
    }, {
        'url': 'https://cdn.espn.go.com/video/clip/_/id/19771774',
        'only_matching': True,
    }, {
        'url': 'http://www.espn.com/video/clip?id=10365079',
        'only_matching': True,
    }, {
        'url': 'http://www.espn.com/video/clip/_/id/17989860',
        'only_matching': True,
    }, {
        'url': 'https://espn.go.com/video/iframe/twitter/?cms=espn&id=10365079',
        'only_matching': True,
    }, {
        'url': 'http://www.espnfc.us/video/espn-fc-tv/86/video/3319154/nashville-unveiled-as-the-newest-club-in-mls',
        'only_matching': True,
    }, {
        'url': 'http://www.espnfc.com/english-premier-league/23/video/3324163/premier-league-in-90-seconds-golden-tweets',
        'only_matching': True,
    }, {
        'url': 'http://www.espn.com/espnw/video/26066627/arkansas-gibson-completes-hr-cycle-four-innings',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        clip = self._download_json(
            'http://api-app.espn.com/v1/video/clips/%s' % video_id,
            video_id)['videos'][0]

        title = clip['headline']

        format_urls = set()
        formats = []

        def traverse_source(source, base_source_id=None):
            for source_id, source in source.items():
                if source_id == 'alert':
                    continue
                elif isinstance(source, compat_str):
                    extract_source(source, base_source_id)
                elif isinstance(source, dict):
                    traverse_source(
                        source,
                        '%s-%s' % (base_source_id, source_id)
                        if base_source_id else source_id)

        def extract_source(source_url, source_id=None):
            if source_url in format_urls:
                return
            format_urls.add(source_url)
            ext = determine_ext(source_url)
            if OnceIE.suitable(source_url):
                formats.extend(self._extract_once_formats(source_url))
            elif ext == 'smil':
                formats.extend(self._extract_smil_formats(
                    source_url, video_id, fatal=False))
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    source_url, video_id, f4m_id=source_id, fatal=False))
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    source_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id=source_id, fatal=False))
            else:
                f = {
                    'url': source_url,
                    'format_id': source_id,
                }
                mobj = re.search(r'(\d+)p(\d+)_(\d+)k\.', source_url)
                if mobj:
                    f.update({
                        'height': int(mobj.group(1)),
                        'fps': int(mobj.group(2)),
                        'tbr': int(mobj.group(3)),
                    })
                if source_id == 'mezzanine':
                    f['quality'] = 1
                formats.append(f)

        links = clip.get('links', {})
        traverse_source(links.get('source', {}))
        traverse_source(links.get('mobile', {}))
        self._sort_formats(formats)

        description = clip.get('caption') or clip.get('description')
        thumbnail = clip.get('thumbnail')
        duration = int_or_none(clip.get('duration'))
        timestamp = unified_timestamp(clip.get('originalPublishDate'))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'duration': duration,
            'formats': formats,
        }


class ESPNArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:espn\.go|(?:www\.)?espn)\.com/(?:[^/]+/)*(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'http://espn.go.com/nba/recap?gameId=400793786',
        'only_matching': True,
    }, {
        'url': 'http://espn.go.com/blog/golden-state-warriors/post/_/id/593/how-warriors-rapidly-regained-a-winning-edge',
        'only_matching': True,
    }, {
        'url': 'http://espn.go.com/sports/endurance/story/_/id/12893522/dzhokhar-tsarnaev-sentenced-role-boston-marathon-bombings',
        'only_matching': True,
    }, {
        'url': 'http://espn.go.com/nba/playoffs/2015/story/_/id/12887571/john-wall-washington-wizards-no-swelling-left-hand-wrist-game-5-return',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if (ESPNIE.suitable(url) or WatchESPNIE.suitable(url)) else super(ESPNArticleIE, cls).suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_id = self._search_regex(
            r'class=(["\']).*?video-play-button.*?\1[^>]+data-id=["\'](?P<id>\d+)',
            webpage, 'video id', group='id')

        return self.url_result(
            'http://espn.go.com/video/clip?id=%s' % video_id, ESPNIE.ie_key())


class FiveThirtyEightIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fivethirtyeight\.com/features/(?P<id>[^/?#]+)'
    _TEST = {
        'url': 'http://fivethirtyeight.com/features/how-the-6-8-raiders-can-still-make-the-playoffs/',
        'info_dict': {
            'id': '56032156',
            'ext': 'flv',
            'title': 'FiveThirtyEight: The Raiders can still make the playoffs',
            'description': 'Neil Paine breaks down the simplest scenario that will put the Raiders into the playoffs at 8-8.',
        },
        'params': {
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        embed_url = self._search_regex(
            r'<iframe[^>]+src=["\'](https?://fivethirtyeight\.abcnews\.go\.com/video/embed/\d+/\d+)',
            webpage, 'embed url')

        return self.url_result(embed_url, 'AbcNewsVideo')


class ESPNCricInfoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?espncricinfo\.com/video/[^#$&?/]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.espncricinfo.com/video/finch-chasing-comes-with-risks-despite-world-cup-trend-1289135',
        'info_dict': {
            'id': '1289135',
            'ext': 'mp4',
            'title': 'Finch: Chasing comes with \'risks\' despite World Cup trend',
            'description': 'md5:ea32373303e25efbb146efdfc8a37829',
            'upload_date': '20211113',
            'duration': 96,
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        data_json = self._download_json(f'https://hs-consumer-api.espncricinfo.com/v1/pages/video/video-details?videoId={id}', id)['video']
        formats, subtitles = [], {}
        for item in data_json.get('playbacks') or []:
            if item.get('type') == 'HLS' and item.get('url'):
                m3u8_frmts, m3u8_subs = self._extract_m3u8_formats_and_subtitles(item['url'], id)
                formats.extend(m3u8_frmts)
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            elif item.get('type') == 'AUDIO' and item.get('url'):
                formats.append({
                    'url': item['url'],
                    'vcodec': 'none',
                })
        self._sort_formats(formats)
        return {
            'id': id,
            'title': data_json.get('title'),
            'description': data_json.get('summary'),
            'upload_date': unified_strdate(dict_get(data_json, ('publishedAt', 'recordedAt'))),
            'duration': data_json.get('duration'),
            'formats': formats,
            'subtitles': subtitles,
        }


class WatchESPNIE(AdobePassIE):
    _VALID_URL = r'https://www.espn.com/watch/player/_/id/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
    _TESTS = [{
        'url': 'https://www.espn.com/watch/player/_/id/6eee6cb0-1795-49e3-84ea-766b517e0309',
        'info_dict': {
            'id': '6eee6cb0-1795-49e3-84ea-766b517e0309',
            'ext': 'mp4',
            'title': 'Miami vs. #2 Duke',
            'thumbnail': 'https://artwork.api.espn.com/artwork/collections/media/6eee6cb0-1795-49e3-84ea-766b517e0309/default?width=640&apikey=1ngjw23osgcis1i1vbj96lmfqs',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.espn.com/watch/player/_/id/bd1f3d12-0654-47d9-852e-71b85ea695c7',
        'info_dict': {
            'id': 'bd1f3d12-0654-47d9-852e-71b85ea695c7',
            'ext': 'mp4',
            'title': 'Tue, 1/11 - ESPN FC',
            'thumbnail': 'https://s.secure.espncdn.com/stitcher/artwork/collections/media/bd1f3d12-0654-47d9-852e-71b85ea695c7/16x9.jpg?timestamp=202201112217&showBadge=true&cb=12&package=ESPN_PLUS',
        },
        'params': {
            'skip_download': True,
        },
    }]

    _API_KEY = 'ZXNwbiZicm93c2VyJjEuMC4w.ptUt7QxsteaRruuPmGZFaJByOoqKvDP2a5YkInHrc7c'

    def _call_bamgrid_api(self, path, video_id, data=None, headers={}):
        if 'authorization' not in headers:
            headers['authorization'] = 'Bearer ' + self._API_KEY
        return self._download_json(
            'https://espn.api.edge.bamgrid.com/' + path,
            video_id, data=data, headers=headers)

    def _payload_to_string_data(self, payload):
        return '&'.join(['%s=%s' % (key, compat_urllib_parse_quote_plus(payload[key])) for key in payload]).encode('utf-8')

    def _payload_to_json_data(self, payload):
        return json.dumps(payload).encode('utf-8')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(
            'https://watch-cdn.product.api.espn.com/api/product/v3/watchespn/web/playback/event?id=%s' % video_id, video_id)['playbackState']
        title = video_data['name']

        # ESPN+ subscription required, through cookies
        if video_data.get('sourceId') == 'ESPN_DTC':
            cookies = self._get_cookies(url)
            try:
                id_token = cookies['ESPN-ONESITE.WEB-PROD.token'].value.split('|')[1]
            except KeyError:
                raise ExtractorError('This is an ESPN+ video, which requires cookies. Use --cookies or --cookiesfrombrowser')

            assertion = self._call_bamgrid_api(
                'devices',
                video_id,
                data=self._payload_to_json_data({
                    'deviceFamily': 'android',
                    'applicationRuntime': 'android',
                    'deviceProfile': 'tv',
                    'attributes': {},
                }),
                headers={'content-type': 'application/json; charset=UTF-8'}
            )['assertion']

            token = self._call_bamgrid_api(
                'token',
                video_id,
                data=self._payload_to_string_data({
                    'subject_token': assertion,
                    'subject_token_type': 'urn:bamtech:params:oauth:token-type:device',
                    'platform': 'android',
                    'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange'})
            )['access_token']

            assertion = self._call_bamgrid_api(
                'accounts/grant',
                video_id,
                data=self._payload_to_json_data({'id_token': id_token}),
                headers={
                    'authorization': token,
                    'content-type': 'application/json; charset=UTF-8'}
            )['assertion']

            token = self._call_bamgrid_api(
                'token',
                video_id,
                data=self._payload_to_string_data({
                    'subject_token': assertion,
                    'subject_token_type': 'urn:bamtech:params:oauth:token-type:account',
                    'platform': 'android',
                    'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange'})
            )['access_token']

            playback = self._download_json(
                video_data['videoHref'].format(scenario='browser~ssai'),
                video_id,
                headers={
                    'accept': 'application/vnd.media-service+json; version=5',
                    'authorization': token}
            )

            m3u8_url, m3u8_headers = playback['stream']['complete'][0]['url'], {'authorization': token}

        # TV Provider required
        else:
            resource = self._get_mvpd_resource('ESPN', title, video_id, None)
            auth = self._extract_mvpd_auth(url, video_id, 'ESPN', resource).encode('utf-8')

            asset = self._download_json(
                'https://watch.auth.api.espn.com/video/auth/media/%s/asset?apikey=uiqlbgzdwuru14v627vdusswb' % video_id,
                video_id, data=(
                    'adobeToken=%s&drmSupport=HLS' % compat_urllib_parse_quote_plus(base64.b64encode(auth))).encode())
            m3u8_url, m3u8_headers = asset['stream'], {}

        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls', headers=m3u8_headers)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'http_headers': m3u8_headers,
            'thumbnail': video_data.get('posterHref')
        }
