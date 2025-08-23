import re
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    parse_iso8601,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
)


class AtvBaseIE(InfoExtractor):
    # Checks if value is UUID.4
    def _is_id_valid(self, value):
        # API only accepts value that has length of 32 or 36 identification
        if len(value) not in (32, 36):
            return False
        try:
            u = uuid.UUID(value)
            return u.version == 4
        except ValueError:
            return False

    # Extracts value of input tag identified with name from html
    def _extract_input(self, html, name):
        for input_el in re.findall(r'(?i)(<input[^>]+>)', html):
            if not input_el:
                continue
            attrs = extract_attributes(input_el)
            if name not in (attrs.get('id'), attrs.get('name')):
                continue
            return attrs.get('value') or None

    # Return API response in json
    def _api_call(self, path, video_id, note):
        return self._download_json(f'https://api.tmgrup.com.tr{path}', video_id, note, headers={
            'accept-encoding': 'gzip',
            'user-agent': 'okhttp/5.0.0-alpha.14',
        })

    def _get_video_detail(self, video_id):
        return self._api_call(f'/v2/link/ec8879e8ff?id={video_id}', video_id, 'Downlading video metadata')

    # Episodes returned in reverse chronological order (from newest to oldest)
    def _get_episode_list(self, category_id, next_url='', page=1):
        path = next_url or f'/v2/link/17d1662c72?cid={category_id}'
        return self._api_call(path, category_id, f'Downlading episode list for page {page}')


