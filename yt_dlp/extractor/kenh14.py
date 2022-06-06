from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_attribute,
    get_elements_by_attribute,
    get_elements_html_by_attribute,
    int_or_none,
    parse_duration,
    parse_iso8601,
    remove_end,
    remove_start,
)


class Kenh14IE(InfoExtractor):
    IE_NAME = 'kenh14'
    _VALID_URL = r'https?://video.kenh14\.vn/(?:playlist/)?[^/]*-(?P<id>[0-9]+)\.chn'
    _TESTS = [{
        'url': 'https://video.kenh14.vn/video-mo-hop-iphone-14-pro-max-nguon-unbox-therapy-316173.chn',
        'note': 'Video URL',
        'md5': '525b9c4646a7aed819697cfd17dd25a9',
        'info_dict': {
            'id': '316173',
            'ext': 'mp4',
            'title': 'Video mở hộp iPhone 14 Pro Max (Nguồn: Unbox Therapy)',
            'description': 'Video mở hộp iPhone 14 Pro Max',
            'thumbnail': r're:^https?://.*\.jpg$',
            'thumbnails': list,
            'formats': list,
            'tags': ["iPhone 14 Pro", "iPhone 14 Pro Max", "iPhone 14"],
            'display_id': 'video-mo-hop-iphone-14-pro-max-nguon-unbox-therapy',
            'uploader': 'Unbox Therapy',
            'display_id': 'video-mo-hop-iphone-14-pro-max-nguon-unbox-therapy',
            'upload_date': '20220517',
            'view_count': int,
            'release_date': '20220518',
            'modified_date': '20220518',
            'duration': 722.86,
            'modified_timestamp': 1652848039,
            'release_timestamp': 1652848039,
            'timestamp': int,
        }
    }, {
        'url': 'https://video.kenh14.vn/playlist/tran-tinh-naked-love-mua-2-71.chn',
        'note': 'Playlist URL',
        'info_dict': {
            'id': '316972',
            'ext': 'mp4',
            'description': 'md5:4212062bf4c447efbad5f54e6ab8d132',
            'thumbnail': 'https://kenh14cdn.com/203336854389633024/2022/6/5/1024-1281-1654416995812779954762.jpg',

            'modified_timestamp': 1654376400,
            'duration': 4602.09,
            'timestamp': 1654398990,
            'release_date': '20220604',
            'tags': ['Sơn Soho', 'Linh Keen', 'Trần Tình (Naked Love) mùa 2', 'Naked Love', 'trần tình', 'ShowHot'],
            'release_timestamp': 1654376400,
            'view_count': int,
            'modified_date': '20220604',
            'title': '[4x5] FINAL -  Naked Love EP4 - Moi quan he tieu cuc',
            'upload_date': '20220605',
            'display_id': 'md5:a27d1fbdeafeb740050de0e697c8e02e',
        }
    }, {
        'url': 'https://video.kenh14.vn/video-316173.chn',
        'note': 'javascript-based redirect; set via <body onload="window.location.href=URL">',
        'md5': '525b9c4646a7aed819697cfd17dd25a9',
        'info_dict': {
            'id': '316173',
            'ext': 'mp4',
            'title': 'Video mở hộp iPhone 14 Pro Max (Nguồn: Unbox Therapy)',
            'description': 'Video mở hộp iPhone 14 Pro Max',
            'thumbnail': r're:^https?://.*\.jpg$',
            'thumbnails': list,
            'formats': list,
            'tags': ["iPhone 14 Pro", "iPhone 14 Pro Max", "iPhone 14"],
            'display_id': 'video-mo-hop-iphone-14-pro-max-nguon-unbox-therapy',
            'uploader': 'Unbox Therapy',
            'display_id': 'video-mo-hop-iphone-14-pro-max-nguon-unbox-therapy',
            'upload_date': '20220517',
            'view_count': int,
            'release_date': '20220518',
            'modified_date': '20220518',
            'duration': 722.86,
            'modified_timestamp': 1652848039,
            'release_timestamp': 1652848039,
            'timestamp': int,
        }
    }, {
        'url': 'https://video.kenh14.vn/0-316173.chn',
        'note': 'HTTP 301 redirect to canonical URL',
        'md5': '525b9c4646a7aed819697cfd17dd25a9',
        'info_dict': {
            'id': '316173',
            'ext': 'mp4',
            'title': 'Video mở hộp iPhone 14 Pro Max (Nguồn: Unbox Therapy)',
            'description': 'Video mở hộp iPhone 14 Pro Max',
            'thumbnail': r're:^https?://.*\.jpg$',
            'thumbnails': list,
            'formats': list,
            'tags': ["iPhone 14 Pro", "iPhone 14 Pro Max", "iPhone 14"],
            'display_id': 'video-mo-hop-iphone-14-pro-max-nguon-unbox-therapy',
            'uploader': 'Unbox Therapy',
            'display_id': 'video-mo-hop-iphone-14-pro-max-nguon-unbox-therapy',
            'upload_date': '20220517',
            'view_count': int,
            'release_date': '20220518',
            'modified_date': '20220518',
            'duration': 722.86,
            'modified_timestamp': 1652848039,
            'release_timestamp': 1652848039,
            'timestamp': int,
        }
    }, {
        'url': 'https://video.kenh14.vn/playlist/0-71.chn',
        'note': 'HTTP 301 redirect to canonical playlist URL',
        'info_dict': {
            'id': '316972',
            'ext': 'mp4',
            'description': 'md5:4212062bf4c447efbad5f54e6ab8d132',
            'thumbnail': 'https://kenh14cdn.com/203336854389633024/2022/6/5/1024-1281-1654416995812779954762.jpg',

            'modified_timestamp': 1654376400,
            'duration': 4602.09,
            'timestamp': 1654398990,
            'release_date': '20220604',
            'tags': ['Sơn Soho', 'Linh Keen', 'Trần Tình (Naked Love) mùa 2', 'Naked Love', 'trần tình', 'ShowHot'],
            'release_timestamp': 1654376400,
            'view_count': int,
            'modified_date': '20220604',
            'title': '[4x5] FINAL -  Naked Love EP4 - Moi quan he tieu cuc',
            'upload_date': '20220605',
            'display_id': 'md5:a27d1fbdeafeb740050de0e697c8e02e',
        }
    }, {
        'url': 'https://video.kenh14.vn/playlist/tran-tinh-naked-love-mua-2-71.chn',
        'note': 'Playlist URL with --flat-playlist',
        'info_dict': {
            'id': '316972',
            'ext': 'mp4',
            'description': 'md5:4212062bf4c447efbad5f54e6ab8d132',
            'thumbnail': 'https://videothumbs.mediacdn.vn/kenh14/203336854389633024/2022/6/5/4x5-final-naked-love-ep4-moi-quan-he-tieu-cuc-16544166609501118413296.jpg',
            'tags': ['Sơn Soho', 'Linh Keen', 'Trần Tình (Naked Love) mùa 2', 'Naked Love', 'Trần tình', 'ShowHot'],
            'title': 'Naked Love - Trần Tình tập 4: Sơn Soho, Linh Keen cùng câu chuyện bước ra khỏi mối quan hệ tiêu cực và yêu bản thân mình',
            'display_id': 'md5:db3e1b63976a664b3576f3ef68a17c9a',
        },
        'params': {'extract_flat': 'in_playlist'}
    }]

    def _try_get_redirect_url(self, webpage):
        # javascript-based redirect; set via <body onload="window.location.href=URL">
        url = self._search_regex(r"onload=\"window.location.href='([^']*)'", webpage, 'redirect url', default=None, fatal=False)
        if url:
            return 'https://video.kenh14.vn' + url

    def _extract_formats_wrapper(self, video_id, direct_url):
        formats = [{'url': f'https://{direct_url}'}]
        formats.extend(self._extract_m3u8_formats(f'https://{direct_url}/master.m3u8', video_id))
        self._sort_formats(formats)
        return formats

    def _extract_video(self, webpage, page_url, fallback_url=''):
        video_id = self._match_id(page_url)
        if webpage is None:
            webpage, page_url = self._download_webpage_wrapper(page_url, fatal=False)
        attrs = extract_attributes(self._extract_video_div(webpage))
        direct_url = attrs.get('data-vid', fallback_url)
        filename = remove_start(direct_url, 'kenh14cdn.com/')
        inline_metadata = self._parse_json(attrs.get('data-htmlcode', '{}'), video_id, fatal=False)
        display_id = self._get_display_id(page_url)

        formats = self._extract_formats_wrapper(video_id, direct_url)
        result = {
            'id': video_id,
            'title': (
                clean_html(self._og_search_title(webpage))
                or inline_metadata.get('video_title')
                or self._extract_title(webpage)),
            'formats': formats,
            'duration': parse_duration(inline_metadata.get('video_duration')),
            'description': (
                clean_html(self._og_search_description(webpage))
                or clean_html(inline_metadata.get('video_description'))
                or self._extract_description(webpage)),
            'thumbnail': (
                self._og_search_thumbnail(webpage)
                or inline_metadata.get('video_thumb')
                or attrs.get('data-thumb')),
            'release_timestamp': parse_iso8601(self._html_search_meta('article:published_time', webpage)),
            'modified_timestamp': parse_iso8601(self._html_search_meta('article:modified_time', webpage)),
            'tags': self._extract_page_tags(webpage),
            'webpage_url': page_url,
            'display_id': display_id,
        }
        result['timestamp'] = result.get('release_timestamp') or result.get('modified_timestamp')

        metadata = self._download_json(f'https://api.kinghub.vn/video/api/v1/detailVideoByGet?FileName={filename}', video_id) or {}

        return {
            # Note: API result contains 'videoID' but it's a different number that doesn't seem public-facing.
            'id': video_id,
            'title': metadata.get('title') or result.get('title'),
            'formats': formats,
            'duration': parse_duration(metadata.get('duration')) or result.get('duration'),
            'timestamp': (
                parse_iso8601(metadata.get('uploadtime'), delimiter=' ')
                or result.get('timestamp')),
            'release_timestamp': result.get('release_timestamp'),
            'modified_timestamp': result.get('modified_timestamp'),
            'thumbnail': metadata.get('thumbnail') or result.get('thumbnail'),
            'description': result.get('description'),
            'uploader': metadata.get('author'),
            'view_count': int_or_none(metadata.get('views')),
            'tags': result.get('tags'),
            'webpage_url': page_url,
            'display_id': display_id,
        }

    def _extract_playlist(self, webpage, url):
        playlist_id = self._match_id(url)
        display_id = self._get_display_id(url)

        def _extract_playlist_videos():
            for video_listitem in self._get_list_videos(webpage):
                attrs = extract_attributes(self._extract_video_div(video_listitem))
                direct_url = attrs.get('data-vid')
                if not direct_url:
                    self.report_warning(f'Could not find expected video in playlist {playlist_id}')
                    continue

                video_id = attrs.get('data-item-id')
                share_url = attrs.get('data-share')
                if not share_url:
                    share_url = f'https://video.kenh14.vn/video-{video_id}.chn'

                basename = remove_end(remove_start(direct_url, 'kenh14cdn.com/'), '.mp4')
                video_result = {
                    '_type': 'video',
                    'id': video_id,
                    'webpage_url': share_url,
                    'display_id': display_id,
                    'title': self._extract_title(video_listitem),
                    'description': self._extract_description(video_listitem),
                    'thumbnail': f'https://videothumbs.mediacdn.vn/kenh14/{basename}.jpg',
                    'tags': self._extract_tag_list(video_listitem),
                }

                if not self.get_param('extract_flat', False):
                    video_result.update(self._extract_video(None, share_url, direct_url))
                else:
                    video_result.update({'formats': self._extract_formats_wrapper(video_id, direct_url)})

                yield video_result

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'tags': self._extract_page_tags(webpage),
            'display_id': display_id,
            'entries': _extract_playlist_videos(),
        }
        pass

    def _get_list_videos(self, webpage):
        # get_elements_html_by_class('video-item', webpage) is NOT doing what I
        # expect; it's matching list-video-item for some reason
        return get_elements_html_by_attribute('class', 'video-item', webpage)

    def _extract_video_div(self, content):
        return get_element_html_by_attribute('type', 'VideoStream', content) or ''

    def _extract_title(self, elem):
        return clean_html(get_element_by_class('video-title', elem) or get_element_by_class('vdbw-title', elem))

    def _extract_description(self, elem):
        return clean_html(get_element_by_class('video-sapo', elem) or get_element_by_class('vdbw-sapo', elem))

    def _extract_tag_list(self, elem):
        in_class = list(get_elements_html_by_attribute('class', 'video-tag', elem))
        in_attr = list(get_elements_by_attribute('data', 'video-tag', elem))
        return list(filter(None, map(clean_html, in_class or in_attr)))

    def _extract_page_tags(self, webpage):
        tags = self._html_search_meta('article:tag', webpage) or ''
        return list(filter(None, map(lambda x: x.strip(), tags.split(','))))

    def _download_webpage_wrapper(self, url, fatal=True):
        video_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, video_id, fatal=fatal)
        redirect_url = self._try_get_redirect_url(webpage)
        new_urlh = urlh
        if redirect_url:
            # Page load relies on a javascript redirect
            webpage, new_urlh = self._download_webpage_handle(redirect_url, video_id, fatal=fatal)
        return webpage, (new_urlh or urlh).geturl()

    def _is_playlist(self, url):
        return self._search_regex(
            r'https?://video.kenh14\.vn/(?P<is_playlist>playlist/|)?.*\.chn',
            url, 'url type and display id', default=False, group=('is_playlist'), fatal=False)

    def _get_display_id(self, url):
        return self._search_regex(
            r'https?://video.kenh14\.vn/(?:playlist/|)?(?P<display_id>.*?)-?[0-9]+\.chn',
            url, 'url type and display id', group=('display_id'), fatal=False)

    def _real_extract(self, url):
        webpage, url = self._download_webpage_wrapper(url)

        is_playlist = self._is_playlist(url)
        self.write_debug('deduced page to be a ' + ('playlist' if is_playlist else 'video'))

        if is_playlist:
            return self._extract_playlist(webpage, url)
        else:
            return self._extract_video(webpage, url)
