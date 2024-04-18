import re
import uuid

from .common import InfoExtractor
from ..compat import compat_str
from ..networking.exceptions import HTTPError
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

    def _real_initialize(self):
        if not self._power_guide_hash:
            self.raise_login_required('An account is needed to access this media', method='password')

    def _perform_login(self, username, password):
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
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                raise ExtractorError(
                    'Unable to login: incorrect username and/or password',
                    expected=True)
            raise

        self._power_guide_hash = data['session']['power_guide_hash']

    def _initialize_pre_login(self):
        session_token = self._download_json(
            f'{self._host_url()}/token.json', None, 'Downloading session token')['session_token']

        # Will setup appropriate cookies
        self._request_webpage(
            '%s/zapi/v3/session/hello' % self._host_url(), None,
            'Opening session', data=urlencode_postdata({
                'uuid': compat_str(uuid.uuid4()),
                'lang': 'en',
                'app_version': '1.8.2',
                'format': 'json',
                'client_app_token': session_token,
            }))

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
        """
        @returns    (ondemand_token, ondemand_type, info_dict)
        """
        data = self._download_json(
            '%s/zapi/vod/movies/%s' % (self._host_url(), ondemand_id),
            ondemand_id, 'Downloading ondemand information')
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
        subtitles = {}
        for stream_type in ('dash', 'hls7'):
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
                if stream_type.startswith('dash'):
                    this_formats, subs = self._extract_mpd_formats_and_subtitles(
                        watch_url, video_id, mpd_id=format_id, fatal=False)
                    self._merge_subtitles(subs, target=subtitles)
                elif stream_type.startswith('hls'):
                    this_formats, subs = self._extract_m3u8_formats_and_subtitles(
                        watch_url, video_id, 'mp4',
                        entry_protocol='m3u8_native', m3u8_id=format_id,
                        fatal=False)
                    self._merge_subtitles(subs, target=subtitles)
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
        return formats, subtitles

    def _extract_video(self, video_id, record_id=None):
        cid, info_dict = self._extract_cid_and_video_info(video_id)
        info_dict['formats'], info_dict['subtitles'] = self._extract_formats(cid, video_id, record_id=record_id)
        return info_dict

    def _extract_live(self, channel_name):
        cid = self._extract_cid(channel_name, channel_name)
        formats, subtitles = self._extract_formats(cid, cid, is_live=True)
        return {
            'id': channel_name,
            'title': channel_name,
            'is_live': True,
            'formats': formats,
            'subtitles': subtitles
        }

    def _extract_record(self, record_id):
        video_id = self._extract_video_id_from_recording(record_id)
        cid, info_dict = self._extract_cid_and_video_info(video_id)
        info_dict['formats'], info_dict['subtitles'] = self._extract_formats(cid, video_id, record_id=record_id)
        return info_dict

    def _extract_ondemand(self, ondemand_id):
        ondemand_termtoken, ondemand_type, info_dict = self._extract_ondemand_info(ondemand_id)
        info_dict['formats'], info_dict['subtitles'] = self._extract_formats(
            None, ondemand_id, ondemand_id=ondemand_id,
            ondemand_termtoken=ondemand_termtoken, ondemand_type=ondemand_type)
        return info_dict

    def _real_extract(self, url):
        video_id, record_id = self._match_valid_url(url).groups()
        return getattr(self, f'_extract_{self._TYPE}')(video_id or record_id)


def _create_valid_url(host, match, qs, base_re=None):
    match_base = fr'|{base_re}/(?P<vid1>{match})' if base_re else '(?P<vid1>)'
    return rf'''(?x)https?://(?:www\.)?{re.escape(host)}/(?:
        [^?#]+\?(?:[^#]+&)?{qs}=(?P<vid2>{match})
        {match_base}
    )'''


class ZattooBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'zattoo'
    _HOST = 'zattoo.com'


