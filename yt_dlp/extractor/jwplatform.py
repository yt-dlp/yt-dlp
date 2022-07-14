import re
from ..utils import (
    ExtractorError,
    js_to_json,
    unsmuggle_url,
)
from .common import InfoExtractor


class JWPlatformIE(InfoExtractor):
    _VALID_URL = r'(?:https?://(?:content\.jwplatform|cdn\.jwplayer)\.com/(?:(?:feed|player|thumb|preview|manifest)s|jw6|v2/media)/|jwplatform:)(?P<id>[a-zA-Z0-9]{8})'
    _TESTS = [{
        'url': 'http://content.jwplatform.com/players/nPripu9l-ALJ3XQCI.js',
        'md5': '3aa16e4f6860e6e78b7df5829519aed3',
        'info_dict': {
            'id': 'nPripu9l',
            'ext': 'mp4',
            'title': 'Big Buck Bunny Trailer',
            'description': 'Big Buck Bunny is a short animated film by the Blender Institute. It is made using free and open source software.',
            'upload_date': '20081127',
            'timestamp': 1227796140,
            'duration': 32.0,
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/nPripu9l/poster.jpg?width=720',
        }
    }, {
        'url': 'https://cdn.jwplayer.com/players/nPripu9l-ALJ3XQCI.js',
        'only_matching': True,
    }]

    _WEBPAGE_TESTS = [
        {
            # JWPlatform iframe
            'url': 'https://www.covermagazine.co.uk/feature/2465255/business-protection-involved',
            'info_dict': {
                'id': 'AG26UQXM',
                'ext': 'mp4',
                'upload_date': '20160719',
                'timestamp': 1468923808,
                'title': '2016_05_18 Cover L&G Business Protection V1 FINAL.mp4',
                'thumbnail': 'https://cdn.jwplayer.com/v2/media/AG26UQXM/poster.jpg?width=720',
                'description': '',
                'duration': 294.0,

            },
        },
        {
            'url': 'https://www.skimag.com/video/ski-people-1980/',
            'info_dict': {
                'id': 'ski-people-1980',
                'title': 'Ski People (1980)',
                'description': '1980\'s Ski People',
                'thumbnail': 'https://www.skimag.com/wp-content/uploads/2021/01/WME_SkiPeople.jpg?width=1200',
                'age_limit': 0,

            },
            'playlist_count': 1,
            'playlist': [{
                'md5': '022a7e31c70620ebec18deeab376ee03',
                'info_dict': {
                    'id': 'YTmgRiNU',
                    'ext': 'mp4',
                    'title': '1980 Ski People',
                    'timestamp': 1610407738,
                    'description': 'md5:cf9c3d101452c91e141f292b19fe4843',
                    'thumbnail': 'https://cdn.jwplayer.com/v2/media/YTmgRiNU/poster.jpg?width=720',
                    'duration': 5688.0,
                    'upload_date': '20210111',
                }
            }]
        },
    ]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for tag, key in ((r'(?:script|iframe)', 'src'), ('input', 'value')):
            # <input value=URL> is used by hyland.com
            # if we find <iframe>, dont look for <input>
            ret = re.findall(
                r'<%s[^>]+?%s=["\']((?:https?:)?//(?:content\.jwplatform|cdn\.jwplayer)\.com/players/[a-zA-Z0-9]{8})' % (tag, key),
                webpage)
            if ret:
                return ret
        mobj = re.search(r'<div\b[^>]* data-video-jw-id="([a-zA-Z0-9]{8})"', webpage)
        if mobj:
            return [f'jwplatform:{mobj.group(1)}']

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        self._initialize_geo_bypass({
            'countries': smuggled_data.get('geo_countries'),
        })
        video_id = self._match_id(url)
        json_data = self._download_json('https://cdn.jwplayer.com/v2/media/' + video_id, video_id)
        return self._parse_jwplayer_data(json_data, video_id)


class JWPlayerEmbedIE(InfoExtractor):
    _VALID_URL = False
    IE_NAME = 'jwplayer'

    _WEBPAGE_TESTS = [
        # jwplayer YouTube
        {
            'url': 'http://media.nationalarchives.gov.uk/index.php/webinar-using-discovery-national-archives-online-catalogue/',
            'info_dict': {
                'id': 'Mrj4DVp2zeA',
                'ext': 'mp4',
                'upload_date': '20150212',
                'uploader': 'The National Archives UK',
                'description': 'md5:a236581cd2449dd2df4f93412f3f01c6',
                'uploader_id': 'NationalArchives08',
                'title': 'Webinar: Using Discovery, The National Archives’ online catalogue',
                'playable_in_embed': True,
                'view_count': int,
                'availability': 'public',
                'tags': ['catalogue', 'discovery', 'the national archives', 'archives', 'history'],
                'live_status': 'not_live',
                'channel_url': 'https://www.youtube.com/channel/UCUuzebc1yADDJEnOLA5P9xw',
                'like_count': int,
                'channel_follower_count': int,
                'channel': 'The National Archives UK',
                'categories': ['Education'],
                'uploader_url': 'http://www.youtube.com/user/NationalArchives08',
                'age_limit': 0,
                'duration': 3066,
                'thumbnail': 'https://media.nationalarchives.gov.uk/files/2015/01/discovery.jpg',
                'channel_id': 'UCUuzebc1yADDJEnOLA5P9xw',
            },
        },
        {
            # no title in jw player data
            # FIXME, why is this failing?!?
            'url': 'http://www.hodiho.fr/2013/02/regis-plante-sa-jeep.html',
            'md5': '85b90ccc9d73b4acd9138d3af4c27f89',
            'info_dict': {
                'id': 'regis-plante-sa-jeep',
                'ext': 'mp4',
                'thumbnail': 'http://www.hodiho.fr/wp-content/files_flutter/1360133825image.jpg',
                'title': 'hodiho » Blog Archive » Régis plante sa Jeep',

            }
        },
    ]

    def _extract_from_webpage(self, url, webpage):
        video_id = self._generic_id(url)
        jwplayer_data = self._find_jwplayer_data(
            webpage, video_id, transform_source=js_to_json)
        if not jwplayer_data:
            return

        # JW Playlist
        if isinstance(jwplayer_data.get('playlist'), str):
            yield {
                '_type': 'url',
                'ie_key': 'JWPlatform',
                'url': jwplayer_data['playlist'],
            }
            return

        # JW Player data
        try:
            info = self._parse_jwplayer_data(
                jwplayer_data, video_id, require_title=False, base_url=url)
            if not info.get('title'):
                info['title'] = (
                    self._og_search_title(webpage, default=None)
                    or self._html_extract_title(webpage, 'video title', default=None)
                    or self._generic_title(url))
            yield info
        except ExtractorError:
            # See https://github.com/ytdl-org/youtube-dl/pull/16735
            pass
