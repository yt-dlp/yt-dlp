import base64
import hashlib
import itertools
import functools
import re
import math

from .common import InfoExtractor, SearchInfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urlparse,
    compat_urllib_parse_urlparse
)
from ..utils import (
    ExtractorError,
    filter_dict,
    int_or_none,
    float_or_none,
    mimetype2ext,
    parse_iso8601,
    qualities,
    traverse_obj,
    parse_count,
    smuggle_url,
    srt_subtitles_timecode,
    str_or_none,
    strip_jsonp,
    unified_timestamp,
    unsmuggle_url,
    urlencode_postdata,
    url_or_none,
    OnDemandPagedList
)


class BiliBiliIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:(?:www|bangumi)\.)?
                        bilibili\.(?:tv|com)/
                        (?:
                            (?:
                                video/[aA][vV]|
                                anime/(?P<anime_id>\d+)/play\#
                            )(?P<id>\d+)|
                            (s/)?video/[bB][vV](?P<id_bv>[^/?#&]+)
                        )
                        (?:/?\?p=(?P<page>\d+))?
                    '''

    _TESTS = [{
        'url': 'http://www.bilibili.com/video/av1074402/',
        'md5': '7ac275ec84a99a6552c5d229659a0fe1',
        'info_dict': {
            'id': '1074402_part1',
            'ext': 'mp4',
            'title': '【金坷垃】金泡沫',
            'uploader_id': '156160',
            'uploader': '菊子桑',
            'upload_date': '20140420',
            'description': 'md5:ce18c2a2d2193f0df2917d270f2e5923',
            'timestamp': 1398012678,
            'tags': ['顶上去报复社会', '该来的总会来的', '金克拉是检验歌曲的唯一标准', '坷垃教主', '金坷垃', '邓紫棋', '治愈系坷垃'],
            'bv_id': 'BV11x411K7CN',
            'cid': '1554319',
            'thumbnail': 'http://i2.hdslb.com/bfs/archive/c79a8cf0347cd7a897c53a2f756e96aead128e8c.jpg',
            'duration': 308.36,
        },
    }, {
        # Tested in BiliBiliBangumiIE
        'url': 'http://bangumi.bilibili.com/anime/1869/play#40062',
        'only_matching': True,
    }, {
        # bilibili.tv
        'url': 'http://www.bilibili.tv/video/av1074402/',
        'only_matching': True,
    }, {
        'url': 'http://bangumi.bilibili.com/anime/5802/play#100643',
        'md5': '3f721ad1e75030cc06faf73587cfec57',
        'info_dict': {
            'id': '100643_part1',
            'ext': 'mp4',
            'title': 'CHAOS;CHILD',
            'description': '如果你是神明，并且能够让妄想成为现实。那你会进行怎么样的妄想？是淫靡的世界？独裁社会？毁灭性的制裁？还是……2015年，涩谷。从6年前发生的大灾害“涩谷地震”之后复兴了的这个街区里新设立的私立高中...',
        },
        'skip': 'Geo-restricted to China',
    }, {
        'url': 'http://www.bilibili.com/video/av8903802/',
        'info_dict': {
            'id': '8903802_part1',
            'ext': 'mp4',
            'title': '阿滴英文｜英文歌分享#6 "Closer',
            'upload_date': '20170301',
            'description': '滴妹今天唱Closer給你聽! 有史以来，被推最多次也是最久的歌曲，其实歌词跟我原本想像差蛮多的，不过还是好听！ 微博@阿滴英文',
            'timestamp': 1488382634,
            'uploader_id': '65880958',
            'uploader': '阿滴英文',
            'thumbnail': 'http://i2.hdslb.com/bfs/archive/49267ce20bc246be6304bf369a3ded0256854c23.jpg',
            'cid': '14694589',
            'duration': 554.117,
            'bv_id': 'BV13x41117TL',
            'tags': ['人文', '英语', '文化', '公开课', '阿滴英文'],
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # new BV video id format
        'url': 'https://www.bilibili.com/video/BV1JE411F741',
        'only_matching': True,
    }, {
        # Anthology
        'url': 'https://www.bilibili.com/video/BV1bK411W797',
        'info_dict': {
            'id': 'BV1bK411W797',
            'title': '物语中的人物是如何吐槽自己的OP的'
        },
        'playlist_count': 17,
    }, {
        # Correct matching of single and double quotes in title
        'url': 'https://www.bilibili.com/video/BV1NY411E7Rx/',
        'info_dict': {
            'id': '255513412_part1',
            'ext': 'mp4',
            'title': 'Vid"eo" Te\'st',
            'cid': '570602418',
            'thumbnail': 'http://i2.hdslb.com/bfs/archive/0c0de5a90b6d5b991b8dcc6cde0afbf71d564791.jpg',
            'upload_date': '20220408',
            'timestamp': 1649436552,
            'description': 'Vid"eo" Te\'st',
            'uploader_id': '1630758804',
            'bv_id': 'BV1NY411E7Rx',
            'duration': 60.394,
            'uploader': 'bili_31244483705',
            'tags': ['VLOG'],
        },
        'params': {
            'skip_download': True,
        },
    }]

    _APP_KEY = 'iVGUTjsxvpLeuDCf'
    _BILIBILI_KEY = 'aHRmhWMLkdeMuILqORnYZocwMBpMEOdt'

    def _report_error(self, result):
        if 'message' in result:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, result['message']), expected=True)
        elif 'code' in result:
            raise ExtractorError('%s returns error %d' % (self.IE_NAME, result['code']), expected=True)
        else:
            raise ExtractorError('Can\'t extract Bangumi episode ID')

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        mobj = self._match_valid_url(url)
        video_id = mobj.group('id_bv') or mobj.group('id')

        av_id, bv_id = self._get_video_id_set(video_id, mobj.group('id_bv') is not None)
        video_id = av_id

        info = {}
        anime_id = mobj.group('anime_id')
        page_id = mobj.group('page')
        webpage = self._download_webpage(url, video_id)

        # Bilibili anthologies are similar to playlists but all videos share the same video ID as the anthology itself.
        # If the video has no page argument, check to see if it's an anthology
        if page_id is None:
            if not self.get_param('noplaylist'):
                r = self._extract_anthology_entries(bv_id, video_id, webpage)
                if r is not None:
                    self.to_screen('Downloading anthology %s - add --no-playlist to just download video' % video_id)
                    return r
            else:
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)

        if 'anime/' not in url:
            cid = self._search_regex(
                r'\bcid(?:["\']:|=)(\d+),["\']page(?:["\']:|=)' + str(page_id), webpage, 'cid',
                default=None
            ) or self._search_regex(
                r'\bcid(?:["\']:|=)(\d+)', webpage, 'cid',
                default=None
            ) or compat_parse_qs(self._search_regex(
                [r'EmbedPlayer\([^)]+,\s*"([^"]+)"\)',
                 r'EmbedPlayer\([^)]+,\s*\\"([^"]+)\\"\)',
                 r'<iframe[^>]+src="https://secure\.bilibili\.com/secure,([^"]+)"'],
                webpage, 'player parameters'))['cid'][0]
        else:
            if 'no_bangumi_tip' not in smuggled_data:
                self.to_screen('Downloading episode %s. To download all videos in anime %s, re-run yt-dlp with %s' % (
                    video_id, anime_id, compat_urlparse.urljoin(url, '//bangumi.bilibili.com/anime/%s' % anime_id)))
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': url
            }
            headers.update(self.geo_verification_headers())

            js = self._download_json(
                'http://bangumi.bilibili.com/web_api/get_source', video_id,
                data=urlencode_postdata({'episode_id': video_id}),
                headers=headers)
            if 'result' not in js:
                self._report_error(js)
            cid = js['result']['cid']

        headers = {
            'Accept': 'application/json',
            'Referer': url
        }
        headers.update(self.geo_verification_headers())

        video_info = self._parse_json(
            self._search_regex(r'window.__playinfo__\s*=\s*({.+?})</script>', webpage, 'video info', default=None) or '{}',
            video_id, fatal=False)
        video_info = video_info.get('data') or {}

        durl = traverse_obj(video_info, ('dash', 'video'))
        audios = traverse_obj(video_info, ('dash', 'audio')) or []
        flac_audio = traverse_obj(video_info, ('dash', 'flac', 'audio'))
        if flac_audio:
            audios.append(flac_audio)
        entries = []

        RENDITIONS = ('qn=80&quality=80&type=', 'quality=2&type=mp4')
        for num, rendition in enumerate(RENDITIONS, start=1):
            payload = 'appkey=%s&cid=%s&otype=json&%s' % (self._APP_KEY, cid, rendition)
            sign = hashlib.md5((payload + self._BILIBILI_KEY).encode('utf-8')).hexdigest()
            if not video_info:
                video_info = self._download_json(
                    'http://interface.bilibili.com/v2/playurl?%s&sign=%s' % (payload, sign),
                    video_id, note='Downloading video info page',
                    headers=headers, fatal=num == len(RENDITIONS))
                if not video_info:
                    continue

            if not durl and 'durl' not in video_info:
                if num < len(RENDITIONS):
                    continue
                self._report_error(video_info)

            formats = []
            for idx, durl in enumerate(durl or video_info['durl']):
                formats.append({
                    'url': durl.get('baseUrl') or durl.get('base_url') or durl.get('url'),
                    'ext': mimetype2ext(durl.get('mimeType') or durl.get('mime_type')),
                    'fps': int_or_none(durl.get('frameRate') or durl.get('frame_rate')),
                    'width': int_or_none(durl.get('width')),
                    'height': int_or_none(durl.get('height')),
                    'vcodec': durl.get('codecs'),
                    'acodec': 'none' if audios else None,
                    'tbr': float_or_none(durl.get('bandwidth'), scale=1000),
                    'filesize': int_or_none(durl.get('size')),
                })
                for backup_url in traverse_obj(durl, 'backup_url', expected_type=list) or []:
                    formats.append({
                        'url': backup_url,
                        'quality': -2 if 'hd.mp4' in backup_url else -3,
                    })

            for audio in audios:
                formats.append({
                    'url': audio.get('baseUrl') or audio.get('base_url') or audio.get('url'),
                    'ext': mimetype2ext(audio.get('mimeType') or audio.get('mime_type')),
                    'fps': int_or_none(audio.get('frameRate') or audio.get('frame_rate')),
                    'width': int_or_none(audio.get('width')),
                    'height': int_or_none(audio.get('height')),
                    'acodec': audio.get('codecs'),
                    'vcodec': 'none',
                    'tbr': float_or_none(audio.get('bandwidth'), scale=1000),
                    'filesize': int_or_none(audio.get('size'))
                })
                for backup_url in traverse_obj(audio, 'backup_url', expected_type=list) or []:
                    formats.append({
                        'url': backup_url,
                        # backup URLs have lower priorities
                        'quality': -3,
                    })

            info.update({
                'id': video_id,
                'duration': float_or_none(durl.get('length'), 1000),
                'formats': formats,
                'http_headers': {
                    'Referer': url,
                },
            })
            break

        self._sort_formats(formats)

        title = self._html_search_regex((
            r'<h1[^>]+title=(["])(?P<content>[^"]+)',
            r'<h1[^>]+title=([\'])(?P<content>[^\']+)',
            r'(?s)<h1[^>]*>(?P<content>.+?)</h1>',
            self._meta_regex('title')
        ), webpage, 'title', group='content', fatal=False)

        # Get part title for anthologies
        if page_id is not None:
            # TODO: The json is already downloaded by _extract_anthology_entries. Don't redownload for each video.
            part_info = traverse_obj(self._download_json(
                f'https://api.bilibili.com/x/player/pagelist?bvid={bv_id}&jsonp=jsonp',
                video_id, note='Extracting videos in anthology'), 'data', expected_type=list)
            title = title if len(part_info) == 1 else traverse_obj(part_info, (int(page_id) - 1, 'part')) or title

        description = self._html_search_meta('description', webpage)
        timestamp = unified_timestamp(self._html_search_regex(
            r'<time[^>]+datetime="([^"]+)"', webpage, 'upload time',
            default=None) or self._html_search_meta(
            'uploadDate', webpage, 'timestamp', default=None))
        thumbnail = self._html_search_meta(['og:image', 'thumbnailUrl'], webpage)

        # TODO 'view_count' requires deobfuscating Javascript
        info.update({
            'id': f'{video_id}_part{page_id or 1}',
            'cid': cid,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'thumbnail': thumbnail,
            'duration': float_or_none(video_info.get('timelength'), scale=1000),
        })

        uploader_mobj = re.search(
            r'<a[^>]+href="(?:https?:)?//space\.bilibili\.com/(?P<id>\d+)"[^>]*>\s*(?P<name>[^<]+?)\s*<',
            webpage)
        if uploader_mobj:
            info.update({
                'uploader': uploader_mobj.group('name').strip(),
                'uploader_id': uploader_mobj.group('id'),
            })

        if not info.get('uploader'):
            info['uploader'] = self._html_search_meta(
                'author', webpage, 'uploader', default=None)

        top_level_info = {
            'tags': traverse_obj(self._download_json(
                f'https://api.bilibili.com/x/tag/archive/tags?aid={video_id}',
                video_id, fatal=False, note='Downloading tags'), ('data', ..., 'tag_name')),
        }

        info['subtitles'] = {
            'danmaku': [{
                'ext': 'xml',
                'url': f'https://comment.bilibili.com/{cid}.xml',
            }]
        }

        r'''
        # Requires https://github.com/m13253/danmaku2ass which is licenced under GPL3
        # See https://github.com/animelover1984/youtube-dl

        raw_danmaku = self._download_webpage(
            f'https://comment.bilibili.com/{cid}.xml', video_id, fatal=False, note='Downloading danmaku comments')
        danmaku = NiconicoIE.CreateDanmaku(raw_danmaku, commentType='Bilibili', x=1024, y=576)
        entries[0]['subtitles'] = {
            'danmaku': [{
                'ext': 'ass',
                'data': danmaku
            }]
        }
        '''

        top_level_info['__post_extractor'] = self.extract_comments(video_id)

        for entry in entries:
            entry.update(info)

        if len(entries) == 1:
            entries[0].update(top_level_info)
            return entries[0]

        for idx, entry in enumerate(entries):
            entry['id'] = '%s_part%d' % (video_id, (idx + 1))

        return {
            'id': str(video_id),
            'bv_id': bv_id,
            'title': title,
            'description': description,
            **info, **top_level_info
        }

    def _extract_anthology_entries(self, bv_id, video_id, webpage):
        title = self._html_search_regex(
            (r'<h1[^>]+\btitle=(["\'])(?P<title>(?:(?!\1).)+)\1',
             r'(?s)<h1[^>]*>(?P<title>.+?)</h1>',
             r'<title>(?P<title>.+?)</title>'), webpage, 'title',
            group='title')
        json_data = self._download_json(
            f'https://api.bilibili.com/x/player/pagelist?bvid={bv_id}&jsonp=jsonp',
            video_id, note='Extracting videos in anthology')

        if json_data['data']:
            return self.playlist_from_matches(
                json_data['data'], bv_id, title, ie=BiliBiliIE.ie_key(),
                getter=lambda entry: 'https://www.bilibili.com/video/%s?p=%d' % (bv_id, entry['page']))

    def _get_video_id_set(self, id, is_bv):
        query = {'bvid': id} if is_bv else {'aid': id}
        response = self._download_json(
            "http://api.bilibili.cn/x/web-interface/view",
            id, query=query,
            note='Grabbing original ID via API')

        if response['code'] == -400:
            raise ExtractorError('Video ID does not exist', expected=True, video_id=id)
        elif response['code'] != 0:
            raise ExtractorError(f'Unknown error occurred during API check (code {response["code"]})',
                                 expected=True, video_id=id)
        return response['data']['aid'], response['data']['bvid']

    def _get_comments(self, video_id, commentPageNumber=0):
        for idx in itertools.count(1):
            replies = traverse_obj(
                self._download_json(
                    f'https://api.bilibili.com/x/v2/reply?pn={idx}&oid={video_id}&type=1&jsonp=jsonp&sort=2&_=1567227301685',
                    video_id, note=f'Extracting comments from page {idx}', fatal=False),
                ('data', 'replies'))
            if not replies:
                return
            for children in map(self._get_all_children, replies):
                yield from children

    def _get_all_children(self, reply):
        yield {
            'author': traverse_obj(reply, ('member', 'uname')),
            'author_id': traverse_obj(reply, ('member', 'mid')),
            'id': reply.get('rpid'),
            'text': traverse_obj(reply, ('content', 'message')),
            'timestamp': reply.get('ctime'),
            'parent': reply.get('parent') or 'root',
        }
        for children in map(self._get_all_children, reply.get('replies') or []):
            yield from children


class BiliBiliBangumiIE(InfoExtractor):
    _VALID_URL = r'https?://bangumi\.bilibili\.com/anime/(?P<id>\d+)'

    IE_NAME = 'bangumi.bilibili.com'
    IE_DESC = 'BiliBili番剧'

    _TESTS = [{
        'url': 'http://bangumi.bilibili.com/anime/1869',
        'info_dict': {
            'id': '1869',
            'title': '混沌武士',
            'description': 'md5:6a9622b911565794c11f25f81d6a97d2',
        },
        'playlist_count': 26,
    }, {
        'url': 'http://bangumi.bilibili.com/anime/1869',
        'info_dict': {
            'id': '1869',
            'title': '混沌武士',
            'description': 'md5:6a9622b911565794c11f25f81d6a97d2',
        },
        'playlist': [{
            'md5': '91da8621454dd58316851c27c68b0c13',
            'info_dict': {
                'id': '40062',
                'ext': 'mp4',
                'title': '混沌武士',
                'description': '故事发生在日本的江户时代。风是一个小酒馆的打工女。一日，酒馆里来了一群恶霸，虽然他们的举动令风十分不满，但是毕竟风只是一届女流，无法对他们采取什么行动，只能在心里嘟哝。这时，酒家里又进来了个“不良份子...',
                'timestamp': 1414538739,
                'upload_date': '20141028',
                'episode': '疾风怒涛 Tempestuous Temperaments',
                'episode_number': 1,
            },
        }],
        'params': {
            'playlist_items': '1',
        },
    }]

    @classmethod
    def suitable(cls, url):
        return False if BiliBiliIE.suitable(url) else super(BiliBiliBangumiIE, cls).suitable(url)

    def _real_extract(self, url):
        bangumi_id = self._match_id(url)

        # Sometimes this API returns a JSONP response
        season_info = self._download_json(
            'http://bangumi.bilibili.com/jsonp/seasoninfo/%s.ver' % bangumi_id,
            bangumi_id, transform_source=strip_jsonp)['result']

        entries = [{
            '_type': 'url_transparent',
            'url': smuggle_url(episode['webplay_url'], {'no_bangumi_tip': 1}),
            'ie_key': BiliBiliIE.ie_key(),
            'timestamp': parse_iso8601(episode.get('update_time'), delimiter=' '),
            'episode': episode.get('index_title'),
            'episode_number': int_or_none(episode.get('index')),
        } for episode in season_info['episodes']]

        entries = sorted(entries, key=lambda entry: entry.get('episode_number'))

        return self.playlist_result(
            entries, bangumi_id,
            season_info.get('bangumi_title'), season_info.get('evaluate'))


class BilibiliChannelIE(InfoExtractor):
    _VALID_URL = r'https?://space.bilibili\.com/(?P<id>\d+)'
    _API_URL = "https://api.bilibili.com/x/space/arc/search?mid=%s&pn=%d&jsonp=jsonp"
    _TESTS = [{
        'url': 'https://space.bilibili.com/3985676/video',
        'info_dict': {},
        'playlist_mincount': 112,
    }]

    def _entries(self, list_id):
        count, max_count = 0, None

        for page_num in itertools.count(1):
            data = self._download_json(
                self._API_URL % (list_id, page_num), list_id, note=f'Downloading page {page_num}')['data']

            max_count = max_count or traverse_obj(data, ('page', 'count'))

            entries = traverse_obj(data, ('list', 'vlist'))
            if not entries:
                return
            for entry in entries:
                yield self.url_result(
                    'https://www.bilibili.com/video/%s' % entry['bvid'],
                    BiliBiliIE.ie_key(), entry['bvid'])

            count += len(entries)
            if max_count and count >= max_count:
                return

    def _real_extract(self, url):
        list_id = self._match_id(url)
        return self.playlist_result(self._entries(list_id), list_id)


class BilibiliCategoryIE(InfoExtractor):
    IE_NAME = 'Bilibili category extractor'
    _MAX_RESULTS = 1000000
    _VALID_URL = r'https?://www\.bilibili\.com/v/[a-zA-Z]+\/[a-zA-Z]+'
    _TESTS = [{
        'url': 'https://www.bilibili.com/v/kichiku/mad',
        'info_dict': {
            'id': 'kichiku: mad',
            'title': 'kichiku: mad'
        },
        'playlist_mincount': 45,
        'params': {
            'playlistend': 45
        }
    }]

    def _fetch_page(self, api_url, num_pages, query, page_num):
        parsed_json = self._download_json(
            api_url, query, query={'Search_key': query, 'pn': page_num},
            note='Extracting results from page %s of %s' % (page_num, num_pages))

        video_list = traverse_obj(parsed_json, ('data', 'archives'), expected_type=list)
        if not video_list:
            raise ExtractorError('Failed to retrieve video list for page %d' % page_num)

        for video in video_list:
            yield self.url_result(
                'https://www.bilibili.com/video/%s' % video['bvid'], 'BiliBili', video['bvid'])

    def _entries(self, category, subcategory, query):
        # map of categories : subcategories : RIDs
        rid_map = {
            'kichiku': {
                'mad': 26,
                'manual_vocaloid': 126,
                'guide': 22,
                'theatre': 216,
                'course': 127
            },
        }

        if category not in rid_map:
            raise ExtractorError(
                f'The category {category} isn\'t supported. Supported categories: {list(rid_map.keys())}')
        if subcategory not in rid_map[category]:
            raise ExtractorError(
                f'The subcategory {subcategory} isn\'t supported for this category. Supported subcategories: {list(rid_map[category].keys())}')
        rid_value = rid_map[category][subcategory]

        api_url = 'https://api.bilibili.com/x/web-interface/newlist?rid=%d&type=1&ps=20&jsonp=jsonp' % rid_value
        page_json = self._download_json(api_url, query, query={'Search_key': query, 'pn': '1'})
        page_data = traverse_obj(page_json, ('data', 'page'), expected_type=dict)
        count, size = int_or_none(page_data.get('count')), int_or_none(page_data.get('size'))
        if count is None or not size:
            raise ExtractorError('Failed to calculate either page count or size')

        num_pages = math.ceil(count / size)

        return OnDemandPagedList(functools.partial(
            self._fetch_page, api_url, num_pages, query), size)

    def _real_extract(self, url):
        u = compat_urllib_parse_urlparse(url)
        category, subcategory = u.path.split('/')[2:4]
        query = '%s: %s' % (category, subcategory)

        return self.playlist_result(self._entries(category, subcategory, query), query, query)


class BiliBiliSearchIE(SearchInfoExtractor):
    IE_DESC = 'Bilibili video search'
    _MAX_RESULTS = 100000
    _SEARCH_KEY = 'bilisearch'

    def _search_results(self, query):
        for page_num in itertools.count(1):
            videos = self._download_json(
                'https://api.bilibili.com/x/web-interface/search/type', query,
                note=f'Extracting results from page {page_num}', query={
                    'Search_key': query,
                    'keyword': query,
                    'page': page_num,
                    'context': '',
                    'duration': 0,
                    'tids_2': '',
                    '__refresh__': 'true',
                    'search_type': 'video',
                    'tids': 0,
                    'highlight': 1,
                })['data'].get('result')
            if not videos:
                break
            for video in videos:
                yield self.url_result(video['arcurl'], 'BiliBili', str(video['aid']))


class BilibiliAudioBaseIE(InfoExtractor):
    def _call_api(self, path, sid, query=None):
        if not query:
            query = {'sid': sid}
        return self._download_json(
            'https://www.bilibili.com/audio/music-service-c/web/' + path,
            sid, query=query)['data']


class BilibiliAudioIE(BilibiliAudioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/audio/au(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.bilibili.com/audio/au1003142',
        'md5': 'fec4987014ec94ef9e666d4d158ad03b',
        'info_dict': {
            'id': '1003142',
            'ext': 'm4a',
            'title': '【tsukimi】YELLOW / 神山羊',
            'artist': 'tsukimi',
            'comment_count': int,
            'description': 'YELLOW的mp3版！',
            'duration': 183,
            'subtitles': {
                'origin': [{
                    'ext': 'lrc',
                }],
            },
            'thumbnail': r're:^https?://.+\.jpg',
            'timestamp': 1564836614,
            'upload_date': '20190803',
            'uploader': 'tsukimi-つきみぐー',
            'view_count': int,
        },
    }

    def _real_extract(self, url):
        au_id = self._match_id(url)

        play_data = self._call_api('url', au_id)
        formats = [{
            'url': play_data['cdns'][0],
            'filesize': int_or_none(play_data.get('size')),
            'vcodec': 'none'
        }]

        for a_format in formats:
            a_format.setdefault('http_headers', {}).update({
                'Referer': url,
            })

        song = self._call_api('song/info', au_id)
        title = song['title']
        statistic = song.get('statistic') or {}

        subtitles = None
        lyric = song.get('lyric')
        if lyric:
            subtitles = {
                'origin': [{
                    'url': lyric,
                }]
            }

        return {
            'id': au_id,
            'title': title,
            'formats': formats,
            'artist': song.get('author'),
            'comment_count': int_or_none(statistic.get('comment')),
            'description': song.get('intro'),
            'duration': int_or_none(song.get('duration')),
            'subtitles': subtitles,
            'thumbnail': song.get('cover'),
            'timestamp': int_or_none(song.get('passtime')),
            'uploader': song.get('uname'),
            'view_count': int_or_none(statistic.get('play')),
        }


class BilibiliAudioAlbumIE(BilibiliAudioBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bilibili\.com/audio/am(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.bilibili.com/audio/am10624',
        'info_dict': {
            'id': '10624',
            'title': '每日新曲推荐（每日11:00更新）',
            'description': '每天11:00更新，为你推送最新音乐',
        },
        'playlist_count': 19,
    }

    def _real_extract(self, url):
        am_id = self._match_id(url)

        songs = self._call_api(
            'song/of-menu', am_id, {'sid': am_id, 'pn': 1, 'ps': 100})['data']

        entries = []
        for song in songs:
            sid = str_or_none(song.get('id'))
            if not sid:
                continue
            entries.append(self.url_result(
                'https://www.bilibili.com/audio/au' + sid,
                BilibiliAudioIE.ie_key(), sid))

        if entries:
            album_data = self._call_api('menu/info', am_id) or {}
            album_title = album_data.get('title')
            if album_title:
                for entry in entries:
                    entry['album'] = album_title
                return self.playlist_result(
                    entries, am_id, album_title, album_data.get('intro'))

        return self.playlist_result(entries, am_id)


class BiliBiliPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://player\.bilibili\.com/player\.html\?.*?\baid=(?P<id>\d+)'
    _TEST = {
        'url': 'http://player.bilibili.com/player.html?aid=92494333&cid=157926707&page=1',
        'only_matching': True,
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            'http://www.bilibili.tv/video/av%s/' % video_id,
            ie=BiliBiliIE.ie_key(), video_id=video_id)


class BiliIntlBaseIE(InfoExtractor):
    _API_URL = 'https://api.bilibili.tv/intl/gateway'
    _NETRC_MACHINE = 'biliintl'

    def _call_api(self, endpoint, *args, **kwargs):
        json = self._download_json(self._API_URL + endpoint, *args, **kwargs)
        if json.get('code'):
            if json['code'] in (10004004, 10004005, 10023006):
                self.raise_login_required()
            elif json['code'] == 10004001:
                self.raise_geo_restricted()
            else:
                if json.get('message') and str(json['code']) != json['message']:
                    errmsg = f'{kwargs.get("errnote", "Unable to download JSON metadata")}: {self.IE_NAME} said: {json["message"]}'
                else:
                    errmsg = kwargs.get('errnote', 'Unable to download JSON metadata')
                if kwargs.get('fatal'):
                    raise ExtractorError(errmsg)
                else:
                    self.report_warning(errmsg)
        return json.get('data')

    def json2srt(self, json):
        data = '\n\n'.join(
            f'{i + 1}\n{srt_subtitles_timecode(line["from"])} --> {srt_subtitles_timecode(line["to"])}\n{line["content"]}'
            for i, line in enumerate(traverse_obj(json, (
                'body', lambda _, l: l['content'] and l['from'] and l['to']))))
        return data

    def _get_subtitles(self, *, ep_id=None, aid=None):
        sub_json = self._call_api(
            '/web/v2/subtitle', ep_id or aid, fatal=False,
            note='Downloading subtitles list', errnote='Unable to download subtitles list',
            query=filter_dict({
                'platform': 'web',
                's_locale': 'en_US',
                'episode_id': ep_id,
                'aid': aid,
            })) or {}
        subtitles = {}
        for sub in sub_json.get('subtitles') or []:
            sub_url = sub.get('url')
            if not sub_url:
                continue
            sub_data = self._download_json(
                sub_url, ep_id or aid, errnote='Unable to download subtitles', fatal=False,
                note='Downloading subtitles%s' % f' for {sub["lang"]}' if sub.get('lang') else '')
            if not sub_data:
                continue
            subtitles.setdefault(sub.get('lang_key', 'en'), []).append({
                'ext': 'srt',
                'data': self.json2srt(sub_data)
            })
        return subtitles

    def _get_formats(self, *, ep_id=None, aid=None):
        video_json = self._call_api(
            '/web/playurl', ep_id or aid, note='Downloading video formats',
            errnote='Unable to download video formats', query=filter_dict({
                'platform': 'web',
                'ep_id': ep_id,
                'aid': aid,
            }))
        video_json = video_json['playurl']
        formats = []
        for vid in video_json.get('video') or []:
            video_res = vid.get('video_resource') or {}
            video_info = vid.get('stream_info') or {}
            if not video_res.get('url'):
                continue
            formats.append({
                'url': video_res['url'],
                'ext': 'mp4',
                'format_note': video_info.get('desc_words'),
                'width': video_res.get('width'),
                'height': video_res.get('height'),
                'vbr': video_res.get('bandwidth'),
                'acodec': 'none',
                'vcodec': video_res.get('codecs'),
                'filesize': video_res.get('size'),
            })
        for aud in video_json.get('audio_resource') or []:
            if not aud.get('url'):
                continue
            formats.append({
                'url': aud['url'],
                'ext': 'mp4',
                'abr': aud.get('bandwidth'),
                'acodec': aud.get('codecs'),
                'vcodec': 'none',
                'filesize': aud.get('size'),
            })

        self._sort_formats(formats)
        return formats

    def _extract_video_info(self, video_data, *, ep_id=None, aid=None):
        return {
            'id': ep_id or aid,
            'title': video_data.get('title_display') or video_data.get('title'),
            'thumbnail': video_data.get('cover'),
            'episode_number': int_or_none(self._search_regex(
                r'^E(\d+)(?:$| - )', video_data.get('title_display') or '', 'episode number', default=None)),
            'formats': self._get_formats(ep_id=ep_id, aid=aid),
            'subtitles': self._get_subtitles(ep_id=ep_id, aid=aid),
            'extractor_key': BiliIntlIE.ie_key(),
        }

    def _perform_login(self, username, password):
        try:
            from Cryptodome.PublicKey import RSA
            from Cryptodome.Cipher import PKCS1_v1_5
        except ImportError:
            try:
                from Crypto.PublicKey import RSA
                from Crypto.Cipher import PKCS1_v1_5
            except ImportError:
                raise ExtractorError('pycryptodomex not found. Please install', expected=True)

        key_data = self._download_json(
            'https://passport.bilibili.tv/x/intl/passport-login/web/key?lang=en-US', None,
            note='Downloading login key', errnote='Unable to download login key')['data']

        public_key = RSA.importKey(key_data['key'])
        password_hash = PKCS1_v1_5.new(public_key).encrypt((key_data['hash'] + password).encode('utf-8'))
        login_post = self._download_json(
            'https://passport.bilibili.tv/x/intl/passport-login/web/login/password?lang=en-US', None, data=urlencode_postdata({
                'username': username,
                'password': base64.b64encode(password_hash).decode('ascii'),
                'keep_me': 'true',
                's_locale': 'en_US',
                'isTrusted': 'true'
            }), note='Logging in', errnote='Unable to log in')
        if login_post.get('code'):
            if login_post.get('message'):
                raise ExtractorError(f'Unable to log in: {self.IE_NAME} said: {login_post["message"]}', expected=True)
            else:
                raise ExtractorError('Unable to log in')


class BiliIntlIE(BiliIntlBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bili(?:bili\.tv|intl\.com)/(?:[a-z]{2}/)?(play/(?P<season_id>\d+)/(?P<ep_id>\d+)|video/(?P<aid>\d+))'
    _TESTS = [{
        # Bstation page
        'url': 'https://www.bilibili.tv/en/play/34613/341736',
        'info_dict': {
            'id': '341736',
            'ext': 'mp4',
            'title': 'E2 - The First Night',
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode_number': 2,
        }
    }, {
        # Non-Bstation page
        'url': 'https://www.bilibili.tv/en/play/1033760/11005006',
        'info_dict': {
            'id': '11005006',
            'ext': 'mp4',
            'title': 'E3 - Who?',
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode_number': 3,
        }
    }, {
        # Subtitle with empty content
        'url': 'https://www.bilibili.tv/en/play/1005144/10131790',
        'info_dict': {
            'id': '10131790',
            'ext': 'mp4',
            'title': 'E140 - Two Heartbeats: Kabuto\'s Trap',
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'episode_number': 140,
        },
        'skip': 'According to the copyright owner\'s request, you may only watch the video after you log in.'
    }, {
        'url': 'https://www.biliintl.com/en/play/34613/341736',
        'only_matching': True,
    }, {
        # User-generated content (as opposed to a series licensed from a studio)
        'url': 'https://bilibili.tv/en/video/2019955076',
        'only_matching': True,
    }, {
        # No language in URL
        'url': 'https://www.bilibili.tv/video/2019955076',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        season_id, ep_id, aid = self._match_valid_url(url).group('season_id', 'ep_id', 'aid')
        video_id = ep_id or aid
        webpage = self._download_webpage(url, video_id)
        # Bstation layout
        initial_data = (
            self._search_json(r'window\.__INITIAL_(?:DATA|STATE)__\s*=', webpage, 'preload state', video_id, default={})
            or self._search_nuxt_data(webpage, video_id, '__initialState', fatal=False, traverse=None))
        video_data = traverse_obj(
            initial_data, ('OgvVideo', 'epDetail'), ('UgcVideo', 'videoData'), ('ugc', 'archive'), expected_type=dict)

        if season_id and not video_data:
            # Non-Bstation layout, read through episode list
            season_json = self._call_api(f'/web/v2/ogv/play/episodes?season_id={season_id}&platform=web', video_id)
            video_data = traverse_obj(season_json,
                                      ('sections', ..., 'episodes', lambda _, v: str(v['episode_id']) == ep_id),
                                      expected_type=dict, get_all=False)
        return self._extract_video_info(video_data or {}, ep_id=ep_id, aid=aid)


class BiliIntlSeriesIE(BiliIntlBaseIE):
    _VALID_URL = r'https?://(?:www\.)?bili(?:bili\.tv|intl\.com)/(?:[a-z]{2}/)?play/(?P<id>\d+)$'
    _TESTS = [{
        'url': 'https://www.bilibili.tv/en/play/34613',
        'playlist_mincount': 15,
        'info_dict': {
            'id': '34613',
            'title': 'Fly Me to the Moon',
            'description': 'md5:a861ee1c4dc0acfad85f557cc42ac627',
            'categories': ['Romance', 'Comedy', 'Slice of life'],
            'thumbnail': r're:^https://pic\.bstarstatic\.com/ogv/.+\.png$',
            'view_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.biliintl.com/en/play/34613',
        'only_matching': True,
    }]

    def _entries(self, series_id):
        series_json = self._call_api(f'/web/v2/ogv/play/episodes?season_id={series_id}&platform=web', series_id)
        for episode in traverse_obj(series_json, ('sections', ..., 'episodes', ...), expected_type=dict, default=[]):
            episode_id = str(episode.get('episode_id'))
            yield self._extract_video_info(episode, ep_id=episode_id)

    def _real_extract(self, url):
        series_id = self._match_id(url)
        series_info = self._call_api(f'/web/v2/ogv/play/season_info?season_id={series_id}&platform=web', series_id).get('season') or {}
        return self.playlist_result(
            self._entries(series_id), series_id, series_info.get('title'), series_info.get('description'),
            categories=traverse_obj(series_info, ('styles', ..., 'title'), expected_type=str_or_none),
            thumbnail=url_or_none(series_info.get('horizontal_cover')), view_count=parse_count(series_info.get('view')))


class BiliLiveIE(InfoExtractor):
    _VALID_URL = r'https?://live.bilibili.com/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://live.bilibili.com/196',
        'info_dict': {
            'id': '33989',
            'description': "周六杂谈回，其他时候随机游戏。 | \n录播：@下播型泛式录播组。 | \n直播通知群（全员禁言）：666906670，902092584，59971⑧481 （功能一样，别多加）",
            'ext': 'flv',
            'title': "太空狼人杀联动，不被爆杀就算赢",
            'thumbnail': "https://i0.hdslb.com/bfs/live/new_room_cover/e607bc1529057ef4b332e1026e62cf46984c314d.jpg",
            'timestamp': 1650802769,
        },
        'skip': 'not live'
    }, {
        'url': 'https://live.bilibili.com/196?broadcast_type=0&is_room_feed=1?spm_id_from=333.999.space_home.strengthen_live_card.click',
        'only_matching': True
    }]

    _FORMATS = {
        80: {'format_id': 'low', 'format_note': '流畅'},
        150: {'format_id': 'high_res', 'format_note': '高清'},
        250: {'format_id': 'ultra_high_res', 'format_note': '超清'},
        400: {'format_id': 'blue_ray', 'format_note': '蓝光'},
        10000: {'format_id': 'source', 'format_note': '原画'},
        20000: {'format_id': '4K', 'format_note': '4K'},
        30000: {'format_id': 'dolby', 'format_note': '杜比'},
    }

    _quality = staticmethod(qualities(list(_FORMATS)))

    def _call_api(self, path, room_id, query):
        api_result = self._download_json(f'https://api.live.bilibili.com/{path}', room_id, query=query)
        if api_result.get('code') != 0:
            raise ExtractorError(api_result.get('message') or 'Unable to download JSON metadata')
        return api_result.get('data') or {}

    def _parse_formats(self, qn, fmt):
        for codec in fmt.get('codec') or []:
            if codec.get('current_qn') != qn:
                continue
            for url_info in codec['url_info']:
                yield {
                    'url': f'{url_info["host"]}{codec["base_url"]}{url_info["extra"]}',
                    'ext': fmt.get('format_name'),
                    'vcodec': codec.get('codec_name'),
                    'quality': self._quality(qn),
                    **self._FORMATS[qn],
                }

    def _real_extract(self, url):
        room_id = self._match_id(url)
        room_data = self._call_api('room/v1/Room/get_info', room_id, {'id': room_id})
        if room_data.get('live_status') == 0:
            raise ExtractorError('Streamer is not live', expected=True)

        formats = []
        for qn in self._FORMATS.keys():
            stream_data = self._call_api('xlive/web-room/v2/index/getRoomPlayInfo', room_id, {
                'room_id': room_id,
                'qn': qn,
                'codec': '0,1',
                'format': '0,2',
                'mask': '0',
                'no_playurl': '0',
                'platform': 'web',
                'protocol': '0,1',
            })
            for fmt in traverse_obj(stream_data, ('playurl_info', 'playurl', 'stream', ..., 'format', ...)) or []:
                formats.extend(self._parse_formats(qn, fmt))
        self._sort_formats(formats)

        return {
            'id': room_id,
            'title': room_data.get('title'),
            'description': room_data.get('description'),
            'thumbnail': room_data.get('user_cover'),
            'timestamp': stream_data.get('live_time'),
            'formats': formats,
            'http_headers': {
                'Referer': url,
            },
        }
