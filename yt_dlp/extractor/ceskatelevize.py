import re
import json

from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote, compat_urllib_parse_urlparse
from ..networking import Request
from ..utils import (
    ExtractorError,
    float_or_none,
    str_or_none,
    traverse_obj,
    unescapeHTML,
    urlencode_postdata,
)

USER_AGENTS = {
    'Safari': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27',
}


class CeskaTelevizeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ceskatelevize\.cz/(?:ivysilani|porady|zive)/(?:[^/?#&]+/)*(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://www.ceskatelevize.cz/porady/10441294653-hyde-park-civilizace/bonus/20641/',
        'info_dict': {
            'id': '61924494877028507',
            'ext': 'mp4',
            'title': 'Bonus 01 - En - Hyde Park Civilizace',
            'description': 'English Subtittles',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 81.3,
            'live_status': 'not_live',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # live stream
        'url': 'https://www.ceskatelevize.cz/zive/ct1/',
        'only_matching': True,
        'info_dict': {
            'id': '61924494878124436',
            'ext': 'mp4',
            'title': r're:^ČT1 - živé vysílání online \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'description': 'Sledujte živé vysílání kanálu ČT1 online. Vybírat si můžete i z dalších kanálů České televize na kterémkoli z vašich zařízení.',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 5373.3,
            'live_status': 'is_live',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # another
        'url': 'https://www.ceskatelevize.cz/zive/sport/',
        'only_matching': True,
        'info_dict': {
            'id': '422',
            'ext': 'mp4',
            'title': r're:^ČT Sport \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'thumbnail': r're:^https?://.*\.jpg',
            'live_status': 'is_live',
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
            'title': 'Bogotart - Queer',
            'description': 'Hlavní město Kolumbie v doprovodu queer umělců. Vroucí svět plný vášně, sebevědomí, ale i násilí a bolesti',
        },
        'playlist': [{
            'info_dict': {
                'id': '61924494877311053',
                'ext': 'mp4',
                'title': 'Bogotart - Queer (Varování 18+)',
                'duration': 11.9,
                'live_status': 'not_live',
            },
        }, {
            'info_dict': {
                'id': '61924494877068022',
                'ext': 'mp4',
                'title': 'Bogotart - Queer (Queer)',
                'thumbnail': r're:^https?://.*\.jpg',
                'duration': 1558.3,
                'live_status': 'not_live',
            },
        }],
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # iframe embed
        'url': 'http://www.ceskatelevize.cz/porady/10614999031-neviditelni/21251212048/',
        'info_dict': {
            'id': '61924494877628660',
            'ext': 'mp4',
            'title': 'Epizoda 1/13 - Neviditelní',
            'description': 'Vypadají jako my, mluví jako my, ale mají něco navíc – gen, který jim umožňuje dýchat vodu. Aniž to tušíme, žijí mezi námi.',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 3576.8,
            'live_status': 'not_live',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, playlist_id)
        parsed_url = compat_urllib_parse_urlparse(urlh.url)
        site_name = self._og_search_property('site_name', webpage, fatal=False, default='Česká televize')
        playlist_title = self._og_search_title(webpage, default=None)
        if site_name and playlist_title:
            playlist_title = re.split(r'\s*[—|]\s*%s' % (site_name, ), playlist_title, 1)[0]
        playlist_description = self._og_search_description(webpage, default=None)
        if playlist_description:
            playlist_description = playlist_description.replace('\xa0', ' ')

        type_ = 'episode'
        is_live = False
        if re.search(r'(^/porady|/zive)/', parsed_url.path):
            next_data = self._search_nextjs_data(webpage, playlist_id)
            if '/zive/' in parsed_url.path:
                idec = traverse_obj(next_data, ('props', 'pageProps', 'data', 'liveBroadcast', 'current', 'idec'), get_all=False)
                sidp = traverse_obj(next_data, ('props', 'pageProps', 'data', 'liveBroadcast', 'current', 'showId'), get_all=False)
                is_live = True
            else:
                idec = traverse_obj(next_data, ('props', 'pageProps', 'data', ('show', 'mediaMeta'), 'idec'), get_all=False)
                if not idec:
                    idec = traverse_obj(next_data, ('props', 'pageProps', 'data', 'videobonusDetail', 'bonusId'), get_all=False)
                    if idec:
                        type_ = 'bonus'
                sidp = self._search_regex(r'https?://(?:www\.)?ceskatelevize\.cz/(?:ivysilani|porady|zive)/([0-9]+)-', url, playlist_id, default=playlist_id)
            if not idec:
                raise ExtractorError('Failed to find IDEC id')
            sidp = sidp.rsplit('-')[0]
            query = {'origin': 'iVysilani', 'autoStart': 'true', 'sidp': sidp, type_: idec}
            webpage = self._download_webpage(
                'https://player.ceskatelevize.cz/',
                playlist_id, note='Downloading player', query=query)
            playlistpage_url = 'https://www.ceskatelevize.cz/ivysilani/ajax/get-client-playlist/'
            data = {
                'playlist[0][type]': type_,
                'playlist[0][id]': idec,
                'requestUrl': parsed_url.path,
                'requestSource': 'iVysilani',
            }
        elif parsed_url.path == '/' and parsed_url.fragment == 'live':
            if self._search_regex(r'(?s)<section[^>]+id=[\'"]live[\'"][^>]+data-ctcomp-data=\'([^\']+)\'[^>]*>', webpage, 'live video player', default=None):
                # CT4
                is_live = True
                ctcomp_data = self._parse_json(
                    self._search_regex(
                        r'(?s)<section[^>]+id=[\'"]live[\'"][^>]+data-ctcomp-data=\'([^\']+)\'[^>]*>',
                        webpage, 'ctcomp data', fatal=True),
                    playlist_id, transform_source=unescapeHTML)
                current_item = traverse_obj(ctcomp_data, ('items', ctcomp_data.get('currentItem'), 'items', 0, 'video', 'data', 'source', 'playlist', 0))
                playlistpage_url = 'https://playlist.ceskatelevize.cz/'
                data = {
                    'contentType': 'live',
                    'items': [{
                        'id': current_item.get('id'),
                        'key': current_item.get('key'),
                        'assetId': current_item.get('assetId'),
                        'playerType': 'dash',
                        'date': current_item.get('date'),
                        'requestSource': current_item.get('requestSource'),
                        'drm': current_item.get('drm'),
                        'quality': current_item.get('quality'),
                    }]
                }
                data = {'data': json.dumps(data).encode('utf-8')}
            else:
                # CT24
                is_live = True
                lvp_url = self._search_regex(
                    r'(?s)<div[^>]+id=[\'"]live-video-player[\'"][^>]+data-url=[\'"]([^\'"]+)[\'"][^>]*>',
                    webpage, 'live video player', fatal=True)
                lvp_hash = self._search_regex(
                    r'(?s)media_ivysilani: *{ *hash *: *[\'"]([0-9a-f]+)[\'"] *}',
                    webpage, 'live video hash', fatal=True)
                lvp_url += '&hash=' + lvp_hash
                webpage = self._download_webpage(unescapeHTML(lvp_url), playlist_id)
                playlistpage = self._search_regex(
                    r'(?s)getPlaylistUrl\((\[[^\]]+\])[,\)]',
                    webpage, 'playlist params', fatal=True)
                playlistpage_params = self._parse_json(playlistpage, playlist_id)[0]
                playlistpage_url = 'https://www.ceskatelevize.cz/ivysilani/ajax/get-client-playlist/'
                idec = playlistpage_params.get('id')
                data = {
                    'playlist[0][type]': playlistpage_params.get('type'),
                    'playlist[0][id]': idec,
                    'requestUrl': '/ivysilani/embed/iFramePlayer.php',
                    'requestSource': 'iVysilani',
                }

        NOT_AVAILABLE_STRING = 'This content is not available at your territory due to limited copyright.'
        if '%s</p>' % NOT_AVAILABLE_STRING in webpage:
            self.raise_geo_restricted(NOT_AVAILABLE_STRING)
        if any(not_found in webpage for not_found in ('Neplatný parametr pro videopřehrávač', 'IDEC nebyl nalezen', )):
            raise ExtractorError('no video with IDEC available', video_id=idec, expected=True)

        entries = []

        for user_agent in (None, USER_AGENTS['Safari']):
            req = Request(playlistpage_url, data=urlencode_postdata(data))
            req.headers['Content-type'] = 'application/x-www-form-urlencoded'
            req.headers['x-addr'] = '127.0.0.1'
            req.headers['X-Requested-With'] = 'XMLHttpRequest'
            if user_agent:
                req.headers['User-Agent'] = user_agent
            req.headers['Referer'] = url

            playlistpage = self._download_json(req, playlist_id, fatal=False)

            if not playlistpage:
                continue

            playlist_url = playlistpage.get('url')
            if playlist_url:
                if playlist_url == 'error_region':
                    raise ExtractorError(NOT_AVAILABLE_STRING, expected=True)
                req = Request(compat_urllib_parse_unquote(playlist_url))
                req.headers['Referer'] = url
                playlist = self._download_json(req, playlist_id, fatal=False)
                if not playlist:
                    continue
                playlist = playlist.get('playlist')
            else:
                playlist = traverse_obj(playlistpage, ('RESULT', 'playlist'))

            if not isinstance(playlist, list):
                continue

            playlist_len = len(playlist)

            for num, item in enumerate(playlist):
                formats = []
                for format_id, stream_url in item.get('streamUrls', {}).items():
                    if 'playerType=flash' in stream_url:
                        stream_formats = self._extract_m3u8_formats(
                            stream_url, playlist_id, 'mp4', 'm3u8_native',
                            m3u8_id='hls-%s' % format_id, fatal=False)
                    else:
                        stream_formats = self._extract_mpd_formats(
                            stream_url, playlist_id,
                            mpd_id='dash-%s' % format_id, fatal=False)
                    if 'drmOnly=true' in stream_url:
                        for f in stream_formats:
                            f['has_drm'] = True
                    # See https://github.com/ytdl-org/youtube-dl/issues/12119#issuecomment-280037031
                    if format_id == 'audioDescription':
                        for f in stream_formats:
                            f['source_preference'] = -10
                    formats.extend(stream_formats)

                if user_agent and len(entries) == playlist_len:
                    entries[num]['formats'].extend(formats)
                    continue

                item_id = str_or_none(item.get('id') or item['assetId'])
                title = item.get('title') or 'live'

                duration = float_or_none(item.get('duration'))
                thumbnail = item.get('previewImageUrl')

                subtitles = {}
                if item.get('type') == 'VOD':
                    subs = item.get('subtitles')
                    if subs:
                        subtitles = self.extract_subtitles(idec, subs)

                if playlist_len == 1:
                    final_title = playlist_title or title
                else:
                    final_title = '%s (%s)' % (playlist_title, title)

                entries.append({
                    'id': item_id,
                    'title': final_title,
                    'description': playlist_description if playlist_len == 1 else None,
                    'thumbnail': thumbnail,
                    'duration': duration,
                    'formats': formats,
                    'subtitles': subtitles,
                    'live_status': 'is_live' if is_live else 'not_live',
                })

        if len(entries) == 1:
            return entries[0]
        return self.playlist_result(entries, playlist_id, playlist_title, playlist_description)

    def _get_subtitles(self, episode_id, subs):
        original_subtitles = self._download_webpage(
            subs[0]['url'], episode_id, 'Downloading subtitles')
        srt_subs = self._fix_subtitles(original_subtitles)
        return {
            'cs': [{
                'ext': 'srt',
                'data': srt_subs,
            }]
        }

    @staticmethod
    def _fix_subtitles(subtitles):
        """ Convert millisecond-based subtitles to SRT """

        def _msectotimecode(msec):
            """ Helper utility to convert milliseconds to timecode """
            components = []
            for divider in [1000, 60, 60, 100]:
                components.append(msec % divider)
                msec //= divider
            return '{3:02}:{2:02}:{1:02},{0:03}'.format(*components)

        def _fix_subtitle(subtitle):
            for line in subtitle.splitlines():
                m = re.match(r'^\s*([0-9]+);\s*([0-9]+)\s+([0-9]+)\s*$', line)
                if m:
                    yield m.group(1)
                    start, stop = (_msectotimecode(int(t)) for t in m.groups()[1:])
                    yield '{0} --> {1}'.format(start, stop)
                else:
                    yield line

        return '\r\n'.join(_fix_subtitle(subtitles))
