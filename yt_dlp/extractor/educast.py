import re
from urllib import parse

from .common import (
    ExtractorError,
    InfoExtractor,
)
from ..networking import HEADRequest
from ..utils import (
    mimetype2ext,
    traverse_obj,
    unified_timestamp,
)


class EducastBaseIE(InfoExtractor):
    _API_BASE = 'https://educast.fccn.pt'

    @staticmethod
    def _paginate_and_collect(get_page_func, parse_func):
        videos = []
        page = 1
        while True:
            webpage = get_page_func(page)
            if not webpage:
                break
            new_videos = parse_func(webpage)
            found = False
            for v in new_videos:
                if not any(existing['id'] == v['id'] for existing in videos):
                    videos.append(v)
                    found = True
            if not found:
                break
            page += 1
        return videos


class EducastIE(EducastBaseIE):
    _VALID_URL = r'https?://(www)?educast\.fccn\.pt/vod/clips/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'note': 'test for public Educast video downloading the merged format',
        'url': 'https://educast.fccn.pt/vod/clips/2o06o2c6hm/streaming.html',
        'md5': '264b3e2f0c6c5d3c8e1a86e57f21d0bc',
        'info_dict': {
            'id': '2o06o2c6hm',
            'ext': 'mp4',
            'title': 'Fundamentos de Bases de Dados',
            'alt_title': '',
            'description': '',
            'uploader': 'Professor Luís Cavique',
            'channel': 'UAB - Fundamentos de Base de dados',
            'channel_url': 'https://educast.fccn.pt/results?channel=k06h42n0w',
            'thumbnail': 'https://educast.fccn.pt/img/clips/2o06o2c6hm/delivery/cover',
            'categories': ['Tecnologia e Ciências Aplicadas', 'FCCN'],
            'timestamp': 1410946740,
            'upload_date': '20140917',
            'license': 'http://creativecommons.org/licenses/by-nc-nd/2.5/pt/',
            'duration': 1041,
        },
    }, {
        'note': 'test for private Educast video downloading the merged format',
        'url': 'https://educast.fccn.pt/vod/clips/jhwehqk9/streaming.html',
        'md5': '242a4a8d1a84a4c3aab93771c3da244e',
        'info_dict': {
            'id': 'jhwehqk9',
            'ext': 'mp4',
            'title': ' Exercícios 8B. Equações Diferenciais Parciais',
            'alt_title': '',
            'description': '',
            'uploader': ' Rui Miguel Saramago',
            'channel': 'Cálculo Diferencial e Integral III - Aulas de Recuperação',
            'channel_url': 'https://educast.fccn.pt/results?channel=2fudccnyj7',
            'thumbnail': 'https://educast.fccn.pt/img/clips/jhwehqk9/delivery/cover',
            'categories': ['Ciências Naturais e Matemática', 'Universidade de Lisboa'],
            'license': 'http://creativecommons.org/licenses/by/4.0/',
            'duration': 2756,
        },
        'skip': 'This video is private and requires authentication to access',
    }, {
        'note': 'test for deprecated streaming url, should rely on fallback',
        'url': 'https://educast.fccn.pt/vod/clips/2by2fw4fkx/streaming.html',
        'md5': '88055700118db7411d1cc0da48ca1747',
        'info_dict': {
            'id': '2by2fw4fkx',
            'ext': 'mp4',
            'title': 'Teoria 3A. Sistemas de Equaces Diferenciais Lineares de Primeira Ordem_',
        },
        'expected_warnings': ['Este vídeo não está preparado para HTML5'],
        'skip': 'This video is private and requires authentication to access',
    }]

    def _extract_video_formats(self, video_json, video_id):
        formats = []
        dash_url = traverse_obj(video_json, ('dash', 'url'))
        if dash_url:
            formats += self._extract_mpd_formats(dash_url, video_id, mpd_id='dash', fatal=False)

        hls_url = traverse_obj(video_json, ('hls', 'url'))
        if hls_url:
            formats += self._extract_m3u8_formats(hls_url, video_id, ext='mp4', entry_protocol='m3u8_native', fatal=False)

        for f in formats:
            f['format_id'] = video_json.get('role')

        return formats

    def _extract_from_json(self, video_id):
        data_json_url = f'https://educast.fccn.pt/vod/clips/{video_id}/video_player/data.json'
        try:
            data_json = self._download_json(data_json_url, video_id)
        except ExtractorError as e:
            self.report_warning(e)
            return None
        if data_json.get('error'):
            self.report_warning(data_json.get('error'))
            return None

        formats = []
        info = {
            'id': video_id,
            'formats': formats,
            **traverse_obj(data_json, {
                'title': ('clip', 'name', {str}),
                'alt_title': ('subtitle', {str}),
                'description': ('clipDescription', {str}),
                'uploader': ('author', {str}),
                'timestamp': ('timestamp', {unified_timestamp}, {lambda x: x - 3600}),
                'thumbnail': ('cover', {str}),
                'license': ('licenceURL', {str}),
                'webpage_url': ('url', {str}),
                'channel': ('channel', 'name', {str}),
                'channel_url': ('channel', 'url', {str}),
                'duration': ('videos', 0, 'duration', {int}),
            }),
            'categories': [cat for cat in (
                traverse_obj(data_json, ('area', 'name'), expected_type=str),
                traverse_obj(data_json, ('institution', 'name'), expected_type=str),
            ) if cat],
        }

        for video_json in data_json.get('videos') or []:
            formats.extend(self._extract_video_formats(video_json, video_id))

        download_url = data_json.get('downloadURL')
        if download_url:
            formats.append({
                'format_id': 'merged',
                'url': download_url,
                'quality': 0,
                'format_note': 'single stream, may be lower res',
            })

        return info

    def _try_fallback(self, url, video_id):
        # Last resort for videos with no working streaming option
        KNOWN_BASENAMES = ['desktop.mp4', 'ipod.m4v', 'quicktime.mov']
        for basename in KNOWN_BASENAMES:
            format_url = url.replace('streaming.html', basename)
            response = self._request_webpage(
                HEADRequest(format_url), video_id,
                note=f'Checking availability of {basename} fallback',
                fatal=False, errnote=False)
            if not response:
                continue
            ext = mimetype2ext(response.get_header('content-type'))
            if ext not in ('mp4', 'm4v', 'mov'):
                continue
            title = None
            ext_header = response.get_header('content-disposition')
            if ext_header:
                m = re.search(r'filename\s*=\s*"([^"]+)"', ext_header, re.IGNORECASE)
                if m:
                    title = m.group(1).strip().removesuffix(f'.{ext}')
            return {
                'id': video_id,
                'title': title,
                'url': format_url,
            }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._extract_from_json(video_id) or self._try_fallback(url, video_id)


