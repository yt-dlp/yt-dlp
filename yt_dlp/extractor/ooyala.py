from __future__ import unicode_literals

import base64
import re

from .common import InfoExtractor
from ..compat import (
    compat_b64decode,
    compat_str,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    float_or_none,
    int_or_none,
    try_get,
    unsmuggle_url,
)


class OoyalaBaseIE(InfoExtractor):
    _PLAYER_BASE = 'http://player.ooyala.com/'
    _CONTENT_TREE_BASE = _PLAYER_BASE + 'player_api/v1/content_tree/'
    _AUTHORIZATION_URL_TEMPLATE = _PLAYER_BASE + 'sas/player_api/v2/authorization/embed_code/%s/%s'

    def _extract(self, content_tree_url, video_id, domain=None, supportedformats=None, embed_token=None):
        content_tree = self._download_json(content_tree_url, video_id)['content_tree']
        metadata = content_tree[list(content_tree)[0]]
        embed_code = metadata['embed_code']
        pcode = metadata.get('asset_pcode') or embed_code
        title = metadata['title']

        auth_data = self._download_json(
            self._AUTHORIZATION_URL_TEMPLATE % (pcode, embed_code),
            video_id, headers=self.geo_verification_headers(), query={
                'domain': domain or 'player.ooyala.com',
                'supportedFormats': supportedformats or 'mp4,rtmp,m3u8,hds,dash,smooth',
                'embedToken': embed_token,
            })['authorization_data'][embed_code]

        urls = []
        formats = []
        streams = auth_data.get('streams') or [{
            'delivery_type': 'hls',
            'url': {
                'data': base64.b64encode(('http://player.ooyala.com/hls/player/all/%s.m3u8' % embed_code).encode()).decode(),
            }
        }]
        for stream in streams:
            url_data = try_get(stream, lambda x: x['url']['data'], compat_str)
            if not url_data:
                continue
            s_url = compat_b64decode(url_data).decode('utf-8')
            if not s_url or s_url in urls:
                continue
            urls.append(s_url)
            ext = determine_ext(s_url, None)
            delivery_type = stream.get('delivery_type')
            if delivery_type == 'hls' or ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    re.sub(r'/ip(?:ad|hone)/', '/all/', s_url), embed_code, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            elif delivery_type == 'hds' or ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    s_url + '?hdcore=3.7.0', embed_code, f4m_id='hds', fatal=False))
            elif delivery_type == 'dash' or ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    s_url, embed_code, mpd_id='dash', fatal=False))
            elif delivery_type == 'smooth':
                self._extract_ism_formats(
                    s_url, embed_code, ism_id='mss', fatal=False)
            elif ext == 'smil':
                formats.extend(self._extract_smil_formats(
                    s_url, embed_code, fatal=False))
            else:
                formats.append({
                    'url': s_url,
                    'ext': ext or delivery_type,
                    'vcodec': stream.get('video_codec'),
                    'format_id': delivery_type,
                    'width': int_or_none(stream.get('width')),
                    'height': int_or_none(stream.get('height')),
                    'abr': int_or_none(stream.get('audio_bitrate')),
                    'vbr': int_or_none(stream.get('video_bitrate')),
                    'fps': float_or_none(stream.get('framerate')),
                })
        if not formats and not auth_data.get('authorized'):
            raise ExtractorError('%s said: %s' % (
                self.IE_NAME, auth_data['message']), expected=True)
        self._sort_formats(formats)

        subtitles = {}
        for lang, sub in metadata.get('closed_captions_vtt', {}).get('captions', {}).items():
            sub_url = sub.get('url')
            if not sub_url:
                continue
            subtitles[lang] = [{
                'url': sub_url,
            }]

        return {
            'id': embed_code,
            'title': title,
            'description': metadata.get('description'),
            'thumbnail': metadata.get('thumbnail_image') or metadata.get('promo_image'),
            'duration': float_or_none(metadata.get('duration'), 1000),
            'subtitles': subtitles,
            'formats': formats,
        }


