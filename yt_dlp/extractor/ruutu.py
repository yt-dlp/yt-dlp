import json
import re

from .common import InfoExtractor
from ..compat import compat_urllib_parse_urlparse
from ..utils import (
    determine_ext,
    ExtractorError,
    find_xpath_attr,
    int_or_none,
    traverse_obj,
    try_call,
    unified_strdate,
    url_or_none,
    xpath_attr,
    xpath_text,
)


class RuutuIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:www\.)?(?:ruutu|supla)\.fi/(?:video|supla|audio)/|
                            static\.nelonenmedia\.fi/player/misc/embed_player\.html\?.*?\bnid=
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [
        {
            'url': 'http://www.ruutu.fi/video/2058907',
            'md5': 'ab2093f39be1ca8581963451b3c0234f',
            'info_dict': {
                'id': '2058907',
                'ext': 'mp4',
                'title': 'Oletko aina halunnut tietää mitä tapahtuu vain hetki ennen lähetystä? - Nyt se selvisi!',
                'description': 'md5:cfc6ccf0e57a814360df464a91ff67d6',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 114,
                'age_limit': 0,
                'upload_date': '20150508',
            },
        },
        {
            'url': 'http://www.ruutu.fi/video/2057306',
            'md5': '065a10ae4d5b8cfd9d0c3d332465e3d9',
            'info_dict': {
                'id': '2057306',
                'ext': 'mp4',
                'title': 'Superpesis: katso koko kausi Ruudussa',
                'description': 'md5:bfb7336df2a12dc21d18fa696c9f8f23',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 40,
                'age_limit': 0,
                'upload_date': '20150507',
                'series': 'Superpesis',
                'categories': ['Urheilu'],
            },
        },
        {
            'url': 'http://www.supla.fi/supla/2231370',
            'md5': 'df14e782d49a2c0df03d3be2a54ef949',
            'info_dict': {
                'id': '2231370',
                'ext': 'mp4',
                'title': 'Osa 1: Mikael Jungner',
                'description': 'md5:7d90f358c47542e3072ff65d7b1bcffe',
                'thumbnail': r're:^https?://.*\.jpg$',
                'age_limit': 0,
                'upload_date': '20151012',
                'series': 'Läpivalaisu',
            },
        },
        # Episode where <SourceFile> is "NOT-USED", but has other
        # downloadable sources available.
        {
            'url': 'http://www.ruutu.fi/video/3193728',
            'only_matching': True,
        },
        {
            # audio podcast
            'url': 'https://www.supla.fi/supla/3382410',
            'md5': 'b9d7155fed37b2ebf6021d74c4b8e908',
            'info_dict': {
                'id': '3382410',
                'ext': 'mp3',
                'title': 'Mikä ihmeen poltergeist?',
                'description': 'md5:bbb6963df17dfd0ecd9eb9a61bf14b52',
                'thumbnail': r're:^https?://.*\.jpg$',
                'age_limit': 0,
                'upload_date': '20190320',
                'series': 'Mysteeritarinat',
                'duration': 1324,
            },
            'expected_warnings': [
                'HTTP Error 502: Bad Gateway',
                'Failed to download m3u8 information',
            ],
        },
        {
            'url': 'http://www.supla.fi/audio/2231370',
            'only_matching': True,
        },
        {
            'url': 'https://static.nelonenmedia.fi/player/misc/embed_player.html?nid=3618790',
            'only_matching': True,
        },
        {
            # episode
            'url': 'https://www.ruutu.fi/video/3401964',
            'info_dict': {
                'id': '3401964',
                'ext': 'mp4',
                'title': 'Temptation Island Suomi - Kausi 5 - Jakso 17',
                'description': 'md5:87cf01d5e1e88adf0c8a2937d2bd42ba',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 2582,
                'age_limit': 12,
                'upload_date': '20190508',
                'series': 'Temptation Island Suomi',
                'season_number': 5,
                'episode_number': 17,
                'categories': ['Reality ja tositapahtumat', 'Kotimaiset suosikit', 'Romantiikka ja parisuhde'],
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # premium
            'url': 'https://www.ruutu.fi/video/3618715',
            'only_matching': True,
        },
    ]
    _API_BASE = 'https://gatling.nelonenmedia.fi'

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        # nelonen.fi
        settings = try_call(
            lambda: json.loads(re.search(
                r'jQuery\.extend\(Drupal\.settings, ({.+?})\);', webpage).group(1), strict=False))
        if settings:
            video_id = traverse_obj(settings, (
                'mediaCrossbowSettings', 'file', 'field_crossbow_video_id', 'und', 0, 'value'))
            if video_id:
                return [f'http://www.ruutu.fi/video/{video_id}']
        # hs.fi and is.fi
        settings = try_call(
            lambda: json.loads(re.search(
                '(?s)<script[^>]+id=[\'"]__NEXT_DATA__[\'"][^>]*>([^<]+)</script>',
                webpage).group(1), strict=False))
        if settings:
            video_ids = set(traverse_obj(settings, (
                'props', 'pageProps', 'page', 'assetData', 'splitBody', ..., 'video', 'sourceId')) or [])
            if video_ids:
                return [f'http://www.ruutu.fi/video/{v}' for v in video_ids]
            video_id = traverse_obj(settings, (
                'props', 'pageProps', 'page', 'assetData', 'mainVideo', 'sourceId'))
            if video_id:
                return [f'http://www.ruutu.fi/video/{video_id}']

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_xml = self._download_xml(
            '%s/media-xml-cache' % self._API_BASE, video_id,
            query={'id': video_id})

        formats = []
        processed_urls = []

        def extract_formats(node):
            for child in node:
                if child.tag.endswith('Files'):
                    extract_formats(child)
                elif child.tag.endswith('File'):
                    video_url = child.text
                    if (not video_url or video_url in processed_urls
                            or any(p in video_url for p in ('NOT_USED', 'NOT-USED'))):
                        continue
                    processed_urls.append(video_url)
                    ext = determine_ext(video_url)
                    auth_video_url = url_or_none(self._download_webpage(
                        '%s/auth/access/v2' % self._API_BASE, video_id,
                        note='Downloading authenticated %s stream URL' % ext,
                        fatal=False, query={'stream': video_url}))
                    if auth_video_url:
                        processed_urls.append(auth_video_url)
                        video_url = auth_video_url
                    if ext == 'm3u8':
                        formats.extend(self._extract_m3u8_formats(
                            video_url, video_id, 'mp4',
                            entry_protocol='m3u8_native', m3u8_id='hls',
                            fatal=False))
                    elif ext == 'f4m':
                        formats.extend(self._extract_f4m_formats(
                            video_url, video_id, f4m_id='hds', fatal=False))
                    elif ext == 'mpd':
                        # video-only and audio-only streams are of different
                        # duration resulting in out of sync issue
                        continue
                        formats.extend(self._extract_mpd_formats(
                            video_url, video_id, mpd_id='dash', fatal=False))
                    elif ext == 'mp3' or child.tag == 'AudioMediaFile':
                        formats.append({
                            'format_id': 'audio',
                            'url': video_url,
                            'vcodec': 'none',
                        })
                    else:
                        proto = compat_urllib_parse_urlparse(video_url).scheme
                        if not child.tag.startswith('HTTP') and proto != 'rtmp':
                            continue
                        preference = -1 if proto == 'rtmp' else 1
                        label = child.get('label')
                        tbr = int_or_none(child.get('bitrate'))
                        format_id = '%s-%s' % (proto, label if label else tbr) if label or tbr else proto
                        if not self._is_valid_url(video_url, video_id, format_id):
                            continue
                        width, height = [int_or_none(x) for x in child.get('resolution', 'x').split('x')[:2]]
                        formats.append({
                            'format_id': format_id,
                            'url': video_url,
                            'width': width,
                            'height': height,
                            'tbr': tbr,
                            'preference': preference,
                        })

        extract_formats(video_xml.find('./Clip'))

        def pv(name):
            value = try_call(lambda: find_xpath_attr(
                video_xml, './Clip/PassthroughVariables/variable', 'name', name).get('value'))
            if value != 'NA':
                return value or None

        if not formats:
            if (not self.get_param('allow_unplayable_formats')
                    and xpath_text(video_xml, './Clip/DRM', default=None)):
                self.report_drm(video_id)
            ns_st_cds = pv('ns_st_cds')
            if ns_st_cds != 'free':
                raise ExtractorError('This video is %s.' % ns_st_cds, expected=True)

        themes = pv('themes')

        return {
            'id': video_id,
            'title': xpath_attr(video_xml, './/Behavior/Program', 'program_name', 'title', fatal=True),
            'description': xpath_attr(video_xml, './/Behavior/Program', 'description', 'description'),
            'thumbnail': xpath_attr(video_xml, './/Behavior/Startpicture', 'href', 'thumbnail'),
            'duration': int_or_none(xpath_text(video_xml, './/Runtime', 'duration')) or int_or_none(pv('runtime')),
            'age_limit': int_or_none(xpath_text(video_xml, './/AgeLimit', 'age limit')),
            'upload_date': unified_strdate(pv('date_start')),
            'series': pv('series_name'),
            'season_number': int_or_none(pv('season_number')),
            'episode_number': int_or_none(pv('episode_number')),
            'categories': themes.split(',') if themes else None,
            'formats': formats,
        }
