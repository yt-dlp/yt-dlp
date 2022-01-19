from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    merge_dicts,
    parse_duration,
    parse_resolution,
    str_to_int,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


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
        }
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
        # 4k
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
        webpage = self._download_webpage(
            url.replace('/%s/embed' % video_id, '/%s/video' % video_id),
            video_id, headers={'Cookie': 'country=US'})

        if re.search(r'<[^>]+\b(?:id|class)=["\']video_removed', webpage):
            raise ExtractorError(
                'Video %s is not available' % video_id, expected=True)

        formats = []

        def extract_format(format_id, format_url):
            f_url = url_or_none(format_url)
            if not f_url:
                return
            f = parse_resolution(format_id)
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

        STREAM_URL_PREFIX = 'stream_url_'

        for mobj in re.finditer(
                r'%s(?P<id>[^\s=]+)\s*=\s*(["\'])(?P<url>(?:(?!\2).)+)\2'
                % STREAM_URL_PREFIX, webpage):
            extract_format(mobj.group('id', 'url'))

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
                })

            for format_id, format_url in stream.items():
                if format_url and isinstance(format_url, list):
                    format_url = format_url[0]
                extract_format(format_id, format_url)

        self._sort_formats(formats)

        info = self._search_json_ld(webpage, video_id, default={})

        title = self._html_search_regex(
            r'(?s)<h1[^>]+\btitle=["\']([^"]+)["\']>', webpage, 'title', default=None)
        description = self._search_regex(
            r'<div[^>]+\bclass=["\']bottom[^>]+>\s*<p>[^<]*</p>\s*<p>([^<]+)',
            webpage, 'description', default=None)
        thumbnail = self._og_search_thumbnail(webpage, default=None)
        uploader = self._html_search_regex(
            r'<svg[^>]+\bclass="(?:[^"]*?user[^"]*?)">.*?</svg>([^<]+)', webpage, 'uploader', default=None)
        uploader_id = self._html_search_regex(
            r'<a[^>]+href="/profile/([^"]+)"', webpage, 'uploader_id', default=None)
        duration = parse_duration(self._search_regex(
            r'<div[^>]+\bclass=["\']right_side[^>]+>\s*<span>([^<]+)',
            webpage, 'duration', default=None))
        view_count = str_to_int(self._search_regex(
            r'([\d,.]+)\s+plays', webpage, 'view count', default=None))

        age_limit = self._rta_search(webpage)

        return merge_dicts({
            'id': video_id,
            'title': title or video_id,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
            'age_limit': age_limit,
        }, info
        )


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
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(
            url, playlist_id, headers={'Cookie': 'country=US; mobile=on'})

        entries = [self.url_result(
            urljoin(url, mobj.group('path')),
            ie=SpankBangIE.ie_key(), video_id=mobj.group('id'))
            for mobj in re.finditer(
                r'<a[^>]+\bhref=(["\'])(?P<path>/?[\da-z]+-(?P<id>[\da-z]+)/playlist/%s(?:(?!\1).)*)\1'
                % re.escape(display_id), webpage)]

        title = self._html_search_regex(
            r'<h1>([^<]+)\s+playlist\s*<', webpage, 'playlist title',
            fatal=False)

        return self.playlist_result(entries, playlist_id, title)
