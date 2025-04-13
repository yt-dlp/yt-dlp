import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UnsupportedError,
    make_archive_id,
    remove_end,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class SenateISVPIE(InfoExtractor):
    IE_NAME = 'senate.gov:isvp'
    _VALID_URL = r'https?://(?:www\.)?senate\.gov/isvp/?\?(?P<qs>.+)'
    _EMBED_REGEX = [r"<iframe[^>]+src=['\"](?P<url>https?://www\.senate\.gov/isvp/?\?[^'\"]+)['\"]"]

    _TESTS = [{
        'url': 'http://www.senate.gov/isvp/?comm=judiciary&type=live&stt=&filename=judiciary031715&auto_play=false&wmode=transparent&poster=http%3A%2F%2Fwww.judiciary.senate.gov%2Fthemes%2Fjudiciary%2Fimages%2Fvideo-poster-flash-fit.png',
        'info_dict': {
            'id': 'judiciary031715',
            'ext': 'mp4',
            'title': 'ISVP',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
            '_old_archive_ids': ['senategov judiciary031715'],
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'http://www.senate.gov/isvp/?type=live&comm=commerce&filename=commerce011514.mp4&auto_play=false',
        'info_dict': {
            'id': 'commerce011514',
            'ext': 'mp4',
            'title': 'Integrated Senate Video Player',
            '_old_archive_ids': ['senategov commerce011514'],
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'This video is not available.',
    }, {
        'url': 'http://www.senate.gov/isvp/?type=arch&comm=intel&filename=intel090613&hc_location=ufi',
        # checksum differs each time
        'info_dict': {
            'id': 'intel090613',
            'ext': 'mp4',
            'title': 'ISVP',
            '_old_archive_ids': ['senategov intel090613'],
        },
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'https://www.senate.gov/isvp/?auto_play=false&comm=help&filename=help090920&poster=https://www.help.senate.gov/assets/images/video-poster.png&stt=950',
        'info_dict': {
            'id': 'help090920',
            'ext': 'mp4',
            'title': 'ISVP',
            'thumbnail': 'https://www.help.senate.gov/assets/images/video-poster.png',
            '_old_archive_ids': ['senategov help090920'],
        },
    }, {
        # From http://www.c-span.org/video/?96791-1
        'url': 'http://www.senate.gov/isvp?type=live&comm=banking&filename=banking012715',
        'only_matching': True,
    }]

    _COMMITTEES = {
        'ag': ('76440', 'https://ag-f.akamaihd.net', '2036803', 'agriculture'),
        'aging': ('76442', 'https://aging-f.akamaihd.net', '2036801', 'aging'),
        'approps': ('76441', 'https://approps-f.akamaihd.net', '2036802', 'appropriations'),
        'arch': ('', 'https://ussenate-f.akamaihd.net', '', 'arch'),
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

    def _real_extract(self, url):
        qs = urllib.parse.parse_qs(self._match_valid_url(url).group('qs'))
        if not qs.get('filename') or not qs.get('comm'):
            raise ExtractorError('Invalid URL', expected=True)
        filename = qs['filename'][0]
        video_id = remove_end(filename, '.mp4')

        webpage = self._download_webpage(url, video_id)
        committee = qs['comm'][0]

        stream_num, stream_domain, stream_id, msl3 = self._COMMITTEES[committee]

        urls_alternatives = [f'https://www-senate-gov-media-srs.akamaized.net/hls/live/{stream_id}/{committee}/{filename}/master.m3u8',
                             f'https://www-senate-gov-msl3archive.akamaized.net/{msl3}/{filename}_1/master.m3u8',
                             f'{stream_domain}/i/{filename}_1@{stream_num}/master.m3u8',
                             f'{stream_domain}/i/{filename}.mp4/master.m3u8']
        formats = []
        subtitles = {}
        for video_url in urls_alternatives:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id, ext='mp4', fatal=False)
            if formats:
                break

        return {
            'id': video_id,
            'title': self._html_extract_title(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': traverse_obj(qs, ('poster', 0, {url_or_none})),
            '_old_archive_ids': [make_archive_id(SenateGovIE, video_id)],
        }


class SenateGovIE(InfoExtractor):
    IE_NAME = 'senate.gov'
    _SUBDOMAIN_RE = '|'.join(map(re.escape, (
        'agriculture', 'aging', 'appropriations', 'armed-services', 'banking',
        'budget', 'commerce', 'energy', 'epw', 'finance', 'foreign', 'help',
        'intelligence', 'inaugural', 'judiciary', 'rules', 'sbc', 'veterans',
    )))
    _VALID_URL = rf'https?://(?:www\.)?(?:{_SUBDOMAIN_RE})\.senate\.gov'
    _TESTS = [{
        'url': 'https://www.help.senate.gov/hearings/vaccines-saving-lives-ensuring-confidence-and-protecting-public-health',
        'info_dict': {
            'id': 'help090920',
            'display_id': 'vaccines-saving-lives-ensuring-confidence-and-protecting-public-health',
            'title': 'Vaccines: Saving Lives, Ensuring Confidence, and Protecting Public Health',
            'description': 'The U.S. Senate Committee on Health, Education, Labor & Pensions',
            'ext': 'mp4',
            'age_limit': 0,
            'thumbnail': 'https://www.help.senate.gov/assets/images/sharelogo.jpg',
            '_old_archive_ids': ['senategov help090920'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.appropriations.senate.gov/hearings/watch?hearingid=B8A25434-5056-A066-6020-1F68CB75F0CD',
        'info_dict': {
            'id': 'appropsA051518',
            'display_id': 'watch?hearingid=B8A25434-5056-A066-6020-1F68CB75F0CD',
            'title': 'Review of the FY2019 Budget Request for the U.S. Army',
            'ext': 'mp4',
            'age_limit': 0,
            'thumbnail': 'https://www.appropriations.senate.gov/themes/appropriations/images/video-poster-flash-fit.png',
            '_old_archive_ids': ['senategov appropsA051518'],
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'https://www.banking.senate.gov/hearings/21st-century-communities-public-transportation-infrastructure-investment-and-fast-act-reauthorization',
        'info_dict': {
            'id': 'banking041521',
            'display_id': '21st-century-communities-public-transportation-infrastructure-investment-and-fast-act-reauthorization',
            'title': '21st Century Communities: Public Transportation Infrastructure Investment and FAST Act Reauthorization',
            'description': 'The Official website of The United States Committee on Banking, Housing, and Urban Affairs',
            'ext': 'mp4',
            'thumbnail': 'https://www.banking.senate.gov/themes/banking/images/sharelogo.jpg',
            'age_limit': 0,
            '_old_archive_ids': ['senategov banking041521'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.agriculture.senate.gov/hearings/hemp-production-and-the-2018-farm-bill',
        'only_matching': True,
    }, {
        'url': 'https://www.aging.senate.gov/hearings/the-older-americans-act-the-local-impact-of-the-law-and-the-upcoming-reauthorization',
        'only_matching': True,
    }, {
        'url': 'https://www.budget.senate.gov/hearings/improving-care-lowering-costs-achieving-health-care-efficiency',
        'only_matching': True,
    }, {
        'url': 'https://www.commerce.senate.gov/2024/12/communications-networks-safety-and-security',
        'only_matching': True,
    }, {
        'url': 'https://www.energy.senate.gov/hearings/2024/2/full-committee-hearing-to-examine',
        'only_matching': True,
    }, {
        'url': 'https://www.epw.senate.gov/public/index.cfm/hearings?ID=F63083EA-2C13-498C-B548-341BED68C209',
        'only_matching': True,
    }, {
        'url': 'https://www.foreign.senate.gov/hearings/american-diplomacy-and-global-leadership-review-of-the-fy25-state-department-budget-request',
        'only_matching': True,
    }, {
        'url': 'https://www.intelligence.senate.gov/hearings/foreign-threats-elections-2024-%E2%80%93-roles-and-responsibilities-us-tech-providers',
        'only_matching': True,
    }, {
        'url': 'https://www.inaugural.senate.gov/52nd-inaugural-ceremonies/',
        'only_matching': True,
    }, {
        'url': 'https://www.rules.senate.gov/hearings/02/07/2023/business-meeting',
        'only_matching': True,
    }, {
        'url': 'https://www.sbc.senate.gov/public/index.cfm/hearings?ID=5B13AA6B-8279-45AF-B54B-94156DC7A2AB',
        'only_matching': True,
    }, {
        'url': 'https://www.veterans.senate.gov/2024/5/frontier-health-care-ensuring-veterans-access-no-matter-where-they-live',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._generic_id(url)
        webpage = self._download_webpage(url, display_id)
        url_info = next(SenateISVPIE.extract_from_webpage(self._downloader, url, webpage), None)
        if not url_info:
            raise UnsupportedError(url)

        title = self._html_search_regex(
            (*self._og_regexes('title'), r'(?s)<title>([^<]*?)</title>'), webpage, 'video title', fatal=False)

        return {
            **url_info,
            '_type': 'url_transparent',
            'display_id': display_id,
            'title': re.sub(r'\s+', ' ', title.split('|')[0]).strip(),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'age_limit': self._rta_search(webpage),
        }
