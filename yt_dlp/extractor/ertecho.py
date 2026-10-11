import itertools

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    int_or_none,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import find_element, require, traverse_obj


class ERTEchoBaseIE(InfoExtractor):
    _API_BASE = 'https://www.ertecho.gr/wp-json/wp/v2'

    def _call_api(self, path, item_id, note='Downloading API JSON', **kwargs):
        return self._download_json(f'{self._API_BASE}/{path}', item_id, note, **kwargs)

    @staticmethod
    def _term_title(term):
        taxonomy = traverse_obj(term, ('taxonomy', {str}))
        return traverse_obj(term, ((
            ('acf', f'{taxonomy}_display_name'), 'name'), {clean_html}, filter, any))


class ERTEchoEpisodeBaseIE(ERTEchoBaseIE):
    _LIVE_STATUS = None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        episode = self._call_api(
            f'{self._POST_TYPE}/{video_id}', video_id, query={'_embed': '1'})

        terms = {}
        for term in traverse_obj(episode, ('_embedded', 'wp:term', ..., lambda _, v: v['taxonomy'])):
            terms.setdefault(term['taxonomy'], []).append(term)

        return {
            'id': video_id,
            'vcodec': 'none' if episode.get('media_type') == 'audio' else None,
            'live_status': self._LIVE_STATUS,
            **traverse_obj(episode, {
                'url': ('media_url', {url_or_none}, {require('media URL')}),
                'title': ('title', 'rendered', {clean_html}, filter),
                'description': ((('content', 'rendered'), 'excerpt'), {clean_html}, filter, any),
                'timestamp': ('date_gmt', {parse_iso8601}),
                'modified_timestamp': ('modified_gmt', {parse_iso8601}),
                'thumbnail': ('_embedded', 'wp:featuredmedia', ..., 'source_url', {url_or_none}, any),
                'creators': ('authors', ..., 'display_name', {clean_html}, filter, all, filter),
            }),
            **traverse_obj(terms, {
                'series': ('show', 0, {self._term_title}),
                'series_id': ('show', 0, 'id', {str_or_none}),
                'channel': ('radio', 0, {self._term_title}),
                'categories': ('category', ..., {self._term_title}, filter, all, filter),
                'tags': ('post_tag', ..., {self._term_title}, filter, all, filter),
            }),
        }


