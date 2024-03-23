import re
import itertools

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_str,
    compat_urlparse,
    compat_urllib_parse_unquote,
    compat_urllib_parse_urlencode,
)
from ..utils import (
    clean_html,
    determine_ext,
    extract_attributes,
    ExtractorError,
    int_or_none,
    parse_duration,
    try_get,
    url_basename,
    urljoin,
)


class XVideosIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:[^/]+\.)?xvideos2?\.com/video\.?|
                            (?:www\.)?xvideos\.es/video\.?|
                            (?:www|flashservice)\.xvideos\.com/embedframe/|
                            static-hw\.xvideos\.com/swf/xv-player\.swf\?.*?\bid_video=
                        )
                        (?P<id>[0-9a-z]+)
                    '''
    _TESTS = [{
        'url': 'http://xvideos.com/video.ucuvbkfda4e/a_beautiful_red-haired_stranger_was_refused_but_still_came_to_my_room_for_sex',
        'md5': '396255a900a6bddb3e98985f0b86c3fd',
        'info_dict': {
            'id': 'ucuvbkfda4e',
            'ext': 'mp4',
            'title': 'A Beautiful Red-Haired Stranger Was Refused, But Still Came To My Room For Sex',
            'duration': 1238,
            'age_limit': 18,
            'thumbnail': r're:^https://cdn\d+-pic.xvideos-cdn.com/.+\.jpg',
        }
    }, {
        # Broken HLS formats
        'url': 'https://www.xvideos.com/video65982001/what_s_her_name',
        'md5': '56742808292c8fa1418e4538c262c58b',
        'info_dict': {
            'id': '65982001',
            'ext': 'mp4',
            'title': 'what\'s her name?',
            'duration': 120,
            'age_limit': 18,
            'thumbnail': r're:^https://cdn\d+-pic.xvideos-cdn.com/.+\.jpg',
        }
    }, {
        'url': 'https://flashservice.xvideos.com/embedframe/4588838',
        'only_matching': True,
    }, {
        'url': 'https://www.xvideos.com/embedframe/4588838',
        'only_matching': True,
    }, {
        'url': 'http://static-hw.xvideos.com/swf/xv-player.swf?id_video=4588838',
        'only_matching': True,
    }, {
        'url': 'http://xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://www.xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://www.xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://fr.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://fr.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://it.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://it.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'http://de.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://de.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True
    }, {
        'url': 'https://flashservice.xvideos.com/embedframe/ucuvbkfda4e',
        'only_matching': True,
    }, {
        'url': 'https://www.xvideos.com/embedframe/ucuvbkfda4e',
        'only_matching': True,
    }, {
        'url': 'http://static-hw.xvideos.com/swf/xv-player.swf?id_video=ucuvbkfda4e',
        'only_matching': True,
    }, {
        'url': 'https://xvideos.es/video.ucuvbkfda4e/a_beautiful_red-haired_stranger_was_refused_but_still_came_to_my_room_for_sex',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        mobj = re.search(r'<h1 class="inlineError">(.+?)</h1>', webpage)
        if mobj:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, clean_html(mobj.group(1))), expected=True)

        title = self._html_search_regex(
            (r'<title>(?P<title>.+?)\s+-\s+XVID',
             r'setVideoTitle\s*\(\s*(["\'])(?P<title>(?:(?!\1).)+)\1'),
            webpage, 'title', default=None,
            group='title') or self._og_search_title(webpage)

        thumbnails = []
        for preference, thumbnail in enumerate(('', '169')):
            thumbnail_url = self._search_regex(
                r'setThumbUrl%s\(\s*(["\'])(?P<thumbnail>(?:(?!\1).)+)\1' % thumbnail,
                webpage, 'thumbnail', default=None, group='thumbnail')
            if thumbnail_url:
                thumbnails.append({
                    'url': thumbnail_url,
                    'preference': preference,
                })

        duration = int_or_none(self._og_search_property(
            'duration', webpage, default=None)) or parse_duration(
            self._search_regex(
                r'<span[^>]+class=["\']duration["\'][^>]*>.*?(\d[^<]+)',
                webpage, 'duration', fatal=False))

        formats = []

        video_url = compat_urllib_parse_unquote(self._search_regex(
            r'flv_url=(.+?)&', webpage, 'video URL', default=''))
        if video_url:
            formats.append({
                'url': video_url,
                'format_id': 'flv',
            })

        for kind, _, format_url in re.findall(
                r'setVideo([^(]+)\((["\'])(http.+?)\2\)', webpage):
            format_id = kind.lower()
            if format_id == 'hls':
                hls_formats = self._extract_m3u8_formats(
                    format_url, video_id, 'mp4',
                    entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)
                self._check_formats(hls_formats, video_id)
                formats.extend(hls_formats)
            elif format_id in ('urllow', 'urlhigh'):
                formats.append({
                    'url': format_url,
                    'format_id': '%s-%s' % (determine_ext(format_url, 'mp4'), format_id[3:]),
                    'quality': -2 if format_id.endswith('low') else None,
                })

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'duration': duration,
            'thumbnails': thumbnails,
            'age_limit': 18,
        }


class XVideosPlaylistIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:[^/]+\.)?xvideos2?\.com/
                          (?:c(?:/[sm]:[^/]+)*|
                             profiles|
                             favorite)/
                            (?P<id>[^#?/]+)
                  '''
    _TESTS = []

    def _extract_videos_from_json_list(self, json_list, path='video'):
        return (
            'https://www.xvideos.com/%s%d/%s' % (path, x.get('id'), str(x.get('u')).split('/')[-1])
            for x in json_list if isinstance(x, dict))

    def _get_playlist_url(self, url, playlist_id):
        """URL of first playlist page"""
        id_match = re.match(self._VALID_URL, url).groupdict()
        video_sort = id_match.get('sort')
        if video_sort:
            url, _ = compat_urlparse.urldefrag(url)
            if url.endswith('/'):
                url = url[:-1]
            url = '%s/%s' % (url, video_sort.replace('-', '/'))
        return url

    def _get_next_page(self, url, num, page):
        '''URL of num'th continuation page of url'''
        if page.startswith('{'):
            url, sub = re.subn(r'(/)(\d{1,7})($|[#?/])', r'\g<1>%d\3' % (num, ), url)
            if sub == 0:
                url += '/%d' % (num, )
            return url
        next_page = self._search_regex(
            r'''(?s)(<a\s[^>]*?\bclass\s*=\s*(?P<q>'|").*?\bnext-page\b.*?(?P=q)[^>]*?>)''',
            page, 'next page', default=None)
        if next_page:
            next_page = extract_attributes(next_page)
            next_page = next_page.get('href')
            if next_page:
                return urljoin(url, next_page)
        return False

    def _extract_videos(self, url, playlist_id, num, page):
        """Get iterable videos plus stop flag"""
        return ((
            'https://www.xvideos.com/video' + x.group('video_id')
            for x in re.finditer(r'''class\s*=\s*"title"\s*>\s*<\s*a\s*href\s*=\s*(\'|")\/video(?P<video_id>(.*?))\1''', page)),
            None)

    def _real_extract(self, url):
        id_match = re.match(self._VALID_URL, url).groupdict()
        playlist_id = id_match['id']
        if "video" in playlist_id and url.endswith(playlist_id):
            url += '/0'

        next_page = self._get_playlist_url(url, playlist_id)

        if id_match['quickiesid']:
            return self.url_result(next_page, XVideosIE)

        matches = []
        for count in itertools.count(0):
            webpage = self._download_webpage(
                next_page,
                '%s (+%d)' % (playlist_id, count) if count > 0 else playlist_id)

            vids, stop = self._extract_videos(next_page, playlist_id, count, webpage)

            if vids:
                matches.append(vids)

            if stop:
                break
            next_page = self._get_next_page(next_page, count + 1, webpage)
            if not next_page:
                break

        return self.playlist_from_matches(
            itertools.chain.from_iterable(matches), playlist_id)


