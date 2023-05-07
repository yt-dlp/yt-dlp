import re

from yt_dlp.utils import ExtractorError, determine_ext, extract_attributes, get_element_by_class, parse_duration, traverse_obj, url_or_none
from .common import InfoExtractor


class NekoHackerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nekohacker\.com/(?P<id>(?!free-dl)[\w-]+)'
    _ENTRY_URL = r'https?://(?:www\.)?nekohacker\.com/wp-content/uploads/\d+/\d+/(?P<id>(?:\d+-)?[a-zA-Z0-9_-]+)\.[a-zA-Z0-9]+'
    _TESTS = [{
        'url': 'https://nekohacker.com/nekoverse/',
        'info_dict': {
            'id': 'nekoverse',
            'title': 'Nekoverse',
        },
        'playlist': [
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2022/11/01-Spaceship.mp3',
                'md5': '44223701ebedba0467ebda4cc07fb3aa',
                'info_dict': {
                    'id': '01-Spaceship',
                    'ext': 'mp3',
                    'title': 'Spaceship',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2022/11/Nekoverse_Artwork-1024x1024.jpg',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'upload_date': '20221101'
                }
            },
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2022/11/02-City-Runner.mp3',
                'md5': '8f853c71719389d32bbbd3f1a87b3f08',
                'info_dict': {
                    'id': '02-City-Runner',
                    'ext': 'mp3',
                    'title': 'City Runner',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2022/11/Nekoverse_Artwork-1024x1024.jpg',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'upload_date': '20221101'
                }
            },
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2022/11/03-Nature-Talk.mp3',
                'md5': '5a8a8ae852720cee4c0ac95c7d1a7450',
                'info_dict': {
                    'id': '03-Nature-Talk',
                    'ext': 'mp3',
                    'title': 'Nature Talk',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2022/11/Nekoverse_Artwork-1024x1024.jpg',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'upload_date': '20221101'
                }
            },
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2022/11/04-Crystal-World.mp3',
                'md5': 'd8e59a48061764e50d92386a294abd50',
                'info_dict': {
                    'id': '04-Crystal-World',
                    'ext': 'mp3',
                    'title': 'Crystal World',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2022/11/Nekoverse_Artwork-1024x1024.jpg',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'upload_date': '20221101'
                }
            }
        ]
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)
        playlist = get_element_by_class('playlist', webpage)

        if playlist is None:
            raise ExtractorError('no playlist element found - likely not a album', expected=True)

        entries = []
        for track_number, track in enumerate(re.findall(r'(<li[^>]+data-audiopath[^>]+>)', playlist), 1):
            entry = traverse_obj(extract_attributes(track), {
                'url': ('data-audiopath', {url_or_none}),
                'ext': ('data-audiopath', {determine_ext}),
                'id': 'data-trackid',
                'title': 'data-tracktitle',
                'track': 'data-tracktitle',
                'album': 'data-albumtitle',
                'duration': ('data-tracktime', {parse_duration}),
                'release_date': ('data-releasedate', {lambda x: re.match(r'\d{8}', x.replace('.', ''))}, 0),
                'thumbnail': ('data-albumart', {url_or_none}),
            })
            entry['track_number'] = track_number
            entry['artist'] = 'Nekohacker'
            entry['vcodec'] = 'none'
            entry['acodec'] = 'mp3' if entry['ext'] == 'mp3' else None
            entries.append(entry)

        return self.playlist_result(entries, playlist_id, traverse_obj(entries, (0, 'album')))
