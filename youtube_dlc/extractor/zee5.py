# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

import requests

token_url = "https://useraction.zee5.com/tokennd"
search_api_endpoint = "https://gwapi.zee5.com/content/details/"
platform_token = "https://useraction.zee5.com/token/platform_tokens.php?platform_name=web_app"
stream_baseurl = "https://zee5vodnd.akamaized.net"

headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-J400F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Mobile Safari/537.36",
    "Referer": "https://www.zee5.com",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.zee5.com",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}


class Zee5IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?zee5\.com/.*/(?P<id>.*)'
    _TEST = {
        'url': 'https://www.zee5.com/movies/details/krishna-the-birth/0-0-63098',
        # 'md5': 'cd5abd10fab020dbb633cb8e94df0e12',
        'info_dict': {
            'id': '0-0-63098',
            'ext': 'm3u8',
            'title': 'Krishna - The Birth',
            'thumbnail': 'https://akamaividz.zee5.com/resources/0-0-63098/list/270x152/0063098_list_80888170.jpg',
            'description': str,
            'show': str,
            'season_title': str,
            'season_index': str,
            'ep_index': str,
        },
        'params': {
            'format': 'bv',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # webpage = self._download_webpage(url, video_id)

        # TODO more code goes here, for example ...
        token_request = requests.get(token_url, headers=headers).json()
        x_access_token = requests.get(platform_token).json()["token"]
        headers["X-Access-Token"] = x_access_token
        json_data = requests.get(search_api_endpoint + video_id, headers=headers,
                                 params={"translation": "en", "country": "IN"}).json()
        partial_m3u8_url = (json_data["hls"][0].replace("drm", "hls") + token_request["video_token"])
        title = json_data['title']
        m3u8_url = stream_baseurl + partial_m3u8_url
        description = json_data['description']
        thumbnail = json_data['image_url']
        formats = self._extract_m3u8_formats(m3u8_url=m3u8_url, video_id=video_id)
        if json_data['asset_subtype'] == 'episode':
            show_title = json_data['tvshow_details']['title']
            season_title = json_data['season_details']['title']
            season_index = json_data['season_details']['index']
            ep_index = json_data['index']
        elif json_data['asset_subtype'] == 'movie':
            show_title = 'None'
            season_title = 'None'
            season_index = 'None'
            ep_index = 'None'
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': description,
            'thumbnail': thumbnail,
            'show_title': show_title,
            'season_title': season_title,
            'season_index': season_index,
            'ep_index': ep_index,

            # TODO more properties (see youtube_dl/extractor/common.py)
        }
