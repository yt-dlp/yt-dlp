import json
import uuid

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    extract_attributes,
    float_or_none,
    get_elements_html_by_class,
    int_or_none,
    mimetype2ext,
    parse_iso8601,
    remove_end,
    remove_start,
    str_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class NYTimesBaseIE(InfoExtractor):
    _GRAPHQL_API = 'https://samizdat-graphql.nytimes.com/graphql/v2'

    @staticmethod
    def _get_file_size(file_size):
        if isinstance(file_size, int):
            return file_size
        elif isinstance(file_size, dict):
            return int(file_size.get('value', 0))
        else:
            return None

    def _extract_media_from_json(self, video_id, content_media_json):
        urls = []
        formats = []
        subtitles = {}
        for video in content_media_json:
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
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            elif ext == 'mpd':
                continue
            else:
                formats.append({
                    'url': video_url,
                    'format_id': format_id,
                    'vcodec': video.get('videoencoding') or video.get('video_codec'),
                    'width': int_or_none(video.get('width')),
                    'height': int_or_none(video.get('height')),
                    'filesize': self._get_file_size(video.get('file_size') or video.get('fileSize')),
                    'tbr': int_or_none(video.get('bitrate'), 1000) or None,
                    'ext': ext,
                })

        return formats, subtitles


