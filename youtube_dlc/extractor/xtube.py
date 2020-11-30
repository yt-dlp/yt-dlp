from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    js_to_json,
    orderedSet,
    parse_duration,
    sanitized_Request,
    str_to_int,
)


class XTubeIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        (?:
                            xtube:|
                            https?://(?:www\.)?xtube\.com/(?:watch\.php\?.*\bv=|video-watch/(?:embedded/)?(?P<display_id>[^/]+)-)
                        )
                        (?P<id>[^/?&#]+)
                    '''

    _TESTS = [{
        # old URL schema
        'url': 'http://www.xtube.com/watch.php?v=kVTUy_G222_',
        'md5': '092fbdd3cbe292c920ef6fc6a8a9cdab',
        'info_dict': {
            'id': 'kVTUy_G222_',
            'ext': 'mp4',
            'title': 'strange erotica',
            'description': 'contains:an ET kind of thing',
            'uploader': 'greenshowers',
            'duration': 450,
            'view_count': int,
            'comment_count': int,
            'age_limit': 18,
        }
    }, {
        # new URL schema
        'url': 'http://www.xtube.com/video-watch/strange-erotica-625837',
        'only_matching': True,
    }, {
        'url': 'xtube:625837',
        'only_matching': True,
    }, {
        'url': 'xtube:kVTUy_G222_',
        'only_matching': True,
    }, {
        'url': 'https://www.xtube.com/video-watch/embedded/milf-tara-and-teen-shared-and-cum-covered-extreme-bukkake-32203482?embedsize=big',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        if not display_id:
            display_id = video_id

        if video_id.isdigit() and len(video_id) < 11:
            url_pattern = 'http://www.xtube.com/video-watch/-%s'
        else:
            url_pattern = 'http://www.xtube.com/watch.php?v=%s'

        webpage = self._download_webpage(
            url_pattern % video_id, display_id, headers={
                'Cookie': 'age_verified=1; cookiesAccepted=1',
            })

        title, thumbnail, duration = [None] * 3

        config = self._parse_json(self._search_regex(
            r'playerConf\s*=\s*({.+?})\s*,\s*(?:\n|loaderConf)', webpage, 'config',
            default='{}'), video_id, transform_source=js_to_json, fatal=False)
        if config:
            config = config.get('mainRoll')
            if isinstance(config, dict):
                title = config.get('title')
                thumbnail = config.get('poster')
                duration = int_or_none(config.get('duration'))
                sources = config.get('sources') or config.get('format')

        if not isinstance(sources, dict):
            sources = self._parse_json(self._search_regex(
                r'(["\'])?sources\1?\s*:\s*(?P<sources>{.+?}),',
                webpage, 'sources', group='sources'), video_id,
                transform_source=js_to_json)

        formats = []
        for format_id, format_url in sources.items():
            formats.append({
                'url': format_url,
                'format_id': format_id,
                'height': int_or_none(format_id),
            })
        self._remove_duplicate_formats(formats)
        self._sort_formats(formats)

        if not title:
            title = self._search_regex(
                (r'<h1>\s*(?P<title>[^<]+?)\s*</h1>', r'videoTitle\s*:\s*(["\'])(?P<title>.+?)\1'),
                webpage, 'title', group='title')
        description = self._og_search_description(
            webpage, default=None) or self._html_search_meta(
            'twitter:description', webpage, default=None) or self._search_regex(
            r'</h1>\s*<p>([^<]+)', webpage, 'description', fatal=False)
        uploader = self._search_regex(
            (r'<input[^>]+name="contentOwnerId"[^>]+value="([^"]+)"',
             r'<span[^>]+class="nickname"[^>]*>([^<]+)'),
            webpage, 'uploader', fatal=False)
        if not duration:
            duration = parse_duration(self._search_regex(
                r'<dt>Runtime:?</dt>\s*<dd>([^<]+)</dd>',
                webpage, 'duration', fatal=False))
        view_count = str_to_int(self._search_regex(
            (r'["\']viewsCount["\'][^>]*>(\d+)\s+views',
             r'<dt>Views:?</dt>\s*<dd>([\d,\.]+)</dd>'),
            webpage, 'view count', fatal=False))
        comment_count = str_to_int(self._html_search_regex(
            r'>Comments? \(([\d,\.]+)\)<',
            webpage, 'comment count', fatal=False))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'duration': duration,
            'view_count': view_count,
            'comment_count': comment_count,
            'age_limit': 18,
            'formats': formats,
        }


class XTubeUserIE(InfoExtractor):
    IE_DESC = 'XTube user profile'
    _VALID_URL = r'https?://(?:www\.)?xtube\.com/profile/(?P<id>[^/]+-\d+)'
    _TEST = {
        'url': 'http://www.xtube.com/profile/greenshowers-4056496',
        'info_dict': {
            'id': 'greenshowers-4056496',
            'age_limit': 18,
        },
        'playlist_mincount': 154,
    }

    def _real_extract(self, url):
        user_id = self._match_id(url)

        entries = []
        for pagenum in itertools.count(1):
            request = sanitized_Request(
                'http://www.xtube.com/profile/%s/videos/%d' % (user_id, pagenum),
                headers={
                    'Cookie': 'popunder=4',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': url,
                })

            page = self._download_json(
                request, user_id, 'Downloading videos JSON page %d' % pagenum)

            html = page.get('html')
            if not html:
                break

            for video_id in orderedSet([video_id for _, video_id in re.findall(
                    r'data-plid=(["\'])(.+?)\1', html)]):
                entries.append(self.url_result('xtube:%s' % video_id, XTubeIE.ie_key()))

            page_count = int_or_none(page.get('pageCount'))
            if not page_count or pagenum == page_count:
                break

        playlist = self.playlist_result(entries, user_id)
        playlist['age_limit'] = 18
        return playlist