class AtvIE(AtvBaseIE):
    _VALID_URL = r'https?://(?:www\.)?atv\.com\.tr/(?P<slug>[a-z\-]+)/(?P<episode>[0-9]+\-bolum)(/izle)?'
    _TESTS = [
        {
            'url': 'https://www.atv.com.tr/aile-saadeti/4-bolum',
            'info_dict': {
                'id': '289b30be-f05f-4dc8-a589-a276e6404e86',
                'title': 'Aile Saadeti - 1. Sezon 4. Bölüm',
                'thumbnails': [
                    {
                        'id': 'normal',
                        'url': 'https://iaatv.tmgrup.com.tr/b8d958/959/566/0/0/1700/1003?u=https://iatv.tmgrup.com.tr/2025/07/04/aile-saadeti-1751635923569.jpg',
                        'width': 959,
                        'height': 566,
                    },
                    {
                        'id': 'large',
                        'url': 'https://iatv.tmgrup.com.tr/2025/07/04/aile-saadeti-1751635923569.jpg',
                        'width': 1700,
                        'height': 1003,
                    },
                ],
                'thumbnail': 'https://iatv.tmgrup.com.tr/2025/07/04/aile-saadeti-1751635923569.jpg',
                'duration': 8131,
                'release_date': '20250703',
                'release_timestamp': 1751541292,
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www.atv.com.tr/kurulus-osman/179-bolum/izle',
            'info_dict': {
                'id': '0cab4081-81cd-4931-b728-2cc5b29a81fb',
                'title': 'Kuruluş Osman - 6. Sezon 179. Bölüm',
                'thumbnails': [
                    {
                        'id': 'normal',
                        'url': 'https://iaatv.tmgrup.com.tr/01c841/959/566/0/0/2048/1209?u=https://iatv.tmgrup.com.tr/2025/02/04/kurulus-osman-1738668332817.jpg',
                        'width': 959,
                        'height': 566,
                    },
                    {
                        'id': 'large',
                        'url': 'https://iatv.tmgrup.com.tr/2025/02/04/kurulus-osman-1738668332817.jpg',
                        'width': 2048,
                        'height': 1209,
                    },
                ],
                'thumbnail': 'https://iatv.tmgrup.com.tr/2025/02/04/kurulus-osman-1738668332817.jpg',
                'duration': 8150,
                'release_date': '20250131',
                'release_timestamp': 1738336473,
                'ext': 'mp4',
            },
        },
    ]

    def _extract_video(self, video_id):
        json = self._get_video_detail(video_id)

        video_player = traverse_obj(json, ('data', 0, 'videoPlayer'))
        video_url = video_player.get('videoUrl')
        formats = self._extract_m3u8_formats(video_url, video_id, 'mp4', m3u8_id='hls')

        # data[0].videoPlayer.image has thumbnail dimensions in path of url
        # ex. https://iaatv.tmgrup.com.tr/b8d958/959/566/0/0/1700/1003?u=https://iatv.tmgrup.com.tr/2025/07/04/aile-saadeti-1751635923569.jpg
        #     | original  | scaled  |
        #     |-----------|---------|
        #     | 1700x1003 | 959x566 |
        thumbnails = []
        thumbnail_url = video_player.get('image')
        # Some programs do not have thumbnails
        # ex. /atv-ana-haber/bolumler
        if thumbnail_url:
            thumbnail_url_path_parts = thumbnail_url.split('?')[0].split('/')
            thumbnails = [
                {
                    'id': 'normal',
                    'url': thumbnail_url,
                    'width': int(thumbnail_url_path_parts[4]),
                    'height': int(thumbnail_url_path_parts[5]),
                    'preference': 1,
                },
                {
                    'id': 'large',
                    'url': video_player.get('imageBig'),
                    'width': int(thumbnail_url_path_parts[8]),
                    'height': int(thumbnail_url_path_parts[9]),
                    'preference': 2,
                },
            ]

        return {
            'id': video_id,
            'title': video_player.get('title'),
            'formats': formats,
            'thumbnails': thumbnails,
            'language': 'tr',
            'duration': int(video_player.get('videoDuration')),
            'release_timestamp': parse_iso8601(video_player.get('publishedDate')),
        }

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        if 'video_id' in smuggled_data:
            return self._extract_video(smuggled_data.get('video_id'))

        slug, episode = self._match_valid_url(url).group('slug', 'episode')
        webpage = self._download_webpage(url, f'{slug} {episode}')
        video_id = self._extract_input(webpage, 'videoId')

        if not self._is_id_valid(video_id):
            raise ExtractorError('Unable to extract video id')

        return self._extract_video(video_id)


class AtvSeriesIE(AtvBaseIE):
    _VALID_URL = r'https?://(?:www\.)?atv\.com\.tr/(?P<id>[a-z\-]+)(/bolumler)?$'
    _TESTS = [
        {
            'url': 'https://www.atv.com.tr/can-borcu',
            'info_dict': {
                'id': '4a8459e8-ba0c-4eb8-a7d3-3982cea3a8a2',
            },
            'playlist_count': 22,
        },
        {
            'url': 'https://www.atv.com.tr/kara-para-ask/bolumler',
            'info_dict': {
                'id': '64c31827-2fb9-43e3-9e3c-1666ffc2d846',
            },
            'playlist_count': 53,
        },
        {
            'url': 'https://www.atv.com.tr/avrupa-yakasi/bolumler',
            'info_dict': {
                'id': 'de68e8b2-4ec5-4321-8e81-1bfa2cef2a3f',
            },
            'playlist_count': 190,
        },
    ]

    def _live_stream(self):
        appid = 'd1ce2d40-5256-4550-b02e-e73c185a314e'
        url = f'https://trkvz.daioncdn.net/atv/atv.m3u8?ce=3&app={appid}'
        json = self._download_json(f'https://securevideotoken.tmgrup.com.tr/webtv/secure?url={url}', appid, 'Downloading live stream metadata',
                                   headers={'referer': 'https://www.atv.com.tr/'})

        return {
            'id': appid,
            'title': 'atv Canlı Yayın',
            'is_live:': True,
            'format_id': 'hls',
            'protocol': 'm3u8',
            'url': json.get('Url') or json.get('AlternateUrl'),
        }

    def _entries(self, category_id):
        page = 1
        pagination = {}
        next_url = ''
        while page <= pagination.get('total_page', 1):
            json = self._get_episode_list(category_id, next_url, page=page)
            pagination = json.get('pagination', {})
            next_url = pagination.get('next_url')

            videos = traverse_obj(json, ('data', 0, 'videos'))
            for video in videos:
                video_id = video.get('id')
                title = video.get('title')
                spot = video.get('spot')

                # Building url by slugifying title and spot fails on some programs
                # ex. /muge-anli-ile-tatli-sert/bolumler
                #     /atv-ana-haber/bolumler
                # And it is wasteful having to download webpage then extract video id again.

                url = smuggle_url('https://www.atv.com.tr/placeholder/1-bolum/izle', {'video_id': video_id})
                yield self.url_result(url, AtvIE, video_id, title=f'{title} {spot}')

            page += 1

    def _real_extract(self, url):
        slug = self._match_id(url)
        if slug == 'canli-yayin':
            return self._live_stream()
        if not url.endswith('/bolumler'):
            # This is needed because category id only found in this path
            # ex. '/aile-saadeti'          does NOT contain category id
            #     '/aile-saadeti/bolumler' has category id as input
            url += '/bolumler'
        webpage = self._download_webpage(url, f'{slug}')

        category_id = self._extract_input(webpage, 'category-id')
        if not self._is_id_valid(category_id):
            raise ExtractorError('Unable to extract category id')

        return self.playlist_result(self._entries(category_id), category_id)
