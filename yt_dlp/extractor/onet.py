# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    float_or_none,
    get_element_by_class,
    int_or_none,
    js_to_json,
    NO_DEFAULT,
    parse_iso8601,
    remove_start,
    strip_or_none,
    url_basename,
)


class OnetBaseIE(InfoExtractor):
    _URL_BASE_RE = r'https?://(?:(?:www\.)?onet\.tv|onet100\.vod\.pl)/[a-z]/'

    def _search_mvp_id(self, webpage):
        return self._search_regex(
            r'id=(["\'])mvp:(?P<id>.+?)\1', webpage, 'mvp id', group='id')

    def _extract_from_id(self, video_id, webpage=None):
        response = self._download_json(
            'http://qi.ckm.onetapi.pl/', video_id,
            query={
                'body[id]': video_id,
                'body[jsonrpc]': '2.0',
                'body[method]': 'get_asset_detail',
                'body[params][ID_Publikacji]': video_id,
                'body[params][Service]': 'www.onet.pl',
                'content-type': 'application/jsonp',
                'x-onet-app': 'player.front.onetapi.pl',
            })

        error = response.get('error')
        if error:
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, error['message']), expected=True)

        video = response['result'].get('0')

        formats = []
        for format_type, formats_dict in video['formats'].items():
            if not isinstance(formats_dict, dict):
                continue
            for format_id, format_list in formats_dict.items():
                if not isinstance(format_list, list):
                    continue
                for f in format_list:
                    video_url = f.get('url')
                    if not video_url:
                        continue
                    ext = determine_ext(video_url)
                    if format_id.startswith('ism'):
                        formats.extend(self._extract_ism_formats(
                            video_url, video_id, 'mss', fatal=False))
                    elif ext == 'mpd':
                        formats.extend(self._extract_mpd_formats(
                            video_url, video_id, mpd_id='dash', fatal=False))
                    elif format_id.startswith('hls'):
                        formats.extend(self._extract_m3u8_formats(
                            video_url, video_id, 'mp4', 'm3u8_native',
                            m3u8_id='hls', fatal=False))
                    else:
                        http_f = {
                            'url': video_url,
                            'format_id': format_id,
                            'abr': float_or_none(f.get('audio_bitrate')),
                        }
                        if format_type == 'audio':
                            http_f['vcodec'] = 'none'
                        else:
                            http_f.update({
                                'height': int_or_none(f.get('vertical_resolution')),
                                'width': int_or_none(f.get('horizontal_resolution')),
                                'vbr': float_or_none(f.get('video_bitrate')),
                            })
                        formats.append(http_f)
        self._sort_formats(formats)

        meta = video.get('meta', {})

        title = (self._og_search_title(
            webpage, default=None) if webpage else None) or meta['title']
        description = (self._og_search_description(
            webpage, default=None) if webpage else None) or meta.get('description')
        duration = meta.get('length') or meta.get('lenght')
        timestamp = parse_iso8601(meta.get('addDate'), ' ')

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'duration': duration,
            'timestamp': timestamp,
            'formats': formats,
        }


class OnetMVPIE(OnetBaseIE):
    _VALID_URL = r'onetmvp:(?P<id>\d+\.\d+)'

    _TEST = {
        'url': 'onetmvp:381027.1509591944',
        'only_matching': True,
    }

    def _real_extract(self, url):
        return self._extract_from_id(self._match_id(url))


