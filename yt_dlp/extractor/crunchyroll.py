# coding: utf-8
from __future__ import unicode_literals

import base64
import re
import json
import zlib

from hashlib import sha1
from math import pow, sqrt, floor
from .common import InfoExtractor
from .vrv import VRVIE
from ..compat import (
    compat_b64decode,
    compat_etree_Element,
    compat_etree_fromstring,
    compat_str,
    compat_urllib_parse_urlencode,
    compat_urllib_request,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    bytes_to_intlist,
    extract_attributes,
    float_or_none,
    format_field,
    intlist_to_bytes,
    int_or_none,
    join_nonempty,
    lowercase_escape,
    merge_dicts,
    qualities,
    remove_end,
    sanitized_Request,
    traverse_obj,
    try_get,
    xpath_text,
)
from ..aes import (
    aes_cbc_decrypt,
)


class CrunchyrollBaseIE(InfoExtractor):
    _LOGIN_URL = 'https://www.crunchyroll.com/welcome/login'
    _API_BASE = 'https://api.crunchyroll.com'
    _NETRC_MACHINE = 'crunchyroll'

    def _call_rpc_api(self, method, video_id, note=None, data=None):
        data = data or {}
        data['req'] = 'RpcApi' + method
        data = compat_urllib_parse_urlencode(data).encode('utf-8')
        return self._download_xml(
            'https://www.crunchyroll.com/xml/',
            video_id, note, fatal=False, data=data, headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            })

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return
        if self._get_cookies(self._LOGIN_URL).get('etp_rt'):
            return

        upsell_response = self._download_json(
            f'{self._API_BASE}/get_upsell_data.0.json', None, 'Getting session id',
            query={
                'sess_id': 1,
                'device_id': 'whatvalueshouldbeforweb',
                'device_type': 'com.crunchyroll.static',
                'access_token': 'giKq5eY27ny3cqz',
                'referer': self._LOGIN_URL
            })
        if upsell_response['code'] != 'ok':
            raise ExtractorError('Could not get session id')
        session_id = upsell_response['data']['session_id']

        login_response = self._download_json(
            f'{self._API_BASE}/login.1.json', None, 'Logging in',
            data=compat_urllib_parse_urlencode({
                'account': username,
                'password': password,
                'session_id': session_id
            }).encode('ascii'))
        if login_response['code'] != 'ok':
            raise ExtractorError('Login failed. Bad username or password?', expected=True)
        if not self._get_cookies(self._LOGIN_URL).get('etp_rt'):
            raise ExtractorError('Login succeeded but did not set etp_rt cookie')

    def _real_initialize(self):
        self._login()

    @staticmethod
    def _add_skip_wall(url):
        parsed_url = compat_urlparse.urlparse(url)
        qs = compat_urlparse.parse_qs(parsed_url.query)
        # Always force skip_wall to bypass maturity wall, namely 18+ confirmation message:
        # > This content may be inappropriate for some people.
        # > Are you sure you want to continue?
        # since it's not disabled by default in crunchyroll account's settings.
        # See https://github.com/ytdl-org/youtube-dl/issues/7202.
        qs['skip_wall'] = ['1']
        return compat_urlparse.urlunparse(
            parsed_url._replace(query=compat_urllib_parse_urlencode(qs, True)))


