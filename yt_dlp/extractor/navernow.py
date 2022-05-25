from .naver import NaverBaseIE
from ..utils import (
    ExtractorError,
    unified_strdate,
    unified_timestamp,
    merge_dicts,
)
from ..compat import (
    compat_urllib_parse_urlparse,
    compat_parse_qs,
)


class NaverNowIE(NaverBaseIE):
    IE_NAME = 'navernow'
    _VALID_URL = r'https?://now\.naver\.com/show/(?P<id>[0-9]+)'
    _PAGE_SIZE = 30
    _TESTS = [{
        'url': 'https://now.naver.com/show/4759?shareReplayId=5901#replay=',
        'info_dict': {
            'id': '4759-5901',
            'title': '아이키X노제\r\n💖꽁냥꽁냥💖(1)',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1650369600,
            'upload_date': '20220419',
            'uploader_id': 'now',
            'uploader': '',
            'uploader_url': '',
            'view_count': int,
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        }
    }, {
        'url': 'https://now.naver.com/show/4759?shareHightlight=1078#highlight=',
        'info_dict': {
            'id': '4759-1078',
            'title': '아이키: 나 리정한테 흔들렸어,,, 질투 폭발하는 노제 여보😾 [아이키의 떰즈업]ㅣ네이버 NOW.',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg',
            'upload_date': '20220504',
            'timestamp': 1651648042,
            'uploader_id': 'now',
            'uploader': '',
            'uploader_url': '',
            'view_count': int,
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        },
    }, {
        'url': 'https://now.naver.com/show/4759',
        'info_dict': {
            'id': '4759',
            'title': '아이키의 떰즈업',
        },
        'playlist_mincount': 48
    }, {
        'url': 'https://now.naver.com/show/4759?shareReplayId=5901#replay',
        'info_dict': {
            'id': '4759',
            'title': '아이키의 떰즈업',
        },
        'playlist_mincount': 48,
        'params': {
            'noplaylist': False,
        }
    }, {
        'url': 'https://now.naver.com/show/4759?shareHightlight=1078#highlight=',
        'info_dict': {
            'id': '4759',
            'title': '아이키의 떰즈업',
        },
        'playlist_mincount': 48,
        'params': {
            'noplaylist': False,
        }
    }]

    def _call_api(self, path, video_id, query=None, note=None):
        if note is None:
            note = 'Downloading JSON metadata'
        return self._download_json(
            'https://apis.naver.com/now_web/nowcms-api-xhmac/cms/v1' + path, video_id,
            note, query=query)

    def _extract_replay(self, show_id, replay_id):
        vod_info = self._call_api(
            f'/shows/{show_id}/vod/{replay_id}', replay_id,
            note=f'Downloading JSON metadata for replay {show_id}-{replay_id}')
        in_key = self._call_api(
            f'/shows/{show_id}/vod/{replay_id}/inkey', replay_id,
            note=f'Downloading JSON inkey for replay {show_id}-{replay_id}')['inKey']
        return merge_dicts(
            {
                'id': f'{show_id}-{replay_id}',
                'title': vod_info.get('episode', {}).get('title'),
                'upload_date': unified_strdate(vod_info.get('episode', {}).get('start_time')),
                'timestamp': unified_timestamp(vod_info.get('episode', {}).get('start_time')),
                'thumbnail': vod_info.get('thumbnail_image_url'),
            },
            self._extract_video_info(replay_id, vod_info['video_id'], in_key))

    def _extract_highlight(self, show_id, highlight_id, highlights=None):
        page = 0
        while True:
            highlights_videos = highlights or self._call_api(
                f'/shows/{show_id}/highlights/videos/', highlight_id,
                query={'offset': page * self._PAGE_SIZE, 'limit': self._PAGE_SIZE},
                note=f'Downloading JSON highlights for show {show_id} - page {page}')
            highlight = [
                v for v in highlights_videos.get('results', [])
                if v.get('id', -1) == int(highlight_id)
            ]
            if highlight or highlights_videos.get('count', 0) <= self._PAGE_SIZE * (page + 1):
                break
            page += 1

        if not highlight:
            raise ExtractorError(f'Unable to find highlight {highlight_id} for show {show_id}')

        highlight = highlight[0]
        return merge_dicts(
            {
                'id': f'{show_id}-{highlight_id}',
                'title': highlight.get('title'),
                'upload_date': unified_strdate(highlight.get('regdate')),
                'timestamp': unified_timestamp(highlight.get('regdate')),
                'thumbnail': highlight.get('thumbnail_url'),
            },
            self._extract_video_info(
                highlight_id, highlight['video_id'], highlight['video_inkey']))

    def _extract_show_replays(self, show_id):
        page = 0
        entries = []
        while True:
            show_vod_info = self._call_api(
                f'/vod-shows/{show_id}', show_id,
                query={'offset': page * self._PAGE_SIZE, 'limit': self._PAGE_SIZE},
                note=f'Downloading JSON vod list for show {show_id} - page {page}'
            ).get('response', {}).get('result', {})
            for v in show_vod_info.get('vod_list', []):
                entries.append(self._extract_replay(show_id, v['id']))

            if show_vod_info.get('count', 0) <= self._PAGE_SIZE * (page + 1):
                break
            page += 1
        return entries

    def _extract_show_highlights(self, show_id):
        page = 0
        entries = []
        while True:
            highlights_videos = self._call_api(
                f'/shows/{show_id}/highlights/videos/', show_id,
                query={'offset': page * self._PAGE_SIZE, 'limit': self._PAGE_SIZE},
                note=f'Downloading JSON highlights for show {show_id} - page {page}')

            highlights = highlights_videos.get('results', [])
            for v in highlights:
                entries.append(self._extract_highlight(show_id, v['id'], highlights_videos))

            if highlights_videos.get('count', 0) <= self._PAGE_SIZE * (page + 1):
                break
            page += 1
        return entries

    def _real_extract(self, url):
        show_id = self._match_id(url)
        qs = compat_parse_qs(compat_urllib_parse_urlparse(url).query)

        if qs.get('shareHightlight') and self._downloader.params.get('noplaylist'):
            self.to_screen(
                f'Downloading just video {show_id}-{qs["shareHightlight"][0]} because of --no-playlist')
            return self._extract_highlight(show_id, qs['shareHightlight'][0])

        if qs.get('shareReplayId') and self._downloader.params.get('noplaylist'):
            self.to_screen(
                f'Downloading just video {show_id}-{qs["shareReplayId"][0]} because of --no-playlist')
            return self._extract_replay(show_id, qs['shareReplayId'][0])

        show_info = self._call_api(
            f'/shows/{show_id}', show_id,
            note=f'Downloading JSON vod list for show {show_id}')

        if qs.get('shareHightlight') or qs.get('shareReplayId'):
            self.to_screen(
                'Downloading entire show. To download only the replay/highlight, use --no-playlist')

        # extract both replays and highlights
        entries = self._extract_show_replays(show_id)
        entries.extend(self._extract_show_highlights(show_id))

        return self.playlist_result(entries, show_id, show_info.get('title'))
