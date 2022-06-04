from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    unified_timestamp,
)


# Livestreams support cannot be implemented as this service uses WebRTC for it
# Support request may still qualify

class FourZeroStudioBaseIE(InfoExtractor):

    @staticmethod
    def _extract_uploader_info(nuxt_data):
        uploader_info = traverse_obj(nuxt_data, ('ssrRefs', lambda _, v: v['__typename'] == 'PublicUser'), get_all=False)
        return {
            'uploader': uploader_info.get('username'),
        }


class FourZeroStudioArchiveIE(FourZeroStudioBaseIE):
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
        nuxt_data = self._search_nuxt_data(webpage, video_id, full_data=True)

        pcb = traverse_obj(nuxt_data, ('ssrRefs', lambda _, v: v['__typename'] == 'PublicCreatorBroadcast'), get_all=False)
        comments = traverse_obj(nuxt_data, ('ssrRefs', ..., lambda _, v: v['__typename'] == 'PublicCreatorBroadcastComment'))

        formats = self._extract_m3u8_formats(
            pcb.get('archiveUrl'), video_id, ext='mp4')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': pcb.get('title'),
            'age_limit': 18 if pcb.get('isAdult') else None,
            'timestamp': unified_timestamp(pcb.get('finishTime')),
            'release_timestamp': unified_timestamp(pcb.get('createdAt')),
            'thumbnails': [{
                'url': pcb.get('thumbnailUrl'),
                # the file seems a PNG file
                'ext': 'png',
            }],
            'formats': formats,
            'comments': comments,
            'comment_count': len(comments),
            'uploader_id': uploader_id,
            **self._extract_uploader_info(nuxt_data),
        }


class FourZeroStudioClipIE(FourZeroStudioBaseIE):
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
        nuxt_data = self._search_nuxt_data(webpage, video_id, full_data=True)

        clip_info = traverse_obj(nuxt_data, ('ssrRefs', lambda _, v: v['__typename'] == 'PublicCreatorArchivedClip'), get_all=False)

        for m in self._parse_html5_media_entries(url, webpage, video_id):
            if 'mp4' in traverse_obj(m, ('formats', ..., 'ext')):
                info = m
                break
        else:
            self.report_warning('Failed to find a desired media element. Falling back to using NUXT data.')
            info = {
                'formats': [{
                    'ext': 'mp4',
                    'url': url,
                } for url in clip_info.get('mediaFiles') if url],
            }
        info.update({
            'id': video_id,
            'title': clip_info.get('clipComment'),
            'timestamp': unified_timestamp(clip_info.get('createdAt')),
            'like_count': clip_info.get('likeCount'),
            'uploader_id': uploader_id,
            **self._extract_uploader_info(nuxt_data),
        })
        return info
