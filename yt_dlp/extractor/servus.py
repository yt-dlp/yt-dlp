# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    unified_timestamp,
    urlencode_postdata,
    url_or_none,
)


class ServusIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        (?:
                            servus\.com/(?:(?:at|de)/p/[^/]+|tv/videos)|
                            (?:servustv|pm-wissen)\.com/videos
                        )
                        /(?P<id>[aA]{2}-\w+|\d+-\d+)
                    '''
    _TESTS = [{
        # new URL schema
        'url': 'https://www.servustv.com/videos/aa-1t6vbu5pw1w12/',
        'md5': '60474d4c21f3eb148838f215c37f02b9',
        'info_dict': {
            'id': 'AA-1T6VBU5PW1W12',
            'ext': 'mp4',
            'title': 'Die Grünen aus Sicht des Volkes',
            'alt_title': 'Talk im Hangar-7 Voxpops Gruene',
            'description': 'md5:1247204d85783afe3682644398ff2ec4',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 62.442,
            'timestamp': 1605193976,
            'upload_date': '20201112',
            'series': 'Talk im Hangar-7',
            'season': 'Season 9',
            'season_number': 9,
            'episode': 'Episode 31 - September 14',
            'episode_number': 31,
        }
    }, {
        # old URL schema
        'url': 'https://www.servus.com/de/p/Die-Gr%C3%BCnen-aus-Sicht-des-Volkes/AA-1T6VBU5PW1W12/',
        'only_matching': True,
    }, {
        'url': 'https://www.servus.com/at/p/Wie-das-Leben-beginnt/1309984137314-381415152/',
        'only_matching': True,
    }, {
        'url': 'https://www.servus.com/tv/videos/aa-1t6vbu5pw1w12/',
        'only_matching': True,
    }, {
        'url': 'https://www.servus.com/tv/videos/1380889096408-1235196658/',
        'only_matching': True,
    }, {
        'url': 'https://www.pm-wissen.com/videos/aa-24mus4g2w2112/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).upper()

        token = self._download_json(
            'https://auth.redbullmediahouse.com/token', video_id,
            'Downloading token', data=urlencode_postdata({
                'grant_type': 'client_credentials',
            }), headers={
                'Authorization': 'Basic SVgtMjJYNEhBNFdEM1cxMTpEdDRVSkFLd2ZOMG5IMjB1NGFBWTBmUFpDNlpoQ1EzNA==',
            })
        access_token = token['access_token']
        token_type = token.get('token_type', 'Bearer')

        video = self._download_json(
            'https://sparkle-api.liiift.io/api/v1/stv/channels/international/assets/%s' % video_id,
            video_id, 'Downloading video JSON', headers={
                'Authorization': '%s %s' % (token_type, access_token),
            })

        formats = []
        thumbnail = None
        for resource in video['resources']:
            if not isinstance(resource, dict):
                continue
            format_url = url_or_none(resource.get('url'))
            if not format_url:
                continue
            extension = resource.get('extension')
            type_ = resource.get('type')
            if extension == 'jpg' or type_ == 'reference_keyframe':
                thumbnail = format_url
                continue
            ext = determine_ext(format_url)
            if type_ == 'dash' or ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    format_url, video_id, mpd_id='dash', fatal=False))
            elif type_ == 'hls' or ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            elif extension == 'mp4' or ext == 'mp4':
                formats.append({
                    'url': format_url,
                    'format_id': type_,
                    'width': int_or_none(resource.get('width')),
                    'height': int_or_none(resource.get('height')),
                })
        self._sort_formats(formats)

        attrs = {}
        for attribute in video['attributes']:
            if not isinstance(attribute, dict):
                continue
            key = attribute.get('fieldKey')
            value = attribute.get('fieldValue')
            if not key or not value:
                continue
            attrs[key] = value

        title = attrs.get('title_stv') or video_id
        alt_title = attrs.get('title')
        description = attrs.get('long_description') or attrs.get('short_description')
        series = attrs.get('label')
        season = attrs.get('season')
        episode = attrs.get('chapter')
        duration = float_or_none(attrs.get('duration'), scale=1000)
        season_number = int_or_none(self._search_regex(
            r'Season (\d+)', season or '', 'season number', default=None))
        episode_number = int_or_none(self._search_regex(
            r'Episode (\d+)', episode or '', 'episode number', default=None))

        return {
            'id': video_id,
            'title': title,
            'alt_title': alt_title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': unified_timestamp(video.get('lastPublished')),
            'series': series,
            'season': season,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'formats': formats,
        }
