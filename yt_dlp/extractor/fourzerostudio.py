from .common import InfoExtractor
from ..utils import traverse_obj, unified_timestamp


class FourZeroStudioArchiveIE(InfoExtractor):
    _VALID_URL = r'https?://0000\.studio/(?P<uploader_id>[^/]+)/broadcasts/(?P<id>[^/]+)/archive'
    IE_NAME = '0000studio:archive'
    _TESTS = [{
        'url': 'https://0000.studio/mumeijiten/broadcasts/1290f433-fce0-4909-a24a-5f7df09665dc/archive',
        'info_dict': {
            'id': '1290f433-fce0-4909-a24a-5f7df09665dc',
            'title': 'noteで『canape』様へのファンレターを執筆します。（数秘術その2）',
            'timestamp': 1653802534,
            'release_timestamp': 1653796604,
            'thumbnails': 'count:1',
            'comments': 'count:7',
            'uploader': '『中崎雄心』の執務室。',
            'uploader_id': 'mumeijiten',
        }
    }]

    def _real_extract(self, url):
        video_id, uploader_id = self._match_valid_url(url).group('id', 'uploader_id')
        webpage = self._download_webpage(url, video_id)
        nuxt_data = self._search_nuxt_data(webpage, video_id, traverse=None)

        pcb = traverse_obj(nuxt_data, ('ssrRefs', lambda _, v: v['__typename'] == 'PublicCreatorBroadcast'), get_all=False)
        uploader_internal_id = traverse_obj(nuxt_data, (
            'ssrRefs', lambda _, v: v['__typename'] == 'PublicUser', 'id'), get_all=False)

        formats, subs = self._extract_m3u8_formats_and_subtitles(pcb['archiveUrl'], video_id, ext='mp4')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': pcb.get('title'),
            'age_limit': 18 if pcb.get('isAdult') else None,
            'timestamp': unified_timestamp(pcb.get('finishTime')),
            'release_timestamp': unified_timestamp(pcb.get('createdAt')),
            'thumbnails': [{
                'url': pcb['thumbnailUrl'],
                'ext': 'png',
            }] if pcb.get('thumbnailUrl') else None,
            'formats': formats,
            'subtitles': subs,
            'comments': [{
                'author': c.get('username'),
                'author_id': c.get('postedUserId'),
                'author_thumbnail': c.get('userThumbnailUrl'),
                'id': c.get('id'),
                'text': c.get('body'),
                'timestamp': unified_timestamp(c.get('createdAt')),
                'like_count': c.get('likeCount'),
                'is_favorited': c.get('isLikedByOwner'),
                'author_is_uploader': c.get('postedUserId') == uploader_internal_id,
            } for c in traverse_obj(nuxt_data, (
                'ssrRefs', ..., lambda _, v: v['__typename'] == 'PublicCreatorBroadcastComment')) or []],
            'uploader_id': uploader_id,
            'uploader': traverse_obj(nuxt_data, (
                'ssrRefs', lambda _, v: v['__typename'] == 'PublicUser', 'username'), get_all=False),
        }


class FourZeroStudioClipIE(InfoExtractor):
    _VALID_URL = r'https?://0000\.studio/(?P<uploader_id>[^/]+)/archive-clip/(?P<id>[^/]+)'
    IE_NAME = '0000studio:clip'
    _TESTS = [{
        'url': 'https://0000.studio/soeji/archive-clip/e46b0278-24cd-40a8-92e1-b8fc2b21f34f',
        'info_dict': {
            'id': 'e46b0278-24cd-40a8-92e1-b8fc2b21f34f',
            'title': 'わたベーさんからイラスト差し入れいただきました。ありがとうございました！',
            'timestamp': 1652109105,
            'like_count': 1,
            'uploader': 'ソエジマケイタ',
            'uploader_id': 'soeji',
        }
    }]

    def _real_extract(self, url):
        video_id, uploader_id = self._match_valid_url(url).group('id', 'uploader_id')
        webpage = self._download_webpage(url, video_id)
        nuxt_data = self._search_nuxt_data(webpage, video_id, traverse=None)

        clip_info = traverse_obj(nuxt_data, ('ssrRefs', lambda _, v: v['__typename'] == 'PublicCreatorArchivedClip'), get_all=False)

        info = next((
            m for m in self._parse_html5_media_entries(url, webpage, video_id)
            if 'mp4' in traverse_obj(m, ('formats', ..., 'ext'))
        ), None)
        if not info:
            self.report_warning('Failed to find a desired media element. Falling back to using NUXT data.')
            info = {
                'formats': [{
                    'ext': 'mp4',
                    'url': url,
                } for url in clip_info.get('mediaFiles') or [] if url],
            }
        return {
            **info,
            'id': video_id,
            'title': clip_info.get('clipComment'),
            'timestamp': unified_timestamp(clip_info.get('createdAt')),
            'like_count': clip_info.get('likeCount'),
            'uploader_id': uploader_id,
            'uploader': traverse_obj(nuxt_data, (
                'ssrRefs', lambda _, v: v['__typename'] == 'PublicUser', 'username'), get_all=False),
        }
