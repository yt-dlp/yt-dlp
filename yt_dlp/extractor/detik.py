from .common import InfoExtractor
from ..utils import merge_dicts, str_or_none


class Detik20IE(InfoExtractor):
    IE_NAME = '20.detik.com'
    _VALID_URL = r'https?://20\.detik\.com/((?!program)[\w-]+)/[\d-]+/(?P<id>[\w-]+)'
    _TESTS = [{
        # detikflash
        'url': 'https://20.detik.com/detikflash/20220705-220705098/zulhas-klaim-sukses-turunkan-harga-migor-jawa-bali',
        'info_dict': {
            'id': '220705098',
            'ext': 'mp4',
            'duration': 157,
            'thumbnail': 'https://cdnv.detik.com/videoservice/AdminTV/2022/07/05/bfe0384db04f4bbb9dd5efc869c5d4b1-20220705164334-0s.jpg?w=650&q=80',
            'description': 'md5:ac18dcee5b107abbec1ed46e0bf400e3',
            'title': 'Zulhas Klaim Sukses Turunkan Harga Migor Jawa-Bali',
            'tags': ['zulkifli hasan', 'menteri perdagangan', 'minyak goreng'],
            'timestamp': 1657039548,
            'upload_date': '20220705'
        }
    }, {
        # e-flash
        'url': 'https://20.detik.com/e-flash/20220705-220705109/ahli-level-ppkm-jadi-payung-strategi-protokol-kesehatan',
        'info_dict': {
            'id': '220705109',
            'ext': 'mp4',
            'tags': ['ppkm jabodetabek', 'dicky budiman', 'ppkm'],
            'upload_date': '20220705',
            'duration': 110,
            'title': 'Ahli: Level PPKM Jadi Payung Strategi Protokol Kesehatan',
            'thumbnail': 'https://cdnv.detik.com/videoservice/AdminTV/2022/07/05/Ahli-_Level_PPKM_Jadi_Payung_Strat_jOgUMCN-20220705182313-custom.jpg?w=650&q=80',
            'description': 'md5:4eb825a9842e6bdfefd66f47b364314a',
            'timestamp': 1657045255,
        }
    }, {
        # otobuzz
        'url': 'https://20.detik.com/otobuzz/20220704-220704093/mulai-rp-10-jutaan-ini-skema-kredit-mitsubishi-pajero-sport',
        'info_dict': {
            'id': '220704093',
            'ext': 'mp4',
            'tags': ['cicilan mobil', 'mitsubishi pajero sport', 'mitsubishi', 'pajero sport'],
            'timestamp': 1656951521,
            'duration': 83,
            'upload_date': '20220704',
            'thumbnail': 'https://cdnv.detik.com/videoservice/AdminTV/2022/07/04/5d6187e402ec4a91877755a5886ff5b6-20220704161859-0s.jpg?w=650&q=80',
            'description': 'md5:9b2257341b6f375cdcf90106146d5ffb',
            'title': 'Mulai Rp 10 Jutaan! Ini Skema Kredit Mitsubishi Pajero Sport',
        }
    }, {
        # sport-buzz
        'url': 'https://20.detik.com/sport-buzz/20220704-220704054/crash-crash-horor-di-paruh-pertama-motogp-2022',
        'info_dict': {
            'id': '220704054',
            'ext': 'mp4',
            'thumbnail': 'https://cdnv.detik.com/videoservice/AdminTV/2022/07/04/6b172c6fb564411996ea145128315630-20220704090746-0s.jpg?w=650&q=80',
            'title': 'Crash-crash Horor di Paruh Pertama MotoGP 2022',
            'description': 'md5:fbcc6687572ad7d16eb521b76daa50e4',
            'timestamp': 1656925591,
            'duration': 107,
            'tags': ['marc marquez', 'fabio quartararo', 'francesco bagnaia', 'motogp crash', 'motogp 2022'],
            'upload_date': '20220704',
        }
    }, {
        # adu-perspektif
        'url': 'https://20.detik.com/adu-perspektif/20220518-220518144/24-tahun-reformasi-dan-alarm-demokrasi-dari-filipina',
        'info_dict': {
            'id': '220518144',
            'ext': 'mp4',
            'title': '24 Tahun Reformasi dan Alarm Demokrasi dari Filipina',
            'upload_date': '20220518',
            'timestamp': 1652913823,
            'duration': 185.0,
            'tags': ['politik', 'adu perspektif', 'indonesia', 'filipina', 'demokrasi'],
            'description': 'md5:8eaaf440b839c3d02dca8c9bbbb099a9',
            'thumbnail': 'https://cdnv.detik.com/videoservice/AdminTV/2022/05/18/adpers_18_mei_compressed-20220518230458-custom.jpg?w=650&q=80',
        }
    }, {
        # sosok
        'url': 'https://20.detik.com/sosok/20220702-220703032/resa-boenard-si-princess-bantar-gebang',
        'info_dict': {
            'id': '220703032',
            'ext': 'mp4',
            'timestamp': 1656824438,
            'thumbnail': 'https://cdnv.detik.com/videoservice/AdminTV/2022/07/02/SOSOK_BGBJ-20220702191138-custom.jpg?w=650&q=80',
            'title': 'Resa Boenard Si \'Princess Bantar Gebang\'',
            'description': 'md5:84ea66306a0285330de6a13fc6218b78',
            'tags': ['sosok', 'sosok20d', 'bantar gebang', 'bgbj', 'resa boenard', 'bantar gebang bgbj', 'bgbj bantar gebang', 'sosok bantar gebang', 'sosok bgbj', 'bgbj resa boenard'],
            'upload_date': '20220703',
            'duration': 650,
        }
    }, {
        # viral
        'url': 'https://20.detik.com/viral/20220603-220603135/merasakan-bus-imut-tanpa-pengemudi-muter-muter-di-kawasan-bsd-city',
        'info_dict': {
            'id': '220603135',
            'ext': 'mp4',
            'description': 'md5:4771fe101aa303edb829c59c26f9e7c6',
            'timestamp': 1654304305,
            'title': 'Merasakan Bus Imut Tanpa Pengemudi, Muter-muter di Kawasan BSD City',
            'tags': ['viral', 'autonomous vehicle', 'electric', 'shuttle bus'],
            'thumbnail': 'https://cdnv.detik.com/videoservice/AdminTV/2022/06/03/VIRAL_BUS_NO_SUPIR-20220604004707-custom.jpg?w=650&q=80',
            'duration': 593,
            'upload_date': '20220604',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        json_ld_data = self._search_json_ld(webpage, display_id)

        video_url = self._html_search_regex(
            r'videoUrl\s*:\s*"(?P<video_url>[^"]+)', webpage, 'videoUrl')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, display_id, ext='mp4')

        return merge_dicts(json_ld_data, {
            'id': self._html_search_meta('video_id', webpage),
            'formats': formats,
            'subtitles': subtitles,
            'tags': str_or_none(self._html_search_meta(['keywords', 'keyword', 'dtk:keywords'], webpage), '').split(','),
        })
