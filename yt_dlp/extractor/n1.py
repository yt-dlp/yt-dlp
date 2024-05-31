import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    unified_timestamp,
)


class N1InfoAssetIE(InfoExtractor):
    _VALID_URL = r'https?://best-vod\.umn\.cdn\.united\.cloud/stream\?asset=(?P<id>[^&]+)'
    _TESTS = [{
        'url': 'https://best-vod.umn.cdn.united.cloud/stream?asset=ljsottomazilirija3060921-n1info-si-worldwide&stream=hp1400&t=0&player=m3u8v&sp=n1info&u=n1info&p=n1Sh4redSecre7iNf0',
        'md5': '28b08b32aeaff2b8562736ccd5a66fe7',
        'info_dict': {
            'id': 'ljsottomazilirija3060921-n1info-si-worldwide',
            'ext': 'mp4',
            'title': 'ljsottomazilirija3060921-n1info-si-worldwide',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        formats = self._extract_m3u8_formats(
            url, video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }


class N1InfoIIE(InfoExtractor):
    IE_NAME = 'N1Info:article'
    _VALID_URL = r'https?://(?:(?:\w+\.)?n1info\.\w+|nova\.rs)/(?:[^/?#]+/){1,2}(?P<id>[^/?#]+)'
    _TESTS = [{
        # Youtube embedded
        'url': 'https://rs.n1info.com/sport-klub/tenis/kako-je-djokovic-propustio-istorijsku-priliku-video/',
        'md5': '01ddb6646d0fd9c4c7d990aa77fe1c5a',
        'info_dict': {
            'id': 'L5Hd4hQVUpk',
            'ext': 'mp4',
            'upload_date': '20210913',
            'title': 'Ozmo i USO21, ep. 13: Novak Đoković – Danil Medvedev | Ključevi Poraza, Budućnost | SPORT KLUB TENIS',
            'description': 'md5:467f330af1effedd2e290f10dc31bb8e',
            'uploader': 'Sport Klub',
            'uploader_id': 'sportklub',
        }
    }, {
        'url': 'https://rs.n1info.com/vesti/djilas-los-plan-za-metro-nece-resiti-nijedan-saobracajni-problem/',
        'info_dict': {
            'id': 'bgmetrosot2409zta20210924174316682-n1info-rs-worldwide',
            'ext': 'mp4',
            'title': 'Đilas: Predlog izgradnje metroa besmislen; SNS odbacuje navode',
            'upload_date': '20210924',
            'timestamp': 1632481347,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://n1info.si/novice/slovenija/zadnji-dnevi-na-kopaliscu-ilirija-ilirija-ni-umrla-ubili-so-jo/',
        'info_dict': {
            'id': 'ljsottomazilirija3060921-n1info-si-worldwide',
            'ext': 'mp4',
            'title': 'Zadnji dnevi na kopališču Ilirija: “Ilirija ni umrla, ubili so jo”',
            'timestamp': 1632567630,
            'upload_date': '20210925',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Reddit embedded
        'url': 'https://ba.n1info.com/lifestyle/vucic-bolji-od-tita-ako-izgubi-ja-cu-da-crknem-jugoslavija-je-gotova/',
        'info_dict': {
            'id': '2wmfee9eycp71',
            'ext': 'mp4',
            'title': '"Ako Vučić izgubi izbore, ja ću da crknem, Jugoslavija je gotova"',
            'upload_date': '20210924',
            'timestamp': 1632448649.0,
            'uploader': 'YouLotWhatDontStop',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://nova.rs/vesti/politika/zaklina-tatalovic-ani-brnabic-pricate-lazi-video/',
        'info_dict': {
            'id': 'tnjganabrnabicizaklinatatalovic100danavladegp-novas-worldwide',
            'ext': 'mp4',
            'title': 'Žaklina Tatalović Ani Brnabić: Pričate laži (VIDEO)',
            'upload_date': '20211102',
            'timestamp': 1635861677,
        },
    }, {
        'url': 'https://n1info.rs/vesti/cuta-biti-u-kosovskoj-mitrovici-znaci-da-te-docekaju-eksplozivnim-napravama/',
        'info_dict': {
            'id': '1332368',
            'ext': 'mp4',
            'title': 'Ćuta: Biti u Kosovskoj Mitrovici znači da te dočekaju eksplozivnim napravama',
            'upload_date': '20230620',
            'timestamp': 1687290536,
            'thumbnail': 'https://cdn.brid.tv/live/partners/26827/snapshot/1332368_th_6492013a8356f_1687290170.jpg'
        },
    }, {
        'url': 'https://hr.n1info.com/vijesti/pravobraniteljica-o-ubojstvu-u-zagrebu-radi-se-o-doista-nezapamcenoj-situaciji/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<h1[^>]+>(.+?)</h1>', webpage, 'title')
        timestamp = unified_timestamp(self._html_search_meta('article:published_time', webpage))
        plugin_data = self._html_search_meta('BridPlugin', webpage)
        entries = []
        if plugin_data:
            site_id = self._html_search_regex(r'site:(\d+)', webpage, 'site id')
            for video_data in re.findall(r'\$bp\("Brid_\d+", (.+)\);', webpage):
                video_id = self._parse_json(video_data, title)['video']
                entries.append({
                    'id': video_id,
                    'title': title,
                    'timestamp': timestamp,
                    'thumbnail': self._html_search_meta('thumbnailURL', webpage),
                    'formats': self._extract_m3u8_formats(
                        f'https://cdn-uc.brid.tv/live/partners/{site_id}/streaming/{video_id}/{video_id}.m3u8',
                        video_id, fatal=False),
                })
        else:
            # Old player still present in older articles
            videos = re.findall(r'(?m)(<video[^>]+>)', webpage)
            for video in videos:
                video_data = extract_attributes(video)
                entries.append({
                    '_type': 'url_transparent',
                    'url': video_data.get('data-url'),
                    'id': video_data.get('id'),
                    'title': title,
                    'thumbnail': video_data.get('data-thumbnail'),
                    'timestamp': timestamp,
                    'ie_key': 'N1InfoAsset',
                })

        embedded_videos = re.findall(r'(<iframe[^>]+>)', webpage)
        for embedded_video in embedded_videos:
            video_data = extract_attributes(embedded_video)
            url = video_data.get('src') or ''
            if url.startswith('https://www.youtube.com'):
                entries.append(self.url_result(url, ie='Youtube'))
            elif url.startswith('https://www.redditmedia.com'):
                entries.append(self.url_result(url, ie='RedditR'))

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': title,
            'timestamp': timestamp,
            'entries': entries,
        }
