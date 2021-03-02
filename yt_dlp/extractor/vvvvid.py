# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
)


class VVVVIDIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?vvvvid\.it/(?:#!)?(?:show|anime|film|series)/'
    _VALID_URL = r'%s(?P<show_id>\d+)/[^/]+/(?P<season_id>\d+)/(?P<id>[0-9]+)' % _VALID_URL_BASE
    _TESTS = [{
        # video_type == 'video/vvvvid'
        'url': 'https://www.vvvvid.it/#!show/434/perche-dovrei-guardarlo-di-dario-moccia/437/489048/ping-pong',
        'md5': 'b8d3cecc2e981adc3835adf07f6df91b',
        'info_dict': {
            'id': '489048',
            'ext': 'mp4',
            'title': 'Ping Pong',
            'duration': 239,
            'series': '"Perché dovrei guardarlo?" di Dario Moccia',
            'season_id': '437',
            'episode': 'Ping Pong',
            'episode_number': 1,
            'episode_id': '3334',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # video_type == 'video/rcs'
        'url': 'https://www.vvvvid.it/#!show/376/death-note-live-action/377/482493/episodio-01',
        'md5': '33e0edfba720ad73a8782157fdebc648',
        'info_dict': {
            'id': '482493',
            'ext': 'mp4',
            'title': 'Episodio 01',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # video_type == 'video/youtube'
        'url': 'https://www.vvvvid.it/show/404/one-punch-man/406/486683/trailer',
        'md5': '33e0edfba720ad73a8782157fdebc648',
        'info_dict': {
            'id': 'RzmFKUDOUgw',
            'ext': 'mp4',
            'title': 'Trailer',
            'upload_date': '20150906',
            'description': 'md5:a5e802558d35247fee285875328c0b80',
            'uploader_id': 'BandaiVisual',
            'uploader': 'BANDAI NAMCO Arts Channel',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.vvvvid.it/show/434/perche-dovrei-guardarlo-di-dario-moccia/437/489048',
        'only_matching': True
    }]
    _conn_id = None

    def _real_initialize(self):
        self._conn_id = self._download_json(
            'https://www.vvvvid.it/user/login',
            None, headers=self.geo_verification_headers())['data']['conn_id']

    def _download_info(self, show_id, path, video_id, fatal=True, query=None):
        q = {
            'conn_id': self._conn_id,
        }
        if query:
            q.update(query)
        response = self._download_json(
            'https://www.vvvvid.it/vvvvid/ondemand/%s/%s' % (show_id, path),
            video_id, headers=self.geo_verification_headers(), query=q, fatal=fatal)
        if not (response or fatal):
            return
        if response.get('result') == 'error':
            raise ExtractorError('%s said: %s' % (
                self.IE_NAME, response['message']), expected=True)
        return response['data']

    def _extract_common_video_info(self, video_data):
        return {
            'thumbnail': video_data.get('thumbnail'),
            'episode_id': str_or_none(video_data.get('id')),
        }

    def _real_extract(self, url):
        show_id, season_id, video_id = re.match(self._VALID_URL, url).groups()

        response = self._download_info(
            show_id, 'season/%s' % season_id,
            video_id, query={'video_id': video_id})

        vid = int(video_id)
        video_data = list(filter(
            lambda episode: episode.get('video_id') == vid, response))[0]
        title = video_data['title']
        formats = []

        # vvvvid embed_info decryption algorithm is reverse engineered from function $ds(h) at vvvvid.js
        def ds(h):
            g = "MNOPIJKL89+/4567UVWXQRSTEFGHABCDcdefYZabstuvopqr0123wxyzklmnghij"

            def f(m):
                l = []
                o = 0
                b = False
                m_len = len(m)
                while ((not b) and o < m_len):
                    n = m[o] << 2
                    o += 1
                    k = -1
                    j = -1
                    if o < m_len:
                        n += m[o] >> 4
                        o += 1
                        if o < m_len:
                            k = (m[o - 1] << 4) & 255
                            k += m[o] >> 2
                            o += 1
                            if o < m_len:
                                j = (m[o - 1] << 6) & 255
                                j += m[o]
                                o += 1
                            else:
                                b = True
                        else:
                            b = True
                    else:
                        b = True
                    l.append(n)
                    if k != -1:
                        l.append(k)
                    if j != -1:
                        l.append(j)
                return l

            c = []
            for e in h:
                c.append(g.index(e))

            c_len = len(c)
            for e in range(c_len * 2 - 1, -1, -1):
                a = c[e % c_len] ^ c[(e + 1) % c_len]
                c[e % c_len] = a

            c = f(c)
            d = ''
            for e in c:
                d += chr(e)

            return d

        info = {}

        def metadata_from_url(r_url):
            if not info and r_url:
                mobj = re.search(r'_(?:S(\d+))?Ep(\d+)', r_url)
                if mobj:
                    info['episode_number'] = int(mobj.group(2))
                    season_number = mobj.group(1)
                    if season_number:
                        info['season_number'] = int(season_number)

        video_type = video_data.get('video_type')
        is_youtube = False
        for quality in ('', '_sd'):
            embed_code = video_data.get('embed_info' + quality)
            if not embed_code:
                continue
            embed_code = ds(embed_code)
            if video_type in ('video/rcs', 'video/kenc'):
                if video_type == 'video/kenc':
                    kenc = self._download_json(
                        'https://www.vvvvid.it/kenc', video_id, query={
                            'action': 'kt',
                            'conn_id': self._conn_id,
                            'url': embed_code,
                        }, fatal=False) or {}
                    kenc_message = kenc.get('message')
                    if kenc_message:
                        embed_code += '?' + ds(kenc_message)
                formats.extend(self._extract_akamai_formats(embed_code, video_id))
            elif video_type == 'video/youtube':
                info.update({
                    '_type': 'url_transparent',
                    'ie_key': YoutubeIE.ie_key(),
                    'url': embed_code,
                })
                is_youtube = True
                break
            else:
                formats.extend(self._extract_wowza_formats(
                    'http://sb.top-ix.org/videomg/_definst_/mp4:%s/playlist.m3u8' % embed_code, video_id))
            metadata_from_url(embed_code)

        if not is_youtube:
            self._sort_formats(formats)
            info['formats'] = formats

        metadata_from_url(video_data.get('thumbnail'))
        info.update(self._extract_common_video_info(video_data))
        info.update({
            'id': video_id,
            'title': title,
            'duration': int_or_none(video_data.get('length')),
            'series': video_data.get('show_title'),
            'season_id': season_id,
            'episode': title,
            'view_count': int_or_none(video_data.get('views')),
            'like_count': int_or_none(video_data.get('video_likes')),
            'repost_count': int_or_none(video_data.get('video_shares')),
        })
        return info


class VVVVIDShowIE(VVVVIDIE):
    _VALID_URL = r'(?P<base_url>%s(?P<id>\d+)(?:/(?P<show_title>[^/?&#]+))?)/?(?:[?#&]|$)' % VVVVIDIE._VALID_URL_BASE
    _TESTS = [{
        'url': 'https://www.vvvvid.it/show/156/psyco-pass',
        'info_dict': {
            'id': '156',
            'title': 'Psycho-Pass',
            'description': 'md5:94d572c0bd85894b193b8aebc9a3a806',
        },
        'playlist_count': 46,
    }, {
        'url': 'https://www.vvvvid.it/show/156',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        base_url, show_id, show_title = re.match(self._VALID_URL, url).groups()

        seasons = self._download_info(
            show_id, 'seasons/', show_title)

        show_info = self._download_info(
            show_id, 'info/', show_title, fatal=False)

        if not show_title:
            base_url += "/title"

        entries = []
        for season in (seasons or []):
            episodes = season.get('episodes') or []
            playlist_title = season.get('name') or show_info.get('title')
            for episode in episodes:
                if episode.get('playable') is False:
                    continue
                season_id = str_or_none(episode.get('season_id'))
                video_id = str_or_none(episode.get('video_id'))
                if not (season_id and video_id):
                    continue
                info = self._extract_common_video_info(episode)
                info.update({
                    '_type': 'url_transparent',
                    'ie_key': VVVVIDIE.ie_key(),
                    'url': '/'.join([base_url, season_id, video_id]),
                    'title': episode.get('title'),
                    'description': episode.get('description'),
                    'season_id': season_id,
                    'playlist_title': playlist_title,
                })
                entries.append(info)

        return self.playlist_result(
            entries, show_id, show_info.get('title'), show_info.get('description'))
