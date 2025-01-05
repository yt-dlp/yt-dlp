from .common import InfoExtractor
from ..utils import int_or_none


class DigitekaIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?(?:digiteka\.net|ultimedia\.com)/
        (?:
            deliver/
            (?P<embed_type>
                generic|
                musique
            )
            (?:/[^/]+)*/
            (?:
                src|
                article
            )|
            default/index/video
            (?P<site_type>
                generic|
                music
            )
            /id
        )/(?P<id>[\d+a-z]+)'''
    _EMBED_REGEX = [
        r'<(?:iframe|script)(?:(?!>)[\s\S])*(?:data-)?src=["\'](?P<url>(?:https?:)?//(?:www\.)?(?:digiteka\.net|ultimedia\.com)/deliver/(?P<embed_type>generic|musique)(?:/[^/]+)*/(?:src|article)/(?P<id>[\d+a-z]+))',
    ]
    _TESTS = [
        {
            'url': 'https://www.ultimedia.com/deliver/generic/iframe/mdtk/01747256/zone/60/src/x8smpxf',
            'info_dict': {
                'id': 'x8smpxf',
                'title': 'B. Bazin (Saint-Gobain) \'Notre cours de bourse a doublé depuis 2 ans et il a encore du potentiel !\'',
                'thumbnail': 'https://vod.digiteka.com/x8smpxf/thumbnails/e7c0403e5ff43ef78ee7baa8e27d3c26fb1deaa4-858x480.jpg',
                'url': 'https://assets.digiteka.com/encoded/04ddd4e10a9bb92f2a6e15d5adf40c9154db532a/mp4/d2da1c9e12f03d3f_480.mp4',
                'ext': 'mp4',
            },
        },
    ]
    _WEBPAGE_TESTS = [
        {
            'url': 'https://www.boursorama.com/bourse/actualites/le-retour-des-taux-negatifs-est-il-possible-169e3e0cf337df132285b41e124dc98e',
            'info_dict': {
                'id': 'xvussq5',
                'title': 'Le retour des taux négatifs est-il possible ? ',
                'thumbnail': 'https://vod.digiteka.com/xvussq5/thumbnails/9a4df121fc0532ab4d0befbece630fd7725d91a7-858x480.jpg',
                'url': 'https://assets.digiteka.com/encoded/0308c71b8ba91157ae76f0ca21c58f80e63ccf7a/mp4/0dde8b5bc0a8f240_480.mp4',
                'ext': 'mp4',
            },
        },
    ]

    def _fallback_to_iframe_content(self, url, video_id):
        iframe_content = self._download_webpage(url, video_id)

        video_url = self._og_search_video_url(iframe_content)
        video_format = video_url.split('.')[-1]
        video_title = self._og_search_title(iframe_content)
        video_thumbnail = self._og_search_thumbnail(iframe_content)

        return {
            'id': video_id,
            'title': video_title,
            'thumbnail': video_thumbnail,
            'formats': [
                {
                    'url': video_url,
                    'ext': video_format,
                },
            ],
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        video_type = mobj.group('embed_type') or mobj.group('site_type')
        if video_type == 'music':
            video_type = 'musique'

        deliver_info = self._download_json(
            f'http://www.ultimedia.com/deliver/video?video={video_id}&topic={video_type}',
            video_id,
        )
        if not deliver_info:
            return self._fallback_to_iframe_content(url, video_id)
        yt_id = deliver_info.get('yt_id')
        if yt_id:
            return self.url_result(yt_id, 'Youtube')

        jwconf = deliver_info['jwconf']

        formats = []

        for source in jwconf['playlist'][0]['sources']:
            if source['file'] is not False:
                formats.append(
                    {
                        'url': source['file'],
                        'format_id': source.get('label'),
                    },
                )
        if not formats:
            return self._fallback_to_iframe_content(url, video_id)

        title = deliver_info['title']
        thumbnail = jwconf.get('image')
        duration = int_or_none(deliver_info.get('duration'))
        timestamp = int_or_none(deliver_info.get('release_time'))
        uploader_id = deliver_info.get('owner_id')

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': timestamp,
            'uploader_id': uploader_id,
            'formats': formats,
        }
