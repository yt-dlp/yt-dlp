# from .cbs import CBSBaseIE
from .common import InfoExtractor
from ..utils import (
    int_or_none,
    try_get,
)


# class CBSSportsEmbedIE(CBSBaseIE):
class CBSSportsEmbedIE(InfoExtractor):
    IE_NAME = 'cbssports:embed'
    _VALID_URL = r'''(?ix)https?://(?:(?:www\.)?cbs|embed\.247)sports\.com/player/embed.+?
        (?:
            ids%3D(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})|
            pcid%3D(?P<pcid>\d+)
        )'''
    _TESTS = [{
        'url': 'https://www.cbssports.com/player/embed/?args=player_id%3Db56c03a6-231a-4bbe-9c55-af3c8a8e9636%26ids%3Db56c03a6-231a-4bbe-9c55-af3c8a8e9636%26resizable%3D1%26autoplay%3Dtrue%26domain%3Dcbssports.com%26comp_ads_enabled%3Dfalse%26watchAndRead%3D0%26startTime%3D0%26env%3Dprod',
        'only_matching': True,
    }, {
        'url': 'https://embed.247sports.com/player/embed/?args=%3fplayer_id%3d1827823171591%26channel%3dcollege-football-recruiting%26pcid%3d1827823171591%26width%3d640%26height%3d360%26autoplay%3dTrue%26comp_ads_enabled%3dFalse%26uvpc%3dhttps%253a%252f%252fwww.cbssports.com%252fapi%252fcontent%252fvideo%252fconfig%252f%253fcfg%253duvp_247sports_v4%2526partner%253d247%26uvpc_m%3dhttps%253a%252f%252fwww.cbssports.com%252fapi%252fcontent%252fvideo%252fconfig%252f%253fcfg%253duvp_247sports_m_v4%2526partner_m%253d247_mobile%26utag%3d247sportssite%26resizable%3dTrue',
        'only_matching': True,
    }]

    # def _extract_video_info(self, filter_query, video_id):
    #     return self._extract_feed_info('dJ5BDC', 'VxxJg8Ymh8sE', filter_query, video_id)

    def _real_extract(self, url):
        uuid, pcid = self._match_valid_url(url).groups()
        query = {'id': uuid} if uuid else {'pcid': pcid}
        video = self._download_json(
            'https://www.cbssports.com/api/content/video/',
            uuid or pcid, query=query)[0]
        video_id = video['id']
        title = video['title']
        metadata = video.get('metaData') or {}
        # return self._extract_video_info('byId=%d' % metadata['mpxOutletId'], video_id)
        # return self._extract_video_info('byGuid=' + metadata['mpxRefId'], video_id)

        formats = self._extract_m3u8_formats(
            metadata['files'][0]['url'], video_id, 'mp4',
            'm3u8_native', m3u8_id='hls', fatal=False)

        image = video.get('image')
        thumbnails = None
        if image:
            image_path = image.get('path')
            if image_path:
                thumbnails = [{
                    'url': image_path,
                    'width': int_or_none(image.get('width')),
                    'height': int_or_none(image.get('height')),
                    'filesize': int_or_none(image.get('size')),
                }]

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnails': thumbnails,
            'description': video.get('description'),
            'timestamp': int_or_none(try_get(video, lambda x: x['dateCreated']['epoch'])),
            'duration': int_or_none(metadata.get('duration')),
        }


class CBSSportsBaseIE(InfoExtractor):
    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        iframe_url = self._search_regex(
            r'<iframe[^>]+(?:data-)?src="(https?://[^/]+/player/embed[^"]+)"',
            webpage, 'embed url')
        return self.url_result(iframe_url, CBSSportsEmbedIE.ie_key())


class CBSSportsIE(CBSSportsBaseIE):
    IE_NAME = 'cbssports'
    _VALID_URL = r'https?://(?:www\.)?cbssports\.com/[^/]+/video/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.cbssports.com/college-football/video/cover-3-stanford-spring-gleaning/',
        'info_dict': {
            'id': 'b56c03a6-231a-4bbe-9c55-af3c8a8e9636',
            'ext': 'mp4',
            'title': 'Cover 3: Stanford Spring Gleaning',
            'description': 'The Cover 3 crew break down everything you need to know about the Stanford Cardinal this spring.',
            'timestamp': 1617218398,
            'upload_date': '20210331',
            'duration': 502,
        },
    }]


class TwentyFourSevenSportsIE(CBSSportsBaseIE):
    IE_NAME = '247sports'
    _VALID_URL = r'https?://(?:www\.)?247sports\.com/Video/(?:[^/?#&]+-)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://247sports.com/Video/2021-QB-Jake-Garcia-senior-highlights-through-five-games-10084854/',
        'info_dict': {
            'id': '4f1265cb-c3b5-44a8-bb1d-1914119a0ccc',
            'ext': 'mp4',
            'title': '2021 QB Jake Garcia senior highlights through five games',
            'description': 'md5:8cb67ebed48e2e6adac1701e0ff6e45b',
            'timestamp': 1607114223,
            'upload_date': '20201204',
            'duration': 208,
        },
    }]
