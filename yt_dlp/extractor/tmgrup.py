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


# Turkuvaz Haberlesme ve Yayincilik A.S. extractor
class TmGrupIE(InfoExtractor):
    # Extracted from below functions at https://i.tmgrup.com.tr/videojs/js/tmdplayersetupv2.js?v=792
    # - PlayerDaion()
    # - TmdConfig.setConfigWebsiteExclusive()
    _CHANNEL = {
        'id': 'atv',
        'title': 'atv',
        'website_id': '0fe2a405-8afa-4238-b429-e5f96aec3a5c',
        'domain': 'www.atv.com.tr',
    }

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

    # Extracts player data from html
    def _extract_player_data(self, html):
        attributes = re.findall(r'data-([a-z]+)="([^"]+)"', html)
        attributes = dict(attributes)
        if 'videoid' not in attributes:
            return {}
        return attributes

    # Get thumbnails from scaled down url
    def _build_thumbnails(self, url):
        if not url:
            return []

        # url has thumbnail dimensions in path of url
        # ex. https://iaatv.tmgrup.com.tr/b8d958/959/566/0/0/1700/1003?u=https://iatv.tmgrup.com.tr/2025/07/04/aile-saadeti-1751635923569.jpg
        #     | original  | scaled  |
        #     |-----------|---------|
        #     | 1700x1003 | 959x566 |

        path, query = url.split('?', 1)
        parts = path.rsplit('/', 6)
        original_url = query.split('=', 1)[1]
        return [
            {
                'id': 'normal',
                'url': url,
                'width': int(parts[1]),
                'height': int(parts[2]),
                'preference': 1,
            },
            {
                'id': 'large',
                'url': original_url,
                'width': int(parts[5]),
                'height': int(parts[6]),
                'preference': 2,
            },
        ]

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
                                   headers={'referer': f"https://{self._CHANNEL['domain']}/"})

    def _videojs_get_video(self, video_id, note):
        website_id = self._CHANNEL['website_id']
        return self._download_json(f'https://videojs.tmgrup.com.tr/getvideo/{website_id}/{video_id}', website_id, note,
                                   headers={'referer': f"https://{self._CHANNEL['domain']}/"})

    def _videojs_get_live_stream(self):
        video_id = '00000000-0000-0000-0000-000000000000'
        return self._videojs_get_video(video_id, 'Get live stream metadata')


class TmGrupGenericIE(TmGrupIE):
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
            'title': f"{self._CHANNEL['title']} Canlı Yayın",
            'is_live:': True,
            'format_id': 'hls',
            'protocol': 'm3u8',
            'formats': formats,
        }

    def _real_extract(self, url):
        path = self._match_id(url)

        if path == 'canli-yayin' or path == 'live-broadcast':
            return self._live_stream()

        webpage = self._download_webpage(url, path)
        encrypted_video_id = self._extract_player_data(webpage).get('videoid', '')
        if not encrypted_video_id:
            raise ExtractorError('Unable to extract video id')

        json = self._videojs_get_video(encrypted_video_id, 'Downloading video metadata')
        if not json['success']:
            raise ExtractorError(f'Failed with "{json["message"]}"')

        video = json['video']
        video_id = video['VideoId']
        formats = self._extract_m3u8_formats(video['VideoSmilUrl'], video_id, 'mp4', m3u8_id='hls', fatal=False)

        url = video['VideoUrl']
        if url:
            basename, ext = url.rsplit('.', 1)
            parts = basename.split('_', 3)

            video_format = {
                'url': url,
                'format_id': 'https-mp4',
                'vcodec': 'h264',
                'acodec': 'aac',
                'ext': 'mp4',
            }

            parts_len = len(parts)
            if parts_len == 1:
                raise ExtractorError('unexpected video url')

            if parts_len == 2:
                # ex. https://.../{video_id}_{tbr}.mp4
                video_format['tbr'] = int_or_none(parts[1])
            elif parts_len == 3:
                # ex. https://.../{video_id}_{resolution}p_{tbr}k.mp4
                video_format['height'] = int_or_none(parts[1][:-1])  # ex. 720p 1080p
                video_format['tbr'] = int_or_none(parts[2][:-1])

            formats.append(video_format)
        thumbnails = self._build_thumbnails(video['PathForPlayer'])

        return {
            'id': video_id,
            'title': video['Title'],
            'formats': formats,
            'thumbnails': thumbnails,
            'language': 'tr',
            'duration': int_or_none(video.get('VideoDuration')),
            # TODO: fix below timestamp
            'timestamp': int(video.get('CreatedDate').removeprefix('/Date(').removesuffix(')/')[:-3]),
        }


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
        thumbnails = self._build_thumbnails(video_player.get('image'))

        return {
            'id': video_id,
            'title': video_player.get('title'),
            'formats': formats,
            'thumbnails': thumbnails,
            'language': 'tr',
            'duration': int_or_none(video_player.get('videoDuration')),
            'release_timestamp': parse_iso8601(video_player.get('publishedDate')),
            'webpage_url': traverse_obj(json, ('stats', 'firebase', 'event', 'dimensions', 'page_location')),
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
            'playlist_count': 54,
        },
        {
            'url': 'https://www.atv.com.tr/avrupa-yakasi/bolumler',
            'info_dict': {
                'id': 'de68e8b2-4ec5-4321-8e81-1bfa2cef2a3f',
            },
            # Should be 190 but episodes 145 and 159 are missing
            'playlist_count': 188,
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


class A2tvLiveIE(TmGrupIE):
    _CHANNEL = {
        'id': 'a2tv',
        'title': 'a2tv',
        'website_id': '0c1bc8ff-c3b1-45be-a95b-f7bb9c8b03ed',
        'domain': 'www.atv.com.tr',
    }
    _VALID_URL = r'https?://(www\.)?atv\.com\.tr/a2tv/canli-yayin'

    def _real_extract(self, url):
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
            'title': 'a2tv Canlı Yayın',
            'is_live:': True,
            'format_id': 'hls',
            'protocol': 'm3u8',
            'formats': formats,
        }


