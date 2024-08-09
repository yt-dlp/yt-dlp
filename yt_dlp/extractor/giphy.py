import itertools
import re

from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    merge_dicts,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class GiphyBaseIE(InfoExtractor):
    _GIPHY_FE_WEB_API_KEY = 'Gc7131jiJuvI7IdN0HZ1D7nh0ow5BU6g'
    _GIPHY_FE_STORIES_AND_GIPHY_TV_API_KEY = '3eFQvabDx69SMoOemSPiYfh9FY0nzO9x'
    _GIPHY_MAX = 5000

    def _extract_formats(self, media, is_still=False):
        f = []
        for format_id in media:
            if ('_still' in format_id) == is_still:
                for key in [k for k, v in media[format_id].items() if str(v)[:4] == 'http']:
                    i = traverse_obj(media[format_id], {
                        'width': ('width', {int_or_none}),
                        'height': ('height', {int_or_none}),
                        'url': (key, {url_or_none}),
                    })
                    f.append({
                        'format_id': format_id,
                        **i,
                    })
        return f

    def _extract_info(self, gif_data, video_id):
        formats, thumbnails, subtitles, uploader = [], [], {}, {}
        # formats, thumbnails, subtitles
        if data := gif_data.get('video'):
            for lang in data.get('captions', {}):
                for key in data['captions'][lang]:
                    subtitles.setdefault(lang, []).append({'url': data['captions'][lang][key]})
            for category in ['assets', 'previews']:
                formats.extend(self._extract_formats(data.get(category, {})))
            if data.get('hls_manifest_url'):
                hls_fmts, hls_subs = self._extract_m3u8_formats_and_subtitles(
                    data['hls_manifest_url'], video_id, 'mp4', m3u8_id='hls', fatal=False)
                formats.extend(hls_fmts)
                self._merge_subtitles(hls_subs, target=subtitles)
            if data.get('dash_manifest_url'):
                dash_fmts, dash_subs = self._extract_mpd_formats_and_subtitles(
                    data['dash_manifest_url'], video_id, mpd_id='dash', fatal=False)
                formats.extend(dash_fmts)
                self._merge_subtitles(dash_subs, target=subtitles)
        if data := gif_data.get('images'):
            if data.get('looping'):
                data['looping']['height'] = traverse_obj(data, ('original_mp4', 'height', {int_or_none}))
                data['looping']['width'] = traverse_obj(data, ('original_mp4', 'width', {int_or_none}))
            sorted_data = dict(sorted(data.items(), reverse=True))
            formats.extend(self._extract_formats(sorted_data))
            thumbnails.extend(self._extract_formats(data, is_still=True))
        self._remove_duplicate_formats(formats)
        for f in formats:
            f.setdefault('http_headers', {})['Accept'] = 'video/*,image/*'
        for l in subtitles:
            for s in subtitles[l]:
                s.setdefault('http_headers', {})['Accept'] = 'text/*'
        for t in thumbnails:
            t.setdefault('http_headers', {})['Accept'] = 'image/*'
        # uploader
        if data := gif_data.get('user'):
            if isinstance(data, dict):
                uploader = traverse_obj(data, {
                    'uploader': (('display_name', 'name', 'attribution_display_name', 'username'),
                                 {lambda x: x or gif_data.get('username')}),
                    'uploader_id': ('username', {lambda x: x or gif_data.get('username')}),
                    'uploader_url': (('profile_url', 'website_url'),
                                     {lambda x: f'https://giphy.com{x}' if x and x[0] == '/' else url_or_none(x)}),
                }, get_all=False)
        # basic info
        info = {
            **traverse_obj(gif_data, {
                'id': ('id', {lambda x: x or video_id}),
                'title': ('title', {lambda x: x.strip() if x else ''}),
                'description': ((None, 'video'), ('alt_text', 'description'),
                                {lambda x: x.strip() if x and not x.startswith('Discover & share') else None}),
                'tags': ('tags', {list}),
                'age_limit': ('rating', {lambda x: 18 if x in ['r', 'nc-17'] else None}),
                'upload_date': (('import_datetime', 'create_datetime'),
                                {lambda x: x[:10].replace('-', '') if x else None}),
            }, get_all=False),
        }
        return {
            **info,
            **{k: v for k, v in uploader.items() if v is not None},
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _api_channel_feed(self, channel_id):
        count, offset = 0, 0
        query_url = f'https://giphy.com/api/v4/channels/{channel_id}/feed/?offset={offset}'
        for _ in itertools.count(1):
            search_results = self._download_json(query_url, channel_id, fatal=False,
                                                 note=f'Downloading feed data {offset + 1}-{offset + 25}')
            if not search_results or not search_results.get('results'):
                return
            for video in search_results['results']:
                yield {
                    **self._extract_info(video, video['id']),
                    'webpage_url': video['url'],
                }
            count += len(search_results.get('results'))
            if count >= (int_or_none(self.get_param('playlistend')) or (self._GIPHY_MAX + 1)):
                return
            query_url = url_or_none(search_results.get('next')) or ''
            offset = int(self._search_regex(r'offset=(\d+)', query_url, 'offset', default=0))
            # offset cannot exceed 5000
            if not query_url or offset > self._GIPHY_MAX:
                return


class GiphyIE(GiphyBaseIE):
    _VALID_URL = r'https?://giphy\.com/(?:clips|gifs|stickers|embed)/(?:.+[/-])?(?P<id>[^/]+)/?$'
    _TESTS = [{
        'url': 'https://giphy.com/gifs/l2JIcQ4UH5SoPtMJi',
        'info_dict': {
            'id': 'l2JIcQ4UH5SoPtMJi',
            'ext': 'mp4',
            'title': 'excited slow motion GIF by Cats the Musical',
            'tags': ['giphyupload', 'excited', 'cats', 'musical', 'flip', 'slow motion', 'somersault', 'cats musical'],
            'thumbnail': r're:^https?://.*',
            'upload_date': '20160125',
            'uploader': 'Cats the Musical',
            'uploader_id': 'catsmusical',
            'uploader_url': 'https://giphy.com/catsmusical/',
        },
    }, {
        'url': 'http://giphy.com/gifs/l3vR8BKU0m8uX2mAg',
        'info_dict': {
            'id': 'l3vR8BKU0m8uX2mAg',
            'ext': 'mp4',
            'title': 'Giphy video #l3vR8BKU0m8uX2mAg',
            'tags': ['giphyupload'],
            'thumbnail': r're:^https?://.*',
            'upload_date': '20161022',
            'uploader': 'gus123',
            'uploader_id': 'gus123',
            'uploader_url': 'https://giphy.com/channel/gus123/',
        },
    }, {
        'url': 'https://giphy.com/gifs/digitalpratik-digital-pratik-happy-fathers-day-dad-E1trcBzr59SGvmRDPY',
        'info_dict': {
            'id': 'E1trcBzr59SGvmRDPY',
            'ext': 'mp4',
            'title': 'Happy Fathers Day GIF by Digital Pratik',
            'tags': 'count:14',
            'thumbnail': r're:^https?://.*',
            'upload_date': '20210619',
            'uploader': 'Digital Pratik',
            'uploader_id': 'digitalpratik',
            'uploader_url': 'https://giphy.com/digitalpratik/',
        },
    }, {
        'url': 'https://giphy.com/clips/southpark-south-park-episode-4-season-20-YyOPrvilA8FdiuSiQi',
        'info_dict': {
            'id': 'YyOPrvilA8FdiuSiQi',
            'ext': 'mp4',
            'title': 'You Can\'t Break Up With Me',
            'description': 'South Park, Season 20, Episode 4, Wieners Out',
            'tags': 'count:16',
            'thumbnail': r're:^https?://.*',
            'upload_date': '20220516',
            'uploader': 'South Park',
            'uploader_id': 'southpark',
            'uploader_url': 'https://giphy.com/southpark',
        },
    }, {
        'url': 'https://giphy.com/stickers/mario-PFxFYEZNUavG8',
        'info_dict': {
            'id': 'PFxFYEZNUavG8',
            'ext': 'mp4',
            'title': 'nintendo mario STICKER',
            'tags': ['transparent', 'gaming', 'nintendo', 'mario', 'giphynintendos'],
            'thumbnail': r're:^https?://.*',
            'upload_date': '20160908',
        },
    }, {
        'url': 'https://giphy.com/embed/00xGP4zv8xENZ2tc3Y',
        'info_dict': {
            'id': '00xGP4zv8xENZ2tc3Y',
            'ext': 'mp4',
            'title': 'Love Is Blind Wow GIF by NETFLIX',
            'description': 'md5:89445e21c848eef12af249faef4fcf9f',
            'tags': 'count:24',
            'thumbnail': r're:^https?://.*',
            'upload_date': '20220214',
            'uploader': 'NETFLIX',
            'uploader_id': 'netflix',
            'uploader_url': 'https://giphy.com/netflix/',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url.replace('/embed/', '/gifs/'), video_id)

        title = (self._html_search_meta('twitter:title', webpage, default=None)
                 or self._og_search_title(webpage).replace(' - Find & Share on GIPHY', '').strip())
        description = (self._html_search_meta('twitter:description', webpage, default=None)
                       or self._og_search_description(webpage))
        description = description if not description.startswith('Discover & share') else None

        gif_data = {}
        # search for:  \"gif\":{\"type\":\"...},
        if json_str := self._html_search_regex(r'\\"\w+\\":({\\"type\\":\\"(?!emoji).*?is_dynamic\\":\w+}),',
                                               webpage, 'video_data', default=None):
            gif_data = self._parse_json(json_str.replace(r'\"', '"'), video_id)
        # search for:  gif: {"...},
        elif json_str := self._html_search_regex(r'\s+\w+:\s*({".*?}),\n\s+', webpage, 'video_data', default='{}'):
            gif_data = self._parse_json(json_str, video_id)

        info = self._extract_info(gif_data, video_id)

        if not info.get('formats'):
            formats = []
            if url := self._og_search_video_url(webpage, default=None):
                formats.append({
                    'format_id': determine_ext(url),
                    'width': int_or_none(self._og_search_property('video:width', webpage)),
                    'height': int_or_none(self._og_search_property('video:height', webpage)),
                    'url': url,
                })
            if url := self._og_search_thumbnail(webpage, default=None):
                formats.append({
                    'format_id': determine_ext(url),
                    'width': int_or_none(self._og_search_property('image:width', webpage)),
                    'height': int_or_none(self._og_search_property('image:height', webpage)),
                    'url': url,
                })
            if url := self._html_search_meta('twitter:image', webpage, default=None):
                thumbnails = [{
                    'width': int_or_none(self._html_search_meta('twitter:image:width', webpage, default=None)),
                    'height': int_or_none(self._html_search_meta('twitter:image:height', webpage, default=None)),
                    'url': url,
                }]
            info['formats'] = formats
            if not info.get('thumbnails'):
                info['thumbnails'] = thumbnails

        if not info.get('uploader'):
            uploader = {}
            if data := gif_data.get('user'):
                if isinstance(data, str):
                    idx = data.replace('$', '')
                    if json_str := self._html_search_regex(rf'\\n{idx}:({{.*?}})\\n\w+:',
                                                           webpage, 'uploader_data', default=None):
                        json_str = re.sub(r'"\]\)self\.__next_f\.push\(\[\d+,"', '', json_str).replace(r'\"', '"')
                        data = self._parse_json(json_str, video_id, fatal=False)
                    if isinstance(data, dict):
                        uploader = traverse_obj(data, {
                            'uploader': (('display_name', 'name', 'attribution_display_name', 'username'),
                                         {lambda x: x or gif_data.get('username')}),
                            'uploader_id': ('username', {str_or_none}),
                            'uploader_url': (('profile_url', 'website_url'),
                                             {lambda x: f'https://giphy.com{x}' if x and x[0] == '/' else url_or_none(x)}),
                        }, get_all=False)
            if not uploader:
                up_id = (gif_data.get('username')
                         or self._html_search_regex(r'<div>@(\w+)</div>', webpage, 'uploader_id', default=None)
                         or self._html_search_regex(r'"woff2"/><link[^>]+\.giphy\.com/(?:channel_assets|avatars)/(.+?)/',
                                                    webpage, 'uploader_id', default=None))
                up_name = (title[(title.rfind(' by ') + 4):] if title.rfind(' by ') > 0 else None
                           or self._html_search_regex(r'(?s)<h2\b[^>]*>([^<]+)</h2>', webpage, 'uploader', default=None)
                           or self._html_search_regex(r'twitter:creator"[^>]+="((?!@giphy").*?)"', webpage, 'uploader', default=None)
                           or up_id)
                uploader = {
                    'uploader': up_name,
                    'uploader_id': up_id,
                    'uploader_url': (f'https://giphy.com/channel/{up_id}/' if up_id else None),
                }
            info = merge_dicts(info, {**{k: v for k, v in uploader.items() if v is not None}})

        return {
            **merge_dicts(info, {
                'title': title,
                'description': description,
            }),
        }


class GiphyChannelPageIE(GiphyBaseIE):
    _VALID_URL = r'https?://giphy\.com/(?!(?:clips|gifs|stickers|stories|search|embed)/)(?:.+/)?(?P<id>[^/]+)/?$'
    _TESTS = [{
        'url': 'https://giphy.com/catsmusical/',
        'playlist_count': 10,
        'info_dict': {
            'id': '8707',
            'title': 'Cats the Musical',
            'uploader_id': 'catsmusical',
            'uploader_url': 'https://giphy.com/channel/catsmusical',
        },
    }, {
        'url': 'https://giphy.com/channel/catsmusical',
        'playlist_count': 10,
        'info_dict': {
            'id': '8707',
            'title': 'Cats the Musical',
            'uploader_id': 'catsmusical',
            'uploader_url': 'https://giphy.com/channel/catsmusical',
        },
    }, {
        'url': 'https://giphy.com/southpark/reactions/lol',
        'playlist_count': 42,
        'info_dict': {
            'id': '1044',
            'title': 'LOL',
            'uploader_id': 'southpark',
            'uploader_url': 'https://giphy.com/channel/southpark',
        },
    }, {
        'url': 'https://giphy.com/corgiyolk/cute-and-wholesome-corgi',
        'playlist_count': 14,
        'info_dict': {
            'id': '34458076',
            'title': 'Cute and Wholesome corgi',
            'uploader_id': 'corgiyolk',
            'uploader_url': 'https://giphy.com/channel/corgiyolk',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # search for:  {"channelId": ...} or {..., "channel_id": ...,
        if channel_id := self._html_search_regex(r'\{[^\}\n]*"channel_?[iI]d":\s*"?([^",\}]+)[",\}]',
                                                 webpage, 'channel_id', default=None):
            uploader_id = self._html_search_meta('twitter:creator', webpage).replace('@', '').lower()
            entries = []
            for i in self._api_channel_feed(channel_id):
                entries.append(i)

            return {
                'id': channel_id,
                'title': (self._html_search_meta('twitter:title', webpage)
                          or self._og_search_title(webpage)
                          ).replace(' GIFs on GIPHY - Be Animated', '').strip(),
                'uploader_id': uploader_id,
                'uploader_url': f'https://giphy.com/channel/{uploader_id}' if uploader_id != 'giphy' else None,
                '_type': 'playlist',
                'entries': entries,
            }


class GiphyChannelIE(GiphyBaseIE, SearchInfoExtractor):
    IE_NAME = 'giphy:channel'
    IE_DESC = 'Giphy Channel'
    _SEARCH_KEY = 'giphychannel'
    _TESTS = [{
        'url': 'giphychannel30:pbsnature',
        'playlist_count': 30,
        'info_dict': {
            'id': 'pbsnature',
            'title': 'pbsnature',
        },
    }]

    def _search_results(self, query):
        if webpage := self._download_webpage(f'https://giphy.com/channel/{query}', query):
            if channel_id := self._html_search_regex(r'\{[^\}\n]*"channel_?[iI]d":\s*"?([^",\}]+)[",\}]',
                                                     webpage, 'channel_id', default=None):
                return self._api_channel_feed(channel_id)


class GiphySearchIE(GiphyBaseIE, SearchInfoExtractor):
    IE_NAME = 'giphy:search'
    IE_DESC = 'Giphy Search'
    _SEARCH_KEY = 'giphysearch'
    _TESTS = [{
        'url': 'giphysearch20:super mario',
        'playlist_count': 20,
        'info_dict': {
            'id': 'super mario',
            'title': 'super mario',
        },
    }, {
        'url': 'giphysearch40:mickey&type=clips,stickers',
        'playlist_count': 40,
        'info_dict': {
            'id': 'mickey&type=clips,stickers',
            'title': 'mickey&type=clips,stickers',
        },
    }]

    def _search_results(self, query):
        def search_query(query, offset, limit, category):
            # search api:
            # https://api.giphy.com/v1/gifs/search?rating=pg-13&offset=40&limit=15&type=gifs&q={query}&excludeDynamicResults=undefined&api_key=Gc7131jiJuvI7IdN0HZ1D7nh0ow5BU6g&pingback_id=1904d6e524cee33d
            return self._download_json(
                f'https://api.giphy.com/v1/{category}/search', query,
                note=f'Downloading {category} result {offset + 1}-{offset + limit}', query={
                    'rating': 'r',      # MPA film rating
                    'offset': offset,
                    'limit': limit,
                    'type': category,   # known types: 'clips', 'gifs', 'stickers', 'text', 'videos'
                    'q': query,
                    'excludeDynamicResults': 'undefined',
                    'api_key': self._GIPHY_FE_WEB_API_KEY,
                })

        # type: comma delimited list
        types = self._search_regex(r'&type=([^&]+)', query, 'type', default='gifs,stickers,videos')
        types = [(f'{x}s' if x[-1] != 's' and any(x in t for t in ['clips', 'gifs', 'stickers', 'videos']) else x)
                 for x in [x.strip() for x in types.lower().split(',')]]
        query = query.split('&type=')[0]

        offset, limit = 0, 50
        types_done = []
        for _ in itertools.count(1):
            for t in types:
                if t not in types_done:
                    search_type = 'videos' if t == 'clips' else t       # clips use 'videos' type
                    search_results = search_query(query, offset, limit, search_type)
                    if not search_results.get('data'):
                        self.to_screen(f'{query}: {offset} {t} found')
                        types_done.append(t)
                    else:
                        for video in search_results['data']:
                            yield {
                                **self._extract_info(video, video['id']),
                                'webpage_url': video['url'],
                            }
                        if len(search_results['data']) < limit:
                            total = offset + len(search_results['data'])
                            self.to_screen(f'{query}: {total} {t} found')
                            types_done.append(t)
            if len(types) > len(types_done):
                offset += limit
                if offset >= self._GIPHY_MAX:
                    return
            else:
                return


class GiphySearchURLIE(GiphyBaseIE):
    _VALID_URL = r'https?://giphy\.com/search/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://giphy.com/search/carcinoma',
        'playlist_count': 13,
        'info_dict': {
            'id': 'carcinoma',
            'title': 'carcinoma',
        },
    }]

    def _real_extract(self, url):
        if query := self._match_id(url):
            query = query.replace('-', ' ')
            return self.url_result(url=f'giphysearchall:{query}', url_transparent=True)


class GiphyStoriesIE(GiphyBaseIE):
    _VALID_URL = r'https?://giphy\.com/stories/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://giphy.com/stories/indian-garyvee-de56ee78-adb5',
        'playlist_count': 6,
        'info_dict': {
            'id': 'de56ee78-adb5-428e-afb6-765bb489c4fc',
            'title': 'Indian Garyvee',
            'description': 'md5:468a8e2c898225baac05e32dcafe313b',
            'tags': [],
            'upload_date': '20190710',
            'uploader': 'Digital Pratik',
            'uploader_id': 'digitalpratik',
            'uploader_url': 'https://giphy.com/digitalpratik',
        },
    }, {
        'url': 'https://giphy.com/stories/a-2021-oscars-wrap-up-161cda9a-4517',
        'playlist_count': 10,
        'info_dict': {
            'id': '161cda9a-4517-473b-9fea-6731af6c0d49',
            'title': 'A 2021 Oscars Wrap-Up',
            'description': 'What were the best moments in GIFs? Glad you asked!',
            'tags': [],
            'upload_date': '20210426',
            'uploader': 'Entertainment GIFs',
            'uploader_id': 'entertainment',
            'uploader_url': 'https://giphy.com/entertainment',
        },
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        # https://x.giphy.com/v1/stories/slug/{slug}?api_key=3eFQvabDx69SMoOemSPiYfh9FY0nzO9x
        story = self._download_json(f'https://x.giphy.com/v1/stories/slug/{slug}?api_key={self._GIPHY_FE_STORIES_AND_GIPHY_TV_API_KEY}', slug)

        if data := story.get('data'):
            entries = []
            for video in data.get('gifs'):
                entries.append({
                    **self._extract_info(video['gif'], video['gif']['id']),
                    'description': video['caption'],
                    'webpage_url': video['gif']['url'],
                })
            info = traverse_obj(data, {
                'id': ('story_id', {lambda x: x or slug}),
                'title': ('title', {str_or_none}),
                'description': ('description', {str_or_none}),
                'tags': ('tags', {list}),
                'thumbnails': ('cover_gif', 'gif', 'images', {dict}, {lambda x: self._extract_formats(x, is_still=True)}),
                'upload_date': (('create_datetime', 'publish_datetime'),
                                {lambda x: x[:10].replace('-', '') if x else None}),
                'uploader': ('user', ('display_name', 'username'), {str_or_none}),
                'uploader_id': ('user', 'username', {str_or_none}),
                'uploader_url': ('user', ('profile_url', 'website_url'),
                                 {lambda x: f'https://giphy.com{x}' if x and x[0] == '/' else url_or_none(x)}),
            }, get_all=False)

            return {
                **info,
                '_type': 'playlist',
                'entries': entries,
            }
