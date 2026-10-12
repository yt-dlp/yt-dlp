import urllib.parse

from .common import InfoExtractor
from ..utils import extract_attributes, get_element_html_by_id, get_element_text_and_html_by_tag


class EscribeIE(InfoExtractor):
    _VALID_URL = r'https://[^.]+\.escribemeetings\.com/(?:Players/ISIStandAlonePlayer|Meeting)\.aspx'
    _TESTS = [
        {
            'url': 'https://pub-guelph.escribemeetings.com/Players/ISIStandAlonePlayer.aspx?Id=3ac80dd1-d45a-45e8-8be0-cfe526e5b829',
            'md5': '06748d4cccc36d12dbd967af92078ef8',
            'info_dict': {
                'id': '3ac80dd1-d45a-45e8-8be0-cfe526e5b829',
                'ext': 'mp4',
                'title': 'Council Planning - October 08, 2024',
                'url': 'https://video.isilive.ca/guelph/Council%20Encoder_CPM_2024-10-08-03-55.mp4',
                'uploader': 'guelph',
                'upload_date': '20241008',
            },
        },
        {
            'url': 'https://pub-guelph.escribemeetings.com/Players/ISIStandAlonePlayer.aspx?Id=4a0da857-5283-48ff-9675-6e41a6608b52',
            'md5': 'd498884762a777a503502871696bd985',
            'info_dict': {
                'id': '4a0da857-5283-48ff-9675-6e41a6608b52',
                'ext': 'mp4',
                'title': 'Council Planning - September 10, 2024',
                'url': 'https://video.isilive.ca/guelph/Council%20Encoder_CPM_2024-09-10-05-56.mp4',
                'uploader': 'guelph',
                'upload_date': '20240910',
            },
        },
        {
            'url': 'https://pub-guelph.escribemeetings.com/Players/ISIStandAlonePlayer.aspx?Id=99dad340-87ab-46cb-a53b-326b8e57b9af',
            'md5': '81e0de48da05e378c14584078c2dffa8',
            'info_dict': {
                'id': '99dad340-87ab-46cb-a53b-326b8e57b9af',
                'ext': 'mp4',
                'title': 'Committee of the Whole - November 05, 2024',
                'url': 'https://video.isilive.ca/guelph/Council%20Encoder_Committee%20of%20the%20Whole_2024-11-05-01-28.mp4',
                'uploader': 'guelph',
                'upload_date': '20241105',
            },
        },
        {
            'url': 'https://pub-guelph.escribemeetings.com/Meeting.aspx?Id=4fd7316d-12ae-4f06-90d7-7b5c9989a5bf&Agenda=PostMinutes&lang=English',
            'md5': '900f850c3a31dd7e1600c529dd5e82b7',
            'info_dict': {
                'id': '4fd7316d-12ae-4f06-90d7-7b5c9989a5bf',
                'ext': 'mp4',
                'title': 'Heritage Guelph - November 04, 2024',
                'url': 'https://video.isilive.ca/guelph/November%204%2C%202024%20-%20Heritage%20Guelph%20Meeting.mp4',
                'uploader': 'guelph',
                'upload_date': '20241104',
            },
        },
        {
            'url': 'https://pub-cutlerbay-fl.escribemeetings.com/Meeting.aspx?Id=8a38be89-e595-45d5-bda4-c4258704b494&Agenda=Agenda&lang=English',
            'md5': 'c8d644d7ceaf125858dc446343faa057',
            'info_dict': {
                'id': '8a38be89-e595-45d5-bda4-c4258704b494',
                'ext': 'mp4',
                'title': 'Town Council Zoning Workshop - With Virtual - June 13, 2024',
                'url': 'https://video.isilive.ca/cutlerbay/06-13-2024%20TCZW_Recording.mp4',
                'uploader': 'cutlerbay',
                'upload_date': '20240613',
            },
        },
    ]

    def _real_extract(self, url):
        query_args = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        video_id = query_args['Id'][0]

        # Potentially switch from the player page to the detailed meeting page.
        url = url.replace('/Players/ISIStandAlonePlayer.aspx', '/Meeting.aspx', 1)

        # Extract the element replaced by the JavaScript ISI player.
        html = self._download_webpage(url, video_id)
        player_target = get_element_html_by_id('isi_player', html)
        player_attrs = extract_attributes(player_target)

        file_name = player_attrs['data-stream_name']
        client_id = player_attrs['data-client_id']

        quoted_file_name = urllib.parse.quote(file_name)
        quoted_client_id = urllib.parse.quote(client_id)
        video_url = f'https://video.isilive.ca/{quoted_client_id}/{quoted_file_name}'

        title, _ = get_element_text_and_html_by_tag('title', html)
        title = title.strip()

        info = {
            'id': video_id,
            'url': video_url,
            'uploader': client_id,
            'title': title,
            'webpage_url': url,
        }

        # No point breaking if there's ever a file without an extension.
        if '.' in file_name:
            _, ext = file_name.rsplit('.', maxsplit=1)
            info['ext'] = ext

        # Use the date of the meeting as the upload date, which is not necessarily
        # the same but it's both what is available and likely desired by users.
        # Using regex as the parser seems to fail on this chunk of the HTML.
        meeting_date = self._html_search_regex(
            r'datetime=["\'](\d{4}-\d{2}-\d{2})', html, 'upload_date', fatal=False)
        if meeting_date is not None:
            info['upload_date'] = meeting_date.replace('-', '')

        return info
