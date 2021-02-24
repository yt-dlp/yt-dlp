# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    orderedSet,
    parse_duration,
    try_get,
)


class MarkizaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?videoarchiv\.markiza\.sk/(?:video/(?:[^/]+/)*|embed/)(?P<id>\d+)(?:[_/]|$)'
    _TESTS = [{
        'url': 'http://videoarchiv.markiza.sk/video/oteckovia/84723_oteckovia-109',
        'md5': 'ada4e9fad038abeed971843aa028c7b0',
        'info_dict': {
            'id': '139078',
            'ext': 'mp4',
            'title': 'Oteckovia 109',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2760,
        },
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/televizne-noviny/televizne-noviny/85430_televizne-noviny',
        'info_dict': {
            'id': '85430',
            'title': 'Televízne noviny',
        },
        'playlist_count': 23,
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/oteckovia/84723',
        'only_matching': True,
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/84723',
        'only_matching': True,
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/filmy/85190_kamenak',
        'only_matching': True,
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/reflex/zo-zakulisia/84651_pribeh-alzbetky',
        'only_matching': True,
    }, {
        'url': 'http://videoarchiv.markiza.sk/embed/85295',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(
            'http://videoarchiv.markiza.sk/json/video_jwplayer7.json',
            video_id, query={'id': video_id})

        info = self._parse_jwplayer_data(data, m3u8_id='hls', mpd_id='dash')

        if info.get('_type') == 'playlist':
            info.update({
                'id': video_id,
                'title': try_get(
                    data, lambda x: x['details']['name'], compat_str),
            })
        else:
            info['duration'] = parse_duration(
                try_get(data, lambda x: x['details']['duration'], compat_str))
        return info


class MarkizaPageIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:(?:[^/]+\.)?markiza|tvnoviny)\.sk/(?:[^/]+/)*(?P<id>\d+)_'
    _TESTS = [{
        'url': 'http://www.markiza.sk/soubiz/zahranicny/1923705_oteckovia-maju-svoj-den-ti-slavni-nie-su-o-nic-menej-rozkosni',
        'md5': 'ada4e9fad038abeed971843aa028c7b0',
        'info_dict': {
            'id': '139355',
            'ext': 'mp4',
            'title': 'Oteckovia 110',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2604,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://dajto.markiza.sk/filmy-a-serialy/1774695_frajeri-vo-vegas',
        'only_matching': True,
    }, {
        'url': 'http://superstar.markiza.sk/aktualne/1923870_to-je-ale-telo-spevacka-ukazala-sexy-postavicku-v-bikinach',
        'only_matching': True,
    }, {
        'url': 'http://hybsa.markiza.sk/aktualne/1923790_uzasna-atmosfera-na-hybsa-v-poprade-superstaristi-si-prve-koncerty-pred-davom-ludi-poriadne-uzili',
        'only_matching': True,
    }, {
        'url': 'http://doma.markiza.sk/filmy/1885250_moja-vysnivana-svadba',
        'only_matching': True,
    }, {
        'url': 'http://www.tvnoviny.sk/domace/1923887_po-smrti-manzela-ju-cakalo-poriadne-prekvapenie',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if MarkizaIE.suitable(url) else super(MarkizaPageIE, cls).suitable(url)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(
            # Downloading for some hosts (e.g. dajto, doma) fails with 500
            # although everything seems to be OK, so considering 500
            # status code to be expected.
            url, playlist_id, expected_status=500)

        entries = [
            self.url_result('http://videoarchiv.markiza.sk/video/%s' % video_id)
            for video_id in orderedSet(re.findall(
                r'(?:initPlayer_|data-entity=["\']|id=["\']player_)(\d+)',
                webpage))]

        return self.playlist_result(entries, playlist_id)
