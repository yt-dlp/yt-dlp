import re

from .srgssr import SRGSSRIE
from ..compat import compat_str
from ..utils import (
    determine_ext,
    int_or_none,
    parse_duration,
    parse_iso8601,
    unescapeHTML,
    urljoin,
)


class RTSIE(SRGSSRIE):  # XXX: Do not subclass from concrete IE
    _WORKING = False
    IE_DESC = 'RTS.ch'
    _VALID_URL = r'rts:(?P<rts_id>\d+)|https?://(?:.+?\.)?rts\.ch/(?:[^/]+/){2,}(?P<id>[0-9]+)-(?P<display_id>.+?)\.html'

    _TESTS = [
        {
            'url': 'http://www.rts.ch/archives/tv/divers/3449373-les-enfants-terribles.html',
            'md5': '753b877968ad8afaeddccc374d4256a5',
            'info_dict': {
                'id': '3449373',
                'display_id': 'les-enfants-terribles',
                'ext': 'mp4',
                'duration': 1488,
                'title': 'Les Enfants Terribles',
                'description': 'France Pommier et sa soeur Luce Feral, les deux filles de ce groupe de 5.',
                'uploader': 'Divers',
                'upload_date': '19680921',
                'timestamp': -40280400,
                'thumbnail': r're:^https?://.*\.image',
                'view_count': int,
            },
            'expected_warnings': ['Unable to download f4m manifest', 'Failed to download m3u8 information'],
        },
        {
            'url': 'http://www.rts.ch/emissions/passe-moi-les-jumelles/5624067-entre-ciel-et-mer.html',
            'info_dict': {
                'id': '5624065',
                'title': 'Passe-moi les jumelles',
            },
            'playlist_mincount': 4,
        },
        {
            'url': 'http://www.rts.ch/video/sport/hockey/5745975-1-2-kloten-fribourg-5-2-second-but-pour-gotteron-par-kwiatowski.html',
            'info_dict': {
                'id': '5745975',
                'display_id': '1-2-kloten-fribourg-5-2-second-but-pour-gotteron-par-kwiatowski',
                'ext': 'mp4',
                'duration': 48,
                'title': '1/2, Kloten - Fribourg (5-2): second but pour Gottéron par Kwiatowski',
                'description': 'Hockey - Playoff',
                'uploader': 'Hockey',
                'upload_date': '20140403',
                'timestamp': 1396556882,
                'thumbnail': r're:^https?://.*\.image',
                'view_count': int,
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
            'expected_warnings': ['Unable to download f4m manifest', 'Failed to download m3u8 information'],
            'skip': 'Blocked outside Switzerland',
        },
        {
            'url': 'http://www.rts.ch/video/info/journal-continu/5745356-londres-cachee-par-un-epais-smog.html',
            'md5': '9bb06503773c07ce83d3cbd793cebb91',
            'info_dict': {
                'id': '5745356',
                'display_id': 'londres-cachee-par-un-epais-smog',
                'ext': 'mp4',
                'duration': 33,
                'title': 'Londres cachée par un épais smog',
                'description': 'Un important voile de smog recouvre Londres depuis mercredi, provoqué par la pollution et du sable du Sahara.',
                'uploader': 'L\'actu en vidéo',
                'upload_date': '20140403',
                'timestamp': 1396537322,
                'thumbnail': r're:^https?://.*\.image',
                'view_count': int,
            },
            'expected_warnings': ['Unable to download f4m manifest', 'Failed to download m3u8 information'],
        },
        {
            'url': 'http://www.rts.ch/audio/couleur3/programmes/la-belle-video-de-stephane-laurenceau/5706148-urban-hippie-de-damien-krisl-03-04-2014.html',
            'md5': 'dd8ef6a22dff163d063e2a52bc8adcae',
            'info_dict': {
                'id': '5706148',
                'display_id': 'urban-hippie-de-damien-krisl-03-04-2014',
                'ext': 'mp3',
                'duration': 123,
                'title': '"Urban Hippie", de Damien Krisl',
                'description': 'Des Hippies super glam.',
                'upload_date': '20140403',
                'timestamp': 1396551600,
            },
        },
        {
            # article with videos on rhs
            'url': 'http://www.rts.ch/sport/hockey/6693917-hockey-davos-decroche-son-31e-titre-de-champion-de-suisse.html',
            'info_dict': {
                'id': '6693917',
                'title': 'Hockey: Davos décroche son 31e titre de champion de Suisse',
            },
            'playlist_mincount': 5,
        },
        {
            'url': 'http://pages.rts.ch/emissions/passe-moi-les-jumelles/5624065-entre-ciel-et-mer.html',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        media_id = m.group('rts_id') or m.group('id')
        display_id = m.group('display_id') or media_id

        def download_json(internal_id):
            return self._download_json(
                'http://www.rts.ch/a/%s.html?f=json/article' % internal_id,
                display_id)

        all_info = download_json(media_id)

        # media_id extracted out of URL is not always a real id
        if 'video' not in all_info and 'audio' not in all_info:
            entries = []

            for item in all_info.get('items', []):
                item_url = item.get('url')
                if not item_url:
                    continue
                entries.append(self.url_result(item_url, 'RTS'))

            if not entries:
                page, urlh = self._download_webpage_handle(url, display_id)
                if re.match(self._VALID_URL, urlh.url).group('id') != media_id:
                    return self.url_result(urlh.url, 'RTS')

                # article with videos on rhs
                videos = re.findall(
                    r'<article[^>]+class="content-item"[^>]*>\s*<a[^>]+data-video-urn="urn:([^"]+)"',
                    page)
                if not videos:
                    videos = re.findall(
                        r'(?s)<iframe[^>]+class="srg-player"[^>]+src="[^"]+urn:([^"]+)"',
                        page)
                if videos:
                    entries = [self.url_result('srgssr:%s' % video_urn, 'SRGSSR') for video_urn in videos]

            if entries:
                return self.playlist_result(entries, media_id, all_info.get('title'))

            internal_id = self._html_search_regex(
                r'<(?:video|audio) data-id="([0-9]+)"', page,
                'internal video id')
            all_info = download_json(internal_id)

        media_type = 'video' if 'video' in all_info else 'audio'

        # check for errors
        self._get_media_data('rts', media_type, media_id)

        info = all_info['video']['JSONinfo'] if 'video' in all_info else all_info['audio']

        title = info['title']

        def extract_bitrate(url):
            return int_or_none(self._search_regex(
                r'-([0-9]+)k\.', url, 'bitrate', default=None))

        formats = []
        streams = info.get('streams', {})
        for format_id, format_url in streams.items():
            if format_id == 'hds_sd' and 'hds' in streams:
                continue
            if format_id == 'hls_sd' and 'hls' in streams:
                continue
            ext = determine_ext(format_url)
            if ext in ('m3u8', 'f4m'):
                format_url = self._get_tokenized_src(format_url, media_id, format_id)
                if ext == 'f4m':
                    formats.extend(self._extract_f4m_formats(
                        format_url + ('?' if '?' not in format_url else '&') + 'hdcore=3.4.0',
                        media_id, f4m_id=format_id, fatal=False))
                else:
                    formats.extend(self._extract_m3u8_formats(
                        format_url, media_id, 'mp4', 'm3u8_native', m3u8_id=format_id, fatal=False))
            else:
                formats.append({
                    'format_id': format_id,
                    'url': format_url,
                    'tbr': extract_bitrate(format_url),
                })

        download_base = 'http://rtsww%s-d.rts.ch/' % ('-a' if media_type == 'audio' else '')
        for media in info.get('media', []):
            media_url = media.get('url')
            if not media_url or re.match(r'https?://', media_url):
                continue
            rate = media.get('rate')
            ext = media.get('ext') or determine_ext(media_url, 'mp4')
            format_id = ext
            if rate:
                format_id += '-%dk' % rate
            formats.append({
                'format_id': format_id,
                'url': urljoin(download_base, media_url),
                'tbr': rate or extract_bitrate(media_url),
            })

        self._check_formats(formats, media_id)

        duration = info.get('duration') or info.get('cutout') or info.get('cutduration')
        if isinstance(duration, compat_str):
            duration = parse_duration(duration)

        return {
            'id': media_id,
            'display_id': display_id,
            'formats': formats,
            'title': title,
            'description': info.get('intro'),
            'duration': duration,
            'view_count': int_or_none(info.get('plays')),
            'uploader': info.get('programName'),
            'timestamp': parse_iso8601(info.get('broadcast_date')),
            'thumbnail': unescapeHTML(info.get('preview_image_url')),
        }
