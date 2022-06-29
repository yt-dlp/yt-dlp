from .common import InfoExtractor
from ..utils import determine_ext


class RTLLuBaseIE(InfoExtractor):
    _MEDIA_REGEX = {
        'video': r'<rtl-player\s*poster\s*=\s*\"(?:[\"\w\.://-]+)\"\s*(title\s*=\s*(?:[\"\w\.-]+))?\s*(type\s*=\s*\"(?:\w+)\")?\s*(channelname\s*=\s*\"(?:\w+)\")?\s*hls\s*=\s*\"(?P<media_url>[\w\.\:/-]+)\"',
        'audio': r'<rtl-audioplayer\s*src\s*=\s*\"(?P<media_url>[\w\.\:/-]+)\"',
    }

    def get_media_url(self, webpage, video_id, media_type):
        media_url = self._search_regex(
            self._MEDIA_REGEX[media_type], webpage, 'media_url', group=('media_url'), 
            default=None, fatal=False)
            
        return media_url
    
    def get_format(self, webpage, video_id):
        video_url, audio_url = self.get_media_url(webpage, video_id, 'video'), self.get_media_url(webpage, video_id, 'audio')
        
        formats, subtitles = [], {}
        if video_url is not None:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id)
        if audio_url is not None:
            audio_format = {'url': audio_url, 'ext': 'mp3'}
            formats.append(audio_format)
        
        return formats, subtitles

class RTLLuTeleVODIE(RTLLuBaseIE):
    IE_NAME = 'rtl.lu:tele-vod'
    _VALID_URL = r'https?://(?:www.)?rtl\.lu/(tele/(?P<slug>[\w-]+)/v/|video/)(?P<id>\d+)(\.html)?'
    _TESTS = [{
        'url': 'https://www.rtl.lu/tele/de-journal-vun-der-tele/v/3266757.html',
        'info_dict': {
            'id': '3266757',
            'title': 'Informatiounsversammlung Héichwaasser',
            'ext': 'mp4',
            'thumbnail': 'https://replay-assets.rtl.lu/2021/11/16/d3647fc4-470d-11ec-adc2-3a00abd6e90f_00008.jpg',
            'description': 'md5:b1db974408cc858c9fd241812e4a2a14',
        }
    }, {
        'url': 'https://www.rtl.lu/video/3295215',
        'info_dict': {
            'id': '3295215',
            'title': 'Kulturassisen iwwer d\'Bestandsopnam vum Lëtzebuerger Konscht',
            'ext': 'mp4',
            'thumbnail': 'https://replay-assets.rtl.lu/2022/06/28/0000_3295215_0000.jpg',
            'description': 'md5:85bcd4e0490aa6ec969d9bf16927437b',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats, subtitles = self.get_format(webpage, video_id)
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': self._og_search_thumbnail(webpage),
        }


class RTLLuArticleIE(RTLLuBaseIE):
    IE_NAME = 'rtl.lu:article'
    _VALID_URL = r'https?://www\.rtl\.lu/(?:\w+)/(?:\w+)/a/(?P<id>\d+)\.html'
    _TESTS = [{
        # Audio-only 
        'url': 'https://www.rtl.lu/sport/news/a/1934360.html',
        'info_dict': {
            'id': '1934360',
            'ext': 'mp3',
            'thumbnail': 'https://static.rtl.lu/rtl2008.lu/nt/p/2022/06/28/19/e4b37d66ddf00bab4c45617b91a5bb9b.jpeg',
            'description': 'md5:5eab4a2a911c1fff7efc1682a38f9ef7',
            'title': 'md5:40aa85f135578fbd549d3c9370321f99',
        }
    }, {
        # Video-only
        'url': 'https://www.rtl.lu/kultur/news/a/1931683.html',
        'info_dict': {
            'id': '1931683',
            'ext': 'mp4',
            'description': 'md5:ad39b36e0039a109384b5996c373e835',
            'title': 'Esch2022: Suessem ass déi nei "Gemeng vum Mount"',
            'thumbnail': 'https://static.rtl.lu/rtl2008.lu/nt/p/2022/06/22/16/7f9d5141c40733ffd0054d1a4d01819e.jpeg',
        }
    }]
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        
        # TODO: extract comment from https://www.rtl.lu/comments?status=1&order=desc&context=news|article|<video_id>
        # we can context from <rtl-comments context=<context> in webpage
        formats, subtitles = self.get_format(webpage, video_id)
        self._sort_formats(formats)
        
        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': self._og_search_thumbnail(webpage),
        }


class RTLLuTeleLiveIE(RTLLuBaseIE):
    _VALID_URL = 'https://www.rtl.lu/tele/live'
    _TESTS = [{
        'url': 'https://www.rtl.lu/tele/live',
        'info_dict': {
            'id': 'Tele:live',
            'ext': 'mp4',
            'live_status': 'is_live',
            'title': 're:RTL - Télé LIVE \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            
        }
    }]
    
    def _real_extract(self, url):
        # live video didn't have id
        video_id = 'Tele:live'
        webpage = self._download_webpage(url, video_id)
        
        # actually the live version has mpd version in <rtl-player ... dash=<mpd_link>,
        # but ffmpeg have problem with live dash
        formats, subtitles = self.get_format(webpage, video_id)
        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'live_status': 'is_live',
        }
        
        