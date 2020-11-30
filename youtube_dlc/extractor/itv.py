# coding: utf-8
from __future__ import unicode_literals

import uuid
import xml.etree.ElementTree as etree
import json
import re

from .common import InfoExtractor
from .brightcove import BrightcoveNewIE
from ..compat import (
    compat_str,
    compat_etree_register_namespace,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    extract_attributes,
    int_or_none,
    merge_dicts,
    parse_duration,
    smuggle_url,
    try_get,
    url_or_none,
    xpath_with_ns,
    xpath_element,
    xpath_text,
)


class ITVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?itv\.com/hub/[^/]+/(?P<id>[0-9a-zA-Z]+)'
    _GEO_COUNTRIES = ['GB']
    _TESTS = [{
        'url': 'http://www.itv.com/hub/mr-bean-animated-series/2a2936a0053',
        'info_dict': {
            'id': '2a2936a0053',
            'ext': 'flv',
            'title': 'Home Movie',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
    }, {
        # unavailable via data-playlist-url
        'url': 'https://www.itv.com/hub/through-the-keyhole/2a2271a0033',
        'only_matching': True,
    }, {
        # InvalidVodcrid
        'url': 'https://www.itv.com/hub/james-martins-saturday-morning/2a5159a0034',
        'only_matching': True,
    }, {
        # ContentUnavailable
        'url': 'https://www.itv.com/hub/whos-doing-the-dishes/2a2898a0024',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        params = extract_attributes(self._search_regex(
            r'(?s)(<[^>]+id="video"[^>]*>)', webpage, 'params'))

        ns_map = {
            'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
            'tem': 'http://tempuri.org/',
            'itv': 'http://schemas.datacontract.org/2004/07/Itv.BB.Mercury.Common.Types',
            'com': 'http://schemas.itv.com/2009/05/Common',
        }
        for ns, full_ns in ns_map.items():
            compat_etree_register_namespace(ns, full_ns)

        def _add_ns(name):
            return xpath_with_ns(name, ns_map)

        def _add_sub_element(element, name):
            return etree.SubElement(element, _add_ns(name))

        production_id = (
            params.get('data-video-autoplay-id')
            or '%s#001' % (
                params.get('data-video-episode-id')
                or video_id.replace('a', '/')))

        req_env = etree.Element(_add_ns('soapenv:Envelope'))
        _add_sub_element(req_env, 'soapenv:Header')
        body = _add_sub_element(req_env, 'soapenv:Body')
        get_playlist = _add_sub_element(body, ('tem:GetPlaylist'))
        request = _add_sub_element(get_playlist, 'tem:request')
        _add_sub_element(request, 'itv:ProductionId').text = production_id
        _add_sub_element(request, 'itv:RequestGuid').text = compat_str(uuid.uuid4()).upper()
        vodcrid = _add_sub_element(request, 'itv:Vodcrid')
        _add_sub_element(vodcrid, 'com:Id')
        _add_sub_element(request, 'itv:Partition')
        user_info = _add_sub_element(get_playlist, 'tem:userInfo')
        _add_sub_element(user_info, 'itv:Broadcaster').text = 'Itv'
        _add_sub_element(user_info, 'itv:DM')
        _add_sub_element(user_info, 'itv:RevenueScienceValue')
        _add_sub_element(user_info, 'itv:SessionId')
        _add_sub_element(user_info, 'itv:SsoToken')
        _add_sub_element(user_info, 'itv:UserToken')
        site_info = _add_sub_element(get_playlist, 'tem:siteInfo')
        _add_sub_element(site_info, 'itv:AdvertisingRestriction').text = 'None'
        _add_sub_element(site_info, 'itv:AdvertisingSite').text = 'ITV'
        _add_sub_element(site_info, 'itv:AdvertisingType').text = 'Any'
        _add_sub_element(site_info, 'itv:Area').text = 'ITVPLAYER.VIDEO'
        _add_sub_element(site_info, 'itv:Category')
        _add_sub_element(site_info, 'itv:Platform').text = 'DotCom'
        _add_sub_element(site_info, 'itv:Site').text = 'ItvCom'
        device_info = _add_sub_element(get_playlist, 'tem:deviceInfo')
        _add_sub_element(device_info, 'itv:ScreenSize').text = 'Big'
        player_info = _add_sub_element(get_playlist, 'tem:playerInfo')
        _add_sub_element(player_info, 'itv:Version').text = '2'

        headers = self.geo_verification_headers()
        headers.update({
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://tempuri.org/PlaylistService/GetPlaylist',
        })

        info = self._search_json_ld(webpage, video_id, default={})
        formats = []
        subtitles = {}

        def extract_subtitle(sub_url):
            ext = determine_ext(sub_url, 'ttml')
            subtitles.setdefault('en', []).append({
                'url': sub_url,
                'ext': 'ttml' if ext == 'xml' else ext,
            })

        resp_env = self._download_xml(
            params['data-playlist-url'], video_id,
            headers=headers, data=etree.tostring(req_env), fatal=False)
        if resp_env:
            playlist = xpath_element(resp_env, './/Playlist')
            if playlist is None:
                fault_code = xpath_text(resp_env, './/faultcode')
                fault_string = xpath_text(resp_env, './/faultstring')
                if fault_code == 'InvalidGeoRegion':
                    self.raise_geo_restricted(
                        msg=fault_string, countries=self._GEO_COUNTRIES)
                elif fault_code not in (
                        'InvalidEntity', 'InvalidVodcrid', 'ContentUnavailable'):
                    raise ExtractorError(
                        '%s said: %s' % (self.IE_NAME, fault_string), expected=True)
                info.update({
                    'title': self._og_search_title(webpage),
                    'episode_title': params.get('data-video-episode'),
                    'series': params.get('data-video-title'),
                })
            else:
                title = xpath_text(playlist, 'EpisodeTitle', default=None)
                info.update({
                    'title': title,
                    'episode_title': title,
                    'episode_number': int_or_none(xpath_text(playlist, 'EpisodeNumber')),
                    'series': xpath_text(playlist, 'ProgrammeTitle'),
                    'duration': parse_duration(xpath_text(playlist, 'Duration')),
                })
                video_element = xpath_element(playlist, 'VideoEntries/Video', fatal=True)
                media_files = xpath_element(video_element, 'MediaFiles', fatal=True)
                rtmp_url = media_files.attrib['base']

                for media_file in media_files.findall('MediaFile'):
                    play_path = xpath_text(media_file, 'URL')
                    if not play_path:
                        continue
                    tbr = int_or_none(media_file.get('bitrate'), 1000)
                    f = {
                        'format_id': 'rtmp' + ('-%d' % tbr if tbr else ''),
                        'play_path': play_path,
                        # Providing this swfVfy allows to avoid truncated downloads
                        'player_url': 'http://www.itv.com/mercury/Mercury_VideoPlayer.swf',
                        'page_url': url,
                        'tbr': tbr,
                        'ext': 'flv',
                    }
                    app = self._search_regex(
                        'rtmpe?://[^/]+/(.+)$', rtmp_url, 'app', default=None)
                    if app:
                        f.update({
                            'url': rtmp_url.split('?', 1)[0],
                            'app': app,
                        })
                    else:
                        f['url'] = rtmp_url
                    formats.append(f)

                for caption_url in video_element.findall('ClosedCaptioningURIs/URL'):
                    if caption_url.text:
                        extract_subtitle(caption_url.text)

        ios_playlist_url = params.get('data-video-playlist') or params.get('data-video-id')
        hmac = params.get('data-video-hmac')
        if ios_playlist_url and hmac and re.match(r'https?://', ios_playlist_url):
            headers = self.geo_verification_headers()
            headers.update({
                'Accept': 'application/vnd.itv.vod.playlist.v2+json',
                'Content-Type': 'application/json',
                'hmac': hmac.upper(),
            })
            ios_playlist = self._download_json(
                ios_playlist_url, video_id, data=json.dumps({
                    'user': {
                        'itvUserId': '',
                        'entitlements': [],
                        'token': ''
                    },
                    'device': {
                        'manufacturer': 'Safari',
                        'model': '5',
                        'os': {
                            'name': 'Windows NT',
                            'version': '6.1',
                            'type': 'desktop'
                        }
                    },
                    'client': {
                        'version': '4.1',
                        'id': 'browser'
                    },
                    'variantAvailability': {
                        'featureset': {
                            'min': ['hls', 'aes', 'outband-webvtt'],
                            'max': ['hls', 'aes', 'outband-webvtt']
                        },
                        'platformTag': 'dotcom'
                    }
                }).encode(), headers=headers, fatal=False)
            if ios_playlist:
                video_data = ios_playlist.get('Playlist', {}).get('Video', {})
                ios_base_url = video_data.get('Base')
                for media_file in video_data.get('MediaFiles', []):
                    href = media_file.get('Href')
                    if not href:
                        continue
                    if ios_base_url:
                        href = ios_base_url + href
                    ext = determine_ext(href)
                    if ext == 'm3u8':
                        formats.extend(self._extract_m3u8_formats(
                            href, video_id, 'mp4', entry_protocol='m3u8_native',
                            m3u8_id='hls', fatal=False))
                    else:
                        formats.append({
                            'url': href,
                        })
                subs = video_data.get('Subtitles')
                if isinstance(subs, list):
                    for sub in subs:
                        if not isinstance(sub, dict):
                            continue
                        href = url_or_none(sub.get('Href'))
                        if href:
                            extract_subtitle(href)
                if not info.get('duration'):
                    info['duration'] = parse_duration(video_data.get('Duration'))

        self._sort_formats(formats)

        info.update({
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
        })

        webpage_info = self._search_json_ld(webpage, video_id, default={})
        if not webpage_info.get('title'):
            webpage_info['title'] = self._html_search_regex(
                r'(?s)<h\d+[^>]+\bclass=["\'][^>]*episode-title["\'][^>]*>([^<]+)<',
                webpage, 'title', default=None) or self._og_search_title(
                webpage, default=None) or self._html_search_meta(
                'twitter:title', webpage, 'title',
                default=None) or webpage_info['episode']

        return merge_dicts(info, webpage_info)


class ITVBTCCIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?itv\.com/btcc/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.itv.com/btcc/articles/btcc-2019-brands-hatch-gp-race-action',
        'info_dict': {
            'id': 'btcc-2019-brands-hatch-gp-race-action',
            'title': 'BTCC 2019: Brands Hatch GP race action',
        },
        'playlist_count': 12,
    }
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/1582188683001/HkiHLnNRx_default/index.html?videoId=%s'

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        json_map = try_get(self._parse_json(self._html_search_regex(
            '(?s)<script[^>]+id=[\'"]__NEXT_DATA__[^>]*>([^<]+)</script>', webpage, 'json_map'), playlist_id),
            lambda x: x['props']['pageProps']['article']['body']['content']) or []

        # Discard empty objects
        video_ids = []
        for video in json_map:
            if video['data'].get('id'):
                video_ids.append(video['data']['id'])

        entries = [
            self.url_result(
                smuggle_url(self.BRIGHTCOVE_URL_TEMPLATE % video_id, {
                    # ITV does not like some GB IP ranges, so here are some
                    # IP blocks it accepts
                    'geo_ip_blocks': [
                        '193.113.0.0/16', '54.36.162.0/23', '159.65.16.0/21'
                    ],
                    'referrer': url,
                }),
                ie=BrightcoveNewIE.ie_key(), video_id=video_id)
            for video_id in video_ids]

        title = self._og_search_title(webpage, fatal=False)

        return self.playlist_result(entries, playlist_id, title)
