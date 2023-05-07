from datetime import datetime
import re

from yt_dlp.utils import ExtractorError, determine_ext, extract_attributes, get_element_by_class, unified_strdate
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

        # the h3 is acutally empty when downloaded by youtube-dl
        # playlist_title = get_element_by_class('sr_it-playlist-title', webpage)
        playlist_title = None

        entries = []

        for track in re.findall(
                r'(<li[^>][^>]+>)',
                playlist):
            attr = extract_attributes(track)
            tracktitle = attr['data-tracktitle']
            trackurl = attr['data-audiopath']

            if playlist_title is None:
                playlist_title = attr['data-albumtitle']

            id = self._search_regex(self._ENTRY_URL, trackurl, 'trackurl id')

            # full_response = self._request_webpage(trackurl, id, headers={
            #     'Accept-Encoding': 'identity',
            # })
            # content_type = full_response.headers.get('Content-Type', '').lower()

            upload_date = datetime.strptime(attr['data-releasedate'], '%Y.%m.%d Release')

            entry = {
                'id': id,
                'title': tracktitle,
                'url': trackurl,
                'ext': determine_ext(trackurl),
                'thumbnail': attr['data-albumart'],
                'upload_date': unified_strdate(upload_date.strftime('%Y%m%d'))
            }

            # if re.match(r'audio/', content_type):
            #     entry['vcodec'] = 'none'
            if entry['ext'] == 'mp3':
                entry['vcodec'] = 'none'
                entry['acodec'] = 'mp3'

            entries.append(entry)

        return self.playlist_result(entries, playlist_id, playlist_title)
