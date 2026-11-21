from .common import InfoExtractor
import re


class FosdemIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:archive\.)?fosdem\.org/(?P<year>\d{4})/schedule/(?P<type>track|event)/(?P<id>[\w.-]+)'
    _TESTS = [
        {
            'url': 'https://archive.fosdem.org/2022/schedule/event/firmware_updates_for_opnsense_and_pfsense/',
            'info_dict': {
                'id': 'firmware_updates_for_opnsense_and_pfsense',
                'ext': 'webm',
                'title': 'Firmware updates for OPNsense and pfSense with fwupd/LVFS',
                'thumbnail': None,
                'release_date': '2022',
                'cast': ['Norbert Kamiński'],
                'uploader': 'FOSDEM',
                'description': 'md5:06a533c1dd130b9b9aa75a8c50c2625f',
            }
        },
        {
            'url': 'https://fosdem.org/2023/schedule/event/microkernel2023/',
            'info_dict': {
                'id': 'microkernel2023',
                'ext': 'webm',
                'title': 'The Microkernel Landscape in 2023',
                'thumbnail': None,
                'release_date': '2023',
                'uploader': 'FOSDEM',
                'cast': ['Martin Děcký'],
                'description': 'md5:dd38c1219fe9cc4aa18b2ef51f70f24c'
            }
        },
        {
            'url': 'https://fosdem.org/2023/schedule/event/hwacceluk/',
            'info_dict': {
                'id': 'hwacceluk',
                'ext': 'webm',
                'title': 'Hardware acceleration for Unikernels',
                'thumbnail': None,
                'release_date': '2023',
                'cast': ['Anastassios Nanos', 'Charalampos Mainas'],
                'uploader': 'FOSDEM',
                'description': 'md5:0e4d502d9aadd42d844407b49fab276c'
            }
        },
        {
            'url': 'https://fosdem.org/2023/schedule/track/microkernel_and_component_based_os/',
            'playlist_count': 11,
            'info_dict': {
                'id': 'microkernel_and_component_based_os',
                'title': 'Microkernel and Component-based OS devroom',
            }
        }
    ]

    def _real_extract(self, url):
        video_id, url_type, year = self._match_valid_url(url).group('id', 'type', 'year')
        webpage = self._download_webpage(url, video_id)
        title_rgx = r'<div id=\"pagetitles\">\n\s+<h1>(.+?)</h1>'
        title = self._html_search_regex(title_rgx, webpage, 'title') \
            or self._og_search_title(webpage)
        if url_type == 'event':
            evnt_blurb_rgx = r'<div class=\"event-blurb\">\n*(?P<blurb>(<div class=\"event-abstract\">(<p>(.+?)</p>\n*)+</div>)+\n*(<div class=\"event-description\">(<p>(.+?)</p>\n*)*</div>))+\n*</div>'
            evnt_blurb = self._html_search_regex(evnt_blurb_rgx,
                                                 webpage,
                                                 'event blurb',
                                                 group='blurb',
                                                 flags=re.DOTALL,
                                                 fatal=False)
            description = evnt_blurb
            video_url_rgx = r'<li><a href=\"(https://video.fosdem.org/[0-9]{4}/.+)\">'
            video_url = self._html_search_regex(video_url_rgx,
                                                webpage,
                                                'video url')
            cast_rgx = r'<td><a href=\"/[0-9]+/schedule/speaker/[a-z_]+/\">(?P<speaker>\w+ \w+)</a></td>'
            cast = re.findall(cast_rgx, webpage, flags=re.UNICODE) or []

            return {
                'id': video_id,
                'title': title,
                'description': description,
                'uploader': 'FOSDEM',
                'url': video_url,
                'thumbnail': None,
                'release_date': year,
                'cast': cast,
                'webpage_url': url,
            }
        elif url_type == 'track':
            events_rgx = r'<td><a href=\"(?P<event>/[0-9]+/schedule/event/[a-z0-9]+/)'
            events_slugs = re.findall(events_rgx, webpage) or []

            if len(events_slugs) > 0:
                events_urls = ['https://fosdem.org' + slug for slug in events_slugs]
            entries = []
            for event_url in events_urls:
                entries.append(self.url_result(event_url, 'Fosdem'))
            return self.playlist_result(entries,
                                        playlist_id=video_id,
                                        playlist_title=title,
                                        playlist_description=None)
        else:
            print(f'The {url_type} is not supported')
