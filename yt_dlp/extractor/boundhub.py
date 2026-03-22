import itertools
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_by_id,
    parse_count,
    parse_duration,
    parse_resolution,
    url_or_none,
    urljoin,
)


class BoundHubIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?boundhub\.com/(?P<type>videos|embed)/(?P<id>\d+)(?:/(?P<display_id>[^/?#]+))?/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.boundhub.com/videos/442614/lil-missy-uk-ballgagged-in-public/',
        'md5': '0c769f26aef65608532e13f6f6a08ccb',
        'info_dict': {
            'id': '442614',
            'ext': 'mp4',
            'title': 'Lil missy UK - Ballgagged in Public',
            'display_id': 'lil-missy-uk-ballgagged-in-public',
            'age_limit': 18,
            'duration': 11,
            'view_count': int,
            'uploader_id': '107027',
            'uploader': 'Surlerra22',
            'description': 'HiddenGag and HiddenBDSM',
            'thumbnail': 'https://cnt.bondageobserver.com/contents/videos_screenshots/442000/442614/preview.jpg',
            'categories': ['Amateur Bondage', 'Gags', 'Humiliation'],
            'webpage_url': 'https://www.boundhub.com/videos/442614/lil-missy-uk-ballgagged-in-public/',
        },
    }, {
        'url': 'https://www.boundhub.com/embed/442614',
        'md5': '0c769f26aef65608532e13f6f6a08ccb',
        'info_dict': {
            'id': '442614',
            'ext': 'mp4',
            'title': 'Lil missy UK - Ballgagged in Public',
            'display_id': 'lil-missy-uk-ballgagged-in-public',
            'age_limit': 18,
            'duration': 11,
            'view_count': int,
            'uploader_id': '107027',
            'uploader': 'Surlerra22',
            'description': 'HiddenGag and HiddenBDSM',
            'thumbnail': 'https://cnt.bondageobserver.com/contents/videos_screenshots/442000/442614/preview.jpg',
            'categories': ['Amateur Bondage', 'Gags', 'Humiliation'],
        },
    }, {
        'url': 'https://www.boundhub.com/videos/442614/',
        'only_matching': True,
    }]

    @classmethod
    def _kvs_get_real_url(cls, video_url, license_code):
        if not video_url.startswith('function/0/'):
            return video_url

        parsed = urllib.parse.urlparse(video_url[len('function/0/'):])
        license_token = cls._kvs_get_license_token(license_code)
        urlparts = parsed.path.split('/')

        hash_length = 32
        hash_ = urlparts[3][:hash_length]
        indices = list(range(hash_length))

        accum = 0
        for src in reversed(range(hash_length)):
            accum += license_token[src]
            dest = (src + accum) % hash_length
            indices[src], indices[dest] = indices[dest], indices[src]

        urlparts[3] = ''.join(hash_[index] for index in indices) + urlparts[3][hash_length:]
        return urllib.parse.urlunparse(parsed._replace(path='/'.join(urlparts)))

    @staticmethod
    def _kvs_get_license_token(license_code):
        license_code = license_code.replace('$', '')
        license_values = [int(char) for char in license_code]

        modlicense = license_code.replace('0', '1')
        center = len(modlicense) // 2
        fronthalf = int(modlicense[:center + 1])
        backhalf = int(modlicense[center:])
        modlicense = str(4 * abs(fronthalf - backhalf))[:center + 1]

        return [
            (license_values[index + offset] + current) % 10
            for index, current in enumerate(map(int, modlicense))
            for offset in range(4)
        ]

    def _real_extract(self, url):
        type_, video_id, display_id = self._match_valid_url(url).group('type', 'id', 'display_id')
        webpage = self._download_webpage(url, video_id)
        target_url = url

        if type_ == 'embed':
            video_alt_url = url_or_none(self._search_regex(
                r'''empty_referer_redirect\s*:\s*['"](?P<url>https?://(?:www\.)?boundhub\.com/videos/\d+/[^'"]+/?)''',
                webpage, 'video page', default=None, group='url'))
            if video_alt_url and video_alt_url != url:
                target_url = video_alt_url
                display_id = self._match_valid_url(video_alt_url).group('display_id')
                webpage = self._download_webpage(
                    video_alt_url, video_id,
                    note='Redirecting embed to main page', fatal=False) or webpage

        title = self._html_search_regex(
            r'<title>\s*BoundHub\s*-\s*(.+?)\s*</title>', webpage, 'title',
            default=None) or self._html_search_regex(
            r'(?s)<div class="headline">\s*<h2>(.+?)</h2>', webpage, 'title')

        video_holder = get_element_by_class('video-holder', webpage) or ''
        if re.search(r'(?i)\b(?:private video|login required|members only)\b', clean_html(video_holder) or ''):
            self.raise_login_required('Private video')

        uploader_path = self._search_regex(
            r'(?s)<div class="username">\s*<a[^>]+\bhref=(["\'])(?P<path>https?://(?:www\.)?boundhub\.com/members/(?P<id>\d+)/?)\1[^>]*>\s*(?P<name>.+?)\s*</a>',
            webpage, 'uploader', default=None, group=('path', 'id', 'name'))
        if uploader_path:
            _, uploader_id, uploader = uploader_path
            uploader = clean_html(uploader)
        else:
            uploader_id = uploader = None

        thumbnail = url_or_none(self._search_regex(
            r'''preview_url\s*:\s*['"]([^'"]+)''', webpage, 'thumbnail', default=None))
        categories = [clean_html(category) for category in self._search_regex(
            r'''video_categories\s*:\s*['"]([^'"]+)''', webpage, 'categories',
            default='').split(',') if clean_html(category)] or None

        description = self._html_search_meta(
            ('description', 'og:description'), webpage, default=None)
        duration = parse_duration(self._search_regex(
            r'Duration:\s*<em>([^<]+)</em>',
            webpage, 'duration', default=None))
        view_count = parse_count(re.sub(r'\s+', '', self._search_regex(
            r'Views:\s*<em>([\d,. ]+)</em>',
            webpage, 'view count', default='') or None))
        license_code = self._search_regex(
            r'''license_code\s*:\s*['"]([^'"]+)''', webpage, 'license code')
        formats = []
        for key in re.findall(r'''\b(video_(?:url|alt_url\d*|url_[^'":\s]+))\s*:''', webpage):
            video_url = url_or_none(self._search_regex(
                rf'''{re.escape(key)}\s*:\s*['"]([^'"]+)''',
                webpage, f'{key} url', default=None))
            if not video_url or '/get_file/' not in video_url:
                continue
            format_id = self._search_regex(
                rf'''{re.escape(key)}_text\s*:\s*['"]([^'"]+)''',
                webpage, f'{key} format', default=key)
            fmt = {
                'url': urljoin(target_url, self._kvs_get_real_url(video_url, license_code)),
                'format_id': format_id,
                'ext': 'mp4',
                'http_headers': {'Referer': target_url},
                **(parse_resolution(format_id) or parse_resolution(video_url)),
            }
            if not fmt.get('height'):
                fmt['quality'] = 1
            formats.append(fmt)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'view_count': view_count,
            'categories': categories,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'age_limit': 18,
            'formats': formats,
        }


