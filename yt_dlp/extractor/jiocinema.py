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

        payload = {
            "appName": "RJIL_JioCinema",
            "deviceType": "phone",
            "os": "ios",
            "deviceId": self.deviceId,
            "freshLaunch": True,
            "adId": self.deviceId,
            "appVersion": "23.11.22.0-dc532c79"
        }

        token_response = self._download_json(url_or_request=token_endpoint, video_id=None, note='Fetching Auth Token', data=bytes(json.dumps(payload), encoding='utf8'))

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

        if media_metadata_response['showName']:
            media_metadata['series'] = media_metadata_response['showName']
        media_metadata['title'] = media_metadata_response['fullTitle']
        media_metadata['description'] = media_metadata_response['fullSynopsis']
        if media_metadata_response['season']:
            media_metadata['season_number'] = int(media_metadata_response['season'])
        if media_metadata_response['episode']:
            media_metadata['episode_number'] = int(media_metadata_response['episode'])
        # media_metadata['subtitles'] = media_metadata_response['subtitles']

        return media_metadata

    def _get_stream_url(self, auth_token, media_id):
        stream_endpoint = 'https://apis-jiovoot.voot.com/playbackjv/v4/{media_id}'

        stream_endpoint = stream_endpoint.format(media_id=media_id)

        headers = {
            'accesstoken': auth_token,
            'x-platform': 'androidweb'
        }

        payload = {
            "4k": True,
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
                        "frameRateSupport": "60fps",
                        "videoQuality": "2160p"
                    }
                ]
            },
            "continueWatchingRequired": True,
            "dolby": False,
            "downloadRequest": False,
            "hevc": True,
            "kidsSafe": False,
            "manufacturer": "Mac OS",
            "model": "Mac OS",
            "multiAudioRequired": True,
            "osVersion": "10.15.7",
            "parentalPinValid": True
        }

        stream_response = self._download_json(url_or_request=stream_endpoint, video_id=None, note='Extracting Stream URL', data=bytes(json.dumps(payload), encoding='utf8'), headers=headers)

        mpd_url = None
        m3u8_url = None

        for url_data in stream_response['data']['playbackUrls']:
            if url_data['encryption'] == 'widevine':
                mpd_url = url_data['url']
            elif url_data['encryption'] == 'aes128':
                m3u8_url = url_data['url']

        return mpd_url, m3u8_url

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
        mpd_url, m3u8_url = self._get_stream_url(self.auth_token, media_id)

        formats = []
        formats.extend(self._extract_mpd_formats(mpd_url, media_id))
        formats.extend(self._extract_m3u8_formats(m3u8_url, media_id))

        response_dict = {
            'id': media_id,
            'formats': formats,
        }
        response_dict.update(media_metadata)
        return response_dict


class JioCinemaTVIE(JioCinemaBaseIE):
    _VALID_URL = r'https?://(?:www\.)?jiocinema\.com/tv-shows/(?P<media_name>[a-zA-Z0-9\-]*)/(?P<season_number>[0-9]*)/(?P<episode_name>[a-zA-Z0-9\-]*)/(?P<media_id>[a-zA-Z0-9\-]*)'
    _TEST = {
        'url': 'https://www.jiocinema.com/tv-shows/cedric/1/i-love-school/3769333',
        'info_dict': {
            'id': '3769333',
            'ext': 'mp4',
            'title': 'I Love School',
            'description': 'md5:71cc843e4ec65f62c6fd33cf38920198',
            'series': 'Cedric',
            'season_number': 1,
            'episode_number': 1,
            'episode': 'Episode 1',
            'season': 'Season 1',
        },
        'params': {
            'skip_download': True,
            'format': 'best'
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
            'description': 'md5:c224c04ce664ac2f41d85e2fb1d49b2f'
        },
        'params': {
            'skip_download': True,
            'format': 'best'
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
            'description': 'md5:71cc843e4ec65f62c6fd33cf38920198',
            'series': 'Cedric',
            'season_number': 1,
            'episode_number': 1,
            'episode': 'Episode 1',
            'season': 'Season 1',
        },
        'params': {
            'skip_download': True,
            'format': 'best'
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
        season_id_list = []

        for tray in season_data_response['trays']:
            if tray['title'] == 'Episodes':
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
