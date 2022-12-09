import json

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    str_or_none,
    strip_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class PinterestBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'''(?x)
        https?://(?:[^/]+\.)?pinterest\.(?:
            com|fr|de|ch|jp|cl|ca|it|co\.uk|nz|ru|com\.au|at|pt|co\.kr|es|com\.mx|
            dk|ph|th|com\.uy|co|nl|info|kr|ie|vn|com\.vn|ec|mx|in|pe|co\.at|hu|
            co\.in|co\.nz|id|com\.ec|com\.py|tw|be|uk|com\.bo|com\.pe)'''

    def _call_api(self, resource, video_id, options):
        return self._download_json(
            'https://www.pinterest.com/resource/%sResource/get/' % resource,
            video_id, 'Download %s JSON metadata' % resource, query={
                'data': json.dumps({'options': options})
            })['resource_response']

    def _extract_video(self, data, extract_formats=True):
        video_id = data['id']
        thumbnails = []
        images = data.get('images')
        if isinstance(images, dict):
            for thumbnail_id, thumbnail in images.items():
                if not isinstance(thumbnail, dict):
                    continue
                thumbnail_url = url_or_none(thumbnail.get('url'))
                if not thumbnail_url:
                    continue
                thumbnails.append({
                    'url': thumbnail_url,
                    'width': int_or_none(thumbnail.get('width')),
                    'height': int_or_none(thumbnail.get('height')),
                })

        info = {
            'title': strip_or_none(traverse_obj(data, 'title', 'grid_title', default='')),
            'description': traverse_obj(data, 'seo_description', 'description'),
            'timestamp': unified_timestamp(data.get('created_at')),
            'thumbnails': thumbnails,
            'uploader': traverse_obj(data, ('closeup_attribution', 'full_name')),
            'uploader_id': str_or_none(traverse_obj(data, ('closeup_attribution', 'id'))),
            'repost_count': int_or_none(data.get('repin_count')),
            'comment_count': int_or_none(data.get('comment_count')),
            'categories': traverse_obj(data, ('pin_join', 'visual_annotation'), expected_type=list),
            'tags': traverse_obj(data, 'hashtags', expected_type=list),
        }

        urls = []
        formats = []
        duration = None
        domain = data.get('domain', '')
        if domain.lower() != 'uploaded by user' and traverse_obj(data, ('embed', 'src')):
            if not info['title']:
                info['title'] = None
            return {
                '_type': 'url_transparent',
                'url': data['embed']['src'],
                **info,
            }

        elif extract_formats:
            video_list = traverse_obj(
                data, ('videos', 'video_list'),
                ('story_pin_data', 'pages', ..., 'blocks', ..., 'video', 'video_list'),
                expected_type=dict, get_all=False, default={})
            for format_id, format_dict in video_list.items():
                if not isinstance(format_dict, dict):
                    continue
                format_url = url_or_none(format_dict.get('url'))
                if not format_url or format_url in urls:
                    continue
                urls.append(format_url)
                duration = float_or_none(format_dict.get('duration'), scale=1000)
                ext = determine_ext(format_url)
                if 'hls' in format_id.lower() or ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                        m3u8_id=format_id, fatal=False))
                else:
                    formats.append({
                        'url': format_url,
                        'format_id': format_id,
                        'width': int_or_none(format_dict.get('width')),
                        'height': int_or_none(format_dict.get('height')),
                        'duration': duration,
                    })

        return {
            'id': video_id,
            'formats': formats,
            'duration': duration,
            'webpage_url': f'https://www.pinterest.com/pin/{video_id}/',
            'extractor_key': PinterestIE.ie_key(),
            'extractor': PinterestIE.IE_NAME,
            **info,
        }


