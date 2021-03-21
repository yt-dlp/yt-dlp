from __future__ import unicode_literals

import base64
import json
import re

from .common import InfoExtractor
from .theplatform import ThePlatformIE
from .adobepass import AdobePassIE
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    int_or_none,
    parse_age_limit,
    parse_duration,
    smuggle_url,
    try_get,
    unified_timestamp,
    update_url_query,
)


class NBCIE(ThePlatformIE):
    _VALID_URL = r'https?(?P<permalink>://(?:www\.)?nbc\.com/(?:classic-tv/)?[^/]+/video/[^/]+/(?P<id>n?\d+))'

    _TESTS = [
        {
            'url': 'http://www.nbc.com/the-tonight-show/video/jimmy-fallon-surprises-fans-at-ben-jerrys/2848237',
            'info_dict': {
                'id': '2848237',
                'ext': 'mp4',
                'title': 'Jimmy Fallon Surprises Fans at Ben & Jerry\'s',
                'description': 'Jimmy gives out free scoops of his new "Tonight Dough" ice cream flavor by surprising customers at the Ben & Jerry\'s scoop shop.',
                'timestamp': 1424246400,
                'upload_date': '20150218',
                'uploader': 'NBCU-COM',
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.nbc.com/saturday-night-live/video/star-wars-teaser/2832821',
            'info_dict': {
                'id': '2832821',
                'ext': 'mp4',
                'title': 'Star Wars Teaser',
                'description': 'md5:0b40f9cbde5b671a7ff62fceccc4f442',
                'timestamp': 1417852800,
                'upload_date': '20141206',
                'uploader': 'NBCU-COM',
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
            'skip': 'Only works from US',
        },
        {
            # HLS streams requires the 'hdnea3' cookie
            'url': 'http://www.nbc.com/Kings/video/goliath/n1806',
            'info_dict': {
                'id': '101528f5a9e8127b107e98c5e6ce4638',
                'ext': 'mp4',
                'title': 'Goliath',
                'description': 'When an unknown soldier saves the life of the King\'s son in battle, he\'s thrust into the limelight and politics of the kingdom.',
                'timestamp': 1237100400,
                'upload_date': '20090315',
                'uploader': 'NBCU-COM',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'Only works from US',
        },
        {
            'url': 'https://www.nbc.com/classic-tv/charles-in-charge/video/charles-in-charge-pilot/n3310',
            'only_matching': True,
        },
        {
            # Percent escaped url
            'url': 'https://www.nbc.com/up-all-night/video/day-after-valentine%27s-day/n2189',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        permalink, video_id = re.match(self._VALID_URL, url).groups()
        permalink = 'http' + compat_urllib_parse_unquote(permalink)
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
        query = {
            'mbr': 'true',
            'manifest': 'm3u',
        }
        video_id = video_data['mpxGuid']
        tp_path = 'NnzsPC/media/guid/%s/%s' % (video_data.get('mpxAccountId') or '2410887629', video_id)
        tpm = self._download_theplatform_metadata(tp_path, video_id)
        title = tpm.get('title') or video_data.get('secondaryTitle')
        if video_data.get('locked'):
            resource = self._get_mvpd_resource(
                video_data.get('resourceId') or 'nbcentertainment',
                title, video_id, video_data.get('rating'))
            query['auth'] = self._extract_mvpd_auth(
                url, video_id, 'nbcentertainment', resource)
        theplatform_url = smuggle_url(update_url_query(
            'http://link.theplatform.com/s/NnzsPC/media/guid/%s/%s' % (video_data.get('mpxAccountId') or '2410887629', video_id),
            query), {'force_smil_url': True})

        # Empty string or 0 can be valid values for these. So the check must be `is None`
        description = video_data.get('description')
        if description is None:
            description = tpm.get('description')
        episode_number = int_or_none(video_data.get('episodeNumber'))
        if episode_number is None:
            episode_number = int_or_none(tpm.get('nbcu$airOrder'))
        rating = video_data.get('rating')
        if rating is None:
            try_get(tpm, lambda x: x['ratings'][0]['rating'])
        season_number = int_or_none(video_data.get('seasonNumber'))
        if season_number is None:
            season_number = int_or_none(tpm.get('nbcu$seasonNumber'))
        series = video_data.get('seriesShortTitle')
        if series is None:
            series = tpm.get('nbcu$seriesShortTitle')
        tags = video_data.get('keywords')
        if tags is None or len(tags) == 0:
            tags = tpm.get('keywords')

        return {
            '_type': 'url_transparent',
            'age_limit': parse_age_limit(rating),
            'description': description,
            'episode': title,
            'episode_number': episode_number,
            'id': video_id,
            'ie_key': 'ThePlatform',
            'season_number': season_number,
            'series': series,
            'tags': tags,
            'title': title,
            'url': theplatform_url,
        }


class NBCSportsVPlayerIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:vplayer\.nbcsports\.com|(?:www\.)?nbcsports\.com/vplayer)/'
    _VALID_URL = _VALID_URL_BASE + r'(?:[^/]+/)+(?P<id>[0-9a-zA-Z_]+)'

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
        }
    }, {
        'url': 'https://vplayer.nbcsports.com/p/BxmELC/nbcsports_embed/select/media/_hqLjQ95yx8Z',
        'only_matching': True,
    }, {
        'url': 'https://www.nbcsports.com/vplayer/p/BxmELC/nbcsports/select/PHJSaFWbrTY9?form=html&autoPlay=true',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_url(webpage):
        iframe_m = re.search(
            r'<(?:iframe[^>]+|div[^>]+data-(?:mpx-)?)src="(?P<url>%s[^"]+)"' % NBCSportsVPlayerIE._VALID_URL_BASE, webpage)
        if iframe_m:
            return iframe_m.group('url')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        theplatform_url = self._og_search_video_url(webpage).replace(
            'vplayer.nbcsports.com', 'player.theplatform.com')
        return self.url_result(theplatform_url, 'ThePlatform')


class NBCSportsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nbcsports\.com//?(?!vplayer/)(?:[^/]+/)+(?P<id>[0-9a-z-]+)'

    _TESTS = [{
        # iframe src
        'url': 'http://www.nbcsports.com//college-basketball/ncaab/tom-izzo-michigan-st-has-so-much-respect-duke',
        'info_dict': {
            'id': 'PHJSaFWbrTY9',
            'ext': 'mp4',
            'title': 'Tom Izzo, Michigan St. has \'so much respect\' for Duke',
            'description': 'md5:ecb459c9d59e0766ac9c7d5d0eda8113',
            'uploader': 'NBCU-SPORTS',
            'upload_date': '20150330',
            'timestamp': 1427726529,
        }
    }, {
        # data-mpx-src
        'url': 'https://www.nbcsports.com/philadelphia/philadelphia-phillies/bruce-bochy-hector-neris-hes-idiot',
        'only_matching': True,
    }, {
        # data-src
        'url': 'https://www.nbcsports.com/boston/video/report-card-pats-secondary-no-match-josh-allen',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        return self.url_result(
            NBCSportsVPlayerIE._extract_url(webpage), 'NBCSportsVPlayer')


class NBCSportsStreamIE(AdobePassIE):
    _VALID_URL = r'https?://stream\.nbcsports\.com/.+?\bpid=(?P<id>\d+)'
    _TEST = {
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
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        live_source = self._download_json(
            'http://stream.nbcsports.com/data/live_sources_%s.json' % video_id,
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
        token = self._extract_mvpd_auth(url, video_id, 'nbcsports', resource)
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
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': self._live_title(title) if is_live else title,
            'description': live_source.get('description'),
            'formats': formats,
            'is_live': is_live,
        }


class NBCNewsIE(ThePlatformIE):
    _VALID_URL = r'(?x)https?://(?:www\.)?(?:nbcnews|today|msnbc)\.com/([^/]+/)*(?:.*-)?(?P<id>[^/?]+)'

    _TESTS = [
        {
            'url': 'http://www.nbcnews.com/watch/nbcnews-com/how-twitter-reacted-to-the-snowden-interview-269389891880',
            'md5': 'cf4bc9e6ce0130f00f545d80ecedd4bf',
            'info_dict': {
                'id': '269389891880',
                'ext': 'mp4',
                'title': 'How Twitter Reacted To The Snowden Interview',
                'description': 'md5:65a0bd5d76fe114f3c2727aa3a81fe64',
                'timestamp': 1401363060,
                'upload_date': '20140529',
            },
        },
        {
            'url': 'http://www.nbcnews.com/feature/dateline-full-episodes/full-episode-family-business-n285156',
            'md5': 'fdbf39ab73a72df5896b6234ff98518a',
            'info_dict': {
                'id': '529953347624',
                'ext': 'mp4',
                'title': 'FULL EPISODE: Family Business',
                'description': 'md5:757988edbaae9d7be1d585eb5d55cc04',
            },
            'skip': 'This page is unavailable.',
        },
        {
            'url': 'http://www.nbcnews.com/nightly-news/video/nightly-news-with-brian-williams-full-broadcast-february-4-394064451844',
            'md5': '8eb831eca25bfa7d25ddd83e85946548',
            'info_dict': {
                'id': '394064451844',
                'ext': 'mp4',
                'title': 'Nightly News with Brian Williams Full Broadcast (February 4)',
                'description': 'md5:1c10c1eccbe84a26e5debb4381e2d3c5',
                'timestamp': 1423104900,
                'upload_date': '20150205',
            },
        },
        {
            'url': 'http://www.nbcnews.com/business/autos/volkswagen-11-million-vehicles-could-have-suspect-software-emissions-scandal-n431456',
            'md5': '4a8c4cec9e1ded51060bdda36ff0a5c0',
            'info_dict': {
                'id': 'n431456',
                'ext': 'mp4',
                'title': "Volkswagen U.S. Chief:  We 'Totally Screwed Up'",
                'description': 'md5:d22d1281a24f22ea0880741bb4dd6301',
                'upload_date': '20150922',
                'timestamp': 1442917800,
            },
        },
        {
            'url': 'http://www.today.com/video/see-the-aurora-borealis-from-space-in-stunning-new-nasa-video-669831235788',
            'md5': '118d7ca3f0bea6534f119c68ef539f71',
            'info_dict': {
                'id': '669831235788',
                'ext': 'mp4',
                'title': 'See the aurora borealis from space in stunning new NASA video',
                'description': 'md5:74752b7358afb99939c5f8bb2d1d04b1',
                'upload_date': '20160420',
                'timestamp': 1461152093,
            },
        },
        {
            'url': 'http://www.msnbc.com/all-in-with-chris-hayes/watch/the-chaotic-gop-immigration-vote-314487875924',
            'md5': '6d236bf4f3dddc226633ce6e2c3f814d',
            'info_dict': {
                'id': '314487875924',
                'ext': 'mp4',
                'title': 'The chaotic GOP immigration vote',
                'description': 'The Republican House votes on a border bill that has no chance of getting through the Senate or signed by the President and is drawing criticism from all sides.',
                'thumbnail': r're:^https?://.*\.jpg$',
                'timestamp': 1406937606,
                'upload_date': '20140802',
            },
        },
        {
            'url': 'http://www.nbcnews.com/watch/dateline/full-episode--deadly-betrayal-386250819952',
            'only_matching': True,
        },
        {
            # From http://www.vulture.com/2016/06/letterman-couldnt-care-less-about-late-night.html
            'url': 'http://www.nbcnews.com/widget/video-embed/701714499682',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data = self._parse_json(self._search_regex(
            r'<script[^>]+id="__NEXT_DATA__"[^>]*>({.+?})</script>',
            webpage, 'bootstrap json'), video_id)['props']['initialState']
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
            if tbr:
                format_id += '-%d' % tbr
            formats.append({
                'format_id': format_id,
                'url': public_url,
                'width': int_or_none(va.get('width')),
                'height': int_or_none(va.get('height')),
                'tbr': tbr,
                'ext': 'mp4',
            })
        self._sort_formats(formats)

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
    _VALID_URL = r'https?://www\.nbcolympics\.com/video/(?P<id>[a-z-]+)'

    _TEST = {
        # Geo-restricted to US
        'url': 'http://www.nbcolympics.com/video/justin-roses-son-leo-was-tears-after-his-dad-won-gold',
        'md5': '54fecf846d05429fbaa18af557ee523a',
        'info_dict': {
            'id': 'WjTBzDXx5AUq',
            'display_id': 'justin-roses-son-leo-was-tears-after-his-dad-won-gold',
            'ext': 'mp4',
            'title': 'Rose\'s son Leo was in tears after his dad won gold',
            'description': 'Olympic gold medalist Justin Rose gets emotional talking to the impact his win in men\'s golf has already had on his children.',
            'timestamp': 1471274964,
            'upload_date': '20160815',
            'uploader': 'NBCU-SPORTS',
        },
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        drupal_settings = self._parse_json(self._search_regex(
            r'jQuery\.extend\(Drupal\.settings\s*,\s*({.+?})\);',
            webpage, 'drupal settings'), display_id)

        iframe_url = drupal_settings['vod']['iframe_url']
        theplatform_url = iframe_url.replace(
            'vplayer.nbcolympics.com', 'player.theplatform.com')

        return {
            '_type': 'url_transparent',
            'url': theplatform_url,
            'ie_key': ThePlatformIE.ie_key(),
            'display_id': display_id,
        }


class NBCOlympicsStreamIE(AdobePassIE):
    IE_NAME = 'nbcolympics:stream'
    _VALID_URL = r'https?://stream\.nbcolympics\.com/(?P<id>[0-9a-z-]+)'
    _TEST = {
        'url': 'http://stream.nbcolympics.com/2018-winter-olympics-nbcsn-evening-feb-8',
        'info_dict': {
            'id': '203493',
            'ext': 'mp4',
            'title': 're:Curling, Alpine, Luge [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }
    _DATA_URL_TEMPLATE = 'http://stream.nbcolympics.com/data/%s_%s.json'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        pid = self._search_regex(r'pid\s*=\s*(\d+);', webpage, 'pid')
        resource = self._search_regex(
            r"resource\s*=\s*'(.+)';", webpage,
            'resource').replace("' + pid + '", pid)
        event_config = self._download_json(
            self._DATA_URL_TEMPLATE % ('event_config', pid),
            pid)['eventConfig']
        title = self._live_title(event_config['eventTitle'])
        source_url = self._download_json(
            self._DATA_URL_TEMPLATE % ('live_sources', pid),
            pid)['videoSources'][0]['sourceUrl']
        media_token = self._extract_mvpd_auth(
            url, pid, event_config.get('requestorId', 'NBCOlympics'), resource)
        formats = self._extract_m3u8_formats(self._download_webpage(
            'http://sp.auth.adobe.com/tvs/v1/sign', pid, query={
                'cdn': 'akamai',
                'mediaToken': base64.b64encode(media_token.encode()),
                'resource': base64.b64encode(resource.encode()),
                'url': source_url,
            }), pid, 'mp4')
        self._sort_formats(formats)

        return {
            'id': pid,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'is_live': True,
        }
