# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

import json
import math
import re
import uuid


class JioCinemaBaseIE(InfoExtractor):
    deviceId = None
    auth_token = None

    def _get_auth_token(self):
        token_endpoint = "https://auth-jiocinema.voot.com/tokenservice/apis/v4/guest"

        headers = {
            'authority': 'auth-jiocinema.voot.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-IN,en;q=0.9',
            'content-type': 'application/json',
            'dnt': '1',
            'origin': 'https://www.jiocinema.com',
            'referer': 'https://www.jiocinema.com/',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }

        payload = {
            "appName": "RJIL_JioCinema",
            "deviceType": "phone",
            "os": "ios",
            "deviceId": self.deviceId,
            "freshLaunch": True,
            "adId": self.deviceId,
            "appVersion": "23.11.22.0-dc532c79"
        }

        token_response = self._download_json(url_or_request=token_endpoint, video_id=None, note='Fetching Auth Token', data=bytes(json.dumps(payload), encoding='utf8'), headers=headers)

        if "authToken" in token_response:
            return token_response["authToken"]

        return None

    def _get_media_metadata(self, media_id):
        media_metadata = {}
        metadata_endpoint_template = 'https://content-jiovoot.voot.com/psapi/voot/v1/voot-web/content/query/asset-details?&ids=include:{media_id}&responseType=common&devicePlatformType=desktop'

        metadata_endpoint = metadata_endpoint_template.format(media_id=media_id)

        media_metadata_response = self._download_json(metadata_endpoint, None, 'Fetching Episode Metadata')

        if media_metadata_response and 'result' in media_metadata_response and media_metadata_response['result']:
            media_metadata_response = media_metadata_response['result'][0]

        media_metadata['showName'] = media_metadata_response['showName']
        media_metadata['title'] = media_metadata_response['fullTitle']
        media_metadata['shortTitle'] = media_metadata_response['shortTitle']
        media_metadata['shortSynopsis'] = media_metadata_response['shortSynopsis']
        media_metadata['fullSynopsis'] = media_metadata_response['fullSynopsis']
        media_metadata['showName'] = media_metadata_response['showName']
        media_metadata['season'] = media_metadata_response['season']
        media_metadata['episode'] = media_metadata_response['episode']
        media_metadata['multiTrackAudioEnabled'] = media_metadata_response['multiTrackAudioEnabled']
        media_metadata['introStart'] = media_metadata_response['introStart']
        media_metadata['introEnd'] = media_metadata_response['introEnd']
        media_metadata['recapStart'] = media_metadata_response['recapStart']
        media_metadata['recapEnd'] = media_metadata_response['recapEnd']
        media_metadata['creditStart'] = media_metadata_response['creditStart']
        media_metadata['creditEnd'] = media_metadata_response['creditEnd']
        media_metadata['is4KSupported'] = media_metadata_response['is4KSupported']
        media_metadata['is1080PSupported'] = media_metadata_response['is1080PSupported']
        media_metadata['isDolbySupported'] = media_metadata_response['isDolbySupported']
        media_metadata['hasSubtitles'] = media_metadata_response['hasSubtitles']
        media_metadata['subtitles'] = media_metadata_response['subtitles']

        return media_metadata

    def _get_stream_url(self, auth_token, media_id):
        stream_endpoint = 'https://apis-jiovoot.voot.com/playbackjv/v4/{media_id}'

        stream_endpoint = stream_endpoint.format(media_id=media_id)

        headers = {
            'authority': 'apis-jiovoot.voot.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6',
            'accesstoken': auth_token,
            'appname': 'RJIL_JioCinema',
            'content-type': 'application/json',
            'deviceid': self.deviceId,
            'dnt': '1',
            'origin': 'https://www.jiocinema.com',
            'referer': 'https://www.jiocinema.com/',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'uniqueid': self.deviceId,
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'versioncode': '2311030',
            'x-platform': 'androidweb',
            'x-platform-token': 'web'
        }

        payload = {
            "4k": False,
            "ageGroup": "18+",
            "appVersion": "3.4.0",
            "bitrateProfile": "xhdpi",
            "capability": {
                "drmCapability": {
                    "aesSupport": "yes",
                    "fairPlayDrmSupport": "yes",
                    "playreadyDrmSupport": "none",
                    "widevineDRMSupport": "yes"
                },
                "frameRateCapability": [
                    {
                        "frameRateSupport": "30fps",
                        "videoQuality": "1440p"
                    }
                ]
            },
            "continueWatchingRequired": True,
            "dolby": False,
            "downloadRequest": False,
            "hevc": False,
            "kidsSafe": False,
            "manufacturer": "Mac OS",
            "model": "Mac OS",
            "multiAudioRequired": True,
            "osVersion": "10.15.7",
            "parentalPinValid": True
        }

        stream_response = self._download_json(url_or_request=stream_endpoint, video_id=None, note='Extracting Stream URL', data=bytes(json.dumps(payload), encoding='utf8'), headers=headers)

        for url_data in stream_response['data']['playbackUrls']:
            if url_data['encryption'] == 'widevine':
                return url_data['url']

    def _real_initialize(self):
        super()._real_initialize()
        if self.deviceId is None:
            self.deviceId = str(uuid.uuid4())

        self.auth_token = self._get_auth_token()

    def _real_extract(self, url):
        media_name, season_number, episode_name, media_id = re.match(self._VALID_URL, url).groups()

        if not self.auth_token:
            return

        media_metadata = self._get_media_metadata(media_id)
        mpd_url = self._get_stream_url(self.auth_token, media_id)

        formats = []
        formats.extend(self._extract_mpd_formats(mpd_url, media_id))

        self._sort_formats(formats)
        response_dict = {
            'id': media_id,
            'formats': formats,
        }
        response_dict.update(media_metadata)
        return response_dict


