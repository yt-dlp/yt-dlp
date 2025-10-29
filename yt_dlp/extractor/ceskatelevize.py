import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    traverse_obj,
)

STREAM_DATA_MEDIA_API_URL_PREFIX = 'https://api.ceskatelevize.cz/video/v1/playlist-vod/v1/stream-data/media/external/'
STREAM_DATA_API_URL_POSTFIX = '?canPlayDrm=true'
STREAM_DATA_BONUS_API_URL_PREFIX = 'https://api.ceskatelevize.cz/video/v1/playlist-vod/v1/stream-data/bonus/BO-'
STREAM_DATA_INDEX_API_URL_PREFIX = 'https://api.ceskatelevize.cz/video/v1/playlist-vod/v1/stream-data/index/'


class CeskaTelevizeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ceskatelevize\.cz/porady/(?:[^/?#&]+/)*(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://www.ceskatelevize.cz/porady/10441294653-hyde-park-civilizace/bonus/11310/',
        'info_dict': {
            'id': '11310',
            'ext': 'mp4',
            'title': 'O Hyde Parku Civilizace - Hyde Park Civilizace',
            'description': 'Nabízíme šest televizních kanálů, mezi které patří ČT1, ČT2, ČT24, ČT Déčko, ČT art a ČT sport. Vysíláme 24 hodin denně. Zajišťujeme doprovodné služby včetně teletextu, elektronického programového průvodce i skrytých titulků. Zabýváme se výrobou a produkcí vlastních pořadů.',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 501,
            'chapters': [],
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # video with 18+ caution trailer
        'url': 'http://www.ceskatelevize.cz/porady/10520528904-queer/215562210900007-bogotart/',
        'info_dict': {
            'id': '215562210900007-bogotart',
            'ext': 'mp4',
            'title': 'Bogotart - Queer',
            'description': 'Hlavní město Kolumbie v doprovodu queer umělců. Vroucí svět plný vášně, sebevědomí, ale i násilí a bolesti',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 1556,
            'chapters': [],
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # iframe embed
        'url': 'http://www.ceskatelevize.cz/porady/10614999031-neviditelni/21251212048/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, playlist_id)
        parsed_url = urllib.parse.urlparse(urlh.url)
        site_name = self._og_search_property('site_name', webpage, fatal=False, default='Česká televize')
        playlist_title = self._og_search_title(webpage, default=None)
        if site_name and playlist_title:
            playlist_title = re.split(rf'\s*[—|]\s*{site_name}', playlist_title, maxsplit=1)[0]
        playlist_description = self._og_search_description(webpage, default=None)
        if playlist_description:
            playlist_description = playlist_description.replace('\xa0', ' ')

        if '/porady/' not in parsed_url.path:
            raise ExtractorError('Only "porady" supported.')

        next_data = self._search_nextjs_data(webpage, playlist_id)
        idec = traverse_obj(next_data, ('props', 'pageProps', 'data', ('show', 'mediaMeta'), 'idec'), get_all=False)
        _type = 'idec'

        if '/cast/' in traverse_obj(next_data, ('page')):
            indexId = traverse_obj(next_data, ('query', 'indexId'))
            _type = 'index'
        if not idec:
            idec = traverse_obj(next_data, ('props', 'pageProps', 'data', 'videobonusDetail', 'bonusId'), get_all=False)
            _type = 'bonus'
        if not idec:
            raise ExtractorError('Failed to find IDEC id')

        try:
            if _type == 'idec':
                api_response = self._download_json(
                    STREAM_DATA_MEDIA_API_URL_PREFIX + idec + STREAM_DATA_API_URL_POSTFIX,
                    idec, note='Getting stream data media api json')
            elif _type == 'bonus':
                api_response = self._download_json(
                    STREAM_DATA_BONUS_API_URL_PREFIX + idec + STREAM_DATA_API_URL_POSTFIX,
                    'BO-' + idec, note='Getting stream data bonus api json')
            elif _type == 'index':
                api_response = self._download_json(
                    STREAM_DATA_INDEX_API_URL_PREFIX + indexId + STREAM_DATA_API_URL_POSTFIX,
                    idec + '/' + indexId, note='Getting stream data bonus api json')
        except ExtractorError as ex:
            self.to_screen('Error: %s' % ex.msg)
            NOT_AVAILABLE_STRING = 'This content is not available. Possibly georestricted or license expired.'
            raise ExtractorError(NOT_AVAILABLE_STRING, expected=True)

        entries = []
        for stream_index, stream in enumerate(api_response['streams']):
            stream_formats = self._extract_mpd_formats(
                stream['url'], idec,
                # mpd_id=f'dash-{format_id}', fatal=False)
                fatal=False)
            if 'drmOnly=true' in stream['url']:
                for f in stream_formats:
                    f['has_drm'] = True

            title = api_response['title']

            duration = float_or_none(stream.get('duration'))
            thumbnail = api_response.get('previewImageUrl')

            subtitles = {}
            subs = stream.get('subtitles')
            if subs:
                subtitles = self.extract_subtitles(playlist_id, subs)

            chapters = []
            if stream.get('chapters'):
                chapters = self._extract_chapters_helper(
                    stream.get('chapters'),
                    start_function=lambda x: x.get('time'),
                    title_function=lambda x: x.get('title'),
                    duration=duration,
                )

            final_title = playlist_title or title
            if len(api_response['streams']) > 1:
                final_title = '%s %d' % (final_title, stream_index + 1)

            entries.append({
                'id': playlist_id,
                'title': final_title,
                'description': playlist_description,
                'thumbnail': thumbnail,
                'duration': duration,
                'formats': stream_formats,
                'subtitles': subtitles,
                'chapters': chapters,
                'is_live': 0,
            })

        if len(entries) == 1:
            return entries[0]
        return self.playlist_result(entries, playlist_id, playlist_title, playlist_description)

    def _get_subtitles(self, episode_id, subs):
        url = None
        for sub in subs:
            if sub['language'] == 'ces':
                for file in sub['files']:
                    if file['format'] == 'vtt':
                        url = file['url']
                        break
                break
        if url is None:
            return {}

        original_subtitles = self._download_webpage(
            url, episode_id, 'Downloading subtitles')
        vtt_subs = self._fix_subtitles(original_subtitles)
        return {
            'cs': [{
                'ext': 'vtt',
                'data': vtt_subs,
            }],
        }

    @staticmethod
    def _fix_subtitles(subtitles):
        """ Convert millisecond-based subtitles to VTT """

        def _msectotimecode(msec):
            """ Helper utility to convert milliseconds to timecode """
            components = []
            for divider in [1000, 60, 60, 100]:
                components.append(msec % divider)
                msec //= divider
            return '{3:02}:{2:02}:{1:02}.{0:03}'.format(*components)

        def _fix_subtitle(subtitle):
            for line in subtitle.splitlines():
                m = re.match(r'^\s*([0-9]+);\s*([0-9]+)\s+([0-9]+)\s*$', line)
                if m:
                    yield m.group(1)
                    start, stop = (_msectotimecode(int(t)) for t in m.groups()[1:])
                    yield f'{start} --> {stop}'
                else:
                    yield line

        return '\r\n'.join(_fix_subtitle(subtitles))
