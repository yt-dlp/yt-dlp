import base64
import json
import re

from .common import InfoExtractor
from ..compat import (
    compat_urlparse,
    compat_parse_qs,
)
from ..utils import (
    clean_html,
    ExtractorError,
    format_field,
    int_or_none,
    unsmuggle_url,
    smuggle_url,
    traverse_obj,
)


class KalturaIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                (?:
                    kaltura:(?P<partner_id>\d+):(?P<id>[0-9a-z_]+)|
                    https?://
                        (:?(?:www|cdnapi(?:sec)?)\.)?kaltura\.com(?::\d+)?/
                        (?:
                            (?:
                                # flash player
                                index\.php/(?:kwidget|extwidget/preview)|
                                # html5 player
                                html5/html5lib/[^/]+/mwEmbedFrame\.php
                            )
                        )(?:/(?P<path>[^?]+))?(?:\?(?P<query>.*))?
                )
                '''
    _SERVICE_URL = 'http://cdnapi.kaltura.com'
    _SERVICE_BASE = '/api_v3/service/multirequest'
    # See https://github.com/kaltura/server/blob/master/plugins/content/caption/base/lib/model/enums/CaptionType.php
    _CAPTION_TYPES = {
        1: 'srt',
        2: 'ttml',
        3: 'vtt',
    }
    _TESTS = [
        {
            'url': 'kaltura:269692:1_1jc2y3e4',
            'md5': '3adcbdb3dcc02d647539e53f284ba171',
            'info_dict': {
                'id': '1_1jc2y3e4',
                'ext': 'mp4',
                'title': 'Straight from the Heart',
                'upload_date': '20131219',
                'uploader_id': 'mlundberg@wolfgangsvault.com',
                'description': 'The Allman Brothers Band, 12/16/1981',
                'thumbnail': 're:^https?://.*/thumbnail/.*',
                'timestamp': int,
            },
        },
        {
            'url': 'http://www.kaltura.com/index.php/kwidget/cache_st/1300318621/wid/_269692/uiconf_id/3873291/entry_id/1_1jc2y3e4',
            'only_matching': True,
        },
        {
            'url': 'https://cdnapisec.kaltura.com/index.php/kwidget/wid/_557781/uiconf_id/22845202/entry_id/1_plr1syf3',
            'only_matching': True,
        },
        {
            'url': 'https://cdnapisec.kaltura.com/html5/html5lib/v2.30.2/mwEmbedFrame.php/p/1337/uiconf_id/20540612/entry_id/1_sf5ovm7u?wid=_243342',
            'only_matching': True,
        },
        {
            # video with subtitles
            'url': 'kaltura:111032:1_cw786r8q',
            'only_matching': True,
        },
        {
            # video with ttml subtitles (no fileExt)
            'url': 'kaltura:1926081:0_l5ye1133',
            'info_dict': {
                'id': '0_l5ye1133',
                'ext': 'mp4',
                'title': 'What Can You Do With Python?',
                'upload_date': '20160221',
                'uploader_id': 'stork',
                'thumbnail': 're:^https?://.*/thumbnail/.*',
                'timestamp': int,
                'subtitles': {
                    'en': [{
                        'ext': 'ttml',
                    }],
                },
            },
            'skip': 'Gone. Maybe https://www.safaribooksonline.com/library/tutorials/introduction-to-python-anon/3469/',
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://www.kaltura.com/index.php/extwidget/preview/partner_id/1770401/uiconf_id/37307382/entry_id/0_58u8kme7/embed/iframe?&flashvars[streamerType]=auto',
            'only_matching': True,
        },
        {
            'url': 'https://www.kaltura.com:443/index.php/extwidget/preview/partner_id/1770401/uiconf_id/37307382/entry_id/0_58u8kme7/embed/iframe?&flashvars[streamerType]=auto',
            'only_matching': True,
        },
        {
            # unavailable source format
            'url': 'kaltura:513551:1_66x4rg7o',
            'only_matching': True,
        }
    ]

    @staticmethod
    def _extract_url(webpage):
        urls = KalturaIE._extract_urls(webpage)
        return urls[0] if urls else None

    @staticmethod
    def _extract_urls(webpage):
        # Embed codes: https://knowledge.kaltura.com/embedding-kaltura-media-players-your-site
        finditer = (
            list(re.finditer(
                r"""(?xs)
                    kWidget\.(?:thumb)?[Ee]mbed\(
                    \{.*?
                        (?P<q1>['"])wid(?P=q1)\s*:\s*
                        (?P<q2>['"])_?(?P<partner_id>(?:(?!(?P=q2)).)+)(?P=q2),.*?
                        (?P<q3>['"])entry_?[Ii]d(?P=q3)\s*:\s*
                        (?P<q4>['"])(?P<id>(?:(?!(?P=q4)).)+)(?P=q4)(?:,|\s*\})
                """, webpage))
            or list(re.finditer(
                r'''(?xs)
                    (?P<q1>["'])
                        (?:https?:)?//cdnapi(?:sec)?\.kaltura\.com(?::\d+)?/(?:(?!(?P=q1)).)*\b(?:p|partner_id)/(?P<partner_id>\d+)(?:(?!(?P=q1)).)*
                    (?P=q1).*?
                    (?:
                        (?:
                            entry_?[Ii]d|
                            (?P<q2>["'])entry_?[Ii]d(?P=q2)
                        )\s*:\s*|
                        \[\s*(?P<q2_1>["'])entry_?[Ii]d(?P=q2_1)\s*\]\s*=\s*
                    )
                    (?P<q3>["'])(?P<id>(?:(?!(?P=q3)).)+)(?P=q3)
                ''', webpage))
            or list(re.finditer(
                r'''(?xs)
                    <(?:iframe[^>]+src|meta[^>]+\bcontent)=(?P<q1>["'])\s*
                      (?:https?:)?//(?:(?:www|cdnapi(?:sec)?)\.)?kaltura\.com/(?:(?!(?P=q1)).)*\b(?:p|partner_id)/(?P<partner_id>\d+)
                      (?:(?!(?P=q1)).)*
                      [?&;]entry_id=(?P<id>(?:(?!(?P=q1))[^&])+)
                      (?:(?!(?P=q1)).)*
                    (?P=q1)
                ''', webpage))
        )
        urls = []
        for mobj in finditer:
            embed_info = mobj.groupdict()
            for k, v in embed_info.items():
                if v:
                    embed_info[k] = v.strip()
            url = 'kaltura:%(partner_id)s:%(id)s' % embed_info
            escaped_pid = re.escape(embed_info['partner_id'])
            service_mobj = re.search(
                r'<script[^>]+src=(["\'])(?P<id>(?:https?:)?//(?:(?!\1).)+)/p/%s/sp/%s00/embedIframeJs' % (escaped_pid, escaped_pid),
                webpage)
            if service_mobj:
                url = smuggle_url(url, {'service_url': service_mobj.group('id')})
            urls.append(url)
        return urls

    def _kaltura_api_call(self, video_id, actions, service_url=None, *args, **kwargs):
        params = actions[0]
        params.update({i: a for i, a in enumerate(actions[1:], start=1)})

        data = self._download_json(
            (service_url or self._SERVICE_URL) + self._SERVICE_BASE,
            video_id, data=json.dumps(params).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Accept-Encoding': 'gzip, deflate, br',
            }, *args, **kwargs)

        for idx, status in enumerate(data):
            if not isinstance(status, dict):
                continue
            if status.get('objectType') == 'KalturaAPIException':
                raise ExtractorError(
                    '%s said: %s (%d)' % (self.IE_NAME, status['message'], idx))

        data[1] = traverse_obj(data, (1, 'objects', 0))

        return data

    def _get_video_info(self, video_id, partner_id, service_url=None):
        actions = [
            {
                'apiVersion': '3.3.0',
                'clientTag': 'html5:v3.1.0',
                'format': 1,  # JSON, 2 = XML, 3 = PHP
                'ks': '',
                'partnerId': partner_id,
            },
            {
                'expiry': 86400,
                'service': 'session',
                'action': 'startWidgetSession',
                'widgetId': '_%s' % partner_id,
            },
            {
                'action': 'list',
                'filter': {'redirectFromEntryId': video_id},
                'service': 'baseentry',
                'ks': '{1:result:ks}',
                'responseProfile': {
                    'type': 1,
                    'fields': 'createdAt,dataUrl,duration,name,plays,thumbnailUrl,userId',
                },
            },
            {
                'action': 'getbyentryid',
                'entryId': video_id,
                'service': 'flavorAsset',
                'ks': '{1:result:ks}',
            },
            {
                'action': 'list',
                'filter:entryIdEqual': video_id,
                'service': 'caption_captionasset',
                'ks': '{1:result:ks}',
            },
        ]
        return self._kaltura_api_call(
            video_id, actions, service_url, note='Downloading video info JSON')

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        mobj = self._match_valid_url(url)
        partner_id, entry_id = mobj.group('partner_id', 'id')
        ks = None
        captions = None
        if partner_id and entry_id:
            _, info, flavor_assets, captions = self._get_video_info(entry_id, partner_id, smuggled_data.get('service_url'))
        else:
            path, query = mobj.group('path', 'query')
            if not path and not query:
                raise ExtractorError('Invalid URL', expected=True)
            params = {}
            if query:
                params = compat_parse_qs(query)
            if path:
                splitted_path = path.split('/')
                params.update(dict((zip(splitted_path[::2], [[v] for v in splitted_path[1::2]]))))
            if 'wid' in params:
                partner_id = params['wid'][0][1:]
            elif 'p' in params:
                partner_id = params['p'][0]
            elif 'partner_id' in params:
                partner_id = params['partner_id'][0]
            else:
                raise ExtractorError('Invalid URL', expected=True)
            if 'entry_id' in params:
                entry_id = params['entry_id'][0]
                _, info, flavor_assets, captions = self._get_video_info(entry_id, partner_id)
            elif 'uiconf_id' in params and 'flashvars[referenceId]' in params:
                reference_id = params['flashvars[referenceId]'][0]
                webpage = self._download_webpage(url, reference_id)
                entry_data = self._parse_json(self._search_regex(
                    r'window\.kalturaIframePackageData\s*=\s*({.*});',
                    webpage, 'kalturaIframePackageData'),
                    reference_id)['entryResult']
                info, flavor_assets = entry_data['meta'], entry_data['contextData']['flavorAssets']
                entry_id = info['id']
                # Unfortunately, data returned in kalturaIframePackageData lacks
                # captions so we will try requesting the complete data using
                # regular approach since we now know the entry_id
                try:
                    _, info, flavor_assets, captions = self._get_video_info(
                        entry_id, partner_id)
                except ExtractorError:
                    # Regular scenario failed but we already have everything
                    # extracted apart from captions and can process at least
                    # with this
                    pass
            else:
                raise ExtractorError('Invalid URL', expected=True)
            ks = params.get('flashvars[ks]', [None])[0]

        source_url = smuggled_data.get('source_url')
        if source_url:
            referrer = base64.b64encode(
                '://'.join(compat_urlparse.urlparse(source_url)[:2])
                .encode('utf-8')).decode('utf-8')
        else:
            referrer = None

        def sign_url(unsigned_url):
            if ks:
                unsigned_url += '/ks/%s' % ks
            if referrer:
                unsigned_url += '?referrer=%s' % referrer
            return unsigned_url

        data_url = info['dataUrl']
        if '/flvclipper/' in data_url:
            data_url = re.sub(r'/flvclipper/.*', '/serveFlavor', data_url)

        formats = []
        subtitles = {}
        for f in flavor_assets:
            # Continue if asset is not ready
            if f.get('status') != 2:
                continue
            # Original format that's not available (e.g. kaltura:1926081:0_c03e1b5g)
            # skip for now.
            if f.get('fileExt') == 'chun':
                continue
            # DRM-protected video, cannot be decrypted
            if not self.get_param('allow_unplayable_formats') and f.get('fileExt') == 'wvm':
                continue
            if not f.get('fileExt'):
                # QT indicates QuickTime; some videos have broken fileExt
                if f.get('containerFormat') == 'qt':
                    f['fileExt'] = 'mov'
                else:
                    f['fileExt'] = 'mp4'
            video_url = sign_url(
                '%s/flavorId/%s' % (data_url, f['id']))
            format_id = '%(fileExt)s-%(bitrate)s' % f
            # Source format may not be available (e.g. kaltura:513551:1_66x4rg7o)
            if f.get('isOriginal') is True and not self._is_valid_url(
                    video_url, entry_id, format_id):
                continue
            # audio-only has no videoCodecId (e.g. kaltura:1926081:0_c03e1b5g
            # -f mp4-56)
            vcodec = 'none' if 'videoCodecId' not in f and f.get(
                'frameRate') == 0 else f.get('videoCodecId')
            formats.append({
                'format_id': format_id,
                'ext': f.get('fileExt'),
                'tbr': int_or_none(f['bitrate']),
                'fps': int_or_none(f.get('frameRate')),
                'filesize_approx': int_or_none(f.get('size'), invscale=1024),
                'container': f.get('containerFormat'),
                'vcodec': vcodec,
                'height': int_or_none(f.get('height')),
                'width': int_or_none(f.get('width')),
                'url': video_url,
            })
        if '/playManifest/' in data_url:
            m3u8_url = sign_url(data_url.replace(
                'format/url', 'format/applehttp'))
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, entry_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        self._sort_formats(formats)

        if captions:
            for caption in captions.get('objects', []):
                # Continue if caption is not ready
                if caption.get('status') != 2:
                    continue
                if not caption.get('id'):
                    continue
                caption_format = int_or_none(caption.get('format'))
                subtitles.setdefault(caption.get('languageCode') or caption.get('language'), []).append({
                    'url': '%s/api_v3/service/caption_captionasset/action/serve/captionAssetId/%s' % (self._SERVICE_URL, caption['id']),
                    'ext': caption.get('fileExt') or self._CAPTION_TYPES.get(caption_format) or 'ttml',
                })

        return {
            'id': entry_id,
            'title': info['name'],
            'formats': formats,
            'subtitles': subtitles,
            'description': clean_html(info.get('description')),
            'thumbnail': info.get('thumbnailUrl'),
            'duration': info.get('duration'),
            'timestamp': info.get('createdAt'),
            'uploader_id': format_field(info, 'userId', ignore=('None', None)),
            'view_count': info.get('plays'),
        }
