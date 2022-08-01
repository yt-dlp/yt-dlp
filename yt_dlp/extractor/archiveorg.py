import json
import re
import urllib.parse

from .common import InfoExtractor
from .youtube import YoutubeBaseInfoExtractor, YoutubeIE
from ..compat import compat_HTTPError, compat_urllib_parse_unquote
from ..utils import (
    KNOWN_EXTENSIONS,
    ExtractorError,
    HEADRequest,
    bug_reports_message,
    clean_html,
    dict_get,
    extract_attributes,
    get_element_by_id,
    int_or_none,
    join_nonempty,
    merge_dicts,
    mimetype2ext,
    orderedSet,
    parse_duration,
    parse_qs,
    str_or_none,
    str_to_int,
    traverse_obj,
    try_get,
    unified_strdate,
    unified_timestamp,
    url_or_none,
    urlhandle_detect_ext,
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
            'thumbnail': r're:https://archive\.org/download/.*\.jpg',
            'release_year': 1968,
            'display_id': 'XD300-23_68HighlightsAResearchCntAugHumanIntellect.cdr',
            'track': 'XD300-23 68HighlightsAResearchCntAugHumanIntellect',

        },
    }, {
        'url': 'https://archive.org/details/Cops1922',
        'md5': '0869000b4ce265e8ca62738b336b268a',
        'info_dict': {
            'id': 'Cops1922',
            'ext': 'mp4',
            'title': 'Buster Keaton\'s "Cops" (1922)',
            'description': 'md5:cd6f9910c35aedd5fc237dbc3957e2ca',
            'uploader': 'yorkmba99@hotmail.com',
            'timestamp': 1387699629,
            'upload_date': '20131222',
            'display_id': 'Cops-v2.mp4',
            'thumbnail': r're:https://archive\.org/download/.*\.jpg',
            'duration': 1091.96,
        },
    }, {
        'url': 'http://archive.org/embed/XD300-23_68HighlightsAResearchCntAugHumanIntellect',
        'only_matching': True,
    }, {
        'url': 'https://archive.org/details/Election_Ads',
        'md5': 'eec5cddebd4793c6a653b69c3b11f2e6',
        'info_dict': {
            'id': 'Election_Ads/Commercial-JFK1960ElectionAdCampaignJingle.mpg',
            'title': 'Commercial-JFK1960ElectionAdCampaignJingle.mpg',
            'ext': 'mpg',
            'thumbnail': r're:https://archive\.org/download/.*\.jpg',
            'duration': 59.77,
            'display_id': 'Commercial-JFK1960ElectionAdCampaignJingle.mpg',
        },
    }, {
        'url': 'https://archive.org/details/Election_Ads/Commercial-Nixon1960ElectionAdToughonDefense.mpg',
        'md5': 'ea1eed8234e7d4165f38c8c769edef38',
        'info_dict': {
            'id': 'Election_Ads/Commercial-Nixon1960ElectionAdToughonDefense.mpg',
            'title': 'Commercial-Nixon1960ElectionAdToughonDefense.mpg',
            'ext': 'mpg',
            'timestamp': 1205588045,
            'uploader': 'mikedavisstripmaster@yahoo.com',
            'description': '1960 Presidential Campaign Election Commercials John F Kennedy, Richard M Nixon',
            'upload_date': '20080315',
            'display_id': 'Commercial-Nixon1960ElectionAdToughonDefense.mpg',
            'duration': 59.51,
            'license': 'http://creativecommons.org/licenses/publicdomain/',
            'thumbnail': r're:https://archive\.org/download/.*\.jpg',
        },
    }, {
        'url': 'https://archive.org/details/gd1977-05-08.shure57.stevenson.29303.flac16',
        'md5': '7d07ffb42aba6537c28e053efa4b54c9',
        'info_dict': {
            'id': 'gd1977-05-08.shure57.stevenson.29303.flac16/gd1977-05-08d01t01.flac',
            'title': 'Turning',
            'ext': 'flac',
            'track': 'Turning',
            'creator': 'Grateful Dead',
            'display_id': 'gd1977-05-08d01t01.flac',
            'track_number': 1,
            'album': '1977-05-08 - Barton Hall - Cornell University',
            'duration': 39.8,
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
            'description': 'md5:6c921464414814720c6593810a5c7e3d',
            'upload_date': '20080319',
            'location': 'Barton Hall - Cornell University',
            'duration': 438.68,
            'track': 'Deal',
            'creator': 'Grateful Dead',
            'album': '1977-05-08 - Barton Hall - Cornell University',
            'release_date': '19770508',
            'display_id': 'gd1977-05-08d01t07.flac',
            'release_year': 1977,
            'track_number': 7,
        },
    }, {
        # FIXME: give a better error message than just IndexError when all available formats are restricted
        'url': 'https://archive.org/details/lp_the-music-of-russia_various-artists-a-askaryan-alexander-melik',
        'md5': '7cb019baa9b332e82ea7c10403acd180',
        'info_dict': {
            'id': 'lp_the-music-of-russia_various-artists-a-askaryan-alexander-melik/disc1/01.01. Bells Of Rostov.mp3',
            'title': 'Bells Of Rostov',
            'ext': 'mp3',
        },
        'skip': 'restricted'
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
        'skip': 'restricted'
    }, {
        # Original formats are private
        'url': 'https://archive.org/details/irelandthemakingofarepublic',
        'info_dict': {
            'id': 'irelandthemakingofarepublic',
            'title': 'Ireland: The Making of a Republic',
            'upload_date': '20160610',
            'description': 'md5:f70956a156645a658a0dc9513d9e78b7',
            'uploader': 'dimitrios@archive.org',
            'creator': ['British Broadcasting Corporation', 'Time-Life Films'],
            'timestamp': 1465594947,
        },
        'playlist': [
            {
                'md5': '0b211261b26590d49df968f71b90690d',
                'info_dict': {
                    'id': 'irelandthemakingofarepublic/irelandthemakingofarepublicreel1_01.mov',
                    'ext': 'mp4',
                    'title': 'irelandthemakingofarepublicreel1_01.mov',
                    'duration': 130.46,
                    'thumbnail': 'https://archive.org/download/irelandthemakingofarepublic/irelandthemakingofarepublic.thumbs/irelandthemakingofarepublicreel1_01_000117.jpg',
                    'display_id': 'irelandthemakingofarepublicreel1_01.mov',
                },
            }, {
                'md5': '67335ee3b23a0da930841981c1e79b02',
                'info_dict': {
                    'id': 'irelandthemakingofarepublic/irelandthemakingofarepublicreel1_02.mov',
                    'ext': 'mp4',
                    'duration': 1395.13,
                    'title': 'irelandthemakingofarepublicreel1_02.mov',
                    'display_id': 'irelandthemakingofarepublicreel1_02.mov',
                    'thumbnail': 'https://archive.org/download/irelandthemakingofarepublic/irelandthemakingofarepublic.thumbs/irelandthemakingofarepublicreel1_02_001374.jpg',
                },
            }, {
                'md5': 'e470e86787893603f4a341a16c281eb5',
                'info_dict': {
                    'id': 'irelandthemakingofarepublic/irelandthemakingofarepublicreel2.mov',
                    'ext': 'mp4',
                    'duration': 1602.67,
                    'title': 'irelandthemakingofarepublicreel2.mov',
                    'thumbnail': 'https://archive.org/download/irelandthemakingofarepublic/irelandthemakingofarepublic.thumbs/irelandthemakingofarepublicreel2_001554.jpg',
                    'display_id': 'irelandthemakingofarepublicreel2.mov',
                },
            }
        ]
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
        video_id = urllib.parse.unquote_plus(self._match_id(url))
        identifier, entry_id = (video_id.split('/', 1) + [None])[:2]

        # Archive.org metadata API doesn't clearly demarcate playlist entries
        # or subtitle tracks, so we get them from the embeddable player.
        embed_page = self._download_webpage(f'https://archive.org/embed/{identifier}', identifier)
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
                'subtitles': {},
            }

            for track in p.get('tracks', []):
                if track['kind'] != 'subtitles':
                    continue
                entries[p['orig']][track['label']] = {
                    'url': 'https://archive.org/' + track['file'].lstrip('/')
                }

        metadata = self._download_json('http://archive.org/metadata/' + identifier, identifier)
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
            'webpage_url': f'https://archive.org/details/{identifier}',
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
            elif traverse_obj(f, 'original', expected_type=str) in entries:
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

            # We don't want to skip private formats if the user has access to them,
            # however without access to an account with such privileges we can't implement/test this.
            # For now to be safe, we will only skip them if there is no user logged in.
            is_logged_in = bool(self._get_cookies('https://archive.org').get('logged-in-sig'))
            if extension in KNOWN_EXTENSIONS and (not f.get('private') or is_logged_in):
                entry['formats'].append({
                    'url': 'https://archive.org/download/' + identifier + '/' + f['name'],
                    'format': f.get('format'),
                    'width': int_or_none(f.get('width')),
                    'height': int_or_none(f.get('height')),
                    'filesize': int_or_none(f.get('size')),
                    'protocol': 'https',
                    'source_preference': 0 if f.get('source') == 'original' else -1,
                    'format_note': f.get('source')
                })

        for entry in entries.values():
            self._sort_formats(entry['formats'], ('source', ))

        if len(entries) == 1:
            # If there's only one item, use it as the main info dict
            only_video = next(iter(entries.values()))
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
    IE_NAME = 'web.archive:youtube'
    IE_DESC = 'web.archive.org saved youtube videos, "ytarchive:" prefix'
    _VALID_URL = r'''(?x)(?:(?P<prefix>ytarchive:)|
            (?:https?://)?web\.archive\.org/
            (?:web/)?(?:(?P<date>[0-9]{14})?[0-9A-Za-z_*]*/)?  # /web and the version index is optional
            (?:https?(?::|%3[Aa])//)?(?:
                (?:\w+\.)?youtube\.com(?::(?:80|443))?/watch(?:\.php)?(?:\?|%3[fF])(?:[^\#]+(?:&|%26))?v(?:=|%3[dD])  # Youtube URL
                |(?:wayback-fakeurl\.archive\.org/yt/)  # Or the internal fake url
            )
        )(?P<id>[0-9A-Za-z_-]{11})
        (?(prefix)
            (?::(?P<date2>[0-9]{14}))?$|
            (?:%26|[#&]|$)
        )'''

    _TESTS = [
        {
            'url': 'https://web.archive.org/web/20150415002341/https://www.youtube.com/watch?v=aYAGB11YrSs',
            'info_dict': {
                'id': 'aYAGB11YrSs',
                'ext': 'webm',
                'title': 'Team Fortress 2 - Sandviches!',
                'description': 'md5:4984c0f9a07f349fc5d8e82ab7af4eaf',
                'upload_date': '20110926',
                'uploader': 'Zeurel',
                'channel_id': 'UCukCyHaD-bK3in_pKpfH9Eg',
                'duration': 32,
                'uploader_id': 'Zeurel',
                'uploader_url': 'http://www.youtube.com/user/Zeurel'
            }
        }, {
            # Internal link
            'url': 'https://web.archive.org/web/2oe/http://wayback-fakeurl.archive.org/yt/97t7Xj_iBv0',
            'info_dict': {
                'id': '97t7Xj_iBv0',
                'ext': 'mp4',
                'title': 'Why Machines That Bend Are Better',
                'description': 'md5:00404df2c632d16a674ff8df1ecfbb6c',
                'upload_date': '20190312',
                'uploader': 'Veritasium',
                'channel_id': 'UCHnyfMqiRRG1u-2MsSQLbXA',
                'duration': 771,
                'uploader_id': '1veritasium',
                'uploader_url': 'http://www.youtube.com/user/1veritasium'
            }
        }, {
            # Video from 2012, webm format itag 45. Newest capture is deleted video, with an invalid description.
            # Should use the date in the link. Title ends with '- Youtube'. Capture has description in eow-description
            'url': 'https://web.archive.org/web/20120712231619/http://www.youtube.com/watch?v=AkhihxRKcrs&gl=US&hl=en',
            'info_dict': {
                'id': 'AkhihxRKcrs',
                'ext': 'webm',
                'title': 'Limited Run: Mondo\'s Modern Classic 1 of 3 (SDCC 2012)',
                'upload_date': '20120712',
                'duration': 398,
                'description': 'md5:ff4de6a7980cb65d951c2f6966a4f2f3',
                'uploader_id': 'machinima',
                'uploader_url': 'http://www.youtube.com/user/machinima'
            }
        }, {
            # FLV video. Video file URL does not provide itag information
            'url': 'https://web.archive.org/web/20081211103536/http://www.youtube.com/watch?v=jNQXAC9IVRw',
            'info_dict': {
                'id': 'jNQXAC9IVRw',
                'ext': 'flv',
                'title': 'Me at the zoo',
                'upload_date': '20050423',
                'channel_id': 'UC4QobU6STFB0P71PMvOGN5A',
                'duration': 19,
                'description': 'md5:10436b12e07ac43ff8df65287a56efb4',
                'uploader_id': 'jawed',
                'uploader_url': 'http://www.youtube.com/user/jawed'
            }
        }, {
            'url': 'https://web.archive.org/web/20110712231407/http://www.youtube.com/watch?v=lTx3G6h2xyA',
            'info_dict': {
                'id': 'lTx3G6h2xyA',
                'ext': 'flv',
                'title': 'Madeon - Pop Culture (live mashup)',
                'upload_date': '20110711',
                'uploader': 'Madeon',
                'channel_id': 'UCqMDNf3Pn5L7pcNkuSEeO3w',
                'duration': 204,
                'description': 'md5:f7535343b6eda34a314eff8b85444680',
                'uploader_id': 'itsmadeon',
                'uploader_url': 'http://www.youtube.com/user/itsmadeon'
            }
        }, {
            # First capture is of dead video, second is the oldest from CDX response.
            'url': 'https://web.archive.org/https://www.youtube.com/watch?v=1JYutPM8O6E',
            'info_dict': {
                'id': '1JYutPM8O6E',
                'ext': 'mp4',
                'title': 'Fake Teen Doctor Strikes AGAIN! - Weekly Weird News',
                'upload_date': '20160218',
                'channel_id': 'UCdIaNUarhzLSXGoItz7BHVA',
                'duration': 1236,
                'description': 'md5:21032bae736421e89c2edf36d1936947',
                'uploader_id': 'MachinimaETC',
                'uploader_url': 'http://www.youtube.com/user/MachinimaETC'
            }
        }, {
            # First capture of dead video, capture date in link links to dead capture.
            'url': 'https://web.archive.org/web/20180803221945/https://www.youtube.com/watch?v=6FPhZJGvf4E',
            'info_dict': {
                'id': '6FPhZJGvf4E',
                'ext': 'mp4',
                'title': 'WTF: Video Games Still Launch BROKEN?! - T.U.G.S.',
                'upload_date': '20160219',
                'channel_id': 'UCdIaNUarhzLSXGoItz7BHVA',
                'duration': 798,
                'description': 'md5:a1dbf12d9a3bd7cb4c5e33b27d77ffe7',
                'uploader_id': 'MachinimaETC',
                'uploader_url': 'http://www.youtube.com/user/MachinimaETC'
            },
            'expected_warnings': [
                r'unable to download capture webpage \(it may not be archived\)'
            ]
        }, {   # Very old YouTube page, has - YouTube in title.
            'url': 'http://web.archive.org/web/20070302011044/http://youtube.com/watch?v=-06-KB9XTzg',
            'info_dict': {
                'id': '-06-KB9XTzg',
                'ext': 'flv',
                'title': 'New Coin Hack!! 100% Safe!!'
            }
        }, {
            'url': 'web.archive.org/https://www.youtube.com/watch?v=dWW7qP423y8',
            'info_dict': {
                'id': 'dWW7qP423y8',
                'ext': 'mp4',
                'title': 'It\'s Bootleg AirPods Time.',
                'upload_date': '20211021',
                'channel_id': 'UC7Jwj9fkrf1adN4fMmTkpug',
                'channel_url': 'http://www.youtube.com/channel/UC7Jwj9fkrf1adN4fMmTkpug',
                'duration': 810,
                'description': 'md5:7b567f898d8237b256f36c1a07d6d7bc',
                'uploader': 'DankPods',
                'uploader_id': 'UC7Jwj9fkrf1adN4fMmTkpug',
                'uploader_url': 'http://www.youtube.com/channel/UC7Jwj9fkrf1adN4fMmTkpug'
            }
        }, {
            # player response contains '};' See: https://github.com/ytdl-org/youtube-dl/issues/27093
            'url': 'https://web.archive.org/web/20200827003909if_/http://www.youtube.com/watch?v=6Dh-RL__uN4',
            'info_dict': {
                'id': '6Dh-RL__uN4',
                'ext': 'mp4',
                'title': 'bitch lasagna',
                'upload_date': '20181005',
                'channel_id': 'UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'channel_url': 'http://www.youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw',
                'duration': 135,
                'description': 'md5:2dbe4051feeff2dab5f41f82bb6d11d0',
                'uploader': 'PewDiePie',
                'uploader_id': 'PewDiePie',
                'uploader_url': 'http://www.youtube.com/user/PewDiePie'
            }
        }, {
            'url': 'https://web.archive.org/web/http://www.youtube.com/watch?v=kH-G_aIBlFw',
            'only_matching': True
        }, {
            'url': 'https://web.archive.org/web/20050214000000_if/http://www.youtube.com/watch?v=0altSZ96U4M',
            'only_matching': True
        }, {
            # Video not archived, only capture is unavailable video page
            'url': 'https://web.archive.org/web/20210530071008/https://www.youtube.com/watch?v=lHJTf93HL1s&spfreload=10',
            'only_matching': True
        }, {   # Encoded url
            'url': 'https://web.archive.org/web/20120712231619/http%3A//www.youtube.com/watch%3Fgl%3DUS%26v%3DAkhihxRKcrs%26hl%3Den',
            'only_matching': True
        }, {
            'url': 'https://web.archive.org/web/20120712231619/http%3A//www.youtube.com/watch%3Fv%3DAkhihxRKcrs%26gl%3DUS%26hl%3Den',
            'only_matching': True
        }, {
            'url': 'https://web.archive.org/web/20060527081937/http://www.youtube.com:80/watch.php?v=ELTFsLT73fA&amp;search=soccer',
            'only_matching': True
        }, {
            'url': 'https://web.archive.org/http://www.youtube.com:80/watch?v=-05VVye-ffg',
            'only_matching': True
        }, {
            'url': 'ytarchive:BaW_jenozKc:20050214000000',
            'only_matching': True
        }, {
            'url': 'ytarchive:BaW_jenozKc',
            'only_matching': True
        },
    ]
    _YT_INITIAL_DATA_RE = YoutubeBaseInfoExtractor._YT_INITIAL_DATA_RE
    _YT_INITIAL_PLAYER_RESPONSE_RE = fr'''(?x)
        (?:window\s*\[\s*["\']ytInitialPlayerResponse["\']\s*\]|ytInitialPlayerResponse)\s*=[(\s]*|
        {YoutubeBaseInfoExtractor._YT_INITIAL_PLAYER_RESPONSE_RE}'''

    _YT_DEFAULT_THUMB_SERVERS = ['i.ytimg.com']  # thumbnails most likely archived on these servers
    _YT_ALL_THUMB_SERVERS = orderedSet(
        _YT_DEFAULT_THUMB_SERVERS + ['img.youtube.com', *[f'{c}{n or ""}.ytimg.com' for c in ('i', 's') for n in (*range(0, 5), 9)]])

    _WAYBACK_BASE_URL = 'https://web.archive.org/web/%sif_/'
    _OLDEST_CAPTURE_DATE = 20050214000000
    _NEWEST_CAPTURE_DATE = 20500101000000

    def _call_cdx_api(self, item_id, url, filters: list = None, collapse: list = None, query: dict = None, note=None, fatal=False):
        # CDX docs: https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md
        query = {
            'url': url,
            'output': 'json',
            'fl': 'original,mimetype,length,timestamp',
            'limit': 500,
            'filter': ['statuscode:200'] + (filters or []),
            'collapse': collapse or [],
            **(query or {})
        }
        res = self._download_json(
            'https://web.archive.org/cdx/search/cdx', item_id,
            note or 'Downloading CDX API JSON', query=query, fatal=fatal)
        if isinstance(res, list) and len(res) >= 2:
            # format response to make it easier to use
            return list(dict(zip(res[0], v)) for v in res[1:])
        elif not isinstance(res, list) or len(res) != 0:
            self.report_warning('Error while parsing CDX API response' + bug_reports_message())

    def _extract_webpage_title(self, webpage):
        page_title = self._html_extract_title(webpage, default='')
        # YouTube video pages appear to always have either 'YouTube -' as prefix or '- YouTube' as suffix.
        return self._html_search_regex(
            r'(?:YouTube\s*-\s*(.*)$)|(?:(.*)\s*-\s*YouTube$)',
            page_title, 'title', default='')

    def _extract_metadata(self, video_id, webpage):
        search_meta = ((lambda x: self._html_search_meta(x, webpage, default=None)) if webpage else (lambda x: None))
        player_response = self._search_json(
            self._YT_INITIAL_PLAYER_RESPONSE_RE, webpage, 'initial player response',
            video_id, default={})
        initial_data = self._search_json(
            self._YT_INITIAL_DATA_RE, webpage, 'initial data', video_id, default={})

        initial_data_video = traverse_obj(
            initial_data, ('contents', 'twoColumnWatchNextResults', 'results', 'results', 'contents', ..., 'videoPrimaryInfoRenderer'),
            expected_type=dict, get_all=False, default={})

        video_details = traverse_obj(
            player_response, 'videoDetails', expected_type=dict, get_all=False, default={})

        microformats = traverse_obj(
            player_response, ('microformat', 'playerMicroformatRenderer'), expected_type=dict, get_all=False, default={})

        video_title = (
            video_details.get('title')
            or YoutubeBaseInfoExtractor._get_text(microformats, 'title')
            or YoutubeBaseInfoExtractor._get_text(initial_data_video, 'title')
            or self._extract_webpage_title(webpage)
            or search_meta(['og:title', 'twitter:title', 'title']))

        channel_id = str_or_none(
            video_details.get('channelId')
            or microformats.get('externalChannelId')
            or search_meta('channelId')
            or self._search_regex(
                r'data-channel-external-id=(["\'])(?P<id>(?:(?!\1).)+)\1',  # @b45a9e6
                webpage, 'channel id', default=None, group='id'))
        channel_url = f'http://www.youtube.com/channel/{channel_id}' if channel_id else None

        duration = int_or_none(
            video_details.get('lengthSeconds')
            or microformats.get('lengthSeconds')
            or parse_duration(search_meta('duration')))
        description = (
            video_details.get('shortDescription')
            or YoutubeBaseInfoExtractor._get_text(microformats, 'description')
            or clean_html(get_element_by_id('eow-description', webpage))  # @9e6dd23
            or search_meta(['description', 'og:description', 'twitter:description']))

        uploader = video_details.get('author')

        # Uploader ID and URL
        uploader_mobj = re.search(
            r'<link itemprop="url" href="(?P<uploader_url>https?://www\.youtube\.com/(?:user|channel)/(?P<uploader_id>[^"]+))">',  # @fd05024
            webpage)
        if uploader_mobj is not None:
            uploader_id, uploader_url = uploader_mobj.group('uploader_id'), uploader_mobj.group('uploader_url')
        else:
            # @a6211d2
            uploader_url = url_or_none(microformats.get('ownerProfileUrl'))
            uploader_id = self._search_regex(
                r'(?:user|channel)/([^/]+)', uploader_url or '', 'uploader id', default=None)

        upload_date = unified_strdate(
            dict_get(microformats, ('uploadDate', 'publishDate'))
            or search_meta(['uploadDate', 'datePublished'])
            or self._search_regex(
                [r'(?s)id="eow-date.*?>(.*?)</span>',
                 r'(?:id="watch-uploader-info".*?>.*?|["\']simpleText["\']\s*:\s*["\'])(?:Published|Uploaded|Streamed live|Started) on (.+?)[<"\']'],  # @7998520
                webpage, 'upload date', default=None))

        return {
            'title': video_title,
            'description': description,
            'upload_date': upload_date,
            'uploader': uploader,
            'channel_id': channel_id,
            'channel_url': channel_url,
            'duration': duration,
            'uploader_url': uploader_url,
            'uploader_id': uploader_id,
        }

    def _extract_thumbnails(self, video_id):
        try_all = 'thumbnails' in self._configuration_arg('check_all')
        thumbnail_base_urls = ['http://{server}/vi{webp}/{video_id}'.format(
            webp='_webp' if ext == 'webp' else '', video_id=video_id, server=server)
            for server in (self._YT_ALL_THUMB_SERVERS if try_all else self._YT_DEFAULT_THUMB_SERVERS) for ext in (('jpg', 'webp') if try_all else ('jpg',))]

        thumbnails = []
        for url in thumbnail_base_urls:
            response = self._call_cdx_api(
                video_id, url, filters=['mimetype:image/(?:webp|jpeg)'],
                collapse=['urlkey'], query={'matchType': 'prefix'})
            if not response:
                continue
            thumbnails.extend(
                {
                    'url': (self._WAYBACK_BASE_URL % (int_or_none(thumbnail_dict.get('timestamp')) or self._OLDEST_CAPTURE_DATE)) + thumbnail_dict.get('original'),
                    'filesize': int_or_none(thumbnail_dict.get('length')),
                    'preference': int_or_none(thumbnail_dict.get('length'))
                } for thumbnail_dict in response)
            if not try_all:
                break

        self._remove_duplicate_formats(thumbnails)
        return thumbnails

    def _get_capture_dates(self, video_id, url_date):
        capture_dates = []
        # Note: CDX API will not find watch pages with extra params in the url.
        response = self._call_cdx_api(
            video_id, f'https://www.youtube.com/watch?v={video_id}',
            filters=['mimetype:text/html'], collapse=['timestamp:6', 'digest'], query={'matchType': 'prefix'}) or []
        all_captures = sorted(int_or_none(r['timestamp']) for r in response if int_or_none(r['timestamp']) is not None)

        # Prefer the new polymer UI captures as we support extracting more metadata from them
        # WBM captures seem to all switch to this layout ~July 2020
        modern_captures = [x for x in all_captures if x >= 20200701000000]
        if modern_captures:
            capture_dates.append(modern_captures[0])
        capture_dates.append(url_date)
        if all_captures:
            capture_dates.append(all_captures[0])

        if 'captures' in self._configuration_arg('check_all'):
            capture_dates.extend(modern_captures + all_captures)

        # Fallbacks if any of the above fail
        capture_dates.extend([self._OLDEST_CAPTURE_DATE, self._NEWEST_CAPTURE_DATE])
        return orderedSet(filter(None, capture_dates))

    def _real_extract(self, url):
        video_id, url_date, url_date_2 = self._match_valid_url(url).group('id', 'date', 'date2')
        url_date = url_date or url_date_2

        urlh = None
        try:
            urlh = self._request_webpage(
                HEADRequest('https://web.archive.org/web/2oe_/http://wayback-fakeurl.archive.org/yt/%s' % video_id),
                video_id, note='Fetching archived video file url', expected_status=True)
        except ExtractorError as e:
            # HTTP Error 404 is expected if the video is not saved.
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 404:
                self.raise_no_formats(
                    'The requested video is not archived, indexed, or there is an issue with web.archive.org',
                    expected=True)
            else:
                raise

        capture_dates = self._get_capture_dates(video_id, int_or_none(url_date))
        self.write_debug('Captures to try: ' + join_nonempty(*capture_dates, delim=', '))
        info = {'id': video_id}
        for capture in capture_dates:
            webpage = self._download_webpage(
                (self._WAYBACK_BASE_URL + 'http://www.youtube.com/watch?v=%s') % (capture, video_id),
                video_id=video_id, fatal=False, errnote='unable to download capture webpage (it may not be archived)',
                note='Downloading capture webpage')
            current_info = self._extract_metadata(video_id, webpage or '')
            # Try avoid getting deleted video metadata
            if current_info.get('title'):
                info = merge_dicts(info, current_info)
                if 'captures' not in self._configuration_arg('check_all'):
                    break

        info['thumbnails'] = self._extract_thumbnails(video_id)

        if urlh:
            url = compat_urllib_parse_unquote(urlh.geturl())
            video_file_url_qs = parse_qs(url)
            # Attempt to recover any ext & format info from playback url & response headers
            format = {'url': url, 'filesize': int_or_none(urlh.headers.get('x-archive-orig-content-length'))}
            itag = try_get(video_file_url_qs, lambda x: x['itag'][0])
            if itag and itag in YoutubeIE._formats:
                format.update(YoutubeIE._formats[itag])
                format.update({'format_id': itag})
            else:
                mime = try_get(video_file_url_qs, lambda x: x['mime'][0])
                ext = (mimetype2ext(mime)
                       or urlhandle_detect_ext(urlh)
                       or mimetype2ext(urlh.headers.get('x-archive-guessed-content-type')))
                format.update({'ext': ext})
            info['formats'] = [format]
            if not info.get('duration'):
                info['duration'] = str_to_int(try_get(video_file_url_qs, lambda x: x['dur'][0]))

        if not info.get('title'):
            info['title'] = video_id
        return info
