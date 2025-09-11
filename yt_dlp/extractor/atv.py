import re
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    int_or_none,
    parse_iso8601,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
)


class TmGrupIE(InfoExtractor):
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
        # Extracted from below functions at https://i.tmgrup.com.tr/videojs/js/tmdplayersetupv2.js?v=792
        # - PlayerDaion()
        # - TmdConfig.setConfigWebsiteExclusive()
        # These are mainly published by two different CDNs
        # - https://trkvz-live.ercdn.net/{channel}/{channel}.m3u8
        # - https://trkvz.daioncdn.net/{channel}/{channel}.m3u8
        CHANNELS = {
            'a2tv': {
                'website_id': '0c1bc8ff-c3b1-45be-a95b-f7bb9c8b03ed',
                'domain': 'www.atv.com.tr',
            },
            'ahaber': {
                'website_id': 'c0fbbd0d-b4cb-4e5b-b516-9993b9e506c3',
                'domain': 'www.ahaber.com.tr',
            },
            'aktuel': {
                'website_id': '36ED4123-943D-49FC-8AE5-24D37ECAA63E',
                'domain': 'www.aktuel.com.tr',
            },
            'anews': {
                'website_id': 'E88D795B-B27A-4B92-8FC0-D1F650213863',
                'domain': 'www.anews.com.tr',
            },
            'apara': {
                'website_id': '1c2ecfe1-ec83-4b4b-ba39-3af0e845f456',
                'domain': 'www.apara.com.tr',
            },
            'aspor': {
                'website_id': '9bbe055a-4cf6-4bc3-a675-d40e89b55b91',
                'domain': 'www.aspor.com.tr',
            },
            'atv': {
                'website_id': '0fe2a405-8afa-4238-b429-e5f96aec3a5c',
                'domain': 'www.atv.com.tr',
            },
            'atvavrupa': {
                'website_id': '45D4CD69-814C-4E2E-BDAD-11DE9E4B9AFD',
                'domain': 'www.atvavrupa.tv',
            },
            'atvdistribution': {
                'website_id': 'EBACDD4C-74BC-43FC-92AA-D08159DF40FE',
                'domain': 'www.atvdistribution.com',
            },
            'cosmopolitan': {
                'website_id': '34CD4123-943D-49FC-8AE5-24D37ECAA669',
                'domain': 'www.cosmopolitanturkiye.com',
            },
            'dailysabah': {
                'website_id': '9f694053-ed61-4c74-a43a-8787e6002b58',
                'domain': 'www.dailysabah.com',
            },
            'esquire': {
                'website_id': '523E8243-B6BF-405A-9052-AEBF5A59FCF8',
                'domain': 'www.esquire.com.tr',
            },
            'fikriyat': {
                'website_id': '2bf2426b-2228-4b0e-9400-8d42f1b6895f',
                'domain': 'www.fikriyat.com',
            },
            'fityasa': {
                'website_id': 'ee86c4db-d4cb-4bd5-b928-56fd44384374',
                'domain': 'www.fityasa.com.tr',
            },
            'fotomac': {
                'website_id': 'ac97138b-a800-4e53-94e4-d6bf4e6782ab',
                'domain': 'www.fotomac.com.tr',
            },
            'harpersbazaar': {
                'website_id': '779B03FF-4989-46AC-A6FE-8C79D70ED60B',
                'domain': 'www.harpersbazaar.com.tr',
            },
            'minikacocuk': {
                'website_id': '01ed59f2-4067-4945-8204-45f6c6db4045',
                'domain': 'www.minikacocuk.com.tr',
            },
            'minikago': {
                'website_id': 'aae2e325-4eae-45b7-b017-26fd7ddb6ce4',
                'domain': 'www.minikago.com.tr',
            },
            'otohaber': {
                'website_id': 'D6C0ED15-C37F-48CD-A5AF-BB187CDB3CFD',
                'domain': 'www.otohaber.com.tr',
            },
            'sabah': {
                'website_id': '50450b66-f39e-4dd8-867b-4d2e15726a5f',
                'domain': 'www.sabah.com.tr',
            },
            'samdan': {
                'website_id': '1A20B172-26B8-49D0-9B7F-A47E8EAE38BB',
                'domain': 'www.samdan.com.tr',
            },
            'sofra': {
                'website_id': '5397bf0c-1694-4ee5-80e3-a8598dfe2c39',
                'domain': 'www.sofra.com.tr',
            },
            'takvim': {
                'website_id': '0E497DBB-D79A-4F7A-9BEB-7E6C1BCD7216',
                'domain': 'www.takvim.com.tr',
            },
            'teknokulis': {
                'website_id': '56D89D93-90CE-4C16-A26E-27B4A91293B6',
                'domain': 'www.teknokulis.com',
            },
            'turkuvapp': {
                'website_id': '46c4d652-21a8-4945-9714-60d6560b1ca0',
                'domain': 'www.turkuvapp.com',
            },
            'turkuvazradyo': {
                'website_id': 'ed05f08d-f444-48cb-8c53-973a96daa466',
                'domain': 'www.turkuvazradyolar.com',
            },
            'usasabah': {
                'website_id': 'f5833018-f743-4f26-b1fc-88467c0816a4',
                'domain': 'www.usasabah.com.tr',
            },
            'vavtv': {
                'website_id': 'c71d7dd4-1b6c-4cf6-a4fe-38d864c6d052',
                'domain': 'www.vavtv.com.tr',
            },
            'yeniasir': {
                'website_id': '35CA7526-A797-40B0-9E44-7340F0225745',
                'domain': 'www.yeniasir.com.tr',
            },
        }
        channel = CHANNELS[channel]
        website_id = channel['website_id']
        return self._download_json(f'https://videojs.tmgrup.com.tr/getvideo/{website_id}/{video_id}', website_id, note,
                                   headers={'referer': f"https://{channel['domain']}/"})

    def _videojs_get_live_stream(self, channel='atv'):
        video_id = '00000000-0000-0000-0000-000000000000'
        return self._videojs_get_video(video_id, 'Get live stream metadata', channel=channel)


class AtvIE(TmGrupIE):
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
        {  # invalid duration
            'url': 'https://www.atv.com.tr/karadayi/113-bolum/izle',
            'info_dict': {
                'id': '02f9fbe4-0e4d-434b-8b1c-ad8dc3425323',
                'title': 'Karadayı',
                'release_date': '20190725',
                'release_timestamp': 1564076474,
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
            'duration': int_or_none(video_player.get('videoDuration')),
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


class AtvSeriesIE(TmGrupIE):
    _VALID_URL = r'https?://(?:www\.)?atv\.com\.tr/(?P<id>[a-z\-]+)(/bolumler)?$'
    _TESTS = [
        {
            'url': 'https://www.atv.com.tr/can-borcu',
            'info_dict': {
                'id': '4a8459e8-ba0c-4eb8-a7d3-3982cea3a8a2',
            },
            'playlist_min_count': 23,
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
                yield self.url_result(url, AtvIE, video_id, url_transparent=True, title=f'{title} {spot}')

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
