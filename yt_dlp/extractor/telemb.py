from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    float_or_none,
    int_or_none,
    mimetype2ext,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import find_element, traverse_obj


class TeleMBIE(InfoExtractor):
    IE_NAME = 'telemb'
    IE_DESC = 'Télé MB'

    _VALID_URL = r'https?://(?:www\.)?telemb\.be(?:/replay)?/(?:actu|emission|sports)(?P<alt_id>(?:/[\w-]+)+)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.telemb.be/actu/frameries-un-concours-pour-conducteurs-dengins-de-chantier/37879',
        'info_dict': {
            'id': '37879',
            'ext': 'mp4',
            'title': 'Frameries - Un concours pour conducteurs d\'engins de chantier',
            'creators': ['Sabine Dupont'],
            'description': 'md5:bfb8fdff559b64684bb005ce4901af12',
            'display_id': 'frameries-un-concours-pour-conducteurs-dengins-de-chantier',
            'duration': 144.6,
            'location': 'Frameries',
            'release_date': '20250515',
            'release_timestamp': 1747319520,
            'thumbnail': r're:https?://www\.telemb\.be/cdn.+\.(?:jpe?g|png)',
            'timestamp': 1747319229,
            'upload_date': '20250515',
        },
    }, {
        'url': 'https://www.telemb.be/sports/karate-cinq-karatekas-du-bushikai-wasmuel-la-coupe-du-monde-tokyo/37849',
        'info_dict': {
            'id': '37849',
            'ext': 'mp4',
            'title': 'Karaté : Cinq karatékas du Bushikai Wasmuel à la Coupe du Monde à Tokyo',
            'creators': ['Jacob Hemptinne'],
            'description': 'md5:82ebfa7a4ddd359c9e05b5a8c8ab04c5',
            'display_id': 'karate-cinq-karatekas-du-bushikai-wasmuel-la-coupe-du-monde-tokyo',
            'duration': 211.6,
            'location': 'Quaregnon',
            'release_date': '20250512',
            'release_timestamp': 1747066800,
            'thumbnail': r're:https?://www\.telemb\.be/cdn/.+\.(?:jpe?g|png)',
            'timestamp': 1746987989,
            'upload_date': '20250511',
        },
    }, {
        'url': 'https://www.telemb.be/replay/emission/les-infos/les-infos-16052025/36502',
        'info_dict': {
            'id': '36502',
            'ext': 'mp4',
            'title': 'Les Infos - 16/05/2025',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'display_id': 'les-infos-16052025',
            'duration': 1144.32,
            'release_date': '20250516',
            'release_timestamp': 1747412520,
            'thumbnail': r're:https?://www\.telemb\.be/cdn.+\.(?:jpe?g|png)',
            'timestamp': 1747408485,
            'upload_date': '20250516',
        },
    }, {
        'url': 'https://www.telemb.be/actu/linvite-des-infos/le-cma-de-jemappes-fetera-ses-20-ans-ce-week-end/36711',
        'info_dict': {
            'id': '36711',
            'ext': 'mp4',
            'title': 'Le CMA de Jemappes fêtera ses 20 ans ce week-end',
            'creators': ['Loélia Chais'],
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'display_id': 'le-cma-de-jemappes-fetera-ses-20-ans-ce-week-end',
            'duration': 316.08,
            'location': 'Mons',
            'release_date': '20241128',
            'release_timestamp': 1732787226,
            'thumbnail': r're:https?://www\.telemb\.be/cdn.+\.(?:jpe?g|png)',
            'timestamp': 1732727988,
            'upload_date': '20241127',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        display_id = self._match_valid_url(url).group('alt_id').split('/')[-1]
        webpage = self._download_webpage(url, video_id)

        player_info = traverse_obj(webpage, (
            {find_element(cls='freecaster-player', html=True)}, {extract_attributes}, {
                'id': ('data-video-id', {str_or_none}),
                'thumbnail': ('data-poster', {lambda x: self._proto_relative_url(x)}, {url_or_none}),
            },
        ))
        video_info = self._download_json(
            f'https://tvlocales-player-v12.freecaster.com/embed/{player_info.pop("id")}.json', video_id,
        ).get('video')

        qualities = {
            '3': (640, 360),
            '5': (960, 540),
            '9': (1280, 720),
            '11': (1920, 1080),
        }
        formats = []
        for src in traverse_obj(video_info, ('src', lambda _, v: v['src'])):
            src_url = src['src']
            ext = mimetype2ext(src.get('type'))

            if ext == 'mp4':
                quality = src_url.rpartition('_')[2].removesuffix('.mp4')
                width, height = qualities.get(quality)
                formats.append({
                    'acodec': 'mp4a.40.2',
                    'ext': ext,
                    'format_id': f'mp4-{quality}',
                    'height': height,
                    'url': src_url,
                    'vcodec': 'avc1',
                    'width': width,
                })
                continue
            elif ext == 'm3u8':
                fmts = self._extract_m3u8_formats(
                    src_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
                for fmt in fmts:
                    if fmt.get('vcodec') == 'none':
                        fmt.update({
                            'abr': int_or_none(self._search_regex(
                                r'-(\d+)-', fmt['format_id'], 'adaptive bit rate')),
                            'acodec': 'mp4a.40.2',
                            'ext': 'm4a',
                        })
            elif ext == 'mpd':
                fmts = self._extract_mpd_formats(
                    src_url, video_id, mpd_id='dash', fatal=False)
            else:
                self.report_warning(f'Unsupported stream type: {ext}')
                continue
            formats.extend(fmts)

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            **player_info,
            **traverse_obj(webpage, {
                'creator': ({find_element(cls='content-author')}, {clean_html}),
                'location': ({find_element(cls='content-location')}, {clean_html}),
            }),
            **traverse_obj(self._search_json_ld(webpage, video_id), {
                'title': ('title', {clean_html}),
                'description': ('description', {clean_html}),
                'release_timestamp': ('timestamp', {int_or_none}),
            }),
            **traverse_obj(video_info, {
                'duration': ('duration', {float_or_none}),
                'timestamp': ('published_at', {parse_iso8601}),
            }),
        }
