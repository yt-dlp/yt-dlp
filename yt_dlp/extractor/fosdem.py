from .common import InfoExtractor
import re


class FosdemIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:archive\.)?fosdem\.org/(?P<year>[0-9]{4})/schedule/(?P<url_type>track|event)/(?P<id>[\w\.-_]+)/'
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
                'description': 'This presentation will describe the results of the proof of concept work that takes into consideration integration of firmware update framework - fwupd/LVFS for OPNsense and pfSense. It will explain the challenges connected with the implementation of firmware update systems for BSD-based firewall and routing software. It will show basic concepts connected to the fwupd and LVFS. The security of the whole system is not determined only by the software it runs, but also by the firmware. Firmware is a piece of software inseparable from the hardware. It is responsible for proper hardware initialization as well as its security features. That means that the safety of the machine strongly depends on the mitigations of vulnerabilities provided by firmware (like microcode updates, bug/exploit fixes). For these particular reasons, the firmware should be kept up-to-date.\nRouters are highly popular attack vectors, therefore they must be appropriately secured. pfSense and OPNsense are well known secure firewall and routing software, but they do not have any firmware update methods. Therefore to secure hardware initialization of the routers, in this presentation we will present proof of concept work that takes into consideration integration of firmware update framework - fwupd/LVFS.\nNowadays, this is one of the most popular firmware update software. fwupd is a daemon that manages firmware updates of each of your hardware components that have some kind of firmware. What is more fwupd is open source, which makes it more trustworthy than proprietary applications delivered by hardware vendors designed for (only) their devices.',
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
                'description': 'The idea of the microkernel OS architecture is more that 50 years old and the term itself is just a few years younger. Over the years, it has been implemented in countless variants and modifications, it has served as a basis for intriguing OS experiments, it has gained strong position in the mission-critical and safety-critical areas and while it is still not the dominant architecture in the general-purpose desktop OS domain, it has had major influence on the "mainstream" operating systems as well.\nThis talk, however, is not about the history. Instead, we describe where are the microkernel-based operating systems today, who works on them and why, who uses them in production and why, where they aim for the future. The purpose of this talk is also to present the basic practical experiences with the existing microkernel-based operating systems — not to compare them, but to provide the potential users and contributors with an initial sorted list of operating systems they should look into in more detail depending on their needs.'
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
                'description': 'Unikernels promise fast boot times, small memory footprint and stronger security but lack in terms of manageability. Moreover, unikernels provide a non-generic environment for applications, with limited or no support for widely used libraries and OS features. This issue is even more apparent in the case of hardware acceleration. Acceleration libraries are often dynamically linked and have numerous dependencies, which directly contradict the statically linked notion of unikernels. Hardware acceleration functionality is almost non-existent in unikernel frameworks, mainly due to the absence of suitable virtualization solutions for such devices. ​ In this talk, we present an update on the vAccel framework we have built that can expose hardware acceleration semantics to workloads running on isolated sandboxes. We go through the components that comprise the framework and elaborate on the challenges in building such a software stack: we first present an overview of vAccel and how it works; then we focus on the porting effort of vAccel in various unikernel frameworks. Finally, we present a hardware acceleration abstraction that expose semantic acceleration functionality to workloads running as unikernels. ​ We will present a short demo of some popular algorithms running on top of Unikraft and vAccel show-casing the merits and trade-offs of this approach.'
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
