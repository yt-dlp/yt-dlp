import itertools

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    try_get,
    unified_strdate,
)


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
            'thumbnail': 'https://scw.divulg.org/cb-medias4/images/0z4Kms8pi8I/maxres.jpg'
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        data_json = self._download_json(f'https://api.divulg.org/post/{id}/details',
                                        id, headers={'accept': 'application/json, text/plain, */*'})
        video_json = data_json['video']
        formats, subtitles = [], {}
        for sub in video_json.get('captions') or []:
            sub_url = try_get(sub, lambda x: x['file']['url'])
            if not sub_url:
                continue
            subtitles.setdefault(sub.get('languageCode', 'fr'), []).append({
                'url': sub_url,
            })

        mpd_url = try_get(video_json, lambda x: x['dashManifest']['url'])
        if mpd_url:
            fmts, subs = self._extract_mpd_formats_and_subtitles(mpd_url, id)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        m3u8_url = try_get(video_json, lambda x: x['hlsManifest']['url'])
        if m3u8_url:
            fmts, subs = self._extract_m3u8_formats_and_subtitles(mpd_url, id)
            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)

        thumbnails = [{
            'url': image['url'],
            'height': int_or_none(image.get('height')),
            'width': int_or_none(image.get('width')),
        } for image in video_json.get('thumbnails') or [] if image.get('url')]

        self._sort_formats(formats)
        return {
            'id': id,
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

    def _entries(self, id):
        last = None

        for page in itertools.count():
            channel_json = self._download_json(
                f'https://api.divulg.org/organization/{id}/posts', id, headers={'accept': 'application/json, text/plain, */*'},
                query={'after': last} if last else {}, note=f'Downloading Page {page}')
            for item in channel_json.get('items') or []:
                v_id = item.get('uid')
                if not v_id:
                    continue
                yield self.url_result(
                    'https://crowdbunker.com/v/%s' % v_id, ie=CrowdBunkerIE.ie_key(), video_id=v_id)
            last = channel_json.get('last')
            if not last:
                break

    def _real_extract(self, url):
        id = self._match_id(url)
        return self.playlist_result(self._entries(id), playlist_id=id)
