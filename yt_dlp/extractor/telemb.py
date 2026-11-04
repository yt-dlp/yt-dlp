import itertools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
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
            'description': 'md5:1dc04a3aa56c5228503071baa8b4cc97',
            'display_id': 'frameries-un-concours-pour-conducteurs-dengins-de-chantier',
            'duration': 144.6,
            'location': 'Frameries',
            'release_date': '20250515',
            'release_timestamp': 1747319520,
            'thumbnail': r're:https?://www\.telemb\.be/cdn.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://www.telemb.be/sports/karate-cinq-karatekas-du-bushikai-wasmuel-la-coupe-du-monde-tokyo/37849',
        'info_dict': {
            'id': '37849',
            'ext': 'mp4',
            'title': 'Karaté : Cinq karatékas du Bushikai Wasmuel à la Coupe du Monde à Tokyo',
            'creators': ['Jacob Hemptinne'],
            'description': 'md5:17f2d55a1533a69079cc21eadd14725f',
            'display_id': 'karate-cinq-karatekas-du-bushikai-wasmuel-la-coupe-du-monde-tokyo',
            'duration': 211.6,
            'location': 'Quaregnon',
            'release_date': '20250512',
            'release_timestamp': 1747066800,
            'thumbnail': r're:https?://www\.telemb\.be/cdn/.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://www.telemb.be/replay/emission/les-infos/les-infos-16052025/36502',
        'info_dict': {
            'id': '36502',
            'ext': 'mp4',
            'title': 'Les Infos - 16/05/2025',
            'creators': ['Télé MB'],
            'description': 'md5:dff75a3a51c769696c23454e932ff720',
            'display_id': 'les-infos-16052025',
            'duration': 1144.32,
            'release_date': '20250516',
            'release_timestamp': 1747412520,
            'thumbnail': r're:https?://www\.telemb\.be/cdn.+\.(?:jpe?g|png)',
        },
    }, {
        'url': 'https://www.telemb.be/actu/linvite-des-infos/le-cma-de-jemappes-fetera-ses-20-ans-ce-week-end/36711',
        'info_dict': {
            'id': '36711',
            'ext': 'mp4',
            'title': 'Le CMA de Jemappes fêtera ses 20 ans ce week-end',
            'creators': ['Loélia Chais'],
            'description': 'md5:f244efcce22f217df044d755e116ddef',
            'display_id': 'le-cma-de-jemappes-fetera-ses-20-ans-ce-week-end',
            'duration': 316.08,
            'location': 'Mons',
            'release_date': '20241128',
            'release_timestamp': 1732787226,
            'thumbnail': r're:https?://www\.telemb\.be/cdn.+\.(?:jpe?g|png)',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        display_id = self._match_valid_url(url).group('alt_id').split('/')[-1]
        webpage = self._download_webpage(url, video_id)
        json_ld = next(itertools.islice(self._yield_json_ld(webpage, video_id), 1, 2), {})

        data_video_id = traverse_obj(webpage, (
            {find_element(cls='freecaster-player', html=True)},
            {extract_attributes}, 'data-video-id', {str_or_none}))
        if not (video_info := traverse_obj(self._download_json(
            f'https://tvlocales-player-v12.freecaster.com/embed/{data_video_id}.json', video_id,
        ), ('video', {dict}), default={})):
            raise ExtractorError('Failed to fetch video information')

        qualities = {
            '3': (640, 360),
            '5': (960, 540),
            '9': (1280, 720),
            '11': (1920, 1080),
        }
        formats = []
        for src in traverse_obj(video_info, ('src', lambda _, v: v['src'])):
            if not (src_url := url_or_none(src['src'])):
                continue
            ext = mimetype2ext(src.get('type'))

            if ext == 'mp4':
                quality = src_url.rpartition('_')[2].removesuffix('.mp4')
                width, height = qualities.get(quality, (None, None))
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
            'duration': traverse_obj(video_info, ('duration', {float_or_none})),
            'formats': formats,
            'location': traverse_obj(webpage, (
                {find_element(cls='content-location')}, {clean_html})),
            **traverse_obj(json_ld, {
                'title': ('headline', {clean_html}),
                'creator': ('author', 'name', {clean_html}),
                'description': ('description', {clean_html}),
                'release_timestamp': ('datePublished', {parse_iso8601}),
                'thumbnail': ('image', ..., {lambda x: self._proto_relative_url(x)}, {url_or_none}, any),
            }),
        }
