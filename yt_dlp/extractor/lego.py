# coding: utf-8
from __future__ import unicode_literals

import re
import uuid

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
)


class LEGOIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lego\.com/(?P<locale>[a-z]{2}-[a-z]{2})/(?:[^/]+/)*videos/(?:[^/]+/)*[^/?#]+-(?P<id>[0-9a-f]{32})'
    _TESTS = [{
        'url': 'http://www.lego.com/en-us/videos/themes/club/blocumentary-kawaguchi-55492d823b1b4d5e985787fa8c2973b1',
        'md5': 'f34468f176cfd76488767fc162c405fa',
        'info_dict': {
            'id': '55492d82-3b1b-4d5e-9857-87fa8c2973b1_en-US',
            'ext': 'mp4',
            'title': 'Blocumentary Great Creations: Akiyuki Kawaguchi',
            'description': 'Blocumentary Great Creations: Akiyuki Kawaguchi',
        },
    }, {
        # geo-restricted but the contentUrl contain a valid url
        'url': 'http://www.lego.com/nl-nl/videos/themes/nexoknights/episode-20-kingdom-of-heroes-13bdc2299ab24d9685701a915b3d71e7##sp=399',
        'md5': 'c7420221f7ffd03ff056f9db7f8d807c',
        'info_dict': {
            'id': '13bdc229-9ab2-4d96-8570-1a915b3d71e7_nl-NL',
            'ext': 'mp4',
            'title': 'Aflevering 20:  Helden van het koninkrijk',
            'description': 'md5:8ee499aac26d7fa8bcb0cedb7f9c3941',
            'age_limit': 5,
        },
    }, {
        # with subtitle
        'url': 'https://www.lego.com/nl-nl/kids/videos/classic/creative-storytelling-the-little-puppy-aa24f27c7d5242bc86102ebdc0f24cba',
        'info_dict': {
            'id': 'aa24f27c-7d52-42bc-8610-2ebdc0f24cba_nl-NL',
            'ext': 'mp4',
            'title': 'De kleine puppy',
            'description': 'md5:5b725471f849348ac73f2e12cfb4be06',
            'age_limit': 1,
            'subtitles': {
                'nl': [{
                    'ext': 'srt',
                    'url': r're:^https://.+\.srt$',
                }],
            },
        },
        'params': {
            'skip_download': True,
        },
    }]
    _QUALITIES = {
        'Lowest': (64, 180, 320),
        'Low': (64, 270, 480),
        'Medium': (96, 360, 640),
        'High': (128, 540, 960),
        'Highest': (128, 720, 1280),
    }

    def _real_extract(self, url):
        locale, video_id = re.match(self._VALID_URL, url).groups()
        countries = [locale.split('-')[1].upper()]
        self._initialize_geo_bypass({
            'countries': countries,
        })

        try:
            item = self._download_json(
                # https://contentfeed.services.lego.com/api/v2/item/[VIDEO_ID]?culture=[LOCALE]&contentType=Video
                'https://services.slingshot.lego.com/mediaplayer/v2',
                video_id, query={
                    'videoId': '%s_%s' % (uuid.UUID(video_id), locale),
                }, headers=self.geo_verification_headers())
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 451:
                self.raise_geo_restricted(countries=countries)
            raise

        video = item['Video']
        video_id = video['Id']
        title = video['Title']

        q = qualities(['Lowest', 'Low', 'Medium', 'High', 'Highest'])
        formats = []
        for video_source in item.get('VideoFormats', []):
            video_source_url = video_source.get('Url')
            if not video_source_url:
                continue
            video_source_format = video_source.get('Format')
            if video_source_format == 'F4M':
                formats.extend(self._extract_f4m_formats(
                    video_source_url, video_id,
                    f4m_id=video_source_format, fatal=False))
            elif video_source_format == 'M3U8':
                formats.extend(self._extract_m3u8_formats(
                    video_source_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=video_source_format, fatal=False))
            else:
                video_source_quality = video_source.get('Quality')
                format_id = []
                for v in (video_source_format, video_source_quality):
                    if v:
                        format_id.append(v)
                f = {
                    'format_id': '-'.join(format_id),
                    'quality': q(video_source_quality),
                    'url': video_source_url,
                }
                quality = self._QUALITIES.get(video_source_quality)
                if quality:
                    f.update({
                        'abr': quality[0],
                        'height': quality[1],
                        'width': quality[2],
                    }),
                formats.append(f)
        self._sort_formats(formats)

        subtitles = {}
        sub_file_id = video.get('SubFileId')
        if sub_file_id and sub_file_id != '00000000-0000-0000-0000-000000000000':
            net_storage_path = video.get('NetstoragePath')
            invariant_id = video.get('InvariantId')
            video_file_id = video.get('VideoFileId')
            video_version = video.get('VideoVersion')
            if net_storage_path and invariant_id and video_file_id and video_version:
                subtitles.setdefault(locale[:2], []).append({
                    'url': 'https://lc-mediaplayerns-live-s.legocdn.com/public/%s/%s_%s_%s_%s_sub.srt' % (net_storage_path, invariant_id, video_file_id, locale, video_version),
                })

        return {
            'id': video_id,
            'title': title,
            'description': video.get('Description'),
            'thumbnail': video.get('GeneratedCoverImage') or video.get('GeneratedThumbnail'),
            'duration': int_or_none(video.get('Length')),
            'formats': formats,
            'subtitles': subtitles,
            'age_limit': int_or_none(video.get('AgeFrom')),
            'season': video.get('SeasonTitle'),
            'season_number': int_or_none(video.get('Season')) or None,
            'episode_number': int_or_none(video.get('Episode')) or None,
        }
