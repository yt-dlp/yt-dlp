# coding: utf-8
from __future__ import unicode_literals

import functools
import re

from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils import (
    extract_attributes,
    int_or_none,
    OnDemandPagedList,
    parse_age_limit,
    strip_or_none,
    try_get,
)


class AsianCrushBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?(?P<host>(?:(?:asiancrush|yuyutv|midnightpulp)\.com|(?:cocoro|retrocrush)\.tv))'
    _KALTURA_KEYS = [
        'video_url', 'progressive_url', 'download_url', 'thumbnail_url',
        'widescreen_thumbnail_url', 'screencap_widescreen',
    ]
    _API_SUFFIX = {'retrocrush.tv': '-ott'}

    def _call_api(self, host, endpoint, video_id, query, resource):
        return self._download_json(
            'https://api%s.%s/%s' % (self._API_SUFFIX.get(host, ''), host, endpoint), video_id,
            'Downloading %s JSON metadata' % resource, query=query,
            headers=self.geo_verification_headers())['objects']

    def _download_object_data(self, host, object_id, resource):
        return self._call_api(
            host, 'search', object_id, {'id': object_id}, resource)[0]

    def _get_object_description(self, obj):
        return strip_or_none(obj.get('long_description') or obj.get('short_description'))

    def _parse_video_data(self, video):
        title = video['name']

        entry_id, partner_id = [None] * 2
        for k in self._KALTURA_KEYS:
            k_url = video.get(k)
            if k_url:
                mobj = re.search(r'/p/(\d+)/.+?/entryId/([^/]+)/', k_url)
                if mobj:
                    partner_id, entry_id = mobj.groups()
                    break

        meta_categories = try_get(video, lambda x: x['meta']['categories'], list) or []
        categories = list(filter(None, [c.get('name') for c in meta_categories]))

        show_info = video.get('show_info') or {}

        return {
            '_type': 'url_transparent',
            'url': 'kaltura:%s:%s' % (partner_id, entry_id),
            'ie_key': KalturaIE.ie_key(),
            'id': entry_id,
            'title': title,
            'description': self._get_object_description(video),
            'age_limit': parse_age_limit(video.get('mpaa_rating') or video.get('tv_rating')),
            'categories': categories,
            'series': show_info.get('show_name'),
            'season_number': int_or_none(show_info.get('season_num')),
            'season_id': show_info.get('season_id'),
            'episode_number': int_or_none(show_info.get('episode_num')),
        }


