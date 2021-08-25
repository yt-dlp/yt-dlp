# coding: utf-8
from __future__ import unicode_literals

import re
import time
import hmac
import binascii
import hashlib


from .once import OnceIE
from .adobepass import AdobePassIE
from ..utils import (
    determine_ext,
    ExtractorError,
    float_or_none,
    int_or_none,
    parse_qs,
    sanitized_Request,
    unsmuggle_url,
    update_url_query,
    xpath_with_ns,
    mimetype2ext,
    find_xpath_attr,
)

default_ns = 'http://www.w3.org/2005/SMIL21/Language'
_x = lambda p: xpath_with_ns(p, {'smil': default_ns})


class ThePlatformBaseIE(OnceIE):
    _TP_TLD = 'com'

    def _extract_theplatform_smil(self, smil_url, video_id, note='Downloading SMIL data'):
        meta = self._download_xml(
            smil_url, video_id, note=note, query={'format': 'SMIL'},
            headers=self.geo_verification_headers())
        error_element = find_xpath_attr(meta, _x('.//smil:ref'), 'src')
        if error_element is not None:
            exception = find_xpath_attr(
                error_element, _x('.//smil:param'), 'name', 'exception')
            if exception is not None:
                if exception.get('value') == 'GeoLocationBlocked':
                    self.raise_geo_restricted(error_element.attrib['abstract'])
                elif error_element.attrib['src'].startswith(
                        'http://link.theplatform.%s/s/errorFiles/Unavailable.'
                        % self._TP_TLD):
                    raise ExtractorError(
                        error_element.attrib['abstract'], expected=True)

        smil_formats = self._parse_smil_formats(
            meta, smil_url, video_id, namespace=default_ns,
            # the parameters are from syfy.com, other sites may use others,
            # they also work for nbc.com
            f4m_params={'g': 'UXWGVKRWHFSP', 'hdcore': '3.0.3'},
            transform_rtmp_url=lambda streamer, src: (streamer, 'mp4:' + src))

        formats = []
        for _format in smil_formats:
            if OnceIE.suitable(_format['url']):
                formats.extend(self._extract_once_formats(_format['url']))
            else:
                media_url = _format['url']
                if determine_ext(media_url) == 'm3u8':
                    hdnea2 = self._get_cookies(media_url).get('hdnea2')
                    if hdnea2:
                        _format['url'] = update_url_query(media_url, {'hdnea3': hdnea2.value})

                formats.append(_format)

        subtitles = self._parse_smil_subtitles(meta, default_ns)

        return formats, subtitles

    def _download_theplatform_metadata(self, path, video_id):
        info_url = 'http://link.theplatform.%s/s/%s?format=preview' % (self._TP_TLD, path)
        return self._download_json(info_url, video_id)

    def _parse_theplatform_metadata(self, info):
        subtitles = {}
        captions = info.get('captions')
        if isinstance(captions, list):
            for caption in captions:
                lang, src, mime = caption.get('lang', 'en'), caption.get('src'), caption.get('type')
                subtitles.setdefault(lang, []).append({
                    'ext': mimetype2ext(mime),
                    'url': src,
                })

        duration = info.get('duration')
        tp_chapters = info.get('chapters', [])
        chapters = []
        if tp_chapters:
            def _add_chapter(start_time, end_time):
                start_time = float_or_none(start_time, 1000)
                end_time = float_or_none(end_time, 1000)
                if start_time is None or end_time is None:
                    return
                chapters.append({
                    'start_time': start_time,
                    'end_time': end_time,
                })

            for chapter in tp_chapters[:-1]:
                _add_chapter(chapter.get('startTime'), chapter.get('endTime'))
            _add_chapter(tp_chapters[-1].get('startTime'), tp_chapters[-1].get('endTime') or duration)

        return {
            'title': info['title'],
            'subtitles': subtitles,
            'description': info['description'],
            'thumbnail': info['defaultThumbnailUrl'],
            'duration': float_or_none(duration, 1000),
            'timestamp': int_or_none(info.get('pubDate'), 1000) or None,
            'uploader': info.get('billingCode'),
            'chapters': chapters,
        }

    def _extract_theplatform_metadata(self, path, video_id):
        info = self._download_theplatform_metadata(path, video_id)
        return self._parse_theplatform_metadata(info)


