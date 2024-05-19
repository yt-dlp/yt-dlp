from .common import InfoExtractor
from .youtube import YoutubeIE, YoutubeTabIE


class BeatBumpVideoIE(InfoExtractor):
    _VALID_URL = r'https?://beatbump\.(?:ml|io)/listen\?id=(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://beatbump.ml/listen?id=MgNrAu2pzNs',
        'md5': '5ff3fff41d3935b9810a9731e485fe66',
        'info_dict': {
            'id': 'MgNrAu2pzNs',
            'ext': 'mp4',
            'artist': 'Stephen',
            'thumbnail': 'https://i.ytimg.com/vi_webp/MgNrAu2pzNs/maxresdefault.webp',
            'channel_url': 'https://www.youtube.com/channel/UC-pWHpBjdGG69N9mM2auIAA',
            'upload_date': '20190312',
            'categories': ['Music'],
            'playable_in_embed': True,
            'duration': 169,
            'like_count': int,
            'alt_title': 'Voyeur Girl',
            'view_count': int,
            'track': 'Voyeur Girl',
            'uploader': 'Stephen',
            'title': 'Voyeur Girl',
            'channel_follower_count': int,
            'age_limit': 0,
            'availability': 'public',
            'live_status': 'not_live',
            'album': 'it\'s too much love to know my dear',
            'channel': 'Stephen',
            'comment_count': int,
            'description': 'md5:7ae382a65843d6df2685993e90a8628f',
            'tags': 'count:11',
            'creator': 'Stephen',
            'channel_id': 'UC-pWHpBjdGG69N9mM2auIAA',
            'channel_is_verified': True,
            'heatmap': 'count:100',
        },
    }, {
        'url': 'https://beatbump.io/listen?id=LDGZAprNGWo',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id_ = self._match_id(url)
        return self.url_result(f'https://music.youtube.com/watch?v={id_}', YoutubeIE, id_)


class BeatBumpPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://beatbump\.(?:ml|io)/(?:release\?id=|artist/|playlist/)(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://beatbump.ml/release?id=MPREb_gTAcphH99wE',
        'playlist_count': 50,
        'info_dict': {
            'id': 'OLAK5uy_l1m0thk3g31NmIIz_vMIbWtyv7eZixlH0',
            'availability': 'unlisted',
            'view_count': int,
            'title': 'Album - Royalty Free Music Library V2 (50 Songs)',
            'description': '',
            'tags': [],
            'modified_date': '20231110',
        },
        'expected_warnings': ['YouTube Music is not directly supported'],
    }, {
        'url': 'https://beatbump.ml/artist/UC_aEa8K-EOJ3D6gOs7HcyNg',
        'playlist_mincount': 1,
        'params': {'flatplaylist': True},
        'info_dict': {
            'id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
            'uploader_url': 'https://www.youtube.com/@NoCopyrightSounds',
            'channel_url': 'https://www.youtube.com/channel/UC_aEa8K-EOJ3D6gOs7HcyNg',
            'uploader_id': '@NoCopyrightSounds',
            'channel_follower_count': int,
            'title': 'NoCopyrightSounds',
            'uploader': 'NoCopyrightSounds',
            'description': 'md5:cd4fd53d81d363d05eee6c1b478b491a',
            'channel': 'NoCopyrightSounds',
            'tags': 'count:65',
            'channel_id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
            'channel_is_verified': True,
        },
        'expected_warnings': ['YouTube Music is not directly supported'],
    }, {
        'url': 'https://beatbump.ml/playlist/VLPLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
        'playlist_mincount': 1,
        'params': {'flatplaylist': True},
        'info_dict': {
            'id': 'PLRBp0Fe2GpgmgoscNFLxNyBVSFVdYmFkq',
            'uploader_url': 'https://www.youtube.com/@NoCopyrightSounds',
            'description': 'Providing you with copyright free / safe music for gaming, live streaming, studying and more!',
            'view_count': int,
            'channel_url': 'https://www.youtube.com/channel/UC_aEa8K-EOJ3D6gOs7HcyNg',
            'uploader_id': '@NoCopyrightSounds',
            'title': 'NCS : All Releases 💿',
            'uploader': 'NoCopyrightSounds',
            'availability': 'public',
            'channel': 'NoCopyrightSounds',
            'tags': [],
            'modified_date': '20231112',
            'channel_id': 'UC_aEa8K-EOJ3D6gOs7HcyNg',
        },
        'expected_warnings': ['YouTube Music is not directly supported'],
    }, {
        'url': 'https://beatbump.io/playlist/VLPLFCHGavqRG-q_2ZhmgU2XB2--ZY6irT1c',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        id_ = self._match_id(url)
        return self.url_result(f'https://music.youtube.com/browse/{id_}', YoutubeTabIE, id_)