class AsianCrushIE(AsianCrushBaseIE):
    _VALID_URL = r'%s/video/(?:[^/]+/)?0+(?P<id>\d+)v\b' % AsianCrushBaseIE._VALID_URL_BASE
    _TESTS = [{
        'url': 'https://www.asiancrush.com/video/004289v/women-who-flirt',
        'md5': 'c3b740e48d0ba002a42c0b72857beae6',
        'info_dict': {
            'id': '1_y4tmjm5r',
            'ext': 'mp4',
            'title': 'Women Who Flirt',
            'description': 'md5:b65c7e0ae03a85585476a62a186f924c',
            'timestamp': 1496936429,
            'upload_date': '20170608',
            'uploader_id': 'craig@crifkin.com',
            'age_limit': 13,
            'categories': 'count:5',
            'duration': 5812,
        },
    }, {
        'url': 'https://www.asiancrush.com/video/she-was-pretty/011886v-pretty-episode-3/',
        'only_matching': True,
    }, {
        'url': 'https://www.yuyutv.com/video/013886v/the-act-of-killing/',
        'only_matching': True,
    }, {
        'url': 'https://www.yuyutv.com/video/peep-show/013922v-warring-factions/',
        'only_matching': True,
    }, {
        'url': 'https://www.midnightpulp.com/video/010400v/drifters/',
        'only_matching': True,
    }, {
        'url': 'https://www.midnightpulp.com/video/mononoke/016378v-zashikiwarashi-part-1/',
        'only_matching': True,
    }, {
        'url': 'https://www.cocoro.tv/video/the-wonderful-wizard-of-oz/008878v-the-wonderful-wizard-of-oz-ep01/',
        'only_matching': True,
    }, {
        'url': 'https://www.retrocrush.tv/video/true-tears/012328v-i...gave-away-my-tears',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        host, video_id = self._match_valid_url(url).groups()

        if host == 'cocoro.tv':
            webpage = self._download_webpage(url, video_id)
            embed_vars = self._parse_json(self._search_regex(
                r'iEmbedVars\s*=\s*({.+?})', webpage, 'embed vars',
                default='{}'), video_id, fatal=False) or {}
            video_id = embed_vars.get('entry_id') or video_id

        video = self._download_object_data(host, video_id, 'video')
        return self._parse_video_data(video)


class AsianCrushPlaylistIE(AsianCrushBaseIE):
    _VALID_URL = r'%s/series/0+(?P<id>\d+)s\b' % AsianCrushBaseIE._VALID_URL_BASE
    _TESTS = [{
        'url': 'https://www.asiancrush.com/series/006447s/fruity-samurai',
        'info_dict': {
            'id': '6447',
            'title': 'Fruity Samurai',
            'description': 'md5:7535174487e4a202d3872a7fc8f2f154',
        },
        'playlist_count': 13,
    }, {
        'url': 'https://www.yuyutv.com/series/013920s/peep-show/',
        'only_matching': True,
    }, {
        'url': 'https://www.midnightpulp.com/series/016375s/mononoke/',
        'only_matching': True,
    }, {
        'url': 'https://www.cocoro.tv/series/008549s/the-wonderful-wizard-of-oz/',
        'only_matching': True,
    }, {
        'url': 'https://www.retrocrush.tv/series/012355s/true-tears',
        'only_matching': True,
    }]
    _PAGE_SIZE = 1000000000

    def _fetch_page(self, domain, parent_id, page):
        videos = self._call_api(
            domain, 'getreferencedobjects', parent_id, {
                'max': self._PAGE_SIZE,
                'object_type': 'video',
                'parent_id': parent_id,
                'start': page * self._PAGE_SIZE,
            }, 'page %d' % (page + 1))
        for video in videos:
            yield self._parse_video_data(video)

    def _real_extract(self, url):
        host, playlist_id = self._match_valid_url(url).groups()

        if host == 'cocoro.tv':
            webpage = self._download_webpage(url, playlist_id)

            entries = []

            for mobj in re.finditer(
                    r'<a[^>]+href=(["\'])(?P<url>%s.*?)\1[^>]*>' % AsianCrushIE._VALID_URL,
                    webpage):
                attrs = extract_attributes(mobj.group(0))
                if attrs.get('class') == 'clearfix':
                    entries.append(self.url_result(
                        mobj.group('url'), ie=AsianCrushIE.ie_key()))

            title = self._html_search_regex(
                r'(?s)<h1\b[^>]\bid=["\']movieTitle[^>]+>(.+?)</h1>', webpage,
                'title', default=None) or self._og_search_title(
                webpage, default=None) or self._html_search_meta(
                'twitter:title', webpage, 'title',
                default=None) or self._search_regex(
                r'<title>([^<]+)</title>', webpage, 'title', fatal=False)
            if title:
                title = re.sub(r'\s*\|\s*.+?$', '', title)

            description = self._og_search_description(
                webpage, default=None) or self._html_search_meta(
                'twitter:description', webpage, 'description', fatal=False)
        else:
            show = self._download_object_data(host, playlist_id, 'show')
            title = show.get('name')
            description = self._get_object_description(show)
            entries = OnDemandPagedList(
                functools.partial(self._fetch_page, host, playlist_id),
                self._PAGE_SIZE)

        return self.playlist_result(entries, playlist_id, title, description)