class EducastChannelIE(EducastBaseIE):
    IE_NAME = 'educast:channel'
    _VALID_URL = r'https?://(?:www\.)?educast\.fccn\.pt/vod/channels/(?P<id>[a-zA-Z0-9]+)/?(?:$|[?#])'
    _TESTS = [{
        'note': 'test for private Educast Channel',
        'url': 'https://educast.fccn.pt/vod/channels/2o0eonmrak',
        'info_dict':
        {
            'id': '2o0eonmrak',
            'title': 'Vídeos Institucionais FCT-FCCN',
            'description': str,
        },
        'playlist_mincount': 26,
    }, {
        'note': 'test for private Educast Channel',
        'url': 'https://educast.fccn.pt/vod/channels/2fudccnyj7',
        'info_dict': {
            'id': '2fudccnyj7',
            'title': 'Cálculo Diferencial e Integral III - Aulas de Recuperação',
            'description': str,
        },
        'playlist_mincount': 26,
        'skip': 'This channel is private and requires authentication to access',
    }]

    def _extract_video_links_from_html(self, webpage, ie_key):
        videos_by_id = {}
        pattern = r'href="https://educast\.fccn\.pt/vod/clips/(?P<id>[a-zA-Z0-9]+)/(?P<option>[^?"/]+)'
        for m in re.finditer(pattern, webpage or '', re.IGNORECASE):
            video_id = m.group('id')
            option = m.group('option')
            if video_id not in videos_by_id:
                videos_by_id[video_id] = []
            videos_by_id[video_id].append(option)

        videos = []
        for video_id, candidates in videos_by_id.items():
            # prefer 'streaming.html'
            candidates.sort(key=lambda x: x[0] == 'streaming.html')
            chosen_url = f'{EducastIE._API_BASE}/vod/clips/{video_id}/{candidates[0]}'
            videos.append({
                '_type': 'url',
                'url': chosen_url,
                'ie_key': ie_key,
                'id': video_id,
            })
        return videos

    def _extract_videos(self, url, channel_id, webpage=None):
        def get_page(page):
            url_parts = list(parse.urlparse(url))
            query = parse.parse_qs(url_parts[4])
            query['page'] = [str(page)]
            url_parts[4] = parse.urlencode(query, doseq=True)
            page_url = parse.urlunparse(url_parts)

            return self._download_webpage(page_url, channel_id, note=f'Downloading page {page}', fatal=False)

        def parse_func(page_result):
            return self._extract_video_links_from_html(page_result, EducastIE.ie_key())

        try:
            videos = EducastIE._paginate_and_collect(get_page, parse_func)
            if videos:
                return videos
        except Exception:
            pass
        # Fallback: parse HTML for video links
        return self._extract_video_links_from_html(webpage, EducastIE.ie_key())

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        webpage = self._download_webpage(url, channel_id)
        description = (
            self._og_search_description(webpage, default=None)
            or self._html_search_meta('description', webpage, default=None)
            or self._html_search_regex(
                r'<div[^>]+class="[^\"]*channel-description[^\"]*">([^<]+)',
                webpage, 'description', default=None)
        )
        return {
            '_type': 'playlist',
            'id': channel_id,
            'title': self._og_search_title(webpage, default='Unknown Channel'),
            'description': description,
            'entries': self._extract_videos(url, channel_id, webpage),
        }


