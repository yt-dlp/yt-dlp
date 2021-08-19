# coding: utf-8
from __future__ import unicode_literals

import hashlib
import json
import re
from xml.sax.saxutils import escape

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_HTTPError,
)
from ..utils import (
    js_to_json,
    smuggle_url,
    try_get,
    xpath_text,
    xpath_element,
    xpath_with_ns,
    find_xpath_attr,
    orderedSet,
    parse_duration,
    parse_iso8601,
    parse_age_limit,
    strip_or_none,
    int_or_none,
    ExtractorError,
)


class CBCIE(InfoExtractor):
    IE_NAME = 'cbc.ca'
    _VALID_URL = r'https?://(?:www\.)?cbc\.ca/(?!player/)(?:[^/]+/)+(?P<id>[^/?#]+)'
    _TESTS = [{
        # with mediaId
        'url': 'http://www.cbc.ca/22minutes/videos/clips-season-23/don-cherry-play-offs',
        'md5': '97e24d09672fc4cf56256d6faa6c25bc',
        'info_dict': {
            'id': '2682904050',
            'ext': 'mp4',
            'title': 'Don Cherry – All-Stars',
            'description': 'Don Cherry has a bee in his bonnet about AHL player John Scott because that guy’s got heart.',
            'timestamp': 1454463000,
            'upload_date': '20160203',
            'uploader': 'CBCC-NEW',
        },
        'skip': 'Geo-restricted to Canada',
    }, {
        # with clipId, feed available via tpfeed.cbc.ca and feed.theplatform.com
        'url': 'http://www.cbc.ca/22minutes/videos/22-minutes-update/22-minutes-update-episode-4',
        'md5': '162adfa070274b144f4fdc3c3b8207db',
        'info_dict': {
            'id': '2414435309',
            'ext': 'mp4',
            'title': '22 Minutes Update: What Not To Wear Quebec',
            'description': "This week's latest Canadian top political story is What Not To Wear Quebec.",
            'upload_date': '20131025',
            'uploader': 'CBCC-NEW',
            'timestamp': 1382717907,
        },
    }, {
        # with clipId, feed only available via tpfeed.cbc.ca
        'url': 'http://www.cbc.ca/archives/entry/1978-robin-williams-freestyles-on-90-minutes-live',
        'md5': '0274a90b51a9b4971fe005c63f592f12',
        'info_dict': {
            'id': '2487345465',
            'ext': 'mp4',
            'title': 'Robin Williams freestyles on 90 Minutes Live',
            'description': 'Wacky American comedian Robin Williams shows off his infamous "freestyle" comedic talents while being interviewed on CBC\'s 90 Minutes Live.',
            'upload_date': '19780210',
            'uploader': 'CBCC-NEW',
            'timestamp': 255977160,
        },
    }, {
        # multiple iframes
        'url': 'http://www.cbc.ca/natureofthings/blog/birds-eye-view-from-vancouvers-burrard-street-bridge-how-we-got-the-shot',
        'playlist': [{
            'md5': '377572d0b49c4ce0c9ad77470e0b96b4',
            'info_dict': {
                'id': '2680832926',
                'ext': 'mp4',
                'title': 'An Eagle\'s-Eye View Off Burrard Bridge',
                'description': 'Hercules the eagle flies from Vancouver\'s Burrard Bridge down to a nearby park with a mini-camera strapped to his back.',
                'upload_date': '20160201',
                'timestamp': 1454342820,
                'uploader': 'CBCC-NEW',
            },
        }, {
            'md5': '415a0e3f586113894174dfb31aa5bb1a',
            'info_dict': {
                'id': '2658915080',
                'ext': 'mp4',
                'title': 'Fly like an eagle!',
                'description': 'Eagle equipped with a mini camera flies from the world\'s tallest tower',
                'upload_date': '20150315',
                'timestamp': 1426443984,
                'uploader': 'CBCC-NEW',
            },
        }],
        'skip': 'Geo-restricted to Canada',
    }, {
        # multiple CBC.APP.Caffeine.initInstance(...)
        'url': 'http://www.cbc.ca/news/canada/calgary/dog-indoor-exercise-winter-1.3928238',
        'info_dict': {
            'title': 'Keep Rover active during the deep freeze with doggie pushups and other fun indoor tasks',
            'id': 'dog-indoor-exercise-winter-1.3928238',
            'description': 'md5:c18552e41726ee95bd75210d1ca9194c',
        },
        'playlist_mincount': 6,
    }]

    @classmethod
    def suitable(cls, url):
        return False if CBCPlayerIE.suitable(url) else super(CBCIE, cls).suitable(url)

    def _extract_player_init(self, player_init, display_id):
        player_info = self._parse_json(player_init, display_id, js_to_json)
        media_id = player_info.get('mediaId')
        if not media_id:
            clip_id = player_info['clipId']
            feed = self._download_json(
                'http://tpfeed.cbc.ca/f/ExhSPC/vms_5akSXx4Ng_Zn?byCustomValue={:mpsReleases}{%s}' % clip_id,
                clip_id, fatal=False)
            if feed:
                media_id = try_get(feed, lambda x: x['entries'][0]['guid'], compat_str)
            if not media_id:
                media_id = self._download_json(
                    'http://feed.theplatform.com/f/h9dtGB/punlNGjMlc1F?fields=id&byContent=byReleases%3DbyId%253D' + clip_id,
                    clip_id)['entries'][0]['id'].split('/')[-1]
        return self.url_result('cbcplayer:%s' % media_id, 'CBCPlayer', media_id)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        title = self._og_search_title(webpage, default=None) or self._html_search_meta(
            'twitter:title', webpage, 'title', default=None) or self._html_search_regex(
                r'<title>([^<]+)</title>', webpage, 'title', fatal=False)
        entries = [
            self._extract_player_init(player_init, display_id)
            for player_init in re.findall(r'CBC\.APP\.Caffeine\.initInstance\(({.+?})\);', webpage)]
        media_ids = []
        for media_id_re in (
                r'<iframe[^>]+src="[^"]+?mediaId=(\d+)"',
                r'<div[^>]+\bid=["\']player-(\d+)',
                r'guid["\']\s*:\s*["\'](\d+)'):
            media_ids.extend(re.findall(media_id_re, webpage))
        entries.extend([
            self.url_result('cbcplayer:%s' % media_id, 'CBCPlayer', media_id)
            for media_id in orderedSet(media_ids)])
        return self.playlist_result(
            entries, display_id, strip_or_none(title),
            self._og_search_description(webpage))


