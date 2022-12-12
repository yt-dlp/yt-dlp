from .common import InfoExtractor, NO_DEFAULT

class GolfChannelIE(InfoExtractor):
    _VALID_URL = r'https?://golfchannel\.com/video/(?P<id>[A-Za-z0-9]+)'
    _TESTS = [{
        'url': 'https://www.golfchannel.com/video/ockie-strydom-changing-plans-after-first-dp-world-tour-win',
        'info_dict': {
            'ext': 'mp4',
            'id' : 'ockie-strydom-changing',
            'title': 'Strydom changing plans after first DP World Tour win',
        },
        
    },
        {
        'url': 'https://www.golfchannel.com/video/five-players-secure-pga-tour-champions-cards-2023',
        'info_dict': {
            'ext': 'mp4',
            'id': "five-players-secure",
            'title': 'Five players secure PGA Tour Champions cards for 2023',
        },

    },
        {
        'url': 'https://www.golfchannel.com/video/nelly-korda-denny-mccarthy-success-could-result-more-mixed-teams-qbe',
        'info_dict': {
            'ext': 'mp4',
            'id': "nelly-korda-denny",
            'title': 'Korda, McCarthy find success at QBE Shootout',
        },

    },
        {
        'url': 'https://www.golfchannel.com/video/highlights-alfred-dunhill-championship-round-4',
        'info_dict': {
            'ext': 'mp4',
            'title': 'Highlights: Alfred Dunhill Championship, Round 4',
        },

    }]



    def report_drm(self, video_id, partial=NO_DEFAULT):
        if partial is not NO_DEFAULT:
            self._downloader.deprecation_warning('InfoExtractor.report_drm no longer accepts the argument partial')
        self.raise_no_formats('This video is DRM protected', expected=True, video_id=video_id)
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<h1>(.+?)</h1>', webpage, 'title')

        return {
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
        }
