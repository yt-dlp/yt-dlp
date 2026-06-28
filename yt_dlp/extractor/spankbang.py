import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    extract_attributes,
    js_to_json,
    parse_resolution,
    str_to_int,
    url_or_none,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import find_element, traverse_obj, trim_str


class SpankBangIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:[^/]+\.)?spankbang\.com/
                        (?:
                            (?P<id>[\da-z]+)/(?:video|play|embed)\b|
                            [\da-z]+-(?P<id_2>[\da-z]+)/playlist/[^/?#&]+
                        )
                    '''
    _TESTS = [{
        'url': 'https://spankbang.com/56b3d/video/the+slut+maker+hmv',
        'md5': '2D13903DE4ECC7895B5D55930741650A',
        'info_dict': {
            'id': '56b3d',
            'ext': 'mp4',
            'title': 'The Slut Maker HMV',
            'description': 'Girls getting converted into cock slaves.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Mindself',
            'uploader_id': 'mindself',
            'timestamp': 1617109572,
            'upload_date': '20210330',
            'age_limit': 18,
        },
        'skip': 'Video removed',
    }, {
        # 4k
        'url': 'https://spankbang.com/6tp5u/video/exodus+world+pmv+games+2022',
        'md5': '8cf68545903071b34b2a2f2999d0e1ce',
        'info_dict': {
            'id': '6tp5u',
            'ext': 'mp4',
            'title': 'Exodus - World PMV Games 2022 ft. Purple Bitch & Reislin: Amateur, Anal & Cosplay Porn - SpankBang',
            'description': 'Watch Exodus - World PMV Games 2022 on SpankBang now! - Anal, Amateur, Cosplay Porn - SpankBang',
            'uploader': 'BigChungoPMV',
            'uploader_url': 'https://spankbang.com/profile/bigchungopmv',
            'view_count': int,
            'age_limit': 18,
            'duration': 361,
            'thumbnail': 'https://tbi.sb-cd.com/t/11463330/2d/66/w:1280/t10-enh/exodus-world-pmv-games-2022.jpg',
            'tags': 'count:12',
        },
    }, {
        # 480p only
        'url': 'http://spankbang.com/1vt0/video/solvane+gangbang',
        'only_matching': True,
    }, {
        # no uploader
        'url': 'http://spankbang.com/lklg/video/sex+with+anyone+wedding+edition+2',
        'only_matching': True,
    }, {
        # mobile page
        'url': 'http://m.spankbang.com/1o2de/video/can+t+remember+her+name',
        'only_matching': True,
    }, {
        'url': 'https://spankbang.com/1vwqx/video/jade+kush+solo+4k',
        'only_matching': True,
    }, {
        'url': 'https://m.spankbang.com/3vvn/play/fantasy+solo/480p/',
        'only_matching': True,
    }, {
        'url': 'https://m.spankbang.com/3vvn/play',
        'only_matching': True,
    }, {
        'url': 'https://spankbang.com/2y3td/embed/',
        'only_matching': True,
    }, {
        'url': 'https://spankbang.com/2v7ik-7ecbgu/playlist/latina+booty',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('id_2')
        country = self.get_param('geo_bypass_country') or 'US'
        self._set_cookie('.spankbang.com', 'country', country.upper())
        webpage = self._download_webpage(
            url.replace(f'/{video_id}/embed', f'/{video_id}/video'),
            video_id, impersonate=True)

        if re.search(r'<[^>]+\b(?:id|class)=["\']video_removed', webpage):
            raise ExtractorError(
                f'Video {video_id} is not available', expected=True)

        formats = []

        def extract_format(format_id, format_url):
            f_url = url_or_none(format_url)
            if not f_url:
                return
            f = parse_resolution(format_id) or parse_resolution(format_url)
            ext = determine_ext(f_url)
            if format_id.startswith('m3u8') or ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    f_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            elif format_id.startswith('mpd') or ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    f_url, video_id, mpd_id='dash', fatal=False))
            elif ext == 'mp4' or f.get('width') or f.get('height'):
                f.update({
                    'url': f_url,
                    'format_id': format_id,
                })
                formats.append(f)

        stream_data = self._search_json(r'var\s+stream_data\s+=', webpage, 'stream data', video_id, transform_source=js_to_json, default={})
        for fmt_id, fmt_data in stream_data.items():
            if not fmt_data or isinstance(fmt_data, (str, int)):
                continue
            extract_format(fmt_id, fmt_data[0])

        if not formats:
            stream_key = self._search_regex(
                r'data-streamkey\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
                webpage, 'stream key', group='value')

            stream = self._download_json(
                'https://spankbang.com/api/videos/stream', video_id,
                'Downloading stream JSON', data=urlencode_postdata({
                    'id': stream_key,
                    'data': 0,
                }), headers={
                    'Referer': url,
                    'X-Requested-With': 'XMLHttpRequest',
                }, impersonate=True)

            for format_id, format_url in stream.items():
                if format_url and isinstance(format_url, list):
                    format_url = format_url[0]
                extract_format(format_id, format_url)

        view_count = str_to_int(self._search_regex(
            [
                r'window\.viewCount\s*=\s*["\'](\d+)["\']',
                r'(?i)<span[^>]+>.*?views.*?</span\s*>\s*<span[^>]+>(\d+)</span>',
            ], webpage, 'view count', default=None))

        return {
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'description': self._html_search_meta(['og:description', 'twitter:description'], webpage),
            'thumbnail': traverse_obj(stream_data, (('cover_image', 'thumbnail'), {url_or_none}, any)) or self._og_search_thumbnail(webpage, default=None),
            'duration': str_to_int(stream_data.get('length') or self._html_search_meta('og:video:duration', webpage, default=None)),
            'view_count': view_count,
            'age_limit': self._rta_search(webpage),
            'tags': list(filter(None, self._search_regex(r'};\s*var\s*\s*live_keywords\s*=\s*["\']([^"\']+)["\']', webpage, 'tags', default='').split(','))),
            **traverse_obj(webpage, ({find_element(attr='data-testid', value='profile')}, {find_element(cls='text-link-primary', html=True)}, {
                'uploader_url': ({extract_attributes}, 'href', {urljoin('https://spankbang.com')}),
                'uploader': ({find_element(tag='p')}, {clean_html}),
            })),
            'formats': formats,
        }


class SpankBangPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?spankbang\.com/(?P<id>[\da-z]+)/playlist/(?P<display_id>[^/]+)'
    _TEST = {
        'url': 'https://spankbang.com/ug0k/playlist/big+ass+titties',
        'info_dict': {
            'id': 'ug0k',
            'title': 'Big Ass Titties',
        },
        'playlist_mincount': 40,
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        playlist_id = mobj.group('id')
        country = self.get_param('geo_bypass_country') or 'US'
        self._set_cookie('.spankbang.com', 'country', country.upper())
        webpage = self._download_webpage(url, playlist_id, impersonate=True)

        entries = [self.url_result(
            urljoin(url, mobj.group('path')),
            ie=SpankBangIE.ie_key(), video_id=mobj.group('id'))
            for mobj in re.finditer(
                r'<a[^>]+\bhref=(["\'])(?P<path>/?[\da-z]+-(?P<id>[\da-z]+)/playlist/[^"\'](?:(?!\1).)*)\1',
                webpage)]

        title = traverse_obj(webpage, (
            {find_element(tag='h1', attr='data-testid', value='playlist-title')},
            {clean_html}, {trim_str(end=' Playlist')}))

        return self.playlist_result(entries, playlist_id, title)
