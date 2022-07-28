from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    str_or_none,
    traverse_obj,
    unescapeHTML,
)

# Video from www.kompas.tv and video.kompas.com seems use jixie player

class KompasVideoIE(InfoExtractor):
    _VALID_URL = r'https?://video\.kompas\.com/\w+/(?P<id>\d+)/(?P<slug>[\w-]+)'
    _TESTS = [{
        'url': 'https://video.kompas.com/watch/164474/kim-jong-un-siap-kirim-nuklir-lawan-as-dan-korsel',
        'info_dict': {
            'id': '164474',
            'ext': 'mp4',
            'title': 'Kim Jong Un Siap Kirim Nuklir Lawan AS dan Korsel',
            'description': 'md5:262530c4fb7462398235f9a5dba92456',
            'uploader_id': '9262bf2590d558736cac4fff7978fcb1',
            'display_id': 'kim-jong-un-siap-kirim-nuklir-lawan-as-dan-korsel',
            'duration': 85.066667,
            'categories': ['news'],
            'thumbnail': 'https://video.jixie.media/1001/164474/164474_426x240.jpg',
            'tags': ['kcm', 'news', 'korea-utara', 'kim-jong-un', 'senjata-nuklir-korea-utara', 'nuklir-korea-utara', 'korea-selatan', 'amerika-serikat', 'latihan-bersama-korea-selatan-dan-amerika-serikat'],
        }
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'slug')
        webpage = self._download_webpage(url, display_id)

        json_data = self._download_json(
            'https://apidam.jixie.io/api/public/stream', display_id,
            query={'metadata': 'full', 'video_id': video_id})['data']

        formats, subtitles = [], {}
        for stream in json_data['streams']:
            if stream.get('type') == 'HLS':
                fmt, sub = self._extract_m3u8_formats_and_subtitles(stream.get('url'), display_id, ext='mp4')
                formats.extend(fmt)
                self._merge_subtitles(sub, target=subtitles)
            else:
                formats.append({
                    'url': stream.get('url'),
                    'width': stream.get('width'),
                    'height': stream.get('height'),
                    'ext': 'mp4',
                })

        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': json_data.get('title') or self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'description': (clean_html(traverse_obj(json_data, ('metadata', 'description')))
                            or self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage)),
            'thumbnails': traverse_obj(json_data, ('metadata', 'thumbnails')),
            'thumbnail': traverse_obj(json_data, ('metadata', 'thumbnail')),
            'duration': float_or_none(traverse_obj(json_data, ('metadata', 'duration'))),
            'has_drm': json_data.get('drm'),
            'tags': str_or_none(traverse_obj(json_data, ('metadata', 'keywords')), '').split(',') or None,
            'categories': str_or_none(traverse_obj(json_data, ('metadata', 'categories')), '').split(',') or None,
            'uploader_id': json_data.get('owner_id'),
        }


class KompasTVIE(InfoExtractor):
    _VALID_URL = r'https?://www\.kompas\.tv/\w+/(?P<id>\d+)/(?P<slug>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.kompas.tv/article/313808/cegah-pmk-dengan-booster-dinas-pertanian-suntik-ratusan-sapi-di-pekanbaru',
        'info_dict': {
            'id': 'fixme',
            'ext': 'mp4',
        }
    }]
    
    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'slug')
        webpage = self._download_webpage(url, display_id)
        
        # the urls can found in json_ld(embedUrl) and iframe(src attr)
        urls = []
        # extracting from json_ld
        json_ld_data = list(self._yield_json_ld(webpage, display_id))
        for json_ld in json_ld_data:
            if json_ld.get('embedUrl'):
                urls.append(unescapeHTML(json_ld.get('embedUrl')))
        print(urls)
        
        # extracting from iframe
        # TODO: better regex
        url = self._search_regex(
            r'<iframe[^>]\s*[\w="\s]+\bsrc=\'(?P<iframe_src>[^\']+)',
            webpage, 'iframe_url', fatal=False, group=('iframe_src'))
        urls.append(url)
        print(urls)
        
        formats = []
        
        for url in urls:
            formats.append(self.url_result(url))
            
        # TODO: add more metadata fallback: json_ld, window.jixie_p.push
        # FIXME: this code return error as __type is not Video
        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': urls[1],
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'description': self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage),
            'thumbnail': self._html_search_meta(['og:image', 'twitter:image'], webpage),
            'tags': str_or_none(self._html_search_meta(['keywords', 'content_tag'], webpage), '').split(',') or None,   
        }        
