from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    try_get,
    url_or_none,
)


class CCCIE(InfoExtractor):
    IE_NAME = 'media.ccc.de'
    _VALID_URL = r'https?://(?:www\.)?media\.ccc\.de/v/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://media.ccc.de/v/30C3_-_5443_-_en_-_saal_g_-_201312281830_-_introduction_to_processor_design_-_byterazor#video',
        'md5': '3a1eda8f3a29515d27f5adb967d7e740',
        'info_dict': {
            'id': '1839',
            'ext': 'mp4',
            'title': 'Introduction to Processor Design',
            'creator': 'byterazor',
            'description': 'md5:df55f6d073d4ceae55aae6f2fd98a0ac',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20131228',
            'timestamp': 1388188800,
            'duration': 3710,
            'tags': list,
        }
    }, {
        'url': 'https://media.ccc.de/v/32c3-7368-shopshifting#download',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        event_id = self._search_regex(r"data-id='(\d+)'", webpage, 'event id')
        event_data = self._download_json('https://media.ccc.de/public/events/%s' % event_id, event_id)

        formats = []
        for recording in event_data.get('recordings', []):
            recording_url = recording.get('recording_url')
            if not recording_url:
                continue
            language = recording.get('language')
            folder = recording.get('folder')
            format_id = None
            if language:
                format_id = language
            if folder:
                if language:
                    format_id += '-' + folder
                else:
                    format_id = folder
            vcodec = 'h264' if 'h264' in folder else (
                'none' if folder in ('mp3', 'opus') else None
            )
            formats.append({
                'format_id': format_id,
                'url': recording_url,
                'width': int_or_none(recording.get('width')),
                'height': int_or_none(recording.get('height')),
                'filesize': int_or_none(recording.get('size'), invscale=1024 * 1024),
                'language': language,
                'vcodec': vcodec,
            })
        self._sort_formats(formats)

        return {
            'id': event_id,
            'display_id': display_id,
            'title': event_data['title'],
            'creator': try_get(event_data, lambda x: ', '.join(x['persons'])),
            'description': event_data.get('description'),
            'thumbnail': event_data.get('thumb_url'),
            'timestamp': parse_iso8601(event_data.get('date')),
            'duration': int_or_none(event_data.get('length')),
            'tags': event_data.get('tags'),
            'formats': formats,
        }


class CCCPlaylistIE(InfoExtractor):
    IE_NAME = 'media.ccc.de:lists'
    _VALID_URL = r'https?://(?:www\.)?media\.ccc\.de/c/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://media.ccc.de/c/30c3',
        'info_dict': {
            'title': '30C3',
            'id': '30c3',
        },
        'playlist_count': 135,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url).lower()

        conf = self._download_json(
            'https://media.ccc.de/public/conferences/' + playlist_id,
            playlist_id)

        entries = []
        for e in conf['events']:
            event_url = url_or_none(e.get('frontend_link'))
            if event_url:
                entries.append(self.url_result(event_url, ie=CCCIE.ie_key()))

        return self.playlist_result(entries, playlist_id, conf.get('title'))
