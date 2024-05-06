from .common import InfoExtractor
from ..utils import merge_dicts, unified_timestamp, url_or_none
from ..utils.traversal import traverse_obj


class ZetlandDKArticleIE(InfoExtractor):
    _VALID_URL = r'https?://www\.zetland\.dk/\w+/(?P<id>(?P<story_id>\w{8})-(?P<uploader_id>\w{8})-(?:\w{5}))'
    _TESTS = [{
        'url': 'https://www.zetland.dk/historie/sO9aq2MY-a81VP3BY-66e69?utm_source=instagram&utm_medium=linkibio&utm_campaign=artikel',
        'info_dict': {
            'id': 'sO9aq2MY-a81VP3BY-66e69',
            'ext': 'mp3',
            'modified_date': '20240118',
            'title': 'Afsnit 1: “Det føltes som en kidnapning.” ',
            'upload_date': '20240116',
            'uploader_id': 'a81VP3BY',
            'modified_timestamp': 1705568739,
            'release_timestamp': 1705377592,
            'uploader_url': 'https://www.zetland.dk/skribent/a81VP3BY',
            'uploader': 'Helle Fuusager',
            'release_date': '20240116',
            'thumbnail': r're:https://zetland\.imgix\.net/2aafe500-b14e-11ee-bf83-65d5e1283a57/Zetland_Image_1\.jpg',
            'description': 'md5:9619d426772c133f5abb26db27f26a01',
            'timestamp': 1705377592,
            'series_id': '62d54630-e87b-4ab1-a255-8de58dbe1b14',
        }

    }]

    def _real_extract(self, url):
        display_id, uploader_id = self._match_valid_url(url).group('id', 'uploader_id')
        webpage = self._download_webpage(url, display_id)

        next_js_data = self._search_nextjs_data(webpage, display_id)['props']['pageProps']
        story_data = traverse_obj(next_js_data, ('initialState', 'consume', 'story', 'story'))

        formats = []
        for audio_url in traverse_obj(story_data, ('story_content', 'meta', 'audioFiles', ..., {url_or_none})):
            formats.append({
                'url': audio_url,
                'vcodec': 'none',
            })

        return merge_dicts({
            'id': display_id,
            'formats': formats,
            'uploader_id': uploader_id
        }, traverse_obj(story_data, {
            'title': ((('story_content', 'content', 'title'), 'title'), {str}),
            'uploader': ('sharer', 'name'),
            'uploader_id': ('sharer', 'sharer_id'),
            'description': ('story_content', 'content', 'socialDescription'),
            'series_id': ('story_content', 'meta', 'seriesId'),
            'release_timestamp': ('published_at', {unified_timestamp}),
            'modified_timestamp': ('revised_at', {unified_timestamp}),
        }, get_all=False), traverse_obj(next_js_data, ('metaInfo', {
            'title': ((('meta', 'title'), ('ld', 'headline'), ('og', 'og:title'), ('og', 'twitter:title')), {str}),
            'description': ((('meta', 'description'), ('ld', 'description'), ('og', 'og:description'), ('og', 'twitter:description')), {str}),
            'uploader': ((('meta', 'author'), ('ld', 'author', 'name')), {str}),
            'uploader_url': ('ld', 'author', 'url', {url_or_none}),
            'thumbnail': ((('ld', 'image'), ('og', 'og:image'), ('og', 'twitter:image')), {url_or_none}),
            'modified_timestamp': ('ld', 'dateModified', {unified_timestamp}),
            'release_timestamp': ('ld', 'datePublished', {unified_timestamp}),
            'timestamp': ('ld', 'dateCreated', {unified_timestamp}),
        }), get_all=False), {
            'title': self._html_search_meta(['title', 'og:title', 'twitter:title'], webpage),
            'description': self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage),
            'thumbnail': self._html_search_meta(['og:image', 'twitter:image'], webpage),
            'uploader': self._html_search_meta(['author'], webpage),
            'release_timestamp': unified_timestamp(self._html_search_meta(['article:published_time'], webpage)),
        }, self._search_json_ld(webpage, display_id, fatal=False))
