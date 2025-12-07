from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
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
    }, {
        'url': 'https://bnrnews.bg/horizont/post/395494/100-godini-ot-rozhdenieto-na-georgi-partsalev',
        'info_dict': {
            'id': '395494',
            'title': '100 години от рождението на Георги Парцалев',
            'thumbnail': 'https://bnrnews.bg/api/media/ff6874b7-6085-4bb6-8152-039d79faf833',
        },
        'playlist_count': 2,
    }]

    def _get_multiple_audio(self, audio_list: list[dict[str, str]]):
        for audio in audio_list:
            ext_handle = self._request_webpage(audio.get('url'), audio.get('id'), note='getting audio entry info')
            ext = urlhandle_detect_ext(ext_handle)
            if ext == 'unknown_video':
                raise ExtractorError('error determining file type')
            yield {
                'id': audio.get('id'),
                'title': audio.get('title'),
                'url': audio.get('url'),
                'ext': ext,
                'vcodec': 'none',
            }

    def _get_single_audio(self, url, audio_id):
        html_page = self._download_webpage(url, audio_id, note='Downloading WebPage', errnote='Failed to download page')
        json_body = self._search_nextjs_data(html_page, audio_id)
        data_field = traverse_obj(json_body, ('props', 'pageProps', 'data'))
        if data_field:
            audio_info: dict[str, str] = traverse_obj(data_field, ({
                'id': ('Id', {int_or_none}, {str_or_none}),
                'title': ('Title', {str}),
                'thumbnail': ('MainImageInstance', 'Id', {str}, {lambda x: f'https://bnrnews.bg/api/media/{x}'}),
            }))

            audio_list = traverse_obj(data_field, (
                'Sections',
                lambda _, v: v.get('SectionType') == 'Audio',
                {
                    'id': ('Id', {int_or_none}, {str_or_none}),
                    'title': ('Audio', 'Description', {str}),
                    'url': ('Audio', 'Id', {lambda x: f'https://bnrnews.bg/api/media/{x}'}),
                },
                all,
            ))
            if audio_list:
                if len(audio_list) > 1:
                    return self.playlist_result(self._get_multiple_audio(audio_list),
                                                playlist_id=audio_id,
                                                playlist_title=audio_info.get('title'), thumbnail=audio_info.get('thumbnail'),
                                                )
                else:
                    ext_handle = self._request_webpage(audio_list[0].get('url'), audio_id, note='getting audio info')
                    ext = urlhandle_detect_ext(ext_handle)
                    if ext == 'unknown_video':
                        raise ExtractorError('error determining file type')
                    audio_info['ext'] = ext
                    audio_info['url'] = audio_list[0].get('url')
                    return audio_info
            raise ExtractorError("there's no audio to download", expected=True)

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        return self._get_single_audio(url, audio_id)
