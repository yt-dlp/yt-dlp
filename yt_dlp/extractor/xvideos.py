import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    int_or_none,
    parse_duration,
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

        mobj = re.search(r'<h1 class="inlineError">(.+?)</h1>', webpage)
        if mobj:
            raise ExtractorError(f'{self.IE_NAME} said: {clean_html(mobj.group(1))}', expected=True)

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
