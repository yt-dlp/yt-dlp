import json
import re

from .common import InfoExtractor
from ..utils import traverse_obj


class TrueIDBaseIE(InfoExtractor):
    def _match_lang(self, pattern, url):
        m = re.match(pattern, url)
        if m:
            return m.group('lang')
        return 'en'

    def _constuct_json(self, video_id, drm_type):
        return {
            'drm': drm_type,
            'cmsId': video_id,
        }

    def _get_auth_key(self):
        return 'Basic NzVlMDFmYjhiODA2ODZkOWVlNjZjYTE3OTZmYTc0YmIyNjcyZjhmODowNjg2ZDllZTY2Y2ExNzk2ZmE3NGJiMjY3MmY4Zjg='

    def _get_cdn_url(self, json_data, video_id, url_type, auth_key=None):
        main_url = 'https://movie.trueid.net/apis/stream'

        if not auth_key:
            auth_key = {
                'Authorization': self._get_auth_key(),
                'Content-Type': 'application/json',
            }

        if url_type == 'm3u8':
            note = 'Downloading m3u8 url'
        elif url_type == 'mpd':
            note = 'Downloading mpd url'

        data = self._download_json(
            main_url,
            video_id,
            headers=auth_key,
            data=json.dumps(json_data).encode(),
            note=note,
        )

        if url_type == 'm3u8':
            cdn_url = traverse_obj(data, ('stream', 'result'))
        elif url_type == 'mpd':
            cdn_url = traverse_obj(data, ('stream', 'streamurl'))

        return cdn_url


class TrueidnetSeriesIE(TrueIDBaseIE):
    _VALID_URL = r'https?://(?:www\.)?movie\.trueid\.net/(?P<lang>[a-z]+-[a-z]+)/series/(?P<series_id>[A-Za-z0-9]+)/(?P<season_id>[A-Za-z0-9]+)/(?P<episode_id>[A-Za-z0-9]+)/(?P<id>[A-Za-z0-9]+)'
    _TESTS = [{
        'url': 'https://movie.trueid.net/th-th/series/4KQG0W161RYB/O4aAzjrgrK84/9mrb47JvQAzm/W3Q09QmpzZD1',
        'info_dict': {
            'id': 'W3Q09QmpzZD1',
            'ext': 'mp4',
            'title': 'EP.01 | ล่าสไลม์มา 300 ปีรู้ตัวอีกทีก็เลเวล MAX ซะแล้ว ซีซัน 2 (ดูพากย์ไทยไม่มีโฆษณา)',
            'description': 'md5:d5a65a3276a7f67e8bbb3e2eec11ee62',
            'thumbnail': 'https://cms.dmpcdn.com/movie/2025/04/02/985cba50-0f8b-11f0-974a-f523c0a0f1ce_webp_original.webp',
        },
    }, {
        'url': 'https://movie.trueid.net/th-th/series/5ppEm0kdMX5/GpWq1QW991aZ/PobKPXALWN87/82ok9EKkNeQ',
        'info_dict': {
            'id': '82ok9EKkNeQ',
            'ext': 'mp4',
            'title': 'EP.01 | The Innovation Startup',
            'description': 'md5:33ff6a321fc75e5bb81e4d340da16a67',
            'thumbnail': 'https://cms.dmpcdn.com/movie/2018/03/29/789768e4-afca-4555-8470-af20c0738e0d.png',
        },
    }, {
        'url': 'https://movie.trueid.net/th-th/series/VPmGdma9EqN1/rq8WWxbPLaPD/vkv44vrgmYoR/b2XeMDrdZLwV',
        'info_dict': {
            'id': 'b2XeMDrdZLwV',
            'ext': 'mp4',
            'title': 'EP.001 คดีฆาตกรรมบนรถไฟเหาะ | ยอดนักสืบจิ๋วโคนัน เดอะซีรีส์ ซีซัน 1',
            'description': 'md5:8557d964105d4fbdca812b648a5a0402',
            'thumbnail': 'https://cms.dmpcdn.com/movie/2022/03/16/bf7422b0-a4e8-11ec-837d-3f3f1e297725_webp_original.jpg',
        },
    },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        aes_json = self._constuct_json(video_id, 'aes')
        m3u8_url = self._get_cdn_url(aes_json, video_id, 'm3u8')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, ext='mp4')

        # workaround for some vtt stream that broke webvtt parser
        wv_json = self._constuct_json(video_id, 'wv')
        mpd_url = self._get_cdn_url(wv_json, video_id, 'mpd')
        wv_vi, wv_sub = self._extract_mpd_formats_and_subtitles(mpd_url, video_id)
        for lang, subs in (wv_sub or {}).items():
            for sub in subs:
                sub['ext'] = 'ttml'  # override ext mp4

            subtitles[lang].extend(subs)

        formats.extend(wv_vi)

        return {
            'id': video_id,
            'title': self._html_search_regex(r'<h1\s*class="title"[^>]*>([^<]+)', webpage, 'title')
            or self._html_search_meta('sm:title', webpage, 'title'),
            'formats': formats,
            'subtitles': subtitles,
            'description': self._html_search_regex(
                r'<div\s*class="synopsis mb-2"><p[^>]*>([^<]+)',
                webpage, 'description'),
            'thumbnail': self._html_search_meta(
                ['sm:thumbnail', 'thumbnail', 'twitter:image'],
                webpage, 'thumbnail', default=None, fatal=False),
        }


