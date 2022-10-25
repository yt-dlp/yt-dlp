import itertools
import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    clean_html,
    determine_ext,
    dict_get,
    extract_attributes,
    ExtractorError,
    float_or_none,
    int_or_none,
    parse_duration,
    str_or_none,
    try_get,
    unified_strdate,
    url_or_none,
    urljoin,
)


class XHamsterIE(InfoExtractor):
    _DOMAINS = r'(?:xhamster\.(?:com|one|desi)|xhms\.pro|xhamster\d+\.com|xhday\.com)'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:.+?\.)?%s/
                        (?:
                            movies/(?P<id>[\dA-Za-z]+)/(?P<display_id>[^/]*)\.html|
                            videos/(?P<display_id_2>[^/]*)-(?P<id_2>[\dA-Za-z]+)
                        )
                    ''' % _DOMAINS
    _TESTS = [{
        'url': 'https://xhamster.com/videos/femaleagent-shy-beauty-takes-the-bait-1509445',
        'md5': '34e1ab926db5dc2750fed9e1f34304bb',
        'info_dict': {
            'id': '1509445',
            'display_id': 'femaleagent-shy-beauty-takes-the-bait',
            'ext': 'mp4',
            'title': 'FemaleAgent Shy beauty takes the bait',
            'timestamp': 1350194821,
            'upload_date': '20121014',
            'uploader': 'Ruseful2011',
            'uploader_id': 'ruseful2011',
            'duration': 893,
            'age_limit': 18,
        },
    }, {
        'url': 'https://xhamster.com/videos/britney-spears-sexy-booty-2221348?hd=',
        'info_dict': {
            'id': '2221348',
            'display_id': 'britney-spears-sexy-booty',
            'ext': 'mp4',
            'title': 'Britney Spears  Sexy Booty',
            'timestamp': 1379123460,
            'upload_date': '20130914',
            'uploader': 'jojo747400',
            'duration': 200,
            'age_limit': 18,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # empty seo, unavailable via new URL schema
        'url': 'http://xhamster.com/movies/5667973/.html',
        'info_dict': {
            'id': '5667973',
            'ext': 'mp4',
            'title': '....',
            'timestamp': 1454948101,
            'upload_date': '20160208',
            'uploader': 'parejafree',
            'uploader_id': 'parejafree',
            'duration': 72,
            'age_limit': 18,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # mobile site
        'url': 'https://m.xhamster.com/videos/cute-teen-jacqueline-solo-masturbation-8559111',
        'only_matching': True,
    }, {
        'url': 'https://xhamster.com/movies/2272726/amber_slayed_by_the_knight.html',
        'only_matching': True,
    }, {
        # This video is visible for marcoalfa123456's friends only
        'url': 'https://it.xhamster.com/movies/7263980/la_mia_vicina.html',
        'only_matching': True,
    }, {
        # new URL schema
        'url': 'https://pt.xhamster.com/videos/euro-pedal-pumping-7937821',
        'only_matching': True,
    }, {
        'url': 'https://xhamster.one/videos/femaleagent-shy-beauty-takes-the-bait-1509445',
        'only_matching': True,
    }, {
        'url': 'https://xhamster.desi/videos/femaleagent-shy-beauty-takes-the-bait-1509445',
        'only_matching': True,
    }, {
        'url': 'https://xhamster2.com/videos/femaleagent-shy-beauty-takes-the-bait-1509445',
        'only_matching': True,
    }, {
        'url': 'https://xhamster11.com/videos/femaleagent-shy-beauty-takes-the-bait-1509445',
        'only_matching': True,
    }, {
        'url': 'https://xhamster26.com/videos/femaleagent-shy-beauty-takes-the-bait-1509445',
        'only_matching': True,
    }, {
        'url': 'http://xhamster.com/movies/1509445/femaleagent_shy_beauty_takes_the_bait.html',
        'only_matching': True,
    }, {
        'url': 'http://xhamster.com/movies/2221348/britney_spears_sexy_booty.html?hd',
        'only_matching': True,
    }, {
        'url': 'http://de.xhamster.com/videos/skinny-girl-fucks-herself-hard-in-the-forest-xhnBJZx',
        'only_matching': True,
    }, {
        'url': 'https://xhday.com/videos/strapless-threesome-xhh7yVf',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id') or mobj.group('id_2')
        display_id = mobj.group('display_id') or mobj.group('display_id_2')

        desktop_url = re.sub(r'^(https?://(?:.+?\.)?)m\.', r'\1', url)
        webpage, urlh = self._download_webpage_handle(desktop_url, video_id)

        error = self._html_search_regex(
            r'<div[^>]+id=["\']videoClosed["\'][^>]*>(.+?)</div>',
            webpage, 'error', default=None)
        if error:
            raise ExtractorError(error, expected=True)

        age_limit = self._rta_search(webpage)

        def get_height(s):
            return int_or_none(self._search_regex(
                r'^(\d+)[pP]', s, 'height', default=None))

        initials = self._parse_json(
            self._search_regex(
                (r'window\.initials\s*=\s*({.+?})\s*;\s*</script>',
                 r'window\.initials\s*=\s*({.+?})\s*;'), webpage, 'initials',
                default='{}'),
            video_id, fatal=False)
        if initials:
            video = initials['videoModel']
            title = video['title']
            formats = []
            format_urls = set()
            format_sizes = {}
            sources = try_get(video, lambda x: x['sources'], dict) or {}
            for format_id, formats_dict in sources.items():
                if not isinstance(formats_dict, dict):
                    continue
                download_sources = try_get(sources, lambda x: x['download'], dict) or {}
                for quality, format_dict in download_sources.items():
                    if not isinstance(format_dict, dict):
                        continue
                    format_sizes[quality] = float_or_none(format_dict.get('size'))
                for quality, format_item in formats_dict.items():
                    if format_id == 'download':
                        # Download link takes some time to be generated,
                        # skipping for now
                        continue
                    format_url = format_item
                    format_url = url_or_none(format_url)
                    if not format_url or format_url in format_urls:
                        continue
                    format_urls.add(format_url)
                    formats.append({
                        'format_id': '%s-%s' % (format_id, quality),
                        'url': format_url,
                        'ext': determine_ext(format_url, 'mp4'),
                        'height': get_height(quality),
                        'filesize': format_sizes.get(quality),
                        'http_headers': {
                            'Referer': urlh.geturl(),
                        },
                    })
            xplayer_sources = try_get(
                initials, lambda x: x['xplayerSettings']['sources'], dict)
            if xplayer_sources:
                hls_sources = xplayer_sources.get('hls')
                if isinstance(hls_sources, dict):
                    for hls_format_key in ('url', 'fallback'):
                        hls_url = hls_sources.get(hls_format_key)
                        if not hls_url:
                            continue
                        hls_url = urljoin(url, hls_url)
                        if not hls_url or hls_url in format_urls:
                            continue
                        format_urls.add(hls_url)
                        formats.extend(self._extract_m3u8_formats(
                            hls_url, video_id, 'mp4', entry_protocol='m3u8_native',
                            m3u8_id='hls', fatal=False))
                standard_sources = xplayer_sources.get('standard')
                if isinstance(standard_sources, dict):
                    for format_id, formats_list in standard_sources.items():
                        if not isinstance(formats_list, list):
                            continue
                        for standard_format in formats_list:
                            if not isinstance(standard_format, dict):
                                continue
                            for standard_format_key in ('url', 'fallback'):
                                standard_url = standard_format.get(standard_format_key)
                                if not standard_url:
                                    continue
                                standard_url = urljoin(url, standard_url)
                                if not standard_url or standard_url in format_urls:
                                    continue
                                format_urls.add(standard_url)
                                ext = determine_ext(standard_url, 'mp4')
                                if ext == 'm3u8':
                                    formats.extend(self._extract_m3u8_formats(
                                        standard_url, video_id, 'mp4', entry_protocol='m3u8_native',
                                        m3u8_id='hls', fatal=False))
                                    continue
                                quality = (str_or_none(standard_format.get('quality'))
                                           or str_or_none(standard_format.get('label'))
                                           or '')
                                formats.append({
                                    'format_id': '%s-%s' % (format_id, quality),
                                    'url': standard_url,
                                    'ext': ext,
                                    'height': get_height(quality),
                                    'filesize': format_sizes.get(quality),
                                    'http_headers': {
                                        'Referer': standard_url,
                                    },
                                })
            self._sort_formats(formats)

            categories_list = video.get('categories')
            if isinstance(categories_list, list):
                categories = []
                for c in categories_list:
                    if not isinstance(c, dict):
                        continue
                    c_name = c.get('name')
                    if isinstance(c_name, compat_str):
                        categories.append(c_name)
            else:
                categories = None

            uploader_url = url_or_none(try_get(video, lambda x: x['author']['pageURL']))
            return {
                'id': video_id,
                'display_id': display_id,
                'title': title,
                'description': video.get('description'),
                'timestamp': int_or_none(video.get('created')),
                'uploader': try_get(
                    video, lambda x: x['author']['name'], compat_str),
                'uploader_url': uploader_url,
                'uploader_id': uploader_url.split('/')[-1] if uploader_url else None,
                'thumbnail': video.get('thumbURL'),
                'duration': int_or_none(video.get('duration')),
                'view_count': int_or_none(video.get('views')),
                'like_count': int_or_none(try_get(
                    video, lambda x: x['rating']['likes'], int)),
                'dislike_count': int_or_none(try_get(
                    video, lambda x: x['rating']['dislikes'], int)),
                'comment_count': int_or_none(video.get('views')),
                'age_limit': age_limit if age_limit is not None else 18,
                'categories': categories,
                'formats': formats,
            }

        # Old layout fallback

        title = self._html_search_regex(
            [r'<h1[^>]*>([^<]+)</h1>',
             r'<meta[^>]+itemprop=".*?caption.*?"[^>]+content="(.+?)"',
             r'<title[^>]*>(.+?)(?:,\s*[^,]*?\s*Porn\s*[^,]*?:\s*xHamster[^<]*| - xHamster\.com)</title>'],
            webpage, 'title')

        formats = []
        format_urls = set()

        sources = self._parse_json(
            self._search_regex(
                r'sources\s*:\s*({.+?})\s*,?\s*\n', webpage, 'sources',
                default='{}'),
            video_id, fatal=False)
        for format_id, format_url in sources.items():
            format_url = url_or_none(format_url)
            if not format_url:
                continue
            if format_url in format_urls:
                continue
            format_urls.add(format_url)
            formats.append({
                'format_id': format_id,
                'url': format_url,
                'height': get_height(format_id),
            })

        video_url = self._search_regex(
            [r'''file\s*:\s*(?P<q>["'])(?P<mp4>.+?)(?P=q)''',
             r'''<a\s+href=(?P<q>["'])(?P<mp4>.+?)(?P=q)\s+class=["']mp4Thumb''',
             r'''<video[^>]+file=(?P<q>["'])(?P<mp4>.+?)(?P=q)[^>]*>'''],
            webpage, 'video url', group='mp4', default=None)
        if video_url and video_url not in format_urls:
            formats.append({
                'url': video_url,
            })

        self._sort_formats(formats)

        # Only a few videos have an description
        mobj = re.search(r'<span>Description: </span>([^<]+)', webpage)
        description = mobj.group(1) if mobj else None

        upload_date = unified_strdate(self._search_regex(
            r'hint=["\'](\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2} [A-Z]{3,4}',
            webpage, 'upload date', fatal=False))

        uploader = self._html_search_regex(
            r'<span[^>]+itemprop=["\']author[^>]+><a[^>]+><span[^>]+>([^<]+)',
            webpage, 'uploader', default='anonymous')

        thumbnail = self._search_regex(
            [r'''["']thumbUrl["']\s*:\s*(?P<q>["'])(?P<thumbnail>.+?)(?P=q)''',
             r'''<video[^>]+"poster"=(?P<q>["'])(?P<thumbnail>.+?)(?P=q)[^>]*>'''],
            webpage, 'thumbnail', fatal=False, group='thumbnail')

        duration = parse_duration(self._search_regex(
            [r'<[^<]+\bitemprop=["\']duration["\'][^<]+\bcontent=["\'](.+?)["\']',
             r'Runtime:\s*</span>\s*([\d:]+)'], webpage,
            'duration', fatal=False))

        view_count = int_or_none(self._search_regex(
            r'content=["\']User(?:View|Play)s:(\d+)',
            webpage, 'view count', fatal=False))

        mobj = re.search(r'hint=[\'"](?P<likecount>\d+) Likes / (?P<dislikecount>\d+) Dislikes', webpage)
        (like_count, dislike_count) = (mobj.group('likecount'), mobj.group('dislikecount')) if mobj else (None, None)

        mobj = re.search(r'</label>Comments \((?P<commentcount>\d+)\)</div>', webpage)
        comment_count = mobj.group('commentcount') if mobj else 0

        categories_html = self._search_regex(
            r'(?s)<table.+?(<span>Categories:.+?)</table>', webpage,
            'categories', default=None)
        categories = [clean_html(category) for category in re.findall(
            r'<a[^>]+>(.+?)</a>', categories_html)] if categories_html else None

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'upload_date': upload_date,
            'uploader': uploader,
            'uploader_id': uploader.lower() if uploader else None,
            'thumbnail': thumbnail,
            'duration': duration,
            'view_count': view_count,
            'like_count': int_or_none(like_count),
            'dislike_count': int_or_none(dislike_count),
            'comment_count': int_or_none(comment_count),
            'age_limit': age_limit,
            'categories': categories,
            'formats': formats,
        }


class XHamsterEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:.+?\.)?%s/xembed\.php\?video=(?P<id>\d+)' % XHamsterIE._DOMAINS
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?xhamster\.com/xembed\.php\?video=\d+)\1']
    _TEST = {
        'url': 'http://xhamster.com/xembed.php?video=3328539',
        'info_dict': {
            'id': '3328539',
            'ext': 'mp4',
            'title': 'Pen Masturbation',
            'timestamp': 1406581861,
            'upload_date': '20140728',
            'uploader': 'ManyakisArt',
            'duration': 5,
            'age_limit': 18,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_url = self._search_regex(
            r'href="(https?://xhamster\.com/(?:movies/{0}/[^"]*\.html|videos/[^/]*-{0})[^"]*)"'.format(video_id),
            webpage, 'xhamster url', default=None)

        if not video_url:
            vars = self._parse_json(
                self._search_regex(r'vars\s*:\s*({.+?})\s*,\s*\n', webpage, 'vars'),
                video_id)
            video_url = dict_get(vars, ('downloadLink', 'homepageLink', 'commentsLink', 'shareUrl'))

        return self.url_result(video_url, 'XHamster')


class XHamsterUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:.+?\.)?%s/users/(?P<id>[^/?#&]+)' % XHamsterIE._DOMAINS
    _TESTS = [{
        # Paginated user profile
        'url': 'https://xhamster.com/users/netvideogirls/videos',
        'info_dict': {
            'id': 'netvideogirls',
        },
        'playlist_mincount': 267,
    }, {
        # Non-paginated user profile
        'url': 'https://xhamster.com/users/firatkaan/videos',
        'info_dict': {
            'id': 'firatkaan',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://xhday.com/users/mobhunter',
        'only_matching': True,
    }]

    def _entries(self, user_id):
        next_page_url = 'https://xhamster.com/users/%s/videos/1' % user_id
        for pagenum in itertools.count(1):
            page = self._download_webpage(
                next_page_url, user_id, 'Downloading page %s' % pagenum)
            for video_tag in re.findall(
                    r'(<a[^>]+class=["\'].*?\bvideo-thumb__image-container[^>]+>)',
                    page):
                video = extract_attributes(video_tag)
                video_url = url_or_none(video.get('href'))
                if not video_url or not XHamsterIE.suitable(video_url):
                    continue
                video_id = XHamsterIE._match_id(video_url)
                yield self.url_result(
                    video_url, ie=XHamsterIE.ie_key(), video_id=video_id)
            mobj = re.search(r'<a[^>]+data-page=["\']next[^>]+>', page)
            if not mobj:
                break
            next_page = extract_attributes(mobj.group(0))
            next_page_url = url_or_none(next_page.get('href'))
            if not next_page_url:
                break

    def _real_extract(self, url):
        user_id = self._match_id(url)
        return self.playlist_result(self._entries(user_id), user_id)
