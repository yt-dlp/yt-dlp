# coding: utf-8
from __future__ import unicode_literals
from .common import InfoExtractor
from ..compat import compat_urllib_parse_urlparse
from ..utils import (
    sanitized_Request,
    urlencode_postdata,
)


class CoverApiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?coverapi\.store/embed/(?P<id>[0-9a-zA-Z]+)(?:/)?'
    _TESTS = [{
        'url': 'https://coverapi.store/embed/tt3915174/',
        'md5': '0ed4bc62f04c48ab3f6760179ec87f27',
        'info_dict': {
            'id': 'tt3915174',
            'title': 'Ο Παπουτσωμένος Γάτος: Η τελευταία επιθυμία / Puss in Boots: The Last Wish (2022)',
            'ext': 'mp4',
            'filename': 'test_CoverApi_tt3915174.mp4'
        }
    }, {
        'url': 'https://coverapi.store/embed/tt23177868',
        'md5': '3040b5715b6d50103e4b4dc71e8901b4',
        'info_dict': {
            'id': 'tt23177868',
            'title': 'GR Audio',
            'ext': 'mp4',
            'filename': 'test_CoverApi_1_tt23177868.mp4'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        html = self._download_webpage(url, video_id)
        news_id = self._search_regex(r"news_id: '(\d+)'", html, 'news_id')
        parsed_url = compat_urllib_parse_urlparse(url)
        base_url = parsed_url.scheme + '://' + parsed_url.netloc
        controller_path = self._search_regex(r"url:\s*'([^']*)'", html, 'controller_path')
        controller_url = base_url + controller_path
        controller_data = urlencode_postdata({'mod': 'players', 'news_id': news_id})
        controller_request = sanitized_Request(controller_url, controller_data)
        controller_request.add_header('Content-type', 'application/x-www-form-urlencoded, charset=UTF-8')
        controller_response = self._download_json(controller_request, video_id)
        html5 = controller_response.get('html5')
        file_url = self._search_regex(r'file:"(.*?)"', html5, 'url')
        if "playlists" in file_url:
            playlist_path = file_url
            playlist_url = base_url + playlist_path
            playlist_request = sanitized_Request(playlist_url)
            playlist_response = self._download_json(playlist_request, video_id)
            playlist = playlist_response.get('playlist', [])
            video_url = ''
            video_title = ''
            for element in playlist:
                if 'audio' in element.get('comment').lower():
                    video_url = element.get('file')
                    video_title = element.get('comment')
                    break
                elif 'subtitles' in element.get('comment').lower():
                    video_url = element.get('file')
                    video_title = element.get('comment')
                    break
            if video_url == '' and playlist:
                video_url = playlist[0].get('file')
            return {
                'id': video_id,
                'url': video_url,
                'title': video_title,
                'ext': 'mp4',
                'filename': 'test_CoverApi_1_tt23177868.mp4'
            }
        else:
            video_title = self._search_regex(r'title:\'(.*?)\'', html5, 'title')
            return {
                'id': video_id,
                'url': file_url,
                'title': video_title,
                'ext': 'mp4',
                'filename': 'test_CoverApi_tt3915174.mp4'
            }
