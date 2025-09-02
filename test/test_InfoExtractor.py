#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import http.server
import threading

from test.helper import FakeYDL, expect_dict, expect_value, http_server_port
from yt_dlp.compat import compat_etree_fromstring
from yt_dlp.extractor import YoutubeIE, get_info_extractor
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    RegexNotFoundError,
    encode_data_uri,
    strip_jsonp,
)

TEAPOT_RESPONSE_STATUS = 418
TEAPOT_RESPONSE_BODY = "<h1>418 I'm a teapot</h1>"


class InfoExtractorTestRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/teapot':
            self.send_response(TEAPOT_RESPONSE_STATUS)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(TEAPOT_RESPONSE_BODY.encode())
        elif self.path == '/fake.m3u8':
            self.send_response(200)
            self.send_header('Content-Length', '1024')
            self.end_headers()
            self.wfile.write(1024 * b'\x00')
        elif self.path == '/bipbop.m3u8':
            with open('test/testdata/m3u8/bipbop_16x9.m3u8', 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            assert False


class DummyIE(InfoExtractor):
    def _sort_formats(self, formats, field_preference=[]):
        self._downloader.sort_formats(
            {'formats': formats, '_format_sort_fields': field_preference})


class TestInfoExtractor(unittest.TestCase):
    def setUp(self):
        self.ie = DummyIE(FakeYDL())

    def test_ie_key(self):
        self.assertEqual(get_info_extractor(YoutubeIE.ie_key()), YoutubeIE)

    def test_get_netrc_login_info(self):
        for params in [
            {'usenetrc': True, 'netrc_location': './test/testdata/netrc/netrc'},
            {'netrc_cmd': f'{sys.executable} ./test/testdata/netrc/print_netrc.py'},
        ]:
            ie = DummyIE(FakeYDL(params))
            self.assertEqual(ie._get_netrc_login_info(netrc_machine='normal_use'), ('user', 'pass'))
            self.assertEqual(ie._get_netrc_login_info(netrc_machine='empty_user'), ('', 'pass'))
            self.assertEqual(ie._get_netrc_login_info(netrc_machine='empty_pass'), ('user', ''))
            self.assertEqual(ie._get_netrc_login_info(netrc_machine='both_empty'), ('', ''))
            self.assertEqual(ie._get_netrc_login_info(netrc_machine='nonexistent'), (None, None))

    def test_html_search_regex(self):
        html = '<p id="foo">Watch this <a href="http://www.youtube.com/watch?v=BaW_jenozKc">video</a></p>'
        search = lambda re, *args: self.ie._html_search_regex(re, html, *args)
        self.assertEqual(search(r'<p id="foo">(.+?)</p>', 'foo'), 'Watch this video')

    def test_opengraph(self):
        ie = self.ie
        html = '''
            <meta name="og:title" content='Foo'/>
            <meta content="Some video's description " name="og:description"/>
            <meta property='og:image' content='http://domain.com/pic.jpg?key1=val1&amp;key2=val2'/>
            <meta content='application/x-shockwave-flash' property='og:video:type'>
            <meta content='Foo' property=og:foobar>
            <meta name="og:test1" content='foo > < bar'/>
            <meta name="og:test2" content="foo >//< bar"/>
            <meta property=og-test3 content='Ill-formatted opengraph'/>
            <meta property=og:test4 content=unquoted-value/>
            '''
        self.assertEqual(ie._og_search_title(html), 'Foo')
        self.assertEqual(ie._og_search_description(html), 'Some video\'s description ')
        self.assertEqual(ie._og_search_thumbnail(html), 'http://domain.com/pic.jpg?key1=val1&key2=val2')
        self.assertEqual(ie._og_search_video_url(html, default=None), None)
        self.assertEqual(ie._og_search_property('foobar', html), 'Foo')
        self.assertEqual(ie._og_search_property('test1', html), 'foo > < bar')
        self.assertEqual(ie._og_search_property('test2', html), 'foo >//< bar')
        self.assertEqual(ie._og_search_property('test3', html), 'Ill-formatted opengraph')
        self.assertEqual(ie._og_search_property(('test0', 'test1'), html), 'foo > < bar')
        self.assertRaises(RegexNotFoundError, ie._og_search_property, 'test0', html, None, fatal=True)
        self.assertRaises(RegexNotFoundError, ie._og_search_property, ('test0', 'test00'), html, None, fatal=True)
        self.assertEqual(ie._og_search_property('test4', html), 'unquoted-value')

    def test_html_search_meta(self):
        ie = self.ie
        html = '''
            <meta name="a" content="1" />
            <meta name='b' content='2'>
            <meta name="c" content='3'>
            <meta name=d content='4'>
            <meta property="e" content='5' >
            <meta content="6" name="f">
        '''

        self.assertEqual(ie._html_search_meta('a', html), '1')
        self.assertEqual(ie._html_search_meta('b', html), '2')
        self.assertEqual(ie._html_search_meta('c', html), '3')
        self.assertEqual(ie._html_search_meta('d', html), '4')
        self.assertEqual(ie._html_search_meta('e', html), '5')
        self.assertEqual(ie._html_search_meta('f', html), '6')
        self.assertEqual(ie._html_search_meta(('a', 'b', 'c'), html), '1')
        self.assertEqual(ie._html_search_meta(('c', 'b', 'a'), html), '3')
        self.assertEqual(ie._html_search_meta(('z', 'x', 'c'), html), '3')
        self.assertRaises(RegexNotFoundError, ie._html_search_meta, 'z', html, None, fatal=True)
        self.assertRaises(RegexNotFoundError, ie._html_search_meta, ('z', 'x'), html, None, fatal=True)

    def test_search_json_ld_realworld(self):
        _TESTS = [
            # https://github.com/ytdl-org/youtube-dl/issues/23306
            (
                r'''<script type="application/ld+json">
{
"@context": "http://schema.org/",
"@type": "VideoObject",
"name": "1 On 1 With Kleio",
"url": "https://www.eporner.com/hd-porn/xN49A1cT3eB/1-On-1-With-Kleio/",
"duration": "PT0H12M23S",
"thumbnailUrl": ["https://static-eu-cdn.eporner.com/thumbs/static4/7/78/780/780814/9_360.jpg", "https://imggen.eporner.com/780814/1920/1080/9.jpg"],
"contentUrl": "https://gvideo.eporner.com/xN49A1cT3eB/xN49A1cT3eB.mp4",
"embedUrl": "https://www.eporner.com/embed/xN49A1cT3eB/1-On-1-With-Kleio/",
"image": "https://static-eu-cdn.eporner.com/thumbs/static4/7/78/780/780814/9_360.jpg",
"width": "1920",
"height": "1080",
"encodingFormat": "mp4",
"bitrate": "6617kbps",
"isFamilyFriendly": "False",
"description": "Kleio Valentien",
"uploadDate": "2015-12-05T21:24:35+01:00",
"interactionStatistic": {
"@type": "InteractionCounter",
"interactionType": { "@type": "http://schema.org/WatchAction" },
"userInteractionCount": 1120958
}, "aggregateRating": {
"@type": "AggregateRating",
"ratingValue": "88",
"ratingCount": "630",
"bestRating": "100",
"worstRating": "0"
}, "actor": [{
"@type": "Person",
"name": "Kleio Valentien",
"url": "https://www.eporner.com/pornstar/kleio-valentien/"
}]}
                </script>''',
                {
                    'title': '1 On 1 With Kleio',
                    'description': 'Kleio Valentien',
                    'url': 'https://gvideo.eporner.com/xN49A1cT3eB/xN49A1cT3eB.mp4',
                    'timestamp': 1449347075,
                    'duration': 743.0,
                    'view_count': 1120958,
                    'width': 1920,
                    'height': 1080,
                },
                {},
            ),
            (
                r'''<script type="application/ld+json">
      {
      "@context": "https://schema.org",
      "@graph": [
      {
      "@type": "NewsArticle",
      "mainEntityOfPage": {
      "@type": "WebPage",
      "@id": "https://www.ant1news.gr/Society/article/620286/symmoria-anilikon-dikigoros-thymaton-ithelan-na-toys-apoteleiosoyn"
      },
      "headline": "Συμμορία ανηλίκων – δικηγόρος θυμάτων: ήθελαν να τους αποτελειώσουν",
      "name": "Συμμορία ανηλίκων – δικηγόρος θυμάτων: ήθελαν να τους αποτελειώσουν",
      "description": "Τα παιδιά δέχθηκαν την επίθεση επειδή αρνήθηκαν να γίνουν μέλη της συμμορίας, ανέφερε ο Γ. Ζαχαρόπουλος.",
      "image": {
      "@type": "ImageObject",
      "url": "https://ant1media.azureedge.net/imgHandler/1100/a635c968-be71-447c-bf9c-80d843ece21e.jpg",
      "width": 1100,
      "height": 756            },
      "datePublished": "2021-11-10T08:50:00+03:00",
      "dateModified": "2021-11-10T08:52:53+03:00",
      "author": {
      "@type": "Person",
      "@id": "https://www.ant1news.gr/",
      "name": "Ant1news",
      "image": "https://www.ant1news.gr/images/logo-e5d7e4b3e714c88e8d2eca96130142f6.png",
      "url": "https://www.ant1news.gr/"
      },
      "publisher": {
      "@type": "Organization",
      "@id": "https://www.ant1news.gr#publisher",
      "name": "Ant1news",
      "url": "https://www.ant1news.gr",
      "logo": {
      "@type": "ImageObject",
      "url": "https://www.ant1news.gr/images/logo-e5d7e4b3e714c88e8d2eca96130142f6.png",
      "width": 400,
      "height": 400                },
      "sameAs": [
      "https://www.facebook.com/Ant1news.gr",
      "https://twitter.com/antennanews",
      "https://www.youtube.com/channel/UC0smvAbfczoN75dP0Hw4Pzw",
      "https://www.instagram.com/ant1news/"
      ]
      },

      "keywords": "μαχαίρωμα,συμμορία ανηλίκων,ΕΙΔΗΣΕΙΣ,ΕΙΔΗΣΕΙΣ ΣΗΜΕΡΑ,ΝΕΑ,Κοινωνία - Ant1news",


      "articleSection": "Κοινωνία"
      }
      ]
      }
                </script>''',
                {
                    'timestamp': 1636523400,
                    'title': 'md5:91fe569e952e4d146485740ae927662b',
                },
                {'expected_type': 'NewsArticle'},
            ),
            (
                r'''<script type="application/ld+json">
                {"url":"/vrtnu/a-z/het-journaal/2021/het-journaal-het-journaal-19u-20211231/",
                "name":"Het journaal 19u",
                "description":"Het journaal 19u van vrijdag 31 december 2021.",
                "potentialAction":{"url":"https://vrtnu.page.link/pfVy6ihgCAJKgHqe8","@type":"ShareAction"},
                "mainEntityOfPage":{"@id":"1640092242445","@type":"WebPage"},
                "publication":[{
                    "startDate":"2021-12-31T19:00:00.000+01:00",
                    "endDate":"2022-01-30T23:55:00.000+01:00",
                    "publishedBy":{"name":"een","@type":"Organization"},
                    "publishedOn":{"url":"https://www.vrt.be/vrtnu/","name":"VRT NU","@type":"BroadcastService"},
                    "@id":"pbs-pub-3a7ec233-da95-4c1e-9b2b-cf5fdfebcbe8",
                    "@type":"BroadcastEvent"
                    }],
                "video":{
                    "name":"Het journaal - Aflevering 365 (Seizoen 2021)",
                    "description":"Het journaal 19u van vrijdag 31 december 2021. Bekijk aflevering 365 van seizoen 2021 met VRT NU via de site of app.",
                    "thumbnailUrl":"//images.vrt.be/width1280/2021/12/31/80d5ed00-6a64-11ec-b07d-02b7b76bf47f.jpg",
                    "expires":"2022-01-30T23:55:00.000+01:00",
                    "hasPart":[
                        {"name":"Explosie Turnhout","startOffset":70,"@type":"Clip"},
                        {"name":"Jaarwisseling","startOffset":440,"@type":"Clip"},
                        {"name":"Natuurbranden Colorado","startOffset":1179,"@type":"Clip"},
                        {"name":"Klimaatverandering","startOffset":1263,"@type":"Clip"},
                        {"name":"Zacht weer","startOffset":1367,"@type":"Clip"},
                        {"name":"Financiële balans","startOffset":1383,"@type":"Clip"},
                        {"name":"Club Brugge","startOffset":1484,"@type":"Clip"},
                        {"name":"Mentale gezondheid bij topsporters","startOffset":1575,"@type":"Clip"},
                        {"name":"Olympische Winterspelen","startOffset":1728,"@type":"Clip"},
                        {"name":"Sober oudjaar in Nederland","startOffset":1873,"@type":"Clip"}
                        ],
                    "duration":"PT34M39.23S",
                    "uploadDate":"2021-12-31T19:00:00.000+01:00",
                    "@id":"vid-9457d0c6-b8ac-4aba-b5e1-15aa3a3295b5",
                    "@type":"VideoObject"
                },
                "genre":["Nieuws en actua"],
                "episodeNumber":365,
                "partOfSeries":{"name":"Het journaal","@id":"222831405527","@type":"TVSeries"},
                "partOfSeason":{"name":"Seizoen 2021","@id":"961809365527","@type":"TVSeason"},
                "@context":"https://schema.org","@id":"961685295527","@type":"TVEpisode"}</script>
                ''',
                {
                    'chapters': [
                        {'title': 'Explosie Turnhout', 'start_time': 70, 'end_time': 440},
                        {'title': 'Jaarwisseling', 'start_time': 440, 'end_time': 1179},
                        {'title': 'Natuurbranden Colorado', 'start_time': 1179, 'end_time': 1263},
                        {'title': 'Klimaatverandering', 'start_time': 1263, 'end_time': 1367},
                        {'title': 'Zacht weer', 'start_time': 1367, 'end_time': 1383},
                        {'title': 'Financiële balans', 'start_time': 1383, 'end_time': 1484},
                        {'title': 'Club Brugge', 'start_time': 1484, 'end_time': 1575},
                        {'title': 'Mentale gezondheid bij topsporters', 'start_time': 1575, 'end_time': 1728},
                        {'title': 'Olympische Winterspelen', 'start_time': 1728, 'end_time': 1873},
                        {'title': 'Sober oudjaar in Nederland', 'start_time': 1873, 'end_time': 2079.23},
                    ],
                    'title': 'Het journaal - Aflevering 365 (Seizoen 2021)',
                }, {},
            ),
            (
                # test multiple thumbnails in a list
                r'''
<script type="application/ld+json">
{"@context":"https://schema.org",
"@type":"VideoObject",
"thumbnailUrl":["https://www.rainews.it/cropgd/640x360/dl/img/2021/12/30/1640886376927_GettyImages.jpg"]}
</script>''',
                {
                    'thumbnails': [{'url': 'https://www.rainews.it/cropgd/640x360/dl/img/2021/12/30/1640886376927_GettyImages.jpg'}],
                },
                {},
            ),
            (
                # test single thumbnail
                r'''
<script type="application/ld+json">
{"@context":"https://schema.org",
"@type":"VideoObject",
"thumbnailUrl":"https://www.rainews.it/cropgd/640x360/dl/img/2021/12/30/1640886376927_GettyImages.jpg"}
</script>''',
                {
                    'thumbnails': [{'url': 'https://www.rainews.it/cropgd/640x360/dl/img/2021/12/30/1640886376927_GettyImages.jpg'}],
                },
                {},
            ),
            (
                # test thumbnail_url key without URL scheme
                r'''
<script type="application/ld+json">
{
"@context": "https://schema.org",
"@type": "VideoObject",
"thumbnail_url": "//www.nobelprize.org/images/12693-landscape-medium-gallery.jpg"
}</script>''',
                {
                    'thumbnails': [{'url': 'https://www.nobelprize.org/images/12693-landscape-medium-gallery.jpg'}],
                },
                {},
            ),
        ]
        for html, expected_dict, search_json_ld_kwargs in _TESTS:
            expect_dict(
                self,
                self.ie._search_json_ld(html, None, **search_json_ld_kwargs),
                expected_dict,
            )

    def test_download_json(self):
        uri = encode_data_uri(b'{"foo": "blah"}', 'application/json')
        self.assertEqual(self.ie._download_json(uri, None), {'foo': 'blah'})
        uri = encode_data_uri(b'callback({"foo": "blah"})', 'application/javascript')
        self.assertEqual(self.ie._download_json(uri, None, transform_source=strip_jsonp), {'foo': 'blah'})
        uri = encode_data_uri(b'{"foo": invalid}', 'application/json')
        self.assertRaises(ExtractorError, self.ie._download_json, uri, None)
        self.assertEqual(self.ie._download_json(uri, None, fatal=False), None)

    def test_parse_html5_media_entries(self):
        # inline video tag
        expect_dict(
            self,
            self.ie._parse_html5_media_entries(
                'https://127.0.0.1/video.html',
                r'<html><video src="/vid.mp4" /></html>', None)[0],
            {
                'formats': [{
                    'url': 'https://127.0.0.1/vid.mp4',
                }],
            })

        # from https://www.r18.com/
        # with kpbs in label
        expect_dict(
            self,
            self.ie._parse_html5_media_entries(
                'https://www.r18.com/',
                r'''
                <video id="samplevideo_amateur" class="js-samplevideo video-js vjs-default-skin vjs-big-play-centered" controls preload="auto" width="400" height="225" poster="//pics.r18.com/digital/amateur/mgmr105/mgmr105jp.jpg">
                    <source id="video_source" src="https://awscc3001.r18.com/litevideo/freepv/m/mgm/mgmr105/mgmr105_sm_w.mp4" type="video/mp4"  res="240" label="300kbps">
                    <source id="video_source" src="https://awscc3001.r18.com/litevideo/freepv/m/mgm/mgmr105/mgmr105_dm_w.mp4" type="video/mp4"  res="480" label="1000kbps">
                    <source id="video_source" src="https://awscc3001.r18.com/litevideo/freepv/m/mgm/mgmr105/mgmr105_dmb_w.mp4" type="video/mp4"  res="740" label="1500kbps">
                    <p>Your browser does not support the video tag.</p>
                </video>
                ''', None)[0],
            {
                'formats': [{
                    'url': 'https://awscc3001.r18.com/litevideo/freepv/m/mgm/mgmr105/mgmr105_sm_w.mp4',
                    'ext': 'mp4',
                    'format_id': '300kbps',
                    'height': 240,
                    'tbr': 300,
                }, {
                    'url': 'https://awscc3001.r18.com/litevideo/freepv/m/mgm/mgmr105/mgmr105_dm_w.mp4',
                    'ext': 'mp4',
                    'format_id': '1000kbps',
                    'height': 480,
                    'tbr': 1000,
                }, {
                    'url': 'https://awscc3001.r18.com/litevideo/freepv/m/mgm/mgmr105/mgmr105_dmb_w.mp4',
                    'ext': 'mp4',
                    'format_id': '1500kbps',
                    'height': 740,
                    'tbr': 1500,
                }],
                'thumbnail': '//pics.r18.com/digital/amateur/mgmr105/mgmr105jp.jpg',
            })

        # from https://www.csfd.cz/
        # with width and height
        expect_dict(
            self,
            self.ie._parse_html5_media_entries(
                'https://www.csfd.cz/',
                r'''
                <video width="770" height="328" preload="none" controls  poster="https://img.csfd.cz/files/images/film/video/preview/163/344/163344118_748d20.png?h360" >
                    <source src="https://video.csfd.cz/files/videos/157/750/157750813/163327358_eac647.mp4" type="video/mp4" width="640" height="360">
                    <source src="https://video.csfd.cz/files/videos/157/750/157750813/163327360_3d2646.mp4" type="video/mp4" width="1280" height="720">
                    <source src="https://video.csfd.cz/files/videos/157/750/157750813/163327356_91f258.mp4" type="video/mp4" width="1920" height="1080">
                    <source src="https://video.csfd.cz/files/videos/157/750/157750813/163327359_962b4a.webm" type="video/webm" width="640" height="360">
                    <source src="https://video.csfd.cz/files/videos/157/750/157750813/163327361_6feee0.webm" type="video/webm" width="1280" height="720">
                    <source src="https://video.csfd.cz/files/videos/157/750/157750813/163327357_8ab472.webm" type="video/webm" width="1920" height="1080">
                    <track src="https://video.csfd.cz/files/subtitles/163/344/163344115_4c388b.srt" type="text/x-srt" kind="subtitles" srclang="cs" label="cs">
                </video>
                ''', None)[0],
            {
                'formats': [{
                    'url': 'https://video.csfd.cz/files/videos/157/750/157750813/163327358_eac647.mp4',
                    'ext': 'mp4',
                    'width': 640,
                    'height': 360,
                }, {
                    'url': 'https://video.csfd.cz/files/videos/157/750/157750813/163327360_3d2646.mp4',
                    'ext': 'mp4',
                    'width': 1280,
                    'height': 720,
                }, {
                    'url': 'https://video.csfd.cz/files/videos/157/750/157750813/163327356_91f258.mp4',
                    'ext': 'mp4',
                    'width': 1920,
                    'height': 1080,
                }, {
                    'url': 'https://video.csfd.cz/files/videos/157/750/157750813/163327359_962b4a.webm',
                    'ext': 'webm',
                    'width': 640,
                    'height': 360,
                }, {
                    'url': 'https://video.csfd.cz/files/videos/157/750/157750813/163327361_6feee0.webm',
                    'ext': 'webm',
                    'width': 1280,
                    'height': 720,
                }, {
                    'url': 'https://video.csfd.cz/files/videos/157/750/157750813/163327357_8ab472.webm',
                    'ext': 'webm',
                    'width': 1920,
                    'height': 1080,
                }],
                'subtitles': {
                    'cs': [{'url': 'https://video.csfd.cz/files/subtitles/163/344/163344115_4c388b.srt'}],
                },
                'thumbnail': 'https://img.csfd.cz/files/images/film/video/preview/163/344/163344118_748d20.png?h360',
            })

        # from https://tamasha.com/v/Kkdjw
        # with height in label
        expect_dict(
            self,
            self.ie._parse_html5_media_entries(
                'https://tamasha.com/v/Kkdjw',
                r'''
                <video crossorigin="anonymous">
                        <source src="https://s-v2.tamasha.com/statics/videos_file/19/8f/Kkdjw_198feff8577d0057536e905cce1fb61438dd64e0_n_240.mp4" type="video/mp4" label="AUTO" res="0"/>
                                <source src="https://s-v2.tamasha.com/statics/videos_file/19/8f/Kkdjw_198feff8577d0057536e905cce1fb61438dd64e0_n_240.mp4" type="video/mp4"
                                        label="240p" res="240"/>
                                <source src="https://s-v2.tamasha.com/statics/videos_file/20/00/Kkdjw_200041c66f657fc967db464d156eafbc1ed9fe6f_n_144.mp4" type="video/mp4"
                                        label="144p" res="144"/>
                </video>
                ''', None)[0],
            {
                'formats': [{
                    'url': 'https://s-v2.tamasha.com/statics/videos_file/19/8f/Kkdjw_198feff8577d0057536e905cce1fb61438dd64e0_n_240.mp4',
                }, {
                    'url': 'https://s-v2.tamasha.com/statics/videos_file/19/8f/Kkdjw_198feff8577d0057536e905cce1fb61438dd64e0_n_240.mp4',
                    'ext': 'mp4',
                    'format_id': '240p',
                    'height': 240,
                }, {
                    'url': 'https://s-v2.tamasha.com/statics/videos_file/20/00/Kkdjw_200041c66f657fc967db464d156eafbc1ed9fe6f_n_144.mp4',
                    'ext': 'mp4',
                    'format_id': '144p',
                    'height': 144,
                }],
            })

        # from https://www.directvnow.com
        # with data-src
        expect_dict(
            self,
            self.ie._parse_html5_media_entries(
                'https://www.directvnow.com',
                r'''
                <video id="vid1" class="header--video-masked active" muted playsinline>
                    <source data-src="https://cdn.directv.com/content/dam/dtv/prod/website_directvnow-international/videos/DTVN_hdr_HBO_v3.mp4" type="video/mp4" />
                </video>
                ''', None)[0],
            {
                'formats': [{
                    'ext': 'mp4',
                    'url': 'https://cdn.directv.com/content/dam/dtv/prod/website_directvnow-international/videos/DTVN_hdr_HBO_v3.mp4',
                }],
            })

        # from https://www.directvnow.com
        # with data-src
        expect_dict(
            self,
            self.ie._parse_html5_media_entries(
                'https://www.directvnow.com',
                r'''
                <video id="vid1" class="header--video-masked active" muted playsinline>
                    <source data-src="https://cdn.directv.com/content/dam/dtv/prod/website_directvnow-international/videos/DTVN_hdr_HBO_v3.mp4" type="video/mp4" />
                </video>
                ''', None)[0],
            {
                'formats': [{
                    'url': 'https://cdn.directv.com/content/dam/dtv/prod/website_directvnow-international/videos/DTVN_hdr_HBO_v3.mp4',
                    'ext': 'mp4',
                }],
            })

        # from https://www.klarna.com/uk/
        # with data-video-src
        expect_dict(
            self,
            self.ie._parse_html5_media_entries(
                'https://www.directvnow.com',
                r'''
                <video loop autoplay muted class="responsive-video block-kl__video video-on-medium">
                    <source src="" data-video-desktop data-video-src="https://www.klarna.com/uk/wp-content/uploads/sites/11/2019/01/KL062_Smooth3_0_DogWalking_5s_920x080_.mp4" type="video/mp4" />
                </video>
                ''', None)[0],
            {
                'formats': [{
                    'url': 'https://www.klarna.com/uk/wp-content/uploads/sites/11/2019/01/KL062_Smooth3_0_DogWalking_5s_920x080_.mp4',
                    'ext': 'mp4',
                }],
            })

        # from https://0000.studio/
        # with type attribute but without extension in URL
        expect_dict(
            self,
            self.ie._parse_html5_media_entries(
                'https://0000.studio',
                r'''
                <video src="https://d1ggyt9m8pwf3g.cloudfront.net/protected/ap-northeast-1:1864af40-28d5-492b-b739-b32314b1a527/archive/clip/838db6a7-8973-4cd6-840d-8517e4093c92"
                    controls="controls" type="video/mp4" preload="metadata" autoplay="autoplay" playsinline class="object-contain">
                </video>
                ''', None)[0],
            {
                'formats': [{
                    'url': 'https://d1ggyt9m8pwf3g.cloudfront.net/protected/ap-northeast-1:1864af40-28d5-492b-b739-b32314b1a527/archive/clip/838db6a7-8973-4cd6-840d-8517e4093c92',
                    'ext': 'mp4',
                }],
            })

    def test_extract_jwplayer_data_realworld(self):
        # from http://www.suffolk.edu/sjc/
        expect_dict(
            self,
            self.ie._extract_jwplayer_data(r'''
                <script type='text/javascript'>
                    jwplayer('my-video').setup({
                        file: 'rtmp://192.138.214.154/live/sjclive',
                        fallback: 'true',
                        width: '95%',
                      aspectratio: '16:9',
                      primary: 'flash',
                      mediaid:'XEgvuql4'
                    });
                </script>
                ''', None, require_title=False),
            {
                'id': 'XEgvuql4',
                'formats': [{
                    'url': 'rtmp://192.138.214.154/live/sjclive',
                    'ext': 'flv',
                }],
            })

        # from https://www.pornoxo.com/videos/7564/striptease-from-sexy-secretary/
        expect_dict(
            self,
            self.ie._extract_jwplayer_data(r'''
<script type="text/javascript">
    jwplayer("mediaplayer").setup({
        'videoid': "7564",
        'width': "100%",
        'aspectratio': "16:9",
        'stretching': "exactfit",
        'autostart': 'false',
        'flashplayer': "https://t04.vipstreamservice.com/jwplayer/v5.10/player.swf",
        'file': "https://cdn.pornoxo.com/key=MF+oEbaxqTKb50P-w9G3nA,end=1489689259,ip=104.199.146.27/ip=104.199.146.27/speed=6573765/buffer=3.0/2009-12/4b2157147afe5efa93ce1978e0265289c193874e02597.flv",
        'image': "https://t03.vipstreamservice.com/thumbs/pxo-full/2009-12/14/a4b2157147afe5efa93ce1978e0265289c193874e02597.flv-full-13.jpg",
        'filefallback': "https://cdn.pornoxo.com/key=9ZPsTR5EvPLQrBaak2MUGA,end=1489689259,ip=104.199.146.27/ip=104.199.146.27/speed=6573765/buffer=3.0/2009-12/m_4b2157147afe5efa93ce1978e0265289c193874e02597.mp4",
        'logo.hide': true,
        'skin': "https://t04.vipstreamservice.com/jwplayer/skin/modieus-blk.zip",
        'plugins': "https://t04.vipstreamservice.com/jwplayer/dock/dockableskinnableplugin.swf",
        'dockableskinnableplugin.piclink': "/index.php?key=ajax-videothumbsn&vid=7564&data=2009-12--14--4b2157147afe5efa93ce1978e0265289c193874e02597.flv--17370",
        'controlbar': 'bottom',
        'modes': [
            {type: 'flash', src: 'https://t04.vipstreamservice.com/jwplayer/v5.10/player.swf'}
        ],
        'provider': 'http'
    });
    //noinspection JSAnnotator
    invideo.setup({
        adsUrl: "/banner-iframe/?zoneId=32",
        adsUrl2: "",
        autostart: false
    });
</script>
            ''', 'dummy', require_title=False),
            {
                'thumbnail': 'https://t03.vipstreamservice.com/thumbs/pxo-full/2009-12/14/a4b2157147afe5efa93ce1978e0265289c193874e02597.flv-full-13.jpg',
                'formats': [{
                    'url': 'https://cdn.pornoxo.com/key=MF+oEbaxqTKb50P-w9G3nA,end=1489689259,ip=104.199.146.27/ip=104.199.146.27/speed=6573765/buffer=3.0/2009-12/4b2157147afe5efa93ce1978e0265289c193874e02597.flv',
                    'ext': 'flv',
                }],
            })

        # from http://www.indiedb.com/games/king-machine/videos
        expect_dict(
            self,
            self.ie._extract_jwplayer_data(r'''
<script>
jwplayer("mediaplayer").setup({"abouttext":"Visit Indie DB","aboutlink":"http:\/\/www.indiedb.com\/","displaytitle":false,"autostart":false,"repeat":false,"title":"king machine trailer 1","sharing":{"link":"http:\/\/www.indiedb.com\/games\/king-machine\/videos\/king-machine-trailer-1","code":"<iframe width=\"560\" height=\"315\" src=\"http:\/\/www.indiedb.com\/media\/iframe\/1522983\" frameborder=\"0\" allowfullscreen><\/iframe><br><a href=\"http:\/\/www.indiedb.com\/games\/king-machine\/videos\/king-machine-trailer-1\">king machine trailer 1 - Indie DB<\/a>"},"related":{"file":"http:\/\/rss.indiedb.com\/media\/recommended\/1522983\/feed\/rss.xml","dimensions":"160x120","onclick":"link"},"sources":[{"file":"http:\/\/cdn.dbolical.com\/cache\/videos\/games\/1\/50\/49678\/encode_mp4\/king-machine-trailer.mp4","label":"360p SD","default":"true"},{"file":"http:\/\/cdn.dbolical.com\/cache\/videos\/games\/1\/50\/49678\/encode720p_mp4\/king-machine-trailer.mp4","label":"720p HD"}],"image":"http:\/\/media.indiedb.com\/cache\/images\/games\/1\/50\/49678\/thumb_620x2000\/king-machine-trailer.mp4.jpg","advertising":{"client":"vast","tag":"http:\/\/ads.intergi.com\/adrawdata\/3.0\/5205\/4251742\/0\/1013\/ADTECH;cors=yes;width=560;height=315;referring_url=http:\/\/www.indiedb.com\/games\/king-machine\/videos\/king-machine-trailer-1;content_url=http:\/\/www.indiedb.com\/games\/king-machine\/videos\/king-machine-trailer-1;media_id=1522983;title=king+machine+trailer+1;device=__DEVICE__;model=__MODEL__;os=Windows+OS;osversion=__OSVERSION__;ua=__UA__;ip=109.171.17.81;uniqueid=1522983;tags=__TAGS__;number=58cac25928151;time=1489683033"},"width":620,"height":349}).once("play", function(event) {
            videoAnalytics("play");
}).once("complete", function(event) {
    videoAnalytics("completed");
});
</script>
                ''', 'dummy'),
            {
                'title': 'king machine trailer 1',
                'thumbnail': 'http://media.indiedb.com/cache/images/games/1/50/49678/thumb_620x2000/king-machine-trailer.mp4.jpg',
                'formats': [{
                    'url': 'http://cdn.dbolical.com/cache/videos/games/1/50/49678/encode_mp4/king-machine-trailer.mp4',
                    'height': 360,
                    'ext': 'mp4',
                }, {
                    'url': 'http://cdn.dbolical.com/cache/videos/games/1/50/49678/encode720p_mp4/king-machine-trailer.mp4',
                    'height': 720,
                    'ext': 'mp4',
                }],
            })

    def test_parse_m3u8_formats(self):
        _TEST_CASES = [
            (
                # https://github.com/ytdl-org/youtube-dl/issues/11995
                # http://teamcoco.com/video/clueless-gamer-super-bowl-for-honor
                'img_bipbop_adv_example_fmp4',
                'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                [{
                    # 60kbps (bitrate not provided in m3u8); sorted as worst because it's grouped with lowest bitrate video track
                    'format_id': 'aud1-English',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/a1/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'language': 'en',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'audio_ext': 'mp4',
                    'source_preference': 0,
                }, {
                    # 192kbps (bitrate not provided in m3u8)
                    'format_id': 'aud3-English',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/a3/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'language': 'en',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'audio_ext': 'mp4',
                    'source_preference': 1,
                }, {
                    # 384kbps (bitrate not provided in m3u8); sorted as best because it's grouped with the highest bitrate video track
                    'format_id': 'aud2-English',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/a2/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'language': 'en',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'audio_ext': 'mp4',
                    'source_preference': 2,
                }, {
                    'format_id': '530',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v2/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 480,
                    'height': 270,
                    'vcodec': 'avc1.640015',
                }, {
                    'format_id': '561',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v2/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 480,
                    'height': 270,
                    'vcodec': 'avc1.640015',
                }, {
                    'format_id': '753',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v2/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 480,
                    'height': 270,
                    'vcodec': 'avc1.640015',
                }, {
                    'format_id': '895',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v3/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 640,
                    'height': 360,
                    'vcodec': 'avc1.64001e',
                }, {
                    'format_id': '926',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v3/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 640,
                    'height': 360,
                    'vcodec': 'avc1.64001e',
                }, {
                    'format_id': '1118',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v3/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 640,
                    'height': 360,
                    'vcodec': 'avc1.64001e',
                }, {
                    'format_id': '1265',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v4/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 768,
                    'height': 432,
                    'vcodec': 'avc1.64001e',
                }, {
                    'format_id': '1295',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v4/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 768,
                    'height': 432,
                    'vcodec': 'avc1.64001e',
                }, {
                    'format_id': '1487',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v4/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 768,
                    'height': 432,
                    'vcodec': 'avc1.64001e',
                }, {
                    'format_id': '2168',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v5/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 960,
                    'height': 540,
                    'vcodec': 'avc1.640020',
                }, {
                    'format_id': '2198',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v5/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 960,
                    'height': 540,
                    'vcodec': 'avc1.640020',
                }, {
                    'format_id': '2390',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v5/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 960,
                    'height': 540,
                    'vcodec': 'avc1.640020',
                }, {
                    'format_id': '3168',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v6/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1280,
                    'height': 720,
                    'vcodec': 'avc1.640020',
                }, {
                    'format_id': '3199',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v6/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1280,
                    'height': 720,
                    'vcodec': 'avc1.640020',
                }, {
                    'format_id': '3391',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v6/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1280,
                    'height': 720,
                    'vcodec': 'avc1.640020',
                }, {
                    'format_id': '4670',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v7/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.64002a',
                }, {
                    'format_id': '4701',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v7/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.64002a',
                }, {
                    'format_id': '4893',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v7/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.64002a',
                }, {
                    'format_id': '6170',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v8/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.64002a',
                }, {
                    'format_id': '6200',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v8/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.64002a',
                }, {
                    'format_id': '6392',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v8/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.64002a',
                }, {
                    'format_id': '7968',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v9/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.64002a',
                }, {
                    'format_id': '7998',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v9/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.64002a',
                }, {
                    'format_id': '8190',
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/v9/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.64002a',
                }],
                {},
            ),
            (
                'bipbop_16x9',
                'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
                [{
                    'format_id': 'bipbop_audio-BipBop Audio 2',
                    'format_index': None,
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/alternate_audio_aac/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
                    'language': 'eng',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'preference': None,
                    'quality': None,
                    'vcodec': 'none',
                    'audio_ext': 'mp4',
                    'video_ext': 'none',
                }, {
                    'format_id': '41',
                    'format_index': None,
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/gear0/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
                    'tbr': 41.457,
                    'ext': 'mp4',
                    'fps': None,
                    'protocol': 'm3u8_native',
                    'preference': None,
                    'quality': None,
                    'vcodec': 'none',
                    'acodec': 'mp4a.40.2',
                    'audio_ext': 'mp4',
                    'video_ext': 'none',
                    'abr': 41.457,
                }, {
                    'format_id': '263',
                    'format_index': None,
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/gear1/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
                    'tbr': 263.851,
                    'ext': 'mp4',
                    'fps': None,
                    'protocol': 'm3u8_native',
                    'preference': None,
                    'quality': None,
                    'width': 416,
                    'height': 234,
                    'vcodec': 'avc1.4d400d',
                    'acodec': 'mp4a.40.2',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                }, {
                    'format_id': '577',
                    'format_index': None,
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/gear2/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
                    'tbr': 577.61,
                    'ext': 'mp4',
                    'fps': None,
                    'protocol': 'm3u8_native',
                    'preference': None,
                    'quality': None,
                    'width': 640,
                    'height': 360,
                    'vcodec': 'avc1.4d401e',
                    'acodec': 'mp4a.40.2',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                }, {
                    'format_id': '915',
                    'format_index': None,
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/gear3/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
                    'tbr': 915.905,
                    'ext': 'mp4',
                    'fps': None,
                    'protocol': 'm3u8_native',
                    'preference': None,
                    'quality': None,
                    'width': 960,
                    'height': 540,
                    'vcodec': 'avc1.4d401f',
                    'acodec': 'mp4a.40.2',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                }, {
                    'format_id': '1030',
                    'format_index': None,
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/gear4/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
                    'tbr': 1030.138,
                    'ext': 'mp4',
                    'fps': None,
                    'protocol': 'm3u8_native',
                    'preference': None,
                    'quality': None,
                    'width': 1280,
                    'height': 720,
                    'vcodec': 'avc1.4d401f',
                    'acodec': 'mp4a.40.2',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                }, {
                    'format_id': '1924',
                    'format_index': None,
                    'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/gear5/prog_index.m3u8',
                    'manifest_url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
                    'tbr': 1924.009,
                    'ext': 'mp4',
                    'fps': None,
                    'protocol': 'm3u8_native',
                    'preference': None,
                    'quality': None,
                    'width': 1920,
                    'height': 1080,
                    'vcodec': 'avc1.4d401f',
                    'acodec': 'mp4a.40.2',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                }],
                {
                    'en': [{
                        'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/subtitles/eng/prog_index.m3u8',
                        'ext': 'vtt',
                        'protocol': 'm3u8_native',
                    }, {
                        'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/subtitles/eng_forced/prog_index.m3u8',
                        'ext': 'vtt',
                        'protocol': 'm3u8_native',
                    }],
                    'fr': [{
                        'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/subtitles/fra/prog_index.m3u8',
                        'ext': 'vtt',
                        'protocol': 'm3u8_native',
                    }, {
                        'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/subtitles/fra_forced/prog_index.m3u8',
                        'ext': 'vtt',
                        'protocol': 'm3u8_native',
                    }],
                    'es': [{
                        'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/subtitles/spa/prog_index.m3u8',
                        'ext': 'vtt',
                        'protocol': 'm3u8_native',
                    }, {
                        'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/subtitles/spa_forced/prog_index.m3u8',
                        'ext': 'vtt',
                        'protocol': 'm3u8_native',
                    }],
                    'ja': [{
                        'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/subtitles/jpn/prog_index.m3u8',
                        'ext': 'vtt',
                        'protocol': 'm3u8_native',
                    }, {
                        'url': 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/subtitles/jpn_forced/prog_index.m3u8',
                        'ext': 'vtt',
                        'protocol': 'm3u8_native',
                    }],
                },
            ),
        ]

        for m3u8_file, m3u8_url, expected_formats, expected_subs in _TEST_CASES:
            with open(f'./test/testdata/m3u8/{m3u8_file}.m3u8', encoding='utf-8') as f:
                formats, subs = self.ie._parse_m3u8_formats_and_subtitles(
                    f.read(), m3u8_url, ext='mp4')
                self.ie._sort_formats(formats)
                expect_value(self, formats, expected_formats, None)
                expect_value(self, subs, expected_subs, None)

    def test_parse_mpd_formats(self):
        _TEST_CASES = [
            (
                # https://github.com/ytdl-org/youtube-dl/issues/13919
                # Also tests duplicate representation ids, see
                # https://github.com/ytdl-org/youtube-dl/issues/15111
                'float_duration',
                'http://unknown/manifest.mpd',  # mpd_url
                None,  # mpd_base_url
                [{
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'm4a',
                    'format_id': '318597',
                    'format_note': 'DASH audio',
                    'protocol': 'http_dash_segments',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'none',
                    'tbr': 61.587,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': '318597',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'none',
                    'vcodec': 'avc1.42001f',
                    'tbr': 318.597,
                    'width': 340,
                    'height': 192,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': '638590',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'none',
                    'vcodec': 'avc1.42001f',
                    'tbr': 638.59,
                    'width': 512,
                    'height': 288,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': '1022565',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'none',
                    'vcodec': 'avc1.4d001f',
                    'tbr': 1022.565,
                    'width': 688,
                    'height': 384,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': '2046506',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'none',
                    'vcodec': 'avc1.4d001f',
                    'tbr': 2046.506,
                    'width': 1024,
                    'height': 576,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': '3998017',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'none',
                    'vcodec': 'avc1.640029',
                    'tbr': 3998.017,
                    'width': 1280,
                    'height': 720,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': '5997485',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'none',
                    'vcodec': 'avc1.640032',
                    'tbr': 5997.485,
                    'width': 1920,
                    'height': 1080,
                }],
                {},
            ), (
                # https://github.com/ytdl-org/youtube-dl/pull/14844
                'urls_only',
                'http://unknown/manifest.mpd',  # mpd_url
                None,  # mpd_base_url
                [{
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': 'h264_aac_144p_m4s',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc3.42c01e',
                    'tbr': 200,
                    'width': 256,
                    'height': 144,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': 'h264_aac_240p_m4s',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc3.42c01e',
                    'tbr': 400,
                    'width': 424,
                    'height': 240,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': 'h264_aac_360p_m4s',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc3.42c01e',
                    'tbr': 800,
                    'width': 640,
                    'height': 360,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': 'h264_aac_480p_m4s',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc3.42c01e',
                    'tbr': 1200,
                    'width': 856,
                    'height': 480,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': 'h264_aac_576p_m4s',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc3.42c01e',
                    'tbr': 1600,
                    'width': 1024,
                    'height': 576,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': 'h264_aac_720p_m4s',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc3.42c01e',
                    'tbr': 2400,
                    'width': 1280,
                    'height': 720,
                }, {
                    'manifest_url': 'http://unknown/manifest.mpd',
                    'ext': 'mp4',
                    'format_id': 'h264_aac_1080p_m4s',
                    'format_note': 'DASH video',
                    'protocol': 'http_dash_segments',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc3.42c01e',
                    'tbr': 4400,
                    'width': 1920,
                    'height': 1080,
                }],
                {},
            ), (
                # https://github.com/ytdl-org/youtube-dl/issues/20346
                # Media considered unfragmented even though it contains
                # Initialization tag
                'unfragmented',
                'https://v.redd.it/hw1x7rcg7zl21/DASHPlaylist.mpd',  # mpd_url
                'https://v.redd.it/hw1x7rcg7zl21',  # mpd_base_url
                [{
                    'url': 'https://v.redd.it/hw1x7rcg7zl21/audio',
                    'manifest_url': 'https://v.redd.it/hw1x7rcg7zl21/DASHPlaylist.mpd',
                    'ext': 'm4a',
                    'format_id': 'AUDIO-1',
                    'format_note': 'DASH audio',
                    'container': 'm4a_dash',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'none',
                    'tbr': 129.87,
                    'asr': 48000,

                }, {
                    'url': 'https://v.redd.it/hw1x7rcg7zl21/DASH_240',
                    'manifest_url': 'https://v.redd.it/hw1x7rcg7zl21/DASHPlaylist.mpd',
                    'ext': 'mp4',
                    'format_id': 'VIDEO-2',
                    'format_note': 'DASH video',
                    'container': 'mp4_dash',
                    'acodec': 'none',
                    'vcodec': 'avc1.4d401e',
                    'tbr': 608.0,
                    'width': 240,
                    'height': 240,
                    'fps': 30,
                }, {
                    'url': 'https://v.redd.it/hw1x7rcg7zl21/DASH_360',
                    'manifest_url': 'https://v.redd.it/hw1x7rcg7zl21/DASHPlaylist.mpd',
                    'ext': 'mp4',
                    'format_id': 'VIDEO-1',
                    'format_note': 'DASH video',
                    'container': 'mp4_dash',
                    'acodec': 'none',
                    'vcodec': 'avc1.4d401e',
                    'tbr': 804.261,
                    'width': 360,
                    'height': 360,
                    'fps': 30,
                }],
                {},
            ), (
                'subtitles',
                'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/',
                [{
                    'format_id': 'audio=128001',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'ext': 'm4a',
                    'tbr': 128.001,
                    'asr': 48000,
                    'format_note': 'DASH audio',
                    'container': 'm4a_dash',
                    'vcodec': 'none',
                    'acodec': 'mp4a.40.2',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'fragment_base_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/dash/',
                    'protocol': 'http_dash_segments',
                    'audio_ext': 'm4a',
                    'video_ext': 'none',
                    'abr': 128.001,
                }, {
                    'format_id': 'video=100000',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'ext': 'mp4',
                    'width': 336,
                    'height': 144,
                    'tbr': 100,
                    'format_note': 'DASH video',
                    'container': 'mp4_dash',
                    'vcodec': 'avc1.4D401F',
                    'acodec': 'none',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'fragment_base_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/dash/',
                    'protocol': 'http_dash_segments',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                    'vbr': 100,
                }, {
                    'format_id': 'video=326000',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'ext': 'mp4',
                    'width': 562,
                    'height': 240,
                    'tbr': 326,
                    'format_note': 'DASH video',
                    'container': 'mp4_dash',
                    'vcodec': 'avc1.4D401F',
                    'acodec': 'none',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'fragment_base_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/dash/',
                    'protocol': 'http_dash_segments',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                    'vbr': 326,
                }, {
                    'format_id': 'video=698000',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'ext': 'mp4',
                    'width': 844,
                    'height': 360,
                    'tbr': 698,
                    'format_note': 'DASH video',
                    'container': 'mp4_dash',
                    'vcodec': 'avc1.4D401F',
                    'acodec': 'none',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'fragment_base_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/dash/',
                    'protocol': 'http_dash_segments',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                    'vbr': 698,
                }, {
                    'format_id': 'video=1493000',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'ext': 'mp4',
                    'width': 1126,
                    'height': 480,
                    'tbr': 1493,
                    'format_note': 'DASH video',
                    'container': 'mp4_dash',
                    'vcodec': 'avc1.4D401F',
                    'acodec': 'none',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'fragment_base_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/dash/',
                    'protocol': 'http_dash_segments',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                    'vbr': 1493,
                }, {
                    'format_id': 'video=4482000',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'ext': 'mp4',
                    'width': 1688,
                    'height': 720,
                    'tbr': 4482,
                    'format_note': 'DASH video',
                    'container': 'mp4_dash',
                    'vcodec': 'avc1.4D401F',
                    'acodec': 'none',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                    'fragment_base_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/dash/',
                    'protocol': 'http_dash_segments',
                    'video_ext': 'mp4',
                    'audio_ext': 'none',
                    'vbr': 4482,
                }],
                {
                    'en': [
                        {
                            'ext': 'mp4',
                            'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                            'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/manifest.mpd',
                            'fragment_base_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/dash/',
                            'protocol': 'http_dash_segments',
                        },
                    ],
                },
            ),
        ]

        for mpd_file, mpd_url, mpd_base_url, expected_formats, expected_subtitles in _TEST_CASES:
            with open(f'./test/testdata/mpd/{mpd_file}.mpd', encoding='utf-8') as f:
                formats, subtitles = self.ie._parse_mpd_formats_and_subtitles(
                    compat_etree_fromstring(f.read().encode()),
                    mpd_base_url=mpd_base_url, mpd_url=mpd_url)
                self.ie._sort_formats(formats)
                expect_value(self, formats, expected_formats, None)
                expect_value(self, subtitles, expected_subtitles, None)

    def test_parse_ism_formats(self):
        _TEST_CASES = [
            (
                'sintel',
                'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                [{
                    'format_id': 'audio-128',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'ext': 'isma',
                    'tbr': 128,
                    'asr': 48000,
                    'vcodec': 'none',
                    'acodec': 'AACL',
                    'protocol': 'ism',
                    'audio_channels': 2,
                    '_download_params': {
                        'stream_type': 'audio',
                        'duration': 8880746666,
                        'timescale': 10000000,
                        'width': 0,
                        'height': 0,
                        'fourcc': 'AACL',
                        'codec_private_data': '1190',
                        'sampling_rate': 48000,
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video-100',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'ext': 'ismv',
                    'width': 336,
                    'height': 144,
                    'tbr': 100,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 8880746666,
                        'timescale': 10000000,
                        'width': 336,
                        'height': 144,
                        'fourcc': 'AVC1',
                        'codec_private_data': '00000001674D401FDA0544EFFC2D002CBC40000003004000000C03C60CA80000000168EF32C8',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video-326',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'ext': 'ismv',
                    'width': 562,
                    'height': 240,
                    'tbr': 326,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 8880746666,
                        'timescale': 10000000,
                        'width': 562,
                        'height': 240,
                        'fourcc': 'AVC1',
                        'codec_private_data': '00000001674D401FDA0241FE23FFC3BC83BA44000003000400000300C03C60CA800000000168EF32C8',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video-698',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'ext': 'ismv',
                    'width': 844,
                    'height': 360,
                    'tbr': 698,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 8880746666,
                        'timescale': 10000000,
                        'width': 844,
                        'height': 360,
                        'fourcc': 'AVC1',
                        'codec_private_data': '00000001674D401FDA0350BFB97FF06AF06AD1000003000100000300300F1832A00000000168EF32C8',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video-1493',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'ext': 'ismv',
                    'width': 1126,
                    'height': 480,
                    'tbr': 1493,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 8880746666,
                        'timescale': 10000000,
                        'width': 1126,
                        'height': 480,
                        'fourcc': 'AVC1',
                        'codec_private_data': '00000001674D401FDA011C3DE6FFF0D890D871000003000100000300300F1832A00000000168EF32C8',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video-4482',
                    'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                    'ext': 'ismv',
                    'width': 1688,
                    'height': 720,
                    'tbr': 4482,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 8880746666,
                        'timescale': 10000000,
                        'width': 1688,
                        'height': 720,
                        'fourcc': 'AVC1',
                        'codec_private_data': '00000001674D401FDA01A816F97FFC1ABC1AB440000003004000000C03C60CA80000000168EF32C8',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }],
                {
                    'eng': [
                        {
                            'ext': 'ismt',
                            'protocol': 'ism',
                            'url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                            'manifest_url': 'https://sdn-global-streaming-cache-3qsdn.akamaized.net/stream/3144/files/17/07/672975/3144-kZT4LWMQw6Rh7Kpd.ism/Manifest',
                            '_download_params': {
                                'stream_type': 'text',
                                'duration': 8880746666,
                                'timescale': 10000000,
                                'fourcc': 'TTML',
                                'codec_private_data': '',
                            },
                        },
                    ],
                },
            ),
            (
                'ec-3_test',
                'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                [{
                    'format_id': 'audio_deu-127',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'isma',
                    'tbr': 127,
                    'asr': 48000,
                    'vcodec': 'none',
                    'acodec': 'AACL',
                    'protocol': 'ism',
                    'language': 'deu',
                    'audio_channels': 2,
                    '_download_params': {
                        'stream_type': 'audio',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 0,
                        'height': 0,
                        'fourcc': 'AACL',
                        'language': 'deu',
                        'codec_private_data': '1190',
                        'sampling_rate': 48000,
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'audio_deu_1-224',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'isma',
                    'tbr': 224,
                    'asr': 48000,
                    'vcodec': 'none',
                    'acodec': 'EC-3',
                    'protocol': 'ism',
                    'language': 'deu',
                    'audio_channels': 6,
                    '_download_params': {
                        'stream_type': 'audio',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 0,
                        'height': 0,
                        'fourcc': 'EC-3',
                        'language': 'deu',
                        'codec_private_data': '00063F000000AF87FBA7022DFB42A4D405CD93843BDD0700200F00',
                        'sampling_rate': 48000,
                        'channels': 6,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video_deu-23',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'ismv',
                    'width': 384,
                    'height': 216,
                    'tbr': 23,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    'language': 'deu',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 384,
                        'height': 216,
                        'fourcc': 'AVC1',
                        'language': 'deu',
                        'codec_private_data': '000000016742C00CDB06077E5C05A808080A00000300020000030009C0C02EE0177CC6300F142AE00000000168CA8DC8',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video_deu-403',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'ismv',
                    'width': 400,
                    'height': 224,
                    'tbr': 403,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    'language': 'deu',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 400,
                        'height': 224,
                        'fourcc': 'AVC1',
                        'language': 'deu',
                        'codec_private_data': '00000001674D4014E98323B602D4040405000003000100000300320F1429380000000168EAECF2',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video_deu-680',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'ismv',
                    'width': 640,
                    'height': 360,
                    'tbr': 680,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    'language': 'deu',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 640,
                        'height': 360,
                        'fourcc': 'AVC1',
                        'language': 'deu',
                        'codec_private_data': '00000001674D401EE981405FF2E02D4040405000000300100000030320F162D3800000000168EAECF2',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video_deu-1253',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'ismv',
                    'width': 640,
                    'height': 360,
                    'tbr': 1253,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    'vbr': 1253,
                    'language': 'deu',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 640,
                        'height': 360,
                        'fourcc': 'AVC1',
                        'language': 'deu',
                        'codec_private_data': '00000001674D401EE981405FF2E02D4040405000000300100000030320F162D3800000000168EAECF2',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video_deu-2121',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'ismv',
                    'width': 768,
                    'height': 432,
                    'tbr': 2121,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    'language': 'deu',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 768,
                        'height': 432,
                        'fourcc': 'AVC1',
                        'language': 'deu',
                        'codec_private_data': '00000001674D401EECA0601BD80B50101014000003000400000300C83C58B6580000000168E93B3C80',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video_deu-3275',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'ismv',
                    'width': 1280,
                    'height': 720,
                    'tbr': 3275,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    'language': 'deu',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 1280,
                        'height': 720,
                        'fourcc': 'AVC1',
                        'language': 'deu',
                        'codec_private_data': '00000001674D4020ECA02802DD80B501010140000003004000000C83C60C65800000000168E93B3C80',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video_deu-5300',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'ismv',
                    'width': 1920,
                    'height': 1080,
                    'tbr': 5300,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    'language': 'deu',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 1920,
                        'height': 1080,
                        'fourcc': 'AVC1',
                        'language': 'deu',
                        'codec_private_data': '00000001674D4028ECA03C0113F2E02D4040405000000300100000030320F18319600000000168E93B3C80',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }, {
                    'format_id': 'video_deu-8079',
                    'url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'manifest_url': 'https://smstr01.dmm.t-online.de/smooth24/smoothstream_m1/streaming/sony/9221438342941275747/636887760842957027/25_km_h-Trailer-9221571562372022953_deu_20_1300k_HD_H_264_ISMV.ism/Manifest',
                    'ext': 'ismv',
                    'width': 1920,
                    'height': 1080,
                    'tbr': 8079,
                    'vcodec': 'AVC1',
                    'acodec': 'none',
                    'protocol': 'ism',
                    'language': 'deu',
                    '_download_params': {
                        'stream_type': 'video',
                        'duration': 370000000,
                        'timescale': 10000000,
                        'width': 1920,
                        'height': 1080,
                        'fourcc': 'AVC1',
                        'language': 'deu',
                        'codec_private_data': '00000001674D4028ECA03C0113F2E02D4040405000000300100000030320F18319600000000168E93B3C80',
                        'channels': 2,
                        'bits_per_sample': 16,
                        'nal_unit_length_field': 4,
                    },
                }],
                {},
            ),
        ]

        for ism_file, ism_url, expected_formats, expected_subtitles in _TEST_CASES:
            with open(f'./test/testdata/ism/{ism_file}.Manifest', encoding='utf-8') as f:
                formats, subtitles = self.ie._parse_ism_formats_and_subtitles(
                    compat_etree_fromstring(f.read().encode()), ism_url=ism_url)
                self.ie._sort_formats(formats)
                expect_value(self, formats, expected_formats, None)
                expect_value(self, subtitles, expected_subtitles, None)

    def test_parse_f4m_formats(self):
        _TEST_CASES = [
            (
                # https://github.com/ytdl-org/youtube-dl/issues/14660
                'custom_base_url',
                'http://api.new.livestream.com/accounts/6115179/events/6764928/videos/144884262.f4m',
                [{
                    'manifest_url': 'http://api.new.livestream.com/accounts/6115179/events/6764928/videos/144884262.f4m',
                    'ext': 'flv',
                    'format_id': '2148',
                    'protocol': 'f4m',
                    'tbr': 2148,
                    'width': 1280,
                    'height': 720,
                }],
            ),
        ]

        for f4m_file, f4m_url, expected_formats in _TEST_CASES:
            with open(f'./test/testdata/f4m/{f4m_file}.f4m', encoding='utf-8') as f:
                formats = self.ie._parse_f4m_formats(
                    compat_etree_fromstring(f.read().encode()),
                    f4m_url, None)
                self.ie._sort_formats(formats)
                expect_value(self, formats, expected_formats, None)

    def test_parse_xspf(self):
        _TEST_CASES = [
            (
                'foo_xspf',
                'https://example.org/src/foo_xspf.xspf',
                [{
                    'id': 'foo_xspf',
                    'title': 'Pandemonium',
                    'description': 'Visit http://bigbrother404.bandcamp.com',
                    'duration': 202.416,
                    'formats': [{
                        'manifest_url': 'https://example.org/src/foo_xspf.xspf',
                        'url': 'https://example.org/src/cd1/track%201.mp3',
                    }],
                }, {
                    'id': 'foo_xspf',
                    'title': 'Final Cartridge (Nichico Twelve Remix)',
                    'description': 'Visit http://bigbrother404.bandcamp.com',
                    'duration': 255.857,
                    'formats': [{
                        'manifest_url': 'https://example.org/src/foo_xspf.xspf',
                        'url': 'https://example.org/%E3%83%88%E3%83%A9%E3%83%83%E3%82%AF%E3%80%80%EF%BC%92.mp3',
                    }],
                }, {
                    'id': 'foo_xspf',
                    'title': 'Rebuilding Nightingale',
                    'description': 'Visit http://bigbrother404.bandcamp.com',
                    'duration': 287.915,
                    'formats': [{
                        'manifest_url': 'https://example.org/src/foo_xspf.xspf',
                        'url': 'https://example.org/src/track3.mp3',
                    }, {
                        'manifest_url': 'https://example.org/src/foo_xspf.xspf',
                        'url': 'https://example.com/track3.mp3',
                    }],
                }],
            ),
        ]

        for xspf_file, xspf_url, expected_entries in _TEST_CASES:
            with open(f'./test/testdata/xspf/{xspf_file}.xspf', encoding='utf-8') as f:
                entries = self.ie._parse_xspf(
                    compat_etree_fromstring(f.read().encode()),
                    xspf_file, xspf_url=xspf_url, xspf_base_url=xspf_url)
                expect_value(self, entries, expected_entries, None)
                for i in range(len(entries)):
                    expect_dict(self, entries[i], expected_entries[i])

    def test_response_with_expected_status_returns_content(self):
        # Checks for mitigations against the effects of
        # <https://bugs.python.org/issue15002> that affect Python 3.4.1+, which
        # manifest as `_download_webpage`, `_download_xml`, `_download_json`,
        # or the underlying `_download_webpage_handle` returning no content
        # when a response matches `expected_status`.

        httpd = http.server.HTTPServer(
            ('127.0.0.1', 0), InfoExtractorTestRequestHandler)
        port = http_server_port(httpd)
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        (content, urlh) = self.ie._download_webpage_handle(
            f'http://127.0.0.1:{port}/teapot', None,
            expected_status=TEAPOT_RESPONSE_STATUS)
        self.assertEqual(content, TEAPOT_RESPONSE_BODY)

    def test_search_nextjs_data(self):
        data = '<script id="__NEXT_DATA__" type="application/json">{"props":{}}</script>'
        self.assertEqual(self.ie._search_nextjs_data(data, None), {'props': {}})
        self.assertEqual(self.ie._search_nextjs_data('', None, fatal=False), {})
        self.assertEqual(self.ie._search_nextjs_data('', None, default=None), None)
        self.assertEqual(self.ie._search_nextjs_data('', None, default={}), {})
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(self.ie._search_nextjs_data('', None, default='{}'), {})

    def test_search_nextjs_v13_data(self):
        HTML = R'''
            <script>(self.__next_f=self.__next_f||[]).push([0])</script>
            <script>self.__next_f.push([2,"0:[\"$\",\"$L0\",null,{\"do_not_add_this\":\"fail\"}]\n"])</script>
            <script>self.__next_f.push([1,"1:I[46975,[],\"HTTPAccessFallbackBoundary\"]\n2:I[32630,[\"8183\",\"static/chunks/8183-768193f6a9e33cdd.js\"]]\n"])</script>
            <script nonce="abc123">self.__next_f.push([1,"e:[false,[\"$\",\"div\",null,{\"children\":[\"$\",\"$L18\",null,{\"foo\":\"bar\"}]}],false]\n    "])</script>
            <script>self.__next_f.push([1,"2a:[[\"$\",\"div\",null,{\"className\":\"flex flex-col\",\"children\":[]}],[\"$\",\"$L16\",null,{\"meta\":{\"dateCreated\":1730489700,\"uuid\":\"40cac41d-8d29-4ef5-aa11-75047b9f0907\"}}]]\n"])</script>
            <script>self.__next_f.push([1,"df:[\"$undefined\",[\"$\",\"div\",null,{\"children\":[\"$\",\"$L17\",null,{}],\"do_not_include_this_field\":\"fail\"}],[\"$\",\"div\",null,{\"children\":[[\"$\",\"$L19\",null,{\"duplicated_field_name\":{\"x\":1}}],[\"$\",\"$L20\",null,{\"duplicated_field_name\":{\"y\":2}}]]}],\"$undefined\"]\n"])</script>
            <script>self.__next_f.push([3,"MzM6WyIkIiwiJEwzMiIsbnVsbCx7ImRlY29kZWQiOiJzdWNjZXNzIn1d"])</script>
            '''
        EXPECTED = {
            '18': {
                'foo': 'bar',
            },
            '16': {
                'meta': {
                    'dateCreated': 1730489700,
                    'uuid': '40cac41d-8d29-4ef5-aa11-75047b9f0907',
                },
            },
            '19': {
                'duplicated_field_name': {'x': 1},
            },
            '20': {
                'duplicated_field_name': {'y': 2},
            },
        }
        self.assertEqual(self.ie._search_nextjs_v13_data(HTML, None), EXPECTED)
        self.assertEqual(self.ie._search_nextjs_v13_data('', None, fatal=False), {})
        self.assertEqual(self.ie._search_nextjs_v13_data(None, None, fatal=False), {})

    def test_search_nuxt_json(self):
        HTML_TMPL = '<script data-ssr="true" id="__NUXT_DATA__" type="application/json">[{}]</script>'
        VALID_DATA = '''
            ["ShallowReactive",1],
            {"data":2,"state":21,"once":25,"_errors":28,"_server_errors":30},
            ["ShallowReactive",3],
            {"$abcdef123456":4},
            {"podcast":5,"activeEpisodeData":7},
            {"podcast":6,"seasons":14},
            {"title":10,"id":11},
            ["Reactive",8],
            {"episode":9,"creators":18,"empty_list":20},
            {"title":12,"id":13,"refs":34,"empty_refs":35},
            "Series Title",
            "podcast-id-01",
            "Episode Title",
            "episode-id-99",
            [15,16,17],
            1,
            2,
            3,
            [19],
            "Podcast Creator",
            [],
            {"$ssite-config":22},
            {"env":23,"name":24,"map":26,"numbers":14},
            "production",
            "podcast-website",
            ["Set"],
            ["Reactive",27],
            ["Map"],
            ["ShallowReactive",29],
            {},
            ["NuxtError",31],
            {"status":32,"message":33},
            503,
            "Service Unavailable",
            [36,37],
            [38,39],
            ["Ref",40],
            ["ShallowRef",41],
            ["EmptyRef",42],
            ["EmptyShallowRef",43],
            "ref",
            "shallow_ref",
            "{\\"ref\\":1}",
            "{\\"shallow_ref\\":2}"
        '''
        PAYLOAD = {
            'data': {
                '$abcdef123456': {
                    'podcast': {
                        'podcast': {
                            'title': 'Series Title',
                            'id': 'podcast-id-01',
                        },
                        'seasons': [1, 2, 3],
                    },
                    'activeEpisodeData': {
                        'episode': {
                            'title': 'Episode Title',
                            'id': 'episode-id-99',
                            'refs': ['ref', 'shallow_ref'],
                            'empty_refs': [{'ref': 1}, {'shallow_ref': 2}],
                        },
                        'creators': ['Podcast Creator'],
                        'empty_list': [],
                    },
                },
            },
            'state': {
                '$ssite-config': {
                    'env': 'production',
                    'name': 'podcast-website',
                    'map': [],
                    'numbers': [1, 2, 3],
                },
            },
            'once': [],
            '_errors': {},
            '_server_errors': {
                'status': 503,
                'message': 'Service Unavailable',
            },
        }
        PARTIALLY_INVALID = [(
            '''
            {"data":1},
            {"invalid_raw_list":2},
            [15,16,17]
            ''',
            {'data': {'invalid_raw_list': [None, None, None]}},
        ), (
            '''
            {"data":1},
            ["EmptyRef",2],
            "not valid JSON"
            ''',
            {'data': None},
        ), (
            '''
            {"data":1},
            ["EmptyShallowRef",2],
            "not valid JSON"
            ''',
            {'data': None},
        )]
        INVALID = [
            '''
                []
            ''',
            '''
                ["unsupported",1],
                {"data":2},
                {}
            ''',
        ]
        DEFAULT = object()

        self.assertEqual(self.ie._search_nuxt_json(HTML_TMPL.format(VALID_DATA), None), PAYLOAD)
        self.assertEqual(self.ie._search_nuxt_json('', None, fatal=False), {})
        self.assertIs(self.ie._search_nuxt_json('', None, default=DEFAULT), DEFAULT)

        for data, expected in PARTIALLY_INVALID:
            self.assertEqual(
                self.ie._search_nuxt_json(HTML_TMPL.format(data), None, fatal=False), expected)

        for data in INVALID:
            self.assertIs(
                self.ie._search_nuxt_json(HTML_TMPL.format(data), None, default=DEFAULT), DEFAULT)


