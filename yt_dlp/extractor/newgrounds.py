import functools
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    get_element_by_id,
    int_or_none,
    parse_count,
    parse_duration,
    unified_timestamp,
    OnDemandPagedList,
    try_get,
)


class NewgroundsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?newgrounds\.com/(?:audio/listen|portal/view)/(?P<id>\d+)(?:/format/flash)?'
    _TESTS = [{
        'url': 'https://www.newgrounds.com/audio/listen/549479',
        'md5': 'fe6033d297591288fa1c1f780386f07a',
        'info_dict': {
            'id': '549479',
            'ext': 'mp3',
            'title': 'B7 - BusMode',
            'uploader': 'Burn7',
            'timestamp': 1378878540,
            'upload_date': '20130911',
            'duration': 143,
            'view_count': int,
            'description': 'md5:b8b3c2958875189f07d8e313462e8c4f',
        },
    }, {
        'url': 'https://www.newgrounds.com/portal/view/1',
        'md5': 'fbfb40e2dc765a7e830cb251d370d981',
        'info_dict': {
            'id': '1',
            'ext': 'mp4',
            'title': 'Scrotum 1',
            'uploader': 'Brian-Beaton',
            'timestamp': 955064100,
            'upload_date': '20000406',
            'view_count': int,
            'description': 'Scrotum plays "catch."',
            'age_limit': 17,
        },
    }, {
        # source format unavailable, additional mp4 formats
        'url': 'http://www.newgrounds.com/portal/view/689400',
        'info_dict': {
            'id': '689400',
            'ext': 'mp4',
            'title': 'ZTV News Episode 8',
            'uploader': 'ZONE-SAMA',
            'timestamp': 1487965140,
            'upload_date': '20170224',
            'view_count': int,
            'description': 'md5:aff9b330ec2e78ed93b1ad6d017accc6',
            'age_limit': 17,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.newgrounds.com/portal/view/297383',
        'md5': '2c11f5fd8cb6b433a63c89ba3141436c',
        'info_dict': {
            'id': '297383',
            'ext': 'mp4',
            'title': 'Metal Gear Awesome',
            'uploader': 'Egoraptor',
            'timestamp': 1140663240,
            'upload_date': '20060223',
            'view_count': int,
            'description': 'md5:9246c181614e23754571995104da92e0',
            'age_limit': 13,
        }
    }, {
        'url': 'https://www.newgrounds.com/portal/view/297383/format/flash',
        'md5': '5d05585a9a0caca059f5abfbd3865524',
        'info_dict': {
            'id': '297383',
            'ext': 'swf',
            'title': 'Metal Gear Awesome',
            'description': 'Metal Gear Awesome',
            'uploader': 'Egoraptor',
            'upload_date': '20060223',
            'timestamp': 1140663240,
            'age_limit': 13,
        }
    }]
    _AGE_LIMIT = {
        'e': 0,
        't': 13,
        'm': 17,
        'a': 18,
    }

    def _real_extract(self, url):
        media_id = self._match_id(url)
        formats = []
        uploader = None
        webpage = self._download_webpage(url, media_id)

        title = self._html_extract_title(webpage)

        media_url_string = self._search_regex(
            r'"url"\s*:\s*("[^"]+"),', webpage, 'media url', default=None)

        if media_url_string:
            media_url = self._parse_json(media_url_string, media_id)
            formats = [{
                'url': media_url,
                'format_id': 'source',
                'quality': 1,
            }]
        else:
            json_video = self._download_json('https://www.newgrounds.com/portal/video/' + media_id, media_id, headers={
                'Accept': 'application/json',
                'Referer': url,
                'X-Requested-With': 'XMLHttpRequest'
            })

            uploader = json_video.get('author')
            media_formats = json_video.get('sources', [])
            for media_format in media_formats:
                media_sources = media_formats[media_format]
                for source in media_sources:
                    formats.append({
                        'format_id': media_format,
                        'quality': int_or_none(media_format[:-1]),
                        'url': source.get('src')
                    })

        if not uploader:
            uploader = self._html_search_regex(
                (r'(?s)<h4[^>]*>(.+?)</h4>.*?<em>\s*(?:Author|Artist)\s*</em>',
                 r'(?:Author|Writer)\s*<a[^>]+>([^<]+)'), webpage, 'uploader',
                fatal=False)

        age_limit = self._html_search_regex(
            r'<h2\s*class=["\']rated-([^"\'])["\'][^>]+>', webpage, 'age_limit', default='e')
        age_limit = self._AGE_LIMIT.get(age_limit)

        timestamp = unified_timestamp(self._html_search_regex(
            (r'<dt>\s*Uploaded\s*</dt>\s*<dd>([^<]+</dd>\s*<dd>[^<]+)',
             r'<dt>\s*Uploaded\s*</dt>\s*<dd>([^<]+)'), webpage, 'timestamp',
            default=None))

        duration = parse_duration(self._html_search_regex(
            r'"duration"\s*:\s*["\']?(\d+)["\']?', webpage,
            'duration', default=None))

        description = clean_html(get_element_by_id('author_comments', webpage)) or self._og_search_description(webpage)

        view_count = parse_count(self._html_search_regex(
            r'(?s)<dt>\s*(?:Views|Listens)\s*</dt>\s*<dd>([\d\.,]+)</dd>', webpage,
            'view count', default=None))

        filesize = int_or_none(self._html_search_regex(
            r'"filesize"\s*:\s*["\']?([\d]+)["\']?,', webpage, 'filesize',
            default=None))

        video_type_description = self._html_search_regex(
            r'"description"\s*:\s*["\']?([^"\']+)["\']?,', webpage, 'filesize',
            default=None)

        if len(formats) == 1:
            formats[0]['filesize'] = filesize

        if video_type_description == 'Audio File':
            formats[0]['vcodec'] = 'none'
        self._check_formats(formats, media_id)

        return {
            'id': media_id,
            'title': title,
            'uploader': uploader,
            'timestamp': timestamp,
            'duration': duration,
            'formats': formats,
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': description,
            'age_limit': age_limit,
            'view_count': view_count,
        }


class NewgroundsPlaylistIE(InfoExtractor):
    IE_NAME = 'Newgrounds:playlist'
    _VALID_URL = r'https?://(?:www\.)?newgrounds\.com/(?:collection|[^/]+/search/[^/]+)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.newgrounds.com/collection/cats',
        'info_dict': {
            'id': 'cats',
            'title': 'Cats',
        },
        'playlist_mincount': 45,
    }, {
        'url': 'https://www.newgrounds.com/collection/dogs',
        'info_dict': {
            'id': 'dogs',
            'title': 'Dogs',
        },
        'playlist_mincount': 26,
    }, {
        'url': 'http://www.newgrounds.com/audio/search/title/cats',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)

        title = self._html_extract_title(webpage, default=None)

        # cut left menu
        webpage = self._search_regex(
            r'(?s)<div[^>]+\bclass=["\']column wide(.+)',
            webpage, 'wide column', default=webpage)

        entries = []
        for a, path, media_id in re.findall(
                r'(<a[^>]+\bhref=["\'][^"\']+((?:portal/view|audio/listen)/(\d+))[^>]+>)',
                webpage):
            a_class = extract_attributes(a).get('class')
            if a_class not in ('item-portalsubmission', 'item-audiosubmission'):
                continue
            entries.append(
                self.url_result(
                    f'https://www.newgrounds.com/{path}',
                    ie=NewgroundsIE.ie_key(), video_id=media_id))

        return self.playlist_result(entries, playlist_id, title)


