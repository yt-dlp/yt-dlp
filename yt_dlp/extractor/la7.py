# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    parse_duration,
    smuggle_url,
    unified_strdate,
)


class LA7IE(InfoExtractor):
    IE_NAME = 'la7.it'
    _VALID_URL = r'''(?x)(https?://)?(?:
        (?:www\.)?la7\.it/([^/]+)/(?:rivedila7|video)/|
        tg\.la7\.it/repliche-tgla7\?id=
    )(?P<id>.+)'''

    _TESTS = [{
        # 'src' is a plain URL
        'url': 'http://www.la7.it/crozza/video/inccool8-02-10-2015-163722',
        'md5': '8b613ffc0c4bf9b9e377169fc19c214c',
        'info_dict': {
            'id': '0_42j6wd36',
            'ext': 'mp4',
            'title': 'Inc.Cool8',
            'description': 'Benvenuti nell\'incredibile mondo della INC. COOL. 8. dove “INC.” sta per “Incorporated” “COOL” sta per “fashion” ed Eight sta per il gesto atletico',
            'thumbnail': 're:^https?://.*',
            'uploader_id': 'kdla7pillole@iltrovatore.it',
            'timestamp': 1443814869,
            'upload_date': '20151002',
        },
    }, {
        'url': 'http://www.la7.it/omnibus/rivedila7/omnibus-news-02-07-2016-189077',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        if not url.startswith('http'):
            url = '%s//%s' % (self.http_scheme(), url)

        webpage = self._download_webpage(url, video_id)

        player_data = self._search_regex(
            [r'(?s)videoParams\s*=\s*({.+?});', r'videoLa7\(({[^;]+})\);'],
            webpage, 'player data')
        vid = self._search_regex(r'vid\s*:\s*"(.+?)",', player_data, 'vid')

        return {
            '_type': 'url_transparent',
            'url': smuggle_url('kaltura:103:%s' % vid, {
                'service_url': 'http://nkdam.iltrovatore.it',
            }),
            'id': video_id,
            'title': self._og_search_title(webpage, default=None),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'ie_key': 'Kaltura',
        }


class LA7PodcastEpisodeIE(InfoExtractor):
    IE_NAME = 'la7.it:pod:episode'
    _VALID_URL = r'''(?x)(https?://)?
        (?:www\.)?la7\.it/[^/]+/podcast/([^/]+-)?(?P<id>\d+)'''

    _TESTS = [{
        'url': 'https://www.la7.it/voicetown/podcast/la-carezza-delle-memoria-di-carlo-verdone-23-03-2021-371497',
        'md5': '7737d4d79b3c1a34b3de3e16297119ed',
        'info_dict': {
            'id': '371497',
            'ext': 'mp3',
            'title': '"La carezza delle memoria" di Carlo Verdone',
            'description': 'md5:5abf07c3c551a687db80af3f9ceb7d52',
            'thumbnail': 'https://www.la7.it/sites/default/files/podcast/371497.jpg',
            'upload_date': '20210323',
        },
    }, {
        # embed url
        'url': 'https://www.la7.it/embed/podcast/371497',
        'only_matching': True,
    }, {
        # date already in the title
        'url': 'https://www.la7.it/propagandalive/podcast/lintervista-di-diego-bianchi-ad-annalisa-cuzzocrea-puntata-del-1932021-20-03-2021-371130',
        'only_matching': True,
    }, {
        # title same as show_title
        'url': 'https://www.la7.it/otto-e-mezzo/podcast/otto-e-mezzo-26-03-2021-372340',
        'only_matching': True,
    }]

    def _extract_info(self, webpage, video_id=None, ppn=None):
        if not video_id:
            video_id = self._search_regex(
                r'data-nid=([\'"])(?P<vid>\d+)\1',
                webpage, 'video_id', group='vid')

        media_url = self._search_regex(
            (r'src:\s*([\'"])(?P<url>.+?mp3.+?)\1',
             r'data-podcast=([\'"])(?P<url>.+?mp3.+?)\1'),
            webpage, 'media_url', group='url')
        ext = determine_ext(media_url)
        formats = [{
            'url': media_url,
            'format_id': ext,
            'ext': ext,
        }]
        self._sort_formats(formats)

        title = self._html_search_regex(
            (r'<div class="title">(?P<title>.+?)</',
             r'<title>(?P<title>[^<]+)</title>',
             r'title:\s*([\'"])(?P<title>.+?)\1'),
            webpage, 'title', group='title')

        description = (
            self._html_search_regex(
                (r'<div class="description">(.+?)</div>',
                 r'<div class="description-mobile">(.+?)</div>',
                 r'<div class="box-txt">([^<]+?)</div>',
                 r'<div class="field-content"><p>(.+?)</p></div>'),
                webpage, 'description', default=None)
            or self._html_search_meta('description', webpage))

        thumb = self._html_search_regex(
            (r'<div class="podcast-image"><img src="(.+?)"></div>',
             r'<div class="container-embed"[^<]+url\((.+?)\);">',
             r'<div class="field-content"><img src="(.+?)"'),
            webpage, 'thumbnail', fatal=False, default=None)

        duration = parse_duration(self._html_search_regex(
            r'<span class="(?:durata|duration)">([\d:]+)</span>',
            webpage, 'duration', fatal=False, default=None))

        date = self._html_search_regex(
            r'class="data">\s*(?:<span>)?([\d\.]+)\s*</',
            webpage, 'date', default=None)

        date_alt = self._search_regex(
            r'(\d+[\./]\d+[\./]\d+)', title, 'date_alt', default=None)
        ppn = ppn or self._search_regex(
            r'ppN:\s*([\'"])(?P<ppn>.+?)\1',
            webpage, 'ppn', group='ppn', default=None)
        # if the date is not in the title
        # and title is the same as the show_title
        # add the date to the title
        if date and not date_alt and ppn and ppn.lower() == title.lower():
            title += ' del %s' % date
        return {
            'id': video_id,
            'title': title,
            'description': description,
            'duration': float_or_none(duration),
            'formats': formats,
            'thumbnail': thumb,
            'upload_date': unified_strdate(date),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        return self._extract_info(webpage, video_id)


class LA7PodcastIE(LA7PodcastEpisodeIE):
    IE_NAME = 'la7.it:podcast'
    _VALID_URL = r'(https?://)?(www\.)?la7\.it/(?P<id>[^/]+)/podcast/?(?:$|[#?])'

    _TESTS = [{
        'url': 'https://www.la7.it/propagandalive/podcast',
        'info_dict': {
            'id': 'propagandalive',
            'title': "Propaganda Live",
        },
        'playlist_count': 10,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        title = (
            self._html_search_regex(
                r'<h1.*?>(.+?)</h1>', webpage, 'title', fatal=False, default=None)
            or self._og_search_title(webpage))
        ppn = self._search_regex(
            r'window\.ppN\s*=\s*([\'"])(?P<ppn>.+?)\1',
            webpage, 'ppn', group='ppn', default=None)

        entries = []
        for episode in re.finditer(
                r'<div class="container-podcast-property">([\s\S]+?)(?:</div>\s*){3}',
                webpage):
            entries.append(self._extract_info(episode.group(1), ppn=ppn))

        return self.playlist_result(entries, playlist_id, title)
