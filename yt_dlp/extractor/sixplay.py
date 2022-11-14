from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    determine_ext,
    int_or_none,
    parse_qs,
    try_get,
    qualities,
)


class SixPlayIE(InfoExtractor):
    IE_NAME = '6play'
    _VALID_URL = r'(?:6play:|https?://(?:www\.)?(?P<domain>6play\.fr|rtlplay\.be|play\.rtl\.hr|rtlmost\.hu)/.+?-c_)(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.6play.fr/minute-par-minute-p_9533/le-but-qui-a-marque-lhistoire-du-football-francais-c_12041051',
        'md5': '31fcd112637baa0c2ab92c4fcd8baf27',
        'info_dict': {
            'id': '12041051',
            'ext': 'mp4',
            'title': 'Le but qui a marqué l\'histoire du football français !',
            'description': 'md5:b59e7e841d646ef1eb42a7868eb6a851',
        },
    }, {
        'url': 'https://www.rtlplay.be/rtl-info-13h-p_8551/les-titres-du-rtlinfo-13h-c_12045869',
        'only_matching': True,
    }, {
        'url': 'https://play.rtl.hr/pj-masks-p_9455/epizoda-34-sezona-1-catboyevo-cudo-na-dva-kotaca-c_11984989',
        'only_matching': True,
    }, {
        'url': 'https://www.rtlmost.hu/megtorve-p_14167/megtorve-6-resz-c_12397787',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, video_id = self._match_valid_url(url).groups()
        service, consumer_name = {
            '6play.fr': ('6play', 'm6web'),
            'rtlplay.be': ('rtlbe_rtl_play', 'rtlbe'),
            'play.rtl.hr': ('rtlhr_rtl_play', 'rtlhr'),
            'rtlmost.hu': ('rtlhu_rtl_most', 'rtlhu'),
        }.get(domain, ('6play', 'm6web'))

        data = self._download_json(
            'https://pc.middleware.6play.fr/6play/v2/platforms/m6group_web/services/%s/videos/clip_%s' % (service, video_id),
            video_id, headers={
                'x-customer-name': consumer_name
            }, query={
                'csa': 5,
                'with': 'clips',
            })

        clip_data = data['clips'][0]
        title = clip_data['title']

        urls = []
        quality_key = qualities(['lq', 'sd', 'hq', 'hd'])
        formats = []
        subtitles = {}
        assets = clip_data.get('assets') or []
        for asset in assets:
            asset_url = asset.get('full_physical_path')
            protocol = asset.get('protocol')
            if not asset_url or ((protocol == 'primetime' or asset.get('type') == 'usp_hlsfp_h264') and not ('_drmnp.ism/' in asset_url or '_unpnp.ism/' in asset_url)) or asset_url in urls:
                continue
            urls.append(asset_url)
            container = asset.get('video_container')
            ext = determine_ext(asset_url)
            if protocol == 'http_subtitle' or ext == 'vtt':
                subtitles.setdefault('fr', []).append({'url': asset_url})
                continue
            if container == 'm3u8' or ext == 'm3u8':
                if protocol == 'usp':
                    if parse_qs(asset_url).get('token', [None])[0]:
                        urlh = self._request_webpage(
                            asset_url, video_id, fatal=False,
                            headers=self.geo_verification_headers())
                        if not urlh:
                            continue
                        asset_url = urlh.geturl()
                    asset_url = asset_url.replace('_drmnp.ism/', '_unpnp.ism/')
                    for i in range(3, 0, -1):
                        asset_url = asset_url = asset_url.replace('_sd1/', '_sd%d/' % i)
                        m3u8_formats = self._extract_m3u8_formats(
                            asset_url, video_id, 'mp4', 'm3u8_native',
                            m3u8_id='hls', fatal=False)
                        formats.extend(m3u8_formats)
                        formats.extend(self._extract_mpd_formats(
                            asset_url.replace('.m3u8', '.mpd'),
                            video_id, mpd_id='dash', fatal=False))
                        if m3u8_formats:
                            break
                else:
                    formats.extend(self._extract_m3u8_formats(
                        asset_url, video_id, 'mp4', 'm3u8_native',
                        m3u8_id='hls', fatal=False))
            elif container == 'mp4' or ext == 'mp4':
                quality = asset.get('video_quality')
                formats.append({
                    'url': asset_url,
                    'format_id': quality,
                    'quality': quality_key(quality),
                    'ext': ext,
                })
        self._sort_formats(formats)

        def get(getter):
            for src in (data, clip_data):
                v = try_get(src, getter, compat_str)
                if v:
                    return v

        return {
            'id': video_id,
            'title': title,
            'description': get(lambda x: x['description']),
            'duration': int_or_none(clip_data.get('duration')),
            'series': get(lambda x: x['program']['title']),
            'formats': formats,
            'subtitles': subtitles,
        }
