from .common import InfoExtractor
from ..utils import (
    int_or_none,
    join_nonempty,
    parse_iso8601,
    try_get,
    url_or_none,
)


class CCCIE(InfoExtractor):
    IE_NAME = 'media.ccc.de'
    _VALID_URL = r'https?://(?:www\.)?media\.ccc\.de/v/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://media.ccc.de/v/30C3_-_5443_-_en_-_saal_g_-_201312281830_-_introduction_to_processor_design_-_byterazor#video',
        'md5': 'e2e286b3b4496540c2ecd897c097daad',
        'info_dict': {
            'id': '1839',
            'ext': 'webm',
            'title': 'Introduction to Processor Design',
            'creators': ['byterazor'],
            'description': 'md5:df55f6d073d4ceae55aae6f2fd98a0ac',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20131228',
            'timestamp': 1388188800,
            'duration': 3710,
            'tags': list,
            'display_id': '30C3_-_5443_-_en_-_saal_g_-_201312281830_-_introduction_to_processor_design_-_byterazor',
            'view_count': int,
        },
    }, {
        'url': 'https://media.ccc.de/v/32c3-7368-shopshifting#download',
        'only_matching': True,
    }, {
        'url': 'https://media.ccc.de/v/39c3-schlechte-karten-it-sicherheit-im-jahr-null-der-epa-fur-alle',
        'md5': 'a6732117186ae1760a6abd5534a859c9',
        'info_dict': {
            'id': '16261',
            'ext': 'webm',
            'title': 'Schlechte Karten - IT-Sicherheit im Jahr null der ePA für alle',
            'display_id': '39c3-schlechte-karten-it-sicherheit-im-jahr-null-der-epa-fur-alle',
            'description': 'md5:719a5a9a52630249d606219c55056cbf',
            'view_count': int,
            'duration': 3619,
            'thumbnail': 'https://static.media.ccc.de/media/congress/2025/2403-2b5a6a8e-327e-594d-8f92-b91201d18a02.jpg',
            'tags': list,
            'creators': ['Bianca Kastl'],
            'timestamp': 1767024900,
            'upload_date': '20251229',
            'formats': [
                {'format_id': 'deu-mp3', 'vcodec': 'none'},
                {'format_id': 'eng-mp3-translated', 'vcodec': 'none'},
                {'format_id': 'deu-opus', 'vcodec': 'none'},
                {'format_id': 'eng-opus-translation', 'vcodec': 'none'},
                {'format_id': 'deu-eng-spa-h264-sd', 'vcodec': 'h264'},
                {'format_id': 'deu-eng-spa-webm-sd', 'vcodec': 'vp9'},
                {'format_id': 'eng-h264-hd', 'vcodec': 'h264'},
                {'format_id': 'spa-h264-hd', 'vcodec': 'h264'},
                {'format_id': 'deu-h264-hd', 'vcodec': 'h264'},
                {'format_id': 'deu-eng-spa-h264-hd', 'vcodec': 'h264'},
                {'format_id': 'deu-eng-spa-webm-hd', 'vcodec': 'vp9'},
                {'format_id': 'deu-eng-spa-av1-hd', 'vcodec': 'av1'},
            ],
        },
    }, {
        'url': 'https://media.ccc.de/v/2025-474-unifiedpush',
        'md5': '5ead6c31f8e961b99a3be15c4956a961',
        'info_dict': {
            'id': '15678',
            'ext': 'webm',
            'title': 'UnifiedPush',
            'display_id': '2025-474-unifiedpush',
            'description': 'md5:e1f57ff158826b663dc7128da52617ad',
            'view_count': int,
            'duration': 2111,
            'thumbnail': 'https://static.media.ccc.de/media/conferences/mrmcd/mrmcd25/474-13533a73-bd03-5104-86d1-cdf3232bc46c.jpg',
            'tags': list,
            'creators': ['Daniel Gultsch'],
            'timestamp': 1757697600,
            'upload_date': '20250912',
            'formats': [
                {'format_id': 'deu-mp3', 'vcodec': 'none'},
                {'format_id': 'deu-opus', 'vcodec': 'none'},
                {'format_id': 'deu-h264-sd', 'vcodec': 'h264'},
                {'format_id': 'deu-webm-sd', 'vcodec': 'vp9'},
                {'format_id': 'deu-h264-hd', 'vcodec': 'h264'},
                {'format_id': 'deu-webm-hd', 'vcodec': 'vp9'},
                {'format_id': 'deu-av1-hd', 'vcodec': 'av1'},
            ],
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        event_id = self._search_regex(r"data-id=(['\"])(?P<event_id>\d+)\1", webpage, 'event id', group='event_id')
        event_data = self._download_json(f'https://media.ccc.de/public/events/{event_id}', event_id)

        formats = []
        for recording in event_data.get('recordings', []):
            recording_url = recording.get('recording_url')
            if not recording_url:
                continue
            language = recording.get('language')
            folder = recording.get('folder') or ''
            vcodec = None
            if 'av1' in folder:
                vcodec = 'av1'
            elif 'webm' in folder:
                vcodec = 'vp9'
            elif 'h264' in folder:
                vcodec = 'h264'
            elif 'mp3' in folder or 'opus' in folder:
                vcodec = 'none'

            formats.append({
                'format_id': join_nonempty(language, folder) or None,
                'url': recording_url,
                'width': int_or_none(recording.get('width')),
                'height': int_or_none(recording.get('height')),
                'filesize': int_or_none(recording.get('size'), invscale=1024 * 1024),
                'language': language,
                'vcodec': vcodec,
            })

        return {
            'id': event_id,
            'display_id': display_id,
            'title': event_data['title'],
            'creator': try_get(event_data, lambda x: ', '.join(x['persons'])),
            'description': event_data.get('description'),
            'thumbnail': event_data.get('thumb_url'),
            'timestamp': parse_iso8601(event_data.get('date')),
            'duration': int_or_none(event_data.get('length')),
            'view_count': int_or_none(event_data.get('view_count')),
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
    }, {
        'url': 'https://media.ccc.de/c/DS2023',
        'info_dict': {
            'title': 'Datenspuren 2023',
            'id': 'DS2023',
        },
        'playlist_count': 37,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        conf = self._download_json(
            'https://media.ccc.de/public/conferences/' + playlist_id,
            playlist_id)

        entries = []
        for e in conf['events']:
            event_url = url_or_none(e.get('frontend_link'))
            if event_url:
                entries.append(self.url_result(event_url, ie=CCCIE.ie_key()))

        return self.playlist_result(entries, playlist_id, conf.get('title'))
