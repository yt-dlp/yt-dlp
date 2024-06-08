import functools
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    int_or_none,
    month_by_name,
    parse_duration,
    try_call,
)


class WyborczaVideoIE(InfoExtractor):
    # this id is not an article id, it has to be extracted from the article
    _VALID_URL = r'(?:wyborcza:video:|https?://wyborcza\.pl/(?:api-)?video/)(?P<id>\d+)'
    IE_NAME = 'wyborcza:video'
    _TESTS = [{
        'url': 'wyborcza:video:26207634',
        'info_dict': {
            'id': '26207634',
            'ext': 'mp4',
            'title': '- Polska w 2020 r. jest innym państwem niż w 2015 r. Nie zmieniła się konstytucja, ale jest to już inny ustrój - mówi Adam Bodnar',
            'description': ' ',
            'uploader': 'Dorota Roman',
            'duration': 2474,
            'thumbnail': r're:https://.+\.jpg',
        },
    }, {
        'url': 'https://wyborcza.pl/video/26207634',
        'only_matching': True,
    }, {
        'url': 'https://wyborcza.pl/api-video/26207634',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        meta = self._download_json(f'https://wyborcza.pl/api-video/{video_id}', video_id)

        formats = []
        base_url = meta['redirector'].replace('http://', 'https://') + meta['basePath']
        for quality in ('standard', 'high'):
            if not meta['files'].get(quality):
                continue
            formats.append({
                'url': base_url + meta['files'][quality],
                'height': int_or_none(
                    self._search_regex(
                        r'p(\d+)[a-z]+\.mp4$', meta['files'][quality],
                        'mp4 video height', default=None)),
                'format_id': quality,
            })
        if meta['files'].get('dash'):
            formats.extend(self._extract_mpd_formats(base_url + meta['files']['dash'], video_id))

        return {
            'id': video_id,
            'formats': formats,
            'title': meta.get('title'),
            'description': meta.get('lead'),
            'uploader': meta.get('signature'),
            'thumbnail': meta.get('imageUrl'),
            'duration': meta.get('duration'),
        }


class WyborczaPodcastIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?(?:
            wyborcza\.pl/podcast(?:/0,172673\.html)?|
            wysokieobcasy\.pl/wysokie-obcasy/0,176631\.html
        )(?:\?(?:[^&#]+?&)*podcast=(?P<id>\d+))?
    '''
    _TESTS = [{
        'url': 'https://wyborcza.pl/podcast/0,172673.html?podcast=100720#S.main_topic-K.C-B.6-L.1.podcast',
        'info_dict': {
            'id': '100720',
            'ext': 'mp3',
            'title': 'Cyfrodziewczyny. Kim były pionierki polskiej informatyki ',
            'uploader': 'Michał Nogaś ',
            'upload_date': '20210117',
            'description': 'md5:49f0a06ffc4c1931210d3ab1416a651d',
            'duration': 3684.0,
            'thumbnail': r're:https://.+\.jpg',
        },
    }, {
        'url': 'https://www.wysokieobcasy.pl/wysokie-obcasy/0,176631.html?podcast=100673',
        'info_dict': {
            'id': '100673',
            'ext': 'mp3',
            'title': 'Czym jest ubóstwo menstruacyjne i dlaczego dotyczy każdej i każdego z nas?',
            'uploader': 'Agnieszka Urazińska ',
            'upload_date': '20210115',
            'description': 'md5:c161dc035f8dbb60077011fc41274899',
            'duration': 1803.0,
            'thumbnail': r're:https://.+\.jpg',
        },
    }, {
        'url': 'https://wyborcza.pl/podcast',
        'info_dict': {
            'id': '334',
            'title': 'Gościnnie: Wyborcza, 8:10',
            'series': 'Gościnnie: Wyborcza, 8:10',
        },
        'playlist_mincount': 370,
    }, {
        'url': 'https://www.wysokieobcasy.pl/wysokie-obcasy/0,176631.html',
        'info_dict': {
            'id': '395',
            'title': 'Gościnnie: Wysokie Obcasy',
            'series': 'Gościnnie: Wysokie Obcasy',
        },
        'playlist_mincount': 12,
    }]

    def _real_extract(self, url):
        podcast_id = self._match_id(url)

        if not podcast_id:  # playlist
            podcast_id = '395' if 'wysokieobcasy.pl/' in url else '334'
            return self.url_result(TokFMAuditionIE._create_url(podcast_id), TokFMAuditionIE, podcast_id)

        meta = self._download_json('https://wyborcza.pl/api/podcast', podcast_id,
                                   query={'guid': podcast_id, 'type': 'wo' if 'wysokieobcasy.pl/' in url else None})

        day, month, year = self._search_regex(r'^(\d\d?) (\w+) (\d{4})$', meta.get('publishedDate'),
                                              'upload date', group=(1, 2, 3), default=(None, None, None))
        return {
            'id': podcast_id,
            'url': meta['url'],
            'title': meta.get('title'),
            'description': meta.get('description'),
            'thumbnail': meta.get('imageUrl'),
            'duration': parse_duration(meta.get('duration')),
            'uploader': meta.get('author'),
            'upload_date': try_call(lambda: f'{year}{month_by_name(month, lang="pl"):0>2}{day:0>2}'),
        }


class TokFMPodcastIE(InfoExtractor):
    _VALID_URL = r'(?:https?://audycje\.tokfm\.pl/podcast/|tokfm:podcast:)(?P<id>\d+),?'
    IE_NAME = 'tokfm:podcast'
    _TESTS = [{
        'url': 'https://audycje.tokfm.pl/podcast/91275,-Systemowy-rasizm-Czy-zamieszki-w-USA-po-morderstwie-w-Minneapolis-doprowadza-do-zmian-w-sluzbach-panstwowych',
        'info_dict': {
            'id': '91275',
            'ext': 'aac',
            'title': 'md5:a9b15488009065556900169fb8061cce',
            'episode': 'md5:a9b15488009065556900169fb8061cce',
            'series': 'Analizy',
        },
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)

        # in case it breaks see this but it returns a lot of useless data
        # https://api.podcast.radioagora.pl/api4/getPodcasts?podcast_id=100091&with_guests=true&with_leaders_for_mobile=true
        metadata = self._download_json(
            f'https://audycje.tokfm.pl/getp/3{media_id}', media_id, 'Downloading podcast metadata')
        if not metadata:
            raise ExtractorError('No such podcast', expected=True)
        metadata = metadata[0]

        formats = []
        for ext in ('aac', 'mp3'):
            url_data = self._download_json(
                f'https://api.podcast.radioagora.pl/api4/getSongUrl?podcast_id={media_id}&device_id={uuid.uuid4()}&ppre=false&audio={ext}',
                media_id, f'Downloading podcast {ext} URL')
            # prevents inserting the mp3 (default) multiple times
            if 'link_ssl' in url_data and f'.{ext}' in url_data['link_ssl']:
                formats.append({
                    'url': url_data['link_ssl'],
                    'ext': ext,
                    'vcodec': 'none',
                    'acodec': ext,
                })

        return {
            'id': media_id,
            'formats': formats,
            'title': metadata.get('podcast_name'),
            'series': metadata.get('series_name'),
            'episode': metadata.get('podcast_name'),
        }


class TokFMAuditionIE(InfoExtractor):
    _VALID_URL = r'(?:https?://audycje\.tokfm\.pl/audycja/|tokfm:audition:)(?P<id>\d+),?'
    IE_NAME = 'tokfm:audition'
    _TESTS = [{
        'url': 'https://audycje.tokfm.pl/audycja/218,Analizy',
        'info_dict': {
            'id': '218',
            'title': 'Analizy',
            'series': 'Analizy',
        },
        'playlist_count': 1635,
    }]

    _PAGE_SIZE = 30
    _HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 9; Redmi 3S Build/PQ3A.190801.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.101 Mobile Safari/537.36',
    }

    @staticmethod
    def _create_url(video_id):
        return f'https://audycje.tokfm.pl/audycja/{video_id}'

    def _real_extract(self, url):
        audition_id = self._match_id(url)

        data = self._download_json(
            f'https://api.podcast.radioagora.pl/api4/getSeries?series_id={audition_id}',
            audition_id, 'Downloading audition metadata', headers=self._HEADERS)
        if not data:
            raise ExtractorError('No such audition', expected=True)
        data = data[0]

        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, audition_id, data), self._PAGE_SIZE)

        return {
            '_type': 'playlist',
            'id': audition_id,
            'title': data.get('series_name'),
            'series': data.get('series_name'),
            'entries': entries,
        }

    def _fetch_page(self, audition_id, data, page):
        for retry in self.RetryManager():
            podcast_page = self._download_json(
                f'https://api.podcast.radioagora.pl/api4/getPodcasts?series_id={audition_id}&limit=30&offset={page}&with_guests=true&with_leaders_for_mobile=true',
                audition_id, f'Downloading podcast list page {page + 1}', headers=self._HEADERS)
            if not podcast_page:
                retry.error = ExtractorError('Agora returned empty page', expected=True)

        for podcast in podcast_page:
            yield {
                '_type': 'url_transparent',
                'url': podcast['podcast_sharing_url'],
                'ie_key': TokFMPodcastIE.ie_key(),
                'title': podcast.get('podcast_name'),
                'episode': podcast.get('podcast_name'),
                'description': podcast.get('podcast_description'),
                'timestamp': int_or_none(podcast.get('podcast_timestamp')),
                'series': data.get('series_name'),
            }
