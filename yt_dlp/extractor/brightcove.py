import base64
import re
import struct
import urllib.parse
import xml.etree.ElementTree

from .adobepass import AdobePassIE
from .common import InfoExtractor
from ..compat import compat_etree_fromstring
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    UnsupportedError,
    clean_html,
    dict_get,
    extract_attributes,
    find_xpath_attr,
    fix_xml_ampersands,
    float_or_none,
    int_or_none,
    join_nonempty,
    js_to_json,
    mimetype2ext,
    parse_iso8601,
    parse_qs,
    smuggle_url,
    str_or_none,
    try_get,
    unescapeHTML,
    unsmuggle_url,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class BrightcoveLegacyIE(InfoExtractor):
    IE_NAME = 'brightcove:legacy'
    _VALID_URL = r'(?:https?://.*brightcove\.com/(services|viewer).*?\?|brightcove:)(?P<query>.*)'

    _TESTS = [
        {
            # From http://www.8tv.cat/8aldia/videos/xavier-sala-i-martin-aquesta-tarda-a-8-al-dia/
            'url': 'http://c.brightcove.com/services/viewer/htmlFederated?playerID=1654948606001&flashID=myExperience&%40videoPlayer=2371591881001',
            'md5': '5423e113865d26e40624dce2e4b45d95',
            'note': 'Test Brightcove downloads and detection in GenericIE',
            'info_dict': {
                'id': '2371591881001',
                'ext': 'mp4',
                'title': 'Xavier Sala i Martín: “Un banc que no presta és un banc zombi que no serveix per a res”',
                'uploader': '8TV',
                'description': 'md5:a950cc4285c43e44d763d036710cd9cd',
                'timestamp': 1368213670,
                'upload_date': '20130510',
                'uploader_id': '1589608506001',
            },
            'skip': 'The player has been deactivated by the content owner',
        },
        {
            # From http://medianetwork.oracle.com/video/player/1785452137001
            'url': 'http://c.brightcove.com/services/viewer/htmlFederated?playerID=1217746023001&flashID=myPlayer&%40videoPlayer=1785452137001',
            'info_dict': {
                'id': '1785452137001',
                'ext': 'flv',
                'title': 'JVMLS 2012: Arrays 2.0 - Opportunities and Challenges',
                'description': 'John Rose speaks at the JVM Language Summit, August 1, 2012.',
                'uploader': 'Oracle',
                'timestamp': 1344975024,
                'upload_date': '20120814',
                'uploader_id': '1460825906',
            },
            'skip': 'video not playable',
        },
        {
            # From http://mashable.com/2013/10/26/thermoelectric-bracelet-lets-you-control-your-body-temperature/
            'url': 'http://c.brightcove.com/services/viewer/federated_f9?&playerID=1265504713001&publisherID=AQ%7E%7E%2CAAABBzUwv1E%7E%2CxP-xFHVUstiMFlNYfvF4G9yFnNaqCw_9&videoID=2750934548001',
            'info_dict': {
                'id': '2750934548001',
                'ext': 'mp4',
                'title': 'This Bracelet Acts as a Personal Thermostat',
                'description': 'md5:547b78c64f4112766ccf4e151c20b6a0',
                # 'uploader': 'Mashable',
                'timestamp': 1382041798,
                'upload_date': '20131017',
                'uploader_id': '1130468786001',
            },
        },
        {
            # test that the default referer works
            # from http://national.ballet.ca/interact/video/Lost_in_Motion_II/
            'url': 'http://link.brightcove.com/services/player/bcpid756015033001?bckey=AQ~~,AAAApYJi_Ck~,GxhXCegT1Dp39ilhXuxMJxasUhVNZiil&bctid=2878862109001',
            'info_dict': {
                'id': '2878862109001',
                'ext': 'mp4',
                'title': 'Lost in Motion II',
                'description': 'md5:363109c02998fee92ec02211bd8000df',
                'uploader': 'National Ballet of Canada',
            },
            'skip': 'Video gone',
        },
        {
            # test flv videos served by akamaihd.net
            # From http://www.redbull.com/en/bike/stories/1331655643987/replay-uci-dh-world-cup-2014-from-fort-william
            'url': 'http://c.brightcove.com/services/viewer/htmlFederated?%40videoPlayer=ref%3Aevent-stream-356&linkBaseURL=http%3A%2F%2Fwww.redbull.com%2Fen%2Fbike%2Fvideos%2F1331655630249%2Freplay-uci-fort-william-2014-dh&playerKey=AQ%7E%7E%2CAAAApYJ7UqE%7E%2Cxqr_zXk0I-zzNndy8NlHogrCb5QdyZRf&playerID=1398061561001#__youtubedl_smuggle=%7B%22Referer%22%3A+%22http%3A%2F%2Fwww.redbull.com%2Fen%2Fbike%2Fstories%2F1331655643987%2Freplay-uci-dh-world-cup-2014-from-fort-william%22%7D',
            # The md5 checksum changes on each download
            'info_dict': {
                'id': '3750436379001',
                'ext': 'flv',
                'title': 'UCI MTB World Cup 2014: Fort William, UK - Downhill Finals',
                'uploader': 'RBTV Old (do not use)',
                'description': 'UCI MTB World Cup 2014: Fort William, UK - Downhill Finals',
                'timestamp': 1409122195,
                'upload_date': '20140827',
                'uploader_id': '710858724001',
            },
            'skip': 'Video gone',
        },
        {
            # playlist with 'videoList'
            # from http://support.brightcove.com/en/video-cloud/docs/playlist-support-single-video-players
            'url': 'http://c.brightcove.com/services/viewer/htmlFederated?playerID=3550052898001&playerKey=AQ%7E%7E%2CAAABmA9XpXk%7E%2C-Kp7jNgisre1fG5OdqpAFUTcs0lP_ZoL',
            'info_dict': {
                'title': 'Sealife',
                'id': '3550319591001',
            },
            'playlist_mincount': 7,
            'skip': 'Unsupported URL',
        },
        {
            # playlist with 'playlistTab' (https://github.com/ytdl-org/youtube-dl/issues/9965)
            'url': 'http://c.brightcove.com/services/json/experience/runtime/?command=get_programming_for_experience&playerKey=AQ%7E%7E,AAABXlLMdok%7E,NJ4EoMlZ4rZdx9eU1rkMVd8EaYPBBUlg',
            'info_dict': {
                'id': '1522758701001',
                'title': 'Lesson 08',
            },
            'playlist_mincount': 10,
            'skip': 'Unsupported URL',
        },
        {
            # playerID inferred from bcpid
            # from http://www.un.org/chinese/News/story.asp?NewsID=27724
            'url': 'https://link.brightcove.com/services/player/bcpid1722935254001/?bctid=5360463607001&autoStart=false&secureConnections=true&width=650&height=350',
            'only_matching': True,  # Tested in GenericIE
        },
    ]

    _WEBPAGE_TESTS = [{
        # embedded brightcove video
        # it also tests brightcove videos that need to set the 'Referer'
        # in the http requests
        'url': 'http://www.bfmtv.com/video/bfmbusiness/cours-bourse/cours-bourse-l-analyse-technique-154522/',
        'info_dict': {
            'id': '2765128793001',
            'ext': 'mp4',
            'title': 'Le cours de bourse : l’analyse technique',
            'description': 'md5:7e9ad046e968cb2d1114004aba466fd9',
            'uploader': 'BFM BUSINESS',
        },
        'params': {
            'skip_download': True,
        },
        'skip': '404 Not Found',
    }, {
        # embedded with itemprop embedURL and video id spelled as `idVideo`
        'url': 'http://bfmbusiness.bfmtv.com/mediaplayer/chroniques/olivier-delamarche/',
        'info_dict': {
            'id': '5255628253001',
            'ext': 'mp4',
            'title': 'md5:37c519b1128915607601e75a87995fc0',
            'description': 'md5:37f7f888b434bb8f8cc8dbd4f7a4cf26',
            'uploader': 'BFM BUSINESS',
            'uploader_id': '876450612001',
            'timestamp': 1482255315,
            'upload_date': '20161220',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Redirects, page gone',
    }, {
        # https://github.com/ytdl-org/youtube-dl/issues/2253
        'url': 'http://bcove.me/i6nfkrc3',
        'md5': '0ba9446db037002366bab3b3eb30c88c',
        'info_dict': {
            'id': '3101154703001',
            'ext': 'mp4',
            'title': 'Still no power',
            'uploader': 'thestar.com',
            'description': 'Mississauga resident David Farmer is still out of power as a result of the ice storm a month ago. To keep the house warm, Farmer cuts wood from his property for a wood burning stove downstairs.',
        },
        'skip': 'video gone',
    }, {
        # https://github.com/ytdl-org/youtube-dl/issues/3541
        'url': 'http://www.kijk.nl/sbs6/leermijvrouwenkennen/videos/jqMiXKAYan2S/aflevering-1',
        'info_dict': {
            'id': '3866516442001',
            'ext': 'mp4',
            'title': 'Leer mij vrouwen kennen: Aflevering 1',
            'description': 'Leer mij vrouwen kennen: Aflevering 1',
            'uploader': 'SBS Broadcasting',
        },
        'skip': 'Restricted to Netherlands, 404 Not Found',
        'params': {
            'skip_download': True,  # m3u8 download
        },
    }, {
        # Brightcove video in <iframe>
        'url': 'http://www.un.org/chinese/News/story.asp?NewsID=27724',
        'md5': '36d74ef5e37c8b4a2ce92880d208b968',
        'info_dict': {
            'id': '5360463607001',
            'ext': 'mp4',
            'title': '叙利亚失明儿童在废墟上演唱《心跳》  呼吁获得正常童年生活',
            'description': '联合国儿童基金会中东和北非区域大使、作曲家扎德·迪拉尼（Zade Dirani）在3月15日叙利亚冲突爆发7周年纪念日之际发布了为叙利亚谱写的歌曲《心跳》（HEARTBEAT），为受到六年冲突影响的叙利亚儿童发出强烈呐喊，呼吁世界做出共同努力，使叙利亚儿童重新获得享有正常童年生活的权利。',
            'uploader': 'United Nations',
            'uploader_id': '1362235914001',
            'timestamp': 1489593889,
            'upload_date': '20170315',
        },
        'skip': '404 Not Found',
    }, {
        # Brightcove with UUID in videoPlayer
        'url': 'http://www8.hp.com/cn/zh/home.html',
        'info_dict': {
            'id': '5255815316001',
            'ext': 'mp4',
            'title': 'Sprocket Video - China',
            'description': 'Sprocket Video - China',
            'uploader': 'HP-Video Gallery',
            'timestamp': 1482263210,
            'upload_date': '20161220',
            'uploader_id': '1107601872001',
        },
        'params': {
            'skip_download': True,  # m3u8 download
        },
        'skip': 'video rotates...weekly?',
    }, {
        # Multiple brightcove videos
        # https://github.com/ytdl-org/youtube-dl/issues/2283
        'url': 'http://www.newyorker.com/online/blogs/newsdesk/2014/01/always-never-nuclear-command-and-control.html',
        'info_dict': {
            'id': 'always-never',
            'title': 'Always / Never - The New Yorker',
        },
        'playlist_count': 3,
        'params': {
            'extract_flat': False,
            'skip_download': True,
        },
        'skip': 'Redirects, page gone',
    }, {
        # BrightcoveInPageEmbed embed
        'url': 'http://www.geekandsundry.com/tabletop-bonus-wils-final-thoughts-on-dread/',
        'info_dict': {
            'id': '4238694884001',
            'ext': 'flv',
            'title': 'Tabletop: Dread, Last Thoughts',
            'description': 'Tabletop: Dread, Last Thoughts',
            'duration': 51690,
        },
        'skip': 'Redirects, page gone',
    }, {
        # Brightcove embed, with no valid 'renditions' but valid 'IOSRenditions'
        # This video can't be played in browsers if Flash disabled and UA set to iPhone, which is actually a false alarm
        'url': 'https://dl.dropboxusercontent.com/u/29092637/interview.html',
        'info_dict': {
            'id': '4785848093001',
            'ext': 'mp4',
            'title': 'The Cardinal Pell Interview',
            'description': 'Sky News Contributor Andrew Bolt interviews George Pell in Rome, following the Cardinal\'s evidence before the Royal Commission into Child Abuse. ',
            'uploader': 'GlobeCast Australia - GlobeStream',
            'uploader_id': '2733773828001',
            'upload_date': '20160304',
            'timestamp': 1457083087,
        },
        'params': {
            # m3u8 downloads
            'skip_download': True,
        },
        'skip': '404 Not Found',
    }, {
        # Brightcove embed with whitespace around attribute names
        'url': 'http://www.stack.com/video/3167554373001/learn-to-hit-open-three-pointers-with-damian-lillard-s-baseline-drift-drill',
        'info_dict': {
            'id': '3167554373001',
            'ext': 'mp4',
            'title': "Learn to Hit Open Three-Pointers With Damian Lillard's Baseline Drift Drill",
            'description': 'md5:57bacb0e0f29349de4972bfda3191713',
            'uploader_id': '1079349493',
            'upload_date': '20140207',
            'timestamp': 1391810548,
        },
        'params': {
            'skip_download': True,
        },
        'skip': '410 Gone',
    }]

    @classmethod
    def _build_brightcove_url(cls, object_str):
        """
        Build a Brightcove url from a xml string containing
        <object class="BrightcoveExperience">{params}</object>
        """

        # Fix up some stupid HTML, see https://github.com/ytdl-org/youtube-dl/issues/1553
        object_str = re.sub(r'(<param(?:\s+[a-zA-Z0-9_]+="[^"]*")*)>',
                            lambda m: m.group(1) + '/>', object_str)
        # Fix up some stupid XML, see https://github.com/ytdl-org/youtube-dl/issues/1608
        object_str = object_str.replace('<--', '<!--')
        # remove namespace to simplify extraction
        object_str = re.sub(r'(<object[^>]*)(xmlns=".*?")', r'\1', object_str)
        object_str = fix_xml_ampersands(object_str)

        try:
            object_doc = compat_etree_fromstring(object_str.encode())
        except xml.etree.ElementTree.ParseError:
            return

        fv_el = find_xpath_attr(object_doc, './param', 'name', 'flashVars')
        if fv_el is not None:
            flashvars = dict(
                (k, v[0])
                for k, v in urllib.parse.parse_qs(fv_el.attrib['value']).items())
        else:
            flashvars = {}

        data_url = object_doc.attrib.get('data', '')
        data_url_params = parse_qs(data_url)

        def find_param(name):
            if name in flashvars:
                return flashvars[name]
            node = find_xpath_attr(object_doc, './param', 'name', name)
            if node is not None:
                return node.attrib['value']
            return data_url_params.get(name)

        params = {}

        player_id = find_param('playerID') or find_param('playerId')
        if player_id is None:
            raise ExtractorError('Cannot find player ID')
        params['playerID'] = player_id

        player_key = find_param('playerKey')
        # Not all pages define this value
        if player_key is not None:
            params['playerKey'] = player_key
        # These fields hold the id of the video
        video_player = find_param('@videoPlayer') or find_param('videoId') or find_param('videoID') or find_param('@videoList')
        if video_player is not None:
            if isinstance(video_player, list):
                video_player = video_player[0]
            video_player = video_player.strip()
            # UUID is also possible for videoPlayer (e.g.
            # http://www.popcornflix.com/hoodies-vs-hooligans/7f2d2b87-bbf2-4623-acfb-ea942b4f01dd
            # or http://www8.hp.com/cn/zh/home.html)
            if not (re.match(
                    r'^(?:\d+|[\da-fA-F]{8}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{4}-?[\da-fA-F]{12})$',
                    video_player) or video_player.startswith('ref:')):
                return None
            params['@videoPlayer'] = video_player
        link_base = find_param('linkBaseURL')
        if link_base is not None:
            params['linkBaseURL'] = link_base
        return cls._make_brightcove_url(params)

    @classmethod
    def _build_brightcove_url_from_js(cls, object_js):
        # The layout of JS is as follows:
        # customBC.createVideo = function (width, height, playerID, playerKey, videoPlayer, VideoRandomID) {
        #   // build Brightcove <object /> XML
        # }
        m = re.search(
            r'''(?x)customBC\.createVideo\(
                .*?                                                  # skipping width and height
                ["\'](?P<playerID>\d+)["\']\s*,\s*                   # playerID
                ["\'](?P<playerKey>AQ[^"\']{48})[^"\']*["\']\s*,\s*  # playerKey begins with AQ and is 50 characters
                                                                     # in length, however it's appended to itself
                                                                     # in places, so truncate
                ["\'](?P<videoID>\d+)["\']                           # @videoPlayer
            ''', object_js)
        if m:
            return cls._make_brightcove_url(m.groupdict())

    @classmethod
    def _make_brightcove_url(cls, params):
        return update_url_query(
            'https://c.brightcove.com/services/viewer/htmlFederated', params)

    @classmethod
    def _extract_brightcove_url(cls, webpage):
        """Try to extract the brightcove url from the webpage, returns None
        if it can't be found
        """
        urls = cls._extract_brightcove_urls(webpage)
        return urls[0] if urls else None

    @classmethod
    def _extract_brightcove_urls(cls, webpage):
        """Return a list of all Brightcove URLs from the webpage """

        url_m = re.search(
            r'''(?x)
                <meta\s+
                    (?:property|itemprop)=([\'"])(?:og:video|embedURL)\1[^>]+
                    content=([\'"])(?P<url>https?://(?:secure|c)\.brightcove.com/(?:(?!\2).)+)\2
            ''', webpage)
        if url_m:
            url = unescapeHTML(url_m.group('url'))
            # Some sites don't add it, we can't download with this url, for example:
            # http://www.ktvu.com/videos/news/raw-video-caltrain-releases-video-of-man-almost/vCTZdY/
            if 'playerKey' in url or 'videoId' in url or 'idVideo' in url:
                return [url]

        matches = re.findall(
            r'''(?sx)<object
            (?:
                [^>]+?class=[\'"][^>]*?BrightcoveExperience.*?[\'"] |
                [^>]*?>\s*<param\s+name="movie"\s+value="https?://[^/]*brightcove\.com/
            ).+?>\s*</object>''',
            webpage)
        if matches:
            return list(filter(None, [cls._build_brightcove_url(m) for m in matches]))

        matches = re.findall(r'(customBC\.createVideo\(.+?\);)', webpage)
        if matches:
            return list(filter(None, [
                cls._build_brightcove_url_from_js(custom_bc)
                for custom_bc in matches]))
        return [src for _, src in re.findall(
            r'<iframe[^>]+src=([\'"])((?:https?:)?//link\.brightcove\.com/services/player/(?!\1).+)\1', webpage)]

    def _extract_from_webpage(self, url, webpage):
        bc_urls = self._extract_brightcove_urls(webpage)
        for bc_url in bc_urls:
            yield self.url_result(smuggle_url(bc_url, {'Referer': url}), BrightcoveLegacyIE)

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        # Change the 'videoId' and others field to '@videoPlayer'
        url = re.sub(r'(?<=[?&])(videoI(d|D)|idVideo|bctid)', '%40videoPlayer', url)
        # Change bckey (used by bcove.me urls) to playerKey
        url = re.sub(r'(?<=[?&])bckey', 'playerKey', url)
        mobj = self._match_valid_url(url)
        query_str = mobj.group('query')
        query = urllib.parse.parse_qs(query_str)

        video_player = query.get('@videoPlayer')
        if video_player:
            # We set the original url as the default 'Referer' header
            referer = query.get('linkBaseURL', [None])[0] or smuggled_data.get('Referer', url)
            video_id = video_player[0]
            if 'playerID' not in query:
                mobj = re.search(r'/bcpid(\d+)', url)
                if mobj is not None:
                    query['playerID'] = [mobj.group(1)]
            publisher_id = query.get('publisherId')
            if publisher_id and publisher_id[0].isdigit():
                publisher_id = publisher_id[0]
            if not publisher_id:
                player_key = query.get('playerKey')
                if player_key and ',' in player_key[0]:
                    player_key = player_key[0]
                else:
                    player_id = query.get('playerID')
                    if player_id and player_id[0].isdigit():
                        headers = {}
                        if referer:
                            headers['Referer'] = referer
                        player_page = self._download_webpage(
                            'https://link.brightcove.com/services/player/bcpid' + player_id[0],
                            video_id, headers=headers, fatal=False)
                        if player_page:
                            player_key = self._search_regex(
                                r'<param\s+name="playerKey"\s+value="([\w~,-]+)"',
                                player_page, 'player key', fatal=False)
                if player_key:
                    enc_pub_id = player_key.split(',')[1].replace('~', '=')
                    publisher_id = struct.unpack('>Q', base64.urlsafe_b64decode(enc_pub_id))[0]
            if publisher_id:
                brightcove_new_url = f'https://players.brightcove.net/{publisher_id}/default_default/index.html?videoId={video_id}'
                if referer:
                    brightcove_new_url = smuggle_url(brightcove_new_url, {'referrer': referer})
                return self.url_result(brightcove_new_url, BrightcoveNewIE.ie_key(), video_id)
        # TODO: figure out if it's possible to extract playlistId from playerKey
        # elif 'playerKey' in query:
        #     player_key = query['playerKey']
        #     return self._get_playlist_info(player_key[0])
        raise UnsupportedError(url)


class BrightcoveNewBaseIE(AdobePassIE):
    def _parse_brightcove_metadata(self, json_data, video_id, headers={}):
        formats, subtitles = [], {}
        sources = json_data.get('sources') or []
        for source in sources:
            container = source.get('container')
            ext = mimetype2ext(source.get('type'))
            src = source.get('src')
            if ext == 'm3u8' or container == 'M2TS':
                if not src:
                    continue
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    src, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif ext == 'mpd':
                if not src:
                    continue
                fmts, subs = self._extract_mpd_formats_and_subtitles(src, video_id, 'dash', fatal=False)
                subtitles = self._merge_subtitles(subtitles, subs)
            else:
                streaming_src = source.get('streaming_src')
                stream_name, app_name = source.get('stream_name'), source.get('app_name')
                if not src and not streaming_src and (not stream_name or not app_name):
                    continue
                tbr = float_or_none(source.get('avg_bitrate'), 1000)
                height = int_or_none(source.get('height'))
                width = int_or_none(source.get('width'))
                f = {
                    'tbr': tbr,
                    'filesize': int_or_none(source.get('size')),
                    'container': container,
                    'ext': ext or container.lower(),
                }
                if width == 0 and height == 0:
                    f.update({
                        'vcodec': 'none',
                    })
                else:
                    f.update({
                        'width': width,
                        'height': height,
                        'vcodec': source.get('codec'),
                    })

                def build_format_id(kind):
                    return join_nonempty(kind, tbr and f'{int(tbr)}k', height and f'{height}p')

                if src or streaming_src:
                    f.update({
                        'url': src or streaming_src,
                        'format_id': build_format_id('http' if src else 'http-streaming'),
                        'source_preference': 0 if src else -1,
                    })
                else:
                    f.update({
                        'url': app_name,
                        'play_path': stream_name,
                        'format_id': build_format_id('rtmp'),
                    })
                fmts = [f]

            # https://support.brightcove.com/playback-api-video-fields-reference#key_systems_object
            if container == 'WVM' or source.get('key_systems') or ext == 'ism':
                for f in fmts:
                    f['has_drm'] = True
            formats.extend(fmts)

        if not formats:
            errors = json_data.get('errors')
            if errors:
                error = errors[0]
                self.raise_no_formats(
                    error.get('message') or error.get('error_subcode') or error['error_code'], expected=True)

        headers.pop('Authorization', None)  # or else http formats will give error 400
        for f in formats:
            f.setdefault('http_headers', {}).update(headers)

        for text_track in json_data.get('text_tracks', []):
            if text_track.get('kind') != 'captions':
                continue
            text_track_url = url_or_none(text_track.get('src'))
            if not text_track_url:
                continue
            lang = (str_or_none(text_track.get('srclang'))
                    or str_or_none(text_track.get('label')) or 'en').lower()
            subtitles.setdefault(lang, []).append({
                'url': text_track_url,
            })

        is_live = False
        duration = float_or_none(json_data.get('duration'), 1000)
        if duration is not None and duration <= 0:
            is_live = True

        common_res = [(160, 90), (320, 180), (480, 720), (640, 360), (768, 432), (1024, 576), (1280, 720), (1366, 768), (1920, 1080)]
        thumb_base_url = dict_get(json_data, ('poster', 'thumbnail'))
        thumbnails = [{
            'url': re.sub(r'\d+x\d+', f'{w}x{h}', thumb_base_url),
            'width': w,
            'height': h,
        } for w, h in common_res] if thumb_base_url else None

        return {
            'id': video_id,
            'thumbnails': thumbnails,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
            **traverse_obj(json_data, {
                'title': ('name', {clean_html}),
                'description': ('description', {clean_html}),
                'tags': ('tags', ..., {str}, filter, all, filter),
                'timestamp': ('published_at', {parse_iso8601}),
                'uploader_id': ('account_id', {str}),
            }),
        }


class BrightcoveNewIE(BrightcoveNewBaseIE):
    IE_NAME = 'brightcove:new'
    _VALID_URL = r'https?://players\.brightcove\.net/(?P<account_id>\d+)/(?P<player_id>[^/]+)_(?P<embed>[^/]+)/index\.html\?.*(?P<content_type>video|playlist)Id=(?P<video_id>\d+|ref:[^&]+)'
    _TESTS = [{
        'url': 'http://players.brightcove.net/929656772001/e41d32dc-ec74-459e-a845-6c69f7b724ea_default/index.html?videoId=4463358922001',
        'md5': 'c8100925723840d4b0d243f7025703be',
        'info_dict': {
            'id': '4463358922001',
            'ext': 'mp4',
            'title': 'Meet the man behind Popcorn Time',
            'description': 'md5:eac376a4fe366edc70279bfb681aea16',
            'duration': 165.768,
            'timestamp': 1441391203,
            'upload_date': '20150904',
            'uploader_id': '929656772001',
            'formats': 'mincount:20',
        },
        'skip': '404 Not Found',
    }, {
        # with rtmp streams
        'url': 'http://players.brightcove.net/4036320279001/5d112ed9-283f-485f-a7f9-33f42e8bc042_default/index.html?videoId=4279049078001',
        'info_dict': {
            'id': '4279049078001',
            'ext': 'mp4',
            'title': 'Titansgrave: Chapter 0',
            'description': 'Titansgrave: Chapter 0',
            'duration': 1242.058,
            'timestamp': 1433556729,
            'upload_date': '20150606',
            'uploader_id': '4036320279001',
            'formats': 'mincount:39',
        },
        'skip': '404 Not Found',
    }, {
        # playlist stream
        'url': 'https://players.brightcove.net/1752604059001/S13cJdUBz_default/index.html?playlistId=5718313430001',
        'info_dict': {
            'id': '5718313430001',
            'title': 'No Audio Playlist',
        },
        'playlist_count': 7,
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://players.brightcove.net/5690807595001/HyZNerRl7_default/index.html?playlistId=5743160747001',
        'only_matching': True,
    }, {
        # ref: prefixed video id
        'url': 'http://players.brightcove.net/3910869709001/21519b5c-4b3b-4363-accb-bdc8f358f823_default/index.html?videoId=ref:7069442',
        'only_matching': True,
    }, {
        # non numeric ref: prefixed video id
        'url': 'http://players.brightcove.net/710858724001/default_default/index.html?videoId=ref:event-stream-356',
        'only_matching': True,
    }, {
        # unavailable video without message but with error_code
        'url': 'http://players.brightcove.net/1305187701/c832abfb-641b-44eb-9da0-2fe76786505f_default/index.html?videoId=4377407326001',
        'only_matching': True,
    }]

    _WEBPAGE_TESTS = [{
        # brightcove player url embed
        'url': 'https://nbc-2.com/weather/forecast/2022/11/16/forecast-warmest-day-of-the-week/',
        'md5': '2934d5372b354d27083ccf8575dbfee2',
        'info_dict': {
            'id': '6315650313112',
            'title': 'First Alert Forecast: November 15, 2022',
            'ext': 'mp4',
            'tags': ['nbc2', 'forecast'],
            'uploader_id': '6146886170001',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1668574571,
            'duration': 233.375,
            'upload_date': '20221116',
        },
    }, {
        # embedded with video tag only
        'url': 'https://www.gooddishtv.com/tiktok-rapping-chef-mr-pyrex',
        'info_dict': {
            'id': 'tiktok-rapping-chef-mr-pyrex',
            'title': 'TikTok\'s Rapping Chef Makes Jambalaya for the Hosts',
            'thumbnail': r're:^https?://.*\.jpg$',
            'age_limit': 0,
            'description': 'Just in time for Mardi Gras',
        },
        'playlist': [{
            'info_dict': {
                'id': '6299189544001',
                'ext': 'mp4',
                'title': 'TGD_01-032_5',
                'thumbnail': r're:^https?://.*\.jpg$',
                'timestamp': 1646078943,
                'uploader_id': '1569565978001',
                'upload_date': '20220228',
                'duration': 217.195,
            },
        }, {
            'info_dict': {
                'id': '6305565995112',
                'ext': 'mp4',
                'title': 'TGD 01-087 (Airs 05.25.22)_Segment 5',
                'thumbnail': r're:^https?://.*\.jpg$',
                'timestamp': 1651604591,
                'uploader_id': '1569565978001',
                'upload_date': '20220503',
                'duration': 310.421,
            },
        }],
    }, {
        # Brightcove:new type [2].
        'url': 'http://www.delawaresportszone.com/video-st-thomas-more-earns-first-trip-to-basketball-semis',
        'md5': '2b35148fcf48da41c9fb4591650784f3',
        'info_dict': {
            'id': '5348741021001',
            'ext': 'mp4',
            'upload_date': '20170306',
            'uploader_id': '4191638492001',
            'timestamp': 1488769918,
            'title': 'VIDEO:  St. Thomas More earns first trip to basketball semis',
        },
        'skip': '404 Not Found',
    }, {
        # Alternative brightcove <video> attributes
        'url': 'http://www.programme-tv.net/videos/extraits/81095-guillaume-canet-evoque-les-rumeurs-d-infidelite-de-marion-cotillard-avec-brad-pitt-dans-vivement-dimanche/',
        'info_dict': {
            'id': '81095-guillaume-canet-evoque-les-rumeurs-d-infidelite-de-marion-cotillard-avec-brad-pitt-dans-vivement-dimanche',
            'title': "Guillaume Canet évoque les rumeurs d'infidélité de Marion Cotillard avec Brad Pitt dans Vivement Dimanche, Extraits : toutes les vidéos avec Télé-Loisirs",
        },
        'playlist': [{
            'md5': '732d22ba3d33f2f3fc253c39f8f36523',
            'info_dict': {
                'id': '5311302538001',
                'ext': 'mp4',
                'title': "Guillaume Canet évoque les rumeurs d'infidélité de Marion Cotillard avec Brad Pitt dans Vivement Dimanche",
                'description': "Guillaume Canet évoque les rumeurs d'infidélité de Marion Cotillard avec Brad Pitt dans Vivement Dimanche (France 2, 5 février 2017)",
                'timestamp': 1486321708,
                'upload_date': '20170205',
                'uploader_id': '800000640001',
            },
            'only_matching': True,
        }],
        'skip': '404 Not Found',
    }, {
        # Brightcove URL in single quotes
        'url': 'http://www.sportsnet.ca/baseball/mlb/sn-presents-russell-martin-world-citizen/',
        'md5': '4ae374f1f8b91c889c4b9203c8c752af',
        'info_dict': {
            'id': '4255764656001',
            'ext': 'mp4',
            'title': 'SN Presents: Russell Martin, World Citizen',
            'description': 'To understand why he was the Toronto Blue Jays’ top off-season priority is to appreciate his background and upbringing in Montreal, where he first developed his baseball skills. Written and narrated by Stephen Brunt.',
            'uploader': 'Rogers Sportsnet',
            'uploader_id': '1704050871',
            'upload_date': '20150525',
            'timestamp': 1432570283,
        },
        'skip': 'Page no longer has URL, now has javascript',
    }]

    @staticmethod
    def _extract_url(ie, webpage):
        urls = BrightcoveNewIE._extract_brightcove_urls(ie, webpage)
        return urls[0] if urls else None

    @staticmethod
    def _extract_brightcove_urls(ie, webpage):
        # Reference:
        # 1. http://docs.brightcove.com/en/video-cloud/brightcove-player/guides/publish-video.html#setvideoiniframe
        # 2. http://docs.brightcove.com/en/video-cloud/brightcove-player/guides/publish-video.html#tag
        # 3. http://docs.brightcove.com/en/video-cloud/brightcove-player/guides/publish-video.html#setvideousingjavascript
        # 4. http://docs.brightcove.com/en/video-cloud/brightcove-player/guides/in-page-embed-player-implementation.html
        # 5. https://support.brightcove.com/en/video-cloud/docs/dynamically-assigning-videos-player

        entries = []

        # Look for iframe embeds [1]
        for _, url in re.findall(
                r'<iframe[^>]+src=(["\'])((?:https?:)?//players\.brightcove\.net/\d+/[^/]+/index\.html.+?)\1', webpage):
            entries.append(url if url.startswith(('http:', 'https:')) else 'https:' + url)

        # Look for <video> tags [2] and embed_in_page embeds [3]
        # [2] looks like:
        for video, script_tag, account_id, player_id, embed in re.findall(
                r'''(?isx)
                    (<video(?:-js)?\s+[^>]*\bdata-video-id\s*=\s*['"]?[^>]+>)
                    (?:.*?
                        (<script[^>]+
                            src=["\'](?:https?:)?//players\.brightcove\.net/
                            (\d+)/([^/]+)_([^/]+)/index(?:\.min)?\.js
                        )
                    )?
                ''', webpage):
            attrs = extract_attributes(video)

            # According to examples from [4] it's unclear whether video id
            # may be optional and what to do when it is
            video_id = attrs.get('data-video-id')
            if not video_id:
                continue

            account_id = account_id or attrs.get('data-account')
            if not account_id:
                continue

            player_id = player_id or attrs.get('data-player') or 'default'
            embed = embed or attrs.get('data-embed') or 'default'

            bc_url = f'https://players.brightcove.net/{account_id}/{player_id}_{embed}/index.html?videoId={video_id}'

            # Some brightcove videos may be embedded with video tag only and
            # without script tag or any mentioning of brightcove at all. Such
            # embeds are considered ambiguous since they are matched based only
            # on data-video-id and data-account attributes and in the wild may
            # not be brightcove embeds at all. Let's check reconstructed
            # brightcove URLs in case of such embeds and only process valid
            # ones. By this we ensure there is indeed a brightcove embed.
            if not script_tag and not ie._is_valid_url(
                    bc_url, video_id, 'possible brightcove video'):
                continue

            entries.append(bc_url)

        return entries

    def _extract_from_webpage(self, url, webpage):
        bc_urls = self._extract_brightcove_urls(self, webpage)
        for bc_url in bc_urls:
            yield self.url_result(smuggle_url(bc_url, {'referrer': url}), BrightcoveNewIE)

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        self._initialize_geo_bypass({
            'countries': smuggled_data.get('geo_countries'),
            'ip_blocks': smuggled_data.get('geo_ip_blocks'),
        })

        account_id, player_id, embed, content_type, video_id = self._match_valid_url(url).groups()

        policy_key_id = f'{account_id}_{player_id}'
        policy_key = self.cache.load('brightcove', policy_key_id)
        policy_key_extracted = False
        store_pk = lambda x: self.cache.store('brightcove', policy_key_id, x)

        def extract_policy_key():
            base_url = f'https://players.brightcove.net/{account_id}/{player_id}_{embed}/'
            config = self._download_json(
                base_url + 'config.json', video_id, fatal=False) or {}
            policy_key = try_get(
                config, lambda x: x['video_cloud']['policy_key'])
            if not policy_key:
                webpage = self._download_webpage(
                    base_url + 'index.min.js', video_id)

                catalog = self._search_regex(
                    r'catalog\(({.+?})\);', webpage, 'catalog', default=None)
                if catalog:
                    catalog = self._parse_json(
                        js_to_json(catalog), video_id, fatal=False)
                    if catalog:
                        policy_key = catalog.get('policyKey')

                if not policy_key:
                    policy_key = self._search_regex(
                        r'policyKey\s*:\s*(["\'])(?P<pk>.+?)\1',
                        webpage, 'policy key', group='pk')

            store_pk(policy_key)
            return policy_key

        token = smuggled_data.get('token')
        api_url = f'https://{"edge-auth" if token else "edge"}.api.brightcove.com/playback/v1/accounts/{account_id}/{content_type}s/{video_id}'
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        referrer = smuggled_data.get('referrer')  # XXX: notice the spelling/case of the key
        if referrer:
            headers.update({
                'Referer': referrer,
                'Origin': re.search(r'https?://[^/]+', referrer).group(0),
            })

        for _ in range(2):
            if not policy_key:
                policy_key = extract_policy_key()
                policy_key_extracted = True
            headers['Accept'] = f'application/json;pk={policy_key}'
            try:
                json_data = self._download_json(api_url, video_id, headers=headers)
                break
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status in (401, 403):
                    json_data = self._parse_json(e.cause.response.read().decode(), video_id)[0]
                    message = json_data.get('message') or json_data['error_code']
                    if json_data.get('error_subcode') == 'CLIENT_GEO':
                        self.raise_geo_restricted(msg=message)
                    elif json_data.get('error_code') == 'INVALID_POLICY_KEY' and not policy_key_extracted:
                        policy_key = None
                        store_pk(None)
                        continue
                    raise ExtractorError(message, expected=True)
                raise

        errors = json_data.get('errors')
        if errors and errors[0].get('error_subcode') == 'TVE_AUTH':
            custom_fields = json_data['custom_fields']
            missing_fields = ', '.join(
                key for key in ('source_url', 'software_statement') if not smuggled_data.get(key))
            if missing_fields:
                raise ExtractorError(
                    f'Missing fields in smuggled data: {missing_fields}. '
                    f'This video can be only extracted from the webpage where it is embedded. '
                    f'Pass the URL of the embedding webpage instead of the Brightcove URL', expected=True)
            tve_token = self._extract_mvpd_auth(
                smuggled_data['source_url'], video_id,
                custom_fields['bcadobepassrequestorid'],
                custom_fields['bcadobepassresourceid'],
                smuggled_data['software_statement'])
            json_data = self._download_json(
                api_url, video_id, headers={
                    'Accept': f'application/json;pk={policy_key}',
                }, query={
                    'tveToken': tve_token,
                })

        if content_type == 'playlist':
            return self.playlist_result(
                (self._parse_brightcove_metadata(vid, vid['id'], headers)
                 for vid in traverse_obj(json_data, ('videos', lambda _, v: v['id']))),
                json_data.get('id'), json_data.get('name'),
                json_data.get('description'))

        return self._parse_brightcove_metadata(
            json_data, video_id, headers=headers)
