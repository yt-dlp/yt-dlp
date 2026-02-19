import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    traverse_obj,
)


class StarTVIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?startv\.com\.tr/
        (?:
            (?:dizi|program)/(?:[^/?#&]+)/(?:bolumler|fragmanlar|ekstralar)|
            video/arsiv/(?:dizi|program)/(?:[^/?#&]+)
        )/
        (?P<id>[^/?#&]+)
    '''
    IE_NAME = 'startv'
    _TESTS = [
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/bolumler/3-bolum',
            'info_dict': {
                'id': '904972',
                'ext': 'mp4',
                'title': '3. Bölüm',
                'timestamp': 1569281400,
                'display_id': '3-bolum',
                'description': 'md5:cff8aaea543d6e4885e394a7346b5104',
                'duration': 7757.0,
                'thumbnail': r're:^https?://.*\.jpg(?:\?.*?)?$',
                'chapters': [],
                'categories': [],
                'series': 'Çocuk',
                'episode': 'Episode 3',
                'episode_number': 3,
                'upload_date': '20190923',
            },
        },
        {
            'url': 'https://www.startv.com.tr/video/arsiv/dizi/avlu/44-bolum',
            'only_matching': True,
        },
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/fragmanlar/5-bolum-fragmani',
            'only_matching': True,
        },
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/ekstralar/5-bolumun-nefes-kesen-final-sahnesi',
            'only_matching': True,
        },
        {
            'url': 'https://www.startv.com.tr/program/burcu-ile-haftasonu/bolumler/1-bolum',
            'only_matching': True,
        },
        {
            'url': 'https://www.startv.com.tr/program/burcu-ile-haftasonu/fragmanlar/2-fragman',
            'only_matching': True,
        },
        {
            'url': 'https://www.startv.com.tr/video/arsiv/program/buyukrisk/14-bolumde-hangi-unlu-ne-sordu-',
            'only_matching': True,
        },
        {
            'url': 'https://www.startv.com.tr/video/arsiv/program/buyukrisk/buyuk-risk-334-bolum',
            'only_matching': True,
        },
        {
            'url': 'https://www.startv.com.tr/video/arsiv/program/dada/dada-58-bolum',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        news_id = self._search_regex(r'\\"?snewsid\\"?\s*:\s*\\"?([^"\\]+)', webpage, 'news id')
        reference_id = self._search_regex(r'\\"?referenceId\\"?\s*:\s*\\"?([^"\\]+)', webpage, 'reference id')

        api_url = (
            'https://dygvideo.dygdigital.com/api/video_info'
            '?akamai=true&PublisherId=1'
            f'&ReferenceId=StarTv_{news_id}'
            '&SecretKey=NtvApiSecret2014*'
        )

        api_data = self._download_json(api_url, display_id, fatal=False)
        if not api_data.get('data'):
            api_url = api_url.replace(news_id, reference_id)
            api_data = self._download_json(api_url, display_id)

        info = traverse_obj(api_data, 'data', expected_type=dict)

        if not info:
            raise ExtractorError('Failed to extract API data')

        video_id = str(info.get('id') or display_id)
        title = info.get('title', info.get('short_title'))
        description = info.get('description', info.get('long_description'))

        thumbnail = traverse_obj(info, ('screenshots', 0, 'image_url'), default=info.get('image'))

        flavors = info.get('flavors') or {}
        extension = str(info.get('filename')).split('.')[-1]
        release_date = info.get('release_date')

        duration = float_or_none(info.get('duration'))
        program_name = info.get('program_name', info.get('channel_name'))

        episode_number = int_or_none(info.get('episode_number'))
        season_number = int_or_none(info.get('season_number'))

        web_url = info.get('web_url')
        categories = traverse_obj(info, ('categories', ...), expected_type=str) or []
        if isinstance(categories, str):
            categories = categories.split('>')

        chapters = []
        intro_start = int_or_none(info.get('skip_intro_start_at'))
        intro_end = int_or_none(info.get('skip_intro_finish_at'))
        if intro_start and intro_end:
            chapters.append(
                {
                    'title': 'Intro',
                    'start_time': intro_start / 1000,
                    'end_time': intro_end / 1000,
                },
            )

        m3u8_urls = set()

        if flavors.get('hls'):
            m3u8_urls.add(flavors['hls'])
        if flavors.get('hds') and flavors['hds'].endswith('.m3u8'):
            m3u8_urls.add(flavors['hds'])
        for v in flavors.values():
            if isinstance(v, dict):
                file_url = v.get('file_url_1')
                if file_url and file_url.endswith('.m3u8'):
                    m3u8_urls.add(file_url)

        formats = []
        for idx, m3u8_url in enumerate(m3u8_urls):
            formats.extend(
                self._extract_m3u8_formats(
                    m3u8_url,
                    video_id,
                    entry_protocol='m3u8_native',
                    m3u8_id=f'hls-{idx}',
                    fatal=False,
                ),
            )
        return {
            'id': video_id,
            'title': title,
            'display_id': display_id,
            'ext': extension,
            'timestamp': release_date,
            'formats': formats,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'series': program_name,
            'episode_number': episode_number,
            'season_number': season_number,
            'webpage_url': web_url,
            'chapters': chapters,
            'categories': categories,
        }


class StarTVSerieIE(InfoExtractor):
    IE_NAME = 'startv:serie'
    _VALID_URL = r'https?://(?:www\.)?startv\.com\.tr/(?P<type>dizi|program)/(?P<id>[^/?#&]+)/bolumler/?$'
    _DEFAULT_ID = '66e4852f0a0e0bf4d45f8c60'

    _TESTS = [
        {
            'url': 'https://www.startv.com.tr/dizi/menajerimi-ara/bolumler',
            'info_dict': {
                'id': 'menajerimi-ara',
                'title': 'Menajerimi Ara',
            },
            'playlist_mincount': 10,
        },
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/bolumler',
            'only_matching': True,
        },
    ]

    def _extract_entries(self, series_id, seasons):
        """
        Generator that yields episode URL results for all seasons.
        """
        for season_number in seasons:
            api_url = (
                f'https://www.startv.com.tr/api/tv-series/{series_id}/episodes'
                f'?sort=sys.published_at%20desc&skip=0&season={season_number}'
            )
            season_data = self._download_json(api_url, series_id)
            episodes = traverse_obj(season_data, 'items', default=[])
            episodes.reverse()  # earliest first

            for episode in episodes:
                episode_no = episode.get('episodeNo')
                episode_title = episode.get('title')
                yield self.url_result(
                    f"https://www.startv.com.tr{episode.get('url')}",
                    StarTVIE,
                    episode_no,
                    episode_title,
                )

    def extract_episodes(self, webpage, url):
        last_episode = max([int(x) for x in re.findall(r'/bolumler/(\d+)-bolum', webpage)])
        episodes = range(1, int(last_episode) + 1)
        for episode_id in episodes:
            yield self.url_result(
                f'{url}/{episode_id}-bolum',
                StarTVIE,
                episode_id,
            )

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        title = self._search_regex(r'<h1[^>]*>([^<]+)</h1>', webpage, 'title')

        seasons = re.findall(r'<button[^>]*data-season="(\d+)"', webpage, re.DOTALL)
        series_id = self._search_regex(r'5d:\{\\"?_id\\"?\s*:\s*\\"?([^"\\]+)', webpage, 'series id')
        if series_id == self._DEFAULT_ID:
            results = list(self.extract_episodes(webpage, url))
        else:
            results = list(self._extract_entries(series_id, seasons))
        return self.playlist_result(results, playlist_id, title)
