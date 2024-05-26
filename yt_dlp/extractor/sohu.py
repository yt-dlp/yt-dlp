import base64
import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_urlencode,
)
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    traverse_obj,
    try_get,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class SohuIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<mytv>my\.)?tv\.sohu\.com/.+?/(?(mytv)|n)(?P<id>\d+)\.shtml.*?'

    # Sohu videos give different MD5 sums on Travis CI and my machine
    _TESTS = [{
        'note': 'This video is available only in Mainland China',
        'url': 'http://tv.sohu.com/20130724/n382479172.shtml#super',
        'info_dict': {
            'id': '382479172',
            'ext': 'mp4',
            'title': 'MV：Far East Movement《The Illest》',
        },
        'skip': 'On available in China',
    }, {
        'url': 'http://tv.sohu.com/20150305/n409385080.shtml',
        'info_dict': {
            'id': '409385080',
            'ext': 'mp4',
            'title': '《2015湖南卫视羊年元宵晚会》唐嫣《花好月圆》',
        },
        'skip': 'no longer available',
    }, {
        'url': 'http://my.tv.sohu.com/us/232799889/78693464.shtml',
        'info_dict': {
            'id': '78693464',
            'ext': 'mp4',
            'title': '【爱范品】第31期：MWC见不到的奇葩手机',
            'uploader': '爱范儿视频',
            'duration': 213,
            'timestamp': 1425519600,
            'upload_date': '20150305',
            'thumbnail': 'http://e3f49eaa46b57.cdn.sohucs.com//group1/M10/83/FA/MTAuMTAuODguODA=/6_14cbccdde5eg104SysCutcloud_78693464_7_0b.jpg',
            'tags': ['爱范儿', '爱范品', 'MWC', '手机'],
        }
    }, {
        'note': 'Multipart video',
        'url': 'http://my.tv.sohu.com/pl/8384802/78910339.shtml',
        'info_dict': {
            'id': '78910339',
            'title': '【神探苍实战秘籍】第13期 战争之影 赫卡里姆',
            'uploader': '小苍cany',
            'duration': 744.0,
            'timestamp': 1426269360,
            'upload_date': '20150313',
            'thumbnail': 'http://e3f49eaa46b57.cdn.sohucs.com//group1/M11/89/57/MTAuMTAuODguODA=/6_14cea022a1dg102SysCutcloud_78910339_8_0b.jpg',
            'tags': ['小苍MM', '英雄联盟', '实战秘籍'],
        },
        'playlist': [{
            'info_dict': {
                'id': '78910339_part1',
                'ext': 'mp4',
                'duration': 294,
                'title': '【神探苍实战秘籍】第13期 战争之影 赫卡里姆',
            }
        }, {
            'info_dict': {
                'id': '78910339_part2',
                'ext': 'mp4',
                'duration': 300,
                'title': '【神探苍实战秘籍】第13期 战争之影 赫卡里姆',
            }
        }, {
            'info_dict': {
                'id': '78910339_part3',
                'ext': 'mp4',
                'duration': 150,
                'title': '【神探苍实战秘籍】第13期 战争之影 赫卡里姆',
            }
        }]
    }, {
        'note': 'Video with title containing dash',
        'url': 'http://my.tv.sohu.com/us/249884221/78932792.shtml',
        'info_dict': {
            'id': '78932792',
            'ext': 'mp4',
            'title': 'youtube-dl testing video',
            'duration': 360,
            'timestamp': 1426348620,
            'upload_date': '20150314',
            'thumbnail': 'http://e3f49eaa46b57.cdn.sohucs.com//group1/M02/8A/00/MTAuMTAuODguNzk=/6_14cee1be192g102SysCutcloud_78932792_7_7b.jpg',
            'tags': [],
        },
        'params': {
            'skip_download': True
        }
    }]

    def _real_extract(self, url):

        def _fetch_data(vid_id, mytv=False):
            if mytv:
                base_data_url = 'http://my.tv.sohu.com/play/videonew.do?vid='
            else:
                base_data_url = 'http://hot.vrs.sohu.com/vrs_flash.action?vid='

            return self._download_json(
                base_data_url + vid_id, video_id,
                'Downloading JSON data for %s' % vid_id,
                headers=self.geo_verification_headers())

        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        mytv = mobj.group('mytv') is not None

        webpage = self._download_webpage(url, video_id)

        title = re.sub(r'( - 高清正版在线观看)? - 搜狐视频$', '', self._og_search_title(webpage))

        vid = self._html_search_regex(
            r'var vid ?= ?["\'](\d+)["\']',
            webpage, 'video path')
        vid_data = _fetch_data(vid, mytv)
        if vid_data['play'] != 1:
            if vid_data.get('status') == 12:
                raise ExtractorError(
                    '%s said: There\'s something wrong in the video.' % self.IE_NAME,
                    expected=True)
            else:
                self.raise_geo_restricted(
                    '%s said: The video is only licensed to users in Mainland China.' % self.IE_NAME)

        formats_json = {}
        for format_id in ('nor', 'high', 'super', 'ori', 'h2644k', 'h2654k'):
            vid_id = vid_data['data'].get('%sVid' % format_id)
            if not vid_id:
                continue
            vid_id = compat_str(vid_id)
            formats_json[format_id] = vid_data if vid == vid_id else _fetch_data(vid_id, mytv)

        part_count = vid_data['data']['totalBlocks']

        playlist = []
        for i in range(part_count):
            formats = []
            for format_id, format_data in formats_json.items():
                allot = format_data['allot']

                data = format_data['data']
                clip_url = traverse_obj(data, (('clipsURL', 'mp4PlayUrl'), i, {url_or_none}), get_all=False)
                if not clip_url:
                    raise ExtractorError(f'Unable to extract url for clip {i}')
                su = data['su']

                video_url = 'newflv.sohu.ccgslb.net'
                cdnId = None
                retries = 0

                while 'newflv.sohu.ccgslb.net' in video_url:
                    params = {
                        'prot': 9,
                        'file': clip_url,
                        'new': su[i],
                        'prod': 'h5n',
                        'rb': 1,
                    }

                    if cdnId is not None:
                        params['idc'] = cdnId

                    download_note = 'Downloading %s video URL part %d of %d' % (
                        format_id, i + 1, part_count)

                    if retries > 0:
                        download_note += ' (retry #%d)' % retries
                    part_info = self._parse_json(self._download_webpage(
                        'http://%s/?%s' % (allot, compat_urllib_parse_urlencode(params)),
                        video_id, download_note), video_id)

                    video_url = part_info['url']
                    cdnId = part_info.get('nid')

                    retries += 1
                    if retries > 5:
                        raise ExtractorError('Failed to get video URL')

                formats.append({
                    'url': video_url,
                    'format_id': format_id,
                    'filesize': int_or_none(
                        try_get(data, lambda x: x['clipsBytes'][i])),
                    'width': int_or_none(data.get('width')),
                    'height': int_or_none(data.get('height')),
                    'fps': int_or_none(data.get('fps')),
                })

            playlist.append({
                'id': '%s_part%d' % (video_id, i + 1),
                'title': title,
                'duration': vid_data['data']['clipsDuration'][i],
                'formats': formats,
            })

        if len(playlist) == 1:
            info = playlist[0]
            info['id'] = video_id
        else:
            info = {
                '_type': 'multi_video',
                'entries': playlist,
                'id': video_id,
                'title': title,
                'duration': traverse_obj(vid_data, ('data', 'totalDuration', {float_or_none})),
            }

        if mytv:
            publish_time = unified_timestamp(self._search_regex(
                r'publishTime:\s*["\'](\d+-\d+-\d+ \d+:\d+)["\']', webpage, 'publish time', fatal=False))
        else:
            publish_time = traverse_obj(vid_data, ('tv_application_time', {unified_timestamp}))

        return {
            'timestamp': publish_time - 8 * 3600 if publish_time else None,
            **traverse_obj(vid_data, {
                'alt_title': ('data', 'subName', {str}),
                'uploader': ('wm_data', 'wm_username', {str}),
                'thumbnail': ('data', 'coverImg', {url_or_none}),
                'tags': ('data', 'tag', {str.split}),
            }),
            **info,
        }


