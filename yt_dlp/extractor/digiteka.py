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
    _EMBED_REGEX = [r'<(?:iframe|script)(?:(?!>)[\s\S])*(?:data-)?src=["\'](?P<url>(?:https?:)?//(?:www\.)?(?:digiteka\.net|ultimedia\.com)/deliver/(?P<embed_type>generic|musique)(?:/[^/]+)*/(?:src|article)/(?P<id>[\d+a-z]+))']
    _TESTS = [
        {'url': 'https://www.ultimedia.com/deliver/generic/iframe/mdtk/01747256/zone/60/src/x8smpxf'}, # direct url
        {'url': 'https://www.boursorama.com/bourse/actualites/le-retour-des-taux-negatifs-est-il-possible-169e3e0cf337df132285b41e124dc98e'} # from an embed
    ]

    def _fallback_to_iframe_content(self, url, video_id):
        iframe_content = self._download_webpage(url, video_id)
        VIDEO_URL_REGEX = '<meta property="og:video" content="(?P<url>.*)"/>'
        VIDEO_TITLE_REGEX = '<meta property="og:title" content="(?P<title>.*)"/>'
        VIDEO_THUMBNAIL_REGEX = '<meta property="og:image" content="(?P<thumbnail>.*)"/>'

        video_url = self._search_regex(VIDEO_URL_REGEX, iframe_content, 'url')
        video_format = video_url.split('.')[-1]
        video_title = self._search_regex(VIDEO_TITLE_REGEX, iframe_content, 'title')
        video_thumbnail = self._search_regex(VIDEO_THUMBNAIL_REGEX, iframe_content, 'thumbnail')

        return {
            'id': video_id,
            'title': video_title,
            'thumbnail': video_thumbnail,
            'formats': [{
                'url': video_url,
                'ext': video_format,
            }]
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        video_type = mobj.group('embed_type') or mobj.group('site_type')
        if video_type == 'music':
            video_type = 'musique'

        deliver_info = self._download_json(
            f'http://www.ultimedia.com/deliver/video?video={video_id}&topic={video_type}',
            video_id)
        if not deliver_info:
            # Apparently some video's deliver_info are not accessible this way anymore
            return self._fallback_to_iframe_content(url, video_id)
        yt_id = deliver_info.get('yt_id')
        if yt_id:
            return self.url_result(yt_id, 'Youtube')

        jwconf = deliver_info['jwconf']


        formats = []

        for source in jwconf['playlist'][0]['sources']:
            if source['file'] is not False:
                formats.append({
                    'url': source['file'],
                    'format_id': source.get('label'),
                })
        if len(formats) == 0:
            # the file urls are not available from the json directly anymore, but
            # can be found in the iframe content
            return self._fallback_to_iframe_content(url, video_id)

        formats.append({
            'url': video_url,
            'ext': video_format,
        })

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
