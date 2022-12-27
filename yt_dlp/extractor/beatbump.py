from .common import InfoExtractor
from .youtube import YoutubeIE, YoutubeTabIE


class BeatBumpVideoIE(InfoExtractor):
    _VALID_URL = r'https://beatbump\.ml/listen\?id=(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://beatbump.ml/listen?id=MgNrAu2pzNs',
        'md5': '5ff3fff41d3935b9810a9731e485fe66',
        'info_dict': {
            'id': 'MgNrAu2pzNs',
            'ext': 'mp4',
            'title': 'Voyeur Girl',
            'description': 'md5:7ae382a65843d6df2685993e90a8628f',
            'upload_date': '20190312',
            'uploader': 'Stephen - Topic',
            'uploader_id': 'UC-pWHpBjdGG69N9mM2auIAA',
            'artist': 'Stephen',
            'track': 'Voyeur Girl',
            'album': 'it\'s too much love to know my dear',
            'alt_title': 'Voyeur Girl',
            'view_count': int,
            'uploader_url': 'http://www.youtube.com/channel/UC-pWHpBjdGG69N9mM2auIAA',
            'playable_in_embed': True,
            'like_count': int,
            'categories': ['Music'],
            'channel_url': 'https://www.youtube.com/channel/UC-pWHpBjdGG69N9mM2auIAA',
            'channel': 'Stephen',
            'availability': 'public',
            'creator': 'Stephen',
            'duration': 169,
            'thumbnail': 'https://i.ytimg.com/vi_webp/MgNrAu2pzNs/maxresdefault.webp',
            'age_limit': 0,
            'channel_id': 'UC-pWHpBjdGG69N9mM2auIAA',
            'tags': 'count:11',
            'live_status': 'not_live',
            'channel_follower_count': int,
            'comment_count': int,
        }
    }]

    def _real_extract(self, url):
        id_ = self._match_id(url)
        return self.url_result(f'https://music.youtube.com/watch?v={id_}', YoutubeIE, id_)


class BeatBumpPlaylistIE(InfoExtractor):
    _VALID_URL = r'https://beatbump\.ml/(?:release\?id=|artist/|playlist/)(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://beatbump.ml/release?id=MPREb_gTAcphH99wE',
        'playlist_count': 50,
        'info_dict': {
            'id': 'OLAK5uy_l1m0thk3g31NmIIz_vMIbWtyv7eZixlH0',
            'title': 'Album - Royalty Free Music Library V2 (50 Songs)',
            'description': '',
            'webpage_url': 'https://music.youtube.com/playlist?list=OLAK5uy_l1m0thk3g31NmIIz_vMIbWtyv7eZixlH0',
            'webpage_url_basename': 'playlist',
            'webpage_url_domain': 'music.youtube.com',
            'availability': str,
            'modified_date': str,
            'tags': [],
            'view_count': int,
        }
    }, {
        'url': 'https://beatbump.ml/artist/UC_aEa8K-EOJ3D6gOs7HcyNg',
        'playlist_mincount': 1,
        'params': {'flatplaylist': True},
        'info_dict': {
            'id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
            'title': 'NoCopyrightSounds - Videos',
            'uploader_id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
            'uploader': 'NoCopyrightSounds',
            'channel_follower_count': int,
            'channel': 'NoCopyrightSounds',
            'channel_id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
            'description': str,
            'tags': 'count:12',
            'channel_url': 'https://www.youtube.com/channel/UC_aEa8K-EOJ3D6gOs7HcyNg',
            'uploader_url': 'https://www.youtube.com/channel/UC_aEa8K-EOJ3D6gOs7HcyNg',
        },
    }, {
        'url': 'https://beatbump.ml/playlist/VLPLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
        'playlist_mincount': 1,
        'params': {'flatplaylist': True},
        'info_dict': {
            'id': 'PLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
            'uploader': 'NoCopyrightSounds',
            'description': 'Providing you with copyright free / safe music for gaming, live streaming, studying and more!',
            'uploader_id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
            'title': 'NCS : All Releases 💿',
            'modified_date': r're:\d{8}',
            'view_count': int,
            'channel_id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
            'tags': [],
            'channel': 'NoCopyrightSounds',
            'availability': 'public',
            'channel_url': 'https://www.youtube.com/@NoCopyrightSounds',
            'uploader_url': 'https://www.youtube.com/@NoCopyrightSounds',
        }
    }]

    def _real_extract(self, url):
        id_ = self._match_id(url)
        return self.url_result(f'https://music.youtube.com/browse/{id_}', YoutubeTabIE, id_)
