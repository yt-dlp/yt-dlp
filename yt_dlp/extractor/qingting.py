import math
from .common import InfoExtractor
from ..utils import traverse_obj, InAdvancePagedList
from lxml import html


class QingTingBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['CN']


class QingTingIE(QingTingBaseIE):
    _VALID_URL = r'https?://(?:www\.|m\.)?(?:qingting\.fm|qtfm\.cn)/v?channels/(?P<channel>\d+)/programs/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.qingting.fm/channels/378005/programs/22257411/',
        'md5': '47e6a94f4e621ed832c316fd1888fb3c',
        'info_dict': {
            'id': '22257411',
            'title': '用了十年才修改，谁在乎教科书？',
            'channel_id': '378005',
            'channel': '睡前消息',
            'uploader': '马督工',
            'ext': 'm4a',
        }
    }, {
        'url': 'https://m.qtfm.cn/vchannels/378005/programs/23023573/',
        'md5': '2703120b6abe63b5fa90b975a58f4c0e',
        'info_dict': {
            'id': '23023573',
            'title': '【睡前消息488】重庆山火之后，有图≠真相',
            'channel_id': '378005',
            'channel': '睡前消息',
            'uploader': '马督工',
            'ext': 'm4a',
        }
    }]

    def _real_extract(self, url):
        channel_id, pid = self._match_valid_url(url).group('channel', 'id')
        webpage = self._download_webpage(
            f'https://m.qtfm.cn/vchannels/{channel_id}/programs/{pid}/', pid)
        info = self._search_json(r'window\.__initStores\s*=', webpage, 'program info', pid)
        return {
            'id': pid,
            'title': traverse_obj(info, ('ProgramStore', 'programInfo', 'title')),
            'channel_id': channel_id,
            'channel': traverse_obj(info, ('ProgramStore', 'channelInfo', 'title')),
            'uploader': traverse_obj(info, ('ProgramStore', 'podcasterInfo', 'podcaster', 'nickname')),
            'url': traverse_obj(info, ('ProgramStore', 'programInfo', 'audioUrl')),
            'vcodec': 'none',
            'acodec': 'm4a',
            'ext': 'm4a',
        }


class QingTingChannelIE(QingTingBaseIE):
    IE_NAME = 'QingTing:Channel'
    IE_DESC = '蜻蜓FM 专辑'
    _VALID_URL = r'https?://(?:www\.|m\.)?(?:qingting\.fm|qtfm\.cn)/v?channels/(?P<id>\d+)/'
    _TESTS = [{
        'url': 'https://www.qingting.fm/channels/324131',
        'info_dict': {
            'title': '小学篇',
            'id': '324131',
        },
        'playlist_mincount': 75,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        first_page = self._fetch_page(playlist_id, 1)
        web_tree = html.fromstring(first_page)
        # use xpath //*[@id="app"]/div/div[3]/div[2]/div[1]/div[1]/div[1]/div[3]/h1
        # to find title.
        title = str(
            web_tree.xpath('//*[@id="app"]/div/div[3]/div[2]/div[1]/div[1]/div[1]/div[3]/h1/text()')[0])
        # use xpath //*[@id="app"]/div/div[3]/div[2]/div[1]/div[2]/div/div[1]/span[2]
        # to find total audio count.
        total_audio_count = int(
            web_tree.xpath('//*[@id="app"]/div/div[3]/div[2]/div[1]/div[2]/div/div[1]/span[2]/text()')[1])
        page_count = math.ceil(total_audio_count / 30)

        entries = InAdvancePagedList(
            lambda idx: self._get_entries(self._fetch_page(playlist_id, idx + 1) if idx else first_page),
            page_count, 30)

        return self.playlist_result(entries, playlist_id, title)

    def _fetch_page(self, playlist_id, page_idx):
        return self._download_webpage(
            f'https://www.qingting.fm/channels/{playlist_id}/{page_idx}',
            playlist_id,
            note='Download channel page for %s' % playlist_id,
            errnote='Unable to get channel info')

    def _get_entries(self, page_data):
        page_data_tree = html.fromstring(page_data)
        # use xpath //*[@id="app"]/div/div[3]/div[2]/div[1]/div[2]/div/ul/li
        # to find all programs, which are html <a> tags.
        programs = page_data_tree.xpath('//*[@id="app"]/div/div[3]/div[2]/div[1]/div[2]/div/ul/li//a')
        for program in programs:
            program_url = f'https://www.qingting.fm{program.xpath("@href")[0]}'
            program_id = program.xpath("@href")[0].split('/')[-1]
            program_title = str(program.xpath('p/text()')[0])
            yield self.url_result(program_url, QingTingIE, program_id, program_title)
