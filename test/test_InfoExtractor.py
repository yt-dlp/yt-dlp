#!/usr/bin/env python

from __future__ import unicode_literals

# Allow direct execution
import io
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import FakeYDL, expect_dict, expect_value, http_server_port
from youtube_dlc.compat import compat_etree_fromstring, compat_http_server
from youtube_dlc.extractor.common import InfoExtractor
from youtube_dlc.extractor import YoutubeIE, get_info_extractor
from youtube_dlc.utils import encode_data_uri, strip_jsonp, ExtractorError, RegexNotFoundError
import threading


TEAPOT_RESPONSE_STATUS = 418
TEAPOT_RESPONSE_BODY = "<h1>418 I'm a teapot</h1>"


class InfoExtractorTestRequestHandler(compat_http_server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/teapot':
            self.send_response(TEAPOT_RESPONSE_STATUS)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(TEAPOT_RESPONSE_BODY.encode())
        else:
            assert False


class TestIE(InfoExtractor):
    pass


class TestInfoExtractor(unittest.TestCase):
    def setUp(self):
        self.ie = TestIE(FakeYDL())

    def test_ie_key(self):
        self.assertEqual(get_info_extractor(YoutubeIE.ie_key()), YoutubeIE)

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
        # https://github.com/ytdl-org/youtube-dl/issues/23306
        expect_dict(
            self,
            self.ie._search_json_ld(r'''<script type="application/ld+json">
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
</script>''', None),
            {
                'title': '1 On 1 With Kleio',
                'description': 'Kleio Valentien',
                'url': 'https://gvideo.eporner.com/xN49A1cT3eB/xN49A1cT3eB.mp4',
                'timestamp': 1449347075,
                'duration': 743.0,
                'view_count': 1120958,
                'width': 1920,
                'height': 1080,
            })

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
                'thumbnail': '//pics.r18.com/digital/amateur/mgmr105/mgmr105jp.jpg'
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
                    'cs': [{'url': 'https://video.csfd.cz/files/subtitles/163/344/163344115_4c388b.srt'}]
                },
                'thumbnail': 'https://img.csfd.cz/files/images/film/video/preview/163/344/163344118_748d20.png?h360'
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
                }]
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
                }]
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
                }]
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
                    'ext': 'flv'
                }]
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
                    'ext': 'flv'
                }]
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
                    'ext': 'mp4'
                }, {
                    'url': 'http://cdn.dbolical.com/cache/videos/games/1/50/49678/encode720p_mp4/king-machine-trailer.mp4',
                    'height': 720,
                    'ext': 'mp4'
                }]
            })

    def test_parse_m3u8_formats(self):
        _TEST_CASES = [
            (
                # https://github.com/ytdl-org/youtube-dl/issues/11507
                # http://pluzz.francetv.fr/videos/le_ministere.html
                'pluzz_francetv_11507',
                'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/master.m3u8?caption=2017%2F16%2F156589847-1492488987.m3u8%3Afra%3AFrancais&audiotrack=0%3Afra%3AFrancais',
                [{
                    'url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/index_0_av.m3u8?null=0',
                    'manifest_url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/master.m3u8?caption=2017%2F16%2F156589847-1492488987.m3u8%3Afra%3AFrancais&audiotrack=0%3Afra%3AFrancais',
                    'ext': 'mp4',
                    'format_id': '180',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.66.30',
                    'tbr': 180,
                    'width': 256,
                    'height': 144,
                }, {
                    'url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/index_1_av.m3u8?null=0',
                    'manifest_url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/master.m3u8?caption=2017%2F16%2F156589847-1492488987.m3u8%3Afra%3AFrancais&audiotrack=0%3Afra%3AFrancais',
                    'ext': 'mp4',
                    'format_id': '303',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.66.30',
                    'tbr': 303,
                    'width': 320,
                    'height': 180,
                }, {
                    'url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/index_2_av.m3u8?null=0',
                    'manifest_url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/master.m3u8?caption=2017%2F16%2F156589847-1492488987.m3u8%3Afra%3AFrancais&audiotrack=0%3Afra%3AFrancais',
                    'ext': 'mp4',
                    'format_id': '575',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.66.30',
                    'tbr': 575,
                    'width': 512,
                    'height': 288,
                }, {
                    'url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/index_3_av.m3u8?null=0',
                    'manifest_url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/master.m3u8?caption=2017%2F16%2F156589847-1492488987.m3u8%3Afra%3AFrancais&audiotrack=0%3Afra%3AFrancais',
                    'ext': 'mp4',
                    'format_id': '831',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.77.30',
                    'tbr': 831,
                    'width': 704,
                    'height': 396,
                }, {
                    'url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/index_4_av.m3u8?null=0',
                    'manifest_url': 'http://replayftv-vh.akamaihd.net/i/streaming-adaptatif_france-dom-tom/2017/S16/J2/156589847-58f59130c1f52-,standard1,standard2,standard3,standard4,standard5,.mp4.csmil/master.m3u8?caption=2017%2F16%2F156589847-1492488987.m3u8%3Afra%3AFrancais&audiotrack=0%3Afra%3AFrancais',
                    'ext': 'mp4',
                    'protocol': 'm3u8',
                    'format_id': '1467',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.77.30',
                    'tbr': 1467,
                    'width': 1024,
                    'height': 576,
                }]
            ),
            (
                # https://github.com/ytdl-org/youtube-dl/issues/11995
                # http://teamcoco.com/video/clueless-gamer-super-bowl-for-honor
                'teamcoco_11995',
                'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/main.m3u8',
                [{
                    'url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/hls/CONAN_020217_Highlight_show-audio-160k_v4.m3u8',
                    'manifest_url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/main.m3u8',
                    'ext': 'mp4',
                    'format_id': 'audio-0-Default',
                    'protocol': 'm3u8',
                    'vcodec': 'none',
                }, {
                    'url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/hls/CONAN_020217_Highlight_show-audio-64k_v4.m3u8',
                    'manifest_url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/main.m3u8',
                    'ext': 'mp4',
                    'format_id': 'audio-1-Default',
                    'protocol': 'm3u8',
                    'vcodec': 'none',
                }, {
                    'url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/hls/CONAN_020217_Highlight_show-audio-64k_v4.m3u8',
                    'manifest_url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/main.m3u8',
                    'ext': 'mp4',
                    'format_id': '71',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.5',
                    'vcodec': 'none',
                    'tbr': 71,
                }, {
                    'url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/hls/CONAN_020217_Highlight_show-400k_v4.m3u8',
                    'manifest_url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/main.m3u8',
                    'ext': 'mp4',
                    'format_id': '413',
                    'protocol': 'm3u8',
                    'acodec': 'none',
                    'vcodec': 'avc1.42001e',
                    'tbr': 413,
                    'width': 400,
                    'height': 224,
                }, {
                    'url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/hls/CONAN_020217_Highlight_show-400k_v4.m3u8',
                    'manifest_url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/main.m3u8',
                    'ext': 'mp4',
                    'format_id': '522',
                    'protocol': 'm3u8',
                    'acodec': 'none',
                    'vcodec': 'avc1.42001e',
                    'tbr': 522,
                    'width': 400,
                    'height': 224,
                }, {
                    'url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/hls/CONAN_020217_Highlight_show-1m_v4.m3u8',
                    'manifest_url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/main.m3u8',
                    'ext': 'mp4',
                    'format_id': '1205',
                    'protocol': 'm3u8',
                    'acodec': 'none',
                    'vcodec': 'avc1.4d001e',
                    'tbr': 1205,
                    'width': 640,
                    'height': 360,
                }, {
                    'url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/hls/CONAN_020217_Highlight_show-2m_v4.m3u8',
                    'manifest_url': 'http://ak.storage-w.teamcococdn.com/cdn/2017-02/98599/ed8f/main.m3u8',
                    'ext': 'mp4',
                    'format_id': '2374',
                    'protocol': 'm3u8',
                    'acodec': 'none',
                    'vcodec': 'avc1.4d001f',
                    'tbr': 2374,
                    'width': 1024,
                    'height': 576,
                }]
            ),
            (
                # https://github.com/ytdl-org/youtube-dl/issues/12211
                # http://video.toggle.sg/en/series/whoopie-s-world/ep3/478601
                'toggle_mobile_12211',
                'http://cdnapi.kaltura.com/p/2082311/sp/208231100/playManifest/protocol/http/entryId/0_89q6e8ku/format/applehttp/tags/mobile_sd/f/a.m3u8',
                [{
                    'url': 'http://k.toggle.sg/fhls/p/2082311/sp/208231100/serveFlavor/entryId/0_89q6e8ku/v/2/pv/1/flavorId/0_sa2ntrdg/name/a.mp4/index.m3u8',
                    'manifest_url': 'http://cdnapi.kaltura.com/p/2082311/sp/208231100/playManifest/protocol/http/entryId/0_89q6e8ku/format/applehttp/tags/mobile_sd/f/a.m3u8',
                    'ext': 'mp4',
                    'format_id': 'audio-English',
                    'protocol': 'm3u8',
                    'language': 'eng',
                    'vcodec': 'none',
                }, {
                    'url': 'http://k.toggle.sg/fhls/p/2082311/sp/208231100/serveFlavor/entryId/0_89q6e8ku/v/2/pv/1/flavorId/0_r7y0nitg/name/a.mp4/index.m3u8',
                    'manifest_url': 'http://cdnapi.kaltura.com/p/2082311/sp/208231100/playManifest/protocol/http/entryId/0_89q6e8ku/format/applehttp/tags/mobile_sd/f/a.m3u8',
                    'ext': 'mp4',
                    'format_id': 'audio-Undefined',
                    'protocol': 'm3u8',
                    'language': 'und',
                    'vcodec': 'none',
                }, {
                    'url': 'http://k.toggle.sg/fhls/p/2082311/sp/208231100/serveFlavor/entryId/0_89q6e8ku/v/2/pv/1/flavorId/0_qlk9hlzr/name/a.mp4/index.m3u8',
                    'manifest_url': 'http://cdnapi.kaltura.com/p/2082311/sp/208231100/playManifest/protocol/http/entryId/0_89q6e8ku/format/applehttp/tags/mobile_sd/f/a.m3u8',
                    'ext': 'mp4',
                    'format_id': '155',
                    'protocol': 'm3u8',
                    'tbr': 155.648,
                    'width': 320,
                    'height': 180,
                }, {
                    'url': 'http://k.toggle.sg/fhls/p/2082311/sp/208231100/serveFlavor/entryId/0_89q6e8ku/v/2/pv/1/flavorId/0_oefackmi/name/a.mp4/index.m3u8',
                    'manifest_url': 'http://cdnapi.kaltura.com/p/2082311/sp/208231100/playManifest/protocol/http/entryId/0_89q6e8ku/format/applehttp/tags/mobile_sd/f/a.m3u8',
                    'ext': 'mp4',
                    'format_id': '502',
                    'protocol': 'm3u8',
                    'tbr': 502.784,
                    'width': 480,
                    'height': 270,
                }, {
                    'url': 'http://k.toggle.sg/fhls/p/2082311/sp/208231100/serveFlavor/entryId/0_89q6e8ku/v/12/pv/1/flavorId/0_vyg9pj7k/name/a.mp4/index.m3u8',
                    'manifest_url': 'http://cdnapi.kaltura.com/p/2082311/sp/208231100/playManifest/protocol/http/entryId/0_89q6e8ku/format/applehttp/tags/mobile_sd/f/a.m3u8',
                    'ext': 'mp4',
                    'format_id': '827',
                    'protocol': 'm3u8',
                    'tbr': 827.392,
                    'width': 640,
                    'height': 360,
                }, {
                    'url': 'http://k.toggle.sg/fhls/p/2082311/sp/208231100/serveFlavor/entryId/0_89q6e8ku/v/12/pv/1/flavorId/0_50n4psvx/name/a.mp4/index.m3u8',
                    'manifest_url': 'http://cdnapi.kaltura.com/p/2082311/sp/208231100/playManifest/protocol/http/entryId/0_89q6e8ku/format/applehttp/tags/mobile_sd/f/a.m3u8',
                    'ext': 'mp4',
                    'format_id': '1396',
                    'protocol': 'm3u8',
                    'tbr': 1396.736,
                    'width': 854,
                    'height': 480,
                }]
            ),
            (
                # http://www.twitch.tv/riotgames/v/6528877
                'twitch_vod',
                'https://usher.ttvnw.net/vod/6528877?allow_source=true&allow_audio_only=true&allow_spectre=true&player=twitchweb&nauth=%7B%22user_id%22%3Anull%2C%22vod_id%22%3A6528877%2C%22expires%22%3A1492887874%2C%22chansub%22%3A%7B%22restricted_bitrates%22%3A%5B%5D%7D%2C%22privileged%22%3Afalse%2C%22https_required%22%3Afalse%7D&nauthsig=3e29296a6824a0f48f9e731383f77a614fc79bee',
                [{
                    'url': 'https://vod.edgecast.hls.ttvnw.net/e5da31ab49_riotgames_15001215120_261543898/audio_only/index-muted-HM49I092CC.m3u8',
                    'manifest_url': 'https://usher.ttvnw.net/vod/6528877?allow_source=true&allow_audio_only=true&allow_spectre=true&player=twitchweb&nauth=%7B%22user_id%22%3Anull%2C%22vod_id%22%3A6528877%2C%22expires%22%3A1492887874%2C%22chansub%22%3A%7B%22restricted_bitrates%22%3A%5B%5D%7D%2C%22privileged%22%3Afalse%2C%22https_required%22%3Afalse%7D&nauthsig=3e29296a6824a0f48f9e731383f77a614fc79bee',
                    'ext': 'mp4',
                    'format_id': 'Audio Only',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'none',
                    'tbr': 182.725,
                }, {
                    'url': 'https://vod.edgecast.hls.ttvnw.net/e5da31ab49_riotgames_15001215120_261543898/mobile/index-muted-HM49I092CC.m3u8',
                    'manifest_url': 'https://usher.ttvnw.net/vod/6528877?allow_source=true&allow_audio_only=true&allow_spectre=true&player=twitchweb&nauth=%7B%22user_id%22%3Anull%2C%22vod_id%22%3A6528877%2C%22expires%22%3A1492887874%2C%22chansub%22%3A%7B%22restricted_bitrates%22%3A%5B%5D%7D%2C%22privileged%22%3Afalse%2C%22https_required%22%3Afalse%7D&nauthsig=3e29296a6824a0f48f9e731383f77a614fc79bee',
                    'ext': 'mp4',
                    'format_id': 'Mobile',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.42C00D',
                    'tbr': 280.474,
                    'width': 400,
                    'height': 226,
                }, {
                    'url': 'https://vod.edgecast.hls.ttvnw.net/e5da31ab49_riotgames_15001215120_261543898/low/index-muted-HM49I092CC.m3u8',
                    'manifest_url': 'https://usher.ttvnw.net/vod/6528877?allow_source=true&allow_audio_only=true&allow_spectre=true&player=twitchweb&nauth=%7B%22user_id%22%3Anull%2C%22vod_id%22%3A6528877%2C%22expires%22%3A1492887874%2C%22chansub%22%3A%7B%22restricted_bitrates%22%3A%5B%5D%7D%2C%22privileged%22%3Afalse%2C%22https_required%22%3Afalse%7D&nauthsig=3e29296a6824a0f48f9e731383f77a614fc79bee',
                    'ext': 'mp4',
                    'format_id': 'Low',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.42C01E',
                    'tbr': 628.347,
                    'width': 640,
                    'height': 360,
                }, {
                    'url': 'https://vod.edgecast.hls.ttvnw.net/e5da31ab49_riotgames_15001215120_261543898/medium/index-muted-HM49I092CC.m3u8',
                    'manifest_url': 'https://usher.ttvnw.net/vod/6528877?allow_source=true&allow_audio_only=true&allow_spectre=true&player=twitchweb&nauth=%7B%22user_id%22%3Anull%2C%22vod_id%22%3A6528877%2C%22expires%22%3A1492887874%2C%22chansub%22%3A%7B%22restricted_bitrates%22%3A%5B%5D%7D%2C%22privileged%22%3Afalse%2C%22https_required%22%3Afalse%7D&nauthsig=3e29296a6824a0f48f9e731383f77a614fc79bee',
                    'ext': 'mp4',
                    'format_id': 'Medium',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.42C01E',
                    'tbr': 893.387,
                    'width': 852,
                    'height': 480,
                }, {
                    'url': 'https://vod.edgecast.hls.ttvnw.net/e5da31ab49_riotgames_15001215120_261543898/high/index-muted-HM49I092CC.m3u8',
                    'manifest_url': 'https://usher.ttvnw.net/vod/6528877?allow_source=true&allow_audio_only=true&allow_spectre=true&player=twitchweb&nauth=%7B%22user_id%22%3Anull%2C%22vod_id%22%3A6528877%2C%22expires%22%3A1492887874%2C%22chansub%22%3A%7B%22restricted_bitrates%22%3A%5B%5D%7D%2C%22privileged%22%3Afalse%2C%22https_required%22%3Afalse%7D&nauthsig=3e29296a6824a0f48f9e731383f77a614fc79bee',
                    'ext': 'mp4',
                    'format_id': 'High',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.42C01F',
                    'tbr': 1603.789,
                    'width': 1280,
                    'height': 720,
                }, {
                    'url': 'https://vod.edgecast.hls.ttvnw.net/e5da31ab49_riotgames_15001215120_261543898/chunked/index-muted-HM49I092CC.m3u8',
                    'manifest_url': 'https://usher.ttvnw.net/vod/6528877?allow_source=true&allow_audio_only=true&allow_spectre=true&player=twitchweb&nauth=%7B%22user_id%22%3Anull%2C%22vod_id%22%3A6528877%2C%22expires%22%3A1492887874%2C%22chansub%22%3A%7B%22restricted_bitrates%22%3A%5B%5D%7D%2C%22privileged%22%3Afalse%2C%22https_required%22%3Afalse%7D&nauthsig=3e29296a6824a0f48f9e731383f77a614fc79bee',
                    'ext': 'mp4',
                    'format_id': 'Source',
                    'protocol': 'm3u8',
                    'acodec': 'mp4a.40.2',
                    'vcodec': 'avc1.100.31',
                    'tbr': 3214.134,
                    'width': 1280,
                    'height': 720,
                }]
            ),
            (
                # http://www.vidio.com/watch/165683-dj_ambred-booyah-live-2015
                # EXT-X-STREAM-INF tag with NAME attribute that is not defined
                # in HLS specification
                'vidio',
                'https://www.vidio.com/videos/165683/playlist.m3u8',
                [{
                    'url': 'https://cdn1-a.production.vidio.static6.com/uploads/165683/dj_ambred-4383-b300.mp4.m3u8',
                    'manifest_url': 'https://www.vidio.com/videos/165683/playlist.m3u8',
                    'ext': 'mp4',
                    'format_id': '270p 3G',
                    'protocol': 'm3u8',
                    'tbr': 300,
                    'width': 480,
                    'height': 270,
                }, {
                    'url': 'https://cdn1-a.production.vidio.static6.com/uploads/165683/dj_ambred-4383-b600.mp4.m3u8',
                    'manifest_url': 'https://www.vidio.com/videos/165683/playlist.m3u8',
                    'ext': 'mp4',
                    'format_id': '360p SD',
                    'protocol': 'm3u8',
                    'tbr': 600,
                    'width': 640,
                    'height': 360,
                }, {
                    'url': 'https://cdn1-a.production.vidio.static6.com/uploads/165683/dj_ambred-4383-b1200.mp4.m3u8',
                    'manifest_url': 'https://www.vidio.com/videos/165683/playlist.m3u8',
                    'ext': 'mp4',
                    'format_id': '720p HD',
                    'protocol': 'm3u8',
                    'tbr': 1200,
                    'width': 1280,
                    'height': 720,
                }]
            ),
            (
                # https://github.com/ytdl-org/youtube-dl/issues/18923
                # https://www.ted.com/talks/boris_hesser_a_grassroots_healthcare_revolution_in_africa
                'ted_18923',
                'http://hls.ted.com/talks/31241.m3u8',
                [{
                    'url': 'http://hls.ted.com/videos/BorisHesser_2018S/audio/600k.m3u8?nobumpers=true&uniqueId=76011e2b',
                    'format_id': '600k-Audio',
                    'vcodec': 'none',
                }, {
                    'url': 'http://hls.ted.com/videos/BorisHesser_2018S/audio/600k.m3u8?nobumpers=true&uniqueId=76011e2b',
                    'format_id': '68',
                    'vcodec': 'none',
                }, {
                    'url': 'http://hls.ted.com/videos/BorisHesser_2018S/video/64k.m3u8?nobumpers=true&uniqueId=76011e2b',
                    'format_id': '163',
                    'acodec': 'none',
                    'width': 320,
                    'height': 180,
                }, {
                    'url': 'http://hls.ted.com/videos/BorisHesser_2018S/video/180k.m3u8?nobumpers=true&uniqueId=76011e2b',
                    'format_id': '481',
                    'acodec': 'none',
                    'width': 512,
                    'height': 288,
                }, {
                    'url': 'http://hls.ted.com/videos/BorisHesser_2018S/video/320k.m3u8?nobumpers=true&uniqueId=76011e2b',
                    'format_id': '769',
                    'acodec': 'none',
                    'width': 512,
                    'height': 288,
                }, {
                    'url': 'http://hls.ted.com/videos/BorisHesser_2018S/video/450k.m3u8?nobumpers=true&uniqueId=76011e2b',
                    'format_id': '984',
                    'acodec': 'none',
                    'width': 512,
                    'height': 288,
                }, {
                    'url': 'http://hls.ted.com/videos/BorisHesser_2018S/video/600k.m3u8?nobumpers=true&uniqueId=76011e2b',
                    'format_id': '1255',
                    'acodec': 'none',
                    'width': 640,
                    'height': 360,
                }, {
                    'url': 'http://hls.ted.com/videos/BorisHesser_2018S/video/950k.m3u8?nobumpers=true&uniqueId=76011e2b',
                    'format_id': '1693',
                    'acodec': 'none',
                    'width': 853,
                    'height': 480,
                }, {
                    'url': 'http://hls.ted.com/videos/BorisHesser_2018S/video/1500k.m3u8?nobumpers=true&uniqueId=76011e2b',
                    'format_id': '2462',
                    'acodec': 'none',
                    'width': 1280,
                    'height': 720,
                }]
            ),
        ]

        for m3u8_file, m3u8_url, expected_formats in _TEST_CASES:
            with io.open('./test/testdata/m3u8/%s.m3u8' % m3u8_file,
                         mode='r', encoding='utf-8') as f:
                formats = self.ie._parse_m3u8_formats(
                    f.read(), m3u8_url, ext='mp4')
                self.ie._sort_formats(formats)
                expect_value(self, formats, expected_formats, None)

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
                }]
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
                }]
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
                }]
            )
        ]

        for mpd_file, mpd_url, mpd_base_url, expected_formats in _TEST_CASES:
            with io.open('./test/testdata/mpd/%s.mpd' % mpd_file,
                         mode='r', encoding='utf-8') as f:
                formats = self.ie._parse_mpd_formats(
                    compat_etree_fromstring(f.read().encode('utf-8')),
                    mpd_base_url=mpd_base_url, mpd_url=mpd_url)
                self.ie._sort_formats(formats)
                expect_value(self, formats, expected_formats, None)

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
                }]
            ),
        ]

        for f4m_file, f4m_url, expected_formats in _TEST_CASES:
            with io.open('./test/testdata/f4m/%s.f4m' % f4m_file,
                         mode='r', encoding='utf-8') as f:
                formats = self.ie._parse_f4m_formats(
                    compat_etree_fromstring(f.read().encode('utf-8')),
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
                    }]
                }]
            ),
        ]

        for xspf_file, xspf_url, expected_entries in _TEST_CASES:
            with io.open('./test/testdata/xspf/%s.xspf' % xspf_file,
                         mode='r', encoding='utf-8') as f:
                entries = self.ie._parse_xspf(
                    compat_etree_fromstring(f.read().encode('utf-8')),
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

        httpd = compat_http_server.HTTPServer(
            ('127.0.0.1', 0), InfoExtractorTestRequestHandler)
        port = http_server_port(httpd)
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        (content, urlh) = self.ie._download_webpage_handle(
            'http://127.0.0.1:%d/teapot' % port, None,
            expected_status=TEAPOT_RESPONSE_STATUS)
        self.assertEqual(content, TEAPOT_RESPONSE_BODY)


if __name__ == '__main__':
    unittest.main()
