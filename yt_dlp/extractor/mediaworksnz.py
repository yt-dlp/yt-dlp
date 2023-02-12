import re

from .common import InfoExtractor
from ..utils import (
    bug_reports_message,
    float_or_none,
    traverse_obj,
    unified_timestamp,
)


class MediaWorksNZVODIE(InfoExtractor):
    _VALID_URL_BASE_RE = r'https?://vodupload-api\.mediaworks\.nz/library/asset/published/'
    _VALID_URL_ID_RE = r'(?P<id>[A-Za-z0-9-]+)'
    _VALID_URL = rf'{_VALID_URL_BASE_RE}{_VALID_URL_ID_RE}'
    _TESTS = [{
        'url': 'https://vodupload-api.mediaworks.nz/library/asset/published/VID00359',
        'info_dict': {
            'id': 'VID00359',
            'ext': 'mp4',
            'title': 'GRG Jacinda Ardern safe drug testing 1920x1080',
            'description': 'md5:d4d7dc366742e86d8130b257dcb520ba',
            'duration': 142.76,
            'timestamp': 1604268608,
            'upload_date': '20201101',
            'thumbnail': r're:^https?://.*\.jpg$',
            'channel': 'George FM'
        }
    }, {
        # has audio-only format
        'url': 'https://vodupload-api.mediaworks.nz/library/asset/published/VID02627',
        'info_dict': {
            'id': 'VID02627',
            'ext': 'mp3',
            'title': 'Tova O\'Brien meets Ukraine President Volodymyr Zelensky',
            'channel': 'Today FM',
            'description': 'Watch in full the much anticipated interview of Volodymyr Zelensky',
            'duration': 2061.16,
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20220822',
            'timestamp': 1661152289,
        },
        'params': {'format': 'ba[ext=mp3]'}
    }]

    _WEBPAGE_TESTS = [{
        'url': 'https://www.rova.nz/home/podcasts/socrates-walks-into-a-bar/the-trolley-problem---episode-1.html',
        'info_dict': {
            'id': 'VID02494',
            'ext': 'mp4',
            'title': 'The Trolley Problem',
            'duration': 2843.56,
            'channel': 'Other',
            'timestamp': 1658356489,
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'Socrates Walks Into A Bar Podcast Episode 1',
            'upload_date': '20220720',
        }
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for mobj in re.finditer(
            rf'''(?x)<div\s+\bid=["']Player-Attributes-JWID[^>]+\b
            data-request-url=["']{cls._VALID_URL_BASE_RE}["'][^>]+\b
            data-asset-id=["']{cls._VALID_URL_ID_RE}["']''', webpage
        ):
            yield f'https://vodupload-api.mediaworks.nz/library/asset/published/{mobj.group("id")}'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        asset = self._download_json(url, video_id)['asset']

        if asset.get('drm') not in ('NonDRM', None):
            self.report_drm(video_id)

        content_type = asset.get('type')
        if content_type and content_type != 'video':
            self.report_warning(f'Unknown content type: {content_type}' + bug_reports_message(), video_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(asset['streamingUrl'], video_id)

        audio_streaming_url = traverse_obj(
            asset, 'palyoutPathAudio', 'playoutpathaudio', expected_type=str)
        if audio_streaming_url:
            audio_formats = self._extract_m3u8_formats(audio_streaming_url, video_id, fatal=False, ext='mp3')
            for audio_format in audio_formats:
                # all the audio streams appear to be aac
                audio_format.setdefault('vcodec', 'none')
                audio_format.setdefault('acodec', 'aac')
                formats.append(audio_format)

        return {
            'id': video_id,
            'title': asset.get('title'),
            'description': asset.get('description'),
            'duration': float_or_none(asset.get('duration')),
            'timestamp': unified_timestamp(asset.get('dateadded')),
            'channel': asset.get('brand'),
            'thumbnails': [{'url': thumbnail_url} for thumbnail_url in asset.get('thumbnails') or []],
            'formats': formats,
            'subtitles': subtitles,
        }
