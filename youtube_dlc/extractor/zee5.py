# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import try_get


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
        },
        'params': {
            'format': 'bv',
        },
    }

    def _real_extract(self, url):
        token_url = "https://useraction.zee5.com/tokennd"
        search_api_endpoint = "https://gwapi.zee5.com/content/details/{}?translation=en&country=IN"
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
        video_id = self._match_id(url)
        token_request = self._download_json(url_or_request=token_url, video_id=video_id, headers=headers)
        x_access_token = self._download_json(url_or_request=platform_token, video_id=video_id)["token"]
        headers["X-Access-Token"] = x_access_token
        json_data = self._download_json(url_or_request=search_api_endpoint.format(video_id), video_id=video_id, headers=headers,)
        partial_m3u8_url = (json_data["hls"][0].replace("drm", "hls") + token_request["video_token"])
        title = json_data['title']
        m3u8_url = stream_baseurl + partial_m3u8_url
        description = json_data['description']
        thumbnail = json_data['image_url']
        formats = self._extract_m3u8_formats(m3u8_url=m3u8_url, video_id=video_id)
        if json_data['asset_subtype'] == 'episode':
            show_title = try_get(json_data, lambda x: x['tvshow_details']['title'])
            season_title = try_get(json_data, lambda x: x['season_details']['title'])
            season_index = try_get(json_data, lambda x: x['season_details']['index'])
            ep_index = try_get(json_data, lambda x: x['index'])
        elif json_data['asset_subtype'] == 'movie':
            show_title = None
            season_title = None
            season_index = None
            ep_index = None
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

        }
