import re

from .common import InfoExtractor


class RbgTumIE(InfoExtractor):
    _VALID_URL = r'https://live\.rbg\.tum\.de/w/(?P<id>.+)'
    _TESTS = [{
        # Combined view
        'url': 'https://live.rbg.tum.de/w/cpp/22128',
        'md5': '53a5e7b3e07128e33bbf36687fe1c08f',
        'info_dict': {
            'id': 'cpp/22128',
            'ext': 'mp4',
            'title': 'Lecture: October 18. 2022',
            'series': 'Concepts of C++ programming (IN2377)',
        }
    }, {
        # Presentation only
        'url': 'https://live.rbg.tum.de/w/I2DL/12349/PRES',
        'md5': '36c584272179f3e56b0db5d880639cba',
        'info_dict': {
            'id': 'I2DL/12349/PRES',
            'ext': 'mp4',
            'title': 'Lecture 3: Introduction to Neural Networks',
            'series': 'Introduction to Deep Learning (IN2346)',
        }
    }, {
        # Camera only
        'url': 'https://live.rbg.tum.de/w/fvv-info/16130/CAM',
        'md5': 'e04189d92ff2f56aedf5cede65d37aad',
        'info_dict': {
            'id': 'fvv-info/16130/CAM',
            'ext': 'mp4',
            'title': 'Fachschaftsvollversammlung',
            'series': 'Fachschaftsvollversammlung Informatik',
        }
    }, ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        m3u8 = self._html_search_regex(r'(https://.+?\.m3u8)', webpage, 'm3u8')
        lecture_title = self._html_search_regex(r'(?si)<h1.*?>(.*)</h1>', webpage, 'title')
        lecture_series_title = self._html_search_regex(
            r'(?s)<title\b[^>]*>\s*(?:TUM-Live\s\|\s?)?([^:]+):?.*?</title>', webpage, 'series')

        formats = self._extract_m3u8_formats(m3u8, video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls')

        return {
            'id': video_id,
            'title': lecture_title,
            'series': lecture_series_title,
            'formats': formats,
        }


class RbgTumCourseIE(InfoExtractor):
    _VALID_URL = r'https://live\.rbg\.tum\.de/course/(?P<id>.+)'
    _TESTS = [{
        'url': 'https://live.rbg.tum.de/course/2022/S/fpv',
        'info_dict': {
            'title': 'Funktionale Programmierung und Verifikation (IN0003)',
            'id': '2022/S/fpv',
        },
        'params': {
            'noplaylist': False,
        },
        'playlist_count': 13,
    }, {
        'url': 'https://live.rbg.tum.de/course/2022/W/set',
        'info_dict': {
            'title': 'SET FSMPIC',
            'id': '2022/W/set',
        },
        'params': {
            'noplaylist': False,
        },
        'playlist_count': 6,
    }, ]

    def _real_extract(self, url):
        course_id = self._match_id(url)
        webpage = self._download_webpage(url, course_id)

        lecture_series_title = self._html_search_regex(r'(?si)<h1.*?>(.*)</h1>', webpage, 'title')

        lecture_urls = []
        for lecture_url in re.findall(r'(?i)href="/w/(.+)(?<!/cam)(?<!/pres)(?<!/chat)"', webpage):
            lecture_urls.append(self.url_result('https://live.rbg.tum.de/w/' + lecture_url, ie=RbgTumIE.ie_key()))

        return self.playlist_result(lecture_urls, course_id, lecture_series_title)
