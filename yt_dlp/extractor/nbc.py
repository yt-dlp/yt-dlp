import base64
import json
import re

from .common import InfoExtractor
from .theplatform import ThePlatformIE
from .adobepass import AdobePassIE
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_age_limit,
    parse_duration,
    RegexNotFoundError,
    smuggle_url,
    str_or_none,
    traverse_obj,
    try_get,
    unified_strdate,
    unified_timestamp,
    update_url_query,
    url_basename,
    variadic,
)


class NBCIE(ThePlatformIE):  # XXX: Do not subclass from concrete IE
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
        permalink, video_id = self._match_valid_url(url).groups()
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
    _EMBED_REGEX = [r'(?:iframe[^>]+|var video|div[^>]+data-(?:mpx-)?)[sS]rc\s?=\s?"(?P<url>%s[^\"]+)' % _VALID_URL_BASE]

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
            'thumbnail': r're:^https?://.*\.jpg$'
        }
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
            'chapters': [],
            'thumbnail': 'https://hdliveextra-a.akamaihd.net/HD/image_sports/NBCU_Sports_Group_-_nbcsports/253/303/izzodps.jpg',
            'duration': 528.395,
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
                webpage, 'embedding URL', group="embedUrl")

        return {
            '_type': 'url_transparent',
            'url': theplatform_url,
            'ie_key': ThePlatformIE.ie_key(),
            'display_id': display_id,
        }


