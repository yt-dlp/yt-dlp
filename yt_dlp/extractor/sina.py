from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    clean_html,
    get_element_by_attribute,
    int_or_none,
    qualities,
    update_url_query,
)


class SinaIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://(?:[^/?#]+\.)?video\.sina\.com\.cn/
                        (?:
                            (?:view/|.*\#)(?P<id>\d+)|
                            .+?/(?P<pseudo_id>[^/?#]+)(?:\.s?html)|
                            # This is used by external sites like Weibo
                            api/sinawebApi/outplay.php/(?P<token>.+?)\.swf
                        )
                  '''

    _TESTS = [
        {
            'url': 'http://video.sina.com.cn/news/spj/topvideoes20160504/?opsubject_id=top1#250576622',
            'md5': 'd38433e2fc886007729735650ae4b3e9',
            'info_dict': {
                'id': '250576622',
                'ext': 'mp4',
                'title': '现场:克鲁兹宣布退选 特朗普将稳获提名',
            }
        },
        {
            'url': 'http://video.sina.com.cn/v/b/101314253-1290078633.html',
            'info_dict': {
                'id': '101314253',
                'ext': 'flv',
                'title': '军方提高对朝情报监视级别',
            },
            'skip': 'the page does not exist or has been deleted',
        },
        {
            'url': 'http://video.sina.com.cn/view/250587748.html',
            'md5': '3d1807a25c775092aab3bc157fff49b4',
            'info_dict': {
                'id': '250587748',
                'ext': 'mp4',
                'title': '瞬间泪目：8年前汶川地震珍贵视频首曝光',
            },
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)

        video_id = mobj.group('id')
        if not video_id:
            if mobj.group('token') is not None:
                # The video id is in the redirected url
                self.to_screen('Getting video id')
                request = HEADRequest(url)
                _, urlh = self._download_webpage_handle(request, 'NA', False)
                return self._real_extract(urlh.url)
            else:
                pseudo_id = mobj.group('pseudo_id')
                webpage = self._download_webpage(url, pseudo_id)
                error = get_element_by_attribute('class', 'errtitle', webpage)
                if error:
                    raise ExtractorError('%s said: %s' % (
                        self.IE_NAME, clean_html(error)), expected=True)
                video_id = self._search_regex(
                    r"video_id\s*:\s*'(\d+)'", webpage, 'video id')

        video_data = self._download_json(
            'http://s.video.sina.com.cn/video/h5play',
            video_id, query={'video_id': video_id})
        if video_data['code'] != 1:
            raise ExtractorError('%s said: %s' % (
                self.IE_NAME, video_data['message']), expected=True)
        else:
            video_data = video_data['data']
            title = video_data['title']
            description = video_data.get('description')
            if description:
                description = description.strip()

            preference = qualities(['cif', 'sd', 'hd', 'fhd', 'ffd'])
            formats = []
            for quality_id, quality in video_data.get('videos', {}).get('mp4', {}).items():
                file_api = quality.get('file_api')
                file_id = quality.get('file_id')
                if not file_api or not file_id:
                    continue
                formats.append({
                    'format_id': quality_id,
                    'url': update_url_query(file_api, {'vid': file_id}),
                    'quality': preference(quality_id),
                    'ext': 'mp4',
                })

            return {
                'id': video_id,
                'title': title,
                'description': description,
                'thumbnail': video_data.get('image'),
                'duration': int_or_none(video_data.get('length')),
                'timestamp': int_or_none(video_data.get('create_time')),
                'formats': formats,
            }
