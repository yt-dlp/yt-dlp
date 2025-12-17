from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    parse_iso8601,
    smuggle_url,
    unsmuggle_url,
)


class StarTVIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(www\.)?startv\.com\.tr
        /(?P<showType>dizi|program)
        /(?P<showSlug>[a-z0-9\-]+)
        /(?P<contentType>bolumler|fragmanlar|ekstralar)
        /(?P<contentSlug>[a-z0-9\-]+)
    '''
    _TESTS = [
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/bolumler/3-bolum',
            'info_dict': {
                'id': '80422',
                'display_id': 'cocuk-3-bolum',
                'title': 'Çocuk: 3. Bölüm',
                'description': 'md5:63209e03c6f409223d60659fa7263082',
                'duration': 7762.918,
                'timestamp': 1569278940,
                'thumbnail': 'https://media.startv.com.tr/star-tv//images/06e4350f491299c81dac336a.jpg',
                'series': 'Çocuk',
                'series_id': '65370e7af7378a107c1ed46b',
                'season': 'Season 1',
                'season_number': 1,
                'episode': 'Episode 3',
                'episode_number': 3,
                'upload_date': '20190923',
                'release_timestamp': 1568996640,
                'release_date': '20190920',
                'modified_timestamp': 1569278940,
                'modified_date': '20190923',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/fragmanlar/5-bolum-fragmani',
            'info_dict': {
                'id': '80514',
                'display_id': 'cocuk-5-bolum-fragmani',
                'title': 'Çocuk: 5. Bölüm Fragmanı',
                'description': 'md5:c0cbc36b9d044f33e425fcd7fcfd406c',
                'duration': 54.24,
                'thumbnail': 'https://media.startv.com.tr/star-tv//images/0f286bda4f679588b9f9ab81.jpg',
                'series': 'Çocuk',
                'series_id': '65370e7af7378a107c1ed46b',
                'episode': 'Episode 5',
                'episode_number': 5,
                'timestamp': 1570199426,
                'upload_date': '20191004',
                'release_timestamp': 1569591120,
                'release_date': '20190927',
                'modified_timestamp': 1570199426,
                'modified_date': '20191004',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www.startv.com.tr/dizi/cocuk/ekstralar/5-bolumun-nefes-kesen-final-sahnesi',
            'info_dict': {
                'id': '80687',
                'display_id': 'cocuk-5-bolumun-nefes-kesen-final-sahnesi',
                'title': 'Çocuk: 5. Bölümün nefes kesen final sahnesi',
                'description': '',
                'duration': 713.798,
                'thumbnail': 'https://media.startv.com.tr/star-tv//images/d3b18d3144228b9abb64df4d.jpg',
                'series': 'Çocuk',
                'series_id': '65370e7af7378a107c1ed46b',
                'timestamp': 1570534487,
                'upload_date': '20191008',
                'release_timestamp': 1570534500,
                'release_date': '20191008',
                'modified_timestamp': 1570534487,
                'modified_date': '20191008',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www.startv.com.tr/dizi/avlu/bolumler/44-bolum',
            'info_dict': {
                'id': '79509',
                'display_id': 'avlu-44-bolum',
                'title': 'Avlu: 44. Bölüm',
                'description': 'md5:572444feb6b25dfff554b3685c42d8a0',
                'duration': 8787.878,
                'timestamp': 1567607820,
                'thumbnail': 'https://media.startv.com.tr/star-tv//images/38aa9e384654abfb934651d8.jpg',
                'series': 'Avlu',
                'series_id': '6537746df7378a107c1ef9c0',
                'season': 'Season 1',
                'season_number': 1,
                'episode': 'Episode 44',
                'episode_number': 44,
                'upload_date': '20190904',
                'release_timestamp': 1559054280,
                'release_date': '20190528',
                'modified_timestamp': 1567607820,
                'modified_date': '20190904',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www.startv.com.tr/program/burcu-ile-hafta-sonu/bolumler/1-bolum',
            'info_dict': {
                'id': '80729',
                'display_id': 'burcu-ile-hafta-sonu-1-bolum',
                'title': 'Burcu ile Hafta Sonu: 1. Bölüm',
                'description': 'md5:0a38807192a8845af934f629101162ae',
                'duration': 3183.798,
                'thumbnail': 'https://media.startv.com.tr/star-tv//images/22eb65dd4fb79d7e5b86e21c.jpg',
                'series': 'Burcu ile Hafta Sonu',
                'series_id': '6537c6adf7378a107c1f673c',
                'season': 'Season 1',
                'season_number': 1,
                'episode': 'Episode 1',
                'episode_number': 1,
                'timestamp': 1570833240,
                'upload_date': '20191011',
                'release_timestamp': 1570807260,
                'release_date': '20191011',
                'modified_timestamp': 1570833240,
                'modified_date': '20191011',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www.startv.com.tr/program/burcu-ile-hafta-sonu/fragmanlar/2-fragman',
            'info_dict': {
                'id': '80724',
                'display_id': 'burcu-ile-hafta-sonu-2-fragman',
                'title': 'Burcu ile Hafta Sonu: 2. Fragman',
                'description': 'md5:a6afa1708fab477bf5320c7293625edb',
                'duration': 45.8,
                'thumbnail': 'https://media.startv.com.tr/star-tv//images/98041edf4937af6327cc14a3.jpg',
                'series': 'Burcu ile Hafta Sonu',
                'series_id': '6537c6adf7378a107c1f673c',
                'timestamp': 1570731524,
                'upload_date': '20191010',
                'release_timestamp': 1570731300,
                'release_date': '20191010',
                'modified_timestamp': 1570731524,
                'modified_date': '20191010',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www.startv.com.tr/program/tulin-sahin-ile-moda/ekstralar/hollywood-yildizlarinin-sac-tasarimcisi-jamal-hammadi-medcezirde',
            'info_dict': {
                'id': '65393870f7378a107c20bad6',
                'display_id': 'tulin-sahin-ile-moda-hollywood-yildizlarinin-sac-tasarimcisi-jamal-hammadi-medcezirde',
                'title': 'Tülin Şahin ile Moda: Hollywood yıldızlarının saç tasarımcısı Jamal Hammadi, Medcezir\'de!',
                'description': 'Hollywood yıldızlarının saç tasarımcısı Jamal Hammadi, Medcezir\'de!\n',
                'duration': 37.48,
                'thumbnail': 'https://media.startv.com.tr/star-tv//images/a579ddba49e59d356c387096.jpg',
                'series': 'Tülin Şahin ile Moda',
                'series_id': '65393731f7378a107c20b90c',
                'timestamp': 1397391080,
                'upload_date': '20140413',
                'release_timestamp': 1397391060,
                'release_date': '20140413',
                'modified_timestamp': 1706892776,
                'modified_date': '20240202',
                'ext': 'mp4',
            },
        },
    ]

    def _api_call(self, path, identifier, note):
        return self._download_json(f'https://www.startv.com.tr/api/{path}', identifier, note)

    def _get_content(self, show_type, show_id_or_slug, content_type, content_slug_or_id):
        endpoint_parts = [
            {
                'TvSeries': 'tv-series',
                'Program': 'programs',
            }[show_type],
            show_id_or_slug,
            content_type,
            content_slug_or_id,
        ]
        return self._api_call('/'.join(endpoint_parts), content_slug_or_id, 'Fetching content information')

    def _get_video_info(self, reference_id):
        parameters = [
            'SecretKey=NtvApiSecret2014*',
            'PublisherId=1',
            'akamai=true',
            f'ReferenceId=StarTv_{reference_id}',
        ]
        json = self._download_json(f"https://dygvideo.dygdigital.com/api/video_info?{'&'.join(parameters)}", reference_id, note='Fetching video url', data=[])
        if not json['success']:
            return {}

        return json['data']

    def _get_media_url(self, path):
        return f'https://media.startv.com.tr/star-tv/{path}'

    def _parse_content(self, content):
        video = content['video']
        video_id = video['referenceId']
        video_info = self._get_video_info(video_id)
        formats = self._extract_m3u8_formats(video_info['flavors']['hls'], video_id, entry_protocol='m3u8_native', m3u8_id='hls')
        sys = content['sys']

        show_name = content['heading']
        return {
            'id': video_id,
            'display_id': f'{content["parent_slug"]}-{content["slug"]}',
            'title': f'{show_name}: {video["title"]}',
            'description': content['plain_summary'],
            'duration': float_or_none(video.get('duration'), scale=1000),
            'series': show_name,
            'series_id': content.get('tvSeriesId') or content.get('programId'),
            'season_number': content.get('seasonNo'),
            'episode_number': content.get('episodeNo'),
            'timestamp': parse_iso8601(sys['published_at']),  # Available to users
            'release_timestamp': parse_iso8601(sys['created_at']),  # Editorial / air date
            'modified_timestamp': parse_iso8601(sys['modified_at']),  # Last update
            'thumbnail': self._get_media_url(content['image']['fullPath']),
            'formats': formats,
        }

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        if 'content' in smuggled_data:
            return self._parse_content(smuggled_data['content'])

        match = self._match_valid_url(url)
        show_type = {
            'dizi': 'TvSeries',
            'program': 'Program',
        }[match.group('showType')]
        show_slug = match.group('showSlug')
        content_type = {
            'bolumler': 'episodes',
            'fragmanlar': 'trailers',
            'ekstralar': 'short-videos',
        }[match.group('contentType')]
        content_slug = match.group('contentSlug')

        content = self._get_content(show_type, show_slug, content_type, content_slug)
        if content == 404:
            raise ExtractorError('no content found')
        return self._parse_content(content)


class StarTVSeriesIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(www\.)?startv\.com\.tr
        /(?P<showType>dizi|program)
        /(?P<showSlug>[a-z0-9\-]+)
        (/(?P<contentType>bolumler|fragmanlar|ekstralar))?
    '''
    _TESTS = [
        {
            'url': 'https://www.startv.com.tr/dizi/sahipsizler/bolumler',
            'playlist_min_count': 42,
            'info_dict': {
                'id': '66e4852f0a0e0bf4d45f8c60',
                'title': 'Sahipsizler',
            },
        },
        {
            'url': 'https://www.startv.com.tr/dizi/carpinti',
            'playlist_count': 13,
            'info_dict': {
                'id': '6880d3bd6b7ac0743eaff427',
                'title': 'Çarpıntı',
            },
        },
        {
            'url': 'https://www.startv.com.tr/dizi/carpinti/fragmanlar',
            'playlist_count': 30,
            'info_dict': {
                'id': '6880d3bd6b7ac0743eaff427',
                'title': 'Çarpıntı',
            },
        },
        {
            'url': 'https://www.startv.com.tr/dizi/carpinti/ekstralar',
            'playlist_count': 64,
            'info_dict': {
                'id': '6880d3bd6b7ac0743eaff427',
                'title': 'Çarpıntı',
            },
        },
        {
            'url': 'https://www.startv.com.tr/program/songul-ve-ugur-ile-sana-deger',
            'playlist_min_count': 308,
            'info_dict': {
                'id': '66b0c336197342ccbaadf9e0',
                'title': 'Songül ve Uğur ile Sana Değer',
            },
        },
        {
            'url': 'https://www.startv.com.tr/program/burcu-ile-hafta-sonu/bolumler',
            'playlist_count': 178,
            'info_dict': {
                'id': '6537c6adf7378a107c1f673c',
                'title': 'Burcu ile Hafta Sonu',
            },
        },
        {
            'url': 'https://www.startv.com.tr/program/burcu-ile-hafta-sonu/fragmanlar',
            'playlist_count': 10,
            'info_dict': {
                'id': '6537c6adf7378a107c1f673c',
                'title': 'Burcu ile Hafta Sonu',
            },
        },
    ]

    def _api_call(self, path, identifier, note):
        return self._download_json(f'https://www.startv.com.tr/api/{path}', identifier, note)

    def _get_show_detail(self, show_type, id_or_slug):
        endpoint_parts = [
            {
                'TvSeries': 'tv-series',
                'Program': 'programs',
            }[show_type],
            id_or_slug,
        ]
        return self._api_call('/'.join(endpoint_parts), id_or_slug, 'Fetching show information')

    def _get_show_contents(self, show_type, id_or_slug, content_type, skip, limit):
        endpoint_parts = [
            {
                'TvSeries': 'tv-series',
                'Program': 'programs',
            }[show_type],
            id_or_slug,
            content_type,
        ]
        parameters = [
            'sort=sys.published_at asc',
            'skip={skip}',
            'limit={limit}',
        ]
        json = self._api_call(f"{'/'.join(endpoint_parts)}?{'&'.join(parameters)}", id_or_slug, 'Fetching show contents')
        return json['items']

    def _extract_entries(self, show_type, show_id_or_slug, content_type, content_count):
        contents = self._get_show_contents(show_type, show_id_or_slug, content_type, skip=0, limit=content_count)
        for content in contents:
            url = smuggle_url(f"https://www.startv.com.tr{content['url']}", {'content': content})
            yield self.url_result(url, StarTVIE, content['_id'], content['title'])

    def _real_extract(self, url):
        match = self._match_valid_url(url)
        show_type = {
            'dizi': 'TvSeries',
            'program': 'Program',
        }[match.group('showType')]
        show_slug = match.group('showSlug')
        content_type = {
            'bolumler': 'episodes',
            'fragmanlar': 'trailers',
            'ekstralar': 'short-videos',
        }.get(match.group('contentType'), 'episodes')

        show = self._get_show_detail(show_type, show_slug)
        content_count = show.get({
            'episodes': 'episodeCount',
            'trailers': 'trailerCount',
            'short-videos': 'shortVideoCount',
        }[content_type], 0)
        if content_count == 0:
            raise ExtractorError({
                'episodes': 'No episode found',
                'trailers': 'No trailer found',
                'short-videos': 'No short video found',
            }[content_type])

        return self.playlist_result(self._extract_entries(show_type, show_slug, content_type, content_count), show['_id'], show['name'])
