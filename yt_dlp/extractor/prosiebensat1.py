import re

from hashlib import sha1
from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    merge_dicts,
    unified_strdate,
)


class ProSiebenSat1BaseIE(InfoExtractor):
    _GEO_BYPASS = False
    _ACCESS_ID = None
    _SUPPORTED_PROTOCOLS = 'dash:clear,hls:clear,progressive:clear'
    _V4_BASE_URL = 'https://vas-v4.p7s1video.net/4.0/get'

    def _extract_video_info(self, url, clip_id):
        client_location = url

        video = self._download_json(
            'http://vas.sim-technik.de/vas/live/v2/videos',
            clip_id, 'Downloading videos JSON', query={
                'access_token': self._TOKEN,
                'client_location': client_location,
                'client_name': self._CLIENT_NAME,
                'ids': clip_id,
            })[0]

        if not self.get_param('allow_unplayable_formats') and video.get('is_protected') is True:
            self.report_drm(clip_id)

        formats = []
        if self._ACCESS_ID:
            raw_ct = self._ENCRYPTION_KEY + clip_id + self._IV + self._ACCESS_ID
            protocols = self._download_json(
                self._V4_BASE_URL + 'protocols', clip_id,
                'Downloading protocols JSON',
                headers=self.geo_verification_headers(), query={
                    'access_id': self._ACCESS_ID,
                    'client_token': sha1((raw_ct).encode()).hexdigest(),
                    'video_id': clip_id,
                }, fatal=False, expected_status=(403,)) or {}
            error = protocols.get('error') or {}
            if error.get('title') == 'Geo check failed':
                self.raise_geo_restricted(countries=['AT', 'CH', 'DE'])
            server_token = protocols.get('server_token')
            if server_token:
                urls = (self._download_json(
                    self._V4_BASE_URL + 'urls', clip_id, 'Downloading urls JSON', query={
                        'access_id': self._ACCESS_ID,
                        'client_token': sha1((raw_ct + server_token + self._SUPPORTED_PROTOCOLS).encode()).hexdigest(),
                        'protocols': self._SUPPORTED_PROTOCOLS,
                        'server_token': server_token,
                        'video_id': clip_id,
                    }, fatal=False) or {}).get('urls') or {}
                for protocol, variant in urls.items():
                    source_url = variant.get('clear', {}).get('url')
                    if not source_url:
                        continue
                    if protocol == 'dash':
                        formats.extend(self._extract_mpd_formats(
                            source_url, clip_id, mpd_id=protocol, fatal=False))
                    elif protocol == 'hls':
                        formats.extend(self._extract_m3u8_formats(
                            source_url, clip_id, 'mp4', 'm3u8_native',
                            m3u8_id=protocol, fatal=False))
                    else:
                        formats.append({
                            'url': source_url,
                            'format_id': protocol,
                        })
        if not formats:
            source_ids = [compat_str(source['id']) for source in video['sources']]

            client_id = self._SALT[:2] + sha1(''.join([clip_id, self._SALT, self._TOKEN, client_location, self._SALT, self._CLIENT_NAME]).encode('utf-8')).hexdigest()

            sources = self._download_json(
                'http://vas.sim-technik.de/vas/live/v2/videos/%s/sources' % clip_id,
                clip_id, 'Downloading sources JSON', query={
                    'access_token': self._TOKEN,
                    'client_id': client_id,
                    'client_location': client_location,
                    'client_name': self._CLIENT_NAME,
                })
            server_id = sources['server_id']

            def fix_bitrate(bitrate):
                bitrate = int_or_none(bitrate)
                if not bitrate:
                    return None
                return (bitrate // 1000) if bitrate % 1000 == 0 else bitrate

            for source_id in source_ids:
                client_id = self._SALT[:2] + sha1(''.join([self._SALT, clip_id, self._TOKEN, server_id, client_location, source_id, self._SALT, self._CLIENT_NAME]).encode('utf-8')).hexdigest()
                urls = self._download_json(
                    'http://vas.sim-technik.de/vas/live/v2/videos/%s/sources/url' % clip_id,
                    clip_id, 'Downloading urls JSON', fatal=False, query={
                        'access_token': self._TOKEN,
                        'client_id': client_id,
                        'client_location': client_location,
                        'client_name': self._CLIENT_NAME,
                        'server_id': server_id,
                        'source_ids': source_id,
                    })
                if not urls:
                    continue
                if urls.get('status_code') != 0:
                    raise ExtractorError('This video is unavailable', expected=True)
                urls_sources = urls['sources']
                if isinstance(urls_sources, dict):
                    urls_sources = urls_sources.values()
                for source in urls_sources:
                    source_url = source.get('url')
                    if not source_url:
                        continue
                    protocol = source.get('protocol')
                    mimetype = source.get('mimetype')
                    if mimetype == 'application/f4m+xml' or 'f4mgenerator' in source_url or determine_ext(source_url) == 'f4m':
                        formats.extend(self._extract_f4m_formats(
                            source_url, clip_id, f4m_id='hds', fatal=False))
                    elif mimetype == 'application/x-mpegURL':
                        formats.extend(self._extract_m3u8_formats(
                            source_url, clip_id, 'mp4', 'm3u8_native',
                            m3u8_id='hls', fatal=False))
                    elif mimetype == 'application/dash+xml':
                        formats.extend(self._extract_mpd_formats(
                            source_url, clip_id, mpd_id='dash', fatal=False))
                    else:
                        tbr = fix_bitrate(source['bitrate'])
                        if protocol in ('rtmp', 'rtmpe'):
                            mobj = re.search(r'^(?P<url>rtmpe?://[^/]+)/(?P<path>.+)$', source_url)
                            if not mobj:
                                continue
                            path = mobj.group('path')
                            mp4colon_index = path.rfind('mp4:')
                            app = path[:mp4colon_index]
                            play_path = path[mp4colon_index:]
                            formats.append({
                                'url': '%s/%s' % (mobj.group('url'), app),
                                'app': app,
                                'play_path': play_path,
                                'player_url': 'http://livepassdl.conviva.com/hf/ver/2.79.0.17083/LivePassModuleMain.swf',
                                'page_url': 'http://www.prosieben.de',
                                'tbr': tbr,
                                'ext': 'flv',
                                'format_id': 'rtmp%s' % ('-%d' % tbr if tbr else ''),
                            })
                        else:
                            formats.append({
                                'url': source_url,
                                'tbr': tbr,
                                'format_id': 'http%s' % ('-%d' % tbr if tbr else ''),
                            })

        return {
            'duration': float_or_none(video.get('duration')),
            'formats': formats,
        }


class ProSiebenSat1IE(ProSiebenSat1BaseIE):
    IE_NAME = 'prosiebensat1'
    IE_DESC = 'ProSiebenSat.1 Digital'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:
                            (?:beta\.)?
                            (?:
                                prosieben(?:maxx)?|sixx|sat1(?:gold)?|kabeleins(?:doku)?|the-voice-of-germany|advopedia
                            )\.(?:de|at|ch)|
                            ran\.de|fem\.com|advopedia\.de|galileo\.tv/video
                        )
                        /(?P<id>.+)
                    '''

    _TESTS = [
        {
            # Tests changes introduced in https://github.com/ytdl-org/youtube-dl/pull/6242
            # in response to fixing https://github.com/ytdl-org/youtube-dl/issues/6215:
            # - malformed f4m manifest support
            # - proper handling of URLs starting with `https?://` in 2.0 manifests
            # - recursive child f4m manifests extraction
            'url': 'http://www.prosieben.de/tv/circus-halligalli/videos/218-staffel-2-episode-18-jahresrueckblick-ganze-folge',
            'info_dict': {
                'id': '2104602',
                'ext': 'mp4',
                'title': 'CIRCUS HALLIGALLI - Episode 18 - Staffel 2',
                'description': 'md5:8733c81b702ea472e069bc48bb658fc1',
                'upload_date': '20131231',
                'duration': 5845.04,
                'series': 'CIRCUS HALLIGALLI',
                'season_number': 2,
                'episode': 'Episode 18 - Staffel 2',
                'episode_number': 18,
            },
        },
        {
            'url': 'http://www.prosieben.de/videokatalog/Gesellschaft/Leben/Trends/video-Lady-Umstyling-f%C3%BCr-Audrina-Rebekka-Audrina-Fergen-billig-aussehen-Battal-Modica-700544.html',
            'info_dict': {
                'id': '2570327',
                'ext': 'mp4',
                'title': 'Lady-Umstyling für Audrina',
                'description': 'md5:4c16d0c17a3461a0d43ea4084e96319d',
                'upload_date': '20131014',
                'duration': 606.76,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'Seems to be broken',
        },
        {
            'url': 'http://www.prosiebenmaxx.de/tv/experience/video/144-countdown-fuer-die-autowerkstatt-ganze-folge',
            'info_dict': {
                'id': '2429369',
                'ext': 'mp4',
                'title': 'Countdown für die Autowerkstatt',
                'description': 'md5:809fc051a457b5d8666013bc40698817',
                'upload_date': '20140223',
                'duration': 2595.04,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'This video is unavailable',
        },
        {
            'url': 'http://www.sixx.de/stars-style/video/sexy-laufen-in-ugg-boots-clip',
            'info_dict': {
                'id': '2904997',
                'ext': 'mp4',
                'title': 'Sexy laufen in Ugg Boots',
                'description': 'md5:edf42b8bd5bc4e5da4db4222c5acb7d6',
                'upload_date': '20140122',
                'duration': 245.32,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'This video is unavailable',
        },
        {
            'url': 'http://www.sat1.de/film/der-ruecktritt/video/im-interview-kai-wiesinger-clip',
            'info_dict': {
                'id': '2906572',
                'ext': 'mp4',
                'title': 'Im Interview: Kai Wiesinger',
                'description': 'md5:e4e5370652ec63b95023e914190b4eb9',
                'upload_date': '20140203',
                'duration': 522.56,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'This video is unavailable',
        },
        {
            'url': 'http://www.kabeleins.de/tv/rosins-restaurants/videos/jagd-auf-fertigkost-im-elsthal-teil-2-ganze-folge',
            'info_dict': {
                'id': '2992323',
                'ext': 'mp4',
                'title': 'Jagd auf Fertigkost im Elsthal - Teil 2',
                'description': 'md5:2669cde3febe9bce13904f701e774eb6',
                'upload_date': '20141014',
                'duration': 2410.44,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'This video is unavailable',
        },
        {
            'url': 'http://www.ran.de/fussball/bundesliga/video/schalke-toennies-moechte-raul-zurueck-ganze-folge',
            'info_dict': {
                'id': '3004256',
                'ext': 'mp4',
                'title': 'Schalke: Tönnies möchte Raul zurück',
                'description': 'md5:4b5b271d9bcde223b54390754c8ece3f',
                'upload_date': '20140226',
                'duration': 228.96,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'This video is unavailable',
        },
        {
            'url': 'http://www.the-voice-of-germany.de/video/31-andreas-kuemmert-rocket-man-clip',
            'info_dict': {
                'id': '2572814',
                'ext': 'mp4',
                'title': 'The Voice of Germany - Andreas Kümmert: Rocket Man',
                'description': 'md5:6ddb02b0781c6adf778afea606652e38',
                'timestamp': 1382041620,
                'upload_date': '20131017',
                'duration': 469.88,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.fem.com/videos/beauty-lifestyle/kurztrips-zum-valentinstag',
            'info_dict': {
                'id': '2156342',
                'ext': 'mp4',
                'title': 'Kurztrips zum Valentinstag',
                'description': 'Romantischer Kurztrip zum Valentinstag? Nina Heinemann verrät, was sich hier wirklich lohnt.',
                'duration': 307.24,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.prosieben.de/tv/joko-gegen-klaas/videos/playlists/episode-8-ganze-folge-playlist',
            'info_dict': {
                'id': '439664',
                'title': 'Episode 8 - Ganze Folge - Playlist',
                'description': 'md5:63b8963e71f481782aeea877658dec84',
            },
            'playlist_count': 2,
            'skip': 'This video is unavailable',
        },
        {
            # title in <h2 class="subtitle">
            'url': 'http://www.prosieben.de/stars/oscar-award/videos/jetzt-erst-enthuellt-das-geheimnis-von-emma-stones-oscar-robe-clip',
            'info_dict': {
                'id': '4895826',
                'ext': 'mp4',
                'title': 'Jetzt erst enthüllt: Das Geheimnis von Emma Stones Oscar-Robe',
                'description': 'md5:e5ace2bc43fadf7b63adc6187e9450b9',
                'upload_date': '20170302',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'geo restricted to Germany',
        },
        {
            # geo restricted to Germany
            'url': 'http://www.kabeleinsdoku.de/tv/mayday-alarm-im-cockpit/video/102-notlandung-im-hudson-river-ganze-folge',
            'only_matching': True,
        },
        {
            # geo restricted to Germany
            'url': 'http://www.sat1gold.de/tv/edel-starck/video/11-staffel-1-episode-1-partner-wider-willen-ganze-folge',
            'only_matching': True,
        },
        {
            # geo restricted to Germany
            'url': 'https://www.galileo.tv/video/diese-emojis-werden-oft-missverstanden',
            'only_matching': True,
        },
        {
            'url': 'http://www.sat1gold.de/tv/edel-starck/playlist/die-gesamte-1-staffel',
            'only_matching': True,
        },
        {
            'url': 'http://www.advopedia.de/videos/lenssen-klaert-auf/lenssen-klaert-auf-folge-8-staffel-3-feiertage-und-freie-tage',
            'only_matching': True,
        },
    ]

    _TOKEN = 'prosieben'
    _SALT = '01!8d8F_)r9]4s[qeuXfP%'
    _CLIENT_NAME = 'kolibri-2.0.19-splec4'

    _ACCESS_ID = 'x_prosiebenmaxx-de'
    _ENCRYPTION_KEY = 'Eeyeey9oquahthainoofashoyoikosag'
    _IV = 'Aeluchoc6aevechuipiexeeboowedaok'

    _CLIPID_REGEXES = [
        r'"clip_id"\s*:\s+"(\d+)"',
        r'clipid: "(\d+)"',
        r'clip[iI]d=(\d+)',
        r'clip[iI][dD]\s*=\s*["\'](\d+)',
        r"'itemImageUrl'\s*:\s*'/dynamic/thumbnails/full/\d+/(\d+)",
        r'proMamsId&quot;\s*:\s*&quot;(\d+)',
        r'proMamsId"\s*:\s*"(\d+)',
    ]
    _TITLE_REGEXES = [
        r'<h2 class="subtitle" itemprop="name">\s*(.+?)</h2>',
        r'<header class="clearfix">\s*<h3>(.+?)</h3>',
        r'<!-- start video -->\s*<h1>(.+?)</h1>',
        r'<h1 class="att-name">\s*(.+?)</h1>',
        r'<header class="module_header">\s*<h2>([^<]+)</h2>\s*</header>',
        r'<h2 class="video-title" itemprop="name">\s*(.+?)</h2>',
        r'<div[^>]+id="veeseoTitle"[^>]*>(.+?)</div>',
        r'<h2[^>]+class="subtitle"[^>]*>([^<]+)</h2>',
    ]
    _DESCRIPTION_REGEXES = [
        r'<p itemprop="description">\s*(.+?)</p>',
        r'<div class="videoDecription">\s*<p><strong>Beschreibung</strong>: (.+?)</p>',
        r'<div class="g-plusone" data-size="medium"></div>\s*</div>\s*</header>\s*(.+?)\s*<footer>',
        r'<p class="att-description">\s*(.+?)\s*</p>',
        r'<p class="video-description" itemprop="description">\s*(.+?)</p>',
        r'<div[^>]+id="veeseoDescription"[^>]*>(.+?)</div>',
    ]
    _UPLOAD_DATE_REGEXES = [
        r'<span>\s*(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}) \|\s*<span itemprop="duration"',
        r'<footer>\s*(\d{2}\.\d{2}\.\d{4}) \d{2}:\d{2} Uhr',
        r'<span style="padding-left: 4px;line-height:20px; color:#404040">(\d{2}\.\d{2}\.\d{4})</span>',
        r'(\d{2}\.\d{2}\.\d{4}) \| \d{2}:\d{2} Min<br/>',
    ]
    _PAGE_TYPE_REGEXES = [
        r'<meta name="page_type" content="([^"]+)">',
        r"'itemType'\s*:\s*'([^']*)'",
    ]
    _PLAYLIST_ID_REGEXES = [
        r'content[iI]d=(\d+)',
        r"'itemId'\s*:\s*'([^']*)'",
    ]
    _PLAYLIST_CLIP_REGEXES = [
        r'(?s)data-qvt=.+?<a href="([^"]+)"',
    ]

    def _extract_clip(self, url, webpage):
        clip_id = self._html_search_regex(
            self._CLIPID_REGEXES, webpage, 'clip id')
        title = self._html_search_regex(
            self._TITLE_REGEXES, webpage, 'title',
            default=None) or self._og_search_title(webpage)
        info = self._extract_video_info(url, clip_id)
        description = self._html_search_regex(
            self._DESCRIPTION_REGEXES, webpage, 'description', default=None)
        if description is None:
            description = self._og_search_description(webpage)
        thumbnail = self._og_search_thumbnail(webpage)
        upload_date = unified_strdate(
            self._html_search_meta('og:published_time', webpage,
                                   'upload date', default=None)
            or self._html_search_regex(self._UPLOAD_DATE_REGEXES,
                                       webpage, 'upload date', default=None))

        json_ld = self._search_json_ld(webpage, clip_id, default={})

        return merge_dicts(info, {
            'id': clip_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
        }, json_ld)

    def _extract_playlist(self, url, webpage):
        playlist_id = self._html_search_regex(
            self._PLAYLIST_ID_REGEXES, webpage, 'playlist id')
        playlist = self._parse_json(
            self._search_regex(
                r'var\s+contentResources\s*=\s*(\[.+?\]);\s*</script',
                webpage, 'playlist'),
            playlist_id)
        entries = []
        for item in playlist:
            clip_id = item.get('id') or item.get('upc')
            if not clip_id:
                continue
            info = self._extract_video_info(url, clip_id)
            info.update({
                'id': clip_id,
                'title': item.get('title') or item.get('teaser', {}).get('headline'),
                'description': item.get('teaser', {}).get('description'),
                'thumbnail': item.get('poster'),
                'duration': float_or_none(item.get('duration')),
                'series': item.get('tvShowTitle'),
                'uploader': item.get('broadcastPublisher'),
            })
            entries.append(info)
        return self.playlist_result(entries, playlist_id)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        page_type = self._search_regex(
            self._PAGE_TYPE_REGEXES, webpage,
            'page type', default='clip').lower()
        if page_type == 'clip':
            return self._extract_clip(url, webpage)
        elif page_type == 'playlist':
            return self._extract_playlist(url, webpage)
        else:
            raise ExtractorError(
                'Unsupported page type %s' % page_type, expected=True)
