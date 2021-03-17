# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    get_element_by_attribute,
    get_element_by_class,
    int_or_none,
    parse_bitrate,
    parse_resolution,
    unified_timestamp,
    urlencode_postdata,
    url_or_none,
)


class IcareusIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://(?:www\.)?
                        (?:
                            asahitv\.fi|
                            helsinkikanava\.fi|
                            hyvinvointitv\.fi|
                            inez\.fi|
                            permanto\.fi|
                            suite.icareus.com|
                            videos\.minifiddlers\.org
                        )
                        /.+/player/.*(?:assetId|eventId)=(?P<id>\d+).*'''
    _TESTS = [{
        'url': 'https://www.helsinkikanava.fi/fi_FI/web/helsinkikanava/player/vod?assetId=68021894',
        'md5': 'ca0b62ffc814a5411dfa6349cf5adb8a',
        'info_dict': {
            'id': '68021894',
            'ext': 'mp4',
            'title': 'Perheiden parhaaksi',
            'description': 'md5:295785ea408e5ac00708766465cc1325',
            'thumbnail': 'https://www.helsinkikanava.fi/image/image_gallery?img_id=68022501',
            'upload_date': '20200924',
            'timestamp': 1600938300,
        },
    }, {  # Recorded livestream
        'url': 'https://www.helsinkikanava.fi/fi/web/helsinkikanava/player/event/view?eventId=76241489',
        'md5': '014327e69dfa7b949fcc861f6d162d6d',
        'info_dict': {
            'id': '76258304',
            'ext': 'mp4',
            'title': 'Helsingin kaupungin ja HUSin tiedotustilaisuus koronaepidemiatilanteesta 24.11.2020',
            'description': 'md5:3129d041c6fbbcdc7fe68d9a938fef1c',
            'thumbnail': 'https://icareus-suite.secure2.footprint.net/image/image_gallery?img_id=76288630',
            'upload_date': '20201124',
            'timestamp': 1606206600,
        },
    }, {
        'url': 'https://asahitv.fi/fi/web/asahi/player/vod?assetId=89415818',
        'only_matching': True
    }, {
        'url': 'https://hyvinvointitv.fi/fi/web/hyvinvointitv/player/vod?assetId=89149730',
        'only_matching': True
    }, {
        'url': 'https://inez.fi/fi/web/inez-media/player/vod?assetId=71328822',
        'only_matching': True
    }, {
        'url': 'https://www.permanto.fi/web/alfatv/player/vod?assetId=165743121',
        'only_matching': True
    }, {
        'url': 'https://suite.icareus.com/fi/web/westend-indians/player/vod?assetId=47567389',
        'only_matching': True
    }, {
        'url': 'https://videos.minifiddlers.org/web/international-minifiddlers/player/vod?assetId=1982759',
        'only_matching': True
    }]
    _API2_PATH = '/icareus-suite-api-portlet/publishing'

    def _real_extract(self, url):
        maybe_id = self._match_id(url)
        page = self._download_webpage(url, maybe_id)
        video_id = self._search_regex(
            r"_icareus\['itemId'\]='(\d+)'", page, "video_id")
        api_base = self._search_regex(
            r'var publishingServiceURL = "(http.*?)";', page, "api_base")
        organization_id = self._search_regex(
            r"_icareus\['organizationId'\]='(\d+)'", page, "organization_id")
        token = self._search_regex(
            r"_icareus\['token'\]='([a-f0-9]+)'", page, "token")

        token2 = self._search_regex(
            r'''data\s*:\s*{action:"getAsset".*?token:'([a-f0-9]+)'}''', page,
            "token2", default=None, fatal=False)
        metajson = get_element_by_attribute('type', 'application/ld+json', page)

        metad = None
        if metajson:
            # The description can contain newlines, HTML tags, quote chars etc.
            # so we'll extract it manually
            mo = re.match(
                r'(.*",)\s*"description": "(.*?)",(\s*"thumbnailUrl":.*)',
                metajson, flags=re.DOTALL)
            if mo:
                desc_text = mo.group(2)
                metajson = mo.group(1) + mo.group(3)
                metad = self._parse_json(metajson, video_id, fatal=False)
            else:
                self.report_warning("Could not fix metadata JSON", video_id)

        livestream_title = get_element_by_class(
            'unpublished-info-item future-event-title', page)

        duration = None
        thumbnail = None
        if metad:
            title = metad.get('name')
            description = desc_text
            timestamp = unified_timestamp(metad.get('uploadDate'))
            thumbnail = url_or_none(metad.get('thumbnailUrl'))
        elif token2:
            base_url = self._search_regex(r'(https?://[^/]+)/', url, 'base_url')
            data = {
                "version": "03",
                "action": "getAsset",
                "organizationId": organization_id,
                "assetId": video_id,
                "languageId": "en_US",
                "userId": "0",
                "token": token2,
            }
            metad = self._download_json(base_url + self._API2_PATH, video_id,
                                        data=urlencode_postdata(data))
            title = metad.get('name')
            description = metad.get('description')
            timestamp = int_or_none(metad.get('date'), scale=1000)
            duration = int_or_none(metad.get('duration'))
            thumbnail = url_or_none(metad.get('thumbnailMedium'))
        elif livestream_title:  # Recorded livestream
            title = livestream_title
            description = get_element_by_class(
                'unpublished-info-item future-event-description', page)
            timestamp = int_or_none(self._search_regex(
                r"var startEvent\s*=\s*(\d+);", page, "uploadDate",
                fatal=False), scale=1000)
        else:
            self.report_warning("Could not extract metadata", video_id)
            description = None
            timestamp = None

        title = title if title else video_id
        description = clean_html(description)

        data = {
            "version": "03",
            "action": "getAssetPlaybackUrls",
            "organizationId": organization_id,
            "assetId": video_id,
            "token": token,
        }
        jsond = self._download_json(api_base, video_id,
                                    data=urlencode_postdata(data))

        if thumbnail is None:
            thumbnail = url_or_none(jsond.get('thumbnail'))

        formats = []
        for item in jsond.get('urls', []):
            video_url = url_or_none(item.get('url'))
            ext = determine_ext(video_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    video_url, video_id, 'mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls',
                    fatal=False))
            else:
                fd = {'url': video_url}
                fmt = item.get('name')
                if fmt:
                    fd['format'] = fmt
                    fd.update(parse_resolution(fmt))
                    mo = re.search(r'\((\d+)\s*kbps\)\s*\+\s*(\d+)\s*kbps', fmt)
                    if mo:
                        fd['vbr'] = int_or_none(mo.group(1))
                        fd['abr'] = int_or_none(mo.group(2))
                    else:
                        fd['tbr'] = parse_bitrate(fmt)
                fmt_id = item.get('id')
                if fmt_id:
                    fd['format_id'] = str(fmt_id)
                formats.append(fd)

        for item in jsond.get('audio_urls', []):
            fmt = item.get('name')
            mo = re.match(r'.*\((\d+)k\).*', fmt if fmt else '')
            abr = int_or_none(mo.group(1)) if mo else None
            fd = {
                'format': fmt,
                'format_id': 'audio',
                'url': url_or_none(item.get('url')),
                'vcodec': 'none',
            }
            if abr:
                fd['abr'] = abr
            formats.append(fd)

        subtitles = {}
        for sub in jsond.get('subtitles', []):
            scode, sdesc, surl = sub
            lang = sdesc.split(' ')[0]
            lang = lang[:-1] if lang.endswith(':') else lang
            subtitles[lang] = [{"url": url_or_none(surl)}]

        info = {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'formats': formats,
        }
        if duration:
            info['duration'] = duration
        if subtitles:
            info['subtitles'] = subtitles

        return info
