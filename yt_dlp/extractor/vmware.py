import itertools

from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    float_or_none,
    join_nonempty,
    traverse_obj,
    url_or_none,
)


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
        'url': 'vmwaresearch5:firewall',
        'info_dict': {
            'id': 'firewall',
            'title': 'firewall',
        },
        'playlist_count': 5,
    }, {
        'url': 'vmwaresearchall:uptime',
        'info_dict': {
            'id': 'uptime',
            'title': 'uptime',
        },
        'playlist_mincount': 2,
    }]
    _LIBRARY_MAP = {
        'explore': ('VMware Explore Video Library', 'https://www.vmware.com/explore/video-library/video/%s'),
        'vmware': ('VMware Video Library', 'https://www.vmware.com/video/%s'),
    }

    def _search_results(self, query):
        def search_query(query, page_no, records_per_page, account):
            # search api:
            # https://api.swiftype.com/api/v1/public/engines/search.json?engine_key=J3yan3XpFywGvRxQMcEr&document_types[]=videos&&filters[videos][locale]=en-us&filters[videos][vod_on_demand_publish][]=!False&filters[videos][complete]=true&filters[videos][state]=ACTIVE&facets[videos][]=products&facets[videos][]=sessiontype&facets[videos][]=audience&facets[videos][]=track&facets[videos][]=level&filters[videos][year][]=!&filters[videos][account]=explore&q[]=ransomware&q[]=uptime&page=1&per_page=12&sort_field[videos]=updated_date&sort_direction[videos]=desc
            return self._download_json(
                'https://api.swiftype.com/api/v1/public/engines/search.json', query,
                note=f'Page {page_no}: Searching for videos in {self._LIBRARY_MAP[account][0]}', query={
                    'engine_key': 'J3yan3XpFywGvRxQMcEr',
                    'document_types[]': 'videos',
                    'filters[videos][state]': 'ACTIVE',
                    'filters[videos][account]': account,
                    'q[]': query,
                    'page': page_no,
                    'per_page': records_per_page,
                    'sort_field[videos]': 'video_id',
                    'sort_direction[videos]': 'asc',    # 'desc' for descending order
                })

        for account in ['explore', 'vmware']:
            records_per_page, total_count = 100, None   # records_per_page: maximum 100
            for i in itertools.count(start=1, step=1):
                search_results = search_query(query, i, records_per_page, account)
                total_count = traverse_obj(
                    search_results, ('info', 'videos', 'total_result_count', {int}), default=0)
                for video in traverse_obj(search_results, ('records', 'videos', lambda _, v: v['external_id'])):
                    yield self.url_result(
                        self._LIBRARY_MAP[account][1] % video['external_id'],
                        **traverse_obj(video, {
                            'id': ('external_id', {str}),
                            'title': ('name', {str}),
                            'description': ({lambda v: join_nonempty('description', 'long_description',
                                                                     from_dict=video, delim='\n')}),
                            'thumbnail': (('images', 'thumbnail'), {url_or_none}),
                            'tags': ('tags'),
                            'uploader_id': ('account_id'),
                            'duration': ('duration', {lambda v: float_or_none(v, 1000)}),
                        }, get_all=False))
                if i * records_per_page >= total_count:
                    self.to_screen(f'{query}: {total_count} video(s) found')
                    break
