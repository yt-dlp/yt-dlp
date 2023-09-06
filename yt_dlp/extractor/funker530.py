from .common import InfoExtractor
from .generic import GenericIE
from .youtube import YoutubeIE
from ..utils import ExtractorError, clean_html, get_element_by_class, strip_or_none
import re


def extract_video_id(response):
    # Define a regular expression pattern to match "Rumble" followed by parentheses and content inside them.
    pattern = r'Rumble\s*\((.*?)\)'

    # Use re.search() to find the first occurrence of the pattern in the response.
    match = re.search(pattern, response)

    # Check if a match is found.
    if match:
        # Extract the content inside parentheses using group(1).
        content_inside_parentheses = match.group(1)

        # Use another regular expression to extract the video ID.
        video_id_match = re.search(r'video:\s*"([^"]+)"', content_inside_parentheses)

        if video_id_match:
            # Extract the video ID using group(1).
            video_id = video_id_match.group(1)
            return video_id
    return None  # Return None if "Rumble" followed by parentheses or video ID is not found.


def url_clean(self, display_id, video_id):
    url = f"https://rumble.com/embedJS/{video_id}"

    webpage = self._download_webpage(url, display_id)

    # Extract the link after "url" from the response using regex.
    link_match = re.search(r'"url":"(.*?)",', webpage)

    if link_match:
        link = link_match.group(1)

        # Remove all "\" symbols from the link.
        cleaned_link = link.replace('/', '')
        cleaned_link = cleaned_link.replace('\\', '/')
        return cleaned_link


class Funker530IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?funker530\.com/video/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://funker530.com/video/azov-patrol-caught-in-open-under-automatic-grenade-launcher-fire/',
        'md5': 'fcb1880a5703f5c17e9191bab27fb822',
        'info_dict': {
            'id': 'c1Mgk.caa',
            'ext': 'mp4',
            'title': 'c1Mgk.caa',
            'upload_date': '20230608',
            'timestamp': 1686241352.0,
            'direct': True
        }
    }]

    def _real_extract(self, url):
        info = {}
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_id = extract_video_id(webpage)
        cleaned_link = url_clean(self, display_id, video_id)
        rumble_url = cleaned_link

        youtube_url = list(YoutubeIE._extract_embed_urls(url, webpage))

        if rumble_url:
            info = {
                'url': rumble_url,
                'info_dict': {
                    'ext': 'mp4',
                    'direct': True
                },

                'ie_key': GenericIE.ie_key()
            }
        elif youtube_url:
            info = {'url': youtube_url[0], 'ie_key': YoutubeIE.ie_key()}
        if info == {}:
            raise ExtractorError('No videos found on webpage', expected=True)

        return {
            **info,
            '_type': 'url',
            'description': strip_or_none(self._search_regex(
                r'(?s)(.+)About the Author', clean_html(get_element_by_class('video-desc-paragraph', webpage)),
                'description', default=None)),


        }
