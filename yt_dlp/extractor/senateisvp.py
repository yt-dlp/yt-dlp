# coding: utf-8
from __future__ import unicode_literals

import re
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    unsmuggle_url,
)
from ..compat import (
    compat_parse_qs,
    compat_urlparse,
)


class SenateISVPIE(InfoExtractor):
    _COMM_MAP = [
        ['ag', '76440', 'http://ag-f.akamaihd.net'],
        ['aging', '76442', 'http://aging-f.akamaihd.net'],
        ['approps', '76441', 'http://approps-f.akamaihd.net'],
        ['armed', '76445', 'http://armed-f.akamaihd.net'],
        ['banking', '76446', 'http://banking-f.akamaihd.net'],
        ['budget', '76447', 'http://budget-f.akamaihd.net'],
        ['cecc', '76486', 'http://srs-f.akamaihd.net'],
        ['commerce', '80177', 'http://commerce1-f.akamaihd.net'],
        ['csce', '75229', 'http://srs-f.akamaihd.net'],
        ['dpc', '76590', 'http://dpc-f.akamaihd.net'],
        ['energy', '76448', 'http://energy-f.akamaihd.net'],
        ['epw', '76478', 'http://epw-f.akamaihd.net'],
        ['ethics', '76449', 'http://ethics-f.akamaihd.net'],
        ['finance', '76450', 'http://finance-f.akamaihd.net'],
        ['foreign', '76451', 'http://foreign-f.akamaihd.net'],
        ['govtaff', '76453', 'http://govtaff-f.akamaihd.net'],
        ['help', '76452', 'http://help-f.akamaihd.net'],
        ['indian', '76455', 'http://indian-f.akamaihd.net'],
        ['intel', '76456', 'http://intel-f.akamaihd.net'],
        ['intlnarc', '76457', 'http://intlnarc-f.akamaihd.net'],
        ['jccic', '85180', 'http://jccic-f.akamaihd.net'],
        ['jec', '76458', 'http://jec-f.akamaihd.net'],
        ['judiciary', '76459', 'http://judiciary-f.akamaihd.net'],
        ['rpc', '76591', 'http://rpc-f.akamaihd.net'],
        ['rules', '76460', 'http://rules-f.akamaihd.net'],
        ['saa', '76489', 'http://srs-f.akamaihd.net'],
        ['smbiz', '76461', 'http://smbiz-f.akamaihd.net'],
        ['srs', '75229', 'http://srs-f.akamaihd.net'],
        ['uscc', '76487', 'http://srs-f.akamaihd.net'],
        ['vetaff', '76462', 'http://vetaff-f.akamaihd.net'],
        ['arch', '', 'http://ussenate-f.akamaihd.net/']
    ]
    _IE_NAME = 'senate.gov'
    _VALID_URL = r'https?://(?:www\.)?senate\.gov/isvp/?\?(?P<qs>.+)'
    _TESTS = [{
        'url': 'http://www.senate.gov/isvp/?comm=judiciary&type=live&stt=&filename=judiciary031715&auto_play=false&wmode=transparent&poster=http%3A%2F%2Fwww.judiciary.senate.gov%2Fthemes%2Fjudiciary%2Fimages%2Fvideo-poster-flash-fit.png',
        'info_dict': {
            'id': 'judiciary031715',
            'ext': 'mp4',
            'title': 'Integrated Senate Video Player',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.senate.gov/isvp/?type=live&comm=commerce&filename=commerce011514.mp4&auto_play=false',
        'info_dict': {
            'id': 'commerce011514',
            'ext': 'mp4',
            'title': 'Integrated Senate Video Player'
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.senate.gov/isvp/?type=arch&comm=intel&filename=intel090613&hc_location=ufi',
        # checksum differs each time
        'info_dict': {
            'id': 'intel090613',
            'ext': 'mp4',
            'title': 'Integrated Senate Video Player'
        }
    }, {
        # From http://www.c-span.org/video/?96791-1
        'url': 'http://www.senate.gov/isvp?type=live&comm=banking&filename=banking012715',
        'only_matching': True,
    }]

    @staticmethod
    def _search_iframe_url(webpage):
        mobj = re.search(
            r"<iframe[^>]+src=['\"](?P<url>https?://www\.senate\.gov/isvp/?\?[^'\"]+)['\"]",
            webpage)
        if mobj:
            return mobj.group('url')

    def _get_info_for_comm(self, committee):
        for entry in self._COMM_MAP:
            if entry[0] == committee:
                return entry[1:]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        qs = compat_parse_qs(re.match(self._VALID_URL, url).group('qs'))
        if not qs.get('filename') or not qs.get('type') or not qs.get('comm'):
            raise ExtractorError('Invalid URL', expected=True)

        video_id = re.sub(r'.mp4$', '', qs['filename'][0])

        webpage = self._download_webpage(url, video_id)

        if smuggled_data.get('force_title'):
            title = smuggled_data['force_title']
        else:
            title = self._html_search_regex(r'<title>([^<]+)</title>', webpage, video_id)
        poster = qs.get('poster')
        thumbnail = poster[0] if poster else None

        video_type = qs['type'][0]
        committee = video_type if video_type == 'arch' else qs['comm'][0]
        stream_num, domain = self._get_info_for_comm(committee)

        formats = []
        if video_type == 'arch':
            filename = video_id if '.' in video_id else video_id + '.mp4'
            formats = [{
                # All parameters in the query string are necessary to prevent a 403 error
                'url': compat_urlparse.urljoin(domain, filename) + '?v=3.1.0&fp=&r=&g=',
            }]
        else:
            hdcore_sign = 'hdcore=3.1.0'
            url_params = (domain, video_id, stream_num)
            f4m_url = '%s/z/%s_1@%s/manifest.f4m?' % url_params + hdcore_sign
            m3u8_url = '%s/i/%s_1@%s/master.m3u8' % url_params
            for entry in self._extract_f4m_formats(f4m_url, video_id, f4m_id='f4m'):
                # URLs without the extra param induce an 404 error
                entry.update({'extra_param_to_segment_url': hdcore_sign})
                formats.append(entry)
            for entry in self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4', m3u8_id='m3u8'):
                mobj = re.search(r'(?P<tag>(?:-p|-b)).m3u8', entry['url'])
                if mobj:
                    entry['format_id'] += mobj.group('tag')
                formats.append(entry)

            self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
        }
