# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import base_url, ExtractorError, urljoin

from random import randint
import re


class MuchoHentaiIE(InfoExtractor):
    REFERER_HEADER = {'Referer': 'https://muchohentai.com/'}

    _VALID_URL = r'https?://(?:www\.)?muchohentai\.com/(?P<other>\w+)/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://muchohentai.com/aBo4Rk/134179/',
        'md5': 'f1b163da6e0c3abf200ecd475a54d116',
        'info_dict': {
            'id': '134179',
            'ext': 'mp4',
            'title': 'Nanatsu no Bitoku Uncensored Opening',
            'description': 're:Watch Nanatsu no Bitoku Uncensored Opening.*',
            'duration': 32,
            'thumbnail': 're:^https?://.*.tmncdn.io/wp-content/uploads/Nanatsu_no_Bitoku/thumbs.vtt'
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
        description = self._html_search_meta('description', webpage, default=None)
        is_deleted = re.search(pattern='https://downloads.muchohentai.com/wp-content/uploads/.*Banned/[^"]*',
                               string=webpage)
        if is_deleted is not None:
            # Note: MuchoHentai does not delete the page but only the video. Clicking on the video that is deleted
            #       just redirects to an adult live show for ad money.
            #       The whole site is actually a click-to-open-the-next-ad minefield.
            self.to_screen('NOTE: This Download may have been deleted. Found link {0}'.format(is_deleted.group()))
        m = re.search(
            pattern=r'var servers=\[(?P<servers>.*)\].*var server="(?P<server>[^;]+).*"file":"(?P<file>['
                    r'^"]+).*file:"(?P<thumbs>[^"]+)\",kind:\'thumbnails\'}',
            string=webpage, flags=re.MULTILINE)
        if m is None:
            raise ExtractorError('Could not extract inline js from webpage.')
        md = m.groupdict()
        required_keys = ["servers", "server", "file", "thumbs"]
        for key in required_keys:
            if key not in md:
                raise ExtractorError('Could not extract required value {0}'.format(key))
        server_names = [x.strip("'") for x in md.get('servers').split(',')]
        server_urls = [re.sub('".*?"', server, md.get("server").rstrip('"')) for server in server_names]
        server_url = server_urls[randint(0, len(server_urls) - 1)]
        m3u8_path = md.get('file').replace('\\', '')
        vtt_path = md.get('thumbs').replace('\\', '')
        m3u8_url = urljoin(server_url, m3u8_path)
        vtt_url = urljoin(server_url, vtt_path)
        fragment_base_url = base_url(m3u8_url)
        m3u8_formats = self._extract_m3u8_formats(m3u8_url, video_id, headers=self.REFERER_HEADER)
        if len(m3u8_formats) == 0:
            raise ExtractorError('Not Implemented! - Playlist has size 0.')
        else:
            # More then one format to be merged. Formats are compliated.
            for m3u8_format in m3u8_formats:
                m3u8_format.update({'http_headers': self.REFERER_HEADER})  # mandatory
                if m3u8_format.get('fragment_base_url') is None:
                    # only if not found by _extract_m3u8_formats
                    m3u8_format.update({'fragment_base_url': fragment_base_url})

                if m3u8_format.get('ext') is None:
                    ext_from_parent_m3u = None
                    # Check if the format can be found in parent M3U file
                    possible_length_for_two_exts = (len('.m3u8') + len('.mp4') + 2)
                    if m3u8_url[-possible_length_for_two_exts:].count('.') == 2:
                        ext_from_parent_m3u = m3u8_url[-possible_length_for_two_exts:].split('.')[-2]

                    # Check if the format can be found by format_id
                    ext_from_format_id = None
                    format_id = m3u8_format.get('format_id')
                    if format_id is not None \
                            and not format_id.isnumeric() \
                            and m3u8_format.get('vcodec') in [None, 'none']:
                        # it can only be an audio format
                        if format_id.startswith('audio_aac'):
                            ext_from_format_id = 'aac'
                        else:
                            ext_from_format_id = 'unknown_audio'
                    ext = ext_from_parent_m3u or ext_from_format_id
                    m3u8_format.update({'ext': ext})

        duration = self._extract_m3u8_vod_duration(m3u8_url, video_id, headers=self.REFERER_HEADER)

        return {'id': video_id,
                'title': title,
                'description': description,
                'formats': m3u8_formats,
                'duration': duration,
                'thumbnail': vtt_url}
