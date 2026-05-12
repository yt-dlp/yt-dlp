import itertools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    parse_iso8601,
    str_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class ArteRadioBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?arteradio\.com'
    _FRONTAPI = 'https://frontapi.arteradio.lab.arte.tv/api'
    # Page size used by the Arte Radio front-end when paging through episodes
    _PAGE_SIZE = 18

    def _extract_next_data(self, url, display_id):
        webpage = self._download_webpage(url, display_id)
        return self._search_json(
            r'<script[^>]+id="__NEXT_DATA__"[^>]*>', webpage,
            'next data', display_id)['props']['pageProps']

    def _sound_entry(self, sound):
        sound_id = sound.get('uuid') or sound['slug']
        formats = []
        for key, fmt_id, acodec, quality in (
            ('mp3HifiMedia', 'mp3-hifi', 'mp3', 1),
            ('mp3LofiMedia', 'mp3-lofi', 'mp3', 0),
            ('oggMedia', 'ogg', 'vorbis', 0),
        ):
            audio_url = traverse_obj(sound, (key, 'finalUrl', {url_or_none}))
            if audio_url:
                formats.append({
                    'url': audio_url,
                    'format_id': fmt_id,
                    'acodec': acodec,
                    'vcodec': 'none',
                    'quality': quality,
                })

        return {
            'id': sound_id,
            'display_id': sound.get('slug'),
            'title': sound.get('title'),
            'description': clean_html(sound.get('description')),
            'duration': int_or_none(sound.get('durationInSeconds')),
            'thumbnail': traverse_obj(
                sound, (('squaredImage', 'mainImage'), 'finalUrl', {url_or_none}), get_all=False),
            'upload_date': unified_strdate(traverse_obj(sound, ('publication', 'period', 'start'))),
            'series': traverse_obj(sound, ('containingCollection', 'title', {str})),
            'series_id': traverse_obj(sound, ('containingCollection', 'uuid', {str})),
            'episode_number': traverse_obj(sound, ('containingCollection', 'episodeNumber', {int_or_none})),
            'creators': traverse_obj(sound, ('authors', ..., 'name', {str})) or None,
            'formats': formats,
        }

    def _search_sounds(self, display_id, body, *, note=None):
        return self._download_json(
            f'{self._FRONTAPI}/content/search', display_id,
            note=note or 'Downloading episodes',
            data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'})


class ArteRadioIE(ArteRadioBaseIE):
    _VALID_URL = rf'{ArteRadioBaseIE._VALID_URL_BASE}/son/(?P<id>[\w-]+)'
    IE_NAME = 'arteradio'

    _TESTS = [{
        'url': 'https://www.arteradio.com/son/guillemette-1-7-guillemette-a-la-plage',
        'md5': '60553712d46a589adcfa9ebf5dedb80e',
        'info_dict': {
            'id': 'bb26b801-620a-4351-a413-48e653ca0aaa',
            'display_id': 'guillemette-1-7-guillemette-a-la-plage',
            'ext': 'mp3',
            'title': 'Guillemette (1/7) : Guillemette à la plage',
            'description': r're:Guillemette est à la plage avec ses parents.+Bernard-l.Hermite.+',
            'duration': 453,
            'thumbnail': r're:^https?://cdn\.arteradio\.com/.+\.(?:png|jpe?g)',
            'series': 'Guillemette',
            'series_id': 'ec7e99ec-5c2d-4040-9b64-2fa21b72098b',
            'episode': str,
            'episode_number': int,
            'creators': list,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        sound = self._extract_next_data(url, display_id)['sound']
        return self._sound_entry(sound)


class ArteRadioCollectionIE(ArteRadioBaseIE):
    _VALID_URL = rf'{ArteRadioBaseIE._VALID_URL_BASE}/(?:serie|emission|collection)/(?P<id>[\w-]+)'
    IE_NAME = 'arteradio:collection'

    _TESTS = [{
        # small "serie" collection
        'url': 'https://www.arteradio.com/serie/guillemette',
        'info_dict': {
            'id': 'ec7e99ec-5c2d-4040-9b64-2fa21b72098b',
            'display_id': 'guillemette',
            'title': 'Guillemette',
            'description': r're:Les aventures de Guillemette.+',
            'thumbnail': r're:^https?://cdn\.arteradio\.com/.+',
        },
        'playlist_count': 7,
    }, {
        # large collection that exercises pagination through /content/search
        'url': 'https://www.arteradio.com/serie/polissons',
        'info_dict': {
            'id': '41f5fd78-1449-4fb7-aa23-39255c490005',
            'display_id': 'polissons',
            'title': 'Polissons',
        },
        'playlist_mincount': 40,
    }, {
        'url': 'https://www.arteradio.com/emission/les-podcasts-derriere-les-portes',
        'only_matching': True,
    }]

    def _paged_entries(self, collection):
        episode_uuids = collection.get('allEpisodesUuids') or []
        first_episodes = collection.get('firstEpisodes') or []
        # The first batch is already in __NEXT_DATA__; fetch additional pages from /content/search
        for page_num in itertools.count(0):
            start = page_num * self._PAGE_SIZE
            if start >= len(episode_uuids):
                return
            if page_num == 0 and first_episodes:
                results = first_episodes
            else:
                results = traverse_obj(
                    self._search_sounds(
                        collection.get('slug') or collection.get('uuid'),
                        {'start': start, 'end': start + self._PAGE_SIZE, 'byUuidsIn': episode_uuids},
                        note=f'Downloading episodes page {page_num + 1}'),
                    ('results', ..., {dict})) or []
            if not results:
                return
            for sound in results:
                yield self._sound_entry(sound)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        collection = self._extract_next_data(url, display_id)['collection']

        return self.playlist_result(
            self._paged_entries(collection),
            collection.get('uuid') or display_id,
            display_id=display_id,
            title=collection.get('title'),
            description=clean_html(collection.get('description')),
            thumbnail=traverse_obj(
                collection, (('squaredImage', 'mainImage'), 'finalUrl', {url_or_none}), get_all=False))


class ArteRadioAudioblogBaseIE(InfoExtractor):
    _API = 'https://back-audioblog.arteradio.com/api'

    def _podcast_entry(self, item):
        # /api/blog/podcasts/.. wraps every entry in {"podcast": {...}, "stats": {...}}
        if isinstance(item, dict) and 'podcast' in item and isinstance(item['podcast'], dict):
            item = item['podcast']

        audio_url = traverse_obj(item, ('file_url', {url_or_none}))
        if not audio_url:
            raise ExtractorError('No audio URL available for this podcast', expected=True)
        podcast_id = str(item.get('id') or '')

        return {
            'id': podcast_id or item.get('uuid') or audio_url,
            'title': item.get('title'),
            'description': clean_html(item.get('description')),
            'duration': int_or_none(item.get('duration')),
            'timestamp': parse_iso8601(item.get('created')),
            'thumbnail': traverse_obj(item, ('image_akamai', {url_or_none})),
            'url': audio_url,
            'ext': 'mp3',
            'vcodec': 'none',
            'acodec': 'mp3',
            'series': traverse_obj(item, ('blog', 'title', {str})),
            'series_id': traverse_obj(item, ('blog', 'id', {int_or_none}, {str_or_none})),
            'uploader': traverse_obj(item, ('blog', 'blogger', 'name', {str})),
            'tags': traverse_obj(item, ('keywords', ..., 'name', {str})) or None,
        }


class ArteRadioAudioblogIE(ArteRadioAudioblogBaseIE):
    _VALID_URL = r'https?://audioblog\.arteradio\.com/blog/(?P<blog_id>\d+)/podcast/(?P<id>\d+)'
    IE_NAME = 'arteradio:audioblog'

    _TESTS = [{
        'url': 'https://audioblog.arteradio.com/blog/275449/podcast/275453',
        'md5': '43dbf25efac6b2d11d9670f8631af0b6',
        'info_dict': {
            'id': '275453',
            'ext': 'mp3',
            'title': r're:Lignes publiques.*',
            'duration': 1247,
            'series': r're:Nos Transports.*',
            'series_id': '275449',
            'uploader': 'Zeïneb Grimbert',
            'thumbnail': r're:^https?://.*\.jpe?g',
            'timestamp': int,
            'upload_date': r're:\d{8}',
            'tags': list,
        },
    }, {
        'url': 'https://audioblog.arteradio.com/blog/275449/podcast/275453/lignes-publiques',
        'only_matching': True,
    }]

    def _find_podcast(self, blog_id, podcast_id):
        # The single-podcast JSON endpoint requires auth, so list and filter instead.
        # Audioblogs are typically small (a few dozen entries at most).
        for offset in itertools.count(0, 50):
            items = self._download_json(
                f'{self._API}/blog/podcasts/{blog_id}/{offset}/50',
                podcast_id, note=f'Downloading podcasts (offset {offset})')
            if not items:
                break
            for item in items:
                if str(traverse_obj(item, ('podcast', 'id'))) == podcast_id:
                    return item
            if len(items) < 50:
                break
        raise ExtractorError(f'Podcast {podcast_id} not found in blog {blog_id}', expected=True)

    def _real_extract(self, url):
        blog_id, podcast_id = self._match_valid_url(url).group('blog_id', 'id')
        return self._podcast_entry(self._find_podcast(blog_id, podcast_id))


class ArteRadioAudioblogBlogIE(ArteRadioAudioblogBaseIE):
    _VALID_URL = r'https?://audioblog\.arteradio\.com/blog/(?P<id>\d+)(?:/[^/?#]+)?/?(?:[?#]|$)'
    IE_NAME = 'arteradio:audioblog:blog'

    _TESTS = [{
        'url': 'https://audioblog.arteradio.com/blog/275449',
        'info_dict': {
            'id': '275449',
            'title': r're:Nos Transports.*',
            'description': str,
            'uploader': 'Zeïneb Grimbert',
            'thumbnail': r're:^https?://',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://audioblog.arteradio.com/blog/275449/nos-transports',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        # Defer single-podcast URLs to ArteRadioAudioblogIE
        if ArteRadioAudioblogIE.suitable(url):
            return False
        return super().suitable(url)

    def _entries(self, blog_id):
        page_size = 50
        seen_blog = {}
        for offset in itertools.count(0, page_size):
            items = self._download_json(
                f'{self._API}/blog/podcasts/{blog_id}/{offset}/{page_size}',
                blog_id, note=f'Downloading podcasts (offset {offset})')
            if not items:
                break
            for item in items:
                if not seen_blog:
                    seen_blog.update(traverse_obj(item, ('podcast', 'blog', {dict})) or {})
                yield self._podcast_entry(item)
            if len(items) < page_size:
                break
        self._blog_meta = seen_blog

    def _real_extract(self, url):
        blog_id = self._match_id(url)
        # Pull the first page eagerly so we can populate playlist metadata
        items = self._download_json(
            f'{self._API}/blog/podcasts/{blog_id}/0/50', blog_id,
            note='Downloading podcasts (offset 0)')
        if not items:
            raise ExtractorError('Blog has no published podcasts', expected=True)

        blog = traverse_obj(items[0], ('podcast', 'blog', {dict})) or {}

        def entries():
            for item in items:
                yield self._podcast_entry(item)
            # If we got a full page, there may be more
            if len(items) >= 50:
                for offset in itertools.count(50, 50):
                    more = self._download_json(
                        f'{self._API}/blog/podcasts/{blog_id}/{offset}/50',
                        blog_id, note=f'Downloading podcasts (offset {offset})')
                    if not more:
                        break
                    for item in more:
                        yield self._podcast_entry(item)
                    if len(more) < 50:
                        break

        return self.playlist_result(
            entries(), blog_id,
            title=blog.get('title'),
            description=clean_html(blog.get('presentation')),
            thumbnail=traverse_obj(blog, ('image_akamai_blog', {url_or_none})) or traverse_obj(blog, ('image_akamai', {url_or_none})),
            uploader=traverse_obj(blog, ('blogger', 'name', {str})))
