import re

from .common import InfoExtractor
from .kick import KickVODIE
from .lbry import LBRYIE
from .rumble import RumbleIE
from .youtube import YoutubeIE
from ..utils import ExtractorError


class VyneerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vyneer\.me/vods/\?'
    _TESTS = [{
        'url': 'https://vyneer.me/vods/?v=6lf3maUT9dE&start=2024-07-16T21:53:29Z&end=2024-07-16T22:06:39Z',
        'info_dict': {
            'id': '6lf3maUT9dE',
            'ext': 'mp4',
            'title': 'Is Twitter 90% bots???? | Creating an Insurrection Video',
            'upload_date': '20240716',
            'uploader_id': '@destiny',
            'uploader': 'Destiny',
            'duration': 788,
            'playable_in_embed': True,
            'channel_id': 'UC554eY5jNUfDq3yDOJYirOQ',
            'categories': ['Entertainment'],
            'release_timestamp': 1721166809,
            'timestamp': 1721092786,
            'description': 'md5:e91a9cede093ed65e4be98fe8aeed0be',
            'thumbnail': 'https://i.ytimg.com/vi/6lf3maUT9dE/maxresdefault.jpg',
            'view_count': int,
            'channel_follower_count': int,
            'channel_url': 'https://www.youtube.com/channel/UC554eY5jNUfDq3yDOJYirOQ',
            'channel': 'Destiny',
            'uploader_url': 'https://www.youtube.com/@destiny',
            'release_date': '20240716',
            'tags': ['destiny', 'debates', 'biden', 'trump'],
            'live_status': 'was_live',
            'channel_is_verified': True,
            'like_count': int,
            'availability': 'unlisted',
            'age_limit': 0,
        },
    },
        {
        'url': 'https://vyneer.me/vods/?r=v554vlh&start=2024-07-18T19:06:53Z&end=2024-07-19T01:14:49Z',
        'info_dict': {
            'id': 'v554vlh',
            'title': '[Mirror] Destiny YouTube Stream',
            'ext': 'mp4',
            'duration': 22076,
            'description': 'My own archive of Destiny streams',
            'thumbnail': 'https://hugh.cdn.rumble.cloud/s/s8/1/1/Q/m/X/1QmXs.qR4e-small-Mirror-Destiny-YouTube-Stre.jpg',
            'channel_url': 'https://rumble.com/c/OmniMirror',
            'uploader': 'OmniMirror',
            'like_count': int,
            'release_date': '20240718',
            'dislike_count': int,
            'channel': 'OmniMirror',
            'live_status': 'was_live',
            'timestamp': 1721330391,
            'release_timestamp': 1721329613,
            'view_count': int,
            'upload_date': '20240718',
        },
    },
        {
        'skip': 'No Kick VODs on vyneer.me at present, also Kick extractor doesn\'t work',
        'url': 'https://vyneer.me/vods/?k=',
        'only_matching': True,
    },
        {
        # Note, no Odysee VODs are on vyneer.me at present, but the linked channel does have videos, so I'm aassuming this is what the URL would look like. 'od=' is correct as found in: https://github.com/vyneer/orvods-go/blob/main/templates/index.html
        'url': 'https://vyneer.me/vods/?od=0nHUYOBlKsg-r-youtube361:4',
        'info_dict': {
            'id': '4ddddeeb018b1e11ab54c9ae210d6044447e1139',
            'title': '[youtube:0nHUYOBlKsg] Researching for an anti-Trump manifesto',
            'ext': 'mp4',
            'channel_id': '777097516b312ee377e1cc63e2d3aa4097d0e63d',
            'release_timestamp': 1721465042,
            'channel_url': 'https://odysee.com/@odysteve:777097516b312ee377e1cc63e2d3aa4097d0e63d',
            'upload_date': '20240720',
            'uploader_id': '@odysteve',
            'release_date': '20240720',
            'tags': ['destiny', 'vod', 'yee wins', 'reupload', 'mirror'],
            'timestamp': 1721466514,
            'description': '2024-07-19T20:10:57Z\n2024-07-20T06:50:40Z',
            'thumbnail': 'https://thumbs.odycdn.com/71d4cf59e2409bd2e329d3de0f6e9e66.webp',
            'duration': 38383,
            'license': 'None',
        },
    }]

    def _real_extract(self, url):
        if re.match(r'https?://(?:www\.)?vyneer\.me/vods/\?v', url):
            video_id = re.search(r'https?://(?:www\.)?vyneer\.me/vods/\?v=([^&]*)', url).group(1)
            youtube_url = 'https://www.youtube.com/watch?v=' + video_id
            return self.url_result(youtube_url, YoutubeIE.ie_key())

        elif re.match(r'https?://(?:www\.)?vyneer\.me/vods/\?r', url):
            video_id = re.search(r'https?://(?:www\.)?vyneer\.me/vods/\?r=([^&]*)', url).group(1)
            rumble_url = 'https://rumble.com/' + video_id
            return self.url_result(rumble_url, RumbleIE.ie_key())

        elif re.match(r'https?://(?:www\.)?vyneer\.me/vods/\?k', url):
            video_id = re.search(r'https?://(?:www\.)?vyneer\.me/vods/\?k=([^&]*)', url).group(1)
            kick_url = 'https://kick.com/video/' + video_id
            return self.url_result(kick_url, KickVODIE.ie_key())

        elif re.match(r'https?://(?:www\.)?vyneer\.me/vods/\?od', url):
            video_id = re.search(r'https?://(?:www\.)?vyneer\.me/vods/\?od=([^&]*)', url).group(1)
            odysee_url = 'https://odysee.com/@odysteve:7/' + video_id
            return self.url_result(odysee_url, LBRYIE.ie_key())

        raise ExtractorError('Unsupported vyneer.me URL')
