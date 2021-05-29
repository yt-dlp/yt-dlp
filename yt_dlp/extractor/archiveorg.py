from __future__ import unicode_literals

import re
import json

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..compat import (
    compat_urllib_parse_unquote,
    compat_urllib_parse_unquote_plus,
    compat_urlparse,
    compat_parse_qs
)
from ..utils import (
    clean_html,
    determine_ext,
    dict_get,
    extract_attributes,
    HEADRequest,
    int_or_none,
    KNOWN_EXTENSIONS,
    merge_dicts,
    mimetype2ext,
    parse_duration,
    str_to_int,
    str_or_none,
    try_get,
    unified_strdate,
    unified_timestamp
)


class ArchiveOrgIE(InfoExtractor):
    IE_NAME = 'archive.org'
    IE_DESC = 'archive.org video and audio'
    _VALID_URL = r'https?://(?:www\.)?archive\.org/(?:details|embed)/(?P<id>[^?#]+)(?:[?].*)?$'
    _TESTS = [{
        'url': 'http://archive.org/details/XD300-23_68HighlightsAResearchCntAugHumanIntellect',
        'md5': '8af1d4cf447933ed3c7f4871162602db',
        'info_dict': {
            'id': 'XD300-23_68HighlightsAResearchCntAugHumanIntellect',
            'ext': 'ogv',
            'title': '1968 Demo - FJCC Conference Presentation Reel #1',
            'description': 'md5:da45c349df039f1cc8075268eb1b5c25',
            'release_date': '19681210',
            'timestamp': 1268695290,
            'upload_date': '20100315',
            'creator': 'SRI International',
            'uploader': 'laura@archive.org',
        },
    }, {
        'url': 'https://archive.org/details/Cops1922',
        'md5': '0869000b4ce265e8ca62738b336b268a',
        'info_dict': {
            'id': 'Cops1922',
            'ext': 'mp4',
            'title': 'Buster Keaton\'s "Cops" (1922)',
            'description': 'md5:43a603fd6c5b4b90d12a96b921212b9c',
            'uploader': 'yorkmba99@hotmail.com',
            'timestamp': 1387699629,
            'upload_date': "20131222",
        },
    }, {
        'url': 'http://archive.org/embed/XD300-23_68HighlightsAResearchCntAugHumanIntellect',
        'only_matching': True,
    }, {
        'url': 'https://archive.org/details/Election_Ads',
        'md5': '284180e857160cf866358700bab668a3',
        'info_dict': {
            'id': 'Election_Ads/Commercial-JFK1960ElectionAdCampaignJingle.mpg',
            'title': 'Commercial-JFK1960ElectionAdCampaignJingle.mpg',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://archive.org/details/Election_Ads/Commercial-Nixon1960ElectionAdToughonDefense.mpg',
        'md5': '7915213ef02559b5501fe630e1a53f59',
        'info_dict': {
            'id': 'Election_Ads/Commercial-Nixon1960ElectionAdToughonDefense.mpg',
            'title': 'Commercial-Nixon1960ElectionAdToughonDefense.mpg',
            'ext': 'mp4',
            'timestamp': 1205588045,
            'uploader': 'mikedavisstripmaster@yahoo.com',
            'description': '1960 Presidential Campaign Election Commercials John F Kennedy, Richard M Nixon',
            'upload_date': '20080315',
        },
    }, {
        'url': 'https://archive.org/details/gd1977-05-08.shure57.stevenson.29303.flac16',
        'md5': '7d07ffb42aba6537c28e053efa4b54c9',
        'info_dict': {
            'id': 'gd1977-05-08.shure57.stevenson.29303.flac16/gd1977-05-08d01t01.flac',
            'title': 'Turning',
            'ext': 'flac',
        },
    }, {
        'url': 'https://archive.org/details/gd1977-05-08.shure57.stevenson.29303.flac16/gd1977-05-08d01t07.flac',
        'md5': 'a07cd8c6ab4ee1560f8a0021717130f3',
        'info_dict': {
            'id': 'gd1977-05-08.shure57.stevenson.29303.flac16/gd1977-05-08d01t07.flac',
            'title': 'Deal',
            'ext': 'flac',
            'timestamp': 1205895624,
            'uploader': 'mvernon54@yahoo.com',
            'description': 'md5:6a31f1996db0aa0fc9da6d6e708a1bb0',
            'upload_date': '20080319',
            'location': 'Barton Hall - Cornell University',
        },
    }, {
        'url': 'https://archive.org/details/lp_the-music-of-russia_various-artists-a-askaryan-alexander-melik',
        'md5': '7cb019baa9b332e82ea7c10403acd180',
        'info_dict': {
            'id': 'lp_the-music-of-russia_various-artists-a-askaryan-alexander-melik/disc1/01.01. Bells Of Rostov.mp3',
            'title': 'Bells Of Rostov',
            'ext': 'mp3',
        },
    }, {
        'url': 'https://archive.org/details/lp_the-music-of-russia_various-artists-a-askaryan-alexander-melik/disc1/02.02.+Song+And+Chorus+In+The+Polovetsian+Camp+From+%22Prince+Igor%22+(Act+2%2C+Scene+1).mp3',
        'md5': '1d0aabe03edca83ca58d9ed3b493a3c3',
        'info_dict': {
            'id': 'lp_the-music-of-russia_various-artists-a-askaryan-alexander-melik/disc1/02.02. Song And Chorus In The Polovetsian Camp From "Prince Igor" (Act 2, Scene 1).mp3',
            'title': 'Song And Chorus In The Polovetsian Camp From "Prince Igor" (Act 2, Scene 1)',
            'ext': 'mp3',
            'timestamp': 1569662587,
            'uploader': 'associate-joygen-odiongan@archive.org',
            'description': 'md5:012b2d668ae753be36896f343d12a236',
            'upload_date': '20190928',
        },
    }]

    @staticmethod
    def _playlist_data(webpage):
        element = re.findall(r'''(?xs)
            <input
            (?:\s+[a-zA-Z0-9:._-]+(?:=[a-zA-Z0-9:._-]*|="[^"]*"|='[^']*'|))*?
            \s+class=['"]?js-play8-playlist['"]?
            (?:\s+[a-zA-Z0-9:._-]+(?:=[a-zA-Z0-9:._-]*|="[^"]*"|='[^']*'|))*?
            \s*/>
        ''', webpage)[0]

        return json.loads(extract_attributes(element)['value'])

    def _real_extract(self, url):
        video_id = compat_urllib_parse_unquote_plus(self._match_id(url))
        identifier, entry_id = (video_id.split('/', 1) + [None])[:2]

        # Archive.org metadata API doesn't clearly demarcate playlist entries
        # or subtitle tracks, so we get them from the embeddable player.
        embed_page = self._download_webpage(
            'https://archive.org/embed/' + identifier, identifier)
        playlist = self._playlist_data(embed_page)

        entries = {}
        for p in playlist:
            # If the user specified a playlist entry in the URL, ignore the
            # rest of the playlist.
            if entry_id and p['orig'] != entry_id:
                continue

            entries[p['orig']] = {
                'formats': [],
                'thumbnails': [],
                'artist': p.get('artist'),
                'track': p.get('title'),
                'subtitles': {}}

            for track in p.get('tracks', []):
                if track['kind'] != 'subtitles':
                    continue

                entries[p['orig']][track['label']] = {
                    'url': 'https://archive.org/' + track['file'].lstrip('/')}

        metadata = self._download_json(
            'http://archive.org/metadata/' + identifier, identifier)
        m = metadata['metadata']
        identifier = m['identifier']

        info = {
            'id': identifier,
            'title': m['title'],
            'description': clean_html(m.get('description')),
            'uploader': dict_get(m, ['uploader', 'adder']),
            'creator': m.get('creator'),
            'license': m.get('licenseurl'),
            'release_date': unified_strdate(m.get('date')),
            'timestamp': unified_timestamp(dict_get(m, ['publicdate', 'addeddate'])),
            'webpage_url': 'https://archive.org/details/' + identifier,
            'location': m.get('venue'),
            'release_year': int_or_none(m.get('year'))}

        for f in metadata['files']:
            if f['name'] in entries:
                entries[f['name']] = merge_dicts(entries[f['name']], {
                    'id': identifier + '/' + f['name'],
                    'title': f.get('title') or f['name'],
                    'display_id': f['name'],
                    'description': clean_html(f.get('description')),
                    'creator': f.get('creator'),
                    'duration': parse_duration(f.get('length')),
                    'track_number': int_or_none(f.get('track')),
                    'album': f.get('album'),
                    'discnumber': int_or_none(f.get('disc')),
                    'release_year': int_or_none(f.get('year'))})
                entry = entries[f['name']]
            elif f.get('original') in entries:
                entry = entries[f['original']]
            else:
                continue

            if f.get('format') == 'Thumbnail':
                entry['thumbnails'].append({
                    'id': f['name'],
                    'url': 'https://archive.org/download/' + identifier + '/' + f['name'],
                    'width': int_or_none(f.get('width')),
                    'height': int_or_none(f.get('width')),
                    'filesize': int_or_none(f.get('size'))})

            extension = (f['name'].rsplit('.', 1) + [None])[1]
            if extension in KNOWN_EXTENSIONS:
                entry['formats'].append({
                    'url': 'https://archive.org/download/' + identifier + '/' + f['name'],
                    'format': f.get('format'),
                    'width': int_or_none(f.get('width')),
                    'height': int_or_none(f.get('height')),
                    'filesize': int_or_none(f.get('size')),
                    'protocol': 'https'})

        # Sort available formats by filesize
        for entry in entries.values():
            entry['formats'] = list(sorted(entry['formats'], key=lambda x: x.get('filesize', -1)))

        if len(entries) == 1:
            # If there's only one item, use it as the main info dict
            only_video = entries[list(entries.keys())[0]]
            if entry_id:
                info = merge_dicts(only_video, info)
            else:
                info = merge_dicts(info, only_video)
        else:
            # Otherwise, we have a playlist.
            info['_type'] = 'playlist'
            info['entries'] = list(entries.values())

        if metadata.get('reviews'):
            info['comments'] = []
            for review in metadata['reviews']:
                info['comments'].append({
                    'id': review.get('review_id'),
                    'author': review.get('reviewer'),
                    'text': str_or_none(review.get('reviewtitle'), '') + '\n\n' + review.get('reviewbody'),
                    'timestamp': unified_timestamp(review.get('createdate')),
                    'parent': 'root'})

        return info


class YoutubeWebArchiveIE(InfoExtractor):
    IE_NAME = 'youtube:web.archive.org'
    IE_DESC = 'web.archive.org saved youtube videos'
    _VALID_URL = r"""(?x)^
                (?:https?://|//)?web\.archive\.org\/
                    (?:web/)?
                    (?:[0-9A-Za-z_*]+/)? # /web and the version index is optional
                (?:https?:\/\/)?
                (?:
                    (?:\w+\.)?youtube\.com\/watch\?v= # Youtube URL
                    |(wayback-fakeurl\.archive\.org\/yt\/) # Or optionally, also support the internal fake url
                )
                (?P<id>[0-9A-Za-z_-]{11})(?(1).+)?(?:\#|&|$)
                """

    _INTERNAL_URL_TEMPLATE = "https://web.archive.org/web/2oe_/http://wayback-fakeurl.archive.org/yt/%s"

    _TESTS = [
        {
            'url': 'https://web.archive.org/web/20150415002341/https://www.youtube.com/watch?v=aYAGB11YrSs',
            'info_dict': {
                'id': 'aYAGB11YrSs',
                'ext': 'webm',
                'title': "Unknown Video"
            }
        },
        {
            # Internal link
            'url': 'https://web.archive.org/web/2oe/http://wayback-fakeurl.archive.org/yt/97t7Xj_iBv0',
            'info_dict': {
                'id': '97t7Xj_iBv0',
                'ext': 'mp4',
                'title': "Unknown Video"
            }

        },
        {
            # Video from 2012, webm format itag 45
            'url': 'https://web.archive.org/web/20120712231619/http://www.youtube.com/watch?v=AkhihxRKcrs&gl=US&hl=en',
            'info_dict': {
                'id': 'AkhihxRKcrs',
                'ext': 'webm',
                'title': "Unknown Video"
            }
        },
        {
            # Old flash-only video
            'url': 'https://web.archive.org/web/20081211103536/http://www.youtube.com/watch?v=jNQXAC9IVRw',
            'info_dict': {
                'id': 'jNQXAC9IVRw',
                'ext': 'unknown_video',
                'title': "Unknown Video"
            }
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # Use link translator mentioned in https://github.com/ytdl-org/youtube-dl/issues/13655
        internal_fake_url = self._INTERNAL_URL_TEMPLATE % video_id
        video_file_webpage = self._request_webpage(
            HEADRequest(internal_fake_url), video_id, errnote="Video is not archived or issue with web.archive.org")
        video_file_url = compat_urllib_parse_unquote(video_file_webpage.url)
        video_file_url_qs = compat_parse_qs(compat_urlparse.urlparse(video_file_url).query)

        # Attempt to recover any ext & format info from playback url
        format = {'url': video_file_url}
        itag = try_get(video_file_url_qs, lambda x: x['itag'][0])
        if itag and itag in YoutubeIE._formats:  # Naughty access but it works
            format.update(YoutubeIE._formats[itag])
            format.update({'format_id': itag})
        else:
            mime = try_get(video_file_url_qs, lambda x: x['mime'][0])
            ext = mimetype2ext(mime) or determine_ext(video_file_url)
            format.update({'ext': ext})
        return {
            'id': video_id,
            'title': "Unknown Video",  # In this case we are not able to get a title reliably.
            'formats': [format],
            'webpage_url': url,
            'duration': str_to_int(try_get(video_file_url_qs, lambda x: x['dur'][0]))
        }
