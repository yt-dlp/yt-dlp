# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    unified_strdate,
    compat_str,
    determine_ext,
    ExtractorError,
    update_url_query,
)


class DisneyIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?P<domain>(?:[^/]+\.)?(?:disney\.[a-z]{2,3}(?:\.[a-z]{2})?|disney(?:(?:me|latino)\.com|turkiye\.com\.tr|channel\.de)|(?:starwars|marvelkids)\.com))/(?:(?:embed/|(?:[^/]+/)+[\w-]+-)(?P<id>[a-z0-9]{24})|(?:[^/]+/)?(?P<display_id>[^/?#]+))'''
    _TESTS = [{
        # Disney.EmbedVideo
        'url': 'http://video.disney.com/watch/moana-trailer-545ed1857afee5a0ec239977',
        'info_dict': {
            'id': '545ed1857afee5a0ec239977',
            'ext': 'mp4',
            'title': 'Moana - Trailer',
            'description': 'A fun adventure for the entire Family!  Bring home Moana on Digital HD Feb 21 & Blu-ray March 7',
            'upload_date': '20170112',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }, {
        # Grill.burger
        'url': 'http://www.starwars.com/video/rogue-one-a-star-wars-story-intro-featurette',
        'info_dict': {
            'id': '5454e9f4e9804a552e3524c8',
            'ext': 'mp4',
            'title': '"Intro" Featurette: Rogue One: A Star Wars Story',
            'upload_date': '20170104',
            'description': 'Go behind-the-scenes of Rogue One: A Star Wars Story in this featurette with Director Gareth Edwards and the cast of the film.',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }, {
        'url': 'http://videos.disneylatino.com/ver/spider-man-de-regreso-a-casa-primer-adelanto-543a33a1850bdcfcca13bae2',
        'only_matching': True,
    }, {
        'url': 'http://video.en.disneyme.com/watch/future-worm/robo-carp-2001-544b66002aa7353cdd3f5114',
        'only_matching': True,
    }, {
        'url': 'http://video.disneyturkiye.com.tr/izle/7c-7-cuceler/kimin-sesi-zaten-5456f3d015f6b36c8afdd0e2',
        'only_matching': True,
    }, {
        'url': 'http://disneyjunior.disney.com/embed/546a4798ddba3d1612e4005d',
        'only_matching': True,
    }, {
        'url': 'http://www.starwars.com/embed/54690d1e6c42e5f09a0fb097',
        'only_matching': True,
    }, {
        'url': 'http://spiderman.marvelkids.com/embed/522900d2ced3c565e4cc0677',
        'only_matching': True,
    }, {
        'url': 'http://spiderman.marvelkids.com/videos/contest-of-champions-part-four-clip-1',
        'only_matching': True,
    }, {
        'url': 'http://disneyjunior.en.disneyme.com/dj/watch-my-friends-tigger-and-pooh-promo',
        'only_matching': True,
    }, {
        'url': 'http://disneychannel.de/sehen/soy-luna-folge-118-5518518987ba27f3cc729268',
        'only_matching': True,
    }, {
        'url': 'http://disneyjunior.disney.com/galactech-the-galactech-grab-galactech-an-admiral-rescue',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, video_id, display_id = re.match(self._VALID_URL, url).groups()
        if not video_id:
            webpage = self._download_webpage(url, display_id)
            grill = re.sub(r'"\s*\+\s*"', '', self._search_regex(
                r'Grill\.burger\s*=\s*({.+})\s*:',
                webpage, 'grill data'))
            page_data = next(s for s in self._parse_json(grill, display_id)['stack'] if s.get('type') == 'video')
            video_data = page_data['data'][0]
        else:
            webpage = self._download_webpage(
                'http://%s/embed/%s' % (domain, video_id), video_id)
            page_data = self._parse_json(self._search_regex(
                r'Disney\.EmbedVideo\s*=\s*({.+});',
                webpage, 'embed data'), video_id)
            video_data = page_data['video']

        for external in video_data.get('externals', []):
            if external.get('source') == 'vevo':
                return self.url_result('vevo:' + external['data_id'], 'Vevo')

        video_id = video_data['id']
        title = video_data['title']

        formats = []
        for flavor in video_data.get('flavors', []):
            flavor_format = flavor.get('format')
            flavor_url = flavor.get('url')
            if not flavor_url or not re.match(r'https?://', flavor_url) or flavor_format == 'mp4_access':
                continue
            tbr = int_or_none(flavor.get('bitrate'))
            if tbr == 99999:
                # wrong ks(Kaltura Signature) causes 404 Error
                flavor_url = update_url_query(flavor_url, {'ks': ''})
                m3u8_formats = self._extract_m3u8_formats(
                    flavor_url, video_id, 'mp4',
                    m3u8_id=flavor_format, fatal=False)
                for f in m3u8_formats:
                    # Apple FairPlay
                    if '/fpshls/' in f['url']:
                        continue
                    formats.append(f)
                continue
            format_id = []
            if flavor_format:
                format_id.append(flavor_format)
            if tbr:
                format_id.append(compat_str(tbr))
            ext = determine_ext(flavor_url)
            if flavor_format == 'applehttp' or ext == 'm3u8':
                ext = 'mp4'
            width = int_or_none(flavor.get('width'))
            height = int_or_none(flavor.get('height'))
            formats.append({
                'format_id': '-'.join(format_id),
                'url': flavor_url,
                'width': width,
                'height': height,
                'tbr': tbr,
                'ext': ext,
                'vcodec': 'none' if (width == 0 and height == 0) else None,
            })
        if not formats and video_data.get('expired'):
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, page_data['translations']['video_expired']),
                expected=True)
        self._sort_formats(formats)

        subtitles = {}
        for caption in video_data.get('captions', []):
            caption_url = caption.get('url')
            caption_format = caption.get('format')
            if not caption_url or caption_format.startswith('unknown'):
                continue
            subtitles.setdefault(caption.get('language', 'en'), []).append({
                'url': caption_url,
                'ext': {
                    'webvtt': 'vtt',
                }.get(caption_format, caption_format),
            })

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description') or video_data.get('short_desc'),
            'thumbnail': video_data.get('thumb') or video_data.get('thumb_secure'),
            'duration': int_or_none(video_data.get('duration_sec')),
            'upload_date': unified_strdate(video_data.get('publish_date')),
            'formats': formats,
            'subtitles': subtitles,
        }
