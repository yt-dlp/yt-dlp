import base64
import json
import re
import urllib.parse
import xml.etree.ElementTree

from .adobepass import AdobePassIE
from .common import InfoExtractor
from .theplatform import ThePlatformBaseIE, ThePlatformIE, default_ns
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    RegexNotFoundError,
    UserNotLive,
    clean_html,
    determine_ext,
    extract_attributes,
    float_or_none,
    get_element_html_by_class,
    int_or_none,
    join_nonempty,
    make_archive_id,
    mimetype2ext,
    parse_age_limit,
    parse_duration,
    parse_iso8601,
    remove_end,
    try_get,
    unescapeHTML,
    unified_timestamp,
    update_url_query,
    url_basename,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class NBCUniversalBaseIE(ThePlatformBaseIE):
    _GEO_COUNTRIES = ['US']
    _GEO_BYPASS = False
    _M3U8_RE = r'https?://[^/?#]+/prod/[\w-]+/(?P<folders>[^?#]+/)cmaf/mpeg_(?:cbcs|cenc)\w*/master_cmaf\w*\.m3u8'

    def _download_nbcu_smil_and_extract_m3u8_url(self, tp_path, video_id, query):
        smil = self._download_xml(
            f'https://link.theplatform.com/s/{tp_path}', video_id,
            'Downloading SMIL manifest', 'Failed to download SMIL manifest', query={
                **query,
                'format': 'SMIL',  # XXX: Do not confuse "format" with "formats"
                'manifest': 'm3u',
                'switch': 'HLSServiceSecure',  # Or else we get broken mp4 http URLs instead of HLS
            }, headers=self.geo_verification_headers())

        ns = f'//{{{default_ns}}}'
        if url := traverse_obj(smil, (f'{ns}video/@src', lambda _, v: determine_ext(v) == 'm3u8', any)):
            return url

        exc = traverse_obj(smil, (f'{ns}param', lambda _, v: v.get('name') == 'exception', '@value', any))
        if exc == 'GeoLocationBlocked':
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
        raise ExtractorError(traverse_obj(smil, (f'{ns}ref/@abstract', ..., any)), expected=exc == 'Expired')

    def _extract_nbcu_formats_and_subtitles(self, tp_path, video_id, query):
        # formats='mpeg4' will return either a working m3u8 URL or an m3u8 template for non-DRM HLS
        # formats='m3u+none,mpeg4' may return DRM HLS but w/the "folders" needed for non-DRM template
        query['formats'] = 'm3u+none,mpeg4'
        orig_m3u8_url = m3u8_url = self._download_nbcu_smil_and_extract_m3u8_url(tp_path, video_id, query)

        if mobj := re.fullmatch(self._M3U8_RE, m3u8_url):
            query['formats'] = 'mpeg4'
            m3u8_tmpl = self._download_nbcu_smil_and_extract_m3u8_url(tp_path, video_id, query)
            # Example: https://vod-lf-oneapp-prd.akamaized.net/prod/video/{folders}master_hls.m3u8
            if '{folders}' in m3u8_tmpl:
                self.write_debug('Found m3u8 URL template, formatting URL path')
            m3u8_url = m3u8_tmpl.format(folders=mobj.group('folders'))

        if '/mpeg_cenc' in m3u8_url or '/mpeg_cbcs' in m3u8_url:
            self.report_drm(video_id)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, 'mp4', m3u8_id='hls', fatal=False)

        if not formats and m3u8_url != orig_m3u8_url:
            orig_fmts, subtitles = self._extract_m3u8_formats_and_subtitles(
                orig_m3u8_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            formats = [f for f in orig_fmts if not f.get('has_drm')]
            if orig_fmts and not formats:
                self.report_drm(video_id)

        return formats, subtitles

    def _extract_nbcu_video(self, url, display_id, old_ie_key=None):
        webpage = self._download_webpage(url, display_id)
        settings = self._search_json(
            r'<script[^>]+data-drupal-selector="drupal-settings-json"[^>]*>',
            webpage, 'settings', display_id)

        query = {}
        tve = extract_attributes(get_element_html_by_class('tve-video-deck-app', webpage) or '')
        if tve:
            account_pid = tve.get('data-mpx-media-account-pid') or tve['data-mpx-account-pid']
            account_id = tve['data-mpx-media-account-id']
            metadata = self._parse_json(
                tve.get('data-normalized-video') or '', display_id, fatal=False, transform_source=unescapeHTML)
            video_id = tve.get('data-guid') or metadata['guid']
            if tve.get('data-entitlement') == 'auth':
                auth = settings['tve_adobe_auth']
                release_pid = tve['data-release-pid']
                resource = self._get_mvpd_resource(
                    tve.get('data-adobe-pass-resource-id') or auth['adobePassResourceId'],
                    tve['data-title'], release_pid, tve.get('data-rating'))
                query['auth'] = self._extract_mvpd_auth(
                    url, release_pid, auth['adobePassRequestorId'],
                    resource, auth['adobePassSoftwareStatement'])
        else:
            ls_playlist = traverse_obj(settings, (
                'ls_playlist', lambda _, v: v['defaultGuid'], any, {require('LS playlist')}))
            video_id = ls_playlist['defaultGuid']
            account_pid = ls_playlist.get('mpxMediaAccountPid') or ls_playlist['mpxAccountPid']
            account_id = ls_playlist['mpxMediaAccountId']
            metadata = traverse_obj(ls_playlist, ('videos', lambda _, v: v['guid'] == video_id, any)) or {}

        tp_path = f'{account_pid}/media/guid/{account_id}/{video_id}'
        formats, subtitles = self._extract_nbcu_formats_and_subtitles(tp_path, video_id, query)
        tp_metadata = self._download_theplatform_metadata(tp_path, video_id, fatal=False)
        parsed_info = self._parse_theplatform_metadata(tp_metadata)
        self._merge_subtitles(parsed_info['subtitles'], target=subtitles)

        return {
            **parsed_info,
            **traverse_obj(metadata, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'duration': ('durationInSeconds', {int_or_none}),
                'timestamp': ('airDate', {parse_iso8601}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'episode': ('episodeTitle', {str}),
                'series': ('show', {str}),
            }),
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            '_old_archive_ids': [make_archive_id(old_ie_key, video_id)] if old_ie_key else None,
        }


class NBCIE(NBCUniversalBaseIE):
    _VALID_URL = r'https?(?P<permalink>://(?:www\.)?nbc\.com/(?:classic-tv/)?[^/?#]+/video/[^/?#]+/(?P<id>\w+))'
    _TESTS = [{
        'url': 'http://www.nbc.com/the-tonight-show/video/jimmy-fallon-surprises-fans-at-ben-jerrys/2848237',
        'info_dict': {
            'id': '2848237',
            'ext': 'mp4',
            'title': 'Jimmy Fallon Surprises Fans at Ben & Jerry\'s',
            'description': 'Jimmy gives out free scoops of his new "Tonight Dough" ice cream flavor by surprising customers at the Ben & Jerry\'s scoop shop.',
            'timestamp': 1424246400,
            'upload_date': '20150218',
            'uploader': 'NBCU-COM',
            'episode': 'Jimmy Fallon Surprises Fans at Ben & Jerry\'s',
            'episode_number': 86,
            'season': 'Season 2',
            'season_number': 2,
            'series': 'Tonight',
            'duration': 236.504,
            'tags': 'count:2',
            'thumbnail': r're:https?://.+\.jpg',
            'categories': ['Series/The Tonight Show Starring Jimmy Fallon'],
            'media_type': 'Full Episode',
            'age_limit': 14,
            '_old_archive_ids': ['theplatform 2848237'],
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.nbc.com/the-golden-globe-awards/video/oprah-winfrey-receives-cecil-b-de-mille-award-at-the-2018-golden-globes/3646439',
        'info_dict': {
            'id': '3646439',
            'ext': 'mp4',
            'title': 'Oprah Winfrey Receives Cecil B. de Mille Award at the 2018 Golden Globes',
            'episode': 'Oprah Winfrey Receives Cecil B. de Mille Award at the 2018 Golden Globes',
            'episode_number': 1,
            'season': 'Season 75',
            'season_number': 75,
            'series': 'Golden Globes',
            'description': 'Oprah Winfrey receives the Cecil B. de Mille Award at the 75th Annual Golden Globe Awards.',
            'uploader': 'NBCU-COM',
            'upload_date': '20180107',
            'timestamp': 1515312000,
            'duration': 569.703,
            'tags': 'count:8',
            'thumbnail': r're:https?://.+\.jpg',
            'media_type': 'Highlight',
            'age_limit': 0,
            'categories': ['Series/The Golden Globe Awards'],
            '_old_archive_ids': ['theplatform 3646439'],
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # Needs to be extracted from webpage instead of GraphQL
        'url': 'https://www.nbc.com/paris2024/video/ali-truwit-found-purpose-pool-after-her-life-changed/para24_sww_alitruwittodayshow_240823',
        'info_dict': {
            'id': 'para24_sww_alitruwittodayshow_240823',
            'ext': 'mp4',
            'title': 'Ali Truwit found purpose in the pool after her life changed',
            'description': 'md5:c16d7489e1516593de1cc5d3f39b9bdb',
            'uploader': 'NBCU-SPORTS',
            'duration': 311.077,
            'thumbnail': r're:https?://.+\.jpg',
            'episode': 'Ali Truwit found purpose in the pool after her life changed',
            'timestamp': 1724435902.0,
            'upload_date': '20240823',
            '_old_archive_ids': ['theplatform para24_sww_alitruwittodayshow_240823'],
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.nbc.com/quantum-leap/video/bens-first-leap-nbcs-quantum-leap/NBCE125189978',
        'only_matching': True,
    }, {
        'url': 'https://www.nbc.com/classic-tv/charles-in-charge/video/charles-in-charge-pilot/n3310',
        'only_matching': True,
    }, {
        # Percent escaped url
        'url': 'https://www.nbc.com/up-all-night/video/day-after-valentine%27s-day/n2189',
        'only_matching': True,
    }]
    _SOFTWARE_STATEMENT = 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI1Yzg2YjdkYy04NDI3LTRjNDUtOGQwZi1iNDkzYmE3MmQwYjQiLCJuYmYiOjE1Nzg3MDM2MzEsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTc4NzAzNjMxfQ.QQKIsBhAjGQTMdAqRTqhcz2Cddr4Y2hEjnSiOeKKki4nLrkDOsjQMmqeTR0hSRarraxH54wBgLvsxI7LHwKMvr7G8QpynNAxylHlQD3yhN9tFhxt4KR5wW3as02B-W2TznK9bhNWPKIyHND95Uo2Mi6rEQoq8tM9O09WPWaanE5BX_-r6Llr6dPq5F0Lpx2QOn2xYRb1T4nFxdFTNoss8GBds8OvChTiKpXMLHegLTc1OS4H_1a8tO_37jDwSdJuZ8iTyRLV4kZ2cpL6OL5JPMObD4-HQiec_dfcYgMKPiIfP9ZqdXpec2SVaCLsWEk86ZYvD97hLIQrK5rrKd1y-A'

    def _real_extract(self, url):
        permalink, video_id = self._match_valid_url(url).groups()
        permalink = 'http' + urllib.parse.unquote(permalink)
        video_data = self._download_json(
            'https://friendship.nbc.co/v2/graphql', video_id, query={
                'query': '''query bonanzaPage(
  $app: NBCUBrands! = nbc
  $name: String!
  $oneApp: Boolean
  $platform: SupportedPlatforms! = web
  $type: EntityPageType! = VIDEO
  $userId: String!
) {
  bonanzaPage(
    app: $app
    name: $name
    oneApp: $oneApp
    platform: $platform
    type: $type
    userId: $userId
  ) {
    metadata {
      ... on VideoPageData {
        description
        episodeNumber
        keywords
        locked
        mpxAccountId
        mpxGuid
        rating
        resourceId
        seasonNumber
        secondaryTitle
        seriesShortTitle
      }
    }
  }
}''',
                'variables': json.dumps({
                    'name': permalink,
                    'oneApp': True,
                    'userId': '0',
                }),
            })['data']['bonanzaPage']['metadata']

        if not video_data:
            # Some videos are not available via GraphQL API
            webpage = self._download_webpage(url, video_id)
            video_data = self._search_json(
                r'<script>\s*PRELOAD\s*=', webpage, 'video data',
                video_id)['pages'][urllib.parse.urlparse(url).path]['base']['metadata']

        video_id = video_data['mpxGuid']
        tp_path = f'NnzsPC/media/guid/{video_data["mpxAccountId"]}/{video_id}'
        tpm = self._download_theplatform_metadata(tp_path, video_id, fatal=False)
        title = traverse_obj(tpm, ('title', {str})) or video_data.get('secondaryTitle')
        query = {}
        if video_data.get('locked'):
            resource = self._get_mvpd_resource(
                video_data['resourceId'], title, video_id, video_data.get('rating'))
            query['auth'] = self._extract_mvpd_auth(
                url, video_id, 'nbcentertainment', resource, self._SOFTWARE_STATEMENT)

        formats, subtitles = self._extract_nbcu_formats_and_subtitles(tp_path, video_id, query)
        parsed_info = self._parse_theplatform_metadata(tpm)
        self._merge_subtitles(parsed_info['subtitles'], target=subtitles)

        return {
            **traverse_obj(video_data, {
                'description': ('description', {str}, filter),
                'episode': ('secondaryTitle', {str}, filter),
                'episode_number': ('episodeNumber', {int_or_none}),
                'season_number': ('seasonNumber', {int_or_none}),
                'age_limit': ('rating', {parse_age_limit}),
                'tags': ('keywords', ..., {str}, filter, all, filter),
                'series': ('seriesShortTitle', {str}),
            }),
            **parsed_info,
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            '_old_archive_ids': [make_archive_id('ThePlatform', video_id)],
        }


class NBCSportsVPlayerIE(InfoExtractor):
    _WORKING = False
    _VALID_URL_BASE = r'https?://(?:vplayer\.nbcsports\.com|(?:www\.)?nbcsports\.com/vplayer)/'
    _VALID_URL = _VALID_URL_BASE + r'(?:[^/]+/)+(?P<id>[0-9a-zA-Z_]+)'
    _EMBED_REGEX = [rf'(?:iframe[^>]+|var video|div[^>]+data-(?:mpx-)?)[sS]rc\s?=\s?"(?P<url>{_VALID_URL_BASE}[^\"]+)']

    _TESTS = [{
        'url': 'https://vplayer.nbcsports.com/p/BxmELC/nbcsports_embed/select/9CsDKds0kvHI',
        'info_dict': {
            'id': '9CsDKds0kvHI',
            'ext': 'mp4',
            'description': 'md5:df390f70a9ba7c95ff1daace988f0d8d',
            'title': 'Tyler Kalinoski hits buzzer-beater to lift Davidson',
            'timestamp': 1426270238,
            'upload_date': '20150313',
            'uploader': 'NBCU-SPORTS',
            'duration': 72.818,
            'chapters': [],
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'https://vplayer.nbcsports.com/p/BxmELC/nbcsports_embed/select/media/PEgOtlNcC_y2',
        'only_matching': True,
    }, {
        'url': 'https://www.nbcsports.com/vplayer/p/BxmELC/nbcsports/select/PHJSaFWbrTY9?form=html&autoPlay=true',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        theplatform_url = self._html_search_regex(r'tp:releaseUrl="(.+?)"', webpage, 'url')
        return self.url_result(theplatform_url, 'ThePlatform')


class NBCSportsIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?nbcsports\.com//?(?!vplayer/)(?:[^/]+/)+(?P<id>[0-9a-z-]+)'

    _TESTS = [{
        # iframe src
        'url': 'https://www.nbcsports.com/watch/nfl/profootballtalk/pft-pm/unpacking-addisons-reckless-driving-citation',
        'info_dict': {
            'id': 'PHJSaFWbrTY9',
            'ext': 'mp4',
            'title': 'Tom Izzo, Michigan St. has \'so much respect\' for Duke',
            'description': 'md5:ecb459c9d59e0766ac9c7d5d0eda8113',
            'uploader': 'NBCU-SPORTS',
            'upload_date': '20150330',
            'timestamp': 1427726529,
            'chapters': [],
            'thumbnail': 'https://hdliveextra-a.akamaihd.net/HD/image_sports/NBCU_Sports_Group_-_nbcsports/253/303/izzodps.jpg',
            'duration': 528.395,
        },
    }, {
        # data-mpx-src
        'url': 'https://www.nbcsports.com/philadelphia/philadelphia-phillies/bruce-bochy-hector-neris-hes-idiot',
        'only_matching': True,
    }, {
        # data-src
        'url': 'https://www.nbcsports.com/boston/video/report-card-pats-secondary-no-match-josh-allen',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'http://www.riderfans.com/forum/showthread.php?121827-Freeman&s=e98fa1ea6dc08e886b1678d35212494a',
        'info_dict': {
            'id': 'ln7x1qSThw4k',
            'ext': 'flv',
            'title': "PFT Live: New leader in the 'new-look' defense",
        },
        'skip': 'Invalid URL',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        return self.url_result(
            NBCSportsVPlayerIE._extract_url(webpage), 'NBCSportsVPlayer')


class NBCSportsStreamIE(AdobePassIE):
    _WORKING = False
    _VALID_URL = r'https?://stream\.nbcsports\.com/.+?\bpid=(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://stream.nbcsports.com/nbcsn/generic?pid=206559',
        'info_dict': {
            'id': '206559',
            'ext': 'mp4',
            'title': 'Amgen Tour of California Women\'s Recap',
            'description': 'md5:66520066b3b5281ada7698d0ea2aa894',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'Requires Adobe Pass Authentication',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        live_source = self._download_json(
            f'http://stream.nbcsports.com/data/live_sources_{video_id}.json',
            video_id)
        video_source = live_source['videoSources'][0]
        title = video_source['title']
        source_url = None
        for k in ('source', 'msl4source', 'iossource', 'hlsv4'):
            sk = k + 'Url'
            source_url = video_source.get(sk) or video_source.get(sk + 'Alt')
            if source_url:
                break
        else:
            source_url = video_source['ottStreamUrl']
        is_live = video_source.get('type') == 'live' or video_source.get('status') == 'Live'
        resource = self._get_mvpd_resource('nbcsports', title, video_id, '')
        token = self._extract_mvpd_auth(url, video_id, 'nbcsports', resource, None)  # XXX: None arg needs to be software_statement
        tokenized_url = self._download_json(
            'https://token.playmakerservices.com/cdn',
            video_id, data=json.dumps({
                'requestorId': 'nbcsports',
                'pid': video_id,
                'application': 'NBCSports',
                'version': 'v1',
                'platform': 'desktop',
                'cdn': 'akamai',
                'url': video_source['sourceUrl'],
                'token': base64.b64encode(token.encode()).decode(),
                'resourceId': base64.b64encode(resource.encode()).decode(),
            }).encode())['tokenizedUrl']
        formats = self._extract_m3u8_formats(tokenized_url, video_id, 'mp4')
        return {
            'id': video_id,
            'title': title,
            'description': live_source.get('description'),
            'formats': formats,
            'is_live': is_live,
        }


class NBCNewsIE(ThePlatformIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'(?x)https?://(?:www\.)?(?:nbcnews|today|msnbc)\.com/([^/]+/)*(?:.*-)?(?P<id>[^/?]+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//www\.nbcnews\.com/widget/video-embed/[^"\']+)\1']

    _TESTS = [{
        'url': 'http://www.nbcnews.com/watch/nbcnews-com/how-twitter-reacted-to-the-snowden-interview-269389891880',
        'md5': 'fb3dcd2d7b1dd9804305fa2fc95ab610',  # md5 tends to fluctuate
        'info_dict': {
            'id': '269389891880',
            'ext': 'mp4',
            'title': 'How Twitter Reacted To The Snowden Interview',
            'description': 'md5:65a0bd5d76fe114f3c2727aa3a81fe64',
            'timestamp': 1401363060,
            'upload_date': '20140529',
            'duration': 46.0,
            'thumbnail': 'https://media-cldnry.s-nbcnews.com/image/upload/MSNBC/Components/Video/140529/p_tweet_snow_140529.jpg',
        },
    }, {
        'url': 'http://www.nbcnews.com/feature/dateline-full-episodes/full-episode-family-business-n285156',
        'md5': 'fdbf39ab73a72df5896b6234ff98518a',
        'info_dict': {
            'id': '529953347624',
            'ext': 'mp4',
            'title': 'FULL EPISODE: Family Business',
            'description': 'md5:757988edbaae9d7be1d585eb5d55cc04',
        },
        'skip': 'This page is unavailable.',
    }, {
        'url': 'http://www.nbcnews.com/nightly-news/video/nightly-news-with-brian-williams-full-broadcast-february-4-394064451844',
        'md5': '40d0e48c68896359c80372306ece0fc3',
        'info_dict': {
            'id': '394064451844',
            'ext': 'mp4',
            'title': 'Nightly News with Brian Williams Full Broadcast (February 4)',
            'description': 'md5:1c10c1eccbe84a26e5debb4381e2d3c5',
            'timestamp': 1423104900,
            'upload_date': '20150205',
            'duration': 1236.0,
            'thumbnail': 'https://media-cldnry.s-nbcnews.com/image/upload/MSNBC/Components/Video/__NEW/nn_netcast_150204.jpg',
        },
    }, {
        'url': 'http://www.nbcnews.com/business/autos/volkswagen-11-million-vehicles-could-have-suspect-software-emissions-scandal-n431456',
        'md5': 'ffb59bcf0733dc3c7f0ace907f5e3939',
        'info_dict': {
            'id': 'n431456',
            'ext': 'mp4',
            'title': "Volkswagen U.S. Chief:  We 'Totally Screwed Up'",
            'description': 'md5:d22d1281a24f22ea0880741bb4dd6301',
            'upload_date': '20150922',
            'timestamp': 1442917800,
            'duration': 37.0,
            'thumbnail': 'https://media-cldnry.s-nbcnews.com/image/upload/MSNBC/Components/Video/__NEW/x_lon_vwhorn_150922.jpg',
        },
    }, {
        'url': 'http://www.today.com/video/see-the-aurora-borealis-from-space-in-stunning-new-nasa-video-669831235788',
        'md5': '693d1fa21d23afcc9b04c66b227ed9ff',
        'info_dict': {
            'id': '669831235788',
            'ext': 'mp4',
            'title': 'See the aurora borealis from space in stunning new NASA video',
            'description': 'md5:74752b7358afb99939c5f8bb2d1d04b1',
            'upload_date': '20160420',
            'timestamp': 1461152093,
            'duration': 69.0,
            'thumbnail': 'https://media-cldnry.s-nbcnews.com/image/upload/MSNBC/Components/Video/201604/2016-04-20T11-35-09-133Z--1280x720.jpg',
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'http://www.msnbc.com/all-in-with-chris-hayes/watch/the-chaotic-gop-immigration-vote-314487875924',
        'md5': '6d236bf4f3dddc226633ce6e2c3f814d',
        'info_dict': {
            'id': '314487875924',
            'ext': 'mp4',
            'title': 'The chaotic GOP immigration vote',
            'description': 'The Republican House votes on a border bill that has no chance of getting through the Senate or signed by the President and is drawing criticism from all sides.',
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1406937606,
            'upload_date': '20140802',
            'duration': 940.0,
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'http://www.nbcnews.com/watch/dateline/full-episode--deadly-betrayal-386250819952',
        'only_matching': True,
    }, {
        # From http://www.vulture.com/2016/06/letterman-couldnt-care-less-about-late-night.html
        'url': 'http://www.nbcnews.com/widget/video-embed/701714499682',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'http://www.vulture.com/2016/06/letterman-couldnt-care-less-about-late-night.html',
        'info_dict': {
            'id': 'x_dtl_oa_LettermanliftPR_160608',
            'ext': 'mp4',
            'title': 'David Letterman: A Preview',
        },
        'skip': 'Invalid URL',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data = self._search_nextjs_data(webpage, video_id)['props']['initialState']
        video_data = try_get(data, lambda x: x['video']['current'], dict)
        if not video_data:
            video_data = data['article']['content'][0]['primaryMedia']['video']
        title = video_data['headline']['primary']

        formats = []
        for va in video_data.get('videoAssets', []):
            public_url = va.get('publicUrl')
            if not public_url:
                continue
            if '://link.theplatform.com/' in public_url:
                public_url = update_url_query(public_url, {'format': 'redirect'})
            format_id = va.get('format')
            if format_id == 'M3U':
                formats.extend(self._extract_m3u8_formats(
                    public_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=format_id, fatal=False))
                continue
            tbr = int_or_none(va.get('bitrate'), 1000)
            formats.append({
                'format_id': join_nonempty(format_id, tbr),
                'url': public_url,
                'width': int_or_none(va.get('width')),
                'height': int_or_none(va.get('height')),
                'tbr': tbr,
                'ext': 'mp4',
            })

        subtitles = {}
        closed_captioning = video_data.get('closedCaptioning')
        if closed_captioning:
            for cc_url in closed_captioning.values():
                if not cc_url:
                    continue
                subtitles.setdefault('en', []).append({
                    'url': cc_url,
                })

        return {
            'id': video_id,
            'title': title,
            'description': try_get(video_data, lambda x: x['description']['primary']),
            'thumbnail': try_get(video_data, lambda x: x['primaryImage']['url']['primary']),
            'duration': parse_duration(video_data.get('duration')),
            'timestamp': unified_timestamp(video_data.get('datePublished')),
            'formats': formats,
            'subtitles': subtitles,
        }


class NBCOlympicsIE(InfoExtractor):
    IE_NAME = 'nbcolympics'
    _VALID_URL = r'https?://www\.nbcolympics\.com/videos?/(?P<id>[0-9a-z-]+)'

    _TESTS = [{
        # Geo-restricted to US
        'url': 'https://www.nbcolympics.com/videos/watch-final-minutes-team-usas-mens-basketball-gold',
        'info_dict': {
            'id': 'SAwGfPlQ1q01',
            'ext': 'mp4',
            'display_id': 'watch-final-minutes-team-usas-mens-basketball-gold',
            'title': 'Watch the final minutes of Team USA\'s men\'s basketball gold',
            'description': 'md5:f704f591217305c9559b23b877aa8d31',
            'episode': 'Watch the final minutes of Team USA\'s men\'s basketball gold',
            'uploader': 'NBCU-SPORTS',
            'duration': 387.053,
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1723346984,
            'upload_date': '20240811',
        },
    }, {
        'url': 'http://www.nbcolympics.com/video/justin-roses-son-leo-was-tears-after-his-dad-won-gold',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        try:
            drupal_settings = self._parse_json(self._search_regex(
                r'jQuery\.extend\(Drupal\.settings\s*,\s*({.+?})\);',
                webpage, 'drupal settings'), display_id)

            iframe_url = drupal_settings['vod']['iframe_url']
            theplatform_url = iframe_url.replace(
                'vplayer.nbcolympics.com', 'player.theplatform.com')
        except RegexNotFoundError:
            theplatform_url = self._search_regex(
                r"([\"'])embedUrl\1: *([\"'])(?P<embedUrl>.+)\2",
                webpage, 'embedding URL', group='embedUrl')

        return {
            '_type': 'url_transparent',
            'url': theplatform_url,
            'ie_key': ThePlatformIE.ie_key(),
            'display_id': display_id,
        }


class NBCOlympicsStreamIE(AdobePassIE):
    _WORKING = False
    IE_NAME = 'nbcolympics:stream'
    _VALID_URL = r'https?://stream\.nbcolympics\.com/(?P<id>[0-9a-z-]+)'
    _TESTS = [{
        'note': 'Tokenized m3u8 source URL',
        'url': 'https://stream.nbcolympics.com/womens-soccer-group-round-11',
        'info_dict': {
            'id': '2019740',
            'ext': 'mp4',
            'title': r"re:Women's Group Stage - Netherlands vs\. Brazil [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$",
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'Livestream',
    }, {
        'note': 'Plain m3u8 source URL',
        'url': 'https://stream.nbcolympics.com/gymnastics-event-finals-mens-floor-pommel-horse-womens-vault-bars',
        'info_dict': {
            'id': '2021729',
            'ext': 'mp4',
            'title': r're:Event Finals: M Floor, W Vault, M Pommel, W Uneven Bars [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'Livestream',
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        pid = self._search_regex(r'pid\s*=\s*(\d+);', webpage, 'pid')

        event_config = self._download_json(
            f'http://stream.nbcolympics.com/data/event_config_{pid}.json',
            pid, 'Downloading event config')['eventConfig']

        title = event_config['eventTitle']
        is_live = {'live': True, 'replay': False}.get(event_config.get('eventStatus'))

        source_url = self._download_json(
            f'https://api-leap.nbcsports.com/feeds/assets/{pid}?application=NBCOlympics&platform=desktop&format=nbc-player&env=staging',
            pid, 'Downloading leap config',
        )['videoSources'][0]['cdnSources']['primary'][0]['sourceUrl']

        if event_config.get('cdnToken'):
            ap_resource = self._get_mvpd_resource(
                event_config.get('resourceId', 'NBCOlympics'),
                re.sub(r'[^\w\d ]+', '', event_config['eventTitle']), pid,
                event_config.get('ratingId', 'NO VALUE'))
            # XXX: The None arg below needs to be the software_statement for this requestor
            media_token = self._extract_mvpd_auth(url, pid, event_config.get('requestorId', 'NBCOlympics'), ap_resource, None)

            source_url = self._download_json(
                'https://tokens.playmakerservices.com/', pid, 'Retrieving tokenized URL',
                data=json.dumps({
                    'application': 'NBCSports',
                    'authentication-type': 'adobe-pass',
                    'cdn': 'akamai',
                    'pid': pid,
                    'platform': 'desktop',
                    'requestorId': 'NBCOlympics',
                    'resourceId': base64.b64encode(ap_resource.encode()).decode(),
                    'token': base64.b64encode(media_token.encode()).decode(),
                    'url': source_url,
                    'version': 'v1',
                }).encode(),
            )['akamai'][0]['tokenizedUrl']

        formats = self._extract_m3u8_formats(source_url, pid, 'mp4', live=is_live)
        for f in formats:
            # -http_seekable requires ffmpeg 4.3+ but it doesnt seem possible to
            # download with ffmpeg without this option
            f['downloader_options'] = {'ffmpeg_args': ['-seekable', '0', '-http_seekable', '0', '-icy', '0']}

        return {
            'id': pid,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'is_live': is_live,
        }


class NBCStationsIE(InfoExtractor):
    _DOMAIN_RE = '|'.join(map(re.escape, (
        'nbcbayarea', 'nbcboston', 'nbcchicago', 'nbcconnecticut', 'nbcdfw', 'nbclosangeles',
        'nbcmiami', 'nbcnewyork', 'nbcphiladelphia', 'nbcsandiego', 'nbcwashington',
        'necn', 'telemundo52', 'telemundoarizona', 'telemundochicago', 'telemundonuevainglaterra',
    )))
    _VALID_URL = rf'https?://(?:www\.)?(?P<site>{_DOMAIN_RE})\.com/(?:[^/?#]+/)*(?P<id>[^/?#]+)/?(?:$|[#?])'

    _TESTS = [{
        'url': 'https://www.nbclosangeles.com/news/local/large-structure-fire-in-downtown-la-prompts-smoke-odor-advisory/2968618/',
        'info_dict': {
            'id': '2968618',
            'ext': 'mp4',
            'title': 'Large Structure Fire in Downtown LA Prompts Smoke Odor Advisory',
            'description': 'md5:417ed3c2d91fe9d301e6db7b0942f182',
            'duration': 112.513,
            'timestamp': 1661135892,
            'upload_date': '20220822',
            'uploader': 'NBC 4',
            'channel_id': 'KNBC',
            'channel': 'nbclosangeles',
        },
        'skip': 'Site changed',
    }, {
        'url': 'https://www.telemundoarizona.com/responde/huracan-complica-reembolso-para-televidente-de-tucson/2247002/',
        'info_dict': {
            'id': '2247002',
            'ext': 'mp4',
            'title': 'Huracán complica que televidente de Tucson reciba  reembolso',
            'description': 'md5:af298dc73aab74d4fca6abfb12acb6cf',
            'duration': 172.406,
            'timestamp': 1660886507,
            'upload_date': '20220819',
            'uploader': 'Telemundo Arizona',
            'channel_id': 'KTAZ',
            'channel': 'telemundoarizona',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # direct mp4 link
        'url': 'https://www.nbcboston.com/weather/video-weather/highs-near-freezing-in-boston-on-wednesday/2961135/',
        'md5': '9bf8c41dc7abbb75b1a44f1491a4cc85',
        'info_dict': {
            'id': '2961135',
            'ext': 'mp4',
            'title': 'Highs Near Freezing in Boston on Wednesday',
            'description': 'md5:3ec486609a926c99f00a3512e6c0e85b',
            'duration': 235.669,
            'timestamp': 1675268656,
            'upload_date': '20230201',
            'uploader': '',
            'channel_id': 'WBTS',
            'channel': 'nbcboston',
        },
    }]

    _RESOLUTIONS = {
        '1080': '1920',
        '720': '1280',
        '540': '960',
        '360': '640',
        '234': '416',
    }

    def _real_extract(self, url):
        channel, video_id = self._match_valid_url(url).group('site', 'id')
        webpage = self._download_webpage(url, video_id)

        nbc_data = self._search_json(
            r'(?:<script>\s*var\s+nbc\s*=|Object\.assign\(nbc,)', webpage, 'NBC JSON data', video_id)
        pdk_acct = nbc_data.get('pdkAcct') or 'Yh1nAC'
        fw_ssid = traverse_obj(nbc_data, ('video', 'fwSSID'))

        video_data = self._search_json(
            r'data-videos="\[', webpage, 'video data', video_id, default={}, transform_source=unescapeHTML)
        video_data.update(self._search_json(
            r'data-meta="', webpage, 'metadata', video_id, default={}, transform_source=unescapeHTML))
        if not video_data:
            raise ExtractorError('No video metadata found in webpage', expected=True)

        info, formats = {}, []
        is_live = int_or_none(video_data.get('mpx_is_livestream')) == 1
        query = {
            'formats': 'MPEG-DASH none,M3U none,MPEG-DASH none,MPEG4,MP3',
            'format': 'SMIL',
            'fwsitesection': fw_ssid,
            'fwNetworkID': traverse_obj(nbc_data, ('video', 'fwNetworkID'), default='382114'),
            'pprofile': 'ots_desktop_html',
            'sensitive': 'false',
            'w': '1920',
            'h': '1080',
            'mode': 'LIVE' if is_live else 'on-demand',
            'vpaid': 'script',
            'schema': '2.0',
            'sdk': 'PDK 6.1.3',
        }

        if is_live:
            player_id = traverse_obj(video_data, ((None, ('video', 'meta')), (
                'mpx_m3upid', 'mpx_pid', 'pid_streaming_web_medium')), get_all=False)
            info['title'] = f'{channel} livestream'

        else:
            player_id = traverse_obj(video_data, (
                (None, ('video', 'meta')), ('pid_streaming_web_high', 'mpx_pid')), get_all=False)

            date_string = traverse_obj(video_data, 'date_string', 'date_gmt')
            if date_string:
                date_string = self._search_regex(
                    r'datetime="([^"]+)"', date_string, 'date string', fatal=False)
            else:
                date_string = traverse_obj(
                    nbc_data, ('dataLayer', 'adobe', ('prop70', 'eVar70', 'eVar59')), get_all=False)

            video_url = traverse_obj(video_data, ((None, ('video', 'meta')), 'mp4_url'), get_all=False)
            if video_url:
                ext = determine_ext(video_url)
                height = self._search_regex(r'\d+-(\d+)p', url_basename(video_url), 'height', default=None)
                formats.append({
                    'url': video_url,
                    'ext': ext,
                    'width': int_or_none(self._RESOLUTIONS.get(height)),
                    'height': int_or_none(height),
                    'format_id': f'http-{ext}',
                })

            info.update({
                'title': video_data.get('title') or traverse_obj(nbc_data, (
                    'dataLayer', (None, 'adobe'), ('contenttitle', 'title', 'prop22')), get_all=False),
                'description':
                    traverse_obj(video_data, 'summary', 'excerpt', 'video_hero_text')
                    or clean_html(traverse_obj(nbc_data, ('dataLayer', 'summary'))),
                'timestamp': unified_timestamp(date_string),
            })

        smil = None
        if player_id and fw_ssid:
            smil = self._download_xml(
                f'https://link.theplatform.com/s/{pdk_acct}/{player_id}', video_id,
                note='Downloading SMIL data', query=query, fatal=is_live)
            if not isinstance(smil, xml.etree.ElementTree.Element):
                smil = None
        subtitles = self._parse_smil_subtitles(smil, default_ns) if smil is not None else {}
        for video in smil.findall(self._xpath_ns('.//video', default_ns)) if smil is not None else []:
            info['duration'] = float_or_none(remove_end(video.get('dur'), 'ms'), 1000)
            video_src_url = video.get('src')
            ext = mimetype2ext(video.get('type'), default=determine_ext(video_src_url))
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video_src_url, video_id, 'mp4', m3u8_id='hls', fatal=is_live,
                    live=is_live, errnote='No HLS formats found')
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif video_src_url:
                formats.append({
                    'url': video_src_url,
                    'format_id': f'https-{ext}',
                    'ext': ext,
                    'width': int_or_none(video.get('width')),
                    'height': int_or_none(video.get('height')),
                })

        if not formats:
            self.raise_no_formats('No video content found in webpage', expected=True)
        elif is_live:
            try:
                self._request_webpage(
                    HEADRequest(formats[0]['url']), video_id, note='Checking live status')
            except ExtractorError:
                raise UserNotLive(video_id=channel)

        return {
            'id': video_id,
            'channel': channel,
            'channel_id': nbc_data.get('callLetters'),
            'uploader': nbc_data.get('on_air_name'),
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
            **info,
        }


class BravoTVIE(NBCUniversalBaseIE):
    _VALID_URL = r'https?://(?:www\.)?(?:bravotv|oxygen)\.com/(?:[^/?#]+/)+(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.bravotv.com/top-chef/season-16/episode-15/videos/the-top-chef-season-16-winner-is',
        'info_dict': {
            'id': '3923059',
            'ext': 'mp4',
            'title': 'The Top Chef Season 16 Winner Is...',
            'display_id': 'the-top-chef-season-16-winner-is',
            'description': 'Find out who takes the title of Top Chef!',
            'upload_date': '20190315',
            'timestamp': 1552618860,
            'season_number': 16,
            'episode_number': 15,
            'series': 'Top Chef',
            'episode': 'Finale',
            'duration': 190,
            'season': 'Season 16',
            'thumbnail': r're:^https://.+\.jpg',
            'uploader': 'NBCU-BRAV',
            'categories': ['Series', 'Series/Top Chef'],
            'tags': 'count:10',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.bravotv.com/top-chef/season-20/episode-1/london-calling',
        'info_dict': {
            'id': '9000234570',
            'ext': 'mp4',
            'title': 'London Calling',
            'display_id': 'london-calling',
            'description': 'md5:5af95a8cbac1856bd10e7562f86bb759',
            'upload_date': '20230310',
            'timestamp': 1678418100,
            'season_number': 20,
            'episode_number': 1,
            'series': 'Top Chef',
            'episode': 'London Calling',
            'duration': 3266,
            'season': 'Season 20',
            'chapters': 'count:7',
            'thumbnail': r're:^https://.+\.jpg',
            'age_limit': 14,
            'media_type': 'Full Episode',
            'uploader': 'NBCU-MPAT',
            'categories': ['Series/Top Chef'],
            'tags': 'count:10',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'This video requires AdobePass MSO credentials',
    }, {
        'url': 'https://www.oxygen.com/in-ice-cold-blood/season-1/closing-night',
        'info_dict': {
            'id': '3692045',
            'ext': 'mp4',
            'title': 'Closing Night',
            'display_id': 'closing-night',
            'description': 'md5:c8a5bb523c8ef381f3328c6d9f1e4632',
            'upload_date': '20230126',
            'timestamp': 1674709200,
            'season_number': 1,
            'episode_number': 1,
            'series': 'In Ice Cold Blood',
            'episode': 'Closing Night',
            'duration': 2629,
            'season': 'Season 1',
            'chapters': 'count:6',
            'thumbnail': r're:^https://.+\.jpg',
            'age_limit': 14,
            'media_type': 'Full Episode',
            'uploader': 'NBCU-MPAT',
            'categories': ['Series/In Ice Cold Blood'],
            'tags': ['ice-t', 'in ice cold blood', 'law and order', 'oxygen', 'true crime'],
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'This video requires AdobePass MSO credentials',
    }, {
        'url': 'https://www.oxygen.com/in-ice-cold-blood/season-2/episode-16/videos/handling-the-horwitz-house-after-the-murder-season-2',
        'info_dict': {
            'id': '3974019',
            'ext': 'mp4',
            'title': '\'Handling The Horwitz House After The Murder (Season 2, Episode 16)',
            'display_id': 'handling-the-horwitz-house-after-the-murder-season-2',
            'description': 'md5:f9d638dd6946a1c1c0533a9c6100eae5',
            'upload_date': '20190618',
            'timestamp': 1560819600,
            'season_number': 2,
            'episode_number': 16,
            'series': 'In Ice Cold Blood',
            'episode': 'Mother Vs Son',
            'duration': 68,
            'season': 'Season 2',
            'thumbnail': r're:^https://.+\.jpg',
            'age_limit': 14,
            'uploader': 'NBCU-OXY',
            'categories': ['Series/In Ice Cold Blood'],
            'tags': ['in ice cold blood', 'ice-t', 'law and order', 'true crime', 'oxygen'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.bravotv.com/below-deck/season-3/ep-14-reunion-part-1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        return self._extract_nbcu_video(url, display_id)


class SyfyIE(NBCUniversalBaseIE):
    _VALID_URL = r'https?://(?:www\.)?syfy\.com/[^/?#]+/(?:season-\d+/episode-\d+/(?:videos/)?|videos/)(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.syfy.com/face-off/season-13/episode-10/videos/keyed-up',
        'info_dict': {
            'id': '3774403',
            'ext': 'mp4',
            'display_id': 'keyed-up',
            'title': 'Keyed Up',
            'description': 'md5:feafd15bee449f212dcd3065bbe9a755',
            'age_limit': 14,
            'duration': 169,
            'thumbnail': r're:https://www\.syfy\.com/.+/.+\.jpg',
            'series': 'Face Off',
            'season': 'Season 13',
            'season_number': 13,
            'episode': 'Through the Looking Glass Part 2',
            'episode_number': 10,
            'timestamp': 1533711618,
            'upload_date': '20180808',
            'media_type': 'Excerpt',
            'uploader': 'NBCU-MPAT',
            'categories': ['Series/Face Off'],
            'tags': 'count:15',
            '_old_archive_ids': ['theplatform 3774403'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.syfy.com/face-off/season-13/episode-10/through-the-looking-glass-part-2',
        'info_dict': {
            'id': '3772391',
            'ext': 'mp4',
            'display_id': 'through-the-looking-glass-part-2',
            'title': 'Through the Looking Glass Pt.2',
            'description': 'md5:90bd5dcbf1059fe3296c263599af41d2',
            'age_limit': 0,
            'duration': 2599,
            'thumbnail': r're:https://www\.syfy\.com/.+/.+\.jpg',
            'chapters': [{'start_time': 0.0, 'end_time': 679.0, 'title': '<Untitled Chapter 1>'},
                         {'start_time': 679.0, 'end_time': 1040.967, 'title': '<Untitled Chapter 2>'},
                         {'start_time': 1040.967, 'end_time': 1403.0, 'title': '<Untitled Chapter 3>'},
                         {'start_time': 1403.0, 'end_time': 1870.0, 'title': '<Untitled Chapter 4>'},
                         {'start_time': 1870.0, 'end_time': 2496.967, 'title': '<Untitled Chapter 5>'},
                         {'start_time': 2496.967, 'end_time': 2599, 'title': '<Untitled Chapter 6>'}],
            'series': 'Face Off',
            'season': 'Season 13',
            'season_number': 13,
            'episode': 'Through the Looking Glass Part 2',
            'episode_number': 10,
            'timestamp': 1672570800,
            'upload_date': '20230101',
            'media_type': 'Full Episode',
            'uploader': 'NBCU-MPAT',
            'categories': ['Series/Face Off'],
            'tags': 'count:15',
            '_old_archive_ids': ['theplatform 3772391'],
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'This video requires AdobePass MSO credentials',
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        return self._extract_nbcu_video(url, display_id, old_ie_key='ThePlatform')
