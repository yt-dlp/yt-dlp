from .common import InfoExtractor

from ..utils import traverse_obj


class QingTingIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|m\.)?(?:qingting\.fm|qtfm\.cn)/v?channels/(?P<channel>\d+)/programs/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.qingting.fm/channels/378005/programs/22257411/',
        'md5': '47e6a94f4e621ed832c316fd1888fb3c',
        'info_dict': {
            'id': '22257411',
            'title': '用了十年才修改，谁在乎教科书？',
            'channel_id': '378005',
            'channel_name': '睡前消息',
            'podcaster': '马督工',
            'ext': 'm4a',
        }
    }, {
        'url': 'https://m.qtfm.cn/vchannels/378005/programs/23023573/',
        'md5': '2703120b6abe63b5fa90b975a58f4c0e',
        'info_dict': {
            'id': '23023573',
            'title': '【睡前消息488】重庆山火之后，有图≠真相',
            'channel_id': '378005',
            'channel_name': '睡前消息',
            'podcaster': '马督工',
            'ext': 'm4a',
        }
    }]

    def _real_extract(self, url):
        channel_id, pid = self._match_valid_url(url).groups()
        web_page = self._download_webpage(
            f'https://m.qtfm.cn/vchannels/{channel_id}/programs/{pid}/', pid)
        info = self._search_json(r'window\.__initStores\s*=', web_page, 'program info', pid)
        return {
            'id': pid,
            'title': traverse_obj(info, ('ProgramStore', 'programInfo', 'title')),
            'channel_id': channel_id,
            'channel_name': traverse_obj(info, ('ProgramStore', 'channelInfo', 'title')),
            'podcaster': traverse_obj(info, ('ProgramStore', 'podcasterInfo', 'podcaster', 'nickname')),
            'url': traverse_obj(info, ('ProgramStore', 'programInfo', 'audioUrl')),
            'vcodec': 'none',
            'acodec': 'm4a',
            'ext': 'm4a',
        }
