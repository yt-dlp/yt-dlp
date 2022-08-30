import json
from datetime import datetime
from .common import InfoExtractor
from ..utils import parse_duration


class PrankCastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?prankcast\.com/.*/showreel/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://prankcast.com/Devonanustart/showreel/1561-Beverly-is-back-like-a-heart-attack-',
        'info_dict': {
            'id': '1561',
            'ext': 'mp3',
            'title': 'Beverly is back like a heart attack!',
            'uploader': 'Devonanustart',
            'upload_date': '20220825'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # Extract the JSON
        json_info = self._search_nextjs_data(webpage, video_id)

        # Get the broadcast URL and the recording hash.
        # The full URL is {broadcast_url}/{recording_hash}.mp3
        broadcast_url = json_info['props']['pageProps']['ssr_data_showreel']['broadcast_url']
        recording_hash = json_info['props']['pageProps']['ssr_data_showreel']['recording_hash']
        url = broadcast_url + recording_hash + ".mp3"

        # Get dates
        start_date = json_info['props']['pageProps']['ssr_data_showreel']['start_date'].replace('Z', '')
        end_date = json_info['props']['pageProps']['ssr_data_showreel']['end_date'].replace('Z', '')

        # Get broadcast date
        upload_date = start_date.split('T')[0].replace('-', '')

        # Get broadcast title
        broadcast_title = json_info['props']['pageProps']['ssr_data_showreel']['broadcast_title']

        # Get author (AKA show host)
        uploader = json_info['props']['pageProps']['ssr_data_showreel']['user_name']

        # Get the co-hosts/guests
        guests = [uploader]
        for guest in json.loads(json_info['props']['pageProps']['ssr_data_showreel']['guests_json']):
            guests.append(guest['name'])

        # Parse the duration of the stream
        duration = datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)
        parsed_duration = int(parse_duration(str(duration)))

        return {
            'id': video_id,
            'title': broadcast_title,
            'upload_date': upload_date,
            'uploader': uploader,
            'url': url,
            'duration': parsed_duration,
            'cast': ', '.join(guests)
        }
