from .common import InfoExtractor 


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
        json = self._html_search_regex(r'<script id=\"__NEXT_DATA__\"[^>]*>(.*)</script>', webpage, 'json_info')

        # Get the broadcast URL and the recording hash.
        # The full URL is {broadcast_url}/{recording_hash}.mp3
        broadcast_url = self._html_search_regex(r'(?<=broadcast_url\")(?:\s*\:\s*)(\".*?(?=\")\")', json, 'broadcast_url').replace('"', '')
        recording_hash = self._html_search_regex(r'(?<=recording_hash\")(?:\s*\:\s*)(\".*?(?=\")\")', json, 'recording_hash').replace('"', '')
        url = broadcast_url+recording_hash+".mp3"

        # Get broadcast date
        upload_date = self._html_search_regex(r'(?<=start_date\")(?:\s*\:\s*)(\".*?(?=\")\")', json, 'upload_date').replace('"', '').split('T')[0].replace('-', '')
        
        # Get broadcast title
        title = self._html_search_regex(r'(?<=broadcast_title\")(?:\s*\:\s*)(\".*?(?=\")\")', json, 'title').replace('"', '')

        # Get author (AKA show host)
        uploader = self._html_search_regex(r'(?<=user_name\")(?:\s*\:\s*)(\".*?(?=\")\")', json, 'uploader').replace('"', '')

        return {
            'id': video_id,
            'title': title,
            'upload_date': upload_date,
            'uploader': uploader,
            'url': url
        }
