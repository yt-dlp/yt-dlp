from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    url_or_none,
    urlhandle_detect_ext,
)
from ..utils.traversal import traverse_obj


class BNRNewsIE(InfoExtractor):
    _IE_NAME = 'bnrnews'
    _VALID_URL = r'https?://(?:www\.)?bnrnews\.bg/\w+/post/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://bnrnews.bg/de/post/394279/bulgarien-heute-2-dezember-2025',
        'md5': 'eb5a9d9b47347e703c37270124a14169',
        'info_dict': {
            'id': '394279',
            'title': 'Bulgarien heute – 2. Dezember 2025',
            'thumbnail': 'https://bnrnews.bg/api/media/5168339e-0b81-4d38-9a00-039ef0860035',
            'url': 'https://bnrnews.bg/api/media/9ce1fff8-f2aa-4d87-90b5-01dff966bb9a',
            'ext': 'mp3',
        },
    }]

    def _make_media_api(self, url_path: str) -> str:
        return f'https://bnrnews.bg/api/media/{url_path}'

    def _get_single_audio(self, url, video_id):
        html_page = self._download_webpage(url, video_id, note='Downloading WebPage', errnote='Failed to download page')
        if html_page:
            json_body = self._search_nextjs_data(html_page, video_id)
            if json_body:
                data_field = traverse_obj(json_body, ('props', 'pageProps', 'data'))
                if data_field:
                    audio_info: dict[str, str] = traverse_obj(data_field, ({
                        'id': ('Id', {int_or_none}, {str_or_none}),
                        'title': ('Title', {str}),
                        'thumbnail': ('MainImageInstance', 'Id', {self._make_media_api}, {url_or_none}),
                        'url': ('Sections', lambda _, v: v.get('SectionType') == 'Audio', 'Audio', 'Id', {self._make_media_api}, {url_or_none}, any),
                    }))

                    if traverse_obj(audio_info, 'url'):
                        ext_handle = self._request_webpage(audio_info.get('url'), video_id)
                        ext = urlhandle_detect_ext(ext_handle)
                        if ext == 'unknown_video':
                            raise ExtractorError('error determining file type')
                        audio_info['ext'] = ext
                        return audio_info
                    else:
                        raise ExtractorError("there's no audio to download", expected=True)
                else:
                    raise ExtractorError("the data field is either empty or it doesn't exist")

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._get_single_audio(url, video_id)
