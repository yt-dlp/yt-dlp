import itertools

from .common import InfoExtractor, SearchInfoExtractor


class VMwareExploreIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vmware\.com/explore/video-library/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.vmware.com/explore/video-library/video/6360758183112',
        'info_dict': {
            'id': '6360758183112',
            'ext': 'mp4',
            'title': 'VCFB1440LV',
            'description': r're:^All About vSphere 8: What\'s New in the Technology',
            'thumbnail': 'https://cf-images.us-east-1.prod.boltdns.net/v1/jit/6164421911001/cde65c5a-51ff-4a0c-905f-ed71e25c0f2c/main/1920x1080/22m53s824ms/match/image.jpg',
            'tags': 'count:6',
            'timestamp': 1724585610,
            'upload_date': '20240825',
            'uploader_id': '6164421911001',
            'duration': 2747.648,
        },
    }, {
        'url': 'https://www.vmware.com/explore/video-library/video/6360759173112',
        'info_dict': {
            'id': '6360759173112',
            'ext': 'mp4',
            'title': 'AODB1676LV',
            'description': r're:^Automation, Analytics and Intelligence: Our Quest for Operational Excellence',
            'thumbnail': 'https://cf-images.us-east-1.prod.boltdns.net/v1/jit/6164421911001/56cc0c8e-9d51-4c25-9d97-4b7364989c47/main/1920x1080/14m18s858ms/match/image.jpg',
            'tags': 'count:6',
            'timestamp': 1724585574,
            'upload_date': '20240825',
            'uploader_id': '6164421911001',
            'duration': 1717.717,
        },
    }, {
        'url': 'https://www.vmware.com/explore/video-library/video/6360760732112',
        'info_dict': {
            'id': '6360760732112',
            'ext': 'mp4',
            'title': 'ANSB1976LV',
            'description': r're:^The Conman of the Digital Era — Ransomware',
            'thumbnail': 'https://cf-images.us-east-1.prod.boltdns.net/v1/jit/6164421911001/4ec22e41-7812-49d9-9fc8-5dbcf1ef4b3c/main/1920x1080/22m36s555ms/match/image.jpg',
            'tags': 'count:6',
            'timestamp': 1724585612,
            'upload_date': '20240825',
            'uploader_id': '6164421911001',
            'duration': 2713.11,
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/6164421911001/lUBT2rAMW_default/index.html?videoId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(self.BRIGHTCOVE_URL_TEMPLATE % video_id, url_transparent=True)


class VMwareExploreSearchIE(SearchInfoExtractor):
    IE_NAME = 'VMwareExplore:search'
    _SEARCH_KEY = 'vmwaresearch'
    _TESTS = [{
        'url': 'vmwaresearch10:*',
        'playlist_count': 10,
        'info_dict': {
            'id': '*',
            'title': '*',
        },
    }, {
        'url': 'vmwaresearchall:ransomware',
        'playlist_count': 15,
        'info_dict': {
            'id': 'ransomware',
            'title': 'ransomware',
        },
    }]
    _URL_TEMPLATE = 'https://www.vmware.com/explore/video-library/video/%s'

    def _search_results(self, query):
        def search_query(query, offset, limit, total_count):
            # search api:
            # https://www.vmware.com/api/nocache/tools/brightcove/search?q=%2B{query}%20%2Byear:2023:2024%20%20-vod_on_demand_publish:%22False%22%2Bcomplete:%22true%22%2Bstate:%22ACTIVE%22&limit=12&offset=0&sort=-updated_at&account=explore
            return self._download_json(
                'https://www.vmware.com/api/nocache/tools/brightcove/search', query,
                note=f'Downloading result {offset + 1}-{min(offset + limit, total_count or 99999999)}', query={
                    'q': f'+{query} -vod_on_demand_publish:"False"+complete:"true"+state:"ACTIVE"',
                    'limit': limit,
                    'offset': offset,
                    'sort': 'updated_at',   # chronological ascending order. For descending order: '-updated_at'
                    'account': 'explore',
                })

        limit, total_count = 100, None      # limit: maximum 100
        for i in itertools.count():
            search_results = search_query(query, i * limit, limit, total_count)
            total_count = search_results.get('count', 0)
            for video in search_results.get('videos', []):
                if video_id := video.get('id'):
                    yield self.url_result(self._URL_TEMPLATE % video_id)
            if (i + 1) * limit >= total_count:
                break