class SohuVIE(InfoExtractor):
    _VALID_URL = r'https?://tv\.sohu\.com/v/(?P<id>[\w=-]+)\.html(?:$|[#?])'

    _TESTS = [{
        'note': 'Multipart video',
        'url': 'https://tv.sohu.com/v/MjAyMzA2MTQvbjYwMTMxNTE5Mi5zaHRtbA==.html',
        'info_dict': {
            'id': '601315192',
            'title': '《淬火丹心》第1集',
            'alt_title': '“点天灯”发生事故',
            'duration': 2701.692,
            'timestamp': 1686758040,
            'upload_date': '20230614',
            'thumbnail': 'http://photocdn.tv.sohu.com/img/20230614/vrsa_hor_1686738763256_454010551.jpg',
        },
        'playlist_mincount': 9,
        'skip': 'Only available in China',
    }, {
        'url': 'https://tv.sohu.com/v/dXMvMjMyNzk5ODg5Lzc4NjkzNDY0LnNodG1s.html',
        'info_dict': {
            'id': '78693464',
            'ext': 'mp4',
            'title': '【爱范品】第31期：MWC见不到的奇葩手机',
            'uploader': '爱范儿视频',
            'duration': 213,
            'timestamp': 1425519600,
            'upload_date': '20150305',
            'thumbnail': 'http://e3f49eaa46b57.cdn.sohucs.com//group1/M10/83/FA/MTAuMTAuODguODA=/6_14cbccdde5eg104SysCutcloud_78693464_7_0b.jpg',
            'tags': ['爱范儿', '爱范品', 'MWC', '手机'],
        }
    }, {
        'note': 'Multipart video',
        'url': 'https://tv.sohu.com/v/dXMvMjQyNTYyMTYzLzc4OTEwMzM5LnNodG1s.html?src=pl',
        'info_dict': {
            'id': '78910339',
            'title': '【神探苍实战秘籍】第13期 战争之影 赫卡里姆',
            'uploader': '小苍cany',
            'duration': 744.0,
            'timestamp': 1426269360,
            'upload_date': '20150313',
            'thumbnail': 'http://e3f49eaa46b57.cdn.sohucs.com//group1/M11/89/57/MTAuMTAuODguODA=/6_14cea022a1dg102SysCutcloud_78910339_8_0b.jpg',
            'tags': ['小苍MM', '英雄联盟', '实战秘籍'],
        },
        'playlist_mincount': 3,
    }]

    def _real_extract(self, url):
        encoded_id = self._match_id(url)
        path = base64.urlsafe_b64decode(encoded_id).decode()
        subdomain = 'tv' if re.match(r'\d+/n\d+\.shtml', path) else 'my.tv'
        return self.url_result(urljoin(f'http://{subdomain}.sohu.com/', path), SohuIE)
