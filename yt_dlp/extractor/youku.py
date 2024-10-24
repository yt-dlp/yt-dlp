import random
import re
import string
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    get_element_by_class,
    js_to_json,
    str_or_none,
    strip_jsonp,
)


class YoukuIE(InfoExtractor):
    IE_NAME = 'youku'
    IE_DESC = '优酷'
    _VALID_URL = r'''(?x)
        (?:
            https?://(
                (?:v|play(?:er)?)\.(?:youku|tudou)\.com/(?:v_show/id_|player\.php/sid/)|
                video\.tudou\.com/v/)|
            youku:)
        (?P<id>[A-Za-z0-9]+)(?:\.html|/v\.swf|)
    '''

    _TESTS = [{
        'url': 'http://player.youku.com/player.php/sid/XNDgyMDQ2NTQw/v.swf',
        'only_matching': True,
    }, {
        'url': 'http://v.youku.com/v_show/id_XNjA1NzA2Njgw.html',
        'note': 'Video protected with password',
        'info_dict': {
            'id': 'XNjA1NzA2Njgw',
            'ext': 'mp4',
            'title': '邢義田复旦讲座之想象中的胡人—从“左衽孔子”说起',
            'duration': 7264.5,
            'thumbnail': r're:^https?://.*',
            'uploader': 'FoxJin1006',
            'uploader_id': '322014285',
            'uploader_url': 'http://i.youku.com/u/UMTI4ODA1NzE0MA==',
            'tags': list,
        },
        'params': {
            'videopassword': '100600',
        },
        'skip': '404',
    }, {
        # /play/get.json contains streams with "channel_type":"tail"
        'url': 'http://v.youku.com/v_show/id_XOTUxMzg4NDMy.html',
        'info_dict': {
            'id': 'XOTUxMzg4NDMy',
            'ext': 'mp4',
            'title': '我的世界☆明月庄主☆车震猎杀☆杀人艺术Minecraft',
            'duration': 702.08,
            'thumbnail': r're:^https?://.*',
            'uploader': '明月庄主moon',
            'uploader_id': '38465621',
            'uploader_url': 'https://www.youku.com/profile/index/?uid=UMTUzODYyNDg0',
            'tags': list,
        },
    }, {
        'url': 'https://v.youku.com/v_show/id_XNTA2NTA0MjA1Mg==.html',
        'info_dict': {
            'id': 'XNTA2NTA0MjA1Mg',
            'ext': 'mp4',
            'title': 'Minecraft我的世界：建造超大巨型航空飞机，菜鸟vs高手vs黑客',
            'duration': 542.13,
            'thumbnail': r're:^https?://.*',
            'uploader': '波哥游戏解说',
            'uploader_id': '156688084',
            'uploader_url': 'https://www.youku.com/profile/index/?uid=UNjI2NzUyMzM2',
            'tags': list,
        },
    }, {
        'url': 'https://v.youku.com/v_show/id_XNTE1MzczOTg4MA==.html',
        'info_dict': {
            'id': 'XNTE1MzczOTg4MA',
            'ext': 'mp4',
            'title': '国产超A特工片',
            'duration': 362.97,
            'thumbnail': r're:^https?://.*',
            'uploader': '陈晓娟说历史',
            'uploader_id': '1640913339',
            'uploader_url': 'https://www.youku.com/profile/index/?uid=UNjU2MzY1MzM1Ng==',
            'tags': list,
        },
    }, {
        'url': 'https://play.tudou.com/v_show/id_XNjAxNjI2OTU3Ng==.html?',
        'info_dict': {
            'id': 'XNjAxNjI2OTU3Ng',
            'ext': 'mp4',
            'title': '阿斯塔意识到哈里杀了人，自己被骗了',
            'thumbnail': 'https://m.ykimg.com/0541010164F732752794D4D7B70331D1',
            'uploader_id': '88758207',
            'tags': [],
            'uploader_url': 'https://www.youku.com/profile/index/?uid=UMzU1MDMyODI4',
            'uploader': '英美剧场',
            'duration': 72.91,
        },
    }]

    @staticmethod
    def get_ysuid():
        return '{}{}'.format(int(time.time()), ''.join(
            random.choices(string.ascii_letters, k=3)))

    def get_format_name(self, fm):
        _dict = {
            '3gp': 'h6',
            '3gphd': 'h5',
            'flv': 'h4',
            'flvhd': 'h4',
            'mp4': 'h3',
            'mp4hd': 'h3',
            'mp4hd2': 'h4',
            'mp4hd3': 'h4',
            'hd2': 'h2',
            'hd3': 'h1',
        }
        return _dict.get(fm)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        self._set_cookie('youku.com', '__ysuid', self.get_ysuid())
        self._set_cookie('youku.com', 'xreferrer', 'http://www.youku.com')

        _, urlh = self._download_webpage_handle(
            'https://log.mmstat.com/eg.js', video_id, 'Retrieving cna info')
        # The etag header is '"foobar"'; let's remove the double quotes
        cna = urlh.headers['etag'][1:-1]

        # request basic data
        basic_data_params = {
            'vid': video_id,
            'ccode': '0564',
            'client_ip': '192.168.1.1',
            'utid': cna,
            'client_ts': time.time() / 1000,
        }

        video_password = self.get_param('videopassword')
        if video_password:
            basic_data_params['password'] = video_password

        headers = {
            'Referer': url,
        }
        headers.update(self.geo_verification_headers())
        data = self._download_json(
            'https://ups.youku.com/ups/get.json', video_id,
            'Downloading JSON metadata',
            query=basic_data_params, headers=headers)['data']

        error = data.get('error')
        if error:
            error_note = error.get('note')
            if error_note is not None and '因版权原因无法观看此视频' in error_note:
                raise ExtractorError(
                    'Youku said: Sorry, this video is available in China only', expected=True)
            elif error_note and '该视频被设为私密' in error_note:
                raise ExtractorError(
                    'Youku said: Sorry, this video is private', expected=True)
            else:
                msg = 'Youku server reported error %i' % error.get('code')
                if error_note is not None:
                    msg += ': ' + clean_html(error_note)
                raise ExtractorError(msg)

        # get video title
        video_data = data['video']
        title = video_data['title']

        formats = [{
            'url': stream['m3u8_url'],
            'format_id': self.get_format_name(stream.get('stream_type')),
            'ext': 'mp4',
            'protocol': 'm3u8_native',
            'filesize': int(stream.get('size')),
            'width': stream.get('width'),
            'height': stream.get('height'),
        } for stream in data['stream'] if stream.get('channel_type') != 'tail']

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'duration': video_data.get('seconds'),
            'thumbnail': video_data.get('logo'),
            'uploader': video_data.get('username'),
            'uploader_id': str_or_none(video_data.get('userid')),
            'uploader_url': data.get('uploader', {}).get('homepage'),
            'tags': video_data.get('tags'),
        }


