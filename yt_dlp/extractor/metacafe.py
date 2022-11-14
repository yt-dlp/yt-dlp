import json
import re
import urllib.parse

from .common import InfoExtractor
from ..compat import compat_parse_qs, compat_urllib_parse_unquote
from ..utils import (
    ExtractorError,
    determine_ext,
    get_element_by_attribute,
    int_or_none,
    mimetype2ext,
)


class MetacafeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?metacafe\.com/watch/(?P<id>[^/]+)/(?P<display_id>[^/?#]+)'
    _DISCLAIMER = 'http://www.metacafe.com/family_filter/'
    _FILTER_POST = 'http://www.metacafe.com/f/index.php?inputType=filter&controllerGroup=user'
    IE_NAME = 'metacafe'
    _TESTS = [
        # Youtube video
        {
            'add_ie': ['Youtube'],
            'url': 'http://metacafe.com/watch/yt-_aUehQsCQtM/the_electric_company_short_i_pbs_kids_go/',
            'info_dict': {
                'id': '_aUehQsCQtM',
                'ext': 'mp4',
                'upload_date': '20090102',
                'title': 'The Electric Company | "Short I" | PBS KIDS GO!',
                'description': 'md5:2439a8ef6d5a70e380c22f5ad323e5a8',
                'uploader': 'PBS',
                'uploader_id': 'PBS'
            }
        },
        # Normal metacafe video
        {
            'url': 'http://www.metacafe.com/watch/11121940/news_stuff_you_wont_do_with_your_playstation_4/',
            'md5': '6e0bca200eaad2552e6915ed6fd4d9ad',
            'info_dict': {
                'id': '11121940',
                'ext': 'mp4',
                'title': 'News: Stuff You Won\'t Do with Your PlayStation 4',
                'uploader': 'ign',
                'description': 'Sony released a massive FAQ on the PlayStation Blog detailing the PS4\'s capabilities and limitations.',
            },
            'skip': 'Page is temporarily unavailable.',
        },
        # metacafe video with family filter
        {
            'url': 'http://www.metacafe.com/watch/2155630/adult_art_by_david_hart_156/',
            'md5': 'b06082c5079bbdcde677a6291fbdf376',
            'info_dict': {
                'id': '2155630',
                'ext': 'mp4',
                'title': 'Adult Art By David Hart 156',
                'uploader': '63346',
                'description': 'md5:9afac8fc885252201ad14563694040fc',
            },
            'params': {
                'skip_download': True,
            },
        },
        # AnyClip video
        {
            'url': 'http://www.metacafe.com/watch/an-dVVXnuY7Jh77J/the_andromeda_strain_1971_stop_the_bomb_part_3/',
            'info_dict': {
                'id': 'an-dVVXnuY7Jh77J',
                'ext': 'mp4',
                'title': 'The Andromeda Strain (1971): Stop the Bomb Part 3',
                'uploader': 'AnyClip',
                'description': 'md5:cbef0460d31e3807f6feb4e7a5952e5b',
            },
        },
        # age-restricted video
        {
            'url': 'http://www.metacafe.com/watch/5186653/bbc_internal_christmas_tape_79_uncensored_outtakes_etc/',
            'md5': '98dde7c1a35d02178e8ab7560fe8bd09',
            'info_dict': {
                'id': '5186653',
                'ext': 'mp4',
                'title': 'BBC INTERNAL Christmas Tape \'79 - UNCENSORED Outtakes, Etc.',
                'uploader': 'Dwayne Pipe',
                'description': 'md5:950bf4c581e2c059911fa3ffbe377e4b',
                'age_limit': 18,
            },
        },
        # cbs video
        {
            'url': 'http://www.metacafe.com/watch/cb-8VD4r_Zws8VP/open_this_is_face_the_nation_february_9/',
            'info_dict': {
                'id': '8VD4r_Zws8VP',
                'ext': 'flv',
                'title': 'Open: This is Face the Nation, February 9',
                'description': 'md5:8a9ceec26d1f7ed6eab610834cc1a476',
                'duration': 96,
                'uploader': 'CBSI-NEW',
                'upload_date': '20140209',
                'timestamp': 1391959800,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        # Movieclips.com video
        {
            'url': 'http://www.metacafe.com/watch/mv-Wy7ZU/my_week_with_marilyn_do_you_love_me/',
            'info_dict': {
                'id': 'mv-Wy7ZU',
                'ext': 'mp4',
                'title': 'My Week with Marilyn - Do You Love Me?',
                'description': 'From the movie My Week with Marilyn - Colin (Eddie Redmayne) professes his love to Marilyn (Michelle Williams) and gets her to promise to return to set and finish the movie.',
                'uploader': 'movie_trailers',
                'duration': 176,
            },
            'params': {
                'skip_download': 'requires rtmpdump',
            }
        }
    ]

    def report_disclaimer(self):
        self.to_screen('Retrieving disclaimer')

    def _real_extract(self, url):
        # Extract id and simplified title from URL
        video_id, display_id = self._match_valid_url(url).groups()

        # the video may come from an external site
        m_external = re.match(r'^(\w{2})-(.*)$', video_id)
        if m_external is not None:
            prefix, ext_id = m_external.groups()
            # Check if video comes from YouTube
            if prefix == 'yt':
                return self.url_result('http://www.youtube.com/watch?v=%s' % ext_id, 'Youtube')
            # CBS videos use theplatform.com
            if prefix == 'cb':
                return self.url_result('theplatform:%s' % ext_id, 'ThePlatform')

        headers = {
            # Disable family filter
            'Cookie': 'user=%s; ' % urllib.parse.quote(json.dumps({'ffilter': False}))
        }

        # AnyClip videos require the flashversion cookie so that we get the link
        # to the mp4 file
        if video_id.startswith('an-'):
            headers['Cookie'] += 'flashVersion=0; '

        # Retrieve video webpage to extract further information
        webpage = self._download_webpage(url, video_id, headers=headers)

        error = get_element_by_attribute(
            'class', 'notfound-page-title', webpage)
        if error:
            raise ExtractorError(error, expected=True)

        video_title = self._html_search_meta(
            ['og:title', 'twitter:title'], webpage, 'title', default=None) or self._search_regex(r'<h1>(.*?)</h1>', webpage, 'title')

        # Extract URL, uploader and title from webpage
        self.report_extraction(video_id)
        video_url = None
        mobj = re.search(r'(?m)&(?:media|video)URL=([^&]+)', webpage)
        if mobj is not None:
            mediaURL = compat_urllib_parse_unquote(mobj.group(1))
            video_ext = determine_ext(mediaURL)

            # Extract gdaKey if available
            mobj = re.search(r'(?m)&gdaKey=(.*?)&', webpage)
            if mobj is None:
                video_url = mediaURL
            else:
                gdaKey = mobj.group(1)
                video_url = '%s?__gda__=%s' % (mediaURL, gdaKey)
        if video_url is None:
            mobj = re.search(r'<video src="([^"]+)"', webpage)
            if mobj:
                video_url = mobj.group(1)
                video_ext = 'mp4'
        if video_url is None:
            flashvars = self._search_regex(
                r' name="flashvars" value="(.*?)"', webpage, 'flashvars',
                default=None)
            if flashvars:
                vardict = compat_parse_qs(flashvars)
                if 'mediaData' not in vardict:
                    raise ExtractorError('Unable to extract media URL')
                mobj = re.search(
                    r'"mediaURL":"(?P<mediaURL>http.*?)",(.*?)"key":"(?P<key>.*?)"', vardict['mediaData'][0])
                if mobj is None:
                    raise ExtractorError('Unable to extract media URL')
                mediaURL = mobj.group('mediaURL').replace('\\/', '/')
                video_url = '%s?__gda__=%s' % (mediaURL, mobj.group('key'))
                video_ext = determine_ext(video_url)
        if video_url is None:
            player_url = self._search_regex(
                r"swfobject\.embedSWF\('([^']+)'",
                webpage, 'config URL', default=None)
            if player_url:
                config_url = self._search_regex(
                    r'config=(.+)$', player_url, 'config URL')
                config_doc = self._download_xml(
                    config_url, video_id,
                    note='Downloading video config')
                smil_url = config_doc.find('.//properties').attrib['smil_file']
                smil_doc = self._download_xml(
                    smil_url, video_id,
                    note='Downloading SMIL document')
                base_url = smil_doc.find('./head/meta').attrib['base']
                video_url = []
                for vn in smil_doc.findall('.//video'):
                    br = int(vn.attrib['system-bitrate'])
                    play_path = vn.attrib['src']
                    video_url.append({
                        'format_id': 'smil-%d' % br,
                        'url': base_url,
                        'play_path': play_path,
                        'page_url': url,
                        'player_url': player_url,
                        'ext': play_path.partition(':')[0],
                    })
        if video_url is None:
            flashvars = self._parse_json(self._search_regex(
                r'flashvars\s*=\s*({.*});', webpage, 'flashvars',
                default=None), video_id, fatal=False)
            if flashvars:
                video_url = []
                for source in flashvars.get('sources'):
                    source_url = source.get('src')
                    if not source_url:
                        continue
                    ext = mimetype2ext(source.get('type')) or determine_ext(source_url)
                    if ext == 'm3u8':
                        video_url.extend(self._extract_m3u8_formats(
                            source_url, video_id, 'mp4',
                            'm3u8_native', m3u8_id='hls', fatal=False))
                    else:
                        video_url.append({
                            'url': source_url,
                            'ext': ext,
                        })

        if video_url is None:
            raise ExtractorError('Unsupported video type')

        description = self._html_search_meta(
            ['og:description', 'twitter:description', 'description'],
            webpage, 'title', fatal=False)
        thumbnail = self._html_search_meta(
            ['og:image', 'twitter:image'], webpage, 'title', fatal=False)
        video_uploader = self._html_search_regex(
            r'submitter=(.*?);|googletag\.pubads\(\)\.setTargeting\("(?:channel|submiter)","([^"]+)"\);',
            webpage, 'uploader nickname', fatal=False)
        duration = int_or_none(
            self._html_search_meta('video:duration', webpage, default=None))
        age_limit = (
            18
            if re.search(r'(?:"contentRating":|"rating",)"restricted"', webpage)
            else 0)

        if isinstance(video_url, list):
            formats = video_url
        else:
            formats = [{
                'url': video_url,
                'ext': video_ext,
            }]
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'description': description,
            'uploader': video_uploader,
            'title': video_title,
            'thumbnail': thumbnail,
            'age_limit': age_limit,
            'formats': formats,
            'duration': duration,
        }
