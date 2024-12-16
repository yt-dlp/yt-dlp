import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_qs,
    unsmuggle_url,
)

_COMMITTEES = {
    'ag': ('76440', 'https://ag-f.akamaihd.net', '2036803', 'agriculture'),
    'aging': ('76442', 'https://aging-f.akamaihd.net', '2036801', 'aging'),
    'approps': ('76441', 'https://approps-f.akamaihd.net', '2036802', 'appropriations'),
    'arch': ('', 'https://ussenate-f.akamaihd.net/', '', 'arch'),
    'armed': ('76445', 'https://armed-f.akamaihd.net', '2036800', 'armedservices'),
    'banking': ('76446', 'https://banking-f.akamaihd.net', '2036799', 'banking'),
    'budget': ('76447', 'https://budget-f.akamaihd.net', '2036798', 'budget'),
    'cecc': ('76486', 'https://srs-f.akamaihd.net', '2036782', 'srs_cecc'),
    'commerce': ('80177', 'https://commerce1-f.akamaihd.net', '2036779', 'commerce'),
    'csce': ('75229', 'https://srs-f.akamaihd.net', '2036777', 'srs_srs'),
    'dpc': ('76590', 'https://dpc-f.akamaihd.net', '', 'dpc'),
    'energy': ('76448', 'https://energy-f.akamaihd.net', '2036797', 'energy'),
    'epw': ('76478', 'https://epw-f.akamaihd.net', '2036783', 'environment'),
    'ethics': ('76449', 'https://ethics-f.akamaihd.net', '2036796', 'ethics'),
    'finance': ('76450', 'https://finance-f.akamaihd.net', '2036795', 'finance_finance'),
    'foreign': ('76451', 'https://foreign-f.akamaihd.net', '2036794', 'foreignrelations'),
    'govtaff': ('76453', 'https://govtaff-f.akamaihd.net', '2036792', 'hsgac'),
    'help': ('76452', 'https://help-f.akamaihd.net', '2036793', 'help'),
    'indian': ('76455', 'https://indian-f.akamaihd.net', '2036791', 'indianaffairs'),
    'intel': ('76456', 'https://intel-f.akamaihd.net', '2036790', 'intelligence'),
    'intlnarc': ('76457', 'https://intlnarc-f.akamaihd.net', '', 'internationalnarcoticscaucus'),
    'jccic': ('85180', 'https://jccic-f.akamaihd.net', '2036778', 'jccic'),
    'jec': ('76458', 'https://jec-f.akamaihd.net', '2036789', 'jointeconomic'),
    'judiciary': ('76459', 'https://judiciary-f.akamaihd.net', '2036788', 'judiciary'),
    'rpc': ('76591', 'https://rpc-f.akamaihd.net', '', 'rpc'),
    'rules': ('76460', 'https://rules-f.akamaihd.net', '2036787', 'rules'),
    'saa': ('76489', 'https://srs-f.akamaihd.net', '2036780', 'srs_saa'),
    'smbiz': ('76461', 'https://smbiz-f.akamaihd.net', '2036786', 'smallbusiness'),
    'srs': ('75229', 'https://srs-f.akamaihd.net', '2031966', 'srs_srs'),
    'uscc': ('76487', 'https://srs-f.akamaihd.net', '2036781', 'srs_uscc'),
    'vetaff': ('76462', 'https://vetaff-f.akamaihd.net', '2036785', 'veteransaffairs'),
}


