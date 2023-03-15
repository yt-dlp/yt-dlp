from .common import InfoExtractor
from ..utils import (
    mimetype2ext,
    parse_duration,
    parse_qs,
    str_or_none,
    traverse_obj,
)


class BloggerIE(InfoExtractor):
    IE_NAME = 'blogger.com'
    _VALID_URL = r'https?://(?:www\.)?blogger\.com/video\.g\?token=(?P<id>.+)'
    _EMBED_REGEX = [r'''<iframe[^>]+src=["'](?P<url>(?:https?:)?//(?:www\.)?blogger\.com/video\.g\?token=[^"']+)["']''']
    _TESTS = [{
        'url': 'https://www.blogger.com/video.g?token=AD6v5dzEe9hfcARr5Hlq1WTkYy6t-fXH3BBahVhGvVHe5szdEUBEloSEDSTA8-b111089KbfWuBvTN7fnbxMtymsHhXAXwVvyzHH4Qch2cfLQdGxKQrrEuFpC1amSl_9GuLWODjPgw',
        'md5': 'f1bc19b6ea1b0fd1d81e84ca9ec467ac',
        'info_dict': {
            'id': 'BLOGGER-video-3c740e3a49197e16-796',
            'title': 'BLOGGER-video-3c740e3a49197e16-796',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*',
            'duration': 76.068,
        }
    }]

    def _real_extract(self, url):
        token_id = self._match_id(url)
        webpage = self._download_webpage(url, token_id)
        data_json = self._search_regex(r'var\s+VIDEO_CONFIG\s*=\s*(\{.*)', webpage, 'JSON data')
        data = self._parse_json(data_json.encode('utf-8').decode('unicode_escape'), token_id)
        streams = data['streams']
        formats = [{
            'ext': mimetype2ext(traverse_obj(parse_qs(stream['play_url']), ('mime', 0))),
            'url': stream['play_url'],
            'format_id': str_or_none(stream.get('format_id')),
        } for stream in streams]

        return {
            'id': data.get('iframe_id', token_id),
            'title': data.get('iframe_id', token_id),
            'formats': formats,
            'thumbnail': data.get('thumbnail'),
            'duration': parse_duration(traverse_obj(parse_qs(streams[0]['play_url']), ('dur', 0))),
        }
