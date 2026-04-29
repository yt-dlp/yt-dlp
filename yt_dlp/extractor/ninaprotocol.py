from .common import InfoExtractor
from ..utils import int_or_none, mimetype2ext, parse_iso8601, url_or_none
from ..utils.traversal import traverse_obj


class NinaProtocolIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ninaprotocol\.com/releases/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://www.ninaprotocol.com/releases/3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ',
        'info_dict': {
            'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ',
            'title': 'The Spatulas - March Chant',
            'tags': ['punk', 'postpresentmedium', 'cambridge'],
            'uploader_id': '2bGjgdKUddJoj2shYGqfNcUfoSoABP21RJoiwGMZDq3A',
            'channel': 'ppm',
            'description': 'md5:bb9f9d39d8f786449cd5d0ff7c5772db',
            'album': 'The Spatulas - March Chant',
            'thumbnail': 'https://www.arweave.net/VyZA6CBeUuqP174khvSrD44Eosi3MLVyWN42uaQKg50',
            'timestamp': 1701417610,
            'uploader': 'ppmrecs',
            'channel_id': '4ceG4zsb7VVxBTGPtZMqDZWGHo3VUg2xRvzC2b17ymWP',
            'display_id': 'the-spatulas-march-chant',
            'upload_date': '20231201',
            'album_artist': 'Post Present Medium ',
        },
        'playlist': [{
            'info_dict': {
                'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_1',
                'title': 'March Chant In April',
                'track': 'March Chant In April',
                'ext': 'mp3',
                'duration': 152,
                'track_number': 1,
                'uploader_id': '2bGjgdKUddJoj2shYGqfNcUfoSoABP21RJoiwGMZDq3A',
                'uploader': 'ppmrecs',
                'thumbnail': 'https://www.arweave.net/VyZA6CBeUuqP174khvSrD44Eosi3MLVyWN42uaQKg50',
                'timestamp': 1701417610,
                'channel': 'ppm',
                'album': 'The Spatulas - March Chant',
                'tags': ['punk', 'postpresentmedium', 'cambridge'],
                'channel_id': '4ceG4zsb7VVxBTGPtZMqDZWGHo3VUg2xRvzC2b17ymWP',
                'upload_date': '20231201',
                'album_artist': 'Post Present Medium ',
            },
        }, {
            'info_dict': {
                'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_2',
                'title': 'Rescue Mission',
                'track': 'Rescue Mission',
                'ext': 'mp3',
                'duration': 212,
                'track_number': 2,
                'album_artist': 'Post Present Medium ',
                'uploader': 'ppmrecs',
                'tags': ['punk', 'postpresentmedium', 'cambridge'],
                'thumbnail': 'https://www.arweave.net/VyZA6CBeUuqP174khvSrD44Eosi3MLVyWN42uaQKg50',
                'channel': 'ppm',
                'upload_date': '20231201',
                'channel_id': '4ceG4zsb7VVxBTGPtZMqDZWGHo3VUg2xRvzC2b17ymWP',
                'timestamp': 1701417610,
                'album': 'The Spatulas - March Chant',
                'uploader_id': '2bGjgdKUddJoj2shYGqfNcUfoSoABP21RJoiwGMZDq3A',
            },
        }, {
            'info_dict': {
                'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_3',
                'title': 'Slinger Style',
                'track': 'Slinger Style',
                'ext': 'mp3',
                'duration': 179,
                'track_number': 3,
                'timestamp': 1701417610,
                'upload_date': '20231201',
                'channel_id': '4ceG4zsb7VVxBTGPtZMqDZWGHo3VUg2xRvzC2b17ymWP',
                'uploader_id': '2bGjgdKUddJoj2shYGqfNcUfoSoABP21RJoiwGMZDq3A',
                'thumbnail': 'https://www.arweave.net/VyZA6CBeUuqP174khvSrD44Eosi3MLVyWN42uaQKg50',
                'album_artist': 'Post Present Medium ',
                'album': 'The Spatulas - March Chant',
                'tags': ['punk', 'postpresentmedium', 'cambridge'],
                'uploader': 'ppmrecs',
                'channel': 'ppm',
            },
        }, {
            'info_dict': {
                'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_4',
                'title': 'Psychic Signal',
                'track': 'Psychic Signal',
                'ext': 'mp3',
                'duration': 220,
                'track_number': 4,
                'tags': ['punk', 'postpresentmedium', 'cambridge'],
                'upload_date': '20231201',
                'album': 'The Spatulas - March Chant',
                'thumbnail': 'https://www.arweave.net/VyZA6CBeUuqP174khvSrD44Eosi3MLVyWN42uaQKg50',
                'timestamp': 1701417610,
                'album_artist': 'Post Present Medium ',
                'channel_id': '4ceG4zsb7VVxBTGPtZMqDZWGHo3VUg2xRvzC2b17ymWP',
                'channel': 'ppm',
                'uploader_id': '2bGjgdKUddJoj2shYGqfNcUfoSoABP21RJoiwGMZDq3A',
                'uploader': 'ppmrecs',
            },
        }, {
            'info_dict': {
                'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_5',
                'title': 'Curvy Color',
                'track': 'Curvy Color',
                'ext': 'mp3',
                'duration': 148,
                'track_number': 5,
                'timestamp': 1701417610,
                'uploader_id': '2bGjgdKUddJoj2shYGqfNcUfoSoABP21RJoiwGMZDq3A',
                'thumbnail': 'https://www.arweave.net/VyZA6CBeUuqP174khvSrD44Eosi3MLVyWN42uaQKg50',
                'album': 'The Spatulas - March Chant',
                'album_artist': 'Post Present Medium ',
                'channel': 'ppm',
                'tags': ['punk', 'postpresentmedium', 'cambridge'],
                'uploader': 'ppmrecs',
                'channel_id': '4ceG4zsb7VVxBTGPtZMqDZWGHo3VUg2xRvzC2b17ymWP',
                'upload_date': '20231201',
            },
        }, {
            'info_dict': {
                'id': '3SvsMM3y4oTPZ5DXFJnLkCAqkxz34hjzFxqms1vu9XBJ_6',
                'title': 'Caveman Star',
                'track': 'Caveman Star',
                'ext': 'mp3',
                'duration': 121,
                'track_number': 6,
                'channel_id': '4ceG4zsb7VVxBTGPtZMqDZWGHo3VUg2xRvzC2b17ymWP',
                'thumbnail': 'https://www.arweave.net/VyZA6CBeUuqP174khvSrD44Eosi3MLVyWN42uaQKg50',
                'tags': ['punk', 'postpresentmedium', 'cambridge'],
                'album_artist': 'Post Present Medium ',
                'uploader': 'ppmrecs',
                'timestamp': 1701417610,
                'uploader_id': '2bGjgdKUddJoj2shYGqfNcUfoSoABP21RJoiwGMZDq3A',
                'album': 'The Spatulas - March Chant',
                'channel': 'ppm',
                'upload_date': '20231201',
            },
        }],
    }, {
        'url': 'https://www.ninaprotocol.com/releases/f-g-s-american-shield',
        'info_dict': {
            'id': '76PZnJwaMgViQHYfA4NYJXds7CmW6vHQKAtQUxGene6J',
            'description': 'md5:63f08d5db558b4b36e1896f317062721',
            'title': 'F.G.S. - American Shield',
            'uploader_id': 'Ej3rozs11wYqFk1Gs6oggGCkGLz8GzBhmJfnUxf6gPci',
            'channel_id': '6JuksCZPXuP16wJ1BUfwuukJzh42C7guhLrFPPkVJfyE',
            'channel': 'tinkscough',
            'tags': [],
            'album_artist': 'F.G.S.',
            'album': 'F.G.S. - American Shield',
            'thumbnail': 'https://www.arweave.net/YJpgImkXLT9SbpFb576KuZ5pm6bdvs452LMs3Rx6lm8',
            'display_id': 'f-g-s-american-shield',
            'uploader': 'flannerysilva',
            'timestamp': 1702395858,
            'upload_date': '20231212',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.ninaprotocol.com/releases/time-to-figure-things-out',
        'info_dict': {
            'id': '6Zi1nC5hj6b13NkpxVYwRhFy6mYA7oLBbe9DMrgGDcYh',
            'display_id': 'time-to-figure-things-out',
            'description': 'md5:960202ed01c3134bb8958f1008527e35',
            'timestamp': 1706283607,
            'title': 'DJ STEPDAD - time to figure things out',
            'album_artist': 'DJ STEPDAD',
            'uploader': 'tddvsss',
            'upload_date': '20240126',
            'album': 'time to figure things out',
            'uploader_id': 'AXQNRgTyYsySyAMFDwxzumuGjfmoXshorCesjpquwCBi',
            'thumbnail': 'https://www.arweave.net/O4i8bcKVqJVZvNeHHFp6r8knpFGh9ZwEgbeYacr4nss',
            'tags': [],
        },
        'playlist_count': 4,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        release = self._download_json(
            f'https://api.ninaprotocol.com/v1/releases/{video_id}', video_id)['release']

        video_id = release.get('publicKey') or video_id

        common_info = traverse_obj(release, {
            'album': ('metadata', 'properties', 'title', {str}),
            'album_artist': ((('hub', 'data'), 'publisherAccount'), 'displayName', {str}),
            'timestamp': ('datetime', {parse_iso8601}),
            'thumbnail': ('metadata', 'image', {url_or_none}),
            'uploader': ('publisherAccount', 'handle', {str}),
            'uploader_id': ('publisherAccount', 'publicKey', {str}),
            'channel': ('hub', 'handle', {str}),
            'channel_id': ('hub', 'publicKey', {str}),
        }, get_all=False)
        common_info['tags'] = traverse_obj(release, ('metadata', 'properties', 'tags', ..., {str}))

        entries = []
        for track_num, track in enumerate(traverse_obj(release, (
                'metadata', 'properties', 'files', lambda _, v: url_or_none(v['uri']))), 1):
            entries.append({
                'id': f'{video_id}_{track_num}',
                'url': track['uri'],
                **traverse_obj(track, {
                    'title': ('track_title', {str}),
                    'track': ('track_title', {str}),
                    'ext': ('type', {mimetype2ext}),
                    'track_number': ('track', {int_or_none}),
                    'duration': ('duration', {int_or_none}),
                }),
                'vcodec': 'none',
                **common_info,
            })

        return {
            '_type': 'playlist',
            'id': video_id,
            'entries': entries,
            **traverse_obj(release, {
                'display_id': ('slug', {str}),
                'title': ('metadata', 'name', {str}),
                'description': ('metadata', 'description', {str}),
            }),
            **common_info,
        }
