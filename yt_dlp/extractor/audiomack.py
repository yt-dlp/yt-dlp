# coding: utf-8
from __future__ import unicode_literals

import itertools
import time

from .common import InfoExtractor
from .soundcloud import SoundcloudIE
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    url_basename,
)


class AudiomackIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?audiomack\.com/(?:song/|(?=.+/song/))(?P<id>[\w/-]+)'
    IE_NAME = 'audiomack'
    _TESTS = [
        # hosted on audiomack
        {
            'url': 'http://www.audiomack.com/song/roosh-williams/extraordinary',
            'info_dict':
            {
                'id': '310086',
                'ext': 'mp3',
                'uploader': 'Roosh Williams',
                'title': 'Extraordinary'
            }
        },
        # audiomack wrapper around soundcloud song
        # Needs new test URL.
        {
            'add_ie': ['Soundcloud'],
            'url': 'http://www.audiomack.com/song/hip-hop-daily/black-mamba-freestyle',
            'only_matching': True,
            # 'info_dict': {
                # 'id': '258901379',
                # 'ext': 'mp3',
                # 'description': 'mamba day freestyle for the legend Kobe Bryant ',
                # 'title': 'Black Mamba Freestyle [Prod. By Danny Wolf]',
                # 'uploader': 'ILOVEMAKONNEN',
                # 'upload_date': '20160414',
            # }
        },
    ]

    def _real_extract(self, url):
        # URLs end with [uploader name]/song/[uploader title]
        # this title is whatever the user types in, and is rarely
        # the proper song title.  Real metadata is in the api response
        album_url_tag = self._match_id(url).replace('/song/', '/')

        # Request the extended version of the api for extra fields like artist and title
        api_response = self._download_json(
            'http://www.audiomack.com/api/music/url/song/%s?extended=1&_=%d' % (
                album_url_tag, time.time()),
            album_url_tag)

        # API is inconsistent with errors
        if 'url' not in api_response or not api_response['url'] or 'error' in api_response:
            raise ExtractorError('Invalid url %s' % url)

        # Audiomack wraps a lot of soundcloud tracks in their branded wrapper
        # if so, pass the work off to the soundcloud extractor
        if SoundcloudIE.suitable(api_response['url']):
            return self.url_result(api_response['url'], SoundcloudIE.ie_key())

        return {
            'id': compat_str(api_response.get('id', album_url_tag)),
            'uploader': api_response.get('artist'),
            'title': api_response.get('title'),
            'url': api_response['url'],
        }


class AudiomackAlbumIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?audiomack\.com/(?:album/|(?=.+/album/))(?P<id>[\w/-]+)'
    IE_NAME = 'audiomack:album'
    _TESTS = [
        # Standard album playlist
        {
            'url': 'http://www.audiomack.com/album/flytunezcom/tha-tour-part-2-mixtape',
            'playlist_count': 11,
            'info_dict':
            {
                'id': '812251',
                'title': 'Tha Tour: Part 2 (Official Mixtape)'
            }
        },
        # Album playlist ripped from fakeshoredrive with no metadata
        {
            'url': 'http://www.audiomack.com/album/fakeshoredrive/ppp-pistol-p-project',
            'info_dict': {
                'title': 'PPP (Pistol P Project)',
                'id': '837572',
            },
            'playlist': [{
                'info_dict': {
                    'title': 'PPP (Pistol P Project) - 10. 4 Minutes Of Hell Part 4 (prod by DY OF 808 MAFIA)',
                    'id': '837580',
                    'ext': 'mp3',
                    'uploader': 'Lil Herb a.k.a. G Herbo',
                }
            }],
            'params': {
                'playliststart': 2,
                'playlistend': 2,
            }
        }
    ]

    def _real_extract(self, url):
        # URLs end with [uploader name]/album/[uploader title]
        # this title is whatever the user types in, and is rarely
        # the proper song title.  Real metadata is in the api response
        album_url_tag = self._match_id(url).replace('/album/', '/')
        result = {'_type': 'playlist', 'entries': []}
        # There is no one endpoint for album metadata - instead it is included/repeated in each song's metadata
        # Therefore we don't know how many songs the album has and must infi-loop until failure
        for track_no in itertools.count():
            # Get song's metadata
            api_response = self._download_json(
                'http://www.audiomack.com/api/music/url/album/%s/%d?extended=1&_=%d'
                % (album_url_tag, track_no, time.time()), album_url_tag,
                note='Querying song information (%d)' % (track_no + 1))

            # Total failure, only occurs when url is totally wrong
            # Won't happen in middle of valid playlist (next case)
            if 'url' not in api_response or 'error' in api_response:
                raise ExtractorError('Invalid url for track %d of album url %s' % (track_no, url))
            # URL is good but song id doesn't exist - usually means end of playlist
            elif not api_response['url']:
                break
            else:
                # Pull out the album metadata and add to result (if it exists)
                for resultkey, apikey in [('id', 'album_id'), ('title', 'album_title')]:
                    if apikey in api_response and resultkey not in result:
                        result[resultkey] = compat_str(api_response[apikey])
                song_id = url_basename(api_response['url']).rpartition('.')[0]
                result['entries'].append({
                    'id': compat_str(api_response.get('id', song_id)),
                    'uploader': api_response.get('artist'),
                    'title': api_response.get('title', song_id),
                    'url': api_response['url'],
                })
        return result
