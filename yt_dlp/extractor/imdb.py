import base64
import json
import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    mimetype2ext,
    qualities,
    traverse_obj,
    try_get,
    url_or_none,
)


class ImdbIE(InfoExtractor):
    IE_NAME = 'imdb'
    IE_DESC = 'Internet Movie Database trailers'
    _VALID_URL = r'https?://(?:www|m)\.imdb\.com/(?:video|title|list).*?[/-]vi(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://www.imdb.com/video/imdb/vi2524815897',
        'info_dict': {
            'id': '2524815897',
            'ext': 'mp4',
            'title': 'No. 2',
            'description': 'md5:87bd0bdc61e351f21f20d2d7441cb4e7',
            'duration': 152,
            'thumbnail': r're:^https?://.+\.jpg',
        }
    }, {
        'url': 'https://www.imdb.com/video/vi3516832537',
        'info_dict': {
            'id': '3516832537',
            'ext': 'mp4',
            'title': 'Paul: U.S. Trailer #1',
            'description': 'md5:17fcc4fe11ec29b4399be9d4c5ef126c',
            'duration': 153,
            'thumbnail': r're:^https?://.+\.jpg',
        }
    }, {
        'url': 'http://www.imdb.com/video/_/vi2524815897',
        'only_matching': True,
    }, {
        'url': 'http://www.imdb.com/title/tt1667889/?ref_=ext_shr_eml_vi#lb-vi2524815897',
        'only_matching': True,
    }, {
        'url': 'http://www.imdb.com/title/tt1667889/#lb-vi2524815897',
        'only_matching': True,
    }, {
        'url': 'http://www.imdb.com/videoplayer/vi1562949145',
        'only_matching': True,
    }, {
        'url': 'http://www.imdb.com/title/tt4218696/videoplayer/vi2608641561',
        'only_matching': True,
    }, {
        'url': 'https://www.imdb.com/list/ls009921623/videoplayer/vi260482329',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://www.imdb.com/video/vi{video_id}', video_id)
        info = self._search_nextjs_data(webpage, video_id)
        video_info = traverse_obj(info, ('props', 'pageProps', 'videoPlaybackData', 'video'), default={})
        title = (traverse_obj(video_info, ('name', 'value'), ('primaryTitle', 'titleText', 'text'))
                 or self._html_search_meta(('og:title', 'twitter:title'), webpage, default=None)
                 or self._html_extract_title(webpage))
        data = video_info.get('playbackURLs') or try_get(self._download_json(
            'https://www.imdb.com/ve/data/VIDEO_PLAYBACK_DATA', video_id,
            query={
                'key': base64.b64encode(json.dumps({
                    'type': 'VIDEO_PLAYER',
                    'subType': 'FORCE_LEGACY',
                    'id': 'vi%s' % video_id,
                }).encode()).decode(),
            }), lambda x: x[0]['videoLegacyEncodings'])
        quality = qualities(('SD', '480p', '720p', '1080p'))
        formats, subtitles = [], {}
        for encoding in data:
            if not encoding or not isinstance(encoding, dict):
                continue
            video_url = url_or_none(encoding.get('url'))
            if not video_url:
                continue
            ext = mimetype2ext(encoding.get(
                'mimeType')) or determine_ext(video_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    preference=1, m3u8_id='hls', fatal=False)
                subtitles = self._merge_subtitles(subtitles, subs)
                formats.extend(fmts)
                continue
            format_id = traverse_obj(encoding, ('displayName', 'value'), 'definition')
            formats.append({
                'format_id': format_id,
                'url': video_url,
                'ext': ext,
                'quality': quality(format_id),
            })

        return {
            'id': video_id,
            'title': title,
            'alt_title': info.get('videoSubTitle'),
            'formats': formats,
            'description': try_get(video_info, lambda x: x['description']['value']),
            'thumbnail': url_or_none(try_get(video_info, lambda x: x['thumbnail']['url'])),
            'duration': int_or_none(try_get(video_info, lambda x: x['runtime']['value'])),
            'subtitles': subtitles,
        }


class ImdbListIE(InfoExtractor):
    IE_NAME = 'imdb:list'
    IE_DESC = 'Internet Movie Database lists'
    _VALID_URL = r'https?://(?:www\.)?imdb\.com/list/ls(?P<id>\d{9})(?!/videoplayer/vi\d+)'
    _TEST = {
        'url': 'https://www.imdb.com/list/ls009921623/',
        'info_dict': {
            'id': '009921623',
            'title': 'The Bourne Legacy',
            'description': 'A list of trailers, clips, and more from The Bourne Legacy, starring Jeremy Renner and Rachel Weisz.',
        },
        'playlist_count': 8,
    }

    def _real_extract(self, url):
        list_id = self._match_id(url)
        webpage = self._download_webpage(url, list_id)
        entries = [
            self.url_result('http://www.imdb.com' + m, 'Imdb')
            for m in re.findall(r'href="(/list/ls%s/videoplayer/vi[^"]+)"' % list_id, webpage)]

        list_title = self._html_search_regex(
            r'<h1[^>]+class="[^"]*header[^"]*"[^>]*>(.*?)</h1>',
            webpage, 'list title')
        list_description = self._html_search_regex(
            r'<div[^>]+class="[^"]*list-description[^"]*"[^>]*><p>(.*?)</p>',
            webpage, 'list description')

        return self.playlist_result(entries, list_id, list_title, list_description)
