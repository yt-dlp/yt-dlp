import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    parse_iso8601,
    remove_end,
)


class LifeNewsIE(InfoExtractor):
    IE_NAME = 'life'
    IE_DESC = 'Life.ru'
    _VALID_URL = r'https?://life\.ru/t/[^/]+/(?P<id>\d+)'

    _TESTS = [{
        # single video embedded via video/source
        'url': 'https://life.ru/t/новости/98736',
        'md5': '77c95eaefaca216e32a76a343ad89d23',
        'info_dict': {
            'id': '98736',
            'ext': 'mp4',
            'title': 'Мужчина нашел дома архив оборонного завода',
            'description': 'md5:3b06b1b39b5e2bea548e403d99b8bf26',
            'timestamp': 1344154740,
            'upload_date': '20120805',
            'view_count': int,
        }
    }, {
        # single video embedded via iframe
        'url': 'https://life.ru/t/новости/152125',
        'md5': '77d19a6f0886cd76bdbf44b4d971a273',
        'info_dict': {
            'id': '152125',
            'ext': 'mp4',
            'title': 'В Сети появилось видео захвата «Правым сектором» колхозных полей ',
            'description': 'Жители двух поселков Днепропетровской области не простили радикалам угрозу лишения плодородных земель и пошли в лобовую. ',
            'timestamp': 1427961840,
            'upload_date': '20150402',
            'view_count': int,
        }
    }, {
        # two videos embedded via iframe
        'url': 'https://life.ru/t/новости/153461',
        'info_dict': {
            'id': '153461',
            'title': 'В Москве спасли потерявшегося медвежонка, который спрятался на дереве',
            'description': 'Маленький хищник не смог найти дорогу домой и обрел временное убежище на тополе недалеко от жилого массива, пока его не нашла соседская собака.',
            'timestamp': 1430825520,
            'view_count': int,
        },
        'playlist': [{
            'md5': '9b6ef8bc0ffa25aebc8bdb40d89ab795',
            'info_dict': {
                'id': '153461-video1',
                'ext': 'mp4',
                'title': 'В Москве спасли потерявшегося медвежонка, который спрятался на дереве (Видео 1)',
                'description': 'Маленький хищник не смог найти дорогу домой и обрел временное убежище на тополе недалеко от жилого массива, пока его не нашла соседская собака.',
                'timestamp': 1430825520,
                'upload_date': '20150505',
            },
        }, {
            'md5': 'ebb3bf3b1ce40e878d0d628e93eb0322',
            'info_dict': {
                'id': '153461-video2',
                'ext': 'mp4',
                'title': 'В Москве спасли потерявшегося медвежонка, который спрятался на дереве (Видео 2)',
                'description': 'Маленький хищник не смог найти дорогу домой и обрел временное убежище на тополе недалеко от жилого массива, пока его не нашла соседская собака.',
                'timestamp': 1430825520,
                'upload_date': '20150505',
            },
        }],
    }, {
        'url': 'https://life.ru/t/новости/213035',
        'only_matching': True,
    }, {
        'url': 'https://life.ru/t/%D0%BD%D0%BE%D0%B2%D0%BE%D1%81%D1%82%D0%B8/153461',
        'only_matching': True,
    }, {
        'url': 'https://life.ru/t/новости/411489/manuel_vals_nazval_frantsiiu_tsieliu_nomier_odin_dlia_ighil',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_urls = re.findall(
            r'<video[^>]+><source[^>]+src=["\'](.+?)["\']', webpage)

        iframe_links = re.findall(
            r'<iframe[^>]+src=["\']((?:https?:)?//embed\.life\.ru/(?:embed|video)/.+?)["\']',
            webpage)

        if not video_urls and not iframe_links:
            raise ExtractorError('No media links available for %s' % video_id)

        title = remove_end(
            self._og_search_title(webpage),
            ' - Life.ru')

        description = self._og_search_description(webpage)

        view_count = self._html_search_regex(
            r'<div[^>]+class=(["\']).*?\bhits-count\b.*?\1[^>]*>\s*(?P<value>\d+)\s*</div>',
            webpage, 'view count', fatal=False, group='value')

        timestamp = parse_iso8601(self._search_regex(
            r'<time[^>]+datetime=(["\'])(?P<value>.+?)\1',
            webpage, 'upload date', fatal=False, group='value'))

        common_info = {
            'description': description,
            'view_count': int_or_none(view_count),
            'timestamp': timestamp,
        }

        def make_entry(video_id, video_url, index=None):
            cur_info = dict(common_info)
            cur_info.update({
                'id': video_id if not index else '%s-video%s' % (video_id, index),
                'url': video_url,
                'title': title if not index else '%s (Видео %s)' % (title, index),
            })
            return cur_info

        def make_video_entry(video_id, video_url, index=None):
            video_url = compat_urlparse.urljoin(url, video_url)
            return make_entry(video_id, video_url, index)

        def make_iframe_entry(video_id, video_url, index=None):
            video_url = self._proto_relative_url(video_url, 'http:')
            cur_info = make_entry(video_id, video_url, index)
            cur_info['_type'] = 'url_transparent'
            return cur_info

        if len(video_urls) == 1 and not iframe_links:
            return make_video_entry(video_id, video_urls[0])

        if len(iframe_links) == 1 and not video_urls:
            return make_iframe_entry(video_id, iframe_links[0])

        entries = []

        if video_urls:
            for num, video_url in enumerate(video_urls, 1):
                entries.append(make_video_entry(video_id, video_url, num))

        if iframe_links:
            for num, iframe_link in enumerate(iframe_links, len(video_urls) + 1):
                entries.append(make_iframe_entry(video_id, iframe_link, num))

        playlist = common_info.copy()
        playlist.update(self.playlist_result(entries, video_id, title, description))
        return playlist


class LifeEmbedIE(InfoExtractor):
    IE_NAME = 'life:embed'
    _VALID_URL = r'https?://embed\.life\.ru/(?:embed|video)/(?P<id>[\da-f]{32})'

    _TESTS = [{
        'url': 'http://embed.life.ru/embed/e50c2dec2867350528e2574c899b8291',
        'md5': 'b889715c9e49cb1981281d0e5458fbbe',
        'info_dict': {
            'id': 'e50c2dec2867350528e2574c899b8291',
            'ext': 'mp4',
            'title': 'e50c2dec2867350528e2574c899b8291',
            'thumbnail': r're:http://.*\.jpg',
        }
    }, {
        # with 1080p
        'url': 'https://embed.life.ru/video/e50c2dec2867350528e2574c899b8291',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        thumbnail = None
        formats = []

        def extract_m3u8(manifest_url):
            formats.extend(self._extract_m3u8_formats(
                manifest_url, video_id, 'mp4',
                entry_protocol='m3u8_native', m3u8_id='m3u8'))

        def extract_original(original_url):
            formats.append({
                'url': original_url,
                'format_id': determine_ext(original_url, None),
                'quality': 1,
            })

        playlist = self._parse_json(
            self._search_regex(
                r'options\s*=\s*({.+?});', webpage, 'options', default='{}'),
            video_id).get('playlist', {})
        if playlist:
            master = playlist.get('master')
            if isinstance(master, compat_str) and determine_ext(master) == 'm3u8':
                extract_m3u8(compat_urlparse.urljoin(url, master))
            original = playlist.get('original')
            if isinstance(original, compat_str):
                extract_original(original)
            thumbnail = playlist.get('image')

        # Old rendition fallback
        if not formats:
            for video_url in re.findall(r'"file"\s*:\s*"([^"]+)', webpage):
                video_url = compat_urlparse.urljoin(url, video_url)
                if determine_ext(video_url) == 'm3u8':
                    extract_m3u8(video_url)
                else:
                    extract_original(video_url)

        thumbnail = thumbnail or self._search_regex(
            r'"image"\s*:\s*"([^"]+)', webpage, 'thumbnail', default=None)

        return {
            'id': video_id,
            'title': video_id,
            'thumbnail': thumbnail,
            'formats': formats,
        }
