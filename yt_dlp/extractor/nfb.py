from .common import InfoExtractor
from ..utils import (
    int_or_none,
    join_nonempty,
    merge_dicts,
    parse_count,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class NFBBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?(?P<site>nfb|onf)\.ca'
    _GEO_COUNTRIES = ['CA']

    def _extract_ep_data(self, webpage, video_id, fatal=False):
        return self._search_json(
            r'const\s+episodesData\s*=', webpage, 'episode data', video_id,
            contains_pattern=r'\[\s*{(?s:.+)}\s*\]', fatal=fatal) or []

    def _extract_ep_info(self, data, video_id, slug=None):
        info = traverse_obj(data, (lambda _, v: video_id in v['embed_url'], {
            'description': ('description', {str}),
            'thumbnail': ('thumbnail_url', {url_or_none}),
            'uploader': ('data_layer', 'episodeMaker', {str}),
            'release_year': ('data_layer', 'episodeYear', {int_or_none}),
            'episode': ('data_layer', 'episodeTitle', {str}),
            'season': ('data_layer', 'seasonTitle', {str}),
            'season_number': ('data_layer', 'seasonTitle', {parse_count}),
            'series': ('data_layer', 'seriesTitle', {str}),
        }), get_all=False)

        return {
            **info,
            'id': video_id,
            'title': join_nonempty('series', 'episode', from_dict=info, delim=' - '),
            'episode_number': int_or_none(self._search_regex(
                r'[/-]e(?:pisode)?-?(\d+)(?:[/-]|$)', slug or video_id, 'episode number', default=None)),
        }


class NFBIE(NFBBaseIE):
    IE_NAME = 'nfb'
    IE_DESC = 'nfb.ca and onf.ca films and episodes'
    _VALID_URL = [
        rf'{NFBBaseIE._VALID_URL_BASE}/(?P<type>film)/(?P<id>[^/?#&]+)',
        rf'{NFBBaseIE._VALID_URL_BASE}/(?P<type>series?)/(?P<id>[^/?#&]+/s(?:ea|ai)son\d+/episode\d+)',
    ]
    _TESTS = [{
        'note': 'NFB film',
        'url': 'https://www.nfb.ca/film/trafficopter/',
        'info_dict': {
            'id': 'trafficopter',
            'ext': 'mp4',
            'title': 'Trafficopter',
            'description': 'md5:060228455eb85cf88785c41656776bc0',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Barrie Howells',
            'release_year': 1972,
            'duration': 600.0,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'ONF film',
        'url': 'https://www.onf.ca/film/mal-du-siecle/',
        'info_dict': {
            'id': 'mal-du-siecle',
            'ext': 'mp4',
            'title': 'Le mal du siècle',
            'description': 'md5:1abf774d77569ebe603419f2d344102b',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Catherine Lepage',
            'release_year': 2019,
            'duration': 300.0,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'NFB episode with English title',
        'url': 'https://www.nfb.ca/series/true-north-inside-the-rise-of-toronto-basketball/season1/episode9/',
        'info_dict': {
            'id': 'true-north-episode9-true-north-finale-making-it',
            'ext': 'mp4',
            'title': 'True North: Inside the Rise of Toronto Basketball - Finale: Making It',
            'description': 'We catch up with each player in the midst of their journey as they reflect on their road ahead.',
            'series': 'True North: Inside the Rise of Toronto Basketball',
            'release_year': 2018,
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Finale: Making It',
            'episode_number': 9,
            'uploader': 'Ryan Sidhoo',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'ONF episode with French title',
        'url': 'https://www.onf.ca/serie/direction-nord-la-montee-du-basketball-a-toronto/saison1/episode9/',
        'info_dict': {
            'id': 'direction-nord-episode-9',
            'ext': 'mp4',
            'title': 'Direction nord – La montée du basketball à Toronto - Finale : Réussir',
            'description': 'md5:349a57419b71432b97bf6083d92b029d',
            'series': 'Direction nord – La montée du basketball à Toronto',
            'release_year': 2018,
            'season': 'Saison 1',
            'season_number': 1,
            'episode': 'Finale : Réussir',
            'episode_number': 9,
            'uploader': 'Ryan Sidhoo',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'NFB episode with French title (needs geo-bypass)',
        'url': 'https://www.nfb.ca/series/etoile-du-nord/saison1/episode1/',
        'info_dict': {
            'id': 'etoile-du-nord-episode-1-lobservation',
            'ext': 'mp4',
            'title': 'Étoile du Nord - L\'observation',
            'description': 'md5:161a4617260dee3de70f509b2c9dd21b',
            'series': 'Étoile du Nord',
            'release_year': 2023,
            'season': 'Saison 1',
            'season_number': 1,
            'episode': 'L\'observation',
            'episode_number': 1,
            'uploader': 'Patrick Bossé',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'ONF episode with English title (needs geo-bypass)',
        'url': 'https://www.onf.ca/serie/north-star/season1/episode1/',
        'info_dict': {
            'id': 'north-star-episode-1-observation',
            'ext': 'mp4',
            'title': 'North Star - Observation',
            'description': 'md5:c727f370839d8a817392b9e3f23655c7',
            'series': 'North Star',
            'release_year': 2023,
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Observation',
            'episode_number': 1,
            'uploader': 'Patrick Bossé',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'NFB episode with /film/ URL and English title (needs geo-bypass)',
        'url': 'https://www.nfb.ca/film/north-star-episode-1-observation/',
        'info_dict': {
            'id': 'north-star-episode-1-observation',
            'ext': 'mp4',
            'title': 'North Star - Observation',
            'description': 'md5:c727f370839d8a817392b9e3f23655c7',
            'series': 'North Star',
            'release_year': 2023,
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Observation',
            'episode_number': 1,
            'uploader': 'Patrick Bossé',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'ONF episode with /film/ URL and French title (needs geo-bypass)',
        'url': 'https://www.onf.ca/film/etoile-du-nord-episode-1-lobservation/',
        'info_dict': {
            'id': 'etoile-du-nord-episode-1-lobservation',
            'ext': 'mp4',
            'title': 'Étoile du Nord - L\'observation',
            'description': 'md5:161a4617260dee3de70f509b2c9dd21b',
            'series': 'Étoile du Nord',
            'release_year': 2023,
            'season': 'Saison 1',
            'season_number': 1,
            'episode': 'L\'observation',
            'episode_number': 1,
            'uploader': 'Patrick Bossé',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'Season 2 episode w/o episode num in id, extract from json ld',
        'url': 'https://www.onf.ca/film/liste-des-choses-qui-existent-saison-2-ours',
        'info_dict': {
            'id': 'liste-des-choses-qui-existent-saison-2-ours',
            'ext': 'mp4',
            'title': 'La liste des choses qui existent - L\'ours en peluche',
            'description': 'md5:d5e8d8fc5f3a7385a9cf0f509b37e28a',
            'series': 'La liste des choses qui existent',
            'release_year': 2022,
            'season': 'Saison 2',
            'season_number': 2,
            'episode': 'L\'ours en peluche',
            'episode_number': 12,
            'uploader': 'Francis Papillon',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'note': 'NFB film /embed/player/ page',
        'url': 'https://www.nfb.ca/film/afterlife/embed/player/',
        'info_dict': {
            'id': 'afterlife',
            'ext': 'mp4',
            'title': 'Afterlife',
            'description': 'md5:84951394f594f1fb1e62d9c43242fdf5',
            'release_year': 1978,
            'duration': 420.0,
            'uploader': 'Ishu Patel',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        site, type_, slug = self._match_valid_url(url).group('site', 'type', 'id')
        # Need to construct the URL since we match /embed/player/ URLs as well
        webpage, urlh = self._download_webpage_handle(f'https://www.{site}.ca/{type_}/{slug}/', slug)
        # type_ can change from film to serie(s) after redirect; new slug may have episode number
        type_, slug = self._match_valid_url(urlh.url).group('type', 'id')

        embed_url = urljoin(f'https://www.{site}.ca', self._html_search_regex(
            r'<[^>]+\bid=["\']player-iframe["\'][^>]*\bsrc=["\']([^"\']+)', webpage, 'embed url'))
        video_id = self._match_id(embed_url)  # embed url has unique slug
        player = self._download_webpage(embed_url, video_id, 'Downloading player page')
        if 'MESSAGE_GEOBLOCKED' in player:
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            self._html_search_regex(r'source:\s*\'([^\']+)', player, 'm3u8 url'),
            video_id, 'mp4', m3u8_id='hls')

        if dv_source := self._html_search_regex(r'dvSource:\s*\'([^\']+)', player, 'dv', default=None):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                dv_source, video_id, 'mp4', m3u8_id='dv', preference=-2, fatal=False)
            for fmt in fmts:
                fmt['format_note'] = 'described video'
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        info = {
            'id': video_id,
            'title': self._html_search_regex(
                r'<[^>]+\bid=["\']titleHeader["\'][^>]*>\s*<h1[^>]*>\s*([^<]+?)\s*</h1>',
                webpage, 'title', default=None),
            'description': self._html_search_regex(
                r'<[^>]+\bid=["\']tabSynopsis["\'][^>]*>\s*<p[^>]*>\s*([^<]+)',
                webpage, 'description', default=None),
            'thumbnail': self._html_search_regex(
                r'poster:\s*\'([^\']+)', player, 'thumbnail', default=None),
            'uploader': self._html_search_regex(
                r'<[^>]+\bitemprop=["\']name["\'][^>]*>([^<]+)', webpage, 'uploader', default=None),
            'release_year': int_or_none(self._html_search_regex(
                r'<[^>]+\bitemprop=["\']datePublished["\'][^>]*>([^<]+)',
                webpage, 'release_year', default=None)),
        } if type_ == 'film' else self._extract_ep_info(self._extract_ep_data(webpage, video_id, slug), video_id)

        return merge_dicts({
            'formats': formats,
            'subtitles': subtitles,
        }, info, self._search_json_ld(webpage, video_id, default={}))


class NFBSeriesIE(NFBBaseIE):
    IE_NAME = 'nfb:series'
    IE_DESC = 'nfb.ca and onf.ca series'
    _VALID_URL = rf'{NFBBaseIE._VALID_URL_BASE}/(?P<type>series?)/(?P<id>[^/?#&]+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.nfb.ca/series/true-north-inside-the-rise-of-toronto-basketball/',
        'playlist_mincount': 9,
        'info_dict': {
            'id': 'true-north-inside-the-rise-of-toronto-basketball',
        },
    }, {
        'url': 'https://www.onf.ca/serie/la-liste-des-choses-qui-existent-serie/',
        'playlist_mincount': 26,
        'info_dict': {
            'id': 'la-liste-des-choses-qui-existent-serie',
        },
    }]

    def _entries(self, episodes):
        for episode in traverse_obj(episodes, lambda _, v: NFBIE.suitable(v['embed_url'])):
            mobj = NFBIE._match_valid_url(episode['embed_url'])
            yield self.url_result(
                mobj[0], NFBIE, **self._extract_ep_info([episode], mobj.group('id')))

    def _real_extract(self, url):
        site, type_, series_id = self._match_valid_url(url).group('site', 'type', 'id')
        season_path = 'saison' if type_ == 'serie' else 'season'
        webpage = self._download_webpage(
            f'https://www.{site}.ca/{type_}/{series_id}/{season_path}1/episode1', series_id)
        episodes = self._extract_ep_data(webpage, series_id, fatal=True)

        return self.playlist_result(self._entries(episodes), series_id)
