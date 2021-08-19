# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_urlencode,
)
from ..utils import (
    clean_html,
    int_or_none,
    parse_duration,
    parse_iso8601,
    qualities,
    update_url_query,
)


class UOLIE(InfoExtractor):
    IE_NAME = 'uol.com.br'
    _VALID_URL = r'https?://(?:.+?\.)?uol\.com\.br/.*?(?:(?:mediaId|v)=|view/(?:[a-z0-9]+/)?|video(?:=|/(?:\d{4}/\d{2}/\d{2}/)?))(?P<id>\d+|[\w-]+-[A-Z0-9]+)'
    _TESTS = [{
        'url': 'http://player.mais.uol.com.br/player_video_v3.swf?mediaId=15951931',
        'md5': '4f1e26683979715ff64e4e29099cf020',
        'info_dict': {
            'id': '15951931',
            'ext': 'mp4',
            'title': 'Miss simpatia é encontrada morta',
            'description': 'md5:3f8c11a0c0556d66daf7e5b45ef823b2',
            'timestamp': 1470421860,
            'upload_date': '20160805',
        }
    }, {
        'url': 'http://tvuol.uol.com.br/video/incendio-destroi-uma-das-maiores-casas-noturnas-de-londres-04024E9A3268D4C95326',
        'md5': '2850a0e8dfa0a7307e04a96c5bdc5bc2',
        'info_dict': {
            'id': '15954259',
            'ext': 'mp4',
            'title': 'Incêndio destrói uma das maiores casas noturnas de Londres',
            'description': 'Em Londres, um incêndio destruiu uma das maiores boates da cidade. Não há informações sobre vítimas.',
            'timestamp': 1470674520,
            'upload_date': '20160808',
        }
    }, {
        'url': 'http://mais.uol.com.br/static/uolplayer/index.html?mediaId=15951931',
        'only_matching': True,
    }, {
        'url': 'http://mais.uol.com.br/view/15954259',
        'only_matching': True,
    }, {
        'url': 'http://noticias.band.uol.com.br/brasilurgente/video/2016/08/05/15951931/miss-simpatia-e-encontrada-morta.html',
        'only_matching': True,
    }, {
        'url': 'http://videos.band.uol.com.br/programa.asp?e=noticias&pr=brasil-urgente&v=15951931&t=Policia-desmonte-base-do-PCC-na-Cracolandia',
        'only_matching': True,
    }, {
        'url': 'http://mais.uol.com.br/view/cphaa0gl2x8r/incendio-destroi-uma-das-maiores-casas-noturnas-de-londres-04024E9A3268D4C95326',
        'only_matching': True,
    }, {
        'url': 'http://noticias.uol.com.br//videos/assistir.htm?video=rafaela-silva-inspira-criancas-no-judo-04024D983968D4C95326',
        'only_matching': True,
    }, {
        'url': 'http://mais.uol.com.br/view/e0qbgxid79uv/15275470',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_data = self._download_json(
            # https://api.mais.uol.com.br/apiuol/v4/player/data/[MEDIA_ID]
            'https://api.mais.uol.com.br/apiuol/v3/media/detail/' + video_id,
            video_id)['item']
        media_id = compat_str(video_data['mediaId'])
        title = video_data['title']
        ver = video_data.get('revision', 2)

        uol_formats = self._download_json(
            'https://croupier.mais.uol.com.br/v3/formats/%s/jsonp' % media_id,
            media_id)
        quality = qualities(['mobile', 'WEBM', '360p', '720p', '1080p'])
        formats = []
        for format_id, f in uol_formats.items():
            if not isinstance(f, dict):
                continue
            f_url = f.get('url') or f.get('secureUrl')
            if not f_url:
                continue
            query = {
                'ver': ver,
                'r': 'http://mais.uol.com.br',
            }
            for k in ('token', 'sign'):
                v = f.get(k)
                if v:
                    query[k] = v
            f_url = update_url_query(f_url, query)
            format_id = format_id
            if format_id == 'HLS':
                m3u8_formats = self._extract_m3u8_formats(
                    f_url, media_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False)
                encoded_query = compat_urllib_parse_urlencode(query)
                for m3u8_f in m3u8_formats:
                    m3u8_f['extra_param_to_segment_url'] = encoded_query
                    m3u8_f['url'] = update_url_query(m3u8_f['url'], query)
                formats.extend(m3u8_formats)
                continue
            formats.append({
                'format_id': format_id,
                'url': f_url,
                'quality': quality(format_id),
            })
        self._sort_formats(formats)

        tags = []
        for tag in video_data.get('tags', []):
            tag_description = tag.get('description')
            if not tag_description:
                continue
            tags.append(tag_description)

        thumbnails = []
        for q in ('Small', 'Medium', 'Wmedium', 'Large', 'Wlarge', 'Xlarge'):
            q_url = video_data.get('thumb' + q)
            if not q_url:
                continue
            thumbnails.append({
                'id': q,
                'url': q_url,
            })

        return {
            'id': media_id,
            'title': title,
            'description': clean_html(video_data.get('description')),
            'thumbnails': thumbnails,
            'duration': parse_duration(video_data.get('duration')),
            'tags': tags,
            'formats': formats,
            'timestamp': parse_iso8601(video_data.get('publishDate'), ' '),
            'view_count': int_or_none(video_data.get('viewsQtty')),
        }
