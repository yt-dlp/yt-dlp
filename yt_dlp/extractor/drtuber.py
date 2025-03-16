import re

from .common import InfoExtractor
from ..utils import (
    NO_DEFAULT,
    int_or_none,
    parse_duration,
    strip_or_none,
    str_to_int,
    url_or_none,
)


class DrTuberIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|m)\.)?(?P<domain>drtuber|iceporn|nuvid)\.com/(?:video|embed)/(?P<id>\d+)(?:/(?P<display_id>[\w-]+))?'
    _EMBED_REGEX = [r'<iframe[^>]+?src=["\'](?P<url>(?:https?:)?//(?:www\.)?(?:drtuber|iceporn|nuvid)\.com/embed/\d+)']
    _TESTS = [{
        'url': 'http://www.drtuber.com/video/1740434/hot-perky-blonde-naked-golf',
        'md5': '93e680cf2536ad0dfb7e74d94a89facd',
        'info_dict': {
            'id': '1740434',
            'display_id': 'hot-perky-blonde-naked-golf',
            'ext': 'mp4',
            'title': 'hot perky blonde naked golf',
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'categories': ['babe', 'blonde', 'erotic', 'outdoor', 'softcore', 'solo'],
            'thumbnail': r're:https?://.*\.jpg$',
            'age_limit': 18,
            'duration': 304,
            'description': 'Welcome to this hot porn video named Hot Perky Blonde Naked Golf. DrTuber is the best place for watching xxx movies online!'
        },
    }, {
        'url': 'https://www.iceporn.com/video/2296835/eva-karera-gets-her-trimmed-cunt-plowed',
        'md5': '88be0402a06e61cd1dfaea69dc8623a7',
        'info_dict': {
            'id': '2296835',
            'display_id': 'eva-karera-gets-her-trimmed-cunt-plowed',
            'title': 'Eva Karera gets her trimmed cunt plowed',
            'description': 're:Eva Karera Gets Her Trimmed Cunt Plowed - Pornstar, Milf, Blowjob, Big Boobs Porn Movies - 2296835',
            'thumbnail': 're:https?://g\\d.iceppsn.com/media/videos/tmb/\\d+/preview/\\d+.jpg',
            'ext': 'mp4',
            'duration': 2178,
            'age_limit': 18,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'categories': ['Big Boobs', 'Blowjob', 'Brunette', 'Doggystyle', 'Hardcore', 'Hd', 'Lingerie', 'Masturbation', 'Milf', 'Pornstar', 'Titjob'],
        },
    }, {
        'url': 'https://www.nuvid.com/video/6513023/italian-babe',
        'md5': '772d2f8288f3d3c5c45f7a41761c7844',
        'info_dict': {
            'id': '6513023',
            'display_id': 'italian-babe',
            'description': 'Welcome to this hot Italian porn video named Italian Babe. Nuvid is the best place for watching xxx movies online!',
            'ext': 'mp4',
            'title': 'italian babe',
            'duration': 321.0,
            'age_limit': 18,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpg',
            'categories': ['Amateur', 'BBW', 'Brunette', 'Fingering', 'Italian', 'Softcore', 'Solo', 'Webcam'],
        },
    }, {
        'url': 'https://m.nuvid.com/video/6523263',
        'md5': 'ebd22ce8e47e1d9a4d0756a15c67da52',
        'info_dict': {
            'id': '6523263',
            'display_id': '6523263',
            'ext': 'mp4',
            'title': 'Slut brunette college student anal dorm',
            'description': 'Welcome to this hot Brunette porn video named Slut Brunette College Student Anal Dorm. Nuvid is the best place for watching xxx movies online!',
            'duration': 421.0,
            'age_limit': 18,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpg',
            'thumbnails': list,
            'categories': list,
        },
    }, {
        'url': 'http://m.nuvid.com/video/6415801/',
        'md5': '638d5ececb138d5753593f751ae3f697',
        'info_dict': {
            'id': '6415801',
            'display_id': '6415801',
            'ext': 'mp4',
            'title': 'My best friend wanted to fuck my wife for a long time',
            'description': 'Welcome to this hot Redhead porn video named My Best Friend Wanted To Fuck My Wife For A Long Time. Nuvid is the best place for watching xxx movies online!',
            'duration': 1882,
            'age_limit': 18,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://.+\.jpg',
            'categories': list,
        },
    }, {
        'url': 'http://www.drtuber.com/embed/489939',
        'only_matching': True,
    }, {
        'url': 'https://www.iceporn.com/video/2296835',
        'only_matching': True,
    }, {
        'url': 'https://www.nuvid.com/video/6513023',
        'only_matching': True,
    }, {
        'url': 'http://m.drtuber.com/video/3893529/lingerie-blowjob-from-beautiful-teen',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id, display_id, domain = mobj.group('id', 'display_id', 'domain')
        display_id = display_id or video_id

        webpage = self._download_webpage(
            f'http://www.{domain}.com/video/{video_id}', display_id)

        video_data = self._download_json(
            f'http://www.{domain}.com/player_config_json/', video_id, query={
                'vid': video_id,
                'embed': 0,
                'aid': 0,
                'domain_id': 0,
            }, headers={
                'Accept': 'application/json',
            })

        qualities = {
            'lq': '360p',
            'hq': '720p',
            '4k': '2160p',
        }

        formats = []
        for format_id, video_url in video_data['files'].items():
            if video_url:
                formats.append({
                    'format_id': format_id,
                    'quality': qualities.get(format_id) or format_id,
                    'height': int_or_none(qualities.get(format_id)[:-1]),
                    'url': video_url,
                })
        self._check_formats(formats, video_id)

        duration = int_or_none(video_data.get('duration')) or parse_duration(
            video_data.get('duration_format'))

        title = video_data.get('title') or self._html_search_regex(
            (r'<div.*class=[\'"]caption[\'"].*?><h2>(.+?)</h2>',
             r'<h1[^>]+class=["\']title[^>]+>([^<]+)',
             r'<title>([^<]+)\s*@\s+DrTuber',
             r'class="title_watch"[^>]*><(?:p|h\d+)[^>]*>([^<]+)<',
             r'<p[^>]+class="title_substrate">([^<]+)</p>',
             r'<title>([^<]+) - \d+'),
            webpage, 'title')

        mobile_webpage = None
        if not title:
            mobile_webpage = self._download_webpage(
                f'http://m.{domain}.com/video/{video_id}',
                video_id, 'Downloading mobile video page', fatal=False) or ''

            title = strip_or_none(video_data.get('title') or self._html_search_regex(
                (r'''<span\s[^>]*?\btitle\s*=\s*(?P<q>"|'|\b)(?P<title>[^"]+)(?P=q)\s*>''',
                    r'''<div\s[^>]*?\bclass\s*=\s*(?P<q>"|'|\b)thumb-holder video(?P=q)>\s*<h5\b[^>]*>(?P<title>[^<]+)</h5''',
                    r'''<span\s[^>]*?\bclass\s*=\s*(?P<q>"|'|\b)title_thumb(?P=q)>(?P<title>[^<]+)</span'''),
                mobile_webpage, 'title', group='title'))

        thumbnails = []
        if not mobile_webpage:
            mobile_webpage = self._download_webpage(
                f'http://m.{domain}.com/video/{video_id}',
                video_id, 'Downloading mobile video page', fatal=False) or ''

            thumbnails = [
                {'url': thumb_url} for thumb_url in re.findall(
                    r'<div\s+class\s*=\s*"video-tmb-wrap"\s*>\s*<img\s+src\s*=\s*"([^"]+)"\s*/>', mobile_webpage)
                if url_or_none(thumb_url)]

        if url_or_none(video_data.get('poster')):
            thumbnails.append({'url': video_data['poster'], 'preference': 1})

        def extract_count(id_, name, default=NO_DEFAULT):
            return str_to_int(self._html_search_regex(
                rf'<span[^>]+(?:class|id)="{id_}"[^>]*>(?P<{name}>[\d,\.]+)</span>',
                webpage, f'{name} count', default=default, fatal=False, group=name))

        like_count = extract_count('(?:rate_likes|rate_votes|video_rate_votes)', 'like')
        dislike_count = extract_count('(?:rate_dislikes|rate_votes|video_rate_votes)', 'dislike', default=None)
        comment_count = extract_count('(?:comments_count|comments__counter)', 'comment')

        cats_str = self._search_regex(
            r'<div[^>]+class="(?:categories_list|data_categories|video-cat)">(.+?)</div>',
            webpage, 'categories', fatal=False)

        categories = None
        if cats_str:
            for pattern in [r'<a[^>]+title="([^"]+)"', r'<a[^>]+href="/categories/([^"]+)"']:
                categories = re.findall(pattern, cats_str)
                if categories:
                    break

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'title': title,
            'thumbnails': thumbnails,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'comment_count': comment_count,
            'categories': categories,
            'age_limit': self._rta_search(webpage),
            'duration': duration,
            'description': self._html_search_meta('description', webpage),
        }
