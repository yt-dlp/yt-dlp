import json
import re

from .common import InfoExtractor
from .jwplatform import JWPlatformIE
from ..utils import (
    determine_ext,
    js_to_json,
    url_or_none,
)
from ..utils.traversal import find_element, traverse_obj


class TV2DKIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:
                            tvsyd|
                            tv2ostjylland|
                            tvmidtvest|
                            tv2fyn|
                            tv2east|
                            tv2lorry|
                            tv2nord|
                            tv2kosmopol
                        )\.dk/
                        (?:[^/?#]+/)*
                        (?P<id>[^/?\#&]+)
                    '''
    _TESTS = [{
        'url': 'https://www.tvsyd.dk/nyheder/28-10-2019/1930/1930-28-okt-2019?autoplay=1#player',
        'info_dict': {
            'id': 'sPp5z21q',
            'ext': 'mp4',
            'title': '19:30 - 28. okt. 2019',
            'description': '',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/sPp5z21q/poster.jpg?width=720',
            'timestamp': 1572287400,
            'upload_date': '20191028',
        },
    }, {
        'url': 'https://www.tv2lorry.dk/gadekamp/gadekamp-6-hoejhuse-i-koebenhavn',
        'info_dict': {
            'id': 'oD9cyq0m',
            'ext': 'mp4',
            'title': 'Gadekamp #6 - Højhuse i København',
            'description': '',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/oD9cyq0m/poster.jpg?width=720',
            'timestamp': 1635348600,
            'upload_date': '20211027',
        },
    }, {
        'url': 'https://www.tvsyd.dk/haderslev/x-factor-brodre-fulde-af-selvtillid-er-igen-hjemme-hos-mor-vores-diagnoser-har-vaeret-en-fordel',
        'info_dict': {
            'id': 'x-factor-brodre-fulde-af-selvtillid-er-igen-hjemme-hos-mor-vores-diagnoser-har-vaeret-en-fordel',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://www.tv2ostjylland.dk/aarhus/dom-kan-fa-alvorlige-konsekvenser',
        'info_dict': {
            'id': 'dom-kan-fa-alvorlige-konsekvenser',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://www.tv2ostjylland.dk/artikel/minister-gaar-ind-i-sag-om-diabetes-teknologi',
        'only_matching': True,
    }, {
        'url': 'https://www.tv2ostjylland.dk/nyheder/28-10-2019/22/2200-nyhederne-mandag-d-28-oktober-2019?autoplay=1#player',
        'only_matching': True,
    }, {
        'url': 'https://www.tvmidtvest.dk/nyheder/27-10-2019/1930/1930-27-okt-2019',
        'only_matching': True,
    }, {
        'url': 'https://www.tv2fyn.dk/artikel/fyn-kan-faa-landets-foerste-fabrik-til-groent-jetbraendstof',
        'only_matching': True,
    }, {
        'url': 'https://www.tv2east.dk/artikel/gods-faar-indleveret-tonsvis-af-aebler-100-kilo-aebler-gaar-til-en-aeblebrandy',
        'only_matching': True,
    }, {
        'url': 'https://www.tv2lorry.dk/koebenhavn/rasmus-paludan-evakueret-til-egen-demonstration#player',
        'only_matching': True,
    }, {
        'url': 'https://www.tv2nord.dk/artikel/dybt-uacceptabelt',
        'only_matching': True,
    }, {
        'url': 'https://www.tv2kosmopol.dk/metropolen/chaufforer-beordres-til-at-kore-videre-i-ulovlige-busser-med-rode-advarselslamper',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        search_space = traverse_obj(webpage, {find_element(tag='article')}) or webpage

        player_ids = traverse_obj(
            re.findall(r'x-data="(?:video_player|simple_player)\(({[^"]+})', search_space),
            (..., {js_to_json}, {json.loads}, ('jwpMediaId', 'videoId'), {str}))

        return self.playlist_from_matches(
            player_ids, video_id, getter=lambda x: f'jwplatform:{x}', ie=JWPlatformIE)


class TV2DKBornholmPlayIE(InfoExtractor):
    _VALID_URL = r'https?://play\.tv2bornholm\.dk/\?.*?\bid=(?P<id>\d+)'
    _TEST = {
        'url': 'http://play.tv2bornholm.dk/?area=specifikTV&id=781021',
        'info_dict': {
            'id': '781021',
            'ext': 'mp4',
            'title': '12Nyheder-27.11.19',
        },
        'params': {
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'https://play.tv2bornholm.dk/controls/AJAX.aspx/specifikVideo', video_id,
            data=json.dumps({
                'playlist_id': video_id,
                'serienavn': '',
            }).encode(), headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json; charset=UTF-8',
            })['d']

        # TODO: generalize flowplayer
        title = self._search_regex(
            r'title\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1', video, 'title',
            group='value')
        sources = self._parse_json(self._search_regex(
            r'(?s)sources:\s*(\[.+?\]),', video, 'sources'),
            video_id, js_to_json)

        formats = []
        srcs = set()
        for source in sources:
            src = url_or_none(source.get('src'))
            if not src:
                continue
            if src in srcs:
                continue
            srcs.add(src)
            ext = determine_ext(src)
            src_type = source.get('type')
            if src_type == 'application/x-mpegurl' or ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    src, video_id, ext='mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            elif src_type == 'application/dash+xml' or ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    src, video_id, mpd_id='dash', fatal=False))
            else:
                formats.append({
                    'url': src,
                })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }
