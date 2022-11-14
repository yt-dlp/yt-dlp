import functools
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    get_element_by_class,
    parse_count,
    remove_end,
    unified_strdate,
    js_to_json,
    OnDemandPagedList,
)


class TokentubeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tokentube\.net/(?:view\?[vl]=|[vl]/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://tokentube.net/l/3236632011/Praise-A-Thon-Pastori-Chrisin-ja-Pastori-Bennyn-kanssa-27-8-2021',
        'info_dict': {
            'id': '3236632011',
            'ext': 'mp4',
            'title': 'Praise-A-Thon Pastori Chrisin ja Pastori Bennyn kanssa 27.8.2021',
            'description': '',
            'uploader': 'Pastori Chris - Rapsodia.fi',
            'upload_date': '20210827',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://tokentube.net/v/3950239124/Linux-Ubuntu-Studio-perus-k%C3%A4ytt%C3%B6',
        'md5': '0e1f00421f501f5eada9890d38fcfb56',
        'info_dict': {
            'id': '3950239124',
            'ext': 'mp4',
            'title': 'Linux Ubuntu Studio perus käyttö',
            'description': 'md5:46077d0daaba1974f2dc381257f9d64c',
            'uploader': 'jyrilehtonen',
            'upload_date': '20210825',
        },
    }, {
        'url': 'https://tokentube.net/view?v=3582463289',
        'info_dict': {
            'id': '3582463289',
            'ext': 'mp4',
            'title': 'Police for Freedom - toiminta aloitetaan Suomessa ❤️??',
            'description': 'md5:37ebf1cb44264e0bf23ed98b337ee63e',
            'uploader': 'Voitontie',
            'upload_date': '20210428',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<h1\s*class=["\']title-text["\']>(.+?)</h1>', webpage, 'title')

        data_json = self._html_search_regex(r'({["\']html5["\'].+?}}}+)', webpage, 'data json')
        data_json = self._parse_json(js_to_json(data_json), video_id, fatal=False)

        sources = data_json.get('sources') or self._parse_json(
            self._html_search_regex(r'updateSrc\(([^\)]+)\)', webpage, 'sources'),
            video_id, transform_source=js_to_json)

        formats = [{
            'url': format.get('src'),
            'format_id': format.get('label'),
            'height': format.get('res'),
        } for format in sources]

        view_count = parse_count(self._html_search_regex(
            r'<p\s*class=["\']views_counter["\']>\s*([\d\.,]+)\s*<span>views?</span></p>',
            webpage, 'view_count', fatal=False))

        like_count = parse_count(self._html_search_regex(
            r'<div\s*class="sh_button\s*likes_count">\s*(\d+)\s*</div>',
            webpage, 'like count', fatal=False))

        dislike_count = parse_count(self._html_search_regex(
            r'<div\s*class="sh_button\s*dislikes_count">\s*(\d+)\s*</div>',
            webpage, 'dislike count', fatal=False))

        upload_date = unified_strdate(self._html_search_regex(
            r'<span\s*class="p-date">Published\s*on\s+([^<]+)',
            webpage, 'upload date', fatal=False))

        uploader = self._html_search_regex(
            r'<a\s*class="place-left"[^>]+>(.+?)</a>',
            webpage, 'uploader', fatal=False)

        description = (clean_html(get_element_by_class('p-d-txt', webpage))
                       or self._html_search_meta(('og:description', 'description', 'twitter:description'), webpage))

        description = remove_end(description, 'Category')

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'upload_date': upload_date,
            'description': description,
            'uploader': uploader,
        }


class TokentubeChannelIE(InfoExtractor):
    _PAGE_SIZE = 20
    IE_NAME = 'Tokentube:channel'
    _VALID_URL = r'https?://(?:www\.)?tokentube\.net/channel/(?P<id>\d+)/[^/]+(?:/videos)?'
    _TESTS = [{
        'url': 'https://tokentube.net/channel/3697658904/TokenTube',
        'info_dict': {
            'id': '3697658904',
        },
        'playlist_mincount': 7,
    }, {
        'url': 'https://tokentube.net/channel/3353234420/Linux/videos',
        'info_dict': {
            'id': '3353234420',
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://tokentube.net/channel/3475834195/Voitontie',
        'info_dict': {
            'id': '3475834195',
        },
        'playlist_mincount': 150,
    }]

    def _fetch_page(self, channel_id, page):
        page += 1
        videos_info = self._download_webpage(
            f'https://tokentube.net/videos?p=0&m=1&sort=recent&u={channel_id}&page={page}',
            channel_id, headers={'X-Requested-With': 'XMLHttpRequest'},
            note=f'Downloading page {page}', fatal=False)
        if '</i> Sorry, no results were found.' not in videos_info:
            for path, media_id in re.findall(
                    r'<a[^>]+\bhref=["\']([^"\']+/[lv]/(\d+)/\S+)["\'][^>]+>',
                    videos_info):
                yield self.url_result(path, ie=TokentubeIE.ie_key(), video_id=media_id)

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, channel_id), self._PAGE_SIZE)

        return self.playlist_result(entries, channel_id)
