import re
from .common import InfoExtractor
from ..utils import js_to_json, parse_resolution


class KVSPlayerEmbedIE(InfoExtractor):
    _VALID_URL = False

    _WEBPAGE_TESTS = [
        {
            # KVS Player
            'url': 'https://www.kvs-demo.com/videos/105/kelis-4th-of-july/',
            'info_dict': {
                'id': '105',
                'display_id': 'kelis-4th-of-july',
                'ext': 'mp4',
                'title': 'Kelis - 4th Of July',
                'thumbnail': 'https://www.kvs-demo.com/contents/videos_screenshots/0/105/preview.jpg',
            },
            'params': {
                'skip_download': True,
            },
        }, {
            # KVS Player
            'url': 'https://www.kvs-demo.com/embed/105/',
            'info_dict': {
                'id': '105',
                'display_id': 'kelis-4th-of-july',
                'ext': 'mp4',
                'title': 'Kelis - 4th Of July / Embed Player',
                'thumbnail': 'https://www.kvs-demo.com/contents/videos_screenshots/0/105/preview.jpg',
            },
            'params': {
                'skip_download': True,
            },
        }, {
            # KVS Player
            'url': 'https://thisvid.com/videos/french-boy-pantsed/',
            'md5': '3397979512c682f6b85b3b04989df224',
            'info_dict': {
                'id': '2400174',
                'display_id': 'french-boy-pantsed',
                'ext': 'mp4',
                'title': 'French Boy Pantsed - ThisVid.com',
                'thumbnail': 'https://media.thisvid.com/contents/videos_screenshots/2400000/2400174/preview.mp4.jpg',
            },
            'skip': 'dead'
        }, {
            # KVS Player
            'url': 'https://thisvid.com/embed/2400174/',
            'md5': '3397979512c682f6b85b3b04989df224',
            'info_dict': {
                'id': '2400174',
                'display_id': 'french-boy-pantsed',
                'ext': 'mp4',
                'title': 'French Boy Pantsed - ThisVid.com',
                'thumbnail': 'https://media.thisvid.com/contents/videos_screenshots/2400000/2400174/preview.mp4.jpg',
            },
            'skip': 'dead'
        }, {
            # KVS Player
            'url': 'https://youix.com/video/leningrad-zoj/',
            'md5': '94f96ba95706dc3880812b27b7d8a2b8',
            'info_dict': {
                'id': '18485',
                'display_id': 'leningrad-zoj',
                'ext': 'mp4',
                'title': 'Клип: Ленинград - ЗОЖ скачать, смотреть онлайн | Youix.com',
                'thumbnail': 'https://youix.com/contents/videos_screenshots/18000/18485/preview.jpg',
            },
        }, {
            # KVS Player
            'url': 'https://youix.com/embed/18485',
            'md5': '94f96ba95706dc3880812b27b7d8a2b8',
            'info_dict': {
                'id': '18485',
                'display_id': 'leningrad-zoj',
                'ext': 'mp4',
                'title': 'Ленинград - ЗОЖ',
                'thumbnail': 'https://youix.com/contents/videos_screenshots/18000/18485/preview.jpg',
            }
        }, {
            # KVS Player
            'url': 'https://bogmedia.org/videos/21217/40-nochey-40-nights-2016/',
            'md5': '94166bdb26b4cb1fb9214319a629fc51',
            'info_dict': {
                'id': '21217',
                'display_id': '40-nochey-2016',
                'ext': 'mp4',
                'title': '40 ночей (2016) - BogMedia.org',
                'thumbnail': 'https://bogmedia.org/contents/videos_screenshots/21000/21217/preview_480p.mp4.jpg',
            }
        },
        {
            # KVS Player (for sites that serve kt_player.js via non-https urls)
            'url': 'http://www.camhub.world/embed/389508',
            'md5': 'fbe89af4cfb59c8fd9f34a202bb03e32',
            'info_dict': {
                'id': '389508',
                'display_id': 'syren-de-mer-onlyfans-05-07-2020have-a-happy-safe-holiday5f014e68a220979bdb8cd-source',
                'ext': 'mp4',
                'title': 'Syren De Mer onlyfans_05-07-2020Have_a_happy_safe_holiday5f014e68a220979bdb8cd_source / Embed плеер',
                'thumbnail': 'https://www.camhub.world/contents/videos_screenshots/389000/389508/preview.mp4.jpg',
            }
        },
    ]

    def _kvs_getrealurl(self, video_url, license_code):
        if not video_url.startswith('function/0/'):
            return video_url  # not obfuscated

        url_path, _, url_query = video_url.partition('?')
        urlparts = url_path.split('/')[2:]
        license = self._kvs_getlicensetoken(license_code)
        newmagic = urlparts[5][:32]

        for o in range(len(newmagic) - 1, -1, -1):
            new = ''
            l = (o + sum(int(n) for n in license[o:])) % 32

            for i in range(0, len(newmagic)):
                if i == o:
                    new += newmagic[l]
                elif i == l:
                    new += newmagic[o]
                else:
                    new += newmagic[i]
            newmagic = new

        urlparts[5] = newmagic + urlparts[5][32:]
        return '/'.join(urlparts) + '?' + url_query

    def _kvs_getlicensetoken(self, license):
        modlicense = license.replace('$', '').replace('0', '1')
        center = int(len(modlicense) / 2)
        fronthalf = int(modlicense[:center + 1])
        backhalf = int(modlicense[center:])

        modlicense = str(4 * abs(fronthalf - backhalf))
        retval = ''
        for o in range(0, center + 1):
            for i in range(1, 5):
                retval += str((int(license[o + i]) + int(modlicense[o])) % 10)
        return retval

    def _extract_from_webpage(self, url, webpage):
        # Look for generic KVS player
        found = re.search(r'<script [^>]*?src="https?://.+?/kt_player\.js\?v=(?P<ver>(?P<maj_ver>\d+)(\.\d+)+)".*?>',
                          webpage)
        if not found:
            return
        if found.group('maj_ver') not in ['4', '5']:
            self.report_warning(
                'Untested major version (%s) in player engine--Download may fail.' % found.group('ver'))
        flashvars = re.search(r'(?ms)<script.*?>.*?var\s+flashvars\s*=\s*(\{.*?\});.*?</script>', webpage)
        flashvars = self._parse_json(flashvars.group(1), self._generic_id(url), transform_source=js_to_json)

        # extract the part after the last / as the display_id from the
        # canonical URL.
        display_id = self._search_regex(
            r'(?:<link href="https?://[^"]+/(.+?)/?" rel="canonical"\s*/?>'
            r'|<link rel="canonical" href="https?://[^"]+/(.+?)/?"\s*/?>)',
            webpage, 'display_id', fatal=False
        )
        title = self._html_search_regex(r'<(?:h1|title)>(?:Video: )?(.+?)</(?:h1|title)>', webpage, 'title')

        thumbnail = flashvars['preview_url']
        if thumbnail.startswith('//'):
            protocol, _, _ = url.partition('/')
            thumbnail = protocol + thumbnail

        url_keys = list(filter(re.compile(r'video_url|video_alt_url\d*').fullmatch, flashvars.keys()))
        formats = []
        for key in url_keys:
            if '/get_file/' not in flashvars[key]:
                continue
            format_id = flashvars.get(f'{key}_text', key)
            formats.append({
                'url': self._kvs_getrealurl(flashvars[key], flashvars['license_code']),
                'format_id': format_id,
                'ext': 'mp4',
                **(parse_resolution(format_id) or parse_resolution(flashvars[key]))
            })
            if not formats[-1].get('height'):
                formats[-1]['quality'] = 1

        self._sort_formats(formats)

        yield {
            'id': flashvars['video_id'],
            'display_id': display_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }
