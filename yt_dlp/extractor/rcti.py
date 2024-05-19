import json
import random
import time

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    dict_get,
    ExtractorError,
    strip_or_none,
    traverse_obj,
    try_get
)


class RCTIPlusBaseIE(InfoExtractor):
    def _real_initialize(self):
        self._AUTH_KEY = self._download_json(
            'https://api.rctiplus.com/api/v1/visitor?platform=web',  # platform can be web, mweb, android, ios
            None, 'Fetching authorization key')['data']['access_token']

    def _call_api(self, url, video_id, note=None):
        json = self._download_json(
            url, video_id, note=note, headers={'Authorization': self._AUTH_KEY})
        if json.get('status', {}).get('code', 0) != 0:
            raise ExtractorError(f'{self.IE_NAME} said: {json["status"]["message_client"]}', cause=json)
        return json.get('data'), json.get('meta')


class RCTIPlusIE(RCTIPlusBaseIE):
    _VALID_URL = r'https?://www\.rctiplus\.com/(?:programs/\d+?/.*?/)?(?P<type>episode|clip|extra|live-event|missed-event)/(?P<id>\d+)/(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.rctiplus.com/programs/1259/kiko-untuk-lola/episode/22124/untuk-lola',
        'md5': '56ed45affad45fa18d5592a1bc199997',
        'info_dict': {
            'id': 'v_e22124',
            'title': 'Untuk Lola',
            'display_id': 'untuk-lola',
            'description': 'md5:2b809075c0b1e071e228ad6d13e41deb',
            'ext': 'mp4',
            'duration': 1400,
            'timestamp': 1615978800,
            'upload_date': '20210317',
            'series': 'Kiko : Untuk Lola',
            'season_number': 1,
            'episode_number': 1,
            'channel': 'RCTI',
        },
        'params': {
            'fixup': 'never',
        },
    }, {  # Clip; Series title doesn't appear on metadata JSON
        'url': 'https://www.rctiplus.com/programs/316/cahaya-terindah/clip/3921/make-a-wish',
        'md5': 'd179b2ff356f0e91a53bcc6a4d8504f0',
        'info_dict': {
            'id': 'v_c3921',
            'title': 'Make A Wish',
            'display_id': 'make-a-wish',
            'description': 'Make A Wish',
            'ext': 'mp4',
            'duration': 288,
            'timestamp': 1571652600,
            'upload_date': '20191021',
            'series': 'Cahaya Terindah',
            'channel': 'RCTI',
        },
        'params': {
            'fixup': 'never',
        },
    }, {  # Extra
        'url': 'https://www.rctiplus.com/programs/616/inews-malam/extra/9438/diungkapkan-melalui-surat-terbuka-ceo-ruangguru-belva-devara-mundur-dari-staf-khusus-presiden',
        'md5': 'c48106afdbce609749f5e0c007d9278a',
        'info_dict': {
            'id': 'v_ex9438',
            'title': 'md5:2ede828c0f8bde249e0912be150314ca',
            'display_id': 'md5:62b8d4e9ff096db527a1ad797e8a9933',
            'description': 'md5:2ede828c0f8bde249e0912be150314ca',
            'ext': 'mp4',
            'duration': 93,
            'timestamp': 1587561540,
            'upload_date': '20200422',
            'series': 'iNews Malam',
            'channel': 'INews',
        },
    }, {  # Missed event/replay
        'url': 'https://www.rctiplus.com/missed-event/2507/mou-signing-ceremony-27-juli-2021-1400-wib',
        'md5': '649c5f27250faed1452ca8b91e06922d',
        'info_dict': {
            'id': 'v_pe2507',
            'title': 'MOU Signing Ceremony | 27 Juli 2021 | 14.00 WIB',
            'display_id': 'mou-signing-ceremony-27-juli-2021-1400-wib',
            'ext': 'mp4',
            'timestamp': 1627142400,
            'upload_date': '20210724',
            'was_live': True,
            'release_timestamp': 1627369200,
        },
        'params': {
            'fixup': 'never',
        },
    }, {  # Live event; Cloudfront CDN
        'url': 'https://www.rctiplus.com/live-event/2530/dai-muda-charging-imun-dengan-iman-4-agustus-2021-1600-wib',
        'info_dict': {
            'id': 'v_le2530',
            'title': 'Dai Muda : Charging Imun dengan Iman | 4 Agustus 2021 | 16.00 WIB',
            'display_id': 'dai-muda-charging-imun-dengan-iman-4-agustus-2021-1600-wib',
            'ext': 'mp4',
            'timestamp': 1627898400,
            'upload_date': '20210802',
            'release_timestamp': 1628067600,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'This live event has ended.',
    }, {  # TV; live_at is null
        'url': 'https://www.rctiplus.com/live-event/1/rcti',
        'info_dict': {
            'id': 'v_lt1',
            'title': 'RCTI',
            'display_id': 'rcti',
            'ext': 'mp4',
            'timestamp': 1546344000,
            'upload_date': '20190101',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }]
    _CONVIVA_JSON_TEMPLATE = {
        't': 'CwsSessionHb',
        'cid': 'ff84ae928c3b33064b76dec08f12500465e59a6f',
        'clid': '0',
        'sid': 0,
        'seq': 0,
        'caps': 0,
        'sf': 7,
        'sdk': True,
    }

    def _real_extract(self, url):
        match = self._match_valid_url(url).groupdict()
        video_type, video_id, display_id = match['type'], match['id'], match['display_id']

        url_api_version = 'v2' if video_type == 'missed-event' else 'v1'
        appier_id = '23984824_' + str(random.randint(0, 10000000000))  # Based on the webpage's uuidRandom generator
        video_json = self._call_api(
            f'https://api.rctiplus.com/api/{url_api_version}/{video_type}/{video_id}/url?appierid={appier_id}', display_id, 'Downloading video URL JSON')[0]
        video_url = video_json['url']

        is_upcoming = try_get(video_json, lambda x: x['current_date'] < x['live_at'])
        if is_upcoming is None:
            is_upcoming = try_get(video_json, lambda x: x['current_date'] < x['start_date'])
        if is_upcoming:
            self.raise_no_formats(
                'This event will start at %s.' % video_json['live_label'] if video_json.get('live_label') else 'This event has not started yet.', expected=True)
        if 'akamaized' in video_url:
            # For some videos hosted on Akamai's CDN (possibly AES-encrypted ones?), a session needs to at least be made via Conviva's API
            conviva_json_data = {
                **self._CONVIVA_JSON_TEMPLATE,
                'url': video_url,
                'sst': int(time.time())
            }
            conviva_json_res = self._download_json(
                'https://ff84ae928c3b33064b76dec08f12500465e59a6f.cws.conviva.com/0/wsg', display_id,
                'Creating Conviva session', 'Failed to create Conviva session',
                fatal=False, data=json.dumps(conviva_json_data).encode('utf-8'))
            if conviva_json_res and conviva_json_res.get('err') != 'ok':
                self.report_warning('Conviva said: %s' % str(conviva_json_res.get('err')))

        video_meta, meta_paths = self._call_api(
            'https://api.rctiplus.com/api/v1/%s/%s' % (video_type, video_id), display_id, 'Downloading video metadata')

        thumbnails, image_path = [], meta_paths.get('image_path', 'https://rstatic.akamaized.net/media/')
        if video_meta.get('portrait_image'):
            thumbnails.append({
                'id': 'portrait_image',
                'url': '%s%d%s' % (image_path, 2000, video_meta['portrait_image'])  # 2000px seems to be the highest resolution that can be given
            })
        if video_meta.get('landscape_image'):
            thumbnails.append({
                'id': 'landscape_image',
                'url': '%s%d%s' % (image_path, 2000, video_meta['landscape_image'])
            })
        try:
            formats = self._extract_m3u8_formats(video_url, display_id, 'mp4', headers={'Referer': 'https://www.rctiplus.com/'})
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                self.raise_geo_restricted(countries=['ID'], metadata_available=True)
            else:
                raise e
        for f in formats:
            if 'akamaized' in f['url'] or 'cloudfront' in f['url']:
                f.setdefault('http_headers', {})['Referer'] = 'https://www.rctiplus.com/'  # Referer header is required for akamai/cloudfront CDNs

        return {
            'id': video_meta.get('product_id') or video_json.get('product_id'),
            'title': dict_get(video_meta, ('title', 'name')) or dict_get(video_json, ('content_name', 'assets_name')),
            'display_id': display_id,
            'description': video_meta.get('summary'),
            'timestamp': video_meta.get('release_date') or video_json.get('start_date'),
            'duration': video_meta.get('duration'),
            'categories': [video_meta['genre']] if video_meta.get('genre') else None,
            'average_rating': video_meta.get('star_rating'),
            'series': video_meta.get('program_title') or video_json.get('program_title'),
            'season_number': video_meta.get('season'),
            'episode_number': video_meta.get('episode'),
            'channel': video_json.get('tv_name'),
            'channel_id': video_json.get('tv_id'),
            'formats': formats,
            'thumbnails': thumbnails,
            'is_live': video_type == 'live-event' and not is_upcoming,
            'was_live': video_type == 'missed-event',
            'live_status': 'is_upcoming' if is_upcoming else None,
            'release_timestamp': video_json.get('live_at'),
        }


class RCTIPlusSeriesIE(RCTIPlusBaseIE):
    _VALID_URL = r'https?://www\.rctiplus\.com/programs/(?P<id>\d+)/(?P<display_id>[^/?#&]+)(?:/(?P<type>episodes|extras|clips))?'
    _TESTS = [{
        'url': 'https://www.rctiplus.com/programs/829/putri-untuk-pangeran',
        'playlist_mincount': 1019,
        'info_dict': {
            'id': '829',
            'title': 'Putri Untuk Pangeran',
            'description': 'md5:aca7b54d05bd95a67d4f4613cc1d622d',
            'age_limit': 2,
            'cast': ['Verrel Bramasta', 'Ranty Maria', 'Riza Syah', 'Ivan Fadilla', 'Nicole Parham', 'Dll', 'Aviv Elham'],
            'display_id': 'putri-untuk-pangeran',
            'tags': 'count:18',
        },
    }, {  # No episodes
        'url': 'https://www.rctiplus.com/programs/615/inews-pagi',
        'playlist_mincount': 388,
        'info_dict': {
            'id': '615',
            'title': 'iNews Pagi',
            'description': 'md5:f18ee3d4643cfb41c358e5a9b693ee04',
            'age_limit': 2,
            'tags': 'count:11',
            'display_id': 'inews-pagi',
        }
    }]
    _AGE_RATINGS = {  # Based off https://id.wikipedia.org/wiki/Sistem_rating_konten_televisi with additional ratings
        'S-SU': 2,
        'SU': 2,
        'P': 2,
        'A': 7,
        'R': 13,
        'R-R/1': 17,  # Labelled as 17+ despite being R
        'D': 18,
    }

    @classmethod
    def suitable(cls, url):
        return False if RCTIPlusIE.suitable(url) else super(RCTIPlusSeriesIE, cls).suitable(url)

    def _entries(self, url, display_id=None, note='Downloading entries JSON', metadata={}):
        total_pages = 0
        try:
            total_pages = self._call_api(
                '%s&length=20&page=0' % url,
                display_id, note)[1]['pagination']['total_page']
        except ExtractorError as e:
            if 'not found' in str(e):
                return []
            raise e
        if total_pages <= 0:
            return []

        for page_num in range(1, total_pages + 1):
            episode_list = self._call_api(
                '%s&length=20&page=%s' % (url, page_num),
                display_id, '%s page %s' % (note, page_num))[0] or []

            for video_json in episode_list:
                yield {
                    '_type': 'url',
                    'url': video_json['share_link'],
                    'ie_key': RCTIPlusIE.ie_key(),
                    'id': video_json.get('product_id'),
                    'title': video_json.get('title'),
                    'display_id': video_json.get('title_code').replace('_', '-'),
                    'description': video_json.get('summary'),
                    'timestamp': video_json.get('release_date'),
                    'duration': video_json.get('duration'),
                    'season_number': video_json.get('season'),
                    'episode_number': video_json.get('episode'),
                    **metadata
                }

    def _series_entries(self, series_id, display_id=None, video_type=None, metadata={}):
        if not video_type or video_type in 'episodes':
            try:
                seasons_list = self._call_api(
                    f'https://api.rctiplus.com/api/v1/program/{series_id}/season',
                    display_id, 'Downloading seasons list JSON')[0]
            except ExtractorError as e:
                if 'not found' not in str(e):
                    raise
                seasons_list = []
            for season in seasons_list:
                yield from self._entries(
                    f'https://api.rctiplus.com/api/v2/program/{series_id}/episode?season={season["season"]}',
                    display_id, f'Downloading season {season["season"]} episode entries', metadata)
        if not video_type or video_type in 'extras':
            yield from self._entries(
                f'https://api.rctiplus.com/api/v2/program/{series_id}/extra?content_id=0',
                display_id, 'Downloading extra entries', metadata)
        if not video_type or video_type in 'clips':
            yield from self._entries(
                f'https://api.rctiplus.com/api/v2/program/{series_id}/clip?content_id=0',
                display_id, 'Downloading clip entries', metadata)

    def _real_extract(self, url):
        series_id, display_id, video_type = self._match_valid_url(url).group('id', 'display_id', 'type')
        if video_type:
            self.report_warning(
                f'Only {video_type} will be downloaded. '
                f'To download everything from the series, remove "/{video_type}" from the URL')

        series_meta, meta_paths = self._call_api(
            f'https://api.rctiplus.com/api/v1/program/{series_id}/detail', display_id, 'Downloading series metadata')
        metadata = {
            'age_limit': try_get(series_meta, lambda x: self._AGE_RATINGS[x['age_restriction'][0]['code']]),
            'cast': traverse_obj(series_meta, (('starring', 'creator', 'writer'), ..., 'name'),
                                 expected_type=lambda x: strip_or_none(x) or None),
            'tags': traverse_obj(series_meta, ('tag', ..., 'name'),
                                 expected_type=lambda x: strip_or_none(x) or None),
        }
        return self.playlist_result(
            self._series_entries(series_id, display_id, video_type, metadata), series_id,
            series_meta.get('title'), series_meta.get('summary'), display_id=display_id, **metadata)


class RCTIPlusTVIE(RCTIPlusBaseIE):
    _VALID_URL = r'https?://www\.rctiplus\.com/((tv/(?P<tvname>\w+))|(?P<eventname>live-event|missed-event))'
    _TESTS = [{
        'url': 'https://www.rctiplus.com/tv/rcti',
        'info_dict': {
            'id': 'v_lt1',
            'title': 'RCTI',
            'ext': 'mp4',
            'timestamp': 1546344000,
            'upload_date': '20190101',
        },
        'params': {
            'skip_download': True,
        }
    }, {
        # Returned video will always change
        'url': 'https://www.rctiplus.com/live-event',
        'only_matching': True,
    }, {
        # Returned video will also always change
        'url': 'https://www.rctiplus.com/missed-event',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if RCTIPlusIE.suitable(url) else super(RCTIPlusTVIE, cls).suitable(url)

    def _real_extract(self, url):
        match = self._match_valid_url(url).groupdict()
        tv_id = match.get('tvname') or match.get('eventname')
        webpage = self._download_webpage(url, tv_id)
        video_type, video_id = self._search_regex(
            r'url\s*:\s*["\']https://api\.rctiplus\.com/api/v./(?P<type>[^/]+)/(?P<id>\d+)/url',
            webpage, 'video link', group=('type', 'id'))
        return self.url_result(f'https://www.rctiplus.com/{video_type}/{video_id}/{tv_id}', 'RCTIPlus')
