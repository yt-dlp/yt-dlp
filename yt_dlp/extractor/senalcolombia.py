from .common import InfoExtractor
from ..utils import js_to_json, traverse_obj


class SenalColombiaLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?senalcolombia\.tv/(?P<id>senal-en-vivo)'

    _TESTS = [{
        'url': 'https://www.senalcolombia.tv/senal-en-vivo',
        'info_dict': {
            'id': 'senal-en-vivo',
            'title': 're:^Señal Colombia',
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

        player_webpage = self._download_webpage(
            'https://media.rtvc.gov.co/kalturartvc/indexSC.html', video_id)

        player_config = self._search_json(
            r'<script\b[^>]*>[^<]*(?:var|let|const)\s+config\s*=', player_webpage, 'player_config', video_id,
            transform_source=js_to_json)

        # player_js = self._download_webpage(
        #     'https://media.rtvc.gov.co/kalturartvc/kaltura-ovp-playerv2.1.js', video_id,
        #     transform_source=js_to_json,fatal=False)

        # function verifyChannelLiveInfo(channelid, urlbase) {
        #   var url = environment() + '/api/v1/taxonomy_term/streaming/' + channelid;
        #   return fetch(url, {
        #     method: 'GET', // or 'PUT'
        #     headers: {
        #       'Content-Type': 'application/json'
        #     }
        #   }).then(function (res) {
        #     return res.json();
        #   }).catch(function (error) {
        #     return console.error('Error:', error);
        #   });
        # }

        channel_id = traverse_obj(player_config, ('rtvcplay', 'channelId')) or 68
        channel_data = self._download_json(
            f'https://cms.rtvcplay.co/api/v1/taxonomy_term/streaming/{channel_id}', video_id, fatal=False)

        formats, subtitles = [], {}
        for source_type in traverse_obj(player_config, 'sources') or ():
            for media_source in traverse_obj(player_config, ('sources', source_type)) or ():
                if source_type == 'hls':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        media_source.get('url'), video_id, 'mp4', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                else:
                    formats.append({
                        'url': media_source.get('url'),
                    })

        fmts, subs = self._extract_m3u8_formats_and_subtitles(
            traverse_obj(channel_data, ('channel', 'hls')), video_id, 'mp4', fatal=False)
        formats.extend(fmts)
        self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
            **traverse_obj(channel_data, {
                'title': ('title', ('channel', 'title')),
                'description': ('description', ('channel', 'description')),
                'thumbnail': ('channel', 'image', 'logo', 'path'),
            }),
        }