class CrunchyrollIE(CrunchyrollBaseIE, VRVIE):
    IE_NAME = 'crunchyroll'
    _VALID_URL = r'https?://(?:(?P<prefix>www|m)\.)?(?P<url>crunchyroll\.(?:com|fr)/(?:media(?:-|/\?id=)|(?:[^/]*/){1,2}[^/?&]*?)(?P<id>[0-9]+))(?:[/?&]|$)'
    _TESTS = [{
        'url': 'http://www.crunchyroll.com/wanna-be-the-strongest-in-the-world/episode-1-an-idol-wrestler-is-born-645513',
        'info_dict': {
            'id': '645513',
            'ext': 'mp4',
            'title': 'Wanna be the Strongest in the World Episode 1 – An Idol-Wrestler is Born!',
            'description': 'md5:2d17137920c64f2f49981a7797d275ef',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Yomiuri Telecasting Corporation (YTV)',
            'upload_date': '20131013',
            'url': 're:(?!.*&amp)',
        },
        'params': {
            # rtmp
            'skip_download': True,
        },
        'skip': 'Video gone',
    }, {
        'url': 'http://www.crunchyroll.com/media-589804/culture-japan-1',
        'info_dict': {
            'id': '589804',
            'ext': 'flv',
            'title': 'Culture Japan Episode 1 – Rebuilding Japan after the 3.11',
            'description': 'md5:2fbc01f90b87e8e9137296f37b461c12',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Danny Choo Network',
            'upload_date': '20120213',
        },
        'params': {
            # rtmp
            'skip_download': True,
        },
        'skip': 'Video gone',
    }, {
        'url': 'http://www.crunchyroll.com/rezero-starting-life-in-another-world-/episode-5-the-morning-of-our-promise-is-still-distant-702409',
        'info_dict': {
            'id': '702409',
            'ext': 'mp4',
            'title': compat_str,
            'description': compat_str,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Re:Zero Partners',
            'timestamp': 1462098900,
            'upload_date': '20160501',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.crunchyroll.com/konosuba-gods-blessing-on-this-wonderful-world/episode-1-give-me-deliverance-from-this-judicial-injustice-727589',
        'info_dict': {
            'id': '727589',
            'ext': 'mp4',
            'title': compat_str,
            'description': compat_str,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Kadokawa Pictures Inc.',
            'timestamp': 1484130900,
            'upload_date': '20170111',
            'series': compat_str,
            'season': "KONOSUBA -God's blessing on this wonderful world! 2",
            'season_number': 2,
            'episode': 'Give Me Deliverance From This Judicial Injustice!',
            'episode_number': 1,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.crunchyroll.fr/girl-friend-beta/episode-11-goodbye-la-mode-661697',
        'only_matching': True,
    }, {
        # geo-restricted (US), 18+ maturity wall, non-premium available
        'url': 'http://www.crunchyroll.com/cosplay-complex-ova/episode-1-the-birth-of-the-cosplay-club-565617',
        'only_matching': True,
    }, {
        # A description with double quotes
        'url': 'http://www.crunchyroll.com/11eyes/episode-1-piros-jszaka-red-night-535080',
        'info_dict': {
            'id': '535080',
            'ext': 'mp4',
            'title': compat_str,
            'description': compat_str,
            'uploader': 'Marvelous AQL Inc.',
            'timestamp': 1255512600,
            'upload_date': '20091014',
        },
        'params': {
            # Just test metadata extraction
            'skip_download': True,
        },
    }, {
        # make sure we can extract an uploader name that's not a link
        'url': 'http://www.crunchyroll.com/hakuoki-reimeiroku/episode-1-dawn-of-the-divine-warriors-606899',
        'info_dict': {
            'id': '606899',
            'ext': 'mp4',
            'title': 'Hakuoki Reimeiroku Episode 1 – Dawn of the Divine Warriors',
            'description': 'Ryunosuke was left to die, but Serizawa-san asked him a simple question "Do you want to live?"',
            'uploader': 'Geneon Entertainment',
            'upload_date': '20120717',
        },
        'params': {
            # just test metadata extraction
            'skip_download': True,
        },
        'skip': 'Video gone',
    }, {
        # A video with a vastly different season name compared to the series name
        'url': 'http://www.crunchyroll.com/nyarko-san-another-crawling-chaos/episode-1-test-590532',
        'info_dict': {
            'id': '590532',
            'ext': 'mp4',
            'title': compat_str,
            'description': compat_str,
            'uploader': 'TV TOKYO',
            'timestamp': 1330956000,
            'upload_date': '20120305',
            'series': 'Nyarko-san: Another Crawling Chaos',
            'season': 'Haiyoru! Nyaruani (ONA)',
        },
        'params': {
            # Just test metadata extraction
            'skip_download': True,
        },
    }, {
        'url': 'http://www.crunchyroll.com/media-723735',
        'only_matching': True,
    }, {
        'url': 'https://www.crunchyroll.com/en-gb/mob-psycho-100/episode-2-urban-legends-encountering-rumors-780921',
        'only_matching': True,
    }]

    _FORMAT_IDS = {
        '360': ('60', '106'),
        '480': ('61', '106'),
        '720': ('62', '106'),
        '1080': ('80', '108'),
    }

    def _download_webpage(self, url_or_request, *args, **kwargs):
        request = (url_or_request if isinstance(url_or_request, compat_urllib_request.Request)
                   else sanitized_Request(url_or_request))
        # Accept-Language must be set explicitly to accept any language to avoid issues
        # similar to https://github.com/ytdl-org/youtube-dl/issues/6797.
        # Along with IP address Crunchyroll uses Accept-Language to guess whether georestriction
        # should be imposed or not (from what I can see it just takes the first language
        # ignoring the priority and requires it to correspond the IP). By the way this causes
        # Crunchyroll to not work in georestriction cases in some browsers that don't place
        # the locale lang first in header. However allowing any language seems to workaround the issue.
        request.add_header('Accept-Language', '*')
        return super(CrunchyrollBaseIE, self)._download_webpage(request, *args, **kwargs)

    def _decrypt_subtitles(self, data, iv, id):
        data = bytes_to_intlist(compat_b64decode(data))
        iv = bytes_to_intlist(compat_b64decode(iv))
        id = int(id)

        def obfuscate_key_aux(count, modulo, start):
            output = list(start)
            for _ in range(count):
                output.append(output[-1] + output[-2])
            # cut off start values
            output = output[2:]
            output = list(map(lambda x: x % modulo + 33, output))
            return output

        def obfuscate_key(key):
            num1 = int(floor(pow(2, 25) * sqrt(6.9)))
            num2 = (num1 ^ key) << 5
            num3 = key ^ num1
            num4 = num3 ^ (num3 >> 3) ^ num2
            prefix = intlist_to_bytes(obfuscate_key_aux(20, 97, (1, 2)))
            shaHash = bytes_to_intlist(sha1(prefix + str(num4).encode('ascii')).digest())
            # Extend 160 Bit hash to 256 Bit
            return shaHash + [0] * 12

        key = obfuscate_key(id)

        decrypted_data = intlist_to_bytes(aes_cbc_decrypt(data, key, iv))
        return zlib.decompress(decrypted_data)

    def _convert_subtitles_to_srt(self, sub_root):
        output = ''

        for i, event in enumerate(sub_root.findall('./events/event'), 1):
            start = event.attrib['start'].replace('.', ',')
            end = event.attrib['end'].replace('.', ',')
            text = event.attrib['text'].replace('\\N', '\n')
            output += '%d\n%s --> %s\n%s\n\n' % (i, start, end, text)
        return output

    def _convert_subtitles_to_ass(self, sub_root):
        output = ''

        def ass_bool(strvalue):
            assvalue = '0'
            if strvalue == '1':
                assvalue = '-1'
            return assvalue

        output = '[Script Info]\n'
        output += 'Title: %s\n' % sub_root.attrib['title']
        output += 'ScriptType: v4.00+\n'
        output += 'WrapStyle: %s\n' % sub_root.attrib['wrap_style']
        output += 'PlayResX: %s\n' % sub_root.attrib['play_res_x']
        output += 'PlayResY: %s\n' % sub_root.attrib['play_res_y']
        output += """
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
        for style in sub_root.findall('./styles/style'):
            output += 'Style: ' + style.attrib['name']
            output += ',' + style.attrib['font_name']
            output += ',' + style.attrib['font_size']
            output += ',' + style.attrib['primary_colour']
            output += ',' + style.attrib['secondary_colour']
            output += ',' + style.attrib['outline_colour']
            output += ',' + style.attrib['back_colour']
            output += ',' + ass_bool(style.attrib['bold'])
            output += ',' + ass_bool(style.attrib['italic'])
            output += ',' + ass_bool(style.attrib['underline'])
            output += ',' + ass_bool(style.attrib['strikeout'])
            output += ',' + style.attrib['scale_x']
            output += ',' + style.attrib['scale_y']
            output += ',' + style.attrib['spacing']
            output += ',' + style.attrib['angle']
            output += ',' + style.attrib['border_style']
            output += ',' + style.attrib['outline']
            output += ',' + style.attrib['shadow']
            output += ',' + style.attrib['alignment']
            output += ',' + style.attrib['margin_l']
            output += ',' + style.attrib['margin_r']
            output += ',' + style.attrib['margin_v']
            output += ',' + style.attrib['encoding']
            output += '\n'

        output += """
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        for event in sub_root.findall('./events/event'):
            output += 'Dialogue: 0'
            output += ',' + event.attrib['start']
            output += ',' + event.attrib['end']
            output += ',' + event.attrib['style']
            output += ',' + event.attrib['name']
            output += ',' + event.attrib['margin_l']
            output += ',' + event.attrib['margin_r']
            output += ',' + event.attrib['margin_v']
            output += ',' + event.attrib['effect']
            output += ',' + event.attrib['text']
            output += '\n'

        return output

    def _extract_subtitles(self, subtitle):
        sub_root = compat_etree_fromstring(subtitle)
        return [{
            'ext': 'srt',
            'data': self._convert_subtitles_to_srt(sub_root),
        }, {
            'ext': 'ass',
            'data': self._convert_subtitles_to_ass(sub_root),
        }]

    def _get_subtitles(self, video_id, webpage):
        subtitles = {}
        for sub_id, sub_name in re.findall(r'\bssid=([0-9]+)"[^>]+?\btitle="([^"]+)', webpage):
            sub_doc = self._call_rpc_api(
                'Subtitle_GetXml', video_id,
                'Downloading subtitles for ' + sub_name, data={
                    'subtitle_script_id': sub_id,
                })
            if not isinstance(sub_doc, compat_etree_Element):
                continue
            sid = sub_doc.get('id')
            iv = xpath_text(sub_doc, 'iv', 'subtitle iv')
            data = xpath_text(sub_doc, 'data', 'subtitle data')
            if not sid or not iv or not data:
                continue
            subtitle = self._decrypt_subtitles(data, iv, sid).decode('utf-8')
            lang_code = self._search_regex(r'lang_code=["\']([^"\']+)', subtitle, 'subtitle_lang_code', fatal=False)
            if not lang_code:
                continue
            subtitles[lang_code] = self._extract_subtitles(subtitle)
        return subtitles

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        if mobj.group('prefix') == 'm':
            mobile_webpage = self._download_webpage(url, video_id, 'Downloading mobile webpage')
            webpage_url = self._search_regex(r'<link rel="canonical" href="([^"]+)" />', mobile_webpage, 'webpage_url')
        else:
            webpage_url = 'http://www.' + mobj.group('url')

        webpage = self._download_webpage(
            self._add_skip_wall(webpage_url), video_id,
            headers=self.geo_verification_headers())
        note_m = self._html_search_regex(
            r'<div class="showmedia-trailer-notice">(.+?)</div>',
            webpage, 'trailer-notice', default='')
        if note_m:
            raise ExtractorError(note_m, expected=True)

        mobj = re.search(r'Page\.messaging_box_controller\.addItems\(\[(?P<msg>{.+?})\]\)', webpage)
        if mobj:
            msg = json.loads(mobj.group('msg'))
            if msg.get('type') == 'error':
                raise ExtractorError('crunchyroll returned error: %s' % msg['message_body'], expected=True)

        if 'To view this, please log in to verify you are 18 or older.' in webpage:
            self.raise_login_required()

        media = self._parse_json(self._search_regex(
            r'vilos\.config\.media\s*=\s*({.+?});',
            webpage, 'vilos media', default='{}'), video_id)
        media_metadata = media.get('metadata') or {}

        language = self._search_regex(
            r'(?:vilos\.config\.player\.language|LOCALE)\s*=\s*(["\'])(?P<lang>(?:(?!\1).)+)\1',
            webpage, 'language', default=None, group='lang')

        video_title = self._html_search_regex(
            (r'(?s)<h1[^>]*>((?:(?!<h1).)*?<(?:span[^>]+itemprop=["\']title["\']|meta[^>]+itemprop=["\']position["\'])[^>]*>(?:(?!<h1).)+?)</h1>',
             r'<title>(.+?),\s+-\s+.+? Crunchyroll'),
            webpage, 'video_title', default=None)
        if not video_title:
            video_title = re.sub(r'^Watch\s+', '', self._og_search_description(webpage))
        video_title = re.sub(r' {2,}', ' ', video_title)
        video_description = (self._parse_json(self._html_search_regex(
            r'<script[^>]*>\s*.+?\[media_id=%s\].+?({.+?"description"\s*:.+?})\);' % video_id,
            webpage, 'description', default='{}'), video_id) or media_metadata).get('description')

        thumbnails = []
        thumbnail_url = (self._parse_json(self._html_search_regex(
            r'<script type="application\/ld\+json">\n\s*(.+?)<\/script>',
            webpage, 'thumbnail_url', default='{}'), video_id)).get('image')
        if thumbnail_url:
            thumbnails.append({
                'url': thumbnail_url,
                'width': 1920,
                'height': 1080
            })

        if video_description:
            video_description = lowercase_escape(video_description.replace(r'\r\n', '\n'))
        video_uploader = self._html_search_regex(
            # try looking for both an uploader that's a link and one that's not
            [r'<a[^>]+href="/publisher/[^"]+"[^>]*>([^<]+)</a>', r'<div>\s*Publisher:\s*<span>\s*(.+?)\s*</span>\s*</div>'],
            webpage, 'video_uploader', default=False)

        requested_languages = self._configuration_arg('language')
        requested_hardsubs = [('' if val == 'none' else val) for val in self._configuration_arg('hardsub')]
        language_preference = qualities((requested_languages or [language or ''])[::-1])
        hardsub_preference = qualities((requested_hardsubs or ['', language or ''])[::-1])

        formats = []
        for stream in media.get('streams', []):
            audio_lang = stream.get('audio_lang') or ''
            hardsub_lang = stream.get('hardsub_lang') or ''
            if (requested_languages and audio_lang.lower() not in requested_languages
                    or requested_hardsubs and hardsub_lang.lower() not in requested_hardsubs):
                continue
            vrv_formats = self._extract_vrv_formats(
                stream.get('url'), video_id, stream.get('format'),
                audio_lang, hardsub_lang)
            for f in vrv_formats:
                f['language_preference'] = language_preference(audio_lang)
                f['quality'] = hardsub_preference(hardsub_lang)
            formats.extend(vrv_formats)
        if not formats:
            available_fmts = []
            for a, fmt in re.findall(r'(<a[^>]+token=["\']showmedia\.([0-9]{3,4})p["\'][^>]+>)', webpage):
                attrs = extract_attributes(a)
                href = attrs.get('href')
                if href and '/freetrial' in href:
                    continue
                available_fmts.append(fmt)
            if not available_fmts:
                for p in (r'token=["\']showmedia\.([0-9]{3,4})p"', r'showmedia\.([0-9]{3,4})p'):
                    available_fmts = re.findall(p, webpage)
                    if available_fmts:
                        break
            if not available_fmts:
                available_fmts = self._FORMAT_IDS.keys()
            video_encode_ids = []

            for fmt in available_fmts:
                stream_quality, stream_format = self._FORMAT_IDS[fmt]
                video_format = fmt + 'p'
                stream_infos = []
                streamdata = self._call_rpc_api(
                    'VideoPlayer_GetStandardConfig', video_id,
                    'Downloading media info for %s' % video_format, data={
                        'media_id': video_id,
                        'video_format': stream_format,
                        'video_quality': stream_quality,
                        'current_page': url,
                    })
                if isinstance(streamdata, compat_etree_Element):
                    stream_info = streamdata.find('./{default}preload/stream_info')
                    if stream_info is not None:
                        stream_infos.append(stream_info)
                stream_info = self._call_rpc_api(
                    'VideoEncode_GetStreamInfo', video_id,
                    'Downloading stream info for %s' % video_format, data={
                        'media_id': video_id,
                        'video_format': stream_format,
                        'video_encode_quality': stream_quality,
                    })
                if isinstance(stream_info, compat_etree_Element):
                    stream_infos.append(stream_info)
                for stream_info in stream_infos:
                    video_encode_id = xpath_text(stream_info, './video_encode_id')
                    if video_encode_id in video_encode_ids:
                        continue
                    video_encode_ids.append(video_encode_id)

                    video_file = xpath_text(stream_info, './file')
                    if not video_file:
                        continue
                    if video_file.startswith('http'):
                        formats.extend(self._extract_m3u8_formats(
                            video_file, video_id, 'mp4', entry_protocol='m3u8_native',
                            m3u8_id='hls', fatal=False))
                        continue

                    video_url = xpath_text(stream_info, './host')
                    if not video_url:
                        continue
                    metadata = stream_info.find('./metadata')
                    format_info = {
                        'format': video_format,
                        'height': int_or_none(xpath_text(metadata, './height')),
                        'width': int_or_none(xpath_text(metadata, './width')),
                    }

                    if '.fplive.net/' in video_url:
                        video_url = re.sub(r'^rtmpe?://', 'http://', video_url.strip())
                        parsed_video_url = compat_urlparse.urlparse(video_url)
                        direct_video_url = compat_urlparse.urlunparse(parsed_video_url._replace(
                            netloc='v.lvlt.crcdn.net',
                            path='%s/%s' % (remove_end(parsed_video_url.path, '/'), video_file.split(':')[-1])))
                        if self._is_valid_url(direct_video_url, video_id, video_format):
                            format_info.update({
                                'format_id': 'http-' + video_format,
                                'url': direct_video_url,
                            })
                            formats.append(format_info)
                            continue

                    format_info.update({
                        'format_id': 'rtmp-' + video_format,
                        'url': video_url,
                        'play_path': video_file,
                        'ext': 'flv',
                    })
                    formats.append(format_info)
        self._sort_formats(formats)

        metadata = self._call_rpc_api(
            'VideoPlayer_GetMediaMetadata', video_id,
            note='Downloading media info', data={
                'media_id': video_id,
            })

        subtitles = {}
        for subtitle in media.get('subtitles', []):
            subtitle_url = subtitle.get('url')
            if not subtitle_url:
                continue
            subtitles.setdefault(subtitle.get('language', 'enUS'), []).append({
                'url': subtitle_url,
                'ext': subtitle.get('format', 'ass'),
            })
        if not subtitles:
            subtitles = self.extract_subtitles(video_id, webpage)

        # webpage provide more accurate data than series_title from XML
        series = self._html_search_regex(
            r'(?s)<h\d[^>]+\bid=["\']showmedia_about_episode_num[^>]+>(.+?)</h\d',
            webpage, 'series', fatal=False)

        season = episode = episode_number = duration = None

        if isinstance(metadata, compat_etree_Element):
            season = xpath_text(metadata, 'series_title')
            episode = xpath_text(metadata, 'episode_title')
            episode_number = int_or_none(xpath_text(metadata, 'episode_number'))
            duration = float_or_none(media_metadata.get('duration'), 1000)

        if not episode:
            episode = media_metadata.get('title')
        if not episode_number:
            episode_number = int_or_none(media_metadata.get('episode_number'))
        thumbnail_url = try_get(media, lambda x: x['thumbnail']['url'])
        if thumbnail_url:
            thumbnails.append({
                'url': thumbnail_url,
                'width': 640,
                'height': 360
            })

        season_number = int_or_none(self._search_regex(
            r'(?s)<h\d[^>]+id=["\']showmedia_about_episode_num[^>]+>.+?</h\d>\s*<h4>\s*Season (\d+)',
            webpage, 'season number', default=None))

        info = self._search_json_ld(webpage, video_id, default={})

        return merge_dicts({
            'id': video_id,
            'title': video_title,
            'description': video_description,
            'duration': duration,
            'thumbnails': thumbnails,
            'uploader': video_uploader,
            'series': series,
            'season': season,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'subtitles': subtitles,
            'formats': formats,
        }, info)


class CrunchyrollShowPlaylistIE(CrunchyrollBaseIE):
    IE_NAME = 'crunchyroll:playlist'
    _VALID_URL = r'https?://(?:(?P<prefix>www|m)\.)?(?P<url>crunchyroll\.com/(?:\w{1,2}/)?(?!(?:news|anime-news|library|forum|launchcalendar|lineup|store|comics|freetrial|login|media-\d+))(?P<id>[\w\-]+))/?(?:\?|$)'

    _TESTS = [{
        'url': 'https://www.crunchyroll.com/a-bridge-to-the-starry-skies-hoshizora-e-kakaru-hashi',
        'info_dict': {
            'id': 'a-bridge-to-the-starry-skies-hoshizora-e-kakaru-hashi',
            'title': 'A Bridge to the Starry Skies - Hoshizora e Kakaru Hashi'
        },
        'playlist_count': 13,
    }, {
        # geo-restricted (US), 18+ maturity wall, non-premium available
        'url': 'http://www.crunchyroll.com/cosplay-complex-ova',
        'info_dict': {
            'id': 'cosplay-complex-ova',
            'title': 'Cosplay Complex OVA'
        },
        'playlist_count': 3,
        'skip': 'Georestricted',
    }, {
        # geo-restricted (US), 18+ maturity wall, non-premium will be available since 2015.11.14
        'url': 'http://www.crunchyroll.com/ladies-versus-butlers?skip_wall=1',
        'only_matching': True,
    }, {
        'url': 'http://www.crunchyroll.com/fr/ladies-versus-butlers',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        show_id = self._match_id(url)

        webpage = self._download_webpage(
            # https:// gives a 403, but http:// does not
            self._add_skip_wall(url).replace('https://', 'http://'), show_id,
            headers=self.geo_verification_headers())
        title = self._html_search_meta('name', webpage, default=None)

        episode_re = r'<li id="showview_videos_media_(\d+)"[^>]+>.*?<a href="([^"]+)"'
        season_re = r'<a [^>]+season-dropdown[^>]+>([^<]+)'
        paths = re.findall(f'(?s){episode_re}|{season_re}', webpage)

        entries, current_season = [], None
        for ep_id, ep, season in paths:
            if season:
                current_season = season
                continue
            entries.append(self.url_result(
                f'http://www.crunchyroll.com{ep}', CrunchyrollIE.ie_key(), ep_id, season=current_season))

        return {
            '_type': 'playlist',
            'id': show_id,
            'title': title,
            'entries': reversed(entries),
        }


class CrunchyrollBetaIE(CrunchyrollBaseIE):
    IE_NAME = 'crunchyroll:beta'
    _VALID_URL = r'https?://beta\.crunchyroll\.com/(?P<lang>(?:\w{1,2}/)?)watch/(?P<internal_id>\w+)/(?P<id>[\w\-]+)/?(?:\?|$)'
    _TESTS = [{
        'url': 'https://beta.crunchyroll.com/watch/GY2P1Q98Y/to-the-future',
        'info_dict': {
            'id': '696363',
            'ext': 'mp4',
            'timestamp': 1459610100,
            'description': 'md5:a022fbec4fbb023d43631032c91ed64b',
            'uploader': 'Toei Animation',
            'title': 'World Trigger Episode 73 – To the Future',
            'upload_date': '20160402',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Unable to download XML']
    }]

    def _real_extract(self, url):
        lang, internal_id, display_id = self._match_valid_url(url).group('lang', 'internal_id', 'id')
        webpage = self._download_webpage(url, display_id)
        initial_state = self._parse_json(
            self._search_regex(r'__INITIAL_STATE__\s*=\s*({.+?})\s*;', webpage, 'initial state'),
            display_id)
        episode_data = initial_state['content']['byId'][internal_id]
        if not self._get_cookies(url).get('etp_rt'):
            video_id = episode_data['external_id'].split('.')[1]
            series_id = episode_data['episode_metadata']['series_slug_title']
            return self.url_result(f'https://www.crunchyroll.com/{lang}{series_id}/{display_id}-{video_id}',
                                   CrunchyrollIE.ie_key(), video_id)

        app_config = self._parse_json(
            self._search_regex(r'__APP_CONFIG__\s*=\s*({.+?})\s*;', webpage, 'app config'),
            display_id)
        client_id = app_config['cxApiParams']['accountAuthClientId']
        api_domain = app_config['cxApiParams']['apiDomain']
        basic_token = str(base64.b64encode(('%s:' % client_id).encode('ascii')), 'ascii')
        auth_response = self._download_json(
            f'{api_domain}/auth/v1/token', display_id,
            note='Authenticating with cookie',
            headers={
                'Authorization': 'Basic ' + basic_token
            }, data='grant_type=etp_rt_cookie'.encode('ascii'))
        policy_response = self._download_json(
            f'{api_domain}/index/v2', display_id,
            note='Retrieving signed policy',
            headers={
                'Authorization': auth_response['token_type'] + ' ' + auth_response['access_token']
            })
        bucket = policy_response['cms']['bucket']
        params = {
            'Policy': policy_response['cms']['policy'],
            'Signature': policy_response['cms']['signature'],
            'Key-Pair-Id': policy_response['cms']['key_pair_id']
        }
        locale = traverse_obj(initial_state, ('localization', 'locale'))
        if locale:
            params['locale'] = locale
        episode_response = self._download_json(
            f'{api_domain}/cms/v2{bucket}/episodes/{internal_id}', display_id,
            note='Retrieving episode metadata',
            query=params)
        if episode_response.get('is_premium_only') and not episode_response.get('playback'):
            raise ExtractorError('This video is for premium members only.', expected=True)
        stream_response = self._download_json(
            episode_response['playback'], display_id,
            note='Retrieving stream info')

        thumbnails = []
        for thumbnails_data in traverse_obj(episode_response, ('images', 'thumbnail')):
            for thumbnail_data in thumbnails_data:
                thumbnails.append({
                    'url': thumbnail_data.get('source'),
                    'width': thumbnail_data.get('width'),
                    'height': thumbnail_data.get('height'),
                })
        subtitles = {}
        for lang, subtitle_data in stream_response.get('subtitles').items():
            subtitles[lang] = [{
                'url': subtitle_data.get('url'),
                'ext': subtitle_data.get('format')
            }]

        requested_hardsubs = [('' if val == 'none' else val) for val in (self._configuration_arg('hardsub') or ['none'])]
        hardsub_preference = qualities(requested_hardsubs[::-1])
        requested_formats = self._configuration_arg('format') or ['adaptive_hls']

        formats = []
        for stream_type, streams in stream_response.get('streams', {}).items():
            if stream_type not in requested_formats:
                continue
            for stream in streams.values():
                hardsub_lang = stream.get('hardsub_locale') or ''
                if hardsub_lang.lower() not in requested_hardsubs:
                    continue
                format_id = join_nonempty(
                    stream_type,
                    format_field(stream, 'hardsub_locale', 'hardsub-%s'))
                if not stream.get('url'):
                    continue
                if stream_type.split('_')[-1] == 'hls':
                    adaptive_formats = self._extract_m3u8_formats(
                        stream['url'], display_id, 'mp4', m3u8_id=format_id,
                        note='Downloading %s information' % format_id,
                        fatal=False)
                elif stream_type.split('_')[-1] == 'dash':
                    adaptive_formats = self._extract_mpd_formats(
                        stream['url'], display_id, mpd_id=format_id,
                        note='Downloading %s information' % format_id,
                        fatal=False)
                for f in adaptive_formats:
                    if f.get('acodec') != 'none':
                        f['language'] = stream_response.get('audio_locale')
                    f['quality'] = hardsub_preference(hardsub_lang.lower())
                formats.extend(adaptive_formats)
        self._sort_formats(formats)

        return {
            'id': internal_id,
            'title': '%s Episode %s – %s' % (episode_response.get('season_title'), episode_response.get('episode'), episode_response.get('title')),
            'description': episode_response.get('description').replace(r'\r\n', '\n'),
            'duration': float_or_none(episode_response.get('duration_ms'), 1000),
            'thumbnails': thumbnails,
            'series': episode_response.get('series_title'),
            'series_id': episode_response.get('series_id'),
            'season': episode_response.get('season_title'),
            'season_id': episode_response.get('season_id'),
            'season_number': episode_response.get('season_number'),
            'episode': episode_response.get('title'),
            'episode_number': episode_response.get('sequence_number'),
            'subtitles': subtitles,
            'formats': formats
        }


class CrunchyrollBetaShowIE(CrunchyrollBaseIE):
    IE_NAME = 'crunchyroll:playlist:beta'
    _VALID_URL = r'https?://beta\.crunchyroll\.com/(?P<lang>(?:\w{1,2}/)?)series/\w+/(?P<id>[\w\-]+)/?(?:\?|$)'
    _TESTS = [{
        'url': 'https://beta.crunchyroll.com/series/GY19NQ2QR/Girl-Friend-BETA',
        'info_dict': {
            'id': 'girl-friend-beta',
            'title': 'Girl Friend BETA',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://beta.crunchyroll.com/it/series/GY19NQ2QR/Girl-Friend-BETA',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lang, series_id = self._match_valid_url(url).group('lang', 'id')
        return self.url_result(f'https://www.crunchyroll.com/{lang}{series_id.lower()}',
                               CrunchyrollShowPlaylistIE.ie_key(), series_id)
