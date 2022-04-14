import re

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_urlencode,
    compat_urlparse,
)
from ..utils import (
    clean_html,
    parse_duration,
    str_to_int,
    unified_strdate,
)


class CamdemyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?camdemy\.com/media/(?P<id>\d+)'
    _TESTS = [{
        # single file
        'url': 'http://www.camdemy.com/media/5181/',
        'md5': '5a5562b6a98b37873119102e052e311b',
        'info_dict': {
            'id': '5181',
            'ext': 'mp4',
            'title': 'Ch1-1 Introduction, Signals (02-23-2012)',
            'thumbnail': r're:^https?://.*\.jpg$',
            'creator': 'ss11spring',
            'duration': 1591,
            'upload_date': '20130114',
            'view_count': int,
        }
    }, {
        # With non-empty description
        # webpage returns "No permission or not login"
        'url': 'http://www.camdemy.com/media/13885',
        'md5': '4576a3bb2581f86c61044822adbd1249',
        'info_dict': {
            'id': '13885',
            'ext': 'mp4',
            'title': 'EverCam + Camdemy QuickStart',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:2a9f989c2b153a2342acee579c6e7db6',
            'creator': 'evercam',
            'duration': 318,
        }
    }, {
        # External source (YouTube)
        'url': 'http://www.camdemy.com/media/14842',
        'info_dict': {
            'id': '2vsYQzNIsJo',
            'ext': 'mp4',
            'title': 'Excel 2013 Tutorial - How to add Password Protection',
            'description': 'Excel 2013 Tutorial for Beginners - How to add Password Protection',
            'upload_date': '20130211',
            'uploader': 'Hun Kim',
            'uploader_id': 'hunkimtutorials',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        src_from = self._html_search_regex(
            r"class=['\"]srcFrom['\"][^>]*>Sources?(?:\s+from)?\s*:\s*<a[^>]+(?:href|title)=(['\"])(?P<url>(?:(?!\1).)+)\1",
            webpage, 'external source', default=None, group='url')
        if src_from:
            return self.url_result(src_from)

        oembed_obj = self._download_json(
            'http://www.camdemy.com/oembed/?format=json&url=' + url, video_id)

        title = oembed_obj['title']
        thumb_url = oembed_obj['thumbnail_url']
        video_folder = compat_urlparse.urljoin(thumb_url, 'video/')
        file_list_doc = self._download_xml(
            compat_urlparse.urljoin(video_folder, 'fileList.xml'),
            video_id, 'Downloading filelist XML')
        file_name = file_list_doc.find('./video/item/fileName').text
        video_url = compat_urlparse.urljoin(video_folder, file_name)

        # Some URLs return "No permission or not login" in a webpage despite being
        # freely available via oembed JSON URL (e.g. http://www.camdemy.com/media/13885)
        upload_date = unified_strdate(self._search_regex(
            r'>published on ([^<]+)<', webpage,
            'upload date', default=None))
        view_count = str_to_int(self._search_regex(
            r'role=["\']viewCnt["\'][^>]*>([\d,.]+) views',
            webpage, 'view count', default=None))
        description = self._html_search_meta(
            'description', webpage, default=None) or clean_html(
            oembed_obj.get('description'))

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'thumbnail': thumb_url,
            'description': description,
            'creator': oembed_obj.get('author_name'),
            'duration': parse_duration(oembed_obj.get('duration')),
            'upload_date': upload_date,
            'view_count': view_count,
        }


class CamdemyFolderIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?camdemy\.com/folder/(?P<id>\d+)'
    _TESTS = [{
        # links with trailing slash
        'url': 'http://www.camdemy.com/folder/450',
        'info_dict': {
            'id': '450',
            'title': '信號與系統 2012 & 2011 (Signals and Systems)',
        },
        'playlist_mincount': 145
    }, {
        # links without trailing slash
        # and multi-page
        'url': 'http://www.camdemy.com/folder/853',
        'info_dict': {
            'id': '853',
            'title': '科學計算 - 使用 Matlab'
        },
        'playlist_mincount': 20
    }, {
        # with displayMode parameter. For testing the codes to add parameters
        'url': 'http://www.camdemy.com/folder/853/?displayMode=defaultOrderByOrg',
        'info_dict': {
            'id': '853',
            'title': '科學計算 - 使用 Matlab'
        },
        'playlist_mincount': 20
    }]

    def _real_extract(self, url):
        folder_id = self._match_id(url)

        # Add displayMode=list so that all links are displayed in a single page
        parsed_url = list(compat_urlparse.urlparse(url))
        query = dict(compat_urlparse.parse_qsl(parsed_url[4]))
        query.update({'displayMode': 'list'})
        parsed_url[4] = compat_urllib_parse_urlencode(query)
        final_url = compat_urlparse.urlunparse(parsed_url)

        page = self._download_webpage(final_url, folder_id)
        matches = re.findall(r"href='(/media/\d+/?)'", page)

        entries = [self.url_result('http://www.camdemy.com' + media_path)
                   for media_path in matches]

        folder_title = self._html_search_meta('keywords', page)

        return self.playlist_result(entries, folder_id, folder_title)
