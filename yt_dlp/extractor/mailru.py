import itertools
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    int_or_none,
    parse_duration,
    remove_end,
    try_get,
    urljoin,
)


class MailRuIE(InfoExtractor):
    IE_NAME = 'mailru'
    IE_DESC = 'Видео@Mail.Ru'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:(?:www|m|videoapi)\.)?my\.mail\.ru/+
                        (?:
                            video/.*\#video=/?(?P<idv1>(?:[^/]+/){3}\d+)|
                            (?:videos/embed/)?(?:(?P<idv2prefix>(?:[^/]+/+){2})(?:video/(?:embed/)?)?(?P<idv2suffix>[^/]+/\d+))(?:\.html)?|
                            (?:video/embed|\+/video/meta)/(?P<metaid>\d+)
                        )
                    '''
    _TESTS = [
        {
            'url': 'http://my.mail.ru/video/top#video=/mail/sonypicturesrus/75/76',
            'md5': 'dea205f03120046894db4ebb6159879a',
            'info_dict': {
                'id': '46301138_76',
                'ext': 'mp4',
                'title': 'Новый Человек-Паук. Высокое напряжение. Восстание Электро',
                'timestamp': 1393235077,
                'upload_date': '20140224',
                'uploader': 'sonypicturesrus',
                'uploader_id': 'sonypicturesrus@mail.ru',
                'duration': 184,
            },
            'skip': 'Not accessible from Travis CI server',
        },
        {
            'url': 'http://my.mail.ru/corp/hitech/video/news_hi-tech_mail_ru/1263.html',
            'md5': '00a91a58c3402204dcced523777b475f',
            'info_dict': {
                'id': '46843144_1263',
                'ext': 'mp4',
                'title': 'Samsung Galaxy S5 Hammer Smash Fail Battery Explosion',
                'timestamp': 1397039888,
                'upload_date': '20140409',
                'uploader': 'hitech',
                'uploader_id': 'hitech@corp.mail.ru',
                'duration': 245,
            },
            'skip': 'Not accessible from Travis CI server',
        },
        {
            # only available via metaUrl API
            'url': 'http://my.mail.ru/mail/720pizle/video/_myvideo/502.html',
            'md5': '3b26d2491c6949d031a32b96bd97c096',
            'info_dict': {
                'id': '56664382_502',
                'ext': 'mp4',
                'title': ':8336',
                'timestamp': 1449094163,
                'upload_date': '20151202',
                'uploader': '720pizle@mail.ru',
                'uploader_id': '720pizle@mail.ru',
                'duration': 6001,
            },
            'skip': 'Not accessible from Travis CI server',
        },
        {
            'url': 'http://m.my.mail.ru/mail/3sktvtr/video/_myvideo/138.html',
            'only_matching': True,
        },
        {
            'url': 'https://my.mail.ru/video/embed/7949340477499637815',
            'only_matching': True,
        },
        {
            'url': 'http://my.mail.ru/+/video/meta/7949340477499637815',
            'only_matching': True,
        },
        {
            'url': 'https://my.mail.ru//list/sinyutin10/video/_myvideo/4.html',
            'only_matching': True,
        },
        {
            'url': 'https://my.mail.ru//list//sinyutin10/video/_myvideo/4.html',
            'only_matching': True,
        },
        {
            'url': 'https://my.mail.ru/mail/cloud-strife/video/embed/Games/2009',
            'only_matching': True,
        },
        {
            'url': 'https://videoapi.my.mail.ru/videos/embed/mail/cloud-strife/Games/2009.html',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        meta_id = mobj.group('metaid')

        video_id = None
        if meta_id:
            meta_url = 'https://my.mail.ru/+/video/meta/%s' % meta_id
        else:
            video_id = mobj.group('idv1')
            if not video_id:
                video_id = mobj.group('idv2prefix') + mobj.group('idv2suffix')
            webpage = self._download_webpage(url, video_id)
            page_config = self._parse_json(self._search_regex([
                r'(?s)<script[^>]+class="sp-video__page-config"[^>]*>(.+?)</script>',
                r'(?s)"video":\s*({.+?}),'],
                webpage, 'page config', default='{}'), video_id, fatal=False)
            if page_config:
                meta_url = page_config.get('metaUrl') or page_config.get('video', {}).get('metaUrl') or page_config.get('metadataUrl')
            else:
                meta_url = None

        video_data = None

        # fix meta_url if missing the host address
        if re.match(r'^\/\+\/', meta_url):
            meta_url = urljoin('https://my.mail.ru', meta_url)

        if meta_url:
            video_data = self._download_json(
                meta_url, video_id or meta_id, 'Downloading video meta JSON',
                fatal=not video_id)

        # Fallback old approach
        if not video_data:
            video_data = self._download_json(
                'http://api.video.mail.ru/videos/%s.json?new=1' % video_id,
                video_id, 'Downloading video JSON')

        video_key = self._get_cookies('https://my.mail.ru').get('video_key')

        formats = []
        for f in video_data['videos']:
            video_url = f.get('url')
            if not video_url:
                continue
            if video_key:
                self._set_cookie(urllib.parse.urlparse(video_url).hostname, 'video_key', video_key.value)
            format_id = f.get('key')
            height = int_or_none(self._search_regex(
                r'^(\d+)[pP]$', format_id, 'height', default=None)) if format_id else None
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'height': height,
            })

        meta_data = video_data['meta']
        title = remove_end(meta_data['title'], '.mp4')

        author = video_data.get('author')
        uploader = author.get('name')
        uploader_id = author.get('id') or author.get('email')
        view_count = int_or_none(video_data.get('viewsCount') or video_data.get('views_count'))

        acc_id = meta_data.get('accId')
        item_id = meta_data.get('itemId')
        content_id = '%s_%s' % (acc_id, item_id) if acc_id and item_id else video_id

        thumbnail = meta_data.get('poster')
        duration = int_or_none(meta_data.get('duration'))
        timestamp = int_or_none(meta_data.get('timestamp'))

        return {
            'id': content_id,
            'title': title,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
        }


class MailRuMusicSearchBaseIE(InfoExtractor):
    def _search(self, query, url, audio_id, limit=100, offset=0):
        search = self._download_json(
            'https://my.mail.ru/cgi-bin/my/ajax', audio_id,
            'Downloading songs JSON page %d' % (offset // limit + 1),
            headers={
                'Referer': url,
                'X-Requested-With': 'XMLHttpRequest',
            }, query={
                'xemail': '',
                'ajax_call': '1',
                'func_name': 'music.search',
                'mna': '',
                'mnb': '',
                'arg_query': query,
                'arg_extended': '1',
                'arg_search_params': json.dumps({
                    'music': {
                        'limit': limit,
                        'offset': offset,
                    },
                }),
                'arg_limit': limit,
                'arg_offset': offset,
            })
        return next(e for e in search if isinstance(e, dict))

    @staticmethod
    def _extract_track(t, fatal=True):
        audio_url = t['URL'] if fatal else t.get('URL')
        if not audio_url:
            return

        audio_id = t['File'] if fatal else t.get('File')
        if not audio_id:
            return

        thumbnail = t.get('AlbumCoverURL') or t.get('FiledAlbumCover')
        uploader = t.get('OwnerName') or t.get('OwnerName_Text_HTML')
        uploader_id = t.get('UploaderID')
        duration = int_or_none(t.get('DurationInSeconds')) or parse_duration(
            t.get('Duration') or t.get('DurationStr'))
        view_count = int_or_none(t.get('PlayCount') or t.get('PlayCount_hr'))

        track = t.get('Name') or t.get('Name_Text_HTML')
        artist = t.get('Author') or t.get('Author_Text_HTML')

        if track:
            title = '%s - %s' % (artist, track) if artist else track
        else:
            title = audio_id

        return {
            'extractor_key': MailRuMusicIE.ie_key(),
            'id': audio_id,
            'title': title,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'duration': duration,
            'view_count': view_count,
            'vcodec': 'none',
            'abr': int_or_none(t.get('BitRate')),
            'track': track,
            'artist': artist,
            'album': t.get('Album'),
            'url': audio_url,
        }


class MailRuMusicIE(MailRuMusicSearchBaseIE):
    IE_NAME = 'mailru:music'
    IE_DESC = 'Музыка@Mail.Ru'
    _VALID_URL = r'https?://my\.mail\.ru/+music/+songs/+[^/?#&]+-(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'https://my.mail.ru/music/songs/%D0%BC8%D0%BB8%D1%82%D1%85-l-a-h-luciferian-aesthetics-of-herrschaft-single-2017-4e31f7125d0dfaef505d947642366893',
        'md5': '0f8c22ef8c5d665b13ac709e63025610',
        'info_dict': {
            'id': '4e31f7125d0dfaef505d947642366893',
            'ext': 'mp3',
            'title': 'L.A.H. (Luciferian Aesthetics of Herrschaft) single, 2017 - М8Л8ТХ',
            'uploader': 'Игорь Мудрый',
            'uploader_id': '1459196328',
            'duration': 280,
            'view_count': int,
            'vcodec': 'none',
            'abr': 320,
            'track': 'L.A.H. (Luciferian Aesthetics of Herrschaft) single, 2017',
            'artist': 'М8Л8ТХ',
        },
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        webpage = self._download_webpage(url, audio_id)

        title = self._og_search_title(webpage)
        music_data = self._search(title, url, audio_id)['MusicData']
        t = next(t for t in music_data if t.get('File') == audio_id)

        info = self._extract_track(t)
        info['title'] = title
        return info


class MailRuMusicSearchIE(MailRuMusicSearchBaseIE):
    IE_NAME = 'mailru:music:search'
    IE_DESC = 'Музыка@Mail.Ru'
    _VALID_URL = r'https?://my\.mail\.ru/+music/+search/+(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://my.mail.ru/music/search/black%20shadow',
        'info_dict': {
            'id': 'black shadow',
        },
        'playlist_mincount': 532,
    }]

    def _real_extract(self, url):
        query = compat_urllib_parse_unquote(self._match_id(url))

        entries = []

        LIMIT = 100
        offset = 0

        for _ in itertools.count(1):
            search = self._search(query, url, query, LIMIT, offset)

            music_data = search.get('MusicData')
            if not music_data or not isinstance(music_data, list):
                break

            for t in music_data:
                track = self._extract_track(t, fatal=False)
                if track:
                    entries.append(track)

            total = try_get(
                search, lambda x: x['Results']['music']['Total'], int)

            if total is not None:
                if offset > total:
                    break

            offset += LIMIT

        return self.playlist_result(entries, query)