class NYTimesArticleIE(NYTimesBaseIE):
    _VALID_URL = r'https?://(?:www\.)?nytimes\.com/\d{4}/\d{2}/\d{2}/[^/]+/(?:\w+/)?(?P<id>[^.]+)(?:\.html)?'
    _TESTS = [{
        'url': 'http://www.nytimes.com/2015/04/14/business/owner-of-gravity-payments-a-credit-card-processor-is-setting-a-new-minimum-wage-70000-a-year.html?_r=0',
        'md5': '3eb5ddb1d6f86254fe4f233826778737',
        'info_dict': {
            'id': '100000003628438',
            'ext': 'mp4',
            'title': 'One Company’s New Minimum Wage: $70,000 a Year',
            'description': 'The owner of Gravity Payments, a credit card processor in Seattle, said he heard stories of how tough it was to make ends meet even on salaries that exceeded the federal minimum wage.',
            'timestamp': 1429047468,
            'upload_date': '20150414',
            'uploader': 'Matthew Williams',
            'creator': 'Patricia Cohen',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.*\.jpg',
            'duration': 119,
        }
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
        }
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
            'duration': 97,
        },
        'params': {
            # inconsistant md5
            'skip_download': True,
        },
    }, {
        # multiple videos in the same article
        'url': 'https://www.nytimes.com/2023/12/02/business/air-traffic-controllers-safety.html',
        'info_dict': {
            'id': 'air-traffic-controllers-safety',
            'title': 'Drunk and Asleep on the Job: Air Traffic Controllers Pushed to the Brink',
            'description': 'A nationwide shortage of controllers has resulted in an exhausted and demoralized work force that is increasingly prone to making dangerous mistakes.',
        },
        'playlist_count': 3,

    }, {
        'url': 'https://www.nytimes.com/2023/12/02/business/media/netflix-squid-game-challenge.html',
        'only_matching': True,
    }, {
        'url': 'http://www.nytimes.com/news/minute/2014/03/17/times-minute-whats-next-in-crimea/?_php=true&_type=blogs&_php=true&_type=blogs&_r=1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id).replace(':undefined', ':null')
        article_json = traverse_obj(self._search_json(
            r'window.__preloadedData\s=', webpage, 'media details', page_id), ('initialData', 'data', 'article'))
        blocks_json = traverse_obj(
            article_json, ('sprinkledBody', 'content', ..., ('ledeMedia', None), lambda _, v: v['__typename'] in ('Video', 'Audio')))

        art_title = remove_end(self._html_extract_title(webpage), ' - The New York Times')
        art_description = traverse_obj(
            article_json, ('sprinkledBody', 'content', ..., 'summary', 'content', ..., 'text'),
            get_all=False) or self._html_search_meta(['og:description', 'twitter:description'], webpage)
        creator = ', '.join(
            traverse_obj(article_json, ('bylines', ..., 'creators', ..., 'displayName'), get_all=True))

        # more than 1 video in the article, treat it as a playlist
        if len(blocks_json) > 1:
            entries = []
            for block_json in blocks_json:
                video_id = traverse_obj(block_json, ('sourceId'), get_all=False)
                media_title = traverse_obj(block_json, ('promotionalHeadline'), get_all=False) or art_title
                media_description = traverse_obj(block_json, ('summary'), get_all=False)
                uploader = traverse_obj(block_json, ('bylines', ..., 'renderedRepresentation'), get_all=False)
                duration = float_or_none(traverse_obj(block_json, ('duration'), get_all=False))
                publication_date = traverse_obj(block_json, ('firstPublished'))
                timestamp = parse_iso8601(publication_date) if publication_date else None

                media_content = traverse_obj(block_json, ('renditions', ...))
                formats, subtitles = self._extract_media_from_json(video_id, media_content)

                thumbnails = []
                for image in traverse_obj(block_json, ('promotionalMedia', 'crops', ..., 'renditions', ...), get_all=True):
                    image_url = image.get('url')
                    if not image_url:
                        continue
                    thumbnails.append({
                        'url': image_url,
                        'width': int_or_none(image.get('width')),
                        'height': int_or_none(image.get('height')),
                    })

                entries.append({
                    'id': video_id,
                    'title': media_title,
                    'description': media_description,
                    'timestamp': timestamp,
                    'upload_date': unified_strdate(publication_date),
                    'uploader': uploader,
                    'creator': creator,
                    'duration': int_or_none(duration, 1000),
                    'formats': formats,
                    'subtitles': subtitles,
                    'thumbnails': thumbnails})

            return self.playlist_result(entries, page_id, art_title, art_description)

        block_json = blocks_json.pop()
        media_id = traverse_obj(block_json, ('sourceId'), get_all=False)
        publication_date = traverse_obj(
            block_json, ('firstPublished')) or traverse_obj(article_json, ('firstPublished'))
        timestamp = parse_iso8601(publication_date) if publication_date else None
        duration = int_or_none(traverse_obj(
            block_json, ('duration'), get_all=False), 1000) or traverse_obj(block_json, ('length'), get_all=False)
        series = traverse_obj(block_json, ('podcastSeries'), get_all=False)
        uploader = traverse_obj(block_json, ('bylines', ..., 'renderedRepresentation'), get_all=False)

        media_content = traverse_obj(block_json, ('renditions', ...))
        formats, subtitles = self._extract_media_from_json(media_id, media_content)

        # audio articles won't have formats
        url = traverse_obj(block_json, ('fileUrl'), get_all=False)
        if not formats and url:
            formats.append({'url': url, 'ext': determine_ext(url)})

        thumbnails = []
        for image in traverse_obj(
            block_json, ('promotionalMedia', 'crops', ..., 'renditions', ...), get_all=True) or traverse_obj(
                article_json, ('promotionalMedia', 'assetCrops', ..., 'renditions', ...)):
            image_url = image.get('url')
            if not image_url:
                continue
            thumbnails.append({
                'url': image_url,
                'width': int_or_none(image.get('width')),
                'height': int_or_none(image.get('height')),
            })

        return {
            'id': media_id,
            'title': art_title,
            'description': art_description,
            'timestamp': timestamp,
            'upload_date': unified_strdate(publication_date),
            'uploader': uploader,
            'creator': creator,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'series': series
        }


class NYTimesCookingReceipesIE(InfoExtractor):
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
        }
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        json_obj = traverse_obj(
            self._search_nextjs_data(webpage, page_id), ('props', 'pageProps'), default={})

        info = traverse_obj(json_obj, {
            'id': ('recipe', 'id', {str_or_none}),
            'title': ('recipe', 'title'),
            'description': ('recipe', 'topnote', {clean_html}),
            'timestamp': ('recipe', 'publishedAt'),
            'creator': ('recipe', 'contentAttribution', 'cardByline'),
            'upload_date': ('meta', 'jsonLD', 'video', 'uploadDate', {unified_strdate}),
            'formats': ('recipe', 'videoSrc', {url_or_none}),
        })

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            info.get('formats'), info.get('id'), 'mp4', entry_protocol='m3u8_native', m3u8_id='hls')

        thumbnails = []
        for image in traverse_obj(json_obj, ('recipe', 'image', 'crops', 'recipe', ...)):
            if not url_or_none(image):
                continue
            thumbnails.append({
                'url': image,
            })

        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'description': info.get('description'),
            'timestamp': info.get('timestamp'),
            'upload_date': info.get(' upload_date'),
            'creator': info.get('creator'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
        }


