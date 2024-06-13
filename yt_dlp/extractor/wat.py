from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    try_get,
    unified_strdate,
)


class WatIE(InfoExtractor):
    _VALID_URL = r'(?:wat:|https?://(?:www\.)?wat\.tv/video/.*-)(?P<id>[0-9a-z]+)'
    IE_NAME = 'wat.tv'
    _TESTS = [
        {
            'url': 'http://www.wat.tv/video/soupe-figues-l-orange-aux-epices-6z1uz_2hvf7_.html',
            'info_dict': {
                'id': '11713067',
                'ext': 'mp4',
                'title': 'Soupe de figues à l\'orange et aux épices',
                'description': 'Retrouvez l\'émission "Petits plats en équilibre", diffusée le 18 août 2014.',
                'upload_date': '20140819',
                'duration': 120,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
            'expected_warnings': ['HTTP Error 404'],
            'skip': 'This content is no longer available',
        },
        {
            'url': 'http://www.wat.tv/video/gregory-lemarchal-voix-ange-6z1v7_6ygkj_.html',
            'md5': 'b16574df2c3cd1a36ca0098f2a791925',
            'info_dict': {
                'id': '11713075',
                'ext': 'mp4',
                'title': 'Grégory Lemarchal, une voix d\'ange depuis 10 ans (1/3)',
                'upload_date': '20140816',
            },
            'expected_warnings': ["Ce contenu n'est pas disponible pour l'instant."],
            'skip': 'This content is no longer available',
        },
        {
            'url': 'wat:14010600',
            'info_dict': {
                'id': '14010600',
                'title': 'Burger Quiz - S03 EP21 avec Eye Haidara, Anne Depétrini, Jonathan Zaccaï et Pio Marmaï',
                'thumbnail': 'https://photos.tf1.fr/1280/720/burger-quiz-11-9adb79-0@1x.jpg',
                'upload_date': '20230819',
                'duration': 2312,
                'ext': 'mp4',
            },
            'params': {'skip_download': 'm3u8'},
        },
    ]
    _GEO_BYPASS = False

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_id = video_id if video_id.isdigit() and len(video_id) > 6 else str(int(video_id, 36))

        # 'contentv4' is used in the website, but it also returns the related
        # videos, we don't need them
        # video_data = self._download_json(
        #     'http://www.wat.tv/interface/contentv4s/' + video_id, video_id)
        video_data = self._download_json(
            'https://mediainfo.tf1.fr/mediainfocombo/' + video_id,
            video_id, query={'pver': '5010000'})
        video_info = video_data['media']

        error_desc = video_info.get('error_desc')
        if error_desc:
            if video_info.get('error_code') == 'GEOBLOCKED':
                self.raise_geo_restricted(error_desc, video_info.get('geoList'))
            raise ExtractorError(error_desc, expected=True)

        title = video_info['title']

        formats = []
        subtitles = {}

        def extract_formats(manifest_urls):
            for f, f_url in manifest_urls.items():
                if not f_url:
                    continue
                if f in ('dash', 'mpd'):
                    fmts, subs = self._extract_mpd_formats_and_subtitles(
                        f_url.replace('://das-q1.tf1.fr/', '://das-q1-ssl.tf1.fr/'),
                        video_id, mpd_id='dash', fatal=False)
                elif f == 'hls':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        f_url, video_id, 'mp4',
                        'm3u8_native', m3u8_id='hls', fatal=False)
                else:
                    continue
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

        delivery = video_data.get('delivery') or {}
        extract_formats({delivery.get('format'): delivery.get('url')})
        if not formats:
            if delivery.get('drm'):
                self.report_drm(video_id)
            manifest_urls = self._download_json(
                'http://www.wat.tv/get/webhtml/' + video_id, video_id, fatal=False)
            if manifest_urls:
                extract_formats(manifest_urls)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': video_info.get('preview'),
            'upload_date': unified_strdate(try_get(
                video_data, lambda x: x['mediametrie']['chapters'][0]['estatS4'])),
            'duration': int_or_none(video_info.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
        }
