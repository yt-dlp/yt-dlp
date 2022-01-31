# coding: utf-8
from __future__ import unicode_literals

import re
from uuid import uuid4

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    try_get,
    url_or_none,
    urlencode_postdata,
)


class ZattooPlatformBaseIE(InfoExtractor):
    _power_guide_hash = None

    def _host_url(self):
        return 'https://%s' % (self._API_HOST if hasattr(self, '_API_HOST') else self._HOST)

    def _login(self):
        username, password = self._get_login_info()
        if not username or not password:
            self.raise_login_required(
                'A valid %s account is needed to access this media.'
                % self._NETRC_MACHINE)

        try:
            data = self._download_json(
                '%s/zapi/v2/account/login' % self._host_url(), None, 'Logging in',
                data=urlencode_postdata({
                    'login': username,
                    'password': password,
                    'remember': 'true',
                }), headers={
                    'Referer': '%s/login' % self._host_url(),
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                })
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 400:
                raise ExtractorError(
                    'Unable to login: incorrect username and/or password',
                    expected=True)
            raise

        self._power_guide_hash = data['session']['power_guide_hash']

    def _real_initialize(self):
        session_token = self._download_json(
            f'{self._host_url()}/token.json', None, 'Downloading session token')['session_token']

        # Will setup appropriate cookies
        self._request_webpage(
            '%s/zapi/v3/session/hello' % self._host_url(), None,
            'Opening session', data=urlencode_postdata({
                'uuid': compat_str(uuid4()),
                'lang': 'en',
                'app_version': '1.8.2',
                'format': 'json',
                'client_app_token': session_token,
            }))

        self._login()

    def _extract_video_id_from_recording(self, recid):
        playlist = self._download_json(
            f'{self._host_url()}/zapi/v2/playlist', recid, 'Downloading playlist')
        try:
            return next(
                str(item['program_id']) for item in playlist['recordings']
                if item.get('program_id') and str(item.get('id')) == recid)
        except (StopIteration, KeyError):
            raise ExtractorError('Could not extract video id from recording')

    def _extract_cid(self, video_id, channel_name):
        channel_groups = self._download_json(
            '%s/zapi/v2/cached/channels/%s' % (self._host_url(),
                                               self._power_guide_hash),
            video_id, 'Downloading channel list',
            query={'details': False})['channel_groups']
        channel_list = []
        for chgrp in channel_groups:
            channel_list.extend(chgrp['channels'])
        try:
            return next(
                chan['cid'] for chan in channel_list
                if chan.get('cid') and (
                    chan.get('display_alias') == channel_name
                    or chan.get('cid') == channel_name))
        except StopIteration:
            raise ExtractorError('Could not extract channel id')

    def _extract_cid_and_video_info(self, video_id):
        data = self._download_json(
            '%s/zapi/v2/cached/program/power_details/%s' % (
                self._host_url(), self._power_guide_hash),
            video_id,
            'Downloading video information',
            query={
                'program_ids': video_id,
                'complete': True,
            })

        p = data['programs'][0]
        cid = p['cid']

        info_dict = {
            'id': video_id,
            'title': p.get('t') or p['et'],
            'description': p.get('d'),
            'thumbnail': p.get('i_url'),
            'creator': p.get('channel_name'),
            'episode': p.get('et'),
            'episode_number': int_or_none(p.get('e_no')),
            'season_number': int_or_none(p.get('s_no')),
            'release_year': int_or_none(p.get('year')),
            'categories': try_get(p, lambda x: x['c'], list),
            'tags': try_get(p, lambda x: x['g'], list)
        }

        return cid, info_dict

    def _extract_ondemand_info(self, ondemand_id):
        data = self._download_json(
            '%s/zapi/vod/movies/%s' % (self._host_url(), ondemand_id),
            ondemand_id, 'Downloading ondemand information'
        )
        info_dict = {
            'id': ondemand_id,
            'title': data.get('title'),
            'description': data.get('description'),
            'duration': int_or_none(data.get('duration')),
            'release_year': int_or_none(data.get('year')),
            'episode_number': int_or_none(data.get('episode_number')),
            'season_number': int_or_none(data.get('season_number')),
            'categories': try_get(data, lambda x: x['categories'], list),
        }
        return data['terms_catalog'][0]['terms'][0]['token'], data['type'], info_dict

    def _extract_formats(self, cid, video_id, record_id=None, ondemand_id=None, ondemand_termtoken=None, ondemand_type=None, is_live=False):
        postdata_common = {
            'https_watch_urls': True,
        }

        if is_live:
            postdata_common.update({'timeshift': 10800})
            url = '%s/zapi/watch/live/%s' % (self._host_url(), cid)
        elif record_id:
            url = '%s/zapi/watch/recording/%s' % (self._host_url(), record_id)
        elif ondemand_id:
            postdata_common.update({
                'teasable_id': ondemand_id,
                'term_token': ondemand_termtoken,
                'teasable_type': ondemand_type
            })
            url = '%s/zapi/watch/vod/video' % self._host_url()
        else:
            url = '%s/zapi/v3/watch/replay/%s/%s' % (self._host_url(), cid, video_id)

        formats = []
        for stream_type in ('dash', 'hls', 'hls5', 'hds'):
            postdata = postdata_common.copy()
            postdata['stream_type'] = stream_type

            data = self._download_json(
                url, video_id, 'Downloading %s formats' % stream_type.upper(),
                data=urlencode_postdata(postdata), fatal=False)
            if not data:
                continue

            watch_urls = try_get(
                data, lambda x: x['stream']['watch_urls'], list)
            if not watch_urls:
                continue

            for watch in watch_urls:
                if not isinstance(watch, dict):
                    continue
                watch_url = url_or_none(watch.get('url'))
                if not watch_url:
                    continue
                audio_channel = watch.get('audio_channel')
                preference = 1 if audio_channel == 'A' else None
                format_id = join_nonempty(stream_type, watch.get('maxrate'), audio_channel)
                if stream_type in ('dash', 'dash_widevine', 'dash_playready'):
                    this_formats = self._extract_mpd_formats(
                        watch_url, video_id, mpd_id=format_id, fatal=False)
                elif stream_type in ('hls', 'hls5', 'hls5_fairplay'):
                    this_formats = self._extract_m3u8_formats(
                        watch_url, video_id, 'mp4',
                        entry_protocol='m3u8_native', m3u8_id=format_id,
                        fatal=False)
                elif stream_type == 'hds':
                    this_formats = self._extract_f4m_formats(
                        watch_url, video_id, f4m_id=format_id, fatal=False)
                elif stream_type == 'smooth_playready':
                    this_formats = self._extract_ism_formats(
                        watch_url, video_id, ism_id=format_id, fatal=False)
                else:
                    assert False
                for this_format in this_formats:
                    this_format['quality'] = preference
                formats.extend(this_formats)
        self._sort_formats(formats)
        return formats

    def _extract_video(self, video_id, record_id=None):
        cid, info_dict = self._extract_cid_and_video_info(video_id)
        info_dict['formats'] = self._extract_formats(cid, video_id, record_id=record_id)
        return info_dict

    def _extract_live(self, channel_name):
        cid = self._extract_cid(channel_name, channel_name)
        return {
            'id': channel_name,
            'title': channel_name,
            'is_live': True,
            'format': self._extract_formats(cid, cid, is_live=True),
        }

    def _extract_record(self, record_id):
        video_id = self._extract_video_id_from_recording(record_id)
        cid, info_dict = self._extract_cid_and_video_info(video_id)
        info_dict['formats'] = self._extract_formats(cid, video_id, record_id=record_id)
        return info_dict

    def _extract_ondemand(self, ondemand_id):
        ondemand_termtoken, ondemand_type, info_dict = self._extract_ondemand_info(ondemand_id)
        formats = self._extract_formats(
            None, ondemand_id, ondemand_id=ondemand_id,
            ondemand_termtoken=ondemand_termtoken, ondemand_type=ondemand_type)
        info_dict['formats'] = formats
        return info_dict


class QuicklineBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'quickline'
    _HOST = 'mobiltv.quickline.com'


class QuicklineIE(QuicklineBaseIE):
    _VALID_URL = r'https?://(?:www\.)?%s/watch/[^/]+/(?P<id>[0-9]+)' % re.escape(QuicklineBaseIE._HOST)

    _TEST = {
        'url': 'https://mobiltv.quickline.com/watch/prosieben/130671867-maze-runner-die-auserwaehlten-in-der-brandwueste',
        'only_matching': True,
    }

    def _real_extract(self, url):
        return self._extract_video(self._match_id(url))


class QuicklineLiveIE(QuicklineBaseIE):
    _VALID_URL = r'https?://(?:www\.)?%s/watch/(?P<id>[^/]+)' % re.escape(QuicklineBaseIE._HOST)

    _TEST = {
        'url': 'https://mobiltv.quickline.com/watch/srf1',
        'only_matching': True,
    }

    @classmethod
    def suitable(cls, url):
        return False if QuicklineIE.suitable(url) else super(QuicklineLiveIE, cls).suitable(url)

    def _real_extract(self, url):
        return self._extract_live(self._match_id(url))


class ZattooBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'zattoo'
    _HOST = 'zattoo.com'


def _make_valid_url(tmpl, host):
    return tmpl % re.escape(host)


