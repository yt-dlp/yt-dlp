import json
import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    js_to_json,
    url_or_none,
)


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
                            tv2nord
                        )\.dk/
                        (:[^/]+/)*
                        (?P<id>[^/?\#&]+)
                    '''
    _TESTS = [{
        'url': 'https://www.tvsyd.dk/nyheder/28-10-2019/1930/1930-28-okt-2019?autoplay=1#player',
        'info_dict': {
            'id': '0_52jmwa0p',
            'ext': 'mp4',
            'title': '19:30 - 28. okt. 2019',
            'timestamp': 1572290248,
            'upload_date': '20191028',
            'uploader_id': 'tvsyd',
            'duration': 1347,
            'view_count': int,
        },
        'add_ie': ['Kaltura'],
    }, {
        'url': 'https://www.tv2lorry.dk/gadekamp/gadekamp-6-hoejhuse-i-koebenhavn',
        'info_dict': {
            'id': '1_7iwll9n0',
            'ext': 'mp4',
            'upload_date': '20211027',
            'title': 'Gadekamp #6 - Højhuse i København',
            'uploader_id': 'tv2lorry',
            'timestamp': 1635345229,
        },
        'add_ie': ['Kaltura'],
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
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        entries = []

        def add_entry(partner_id, kaltura_id):
            entries.append(self.url_result(
                f'kaltura:{partner_id}:{kaltura_id}', 'Kaltura',
                video_id=kaltura_id))

        for video_el in re.findall(r'(?s)<[^>]+\bdata-entryid\s*=[^>]*>', webpage):
            video = extract_attributes(video_el)
            kaltura_id = video.get('data-entryid')
            if not kaltura_id:
                continue
            partner_id = video.get('data-partnerid')
            if not partner_id:
                continue
            add_entry(partner_id, kaltura_id)
        if not entries:
            kaltura_id = self._search_regex(
                (r'entry_id\s*:\s*["\']([0-9a-z_]+)',
                 r'\\u002FentryId\\u002F(\w+)\\u002F'), webpage, 'kaltura id')
            partner_id = self._search_regex(
                (r'\\u002Fp\\u002F(\d+)\\u002F', r'/p/(\d+)/'), webpage,
                'partner id')
            add_entry(partner_id, kaltura_id)
        if len(entries) == 1:
            return entries[0]
        return self.playlist_result(entries)


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
