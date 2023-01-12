from .mtv import MTVIE

# TODO Remove - Reason: Outdated Site


class CMTIE(MTVIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'cmt.com'
    _VALID_URL = r'https?://(?:www\.)?cmt\.com/(?:videos|shows|(?:full-)?episodes|video-clips)/(?P<id>[^/]+)'

    _TESTS = [{
        'url': 'http://www.cmt.com/videos/garth-brooks/989124/the-call-featuring-trisha-yearwood.jhtml#artist=30061',
        'md5': 'e6b7ef3c4c45bbfae88061799bbba6c2',
        'info_dict': {
            'id': '989124',
            'ext': 'mp4',
            'title': 'Garth Brooks - "The Call (featuring Trisha Yearwood)"',
            'description': 'Blame It All On My Roots',
        },
        'skip': 'Video not available',
    }, {
        'url': 'http://www.cmt.com/videos/misc/1504699/still-the-king-ep-109-in-3-minutes.jhtml#id=1739908',
        'md5': 'e61a801ca4a183a466c08bd98dccbb1c',
        'info_dict': {
            'id': '1504699',
            'ext': 'mp4',
            'title': 'Still The King Ep. 109 in 3 Minutes',
            'description': 'Relive or catch up with Still The King by watching this recap of season 1, episode 9.',
            'timestamp': 1469421000.0,
            'upload_date': '20160725',
        },
    }, {
        'url': 'http://www.cmt.com/shows/party-down-south/party-down-south-ep-407-gone-girl/1738172/playlist/#id=1738172',
        'only_matching': True,
    }, {
        'url': 'http://www.cmt.com/full-episodes/537qb3/nashville-the-wayfaring-stranger-season-5-ep-501',
        'only_matching': True,
    }, {
        'url': 'http://www.cmt.com/video-clips/t9e4ci/nashville-juliette-in-2-minutes',
        'only_matching': True,
    }]

    def _extract_mgid(self, webpage, url):
        mgid = self._search_regex(
            r'MTVN\.VIDEO\.contentUri\s*=\s*([\'"])(?P<mgid>.+?)\1',
            webpage, 'mgid', group='mgid', default=None)
        if not mgid:
            mgid = self._extract_triforce_mgid(webpage)
        return mgid

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        mgid = self._extract_mgid(webpage, url)
        return self.url_result('http://media.mtvnservices.com/embed/%s' % mgid)