class ZattooIE(ZattooBaseIE):
    _VALID_URL_TEMPLATE = r'''(?x)
                            https?://(?:www\.)?%s/
                            (?:
                                (?:
                                    vod/movies/([A-Za-z0-9]+)|
                                    (?:program|watch)/([^/]+)/(\d+)|
                                    live/([^/]+)
                                )|
                                (?:
                                    .+\?recording=([0-9]+)|
                                    .+\?movie_id=([A-Za-z0-9]+)|
                                    .+\?channel=([^&]+)(?:
                                        &program=(\d+)
                                    )?
                                )
                            )'''

    _VALID_URL = _make_valid_url(_VALID_URL_TEMPLATE, ZattooBaseIE._HOST)
    _TESTS = [{
        'url': 'https://zattoo.com/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/vod/movies/7521',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/ondemand?movie_id=7521&term_token=9f00f43183269484edde',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/live/srf1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        oid1, cid1, pid1, cid2, record_id, oid2, cid3, pid2 = self._match_valid_url(url).groups()
        ondemand_id = oid1 or oid2
        channel_id = cid1 or cid2 or cid3
        program_id = pid1 or pid2
        if record_id:
            return self._extract_record(record_id)
        elif ondemand_id:
            return self._extract_ondemand(ondemand_id)
        elif channel_id:
            if program_id:
                return self._extract_video(program_id)
            return self._extract_live(channel_id)


class ZattooOldIE(ZattooBaseIE):
    _VALID_URL_TEMPLATE = r'https?://(?:www\.)?%s/watch/[^/]+?/(?P<id>[0-9]+)[^/]+(?:/(?P<recid>[0-9]+))?'
    _VALID_URL = _make_valid_url(_VALID_URL_TEMPLATE, ZattooBaseIE._HOST)

    # Since regular videos are only available for 7 days and recorded videos
    # are only available for a specific user, we cannot have detailed tests.
    _TESTS = [{
        'url': 'https://zattoo.com/watch/prosieben/130671867-maze-runner-die-auserwaehlten-in-der-brandwueste',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/watch/srf_zwei/132905652-eishockey-spengler-cup/102791477/1512211800000/1514433500000/92000',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, record_id = self._match_valid_url(url).groups()
        return self._extract_video(video_id, record_id=record_id)


class ZattooOldLiveIE(ZattooBaseIE):
    _VALID_URL = r'https?://(?:www\.)?zattoo\.com/watch/(?P<id>[^/]+)'

    _TEST = {
        'url': 'https://zattoo.com/watch/srf1',
        'only_matching': True,
    }

    @classmethod
    def suitable(cls, url):
        return False if ZattooOldIE.suitable(url) else super(ZattooOldLiveIE, cls).suitable(url)

    def _real_extract(self, url):
        channel_name = self._match_id(url)
        return self._extract_live(channel_name)


class NetPlusIE(ZattooOldIE):
    _NETRC_MACHINE = 'netplus'
    _HOST = 'netplus.tv'
    _API_HOST = 'www.%s' % _HOST
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://www.netplus.tv/watch/abc/123-abc',
        'only_matching': True,
    }]


class MNetTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'mnettv'
    _HOST = 'tvplus.m-net.de'
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://tvplus.m-net.de/watch/abc/123-abc',
        'only_matching': True,
    }]


class WalyTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'walytv'
    _HOST = 'player.waly.tv'
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://player.waly.tv/watch/abc/123-abc',
        'only_matching': True,
    }]


class BBVTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'bbvtv'
    _HOST = 'bbv-tv.net'
    _API_HOST = 'www.%s' % _HOST
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://www.bbv-tv.net/watch/abc/123-abc',
        'only_matching': True,
    }]


class VTXTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'vtxtv'
    _HOST = 'vtxtv.ch'
    _API_HOST = 'www.%s' % _HOST
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://www.vtxtv.ch/watch/abc/123-abc',
        'only_matching': True,
    }]


class MyVisionTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'myvisiontv'
    _HOST = 'myvisiontv.ch'
    _API_HOST = 'www.%s' % _HOST
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://www.myvisiontv.ch/watch/abc/123-abc',
        'only_matching': True,
    }]


class GlattvisionTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'glattvisiontv'
    _HOST = 'iptv.glattvision.ch'
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://iptv.glattvision.ch/watch/abc/123-abc',
        'only_matching': True,
    }]


class SAKTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'saktv'
    _HOST = 'saktv.ch'
    _API_HOST = 'www.%s' % _HOST
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://www.saktv.ch/watch/abc/123-abc',
        'only_matching': True,
    }]


class EWETVIE(ZattooOldIE):
    _NETRC_MACHINE = 'ewetv'
    _HOST = 'tvonline.ewe.de'
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://tvonline.ewe.de/watch/abc/123-abc',
        'only_matching': True,
    }]


class QuantumTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'quantumtv'
    _HOST = 'quantum-tv.com'
    _API_HOST = 'www.%s' % _HOST
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://www.quantum-tv.com/watch/abc/123-abc',
        'only_matching': True,
    }]


class OsnatelTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'osnateltv'
    _HOST = 'tvonline.osnatel.de'
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://tvonline.osnatel.de/watch/abc/123-abc',
        'only_matching': True,
    }]


class EinsUndEinsTVIE(ZattooOldIE):
    _NETRC_MACHINE = '1und1tv'
    _HOST = '1und1.tv'
    _API_HOST = 'www.%s' % _HOST
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://www.1und1.tv/watch/abc/123-abc',
        'only_matching': True,
    }]


class SaltTVIE(ZattooOldIE):
    _NETRC_MACHINE = 'salttv'
    _HOST = 'tv.salt.ch'
    _VALID_URL = _make_valid_url(ZattooOldIE._VALID_URL_TEMPLATE, _HOST)

    _TESTS = [{
        'url': 'https://tv.salt.ch/watch/abc/123-abc',
        'only_matching': True,
    }]
