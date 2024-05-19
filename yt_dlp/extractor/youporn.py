import itertools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_by_id,
    int_or_none,
    merge_dicts,
    parse_count,
    parse_qs,
    traverse_obj,
    unified_strdate,
    url_or_none,
    urljoin,
)


class YouPornIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?youporn\.com/(?:watch|embed)/(?P<id>\d+)(?:/(?P<display_id>[^/?#&]+))?/?(?:[#?]|$)'
    _EMBED_REGEX = [r'<iframe[^>]+\bsrc=["\'](?P<url>(?:https?:)?//(?:www\.)?youporn\.com/embed/\d+)']
    _TESTS = [{
        'url': 'http://www.youporn.com/watch/505835/sex-ed-is-it-safe-to-masturbate-daily/',
        'md5': '3744d24c50438cf5b6f6d59feb5055c2',
        'info_dict': {
            'id': '505835',
            'display_id': 'sex-ed-is-it-safe-to-masturbate-daily',
            'ext': 'mp4',
            'title': 'Sex Ed: Is It Safe To Masturbate Daily?',
            'description': 'Love & Sex Answers: http://bit.ly/DanAndJenn -- Is It Unhealthy To Masturbate Daily?',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 210,
            'uploader': 'Ask Dan And Jennifer',
            'upload_date': '20101217',
            'average_rating': int,
            'view_count': int,
            'categories': list,
            'tags': list,
            'age_limit': 18,
        },
        'skip': 'This video has been deactivated',
    }, {
        # Unknown uploader
        'url': 'http://www.youporn.com/watch/561726/big-tits-awesome-brunette-on-amazing-webcam-show/?from=related3&al=2&from_id=561726&pos=4',
        'info_dict': {
            'id': '561726',
            'display_id': 'big-tits-awesome-brunette-on-amazing-webcam-show',
            'ext': 'mp4',
            'title': 'Big Tits Awesome Brunette On amazing webcam show',
            'description': 'http://sweetlivegirls.com Big Tits Awesome Brunette On amazing webcam show.mp4',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Unknown',
            'upload_date': '20110418',
            'average_rating': int,
            'view_count': int,
            'categories': list,
            'tags': list,
            'age_limit': 18,
        },
        'params': {
            'skip_download': True,
        },
        'skip': '404',
    }, {
        'url': 'https://www.youporn.com/embed/505835/sex-ed-is-it-safe-to-masturbate-daily/',
        'only_matching': True,
    }, {
        'url': 'http://www.youporn.com/watch/505835',
        'only_matching': True,
    }, {
        'url': 'https://www.youporn.com/watch/13922959/femdom-principal/',
        'only_matching': True,
    }, {
        'url': 'https://www.youporn.com/watch/16290308/tinderspecial-trailer1/',
        'info_dict': {
            'id': '16290308',
            'age_limit': 18,
            'categories': [],
            'display_id': 'tinderspecial-trailer1',
            'duration': 298.0,
            'ext': 'mp4',
            'upload_date': '20201123',
            'uploader': 'Ersties',
            'tags': [],
            'thumbnail': r're:https://.+\.jpg',
            'timestamp': 1606147564,
            'title': 'Tinder In Real Life',
            'view_count': int,
        }
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        self._set_cookie('.youporn.com', 'age_verified', '1')
        webpage = self._download_webpage(f'https://www.youporn.com/watch/{video_id}', video_id)

        watchable = self._search_regex(
            r'''(<div\s[^>]*\bid\s*=\s*('|")?watch-container(?(2)\2|(?!-)\b)[^>]*>)''',
            webpage, 'watchability', default=None)
        if not watchable:
            msg = re.split(r'\s{2}', clean_html(get_element_by_id('mainContent', webpage)) or '')[0]
            raise ExtractorError(
                f'{self.IE_NAME} says: {msg}' if msg else 'Video unavailable', expected=True)

        player_vars = self._search_json(r'\bplayervars\s*:', webpage, 'player vars', video_id)
        definitions = player_vars['mediaDefinitions']

        def get_format_data(data, stream_type):
            info_url = traverse_obj(data, (lambda _, v: v['format'] == stream_type, 'videoUrl', {url_or_none}, any))
            if not info_url:
                return []
            return traverse_obj(
                self._download_json(info_url, video_id, f'Downloading {stream_type} info JSON', fatal=False),
                lambda _, v: v['format'] == stream_type and url_or_none(v['videoUrl']))

        formats = []
        # Try to extract only the actual master m3u8 first, avoiding the duplicate single resolution "master" m3u8s
        for hls_url in traverse_obj(get_format_data(definitions, 'hls'), (
                lambda _, v: not isinstance(v['defaultQuality'], bool), 'videoUrl'), (..., 'videoUrl')):
            formats.extend(self._extract_m3u8_formats(hls_url, video_id, 'mp4', fatal=False, m3u8_id='hls'))

        for definition in get_format_data(definitions, 'mp4'):
            f = traverse_obj(definition, {
                'url': 'videoUrl',
                'filesize': ('videoSize', {int_or_none})
            })
            height = int_or_none(definition.get('quality'))
            # Video URL's path looks like this:
            #  /201012/17/505835/720p_1500k_505835/YouPorn%20-%20Sex%20Ed%20Is%20It%20Safe%20To%20Masturbate%20Daily.mp4
            #  /201012/17/505835/vl_240p_240k_505835/YouPorn%20-%20Sex%20Ed%20Is%20It%20Safe%20To%20Masturbate%20Daily.mp4
            #  /videos/201703/11/109285532/1080P_4000K_109285532.mp4
            # We will benefit from it by extracting some metadata
            mobj = re.search(r'(?P<height>\d{3,4})[pP]_(?P<bitrate>\d+)[kK]_\d+', definition['videoUrl'])
            if mobj:
                if not height:
                    height = int(mobj.group('height'))
                bitrate = int(mobj.group('bitrate'))
                f.update({
                    'format_id': '%dp-%dk' % (height, bitrate),
                    'tbr': bitrate,
                })
            f['height'] = height
            formats.append(f)

        title = self._html_search_regex(
            r'(?s)<div[^>]+class=["\']watchVideoTitle[^>]+>(.+?)</div>',
            webpage, 'title', default=None) or self._og_search_title(
            webpage, default=None) or self._html_search_meta(
            'title', webpage, fatal=True)

        description = self._html_search_regex(
            r'(?s)<div[^>]+\bid=["\']description["\'][^>]*>(.+?)</div>',
            webpage, 'description',
            default=None) or self._og_search_description(
            webpage, default=None)
        thumbnail = self._search_regex(
            r'(?:imageurl\s*=|poster\s*:)\s*(["\'])(?P<thumbnail>.+?)\1',
            webpage, 'thumbnail', fatal=False, group='thumbnail')
        duration = traverse_obj(player_vars, ('duration', {int_or_none}))
        if duration is None:
            duration = int_or_none(self._html_search_meta(
                'video:duration', webpage, 'duration', fatal=False))

        uploader = self._html_search_regex(
            r'(?s)<div[^>]+class=["\']submitByLink["\'][^>]*>(.+?)</div>',
            webpage, 'uploader', fatal=False)
        upload_date = unified_strdate(self._html_search_regex(
            (r'UPLOADED:\s*<span>([^<]+)',
             r'Date\s+[Aa]dded:\s*<span>([^<]+)',
             r'''(?s)<div[^>]+class=["']videoInfo(?:Date|Time)\b[^>]*>(.+?)</div>''',
             r'(?s)<label\b[^>]*>Uploaded[^<]*</label>\s*<span\b[^>]*>(.+?)</span>'),
            webpage, 'upload date', fatal=False))

        age_limit = self._rta_search(webpage)

        view_count = None
        views = self._search_regex(
            r'(<div [^>]*\bdata-value\s*=[^>]+>)\s*<label>Views:</label>',
            webpage, 'views', default=None)
        if views:
            view_count = parse_count(extract_attributes(views).get('data-value'))
        comment_count = parse_count(self._search_regex(
            r'>All [Cc]omments? \(([\d,.]+)\)',
            webpage, 'comment count', default=None))

        def extract_tag_box(regex, title):
            tag_box = self._search_regex(regex, webpage, title, default=None)
            if not tag_box:
                return []
            return re.findall(r'<a[^>]+href=[^>]+>([^<]+)', tag_box)

        categories = extract_tag_box(
            r'(?s)Categories:.*?</[^>]+>(.+?)</div>', 'categories')
        tags = extract_tag_box(
            r'(?s)Tags:.*?</div>\s*<div[^>]+class=["\']tagBoxContent["\'][^>]*>(.+?)</div>',
            'tags')

        data = self._search_json_ld(webpage, video_id, expected_type='VideoObject', fatal=False)
        data.pop('url', None)

        result = merge_dicts(data, {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'uploader': uploader,
            'upload_date': upload_date,
            'view_count': view_count,
            'comment_count': comment_count,
            'categories': categories,
            'tags': tags,
            'age_limit': age_limit,
            'formats': formats,
        })

        # Remove SEO spam "description"
        description = result.get('description')
        if description and description.startswith(f'Watch {result.get("title")} online'):
            del result['description']

        return result


class YouPornListBase(InfoExtractor):
    # pattern in '.title-text' element of page section containing videos
    _PLAYLIST_TITLEBAR_RE = r'\s+[Vv]ideos\s*$'
    _PAGE_RETRY_COUNT = 0  # ie, no retry
    _PAGE_RETRY_DELAY = 2  # seconds

    def _get_next_url(self, url, pl_id, html):
        return urljoin(url, self._search_regex(
            r'''<a [^>]*?\bhref\s*=\s*("|')(?P<url>(?:(?!\1)[^>])+)\1''',
            get_element_by_id('next', html) or '', 'next page',
            group='url', default=None))

    @classmethod
    def _get_title_from_slug(cls, title_slug):
        return re.sub(r'[_-]', ' ', title_slug)

    def _entries(self, url, pl_id, html=None, page_num=None):
        # separates page sections
        PLAYLIST_SECTION_RE = (
            r'''<div [^>]*\bclass\s*=\s*('|")(?:[\w$-]+\s+|\s)*?title-bar(?:\s+[\w$-]+|\s)*\1[^>]*>'''
        )
        # contains video link
        VIDEO_URL_RE = r'''(?x)
            <div [^>]*\bdata-video-id\s*=\s*('|")\d+\1[^>]*>\s*
            (?:<div\b[\s\S]+?</div>\s*)*
            <a\s[^>]*\bhref\s*=\s*('|")(?P<url>(?:(?!\2)[^>])+)\2
        '''

        def yield_pages(url, html=html, page_num=page_num):
            fatal = not html
            for pnum in itertools.count(start=page_num or 1):
                if not html:
                    html = self._download_webpage(
                        url, pl_id, note=f'Downloading page {pnum}', fatal=fatal)
                if not html:
                    break
                fatal = False
                yield (url, html, pnum)
                # explicit page: extract just that page
                if page_num is not None:
                    break
                next_url = self._get_next_url(url, pl_id, html)
                if not next_url or next_url == url:
                    break
                url, html = next_url, None

        def retry_page(msg, tries_left, page_data):
            if tries_left <= 0:
                return
            self.report_warning(msg, pl_id)
            self._sleep(self._PAGE_RETRY_DELAY, pl_id)
            return next(
                yield_pages(page_data[0], page_num=page_data[2]), None)

        def yield_entries(html):
            for frag in re.split(PLAYLIST_SECTION_RE, html):
                if not frag:
                    continue
                t_text = get_element_by_class('title-text', frag or '')
                if not (t_text and re.search(self._PLAYLIST_TITLEBAR_RE, t_text)):
                    continue
                for m in re.finditer(VIDEO_URL_RE, frag):
                    video_url = urljoin(url, m.group('url'))
                    if video_url:
                        yield self.url_result(video_url)

        last_first_url = None
        for page_data in yield_pages(url, html=html, page_num=page_num):
            # page_data: url, html, page_num
            first_url = None
            tries_left = self._PAGE_RETRY_COUNT + 1
            while tries_left > 0:
                tries_left -= 1
                for from_ in yield_entries(page_data[1]):
                    # may get the same page twice instead of empty page
                    # or (site bug) intead of actual next page
                    if not first_url:
                        first_url = from_['url']
                        if first_url == last_first_url:
                            # sometimes (/porntags/) the site serves the previous page
                            # instead but may provide the correct page after a delay
                            page_data = retry_page(
                                'Retrying duplicate page...', tries_left, page_data)
                            if page_data:
                                first_url = None
                                break
                            continue
                    yield from_
                else:
                    if not first_url and 'no-result-paragarph1' in page_data[1]:
                        page_data = retry_page(
                            'Retrying empty page...', tries_left, page_data)
                        if page_data:
                            continue
                    else:
                        # success/failure
                        break
            # may get an infinite (?) sequence of empty pages
            if not first_url:
                break
            last_first_url = first_url

    def _real_extract(self, url, html=None):
        m_dict = self._match_valid_url(url).groupdict()
        pl_id, page_type, sort = (m_dict.get(k) for k in ('id', 'type', 'sort'))
        qs = {k: v[-1] for k, v in parse_qs(url).items() if v}

        base_id = pl_id or 'YouPorn'
        title = self._get_title_from_slug(base_id)
        if page_type:
            title = f'{page_type.capitalize()} {title}'
        base_id = [base_id.lower()]
        if sort is None:
            title += ' videos'
        else:
            title = f'{title} videos by {re.sub(r"[_-]", " ", sort)}'
            base_id.append(sort)
        if qs:
            ps = ['%s=%s' % item for item in sorted(qs.items())]
            title += f' ({",".join(ps)})'
            base_id.extend(ps)
        pl_id = '/'.join(base_id)

        return self.playlist_result(
            self._entries(url, pl_id, html=html, page_num=int_or_none(qs.get('page'))),
            playlist_id=pl_id, playlist_title=title)


class YouPornCategoryIE(YouPornListBase):
    IE_DESC = 'YouPorn category, with sorting, filtering and pagination'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?youporn\.com/
        (?P<type>category)/(?P<id>[^/?#&]+)
        (?:/(?P<sort>popular|views|rating|time|duration))?/?(?:[#?]|$)
    '''
    _TESTS = [{
        'note': 'Full list with pagination',
        'url': 'https://www.youporn.com/category/popular-with-women/popular/',
        'info_dict': {
            'id': 'popular-with-women/popular',
            'title': 'Category popular with women videos by popular',
        },
        'playlist_mincount': 39,
    }, {
        'note': 'Filtered paginated list with single page result',
        'url': 'https://www.youporn.com/category/popular-with-women/duration/?min_minutes=10',
        'info_dict': {
            'id': 'popular-with-women/duration/min_minutes=10',
            'title': 'Category popular with women videos by duration (min_minutes=10)',
        },
        'playlist_mincount': 2,
        # 'playlist_maxcount': 30,
    }, {
        'note': 'Single page of full list',
        'url': 'https://www.youporn.com/category/popular-with-women/popular?page=1',
        'info_dict': {
            'id': 'popular-with-women/popular/page=1',
            'title': 'Category popular with women videos by popular (page=1)',
        },
        'playlist_count': 30,
    }]


class YouPornChannelIE(YouPornListBase):
    IE_DESC = 'YouPorn channel, with sorting and pagination'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?youporn\.com/
        (?P<type>channel)/(?P<id>[^/?#&]+)
        (?:/(?P<sort>rating|views|duration))?/?(?:[#?]|$)
    '''
    _TESTS = [{
        'note': 'Full list with pagination',
        'url': 'https://www.youporn.com/channel/x-feeds/',
        'info_dict': {
            'id': 'x-feeds',
            'title': 'Channel X-Feeds videos',
        },
        'playlist_mincount': 37,
    }, {
        'note': 'Single page of full list (no filters here)',
        'url': 'https://www.youporn.com/channel/x-feeds/duration?page=1',
        'info_dict': {
            'id': 'x-feeds/duration/page=1',
            'title': 'Channel X-Feeds videos by duration (page=1)',
        },
        'playlist_count': 24,
    }]

    @staticmethod
    def _get_title_from_slug(title_slug):
        return re.sub(r'_', ' ', title_slug).title()


class YouPornCollectionIE(YouPornListBase):
    IE_DESC = 'YouPorn collection (user playlist), with sorting and pagination'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?youporn\.com/
        (?P<type>collection)s/videos/(?P<id>\d+)
        (?:/(?P<sort>rating|views|time|duration))?/?(?:[#?]|$)
    '''
    _PLAYLIST_TITLEBAR_RE = r'^\s*Videos\s+in\s'
    _TESTS = [{
        'note': 'Full list with pagination',
        'url': 'https://www.youporn.com/collections/videos/33044251/',
        'info_dict': {
            'id': '33044251',
            'title': 'Collection Sexy Lips videos',
            'uploader': 'ph-littlewillyb',
        },
        'playlist_mincount': 50,
    }, {
        'note': 'Single page of full list (no filters here)',
        'url': 'https://www.youporn.com/collections/videos/33044251/time?page=1',
        'info_dict': {
            'id': '33044251/time/page=1',
            'title': 'Collection Sexy Lips videos by time (page=1)',
            'uploader': 'ph-littlewillyb',
        },
        'playlist_count': 20,
    }]

    def _real_extract(self, url):
        pl_id = self._match_id(url)
        html = self._download_webpage(url, pl_id)
        playlist = super(YouPornCollectionIE, self)._real_extract(url, html=html)
        infos = re.sub(r'\s+', ' ', clean_html(get_element_by_class(
            'collection-infos', html)) or '')
        title, uploader = self._search_regex(
            r'^\s*Collection: (?P<title>.+?) \d+ VIDEOS \d+ VIEWS \d+ days LAST UPDATED From: (?P<uploader>[\w_-]+)',
            infos, 'title/uploader', group=('title', 'uploader'), default=(None, None))
        if title:
            playlist.update({
                'title': playlist['title'].replace(playlist['id'].split('/')[0], title),
                'uploader': uploader,
            })

        return playlist


class YouPornTagIE(YouPornListBase):
    IE_DESC = 'YouPorn tag (porntags), with sorting, filtering and pagination'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?youporn\.com/
        porn(?P<type>tag)s/(?P<id>[^/?#&]+)
        (?:/(?P<sort>views|rating|time|duration))?/?(?:[#?]|$)
    '''
    _PLAYLIST_TITLEBAR_RE = r'^\s*Videos\s+tagged\s'
    _PAGE_RETRY_COUNT = 1
    _TESTS = [{
        'note': 'Full list with pagination',
        'url': 'https://www.youporn.com/porntags/austrian',
        'info_dict': {
            'id': 'austrian',
            'title': 'Tag austrian videos',
        },
        'playlist_mincount': 35,
        'expected_warnings': ['Retrying duplicate page'],
    }, {
        'note': 'Filtered paginated list with single page result',
        'url': 'https://www.youporn.com/porntags/austrian/duration/?min_minutes=10',
        'info_dict': {
            'id': 'austrian/duration/min_minutes=10',
            'title': 'Tag austrian videos by duration (min_minutes=10)',
        },
        'playlist_mincount': 10,
        # number of videos per page is (row x col) 2x3 + 6x4 + 2, or + 3,
        # or more, varying with number of ads; let's set max as 9x4
        # NB col 1 may not be shown in non-JS page with site CSS and zoom 100%
        # 'playlist_count': 32,
        'expected_warnings': ['Retrying duplicate page', 'Retrying empty page'],
    }, {
        'note': 'Single page of full list',
        'url': 'https://www.youporn.com/porntags/austrian/?page=1',
        'info_dict': {
            'id': 'austrian/page=1',
            'title': 'Tag austrian videos (page=1)',
        },
        'playlist_mincount': 32,
        # 'playlist_maxcount': 34,
        'expected_warnings': ['Retrying duplicate page', 'Retrying empty page'],
    }]

    # YP tag navigation is broken, loses sort
    def _get_next_url(self, url, pl_id, html):
        if next_url := super(YouPornTagIE, self)._get_next_url(url, pl_id, html):
            if n := self._match_valid_url(next_url):
                if s := n.groupdict().get('sort'):
                    if u := self._match_valid_url(url):
                        u = u.groupdict().get('sort')
                        if s and not u:
                            n = n.end('sort')
                            next_url = next_url[:n] + '/' + next_url[n:]
        return next_url


class YouPornStarIE(YouPornListBase):
    IE_DESC = 'YouPorn Pornstar, with description, sorting and pagination'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?youporn\.com/
        (?P<type>pornstar)/(?P<id>[^/?#&]+)
        (?:/(?P<sort>rating|views|duration))?/?(?:[#?]|$)
    '''
    _PLAYLIST_TITLEBAR_RE = r'^\s*Videos\s+[fF]eaturing\s'
    _TESTS = [{
        'note': 'Full list with pagination',
        'url': 'https://www.youporn.com/pornstar/daynia/',
        'info_dict': {
            'id': 'daynia',
            'title': 'Pornstar Daynia videos',
            'description': r're:Daynia Rank \d+ Videos \d+ Views [\d,.]+ .+ Subscribers \d+',
        },
        'playlist_mincount': 40,
    }, {
        'note': 'Single page of full list (no filters here)',
        'url': 'https://www.youporn.com/pornstar/daynia/?page=1',
        'info_dict': {
            'id': 'daynia/page=1',
            'title': 'Pornstar Daynia videos (page=1)',
            'description': 're:.{180,}',
        },
        'playlist_count': 26,
    }]

    @staticmethod
    def _get_title_from_slug(title_slug):
        return re.sub(r'_', ' ', title_slug).title()

    def _real_extract(self, url):
        pl_id = self._match_id(url)
        html = self._download_webpage(url, pl_id)
        playlist = super(YouPornStarIE, self)._real_extract(url, html=html)
        INFO_ELEMENT_RE = r'''(?x)
            <div [^>]*\bclass\s*=\s*('|")(?:[\w$-]+\s+|\s)*?pornstar-info-wrapper(?:\s+[\w$-]+|\s)*\1[^>]*>
            (?P<info>[\s\S]+?)(?:</div>\s*){6,}
        '''

        if infos := self._search_regex(INFO_ELEMENT_RE, html, 'infos', group='info', default=''):
            infos = re.sub(
                r'(?:\s*nl=nl)+\s*', ' ',
                re.sub(r'(?u)\s+', ' ', clean_html(re.sub('\n', 'nl=nl', infos)))).replace('ribe Subsc', '')

        return {
            **playlist,
            'description': infos.strip() or None,
        }


class YouPornVideosIE(YouPornListBase):
    IE_DESC = 'YouPorn video (browse) playlists, with sorting, filtering and pagination'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?youporn\.com/
            (?:(?P<id>browse)/)?
            (?P<sort>(?(id)
                (?:duration|rating|time|views)|
                (?:most_(?:favou?rit|view)ed|recommended|top_rated)?))
            (?:[/#?]|$)
    '''
    _PLAYLIST_TITLEBAR_RE = r'\s+(?:[Vv]ideos|VIDEOS)\s*$'
    _TESTS = [{
        'note': 'Full list with pagination (too long for test)',
        'url': 'https://www.youporn.com/',
        'info_dict': {
            'id': 'youporn',
            'title': 'YouPorn videos',
        },
        'only_matching': True,
    }, {
        'note': 'Full list with pagination (too long for test)',
        'url': 'https://www.youporn.com/recommended',
        'info_dict': {
            'id': 'youporn/recommended',
            'title': 'YouPorn videos by recommended',
        },
        'only_matching': True,
    }, {
        'note': 'Full list with pagination (too long for test)',
        'url': 'https://www.youporn.com/top_rated',
        'info_dict': {
            'id': 'youporn/top_rated',
            'title': 'YouPorn videos by top rated',
        },
        'only_matching': True,
    }, {
        'note': 'Full list with pagination (too long for test)',
        'url': 'https://www.youporn.com/browse/time',
        'info_dict': {
            'id': 'browse/time',
            'title': 'YouPorn videos by time',
        },
        'only_matching': True,
    }, {
        'note': 'Filtered paginated list with single page result',
        'url': 'https://www.youporn.com/most_favorited/?res=VR&max_minutes=2',
        'info_dict': {
            'id': 'youporn/most_favorited/max_minutes=2/res=VR',
            'title': 'YouPorn videos by most favorited (max_minutes=2,res=VR)',
        },
        'playlist_mincount': 10,
        # 'playlist_maxcount': 28,
    }, {
        'note': 'Filtered paginated list with several pages',
        'url': 'https://www.youporn.com/most_favorited/?res=VR&max_minutes=5',
        'info_dict': {
            'id': 'youporn/most_favorited/max_minutes=5/res=VR',
            'title': 'YouPorn videos by most favorited (max_minutes=5,res=VR)',
        },
        'playlist_mincount': 45,
    }, {
        'note': 'Single page of full list',
        'url': 'https://www.youporn.com/browse/time?page=1',
        'info_dict': {
            'id': 'browse/time/page=1',
            'title': 'YouPorn videos by time (page=1)',
        },
        'playlist_count': 36,
    }]

    @staticmethod
    def _get_title_from_slug(title_slug):
        return 'YouPorn' if title_slug == 'browse' else title_slug