# TODO: see the android app for other API endpoints
class AHaberIE(TmGrupGenericIE):
    _CHANNEL = {
        'id': 'ahaber',
        'title': 'A Haber',
        'website_id': 'c0fbbd0d-b4cb-4e5b-b516-9993b9e506c3',
        'domain': 'www.ahaber.com.tr',
    }
    _VALID_URL = r'https?://(?:www\.)?ahaber\.com\.tr/video/(?P<id>.*)'
    _TESTS = [
        {
            'url': 'https://www.ahaber.com.tr/video/yasam-videolari/afyonkarahisarda-motosiklet-surucusunun-oldugu-kaza-kamerada',
            'info_dict': {
                'id': '4500a9d0-79f1-40a0-b78c-d535c1f686c3',
                'title': "Afyonkarahisar'da motosiklet sürücüsünün öldüğü kaza kamerada",
                'thumbnails': [
                    {
                        'id': 'normal',
                        'url': 'https://iaahbr.tmgrup.com.tr/125c2d/960/540/0/0/1920/1080?u=https://iahbr.tmgrup.com.tr/2025/09/16/afyonkarahisarda-motosiklet-surucusunun-oldugu-kaza-kamerada-1758010375494.jpeg',
                        'width': 960,
                        'height': 540,
                    },
                    {
                        'id': 'large',
                        'url': 'https://iahbr.tmgrup.com.tr/2025/09/16/afyonkarahisarda-motosiklet-surucusunun-oldugu-kaza-kamerada-1758010375494.jpeg',
                        'width': 1920,
                        'height': 1080,
                    },
                ],
                'thumbnail': 'https://iahbr.tmgrup.com.tr/2025/09/16/afyonkarahisarda-motosiklet-surucusunun-oldugu-kaza-kamerada-1758010375494.jpeg',
                'duration': 22,
                'upload_date': '20250916',
                'timestamp': 1757970000,
                'ext': 'mp4',
            },
        },
    ]


class ANewsIE(TmGrupGenericIE):
    _CHANNEL = {
        'id': 'anews',
        'title': 'A News',
        'website_id': 'e88d795b-b27a-4b92-8fc0-d1f650213863',
        'domain': 'www.anews.com.tr',
    }
    _VALID_URL = r'https?://(?:www\.)?anews\.com\.tr/webtv/(?P<id>.*)'
    _TESTS = [
    ]


class ASporIE(TmGrupGenericIE):
    _CHANNEL = {
        'id': 'aspor',
        'title': 'A Spor',
        'website_id': '9bbe055a-4cf6-4bc3-a675-d40e89b55b91',
        'domain': 'www.aspor.com.tr',
    }
    _VALID_URL = r'https?://(?:www\.)?aspor\.com\.tr/webtv/(?P<id>.*)'
    _TESTS = [
    ]


