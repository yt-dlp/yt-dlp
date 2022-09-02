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
        json_info = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['ssr_data_showreel']

        # Get the broadcast URL and the recording hash.
        # The full URL is {broadcast_url}/{recording_hash}.mp3
        broadcast_url = json_info.get('broadcast_url')
        recording_hash = json_info.get('recording_hash')
        url = broadcast_url + recording_hash + ".mp3"

        # Get broadcast title
        broadcast_title = json_info.get('broadcast_title') or self._og_search_title(webpage)

        # Get dates
        start_date = json_info.get('start_date')
        if 'start_date' != '':
            start_date = start_date.replace('Z', '')

        end_date = json_info.get('end_date')
        if 'end_date' != '':
            end_date = end_date.replace('Z', '')

        # Get broadcast date
        upload_date = None
        if start_date is not None:
            upload_date = start_date.split('T')[0].replace('-', '')

        # Get author (AKA show host)
        uploader = json_info.get('user_name')

        # Get the co-hosts/guests
        if uploader != '':
            guests = [uploader]
        else:
            guests = []

        guests_json = json_info.get('guests_json')
        if guests_json != '':
            for guest in self._parse_json(json_info['guests_json'], video_id):
                guests.append(guest['name'])

        # Parse the duration of the stream
        parsed_duration = None
        if start_date != '' and end_date != '':
            duration = datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)
            parsed_duration = int(parse_duration(str(duration)))

        return {
            'id': video_id,
            'title': broadcast_title,
            'url': url,
            'upload_date': upload_date,
            'uploader': uploader,
            'duration': parsed_duration,
            'cast': ', '.join(guests)
        }