class JioCinemaTVIE(JioCinemaBaseIE):
    _VALID_URL = r'https?://(?:www\.)?jiocinema\.com/tv-shows/(?P<media_name>[a-zA-Z0-9\-]*)/(?P<season_number>[0-9]*)/(?P<episode_name>[a-zA-Z0-9\-]*)/(?P<media_id>[a-zA-Z0-9\-]*)'
    _TEST = {
        'url': 'https://www.jiocinema.com/tv-shows/cedric/2/mister-fixit/3769452',
        'info_dict': {
            'id': '3769452',
            'ext': 'mp4',
            'title': 'Mister Fixit',
            'shortTitle': 'Mister Fixit',
            'shortSynopsis': 'Cedric offers to fix Chen\'s broken walkman, however he realises that it is much harder than he thought it\'d be. He thinks of taking help from his father and Poppy, but th',
            'fullSynopsis': 'Cedric offers to fix Chen\'s broken walkman, however he realises that it is much harder than he thought it\'d be. He thinks of taking help from his father and Poppy, but they get into an argument over who is a better handyman. Will Cedric be able to fix Chen\'s walkman as promised?',
            'is4KSupported': False,
            'is1080PSupported': False,
            'isDolbySupported': False,
            'introStart': 0,
            'introEnd': 5,
            'creditStart': 765,
            'creditEnd': 770,
            'recapStart': 0,
            'recapEnd': 0,
            'hasSubtitles': False,
            'multiTrackAudioEnabled': False,
            'season': '2',
            'showName': 'Cedric',
            'episode': '1'
        },
        'params': {
            'skip_download': True,
            'format': 'bestvideo'
        }
    }


class JioCinemaMovieIE(JioCinemaBaseIE):
    _VALID_URL = r'https?://(?:www\.)?jiocinema\.com/movies/(?P<media_name>[a-zA-Z0-9\-]*)/?(?P<season_number>[0-9]*)?/?(?P<episode_name>[a-zA-Z0-9\-]*)?/(?P<media_id>[a-zA-Z0-9\-]*)'
    _TEST = {
        'url': 'https://www.jiocinema.com/movies/i-choose-you-pokemon-the-movie/3777402',
        'info_dict': {
            'id': '3777402',
            'ext': 'mp4',
            'title': 'I Choose You! - Pokemon the Movie',
            'shortTitle': 'I Choose You! - Pokemon the Movie',
            'shortSynopsis': 'When Ash Ketchum oversleeps on his 10th birthday, he ends up with a stubborn Pikachu instead of the first partner Pokémon he wanted! But after a rocky start, Ash and Pika',
            'fullSynopsis': 'When Ash Ketchum oversleeps on his 10th birthday, he ends up with a stubborn Pikachu instead of the first partner Pokémon he wanted! But after a rocky start, Ash and Pikachu become close friends and true partners—and when they catch a rare glimpse of the Legendary Pokémon Ho-Oh in flight, they make plans to seek it out together, guided by the Rainbow Wing it leaves behind. Trainers Verity and Sorrel join Ash on his journey. Along the way, Ash catches an abandoned Charmander, raises a Pokémon from Caterpie to Butterfree and then releases it to follow its heart, and meets the mysterious Mythical Pokémon Marshadow. When they near their goal, the arrogant Cross—Charmander\'s former Trainer—stands in their way! Can Ash and Pikachu defeat this powerful Trainer and reach Ho-Oh as they promised, or will their journey end here?',
            'is4KSupported': False,
            'is1080PSupported': False,
            'isDolbySupported': False,
            'introStart': 0,
            'introEnd': 0,
            'creditStart': 0,
            'creditEnd': 0,
            'recapStart': 0,
            'recapEnd': 0,
            'showName': '',
            'episode': '',
            'season': '',
            'hasSubtitles': False,
            'multiTrackAudioEnabled': False
        },
        'params': {
            'skip_download': True,
            'format': 'bestvideo'
        }
    }


