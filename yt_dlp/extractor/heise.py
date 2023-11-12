import urllib.parse

from .common import InfoExtractor
from .kaltura import KalturaIE
from .youtube import YoutubeIE
from ..utils import (
    NO_DEFAULT,
    determine_ext,
    int_or_none,
    parse_iso8601,
    smuggle_url,
    xpath_text,
)


class HeiseIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?heise\.de/(?:[^/]+/)+[^/]+-(?P<id>[0-9]+)\.html'
    _TESTS = [{
        # kaltura embed
        'url': 'http://www.heise.de/video/artikel/Podcast-c-t-uplink-3-3-Owncloud-Tastaturen-Peilsender-Smartphone-2404147.html',
        'info_dict': {
            'id': '1_kkrq94sm',
            'ext': 'mp4',
            'title': "Podcast: c't uplink 3.3 – Owncloud / Tastaturen / Peilsender Smartphone",
            'timestamp': 1512734959,
            'upload_date': '20171208',
            'description': 'md5:c934cbfb326c669c2bcabcbe3d3fcd20',
            'thumbnail': 're:^https?://.*/thumbnail/.*',
            'duration': 2845,
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # YouTube embed
        'url': 'http://www.heise.de/newsticker/meldung/Netflix-In-20-Jahren-vom-Videoverleih-zum-TV-Revolutionaer-3814130.html',
        'md5': 'e403d2b43fea8e405e88e3f8623909f1',
        'info_dict': {
            'id': '6kmWbXleKW4',
            'ext': 'mp4',
            'title': 'Neu im September 2017 | Netflix',
            'description': 'md5:d6852d1f96bb80760608eed3b907437c',
            'upload_date': '20170830',
            'uploader': 'Netflix Deutschland, Österreich und Schweiz',
            'uploader_id': 'netflixdach',
            'categories': ['Entertainment'],
            'tags': 'count:27',
            'age_limit': 0,
            'availability': 'public',
            'comment_count': int,
            'channel_id': 'UCZqgRlLcvO3Fnx_npQJygcQ',
            'thumbnail': 'https://i.ytimg.com/vi_webp/6kmWbXleKW4/maxresdefault.webp',
            'uploader_url': 'http://www.youtube.com/user/netflixdach',
            'playable_in_embed': True,
            'live_status': 'not_live',
            'channel_url': 'https://www.youtube.com/channel/UCZqgRlLcvO3Fnx_npQJygcQ',
            'view_count': int,
            'channel': 'Netflix Deutschland, Österreich und Schweiz',
            'channel_follower_count': int,
            'like_count': int,
            'duration': 67,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.heise.de/video/artikel/nachgehakt-Wie-sichert-das-c-t-Tool-Restric-tor-Windows-10-ab-3700244.html',
        'info_dict': {
            'id': '1_ntrmio2s',
            'ext': 'mp4',
            'title': "nachgehakt: Wie sichert das c't-Tool Restric'tor Windows 10 ab?",
            'description': 'md5:47e8ffb6c46d85c92c310a512d6db271',
            'timestamp': 1512470717,
            'upload_date': '20171205',
            'duration': 786,
            'view_count': int,
            'thumbnail': 're:^https?://.*/thumbnail/.*',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # FIXME: Video m3u8 fails to download; issue with Kaltura extractor
        'url': 'https://www.heise.de/ct/artikel/c-t-uplink-20-8-Staubsaugerroboter-Xiaomi-Vacuum-2-AR-Brille-Meta-2-und-Android-rooten-3959893.html',
        'info_dict': {
            'id': '1_59mk80sf',
            'ext': 'mp4',
            'title': "c't uplink 20.8: Staubsaugerroboter Xiaomi Vacuum 2, AR-Brille Meta 2 und Android rooten",
            'description': 'md5:f50fe044d3371ec73a8f79fcebd74afc',
            'timestamp': 1517567237,
            'upload_date': '20180202',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # videout
        'url': 'https://www.heise.de/ct/artikel/c-t-uplink-3-8-Anonyme-SIM-Karten-G-Sync-Monitore-Citizenfour-2440327.html',
        'info_dict': {
            'id': '2440327',
            'ext': 'mp4',
            'title': 'c\'t uplink 3.8: Anonyme SIM-Karten, G-Sync-Monitore, Citizenfour',
            'thumbnail': 'http://www.heise.de/imagine/yxM2qmol0xV3iFB7qFb70dGvXjc/gallery/',
            'description': 'md5:fa164d8c8707dff124a9626d39205f5d',
            'timestamp': 1414825200,
            'upload_date': '20141101',
        }
    }, {
        'url': 'http://www.heise.de/ct/artikel/c-t-uplink-3-3-Owncloud-Tastaturen-Peilsender-Smartphone-2403911.html',
        'only_matching': True,
    }, {
        'url': 'http://www.heise.de/newsticker/meldung/c-t-uplink-Owncloud-Tastaturen-Peilsender-Smartphone-2404251.html?wt_mc=rss.ho.beitrag.atom',
        'only_matching': True,
    }, {
        'url': 'http://www.heise.de/ct/ausgabe/2016-12-Spiele-3214137.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        def extract_title(default=NO_DEFAULT):
            title = self._html_search_meta(
                ('fulltitle', 'title'), webpage, default=None)
            if not title or title == "c't":
                title = self._search_regex(
                    r'<div[^>]+class="videoplayerjw"[^>]+data-title="([^"]+)"',
                    webpage, 'title', default=None)
            if not title:
                title = self._html_search_regex(
                    r'<h1[^>]+\bclass=["\']article_page_title[^>]+>(.+?)<',
                    webpage, 'title', default=default)
            return title

        title = extract_title(default=None)
        description = self._og_search_description(
            webpage, default=None) or self._html_search_meta(
            'description', webpage)

        def _make_kaltura_result(kaltura_url):
            return {
                '_type': 'url_transparent',
                'url': smuggle_url(kaltura_url, {'source_url': url}),
                'ie_key': KalturaIE.ie_key(),
                'title': title,
                'description': description,
            }

        kaltura_url = KalturaIE._extract_url(webpage)
        if kaltura_url:
            return _make_kaltura_result(kaltura_url)

        kaltura_id = self._search_regex(
            r'entry-id=(["\'])(?P<id>(?:(?!\1).)+)\1', webpage, 'kaltura id',
            default=None, group='id')
        if kaltura_id:
            return _make_kaltura_result('kaltura:2238431:%s' % kaltura_id)

        yt_urls = tuple(YoutubeIE._extract_embed_urls(url, webpage))
        if yt_urls:
            return self.playlist_from_matches(
                yt_urls, video_id, title, ie=YoutubeIE.ie_key())

        title = extract_title()
        api_params = urllib.parse.parse_qs(
            self._search_regex(r'/videout/feed\.json\?([^\']+)', webpage, 'feed params', default=None) or '')
        if not api_params or 'container' not in api_params or 'sequenz' not in api_params:
            container_id = self._search_regex(
                r'<div class="videoplayerjw"[^>]+data-container="([0-9]+)"',
                webpage, 'container ID')

            sequenz_id = self._search_regex(
                r'<div class="videoplayerjw"[^>]+data-sequenz="([0-9]+)"',
                webpage, 'sequenz ID')
            api_params = {
                'container': container_id,
                'sequenz': sequenz_id,
            }
        doc = self._download_xml(
            'http://www.heise.de/videout/feed', video_id, query=api_params)

        formats = []
        for source_node in doc.findall('.//{http://rss.jwpcdn.com/}source'):
            label = source_node.attrib['label']
            height = int_or_none(self._search_regex(
                r'^(.*?_)?([0-9]+)p$', label, 'height', default=None))
            video_url = source_node.attrib['file']
            ext = determine_ext(video_url, '')
            formats.append({
                'url': video_url,
                'format_note': label,
                'format_id': '%s_%s' % (ext, label),
                'height': height,
            })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': (xpath_text(doc, './/{http://rss.jwpcdn.com/}image')
                          or self._og_search_thumbnail(webpage)),
            'timestamp': parse_iso8601(
                self._html_search_meta('date', webpage)),
            'formats': formats,
        }
