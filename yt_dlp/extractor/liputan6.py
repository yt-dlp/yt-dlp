from .common import InfoExtractor
from .vidio import VidioIE


class Liputan6IE(InfoExtractor):
    _VALID_URL = r'https?://www\.liputan6\.com/\w+/read/\d+/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.liputan6.com/news/read/5007510/video-duh-perawat-rs-di-medan-diduga-salah-berikan-obat-ke-pasien',
        'info_dict': {
            'id': '7082548',
            'ext': 'mp4',
            'title': 'Duh, Perawat RS di Medan Diduga Salah Berikan Obat Ke Pasien',
            'thumbnail': 'https://thumbor.prod.vidiocdn.com/lOz5pStm9X-jjlTa_VQQUelOPtw=/640x360/filters:quality(70)/vidio-web-prod-video/uploads/video/image/7082548/duh-perawat-rs-di-medan-diduga-salah-berikan-obat-ke-pasien-ca1125.jpg',
            'channel_id': '185693',
            'uploader': 'Liputan6.com',
            'duration': 104,
            'uploader_url': 'https://www.vidio.com/@liputan6',
            'description': 'md5:3b58ecff10ec3a41d4304cf98228435a',
            'timestamp': 1657159427,
            'uploader_id': 'liputan6',
            'display_id': 'video-duh-perawat-rs-di-medan-diduga-salah-berikan-obat-ke-pasien',
            'like_count': int,
            'view_count': int,
            'comment_count': int,
            'tags': ['perawat indonesia', 'rumah sakit', 'Medan', 'viral hari ini', 'viral', 'enamplus'],
            'channel': 'Default Channel',
            'dislike_count': int,
            'upload_date': '20220707'
        }
    }, {
        'url': 'https://www.liputan6.com/tv/read/5007719/video-program-minyakita-minyak-goreng-kemasan-sederhana-seharga-rp-14-ribu',
        'info_dict': {
            'id': '7082543',
            'ext': 'mp4',
            'title': 'md5:ecb7b3c598b97798bfd0eb50c6233b8c',
            'channel_id': '604054',
            'dislike_count': int,
            'comment_count': int,
            'timestamp': 1657159211,
            'upload_date': '20220707',
            'tags': ['minyakita', 'minyak goreng', 'liputan 6', 'sctv'],
            'uploader_url': 'https://www.vidio.com/@sctv',
            'display_id': 'video-program-minyakita-minyak-goreng-kemasan-sederhana-seharga-rp-14-ribu',
            'like_count': int,
            'uploader': 'SCTV',
            'description': 'md5:6c374d82589b71fb98b3d550edb6873f',
            'duration': 99,
            'uploader_id': 'sctv',
            'thumbnail': 'https://thumbor.prod.vidiocdn.com/AAIOjz-64hKojjdw5hr0oNNEeJg=/640x360/filters:quality(70)/vidio-web-prod-video/uploads/video/image/7082543/program-minyakita-minyak-goreng-kemasan-sederhana-seharga-rp14-ribu-_-liputan-6-7d9fbb.jpg',
            'channel': 'Liputan 6 Pagi',
            'view_count': int,
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        json_data = self._search_json(
            r'window.kmklabs.gtm\s*=', webpage, 'json_data', display_id)
        video_id = json_data['videos']['video_1']['video_id']

        return self.url_result(
            f'https://www.vidio.com/watch/{video_id}-{display_id}', ie=VidioIE, video_id=display_id)