class BoundHubPlaylistBaseIE(InfoExtractor):
    _VIDEO_URL_RE = r'https?://(?:www\.)?boundhub\.com/videos/\d+/[^/"?#]+/?'
    _PAGE_PARAMS_RE = None
    _BLOCK_ID = None

    @staticmethod
    def _parse_kvs_params(params):
        parsed = {}
        if not params:
            return parsed
        for item in params.split(';'):
            key, delim, value = item.partition(':')
            if delim and key:
                parsed[key] = value
        return parsed

    @classmethod
    def _find_urls(cls, html):
        for m in re.finditer(
                rf'''<a\b[^>]+\bhref=(["'])(?P<url>{cls._VIDEO_URL_RE})\1''', html):
            yield m.group('url')

    def _extract_relevant_html(self, html):
        if not self._BLOCK_ID:
            return html
        block = get_element_by_id(self._BLOCK_ID, html) or ''
        pagination = get_element_by_id(f'{self._BLOCK_ID}_pagination', html) or ''
        return f'{block}{pagination}' or html

    def _get_next_page_data(self, html):
        if not self._PAGE_PARAMS_RE:
            return None
        next_link = self._search_regex(
            rf'(?s)<li class="next">\s*(<a\b[^>]+data-parameters=(["\']).*?{self._PAGE_PARAMS_RE}.*?\2[^>]*>)',
            html, 'next page link', default=None)
        if not next_link:
            return None
        attrs = extract_attributes(next_link)
        if not attrs:
            return None
        params = self._parse_kvs_params(attrs.get('data-parameters'))
        return {
            'block_id': attrs.get('data-block-id'),
            'params': params,
        } if params and attrs.get('data-block-id') else None

    def _generate_playlist_entries(self, url, playlist_id, html=None):
        next_page = None
        for page_num in itertools.count(1):
            if not html:
                html = self._download_webpage(
                    url, playlist_id, note=f'Downloading page {page_num}',
                    fatal=False, headers={
                        'Accept': '*/*',
                        'Referer': url,
                        'X-Requested-With': 'XMLHttpRequest',
                    }, query={
                        'mode': 'async',
                        'function': 'get_block',
                        'block_id': next_page['block_id'],
                        **next_page['params'],
                    }) or ''
            html = self._extract_relevant_html(html)

            yield from self._find_urls(html)

            next_page = self._get_next_page_data(html)
            if not next_page:
                return

            html = None

    def _make_playlist_result(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        title = self._html_search_regex(
            r'<title>\s*BoundHub\s*-\s*(.+?)\s*</title>', webpage, 'title',
            default=None)
        return self.playlist_from_matches(
            self._generate_playlist_entries(url, playlist_id, webpage),
            playlist_id=playlist_id, playlist_title=title, ie=BoundHubIE)


class BoundHubMemberIE(BoundHubPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boundhub\.com/members/(?P<id>\d+)(?:/(?P<section>videos|favourites/videos))?/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.boundhub.com/members/19447/',
        'info_dict': {
            'id': '19447',
            'title': "Bper's Page",
        },
        'playlist_mincount': 8,
    }, {
        'url': 'https://www.boundhub.com/members/132955/favourites/videos/',
        'info_dict': {
            'id': '132955',
            'title': "Dpiero's Favourite Videos",
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://www.boundhub.com/members/19447/videos/',
        'info_dict': {
            'id': '19447',
            'title': "Bper's Videos",
        },
        'playlist_mincount': 8,
    }, {
        'url': 'https://www.boundhub.com/members/19447',
        'only_matching': True,
    }, {
        'url': 'https://www.boundhub.com/members/19447/videos',
        'only_matching': True,
    }, {
        'url': 'https://www.boundhub.com/members/132955/favourites/videos',
        'only_matching': True,
    }]
    _PAGE_PARAMS_RE = r'from_(?:fav_)?videos'

    def _get_next_page_data(self, html):
        section = getattr(self, '_section', None)
        if section == 'favourites/videos':
            pattern = r'from_fav_videos'
        else:
            pattern = r'from_videos'
        next_link = self._search_regex(
            rf'(?s)<li class="next">\s*(<a\b[^>]+data-parameters=(["\']).*?{pattern}.*?\2[^>]*>)',
            html, 'next page link', default=None)
        if not next_link:
            return None
        attrs = extract_attributes(next_link)
        if not attrs:
            return None
        params = self._parse_kvs_params(attrs.get('data-parameters'))
        return {
            'block_id': attrs.get('data-block-id'),
            'params': params,
        } if params and attrs.get('data-block-id') else None

    def _real_extract(self, url):
        self._section = self._match_valid_url(url).group('section')
        self._BLOCK_ID = 'list_videos_favourite_videos' if self._section == 'favourites/videos' else 'list_videos_uploaded_videos'
        return self._make_playlist_result(url)


class BoundHubPlaylistIE(BoundHubPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boundhub\.com/playlists/(?P<id>\d+)(?:/[^/?#]+)?/?(?:[?#]|$)'
    _BLOCK_ID = 'playlist_view_playlist_view_items'
    _TESTS = [{
        'url': 'https://www.boundhub.com/playlists/167413/1-mainstream-117/',
        'info_dict': {
            'id': '167413',
            'title': 'Mainstream 385',
        },
        'playlist_mincount': 19,
    }, {
        'url': 'https://www.boundhub.com/playlists/167413/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._make_playlist_result(url)


class BoundHubMyFavoritesIE(BoundHubPlaylistBaseIE):
    IE_NAME = 'BoundHubMyFavorites'
    _VALID_URL = r'https?://(?:www\.)?boundhub\.com/my/favourites/videos/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.boundhub.com/my/favourites/videos/',
        'skip': 'Requires account credentials',
    }, {
        'url': 'https://www.boundhub.com/my/favourites/videos/',
        'only_matching': True,
    }, {
        'url': 'https://www.boundhub.com/my/favourites/videos',
        'only_matching': True,
    }]
    _PAGE_PARAMS_RE = r'from_my_fav_videos'
    _BLOCK_ID = 'list_videos_my_favourite_videos'

    def _make_playlist_result(self, url):
        webpage, urlh = self._download_webpage_handle(url, 'my-favourites-videos')
        if re.search(r'(?i)(?:[?&]login\b|/login-required/)', urlh.url):
            self.raise_login_required('Login required to access favourite videos')
        title = self._html_search_regex(
            r'<title>\s*BoundHub\s*-\s*(.+?)\s*</title>', webpage, 'title',
            default=None)
        return self.playlist_from_matches(
            self._generate_playlist_entries(url, 'my-favourites-videos', webpage),
            playlist_id='my-favourites-videos', playlist_title=title, ie=BoundHubIE)

    def _real_extract(self, url):
        return self._make_playlist_result(url)
