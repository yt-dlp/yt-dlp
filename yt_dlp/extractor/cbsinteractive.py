from .cbs import CBSIE
from ..utils import int_or_none


class CBSInteractiveIE(CBSIE):
    _VALID_URL = r'https?://(?:www\.)?(?P<site>cnet|zdnet)\.com/(?:videos|video(?:/share)?)/(?P<id>[^/?]+)'
    _TESTS = [{
        'url': 'http://www.cnet.com/videos/hands-on-with-microsofts-windows-8-1-update/',
        'info_dict': {
            'id': 'R49SYt__yAfmlXR85z4f7gNmCBDcN_00',
            'display_id': 'hands-on-with-microsofts-windows-8-1-update',
            'ext': 'mp4',
            'title': 'Hands-on with Microsoft Windows 8.1 Update',
            'description': 'The new update to the Windows 8 OS brings improved performance for mouse and keyboard users.',
            'uploader_id': '6085384d-619e-11e3-b231-14feb5ca9861',
            'uploader': 'Sarah Mitroff',
            'duration': 70,
            'timestamp': 1396479627,
            'upload_date': '20140402',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.cnet.com/videos/whiny-pothole-tweets-at-local-government-when-hit-by-cars-tomorrow-daily-187/',
        'md5': 'f11d27b2fa18597fbf92444d2a9ed386',
        'info_dict': {
            'id': 'kjOJd_OoVJqbg_ZD8MZCOk8Wekb9QccK',
            'display_id': 'whiny-pothole-tweets-at-local-government-when-hit-by-cars-tomorrow-daily-187',
            'ext': 'mp4',
            'title': 'Whiny potholes tweet at local government when hit by cars (Tomorrow Daily 187)',
            'description': 'md5:d2b9a95a5ffe978ae6fbd4cf944d618f',
            'uploader_id': 'b163284d-6b73-44fc-b3e6-3da66c392d40',
            'uploader': 'Ashley Esqueda',
            'duration': 1482,
            'timestamp': 1433289889,
            'upload_date': '20150603',
        },
    }, {
        'url': 'http://www.zdnet.com/video/share/video-keeping-android-smartphones-and-tablets-secure/',
        'info_dict': {
            'id': 'k0r4T_ehht4xW_hAOqiVQPuBDPZ8SRjt',
            'display_id': 'video-keeping-android-smartphones-and-tablets-secure',
            'ext': 'mp4',
            'title': 'Video: Keeping Android smartphones and tablets secure',
            'description': 'Here\'s the best way to keep Android devices secure, and what you do when they\'ve come to the end of their lives.',
            'uploader_id': 'f2d97ea2-8175-11e2-9d12-0018fe8a00b0',
            'uploader': 'Adrian Kingsley-Hughes',
            'duration': 731,
            'timestamp': 1449129925,
            'upload_date': '20151203',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.zdnet.com/video/huawei-matebook-x-video/',
        'only_matching': True,
    }]

    MPX_ACCOUNTS = {
        'cnet': 2198311517,
        'zdnet': 2387448114,
    }

    def _real_extract(self, url):
        site, display_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, display_id)

        data_json = self._html_search_regex(
            r"data(?:-(?:cnet|zdnet))?-video(?:-(?:uvp(?:js)?|player))?-options='([^']+)'",
            webpage, 'data json')
        data = self._parse_json(data_json, display_id)
        vdata = data.get('video') or (data.get('videos') or data.get('playlist'))[0]

        video_id = vdata['mpxRefId']

        title = vdata['title']
        author = vdata.get('author')
        if author:
            uploader = '%s %s' % (author['firstName'], author['lastName'])
            uploader_id = author.get('id')
        else:
            uploader = None
            uploader_id = None

        info = self._extract_video_info(video_id, site, self.MPX_ACCOUNTS[site])
        info.update({
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'duration': int_or_none(vdata.get('duration')),
            'uploader': uploader,
            'uploader_id': uploader_id,
        })
        return info
