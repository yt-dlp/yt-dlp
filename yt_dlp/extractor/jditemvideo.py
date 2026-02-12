# -*- coding: utf-8 -*-
import json
import random
import time

from .common import InfoExtractor
from ..utils import determine_ext, ExtractorError, traverse_obj


class JdItemVideoIE(InfoExtractor):
    _VALID_URL = r"https://.+.jd.[a-z\.]{2,9}/(?P<id>\d{6,16}).html"

    IE_NAME = 'jd-video'
    IE_DESC = 'jd-video extractor'
    _NETRC_MACHINE = False

    _JD_API_VIDEO_CALLBACK_URL = 'https://cd.jd.com/tencent/video_v3?callback=jQuery{rand}&vid={video_id}&type=1&from=1&appid=24&_={timestamp}'

    _TESTS = [
        {
            'url': 'https://npcitem.jd.hk/100030101538.html',
            'info_dict': {
                "id": "100030101538",
                "ext": "mp4",
                "title": "ipad 2021第九代",
                "description": "【AppleiPad】Apple苹果 iPad 第9代 10.2英寸平板电脑 2021款 ipad9（64GB WLAN版/A13芯片/1200万像素/iPadOS）深空灰色【行情 报价 价格 评测】-京东",
                "size": 10251794,
                "width": 1280,
                "height": 1280,
                "duration": 56,
                "thumbnail": "https://jvod.300hu.com/img/2022/130871763/1/img7.jpg",
                "url": "https://jvod.300hu.com/vod/product/6e02e2d8-98bc-491d-80a1-448ae5ea1c38/c6ef7b9b14ef4b9ca7e4cebda5b7684c.mp4?source=2&h265=h265/18799/a797504bd6f947dfbf6fdb96acfbb55f.mp4",
            },
        },
        {
            'url': 'https://npcitem.jd.hk/100030101538.html',
            'info_dict': {
                "id": "100037516759",
                "ext": "mp4",
                "title": "RODE Wireless Go II Dual",
                "description": "【RODEWireless Go II Dual】罗德（RODE）Wireless Go II Dual无线领夹麦克风单反手机无线小蜜蜂采访直播vlog收音 一拖二2代 标配【行情 报价 价格 评测】-京东",
                "size": 7547769,
                "width": 1280,
                "height": 720,
                "duration": 60,
                "thumbnail": "https://jvod.300hu.com/img/2022/219535842/1/img7.jpg",
                "url": "https://jvod.300hu.com/vod/product/1fc0661d-546e-446e-a429-a8db696ab06a/4067f4c3bb2d41c5af84081d2b0e3018.mp4?source=2&h265=h265/113074/cf365c28ca3a4fdb8178c4e44f916341.mp4",
            },
        },
    ]

    def _real_extract(self, url):
        item_id = self._match_id(url=url)
        resp = self._download_webpage(url_or_request=url, video_id=item_id)
        pattern_data = self._html_search_regex(pattern=r'"mainVideoId":"(\d+?)"', string=resp, name='videoId')
        if pattern_data is None:
            raise ExtractorError("There are no any video. %s" % url)

        description = self._html_extract_title(resp)
        rand = random.randint(433333, 999999)
        timestamp = int(time.time() * 1000)
        url = self._JD_API_VIDEO_CALLBACK_URL.format(rand=rand, timestamp=timestamp, video_id=pattern_data)
        mp4resp = self._download_webpage(url_or_request=url, video_id=item_id)
        detailResp = self._html_search_regex(pattern=r'jQuery\d+\((.+)\)', string=mp4resp, name='detail')
        if detailResp is None:
            raise ExtractorError("Callback fail. return: %s" % detailResp)

        detailRespJson = json.loads(detailResp)
        if detailRespJson.get("code", -1) != 0:
            raise ExtractorError("Callback fail. return: %s" % detailResp)

        ext = determine_ext(url=detailRespJson.get("playUrl", ""))

        info_dict = {
            'id': item_id,
            'ext': ext,
            'title': traverse_obj(detailRespJson, ('extInfo', 'videoName'), default="unknown_video_title"),
            'description': description,
            'size': traverse_obj(detailRespJson, ("extInfo", "size")),
            'width': traverse_obj(detailRespJson, ("extInfo", "vwidth")),
            'height': traverse_obj(detailRespJson, ("extInfo", "vheight")),
            'duration': detailRespJson.get("duration"),
            'thumbnail': detailRespJson.get("imageUrl"),
            'url': detailRespJson.get("playUrl")
        }
        return info_dict
