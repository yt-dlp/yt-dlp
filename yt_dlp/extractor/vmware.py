import itertools

from .common import InfoExtractor, SearchInfoExtractor


class VMwareIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vmware\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.vmware.com/video/6362484671112',
        'info_dict': {
            'id': '6362484671112',
            'ext': 'mp4',
            'title': 'GCI Communications',
            'description': '',
            'thumbnail': r're:^https?://.*/image\.jpg',
            'tags': [],
            'timestamp': 1727345356,
            'upload_date': '20240926',
            'uploader_id': '6415665063001',
            'duration': 106.283,
        },
    }, {
        'url': 'https://www.vmware.com/video/6350300466112',
        'info_dict': {
            'id': '6350300466112',
            'ext': 'mp4',
            'title': 'VMware Private AI',
            'description': r're:^Learn the significance of AI and Generative AI',
            'thumbnail': r're:^https?://.*/image\.jpg',
            'tags': 'count:8',
            'timestamp': 1712293111,
            'upload_date': '20240405',
            'uploader_id': '6415665063001',
            'duration': 3154.624,
        },
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/6415665063001/83iWkhhmz_default/index.html?videoId=%s'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(self.BRIGHTCOVE_URL_TEMPLATE % video_id, url_transparent=True)


class VMwareExploreIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vmware\.com/explore/video-library/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.vmware.com/explore/video-library/video/6360758183112',
        'info_dict': {
            'id': '6360758183112',
            'ext': 'mp4',
            'title': 'VCFB1440LV',
            'description': r're:^All About vSphere 8: What\'s New in the Technology',
            'thumbnail': r're:^https?://.*/image\.jpg',
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
            'thumbnail': r're:^https?://.*/image\.jpg',
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
            'thumbnail': r're:^https?://.*/image\.jpg',
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


class VMwareSearchIE(SearchInfoExtractor):
    IE_NAME = 'VMware:search'
    _SEARCH_KEY = 'vmwaresearch'
    _TESTS = [{
        'url': 'vmwaresearch10:*',
        'info_dict': {
            'id': '*',
            'title': '*',
        },
        'playlist_count': 10,
    }, {
        'url': 'vmwaresearchall:uptime',
        'info_dict': {
            'id': 'uptime',
            'title': 'uptime',
        },
        'playlist_mincount': 5,
    }]
    _LIBRARY_MAP = {
        'explore': ('VMware Explore Video Library', 'https://www.vmware.com/explore/video-library/video/%s'),
        'vmware': ('VMware Video Library', 'https://www.vmware.com/video/%s'),
    }

    def _search_results(self, query):
        def search_query(query, offset, limit, account):
            # search api:
            # https://www.vmware.com/api/nocache/tools/brightcove/search?q=%2B{query}%20%2Byear:2023:2024%20%20-vod_on_demand_publish:%22False%22%2Bcomplete:%22true%22%2Bstate:%22ACTIVE%22&limit=12&offset=0&sort=-updated_at&account=explore
            return self._download_json(
                'https://www.vmware.com/api/nocache/tools/brightcove/search', query,
                note=f'Searching videos in {self._LIBRARY_MAP[account][0]}', query={
                    'q': f'+{query} -vod_on_demand_publish:"False"+complete:"true"+state:"ACTIVE"',
                    'limit': limit,
                    'offset': offset,
                    'sort': 'updated_at',   # chronological ascending order. For descending order: '-updated_at'
                    'account': account,
                })

        for account in ['explore', 'vmware']:
            limit, total_count = 100, None      # limit: maximum 100
            for i in itertools.count():
                search_results = search_query(query, i * limit, limit, account)
                total_count = search_results.get('count', 0)
                for video in search_results.get('videos', []):
                    if video_id := video.get('id'):
                        yield self.url_result(self._LIBRARY_MAP[account][1] % video_id)
                if (i + 1) * limit >= total_count:
                    self.to_screen(f'{query}: {total_count} video(s) found')
                    break
