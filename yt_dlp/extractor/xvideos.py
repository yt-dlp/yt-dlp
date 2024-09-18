import functools
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    determine_ext,
    get_element_by_class,
    get_element_by_id,
    int_or_none,
    js_to_json,
    parse_duration,
    remove_end,
    str_or_none,
)
from ..utils.traversal import traverse_obj


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
        },
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
        },
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
        'only_matching': True,
    }, {
        'url': 'https://xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'https://xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'https://www.xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'http://xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'http://www.xvideos.es/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'http://fr.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'https://fr.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'http://it.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'https://it.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'http://de.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True,
    }, {
        'url': 'https://de.xvideos.com/video4588838/biker_takes_his_girl',
        'only_matching': True,
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
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if inline_error := get_element_by_class('inlineError', webpage):
            raise ExtractorError(f'{self.IE_NAME} said: {clean_html(inline_error)}', expected=True)

        title = self._html_search_regex(
            (r'<title>(?P<title>.+?)\s+-\s+XVID',
             r'setVideoTitle\s*\(\s*(["\'])(?P<title>(?:(?!\1).)+)\1'),
            webpage, 'title', default=None,
            group='title') or self._og_search_title(webpage)

        thumbnails = []
        for preference, thumbnail in enumerate(('', '169')):
            thumbnail_url = self._search_regex(
                rf'setThumbUrl{thumbnail}\(\s*(["\'])(?P<thumbnail>(?:(?!\1).)+)\1',
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

        video_url = urllib.parse.unquote(self._search_regex(
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
                    'format_id': '{}-{}'.format(determine_ext(format_url, 'mp4'), format_id[3:]),
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


class XVideosQuickiesIE(InfoExtractor):
    IE_NAME = 'xvideos:quickies'
    _VALID_URL = r'https?://(?P<domain>(?:[^/?#]+\.)?xvideos2?\.com)/(?:profiles/|amateur-channels/)?[^/?#]+#quickies/a/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.xvideos.com/lili_love#quickies/a/ipdtikh1a4c',
        'md5': 'f9e4f518ff1de14b99a400bbd0fc5ee0',
        'info_dict': {
            'id': 'ipdtikh1a4c',
            'ext': 'mp4',
            'title': 'Mexican chichóna putisima',
            'age_limit': 18,
            'duration': 81,
            'thumbnail': r're:^https://cdn.*-pic.xvideos-cdn.com/.+\.jpg',
        },
    }, {
        'url': 'https://www.xvideos.com/profiles/lili_love#quickies/a/ipphaob6fd1',
        'md5': '5340938aac6b46e19ebdd1d84535862e',
        'info_dict': {
            'id': 'ipphaob6fd1',
            'ext': 'mp4',
            'title': 'Puta chichona mexicana squirting',
            'age_limit': 18,
            'duration': 56,
            'thumbnail': r're:^https://cdn.*-pic.xvideos-cdn.com/.+\.jpg',
        },
    }, {
        'url': 'https://www.xvideos.com/amateur-channels/lili_love#quickies/a/hfmffmd7661',
        'md5': '92428518bbabcb4c513e55922e022491',
        'info_dict': {
            'id': 'hfmffmd7661',
            'ext': 'mp4',
            'title': 'Chichona mexican slut',
            'age_limit': 18,
            'duration': 9,
            'thumbnail': r're:^https://cdn.*-pic.xvideos-cdn.com/.+\.jpg',
        },
    }, {
        'url': 'https://www.xvideos.com/amateur-channels/wifeluna#quickies/a/47258683',
        'md5': '16e322a93282667f1963915568f782c1',
        'info_dict': {
            'id': '47258683',
            'ext': 'mp4',
            'title': 'Verification video',
            'age_limit': 18,
            'duration': 16,
            'thumbnail': r're:^https://cdn.*-pic.xvideos-cdn.com/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        domain, id_ = self._match_valid_url(url).group('domain', 'id')
        return self.url_result(f'https://{domain}/video{"" if id_.isdecimal() else "."}{id_}/_', XVideosIE, id_)


class XVideosUserIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:.+?\.)?xvideos\.(?:com|es)/
        (?P<page_path>(?:channels|amateur-channels|model-channels|pornstar-channels|profiles)/
        (?P<id>[^/?#&]+))(?:(?:(?!\#quickies).)+)?$'''
    _TESTS = [{
        # channel; "Most viewed"
        'url': 'https://www.xvideos.com/channels/college_girls_gone_bad#_tabVideos,rating',
        'info_dict': {
            'id': '70472676',
            'display_id': 'college_girls_gone_bad',
            'title': 'College Girls Gone Bad',
            'description': 'Hot college girls in real sorority hazing acts!',
            'thumbnails': 'count:2',
        },
        'playlist_mincount': 99,
    }, {
        # channel; "New"
        'url': 'https://www.xvideos.com/model-channels/shonariver#_tabVideos,new',
        'info_dict': {
            'id': '407014987',
            'display_id': 'shonariver',
            'title': 'Shona River',
            'description': 'md5:ad6654037aee13535b0d15a020eb82d0',
            'thumbnails': 'count:2',
        },
        'playlist_mincount': 9,
    }, {
        # channel; "Most commented"
        'url': 'https://www.xvideos.com/amateur-channels/queanfuckingcucking#_tabVideos,comments',
        'info_dict': {
            'id': '227800369',
            'display_id': 'queanfuckingcucking',
            'title': 'Queanfuckingcucking',
            'description': 'md5:265a602186d4e811082782cd6a97b064',
            'thumbnails': 'count:2',
        },
        'playlist_mincount': 8,
    }, {
        # channel; "Watched recently" (default)
        'url': 'https://www.xvideos.com/channels/girlfriendsfilmsofficial#_tabVideos',
        'info_dict': {
            'id': '244972019',
            'display_id': 'girlfriendsfilmsofficial',
            'title': 'Girlfriend\'s Films Official',
            'thumbnails': 'count:2',
        },
        'playlist_mincount': 500,
    }, {
        # /profiles/***
        'url': 'https://www.xvideos.com/profiles/jacobsy',
        'info_dict': {
            'id': '962189',
            'display_id': 'jacobsy',
            'title': 'Jacobsy',
            'description': 'fetishist and bdsm lover...',
            'thumbnails': 'count:2',
        },
        'playlist_mincount': 63,
    }, {
        # no description, no videos
        'url': 'https://www.xvideos.com/profiles/espoder',
        'info_dict': {
            'id': '581228107',
            'display_id': 'espoder',
            'title': 'Espoder',
            'thumbnails': 'count:2',
        },
        'playlist_count': 0,
    }, {
        # no description
        'url': 'https://www.xvideos.com/profiles/alfsun',
        'info_dict': {
            'id': '551066909',
            'display_id': 'alfsun',
            'title': 'Alfsun',
            'thumbnails': 'count:2',
        },
        'playlist_mincount': 3,
    }]
    _PAGE_SIZE = 36

    def _real_extract(self, url):
        page_path, display_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, display_id)

        fragment = urllib.parse.urlparse(url).fragment
        sort_order = traverse_obj(
            ['new', 'rating', 'comments'], (lambda _, v: v in fragment), default='best', get_all=False)
        page_base_url = f'https://www.xvideos.com/{page_path}/videos/{sort_order}'

        user_info = traverse_obj(self._search_json(
            r'<script>.*?window\.xv\.conf\s*=', webpage, 'xv.conf',
            display_id, transform_source=js_to_json, fatal=False), ('data', 'user'))
        user_id = traverse_obj(user_info, ('id_user', {str_or_none})) or display_id

        return self.playlist_result(
            OnDemandPagedList(functools.partial(self._get_page, page_base_url, user_id), self._PAGE_SIZE),
            user_id, traverse_obj(user_info, ('display', {str_or_none})),
            remove_end(clean_html(get_element_by_id('header-about-me', webpage)), '+'),
            display_id=(traverse_obj(user_info, ('username', {str_or_none})) or display_id),
            thumbnails=traverse_obj(user_info, (['profile_picture_small', 'profile_picture'], {lambda x: {'url': x}})))

    def _get_page(self, page_base_url, user_id, page_num):
        page_info = self._download_json(
            f'{page_base_url}/{page_num}', user_id, f'Downloading page {page_num + 1}')
        yield from [self.url_result(
            f'https://www.xvideos.com/video{video["id"]}/{video["eid"]}', ie=XVideosIE.ie_key())
            for video in page_info['videos']]
