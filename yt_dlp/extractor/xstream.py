import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    xpath_with_ns,
    xpath_text,
    find_xpath_attr,
)


class XstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    (?:
                        xstream:|
                        https?://frontend\.xstream\.(?:dk|net)/
                    )
                    (?P<partner_id>[^/]+)
                    (?:
                        :|
                        /feed/video/\?.*?\bid=
                    )
                    (?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'http://frontend.xstream.dk/btno/feed/video/?platform=web&id=86588',
        'md5': 'd7d17e3337dc80de6d3a540aefbe441b',
        'info_dict': {
            'id': '86588',
            'ext': 'mov',
            'title': 'Otto Wollertsen',
            'description': 'Vestlendingen Otto Fredrik Wollertsen',
            'timestamp': 1430473209,
            'upload_date': '20150501',
        },
    }, {
        'url': 'http://frontend.xstream.dk/ap/feed/video/?platform=web&id=21039',
        'only_matching': True,
    }]

    def _extract_video_info(self, partner_id, video_id):
        data = self._download_xml(
            'http://frontend.xstream.dk/%s/feed/video/?platform=web&id=%s'
            % (partner_id, video_id),
            video_id)

        NS_MAP = {
            'atom': 'http://www.w3.org/2005/Atom',
            'xt': 'http://xstream.dk/',
            'media': 'http://search.yahoo.com/mrss/',
        }

        entry = data.find(xpath_with_ns('./atom:entry', NS_MAP))

        title = xpath_text(
            entry, xpath_with_ns('./atom:title', NS_MAP), 'title')
        description = xpath_text(
            entry, xpath_with_ns('./atom:summary', NS_MAP), 'description')
        timestamp = parse_iso8601(xpath_text(
            entry, xpath_with_ns('./atom:published', NS_MAP), 'upload date'))

        formats = []
        media_group = entry.find(xpath_with_ns('./media:group', NS_MAP))
        for media_content in media_group.findall(xpath_with_ns('./media:content', NS_MAP)):
            media_url = media_content.get('url')
            if not media_url:
                continue
            tbr = int_or_none(media_content.get('bitrate'))
            mobj = re.search(r'^(?P<url>rtmp://[^/]+/(?P<app>[^/]+))/(?P<playpath>.+)$', media_url)
            if mobj:
                formats.append({
                    'url': mobj.group('url'),
                    'play_path': 'mp4:%s' % mobj.group('playpath'),
                    'app': mobj.group('app'),
                    'ext': 'flv',
                    'tbr': tbr,
                    'format_id': 'rtmp-%d' % tbr,
                })
            else:
                formats.append({
                    'url': media_url,
                    'tbr': tbr,
                })
        self._sort_formats(formats)

        link = find_xpath_attr(
            entry, xpath_with_ns('./atom:link', NS_MAP), 'rel', 'original')
        if link is not None:
            formats.append({
                'url': link.get('href'),
                'format_id': link.get('rel'),
                'quality': 1,
            })

        thumbnails = [{
            'url': splash.get('url'),
            'width': int_or_none(splash.get('width')),
            'height': int_or_none(splash.get('height')),
        } for splash in media_group.findall(xpath_with_ns('./xt:splash', NS_MAP))]

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'formats': formats,
            'thumbnails': thumbnails,
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        partner_id = mobj.group('partner_id')
        video_id = mobj.group('id')

        return self._extract_video_info(partner_id, video_id)
