from .common import InfoExtractor


class HKETVIE(InfoExtractor):
    IE_NAME = 'hketv'
    IE_DESC = '教育局教育多媒體 (EDB Educational Multimedia (EMM)) (emm.edcity.hk)'
    _VALID_URL = r'https?://emm\.edcity\.hk/media/[^/?#]+/(?P<id>[0-9]+_[0-9a-z]+)'
    _TESTS = [{
        'url': 'https://emm.edcity.hk/media/Hong+Kong-Zhuhai-Macao+Bridge+Thematic+Learning+and+Teaching+Resources%28Chinese+subtitles+available%29/1_2kd22ia5/172025822',
        'md5': '1b3f69f3560f1dbee4df573a7a985eaf',
        'info_dict': {
            'id': '1_2kd22ia5',
            'ext': 'mp4',
            'title': '「港珠澳大橋」主題學與教資源 (中文字幕可供選擇)',
        },
        'skip': 'Geo-restricted to HK',
    }]

    def _real_extract(self, url):
        entry_id = self._match_id(url)
        webpage = self._download_webpage(url, entry_id)
        partner_id = self._search_regex(
            r'"partnerId"\s*:\s*(\d+)', webpage, 'partner ID', default='2621712')
        return self.url_result(
            f'kaltura:{partner_id}:{entry_id}',
            ie='Kaltura', video_id=entry_id)
