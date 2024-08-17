import base64
import json
import re
import urllib.parse

from .adobepass import AdobePassIE
from .common import InfoExtractor
from .once import OnceIE
from ..utils import (
    determine_ext,
    dict_get,
    int_or_none,
    traverse_obj,
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
            'thumbnail': r're:https://.+\.jpg',
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
    }, {
        'url': 'http://www.espn.com/watch/player?id=19141491',
        'only_matching': True,
    }, {
        'url': 'http://www.espn.com/watch/player?bucketId=257&id=19505875',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        clip = self._download_json(
            f'http://api-app.espn.com/v1/video/clips/{video_id}',
            video_id)['videos'][0]

        title = clip['headline']

        format_urls = set()
        formats = []

        def traverse_source(source, base_source_id=None):
            for src_id, src_item in source.items():
                if src_id == 'alert':
                    continue
                elif isinstance(src_item, str):
                    extract_source(src_item, base_source_id)
                elif isinstance(src_item, dict):
                    traverse_source(
                        src_item,
                        f'{base_source_id}-{src_id}'
                        if base_source_id else src_id)

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
        return False if (ESPNIE.suitable(url) or WatchESPNIE.suitable(url)) else super().suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_id = self._search_regex(
            r'class=(["\']).*?video-play-button.*?\1[^>]+data-id=["\'](?P<id>\d+)',
            webpage, 'video id', group='id')

        return self.url_result(
            f'http://espn.go.com/video/clip?id={video_id}', ESPNIE.ie_key())


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
    _VALID_URL = r'https?://(?:www\.)?espncricinfo\.com/(?:cricket-)?videos?/[^#$&?/]+-(?P<id>\d+)'
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
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.espncricinfo.com/cricket-videos/daryl-mitchell-mitchell-santner-is-one-of-the-best-white-ball-spinners-india-vs-new-zealand-1356225',
        'info_dict': {
            'id': '1356225',
            'ext': 'mp4',
            'description': '"Santner has done it for a long time for New Zealand - we\'re lucky to have him"',
            'upload_date': '20230128',
            'title': 'Mitchell: \'Santner is one of the best white-ball spinners at the moment\'',
            'duration': 87,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data_json = self._download_json(
            f'https://hs-consumer-api.espncricinfo.com/v1/pages/video/video-details?videoId={video_id}', video_id)['video']
        formats, subtitles = [], {}
        for item in data_json.get('playbacks') or []:
            if item.get('type') == 'HLS' and item.get('url'):
                m3u8_frmts, m3u8_subs = self._extract_m3u8_formats_and_subtitles(item['url'], video_id)
                formats.extend(m3u8_frmts)
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            elif item.get('type') == 'AUDIO' and item.get('url'):
                formats.append({
                    'url': item['url'],
                    'vcodec': 'none',
                })
        return {
            'id': video_id,
            'title': data_json.get('title'),
            'description': data_json.get('summary'),
            'upload_date': unified_strdate(dict_get(data_json, ('publishedAt', 'recordedAt'))),
            'duration': data_json.get('duration'),
            'formats': formats,
            'subtitles': subtitles,
        }


class WatchESPNIE(AdobePassIE):
    _VALID_URL = r'https?://(?:www\.)?espn\.com/(?:watch|espnplus)/player/_/id/(?P<id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
    _TESTS = [{
        'url': 'https://www.espn.com/watch/player/_/id/dbbc6b1d-c084-4b47-9878-5f13c56ce309',
        'info_dict': {
            'id': 'dbbc6b1d-c084-4b47-9878-5f13c56ce309',
            'ext': 'mp4',
            'title': 'Huddersfield vs. Burnley',
            'duration': 7500,
            'thumbnail': 'https://artwork.api.espn.com/artwork/collections/media/dbbc6b1d-c084-4b47-9878-5f13c56ce309/default?width=640&apikey=1ngjw23osgcis1i1vbj96lmfqs',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.espn.com/watch/player/_/id/a049a56e-a7ce-477e-aef3-c7e48ef8221c',
        'info_dict': {
            'id': 'a049a56e-a7ce-477e-aef3-c7e48ef8221c',
            'ext': 'mp4',
            'title': 'Dynamo Dresden vs. VfB Stuttgart (Round #1) (German Cup)',
            'duration': 8335,
            'thumbnail': 'https://s.secure.espncdn.com/stitcher/artwork/collections/media/bd1f3d12-0654-47d9-852e-71b85ea695c7/16x9.jpg?timestamp=202201112217&showBadge=true&cb=12&package=ESPN_PLUS',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.espn.com/espnplus/player/_/id/317f5fd1-c78a-4ebe-824a-129e0d348421',
        'info_dict': {
            'id': '317f5fd1-c78a-4ebe-824a-129e0d348421',
            'ext': 'mp4',
            'title': 'The Wheel - Episode 10',
            'duration': 3352,
            'thumbnail': 'https://s.secure.espncdn.com/stitcher/artwork/collections/media/317f5fd1-c78a-4ebe-824a-129e0d348421/16x9.jpg?timestamp=202205031523&showBadge=true&cb=12&package=ESPN_PLUS',
        },
        'params': {
            'skip_download': True,
        },
    }]

    _API_KEY = 'ZXNwbiZicm93c2VyJjEuMC4w.ptUt7QxsteaRruuPmGZFaJByOoqKvDP2a5YkInHrc7c'

    def _call_bamgrid_api(self, path, video_id, payload=None, headers={}):
        if 'Authorization' not in headers:
            headers['Authorization'] = f'Bearer {self._API_KEY}'
        parse = urllib.parse.urlencode if path == 'token' else json.dumps
        return self._download_json(
            f'https://espn.api.edge.bamgrid.com/{path}', video_id, headers=headers, data=parse(payload).encode())

    def _real_extract(self, url):
        video_id = self._match_id(url)
        cdn_data = self._download_json(
            f'https://watch-cdn.product.api.espn.com/api/product/v3/watchespn/web/playback/event?id={video_id}',
            video_id)
        video_data = cdn_data['playbackState']

        # ESPN+ subscription required, through cookies
        if 'DTC' in video_data.get('sourceId'):
            cookie = self._get_cookies(url).get('ESPN-ONESITE.WEB-PROD.token')
            if not cookie:
                self.raise_login_required(method='cookies')

            assertion = self._call_bamgrid_api(
                'devices', video_id,
                headers={'Content-Type': 'application/json; charset=UTF-8'},
                payload={
                    'deviceFamily': 'android',
                    'applicationRuntime': 'android',
                    'deviceProfile': 'tv',
                    'attributes': {},
                })['assertion']
            token = self._call_bamgrid_api(
                'token', video_id, payload={
                    'subject_token': assertion,
                    'subject_token_type': 'urn:bamtech:params:oauth:token-type:device',
                    'platform': 'android',
                    'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
                })['access_token']

            assertion = self._call_bamgrid_api(
                'accounts/grant', video_id, payload={'id_token': cookie.value.split('|')[1]},
                headers={
                    'Authorization': token,
                    'Content-Type': 'application/json; charset=UTF-8',
                })['assertion']
            token = self._call_bamgrid_api(
                'token', video_id, payload={
                    'subject_token': assertion,
                    'subject_token_type': 'urn:bamtech:params:oauth:token-type:account',
                    'platform': 'android',
                    'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange',
                })['access_token']

            playback = self._download_json(
                video_data['videoHref'].format(scenario='browser~ssai'), video_id,
                headers={
                    'Accept': 'application/vnd.media-service+json; version=5',
                    'Authorization': token,
                })
            m3u8_url, headers = playback['stream']['complete'][0]['url'], {'authorization': token}

        # No login required
        elif video_data.get('sourceId') == 'ESPN_FREE':
            asset = self._download_json(
                f'https://watch.auth.api.espn.com/video/auth/media/{video_id}/asset?apikey=uiqlbgzdwuru14v627vdusswb',
                video_id)
            m3u8_url, headers = asset['stream'], {}

        # TV Provider required
        else:
            resource = self._get_mvpd_resource('ESPN', video_data['name'], video_id, None)
            auth = self._extract_mvpd_auth(url, video_id, 'ESPN', resource).encode()

            asset = self._download_json(
                f'https://watch.auth.api.espn.com/video/auth/media/{video_id}/asset?apikey=uiqlbgzdwuru14v627vdusswb',
                video_id, data=f'adobeToken={urllib.parse.quote_plus(base64.b64encode(auth))}&drmSupport=HLS'.encode())
            m3u8_url, headers = asset['stream'], {}

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'duration': traverse_obj(cdn_data, ('tracking', 'duration')),
            'title': video_data.get('name'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': video_data.get('posterHref'),
            'http_headers': headers,
        }