class NYTimesCookingGuidesIE(NYTimesBaseIE):
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
            'duration': 9510,
            'creator': 'Alison Roman',
            'thumbnail': r're:https?://\w+\.nyt.com/images/.*\.jpg',
        }
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

    _TOKEN = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuNIzKBOFB77aT/jN/FQ+/QVKWq5V1ka1AYmCR9hstz1pGNPH5ajOU9gAqta0T89iPnhjwla+3oec/Z3kGjxbpv6miQXufHFq3u2RC6HyU458cLat5kVPSOQCe3VVB5NRpOlRuwKHqn0txfxnwSSj8mqzstR997d3gKB//RO9zE16y3PoWlDQXkASngNJEWvL19iob/xwAkfEWCjyRILWFY0JYX3AvLMSbq7wsqOCE5srJpo7rRU32zsByhsp1D5W9OYqqwDmflsgCEQy2vqTsJjrJohuNg+urMXNNZ7Y3naMoqttsGDrWVxtPBafKMI8pM2ReNZBbGQsQXRzQNo7+QIDAQAB"
    _DNS_UUID = '36dd619a-56dc-595b-9e09-37f4152c7b5d'  # uuid -v5 ns:DNS scoop.nyt.net
    _GRAPHQL_QUERY = '''query VideoQuery($id: String!) {
  video(id: $id) {
    ... on Video {
      advertisingProperties {
        sensitivity
        sponsored
      }
      bylines {
        renderedRepresentation
      }
      contentSeries
      cues {
        name
        type
        timeIn
        timeOut
      }
      duration
      embedded
      headline {
        default
      }
      is360
      isLive
      liveUrls
      playlist {
        headline {
          default
        }
        promotionalHeadline
        url
        sourceId
        section {
          displayName
        }
        videos(first: 20) {
          edges @filterEmpty {
            node {
              advertisingProperties {
                sensitivity
                sponsored
              }
              id
              sourceId
              duration
              section {
                id
                name
              }
              headline {
                default
              }
              renditions {
                url
                type
              }
              url
              promotionalMedia {
                ... on Image {
                  crops(
                    cropNames: [SMALL_SQUARE, MEDIUM_SQUARE, SIXTEEN_BY_NINE]
                  ) {
                    renditions {
                      name
                      width
                      height
                      url
                    }
                  }
                }
              }
            }
          }
        }
      }
      promotionalHeadline
      promotionalMedia {
        ... on Image {
          crops(
            cropNames: [
              SMALL_SQUARE
              MEDIUM_SQUARE
              SIXTEEN_BY_NINE
              THREE_BY_TWO
              TWO_BY_THREE
              FLEXIBLE
            ]
          ) {
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
      promotionalSummary
      related {
        ... on Article {
          promotionalHeadline
          url
          sourceId
        }
      }
      renditions {
        type
        width
        height
        url
        bitrate
      }
      section {
        name
      }
      shortUrl
      sourceId
      subsection {
        name
      }
      summary
      timesTags {
        __typename
        displayName
        isAdvertisingBrandSensitive
        vernacular
      }
      url
    }
  }
}'''

    def _build_playlist(self, media_items):
        entries = []
        for media_id in media_items:
            json_obj = traverse_obj(self._json_from_graphql(media_id) or {}, ('data', 'video'))

            title = json_obj.get('promotionalHeadline') or media_id
            description = json_obj.get('summary')
            creators = ', '.join(
                [remove_start(creator, 'By ') for creator in traverse_obj(
                    json_obj, ('bylines', ..., 'renderedRepresentation'))])
            duration = int_or_none(json_obj.get('duration'))
            media_content = json_obj.get('renditions')
            formats, subtitles = self._extract_media_from_json(media_id, media_content)

            thumbnails = []
            for image in traverse_obj(json_obj, ('promotionalMedia', 'crops', ..., 'renditions', ...)):
                image_url = image.get('url')
                if not url_or_none(image_url):
                    continue
                thumbnails.append({
                    'url': image_url,
                    'width': int_or_none(image.get('width')),
                    'height': int_or_none(image.get('height')),
                })

            entries.append({
                'id': media_id,
                'title': title,
                'description': description,
                'duration': duration,
                'creator': creators,
                'formats': formats,
                'subtitles': subtitles,
                'thumbnails': thumbnails,
            })
        return entries

    def _json_from_graphql(self, id):
        # reference: `id-to-uri.js`
        namespace = uuid.UUID(self._DNS_UUID)
        video_uuid = uuid.uuid5(namespace, 'video')
        media_uuid = uuid.uuid5(video_uuid, id)

        payload = {
            "query": self._GRAPHQL_QUERY,
            "variables": {"id": f"nyt://video/{media_uuid}"}
        }

        headers = {
            "Content-Type": "application/json",
            "Nyt-App-Type": "vhs",
            "Nyt-App-Version": "v3.52.21",
            "Nyt-Token": self._TOKEN,
            "Origin": "https://cooking.nytimes.com",
            "Referer": "https://www.google.com/",
        }

        return self._download_json(
            self._GRAPHQL_API, id, note="Downloading json from GRAPHQL API",
            data=json.dumps(payload, separators=(',', ':')).encode(), headers=headers, fatal=False)

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)

        lead_video_id = self._search_regex(
            r'data-video-player-id="(\d+)"></div>', webpage, 'lead video', default=None)
        media_items = traverse_obj(
            get_elements_html_by_class('video-item', webpage), (..., {extract_attributes}, 'data-video-id'))
        title = self._html_search_meta(['og:title', 'twitter:title'], webpage)
        description = self._html_search_meta(['og:description', 'twitter:description'], webpage)
        creator = self._search_regex(
            r'<span itemprop="author">(.+)</span></p>', webpage, 'author', default=None)

        if media_items:
            media_items.append(lead_video_id)
            return self.playlist_result(self._build_playlist(media_items), page_id, title, description)

        json_obj = traverse_obj(self._json_from_graphql(lead_video_id) or {}, ('data', 'video'))
        duration = int_or_none(json_obj.get('duration'))

        media_content = json_obj.get('renditions')
        formats, subtitles = self._extract_media_from_json(lead_video_id, media_content)

        thumbnails = []
        for image in traverse_obj(json_obj, ('promotionalMedia', 'crops', ..., 'renditions', ...)):
            image_url = image.get('url')
            if not url_or_none(image_url):
                continue
            thumbnails.append({
                'url': image_url,
                'width': int_or_none(image.get('width')),
                'height': int_or_none(image.get('height')),
            })

        return {
            'id': lead_video_id,
            'title': title,
            'description': description,
            'duration': duration,
            'creator': creator,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
        }