class JioCinemaTVSeasonIE(JioCinemaBaseIE):
    _VALID_URL = r'https?://(?:www\.)?jiocinema\.com/tv-shows/(?P<playlist_name>[a-zA-Z0-9\-]*)/(?P<playlist_id>[a-zA-Z0-9\-]*)$'
    _TEST = {
        'url': 'https://www.jiocinema.com/tv-shows/cedric/3768448',
        'info_dict': {
            'id': '3769333',
            'ext': 'mp4',
            'title': 'I Love School',
            'shortTitle': 'I Love School',
            'shortSynopsis': 'Cedric loves going to school but his report card doesn\'t reflect his enthusiasm. Cedric\'s dad scolds him for his poor performance but he is least bothered and starts drea',
            'fullSynopsis': 'Cedric loves going to school but his report card doesn\'t reflect his enthusiasm. Cedric\'s dad scolds him for his poor performance but he is least bothered and starts dreaming about his teacher at school, with whom he is in love with.',
            'is4KSupported': False,
            'is1080PSupported': False,
            'isDolbySupported': False,
            'introStart': 0,
            'introEnd': 5,
            'creditStart': 764,
            'creditEnd': 769,
            'recapStart': 0,
            'recapEnd': 0,
            'showName': 'Cedric',
            'episode': '1',
            'season': '1',
            'hasSubtitles': False,
            'multiTrackAudioEnabled': False
        },
        'params': {
            'skip_download': True,
            'format': 'bestvideo'
        }
    }

    def _real_extract(self, url):
        playlist_entries = []
        playlist_name, playlist_id = re.match(self._VALID_URL, url).groups()
        season_data_url_template = 'https://content-jiovoot.voot.com/psapi/voot/v1/voot-web/view/show/{playlist_id}?responseType=common&devicePlatformType=desktop&layoutCohort=default'
        season_data_url = season_data_url_template.format(playlist_id=playlist_id)
        season_data_response = self._download_json(season_data_url, None, 'Fetching Season Info')
        season_id_list = self._extract_season_id_list(season_data_response)
        playlist_entries = self._fetch_episode_data(season_id_list)
        return self.playlist_result(playlist_entries)

    def _extract_season_id_list(self, season_data_response):
        season_count = 0
        season_id_list = []

        for tray in season_data_response['trays']:
            if tray['title'] == 'Episodes':
                season_count = tray['totalTrayTabs']
                for season in tray['trayTabs']:
                    season_id_list.append(season['id'])
                break
        return season_id_list

    def _fetch_episode_data(self, season_id_list):
        episode_url_list = []
        for season_id in season_id_list:
            episode_list_template = 'https://content-jiovoot.voot.com/psapi/voot/v1/voot-web/content/generic/series-wise-episode?sort=episode%3Aasc&id={season_id}&responseType=common&page={page_number}'
            page_number = 1
            total_pages = 1

            episode_details_list_url = episode_list_template.format(season_id=season_id, page_number=page_number)

            paginated_episode_list = self._download_json(episode_details_list_url, None, 'Fetching Episode List')
            episode_url_list.extend(self._extract_episode_urls(paginated_episode_list))
            total_pages = math.ceil(paginated_episode_list['totalAsset'] / 10)

            page_number += 1
            while page_number <= total_pages:
                episode_details_list_url = episode_list_template.format(season_id=season_id, page_number=page_number)
                paginated_episode_list = self._download_json(episode_details_list_url, None, 'Fetching Episode List')
                episode_url_list.extend(self._extract_episode_urls(paginated_episode_list))
                page_number += 1
        return episode_url_list

    def _extract_episode_urls(self, episode_response_list):
        episode_url_list = []
        for episode in episode_response_list['result']:
            episode_url_list.append(self.url_result(episode['slug']))
        return episode_url_list
