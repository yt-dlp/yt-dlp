import re

from .common import InfoExtractor
from ..utils import (
    NO_DEFAULT,
    clean_html,
    determine_ext,
    int_or_none,
    str_to_int,
)


class XNXXIE(InfoExtractor):
    _VALID_URL = r'https?://(?:video|www)\.xnxx3?\.com/video-?(?P<id>[0-9a-z]+)/'
    _TESTS = [{
        'url': 'https://www.xnxx.com/video-u0yn555/chubby_mature_in_swimsuit',
        'md5': '25f139121ff1c414b06a90d8772249ce',
        'info_dict': {
            'id': 'u0yn555',
            'ext': 'mp4',
            'title': 'Chubby Mature in Swimsuit',
            'description': 'Getting wet in a tight one piece swimsuit.',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 157,
            'view_count': int,
            'tags': ['sexy', 'milf', 'mature', 'chubby', 'wet', 'swimsuit', 'pawg', 'one piece'],
            'age_limit': 18,
        },
    }, {
        'url': 'http://www.xnxx.com/video-55awb78/skyrim_test_video',
        'md5': 'f684f53b17babb6a69880d0cd88b33f5',
        'info_dict': {
            'id': '55awb78',
            'ext': 'mp4',
            'title': 'Skyrim Test Video',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 469,
            'view_count': int,
            'age_limit': 18,
        },
    }, {
        'url': 'http://video.xnxx.com/video1135332/lida_naked_funny_actress_5_',
        'only_matching': True,
    }, {
        'url': 'http://www.xnxx.com/video-55awb78/',
        'only_matching': True,
    }, {
        'url': 'http://www.xnxx3.com/video-55awb78/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        def get(meta, default=NO_DEFAULT, fatal=True):
            return self._search_regex(
                rf'set{meta}\s*\(\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
                webpage, meta, default=default, fatal=fatal, group='value')

        def extract_description():
            # <p class="metadata-row video-description">\nGetting wet in a tight one piece swimsuit.\n</p>
            desc = self._search_regex(
                r'(?s)<p[^>]+\bclass=["\'].*?video-description[^>]*?>\s*(.+?)\s*</p>',
                webpage, 'description', default=None)
            if desc:
                # <a class="is-keyword" href="/search/licking">licking</a>
                return clean_html(desc).strip()

        def extract_tags():
            # <div class="metadata-row video-tags">
            div = self._search_regex(
                r'(?s)<div[^>]+\bclass=["\'].*?video-tags[^>]*?>(.+?)</div>',
                webpage, 'tags', default=None)
            if div:
                # <a class="is-keyword" href="/search/licking">licking</a>
                return [clean_html(x).strip() for x in re.findall(r'(?s)<a[^>]+\bclass=["\'].*?is-keyword[^>]+\bhref=[^>]+>.+?</a>', div)]

        def extract_view_count():
            # <div class="video-title-container">
            #   <div class="video-title">
            #     <strong>Skyrim Test Video</strong>
            #     ...
            #     <span class="metadata">
            #        <a class="free-plate" href="/porn-maker/glurp">Glurp</a>						8min
            #   	1080p					- 671,137 <span class="icon-f icf-eye"></span>					</span>
            # </div>
            match = self._search_regex(
                r'(?s)<div[^>]+?\bclass=["\'][^>]*?video-title-container\b[^>]*>.+?<span[^>]+?\bclass=["\'][^>]*?metadata\b[^>]*>.*?\s(\d{1,3}(?:,\d{3})*)\s*<span[^>]+?\bclass=["\'][^>]*?icf-eye\b[^>]*>.*?</a>.*?</div>',
                webpage, 'view_count_outer_div', default=None)
            if match:
                return str_to_int(match)

        title = self._og_search_title(
            webpage, default=None) or get('VideoTitle')

        formats = []
        for mobj in re.finditer(
                r'setVideo(?:Url(?P<id>Low|High)|HLS)\s*\(\s*(?P<q>["\'])(?P<url>(?:https?:)?//.+?)(?P=q)', webpage):
            format_url = mobj.group('url')
            if determine_ext(format_url) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    quality=1, m3u8_id='hls', fatal=False))
            else:
                format_id = mobj.group('id')
                if format_id:
                    format_id = format_id.lower()
                formats.append({
                    'url': format_url,
                    'format_id': format_id,
                    'quality': -1 if format_id == 'low' else 0,
                })

        thumbnail = self._og_search_thumbnail(webpage, default=None) or get(
            'ThumbUrl', fatal=False) or get('ThumbUrl169', fatal=False)
        duration = int_or_none(self._og_search_property('duration', webpage))

        description = extract_description()
        view_count = extract_view_count()
        tags = extract_tags()

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'tags': tags,
            'thumbnail': thumbnail,
            'duration': duration,
            'view_count': view_count,
            'age_limit': 18,
            'formats': formats,
        }
