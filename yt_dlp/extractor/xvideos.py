from __future__ import unicode_literals

import math
import re

from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    InAdvancePagedList,
    int_or_none,
    parse_duration,
    strip_or_none,
    traverse_obj,
)


class XVideosIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:[^/]+\.)?xvideos2?\.com/video|
                            (?:www\.)?xvideos\.es/video|
                            (?:www|flashservice)\.xvideos\.com/embedframe/|
                            static-hw\.xvideos\.com/swf/xv-player\.swf\?.*?\bid_video=
                        )
                        (?P<id>[0-9]+)
                    '''
    _TESTS = [{
        'url': 'https://www.xvideos.com/video4588838/motorcycle_guy_cucks_influencer_steals_his_gf',
        'md5': '14cea69fcb84db54293b1e971466c2e1',
        'info_dict': {
            'id': '4588838',
            'ext': 'mp4',
            'title': 'Motorcycle Guy Cucks Influencer, Steals his GF',
            'duration': 108,
            'age_limit': 18,
            'thumbnail': r're:^https://img-hw.xvideos-cdn.com/.+\.jpg',
        }
    }, {
        # Broken HLS formats
        'url': 'https://www.xvideos.com/video65982001/what_s_her_name',
        'md5': 'b82d7d7ef7d65a84b1fa6965f81f95a5',
        'info_dict': {
            'id': '65982001',
            'ext': 'mp4',
            'title': 'what\'s her name?',
            'duration': 120,
            'age_limit': 18,
            'thumbnail': r're:^https://img-hw.xvideos-cdn.com/.+\.jpg',
        }
    }, {
        'url': 'https://flashservice.xvideos.com/embedframe/4588838',
        'only_matching': True,
    }, {
        'url': 'https://www.xvideos.com/embedframe/4588838',
        'only_matching': True,
    }, {
        'url': 'http://static-hw.xvideos.com/swf/xv-player.swf?id_video=4588838',
        'only_matching': True,
    }, {
        'url': 'http://xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://www.xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://www.xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://fr.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://fr.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://it.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://it.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://de.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://de.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        mobj = re.search(r'<h1 class="inlineError">(.+?)</h1>', webpage)
        if mobj:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, clean_html(mobj.group(1))), expected=True)

        title = self._html_search_regex(
            (r'<title>(?P<title>.+?)\s+-\s+XVID',
             r'setVideoTitle\s*\(\s*(["\'])(?P<title>(?:(?!\1).)+)\1'),
            webpage, 'title', default=None,
            group='title') or self._og_search_title(webpage)

        thumbnails = []
        for preference, thumbnail in enumerate(('', '169')):
            thumbnail_url = self._search_regex(
                r'setThumbUrl%s\(\s*(["\'])(?P<thumbnail>(?:(?!\1).)+)\1' % thumbnail,
                webpage, 'thumbnail', default=None, group='thumbnail')
            if thumbnail_url:
                thumbnails.append({
                    'url': thumbnail_url,
                    'preference': preference,
                })

        duration = int_or_none(self._og_search_property(
            'duration', webpage, default=None)) or parse_duration(
            self._search_regex(
                r'<span[^>]+class=["\']duration["\'][^>]*>.*?(\d[^<]+)',
                webpage, 'duration', fatal=False))

        formats = []

        video_url = compat_urllib_parse_unquote(self._search_regex(
            r'flv_url=(.+?)&', webpage, 'video URL', default=''))
        if video_url:
            formats.append({
                'url': video_url,
                'format_id': 'flv',
            })

        for kind, _, format_url in re.findall(
                r'setVideo([^(]+)\((["\'])(http.+?)\2\)', webpage):
            format_id = kind.lower()
            if format_id == 'hls':
                hls_formats = self._extract_m3u8_formats(
                    format_url, video_id, 'mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)
                self._check_formats(hls_formats, video_id)
                formats.extend(hls_formats)
            elif format_id in ('urllow', 'urlhigh'):
                formats.append({
                    'url': format_url,
                    'format_id': '%s-%s' % (determine_ext(format_url, 'mp4'), format_id[3:]),
                    'quality': -2 if format_id.endswith('low') else None,
                })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'duration': duration,
            'thumbnails': thumbnails,
            'age_limit': 18,
        }


class XVideosUserIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:.+?\.)?xvideos\.(?:com|es)/
        (?P<id>(?:channels|amateur-channels|model-channels|pornstar-channels|profiles)/[^/?#&]+)'''
    _TESTS = [{
        # channels profile and # in url
        'url': 'https://www.xvideos.com/channels/college_girls_gone_bad#_tabVideos,videos-best',
        'info_dict': {
            'id': 'channels/college_girls_gone_bad',
            'title': 'College Girls Gone Bad',
            'description': 'Hot college girls in real sorority hazing acts!',
        },
        'playlist_mincount': 109,
    }, {
        # model-channels profile and # in url
        'url': 'https://www.xvideos.com/model-channels/shonariver#_tabVideos,videos-best',
        'info_dict': {
            'id': 'model-channels/shonariver',
            'title': 'Shona River',
            'description': 'md5:4c695588123b2fb3d39f4d0dbf1da9a0',
        },
        'playlist_mincount': 198,
    }, {
        # amateur-channels profile
        'url': 'https://www.xvideos.com/amateur-channels/queanfuckingcucking',
        'info_dict': {
            'id': 'amateur-channels/queanfuckingcucking',
            'title': 'Queanfuckingcucking',
            'description': 'md5:bf4514baf23bc7d0525727deeaea96a9',
        },
        'playlist_mincount': 8,
    }, {
        # /profiles/***
        'url': 'https://www.xvideos.com/profiles/jacobsy',
        'info_dict': {
            'id': 'profiles/jacobsy',
            'title': 'Jacobsy',
            'description': 'fetishist and bdsm lover...',
        },
        'playlist_mincount': 84,
    }, {
        # no description
        'url': 'https://www.xvideos.com/profiles/espoder',
        'info_dict': {
            'id': 'profiles/espoder',
            'title': 'Espoder',
        },
        'playlist_mincount': 13,
    }]
    _PAGE_SIZE = 36

    def _entries(self, webpage):
        for mobj in re.finditer(r'<p[^>]+class="[^"]*title[^"]*"[^>]*>[^<]*<a[^>]+href="(?P<href>[^"]+)"', webpage):
            href = re.sub(
                r'/prof-video-click/(?:model|upload)/.+?/([0-9]+)/(.+)',
                r'/video\1/\2', mobj.group('href'))

            yield self.url_result(f'https://www.xvideos.com{href}', ie=XVideosIE.ie_key())

    def _real_extract(self, url):
        user_id = self._match_id(url)

        webpage = self._download_webpage(url, user_id, 'Downloading page')

        video_count = int_or_none(re.sub('[^0-9]', '', self._search_regex(
            r'<a[^>]+id="tab-videos"[^>]*>.*<span[^>]+>(.*)</span>.*?</a>',
            webpage, 'video_count', default='0', fatal=False)), default=0)

        page_count = int(math.ceil(video_count / self._PAGE_SIZE))

        title = strip_or_none(traverse_obj(self._parse_json(self._search_regex(
            r'<script>.*window\.xv\.conf=(.*);</script>',
            webpage, 'json', default='{}', fatal=False), user_id),
            ('data', 'user', 'display')))

        description = strip_or_none(self._search_regex(
            r'<div[^>]+id="header-about-me"[^>]*>([^<]+?)<',
            webpage, 'description', default=None, fatal=False))

        def _get_page(idx):
            page_url = 'https://www.xvideos.com/%s/videos/new/%s' % (user_id, idx)

            webpage = self._download_webpage(
                page_url, user_id, 'Downloading page %d/%d' % (idx + 1, page_count))

            return self._entries(webpage)

        return self.playlist_result(
            InAdvancePagedList(_get_page, page_count, self._PAGE_SIZE),
            user_id, title, description)
