from .common import InfoExtractor


class MirrorCoUKIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mirror\.co\.uk/[/+[\w-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.mirror.co.uk/tv/tv-news/love-island-fans-baffled-after-27163139',
        'info_dict': {
            'id': 'voyyS7SV',
            'ext': 'mp4',
            'title': 'Love Island: Gemma Owen enters the villa',
            'description': "Love Island: Michael Owen's daughter Gemma Owen enters the villa.",
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/voyyS7SV/poster.jpg?width=720',
            'timestamp': 1654547895,
            'duration': 57.0,
            'upload_date': '20220606',
        }
    }, {
        'url': 'https://www.mirror.co.uk/3am/celebrity-news/michael-jacksons-son-blankets-new-25344890',
        'info_dict': {
            'id': 'jyXpdvxp',
            'ext': 'mp4',
            "title": "Michael Jackson’s son Bigi calls for action on climate change",
            "description": "Michael Jackson's son, Bigi Jackson, calls on world leaders to take action against climate change, saying 'we have some work to do.'",
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/jyXpdvxp/poster.jpg?width=720',
            'timestamp': 1635749907,
            'duration': 56.0,
            'upload_date': '20211101',
        }
    }, {
        'url': 'https://www.mirror.co.uk/sport/football/news/antonio-conte-next-tottenham-manager-25346042',
        'info_dict': {
            'id': 'q6FkKa4p',
            'ext': 'mp4',
            "title": "Nuno sacked by Tottenham after fifth Premier League defeat of the season",
            "description": "Nuno Espirito Santo has been sacked as Tottenham boss after only four months in charge.",
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/q6FkKa4p/poster.jpg?width=720',
            'timestamp': 1635763157,
            'duration': 40.0,
            'upload_date': '20211101',
        }
    }, {
        'url': 'https://www.mirror.co.uk/3am/celebrity-news/johnny-depp-splashes-50k-curry-27160737',
        'info_dict': {
            'id': 'IT0oa1nH',
            'ext': 'mp4',
            "title": "Johnny Depp Leaves The Grand Hotel in Birmingham",
            "description": "Johnny Depp Leaves The Grand Hotel in Birmingham.",
            'thumbnail': "https://cdn.jwplayer.com/v2/media/IT0oa1nH/poster.jpg?width=720",
            'timestamp': 1654524120,
            'duration': 65.0,
            'upload_date': '20220606',
        }
    }, {
        'url': 'https://www.mirror.co.uk/tv/tv-news/love-islands-liam-could-first-27162602',
        'info_dict': {
            'id': 'EaPr5Z2j',
            'ext': 'mp4',
            "title": "Love Island: Davide reveals plot twist after receiving text",
            "description": "Love Island: Davide reveals plot twist after receiving text",
            'thumbnail': "https://cdn.jwplayer.com/v2/media/EaPr5Z2j/poster.jpg?width=720",
            'timestamp': 1654552597,
            'duration': 23.0,
            'upload_date': '20220606',
        }
    }, {
        'url': 'https://www.mirror.co.uk/news/uk-news/william-kate-sent-message-george-27160572',
        'info_dict': {
            'id': 'ygtceXIu',
            'ext': 'mp4',
            "title": "Prince William and Kate arrive in Wales with George and Charlotte",
            "description": "Prince William and Kate Middleton arrive in Wales with children Prince George and Princess Charlotte.",
            'thumbnail': "https://cdn.jwplayer.com/v2/media/ygtceXIu/poster.jpg?width=720",
            'timestamp': 1654349678,
            'duration': 106.0,
            'upload_date': '20220604',
        }
    },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        jwplayer_id = self._search_regex(
            r'<img[^>]+?\s*?\s*c?\s*lass?\s*=?\s*["\']video-thumbnail["\']?\s*src=?\s*["\']https:\/\/cdn\.jwplayer\.com\/v2\/media\/(\w+)\/', webpage, 'data id')
        return self._parse_jwplayer_data(self._download_json(f"https://cdn.jwplayer.com/v2/media/{jwplayer_id}?page_domain=www.mirror.co.uk", video_id))
