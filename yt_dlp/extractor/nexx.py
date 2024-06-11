import hashlib
import random
import re
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_duration,
    srt_subtitles_timecode,
    traverse_obj,
    try_get,
    urlencode_postdata,
)


class NexxIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        (?:
                            https?://api\.nexx(?:\.cloud|cdn\.com)/v3(?:\.\d)?/(?P<domain_id>\d+)/videos/byid/|
                            nexx:(?:(?P<domain_id_s>\d+):)?|
                            https?://arc\.nexx\.cloud/api/video/
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [{
        # movie
        'url': 'https://api.nexx.cloud/v3/748/videos/byid/128907',
        'md5': '31899fd683de49ad46f4ee67e53e83fe',
        'info_dict': {
            'id': '128907',
            'ext': 'mp4',
            'title': 'Stiftung Warentest',
            'alt_title': 'Wie ein Test abläuft',
            'description': 'md5:d1ddb1ef63de721132abd38639cc2fd2',
            'creator': 'SPIEGEL TV',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2509,
            'timestamp': 1384264416,
            'upload_date': '20131112',
        },
        'skip': 'Spiegel nexx CDNs are now disabled',
    }, {
        # episode with captions
        'url': 'https://api.nexx.cloud/v3.1/741/videos/byid/1701834',
        'info_dict': {
            'id': '1701834',
            'ext': 'mp4',
            'title': 'Mein Leben mit \'nem TikTok E-Boy 😤',
            'alt_title': 'Mein Leben mit \'nem TikTok E-Boy 😤',
            'description': 'md5:f84f395a881fd143f952c892deab528d',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 770,
            'timestamp': 1595600027,
            'upload_date': '20200724',
            'episode_number': 2,
            'season_number': 2,
            'episode': 'Episode 2',
            'season': 'Season 2',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'nexx:741:1269984',
        'md5': 'd5f14e14b592501e51addd5abef95a7f',
        'info_dict': {
            'id': '1269984',
            'ext': 'mp4',
            'title': '1 TAG ohne KLO... wortwörtlich! ?',
            'alt_title': '1 TAG ohne KLO... wortwörtlich! ?',
            'description': 'md5:2016393a31991a900946432ccdd09a6f',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 607,
            'timestamp': 1518614955,
            'upload_date': '20180214',
        },
    }, {
        # free cdn from http://www.spiegel.de/video/eifel-zoo-aufregung-um-ausgebrochene-raubtiere-video-99018031.html
        'url': 'nexx:747:1533779',
        'md5': '6bf6883912b82b7069fb86c2297e9893',
        'info_dict': {
            'id': '1533779',
            'ext': 'mp4',
            'title': 'Aufregung um ausgebrochene Raubtiere',
            'alt_title': 'Eifel-Zoo',
            'description': 'md5:f21375c91c74ad741dcb164c427999d2',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 111,
            'timestamp': 1527874460,
            'upload_date': '20180601',
        },
        'skip': 'Spiegel nexx CDNs are now disabled',
    }, {
        'url': 'https://api.nexxcdn.com/v3/748/videos/byid/128907',
        'only_matching': True,
    }, {
        'url': 'nexx:748:128907',
        'only_matching': True,
    }, {
        'url': 'nexx:128907',
        'only_matching': True,
    }, {
        'url': 'https://arc.nexx.cloud/api/video/128907.json',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_domain_id(webpage):
        mobj = re.search(
            r'<script\b[^>]+\bsrc=["\'](?:https?:)?//(?:require|arc)\.nexx(?:\.cloud|cdn\.com)/(?:sdk/)?(?P<id>\d+)',
            webpage)
        return mobj.group('id') if mobj else None

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        # Reference:
        # 1. https://nx-s.akamaized.net/files/201510/44.pdf

        entries = []

        # JavaScript Integration
        domain_id = NexxIE._extract_domain_id(webpage)
        if domain_id:
            for video_id in re.findall(
                    r'(?is)onPLAYReady.+?_play\.(?:init|(?:control\.)?addPlayer)\s*\(.+?\s*,\s*["\']?(\d+)',
                    webpage):
                entries.append(
                    f'https://api.nexx.cloud/v3/{domain_id}/videos/byid/{video_id}')

        # TODO: support more embed formats

        return entries

    def _handle_error(self, response):
        if traverse_obj(response, ('metadata', 'notice'), expected_type=str):
            self.report_warning('{} said: {}'.format(self.IE_NAME, response['metadata']['notice']))
        status = int_or_none(try_get(
            response, lambda x: x['metadata']['status']) or 200)
        if 200 <= status < 300:
            return
        raise ExtractorError(
            '{} said: {}'.format(self.IE_NAME, response['metadata']['errorhint']),
            expected=True)

    def _call_api(self, domain_id, path, video_id, data=None, headers={}):
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        result = self._download_json(
            f'https://api.nexx.cloud/v3/{domain_id}/{path}', video_id,
            f'Downloading {path} JSON', data=urlencode_postdata(data),
            headers=headers)
        self._handle_error(result)
        return result['result']

    def _extract_free_formats(self, video, video_id):
        stream_data = video['streamdata']
        cdn = stream_data['cdnType']
        assert cdn == 'free'

        video_hash = video['general']['hash']

        ps = str(stream_data['originalDomain'])
        if stream_data['applyFolderHierarchy'] == 1:
            s = ('%04d' % int(video_id))[::-1]
            ps += f'/{s[0:2]}/{s[2:4]}'
        ps += f'/{video_id}/{video_hash}_'

        t = 'http://%s' + ps
        fd = stream_data['azureFileDistribution'].split(',')
        cdn_provider = stream_data['cdnProvider']

        def p0(p):
            return f'_{p}' if stream_data['applyAzureStructure'] == 1 else ''

        formats = []
        if cdn_provider == 'ak':
            t += ','
            for i in fd:
                p = i.split(':')
                t += p[1] + p0(int(p[0])) + ','
            t += '.mp4.csmil/master.%s'
        elif cdn_provider == 'ce':
            k = t.split('/')
            h = k.pop()
            http_base = t = '/'.join(k)
            http_base = http_base % stream_data['cdnPathHTTP']
            t += '/asset.ism/manifest.%s?dcp_ver=aos4&videostream='
            for i in fd:
                p = i.split(':')
                tbr = int(p[0])
                filename = f'{h}{p[1]}{p0(tbr)}.mp4'
                f = {
                    'url': http_base + '/' + filename,
                    'format_id': f'{cdn}-http-{tbr}',
                    'tbr': tbr,
                }
                width_height = p[1].split('x')
                if len(width_height) == 2:
                    f.update({
                        'width': int_or_none(width_height[0]),
                        'height': int_or_none(width_height[1]),
                    })
                formats.append(f)
                a = filename + f':{tbr * 1000}'
                t += a + ','
            t = t[:-1] + '&audiostream=' + a.split(':')[0]
        else:
            assert False

        if cdn_provider == 'ce':
            formats.extend(self._extract_mpd_formats(
                t % (stream_data['cdnPathDASH'], 'mpd'), video_id,
                mpd_id=f'{cdn}-dash', fatal=False))
        formats.extend(self._extract_m3u8_formats(
            t % (stream_data['cdnPathHLS'], 'm3u8'), video_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id=f'{cdn}-hls', fatal=False))

        return formats

    def _extract_3q_formats(self, video, video_id):
        stream_data = video['streamdata']
        cdn = stream_data['cdnType']
        assert cdn == '3q'

        q_acc, q_prefix, q_locator, q_hash = stream_data['qAccount'], stream_data['qPrefix'], stream_data['qLocator'], stream_data['qHash']
        protection_key = traverse_obj(
            video, ('protectiondata', 'key'), expected_type=str)

        def get_cdn_shield_base(shield_type=''):
            for secure in ('', 's'):
                cdn_shield = stream_data.get(f'cdnShield{shield_type}HTTP{secure.upper()}')
                if cdn_shield:
                    return f'http{secure}://{cdn_shield}'
            return f'http://sdn-global-{"prog" if shield_type.lower() == "prog" else "streaming"}-cache.3qsdn.com/' + (f's/{protection_key}/' if protection_key else '')

        stream_base = get_cdn_shield_base()

        formats = []
        formats.extend(self._extract_m3u8_formats(
            f'{stream_base}{q_acc}/files/{q_prefix}/{q_locator}/{q_acc}-{stream_data.get("qHEVCHash") or q_hash}.ism/manifest.m3u8',
            video_id, 'mp4', m3u8_id=f'{cdn}-hls', fatal=False))
        formats.extend(self._extract_mpd_formats(
            f'{stream_base}{q_acc}/files/{q_prefix}/{q_locator}/{q_acc}-{q_hash}.ism/manifest.mpd',
            video_id, mpd_id=f'{cdn}-dash', fatal=False))

        progressive_base = get_cdn_shield_base('Prog')
        q_references = stream_data.get('qReferences') or ''
        fds = q_references.split(',')
        for fd in fds:
            ss = fd.split(':')
            if len(ss) != 3:
                continue
            tbr = int_or_none(ss[1], scale=1000)
            formats.append({
                'url': f'{progressive_base}{q_acc}/uploads/{q_acc}-{ss[2]}.webm',
                'format_id': f'{cdn}-{ss[0]}{f"-{tbr}" if tbr else ""}',
                'tbr': tbr,
            })

        azure_file_distribution = stream_data.get('azureFileDistribution') or ''
        fds = azure_file_distribution.split(',')
        for fd in fds:
            ss = fd.split(':')
            if len(ss) != 3:
                continue
            tbr = int_or_none(ss[0])
            width, height = ss[1].split('x') if len(ss[1].split('x')) == 2 else (None, None)
            f = {
                'url': f'{progressive_base}{q_acc}/files/{q_prefix}/{q_locator}/{ss[2]}.mp4',
                'format_id': f'{cdn}-http-{f"-{tbr}" if tbr else ""}',
                'tbr': tbr,
                'width': int_or_none(width),
                'height': int_or_none(height),
            }
            formats.append(f)

        return formats

    def _extract_azure_formats(self, video, video_id):
        stream_data = video['streamdata']
        cdn = stream_data['cdnType']
        assert cdn == 'azure'

        azure_locator = stream_data['azureLocator']

        def get_cdn_shield_base(shield_type='', static=False):
            for secure in ('', 's'):
                cdn_shield = stream_data.get(f'cdnShield{shield_type}HTTP{secure.upper()}')
                if cdn_shield:
                    return f'http{secure}://{cdn_shield}'
            if 'fb' in stream_data['azureAccount']:
                prefix = 'df' if static else 'f'
            else:
                prefix = 'd' if static else 'p'
            account = int(stream_data['azureAccount'].replace('nexxplayplus', '').replace('nexxplayfb', ''))
            return 'http://nx-%s%02d.akamaized.net/' % (prefix, account)

        language = video['general'].get('language_raw') or ''

        azure_stream_base = get_cdn_shield_base()
        is_ml = ',' in language
        azure_manifest_url = '{}{}/{}_src{}.ism/Manifest'.format(
            azure_stream_base, azure_locator, video_id, ('_manifest' if is_ml else '')) + '%s'

        protection_token = try_get(
            video, lambda x: x['protectiondata']['token'], str)
        if protection_token:
            azure_manifest_url += f'?hdnts={protection_token}'

        formats = self._extract_m3u8_formats(
            azure_manifest_url % '(format=m3u8-aapl)',
            video_id, 'mp4', 'm3u8_native',
            m3u8_id=f'{cdn}-hls', fatal=False)
        formats.extend(self._extract_mpd_formats(
            azure_manifest_url % '(format=mpd-time-csf)',
            video_id, mpd_id=f'{cdn}-dash', fatal=False))
        formats.extend(self._extract_ism_formats(
            azure_manifest_url % '', video_id, ism_id=f'{cdn}-mss', fatal=False))

        azure_progressive_base = get_cdn_shield_base('Prog', True)
        azure_file_distribution = stream_data.get('azureFileDistribution')
        if azure_file_distribution:
            fds = azure_file_distribution.split(',')
            if fds:
                for fd in fds:
                    ss = fd.split(':')
                    if len(ss) == 2:
                        tbr = int_or_none(ss[0])
                        if tbr:
                            f = {
                                'url': f'{azure_progressive_base}{azure_locator}/{video_id}_src_{ss[1]}_{tbr}.mp4',
                                'format_id': f'{cdn}-http-{tbr}',
                                'tbr': tbr,
                            }
                            width_height = ss[1].split('x')
                            if len(width_height) == 2:
                                f.update({
                                    'width': int_or_none(width_height[0]),
                                    'height': int_or_none(width_height[1]),
                                })
                            formats.append(f)

        return formats

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        domain_id = mobj.group('domain_id') or mobj.group('domain_id_s')
        video_id = mobj.group('id')

        video = None

        def find_video(result):
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                vid = int(video_id)
                for v in result:
                    if try_get(v, lambda x: x['general']['ID'], int) == vid:
                        return v
            return None

        response = self._download_json(
            f'https://arc.nexx.cloud/api/video/{video_id}.json',
            video_id, fatal=False)
        if response and isinstance(response, dict):
            result = response.get('result')
            if result:
                video = find_video(result)

        # not all videos work via arc, e.g. nexx:741:1269984
        if not video:
            # Reverse engineered from JS code (see getDeviceID function)
            device_id = f'{random.randint(1, 4)}:{int(time.time())}:{random.randint(1e4, 99999)}{random.randint(1, 9)}'

            result = self._call_api(domain_id, 'session/init', video_id, data={
                'nxp_devh': device_id,
                'nxp_userh': '',
                'precid': '0',
                'playlicense': '0',
                'screenx': '1920',
                'screeny': '1080',
                'playerversion': '6.0.00',
                'gateway': 'html5',
                'adGateway': '',
                'explicitlanguage': 'en-US',
                'addTextTemplates': '1',
                'addDomainData': '1',
                'addAdModel': '1',
            }, headers={
                'X-Request-Enable-Auth-Fallback': '1',
            })

            cid = result['general']['cid']

            # As described in [1] X-Request-Token generation algorithm is
            # as follows:
            #   md5( operation + domain_id + domain_secret )
            # where domain_secret is a static value that will be given by nexx.tv
            # as per [1]. Here is how this "secret" is generated (reversed
            # from _play._factory.data.getDomainData function, search for
            # domaintoken or enableAPIAccess). So it's actually not static
            # and not that much of a secret.
            # 1. https://nexxtvstorage.blob.core.windows.net/files/201610/27.pdf
            secret = result['device']['domaintoken'][int(device_id[0]):]
            secret = secret[0:len(secret) - int(device_id[-1])]

            op = 'byid'

            # Reversed from JS code for _play.api.call function (search for
            # X-Request-Token)
            request_token = hashlib.md5(
                ''.join((op, domain_id, secret)).encode()).hexdigest()

            result = self._call_api(
                domain_id, f'videos/{op}/{video_id}', video_id, data={
                    'additionalfields': 'language,channel,format,licenseby,slug,fileversion,episode,season',
                    'addInteractionOptions': '1',
                    'addStatusDetails': '1',
                    'addStreamDetails': '1',
                    'addFeatures': '1',
                    # Caption format selection doesn't seem to be enforced?
                    'addCaptions': 'vtt',
                    'addScenes': '1',
                    'addChapters': '1',
                    'addHotSpots': '1',
                    'addConnectedMedia': 'persons',
                    'addBumpers': '1',
                }, headers={
                    'X-Request-CID': cid,
                    'X-Request-Token': request_token,
                })
            video = find_video(result)

        general = video['general']
        title = general['title']

        cdn = video['streamdata']['cdnType']

        if cdn == 'azure':
            formats = self._extract_azure_formats(video, video_id)
        elif cdn == 'free':
            formats = self._extract_free_formats(video, video_id)
        elif cdn == '3q':
            formats = self._extract_3q_formats(video, video_id)
        else:
            self.raise_no_formats(f'{cdn} formats are currently not supported', video_id)

        subtitles = {}
        for sub in video.get('captiondata') or []:
            if sub.get('data'):
                subtitles.setdefault(sub.get('language', 'en'), []).append({
                    'ext': 'srt',
                    'data': '\n\n'.join(
                        f'{i + 1}\n{srt_subtitles_timecode(line["fromms"] / 1000)} --> {srt_subtitles_timecode(line["toms"] / 1000)}\n{line["caption"]}'
                        for i, line in enumerate(sub['data'])),
                    'name': sub.get('language_long') or sub.get('title'),
                })
            elif sub.get('url'):
                subtitles.setdefault(sub.get('language', 'en'), []).append({
                    'url': sub['url'],
                    'ext': sub.get('format'),
                    'name': sub.get('language_long') or sub.get('title'),
                })

        return {
            'id': video_id,
            'title': title,
            'alt_title': general.get('subtitle'),
            'description': general.get('description'),
            'release_year': int_or_none(general.get('year')),
            'creator': general.get('studio') or general.get('studio_adref') or None,
            'thumbnail': try_get(
                video, lambda x: x['imagedata']['thumb'], str),
            'duration': parse_duration(general.get('runtime')),
            'timestamp': int_or_none(general.get('uploaded')),
            'episode_number': traverse_obj(
                video, (('episodedata', 'general'), 'episode'), expected_type=int, get_all=False),
            'season_number': traverse_obj(
                video, (('episodedata', 'general'), 'season'), expected_type=int, get_all=False),
            'cast': traverse_obj(video, ('connectedmedia', ..., 'title'), expected_type=str),
            'formats': formats,
            'subtitles': subtitles,
        }


class NexxEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://embed\.nexx(?:\.cloud|cdn\.com)/\d+/(?:video/)?(?P<id>[^/?#&]+)'
    # Reference. https://nx-s.akamaized.net/files/201510/44.pdf
    _EMBED_REGEX = [r'<iframe[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//embed\.nexx(?:\.cloud|cdn\.com)/\d+/(?:(?!\1).)+)\1']
    _TESTS = [{
        'url': 'http://embed.nexx.cloud/748/KC1614647Z27Y7T?autoplay=1',
        'md5': '16746bfc28c42049492385c989b26c4a',
        'info_dict': {
            'id': '161464',
            'ext': 'mp4',
            'title': 'Nervenkitzel Achterbahn',
            'alt_title': 'Karussellbauer in Deutschland',
            'description': 'md5:ffe7b1cc59a01f585e0569949aef73cc',
            'creator': 'SPIEGEL TV',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2761,
            'timestamp': 1394021479,
            'upload_date': '20140305',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://embed.nexx.cloud/11888/video/DSRTO7UVOX06S7',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        embed_id = self._match_id(url)

        webpage = self._download_webpage(url, embed_id)

        return self.url_result(NexxIE._extract_url(webpage), ie=NexxIE.ie_key())