class NewgroundsUserIE(InfoExtractor):
    IE_NAME = 'Newgrounds:user'
    _VALID_URL = r'https?://(?P<id>[^\.]+)\.newgrounds\.com/(?:movies|audio)/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://burn7.newgrounds.com/audio',
        'info_dict': {
            'id': 'burn7',
        },
        'playlist_mincount': 150,
    }, {
        'url': 'https://burn7.newgrounds.com/movies',
        'info_dict': {
            'id': 'burn7',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://brian-beaton.newgrounds.com/movies',
        'info_dict': {
            'id': 'brian-beaton',
        },
        'playlist_mincount': 10,
    }]
    _PAGE_SIZE = 30

    def _fetch_page(self, channel_id, url, page):
        page += 1
        posts_info = self._download_json(
            f'{url}/page/{page}', channel_id,
            note=f'Downloading page {page}', headers={
                'Accept': 'application/json, text/javascript, */*; q = 0.01',
                'X-Requested-With': 'XMLHttpRequest',
            })
        sequence = posts_info.get('sequence', [])
        for year in sequence:
            posts = try_get(posts_info, lambda x: x['years'][str(year)]['items'])
            for post in posts:
                path, media_id = self._search_regex(
                    r'<a[^>]+\bhref=["\'][^"\']+((?:portal/view|audio/listen)/(\d+))[^>]+>',
                    post, 'url', group=(1, 2))
                yield self.url_result(f'https://www.newgrounds.com/{path}', NewgroundsIE.ie_key(), media_id)

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, channel_id, url), self._PAGE_SIZE)

        return self.playlist_result(entries, channel_id)
