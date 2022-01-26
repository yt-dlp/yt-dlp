from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    int_or_none,
    parse_duration, strip_or_none,
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
            'description': 'Thanks for taking an interest in me. You probably already know me from porn. But just in case you don&rsquo;t, let me tell you a bit more.',
        },
        'playlist_mincount': 198,
    }, {
        # amateur-channels profile
        'url': 'https://www.xvideos.com/amateur-channels/queanfuckingcucking',
        'info_dict': {
            'id': 'amateur-channels/queanfuckingcucking',
            'title': 'Queanfuckingcucking',
            'description': 'I&rsquo;m a cuckquean with no interest in men only women for my man to do what he does best please me by pleasing other women',
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
        'playlist_mincount': 85,
    }, {
        # no description
        'url': 'https://www.xvideos.com/profiles/espoder',
        'info_dict': {
            'id': 'profiles/espoder',
            'title': 'Espoder',
            'description': '',
        },
        'playlist_mincount': 13,
    }]

    def _entries(self, user_id):
        page_number = 0

        while True:
            next_page_url = 'https://www.xvideos.com/%s/videos/new/%s' % (user_id, page_number)

            page = self._download_webpage(
                next_page_url, user_id, 'Downloading page %s' % str(page_number + 1))

            for mobj in re.finditer(r'<p[^>]+class="[^"]*title[^"]*"[^>]*>[^<]*<a[^>]+href="(?P<href>[^"]+)"', page):
                href = mobj.group('href')
                href = re.sub(
                    r'/prof-video-click/(?:model|upload)/.+?/([0-9]+)/(.+)',
                    r'/video\1/\2', href)

                video_url = 'https://www.xvideos.com' + href
                video_id = XVideosIE._match_id(video_url)

                yield self.url_result(video_url, ie=XVideosIE.ie_key(), video_id=video_id)

            if not re.search(r'<a[^>]+class="[^"]+next-page[^>]+>', page):
                break

            page_number += 1

    def _real_extract(self, url):
        user_id = self._match_id(url)

        page = self._download_webpage(url, user_id, 'Downloading page')

        mobj = re.search(r'<script>.*window\.xv\.conf=(?P<json>.*);</script>', page)
        if mobj:
            conf = self._parse_json(mobj.group('json'), user_id)
            try:
                title = conf['data']['user']['display']
            except AttributeError:
                title = ''
        else:
            title = ''

        mobj = re.search(r'<div[^>]+id="header-about-me"[^>]*>(?P<description>[^<]+?)<', page)

        if mobj:
            description = mobj.group('description')
        else:
            description = ''

        return self.playlist_result(self._entries(user_id), user_id, strip_or_none(title), strip_or_none(description))
