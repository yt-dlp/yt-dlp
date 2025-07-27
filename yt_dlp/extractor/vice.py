import functools
import hashlib
import json
import random
import time

from .adobepass import AdobePassIE
from .common import InfoExtractor
from .youtube import YoutubeIE
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    int_or_none,
    parse_age_limit,
    str_or_none,
    try_get,
)


class ViceBaseIE(InfoExtractor):
    def _call_api(self, resource, resource_key, resource_id, locale, fields, args=''):
        return self._download_json(
            'https://video.vice.com/api/v1/graphql', resource_id, query={
                'query': '''{
  %s(locale: "%s", %s: "%s"%s) {
    %s
  }
}''' % (resource, locale, resource_key, resource_id, args, fields),  # noqa: UP031
            })['data'][resource]


class ViceIE(ViceBaseIE, AdobePassIE):
    _WORKING = False
    IE_NAME = 'vice'
    _VALID_URL = r'https?://(?:(?:video|vms)\.vice|(?:www\.)?vice(?:land|tv))\.com/(?P<locale>[^/]+)/(?:video/[^/]+|embed)/(?P<id>[\da-f]{24})'
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=["\'](?P<url>(?:https?:)?//video\.vice\.com/[^/]+/embed/[\da-f]{24})']
    _TESTS = [{
        'url': 'https://video.vice.com/en_us/video/pet-cremator/58c69e38a55424f1227dc3f7',
        'info_dict': {
            'id': '58c69e38a55424f1227dc3f7',
            'ext': 'mp4',
            'title': '10 Questions You Always Wanted To Ask: Pet Cremator',
            'description': 'md5:fe856caacf61fe0e74fab15ce2b07ca5',
            'uploader': 'vice',
            'uploader_id': '57a204088cb727dec794c67b',
            'timestamp': 1489664942,
            'upload_date': '20170316',
            'age_limit': 14,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # geo restricted to US
        'url': 'https://video.vice.com/en_us/video/the-signal-from-tolva/5816510690b70e6c5fd39a56',
        'info_dict': {
            'id': '5816510690b70e6c5fd39a56',
            'ext': 'mp4',
            'uploader': 'vice',
            'title': 'The Signal From Tölva',
            'description': 'md5:3927e3c79f9e8094606a2b3c5b5e55d5',
            'uploader_id': '57a204088cb727dec794c67b',
            'timestamp': 1477941983,
            'upload_date': '20161031',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://video.vice.com/alps/video/ulfs-wien-beruchtigste-grafitti-crew-part-1/581b12b60a0e1f4c0fb6ea2f',
        'info_dict': {
            'id': '581b12b60a0e1f4c0fb6ea2f',
            'ext': 'mp4',
            'title': 'ULFs - Wien berüchtigste Grafitti Crew - Part 1',
            'description': 'Zwischen Hinterzimmer-Tattoos und U-Bahnschächten erzählen uns die Ulfs, wie es ist, "süchtig nach Sachbeschädigung" zu sein.',
            'uploader': 'vice',
            'uploader_id': '57a204088cb727dec794c67b',
            'timestamp': 1485368119,
            'upload_date': '20170125',
            'age_limit': 14,
        },
        'params': {
            # AES-encrypted m3u8
            'skip_download': True,
        },
    }, {
        'url': 'https://video.vice.com/en_us/video/pizza-show-trailer/56d8c9a54d286ed92f7f30e4',
        'only_matching': True,
    }, {
        'url': 'https://video.vice.com/en_us/embed/57f41d3556a0a80f54726060',
        'only_matching': True,
    }, {
        'url': 'https://vms.vice.com/en_us/video/preplay/58c69e38a55424f1227dc3f7',
        'only_matching': True,
    }, {
        'url': 'https://www.viceland.com/en_us/video/thursday-march-1-2018/5a8f2d7ff1cdb332dd446ec1',
        'only_matching': True,
    }]
    _SOFTWARE_STATEMENT = 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIwMTVjODBlZC04ZDcxLTQ4ZGEtOTZkZi00NzU5NjIwNzJlYTQiLCJuYmYiOjE2NjgwMTM0ODQsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNjY4MDEzNDg0fQ.CjhUnTrlh-bmYnEFHyC2Y4it5Y_Zfza1x66O4-ki5gBR7JT6aUunYI_YflXomQPACriMpObkITFz4grVaDwdd8Xp9hrQ2R0SwRBdaklkdy1_j68RqSP5PnexJIa0q_ThtOwfRBd5uGcb33nMJ9Qs92W4kVXuca0Ta-i7SJyWgXUaPDlRDdgyCL3hKj5wuM7qUIwrd9A5CMm-j3dMIBCDgw7X6TwRK65eUQe6gTWqcvL2yONHHTpmIfeOTUxGwwKFr29COOTBowm0VJ6HE08xjXCShP08Neusu-JsgkjzhkEbiDE2531EKgfAki_7WCd2JUZVsAsCusv4a1maokk6NA'

    def _real_extract(self, url):
        locale, video_id = self._match_valid_url(url).groups()

        video = self._call_api('videos', 'id', video_id, locale, '''body
    locked
    rating
    thumbnail_url
    title''')[0]
        title = video['title'].strip()
        rating = video.get('rating')

        query = {}
        if video.get('locked'):
            resource = self._get_mvpd_resource(
                'VICELAND', title, video_id, rating)
            query['tvetoken'] = self._extract_mvpd_auth(
                url, video_id, 'VICELAND', resource, self._SOFTWARE_STATEMENT)

        # signature generation algorithm is reverse engineered from signatureGenerator in
        # webpack:///../shared/~/vice-player/dist/js/vice-player.js in
        # https://www.viceland.com/assets/common/js/web.vendor.bundle.js
        # new JS is located here https://vice-web-statics-cdn.vice.com/vice-player/player-embed.js
        exp = int(time.time()) + 1440

        query.update({
            'exp': exp,
            'sign': hashlib.sha512(f'{video_id}:GET:{exp}'.encode()).hexdigest(),
            'skipadstitching': 1,
            'platform': 'desktop',
            'rn': random.randint(10000, 100000),
        })

        try:
            preplay = self._download_json(
                f'https://vms.vice.com/{locale}/video/preplay/{video_id}',
                video_id, query=query)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in (400, 401):
                error = json.loads(e.cause.response.read().decode())
                error_message = error.get('error_description') or error['details']
                raise ExtractorError(f'{self.IE_NAME} said: {error_message}', expected=True)
            raise

        video_data = preplay['video']
        formats = self._extract_m3u8_formats(
            preplay['playURL'], video_id, 'mp4', 'm3u8_native')
        episode = video_data.get('episode') or {}
        channel = video_data.get('channel') or {}
        season = video_data.get('season') or {}

        subtitles = {}
        for subtitle in preplay.get('subtitleURLs', []):
            cc_url = subtitle.get('url')
            if not cc_url:
                continue
            language_code = try_get(subtitle, lambda x: x['languages'][0]['language_code'], str) or 'en'
            subtitles.setdefault(language_code, []).append({
                'url': cc_url,
            })

        return {
            'formats': formats,
            'id': video_id,
            'title': title,
            'description': clean_html(video.get('body')),
            'thumbnail': video.get('thumbnail_url'),
            'duration': int_or_none(video_data.get('video_duration')),
            'timestamp': int_or_none(video_data.get('created_at'), 1000),
            'age_limit': parse_age_limit(video_data.get('video_rating') or rating),
            'series': try_get(video_data, lambda x: x['show']['base']['display_title'], str),
            'episode_number': int_or_none(episode.get('episode_number')),
            'episode_id': str_or_none(episode.get('id') or video_data.get('episode_id')),
            'season_number': int_or_none(season.get('season_number')),
            'season_id': str_or_none(season.get('id') or video_data.get('season_id')),
            'uploader': channel.get('name'),
            'uploader_id': str_or_none(channel.get('id')),
            'subtitles': subtitles,
        }


class ViceShowIE(ViceBaseIE):
    _WORKING = False
    IE_NAME = 'vice:show'
    _VALID_URL = r'https?://(?:video\.vice|(?:www\.)?vice(?:land|tv))\.com/(?P<locale>[^/]+)/show/(?P<id>[^/?#&]+)'
    _PAGE_SIZE = 25
    _TESTS = [{
        'url': 'https://video.vice.com/en_us/show/fck-thats-delicious',
        'info_dict': {
            'id': '57a2040c8cb727dec794c901',
            'title': 'F*ck, That’s Delicious',
            'description': 'The life and eating habits of rap’s greatest bon vivant, Action Bronson.',
        },
        'playlist_mincount': 64,
    }, {
        'url': 'https://www.vicetv.com/en_us/show/fck-thats-delicious',
        'only_matching': True,
    }]

    def _fetch_page(self, locale, show_id, page):
        videos = self._call_api('videos', 'show_id', show_id, locale, '''body
    id
    url''', f', page: {page + 1}, per_page: {self._PAGE_SIZE}')
        for video in videos:
            yield self.url_result(
                video['url'], ViceIE.ie_key(), video.get('id'))

    def _real_extract(self, url):
        locale, display_id = self._match_valid_url(url).groups()
        show = self._call_api('shows', 'slug', display_id, locale, '''dek
    id
    title''')[0]
        show_id = show['id']

        entries = OnDemandPagedList(
            functools.partial(self._fetch_page, locale, show_id),
            self._PAGE_SIZE)

        return self.playlist_result(
            entries, show_id, show.get('title'), show.get('dek'))


class ViceArticleIE(ViceBaseIE):
    _WORKING = False
    IE_NAME = 'vice:article'
    _VALID_URL = r'https?://(?:www\.)?vice\.com/(?P<locale>[^/]+)/article/(?:[0-9a-z]{6}/)?(?P<id>[^?#]+)'

    _TESTS = [{
        'url': 'https://www.vice.com/en_us/article/on-set-with-the-woman-making-mormon-porn-in-utah',
        'info_dict': {
            'id': '58dc0a3dee202d2a0ccfcbd8',
            'ext': 'mp4',
            'title': 'Mormon War on Porn',
            'description': 'md5:1c5d91fe25fa8aa304f9def118b92dbf',
            'uploader': 'vice',
            'uploader_id': '57a204088cb727dec794c67b',
            'timestamp': 1491883129,
            'upload_date': '20170411',
            'age_limit': 17,
        },
        'params': {
            # AES-encrypted m3u8
            'skip_download': True,
        },
        'add_ie': [ViceIE.ie_key()],
    }, {
        'url': 'https://www.vice.com/en_us/article/how-to-hack-a-car',
        'md5': '13010ee0bc694ea87ec40724397c2349',
        'info_dict': {
            'id': '3jstaBeXgAs',
            'ext': 'mp4',
            'title': 'How to Hack a Car: Phreaked Out (Episode 2)',
            'description': 'md5:ee95453f7ff495db8efe14ae8bf56f30',
            'uploader': 'Motherboard',
            'uploader_id': 'MotherboardTV',
            'upload_date': '20140529',
        },
        'add_ie': [YoutubeIE.ie_key()],
    }, {
        'url': 'https://www.vice.com/en_us/article/znm9dx/karley-sciortino-slutever-reloaded',
        'md5': 'a7ecf64ee4fa19b916c16f4b56184ae2',
        'info_dict': {
            'id': '57f41d3556a0a80f54726060',
            'ext': 'mp4',
            'title': "Making The World's First Male Sex Doll",
            'description': 'md5:19b00b215b99961cf869c40fbe9df755',
            'uploader': 'vice',
            'uploader_id': '57a204088cb727dec794c67b',
            'timestamp': 1476919911,
            'upload_date': '20161019',
            'age_limit': 17,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [ViceIE.ie_key()],
    }, {
        'url': 'https://www.vice.com/en_us/article/cowboy-capitalists-part-1',
        'only_matching': True,
    }, {
        'url': 'https://www.vice.com/ru/article/big-night-out-ibiza-clive-martin-229',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        locale, display_id = self._match_valid_url(url).groups()

        article = self._call_api('articles', 'slug', display_id, locale, '''body
    embed_code''')[0]
        body = article['body']

        def _url_res(video_url, ie_key):
            return {
                '_type': 'url_transparent',
                'url': video_url,
                'display_id': display_id,
                'ie_key': ie_key,
            }

        vice_url = ViceIE._extract_url(body)
        if vice_url:
            return _url_res(vice_url, ViceIE.ie_key())

        youtube_url = YoutubeIE._extract_url(body)
        if youtube_url:
            return _url_res(youtube_url, YoutubeIE.ie_key())

        video_url = self._html_search_regex(
            r'data-video-url="([^"]+)"',
            article['embed_code'], 'video URL')

        return _url_res(video_url, ViceIE.ie_key())
