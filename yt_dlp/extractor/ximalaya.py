# coding: utf-8

from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor


class XimalayaBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['CN']


class XimalayaIE(XimalayaBaseIE):
    IE_NAME = 'ximalaya'
    IE_DESC = '喜马拉雅FM'
    _VALID_URL = r'https?://(?:www\.|m\.)?ximalaya\.com/(?P<uid>[0-9]+)/sound/(?P<id>[0-9]+)'
    _USER_URL_FORMAT = '%s://www.ximalaya.com/zhubo/%i/'
    _TESTS = [
        {
            'url': 'http://www.ximalaya.com/61425525/sound/47740352/',
            'info_dict': {
                'id': '47740352',
                'ext': 'm4a',
                'uploader': '小彬彬爱听书',
                'uploader_id': 61425525,
                'uploader_url': 'http://www.ximalaya.com/zhubo/61425525/',
                'title': '261.唐诗三百首.卷八.送孟浩然之广陵.李白',
                'description': "contains:《送孟浩然之广陵》\n作者：李白\n故人西辞黄鹤楼，烟花三月下扬州。\n孤帆远影碧空尽，惟见长江天际流。",
                'thumbnails': [
                    {
                        'name': 'cover_url',
                        'url': r're:^https?://.*\.jpg$',
                    },
                    {
                        'name': 'cover_url_142',
                        'url': r're:^https?://.*\.jpg$',
                        'width': 180,
                        'height': 180
                    }
                ],
                'categories': ['renwen', '人文'],
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
                'thumbnails': [
                    {
                        'name': 'cover_url',
                        'url': r're:^https?://.*\.jpg$',
                    },
                    {
                        'name': 'cover_url_142',
                        'url': r're:^https?://.*\.jpg$',
                        'width': 180,
                        'height': 180
                    }
                ],
                'categories': ['renwen', '人文'],
                'duration': 93,
                'view_count': int,
                'like_count': int,
            }
        },
        {
            'url': 'https://www.ximalaya.com/11045267/sound/15705996/',
            'info_dict': {
                'id': '15705996',
                'ext': 'm4a',
                'uploader': '李延隆老师',
                'uploader_id': 11045267,
                'uploader_url': 'https://www.ximalaya.com/zhubo/11045267/',
                'title': 'Lesson 1 Excuse me!',
                'description': "contains:Listen to the tape then answer\xa0this question. Whose handbag is it?\n"
                               "听录音，然后回答问题，这是谁的手袋？",
                'thumbnails': [
                    {
                        'name': 'cover_url',
                        'url': r're:^https?://.*\.jpg$',
                    },
                    {
                        'name': 'cover_url_142',
                        'url': r're:^https?://.*\.jpg$',
                        'width': 180,
                        'height': 180
                    }
                ],
                'categories': ['train', '外语'],
                'duration': 40,
                'view_count': int,
                'like_count': int,
            }
        },
    ]

    def _real_extract(self, url):

        is_m = 'm.ximalaya' in url
        scheme = 'https' if url.startswith('https') else 'http'

        audio_id = self._match_id(url)
        webpage = self._download_webpage(url, audio_id,
                                         note='Download sound page for %s' % audio_id,
                                         errnote='Unable to get sound page')

        audio_info_file = '%s://m.ximalaya.com/tracks/%s.json' % (scheme, audio_id)
        audio_info = self._download_json(audio_info_file, audio_id,
                                         'Downloading info json %s' % audio_info_file,
                                         'Unable to download info file')

        formats = []
        for bps, k in (('24k', 'play_path_32'), ('64k', 'play_path_64')):
            if audio_info.get(k):
                formats.append({
                    'format_id': bps,
                    'url': audio_info[k],
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

        if is_m:
            audio_description = self._html_search_regex(r'(?s)<section\s+class=["\']content[^>]+>(.+?)</section>',
                                                        webpage, 'audio_description', fatal=False)
        else:
            audio_description = self._html_search_regex(r'(?s)<div\s+class=["\']rich_intro[^>]*>(.+?</article>)',
                                                        webpage, 'audio_description', fatal=False)

        if not audio_description:
            audio_description_file = '%s://www.ximalaya.com/sounds/%s/rich_intro' % (scheme, audio_id)
            audio_description = self._download_webpage(audio_description_file, audio_id,
                                                       note='Downloading description file %s' % audio_description_file,
                                                       errnote='Unable to download descrip file',
                                                       fatal=False)
            audio_description = audio_description.strip() if audio_description else None

        return {
            'id': audio_id,
            'uploader': audio_info.get('nickname'),
            'uploader_id': audio_uploader_id,
            'uploader_url': self._USER_URL_FORMAT % (scheme, audio_uploader_id) if audio_uploader_id else None,
            'title': audio_info['title'],
            'thumbnails': thumbnails,
            'description': audio_description,
            'categories': list(filter(None, (audio_info.get('category_name'), audio_info.get('category_title')))),
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
    _BASE_URL_TEMPL = '%s://www.ximalaya.com%s'
    _LIST_VIDEO_RE = r'<a[^>]+?href="(?P<url>/%s/sound/(?P<id>\d+)/?)"[^>]+?title="(?P<title>[^>]+)">'
    _TESTS = [{
        'url': 'http://www.ximalaya.com/61425525/album/5534601/',
        'info_dict': {
            'title': '唐诗三百首（含赏析）',
            'id': '5534601',
        },
        'playlist_count': 312,
    }, {
        'url': 'http://m.ximalaya.com/61425525/album/5534601',
        'info_dict': {
            'title': '唐诗三百首（含赏析）',
            'id': '5534601',
        },
        'playlist_count': 312,
    },
    ]

    def _real_extract(self, url):
        self.scheme = scheme = 'https' if url.startswith('https') else 'http'

        mobj = self._match_valid_url(url)
        uid, playlist_id = mobj.group('uid'), mobj.group('id')

        webpage = self._download_webpage(self._TEMPLATE_URL % (scheme, uid, playlist_id), playlist_id,
                                         note='Download album page for %s' % playlist_id,
                                         errnote='Unable to get album info')

        title = self._html_search_regex(r'detailContent_title[^>]*><h1(?:[^>]+)?>([^<]+)</h1>',
                                        webpage, 'title', fatal=False)

        return self.playlist_result(self._entries(webpage, playlist_id, uid), playlist_id, title)

    def _entries(self, page, playlist_id, uid):
        html = page
        for page_num in itertools.count(1):
            for entry in self._process_page(html, uid):
                yield entry

            next_url = self._search_regex(r'<a\s+href=(["\'])(?P<more>[\S]+)\1[^>]+rel=(["\'])next\3',
                                          html, 'list_next_url', default=None, group='more')
            if not next_url:
                break

            next_full_url = self._BASE_URL_TEMPL % (self.scheme, next_url)
            html = self._download_webpage(next_full_url, playlist_id)

    def _process_page(self, html, uid):
        find_from = html.index('album_soundlist')
        for mobj in re.finditer(self._LIST_VIDEO_RE % uid, html[find_from:]):
            yield self.url_result(self._BASE_URL_TEMPL % (self.scheme, mobj.group('url')),
                                  XimalayaIE.ie_key(),
                                  mobj.group('id'),
                                  mobj.group('title'))
