from .common import InfoExtractor
import json
import re
from yt_dlp import traverse_obj
from ..utils import ExtractorError


class NinaprotocolIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ninaprotocol\.com/releases/(?P<id>(.*)+)'
    _TESTS = [{
        'url': 'https://www.ninaprotocol.com/releases/3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ',
        'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ',
        'info_dict': {
            'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ',
            'title': 'The Spatulas - March Chant',
            'tags': ['punk', 'postpresentmedium', 'cambridge'],
            'thumbnail': str,
            'description': str,
            'type': 'audio'
        },
        'playlist': [
            {
                'info_dict': {
                    'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_1',
                    'title': 'March Chant In April',
                    'track': 'March Chant In April',
                    'ext': 'mp3',
                    'duration': 152,
                    'track_number': 1,
                    'type': 'audio'
                }
            },
            {
                'info_dict': {
                    'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_2',
                    'title': 'Rescue Mission',
                    'track': 'Rescue Mission',
                    'ext': 'mp3',
                    'duration': 212,
                    'track_number': 2,
                    'type': 'audio',
                }
            },
            {
                'info_dict': {
                    'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_3',
                    'title': 'Slinger Style',
                    'track': 'Slinger Style',
                    'ext': 'mp3',
                    'duration': 179,
                    'track_number': 3,
                    'type': 'audio',
                }
            },

            {
                'info_dict': {
                    'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_4',
                    'title': 'Psychic Signal',
                    'track': 'Psychic Signal',
                    'ext': 'mp3',
                    'duration': 220,
                    'track_number': 4,
                    'type': 'audio',
                }
            },
            {
                'info_dict': {
                    'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_5',
                    'title': 'Curvy Color',
                    'track': 'Curvy Color',
                    'ext': 'mp3',
                    'duration': 148,
                    'track_number': 5,
                    'type': 'audio',
                }
            },
            {
                'info_dict': {
                    'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_6',
                    'title': 'Caveman Star',
                    'track': 'Caveman Star',
                    'ext': 'mp3',
                    'duration': 121,
                    'track_number': 6,
                    'type': 'audio',
                },
            }
        ],
    }, {
            'url': 'https://www.ninaprotocol.com/releases/f-g-s-american-shield',
            'id': 'f-g-s-american-shield',
            'md5': 'f8934f550f6f4db527a50fa47275dc4e',
            'info_dict': {
                'id': 'f-g-s-american-shield_1',
                'ext': 'mp3',
                'title': 'F.G.S. - American Shield',
                'track': 'F.G.S. - American Shield',
                'type': 'audio',
                'duration': 201,
                'track_number': int
            }
        }, {
            'url': 'https://www.ninaprotocol.com/releases/9Uw8FYtc9mbahX7YEWD27NNXxyYUJ9gwZrEoWrMzSw9z',
            'id': '9Uw8FYtc9mbahX7YEWD27NNXxyYUJ9gwZrEoWrMzSw9z',
            'md5': 'fa5d72b8cbb031a01c3ff0262e388967',
            'info_dict': {
                'id': '9Uw8FYtc9mbahX7YEWD27NNXxyYUJ9gwZrEoWrMzSw9z_1',
                'ext': 'mp3',
                'title': 'Pluck',
                'track': 'Pluck',
                'type': 'audio',
                'track_number': int
            }
        }]

    def _get_balanced_brackets_substring(self, text, index=0):
        subtext = text[index:]
        index_of_brackets = [m.start() for m in re.finditer(r'[\[\]{}()]', subtext)]
        stack = [index_of_brackets[0]]
        for i in range(1, len(index_of_brackets)):
            if subtext[index_of_brackets[i]] in r'({[':
                stack.append(index_of_brackets[i])
            else:
                stack.pop()
                if len(stack) == 0:
                    return subtext[:index_of_brackets[i] + 1]
        if stack:
            raise ValueError("Unbalanced brackets: Opening bracket without a corresponding closing bracket.")

    def _search_all_releases(self, webpage, release_name):
        scripts = ''.join(re.findall(r'(?i)<\s*script\s*>(.*?)<\s*/\s*script\s*>', webpage))
        scripts = scripts.encode('utf-8').decode('unicode_escape')

        for m in re.finditer(r'"release":([\[{])', scripts):
            s_json = self._get_balanced_brackets_substring(scripts, m.start(1))
            try:
                release = json.loads(s_json)
            except json.JSONDecodeError:
                return None

            if traverse_obj(release, ('metadata', 'name')) in release_name:
                return release

        return None

    def _get_json_with_api(self, video_id):
        api_url = 'https://api.ninaprotocol.com/v1/releases/' + video_id
        json_string = self._download_webpage(api_url, video_id)
        json_video_data = self._parse_json(json_string, video_id)
        return json_video_data.get('release', None)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        release_name = (self._html_search_meta('og:title', webpage) or
                        self._html_extract_title(webpage))

        release = self._get_json_with_api(video_id)

        if release is None:
            # getting song data from internal workings of a Next.js
            release = self._search_all_releases(webpage, release_name)

        if release is None:
            raise ExtractorError('No song metadata found.')

        files = traverse_obj(release, ('metadata', 'properties', 'files'))
        ext = traverse_obj(release, ('metadata', 'animation_url')).split('?ext=')[-1]

        entries = []
        for n, track in enumerate(files):
            entry = {}
            entry['id'] = video_id + '_' + str(n + 1)
            entry['title'] = track['track_title']
            entry['url'] = track['uri']
            entry['ext'] = ext
            entry['track_number'] = track.get('track')
            entry['track'] = track.get('track_title')
            entry['type'] = traverse_obj(release, ('metadata', 'properties', 'category'))
            if 'artist' in track:
                entry['artist'] = track.get('artist')
            if 'duration' in track:
                entry['duration'] = track.get('duration')
            entries.append(entry)

        return {
            'id': video_id,
            'title': traverse_obj(release, ('metadata', 'name')),
            'description': traverse_obj(release, ('metadata', 'description')),
            'thumbnail': traverse_obj(release, ('metadata', 'image')),
            'tags': traverse_obj(release, ('metadata', 'properties', 'tags')),
            '_type': 'playlist',
            'ext': ext,
            'type': traverse_obj(release, ('metadata', 'properties', 'category')),
            'entries': entries,
        }
