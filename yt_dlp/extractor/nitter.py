# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    parse_count,
    unified_strdate,
    unified_timestamp,
    remove_end,
    determine_ext,
)
import re


class NitterIE(InfoExtractor):
    # Taken from https://github.com/zedeus/nitter/wiki/Instances
    INSTANCES = ('nitter.net',
                 'nitter.snopyta.org',
                 'nitter.42l.fr',
                 'nitter.nixnet.services',
                 'nitter.13ad.de',
                 'nitter.pussthecat.org',
                 'nitter.mastodont.cat',
                 'nitter.dark.fail',
                 'nitter.tedomum.net',
                 'nitter.cattube.org',
                 'nitter.fdn.fr',
                 'nitter.1d4.us',
                 'nitter.kavin.rocks',
                 'tweet.lambda.dance',
                 'nitter.cc',
                 'nitter.weaponizedhumiliation.com',
                 '3nzoldnxplag42gqjs23xvghtzf6t6yzssrtytnntc6ppc7xxuoneoad.onion',
                 'nitter.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd.onion',
                 'nitterlgj3n5fgwesu3vxc5h67ruku33nqaoeoocae2mvlzhsu6k7fqd.onion')

    _INSTANCES_RE = '(?:' + '|'.join([re.escape(instance) for instance in INSTANCES]) + ')'
    _VALID_URL = r'https?://%(instance)s/(?P<uploader_id>.+)/status/(?P<id>[0-9]+)(#.)?' % {'instance': _INSTANCES_RE}
    current_instance = INSTANCES[0]  # the test and official instance
    _TESTS = [
        {
            # GIF (wrapped in mp4)
            'url': 'https://' + current_instance + '/firefox/status/1314279897502629888#m',
            'info_dict': {
                'id': '1314279897502629888',
                'ext': 'mp4',
                'title': 'Firefox 🔥 - You know the old saying, if you see something say something. Now you actually can with the YouTube regrets extension.   Report harmful YouTube recommendations so others can avoid watching them. ➡️ https://mzl.la/3iFIiyg  #UnfckTheInternet',
                'description': 'You know the old saying, if you see something say something. Now you actually can with the YouTube regrets extension.   Report harmful YouTube recommendations so others can avoid watching them. ➡️ https://mzl.la/3iFIiyg  #UnfckTheInternet',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Firefox 🔥',
                'uploader_id': 'firefox',
                'uploader_url': 'https://' + current_instance + '/firefox',
                'upload_date': '20201008',
                'timestamp': 1602183720,
            },
        }, {  # normal video
            'url': 'https://' + current_instance + '/Le___Doc/status/1299715685392756737#m',
            'info_dict': {
                'id': '1299715685392756737',
                'ext': 'mp4',
                'title': 'Le Doc - "Je ne prédis jamais rien" D Raoult, Août 2020...',
                'description': '"Je ne prédis jamais rien" D Raoult, Août 2020...',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Le Doc',
                'uploader_id': 'Le___Doc',
                'uploader_url': 'https://' + current_instance + '/Le___Doc',
                'upload_date': '20200829',
                'timestamp': 1598711341,
                'view_count': int,
                'like_count': int,
                'repost_count': int,
                'comment_count': int,
            },
        }, {  # video embed in a "Streaming Political Ads" box
            'url': 'https://' + current_instance + '/mozilla/status/1321147074491092994#m',
            'info_dict': {
                'id': '1321147074491092994',
                'ext': 'mp4',
                'title': "Mozilla - Are you being targeted with weird, ominous or just plain annoying political ads while streaming your favorite shows?  This isn't a real political ad, but if you're watching streaming TV in the U.S., chances are you've seen quite a few.   Learn more ➡️ https://mzl.la/StreamingAds",
                'description': "Are you being targeted with weird, ominous or just plain annoying political ads while streaming your favorite shows?  This isn't a real political ad, but if you're watching streaming TV in the U.S., chances are you've seen quite a few.   Learn more ➡️ https://mzl.la/StreamingAds",
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Mozilla',
                'uploader_id': 'mozilla',
                'uploader_url': 'https://' + current_instance + '/mozilla',
                'upload_date': '20201027',
                'timestamp': 1603820982
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        parsed_url = compat_urlparse.urlparse(url)
        base_url = parsed_url.scheme + '://' + parsed_url.netloc

        self._set_cookie(parsed_url.netloc, 'hlsPlayback', 'on')
        webpage = self._download_webpage(url, video_id)

        video_url = base_url + self._html_search_regex(r'(?:<video[^>]+data-url|<source[^>]+src)="([^"]+)"', webpage, 'video url')
        ext = determine_ext(video_url)

        if ext == 'unknown_video':
            formats = self._extract_m3u8_formats(video_url, video_id, ext='mp4')
        else:
            formats = [{
                'url': video_url,
                'ext': ext
            }]

        title = (
            self._og_search_description(webpage).replace('\n', ' ')
            or self._html_search_regex(r'<div class="tweet-content[^>]+>([^<]+)</div>', webpage, 'title'))
        description = title

        mobj = re.match(self._VALID_URL, url)
        uploader_id = (
            mobj.group('uploader_id')
            or self._html_search_regex(r'<a class="fullname"[^>]+title="([^"]+)"', webpage, 'uploader name', fatal=False))

        if uploader_id:
            uploader_url = base_url + '/' + uploader_id

        uploader = self._html_search_regex(r'<a class="fullname"[^>]+title="([^"]+)"', webpage, 'uploader name', fatal=False)

        if uploader:
            title = uploader + ' - ' + title

        view_count = parse_count(self._html_search_regex(r'<span[^>]+class="icon-play[^>]*></span>\s([^<]+)</div>', webpage, 'view count', fatal=False))
        like_count = parse_count(self._html_search_regex(r'<span[^>]+class="icon-heart[^>]*></span>\s([^<]+)</div>', webpage, 'like count', fatal=False))
        repost_count = parse_count(self._html_search_regex(r'<span[^>]+class="icon-retweet[^>]*></span>\s([^<]+)</div>', webpage, 'repost count', fatal=False))
        comment_count = parse_count(self._html_search_regex(r'<span[^>]+class="icon-comment[^>]*></span>\s([^<]+)</div>', webpage, 'repost count', fatal=False))

        thumbnail = base_url + (self._html_search_meta('og:image', webpage, 'thumbnail url')
                                or self._html_search_regex(r'<video[^>]+poster="([^"]+)"', webpage, 'thumbnail url', fatal=False))

        thumbnail = remove_end(thumbnail, '%3Asmall')  # if parsed with regex, it should contain this

        thumbnails = []
        thumbnail_ids = ('thumb', 'small', 'large', 'medium', 'orig')
        for id in thumbnail_ids:
            thumbnails.append({
                'id': id,
                'url': thumbnail + '%3A' + id,
            })

        date = self._html_search_regex(r'<span[^>]+class="tweet-date"[^>]*><a[^>]+title="([^"]+)"', webpage, 'upload date', fatal=False)
        upload_date = unified_strdate(date)
        timestamp = unified_timestamp(date)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'uploader_url': uploader_url,
            'view_count': view_count,
            'like_count': like_count,
            'repost_count': repost_count,
            'comment_count': comment_count,
            'formats': formats,
            'thumbnails': thumbnails,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
        }
