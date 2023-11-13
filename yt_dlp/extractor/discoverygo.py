import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    ExtractorError,
    int_or_none,
    parse_age_limit,
    remove_end,
    unescapeHTML,
    url_or_none,
)


class DiscoveryGoBaseIE(InfoExtractor):
    _VALID_URL_TEMPLATE = r'''(?x)https?://(?:www\.)?(?:
            discovery|
            investigationdiscovery|
            discoverylife|
            animalplanet|
            ahctv|
            destinationamerica|
            sciencechannel|
            tlc|
            velocitychannel
        )go\.com/%s(?P<id>[^/?#&]+)'''

    def _extract_video_info(self, video, stream, display_id):
        title = video['name']

        if not stream:
            if video.get('authenticated') is True:
                raise ExtractorError(
                    'This video is only available via cable service provider subscription that'
                    ' is not currently supported. You may want to use --cookies.', expected=True)
            else:
                raise ExtractorError('Unable to find stream')
        STREAM_URL_SUFFIX = 'streamUrl'
        formats = []
        for stream_kind in ('', 'hds'):
            suffix = STREAM_URL_SUFFIX.capitalize() if stream_kind else STREAM_URL_SUFFIX
            stream_url = stream.get('%s%s' % (stream_kind, suffix))
            if not stream_url:
                continue
            if stream_kind == '':
                formats.extend(self._extract_m3u8_formats(
                    stream_url, display_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            elif stream_kind == 'hds':
                formats.extend(self._extract_f4m_formats(
                    stream_url, display_id, f4m_id=stream_kind, fatal=False))

        video_id = video.get('id') or display_id
        description = video.get('description', {}).get('detailed')
        duration = int_or_none(video.get('duration'))

        series = video.get('show', {}).get('name')
        season_number = int_or_none(video.get('season', {}).get('number'))
        episode_number = int_or_none(video.get('episodeNumber'))

        tags = video.get('tags')
        age_limit = parse_age_limit(video.get('parental', {}).get('rating'))

        subtitles = {}
        captions = stream.get('captions')
        if isinstance(captions, list):
            for caption in captions:
                subtitle_url = url_or_none(caption.get('fileUrl'))
                if not subtitle_url or not subtitle_url.startswith('http'):
                    continue
                lang = caption.get('fileLang', 'en')
                ext = determine_ext(subtitle_url)
                subtitles.setdefault(lang, []).append({
                    'url': subtitle_url,
                    'ext': 'ttml' if ext == 'xml' else ext,
                })

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'duration': duration,
            'series': series,
            'season_number': season_number,
            'episode_number': episode_number,
            'tags': tags,
            'age_limit': age_limit,
            'formats': formats,
            'subtitles': subtitles,
        }


class DiscoveryGoIE(DiscoveryGoBaseIE):
    _VALID_URL = DiscoveryGoBaseIE._VALID_URL_TEMPLATE % r'(?:[^/]+/)+'
    _GEO_COUNTRIES = ['US']
    _TEST = {
        'url': 'https://www.discoverygo.com/bering-sea-gold/reaper-madness/',
        'info_dict': {
            'id': '58c167d86b66d12f2addeb01',
            'ext': 'mp4',
            'title': 'Reaper Madness',
            'description': 'md5:09f2c625c99afb8946ed4fb7865f6e78',
            'duration': 2519,
            'series': 'Bering Sea Gold',
            'season_number': 8,
            'episode_number': 6,
            'age_limit': 14,
        },
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        container = extract_attributes(
            self._search_regex(
                r'(<div[^>]+class=["\']video-player-container[^>]+>)',
                webpage, 'video container'))

        video = self._parse_json(
            container.get('data-video') or container.get('data-json'),
            display_id)

        stream = video.get('stream')

        return self._extract_video_info(video, stream, display_id)


class DiscoveryGoPlaylistIE(DiscoveryGoBaseIE):
    _VALID_URL = DiscoveryGoBaseIE._VALID_URL_TEMPLATE % ''
    _TEST = {
        'url': 'https://www.discoverygo.com/bering-sea-gold/',
        'info_dict': {
            'id': 'bering-sea-gold',
            'title': 'Bering Sea Gold',
            'description': 'md5:cc5c6489835949043c0cc3ad66c2fa0e',
        },
        'playlist_mincount': 6,
    }

    @classmethod
    def suitable(cls, url):
        return False if DiscoveryGoIE.suitable(url) else super(
            DiscoveryGoPlaylistIE, cls).suitable(url)

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        entries = []
        for mobj in re.finditer(r'data-json=(["\'])(?P<json>{.+?})\1', webpage):
            data = self._parse_json(
                mobj.group('json'), display_id,
                transform_source=unescapeHTML, fatal=False)
            if not isinstance(data, dict) or data.get('type') != 'episode':
                continue
            episode_url = data.get('socialUrl')
            if not episode_url:
                continue
            entries.append(self.url_result(
                episode_url, ie=DiscoveryGoIE.ie_key(),
                video_id=data.get('id')))

        return self.playlist_result(
            entries, display_id,
            remove_end(self._og_search_title(
                webpage, fatal=False), ' | Discovery GO'),
            self._og_search_description(webpage))
