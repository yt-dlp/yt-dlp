import re

from .common import InfoExtractor
from ..utils import ExtractorError, clean_html, int_or_none, try_get, unified_strdate
from ..compat import compat_str


class DamtomoBaseIE(InfoExtractor):
    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage, handle = self._download_webpage_handle(self._WEBPAGE_URL_TMPL % video_id, video_id, encoding='sjis')

        if handle.url == 'https://www.clubdam.com/sorry/':
            raise ExtractorError('You are rate-limited. Try again later.', expected=True)
        if '<h2>予期せぬエラーが発生しました。</h2>' in webpage:
            raise ExtractorError('There is an error on server-side. Try again later.', expected=True)

        description = self._search_regex(r'(?m)<div id="public_comment">\s*<p>\s*([^<]*?)\s*</p>', webpage, 'description', default=None)
        uploader_id = self._search_regex(r'<a href="https://www\.clubdam\.com/app/damtomo/member/info/Profile\.do\?damtomoId=([^"]+)"', webpage, 'uploader_id', default=None)

        data_dict = {
            mobj.group('class'): re.sub(r'\s+', ' ', clean_html(mobj.group('value')))
            for mobj in re.finditer(r'(?s)<(p|div)\s+class="(?P<class>[^" ]+?)">(?P<value>.+?)</\1>', webpage)}

        # since videos do not have title, give the name of song instead
        data_dict['user_name'] = re.sub(r'\s*さん\s*$', '', data_dict['user_name'])
        title = data_dict.get('song_title')

        stream_tree = self._download_xml(
            self._DKML_XML_URL % video_id, video_id, note='Requesting stream information', encoding='sjis',
            # doing this has no problem since there is no character outside ASCII,
            # and never likely to happen in the future
            transform_source=lambda x: re.sub(r'\s*encoding="[^"]+?"', '', x))
        m3u8_url = try_get(stream_tree, lambda x: x.find(
            './/d:streamingUrl', {'d': self._DKML_XML_NS}).text.strip(), compat_str)
        if not m3u8_url:
            raise ExtractorError('Failed to obtain m3u8 URL')
        formats = self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4')

        return {
            'id': video_id,
            'title': title,
            'uploader_id': uploader_id,
            'description': description,
            'uploader': data_dict.get('user_name'),
            'upload_date': unified_strdate(self._search_regex(r'(\d{4}/\d{2}/\d{2})', data_dict.get('date'), 'upload_date', default=None)),
            'view_count': int_or_none(self._search_regex(r'(\d+)', data_dict['audience'], 'view_count', default=None)),
            'like_count': int_or_none(self._search_regex(r'(\d+)', data_dict['nice'], 'like_count', default=None)),
            'track': title,
            'artist': data_dict.get('song_artist'),
            'formats': formats,
        }


class DamtomoVideoIE(DamtomoBaseIE):
    IE_NAME = 'damtomo:video'
    _VALID_URL = r'https?://(?:www\.)?clubdam\.com/app/damtomo/(?:SP/)?karaokeMovie/StreamingDkm\.do\?karaokeMovieId=(?P<id>\d+)'
    _WEBPAGE_URL_TMPL = 'https://www.clubdam.com/app/damtomo/karaokeMovie/StreamingDkm.do?karaokeMovieId=%s'
    _DKML_XML_URL = 'https://www.clubdam.com/app/damtomo/karaokeMovie/GetStreamingDkmUrlXML.do?movieSelectFlg=2&karaokeMovieId=%s'
    _DKML_XML_NS = 'https://www.clubdam.com/app/damtomo/karaokeMovie/GetStreamingDkmUrlXML'
    _TESTS = [{
        'url': 'https://www.clubdam.com/app/damtomo/karaokeMovie/StreamingDkm.do?karaokeMovieId=2414316',
        'info_dict': {
            'id': '2414316',
            'title': 'Get Wild',
            'uploader': 'Ｋドロン',
            'uploader_id': 'ODk5NTQwMzQ',
            'track': 'Get Wild',
            'artist': 'TM NETWORK(TMN)',
            'upload_date': '20201226',
        }
    }]


class DamtomoRecordIE(DamtomoBaseIE):
    IE_NAME = 'damtomo:record'
    _VALID_URL = r'https?://(?:www\.)?clubdam\.com/app/damtomo/(?:SP/)?karaokePost/StreamingKrk\.do\?karaokeContributeId=(?P<id>\d+)'
    _WEBPAGE_URL_TMPL = 'https://www.clubdam.com/app/damtomo/karaokePost/StreamingKrk.do?karaokeContributeId=%s'
    _DKML_XML_URL = 'https://www.clubdam.com/app/damtomo/karaokePost/GetStreamingKrkUrlXML.do?karaokeContributeId=%s'
    _DKML_XML_NS = 'https://www.clubdam.com/app/damtomo/karaokePost/GetStreamingKrkUrlXML'
    _TESTS = [{
        'url': 'https://www.clubdam.com/app/damtomo/karaokePost/StreamingKrk.do?karaokeContributeId=27376862',
        'info_dict': {
            'id': '27376862',
            'title': 'イカSUMMER [良音]',
            'uploader': 'ＮＡＮＡ',
            'uploader_id': 'MzAyMDExNTY',
            'upload_date': '20210721',
            'view_count': 4,
            'like_count': 1,
            'track': 'イカSUMMER [良音]',
            'artist': 'ORANGE RANGE',
        }
    }, {
        'url': 'https://www.clubdam.com/app/damtomo/karaokePost/StreamingKrk.do?karaokeContributeId=27489418',
        'info_dict': {
            'id': '27489418',
            'title': '心みだれて〜say it with flowers〜(生音)',
            'uploader_id': 'NjI1MjI2MjU',
            'description': 'やっぱりキーを下げて正解だった感じ。リベンジ成功ということで。',
            'uploader': '箱の「中の人」',
            'upload_date': '20210815',
            'view_count': 5,
            'like_count': 3,
            'track': '心みだれて〜say it with flowers〜(生音)',
            'artist': '小林明子',
        }
    }]
