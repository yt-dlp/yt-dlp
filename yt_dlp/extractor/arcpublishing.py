import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    int_or_none,
    parse_iso8601,
    try_get,
)


class ArcPublishingIE(InfoExtractor):
    _UUID_REGEX = r'[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}'
    _VALID_URL = r'arcpublishing:(?P<org>[a-z]+):(?P<id>%s)' % _UUID_REGEX
    _TESTS = [{
        # https://www.adn.com/politics/2020/11/02/video-senate-candidates-campaign-in-anchorage-on-eve-of-election-day/
        'url': 'arcpublishing:adn:8c99cb6e-b29c-4bc9-9173-7bf9979225ab',
        'only_matching': True,
    }, {
        # https://www.bostonglobe.com/video/2020/12/30/metro/footage-released-showing-officer-talking-about-striking-protesters-with-car/
        'url': 'arcpublishing:bostonglobe:232b7ae6-7d73-432d-bc0a-85dbf0119ab1',
        'only_matching': True,
    }, {
        # https://www.actionnewsjax.com/video/live-stream/
        'url': 'arcpublishing:cmg:cfb1cf1b-3ab5-4d1b-86c5-a5515d311f2a',
        'only_matching': True,
    }, {
        # https://elcomercio.pe/videos/deportes/deporte-total-futbol-peruano-seleccion-peruana-la-valorizacion-de-los-peruanos-en-el-exterior-tras-un-2020-atipico-nnav-vr-video-noticia/
        'url': 'arcpublishing:elcomercio:27a7e1f8-2ec7-4177-874f-a4feed2885b3',
        'only_matching': True,
    }, {
        # https://www.clickondetroit.com/video/community/2020/05/15/events-surrounding-woodward-dream-cruise-being-canceled/
        'url': 'arcpublishing:gmg:c8793fb2-8d44-4242-881e-2db31da2d9fe',
        'only_matching': True,
    }, {
        # https://www.wabi.tv/video/2020/12/30/trenton-company-making-equipment-pfizer-covid-vaccine/
        'url': 'arcpublishing:gray:0b0ba30e-032a-4598-8810-901d70e6033e',
        'only_matching': True,
    }, {
        # https://www.lateja.cr/el-mundo/video-china-aprueba-con-condiciones-su-primera/dfcbfa57-527f-45ff-a69b-35fe71054143/video/
        'url': 'arcpublishing:gruponacion:dfcbfa57-527f-45ff-a69b-35fe71054143',
        'only_matching': True,
    }, {
        # https://www.fifthdomain.com/video/2018/03/09/is-america-vulnerable-to-a-cyber-attack/
        'url': 'arcpublishing:mco:aa0ca6fe-1127-46d4-b32c-be0d6fdb8055',
        'only_matching': True,
    }, {
        # https://www.vl.no/kultur/2020/12/09/en-melding-fra-en-lytter-endret-julelista-til-lewi-bergrud/
        'url': 'arcpublishing:mentormedier:47a12084-650b-4011-bfd0-3699b6947b2d',
        'only_matching': True,
    }, {
        # https://www.14news.com/2020/12/30/whiskey-theft-caught-camera-henderson-liquor-store/
        'url': 'arcpublishing:raycom:b89f61f8-79fa-4c09-8255-e64237119bf7',
        'only_matching': True,
    }, {
        # https://www.theglobeandmail.com/world/video-ethiopian-woman-who-became-symbol-of-integration-in-italy-killed-on/
        'url': 'arcpublishing:tgam:411b34c1-8701-4036-9831-26964711664b',
        'only_matching': True,
    }, {
        # https://www.pilotonline.com/460f2931-8130-4719-8ea1-ffcb2d7cb685-132.html
        'url': 'arcpublishing:tronc:460f2931-8130-4719-8ea1-ffcb2d7cb685',
        'only_matching': True,
    }]
    _POWA_DEFAULTS = [
        (['cmg', 'prisa'], '%s-config-prod.api.cdn.arcpublishing.com/video'),
        ([
            'adn', 'advancelocal', 'answers', 'bonnier', 'bostonglobe', 'demo',
            'gmg', 'gruponacion', 'infobae', 'mco', 'nzme', 'pmn', 'raycom',
            'spectator', 'tbt', 'tgam', 'tronc', 'wapo', 'wweek',
        ], 'video-api-cdn.%s.arcpublishing.com/api'),
    ]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        entries = []
        # https://arcpublishing.atlassian.net/wiki/spaces/POWA/overview
        for powa_el in re.findall(r'(<div[^>]+class="[^"]*\bpowa\b[^"]*"[^>]+data-uuid="%s"[^>]*>)' % ArcPublishingIE._UUID_REGEX, webpage):
            powa = extract_attributes(powa_el) or {}
            org = powa.get('data-org')
            uuid = powa.get('data-uuid')
            if org and uuid:
                entries.append('arcpublishing:%s:%s' % (org, uuid))
        return entries

    def _real_extract(self, url):
        org, uuid = self._match_valid_url(url).groups()
        for orgs, tmpl in self._POWA_DEFAULTS:
            if org in orgs:
                base_api_tmpl = tmpl
                break
        else:
            base_api_tmpl = '%s-prod-cdn.video-api.arcpublishing.com/api'
        if org == 'wapo':
            org = 'washpost'
        video = self._download_json(
            'https://%s/v1/ansvideos/findByUuid' % (base_api_tmpl % org),
            uuid, query={'uuid': uuid})[0]
        title = video['headlines']['basic']
        is_live = video.get('status') == 'live'

        urls = []
        formats = []
        for s in video.get('streams', []):
            s_url = s.get('url')
            if not s_url or s_url in urls:
                continue
            urls.append(s_url)
            stream_type = s.get('stream_type')
            if stream_type == 'smil':
                smil_formats = self._extract_smil_formats(
                    s_url, uuid, fatal=False)
                for f in smil_formats:
                    if f['url'].endswith('/cfx/st'):
                        f['app'] = 'cfx/st'
                        if not f['play_path'].startswith('mp4:'):
                            f['play_path'] = 'mp4:' + f['play_path']
                        if isinstance(f['tbr'], float):
                            f['vbr'] = f['tbr'] * 1000
                            del f['tbr']
                            f['format_id'] = 'rtmp-%d' % f['vbr']
                formats.extend(smil_formats)
            elif stream_type in ('ts', 'hls'):
                m3u8_formats = self._extract_m3u8_formats(
                    s_url, uuid, 'mp4', live=is_live, m3u8_id='hls', fatal=False)
                if all([f.get('acodec') == 'none' for f in m3u8_formats]):
                    continue
                for f in m3u8_formats:
                    height = f.get('height')
                    if not height:
                        continue
                    vbr = self._search_regex(
                        r'[_x]%d[_-](\d+)' % height, f['url'], 'vbr', default=None)
                    if vbr:
                        f['vbr'] = int(vbr)
                formats.extend(m3u8_formats)
            else:
                vbr = int_or_none(s.get('bitrate'))
                formats.append({
                    'format_id': '%s-%d' % (stream_type, vbr) if vbr else stream_type,
                    'vbr': vbr,
                    'width': int_or_none(s.get('width')),
                    'height': int_or_none(s.get('height')),
                    'filesize': int_or_none(s.get('filesize')),
                    'url': s_url,
                    'quality': -10,
                })

        subtitles = {}
        for subtitle in (try_get(video, lambda x: x['subtitles']['urls'], list) or []):
            subtitle_url = subtitle.get('url')
            if subtitle_url:
                subtitles.setdefault('en', []).append({'url': subtitle_url})

        return {
            'id': uuid,
            'title': title,
            'thumbnail': try_get(video, lambda x: x['promo_image']['url']),
            'description': try_get(video, lambda x: x['subheadlines']['basic']),
            'formats': formats,
            'duration': int_or_none(video.get('duration'), 100),
            'timestamp': parse_iso8601(video.get('created_date')),
            'subtitles': subtitles,
            'is_live': is_live,
        }
