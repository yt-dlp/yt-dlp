from .common import InfoExtractor
from ..utils import clean_html, float_or_none, traverse_obj, unescapeHTML


class AudioBoomIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?audioboom\.com/(?:boos|posts)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://audioboom.com/posts/7398103-asim-chaudhry',
        'md5': '4d68be11c9f9daf3dab0778ad1e010c3',
        'info_dict': {
            'id': '7398103',
            'ext': 'mp3',
            'title': 'Asim Chaudhry',
            'description': 'md5:0ed714ae0e81e5d9119cac2f618ad679',
            'duration': 4000.99,
            'uploader': 'Sue Perkins: An hour or so with...',
            'uploader_url': r're:https?://(?:www\.)?audioboom\.com/channel/perkins',
        }
    }, {  # Direct mp3-file link
        'url': 'https://audioboom.com/posts/8128496.mp3',
        'md5': 'e329edf304d450def95c7f86a9165ee1',
        'info_dict': {
            'id': '8128496',
            'ext': 'mp3',
            'title': 'TCRNo8 / DAILY 03 - In Control',
            'description': 'md5:44665f142db74858dfa21c5b34787948',
            'duration': 1689.7,
            'uploader': 'Lost Dot Podcast: The Trans Pyrenees and Transcontinental Race',
            'uploader_url': r're:https?://(?:www\.)?audioboom\.com/channels/5003904',
        }
    }, {
        'url': 'https://audioboom.com/posts/4279833-3-09-2016-czaban-hour-3?t=0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://audioboom.com/posts/{video_id}', video_id)

        clip_store = self._search_json(
            r'data-react-class="V5DetailPagePlayer"\s*data-react-props=["\']',
            webpage, 'clip store', video_id, fatal=False, transform_source=unescapeHTML)
        clip = traverse_obj(clip_store, ('clips', 0), expected_type=dict) or {}

        return {
            'id': video_id,
            'url': clip.get('clipURLPriorToLoading') or self._og_search_property('audio', webpage, 'audio url'),
            'title': clip.get('title') or self._html_search_meta(['og:title', 'og:audio:title', 'audio_title'], webpage),
            'description': (clip.get('description') or clean_html(clip.get('formattedDescription'))
                            or self._og_search_description(webpage)),
            'duration': float_or_none(clip.get('duration') or self._html_search_meta('weibo:audio:duration', webpage)),
            'uploader': clip.get('author') or self._html_search_meta(
                ['og:audio:artist', 'twitter:audio:artist_name', 'audio_artist'], webpage, 'uploader'),
            'uploader_url': clip.get('author_url') or self._html_search_regex(
                r'<div class="avatar flex-shrink-0">\s*<a href="(?P<uploader_url>http[^"]+)"',
                webpage, 'uploader url', fatal=False),
        }