class TrueidnetMovieIE(TrueIDBaseIE):
    _VALID_URL = r'https?://(?:www\.)?movie\.trueid\.net/(?P<lang>[a-z]+-[a-z]+)/movie/(?P<id>[A-Za-z0-9]+)'
    _TESTS = [{
        'url': 'https://movie.trueid.net/th-th/movie/bwDM154PDR2V',
        'info_dict': {
            'id': 'bwDM154PDR2V',
            'ext': 'mp4',
            'title': 'ห่วงใยทุกลมหายใจ',
            'description': 'โครงการเข็มวันอานันทมหิดลปีนี้ มุ่งช่วยเหลือผู้ป่วยโรคทางเดินหายใจเรื้อรังและโรคมะเร็งปอด ซึ่งส่งผลกระทบต่อประชาชนจำนวนมากในปัจจุบัน',
            'thumbnail': 'https://cms.dmpcdn.com/movie/2025/05/16/ced485a0-3267-11f0-b639-732615024a50_webp_original.webp',
        },
    }, {
        'url': 'https://movie.trueid.net/th-th/movie/B4Q3B89QAgNk',
        'info_dict': {
            'id': 'B4Q3B89QAgNk',
            'ext': 'mp4',
            'title': 'หมา เป้าหมาย และเด็กชายของผม 2',
            'description': 'สุนัขค้นหาความหมายของชีวิตผ่านการทำความรู้จักกับมนุษย์ทุกคนที่เขาเคยพบเจอมา',
            'thumbnail': 'https://cms.dmpcdn.com/movie/2025/03/14/ae112d80-00b4-11f0-8c7e-e948721548d4_webp_original.webp',

        },
    }, {
        'url': 'https://movie.trueid.net/th-th/movie/al4pKJLKzw8l',
        'info_dict': {
            'id': 'al4pKJLKzw8l',
            'ext': 'mp4',
            'title': 'เมล็ดพันธุ์แห่งความยั่งยืน',
            'description': 'การทำเพื่อผู้อื่นด้วยใจ สร้างคุณค่าได้ไม่มีวันหมดอายุ? ร่วมเดินทางหาคำตอบไปกับเมล็ดพันธุ์แห่งความดี ที่จะสร้างคุณค่าและความสุขต่อไปได้อย่างไม่รู้จบ เพื่อพรุ่งนี้ของเราทุกคน',
            'thumbnail': 'https://cms.dmpcdn.com/movie/2024/02/15/ef0218c0-cbe7-11ee-bf8c-87c600a5197d_webp_original.webp',

        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        aes_json = self._constuct_json(video_id, 'aes')
        m3u8_url = self._get_cdn_url(aes_json, video_id, 'm3u8')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, ext='mp4')

        # workaround for some vtt stream that broke webvtt parser
        wv_json = self._constuct_json(video_id, 'wv')
        mpd_url = self._get_cdn_url(wv_json, video_id, 'mpd')
        wv_vi, wv_sub = self._extract_mpd_formats_and_subtitles(mpd_url, video_id)
        for lang, subs in (wv_sub or {}).items():
            for sub in subs:
                sub['ext'] = 'ttml'  # override ext mp4

            subtitles[lang].extend(subs)

        formats.extend(wv_vi)

        return {
            'id': video_id,
            'title': self._html_search_regex(r'<h1\s*class="title"[^>]*>([^<]+)', webpage, 'title')
            or self._html_search_meta('sm:title', webpage, 'title'),
            'formats': formats,
            'subtitles': subtitles,
            'description': self._html_search_regex(
                r'<div\s*class="synopsis mb-2"><p[^>]*>([^<]+)',
                webpage, 'description'),
            'thumbnail': self._html_search_meta(
                ['sm:thumbnail', 'thumbnail', 'twitter:image'],
                webpage, 'thumbnail', default=None, fatal=False),
        }