class ERTEchoOnDemandIE(ERTEchoEpisodeBaseIE):
    IE_NAME = 'ertecho:ondemand'
    _POST_TYPE = 'ondemand'
    _LIVE_STATUS = 'was_live'
    _VALID_URL = r'https?://(?:www\.)?ertecho\.gr/(?:[\w-]+/)+ondemand/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.ertecho.gr/radio/deftero/show/adespotes-notes/ondemand/1298409/o-dimitris-papadimitriou-sto-deytero-programma-20-05-2026/',
        'md5': '572486c312f7c3d455bd65cc31eef139',
        'info_dict': {
            'id': '1298409',
            'ext': 'mp3',
            'title': 'Ο Δημήτρης Αποστολάκης στο Δεύτερο Πρόγραμμα | 03.06.2026',
            'categories': ['Εκπομπές', 'Μουσική', 'Συνεντεύξεις'],
            'channel': 'ΔΕΥΤΕΡΟ ΠΡΟΓΡΑΜΜΑ',
            'creators': ['Μιχάλης Γελασάκης'],
            'description': 'md5:db1e4d5a6a7fde76b2f344b3c9c50a91',
            'live_status': 'was_live',
            'modified_date': '20260603',
            'modified_timestamp': 1780500586,
            'series': 'Αδέσποτες Νότες',
            'series_id': '1631',
            'tags': ['ΔΗΜΗΤΡΗΣ ΑΠΟΣΤΟΛΑΚΗΣ', 'Μιχάλης Γελασάκης', 'ΧΑΙΝΗΔΕΣ'],
            'thumbnail': r're:https?://www\.ertecho\.gr/wp-content/uploads/.+',
            'timestamp': 1780499160,
            'upload_date': '20260603',
        },
    }, {
        'url': 'https://www.ertecho.gr/radio/ertnewsradio/category/eipan-sto-ertnews-radio-1058/ondemand/1385018/o-dionysis-temponeras-sto-ertnews-radio-105-8-12-09-2026/',
        'md5': '1dc75cd03b8f5bebd7b0c469978d28c0',
        'info_dict': {
            'id': '1385018',
            'ext': 'mp3',
            'title': 'Ο Διονύσης Τεμπονέρας στο ΕΡΤnews Radio 105,8 | 12.09.2026',
            'categories': ['Είπαν στο ΕΡΤnews Radio 105.8'],
            'channel': 'ΕΡΤNEWS RADIO',
            'creators': ['Λέλια Στεργιάκη'],
            'description': 'md5:b4e1d4c69633027cc7cdd94191fce02d',
            'live_status': 'was_live',
            'modified_date': '20260914',
            'modified_timestamp': 1789371390,
            'tags': ['ΑΛΦΟΝΣΟΣ ΒΙΤΑΛΗΣ', 'ΔΙΟΝΥΣΗΣ ΤΕΜΠΟΝΕΡΑΣ', 'ΣΤΟ ΡΥΘΜΟ ΤΗΣ ΕΠΙΚΑΙΡΟΤΗΤΑΣ'],
            'thumbnail': r're:https?://www\.ertecho\.gr/wp-content/uploads/.+',
            'timestamp': 1789198200,
            'upload_date': '20260912',
        },
    }, {
        'url': 'https://www.ertecho.gr/radio/florina/show/proino-kous-kous-florina/ondemand/881325/i-xristina-gkolna-kalesmeni-sto-proino-enimerotiko-kous-kous-30122024/',
        'md5': '0f37597ad564d993e33d137e54666ef5',
        'info_dict': {
            'id': '881325',
            'ext': 'mp3',
            'title': 'Η Χριστίνα Γκόλνα καλεσμένη στο Πρωϊνό ενημερωτικό “κους-κους” | 30.12.2024',
            'categories': ['Εκπομπές'],
            'channel': 'ΦΛΩΡΙΝΑ',
            'creators': ['Θωμαΐς Αδάμου', 'Μαρία Γαϊγάνη'],
            'description': 'md5:e0e5f3fe243d53794a4b0345517bf632',
            'live_status': 'was_live',
            'modified_date': '20241231',
            'modified_timestamp': 1735637577,
            'series': 'Πρωινό Κους Κους',
            'series_id': '40930',
            'tags': ['Θωμαΐς Αδάμου', 'Μαρία Γαϊγάνη', 'Χριστίνα Γκόλνα'],
            'thumbnail': r're:https?://www\.ertecho\.gr/wp-content/uploads/.+',
            'timestamp': 1735547700,
            'upload_date': '20241230',
        },
    }, {
        'url': 'https://www.ertecho.gr/radio/deftero/show/adespotes-notes/ondemand/1298409/',
        'only_matching': True,
    }]


