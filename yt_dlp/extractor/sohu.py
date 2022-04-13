import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_urlencode,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    try_get,
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
        }
    }, {
        'url': 'http://my.tv.sohu.com/us/232799889/78693464.shtml',
        'info_dict': {
            'id': '78693464',
            'ext': 'mp4',
            'title': '【爱范品】第31期：MWC见不到的奇葩手机',
        }
    }, {
        'note': 'Multipart video',
        'url': 'http://my.tv.sohu.com/pl/8384802/78910339.shtml',
        'info_dict': {
            'id': '78910339',
            'title': '【神探苍实战秘籍】第13期 战争之影 赫卡里姆',
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

        title = re.sub(r' - 搜狐视频$', '', self._og_search_title(webpage))

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
                clips_url = data['clipsURL']
                su = data['su']

                video_url = 'newflv.sohu.ccgslb.net'
                cdnId = None
                retries = 0

                while 'newflv.sohu.ccgslb.net' in video_url:
                    params = {
                        'prot': 9,
                        'file': clips_url[i],
                        'new': su[i],
                        'prod': 'flash',
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
            self._sort_formats(formats)

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
            }

        return info