class FotomacIE(TmGrupGenericIE):
    _CHANNEL = {
        'id': 'fotomac',
        'title': 'fotoMaç',
        'website_id': 'ac97138b-a800-4e53-94e4-d6bf4e6782ab',
        'domain': 'www.fotomac.com.tr',
    }
    _VALID_URL = r'https?://(?:www\.)?fotomac\.com\.tr/video-haber/(?P<id>.*)'
    _TESTS = [
    ]

# TODO: implement extractor for below sites
#   'aktuel': {
#       'website_id': '36ED4123-943D-49FC-8AE5-24D37ECAA63E',
#       'domain': 'www.aktuel.com.tr',
#   },
#   'apara': {
#       'website_id': '1c2ecfe1-ec83-4b4b-ba39-3af0e845f456',
#       'domain': 'www.apara.com.tr',
#   },
#   'atvavrupa': {
#       'website_id': '45D4CD69-814C-4E2E-BDAD-11DE9E4B9AFD',
#       'domain': 'www.atvavrupa.tv',
#   },
#   'atvdistribution': {
#       'website_id': 'ebacdd4c-74bc-43fc-92aa-d08159df40fe',
#       'domain': 'www.atvdistribution.com',
#   },
#   'cosmopolitan': {
#       'website_id': '34cd4123-943d-49fc-8ae5-24d37ecaa669',
#       'domain': 'www.cosmopolitanturkiye.com',
#   },
#   'dailysabah': {
#       'website_id': '9f694053-ed61-4c74-a43a-8787e6002b58',
#       'domain': 'www.dailysabah.com',
#   },
#   'esquire': {
#       'website_id': '523e8243-b6bf-405a-9052-aebf5a59fcf8',
#       'domain': 'www.esquire.com.tr',
#   },
#   'fikriyat': {
#       'website_id': '2bf2426b-2228-4b0e-9400-8d42f1b6895f',
#       'domain': 'www.fikriyat.com',
#   },
#   'fityasa': {
#       'website_id': 'ee86c4db-d4cb-4bd5-b928-56fd44384374',
#       'domain': 'www.fityasa.com.tr',
#   },
#   'harpersbazaar': {
#       'website_id': '779b03ff-4989-46ac-a6fe-8c79d70ed60b',
#       'domain': 'www.harpersbazaar.com.tr',
#   },
#   'minikacocuk': {
#       'website_id': '01ed59f2-4067-4945-8204-45f6c6db4045',
#       'domain': 'www.minikacocuk.com.tr',
#   },
#   'minikago': {
#       'website_id': 'aae2e325-4eae-45b7-b017-26fd7ddb6ce4',
#       'domain': 'www.minikago.com.tr',
#   },
#   'otohaber': {
#       'website_id': 'D6C0ED15-C37F-48CD-A5AF-BB187CDB3CFD',
#       'domain': 'www.otohaber.com.tr',
#   },
#   'sabah': {
#       'website_id': '50450b66-f39e-4dd8-867b-4d2e15726a5f',
#       'domain': 'www.sabah.com.tr',
#   },
#   'samdan': {
#       'website_id': '1A20B172-26B8-49D0-9B7F-A47E8EAE38BB',
#       'domain': 'www.samdan.com.tr',
#   },
#   'sofra': {
#       'website_id': '5397bf0c-1694-4ee5-80e3-a8598dfe2c39',
#       'domain': 'www.sofra.com.tr',
#   },
#   'takvim': {
#       'website_id': '0E497DBB-D79A-4F7A-9BEB-7E6C1BCD7216',
#       'domain': 'www.takvim.com.tr',
#   },
#   'teknokulis': {
#       'website_id': '56D89D93-90CE-4C16-A26E-27B4A91293B6',
#       'domain': 'www.teknokulis.com',
#   },
#   'turkuvapp': {
#       'website_id': '46c4d652-21a8-4945-9714-60d6560b1ca0',
#       'domain': 'www.turkuvapp.com',
#   },
#   'turkuvazradyo': {
#       'website_id': 'ed05f08d-f444-48cb-8c53-973a96daa466',
#       'domain': 'www.turkuvazradyolar.com',
#   },
#   'usasabah': {
#       'website_id': 'f5833018-f743-4f26-b1fc-88467c0816a4',
#       'domain': 'www.usasabah.com.tr',
#   },
#   'vavtv': {
#       'website_id': 'c71d7dd4-1b6c-4cf6-a4fe-38d864c6d052',
#       'domain': 'www.vavtv.com.tr',
#   },
#   'yeniasir': {
#       'website_id': '35CA7526-A797-40B0-9E44-7340F0225745',
#       'domain': 'www.yeniasir.com.tr',
#   },
#
