from .common import InfoExtractor
from ..utils import unified_strdate


class HKETIE(InfoExtractor):
    _VALID_URL = r'https?://video\.hket\.com/video/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://video.hket.com/video/3278159/%E3%80%90%E5%89%B5%E6%A5%ADideas%E3%80%91%E9%87%9D%E5%B0%8D%E6%9C%83%E8%A8%88%E5%B7%A5%E4%BD%9C%E7%97%9B%E9%BB%9E%E3%80%80%E7%A7%91%E6%8A%80%E7%94%B7%E5%89%B5AI%E6%99%BA%E8%83%BD%E6%9C%83%E8%A8%88%E5%B9%B3%E5%8F%B0',
        'info_dict': {
            'id': '3278159',
            'ext': 'mp4',
            'tags': 'count:50',
            'upload_date': '20220617',
            'uploader': '創業ideas',
            'description': '會計工作一向被認為複雜繁瑣，不少企業會將其外判給會計公司處理。有港青看準中小企在處理會計業務上的痛點，投資6位數創立智能會計平台，利用AI技術分析現金流狀況、資產及負債等，支援企業決策的關鍵資訊。',
            'video_id': '3278159',
            'title': '【創業ideas】針對會計工作痛點　科技男創AI智能會計平台',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://video.hket.com/video/3270826/%E3%80%90%E5%89%B5%E6%A5%ADideas%E3%80%91%E6%B8%AF%E5%A5%B3%E5%A4%A5%E6%8B%8D%E6%AA%94%E5%89%B5%E9%80%81%E7%A6%AE%E5%B9%B3%E5%8F%B0%20%E7%B7%A9%E8%A7%A3%E7%96%AB%E4%B8%8B%E6%96%B0%E6%9C%8B%E7%96%8F%E9%9B%A2%E6%84%9F?mtc=a0006',
        'info_dict': {
            'id': '3270826',
            'ext': 'mp4',
            'title': '【創業ideas】港女夥拍檔創送禮平台 緩解疫下新朋疏離感',
            'uploader': '創業ideas',
            'description': '疫情期間，為了防疫保持著社交距離，人與人之間變得疏離。90後港女Ivy與兩位拍檔，為了重新拉近親友之間的聯繫，疫下創立本地送禮平台。 透過「一禮物、一心意卡」的訂單設定，強調送禮的心意和儀式感。又加入',
            'tags': 'count:6',
            'video_id': '3270826',
            'upload_date': '20220610',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def generate_m3u8(self, vid, video_filename):
        # In case this extractor is broken, it's likely that these values have changed.
        # These were found in video-autoplay-<whatever>.min.js with same keys.

        domain = 'd3okrhbhk6fs3y.cloudfront.net'
        source_dir = 'p1prod'
        r = int(5e3 * (int(vid / 5e3) | 0))

        return f'https://{domain}/{source_dir}/{r}/{vid}/{video_filename}.m3u8'

    def find_data_property(self, property, webpage, validation=str, fatal=True):
        try:
            return validation(self._search_regex(fr'data-{property}\s*=\s*"([^"]+)"', webpage, property, fatal=fatal))
        except Exception as e:
            if fatal:
                return e
            return None

    def _real_extract(self, url):
        id = self._match_id(url)
        url = url.split(r'\?')[0]

        webpage = self._download_webpage(url, id, headers={'Host': 'video.hket.com'})

        video_filename_with_extension = self.find_data_property('filename', webpage)
        video_filename = video_filename_with_extension.rsplit('.', maxsplit=1)[0]
        video_extension = video_filename_with_extension.rsplit('.', maxsplit=1)[1]

        vid = self.find_data_property('rel', webpage, int)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url=self.generate_m3u8(vid, video_filename),
            video_id=id,
            ext=video_extension
        )

        self._sort_formats(formats)

        return {
            'id': id,
            'video_id': str(vid),
            'formats': formats,
            'subtitles': subtitles,
            'title': self.find_data_property('videotitle', webpage, str, False) or self._og_search_title(webpage),
            'upload_date': self.find_data_property('videopublishdate', webpage, unified_strdate, False),
            'tags': self.find_data_property('formaltag', webpage, lambda x: x.split(','), False),
            'uploader': self.find_data_property('videoprogram', webpage, str, False),
            'description': self._og_search_description(webpage)
        }
