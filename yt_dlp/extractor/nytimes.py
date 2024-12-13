import json
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    extract_attributes,
    float_or_none,
    get_elements_html_by_class,
    int_or_none,
    merge_dicts,
    mimetype2ext,
    parse_iso8601,
    remove_end,
    remove_start,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class NYTimesBaseIE(InfoExtractor):
    _DNS_NAMESPACE = uuid.UUID('36dd619a-56dc-595b-9e09-37f4152c7b5d')
    _TOKEN = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuNIzKBOFB77aT/jN/FQ+/QVKWq5V1ka1AYmCR9hstz1pGNPH5ajOU9gAqta0T89iPnhjwla+3oec/Z3kGjxbpv6miQXufHFq3u2RC6HyU458cLat5kVPSOQCe3VVB5NRpOlRuwKHqn0txfxnwSSj8mqzstR997d3gKB//RO9zE16y3PoWlDQXkASngNJEWvL19iob/xwAkfEWCjyRILWFY0JYX3AvLMSbq7wsqOCE5srJpo7rRU32zsByhsp1D5W9OYqqwDmflsgCEQy2vqTsJjrJohuNg+urMXNNZ7Y3naMoqttsGDrWVxtPBafKMI8pM2ReNZBbGQsQXRzQNo7+QIDAQAB'
    _GRAPHQL_API = 'https://samizdat-graphql.nytimes.com/graphql/v2'
    _GRAPHQL_QUERY = '''query VideoQuery($id: String!) {
  video(id: $id) {
    ... on Video {
      bylines {
        renderedRepresentation
      }
      duration
      firstPublished
      promotionalHeadline
      promotionalMedia {
        ... on Image {
          crops {
            name
            renditions {
              name
              width
              height
              url
            }
          }
        }
      }
      renditions {
        type
        width
        height
        url
        bitrate
      }
      summary
    }
  }
}'''

    def _call_api(self, media_id):
        # reference: `id-to-uri.js`
        video_uuid = uuid.uuid5(self._DNS_NAMESPACE, 'video')
        media_uuid = uuid.uuid5(video_uuid, media_id)

        return traverse_obj(self._download_json(
            self._GRAPHQL_API, media_id, 'Downloading JSON from GraphQL API', data=json.dumps({
                'query': self._GRAPHQL_QUERY,
                'variables': {'id': f'nyt://video/{media_uuid}'},
            }, separators=(',', ':')).encode(), headers={
                'Content-Type': 'application/json',
                'Nyt-App-Type': 'vhs',
                'Nyt-App-Version': 'v3.52.21',
                'Nyt-Token': self._TOKEN,
                'Origin': 'https://nytimes.com',
            }, fatal=False), ('data', 'video', {dict})) or {}

    def _extract_thumbnails(self, thumbs):
        return traverse_obj(thumbs, (lambda _, v: url_or_none(v['url']), {
            'url': 'url',
            'width': ('width', {int_or_none}),
            'height': ('height', {int_or_none}),
        }), default=None)

    def _extract_formats_and_subtitles(self, video_id, content_media_json):
        urls = []
        formats = []
        subtitles = {}
        for video in traverse_obj(content_media_json, ('renditions', ..., {dict})):
            video_url = video.get('url')
            format_id = video.get('type')
            if not video_url or format_id == 'thumbs' or video_url in urls:
                continue
            urls.append(video_url)
            ext = mimetype2ext(video.get('mimetype')) or determine_ext(video_url)
            if ext == 'm3u8':
                m3u8_fmts, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    video_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=format_id or 'hls', fatal=False)
                formats.extend(m3u8_fmts)
                self._merge_subtitles(m3u8_subs, target=subtitles)
            elif ext == 'mpd':
                continue  # all mpd urls give 404 errors
            else:
                formats.append({
                    'url': video_url,
                    'format_id': format_id,
                    'vcodec': video.get('videoencoding') or video.get('video_codec'),
                    'width': int_or_none(video.get('width')),
                    'height': int_or_none(video.get('height')),
                    'filesize': traverse_obj(video, (
                        ('file_size', 'fileSize'), (None, ('value')), {int_or_none}), get_all=False),
                    'tbr': int_or_none(video.get('bitrate'), 1000) or None,
                    'ext': ext,
                })

        return formats, subtitles

    def _extract_video(self, media_id):
        data = self._call_api(media_id)
        formats, subtitles = self._extract_formats_and_subtitles(media_id, data)

        return {
            'id': media_id,
            'title': data.get('promotionalHeadline'),
            'description': data.get('summary'),
            'timestamp': parse_iso8601(data.get('firstPublished')),
            'duration': float_or_none(data.get('duration'), scale=1000),
            'creator': ', '.join(traverse_obj(data, (  # TODO: change to 'creators'
                'bylines', ..., 'renderedRepresentation', {lambda x: remove_start(x, 'By ')}))),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': self._extract_thumbnails(
                traverse_obj(data, ('promotionalMedia', 'crops', ..., 'renditions', ...))),
        }


