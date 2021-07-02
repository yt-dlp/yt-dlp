# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .openload import PhantomJSwrapper

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    RegexNotFoundError,
    strip_or_none,
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
            raise ExtractorError('%s said: %s' % (self.IE_NAME, json["status"]["message_client"]), cause=json)
        return json.get('data'), json.get('meta')


class RCTIPlusIE(RCTIPlusBaseIE):
    _VALID_URL = r'https://www\.rctiplus\.com/programs/\d+?/.*?/(?P<type>episode|clip|extra)/(?P<id>\d+)/(?P<display_id>[^/?#&]+)'
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
        'params': {
            'format': 'bestvideo',
        },
    }]

    def _search_auth_key(self, webpage):
        try:
            self._AUTH_KEY = self._search_regex(
                r'\'Authorization\':"(?P<auth>[^"]+)"', webpage, 'auth-key')
        except RegexNotFoundError:
            pass

    def _real_extract(self, url):
        video_type, video_id, display_id = re.match(self._VALID_URL, url).groups()
        webpage = self._download_webpage(url, display_id)
        self._search_auth_key(webpage)

        video_json = self._call_api(
            'https://api.rctiplus.com/api/v1/%s/%s/url?appierid=.1' % (video_type, video_id), display_id, 'Downloading video URL JSON')[0]
        video_url = video_json['url']
        if 'akamaized' in video_url:
            # Akamai's CDN requires a session to at least be made via Conviva's API
            # TODO: Reverse-engineer Conviva's heartbeat code to avoid phantomJS
            phantom = None
            try:
                phantom = PhantomJSwrapper(self)
                phantom.get(url, webpage, display_id, note2='Initiating video session')
            except ExtractorError:
                self.report_warning('PhantomJS is highly recommended for this video, as it might load incredibly slowly otherwise.'
                                    'You can also try opening the page in this device\'s browser first')

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

        formats = self._extract_m3u8_formats(video_url, display_id, 'mp4', headers={'Referer': 'https://www.rctiplus.com/'})
        for f in formats:
            if 'akamaized' in f['url']:
                f.setdefault('http_headers', {})['Referer'] = 'https://www.rctiplus.com/'  # Referer header is required for akamai CDNs

        self._sort_formats(formats)

        return {
            'id': video_meta.get('product_id') or video_json.get('product_id'),
            'title': video_meta.get('title') or video_json.get('content_name'),
            'display_id': display_id,
            'description': video_meta.get('summary'),
            'timestamp': video_meta.get('release_date'),
            'duration': video_meta.get('duration'),
            'categories': [video_meta.get('genre')],
            'average_rating': video_meta.get('star_rating'),
            'series': video_meta.get('program_title') or video_json.get('program_title'),
            'season_number': video_meta.get('season'),
            'episode_number': video_meta.get('episode'),
            'channel': video_json.get('tv_name'),
            'channel_id': video_json.get('tv_id'),
            'formats': formats,
            'thumbnails': thumbnails
        }


class RCTIPlusSeriesIE(RCTIPlusBaseIE):
    _VALID_URL = r'https://www\.rctiplus\.com/programs/(?P<id>\d+)/(?P<display_id>[^/?#&]+)(?:\W)*$'
    _TESTS = [{
        'url': 'https://www.rctiplus.com/programs/540/upin-ipin',
        'playlist_mincount': 417,
        'info_dict': {
            'id': '540',
            'title': 'Upin & Ipin',
            'description': 'md5:22cc912381f389664416844e1ec4f86b',
        },
    }, {
        'url': 'https://www.rctiplus.com/programs/540/upin-ipin/#',
        'only_matching': True,
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
                link = video_json['share_link']
                url_res = self.url_result(link, 'RCTIPlus', video_json.get('product_id'), video_json.get('title'))
                url_res.update(metadata)
                yield url_res

    def _real_extract(self, url):
        series_id, display_id = re.match(self._VALID_URL, url).groups()

        series_meta, meta_paths = self._call_api(
            'https://api.rctiplus.com/api/v1/program/%s/detail' % series_id, display_id, 'Downloading series metadata')
        metadata = {
            'age_limit': try_get(series_meta, lambda x: self._AGE_RATINGS[x['age_restriction'][0]['code']])
        }

        cast = []
        for star in series_meta.get('starring', []):
            cast.append(strip_or_none(star.get('name')))
        for star in series_meta.get('creator', []):
            cast.append(strip_or_none(star.get('name')))
        for star in series_meta.get('writer', []):
            cast.append(strip_or_none(star.get('name')))
        metadata['cast'] = cast

        tags = []
        for tag in series_meta.get('tag', []):
            tags.append(strip_or_none(tag.get('name')))
        metadata['tag'] = tags

        entries = []
        seasons_list = self._call_api(
            'https://api.rctiplus.com/api/v1/program/%s/season' % series_id, display_id, 'Downloading seasons list JSON')[0]
        for season in seasons_list:
            entries.append(self._entries('https://api.rctiplus.com/api/v2/program/%s/episode?season=%s' % (series_id, season['season']),
                                         display_id, 'Downloading season %s episode entries' % season['season'], metadata))

        entries.append(self._entries('https://api.rctiplus.com/api/v2/program/%s/clip?content_id=0' % series_id,
                                     display_id, 'Downloading clip entries', metadata))
        entries.append(self._entries('https://api.rctiplus.com/api/v2/program/%s/extra?content_id=0' % series_id,
                                     display_id, 'Downloading extra entries', metadata))

        return self.playlist_result(itertools.chain(*entries), series_id, series_meta.get('title'), series_meta.get('summary'), **metadata)
