from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    str_or_none,
    traverse_obj,
    unescapeHTML,
)

# Video from www.kompas.tv and video.kompas.com seems use jixie player
# see [1] https://jixie.atlassian.net/servicedesk/customer/portal/2/article/1339654214?src=-1456335525,
# [2] https://scripts.jixie.media/jxvideo.3.1.min.js for more info

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


class KompasTVBaseIE(InfoExtractor):
    def _extract_formats_from_dailymotion_id(self, webpage, video_id, slug):
        metadata_json = self._download_json(f'https://www.dailymotion.com/player/metadata/video/{video_id}', slug)
        video_urls = traverse_obj(metadata_json, ('qualities', 'auto', ..., 'url'))
        
        formats, subtitles = [], {}
        for url in video_urls:
            fmt, subs = self._extract_m3u8_formats_and_subtitles(url, slug)
            formats.extend(fmt)
            self._merge_subtitles(subs, target=subtitles)
        
        self._sort_formats(formats)
        
        return {
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'formats': formats,
            'subtitles': subtitles,
            'description': self._html_search_meta(['og:description', 'twitter:description'], webpage),
            'uploader': traverse_obj(metadata_json, ('owner', 'screenname')),
            'uploader_url': traverse_obj(metadata_json, ('owner', 'url')),
            'uploader_id': metadata_json.get('owner.id') or traverse_obj(metadata_json, ('owner', 'id')),
            'timestamp': int_or_none(metadata_json.get('created_time')),
        }

