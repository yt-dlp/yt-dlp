# coding: utf-8
from __future__ import unicode_literals

import re

from .amp import AMPIE
from .common import InfoExtractor
from ..utils import (
    parse_duration,
    parse_iso8601,
    try_get,
)


class AbcNewsVideoIE(AMPIE):
    IE_NAME = 'abcnews:video'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            abcnews\.go\.com/
                            (?:
                                (?:[^/]+/)*video/(?P<display_id>[0-9a-z-]+)-|
                                video/(?:embed|itemfeed)\?.*?\bid=
                            )|
                            fivethirtyeight\.abcnews\.go\.com/video/embed/\d+/
                        )
                        (?P<id>\d+)
                    '''

    _TESTS = [{
        'url': 'http://abcnews.go.com/ThisWeek/video/week-exclusive-irans-foreign-minister-zarif-20411932',
        'info_dict': {
            'id': '20411932',
            'ext': 'mp4',
            'display_id': 'week-exclusive-irans-foreign-minister-zarif',
            'title': '\'This Week\' Exclusive: Iran\'s Foreign Minister Zarif',
            'description': 'George Stephanopoulos goes one-on-one with Iranian Foreign Minister Dr. Javad Zarif.',
            'duration': 180,
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1380454200,
            'upload_date': '20130929',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://abcnews.go.com/video/embed?id=46979033',
        'only_matching': True,
    }, {
        'url': 'http://abcnews.go.com/2020/video/2020-husband-stands-teacher-jail-student-affairs-26119478',
        'only_matching': True,
    }, {
        'url': 'http://abcnews.go.com/video/itemfeed?id=46979033',
        'only_matching': True,
    }, {
        'url': 'https://abcnews.go.com/GMA/News/video/history-christmas-story-67894761',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id = mobj.group('display_id')
        video_id = mobj.group('id')
        info_dict = self._extract_feed_info(
            'http://abcnews.go.com/video/itemfeed?id=%s' % video_id)
        info_dict.update({
            'id': video_id,
            'display_id': display_id,
        })
        return info_dict


class AbcNewsIE(InfoExtractor):
    IE_NAME = 'abcnews'
    _VALID_URL = r'https?://abcnews\.go\.com/(?:[^/]+/)+(?P<display_id>[0-9a-z-]+)/story\?id=(?P<id>\d+)'

    _TESTS = [{
        # Youtube Embeds
        'url': 'https://abcnews.go.com/Entertainment/peter-billingsley-child-actor-christmas-story-hollywood-power/story?id=51286501',
        'info_dict': {
            'id': '51286501',
            'title': "Peter Billingsley: From child actor in 'A Christmas Story' to Hollywood power player",
            'description': 'Billingsley went from a child actor to Hollywood power player.',
        },
        'playlist_count': 5,
    }, {
        'url': 'http://abcnews.go.com/Entertainment/justin-timberlake-performs-stop-feeling-eurovision-2016/story?id=39125818',
        'info_dict': {
            'id': '38897857',
            'ext': 'mp4',
            'title': 'Justin Timberlake Drops Hints For Secret Single',
            'description': 'Lara Spencer reports the buzziest stories of the day in "GMA" Pop News.',
            'upload_date': '20160505',
            'timestamp': 1462442280,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
            # The embedded YouTube video is blocked due to copyright issues
            'playlist_items': '1',
        },
        'add_ie': ['AbcNewsVideo'],
    }, {
        'url': 'http://abcnews.go.com/Technology/exclusive-apple-ceo-tim-cook-iphone-cracking-software/story?id=37173343',
        'only_matching': True,
    }, {
        # inline.type == 'video'
        'url': 'http://abcnews.go.com/Technology/exclusive-apple-ceo-tim-cook-iphone-cracking-software/story?id=37173343',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        story_id = self._match_id(url)
        webpage = self._download_webpage(url, story_id)
        story = self._parse_json(self._search_regex(
            r"window\['__abcnews__'\]\s*=\s*({.+?});",
            webpage, 'data'), story_id)['page']['content']['story']['everscroll'][0]
        article_contents = story.get('articleContents') or {}

        def entries():
            featured_video = story.get('featuredVideo') or {}
            feed = try_get(featured_video, lambda x: x['video']['feed'])
            if feed:
                yield {
                    '_type': 'url',
                    'id': featured_video.get('id'),
                    'title': featured_video.get('name'),
                    'url': feed,
                    'thumbnail': featured_video.get('images'),
                    'description': featured_video.get('description'),
                    'timestamp': parse_iso8601(featured_video.get('uploadDate')),
                    'duration': parse_duration(featured_video.get('duration')),
                    'ie_key': AbcNewsVideoIE.ie_key(),
                }

            for inline in (article_contents.get('inlines') or []):
                inline_type = inline.get('type')
                if inline_type == 'iframe':
                    iframe_url = try_get(inline, lambda x: x['attrs']['src'])
                    if iframe_url:
                        yield self.url_result(iframe_url)
                elif inline_type == 'video':
                    video_id = inline.get('id')
                    if video_id:
                        yield {
                            '_type': 'url',
                            'id': video_id,
                            'url': 'http://abcnews.go.com/video/embed?id=' + video_id,
                            'thumbnail': inline.get('imgSrc') or inline.get('imgDefault'),
                            'description': inline.get('description'),
                            'duration': parse_duration(inline.get('duration')),
                            'ie_key': AbcNewsVideoIE.ie_key(),
                        }

        return self.playlist_result(
            entries(), story_id, article_contents.get('headline'),
            article_contents.get('subHead'))
