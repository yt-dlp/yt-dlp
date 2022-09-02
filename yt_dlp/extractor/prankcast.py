from .common import InfoExtractor
from ..utils import parse_iso8601


class PrankCastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?prankcast\.com/.*/showreel/(?P<id>\d+)-(?P<display_id>.+)'
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
        match = self._match_valid_url(url).groupdict()
        video_id, display_id = match['id'], match['display_id']

        webpage = self._download_webpage(url, video_id)

        # Extract the JSON
        json_info = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['ssr_data_showreel']

        # Get the broadcast URL and the recording hash.
        # The full URL is {broadcast_url}/{recording_hash}.mp3
        broadcast_url = json_info.get('broadcast_url')
        recording_hash = json_info.get('recording_hash')
        url = broadcast_url + recording_hash + ".mp3"

        # Get broadcast info
        broadcast_title = json_info.get('broadcast_title')
        broadcast_description = json_info.get('broadcast_description')
        broadcast_category = json_info.get('broadcast_category')
        broadcast_tags = self._parse_json(json_info.get('broadcast_tags'), video_id)

        # Get author (AKA show host)
        uploader = json_info.get('user_name')
        channel_id = json_info.get('user_id')

        # Get the co-hosts/guests
        if uploader != '':
            guests = [uploader]
        else:
            guests = []

        guests_json = self._parse_json(json_info.get('guests_json'), video_id) or []
        for guest in guests_json:
            guest_name = guest.get('name')
            if guest_name is not None:
                guests.append(guest_name)

        # Get dates
        start_date = parse_iso8601(json_info.get('start_date'))
        end_date = parse_iso8601(json_info.get('end_date'))

        # Parse the duration of the stream
        parsed_duration = None
        if start_date is not None and end_date is not None:
            parsed_duration = (end_date - start_date)

        return {
            'id': video_id,
            'title': broadcast_title or self._og_search_title(webpage),
            'display_id': display_id,
            'url': url,
            'timestamp': start_date,
            'uploader': uploader,
            'channel_id': channel_id,
            'duration': parsed_duration,
            'cast': guests,
            'description': broadcast_description,
            'categories': [broadcast_category],
            'tags': broadcast_tags
        }