class KompasTVIE(KompasTVBaseIE):
    _VALID_URL = r'https?://www\.kompas\.tv/\w+/(?P<id>\d+)/(?P<slug>[\w-]+)'
    _TESTS = [{
        # works with generic too
        'url': 'https://www.kompas.tv/article/313808/cegah-pmk-dengan-booster-dinas-pertanian-suntik-ratusan-sapi-di-pekanbaru',
        'info_dict': {
            'id': 'WoDysbXmYrw',
            'ext': 'mp4',
            'comment_count': int,
            'like_count': int,
            'categories': ['News & Politics'],
            'playable_in_embed': True,
            'tags': ['luwak', 'noads', 'pmk', 'sapi pmk', 'vaksin pmk', 'vaksin sapi pmk'],
            'thumbnail': 'https://i.ytimg.com/vi/WoDysbXmYrw/hqdefault.jpg',
            'uploader_id': 'KompasTVNews',
            'upload_date': '20220728',
            'title': 'Cegah PMK dengan Booster, Dinas Pertanian Suntik Ratusan Sapi di Pekanbaru',
            'uploader': 'KOMPASTV',
            'channel': 'KOMPASTV',
            'channel_url': 'https://www.youtube.com/channel/UC5BMIWZe9isJXLZZWPWvBlg',
            'age_limit': 0,
            'channel_follower_count': int,
            'availability': 'public',
            'duration': 110,
            'view_count': int,
            'description': 'md5:9adf1e13cdc6a3fdb0fca19445db0062',
            'channel_id': 'UC5BMIWZe9isJXLZZWPWvBlg',
            'live_status': 'not_live',
            'uploader_url': 'http://www.youtube.com/user/KompasTVNews'
        }
    }, {
        # generic extractor take wrong url (content_url instead embedUrl)
        'url': 'https://www.youtube.com/embed/3N9tV6WFVag?autoplay=0&amp;fs=1&amp;rel=0&amp;showinfo=1&amp;modestbranding=1',
        'info_dict': {
            'id': '3N9tV6WFVag',
            'ext': 'mp4',
            'tags': ['jakarta', 'kunjungan presiden', 'kunjungan presiden ke asia', 'moeldoko', 'staf kepresidenan moeldoko'],
            'categories': ['News & Politics'],
            'thumbnail': 'https://i.ytimg.com/vi/3N9tV6WFVag/hqdefault.jpg',
            'live_status': 'not_live',
            'age_limit': 0,
            'channel_url': 'https://www.youtube.com/channel/UC5BMIWZe9isJXLZZWPWvBlg',
            'channel': 'KOMPASTV',
            'playable_in_embed': True,
            'comment_count': int,
            'uploader_id': 'KompasTVNews',
            'view_count': int,
            'duration': 49,
            'availability': 'public',
            'title': 'Hasil Kunjungan Presiden ke 3 Negara Asia, Moeldoko: Sangat berdampak Baik Bagi Petani Sawit',
            'uploader': 'KOMPASTV',
            'channel_follower_count': int,
            'like_count': int,
            'upload_date': '20220730',
            'description': 'md5:626ccb6110dd77a6213e8c44b4255599',
            'channel_id': 'UC5BMIWZe9isJXLZZWPWvBlg',
            'uploader_url': 'http://www.youtube.com/user/KompasTVNews',
        }
    }, {
        # dailymotion video id only
        'url': 'https://www.kompas.tv/rehat/262882/star-of-the-week-oh-my-v33nus-good-gamer?source=rehat&program=good-gamer',
        'info_dict': {
            'id': 'x880bsp',
            'ext': 'mp4',
            'thumbnail': 'https://s2.dmcdn.net/v/TecEv1YTYIT-DEPKN/x1080',
            'description': 'md5:072b8f77fbdf9db5faa5fad0b4176f1f',
            'uploader': 'KompasTV',
            'tags': ['senz huston', 'founder dan ceo revival tv', 'my v33nus', 'game baru', 'game mobile', 'good gamer'],
            'like_count': int,
            'upload_date': '20220218',
            'duration': 108,
            'view_count': int,
            'title': 'Star Of The Week: Oh My V33nus - GOOD GAMER',
            'timestamp': 1645184491,
            'age_limit': 0,
            'uploader_id': 'x1vv20s',
        }
    }, {
        # FIXME: wrong youtube embed, get actual dailymotion video_id
        'url': 'https://www.kompas.tv/article/314017/komnas-ham-bandingkan-waktu-cctv-dengan-keterangan-pengacara-keluarga-brigadir-j',
        'info_dict': {
            'id': 'fixme',
            'ext': 'mp4',
        }
    }]
    
    def _real_extract(self, url):
        # TODO: consistent id
        video_id, display_id = self._match_valid_url(url).group('id', 'slug')
        webpage = self._download_webpage(url, display_id)
        
        # the urls can found in json_ld(embedUrl) and iframe(src attr)
        urls = []
        # extracting from json_ld
        json_ld_data = list(self._yield_json_ld(webpage, display_id))
        print(json_ld_data)
        for json_ld in json_ld_data:
            if json_ld.get('embedUrl'):
                urls.append(unescapeHTML(json_ld.get('embedUrl')))
        
        # extracting from iframe
        # TODO: better regex
        iframe_url = self._search_regex(
            r'<iframe[^>]\s*[\w="\s]+\bsrc=\'(?P<iframe_src>[^\']+)',
            webpage, 'iframe_url', default=None, fatal=False, group=('iframe_src'))
        
        if iframe_url:
            urls.append(iframe_url)
        
        # extract dailymotion video id and then redirect to DailymotionIE
        dmplayer_video_id = self._search_regex(
            r'videoId\s*=\s*"(?P<id>[^"]+)', webpage, 'dmplayer_video_id', default=None, 
            fatal=False, group=('id'))
        
        # TODO: return from iframe (not implemented until 4307 merged)
        video_url = urls[0] if len(urls) >= 1 else f'https://www.dailymotion.com/video/{dmplayer_video_id}'
        return self.url_result(video_url, video_id=video_id, video_title=self._html_search_meta(['og:title', 'twitter:title'], webpage),
            description=self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage),
            thumbnail=self._html_search_meta(['og:image', 'twitter:image'], webpage),
            tags=str_or_none(self._html_search_meta(['keywords', 'content_tag'], webpage), '').split(',') or None,
        )
        

class KompasTVLiveIE(KompasTVBaseIE):
    _VALID_URL = r'https?://www\.kompas\.tv/(?P<id>live(\d+|report)?|breakingnews)'
    _TESTS = [{
        'url': 'https://www.kompas.tv/live',
        'info_dict': {
            'id': 'kD9l8sWXqRfBh0rvk82',
            'ext': 'mp4',
            'uploader': 'KompasTV',
            'uploader_url': 'https://www.dailymotion.com/kompastv',
            'title': r're:Live Streaming - Kompas TV \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'description': 'md5:e87a1f75bc75a10a93599f556ed5e319',
            'live_status': 'is_live',
            'uploader_id': 'x1vv20s',
            'timestamp': 1532416221,
            'upload_date': '20180724',
        }
    }]
    
    def _real_extract(self, url):
        slug = self._match_id(url)
        webpage = self._download_webpage(url, slug)
        
        video_id = self._search_regex(
            r'privateVideoId\s*=\s*"(?P<id>[^"]+)',webpage, 'privateVideoId')
        
        video_metadata = self._extract_formats_from_dailymotion_id(webpage, video_id, slug)
        
        return {
            **video_metadata,
            'live_status': 'is_live',
        }
        