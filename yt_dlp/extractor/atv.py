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

    def _request_secure_token(self, video_url):
        # Extracted from https://i.tmgrup.com.tr/videojs/js/tmdplayersetupv2.js?v=792 at RequestSecureToken() function
        return self._download_json(f'https://securevideotoken.tmgrup.com.tr/webtv/secure?url={video_url}', video_url, 'Getting secure token',
                                   headers={'referer': 'https://www.atv.com.tr/'})

    def _videojs_get_video(self, video_id, note, channel='atv'):
        # These are the channels published by "Turkuvaz Haberlesme ve Yayincilik A.S."
        # Extracted from https://i.tmgrup.com.tr/videojs/js/tmdplayersetupv2.js?v=792 at PlayerDaion() function
        # | website url                     | website ID                           | channel     | ce | app ID                               | mobile | test |
        # |---------------------------------|--------------------------------------|-------------|----|--------------------------------------|--------|------|
        # | https://www.aspor.com.tr/       | 9bbe055a-4cf6-4bc3-a675-d40e89b55b91 | aspor       | 3  | b6bf3b55-0120-4e0f-983b-a6c7969f9ec6 | yes    | no   |
        # | https://www.aspor.com.tr/       | 9bbe055a-4cf6-4bc3-a675-d40e89b55b91 | aspor       | 3  | 45f847c4-04e8-419a-a561-2ebf87084765 | no     | no   |
        # | https://www.atv.com.tr/a2tv/    | 0c1bc8ff-c3b1-45be-a95b-f7bb9c8b03ed | a2tv        | 3  | 59363a60-be96-4f73-9eff-355d0ff2c758 | -      | no   |
        # | https://www.minikago.com.tr/    | aae2e325-4eae-45b7-b017-26fd7ddb6ce4 | minikago    | 3  | mweb                                 | yes    | no   |
        # | https://www.minikago.com.tr/    | aae2e325-4eae-45b7-b017-26fd7ddb6ce4 | minikago    | 3  | web                                  | no     | no   |
        # | https://www.minikacocuk.com.tr/ | 01ed59f2-4067-4945-8204-45f6c6db4045 | minikacocuk | 3  | mweb                                 | yes    | no   |
        # | https://www.atv.com.tr/         | 0fe2a405-8afa-4238-b429-e5f96aec3a5c | atv         | 3  | 866e32e3-9fea-477f-a5ef-64ebe32956f3 | -      | yes  |
        # | https://www.atv.com.tr/         | 0fe2a405-8afa-4238-b429-e5f96aec3a5c | atv         | 3  | d5eb593f-39d9-4b01-9cfd-4748e8332cf0 | yes    | no   |
        # | https://www.atv.com.tr/         | 0fe2a405-8afa-4238-b429-e5f96aec3a5c | atv         | 3  | d1ce2d40-5256-4550-b02e-e73c185a314e | no     | no   |
        #
        # These are mainly published by two different CDNs
        # - https://trkvz-live.ercdn.net/{channel}/{channel}.m3u8
        # - https://trkvz.daioncdn.net/{channel}/{channel}.m3u8
        CHANNELS = {
            'atv': {
                'website_id': '0fe2a405-8afa-4238-b429-e5f96aec3a5c',
                'website_url': 'https://www.atv.com.tr/',
            },
            'aspor': {
                'website_id': '9bbe055a-4cf6-4bc3-a675-d40e89b55b91',
                'website_url': 'https://www.aspor.com.tr/',
            },
            'a2tv': {
                'website_id': '0c1bc8ff-c3b1-45be-a95b-f7bb9c8b03ed',
                'website_url': 'https://www.atv.com.tr/',
            },
            'minikago': {
                'website_id': 'aae2e325-4eae-45b7-b017-26fd7ddb6ce4',
                'website_url': 'https://www.minikago.com.tr/',
            },
            'minikacocuk': {
                'website_id': '01ed59f2-4067-4945-8204-45f6c6db4045',
                'website_url': 'https://www.minikacocuk.com.tr/',
            },
        }
        website_id = CHANNELS[channel]['website_id']
        return self._download_json(f'https://videojs.tmgrup.com.tr/getvideo/{website_id}/{video_id}', website_id, note,
                                   headers={'referer': CHANNELS[channel]['website_url']})

    def _videojs_get_live_stream(self, channel='atv'):
        video_id = '00000000-0000-0000-0000-000000000000'
        return self._videojs_get_video(video_id, 'Get live stream metadata', channel=channel)


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
        {
            'url': 'https://www.atv.com.tr/mutfak-bahane/723-bolum/izle',
            'info_dict': {
                'id': '78222537-f80b-47c3-baff-2075a4dafc0a',
                'title': 'Mutfak Bahane - 4. Sezon 723. Bölüm',
                'thumbnails': [
                    {
                        'id': 'normal',
                        'url': 'https://iaatv.tmgrup.com.tr/0ed24c/959/566/0/0/1831/1080?u=https://iatv.tmgrup.com.tr/2025/06/25/mutfak-bahane-1750858626323.jpg',
                        'width': 959,
                        'height': 566,
                    },
                    {
                        'id': 'large',
                        'url': 'https://iatv.tmgrup.com.tr/2025/06/25/mutfak-bahane-1750858626323.jpg',
                        'width': 1831,
                        'height': 1080,
                    },
                ],
                'thumbnail': 'https://iatv.tmgrup.com.tr/2025/06/25/mutfak-bahane-1750858626323.jpg',
                'duration': 5608,
                'release_date': '20250625',
                'release_timestamp': 1750869432,
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www.atv.com.tr/atv-ana-haber/9884-bolum/izle',
            'info_dict': {
                'id': 'b428f689-30f7-4ff4-bb75-792519d43216',
                'title': 'atv Ana Haber',
                'duration': 2785,
                'release_date': '20250714',
                'release_timestamp': 1752525577,
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

        # TODO: extract description
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
        json = self._videojs_get_live_stream()
        if not json.get('success', False):
            raise ExtractorError('Unable to fetch live stream url')

        video_url = traverse_obj(json, ('video', 'VideoUrl'))

        json = self._request_secure_token(video_url)
        stream_url = json.get('Url') or json.get('AlternateUrl')
        stream_id = 'canli-yayin'
        formats = self._extract_m3u8_formats(stream_url, stream_id, 'mp4', m3u8_id='hls')
        return {
            'id': stream_id,
            'title': 'atv Canlı Yayın',
            'is_live:': True,
            'format_id': 'hls',
            'protocol': 'm3u8',
            'formats': formats,
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