class ThePlatformIE(ThePlatformBaseIE, AdobePassIE):
    _VALID_URL = r'''(?x)
        (?:https?://(?:link|player)\.theplatform\.com/[sp]/(?P<provider_id>[^/]+)/
           (?:(?:(?:[^/]+/)+select/)?(?P<media>media/(?:guid/\d+/)?)?|(?P<config>(?:[^/\?]+/(?:swf|config)|onsite)/select/))?
         |theplatform:)(?P<id>[^/\?&]+)'''

    _TESTS = [{
        # from http://www.metacafe.com/watch/cb-e9I_cZgTgIPd/blackberrys_big_bold_z30/
        'url': 'http://link.theplatform.com/s/dJ5BDC/e9I_cZgTgIPd/meta.smil?format=smil&Tracking=true&mbr=true',
        'info_dict': {
            'id': 'e9I_cZgTgIPd',
            'ext': 'flv',
            'title': 'Blackberry\'s big, bold Z30',
            'description': 'The Z30 is Blackberry\'s biggest, baddest mobile messaging device yet.',
            'duration': 247,
            'timestamp': 1383239700,
            'upload_date': '20131031',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
        'skip': '404 Not Found',
    }, {
        # from http://www.cnet.com/videos/tesla-model-s-a-second-step-towards-a-cleaner-motoring-future/
        'url': 'http://link.theplatform.com/s/kYEXFC/22d_qsQ6MIRT',
        'info_dict': {
            'id': '22d_qsQ6MIRT',
            'ext': 'flv',
            'description': 'md5:ac330c9258c04f9d7512cf26b9595409',
            'title': 'Tesla Model S: A second step towards a cleaner motoring future',
            'timestamp': 1426176191,
            'upload_date': '20150312',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        }
    }, {
        'url': 'https://player.theplatform.com/p/D6x-PC/pulse_preview/embed/select/media/yMBg9E8KFxZD',
        'info_dict': {
            'id': 'yMBg9E8KFxZD',
            'ext': 'mp4',
            'description': 'md5:644ad9188d655b742f942bf2e06b002d',
            'title': 'HIGHLIGHTS: USA bag first ever series Cup win',
            'uploader': 'EGSM',
        }
    }, {
        'url': 'http://player.theplatform.com/p/NnzsPC/widget/select/media/4Y0TlYUr_ZT7',
        'only_matching': True,
    }, {
        'url': 'http://player.theplatform.com/p/2E2eJC/nbcNewsOffsite?guid=tdy_or_siri_150701',
        'md5': 'fb96bb3d85118930a5b055783a3bd992',
        'info_dict': {
            'id': 'tdy_or_siri_150701',
            'ext': 'mp4',
            'title': 'iPhone Siri’s sassy response to a math question has people talking',
            'description': 'md5:a565d1deadd5086f3331d57298ec6333',
            'duration': 83.0,
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1435752600,
            'upload_date': '20150701',
            'uploader': 'NBCU-NEWS',
        },
    }, {
        # From http://www.nbc.com/the-blacklist/video/sir-crispin-crandall/2928790?onid=137781#vc137781=1
        # geo-restricted (US), HLS encrypted with AES-128
        'url': 'http://player.theplatform.com/p/NnzsPC/onsite_universal/select/media/guid/2410887629/2928790?fwsitesection=nbc_the_blacklist_video_library&autoPlay=true&carouselID=137781',
        'only_matching': True,
    }]

    @classmethod
    def _extract_urls(cls, webpage):
        m = re.search(
            r'''(?x)
                    <meta\s+
                        property=(["'])(?:og:video(?::(?:secure_)?url)?|twitter:player)\1\s+
                        content=(["'])(?P<url>https?://player\.theplatform\.com/p/.+?)\2
            ''', webpage)
        if m:
            return [m.group('url')]

        # Are whitespaces ignored in URLs?
        # https://github.com/ytdl-org/youtube-dl/issues/12044
        matches = re.findall(
            r'(?s)<(?:iframe|script)[^>]+src=(["\'])((?:https?:)?//player\.theplatform\.com/p/.+?)\1', webpage)
        if matches:
            return [re.sub(r'\s', '', list(zip(*matches))[1][0])]

    @staticmethod
    def _sign_url(url, sig_key, sig_secret, life=600, include_qs=False):
        flags = '10' if include_qs else '00'
        expiration_date = '%x' % (int(time.time()) + life)

        def str_to_hex(str):
            return binascii.b2a_hex(str.encode('ascii')).decode('ascii')

        def hex_to_bytes(hex):
            return binascii.a2b_hex(hex.encode('ascii'))

        relative_path = re.match(r'https?://link\.theplatform\.com/s/([^?]+)', url).group(1)
        clear_text = hex_to_bytes(flags + expiration_date + str_to_hex(relative_path))
        checksum = hmac.new(sig_key.encode('ascii'), clear_text, hashlib.sha1).hexdigest()
        sig = flags + expiration_date + checksum + str_to_hex(sig_secret)
        return '%s&sig=%s' % (url, sig)

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        self._initialize_geo_bypass({
            'countries': smuggled_data.get('geo_countries'),
        })

        mobj = self._match_valid_url(url)
        provider_id = mobj.group('provider_id')
        video_id = mobj.group('id')

        if not provider_id:
            provider_id = 'dJ5BDC'

        path = provider_id + '/'
        if mobj.group('media'):
            path += mobj.group('media')
        path += video_id

        qs_dict = parse_qs(url)
        if 'guid' in qs_dict:
            webpage = self._download_webpage(url, video_id)
            scripts = re.findall(r'<script[^>]+src="([^"]+)"', webpage)
            feed_id = None
            # feed id usually locates in the last script.
            # Seems there's no pattern for the interested script filename, so
            # I try one by one
            for script in reversed(scripts):
                feed_script = self._download_webpage(
                    self._proto_relative_url(script, 'http:'),
                    video_id, 'Downloading feed script')
                feed_id = self._search_regex(
                    r'defaultFeedId\s*:\s*"([^"]+)"', feed_script,
                    'default feed id', default=None)
                if feed_id is not None:
                    break
            if feed_id is None:
                raise ExtractorError('Unable to find feed id')
            return self.url_result('http://feed.theplatform.com/f/%s/%s?byGuid=%s' % (
                provider_id, feed_id, qs_dict['guid'][0]))

        if smuggled_data.get('force_smil_url', False):
            smil_url = url
        # Explicitly specified SMIL (see https://github.com/ytdl-org/youtube-dl/issues/7385)
        elif '/guid/' in url:
            headers = {}
            source_url = smuggled_data.get('source_url')
            if source_url:
                headers['Referer'] = source_url
            request = sanitized_Request(url, headers=headers)
            webpage = self._download_webpage(request, video_id)
            smil_url = self._search_regex(
                r'<link[^>]+href=(["\'])(?P<url>.+?)\1[^>]+type=["\']application/smil\+xml',
                webpage, 'smil url', group='url')
            path = self._search_regex(
                r'link\.theplatform\.com/s/((?:[^/?#&]+/)+[^/?#&]+)', smil_url, 'path')
            smil_url += '?' if '?' not in smil_url else '&' + 'formats=m3u,mpeg4'
        elif mobj.group('config'):
            config_url = url + '&form=json'
            config_url = config_url.replace('swf/', 'config/')
            config_url = config_url.replace('onsite/', 'onsite/config/')
            config = self._download_json(config_url, video_id, 'Downloading config')
            if 'releaseUrl' in config:
                release_url = config['releaseUrl']
            else:
                release_url = 'http://link.theplatform.com/s/%s?mbr=true' % path
            smil_url = release_url + '&formats=MPEG4&manifest=f4m'
        else:
            smil_url = 'http://link.theplatform.com/s/%s?mbr=true' % path

        sig = smuggled_data.get('sig')
        if sig:
            smil_url = self._sign_url(smil_url, sig['key'], sig['secret'])

        formats, subtitles = self._extract_theplatform_smil(smil_url, video_id)
        self._sort_formats(formats)

        ret = self._extract_theplatform_metadata(path, video_id)
        combined_subtitles = self._merge_subtitles(ret.get('subtitles', {}), subtitles)
        ret.update({
            'id': video_id,
            'formats': formats,
            'subtitles': combined_subtitles,
        })

        return ret


class ThePlatformFeedIE(ThePlatformBaseIE):
    _URL_TEMPLATE = '%s//feed.theplatform.com/f/%s/%s?form=json&%s'
    _VALID_URL = r'https?://feed\.theplatform\.com/f/(?P<provider_id>[^/]+)/(?P<feed_id>[^?/]+)\?(?:[^&]+&)*(?P<filter>by(?:Gui|I)d=(?P<id>[^&]+))'
    _TESTS = [{
        # From http://player.theplatform.com/p/7wvmTC/MSNBCEmbeddedOffSite?guid=n_hardball_5biden_140207
        'url': 'http://feed.theplatform.com/f/7wvmTC/msnbc_video-p-test?form=json&pretty=true&range=-40&byGuid=n_hardball_5biden_140207',
        'md5': '6e32495b5073ab414471b615c5ded394',
        'info_dict': {
            'id': 'n_hardball_5biden_140207',
            'ext': 'mp4',
            'title': 'The Biden factor: will Joe run in 2016?',
            'description': 'Could Vice President Joe Biden be preparing a 2016 campaign? Mark Halperin and Sam Stein weigh in.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20140208',
            'timestamp': 1391824260,
            'duration': 467.0,
            'categories': ['MSNBC/Issues/Democrats', 'MSNBC/Issues/Elections/Election 2016'],
            'uploader': 'NBCU-NEWS',
        },
    }, {
        'url': 'http://feed.theplatform.com/f/2E2eJC/nnd_NBCNews?byGuid=nn_netcast_180306.Copy.01',
        'only_matching': True,
    }]

    def _extract_feed_info(self, provider_id, feed_id, filter_query, video_id, custom_fields=None, asset_types_query={}, account_id=None):
        real_url = self._URL_TEMPLATE % (self.http_scheme(), provider_id, feed_id, filter_query)
        entry = self._download_json(real_url, video_id)['entries'][0]
        main_smil_url = 'http://link.theplatform.com/s/%s/media/guid/%d/%s' % (provider_id, account_id, entry['guid']) if account_id else entry.get('plmedia$publicUrl')

        formats = []
        subtitles = {}
        first_video_id = None
        duration = None
        asset_types = []
        for item in entry['media$content']:
            smil_url = item['plfile$url']
            cur_video_id = ThePlatformIE._match_id(smil_url)
            if first_video_id is None:
                first_video_id = cur_video_id
                duration = float_or_none(item.get('plfile$duration'))
            file_asset_types = item.get('plfile$assetTypes') or parse_qs(smil_url)['assetTypes']
            for asset_type in file_asset_types:
                if asset_type in asset_types:
                    continue
                asset_types.append(asset_type)
                query = {
                    'mbr': 'true',
                    'formats': item['plfile$format'],
                    'assetTypes': asset_type,
                }
                if asset_type in asset_types_query:
                    query.update(asset_types_query[asset_type])
                cur_formats, cur_subtitles = self._extract_theplatform_smil(update_url_query(
                    main_smil_url or smil_url, query), video_id, 'Downloading SMIL data for %s' % asset_type)
                formats.extend(cur_formats)
                subtitles = self._merge_subtitles(subtitles, cur_subtitles)

        self._sort_formats(formats)

        thumbnails = [{
            'url': thumbnail['plfile$url'],
            'width': int_or_none(thumbnail.get('plfile$width')),
            'height': int_or_none(thumbnail.get('plfile$height')),
        } for thumbnail in entry.get('media$thumbnails', [])]

        timestamp = int_or_none(entry.get('media$availableDate'), scale=1000)
        categories = [item['media$name'] for item in entry.get('media$categories', [])]

        ret = self._extract_theplatform_metadata('%s/%s' % (provider_id, first_video_id), video_id)
        subtitles = self._merge_subtitles(subtitles, ret['subtitles'])
        ret.update({
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'duration': duration,
            'timestamp': timestamp,
            'categories': categories,
        })
        if custom_fields:
            ret.update(custom_fields(entry))

        return ret

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)

        video_id = mobj.group('id')
        provider_id = mobj.group('provider_id')
        feed_id = mobj.group('feed_id')
        filter_query = mobj.group('filter')

        return self._extract_feed_info(provider_id, feed_id, filter_query, video_id)