class TestInfoExtractorNetwork(unittest.TestCase):
    def setUp(self, /):
        self.httpd = http.server.HTTPServer(
            ('127.0.0.1', 0), InfoExtractorTestRequestHandler)
        self.port = http_server_port(self.httpd)

        self.server_thread = threading.Thread(target=self.httpd.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.called = False

        def require_warning(*args, **kwargs):
            self.called = True

        self.ydl = FakeYDL()
        self.ydl.report_warning = require_warning
        self.ie = DummyIE(self.ydl)

    def tearDown(self, /):
        self.ydl.close()
        self.httpd.shutdown()
        self.httpd.server_close()
        self.server_thread.join(1)

    def test_extract_m3u8_formats(self):
        formats, subtitles = self.ie._extract_m3u8_formats_and_subtitles(
            f'http://127.0.0.1:{self.port}/bipbop.m3u8', None, fatal=False)
        self.assertFalse(self.called)
        self.assertTrue(formats)
        self.assertTrue(subtitles)

    def test_extract_m3u8_formats_warning(self):
        formats, subtitles = self.ie._extract_m3u8_formats_and_subtitles(
            f'http://127.0.0.1:{self.port}/fake.m3u8', None, fatal=False)
        self.assertTrue(self.called, 'Warning was not issued for binary m3u8 file')
        self.assertFalse(formats)
        self.assertFalse(subtitles)


if __name__ == '__main__':
    unittest.main()
