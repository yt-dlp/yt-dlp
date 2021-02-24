from __future__ import unicode_literals

from .nhl import NHLBaseIE


class MLBIE(NHLBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:[\da-z_-]+\.)*(?P<site>mlb)\.com/
                        (?:
                            (?:
                                (?:[^/]+/)*c-|
                                (?:
                                    shared/video/embed/(?:embed|m-internal-embed)\.html|
                                    (?:[^/]+/)+(?:play|index)\.jsp|
                                )\?.*?\bcontent_id=
                            )
                            (?P<id>\d+)
                        )
                    '''
    _CONTENT_DOMAIN = 'content.mlb.com'
    _TESTS = [
        {
            'url': 'https://www.mlb.com/mariners/video/ackleys-spectacular-catch/c-34698933',
            'md5': '632358dacfceec06bad823b83d21df2d',
            'info_dict': {
                'id': '34698933',
                'ext': 'mp4',
                'title': "Ackley's spectacular catch",
                'description': 'md5:7f5a981eb4f3cbc8daf2aeffa2215bf0',
                'duration': 66,
                'timestamp': 1405995000,
                'upload_date': '20140722',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        },
        {
            'url': 'https://www.mlb.com/video/stanton-prepares-for-derby/c-34496663',
            'md5': 'bf2619bf9cacc0a564fc35e6aeb9219f',
            'info_dict': {
                'id': '34496663',
                'ext': 'mp4',
                'title': 'Stanton prepares for Derby',
                'description': 'md5:d00ce1e5fd9c9069e9c13ab4faedfa57',
                'duration': 46,
                'timestamp': 1405120200,
                'upload_date': '20140711',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        },
        {
            'url': 'https://www.mlb.com/video/cespedes-repeats-as-derby-champ/c-34578115',
            'md5': '99bb9176531adc600b90880fb8be9328',
            'info_dict': {
                'id': '34578115',
                'ext': 'mp4',
                'title': 'Cespedes repeats as Derby champ',
                'description': 'md5:08df253ce265d4cf6fb09f581fafad07',
                'duration': 488,
                'timestamp': 1405414336,
                'upload_date': '20140715',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        },
        {
            'url': 'https://www.mlb.com/video/bautista-on-home-run-derby/c-34577915',
            'md5': 'da8b57a12b060e7663ee1eebd6f330ec',
            'info_dict': {
                'id': '34577915',
                'ext': 'mp4',
                'title': 'Bautista on Home Run Derby',
                'description': 'md5:b80b34031143d0986dddc64a8839f0fb',
                'duration': 52,
                'timestamp': 1405405122,
                'upload_date': '20140715',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        },
        {
            'url': 'https://www.mlb.com/news/blue-jays-kevin-pillar-goes-spidey-up-the-wall-to-rob-tim-beckham-of-a-homer/c-118550098',
            'md5': 'e09e37b552351fddbf4d9e699c924d68',
            'info_dict': {
                'id': '75609783',
                'ext': 'mp4',
                'title': 'Must C: Pillar climbs for catch',
                'description': '4/15/15: Blue Jays outfielder Kevin Pillar continues his defensive dominance by climbing the wall in left to rob Tim Beckham of a home run',
                'timestamp': 1429139220,
                'upload_date': '20150415',
            }
        },
        {
            'url': 'https://www.mlb.com/video/hargrove-homers-off-caldwell/c-1352023483?tid=67793694',
            'only_matching': True,
        },
        {
            'url': 'http://m.mlb.com/shared/video/embed/embed.html?content_id=35692085&topic_id=6479266&width=400&height=224&property=mlb',
            'only_matching': True,
        },
        {
            'url': 'http://mlb.mlb.com/shared/video/embed/embed.html?content_id=36599553',
            'only_matching': True,
        },
        {
            'url': 'http://mlb.mlb.com/es/video/play.jsp?content_id=36599553',
            'only_matching': True,
        },
        {
            'url': 'https://www.mlb.com/cardinals/video/piscottys-great-sliding-catch/c-51175783',
            'only_matching': True,
        },
        {
            # From http://m.mlb.com/news/article/118550098/blue-jays-kevin-pillar-goes-spidey-up-the-wall-to-rob-tim-beckham-of-a-homer
            'url': 'http://mlb.mlb.com/shared/video/embed/m-internal-embed.html?content_id=75609783&property=mlb&autoplay=true&hashmode=false&siteSection=mlb/multimedia/article_118550098/article_embed&club=mlb',
            'only_matching': True,
        },
        {
            'url': 'https://www.mlb.com/cut4/carlos-gomez-borrowed-sunglasses-from-an-as-fan/c-278912842',
            'only_matching': True,
        }
    ]