class CBCPlayerIE(InfoExtractor):
    IE_NAME = 'cbc.ca:player'
    _VALID_URL = r'(?:cbcplayer:|https?://(?:www\.)?cbc\.ca/(?:player/play/|i/caffeine/syndicate/\?mediaId=))(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.cbc.ca/player/play/2683190193',
        'md5': '64d25f841ddf4ddb28a235338af32e2c',
        'info_dict': {
            'id': '2683190193',
            'ext': 'mp4',
            'title': 'Gerry Runs a Sweat Shop',
            'description': 'md5:b457e1c01e8ff408d9d801c1c2cd29b0',
            'timestamp': 1455071400,
            'upload_date': '20160210',
            'uploader': 'CBCC-NEW',
        },
        'skip': 'Geo-restricted to Canada',
    }, {
        # Redirected from http://www.cbc.ca/player/AudioMobile/All%20in%20a%20Weekend%20Montreal/ID/2657632011/
        'url': 'http://www.cbc.ca/player/play/2657631896',
        'md5': 'e5e708c34ae6fca156aafe17c43e8b75',
        'info_dict': {
            'id': '2657631896',
            'ext': 'mp3',
            'title': 'CBC Montreal is organizing its first ever community hackathon!',
            'description': 'The modern technology we tend to depend on so heavily, is never without it\'s share of hiccups and headaches. Next weekend - CBC Montreal will be getting members of the public for its first Hackathon.',
            'timestamp': 1425704400,
            'upload_date': '20150307',
            'uploader': 'CBCC-NEW',
        },
    }, {
        'url': 'http://www.cbc.ca/player/play/2164402062',
        'md5': '33fcd8f6719b9dd60a5e73adcb83b9f6',
        'info_dict': {
            'id': '2164402062',
            'ext': 'mp4',
            'title': 'Cancer survivor four times over',
            'description': 'Tim Mayer has beaten three different forms of cancer four times in five years.',
            'timestamp': 1320410746,
            'upload_date': '20111104',
            'uploader': 'CBCC-NEW',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return {
            '_type': 'url_transparent',
            'ie_key': 'ThePlatform',
            'url': smuggle_url(
                'http://link.theplatform.com/s/ExhSPC/media/guid/2655402169/%s?mbr=true&formats=MPEG4,FLV,MP3' % video_id, {
                    'force_smil_url': True
                }),
            'id': video_id,
        }


class CBCWatchBaseIE(InfoExtractor):
    _device_id = None
    _device_token = None
    _API_BASE_URL = 'https://api-cbc.cloud.clearleap.com/cloffice/client/'
    _NS_MAP = {
        'media': 'http://search.yahoo.com/mrss/',
        'clearleap': 'http://www.clearleap.com/namespace/clearleap/1.0/',
    }
    _GEO_COUNTRIES = ['CA']
    _LOGIN_URL = 'https://api.loginradius.com/identity/v2/auth/login'
    _TOKEN_URL = 'https://cloud-api.loginradius.com/sso/jwt/api/token'
    _API_KEY = '3f4beddd-2061-49b0-ae80-6f1f2ed65b37'
    _NETRC_MACHINE = 'cbcwatch'

    def _signature(self, email, password):
        data = json.dumps({
            'email': email,
            'password': password,
        }).encode()
        headers = {'content-type': 'application/json'}
        query = {'apikey': self._API_KEY}
        resp = self._download_json(self._LOGIN_URL, None, data=data, headers=headers, query=query)
        access_token = resp['access_token']

        # token
        query = {
            'access_token': access_token,
            'apikey': self._API_KEY,
            'jwtapp': 'jwt',
        }
        resp = self._download_json(self._TOKEN_URL, None, headers=headers, query=query)
        return resp['signature']

    def _call_api(self, path, video_id):
        url = path if path.startswith('http') else self._API_BASE_URL + path
        for _ in range(2):
            try:
                result = self._download_xml(url, video_id, headers={
                    'X-Clearleap-DeviceId': self._device_id,
                    'X-Clearleap-DeviceToken': self._device_token,
                })
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                    # Device token has expired, re-acquiring device token
                    self._register_device()
                    continue
                raise
        error_message = xpath_text(result, 'userMessage') or xpath_text(result, 'systemMessage')
        if error_message:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, error_message))
        return result

    def _real_initialize(self):
        if self._valid_device_token():
            return
        device = self._downloader.cache.load(
            'cbcwatch', self._cache_device_key()) or {}
        self._device_id, self._device_token = device.get('id'), device.get('token')
        if self._valid_device_token():
            return
        self._register_device()

    def _valid_device_token(self):
        return self._device_id and self._device_token

    def _cache_device_key(self):
        email, _ = self._get_login_info()
        return '%s_device' % hashlib.sha256(email.encode()).hexdigest() if email else 'device'

    def _register_device(self):
        result = self._download_xml(
            self._API_BASE_URL + 'device/register',
            None, 'Acquiring device token',
            data=b'<device><type>web</type></device>')
        self._device_id = xpath_text(result, 'deviceId', fatal=True)
        email, password = self._get_login_info()
        if email and password:
            signature = self._signature(email, password)
            data = '<login><token>{0}</token><device><deviceId>{1}</deviceId><type>web</type></device></login>'.format(
                escape(signature), escape(self._device_id)).encode()
            url = self._API_BASE_URL + 'device/login'
            result = self._download_xml(
                url, None, data=data,
                headers={'content-type': 'application/xml'})
            self._device_token = xpath_text(result, 'token', fatal=True)
        else:
            self._device_token = xpath_text(result, 'deviceToken', fatal=True)
        self._downloader.cache.store(
            'cbcwatch', self._cache_device_key(), {
                'id': self._device_id,
                'token': self._device_token,
            })

    def _parse_rss_feed(self, rss):
        channel = xpath_element(rss, 'channel', fatal=True)

        def _add_ns(path):
            return xpath_with_ns(path, self._NS_MAP)

        entries = []
        for item in channel.findall('item'):
            guid = xpath_text(item, 'guid', fatal=True)
            title = xpath_text(item, 'title', fatal=True)

            media_group = xpath_element(item, _add_ns('media:group'), fatal=True)
            content = xpath_element(media_group, _add_ns('media:content'), fatal=True)
            content_url = content.attrib['url']

            thumbnails = []
            for thumbnail in media_group.findall(_add_ns('media:thumbnail')):
                thumbnail_url = thumbnail.get('url')
                if not thumbnail_url:
                    continue
                thumbnails.append({
                    'id': thumbnail.get('profile'),
                    'url': thumbnail_url,
                    'width': int_or_none(thumbnail.get('width')),
                    'height': int_or_none(thumbnail.get('height')),
                })

            timestamp = None
            release_date = find_xpath_attr(
                item, _add_ns('media:credit'), 'role', 'releaseDate')
            if release_date is not None:
                timestamp = parse_iso8601(release_date.text)

            entries.append({
                '_type': 'url_transparent',
                'url': content_url,
                'id': guid,
                'title': title,
                'description': xpath_text(item, 'description'),
                'timestamp': timestamp,
                'duration': int_or_none(content.get('duration')),
                'age_limit': parse_age_limit(xpath_text(item, _add_ns('media:rating'))),
                'episode': xpath_text(item, _add_ns('clearleap:episode')),
                'episode_number': int_or_none(xpath_text(item, _add_ns('clearleap:episodeInSeason'))),
                'series': xpath_text(item, _add_ns('clearleap:series')),
                'season_number': int_or_none(xpath_text(item, _add_ns('clearleap:season'))),
                'thumbnails': thumbnails,
                'ie_key': 'CBCWatchVideo',
            })

        return self.playlist_result(
            entries, xpath_text(channel, 'guid'),
            xpath_text(channel, 'title'),
            xpath_text(channel, 'description'))