class ERTEchoPodcastIE(ERTEchoEpisodeBaseIE):
    IE_NAME = 'ertecho:podcast'
    _POST_TYPE = 'podcast'
    _VALID_URL = r'https?://(?:www\.)?ertecho\.gr/(?:[\w-]+/)+podcast/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.ertecho.gr/radio/kosmos/show/oi-talantouxoi-kyrioi-kosmos/podcast/1037637/hermanos-gutierrez/',
        'md5': '14742d1c34727c9b9e182d76c2453b7a',
        'info_dict': {
            'id': '1037637',
            'ext': 'mp3',
            'title': 'Hermanos Gutiérrez',
            'categories': ['Podcast στο Kosmos'],
            'channel': 'KOSMOS',
            'creators': ['Γιώτα Κοτσέτα'],
            'description': 'md5:60fda9c63ff86a0ad94a676ff9a42641',
            'modified_date': '20250626',
            'modified_timestamp': 1750936898,
            'series': 'Οι Ταλαντούχοι Κύριοι...',
            'series_id': '18942',
            'tags': ['Alejandro Gutiérrez', 'Esteban Gutiérrez', 'Hermanos Gutiérrez', 'Γιώτα Κοτσέτα'],
            'thumbnail': r're:https?://www\.ertecho\.gr/wp-content/uploads/.+',
            'timestamp': 1751014800,
            'upload_date': '20250627',
        },
    }, {
        'url': 'https://www.ertecho.gr/radio/kosmos/show/oi-talantouxoi-kyrioi-kosmos/podcast/1037637/',
        'only_matching': True,
    }]


class ERTEchoPlaylistBaseIE(ERTEchoBaseIE):
    _PAGE_SIZE = 100

    def _entries(self, term_ids, display_id):
        for post_type, entry_ie in (
            ('ondemand', ERTEchoOnDemandIE),
            ('podcast', ERTEchoPodcastIE),
        ):
            for page in itertools.count(1):
                episodes, urlh = self._download_json_handle(
                    f'{self._API_BASE}/{post_type}', display_id,
                    f'Downloading {post_type} page {page}', query={
                        '_fields': 'id,link,title',
                        'page': page,
                        'per_page': self._PAGE_SIZE,
                        self._TAXONOMY: term_ids,
                    })

                for episode in traverse_obj(episodes, lambda _, v: url_or_none(v['link'])):
                    yield self.url_result(episode['link'], entry_ie, **traverse_obj(episode, {
                        'id': ('id', {str_or_none}),
                        'title': ('title', 'rendered', {clean_html}, filter),
                    }))

                total_pages = int_or_none(urlh.headers.get('X-WP-TotalPages'))
                if len(episodes) < self._PAGE_SIZE or (total_pages and page >= total_pages):
                    break

    def _real_extract(self, url):
        display_id = self._match_id(url)
        terms = self._call_api(
            self._TAXONOMY, display_id, 'Downloading playlist metadata', query={
                '_fields': 'acf,description,id,name,taxonomy',
                'slug': display_id,
            })
        term_ids = traverse_obj(terms, (
            ..., 'id', {int_or_none}, all, filter, {require('playlist ID')}))

        return self.playlist_result(
            self._entries(','.join(map(str, term_ids)), display_id),
            display_id, **traverse_obj(terms, (0, {
                'title': {self._term_title},
                'description': ('description', {clean_html}, filter),
            })))


class ERTEchoShowIE(ERTEchoPlaylistBaseIE):
    IE_NAME = 'ertecho:show'
    _TAXONOMY = 'show'
    _VALID_URL = r'https?://(?:www\.)?ertecho\.gr/(?:radio/[\w-]+/)?show/(?P<id>[\w-]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.ertecho.gr/radio/deftero/show/edo-einai-to-taksidi-deytero-programma/',
        'info_dict': {
            'id': 'edo-einai-to-taksidi-deytero-programma',
            'title': 'Εδώ Είναι το Ταξίδι',
            'description': 'md5:bece1e20aa81be136f6e9ac9501a0efd',
        },
        'playlist_mincount': 220,
    }, {
        'url': 'https://www.ertecho.gr/show/adespotes-notes/',
        'info_dict': {
            'id': 'adespotes-notes',
            'title': 'Αδέσποτες Νότες',
            'description': 'md5:08f1d5accd64b01ccfe5c9ee084a104a',
        },
        'playlist_mincount': 180,
    }, {
        'url': 'https://www.ertecho.gr/radio/kosmos/show/oi-talantouxoi-kyrioi-kosmos/',
        'info_dict': {
            'id': 'oi-talantouxoi-kyrioi-kosmos',
            'title': 'Οι Ταλαντούχοι Κύριοι...',
            'description': 'md5:8c83f64c494292a5c65e6c74fda09c6a',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://www.ertecho.gr/radio/kosmos/show/oi-talantouxoi-kyrioi-kosmos',
        'only_matching': True,
    }, {
        'url': 'https://www.ertecho.gr/show/adespotes-notes/?page=2',
        'only_matching': True,
    }]


