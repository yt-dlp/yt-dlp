import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    extract_attributes,
    js_to_json,
    mimetype2ext,
    unified_strdate,
    url_or_none,
    urljoin,
)
from ..utils.traversal import find_element, traverse_obj


class TVNoeIE(InfoExtractor):
    IE_NAME = 'tvnoe'
    IE_DESC = 'Televize Noe'

    _VALID_URL = r'https?://(?:www\.)?tvnoe\.cz/porad/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.tvnoe.cz/porad/43216-outdoor-films-s-mudr-tomasem-kempnym-pomahat-potrebnym-nejen-u-nas',
        'info_dict': {
            'id': '43216-outdoor-films-s-mudr-tomasem-kempnym-pomahat-potrebnym-nejen-u-nas',
            'ext': 'mp4',
            'title': 'Pomáhat potřebným nejen u nás',
            'description': 'md5:78b538ee32f7e881ec23b9c278a0ff3a',
            'release_date': '20250531',
            'series': 'Outdoor Films s MUDr. Tomášem Kempným',
            'thumbnail': r're:https?://www\.tvnoe\.cz/.+\.jpg',
        },
    }, {
        'url': 'https://www.tvnoe.cz/porad/43205-zamysleni-tomase-halika-7-nedele-velikonocni',
        'info_dict': {
            'id': '43205-zamysleni-tomase-halika-7-nedele-velikonocni',
            'ext': 'mp4',
            'title': '7. neděle velikonoční',
            'description': 'md5:6bb9908efc59abe60e1c8c7c0e9bb6cd',
            'release_date': '20250531',
            'series': 'Zamyšlení Tomáše Halíka',
            'thumbnail': r're:https?://www\.tvnoe\.cz/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player = self._search_json(
            r'var\s+INIT_PLAYER\s*=', webpage, 'init player',
            video_id, transform_source=js_to_json)

        formats = []
        for source in traverse_obj(player, ('tracks', ..., lambda _, v: url_or_none(v['src']))):
            src_url = source['src']
            ext = mimetype2ext(source.get('type'))
            if ext == 'm3u8':
                fmts = self._extract_m3u8_formats(
                    src_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            elif ext == 'mpd':
                fmts = self._extract_mpd_formats(
                    src_url, video_id, mpd_id='dash', fatal=False)
            else:
                self.report_warning(f'Unsupported stream type: {ext}')
                continue
            formats.extend(fmts)

        return {
            'id': video_id,
            'description': clean_html(self._search_regex(
                r'<p\s+class="">(.+?)</p>', webpage, 'description', default=None)),
            'formats': formats,
            **traverse_obj(webpage, {
                'title': ({find_element(tag='h2')}, {clean_html}),
                'release_date': (
                    {clean_html}, {re.compile(r'Premiéra:\s*(\d{1,2}\.\d{1,2}\.\d{4})').findall},
                    ..., {str}, {unified_strdate}, any),
                'series': ({find_element(tag='h1')}, {clean_html}),
                'thumbnail': (
                    {find_element(id='player-live', html=True)}, {extract_attributes},
                    'poster', {urljoin('https://www.tvnoe.cz/')}),
            }),
        }
