# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from yt_dlp import utils


class QingTingIE(InfoExtractor):
    IE_NAME = 'QingTing'
    _VALID_URL = r'''(?x)
                     (?:https?://)?(?:www\.)?
                         (?P<m>m\.)?(?:qingting\.fm|qtfm\.cn)/(?(m)v|)
                         channels/\d+/programs/(?P<id>\d+)'''
    _TEST = {
        'url': 'https://www.qingting.fm/channels/378005/programs/22257411/',
        'md5': '47e6a94f4e621ed832c316fd1888fb3c',
        'info_dict': {
            'id': '22257411',
            'ext': 'mp3',
            'title': '用了十年才修改，谁在乎教科书？-睡前消息-蜻蜓FM听头条',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._html_search_regex(r'(?s)<title\b[^>]*>(.*)</title>', webpage, 'title',
                                        default=None) or self._og_search_title(webpage)
        urlType = self._search_regex(
            self._VALID_URL,
            url, 'audio URL', group="m")
        if urlType == 'm.':
            url = self._search_regex(
                r'''("|')audioUrl\1\s*:\s*("|')(?P<url>(?:(?!\2).)*)\2''',
                webpage, 'audio URL', group="url")
            test_url = utils.url_or_none(url)
            if not test_url:
                raise utils.ExtractorError('Invalid audio URL %s' % (url,))
            return {
                'id': video_id,
                'title': title,
                'ext': 'mp3',
                'url': test_url,
            }
        else:
            url = self._search_regex(
                r'''("|')alternate\1\s*:\s*("|')(?P<url>(?:(?!\2).)*)\2''',
                webpage, 'alternate URL', group="url")
            test_url = utils.url_or_none(url)
            if not test_url:
                raise utils.ExtractorError('Invalid audio URL %s' % (url,))
            return self.url_result(url=test_url, video_id=video_id, video_title=title)