class NYTimesIE(NYTimesBaseIE):
    _VALID_URL = r'https?://(?:(?:www\.)?nytimes\.com/video/(?:[^/]+/)+?|graphics8\.nytimes\.com/bcvideo/\d+(?:\.\d+)?/iframe/embed\.html\?videoId=)(?P<id>\d+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//graphics8\.nytimes\.com/bcvideo/[^/]+/iframe/embed\.html.+?)\1>']
    _TESTS = [{
        'url': 'http://www.nytimes.com/video/opinion/100000002847155/verbatim-what-is-a-photocopier.html?playlistId=100000001150263',
        'md5': 'a553aa344014e3723d33893d89d4defc',
        'info_dict': {
            'id': '100000002847155',
            'ext': 'mp4',
            'title': 'Verbatim: What Is a Photocopier?',
            'description': 'md5:93603dada88ddbda9395632fdc5da260',
            'timestamp': 1398646132,
            'upload_date': '20140428',
            'creator': 'Brett Weiner',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.+\.jpg',
            'duration': 419,
        },
    }, {
        'url': 'http://www.nytimes.com/video/travel/100000003550828/36-hours-in-dubai.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        return self._extract_video(video_id)


class NYTimesArticleIE(NYTimesBaseIE):
    _VALID_URL = r'https?://(?:www\.)?nytimes\.com/\d{4}/\d{2}/\d{2}/(?!books|podcasts)[^/?#]+/(?:\w+/)?(?P<id>[^./?#]+)(?:\.html)?'
    _TESTS = [{
        'url': 'http://www.nytimes.com/2015/04/14/business/owner-of-gravity-payments-a-credit-card-processor-is-setting-a-new-minimum-wage-70000-a-year.html?_r=0',
        'md5': '3eb5ddb1d6f86254fe4f233826778737',
        'info_dict': {
            'id': '100000003628438',
            'ext': 'mp4',
            'title': 'One Company’s New Minimum Wage: $70,000 a Year',
            'description': 'md5:89ba9ab67ca767bb92bf823d1f138433',
            'timestamp': 1429047468,
            'upload_date': '20150414',
            'uploader': 'Matthew Williams',
            'creator': 'Patricia Cohen',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.*\.jpg',
            'duration': 119.0,
        },
    }, {
        # article with audio and no video
        'url': 'https://www.nytimes.com/2023/09/29/health/mosquitoes-genetic-engineering.html',
        'md5': '2365b3555c8aa7f4dd34ca735ad02e6a',
        'info_dict': {
            'id': '100000009110381',
            'ext': 'mp3',
            'title': 'The Gamble: Can Genetically Modified Mosquitoes End Disease?',
            'description': 'md5:9ff8b47acbaf7f3ca8c732f5c815be2e',
            'timestamp': 1695960700,
            'upload_date': '20230929',
            'creator': 'Stephanie Nolen, Natalija Gormalova',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.*\.jpg',
            'duration': 1322,
        },
    }, {
        'url': 'https://www.nytimes.com/2023/11/29/business/dealbook/kamala-harris-biden-voters.html',
        'md5': '3eb5ddb1d6f86254fe4f233826778737',
        'info_dict': {
            'id': '100000009202270',
            'ext': 'mp4',
            'title': 'Kamala Harris Defends Biden Policies, but Says ‘More Work’ Needed to Reach Voters',
            'description': 'md5:de4212a7e19bb89e4fb14210ca915f1f',
            'timestamp': 1701290997,
            'upload_date': '20231129',
            'uploader': 'By The New York Times',
            'creator': 'Katie Rogers',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.*\.jpg',
            'duration': 97.631,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        # multiple videos in the same article
        'url': 'https://www.nytimes.com/2023/12/02/business/air-traffic-controllers-safety.html',
        'info_dict': {
            'id': 'air-traffic-controllers-safety',
            'title': 'Drunk and Asleep on the Job: Air Traffic Controllers Pushed to the Brink',
            'description': 'md5:549e5a5e935bf7d048be53ba3d2c863d',
            'upload_date': '20231202',
            'creator': 'Emily Steel, Sydney Ember',
            'timestamp': 1701511264,
        },
        'playlist_count': 3,
    }, {
        'url': 'https://www.nytimes.com/2023/12/02/business/media/netflix-squid-game-challenge.html',
        'only_matching': True,
    }]

    def _extract_content_from_block(self, block):
        details = traverse_obj(block, {
            'id': ('sourceId', {str}),
            'uploader': ('bylines', ..., 'renderedRepresentation', {str}),
            'duration': (None, (('duration', {float_or_none(scale=1000)}), ('length', {int_or_none}))),
            'timestamp': ('firstPublished', {parse_iso8601}),
            'series': ('podcastSeries', {str}),
        }, get_all=False)

        formats, subtitles = self._extract_formats_and_subtitles(details.get('id'), block)
        # audio articles will have an url and no formats
        url = traverse_obj(block, ('fileUrl', {url_or_none}))
        if not formats and url:
            formats.append({'url': url, 'vcodec': 'none'})

        return {
            **details,
            'thumbnails': self._extract_thumbnails(traverse_obj(
                block, ('promotionalMedia', 'crops', ..., 'renditions', ...))),
            'formats': formats,
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)
        art_json = self._search_json(
            r'window\.__preloadedData\s*=', webpage, 'media details', page_id,
            transform_source=lambda x: x.replace('undefined', 'null'))['initialData']['data']['article']

        blocks = traverse_obj(art_json, (
            'sprinkledBody', 'content', ..., ('ledeMedia', None),
            lambda _, v: v['__typename'] in ('Video', 'Audio')))
        if not blocks:
            raise ExtractorError('Unable to extract any media blocks from webpage')

        common_info = {
            'title': remove_end(self._html_extract_title(webpage), ' - The New York Times'),
            'description': traverse_obj(art_json, (
                'sprinkledBody', 'content', ..., 'summary', 'content', ..., 'text', {str}),
                get_all=False) or self._html_search_meta(['og:description', 'twitter:description'], webpage),
            'timestamp': traverse_obj(art_json, ('firstPublished', {parse_iso8601})),
            'creator': ', '.join(
                traverse_obj(art_json, ('bylines', ..., 'creators', ..., 'displayName'))),  # TODO: change to 'creators' (list)
            'thumbnails': self._extract_thumbnails(traverse_obj(
                art_json, ('promotionalMedia', 'assetCrops', ..., 'renditions', ...))),
        }

        entries = []
        for block in blocks:
            entries.append(merge_dicts(self._extract_content_from_block(block), common_info))

        if len(entries) > 1:
            return self.playlist_result(entries, page_id, **common_info)

        return {
            'id': page_id,
            **entries[0],
        }


class NYTimesCookingIE(NYTimesBaseIE):
    IE_NAME = 'NYTimesCookingGuide'
    _VALID_URL = r'https?://cooking\.nytimes\.com/guides/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://cooking.nytimes.com/guides/13-how-to-cook-a-turkey',
        'info_dict': {
            'id': '13-how-to-cook-a-turkey',
            'title': 'How to Cook a Turkey',
            'description': 'md5:726cfd3f9b161bdf5c279879e8050ca0',
        },
        'playlist_count': 2,
    }, {
        # single video example
        'url': 'https://cooking.nytimes.com/guides/50-how-to-make-mac-and-cheese',
        'md5': '64415805fe0b8640fce6b0b9def5989a',
        'info_dict': {
            'id': '100000005835845',
            'ext': 'mp4',
            'title': 'How to Make Mac and Cheese',
            'description': 'md5:b8f2f33ec1fb7523b21367147c9594f1',
            'timestamp': 1522950315,
            'upload_date': '20180405',
            'duration': 9.51,
            'creator': 'Alison Roman',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.*\.jpg',
        },
    }, {
        'url': 'https://cooking.nytimes.com/guides/20-how-to-frost-a-cake',
        'md5': '64415805fe0b8640fce6b0b9def5989a',
        'info_dict': {
            'id': '20-how-to-frost-a-cake',
            'title': 'How to Frost a Cake',
            'description': 'md5:a31fe3b98a8ce7b98aae097730c269cd',
        },
        'playlist_count': 8,
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)
        title = self._html_search_meta(['og:title', 'twitter:title'], webpage)
        description = self._html_search_meta(['og:description', 'twitter:description'], webpage)

        lead_video_id = self._search_regex(
            r'data-video-player-id="(\d+)"></div>', webpage, 'lead video')
        media_ids = traverse_obj(
            get_elements_html_by_class('video-item', webpage), (..., {extract_attributes}, 'data-video-id'))

        if media_ids:
            media_ids.append(lead_video_id)
            return self.playlist_result(
                map(self._extract_video, media_ids), page_id, title, description)

        return {
            **self._extract_video(lead_video_id),
            'title': title,
            'description': description,
            'creator': self._search_regex(  # TODO: change to 'creators'
                r'<span itemprop="author">([^<]+)</span></p>', webpage, 'author', default=None),
        }


class NYTimesCookingRecipeIE(InfoExtractor):
    _VALID_URL = r'https?://cooking\.nytimes\.com/recipes/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://cooking.nytimes.com/recipes/1017817-cranberry-curd-tart',
        'md5': '579e83bbe8e61e9de67f80edba8a78a8',
        'info_dict': {
            'id': '1017817',
            'ext': 'mp4',
            'title': 'Cranberry Curd Tart',
            'description': 'md5:ad77a3fc321db636256d4343c5742152',
            'timestamp': 1447804800,
            'upload_date': '20151118',
            'creator': 'David Tanis',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.*\.jpg',
        },
    }, {
        'url': 'https://cooking.nytimes.com/recipes/1024781-neapolitan-checkerboard-cookies',
        'md5': '58df35998241dcf0620e99e646331b42',
        'info_dict': {
            'id': '1024781',
            'ext': 'mp4',
            'title': 'Neapolitan Checkerboard Cookies',
            'description': 'md5:ba12394c585ababea951cb6d2fcc6631',
            'timestamp': 1701302400,
            'upload_date': '20231130',
            'creator': 'Sue Li',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.*\.jpg',
        },
    }, {
        'url': 'https://cooking.nytimes.com/recipes/1019516-overnight-oats',
        'md5': '2fe7965a3adc899913b8e25ada360823',
        'info_dict': {
            'id': '1019516',
            'ext': 'mp4',
            'timestamp': 1546387200,
            'description': 'md5:8856ce10239161bd2596ac335b9f9bfb',
            'upload_date': '20190102',
            'title': 'Overnight Oats',
            'creator': 'Genevieve Ko',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.*\.jpg',
        },
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)
        recipe_data = self._search_nextjs_data(webpage, page_id)['props']['pageProps']['recipe']

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            recipe_data['videoSrc'], page_id, 'mp4', m3u8_id='hls')

        return {
            **traverse_obj(recipe_data, {
                'id': ('id', {str_or_none}),
                'title': ('title', {str}),
                'description': ('topnote', {clean_html}),
                'timestamp': ('publishedAt', {int_or_none}),
                'creator': ('contentAttribution', 'cardByline', {str}),
            }),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': [{'url': thumb_url} for thumb_url in traverse_obj(
                recipe_data, ('image', 'crops', 'recipe', ..., {url_or_none}))],
        }