class XVideosRelatedIE(XVideosPlaylistIE):
    _VALID_URL = XVideosIE._VALID_URL + r'(?:/[^/]+)*?\#_related-(?P<related>videos|playlists)'

    _TESTS = []

    def _extract_videos(self, url, playlist_id, num, page):
        id_match = re.match(self._VALID_URL, url).groupdict()
        related = id_match.get('related')
        if not related:
            return super(XVideosRelatedIE, self)._extract_videos(url, playlist_id, num, page)

        if related == 'videos':
            related_json = self._search_regex(
                r'(?s)videos_related\s*=\s*(\[.*?])\s*;',
                page, 'related', default='[]')
            related_json = self._parse_json(related_json, playlist_id, fatal=False) or []
            return (self._extract_videos_from_json_list(related_json), True)
        # playlists
        related_json = self._download_json(
            'https://www.xvideos.com/video-playlists/' + playlist_id, playlist_id, fatal=False)
        return (
            self._extract_videos_from_json_list(
                try_get(related_json, lambda x: x['playlists'], list) or [],
                path='favorite/'),
            True)


class XVideosChannelIE(XVideosPlaylistIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:[^/]+\.)?xvideos2?\.com/
                          (?:
                             (?:amateur-|pornstar-|model-)?channel|profile|
                             pornstar|model|amateur
                          )s/
                            (?P<id>[^#?/]+)
                              (?:\#_tab(?P<tab>Videos|Favorites|Playlists|AboutMe)(?:,(?P<sort>[^,]+))?)?
                              (?:\#quickies/a/(?P<quickiesid>.*))?
                 '''
    _TESTS = [{
        'url': 'https://www.xvideos.com/pornstar-channels/sienna-west',
        'playlist_mincount': 5,
    }, {
        'url': 'https://www.xvideos.com/pornstars/silvia-jons#_tabVideos',
        'playlist_mincount': 5,
    }, {
        'url': 'https://www.xvideos.com/channels/miss_floyd#_tabVideos',
        'playlist_mincount': 5,
    }, {
        'url': 'https://www.xvideos.com/models/migurt-1',
        'playlist_mincount': 5,
    }, {
        'url': 'https://www.xvideos.com/amateur-channels/wifeluna#quickies/a/47258683',
        'playlist_mincount': 5,
    }, ]

    def _get_playlist_url(self, url, playlist_id):
        webpage = self._download_webpage(url, playlist_id)
        id_match = re.match(self._VALID_URL, url).groupdict()
        tab = (id_match.get('tab') or '').lower()
        quickiesid = (id_match.get('quickiesid') or '').lower()

        if not tab and not quickiesid:
            url += '#_tabVideos'

        if tab and not quickiesid:
            if tab in ('videos', 'favorites'):
                url, frag = compat_urlparse.urldefrag(url)
                if not url.endswith('/'):
                    url += '/'
                frag = frag.split(',')
                url += tab
                if tab == 'videos':
                    url += '/' + (frag[1] if len(frag) > 1 else 'best')
                url += '/0'
            return url

        elif quickiesid:
            url = f'https://www.xvideos.com/video{quickiesid}/_'
            return url

        # activity
        conf = self._search_regex(
            r'(?s)\.\s*xv\s*\.\s*conf\s*=\s*(\{.*?})[\s;]*</script',
            webpage, 'XV conf')
        conf = self._parse_json(conf, playlist_id)
        act = try_get(conf,
                      ((lambda x: x['dyn'][y])
                       for y in ('page_main_cat', 'user_main_cat')),
                      compat_str) or 'straight'

        url, _ = compat_urlparse.urldefrag(url)
        if url.endswith('/'):
            url = url[:-1]

        return '%s/activity/%s' % (url, act, )

    def _get_next_page(self, url, num, page):
        if page.startswith('{') or '#_tab' in url:
            return super(XVideosChannelIE, self)._get_next_page(url, num, page)

        act_time = int_or_none(url_basename(url)) or 0
        last_act = int(self._search_regex(
            r'(?s)id\s*=\s*"?activity-event-(\d{10})(?!.*id\s*=\s*"?activity-event-\d+.*).+$',
            page, 'last activity', default=act_time))
        if last_act == act_time:
            return False
        return (
            url.replace('/%d' % (act_time, ), '/%d' % (last_act, ))
            if act_time
            else url + ('/%d' % (last_act, )))

    def _extract_videos(self, url, playlist_id, num, page):
        tab = next((x for x in ('videos', 'favorites') if '/%s/' % (x, ) in url), None)
        if tab == 'videos':
            tab_json = self._parse_json(page, playlist_id, fatal=False) or {}
            more = try_get(tab_json, lambda x: x['current_page'] + 1, int)
            more = int_or_none(more, scale=tab_json.get('nb_videos'), invscale=tab_json.get('nb_per_page'), default=0)
            return (
                self._extract_videos_from_json_list(
                    try_get(tab_json, lambda x: x['videos'], list) or []),
                more > 0)

        if tab == 'favorites':
            return ((
                'https://www.xvideos.com' + x.group('playlist')
                for x in re.finditer(r'''<a\s[^>]*?href\s*=\s*('|")(?P<playlist>/favorite/\d+/[^#?]+?)\1''', page)),
                None)

        return super(XVideosChannelIE, self)._extract_videos(url, playlist_id, num, page)


class XVideosSearchIE(XVideosPlaylistIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:[^/]+\.)?xvideos2?\.com/
                          \?k=(?P<id>[^#?/&]+)
                 '''
    _TESTS = [{
        # uninteresting search with probably at least two pages of results,
        # but not too many more
        'url': 'http://www.xvideos.com/?k=libya&sort=length',
        'playlist_mincount': 30,
    }, ]

    def _get_next_page(self, url, num, page):
        parsed_url = compat_urlparse.urlparse(url)
        qs = compat_parse_qs(parsed_url.query)
        qs['p'] = [num]
        parsed_url = (
            list(parsed_url[:4])
            + [compat_urllib_parse_urlencode(qs, True), None])
        return compat_urlparse.urlunparse(parsed_url), False