class ZattooIE(ZattooBaseIE):
    _VALID_URL = _create_valid_url(ZattooBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://zattoo.com/program/zdf/250170418',
        'info_dict': {
            'id': '250170418',
            'ext': 'mp4',
            'title': 'Markus Lanz',
            'description': 'md5:e41cb1257de008ca62a73bb876ffa7fc',
            'thumbnail': 're:http://images.zattic.com/cms/.+/format_480x360.jpg',
            'creator': 'ZDF HD',
            'release_year': 2022,
            'episode': 'Folge 1655',
            'categories': 'count:1',
            'tags': 'count:2'
        },
        'params': {'skip_download': 'm3u8'}
    }, {
        'url': 'https://zattoo.com/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class ZattooLiveIE(ZattooBaseIE):
    _VALID_URL = _create_valid_url(ZattooBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://zattoo.com/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if ZattooIE.suitable(url) else super().suitable(url)


class ZattooMoviesIE(ZattooBaseIE):
    _VALID_URL = _create_valid_url(ZattooBaseIE._HOST, r'\w+', 'movie_id', 'vod/movies')
    _TYPE = 'ondemand'
    _TESTS = [{
        'url': 'https://zattoo.com/vod/movies/7521',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/ondemand?movie_id=7521&term_token=9f00f43183269484edde',
        'only_matching': True,
    }]


class ZattooRecordingsIE(ZattooBaseIE):
    _VALID_URL = _create_valid_url('zattoo.com', r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://zattoo.com/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://zattoo.com/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class NetPlusTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'netplus'
    _HOST = 'netplus.tv'
    _API_HOST = 'www.%s' % _HOST


class NetPlusTVIE(NetPlusTVBaseIE):
    _VALID_URL = _create_valid_url(NetPlusTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://netplus.tv/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://netplus.tv/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class NetPlusTVLiveIE(NetPlusTVBaseIE):
    _VALID_URL = _create_valid_url(NetPlusTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://netplus.tv/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://netplus.tv/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if NetPlusTVIE.suitable(url) else super().suitable(url)


class NetPlusTVRecordingsIE(NetPlusTVBaseIE):
    _VALID_URL = _create_valid_url(NetPlusTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://netplus.tv/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://netplus.tv/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class MNetTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'mnettv'
    _HOST = 'tvplus.m-net.de'


class MNetTVIE(MNetTVBaseIE):
    _VALID_URL = _create_valid_url(MNetTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://tvplus.m-net.de/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://tvplus.m-net.de/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class MNetTVLiveIE(MNetTVBaseIE):
    _VALID_URL = _create_valid_url(MNetTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://tvplus.m-net.de/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://tvplus.m-net.de/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if MNetTVIE.suitable(url) else super().suitable(url)


class MNetTVRecordingsIE(MNetTVBaseIE):
    _VALID_URL = _create_valid_url(MNetTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://tvplus.m-net.de/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://tvplus.m-net.de/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class WalyTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'walytv'
    _HOST = 'player.waly.tv'


class WalyTVIE(WalyTVBaseIE):
    _VALID_URL = _create_valid_url(WalyTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://player.waly.tv/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://player.waly.tv/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class WalyTVLiveIE(WalyTVBaseIE):
    _VALID_URL = _create_valid_url(WalyTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://player.waly.tv/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://player.waly.tv/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if WalyTVIE.suitable(url) else super().suitable(url)


class WalyTVRecordingsIE(WalyTVBaseIE):
    _VALID_URL = _create_valid_url(WalyTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://player.waly.tv/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://player.waly.tv/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class BBVTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'bbvtv'
    _HOST = 'bbv-tv.net'
    _API_HOST = 'www.%s' % _HOST


class BBVTVIE(BBVTVBaseIE):
    _VALID_URL = _create_valid_url(BBVTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://bbv-tv.net/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://bbv-tv.net/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class BBVTVLiveIE(BBVTVBaseIE):
    _VALID_URL = _create_valid_url(BBVTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://bbv-tv.net/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://bbv-tv.net/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if BBVTVIE.suitable(url) else super().suitable(url)


class BBVTVRecordingsIE(BBVTVBaseIE):
    _VALID_URL = _create_valid_url(BBVTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://bbv-tv.net/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://bbv-tv.net/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class VTXTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'vtxtv'
    _HOST = 'vtxtv.ch'
    _API_HOST = 'www.%s' % _HOST


class VTXTVIE(VTXTVBaseIE):
    _VALID_URL = _create_valid_url(VTXTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://vtxtv.ch/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://vtxtv.ch/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class VTXTVLiveIE(VTXTVBaseIE):
    _VALID_URL = _create_valid_url(VTXTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://vtxtv.ch/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://vtxtv.ch/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if VTXTVIE.suitable(url) else super().suitable(url)


class VTXTVRecordingsIE(VTXTVBaseIE):
    _VALID_URL = _create_valid_url(VTXTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://vtxtv.ch/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://vtxtv.ch/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class GlattvisionTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'glattvisiontv'
    _HOST = 'iptv.glattvision.ch'


class GlattvisionTVIE(GlattvisionTVBaseIE):
    _VALID_URL = _create_valid_url(GlattvisionTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://iptv.glattvision.ch/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://iptv.glattvision.ch/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class GlattvisionTVLiveIE(GlattvisionTVBaseIE):
    _VALID_URL = _create_valid_url(GlattvisionTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://iptv.glattvision.ch/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://iptv.glattvision.ch/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if GlattvisionTVIE.suitable(url) else super().suitable(url)


class GlattvisionTVRecordingsIE(GlattvisionTVBaseIE):
    _VALID_URL = _create_valid_url(GlattvisionTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://iptv.glattvision.ch/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://iptv.glattvision.ch/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class SAKTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'saktv'
    _HOST = 'saktv.ch'
    _API_HOST = 'www.%s' % _HOST


class SAKTVIE(SAKTVBaseIE):
    _VALID_URL = _create_valid_url(SAKTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://saktv.ch/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://saktv.ch/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class SAKTVLiveIE(SAKTVBaseIE):
    _VALID_URL = _create_valid_url(SAKTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://saktv.ch/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://saktv.ch/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if SAKTVIE.suitable(url) else super().suitable(url)


class SAKTVRecordingsIE(SAKTVBaseIE):
    _VALID_URL = _create_valid_url(SAKTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://saktv.ch/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://saktv.ch/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class EWETVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'ewetv'
    _HOST = 'tvonline.ewe.de'


class EWETVIE(EWETVBaseIE):
    _VALID_URL = _create_valid_url(EWETVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://tvonline.ewe.de/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://tvonline.ewe.de/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class EWETVLiveIE(EWETVBaseIE):
    _VALID_URL = _create_valid_url(EWETVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://tvonline.ewe.de/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://tvonline.ewe.de/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if EWETVIE.suitable(url) else super().suitable(url)


class EWETVRecordingsIE(EWETVBaseIE):
    _VALID_URL = _create_valid_url(EWETVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://tvonline.ewe.de/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://tvonline.ewe.de/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class QuantumTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'quantumtv'
    _HOST = 'quantum-tv.com'
    _API_HOST = 'www.%s' % _HOST


class QuantumTVIE(QuantumTVBaseIE):
    _VALID_URL = _create_valid_url(QuantumTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://quantum-tv.com/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://quantum-tv.com/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class QuantumTVLiveIE(QuantumTVBaseIE):
    _VALID_URL = _create_valid_url(QuantumTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://quantum-tv.com/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://quantum-tv.com/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if QuantumTVIE.suitable(url) else super().suitable(url)


class QuantumTVRecordingsIE(QuantumTVBaseIE):
    _VALID_URL = _create_valid_url(QuantumTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://quantum-tv.com/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://quantum-tv.com/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class OsnatelTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'osnateltv'
    _HOST = 'tvonline.osnatel.de'


class OsnatelTVIE(OsnatelTVBaseIE):
    _VALID_URL = _create_valid_url(OsnatelTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://tvonline.osnatel.de/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://tvonline.osnatel.de/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class OsnatelTVLiveIE(OsnatelTVBaseIE):
    _VALID_URL = _create_valid_url(OsnatelTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://tvonline.osnatel.de/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://tvonline.osnatel.de/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if OsnatelTVIE.suitable(url) else super().suitable(url)


class OsnatelTVRecordingsIE(OsnatelTVBaseIE):
    _VALID_URL = _create_valid_url(OsnatelTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://tvonline.osnatel.de/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://tvonline.osnatel.de/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class EinsUndEinsTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = '1und1tv'
    _HOST = '1und1.tv'
    _API_HOST = 'www.%s' % _HOST


class EinsUndEinsTVIE(EinsUndEinsTVBaseIE):
    _VALID_URL = _create_valid_url(EinsUndEinsTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://1und1.tv/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://1und1.tv/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class EinsUndEinsTVLiveIE(EinsUndEinsTVBaseIE):
    _VALID_URL = _create_valid_url(EinsUndEinsTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://1und1.tv/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://1und1.tv/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if EinsUndEinsTVIE.suitable(url) else super().suitable(url)


class EinsUndEinsTVRecordingsIE(EinsUndEinsTVBaseIE):
    _VALID_URL = _create_valid_url(EinsUndEinsTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://1und1.tv/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://1und1.tv/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]


class SaltTVBaseIE(ZattooPlatformBaseIE):
    _NETRC_MACHINE = 'salttv'
    _HOST = 'tv.salt.ch'


class SaltTVIE(SaltTVBaseIE):
    _VALID_URL = _create_valid_url(SaltTVBaseIE._HOST, r'\d+', 'program', '(?:program|watch)/[^/]+')
    _TYPE = 'video'
    _TESTS = [{
        'url': 'https://tv.salt.ch/program/daserste/210177916',
        'only_matching': True,
    }, {
        'url': 'https://tv.salt.ch/guide/german?channel=srf1&program=169860555',
        'only_matching': True,
    }]


class SaltTVLiveIE(SaltTVBaseIE):
    _VALID_URL = _create_valid_url(SaltTVBaseIE._HOST, r'[^/?&#]+', 'channel', 'live')
    _TYPE = 'live'
    _TESTS = [{
        'url': 'https://tv.salt.ch/channels/german?channel=srf_zwei',
        'only_matching': True,
    }, {
        'url': 'https://tv.salt.ch/live/srf1',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if SaltTVIE.suitable(url) else super().suitable(url)


class SaltTVRecordingsIE(SaltTVBaseIE):
    _VALID_URL = _create_valid_url(SaltTVBaseIE._HOST, r'\d+', 'recording')
    _TYPE = 'record'
    _TESTS = [{
        'url': 'https://tv.salt.ch/recordings?recording=193615508',
        'only_matching': True,
    }, {
        'url': 'https://tv.salt.ch/tc/ptc_recordings_all_recordings?recording=193615420',
        'only_matching': True,
    }]
