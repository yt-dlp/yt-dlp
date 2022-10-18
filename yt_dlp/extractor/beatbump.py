import re

from yt_dlp.utils import ExtractorError
from .common import InfoExtractor


class BeatBumpIE(InfoExtractor):
    _VALID_URL = r'https:\/\/beatbump\.ml\/(?:(?:listen\?id=)|(?:playlist\/)|(?:artist\/))(?P<id>.*)'
    _TESTS = [{
        'url': 'https://beatbump.ml/listen?id=BciS5krYL80',
        'md5': '7f6c65ee0955228bcbb81066080fb46c',
        'info_dict': {
            'id': 'BciS5krYL80',
            'ext': 'mp4',
            'title': 'Hotel California (2013 Remaster)',
            'thumbnail': 'https://i.ytimg.com/vi_webp/BciS5krYL80/maxresdefault.webp',
            'artist': 'Eagles',
            'track': 'Hotel California (2013 Remaster)',
            'channel_follower_count': int,
            'channel_url': 'https://www.youtube.com/channel/UC49r4GNHHpc-eQ9hmD2Rg6A',
            'uploader': 'The Eagles - Topic',
            'alt_title': 'Hotel California (2013 Remaster)',
            'categories': ['Music'],
            'like_count': int,
            'view_count': int,
            'uploader_id': 'UC49r4GNHHpc-eQ9hmD2Rg6A',
            'tags': ['Eagles', 'Legacy', 'Hotel California'],
            'upload_date': '20181101',
            'release_year': 1976,
            'duration': 391,
            'channel_id': 'UC49r4GNHHpc-eQ9hmD2Rg6A',
            'creator': 'Eagles',
            'description': 'md5:1846212e0e373e0970f844516a9ced39',
            'playable_in_embed': True,
            'uploader_url': 'http://www.youtube.com/channel/UC49r4GNHHpc-eQ9hmD2Rg6A',
            'album': 'Legacy',
            'age_limit': 0,
            'channel': 'Eagles',
            'availability': 'public',
        }
    }, {
        'url': 'https://beatbump.ml/artist/UCfSIVkF2grhFG80NnJQAiwQ',
        'playlist_count': 1,
        'info_dict': {
            'id': 'UCfSIVkF2grhFG80NnJQAiwQ',
            'title': 'Sufi Sounds - Topic - Home',
            'uploader_id': 'UCfSIVkF2grhFG80NnJQAiwQ',
            'uploader_url': 'https://www.youtube.com/channel/UCfSIVkF2grhFG80NnJQAiwQ',
            'uploader': 'Sufi Sounds - Topic',
            'channel_url': 'https://www.youtube.com/channel/UCfSIVkF2grhFG80NnJQAiwQ',
            'channel_follower_count': int,
            'channel': 'Sufi Sounds - Topic',
            'channel_id': 'UCfSIVkF2grhFG80NnJQAiwQ',
            'tags': [],
            'description': '',
        },
    }, {
        'url': 'https://beatbump.ml/playlist/VLPL79MVRBRzH7weNKRSAVNwzCjZZThfBtEt',
        'playlist_count': 7,
        'info_dict': {
            'id': 'PL79MVRBRzH7weNKRSAVNwzCjZZThfBtEt',
            'title': 'aga',
            'description': '',
            'channel': 'Rachid Be',
            'channel_id': 'UCUNlZMee_MAxsYkh92HqvvQ',
            'channel_url': 'https://www.youtube.com/channel/UCUNlZMee_MAxsYkh92HqvvQ',
            'uploader': 'Rachid Be',
            'uploader_id': 'UCUNlZMee_MAxsYkh92HqvvQ',
            'uploader_url': 'https://www.youtube.com/channel/UCUNlZMee_MAxsYkh92HqvvQ',
            'availability': 'public',
            'modified_date': str,
            'tags': [],
            'view_count': int
        }
    }]

    def _real_extract(self, url):
        item_id = self._match_id(url)

        if re.search('listen', url) is not None:
            # Single video id
            return self.url_result(f'https://youtube.com/watch?v={item_id}', ie='Youtube')
        elif re.search('playlist', url) is not None:
            # Playlist id
            return self.url_result(f'https://music.youtube.com/browse/{item_id}')
        elif re.search('artist', url):
            # Artist id
            return self.url_result(f'https://youtube.com/channel/{item_id}')
        else:
            raise ExtractorError('Not a supported beatbump.ml url', expected=True)
