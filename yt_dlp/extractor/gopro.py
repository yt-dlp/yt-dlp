from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    remove_end,
    str_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
)


class GoProIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?gopro\.com/v(/(?P<plid>[A-Za-z0-9]+))?(/(?P<id>[A-Za-z0-9]+))?'

    _TESTS = [{
        'url': 'https://gopro.com/v/ZNVvED8QDzR5V',
        'info_dict': {
            'id': 'LvV9MVbapDqKy',
            'title': 'My GoPro Adventure - 9/19/21',
            'thumbnail': r're:https?://.+',
            'ext': 'mp4',
            'timestamp': 1632070674,
            'upload_date': '20210919',
            'uploader_id': 'fireydive30018',
            'duration': 396062,
        },
    }, {
        'url': 'https://gopro.com/v/KRm6Vgp2peg4e',
        'info_dict': {
            'id': '0rl3J2y2l5N3v',
            'title': 'じゃがいも カリカリ オーブン焼き',
            'thumbnail': r're:https?://.+',
            'ext': 'mp4',
            'timestamp': 1607231111,
            'upload_date': '20201206',
            'uploader_id': 'dc9bcb8b-47d2-47c6-afbc-4c48f9a3769e',
            'duration': 45187,
            'track': 'The Sky Machine',
        },
    }, {
        'url': 'https://gopro.com/v/KRm6Vgp2peg4e/0rl3J2y2l5N3v',
        'note': 'Same video as above, but full link (playlist+video)',
        'info_dict': {
            'id': '0rl3J2y2l5N3v',
            'title': 'じゃがいも カリカリ オーブン焼き',
            'thumbnail': r're:https?://.+',
            'ext': 'mp4',
            'timestamp': 1607231111,
            'upload_date': '20201206',
            'uploader_id': 'dc9bcb8b-47d2-47c6-afbc-4c48f9a3769e',
            'duration': 45187,
            'track': 'The Sky Machine',
        },
    }, {
        'url': 'https://gopro.com/v/kVrK9wlJvBMwn',
        'info_dict': {
            'id': 'pJzDM128KQ8wG',
            'title': 'DARKNESS (DARKNESS)',
            'thumbnail': r're:https?://.+',
            'ext': 'mp4',
            'timestamp': 1594181304,
            'upload_date': '20200708',
            'uploader_id': '闇夜乃皇帝',
            'duration': 313075,
            'track': 'Battery (Live)',
            'artists': ['Metallica'],
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        playlist_id = self._match_valid_url(url).group('plid')
        if playlist_id is None and video_id is None:
            raise ExtractorError('Invalid URL: neither video ID nor playlist ID is present')

        webpage = self._download_webpage(url, video_id or playlist_id)
        metadata = self._search_json(
            r'window\.__reflectData\s*=', webpage, 'metadata', video_id or playlist_id)
        collection_title = str_or_none(
            try_get(metadata, lambda x: x['collection']['title'])
            or self._html_search_meta(['og:title', 'twitter:title'], webpage)
            or remove_end(self._html_search_regex(
                r'<title[^>]*>([^<]+)</title>', webpage, 'title', fatal=False), ' | GoPro'))
        if collection_title:
            collection_title = collection_title.replace('\n', ' ')
        entries = []
        for video_info in metadata['collectionMedia']:
            # If video_id is none, downloading the whole playlist.
            if video_id is None or video_id == video_info['id']:
                entries.append(self.ExtractOneEntry(webpage, metadata, collection_title, video_info))
        if not entries:
            raise ExtractorError(f'{url}: No videos found')
        return self.playlist_result(entries, playlist_id=playlist_id,
                                    playlist_title=collection_title)

    def ExtractOneEntry(self, webpage, metadata, collection_title, video_info):
        video_id = video_info['id']
        media_data = self._download_json(
            f'https://api.gopro.com/media/{video_id}/download', video_id)

        formats = []
        for fmt in try_get(media_data, lambda x: x['_embedded']['variations']) or []:
            format_url = url_or_none(fmt.get('url'))
            if not format_url:
                continue
            formats.append({
                'url': format_url,
                'format_id': str_or_none(fmt.get('quality')),
                'format_note': str_or_none(fmt.get('label')),
                'ext': str_or_none(fmt.get('type')),
                'width': int_or_none(fmt.get('width')),
                'height': int_or_none(fmt.get('height')),
            })

        title = collection_title
        content_title = video_info.get('content_title')
        if content_title:
            content_title = content_title.replace('\n', ' ')
            if title:
                title += f' ({content_title})'
            else:
                title = content_title

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': url_or_none(
                self._html_search_meta(['og:image', 'twitter:image'], webpage)),
            'timestamp': unified_timestamp(
                video_info.get('created_at')
                or try_get(metadata, lambda x: x['collection']['created_at'])),
            'uploader_id': str_or_none(
                try_get(metadata, lambda x: x['account']['nickname'])),
            'duration': int_or_none(
                video_info.get('source_duration')),
            'artist': str_or_none(
                video_info.get('music_track_artist')) or None,
            'track': str_or_none(
                video_info.get('music_track_name')) or None,
        }
