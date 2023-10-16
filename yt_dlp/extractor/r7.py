from .common import InfoExtractor
from ..utils import int_or_none


class R7IE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://
                        (?:
                            (?:[a-zA-Z]+)\.r7\.com(?:/[^/]+)+/idmedia/|
                            noticias\.r7\.com(?:/[^/]+)+/[^/]+-|
                            player\.r7\.com/video/i/
                        )
                        (?P<id>[\da-f]{24})
                    '''
    _TESTS = [{
        'url': 'http://videos.r7.com/policiais-humilham-suspeito-a-beira-da-morte-morre-com-dignidade-/idmedia/54e7050b0cf2ff57e0279389.html',
        'md5': '403c4e393617e8e8ddc748978ee8efde',
        'info_dict': {
            'id': '54e7050b0cf2ff57e0279389',
            'ext': 'mp4',
            'title': 'Policiais humilham suspeito à beira da morte: "Morre com dignidade"',
            'description': 'md5:01812008664be76a6479aa58ec865b72',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 98,
            'like_count': int,
            'view_count': int,
        },
    }, {
        'url': 'http://esportes.r7.com/videos/cigano-manda-recado-aos-fas/idmedia/4e176727b51a048ee6646a1b.html',
        'only_matching': True,
    }, {
        'url': 'http://noticias.r7.com/record-news/video/representante-do-instituto-sou-da-paz-fala-sobre-fim-do-estatuto-do-desarmamento-5480fc580cf2285b117f438d/',
        'only_matching': True,
    }, {
        'url': 'http://player.r7.com/video/i/54e7050b0cf2ff57e0279389?play=true&video=http://vsh.r7.com/54e7050b0cf2ff57e0279389/ER7_RE_BG_MORTE_JOVENS_570kbps_2015-02-2009f17818-cc82-4c8f-86dc-89a66934e633-ATOS_copy.mp4&linkCallback=http://videos.r7.com/policiais-humilham-suspeito-a-beira-da-morte-morre-com-dignidade-/idmedia/54e7050b0cf2ff57e0279389.html&thumbnail=http://vtb.r7.com/ER7_RE_BG_MORTE_JOVENS_570kbps_2015-02-2009f17818-cc82-4c8f-86dc-89a66934e633-thumb.jpg&idCategory=192&share=true&layout=full&full=true',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'http://player-api.r7.com/video/i/%s' % video_id, video_id)

        title = video['title']

        formats = []
        media_url_hls = video.get('media_url_hls')
        if media_url_hls:
            formats.extend(self._extract_m3u8_formats(
                media_url_hls, video_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=False))
        media_url = video.get('media_url')
        if media_url:
            f = {
                'url': media_url,
                'format_id': 'http',
            }
            # m3u8 format always matches the http format, let's copy metadata from
            # one to another
            m3u8_formats = list(filter(
                lambda f: f.get('vcodec') != 'none', formats))
            if len(m3u8_formats) == 1:
                f_copy = m3u8_formats[0].copy()
                f_copy.update(f)
                f_copy['protocol'] = 'http'
                f = f_copy
            formats.append(f)

        description = video.get('description')
        thumbnail = video.get('thumb')
        duration = int_or_none(video.get('media_duration'))
        like_count = int_or_none(video.get('likes'))
        view_count = int_or_none(video.get('views'))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'like_count': like_count,
            'view_count': view_count,
            'formats': formats,
        }


class R7ArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[a-zA-Z]+)\.r7\.com/(?:[^/]+/)+[^/?#&]+-(?P<id>\d+)'
    _TEST = {
        'url': 'http://tv.r7.com/record-play/balanco-geral/videos/policiais-humilham-suspeito-a-beira-da-morte-morre-com-dignidade-16102015',
        'only_matching': True,
    }

    @classmethod
    def suitable(cls, url):
        return False if R7IE.suitable(url) else super(R7ArticleIE, cls).suitable(url)

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        video_id = self._search_regex(
            r'<div[^>]+(?:id=["\']player-|class=["\']embed["\'][^>]+id=["\'])([\da-f]{24})',
            webpage, 'video id')

        return self.url_result('http://player.r7.com/video/i/%s' % video_id, R7IE.ie_key())
