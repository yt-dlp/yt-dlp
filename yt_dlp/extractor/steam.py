from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    ExtractorError,
    get_element_by_class,
    js_to_json,
)


class SteamIE(InfoExtractor):
    _VALID_URL = r"""(?x)
        https?://store\.steampowered\.com/
            (agecheck/)?
            (?P<urltype>video|app)/ #If the page is only for videos or for a game
            (?P<gameID>\d+)/?
            (?P<videoID>\d*)(?P<extra>\??) # For urltype == video we sometimes get the videoID
        |
        https?://(?:www\.)?steamcommunity\.com/sharedfiles/filedetails/\?id=(?P<fileID>[0-9]+)
    """
    _VIDEO_PAGE_TEMPLATE = 'http://store.steampowered.com/video/%s/'
    _AGECHECK_TEMPLATE = 'http://store.steampowered.com/agecheck/video/%s/?snr=1_agecheck_agecheck__age-gate&ageDay=1&ageMonth=January&ageYear=1970'
    _TESTS = [{
        'url': 'http://store.steampowered.com/video/105600/',
        'playlist': [
            {
                'md5': '6a294ee0c4b1f47f5bb76a65e31e3592',
                'info_dict': {
                    'id': '2040428',
                    'ext': 'mp4',
                    'title': 'Terraria 1.3 Trailer',
                    'playlist_index': 1,
                }
            },
            {
                'md5': '911672b20064ca3263fa89650ba5a7aa',
                'info_dict': {
                    'id': '2029566',
                    'ext': 'mp4',
                    'title': 'Terraria 1.2 Trailer',
                    'playlist_index': 2,
                }
            }
        ],
        'info_dict': {
            'id': '105600',
            'title': 'Terraria',
        },
        'params': {
            'playlistend': 2,
        }
    }, {
        'url': 'http://steamcommunity.com/sharedfiles/filedetails/?id=242472205',
        'info_dict': {
            'id': 'X8kpJBlzD2E',
            'ext': 'mp4',
            'upload_date': '20140617',
            'title': 'FRONTIERS - Trapping',
            'description': 'md5:bf6f7f773def614054089e5769c12a6e',
            'uploader': 'AAD Productions',
            'uploader_id': 'AtomicAgeDogGames',
        }
    }]

    def _real_extract(self, url):
        m = re.match(self._VALID_URL, url)
        fileID = m.group('fileID')
        if fileID:
            videourl = url
            playlist_id = fileID
        else:
            gameID = m.group('gameID')
            playlist_id = gameID
            videourl = self._VIDEO_PAGE_TEMPLATE % playlist_id

        self._set_cookie('steampowered.com', 'mature_content', '1')

        webpage = self._download_webpage(videourl, playlist_id)

        if re.search('<h2>Please enter your birth date to continue:</h2>', webpage) is not None:
            videourl = self._AGECHECK_TEMPLATE % playlist_id
            self.report_age_confirmation()
            webpage = self._download_webpage(videourl, playlist_id)

        flash_vars = self._parse_json(self._search_regex(
            r'(?s)rgMovieFlashvars\s*=\s*({.+?});', webpage,
            'flash vars'), playlist_id, js_to_json)

        playlist_title = None
        entries = []
        if fileID:
            playlist_title = get_element_by_class('workshopItemTitle', webpage)
            for movie in flash_vars.values():
                if not movie:
                    continue
                youtube_id = movie.get('YOUTUBE_VIDEO_ID')
                if not youtube_id:
                    continue
                entries.append({
                    '_type': 'url',
                    'url': youtube_id,
                    'ie_key': 'Youtube',
                })
        else:
            playlist_title = get_element_by_class('apphub_AppName', webpage)
            for movie_id, movie in flash_vars.items():
                if not movie:
                    continue
                video_id = self._search_regex(r'movie_(\d+)', movie_id, 'video id', fatal=False)
                title = movie.get('MOVIE_NAME')
                if not title or not video_id:
                    continue
                entry = {
                    'id': video_id,
                    'title': title.replace('+', ' '),
                }
                formats = []
                flv_url = movie.get('FILENAME')
                if flv_url:
                    formats.append({
                        'format_id': 'flv',
                        'url': flv_url,
                    })
                highlight_element = self._search_regex(
                    r'(<div[^>]+id="highlight_movie_%s"[^>]+>)' % video_id,
                    webpage, 'highlight element', fatal=False)
                if highlight_element:
                    highlight_attribs = extract_attributes(highlight_element)
                    if highlight_attribs:
                        entry['thumbnail'] = highlight_attribs.get('data-poster')
                        for quality in ('', '-hd'):
                            for ext in ('webm', 'mp4'):
                                video_url = highlight_attribs.get('data-%s%s-source' % (ext, quality))
                                if video_url:
                                    formats.append({
                                        'format_id': ext + quality,
                                        'url': video_url,
                                    })
                if not formats:
                    continue
                entry['formats'] = formats
                entries.append(entry)
        if not entries:
            raise ExtractorError('Could not find any videos')

        return self.playlist_result(entries, playlist_id, playlist_title)
