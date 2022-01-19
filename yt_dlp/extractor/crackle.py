# coding: utf-8
from __future__ import unicode_literals, division

import hashlib
import hmac
import re
import time

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    orderedSet,
    parse_age_limit,
    parse_duration,
    url_or_none,
    ExtractorError
)


class CrackleIE(InfoExtractor):
    _VALID_URL = r'(?:crackle:|https?://(?:(?:www|m)\.)?(?:sony)?crackle\.com/(?:playlist/\d+/|(?:[^/]+/)+))(?P<id>\d+)'
    _TESTS = [{
        # Crackle is available in the United States and territories
        'url': 'https://www.crackle.com/thanksgiving/2510064',
        'info_dict': {
            'id': '2510064',
            'ext': 'mp4',
            'title': 'Touch Football',
            'description': 'md5:cfbb513cf5de41e8b56d7ab756cff4df',
            'duration': 1398,
            'view_count': int,
            'average_rating': 0,
            'age_limit': 17,
            'genre': 'Comedy',
            'creator': 'Daniel Powell',
            'artist': 'Chris Elliott, Amy Sedaris',
            'release_year': 2016,
            'series': 'Thanksgiving',
            'episode': 'Touch Football',
            'season_number': 1,
            'episode_number': 1,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'expected_warnings': [
            'Trying with a list of known countries'
        ],
    }, {
        'url': 'https://www.sonycrackle.com/thanksgiving/2510064',
        'only_matching': True,
    }]

    _MEDIA_FILE_SLOTS = {
        '360p.mp4': {
            'width': 640,
            'height': 360,
        },
        '480p.mp4': {
            'width': 768,
            'height': 432,
        },
        '480p_1mbps.mp4': {
            'width': 852,
            'height': 480,
        },
    }

    def _download_json(self, url, *args, **kwargs):
        # Authorization generation algorithm is reverse engineered from:
        # https://www.sonycrackle.com/static/js/main.ea93451f.chunk.js
        timestamp = time.strftime('%Y%m%d%H%M', time.gmtime())
        h = hmac.new(b'IGSLUQCBDFHEOIFM', '|'.join([url, timestamp]).encode(), hashlib.sha1).hexdigest().upper()
        headers = {
            'Accept': 'application/json',
            'Authorization': '|'.join([h, timestamp, '117', '1']),
        }
        return InfoExtractor._download_json(self, url, *args, headers=headers, **kwargs)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        geo_bypass_country = self.get_param('geo_bypass_country', None)
        countries = orderedSet((geo_bypass_country, 'US', 'AU', 'CA', 'AS', 'FM', 'GU', 'MP', 'PR', 'PW', 'MH', 'VI', ''))
        num_countries, num = len(countries) - 1, 0

        media = {}
        for num, country in enumerate(countries):
            if num == 1:  # start hard-coded list
                self.report_warning('%s. Trying with a list of known countries' % (
                    'Unable to obtain video formats from %s API' % geo_bypass_country if geo_bypass_country
                    else 'No country code was given using --geo-bypass-country'))
            elif num == num_countries:  # end of list
                geo_info = self._download_json(
                    'https://web-api-us.crackle.com/Service.svc/geo/country',
                    video_id, fatal=False, note='Downloading geo-location information from crackle API',
                    errnote='Unable to fetch geo-location information from crackle') or {}
                country = geo_info.get('CountryCode')
                if country is None:
                    continue
                self.to_screen('%s identified country as %s' % (self.IE_NAME, country))
                if country in countries:
                    self.to_screen('Downloading from %s API was already attempted. Skipping...' % country)
                    continue

            if country is None:
                continue
            try:
                media = self._download_json(
                    'https://web-api-us.crackle.com/Service.svc/details/media/%s/%s?disableProtocols=true' % (video_id, country),
                    video_id, note='Downloading media JSON from %s API' % country,
                    errnote='Unable to download media JSON')
            except ExtractorError as e:
                # 401 means geo restriction, trying next country
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                    continue
                raise

            status = media.get('status')
            if status.get('messageCode') != '0':
                raise ExtractorError(
                    '%s said: %s %s - %s' % (
                        self.IE_NAME, status.get('messageCodeDescription'), status.get('messageCode'), status.get('message')),
                    expected=True)

            # Found video formats
            if isinstance(media.get('MediaURLs'), list):
                break

        ignore_no_formats = self.get_param('ignore_no_formats_error')

        if not media or (not media.get('MediaURLs') and not ignore_no_formats):
            raise ExtractorError(
                'Unable to access the crackle API. Try passing your country code '
                'to --geo-bypass-country. If it still does not work and the '
                'video is available in your country')
        title = media['Title']

        formats, subtitles = [], {}
        has_drm = False
        for e in media.get('MediaURLs') or []:
            if e.get('UseDRM'):
                has_drm = True
                format_url = url_or_none(e.get('DRMPath'))
            else:
                format_url = url_or_none(e.get('Path'))
            if not format_url:
                continue
            ext = determine_ext(format_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    format_url, video_id, mpd_id='dash', fatal=False)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            elif format_url.endswith('.ism/Manifest'):
                fmts, subs = self._extract_ism_formats_and_subtitles(
                    format_url, video_id, ism_id='mss', fatal=False)
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
            else:
                mfs_path = e.get('Type')
                mfs_info = self._MEDIA_FILE_SLOTS.get(mfs_path)
                if not mfs_info:
                    continue
                formats.append({
                    'url': format_url,
                    'format_id': 'http-' + mfs_path.split('.')[0],
                    'width': mfs_info['width'],
                    'height': mfs_info['height'],
                })
        if not formats and has_drm:
            self.report_drm(video_id)
        self._sort_formats(formats)

        description = media.get('Description')
        duration = int_or_none(media.get(
            'DurationInSeconds')) or parse_duration(media.get('Duration'))
        view_count = int_or_none(media.get('CountViews'))
        average_rating = float_or_none(media.get('UserRating'))
        age_limit = parse_age_limit(media.get('Rating'))
        genre = media.get('Genre')
        release_year = int_or_none(media.get('ReleaseYear'))
        creator = media.get('Directors')
        artist = media.get('Cast')

        if media.get('MediaTypeDisplayValue') == 'Full Episode':
            series = media.get('ShowName')
            episode = title
            season_number = int_or_none(media.get('Season'))
            episode_number = int_or_none(media.get('Episode'))
        else:
            series = episode = season_number = episode_number = None

        cc_files = media.get('ClosedCaptionFiles')
        if isinstance(cc_files, list):
            for cc_file in cc_files:
                if not isinstance(cc_file, dict):
                    continue
                cc_url = url_or_none(cc_file.get('Path'))
                if not cc_url:
                    continue
                lang = cc_file.get('Locale') or 'en'
                subtitles.setdefault(lang, []).append({'url': cc_url})

        thumbnails = []
        images = media.get('Images')
        if isinstance(images, list):
            for image_key, image_url in images.items():
                mobj = re.search(r'Img_(\d+)[xX](\d+)', image_key)
                if not mobj:
                    continue
                thumbnails.append({
                    'url': image_url,
                    'width': int(mobj.group(1)),
                    'height': int(mobj.group(2)),
                })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'duration': duration,
            'view_count': view_count,
            'average_rating': average_rating,
            'age_limit': age_limit,
            'genre': genre,
            'creator': creator,
            'artist': artist,
            'release_year': release_year,
            'series': series,
            'episode': episode,
            'season_number': season_number,
            'episode_number': episode_number,
            'thumbnails': thumbnails,
            'subtitles': subtitles,
            'formats': formats,
        }
