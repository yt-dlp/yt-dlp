# coding: utf-8
from __future__ import unicode_literals

import hashlib
import itertools
import json
import re

from .common import InfoExtractor, SearchInfoExtractor
from ..compat import (
    compat_str,
    compat_parse_qs,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    float_or_none,
    parse_iso8601,
    try_get,
    smuggle_url,
    str_or_none,
    strip_jsonp,
    unified_timestamp,
    unsmuggle_url,
    urlencode_postdata,
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
                            video/[bB][vV](?P<id_bv>[^/?#&]+)
                        )
                        (?:/?\?p=(?P<page>\d+))?
                    '''

    _TESTS = [{
        'url': 'http://www.bilibili.com/video/av1074402/',
        'md5': '5f7d29e1a2872f3df0cf76b1f87d3788',
        'info_dict': {
            'id': '1074402',
            'ext': 'flv',
            'title': '【金坷垃】金泡沫',
            'description': 'md5:ce18c2a2d2193f0df2917d270f2e5923',
            'duration': 308.067,
            'timestamp': 1398012678,
            'upload_date': '20140420',
            'thumbnail': r're:^https?://.+\.jpg',
            'uploader': '菊子桑',
            'uploader_id': '156160',
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
            'id': '100643',
            'ext': 'mp4',
            'title': 'CHAOS;CHILD',
            'description': '如果你是神明，并且能够让妄想成为现实。那你会进行怎么样的妄想？是淫靡的世界？独裁社会？毁灭性的制裁？还是……2015年，涩谷。从6年前发生的大灾害“涩谷地震”之后复兴了的这个街区里新设立的私立高中...',
        },
        'skip': 'Geo-restricted to China',
    }, {
        # Title with double quotes
        'url': 'http://www.bilibili.com/video/av8903802/',
        'info_dict': {
            'id': '8903802',
            'title': '阿滴英文｜英文歌分享#6 "Closer',
            'description': '滴妹今天唱Closer給你聽! 有史以来，被推最多次也是最久的歌曲，其实歌词跟我原本想像差蛮多的，不过还是好听！ 微博@阿滴英文',
        },
        'playlist': [{
            'info_dict': {
                'id': '8903802_part1',
                'ext': 'flv',
                'title': '阿滴英文｜英文歌分享#6 "Closer',
                'description': 'md5:3b1b9e25b78da4ef87e9b548b88ee76a',
                'uploader': '阿滴英文',
                'uploader_id': '65880958',
                'timestamp': 1488382634,
                'upload_date': '20170301',
            },
            'params': {
                'skip_download': True,  # Test metadata only
            },
        }, {
            'info_dict': {
                'id': '8903802_part2',
                'ext': 'flv',
                'title': '阿滴英文｜英文歌分享#6 "Closer',
                'description': 'md5:3b1b9e25b78da4ef87e9b548b88ee76a',
                'uploader': '阿滴英文',
                'uploader_id': '65880958',
                'timestamp': 1488382634,
                'upload_date': '20170301',
            },
            'params': {
                'skip_download': True,  # Test metadata only
            },
        }]
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

        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id_bv') or mobj.group('id')

        av_id, bv_id = self._get_video_id_set(video_id, mobj.group('id_bv') is not None)
        video_id = av_id

        anime_id = mobj.group('anime_id')
        page_id = mobj.group('page')
        webpage = self._download_webpage(url, video_id)

        # Bilibili anthologies are similar to playlists but all videos share the same video ID as the anthology itself.
        # If the video has no page argument, check to see if it's an anthology
        if page_id is None:
            if not self._downloader.params.get('noplaylist'):
                r = self._extract_anthology_entries(bv_id, video_id, webpage)
                if r is not None:
                    self.to_screen('Downloading anthology %s - add --no-playlist to just download video' % video_id)
                    return r
            else:
                self.to_screen('Downloading just video %s because of --no-playlist' % video_id)

        if 'anime/' not in url:
            cid = self._search_regex(
                r'\bcid(?:["\']:|=)(\d+),["\']page(?:["\']:|=)' + compat_str(page_id), webpage, 'cid',
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

        entries = []

        RENDITIONS = ('qn=80&quality=80&type=', 'quality=2&type=mp4')
        for num, rendition in enumerate(RENDITIONS, start=1):
            payload = 'appkey=%s&cid=%s&otype=json&%s' % (self._APP_KEY, cid, rendition)
            sign = hashlib.md5((payload + self._BILIBILI_KEY).encode('utf-8')).hexdigest()

            video_info = self._download_json(
                'http://interface.bilibili.com/v2/playurl?%s&sign=%s' % (payload, sign),
                video_id, note='Downloading video info page',
                headers=headers, fatal=num == len(RENDITIONS))

            if not video_info:
                continue

            if 'durl' not in video_info:
                if num < len(RENDITIONS):
                    continue
                self._report_error(video_info)

            for idx, durl in enumerate(video_info['durl']):
                formats = [{
                    'url': durl['url'],
                    'filesize': int_or_none(durl['size']),
                }]
                for backup_url in durl.get('backup_url', []):
                    formats.append({
                        'url': backup_url,
                        # backup URLs have lower priorities
                        'quality': -2 if 'hd.mp4' in backup_url else -3,
                    })

                for a_format in formats:
                    a_format.setdefault('http_headers', {}).update({
                        'Referer': url,
                    })

                self._sort_formats(formats)

                entries.append({
                    'id': '%s_part%s' % (video_id, idx),
                    'duration': float_or_none(durl.get('length'), 1000),
                    'formats': formats,
                })
            break

        title = self._html_search_regex(
            (r'<h1[^>]+\btitle=(["\'])(?P<title>(?:(?!\1).)+)\1',
             r'(?s)<h1[^>]*>(?P<title>.+?)</h1>'), webpage, 'title',
            group='title')

        # Get part title for anthologies
        if page_id is not None:
            # TODO: The json is already downloaded by _extract_anthology_entries. Don't redownload for each video
            part_title = try_get(
                self._download_json(
                    "https://api.bilibili.com/x/player/pagelist?bvid=%s&jsonp=jsonp" % bv_id,
                    video_id, note='Extracting videos in anthology'),
                lambda x: x['data'][int(page_id) - 1]['part'])
            title = part_title or title

        description = self._html_search_meta('description', webpage)
        timestamp = unified_timestamp(self._html_search_regex(
            r'<time[^>]+datetime="([^"]+)"', webpage, 'upload time',
            default=None) or self._html_search_meta(
            'uploadDate', webpage, 'timestamp', default=None))
        thumbnail = self._html_search_meta(['og:image', 'thumbnailUrl'], webpage)

        # TODO 'view_count' requires deobfuscating Javascript
        info = {
            'id': compat_str(video_id) if page_id is None else '%s_p%s' % (video_id, page_id),
            'cid': cid,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'thumbnail': thumbnail,
            'duration': float_or_none(video_info.get('timelength'), scale=1000),
        }

        uploader_mobj = re.search(
            r'<a[^>]+href="(?:https?:)?//space\.bilibili\.com/(?P<id>\d+)"[^>]*>\s*(?P<name>[^<]+?)\s*<',
            webpage)
        if uploader_mobj:
            info.update({
                'uploader': uploader_mobj.group('name'),
                'uploader_id': uploader_mobj.group('id'),
            })

        if not info.get('uploader'):
            info['uploader'] = self._html_search_meta(
                'author', webpage, 'uploader', default=None)

        raw_danmaku = self._get_raw_danmaku(video_id, cid)

        raw_tags = self._get_tags(video_id)
        tags = list(map(lambda x: x['tag_name'], raw_tags))

        top_level_info = {
            'raw_danmaku': raw_danmaku,
            'tags': tags,
            'raw_tags': raw_tags,
        }
        if self._downloader.params.get('getcomments', False):
            def get_comments():
                comments = self._get_all_comment_pages(video_id)
                return {
                    'comments': comments,
                    'comment_count': len(comments)
                }

            top_level_info['__post_extractor'] = get_comments

        '''
        # Requires https://github.com/m13253/danmaku2ass which is licenced under GPL3
        # See https://github.com/animelover1984/youtube-dl
        danmaku = NiconicoIE.CreateDanmaku(raw_danmaku, commentType='Bilibili', x=1024, y=576)
        entries[0]['subtitles'] = {
            'danmaku': [{
                'ext': 'ass',
                'data': danmaku
            }]
        }
        '''

        for entry in entries:
            entry.update(info)

        if len(entries) == 1:
            entries[0].update(top_level_info)
            return entries[0]
        else:
            for idx, entry in enumerate(entries):
                entry['id'] = '%s_part%d' % (video_id, (idx + 1))

            global_info = {
                '_type': 'multi_video',
                'id': compat_str(video_id),
                'bv_id': bv_id,
                'title': title,
                'description': description,
                'entries': entries,
            }

            global_info.update(info)
            global_info.update(top_level_info)

            return global_info

    def _extract_anthology_entries(self, bv_id, video_id, webpage):
        title = self._html_search_regex(
            (r'<h1[^>]+\btitle=(["\'])(?P<title>(?:(?!\1).)+)\1',
             r'(?s)<h1[^>]*>(?P<title>.+?)</h1>'), webpage, 'title',
            group='title')
        json_data = self._download_json(
            "https://api.bilibili.com/x/player/pagelist?bvid=%s&jsonp=jsonp" % bv_id,
            video_id, note='Extracting videos in anthology')

        if len(json_data['data']) > 1:
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
            raise ExtractorError('Unknown error occurred during API check (code %s)' % response['code'], expected=True, video_id=id)
        return (response['data']['aid'], response['data']['bvid'])

    # recursive solution to getting every page of comments for the video
    # we can stop when we reach a page without any comments
    def _get_all_comment_pages(self, video_id, commentPageNumber=0):
        comment_url = "https://api.bilibili.com/x/v2/reply?jsonp=jsonp&pn=%s&type=1&oid=%s&sort=2&_=1567227301685" % (commentPageNumber, video_id)
        json_str = self._download_webpage(
            comment_url, video_id,
            note='Extracting comments from page %s' % (commentPageNumber))
        replies = json.loads(json_str)['data']['replies']
        if replies is None:
            return []
        return self._get_all_children(replies) + self._get_all_comment_pages(video_id, commentPageNumber + 1)

    # extracts all comments in the tree
    def _get_all_children(self, replies):
        if replies is None:
            return []

        ret = []
        for reply in replies:
            author = reply['member']['uname']
            author_id = reply['member']['mid']
            id = reply['rpid']
            text = reply['content']['message']
            timestamp = reply['ctime']
            parent = reply['parent'] if reply['parent'] != 0 else 'root'

            comment = {
                "author": author,
                "author_id": author_id,
                "id": id,
                "text": text,
                "timestamp": timestamp,
                "parent": parent,
            }
            ret.append(comment)

            # from the JSON, the comment structure seems arbitrarily deep, but I could be wrong.
            # Regardless, this should work.
            ret += self._get_all_children(reply['replies'])

        return ret

    def _get_raw_danmaku(self, video_id, cid):
        # This will be useful if I decide to scrape all pages instead of doing them individually
        # cid_url = "https://www.bilibili.com/widget/getPageList?aid=%s" % (video_id)
        # cid_str = self._download_webpage(cid_url, video_id, note=False)
        # cid = json.loads(cid_str)[0]['cid']

        danmaku_url = "https://comment.bilibili.com/%s.xml" % (cid)
        danmaku = self._download_webpage(danmaku_url, video_id, note='Downloading danmaku comments')
        return danmaku

    def _get_tags(self, video_id):
        tags_url = "https://api.bilibili.com/x/tag/archive/tags?aid=%s" % (video_id)
        tags_json = self._download_json(tags_url, video_id, note='Downloading tags')
        return tags_json['data']


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
            data = self._parse_json(
                self._download_webpage(
                    self._API_URL % (list_id, page_num), list_id,
                    note='Downloading page %d' % page_num),
                list_id)['data']

            max_count = max_count or try_get(data, lambda x: x['page']['count'])

            entries = try_get(data, lambda x: x['list']['vlist'])
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


class BiliBiliSearchIE(SearchInfoExtractor):
    IE_DESC = 'Bilibili video search, "bilisearch" keyword'
    _MAX_RESULTS = 100000
    _SEARCH_KEY = 'bilisearch'
    MAX_NUMBER_OF_RESULTS = 1000

    def _get_n_results(self, query, n):
        """Get a specified number of results for a query"""

        entries = []
        pageNumber = 0
        while True:
            pageNumber += 1
            # FIXME
            api_url = "https://api.bilibili.com/x/web-interface/search/type?context=&page=%s&order=pubdate&keyword=%s&duration=0&tids_2=&__refresh__=true&search_type=video&tids=0&highlight=1" % (pageNumber, query)
            json_str = self._download_webpage(
                api_url, "None", query={"Search_key": query},
                note='Extracting results from page %s' % pageNumber)
            data = json.loads(json_str)['data']

            # FIXME: this is hideous
            if "result" not in data:
                return {
                    '_type': 'playlist',
                    'id': query,
                    'entries': entries[:n]
                }

            videos = data['result']
            for video in videos:
                e = self.url_result(video['arcurl'], 'BiliBili', compat_str(video['aid']))
                entries.append(e)

            if(len(entries) >= n or len(videos) >= BiliBiliSearchIE.MAX_NUMBER_OF_RESULTS):
                return {
                    '_type': 'playlist',
                    'id': query,
                    'entries': entries[:n]
                }


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
