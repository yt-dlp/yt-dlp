from .common import InfoExtractor


class MLSSoccerIE(InfoExtractor):
    _VALID_DOMAINS = r'(?:(?:cfmontreal|intermiamicf|lagalaxy|lafc|houstondynamofc|dcunited|atlutd|mlssoccer|fcdallas|columbuscrew|coloradorapids|fccincinnati|chicagofirefc|austinfc|nashvillesc|whitecapsfc|sportingkc|soundersfc|sjearthquakes|rsl|timbers|philadelphiaunion|orlandocitysc|newyorkredbulls|nycfc)\.com|(?:torontofc)\.ca|(?:revolutionsoccer)\.net)'
    _VALID_URL = r'https?://(?:www\.)?%s/video/#?(?P<id>[^/&$#?]+)' % _VALID_DOMAINS

    _TESTS = [{
        'url': 'https://www.mlssoccer.com/video/the-octagon-can-alphonso-davies-lead-canada-to-first-world-cup-since-1986#the-octagon-can-alphonso-davies-lead-canada-to-first-world-cup-since-1986',
        'info_dict': {
            'id': '6276033198001',
            'ext': 'mp4',
            'title': 'The Octagon | Can Alphonso Davies lead Canada to first World Cup since 1986?',
            'description': 'md5:f0a883ee33592a0221798f451a98be8f',
            'thumbnail': 'https://cf-images.us-east-1.prod.boltdns.net/v1/static/5530036772001/1bbc44f6-c63c-4981-82fa-46b0c1f891e0/5c1ca44a-a033-4e98-b531-ff24c4947608/160x90/match/image.jpg',
            'duration': 350.165,
            'timestamp': 1633627291,
            'uploader_id': '5530036772001',
            'tags': ['club/canada'],
            'is_live': False,
            'upload_date': '20211007',
            'filesize_approx': 255193528.83200002
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://www.whitecapsfc.com/video/highlights-san-jose-earthquakes-vs-vancouver-whitecaps-fc-october-23-2021#highlights-san-jose-earthquakes-vs-vancouver-whitecaps-fc-october-23-2021',
        'only_matching': True
    }, {
        'url': 'https://www.torontofc.ca/video/highlights-toronto-fc-vs-cf-montreal-october-23-2021-x6733#highlights-toronto-fc-vs-cf-montreal-october-23-2021-x6733',
        'only_matching': True
    }, {
        'url': 'https://www.sportingkc.com/video/post-match-press-conference-john-pulskamp-oct-27-2021#post-match-press-conference-john-pulskamp-oct-27-2021',
        'only_matching': True
    }, {
        'url': 'https://www.soundersfc.com/video/highlights-seattle-sounders-fc-vs-sporting-kansas-city-october-23-2021',
        'only_matching': True
    }, {
        'url': 'https://www.sjearthquakes.com/video/#highlights-austin-fc-vs-san-jose-earthquakes-june-19-2021',
        'only_matching': True
    }, {
        'url': 'https://www.rsl.com/video/2021-u-of-u-health-mic-d-up-vs-colorado-10-16-21#2021-u-of-u-health-mic-d-up-vs-colorado-10-16-21',
        'only_matching': True
    }, {
        'url': 'https://www.timbers.com/video/highlights-d-chara-asprilla-with-goals-in-portland-timbers-2-0-win-over-san-jose#highlights-d-chara-asprilla-with-goals-in-portland-timbers-2-0-win-over-san-jose',
        'only_matching': True
    }, {
        'url': 'https://www.philadelphiaunion.com/video/highlights-torvphi',
        'only_matching': True
    }, {
        'url': 'https://www.orlandocitysc.com/video/highlight-columbus-crew-vs-orlando-city-sc',
        'only_matching': True
    }, {
        'url': 'https://www.newyorkredbulls.com/video/all-access-matchday-double-derby-week#all-access-matchday-double-derby-week',
        'only_matching': True
    }, {
        'url': 'https://www.nycfc.com/video/highlights-nycfc-1-0-chicago-fire-fc#highlights-nycfc-1-0-chicago-fire-fc',
        'only_matching': True
    }, {
        'url': 'https://www.revolutionsoccer.net/video/two-minute-highlights-revs-1-rapids-0-october-27-2021#two-minute-highlights-revs-1-rapids-0-october-27-2021',
        'only_matching': True
    }, {
        'url': 'https://www.nashvillesc.com/video/goal-c-j-sapong-nashville-sc-92nd-minute',
        'only_matching': True
    }, {
        'url': 'https://www.cfmontreal.com/video/faits-saillants-tor-v-mtl#faits-saillants-orl-v-mtl-x5645',
        'only_matching': True
    }, {
        'url': 'https://www.intermiamicf.com/video/all-access-victory-vs-nashville-sc-by-ukg#all-access-victory-vs-nashville-sc-by-ukg',
        'only_matching': True
    }, {
        'url': 'https://www.lagalaxy.com/video/#moment-of-the-month-presented-by-san-manuel-casino-rayan-raveloson-scores-his-se',
        'only_matching': True
    }, {
        'url': 'https://www.lafc.com/video/breaking-down-lafc-s-final-6-matches-of-the-2021-mls-regular-season#breaking-down-lafc-s-final-6-matches-of-the-2021-mls-regular-season',
        'only_matching': True
    }, {
        'url': 'https://www.houstondynamofc.com/video/postgame-press-conference-michael-nelson-presented-by-coushatta-casino-res-x9660#postgame-press-conference-michael-nelson-presented-by-coushatta-casino-res-x9660',
        'only_matching': True
    }, {
        'url': 'https://www.dcunited.com/video/tony-alfaro-my-family-pushed-me-to-believe-everything-was-possible',
        'only_matching': True
    }, {
        'url': 'https://www.fcdallas.com/video/highlights-fc-dallas-vs-minnesota-united-fc-october-02-2021#highlights-fc-dallas-vs-minnesota-united-fc-october-02-2021',
        'only_matching': True
    }, {
        'url': 'https://www.columbuscrew.com/video/match-rewind-columbus-crew-vs-new-york-red-bulls-october-23-2021',
        'only_matching': True
    }, {
        'url': 'https://www.coloradorapids.com/video/postgame-reaction-robin-fraser-october-27#postgame-reaction-robin-fraser-october-27',
        'only_matching': True
    }, {
        'url': 'https://www.fccincinnati.com/video/#keeping-cincy-chill-presented-by-coors-lite',
        'only_matching': True
    }, {
        'url': 'https://www.chicagofirefc.com/video/all-access-fire-score-dramatic-road-win-in-cincy#all-access-fire-score-dramatic-road-win-in-cincy',
        'only_matching': True
    }, {
        'url': 'https://www.austinfc.com/video/highlights-colorado-rapids-vs-austin-fc-september-29-2021#highlights-colorado-rapids-vs-austin-fc-september-29-2021',
        'only_matching': True
    }, {
        'url': 'https://www.atlutd.com/video/goal-josef-martinez-scores-in-the-73rd-minute#goal-josef-martinez-scores-in-the-73rd-minute',
        'only_matching': True
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        data_json = self._parse_json(self._html_search_regex(r'data-options\=\"([^\"]+)\"', webpage, 'json'), id)['videoList'][0]
        return {
            'id': id,
            '_type': 'url',
            'url': 'https://players.brightcove.net/%s/default_default/index.html?videoId=%s' % (data_json['accountId'], data_json['videoId']),
            'ie_key': 'BrightcoveNew',
        }
