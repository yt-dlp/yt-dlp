import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    int_or_none,
    parse_duration,
    parse_resolution,
    str_or_none,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    traverse_obj,
)


class ZapiksIE(InfoExtractor):
    _VALID_URL = [
        r'https?://(?:www\.)?zapiks\.(?:com|fr)/(?P<id>[\w-]+)\.html',
        r'https?://(?:www\.)?zapiks\.fr/index\.php\?(?:[^#]+&)?media_id=(?P<id>\d+)',
    ]
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=["\'](?P<url>(?:https?:)?//(?:www\.)?zapiks\.fr/index\.php\?(?:[^#"\']+&(?:amp;)?)?media_id=\d+)']
    _TESTS = [{
        'url': 'https://www.zapiks.fr/ep2s3-bon-appetit-eh-be-viva.html',
        'md5': 'aeb3c473b2d564b2d46d664d28d5f050',
        'info_dict': {
            'id': '80798',
            'ext': 'mp4',
            'title': 'EP2S3 - Bon Appétit - Eh bé viva les pyrénées con!',
            'description': 'md5:db07a553c1550e2905bceafa923000fd',
            'display_id': 'ep2s3-bon-appetit-eh-be-viva',
            'duration': 528,
            'tags': 'count:5',
            'thumbnail': r're:https?://zpks\.com/.+',
            'timestamp': 1359044972,
            'upload_date': '20130124',
            'uploader': 'BonAppetit',
            'uploader_id': 'bonappetit',
            'view_count': int,
        },
    }, {
        'url': 'https://www.zapiks.com/ep3s5-bon-appetit-baqueira-m-1.html',
        'md5': '196fe42901639d868956b1dcaa48de15',
        'info_dict': {
            'id': '118046',
            'ext': 'mp4',
            'title': 'EP3S5 - Bon Appétit - Baqueira Mi Corazon !',
            'display_id': 'ep3s5-bon-appetit-baqueira-m-1',
            'duration': 642,
            'tags': 'count:8',
            'thumbnail': r're:https?://zpks\.com/.+',
            'timestamp': 1424370543,
            'upload_date': '20150219',
            'uploader': 'BonAppetit',
            'uploader_id': 'bonappetit',
            'view_count': int,
        },
    }, {
        'url': 'https://www.zapiks.fr/index.php?action=playerIframe&media_id=164049',
        'md5': 'fb81a7c9b7b84c00ba111028aee593b8',
        'info_dict': {
            'id': '164049',
            'ext': 'mp4',
            'title': 'Courchevel Hiver 2025/2026',
            'display_id': 'courchevel-hiver-2025-2026',
            'duration': 38,
            'tags': 'count:1',
            'thumbnail': r're:https?://zpks\.com/.+',
            'timestamp': 1769019147,
            'upload_date': '20260121',
            'uploader': 'jamrek',
            'uploader_id': 'jamrek',
            'view_count': int,
        },
    }, {
        # https://www.youtube.com/watch?v=UBAABvegu2M
        'url': 'https://www.zapiks.com/live-fwt18-vallnord-arcalis-.html',
        'info_dict': {
            'id': 'UBAABvegu2M',
            'ext': 'mp4',
            'title': 'Replay Live - FWT18 Vallnord-Arcalís Andorra - Freeride World Tour 2018',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Sports'],
            'channel': 'FIS Freeride World Tour by Peak Performance',
            'channel_follower_count': int,
            'channel_id': 'UCraJ3GNFfw6LXFuCV6McByg',
            'channel_url': 'https://www.youtube.com/channel/UCraJ3GNFfw6LXFuCV6McByg',
            'comment_count': int,
            'description': 'md5:2d9fefef758d5ad0d5a987d46aff7572',
            'duration': 11328,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'was_live',
            'media_type': 'livestream',
            'playable_in_embed': True,
            'release_date': '20180306',
            'release_timestamp': 1520321809,
            'tags': 'count:27',
            'thumbnail': r're:https?://i\.ytimg\.com/.+',
            'timestamp': 1520336958,
            'upload_date': '20180306',
            'uploader': 'FIS Freeride World Tour by Peak Performance',
            'uploader_id': '@FISFreerideWorldTour',
            'uploader_url': 'https://www.youtube.com/@FISFreerideWorldTour',
            'view_count': int,
        },
        'add_ie': ['Youtube'],
    }, {
        # https://vimeo.com/235746460
        'url': 'https://www.zapiks.fr/waking-dream-2017-full-movie.html',
        'info_dict': {
            'id': '235746460',
            'ext': 'mp4',
            'title': '"WAKING DREAM" (2017) Full Movie by Sam Favret & Julien Herry',
            'duration': 1649,
            'thumbnail': r're:https?://i\.vimeocdn\.com/video/.+',
            'uploader': 'Favret Sam',
            'uploader_id': 'samfavret',
            'uploader_url': 'https://vimeo.com/samfavret',
        },
        'add_ie': ['Vimeo'],
        'expected_warnings': ['Failed to parse XML: not well-formed'],
    }]
    _WEBPAGE_TESTS = [{
        # https://www.zapiks.fr/ep3s5-bon-appetit-baqueira-m-1.html
        # https://www.zapiks.fr/index.php?action=playerIframe&media_id=118046
        'url': 'https://www.skipass.com/news/116090-bon-appetit-s5ep3-baqueira-mi-cor.html',
        'md5': '196fe42901639d868956b1dcaa48de15',
        'info_dict': {
            'id': '118046',
            'ext': 'mp4',
            'title': 'EP3S5 - Bon Appétit - Baqueira Mi Corazon !',
            'description': 'md5:b45295c3897c4c01d7c04e8484c26aaf',
            'display_id': 'ep3s5-bon-appetit-baqueira-m-1',
            'duration': 642,
            'tags': 'count:8',
            'thumbnail': r're:https?://zpks\.com/.+',
            'timestamp': 1424370543,
            'upload_date': '20150219',
            'uploader': 'BonAppetit',
            'uploader_id': 'bonappetit',
            'view_count': int,
        },
    }]
    _UPLOADER_ID_RE = re.compile(r'/pro(?:fil)?/(?P<id>[^/?#]+)/?')

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        if embed_url := traverse_obj(webpage, (
            {find_element(cls='embed-container')}, {find_element(tag='iframe', html=True)},
            {extract_attributes}, 'src', {self._proto_relative_url}, {url_or_none},
        )):
            if not self.suitable(embed_url):
                return self.url_result(embed_url)

        video_responsive = traverse_obj(webpage, (
            {find_element(cls='video-responsive', html=True)}, {extract_attributes}, {dict}))
        data_media_url = traverse_obj(video_responsive, ('data-media-url', {url_or_none}))
        if data_media_url and urllib.parse.urlparse(url).path == '/index.php':
            return self.url_result(data_media_url, ZapiksIE)

        data_playlist = traverse_obj(video_responsive, ('data-playlist', {json.loads}, ..., any))
        formats = []
        for source in traverse_obj(data_playlist, (
            'sources', lambda _, v: url_or_none(v['file']),
        )):
            format_id = traverse_obj(source, ('label', {str_or_none}))
            formats.append({
                'format_id': format_id,
                'url': source['file'],
                **parse_resolution(format_id),
            })

        return {
            'display_id': display_id,
            'duration': parse_duration(self._html_search_meta('duration', webpage, default=None)),
            'formats': formats,
            'timestamp': unified_timestamp(self._html_search_meta('uploadDate', webpage, default=None)),
            **traverse_obj(webpage, {
                'description': ({find_element(cls='description-text')}, {clean_html}, filter),
                'tags': (
                    {find_elements(cls='bs-label', html=True)},
                    ..., {extract_attributes}, 'title', {clean_html}, filter),
                'view_count': (
                    {find_element(cls='video-content-view-counter')}, {clean_html},
                    {lambda x: re.sub(r'(?:vues|views|\s+)', '', x)}, {int_or_none}),
            }),
            **traverse_obj(webpage, ({find_element(cls='video-content-user-link', html=True)}, {
                'uploader': ({clean_html}, filter),
                'uploader_id': ({extract_attributes}, 'href', {self._UPLOADER_ID_RE.fullmatch}, 'id'),
            })),
            **traverse_obj(data_playlist, {
                'id': ('mediaid', {str_or_none}),
                'title': ('title', {clean_html}, filter),
                'thumbnail': ('image', {url_or_none}),
            }),
        }
