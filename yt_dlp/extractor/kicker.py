from .common import InfoExtractor
from .dailymotion import DailymotionIE


class KickerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)kicker\.(?:de)/(?P<id>[\w-]+)/video'
    _TESTS = [{
        'url': 'https://www.kicker.de/pogba-dembel-co-die-top-11-der-abloesefreien-spieler-905049/video',
        'info_dict': {
            'id': 'km04mrK0DrRAVxy2GcA',
            'title': 'md5:b91d145bac5745ac58d5479d8347a875',
            'ext': 'mp4',
            'duration': 350,
            'description': 'md5:a5a3dd77dbb6550dbfb997be100b9998',
            'uploader_id': 'x2dfupo',
            'timestamp': 1654677626,
            'like_count': int,
            'uploader': 'kicker.de',
            'view_count': int,
            'age_limit': 0,
            'thumbnail': r're:https://s\d+\.dmcdn\.net/v/T-x741YeYAx8aSZ0Z/x1080',
            'tags': ['published', 'category.InternationalSoccer'],
            'upload_date': '20220608',
        },
    }, {
        'url': 'https://www.kicker.de/ex-unioner-in-der-bezirksliga-felix-kroos-vereinschallenge-in-pankow-902825/video',
        'info_dict': {
            'id': 'k2omNsJKdZ3TxwxYSFJ',
            'title': 'md5:72ec24d7f84b8436fe1e89d198152adf',
            'ext': 'mp4',
            'uploader_id': 'x2dfupo',
            'duration': 331,
            'timestamp': 1652966015,
            'thumbnail': r're:https?://s\d+\.dmcdn\.net/v/TxU4Z1YYCmtisTbMq/x1080',
            'tags': ['FELIX KROOS', 'EINFACH MAL LUPPEN', 'KROOS', 'FSV FORTUNA PANKOW', 'published', 'category.Amateurs', 'marketingpreset.Spreekick'],
            'age_limit': 0,
            'view_count': int,
            'upload_date': '20220519',
            'uploader': 'kicker.de',
            'description': 'md5:0c2060c899a91c8bf40f578f78c5846f',
            'like_count': int,
        },
    }]

    def _real_extract(self, url):
        video_slug = self._match_id(url)

        webpage = self._download_webpage(url, video_slug)
        dailymotion_video_id = self._search_regex(
            r'data-dmprivateid\s*=\s*[\'"](?P<video_id>\w+)', webpage,
            'video id', group='video_id')

        return self.url_result(
            f'https://www.dailymotion.com/video/{dailymotion_video_id}',
            ie=DailymotionIE, video_title=self._html_extract_title(webpage))