class SenateISVPIE(InfoExtractor):
    _IE_NAME = 'senate.gov:isvp'
    _VALID_URL = r'https?://(?:www\.)?senate\.gov/isvp/?\?(?P<qs>.+)'
    _EMBED_REGEX = [r"<iframe[^>]+src=['\"](?P<url>https?://www\.senate\.gov/isvp/?\?[^'\"]+)['\"]"]

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
            'title': 'Integrated Senate Video Player',
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
            'title': 'Integrated Senate Video Player',
        },
    }, {
        # From http://www.c-span.org/video/?96791-1
        'url': 'http://www.senate.gov/isvp?type=live&comm=banking&filename=banking012715',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        qs = urllib.parse.parse_qs(self._match_valid_url(url).group('qs'))
        if not qs.get('filename') or not qs.get('type') or not qs.get('comm'):
            raise ExtractorError('Invalid URL', expected=True)

        video_id = re.sub(r'.mp4$', '', qs['filename'][0])

        webpage = self._download_webpage(url, video_id)

        if smuggled_data.get('force_title'):
            title = smuggled_data['force_title']
        else:
            title = self._html_extract_title(webpage)
        poster = qs.get('poster')
        thumbnail = poster[0] if poster else None

        video_type = qs['type'][0]
        committee = video_type if video_type == 'arch' else qs['comm'][0]

        stream_num, domain = _COMMITTEES[committee]

        formats = []
        if video_type == 'arch':
            filename = video_id if '.' in video_id else video_id + '.mp4'
            m3u8_url = urllib.parse.urljoin(domain, 'i/' + filename + '/master.m3u8')
            formats = self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4', m3u8_id='m3u8')
        else:
            hdcore_sign = 'hdcore=3.1.0'
            url_params = (domain, video_id, stream_num)
            f4m_url = f'%s/z/%s_1@%s/manifest.f4m?{hdcore_sign}' % url_params
            m3u8_url = '{}/i/{}_1@{}/master.m3u8'.format(*url_params)
            for entry in self._extract_f4m_formats(f4m_url, video_id, f4m_id='f4m'):
                # URLs without the extra param induce an 404 error
                entry.update({'extra_param_to_segment_url': hdcore_sign})
                formats.append(entry)
            for entry in self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4', m3u8_id='m3u8'):
                mobj = re.search(r'(?P<tag>(?:-p|-b)).m3u8', entry['url'])
                if mobj:
                    entry['format_id'] += mobj.group('tag')
                formats.append(entry)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
        }


class SenateGovIE(InfoExtractor):
    _IE_NAME = 'senate.gov'
    _VALID_URL = r'https?:\/\/(?:www\.)?(help|appropriations|judiciary|banking|armed-services|finance)\.senate\.gov'
    _TESTS = [{
        'url': 'https://www.help.senate.gov/hearings/vaccines-saving-lives-ensuring-confidence-and-protecting-public-health',
        'info_dict': {
            'id': 'help090920',
            'display_id': 'vaccines-saving-lives-ensuring-confidence-and-protecting-public-health',
            'title': 'Vaccines: Saving Lives, Ensuring Confidence, and Protecting Public Health',
            'description': 'The U.S. Senate Committee on Health, Education, Labor & Pensions',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.appropriations.senate.gov/hearings/watch?hearingid=B8A25434-5056-A066-6020-1F68CB75F0CD',
        'info_dict': {
            'id': 'appropsA051518',
            'display_id': 'watch?hearingid=B8A25434-5056-A066-6020-1F68CB75F0CD',
            'title': 'Review of the FY2019 Budget Request for the U.S. Army',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.banking.senate.gov/hearings/21st-century-communities-public-transportation-infrastructure-investment-and-fast-act-reauthorization',
        'info_dict': {
            'id': 'banking041521',
            'display_id': '21st-century-communities-public-transportation-infrastructure-investment-and-fast-act-reauthorization',
            'title': '21st Century Communities: Public Transportation Infrastructure Investment and FAST Act Reauthorization',
            'description': 'The Official website of The United States Committee on Banking, Housing, and Urban Affairs',
            'ext': 'mp4',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        display_id = self._generic_id(url)
        webpage = self._download_webpage(url, display_id)
        iframe_src = self._search_regex(
            (r'<iframe class="[^>"]*streaminghearing[^>"]*"\s[^>]*\bsrc="([^">]*)',
             r'<iframe title="[^>"]*[^>"]*"\s[^>]*\bsrc="([^">]*)'),
            webpage, 'hearing URL').replace('&amp;', '&')
        parse_info = parse_qs(iframe_src)
        comm = parse_info['comm'][-1]
        stream_num, stream_domain, stream_id, msl3 = _COMMITTEES[comm]
        filename = parse_info['filename'][-1]

        urls_alternatives = [f'https://www-senate-gov-media-srs.akamaized.net/hls/live/{stream_id}/{comm}/{filename}/master.m3u8',
                             f'https://www-senate-gov-msl3archive.akamaized.net/{msl3}/{filename}_1/master.m3u8',
                             f'{stream_domain}/i/{filename}_1@{stream_num}/master.m3u8',
                             f'{stream_domain}/i/{filename}.mp4/master.m3u8']
        for video_url in urls_alternatives:
            formats = self._extract_m3u8_formats(video_url, display_id, ext='mp4', fatal=False)
            if formats:
                break

        title = self._html_search_regex(
            (*self._og_regexes('title'), r'(?s)<title>([^<]*?)</title>'), webpage, 'video title')

        return {
            'id': re.sub(r'.mp4$', '', filename),
            'display_id': display_id,
            'title': re.sub(r'\s+', ' ', title.split('|')[0]).strip(),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'age_limit': self._rta_search(webpage),
            'formats': formats,
        }
