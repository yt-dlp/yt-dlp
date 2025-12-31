import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    unescapeHTML,
    unified_timestamp,
    xpath_attr,
    xpath_element,
    xpath_text,
)


class SpringboardPlatformIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        cms\.springboardplatform\.com/
                        (?:
                            (?:previews|embed_iframe)/(?P<index>\d+)/video/(?P<id>\d+)|
                            xml_feeds_advanced/index/(?P<index_2>\d+)/rss3/(?P<id_2>\d+)
                        )
                    '''
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//cms\.springboardplatform\.com/embed_iframe/\d+/video/\d+.*?)\1']
    _TESTS = [{
        'url': 'http://cms.springboardplatform.com/previews/159/video/981017/0/0/1',
        'md5': '5c3cb7b5c55740d482561099e920f192',
        'info_dict': {
            'id': '981017',
            'ext': 'mp4',
            'title': 'Redman "BUD like YOU" "Usher Good Kisser" REMIX',
            'description': 'Redman "BUD like YOU" "Usher Good Kisser" REMIX',
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1409132328,
            'upload_date': '20140827',
            'duration': 193,
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'http://cms.springboardplatform.com/embed_iframe/159/video/981017/rab007/rapbasement.com/1/1',
        'only_matching': True,
    }, {
        'url': 'http://cms.springboardplatform.com/embed_iframe/20/video/1731611/ki055/kidzworld.com/10',
        'only_matching': True,
    }, {
        'url': 'http://cms.springboardplatform.com/xml_feeds_advanced/index/159/rss3/981017/0/0/1/',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.kidzworld.com/article/30935-trolls-the-beat-goes-on-interview-skylar-astin-and-amanda-leighton',
        'info_dict': {
            'id': '1731611',
            'ext': 'mp4',
            'title': 'Official Trailer | TROLLS: THE BEAT GOES ON!',
        },
        'skip': 'Invalid URL',
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('id_2')
        index = mobj.group('index') or mobj.group('index_2')

        video = self._download_xml(
            f'http://cms.springboardplatform.com/xml_feeds_advanced/index/{index}/rss3/{video_id}', video_id)

        item = xpath_element(video, './/item', 'item', fatal=True)

        content = xpath_element(
            item, './{http://search.yahoo.com/mrss/}content', 'content',
            fatal=True)
        title = unescapeHTML(xpath_text(item, './title', 'title', fatal=True))

        video_url = content.attrib['url']

        if 'error_video.mp4' in video_url:
            raise ExtractorError(
                f'Video {video_id} no longer exists', expected=True)

        duration = int_or_none(content.get('duration'))
        tbr = int_or_none(content.get('bitrate'))
        filesize = int_or_none(content.get('fileSize'))
        width = int_or_none(content.get('width'))
        height = int_or_none(content.get('height'))

        description = unescapeHTML(xpath_text(
            item, './description', 'description'))
        thumbnail = xpath_attr(
            item, './{http://search.yahoo.com/mrss/}thumbnail', 'url',
            'thumbnail')

        timestamp = unified_timestamp(xpath_text(
            item, './{http://cms.springboardplatform.com/namespaces.html}created',
            'timestamp'))

        formats = [{
            'url': video_url,
            'format_id': 'http',
            'tbr': tbr,
            'filesize': filesize,
            'width': width,
            'height': height,
        }]

        m3u8_format = formats[0].copy()
        m3u8_format.update({
            'url': re.sub(r'(https?://)cdn\.', r'\1hls.', video_url) + '.m3u8',
            'ext': 'mp4',
            'format_id': 'hls',
            'protocol': 'm3u8_native',
        })
        formats.append(m3u8_format)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'duration': duration,
            'formats': formats,
        }
