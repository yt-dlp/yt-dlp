import re

from .common import InfoExtractor, ExtractorError
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    float_or_none,
    js_to_json,
    mimetype2ext,
    traverse_obj,
    urljoin,
    url_or_none,
)


class RTVCPlayBaseIE(InfoExtractor):
    _BASE_VALID_URL = r'https?://(?:www\.)?rtvcplay\.co'

    def _extract_player_config(self, webpage, video_id):
        return self._search_json(
            r'<script\b[^>]*>[^<]*(?:var|let|const)\s+config\s*=', re.sub(r'"\s*\+\s*"', '', webpage),
            'player_config', video_id, transform_source=js_to_json)

    def _extract_formats_and_subtitles_player_config(self, player_config, video_id):
        formats, subtitles = [], {}
        for source in traverse_obj(player_config, ('sources', ..., lambda _, v: url_or_none(v['url']))):
            ext = mimetype2ext(source.get('mimetype'), default=determine_ext(source['url']))
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    source['url'], video_id, 'mp4', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': source['url'],
                    'ext': ext,
                })

        return formats, subtitles


class RTVCPlayIE(RTVCPlayBaseIE):
    _VALID_URL = RTVCPlayBaseIE._BASE_VALID_URL + r'/(?P<category>(?!embed)[^/]+)/(?:[^?#]+/)?(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://www.rtvcplay.co/en-vivo/canal-institucional',
        'info_dict': {
            'id': 'canal-institucional',
            'title': r're:^Canal Institucional',
            'description': 'md5:eff9e548394175928059320c006031ea',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'live_status': 'is_live',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.rtvcplay.co/en-vivo/senal-colombia',
        'info_dict': {
            'id': 'senal-colombia',
            'title': r're:^Señal Colombia',
            'description': 'md5:799f16a401d97f40c33a2c6a3e2a507b',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'live_status': 'is_live',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.rtvcplay.co/en-vivo/radio-nacional',
        'info_dict': {
            'id': 'radio-nacional',
            'title': r're:^Radio Nacional',
            'description': 'md5:5de009bc6a9fa79d2a6cf0b73f977d53',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'live_status': 'is_live',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }, {
        'url': 'https://www.rtvcplay.co/peliculas-ficcion/senoritas',
        'md5': '1288ee6f6d1330d880f98bff2ed710a3',
        'info_dict': {
            'id': 'senoritas',
            'title': 'Señoritas',
            'description': 'md5:f095a2bb52cb6cf279daf6302f86fb32',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.rtvcplay.co/competencias-basicas-ciudadanas-y-socioemocionales/profe-en-tu-casa/james-regresa-clases-28022022',
        'md5': 'f040a7380a269ad633cf837384d5e9fc',
        'info_dict': {
            'id': 'james-regresa-clases-28022022',
            'title': 'James regresa a clases - 28/02/2022',
            'description': 'md5:c5dcdf757c7ab29305e8763c6007e675',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.rtvcplay.co/peliculas-documentales/llinas-el-cerebro-y-el-universo',
        'info_dict': {
            'id': 'llinas-el-cerebro-y-el-universo',
            'title': 'Llinás, el cerebro y el universo',
            'description': 'md5:add875bf2309bb52b3e8b9b06116d9b0',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'https://www.rtvcplay.co/competencias-basicas-ciudadanas-y-socioemocionales/profe-en-tu-casa',
        'info_dict': {
            'id': 'profe-en-tu-casa',
            'title': 'Profe en tu casa',
            'description': 'md5:47dbe20e263194413b1db2a2805a4f2e',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'playlist_mincount': 537,
    }, {
        'url': 'https://www.rtvcplay.co/series-al-oido/relato-de-un-naufrago-una-travesia-del-periodismo-a-la-literatura',
        'info_dict': {
            'id': 'relato-de-un-naufrago-una-travesia-del-periodismo-a-la-literatura',
            'title': 'Relato de un náufrago: una travesía del periodismo a la literatura',
            'description': 'md5:6da28fdca4a5a568ea47ef65ef775603',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'playlist_mincount': 5,
    }, {
        'url': 'https://www.rtvcplay.co/series-al-oido/diez-versiones',
        'info_dict': {
            'id': 'diez-versiones',
            'title': 'Diez versiones',
            'description': 'md5:997471ed971cb3fd8e41969457675306',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'playlist_mincount': 20,
    }]

    def _real_extract(self, url):
        video_id, category = self._match_valid_url(url).group('id', 'category')
        webpage = self._download_webpage(url, video_id)

        hydration = self._search_json(
            r'window\.__RTVCPLAY_STATE__\s*=', webpage, 'hydration',
            video_id, transform_source=js_to_json)['content']['currentContent']

        asset_id = traverse_obj(hydration, ('video', 'assetid'))
        if asset_id:
            hls_url = hydration['base_url_hls'].replace('[node:field_asset_id]', asset_id)
        else:
            hls_url = traverse_obj(hydration, ('channel', 'hls'))

        metadata = traverse_obj(hydration, {
            'title': 'title',
            'description': 'description',
            'thumbnail': ((('channel', 'image', 'logo'), ('resource', 'image', 'cover_desktop')), 'path'),
        }, get_all=False)

        # Probably it's a program's page
        if not hls_url:
            seasons = traverse_obj(
                hydration, ('widgets', lambda _, y: y['type'] == 'seasonList', 'contents'),
                get_all=False)
            if not seasons:
                podcast_episodes = hydration.get('audios')
                if not podcast_episodes:
                    raise ExtractorError('Could not find asset_id nor program playlist nor podcast episodes')

                return self.playlist_result([
                    self.url_result(episode['file'], url_transparent=True, **traverse_obj(episode, {
                        'title': 'title',
                        'description': ('description', {clean_html}),
                        'episode_number': ('chapter_number', {float_or_none}, {int_or_none}),
                        'season_number': ('season', {int_or_none}),
                    })) for episode in podcast_episodes], video_id, **metadata)

            entries = [self.url_result(
                urljoin(url, episode['slug']), url_transparent=True,
                **traverse_obj(season, {
                    'season': 'title',
                    'season_number': ('season', {int_or_none}),
                }), **traverse_obj(episode, {
                    'title': 'title',
                    'thumbnail': ('image', 'cover', 'path'),
                    'episode_number': ('chapter_number', {int_or_none}),
                })) for season in seasons for episode in traverse_obj(season, ('contents', ...))]

            return self.playlist_result(entries, video_id, **metadata)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(hls_url, video_id, 'mp4')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': category == 'en-vivo',
            **metadata,
        }


class RTVCPlayEmbedIE(RTVCPlayBaseIE):
    _VALID_URL = RTVCPlayBaseIE._BASE_VALID_URL + r'/embed/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://www.rtvcplay.co/embed/72b0e699-248b-4929-a4a8-3782702fa7f9',
        'md5': 'ed529aeaee7aa2a72afe91ac7d1177a8',
        'info_dict': {
            'id': '72b0e699-248b-4929-a4a8-3782702fa7f9',
            'title': 'Tráiler: Señoritas',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'ext': 'mp4',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        player_config = self._extract_player_config(webpage, video_id)
        formats, subtitles = self._extract_formats_and_subtitles_player_config(player_config, video_id)

        asset_id = traverse_obj(player_config, ('rtvcplay', 'assetid'))
        metadata = {} if not asset_id else self._download_json(
            f'https://cms.rtvcplay.co/api/v1/video/asset-id/{asset_id}', video_id, fatal=False)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(metadata, {
                'title': 'title',
                'description': 'description',
                'thumbnail': ('image', ..., 'thumbnail', 'path'),
            }, get_all=False)
        }


class RTVCKalturaIE(RTVCPlayBaseIE):
    _VALID_URL = r'https?://media\.rtvc\.gov\.co/kalturartvc/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://media.rtvc.gov.co/kalturartvc/indexSC.html',
        'info_dict': {
            'id': 'indexSC',
            'title': r're:^Señal Colombia',
            'description': 'md5:799f16a401d97f40c33a2c6a3e2a507b',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'live_status': 'is_live',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': 'Livestream',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        player_config = self._extract_player_config(webpage, video_id)
        formats, subtitles = self._extract_formats_and_subtitles_player_config(player_config, video_id)

        channel_id = traverse_obj(player_config, ('rtvcplay', 'channelId'))
        metadata = {} if not channel_id else self._download_json(
            f'https://cms.rtvcplay.co/api/v1/taxonomy_term/streaming/{channel_id}', video_id, fatal=False)

        fmts, subs = self._extract_m3u8_formats_and_subtitles(
            traverse_obj(metadata, ('channel', 'hls')), video_id, 'mp4', fatal=False)
        formats.extend(fmts)
        self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            **traverse_obj(metadata, {
                'title': 'title',
                'description': 'description',
                'thumbnail': ('channel', 'image', 'logo', 'path'),
            })
        }
