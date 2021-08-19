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
import random


class NitterIE(InfoExtractor):
    # Taken from https://github.com/zedeus/nitter/wiki/Instances

    NON_HTTP_INSTANCES = (
        '3nzoldnxplag42gqjs23xvghtzf6t6yzssrtytnntc6ppc7xxuoneoad.onion',
        'nitter.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd.onion',
        'nitter7bryz3jv7e3uekphigvmoyoem4al3fynerxkj22dmoxoq553qd.onion',
        'npf37k3mtzwxreiw52ccs5ay4e6qt2fkcs2ndieurdyn2cuzzsfyfvid.onion',
        'nitter.v6vgyqpa7yefkorazmg5d5fimstmvm2vtbirt6676mt7qmllrcnwycqd.onion',
        'i23nv6w3juvzlw32xzoxcqzktegd4i4fu3nmnc2ewv4ggiu4ledwklad.onion',
        '26oq3gioiwcmfojub37nz5gzbkdiqp7fue5kvye7d4txv4ny6fb4wwid.onion',

        'nitter.i2p',
        'u6ikd6zndl3c4dsdq4mmujpntgeevdk5qzkfb57r4tnfeccrn2qa.b32.i2p',

        'nitterlgj3n5fgwesu3vxc5h67ruku33nqaoeoocae2mvlzhsu6k7fqd.onion',
    )

    HTTP_INSTANCES = (
        'nitter.42l.fr',
        'nitter.pussthecat.org',
        'nitter.nixnet.services',
        'nitter.mastodont.cat',
        'nitter.tedomum.net',
        'nitter.fdn.fr',
        'nitter.1d4.us',
        'nitter.kavin.rocks',
        'tweet.lambda.dance',
        'nitter.cc',
        'nitter.vxempire.xyz',
        'nitter.unixfox.eu',
        'nitter.domain.glass',
        'nitter.himiko.cloud',
        'nitter.eu',
        'nitter.namazso.eu',
        'nitter.mailstation.de',
        'nitter.actionsack.com',
        'nitter.cattube.org',
        'nitter.dark.fail',
        'birdsite.xanny.family',
        'nitter.40two.app',
        'nitter.skrep.in',

        # not in the list anymore
        'nitter.snopyta.org',
    )

    DEAD_INSTANCES = (
        # maintenance
        'nitter.ethibox.fr',

        # official, rate limited
        'nitter.net',
        # offline
        'nitter.13ad.de',
        'nitter.weaponizedhumiliation.com',
    )

    INSTANCES = NON_HTTP_INSTANCES + HTTP_INSTANCES + DEAD_INSTANCES

    _INSTANCES_RE = '(?:' + '|'.join([re.escape(instance) for instance in INSTANCES]) + ')'
    _VALID_URL = r'https?://%(instance)s/(?P<uploader_id>.+)/status/(?P<id>[0-9]+)(#.)?' % {'instance': _INSTANCES_RE}
    current_instance = random.choice(HTTP_INSTANCES)

    _TESTS = [
        {
            # GIF (wrapped in mp4)
            'url': 'https://%s/firefox/status/1314279897502629888#m' % current_instance,
            'info_dict': {
                'id': '1314279897502629888',
                'ext': 'mp4',
                'title': 'Firefox 🔥 - You know the old saying, if you see something say something. Now you actually can with the YouTube regrets extension. \n\nReport harmful YouTube recommendations so others can avoid watching them. ➡️ https://mzl.la/3iFIiyg\n\n#UnfckTheInternet',
                'description': 'You know the old saying, if you see something say something. Now you actually can with the YouTube regrets extension. \n\nReport harmful YouTube recommendations so others can avoid watching them. ➡️ https://mzl.la/3iFIiyg\n\n#UnfckTheInternet',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Firefox 🔥',
                'uploader_id': 'firefox',
                'uploader_url': 'https://%s/firefox' % current_instance,
                'upload_date': '20201008',
                'timestamp': 1602183720,
            },
        }, {  # normal video
            'url': 'https://%s/Le___Doc/status/1299715685392756737#m' % current_instance,
            'info_dict': {
                'id': '1299715685392756737',
                'ext': 'mp4',
                'title': 'Le Doc - "Je ne prédis jamais rien"\nD Raoult, Août 2020...',
                'description': '"Je ne prédis jamais rien"\nD Raoult, Août 2020...',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Le Doc',
                'uploader_id': 'Le___Doc',
                'uploader_url': 'https://%s/Le___Doc' % current_instance,
                'upload_date': '20200829',
                'timestamp': 1598711341,
                'view_count': int,
                'like_count': int,
                'repost_count': int,
                'comment_count': int,
            },
        }, {  # video embed in a "Streaming Political Ads" box
            'url': 'https://%s/mozilla/status/1321147074491092994#m' % current_instance,
            'info_dict': {
                'id': '1321147074491092994',
                'ext': 'mp4',
                'title': "Mozilla - Are you being targeted with weird, ominous or just plain annoying political ads while streaming your favorite shows?\n\nThis isn't a real political ad, but if you're watching streaming TV in the U.S., chances are you've seen quite a few. \n\nLearn more ➡️ https://mzl.la/StreamingAds",
                'description': "Are you being targeted with weird, ominous or just plain annoying political ads while streaming your favorite shows?\n\nThis isn't a real political ad, but if you're watching streaming TV in the U.S., chances are you've seen quite a few. \n\nLearn more ➡️ https://mzl.la/StreamingAds",
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Mozilla',
                'uploader_id': 'mozilla',
                'uploader_url': 'https://%s/mozilla' % current_instance,
                'upload_date': '20201027',
                'timestamp': 1603820982
            },
        }, {  # not the first tweet but main-tweet
            'url': 'https://%s/TheNaturalNu/status/1379050895539724290#m' % current_instance,
            'info_dict': {
                'id': '1379050895539724290',
                'ext': 'mp4',
                'title': 'Dorothy Zbornak - This had me hollering!!',
                'description': 'This had me hollering!!',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Dorothy Zbornak',
                'uploader_id': 'TheNaturalNu',
                'uploader_url': 'https://%s/TheNaturalNu' % current_instance,
                'timestamp': 1617626329,
                'upload_date': '20210405'
            }
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        parsed_url = compat_urlparse.urlparse(url)
        base_url = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)

        self._set_cookie(parsed_url.netloc, 'hlsPlayback', 'on')
        full_webpage = self._download_webpage(url, video_id)

        main_tweet_start = full_webpage.find('class="main-tweet"')
        if main_tweet_start > 0:
            webpage = full_webpage[main_tweet_start:]
        if not webpage:
            webpage = full_webpage

        video_url = '%s%s' % (base_url, self._html_search_regex(r'(?:<video[^>]+data-url|<source[^>]+src)="([^"]+)"', webpage, 'video url'))
        ext = determine_ext(video_url)

        if ext == 'unknown_video':
            formats = self._extract_m3u8_formats(video_url, video_id, ext='mp4')
        else:
            formats = [{
                'url': video_url,
                'ext': ext
            }]

        title = self._og_search_description(full_webpage)
        if not title:
            title = self._html_search_regex(r'<div class="tweet-content[^>]+>([^<]+)</div>', webpage, 'title')
        description = title

        mobj = re.match(self._VALID_URL, url)
        uploader_id = (
            mobj.group('uploader_id')
            or self._html_search_regex(r'<a class="fullname"[^>]+title="([^"]+)"', webpage, 'uploader name', fatal=False)
        )

        if uploader_id:
            uploader_url = '%s/%s' % (base_url, uploader_id)

        uploader = self._html_search_regex(r'<a class="fullname"[^>]+title="([^"]+)"', webpage, 'uploader name', fatal=False)

        if uploader:
            title = '%s - %s' % (uploader, title)

        view_count = parse_count(self._html_search_regex(r'<span[^>]+class="icon-play[^>]*></span>\s([^<]+)</div>', webpage, 'view count', fatal=False))
        like_count = parse_count(self._html_search_regex(r'<span[^>]+class="icon-heart[^>]*></span>\s([^<]+)</div>', webpage, 'like count', fatal=False))
        repost_count = parse_count(self._html_search_regex(r'<span[^>]+class="icon-retweet[^>]*></span>\s([^<]+)</div>', webpage, 'repost count', fatal=False))
        comment_count = parse_count(self._html_search_regex(r'<span[^>]+class="icon-comment[^>]*></span>\s([^<]+)</div>', webpage, 'repost count', fatal=False))

        thumbnail = self._html_search_meta('og:image', full_webpage, 'thumbnail url')
        if not thumbnail:
            thumbnail = '%s%s' % (base_url, self._html_search_regex(r'<video[^>]+poster="([^"]+)"', webpage, 'thumbnail url', fatal=False))
            thumbnail = remove_end(thumbnail, '%3Asmall')

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
