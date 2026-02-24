import random

from .common import InfoExtractor
from ..utils import (
    parse_duration,
    parse_qs,
    str_or_none,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class BloggerIE(InfoExtractor):
    IE_NAME = 'blogger.com'
    _VALID_URL = r'https?://(?:www\.)?blogger\.com/video\.g\?token=(?P<id>.+)'
    _EMBED_REGEX = [r'''<iframe[^>]+src=["'](?P<url>(?:https?:)?//(?:www\.)?blogger\.com/video\.g\?token=[^"']+)["']''']
    _TESTS = [{
        'url': 'https://www.blogger.com/video.g?token=AD6v5dzEe9hfcARr5Hlq1WTkYy6t-fXH3BBahVhGvVHe5szdEUBEloSEDSTA8-b111089KbfWuBvTN7fnbxMtymsHhXAXwVvyzHH4Qch2cfLQdGxKQrrEuFpC1amSl_9GuLWODjPgw',
        'md5': 'f1bc19b6ea1b0fd1d81e84ca9ec467ac',
        'info_dict': {
            'id': 'BLOGGER-video-3c740e3a49197e16-796',
            'title': 'BLOGGER-video-3c740e3a49197e16-796',
            'ext': 'mp4',
            'duration': 76.006,
            'thumbnail': r're:https?://i9\.ytimg\.com/vi_blogger/.+',
        },
    }, {
        'url': 'https://www.blogger.com/video.g?token=AD6v5dxQvB2soRxjzQ6NfKtsKV42CPEC905mnK-zop3trOP32hF4Jb3895aWvR85zvR8Ks5U5Zyyvrkj6nQuOg_9o0HK4C1Iclp-eRxHveFRdhACzMi67UeFS9CO-2Z9r_FCKxfOPA',
        'md5': '309f9a5604ebd272dd2e1538998a0f40',
        'info_dict': {
            'id': 'BLOGGER-video-6f028977527fdc05-338',
            'ext': 'mp4',
            'title': 'BLOGGER-video-6f028977527fdc05-338',
            'duration': 75.966,
            'thumbnail': r're:https?://i9\.ytimg\.com/vi_blogger/.+',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://blog.tomeuvizoso.net/2019/01/a-panfrost-milestone.html',
        'md5': 'f1bc19b6ea1b0fd1d81e84ca9ec467ac',
        'info_dict': {
            'id': 'BLOGGER-video-3c740e3a49197e16-12913',
            'ext': 'mp4',
            'title': 'BLOGGER-video-3c740e3a49197e16-12913',
            'duration': 76.006,
            'thumbnail': r're:https?://i9\.ytimg\.com/vi_blogger/.+',
        },
    }]

    # Source https://www.blogger.com/_/scs/mss-static/_/js/k=boq-blogger.BloggerVideoPlayerUi.en_US.6PupVFhoDlA.2018.O/ck=boq-blogger.BloggerVideoPlayerUi.0lo6xI35Cfs.L.B1.O/am=AAAAwA4/d=1/exm=_b,_tp/excm=_b,_tp,videoplayerview/ed=1/wt=2/ujg=1/rs=AEy-KP3OJHU74ptfWOTb5LeMqh3Kxak-yA/ee=EVNhjf:pw70Gc;EmZ2Bf:zr1jrb;JsbNhc:Xd8iUd;K5nYTd:ZDZcre;LBgRLc:XVMNvd;Me32dd:MEeYgc;NJ1rfe:qTnoBf;NPKaK:PVlQOd;Pjplud:EEDORb;QGR0gd:Mlhmy;SNUn3:ZwDk9d;ScI3Yc:e7Hzgb;Uvc8o:VDovNc;YIZmRd:A1yn5d;a56pNe:JEfCwb;cEt90b:ws9Tlc;dIoSBb:SpsfSb;dowIGb:ebZ3mb;eBAeSb:zbML3c;iFQyKf:QIhFr;lOO0Vd:OTA3Ae;oGtAuc:sOXFj;qQEoOc:KUM7Z;qafBPd:yDVVkb;qddgKe:xQtZb;wR5FRb:siKnQd;yxTchf:KUM7Z/dti=1/m=OXnWq
    # current varianle name (s1) and format table name (r1).
    IF_TABLE = {
        7: {'width': 320, 'height': 240},
        18: {'width': 640, 'height': 360},
        22: {'width': 1280, 'height': 720},
        37: {'width': 1920, 'height': 1080},
        13: {'width': 256, 'height': 144},  # Source https://gist.github.com/MartinEesmaa/2f4b261cb90a47e9c41ba115a011a4aa#legacy-non-dash
    }

    def _real_extract(self, url):
        token_id = self._match_id(url)

        fsid = random.randint(-9999999999999999999, 9999999999999999999)  # Blogger require 19 digit number can be negative or positive

        data, _ = self._download_webpage_handle(
            'https://www.blogger.com/_/BloggerVideoPlayerUi/data/batchexecute',
            token_id,
            note='Downloading blogger batch information',
            headers={
                'Referer': 'https://www.blogger.com/',
            },
            query={
                'rpcids': 'WcwnYd',
                'f.sid': fsid,
                'bl': 'boq_bloggeruiserver_20260218.01_p0',
                'hl': 'en-US',
                'rt': 'c',
            },
            data=urlencode_postdata({
                'f.req': f'[[["WcwnYd","[\\"{token_id}\\",\\"\\",0]",null,"generic"]]]',
            }),
        )

        wrb_data = self._search_regex(r'(\[\[.*?"WcwnYd".*?\]\])\s(?:\d+)?', data, 'wrb.fr')
        data = self._parse_json(self._parse_json(wrb_data, None)[0][2], None)

        formats = []
        for fmtl in traverse_obj(data, (2), default=[]):
            if not isinstance(fmtl, list):
                continue
            fmt_url = traverse_obj(fmtl, (0))
            itag = traverse_obj(fmtl, (1, 0)) or traverse_obj(parse_qs(fmt_url), ('itag', 0))
            formats.append({
                'format_id': str(itag),
                'url': fmt_url,
                'ext': 'mp4',
                'http_headers': {
                    'referer': 'https://youtube.googleapis.com/',
                },
                **self.IF_TABLE.get(int(itag), {}),
            })

        thumbnail = None
        title = None

        for block in data:
            if block is None:
                continue
            if isinstance(block, (list, int)):
                continue
            if 'ytimg.com' in block:
                thumbnail = block
            elif isinstance(block, str):
                title = block
            else:
                continue

        return {
            'id': title or token_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': parse_duration(traverse_obj(parse_qs(formats[0]['url']), ('dur', 0))),
            'formats': formats,
            **traverse_obj(data, (2, {
                'title': (-1, {str_or_none}),
                'thumbnail': (-2, {url_or_none}),
            })),
        }