class ERTEchoCategoryIE(ERTEchoPlaylistBaseIE):
    IE_NAME = 'ertecho:category'
    _TAXONOMY = 'categories'
    _VALID_URL = r'https?://(?:www\.)?ertecho\.gr/(?:radio/[\w-]+/)?category/(?P<id>[\w-]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.ertecho.gr/radio/ertnewsradio/category/eipan-sto-ertnews-radio-1058/',
        'info_dict': {
            'id': 'eipan-sto-ertnews-radio-1058',
            'title': 'Είπαν στο ΕΡΤnews Radio 105.8',
        },
        'playlist_mincount': 1200,
    }, {
        'url': 'https://www.ertecho.gr/category/live-sto-studio/',
        'info_dict': {
            'id': 'live-sto-studio',
            'title': 'Live στο Studio',
        },
        'playlist_mincount': 40,
    }, {
        'url': 'https://www.ertecho.gr/category/live-sto-studio',
        'only_matching': True,
    }, {
        'url': 'https://www.ertecho.gr/radio/ertnewsradio/category/eipan-sto-ertnews-radio-1058/?page=2',
        'only_matching': True,
    }]


class ERTEchoTagIE(ERTEchoPlaylistBaseIE):
    IE_NAME = 'ertecho:tag'
    _TAXONOMY = 'tags'
    _VALID_URL = r'https?://(?:www\.)?ertecho\.gr/tag/(?P<id>[\w-]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.ertecho.gr/tag/mixalis-gelasakis/',
        'info_dict': {
            'id': 'mixalis-gelasakis',
            'title': 'Μιχάλης Γελασάκης',
        },
        'playlist_mincount': 180,
    }, {
        'url': 'https://www.ertecho.gr/tag/mixalis-gelasakis',
        'only_matching': True,
    }]


class ERTEchoLiveIE(ERTEchoBaseIE):
    IE_NAME = 'ertecho:live'
    _VALID_URL = r'https?://(?:www\.)?ertecho\.gr/radio/(?P<id>[\w-]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.ertecho.gr/radio/deftero/',
        'info_dict': {
            'id': 'deftero',
            'ext': 'mp3',
            'title': r're:ΔΕΥΤΕΡΟ ΠΡΟΓΡΑΜΜΑ \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'description': 'Πάρε το Δεύτερο μαζί σου!',
            'live_status': 'is_live',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.ertecho.gr/radio/florina/',
        'only_matching': True,
    }, {
        'url': 'https://www.ertecho.gr/radio/kosmos',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        station_id = self._match_id(url)
        webpage = self._download_webpage(url, station_id)
        station = traverse_obj(self._call_api(
            'radio', station_id, 'Downloading station metadata', fatal=False, query={
                '_fields': 'acf,name,description',
                'slug': station_id,
            }), (0, {dict}))

        stream_url = traverse_obj(webpage, (
            {find_element(attr='data-player-type', value='live', html=True)},
            {extract_attributes}, 'data-player-source', {url_or_none}))
        title = traverse_obj(station, ('name', {clean_html}, filter))
        description = traverse_obj(station, ('description', {clean_html}, filter))

        return {
            'id': station_id,
            'ext': 'mp3',
            'is_live': True,
            'vcodec': 'none',
            'title': title or self._og_search_title(webpage, default=None),
            'description': description or self._html_search_meta(
                ['og:description', 'description', 'twitter:description'], webpage, default=None),
            'url': stream_url or traverse_obj(station, (
                'acf', 'radio_live_streaming_url', {url_or_none}, {require('stream URL')})),
        }
