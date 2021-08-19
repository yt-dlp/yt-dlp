from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    find_xpath_attr,
    int_or_none,
    js_to_json,
    unescapeHTML,
    determine_ext,
)


class HowStuffWorksIE(InfoExtractor):
    _VALID_URL = r'https?://[\da-z-]+\.(?:howstuffworks|stuff(?:(?:youshould|theydontwantyouto)know|toblowyourmind|momnevertoldyou)|(?:brain|car)stuffshow|fwthinking|geniusstuff)\.com/(?:[^/]+/)*(?:\d+-)?(?P<id>.+?)-video\.htm'
    _TESTS = [
        {
            'url': 'http://www.stufftoblowyourmind.com/videos/optical-illusions-video.htm',
            'md5': '76646a5acc0c92bf7cd66751ca5db94d',
            'info_dict': {
                'id': '855410',
                'ext': 'mp4',
                'title': 'Your Trickster Brain: Optical Illusions -- Science on the Web',
                'description': 'md5:e374ff9561f6833ad076a8cc0a5ab2fb',
            },
        },
        {
            'url': 'http://shows.howstuffworks.com/more-shows/why-does-balloon-stick-to-hair-video.htm',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        clip_js = self._search_regex(
            r'(?s)var clip = ({.*?});', webpage, 'clip info')
        clip_info = self._parse_json(
            clip_js, display_id, transform_source=js_to_json)

        video_id = clip_info['content_id']
        formats = []
        m3u8_url = clip_info.get('m3u8')
        if m3u8_url and determine_ext(m3u8_url) == 'm3u8':
            formats.extend(self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', format_id='hls', fatal=True))
        flv_url = clip_info.get('flv_url')
        if flv_url:
            formats.append({
                'url': flv_url,
                'format_id': 'flv',
            })
        for video in clip_info.get('mp4', []):
            formats.append({
                'url': video['src'],
                'format_id': 'mp4-%s' % video['bitrate'],
                'vbr': int_or_none(video['bitrate'].rstrip('k')),
            })

        if not formats:
            smil = self._download_xml(
                'http://services.media.howstuffworks.com/videos/%s/smil-service.smil' % video_id,
                video_id, 'Downloading video SMIL')

            http_base = find_xpath_attr(
                smil,
                './{0}head/{0}meta'.format('{http://www.w3.org/2001/SMIL20/Language}'),
                'name',
                'httpBase').get('content')

            URL_SUFFIX = '?v=2.11.3&fp=LNX 11,2,202,356&r=A&g=A'

            for video in smil.findall(
                    './{0}body/{0}switch/{0}video'.format('{http://www.w3.org/2001/SMIL20/Language}')):
                vbr = int_or_none(video.attrib['system-bitrate'], scale=1000)
                formats.append({
                    'url': '%s/%s%s' % (http_base, video.attrib['src'], URL_SUFFIX),
                    'format_id': '%dk' % vbr,
                    'vbr': vbr,
                })

        self._sort_formats(formats)

        return {
            'id': '%s' % video_id,
            'display_id': display_id,
            'title': unescapeHTML(clip_info['clip_title']),
            'description': unescapeHTML(clip_info.get('caption')),
            'thumbnail': clip_info.get('video_still_url'),
            'duration': int_or_none(clip_info.get('duration')),
            'formats': formats,
        }
