import functools
import math

from .common import InfoExtractor
from ..utils import try_call, InAdvancePagedList


class XimalayaBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['CN']


class XimalayaIE(XimalayaBaseIE):
    IE_NAME = 'ximalaya'
    IE_DESC = '喜马拉雅FM'
    _VALID_URL = r'https?://(?:www\.|m\.)?ximalaya\.com/(:?(?P<uid>\d+)/)?sound/(?P<id>[0-9]+)'
    _TESTS = [
        {
            'url': 'http://www.ximalaya.com/sound/47740352/',
            'info_dict': {
                'id': '47740352',
                'ext': 'm4a',
                'uploader': '小彬彬爱听书',
                'uploader_id': 61425525,
                'uploader_url': 'http://www.ximalaya.com/zhubo/61425525/',
                'title': '261.唐诗三百首.卷八.送孟浩然之广陵.李白',
                'description': "contains:《送孟浩然之广陵》\n作者：李白\n故人西辞黄鹤楼，烟花三月下扬州。\n孤帆远影碧空尽，惟见长江天际流。",
                'thumbnail': r're:^https?://.*\.jpg',
                'thumbnails': [
                    {
                        'name': 'cover_url',
                        'url': r're:^https?://.*\.jpg',
                    },
                    {
                        'name': 'cover_url_142',
                        'url': r're:^https?://.*\.jpg',
                        'width': 180,
                        'height': 180
                    }
                ],
                'categories': ['人文'],
                'duration': 93,
                'view_count': int,
                'like_count': int,
            }
        },
        {
            'url': 'http://m.ximalaya.com/61425525/sound/47740352/',
            'info_dict': {
                'id': '47740352',
                'ext': 'm4a',
                'uploader': '小彬彬爱听书',
                'uploader_id': 61425525,
                'uploader_url': 'http://www.ximalaya.com/zhubo/61425525/',
                'title': '261.唐诗三百首.卷八.送孟浩然之广陵.李白',
                'description': "contains:《送孟浩然之广陵》\n作者：李白\n故人西辞黄鹤楼，烟花三月下扬州。\n孤帆远影碧空尽，惟见长江天际流。",
                'thumbnail': r're:^https?://.*\.jpg',
                'thumbnails': [
                    {
                        'name': 'cover_url',
                        'url': r're:^https?://.*\.jpg',
                    },
                    {
                        'name': 'cover_url_142',
                        'url': r're:^https?://.*\.jpg',
                        'width': 180,
                        'height': 180
                    }
                ],
                'categories': ['人文'],
                'duration': 93,
                'view_count': int,
                'like_count': int,
            }
        }
    ]

    def _real_extract(self, url):
        scheme = 'https' if url.startswith('https') else 'http'

        audio_id = self._match_id(url)
        audio_info_file = '%s://m.ximalaya.com/tracks/%s.json' % (scheme, audio_id)
        audio_info = self._download_json(audio_info_file, audio_id,
                                         'Downloading info json %s' % audio_info_file,
                                         'Unable to download info file')

        formats = []
        for bps, k in ((24, 'play_path_32'), (64, 'play_path_64')):
            if audio_info.get(k):
                formats.append({
                    'format_id': f'{bps}K',
                    'url': audio_info[k],
                    'abr': bps,
                    'quality': bps,
                    'vcodec': 'none'
                })

        thumbnails = []
        for k in audio_info.keys():
            # cover pics kyes like: cover_url', 'cover_url_142'
            if k.startswith('cover_url'):
                thumbnail = {'name': k, 'url': audio_info[k]}
                if k == 'cover_url_142':
                    thumbnail['width'] = 180
                    thumbnail['height'] = 180
                thumbnails.append(thumbnail)

        audio_uploader_id = audio_info.get('uid')

        audio_description = try_call(
            lambda: audio_info['intro'].replace('\r\n\r\n\r\n ', '\n').replace('\r\n', '\n'))

        return {
            'id': audio_id,
            'uploader': audio_info.get('nickname'),
            'uploader_id': audio_uploader_id,
            'uploader_url': f'{scheme}://www.ximalaya.com/zhubo/{audio_uploader_id}/' if audio_uploader_id else None,
            'title': audio_info['title'],
            'thumbnails': thumbnails,
            'description': audio_description,
            'categories': list(filter(None, [audio_info.get('category_name')])),
            'duration': audio_info.get('duration'),
            'view_count': audio_info.get('play_count'),
            'like_count': audio_info.get('favorites_count'),
            'formats': formats,
        }


class XimalayaAlbumIE(XimalayaBaseIE):
    IE_NAME = 'ximalaya:album'
    IE_DESC = '喜马拉雅FM 专辑'
    _VALID_URL = r'https?://(?:www\.|m\.)?ximalaya\.com/(?P<uid>[0-9]+)/album/(?P<id>[0-9]+)'
    _TEMPLATE_URL = '%s://www.ximalaya.com/%s/album/%s/'
    _TESTS = [{
        'url': 'http://www.ximalaya.com/61425525/album/5534601/',
        'info_dict': {
            'title': '唐诗三百首（含赏析）',
            'id': '5534601',
        },
        'playlist_mincount': 323,
    }]

    def _real_extract(self, url):
        self.scheme = scheme = 'https' if url.startswith('https') else 'http'

        mobj = self._match_valid_url(url)
        uid, playlist_id = mobj.group('uid'), mobj.group('id')

        webpage = self._download_webpage(self._TEMPLATE_URL % (scheme, uid, playlist_id), playlist_id,
                                         note='Download album page for %s' % playlist_id,
                                         errnote='Unable to get album info')

        title = self._html_search_regex(r'<h1 class="title dC_">([^<]+)</h1>',
                                        webpage, 'title', fatal=False)

        first_page = self._fetch_page(playlist_id, 0)
        page_count = math.ceil(first_page['trackTotalCount'] / first_page['pageSize'])

        entries = (self._get_entries(first_page)
                   + list(InAdvancePagedList(
                          lambda idx: self._get_entries(self._fetch_page(playlist_id, idx + 1)),
                          page_count, first_page['pageSize']))
                   )

        return self.playlist_result(entries, playlist_id, title)

    def _fetch_page(self, playlist_id, page_idx):
        # page_idx in url should start from 1
        url = f'https://www.ximalaya.com/revision/album/v1/getTracksList?albumId={playlist_id}&pageNum={page_idx + 1}&sort=1'
        data = self._download_json(url, playlist_id, note=f'get tracksList page {page_idx}')['data']
        return data

    def _get_entries(self, page_data):
        return [self.url_result('%s://www.ximalaya.com%s' % (self.scheme, e['url']),
                                XimalayaIE.ie_key(), e['trackId'], e['title'])
                for e in page_data['tracks']]
