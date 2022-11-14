from .common import InfoExtractor


class BellMediaIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://(?:www\.)?
        (?P<domain>
            (?:
                ctv|
                tsn|
                bnn(?:bloomberg)?|
                thecomedynetwork|
                discovery|
                discoveryvelocity|
                sciencechannel|
                investigationdiscovery|
                animalplanet|
                bravo|
                mtv|
                space|
                etalk|
                marilyn
            )\.ca|
            (?:much|cp24)\.com
        )/.*?(?:\b(?:vid(?:eoid)?|clipId)=|-vid|~|%7E|/(?:episode)?)(?P<id>[0-9]{6,})'''
    _TESTS = [{
        'url': 'https://www.bnnbloomberg.ca/video/david-cockfield-s-top-picks~1403070',
        'md5': '3e5b8e38370741d5089da79161646635',
        'info_dict': {
            'id': '1403070',
            'ext': 'flv',
            'title': 'David Cockfield\'s Top Picks',
            'description': 'md5:810f7f8c6a83ad5b48677c3f8e5bb2c3',
            'upload_date': '20180525',
            'timestamp': 1527288600,
            'season_id': 73997,
            'season': '2018',
            'thumbnail': 'http://images2.9c9media.com/image_asset/2018_5_25_baf30cbd-b28d-4a18-9903-4bb8713b00f5_PNG_956x536.jpg',
            'tags': [],
            'categories': ['ETFs'],
            'season_number': 8,
            'duration': 272.038,
            'series': 'Market Call Tonight',
        },
    }, {
        'url': 'http://www.thecomedynetwork.ca/video/player?vid=923582',
        'only_matching': True,
    }, {
        'url': 'http://www.tsn.ca/video/expectations-high-for-milos-raonic-at-us-open~939549',
        'only_matching': True,
    }, {
        'url': 'http://www.bnn.ca/video/berman-s-call-part-two-viewer-questions~939654',
        'only_matching': True,
    }, {
        'url': 'http://www.ctv.ca/YourMorning/Video/S1E6-Monday-August-29-2016-vid938009',
        'only_matching': True,
    }, {
        'url': 'http://www.much.com/shows/atmidnight/episode948007/tuesday-september-13-2016',
        'only_matching': True,
    }, {
        'url': 'http://www.much.com/shows/the-almost-impossible-gameshow/928979/episode-6',
        'only_matching': True,
    }, {
        'url': 'http://www.ctv.ca/DCs-Legends-of-Tomorrow/Video/S2E11-Turncoat-vid1051430',
        'only_matching': True,
    }, {
        'url': 'http://www.etalk.ca/video?videoid=663455',
        'only_matching': True,
    }, {
        'url': 'https://www.cp24.com/video?clipId=1982548',
        'only_matching': True,
    }]
    _DOMAINS = {
        'thecomedynetwork': 'comedy',
        'discoveryvelocity': 'discvel',
        'sciencechannel': 'discsci',
        'investigationdiscovery': 'invdisc',
        'animalplanet': 'aniplan',
        'etalk': 'ctv',
        'bnnbloomberg': 'bnn',
        'marilyn': 'ctv_marilyn',
    }

    def _real_extract(self, url):
        domain, video_id = self._match_valid_url(url).groups()
        domain = domain.split('.')[0]
        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': '9c9media:%s_web:%s' % (self._DOMAINS.get(domain, domain), video_id),
            'ie_key': 'NineCNineMedia',
        }