class PinterestIE(PinterestBaseIE):
    _VALID_URL = r'%s/pin/(?P<id>\d+)' % PinterestBaseIE._VALID_URL_BASE
    _TESTS = [{
        # formats found in data['videos']
        'url': 'https://www.pinterest.com/pin/664281013778109217/',
        'md5': '6550c2af85d6d9f3fe3b88954d1577fc',
        'info_dict': {
            'id': '664281013778109217',
            'ext': 'mp4',
            'title': 'Origami',
            'description': 'md5:e29801cab7d741ea8c741bc50c8d00ab',
            'duration': 57.7,
            'timestamp': 1593073622,
            'upload_date': '20200625',
            'repost_count': int,
            'comment_count': int,
            'categories': list,
            'tags': list,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
        },
    }, {
        # formats found in data['story_pin_data']
        'url': 'https://www.pinterest.com/pin/1084663891475263837/',
        'md5': '069ac19919ab9e1e13fa60de46290b03',
        'info_dict': {
            'id': '1084663891475263837',
            'ext': 'mp4',
            'title': 'Gadget, Cool products, Amazon product, technology, Kitchen gadgets',
            'description': 'md5:d0a4b6ae996ff0c6eed83bc869598d13',
            'uploader': 'CoolCrazyGadgets',
            'uploader_id': '1084664028912989237',
            'upload_date': '20211003',
            'timestamp': 1633246654.0,
            'duration': 14.9,
            'comment_count': int,
            'repost_count': int,
            'categories': 'count:9',
            'tags': list,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
        },
    }, {
        # vimeo.com embed
        'url': 'https://www.pinterest.ca/pin/441282463481903715/',
        'info_dict': {
            'id': '111691128',
            'ext': 'mp4',
            'title': 'Tonite Let\'s All Make Love In London (1967)',
            'description': 'md5:8190f37b3926807809ec57ec21aa77b2',
            'uploader': 'Vimeo',
            'uploader_id': '473792960706651251',
            'upload_date': '20180120',
            'timestamp': 1516409040,
            'duration': 3404,
            'comment_count': int,
            'repost_count': int,
            'categories': 'count:9',
            'tags': [],
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
            'uploader_url': 'https://vimeo.com/willardandrade',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://co.pinterest.com/pin/824721750502199491/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(
            'Pin', video_id, {
                'field_set_key': 'unauth_react_main_pin',
                'id': video_id,
            })['data']
        return self._extract_video(data)


class PinterestCollectionIE(PinterestBaseIE):
    _VALID_URL = r'%s/(?P<username>[^/]+)/(?P<id>[^/?#&]+)' % PinterestBaseIE._VALID_URL_BASE
    _TESTS = [{
        'url': 'https://www.pinterest.ca/mashal0407/cool-diys/',
        'info_dict': {
            'id': '585890301462791043',
            'title': 'cool diys',
        },
        'playlist_count': 8,
    }, {
        'url': 'https://www.pinterest.ca/fudohub/videos/',
        'info_dict': {
            'id': '682858430939307450',
            'title': 'VIDEOS',
        },
        'playlist_mincount': 365,
        'skip': 'Test with extract_formats=False',
    }]

    @classmethod
    def suitable(cls, url):
        return False if PinterestIE.suitable(url) else super(
            PinterestCollectionIE, cls).suitable(url)

    def _real_extract(self, url):
        username, slug = self._match_valid_url(url).groups()
        board = self._call_api(
            'Board', slug, {
                'slug': slug,
                'username': username
            })['data']
        board_id = board['id']
        options = {
            'board_id': board_id,
            'page_size': 250,
        }
        bookmark = None
        entries = []
        while True:
            if bookmark:
                options['bookmarks'] = [bookmark]
            board_feed = self._call_api('BoardFeed', board_id, options)
            for item in (board_feed.get('data') or []):
                if not isinstance(item, dict) or item.get('type') != 'pin':
                    continue
                video_id = item.get('id')
                if video_id:
                    # Some pins may not be available anonymously via pin URL
                    # video = self._extract_video(item, extract_formats=False)
                    # video.update({
                    #     '_type': 'url_transparent',
                    #     'url': 'https://www.pinterest.com/pin/%s/' % video_id,
                    # })
                    # entries.append(video)
                    entries.append(self._extract_video(item))
            bookmark = board_feed.get('bookmark')
            if not bookmark:
                break
        return self.playlist_result(
            entries, playlist_id=board_id, playlist_title=board.get('name'))
