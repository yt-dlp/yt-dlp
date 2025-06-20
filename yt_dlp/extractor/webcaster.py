import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    join_nonempty,
    xpath_text,
)


class WebcasterBaseIE(InfoExtractor):
    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_xml(url, video_id)

        title = xpath_text(video, './/event_name', 'event name')
        if not title:
            msg = 'Invalid video'
            if error_note := xpath_text(video, './/message'):
                msg = f'{msg}: {error_note}'
            raise ExtractorError(msg, expected=True)

        formats = []
        for format_id in (None, 'noise'):
            track_tag = join_nonempty('track', format_id, delim='_')
            for track in video.findall(f'.//iphone/{track_tag}'):
                track_url = track.text
                if not track_url:
                    continue
                if determine_ext(track_url) == 'm3u8':
                    m3u8_formats = self._extract_m3u8_formats(
                        track_url, video_id, 'mp4',
                        entry_protocol='m3u8_native',
                        m3u8_id=join_nonempty('hls', format_id, delim='-'), fatal=False)
                    for f in m3u8_formats:
                        f.update({
                            'source_preference': 0 if format_id == 'noise' else 1,
                            'format_note': track.get('title'),
                        })
                    formats.extend(m3u8_formats)

        thumbnail = xpath_text(video, './/image', 'thumbnail')

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }


class WebcasterIE(WebcasterBaseIE):
    _VALID_URL = r'https?://bl\.webcaster\.pro/(?:quote|media)/start/(?:api_)?free_(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'http://bl.webcaster.pro/media/start/free_6246c7a4453ac4c42b4398f840d13100_hd/2_2991109016/e8d0d82587ef435480118f9f9c41db41/4635726126',
        'md5': 'f0c8dc1b89bf9f9814c5348acde408c8',
        'info_dict': {
            'id': '6246c7a4453ac4c42b4398f840d13100_hd',
            'ext': 'mp4',
            'title': 'Авангард - Нефтехимик 1:3',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'https://bl.webcaster.pro/media/start/api_free_0021c098d99da3f6e74092d1c857fdce_hd/5_6801634533/7396a49492257cd0e9216d81208e7cd7/4634356501',
        'md5': 'b13dcceaeaaf4766d64414a768c285b8',
        'info_dict': {
            'id': '0021c098d99da3f6e74092d1c857fdce_hd',
            'ext': 'mp4',
            'title': 'Малые города России.  Мартыново - лен, кацкари и  Белая Корова. 07.11.2016',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'https://bl.webcaster.pro/quote/start/free_6cabef900bf3e30dd699f16fc2d25ae5/q1199219/d78c13e415110de17295c0ed2d7ea9dd/4852644931',
        'md5': '58fe8def3a82fa3704a153f6b210c574',
        'info_dict': {
            'id': '6cabef900bf3e30dd699f16fc2d25ae5',
            'ext': 'mp4',
            'title': 'Гол. 3:0. Шмелёв Сергей (Салават Юлаев) прошивает вратаря',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        # http://video.khl.ru/quotes/393859
        'url': 'http://bl.webcaster.pro/quote/start/free_c8cefd240aa593681c8d068cff59f407_hd/q393859/eb173f99dd5f558674dae55f4ba6806d/1480289104?sr%3D105%26fa%3D1%26type_id%3D18',
        'expected_exception': 'ExtractorError',
    }, {
        'url': 'https://bl.webcaster.pro/media/start/api_free_903d301687b0455c53088ac0ab14223a_hd/5_2406026867/77d98a80c1083db7c4a4224a17606731/4740107522?locale=en',
        'expected_exception': 'ExtractorError',
    }]


class WebcasterFeedBaseIE(InfoExtractor):
    def _extract_from_webpage(self, url, webpage):
        yield from super()._extract_from_webpage(url, webpage)

        for secure in (True, False):
            video_url = self._og_search_video_url(webpage, secure=secure, default=None)
            if video_url:
                mobj = re.search(
                    r'config=(?P<url>https?://bl\.webcaster\.pro/feed/start/free_[^?&=]+)',
                    video_url)
                if mobj:
                    yield self.url_result(mobj.group('url'), self)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        feed = self._download_xml(url, video_id)

        video_url = xpath_text(
            feed, ('video_hd', 'video'), 'video url', fatal=True)

        return self.url_result(video_url)


class WebcasterFeedIE(WebcasterFeedBaseIE):
    _VALID_URL = r'https?://bl\.webcaster\.pro/feed/start/(?:api_)?free_(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://bl.webcaster.pro/feed/start/api_free_83f86fca0321a284215bfc79bc84b0e4_hd/5_8903164936/5d58e8f398dc57a603d4a1d230f1c2ee/4606466761',
        'md5': '9cfe5c264467494304edc58876d6b6b7',
        'info_dict': {
            'id': '83f86fca0321a284215bfc79bc84b0e4_hd',
            'ext': 'mp4',
            'title': 'Большое интервью 19.12.2015. Юрий Энтин',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'https://bl.webcaster.pro/feed/start/free_2689e8cc10e002cd5bd5df023700541e_hd/2_9028444105/dfbbc633edf34af7254dec8baccd7a59/4652352931',
        'md5': '0b0dc9352a8f84875607edb81046da5d',
        'info_dict': {
            'id': '2689e8cc10e002cd5bd5df023700541e_hd',
            'ext': 'mp4',
            'title': 'Мастер-шоу КХЛ 2017',
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'http://bl.webcaster.pro/feed/start/free_c8cefd240aa593681c8d068cff59f407_hd/q393859/eb173f99dd5f558674dae55f4ba6806d/1480289104',
        'only_matching': True,
    }]


class WebcasterPlayerEmbedIE(InfoExtractor):
    _VALID_URL = False
    _EMBED_REGEX = [r'<(?:object|a|span[^>]+class=["\']webcaster-player["\'])[^>]+data(?:-config)?=(["\']).*?config=(?P<url>https?://(?:(?!\1).)+)\1']