class EducastResultsIE(EducastBaseIE):
    IE_NAME = 'educast:results'
    _VALID_URL = r'https?://(?:www\.)?educast\.fccn\.pt/results\?(?P<params>(search|organization|category|channel)=[^#]+)'
    _TESTS = [{
        'url': 'https://educast.fccn.pt/results?search=Sat%C3%A9lite',
        'info_dict': {
            'id': 'search=Sat%C3%A9lite',
            'title': 'Results for search=Satélite',
        },
        'playlist_mincount': 1,
        'params': {'max_downloads': 3},
    }, {
        'url': 'https://educast.fccn.pt/results?organization=fccn.pt',
        'info_dict': {
            'id': 'organization=fccn.pt',
            'title': 'Results for organization=fccn.pt',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://educast.fccn.pt/results?category=Technology%20&%20Applied%20sciences',
        'info_dict': {
            'id': 'category=Technology%20&%20Applied%20sciences',
            'title': 'Results for category=Technology%20&%20Applied%20sciences',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://educast.fccn.pt/results?channel=16mfovn0pt',
        'info_dict': {
            'id': 'channel=16mfovn0pt',
            'title': 'Results for channel=16mfovn0pt',
        },
        'playlist_mincount': 1,
    }]

    def _extract_video_links_from_html(self, webpage, ie_key):
        videos = []
        for m in re.finditer(r'/vod/clips/([a-zA-Z0-9]+)/streaming.html', webpage or '', re.IGNORECASE):
            video_id = m.group(1)
            url = f'{EducastIE._API_BASE}/vod/clips/{video_id}/streaming.html'
            if not any(v['id'] == video_id for v in videos):
                videos.append({
                    '_type': 'url',
                    'url': url,
                    'ie_key': ie_key,
                    'id': video_id,
                })
        return videos

    def _extract_videos(self, params, webpage=None):
        def get_page(page):
            base_url = f'{EducastIE._API_BASE}/results?{params}'
            url_parts = list(parse.urlparse(base_url))
            query = parse.parse_qs(url_parts[4])
            query['page'] = [str(page)]
            url_parts[4] = parse.urlencode(query, doseq=True)
            page_url = parse.urlunparse(url_parts)
            return self._download_webpage(page_url, params, note=f'Downloading results page {page}', fatal=False)

        def parse_func(webpage):
            return self._extract_video_links_from_html(webpage, EducastIE.ie_key())
        return EducastIE._paginate_and_collect(get_page, parse_func)

    def _real_extract(self, url):
        params = self._match_valid_url(url).group('params')
        params_decoded = parse.unquote(params)
        webpage = self._download_webpage(url, params)
        return {
            '_type': 'playlist',
            'id': params,
            'title': f'Results for {params_decoded}',
            'entries': self._extract_videos(params, webpage),
        }
