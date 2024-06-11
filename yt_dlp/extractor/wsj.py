from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    unified_strdate,
)


class WSJIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        (?:
                            https?://video-api\.wsj\.com/api-video/player/iframe\.html\?.*?\bguid=|
                            https?://(?:www\.)?(?:wsj|barrons)\.com/video/(?:[^/]+/)+|
                            wsj:
                        )
                        (?P<id>[a-fA-F0-9-]{36})
                    '''
    IE_DESC = 'Wall Street Journal'
    _TESTS = [{
        'url': 'http://video-api.wsj.com/api-video/player/iframe.html?guid=1BD01A4C-BFE8-40A5-A42F-8A8AF9898B1A',
        'md5': 'e230a5bb249075e40793b655a54a02e4',
        'info_dict': {
            'id': '1BD01A4C-BFE8-40A5-A42F-8A8AF9898B1A',
            'ext': 'mp4',
            'upload_date': '20150202',
            'uploader_id': 'jdesai',
            'creator': 'jdesai',
            'categories': list,  # a long list
            'duration': 90,
            'title': 'Bills Coach Rex Ryan Updates His Old Jets Tattoo',
        },
    }, {
        'url': 'http://www.wsj.com/video/can-alphabet-build-a-smarter-city/359DDAA8-9AC1-489C-82E6-0429C1E430E0.html',
        'only_matching': True,
    }, {
        'url': 'http://www.barrons.com/video/capitalism-deserves-more-respect-from-millennials/F301217E-6F46-43AE-B8D2-B7180D642EE9.html',
        'only_matching': True,
    }, {
        'url': 'https://www.wsj.com/video/series/a-brief-history-of/the-modern-cell-carrier-how-we-got-here/980E2187-401D-48A1-B82B-1486CEE06CB9',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info = self._download_json(
            'http://video-api.wsj.com/api-video/find_all_videos.asp', video_id,
            query={
                'type': 'guid',
                'count': 1,
                'query': video_id,
                'fields': ','.join((
                    'type', 'hls', 'videoMP4List', 'thumbnailList', 'author',
                    'description', 'name', 'duration', 'videoURL', 'titletag',
                    'formattedCreationDate', 'keywords', 'editor')),
            })['items'][0]
        title = info.get('name', info.get('titletag'))

        formats = []

        f4m_url = info.get('videoURL')
        if f4m_url:
            formats.extend(self._extract_f4m_formats(
                f4m_url, video_id, f4m_id='hds', fatal=False))

        m3u8_url = info.get('hls')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                info['hls'], video_id, ext='mp4',
                entry_protocol='m3u8_native', m3u8_id='hls', fatal=False))

        for v in info.get('videoMP4List', []):
            mp4_url = v.get('url')
            if not mp4_url:
                continue
            tbr = int_or_none(v.get('bitrate'))
            formats.append({
                'url': mp4_url,
                'format_id': 'http' + (f'-{tbr}' if tbr else ''),
                'tbr': tbr,
                'width': int_or_none(v.get('width')),
                'height': int_or_none(v.get('height')),
                'fps': float_or_none(v.get('fps')),
            })

        return {
            'id': video_id,
            'formats': formats,
            # Thumbnails are conveniently in the correct format already
            'thumbnails': info.get('thumbnailList'),
            'creator': info.get('author'),
            'uploader_id': info.get('editor'),
            'duration': int_or_none(info.get('duration')),
            'upload_date': unified_strdate(info.get(
                'formattedCreationDate'), day_first=False),
            'title': title,
            'categories': info.get('keywords'),
        }


class WSJArticleIE(InfoExtractor):
    _VALID_URL = r'(?i)https?://(?:www\.)?wsj\.com/articles/(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.wsj.com/articles/dont-like-china-no-pandas-for-you-1490366939?',
        'info_dict': {
            'id': '4B13FA62-1D8C-45DB-8EA1-4105CB20B362',
            'ext': 'mp4',
            'upload_date': '20170221',
            'uploader_id': 'ralcaraz',
            'title': 'Bao Bao the Panda Leaves for China',
        },
    }

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)
        video_id = self._search_regex(
            r'(?:id=["\']video|video-|iframe\.html\?guid=|data-src=["\'])([a-fA-F0-9-]{36})',
            webpage, 'video id')
        return self.url_result(f'wsj:{video_id}', WSJIE.ie_key(), video_id)