class NBCOlympicsStreamIE(AdobePassIE):
    IE_NAME = 'nbcolympics:stream'
    _VALID_URL = r'https?://stream\.nbcolympics\.com/(?P<id>[0-9a-z-]+)'
    _TESTS = [
        {
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
        },
    ]

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
            pid, 'Downloading leap config'
        )['videoSources'][0]['cdnSources']['primary'][0]['sourceUrl']

        if event_config.get('cdnToken'):
            ap_resource = self._get_mvpd_resource(
                event_config.get('resourceId', 'NBCOlympics'),
                re.sub(r'[^\w\d ]+', '', event_config['eventTitle']), pid,
                event_config.get('ratingId', 'NO VALUE'))
            media_token = self._extract_mvpd_auth(url, pid, event_config.get('requestorId', 'NBCOlympics'), ap_resource)

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
        'md5': '462041d91bd762ef5a38b7d85d6dc18f',
        'info_dict': {
            'id': '2968618',
            'ext': 'mp4',
            'title': 'Large Structure Fire in Downtown LA Prompts Smoke Odor Advisory',
            'description': None,
            'timestamp': 1661135892,
            'upload_date': '20220821',
            'uploader': 'NBC 4',
            'uploader_id': 'KNBC',
            'channel': 'nbclosangeles',
        },
    }, {
        'url': 'https://www.telemundoarizona.com/responde/huracan-complica-reembolso-para-televidente-de-tucson/2247002/',
        'md5': '0917dcf7885be1023a9220630d415f67',
        'info_dict': {
            'id': '2247002',
            'ext': 'mp4',
            'title': 'Huracán complica que televidente de Tucson reciba reembolso',
            'description': 'md5:af298dc73aab74d4fca6abfb12acb6cf',
            'timestamp': 1660886507,
            'upload_date': '20220819',
            'uploader': 'Telemundo Arizona',
            'uploader_id': 'KTAZ',
            'channel': 'telemundoarizona',
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
            r'<script>var\s*nbc\s*=', webpage, 'NBC JSON data', video_id)
        pdk_acct = nbc_data.get('pdkAcct') or 'Yh1nAC'
        fw_ssid = traverse_obj(nbc_data, ('video', 'fwSSID'))
        fw_network_id = traverse_obj(nbc_data, ('video', 'fwNetworkID'), default='382114')

        video_data = self._parse_json(self._html_search_regex(
            r'data-videos="([^"]*)"', webpage, 'video data', default='{}'), video_id)
        video_data = variadic(video_data)[0]
        video_data.update(self._parse_json(self._html_search_regex(
            r'data-meta="([^"]*)"', webpage, 'metadata', default='{}'), video_id))

        formats = []

        if video_data.get('mpx_is_livestream') == '1':
            live = True
            player_id = traverse_obj(
                video_data, 'mpx_m3upid', ('video', 'meta', 'mpx_m3upid'), 'mpx_pid',
                ('video', 'meta', 'mpx_pid'), 'pid_streaming_web_medium')
            query = {
                'mbr': 'true',
                'assetTypes': 'LegacyRelease',
                'fwsitesection': fw_ssid,
                'fwNetworkID': fw_network_id,
                'pprofile': 'ots_desktop_html',
                'sensitive': 'false',
                'w': '1920',
                'h': '1080',
                'rnd': '1660303',
                'mode': 'LIVE',
                'format': 'SMIL',
                'tracking': 'true',
                'formats': 'M3U+none,MPEG-DASH+none,MPEG4,MP3',
                'vpaid': 'script',
                'schema': '2.0',
                'SDK': 'PDK+6.1.3',
            }
            info = {
                'title': f'{channel} livestream',
            }

        else:
            live = False
            player_id = traverse_obj(
                video_data, ('video', 'meta', 'pid_streaming_web_high'), 'pid_streaming_web_high',
                ('video', 'meta', 'mpx_pid'), 'mpx_pid')

            date_string = traverse_obj(video_data, 'date_string', 'date_gmt')
            if date_string:
                date_string = self._search_regex(
                    r'datetime="([^"]+)"', date_string, 'date string', fatal=False)
            else:
                date_string = traverse_obj(
                    nbc_data, ('dataLayer', 'adobe', 'prop70'), ('dataLayer', 'adobe', 'eVar70'),
                    ('dataLayer', 'adobe', 'eVar59'))

            video_url = traverse_obj(video_data, ('video', 'meta', 'mp4_url'), 'mp4_url')
            if video_url:
                height = url_basename(video_url).split('-')[1].split('p')[0]
                formats.append({
                    'url': video_url,
                    'ext': 'mp4',
                    'width': int_or_none(self._RESOLUTIONS.get(height)),
                    'height': int_or_none(height),
                    'format_id': f'http-{height}',
                })

            query = {
                'mbr': 'true',
                'assetTypes': 'LegacyRelease',
                'fwsitesection': fw_ssid,
                'fwNetworkID': fw_network_id,
                'format': 'redirect',
                'manifest': 'm3u',
                'Tracking': 'true',
                'Embedded': 'true',
                'formats': 'MPEG4',
            }
            info = {
                'title': video_data.get('title') or traverse_obj(
                    nbc_data, ('dataLayer', 'contenttitle'), ('dataLayer', 'title'),
                    ('dataLayer', 'adobe', 'prop22'), ('dataLayer', 'id')),
                'description': traverse_obj(video_data, 'summary', 'excerpt', 'video_hero_text'),
                'upload_date': str_or_none(unified_strdate(date_string)),
                'timestamp': int_or_none(unified_timestamp(date_string)),
            }

        if not player_id:
            raise ExtractorError(
                'No video player ID or livestream player ID found in webpage', expected=True)

        headers = {'Origin': f'https://www.{channel}.com'}
        manifest, urlh = self._download_webpage_handle(
            f'https://link.theplatform.com/s/{pdk_acct}/{player_id}', video_id,
            headers=headers, query=query, note='Downloading manifest')
        if live:
            manifest_url = self._search_regex(r'<video src="([^"]*)', manifest, 'manifest URL')
        else:
            manifest_url = urlh.geturl()

        formats.extend(self._extract_m3u8_formats(
            manifest_url, video_id, 'mp4', headers=headers, m3u8_id='hls',
            fatal=live, live=live, errnote='No HLS formats found'))

        return {
            'id': str_or_none(video_id),
            'channel': channel,
            'uploader': str_or_none(nbc_data.get('on_air_name')),
            'uploader_id': str_or_none(nbc_data.get('callLetters')),
            'formats': formats,
            'is_live': live,
            **info,
        }