class YoukuShowIE(InfoExtractor):
    _VALID_URL = r'https?://list\.youku\.com/show/id_(?P<id>[0-9a-z]+)\.html'
    IE_NAME = 'youku:show'

    _TESTS = [{
        'url': 'http://list.youku.com/show/id_zc7c670be07ff11e48b3f.html',
        'info_dict': {
            'id': 'zc7c670be07ff11e48b3f',
            'title': '花千骨 DVD版',
            'description': 'md5:a1ae6f5618571bbeb5c9821f9c81b558',
        },
        'playlist_count': 50,
    }, {
        # Episode number not starting from 1
        'url': 'http://list.youku.com/show/id_zefbfbd70efbfbd780bef.html',
        'info_dict': {
            'id': 'zefbfbd70efbfbd780bef',
            'title': '超级飞侠3',
            'description': 'md5:275715156abebe5ccc2a1992e9d56b98',
        },
        'playlist_count': 24,
    }, {
        # Ongoing playlist. The initial page is the last one
        'url': 'http://list.youku.com/show/id_za7c275ecd7b411e1a19e.html',
        'only_matching': True,
    }, {
        #  No data-id value.
        'url': 'http://list.youku.com/show/id_zefbfbd61237fefbfbdef.html',
        'only_matching': True,
    }, {
        #  Wrong number of reload_id.
        'url': 'http://list.youku.com/show/id_z20eb4acaf5c211e3b2ad.html',
        'only_matching': True,
    }]

    def _extract_entries(self, playlist_data_url, show_id, note, query):
        query['callback'] = 'cb'
        playlist_data = self._download_json(
            playlist_data_url, show_id, query=query, note=note,
            transform_source=lambda s: js_to_json(strip_jsonp(s))).get('html')
        if playlist_data is None:
            return [None, None]
        drama_list = (get_element_by_class('p-drama-grid', playlist_data)
                      or get_element_by_class('p-drama-half-row', playlist_data))
        if drama_list is None:
            raise ExtractorError('No episodes found')
        video_urls = re.findall(r'<a[^>]+href="([^"]+)"', drama_list)
        return playlist_data, [
            self.url_result(self._proto_relative_url(video_url, 'http:'), YoukuIE.ie_key())
            for video_url in video_urls]

    def _real_extract(self, url):
        show_id = self._match_id(url)
        webpage = self._download_webpage(url, show_id)

        entries = []
        page_config = self._parse_json(self._search_regex(
            r'var\s+PageConfig\s*=\s*({.+});', webpage, 'page config'),
            show_id, transform_source=js_to_json)
        first_page, initial_entries = self._extract_entries(
            'http://list.youku.com/show/module', show_id,
            note='Downloading initial playlist data page',
            query={
                'id': page_config['showid'],
                'tab': 'showInfo',
            })
        first_page_reload_id = self._html_search_regex(
            r'<div[^>]+id="(reload_\d+)', first_page, 'first page reload id')
        # The first reload_id has the same items as first_page
        reload_ids = re.findall('<li[^>]+data-id="([^"]+)">', first_page)
        entries.extend(initial_entries)
        for idx, reload_id in enumerate(reload_ids):
            if reload_id == first_page_reload_id:
                continue
            _, new_entries = self._extract_entries(
                'http://list.youku.com/show/episode', show_id,
                note=f'Downloading playlist data page {idx + 1}',
                query={
                    'id': page_config['showid'],
                    'stage': reload_id,
                })
            if new_entries is not None:
                entries.extend(new_entries)
        desc = self._html_search_meta('description', webpage, fatal=False)
        playlist_title = desc.split(',')[0] if desc else None
        detail_li = get_element_by_class('p-intro', webpage)
        playlist_description = get_element_by_class(
            'intro-more', detail_li) if detail_li else None

        return self.playlist_result(
            entries, show_id, playlist_title, playlist_description)
