import itertools

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    try_get,
    unified_strdate,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class CrowdBunkerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?crowdbunker\.com/v/(?P<id>[^/?#$&]+)'

    _TESTS = [{
        'url': 'https://crowdbunker.com/v/0z4Kms8pi8I',
        'info_dict': {
            'id': '0z4Kms8pi8I',
            'ext': 'mp4',
            'title': '117) Pass vax et solutions',
            'description': 'md5:86bcb422c29475dbd2b5dcfa6ec3749c',
            'view_count': int,
            'duration': 5386,
            'uploader': 'Jérémie Mercier',
            'uploader_id': 'UCeN_qQV829NYf0pvPJhW5dQ',
            'like_count': int,
            'upload_date': '20211218',
            'thumbnail': 'https://scw.divulg.org/cb-medias4/images/0z4Kms8pi8I/maxres.jpg',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data_json = self._download_json(
            f'https://api.divulg.org/post/{video_id}/details', video_id,
            headers={'accept': 'application/json, text/plain, */*'})
        video_json = data_json['video']
        formats, subtitles = [], {}
        for sub in video_json.get('captions') or []:
            sub_url = try_get(sub, lambda x: x['file']['url'])
            if not sub_url:
                continue
            subtitles.setdefault(sub.get('languageCode', 'fr'), []).append({
                'url': sub_url,
            })

        if mpd_url := traverse_obj(video_json, ('dashManifest', 'url', {url_or_none})):
            fmts, subs = self._extract_mpd_formats_and_subtitles(mpd_url, video_id, mpd_id='dash', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        if m3u8_url := traverse_obj(video_json, ('hlsManifest', 'url', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        thumbnails = [{
            'url': image['url'],
            'height': int_or_none(image.get('height')),
            'width': int_or_none(image.get('width')),
        } for image in video_json.get('thumbnails') or [] if image.get('url')]

        return {
            'id': video_id,
            'title': video_json.get('title'),
            'description': video_json.get('description'),
            'view_count': video_json.get('viewCount'),
            'duration': video_json.get('duration'),
            'uploader': try_get(data_json, lambda x: x['channel']['name']),
            'uploader_id': try_get(data_json, lambda x: x['channel']['id']),
            'like_count': data_json.get('likesCount'),
            'upload_date': unified_strdate(video_json.get('publishedAt') or video_json.get('createdAt')),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }


class CrowdBunkerChannelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?crowdbunker\.com/@(?P<id>[^/?#$&]+)'

    _TESTS = [{
        'url': 'https://crowdbunker.com/@Milan_UHRIN',
        'playlist_mincount': 14,
        'info_dict': {
            'id': 'Milan_UHRIN',
        },
    }]

    def _entries(self, playlist_id):
        last = None

        for page in itertools.count():
            channel_json = self._download_json(
                f'https://api.divulg.org/organization/{playlist_id}/posts', playlist_id,
                headers={'accept': 'application/json, text/plain, */*'},
                query={'after': last} if last else {}, note=f'Downloading Page {page}')
            for item in channel_json.get('items') or []:
                v_id = item.get('uid')
                if not v_id:
                    continue
                yield self.url_result(
                    f'https://crowdbunker.com/v/{v_id}', ie=CrowdBunkerIE.ie_key(), video_id=v_id)
            last = channel_json.get('last')
            if not last:
                break

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        return self.playlist_result(self._entries(playlist_id), playlist_id=playlist_id)