class OoyalaIE(OoyalaBaseIE):
    _VALID_URL = r'(?:ooyala:|https?://.+?\.ooyala\.com/.*?(?:embedCode|ec)=)(?P<id>.+?)(&|$)'

    _TESTS = [
        {
            # From http://it.slashdot.org/story/13/04/25/178216/recovering-data-from-broken-hard-drives-and-ssds-video
            'url': 'http://player.ooyala.com/player.js?embedCode=pxczE2YjpfHfn1f3M-ykG_AmJRRn0PD8',
            'info_dict': {
                'id': 'pxczE2YjpfHfn1f3M-ykG_AmJRRn0PD8',
                'ext': 'mp4',
                'title': 'Explaining Data Recovery from Hard Drives and SSDs',
                'description': 'How badly damaged does a drive have to be to defeat Russell and his crew? Apparently, smashed to bits.',
                'duration': 853.386,
            },
            # The video in the original webpage now uses PlayWire
            'skip': 'Ooyala said: movie expired',
        }, {
            # Only available for ipad
            'url': 'http://player.ooyala.com/player.js?embedCode=x1b3lqZDq9y_7kMyC2Op5qo-p077tXD0',
            'info_dict': {
                'id': 'x1b3lqZDq9y_7kMyC2Op5qo-p077tXD0',
                'ext': 'mp4',
                'title': 'Simulation Overview - Levels of Simulation',
                'duration': 194.948,
            },
        },
        {
            # Information available only through SAS api
            # From http://community.plm.automation.siemens.com/t5/News-NX-Manufacturing/Tool-Path-Divide/ba-p/4187
            'url': 'http://player.ooyala.com/player.js?embedCode=FiOG81ZTrvckcchQxmalf4aQj590qTEx',
            'md5': 'a84001441b35ea492bc03736e59e7935',
            'info_dict': {
                'id': 'FiOG81ZTrvckcchQxmalf4aQj590qTEx',
                'ext': 'mp4',
                'title': 'Divide Tool Path.mp4',
                'duration': 204.405,
            }
        },
        {
            # empty stream['url']['data']
            'url': 'http://player.ooyala.com/player.js?embedCode=w2bnZtYjE6axZ_dw1Cd0hQtXd_ige2Is',
            'only_matching': True,
        }
    ]

    @staticmethod
    def _url_for_embed_code(embed_code):
        return 'http://player.ooyala.com/player.js?embedCode=%s' % embed_code

    @classmethod
    def _build_url_result(cls, embed_code):
        return cls.url_result(cls._url_for_embed_code(embed_code),
                              ie=cls.ie_key())

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        embed_code = self._match_id(url)
        domain = smuggled_data.get('domain')
        supportedformats = smuggled_data.get('supportedformats')
        embed_token = smuggled_data.get('embed_token')
        content_tree_url = self._CONTENT_TREE_BASE + 'embed_code/%s/%s' % (embed_code, embed_code)
        return self._extract(content_tree_url, embed_code, domain, supportedformats, embed_token)


class OoyalaExternalIE(OoyalaBaseIE):
    _VALID_URL = r'''(?x)
                    (?:
                        ooyalaexternal:|
                        https?://.+?\.ooyala\.com/.*?\bexternalId=
                    )
                    (?P<partner_id>[^:]+)
                    :
                    (?P<id>.+)
                    (?:
                        :|
                        .*?&pcode=
                    )
                    (?P<pcode>.+?)
                    (?:&|$)
                    '''

    _TEST = {
        'url': 'https://player.ooyala.com/player.js?externalId=espn:10365079&pcode=1kNG061cgaoolOncv54OAO1ceO-I&adSetCode=91cDU6NuXTGKz3OdjOxFdAgJVtQcKJnI&callback=handleEvents&hasModuleParams=1&height=968&playerBrandingId=7af3bd04449c444c964f347f11873075&targetReplaceId=videoPlayer&width=1656&wmode=opaque&allowScriptAccess=always',
        'info_dict': {
            'id': 'FkYWtmazr6Ed8xmvILvKLWjd4QvYZpzG',
            'ext': 'mp4',
            'title': 'dm_140128_30for30Shorts___JudgingJewellv2',
            'duration': 1302.0,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        partner_id, video_id, pcode = re.match(self._VALID_URL, url).groups()
        content_tree_url = self._CONTENT_TREE_BASE + 'external_id/%s/%s:%s' % (pcode, partner_id, video_id)
        return self._extract(content_tree_url, video_id)