class OnetIE(OnetBaseIE):
    _VALID_URL = OnetBaseIE._URL_BASE_RE + r'[a-z]+/(?P<display_id>[0-9a-z-]+)/(?P<id>[0-9a-z]+)'
    IE_NAME = 'onet.tv'

    _TESTS = [{
        'url': 'http://onet.tv/k/openerfestival/open-er-festival-2016-najdziwniejsze-wymagania-gwiazd/qbpyqc',
        'md5': '436102770fb095c75b8bb0392d3da9ff',
        'info_dict': {
            'id': 'qbpyqc',
            'display_id': 'open-er-festival-2016-najdziwniejsze-wymagania-gwiazd',
            'ext': 'mp4',
            'title': 'Open\'er Festival 2016: najdziwniejsze wymagania gwiazd',
            'description': 'Trzy samochody, których nigdy nie użyto, prywatne spa, hotel dekorowany czarnym suknem czy nielegalne używki. Organizatorzy koncertów i festiwali muszą stawać przed nie lada wyzwaniem zapraszając gwia...',
            'upload_date': '20160705',
            'timestamp': 1467721580,
        },
    }, {
        'url': 'https://onet100.vod.pl/k/openerfestival/open-er-festival-2016-najdziwniejsze-wymagania-gwiazd/qbpyqc',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id, video_id = mobj.group('display_id', 'id')

        webpage = self._download_webpage(url, display_id)

        mvp_id = self._search_mvp_id(webpage)

        info_dict = self._extract_from_id(mvp_id, webpage)
        info_dict.update({
            'id': video_id,
            'display_id': display_id,
        })

        return info_dict


class OnetChannelIE(OnetBaseIE):
    _VALID_URL = OnetBaseIE._URL_BASE_RE + r'(?P<id>[a-z]+)(?:[?#]|$)'
    IE_NAME = 'onet.tv:channel'

    _TESTS = [{
        'url': 'http://onet.tv/k/openerfestival',
        'info_dict': {
            'id': 'openerfestival',
            'title': "Open'er Festival",
            'description': "Tak było na Open'er Festival 2016! Oglądaj nasze reportaże i wywiady z artystami.",
        },
        'playlist_mincount': 35,
    }, {
        'url': 'https://onet100.vod.pl/k/openerfestival',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        webpage = self._download_webpage(url, channel_id)

        current_clip_info = self._parse_json(self._search_regex(
            r'var\s+currentClip\s*=\s*({[^}]+})', webpage, 'video info'), channel_id,
            transform_source=lambda s: js_to_json(re.sub(r'\'\s*\+\s*\'', '', s)))
        video_id = remove_start(current_clip_info['ckmId'], 'mvp:')
        video_name = url_basename(current_clip_info['url'])

        if self._downloader.params.get('noplaylist'):
            self.to_screen(
                'Downloading just video %s because of --no-playlist' % video_name)
            return self._extract_from_id(video_id, webpage)

        self.to_screen(
            'Downloading channel %s - add --no-playlist to just download video %s' % (
                channel_id, video_name))
        matches = re.findall(
            r'<a[^>]+href=[\'"](%s[a-z]+/[0-9a-z-]+/[0-9a-z]+)' % self._URL_BASE_RE,
            webpage)
        entries = [
            self.url_result(video_link, OnetIE.ie_key())
            for video_link in matches]

        channel_title = strip_or_none(get_element_by_class('o_channelName', webpage))
        channel_description = strip_or_none(get_element_by_class('o_channelDesc', webpage))
        return self.playlist_result(entries, channel_id, channel_title, channel_description)


class OnetPlIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?(?:onet|businessinsider\.com|plejada)\.pl/(?:[^/]+/)+(?P<id>[0-9a-z]+)'
    IE_NAME = 'onet.pl'

    _TESTS = [{
        'url': 'http://eurosport.onet.pl/zimowe/skoki-narciarskie/ziobro-wygral-kwalifikacje-w-pjongczangu/9ckrly',
        'md5': 'b94021eb56214c3969380388b6e73cb0',
        'info_dict': {
            'id': '1561707.1685479',
            'ext': 'mp4',
            'title': 'Ziobro wygrał kwalifikacje w Pjongczangu',
            'description': 'md5:61fb0740084d2d702ea96512a03585b4',
            'upload_date': '20170214',
            'timestamp': 1487078046,
        },
    }, {
        # embedded via pulsembed
        'url': 'http://film.onet.pl/pensjonat-nad-rozlewiskiem-relacja-z-planu-serialu/y428n0',
        'info_dict': {
            'id': '501235.965429946',
            'ext': 'mp4',
            'title': '"Pensjonat nad rozlewiskiem": relacja z planu serialu',
            'upload_date': '20170622',
            'timestamp': 1498159955,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://film.onet.pl/zwiastuny/ghost-in-the-shell-drugi-zwiastun-pl/5q6yl3',
        'only_matching': True,
    }, {
        'url': 'http://moto.onet.pl/jak-wybierane-sa-miejsca-na-fotoradary/6rs04e',
        'only_matching': True,
    }, {
        'url': 'http://businessinsider.com.pl/wideo/scenariusz-na-koniec-swiata-wedlug-nasa/dwnqptk',
        'only_matching': True,
    }, {
        'url': 'http://plejada.pl/weronika-rosati-o-swoim-domniemanym-slubie/n2bq89',
        'only_matching': True,
    }]

    def _search_mvp_id(self, webpage, default=NO_DEFAULT):
        return self._search_regex(
            r'data-(?:params-)?mvp=["\'](\d+\.\d+)', webpage, 'mvp id',
            default=default)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        mvp_id = self._search_mvp_id(webpage, default=None)

        if not mvp_id:
            pulsembed_url = self._search_regex(
                r'data-src=(["\'])(?P<url>(?:https?:)?//pulsembed\.eu/.+?)\1',
                webpage, 'pulsembed url', group='url')
            webpage = self._download_webpage(
                pulsembed_url, video_id, 'Downloading pulsembed webpage')
            mvp_id = self._search_mvp_id(webpage)

        return self.url_result(
            'onetmvp:%s' % mvp_id, OnetMVPIE.ie_key(), video_id=mvp_id)
