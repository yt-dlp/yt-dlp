# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str


class VyboryMosIE(InfoExtractor):
    _VALID_URL = r'https?://vybory\.mos\.ru/(?:#precinct/|account/channels\?.*?\bstation_id=)(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://vybory.mos.ru/#precinct/13636',
        'info_dict': {
            'id': '13636',
            'ext': 'mp4',
            'title': 're:^Участковая избирательная комиссия №2231 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'description': 'Россия, Москва, улица Введенского, 32А',
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'http://vybory.mos.ru/account/channels?station_id=13636',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        station_id = self._match_id(url)

        channels = self._download_json(
            'http://vybory.mos.ru/account/channels?station_id=%s' % station_id,
            station_id, 'Downloading channels JSON')

        formats = []
        for cam_num, (sid, hosts, name, _) in enumerate(channels, 1):
            for num, host in enumerate(hosts, 1):
                formats.append({
                    'url': 'http://%s/master.m3u8?sid=%s' % (host, sid),
                    'ext': 'mp4',
                    'format_id': 'camera%d-host%d' % (cam_num, num),
                    'format_note': '%s, %s' % (name, host),
                })

        info = self._download_json(
            'http://vybory.mos.ru/json/voting_stations/%s/%s.json'
            % (compat_str(station_id)[:3], station_id),
            station_id, 'Downloading station JSON', fatal=False) or {}

        return {
            'id': station_id,
            'title': info.get('name') or station_id,
            'description': info.get('address'),
            'is_live': True,
            'formats': formats,
        }