class CBCWatchVideoIE(CBCWatchBaseIE):
    IE_NAME = 'cbc.ca:watch:video'
    _VALID_URL = r'https?://api-cbc\.cloud\.clearleap\.com/cloffice/client/web/play/?\?.*?\bcontentId=(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'
    _TEST = {
        # geo-restricted to Canada, bypassable
        'url': 'https://api-cbc.cloud.clearleap.com/cloffice/client/web/play/?contentId=3c84472a-1eea-4dee-9267-2655d5055dcf&categoryId=ebc258f5-ee40-4cca-b66b-ba6bd55b7235',
        'only_matching': True,
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        result = self._call_api(url, video_id)

        m3u8_url = xpath_text(result, 'url', fatal=True)
        formats = self._extract_m3u8_formats(re.sub(r'/([^/]+)/[^/?]+\.m3u8', r'/\1/\1.m3u8', m3u8_url), video_id, 'mp4', fatal=False)
        if len(formats) < 2:
            formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')
        for f in formats:
            format_id = f.get('format_id')
            if format_id.startswith('AAC'):
                f['acodec'] = 'aac'
            elif format_id.startswith('AC3'):
                f['acodec'] = 'ac-3'
        self._sort_formats(formats)

        info = {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }

        rss = xpath_element(result, 'rss')
        if rss:
            info.update(self._parse_rss_feed(rss)['entries'][0])
            del info['url']
            del info['_type']
            del info['ie_key']
        return info


class CBCWatchIE(CBCWatchBaseIE):
    IE_NAME = 'cbc.ca:watch'
    _VALID_URL = r'https?://(?:gem|watch)\.cbc\.ca/(?:[^/]+/)+(?P<id>[0-9a-f-]+)'
    _TESTS = [{
        # geo-restricted to Canada, bypassable
        'url': 'http://watch.cbc.ca/doc-zone/season-6/customer-disservice/38e815a-009e3ab12e4',
        'info_dict': {
            'id': '9673749a-5e77-484c-8b62-a1092a6b5168',
            'ext': 'mp4',
            'title': 'Customer (Dis)Service',
            'description': 'md5:8bdd6913a0fe03d4b2a17ebe169c7c87',
            'upload_date': '20160219',
            'timestamp': 1455840000,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
            'format': 'bestvideo',
        },
    }, {
        # geo-restricted to Canada, bypassable
        'url': 'http://watch.cbc.ca/arthur/all/1ed4b385-cd84-49cf-95f0-80f004680057',
        'info_dict': {
            'id': '1ed4b385-cd84-49cf-95f0-80f004680057',
            'title': 'Arthur',
            'description': 'Arthur, the sweetest 8-year-old aardvark, and his pals solve all kinds of problems with humour, kindness and teamwork.',
        },
        'playlist_mincount': 30,
    }, {
        'url': 'https://gem.cbc.ca/media/this-hour-has-22-minutes/season-26/episode-20/38e815a-0108c6c6a42',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        rss = self._call_api('web/browse/' + video_id, video_id)
        return self._parse_rss_feed(rss)


class CBCOlympicsIE(InfoExtractor):
    IE_NAME = 'cbc.ca:olympics'
    _VALID_URL = r'https?://olympics\.cbc\.ca/video/[^/]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://olympics.cbc.ca/video/whats-on-tv/olympic-morning-featuring-the-opening-ceremony/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._hidden_inputs(webpage)['videoId']
        video_doc = self._download_xml(
            'https://olympics.cbc.ca/videodata/%s.xml' % video_id, video_id)
        title = xpath_text(video_doc, 'title', fatal=True)
        is_live = xpath_text(video_doc, 'kind') == 'Live'
        if is_live:
            title = self._live_title(title)

        formats = []
        for video_source in video_doc.findall('videoSources/videoSource'):
            uri = xpath_text(video_source, 'uri')
            if not uri:
                continue
            tokenize = self._download_json(
                'https://olympics.cbc.ca/api/api-akamai/tokenize',
                video_id, data=json.dumps({
                    'VideoSource': uri,
                }).encode(), headers={
                    'Content-Type': 'application/json',
                    'Referer': url,
                    # d3.VideoPlayer._init in https://olympics.cbc.ca/components/script/base.js
                    'Cookie': '_dvp=TK:C0ObxjerU',  # AKAMAI CDN cookie
                }, fatal=False)
            if not tokenize:
                continue
            content_url = tokenize['ContentUrl']
            video_source_format = video_source.get('format')
            if video_source_format == 'IIS':
                formats.extend(self._extract_ism_formats(
                    content_url, video_id, ism_id=video_source_format, fatal=False))
            else:
                formats.extend(self._extract_m3u8_formats(
                    content_url, video_id, 'mp4',
                    'm3u8' if is_live else 'm3u8_native',
                    m3u8_id=video_source_format, fatal=False))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': xpath_text(video_doc, 'description'),
            'thumbnail': xpath_text(video_doc, 'thumbnailUrl'),
            'duration': parse_duration(xpath_text(video_doc, 'duration')),
            'formats': formats,
            'is_live': is_live,
        }
