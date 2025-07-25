import re

from .common import InfoExtractor
from .vimeo import VimeoIE


class PlyrEmbedIE(InfoExtractor):
    _VALID_URL = False
    _WEBPAGE_TESTS = [{
        # data-plyr-embed-id="https://player.vimeo.com/video/522319456/90e5c96063?dnt=1"
        'url': 'https://www.dhm.de/zeughauskino/filmreihen/online-filmreihen/filme-des-marshall-plans/200000000-mouths/',
        'info_dict': {
            'id': '522319456',
            'ext': 'mp4',
            'title': '200.000.000 Mouths (1950–51)',
            'uploader': 'Zeughauskino',
            'uploader_url': '',
            'comment_count': int,
            'like_count': int,
            'duration': 963,
            'thumbnail': 'https://i.vimeocdn.com/video/1081797161-9f09ddb4b7faa86e834e006b8e4b9c2cbaa0baa7da493211bf0796ae133a5ab8-d',
            'timestamp': 1615467405,
            'upload_date': '20210311',
            'release_timestamp': 1615467405,
            'release_date': '20210311',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to parse XML: not well-formed'],
    }, {
        # data-plyr-provider="vimeo" data-plyr-embed-id="803435276"
        'url': 'https://www.inarcassa.it/',
        'info_dict': {
            'id': '803435276',
            'ext': 'mp4',
            'title': 'HOME_Moto_Perpetuo',
            'uploader': 'Inarcassa',
            'uploader_url': '',
            'duration': 38,
            'thumbnail': 'https://i.vimeocdn.com/video/1663734769-945ad7ffabb16dbca009c023fd1d7b36bdb426a3dbae8345ed758136fe28f89a-d',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to parse XML: not well-formed'],
    }, {
        # data-plyr-embed-id="https://youtu.be/GF-BjYKoAqI"
        'url': 'https://www.profile.nl',
        'info_dict': {
            'id': 'GF-BjYKoAqI',
            'ext': 'mp4',
            'title': 'PROFILE: Recruitment Profile',
            'description': '',
            'media_type': 'video',
            'uploader': 'Profile Nederland',
            'uploader_id': '@profilenederland',
            'uploader_url': 'https://www.youtube.com/@profilenederland',
            'channel': 'Profile Nederland',
            'channel_id': 'UC9AUkB0Tv39-TBYjs05n3vg',
            'channel_url': 'https://www.youtube.com/channel/UC9AUkB0Tv39-TBYjs05n3vg',
            'channel_follower_count': int,
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'duration': 39,
            'thumbnail': 'https://i.ytimg.com/vi/GF-BjYKoAqI/maxresdefault.jpg',
            'categories': ['Autos & Vehicles'],
            'tags': [],
            'timestamp': 1675692990,
            'upload_date': '20230206',
            'playable_in_embed': True,
            'availability': 'public',
            'live_status': 'not_live',
        },
    }, {
        # data-plyr-embed-id="B1TZV8rNZoc" data-plyr-provider="youtube"
        'url': 'https://www.vnis.edu.vn',
        'info_dict': {
            'id': 'vnis.edu',
            'title': 'VNIS Education - Master Agent các Trường hàng đầu Bắc Mỹ',
            'description': 'md5:4dafcf7335bb018780e4426da8ab8e4e',
            'age_limit': 0,
            'thumbnail': 'https://vnis.edu.vn/wp-content/uploads/2021/05/ve-welcome-en.png',
            'timestamp': 1753233356,
            'upload_date': '20250723',
        },
        'playlist_count': 3,
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        plyr_embeds = re.finditer(r'''(?x)
            <div[^>]+(?:
                data-plyr-embed-id="(?P<id1>[^"]+)"[^>]+data-plyr-provider="(?P<provider1>[^"]+)"|
                data-plyr-provider="(?P<provider2>[^"]+)"[^>]+data-plyr-embed-id="(?P<id2>[^"]+)"
            )[^>]*>''', webpage)
        for mobj in plyr_embeds:
            embed_id = mobj.group('id1') or mobj.group('id2')
            provider = mobj.group('provider1') or mobj.group('provider2')
            if provider == 'vimeo':
                if not re.match(r'https?://', embed_id):
                    embed_id = f'https://player.vimeo.com/video/{embed_id}'
                yield VimeoIE._smuggle_referrer(embed_id, url)
            elif provider == 'youtube':
                if not re.match(r'https?://', embed_id):
                    embed_id = f'https://youtube.com/watch?v={embed_id}'
                yield embed_id
