import base64
import functools
import json
import re
import urllib.parse

from .common import InfoExtractor, SearchInfoExtractor
from ..aes import aes_cbc_decrypt_bytes, aes_cbc_encrypt_bytes, unpad_pkcs7
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    get_element_by_attribute,
    get_element_by_class,
    get_elements_by_attribute,
    int_or_none,
    join_nonempty,
    merge_dicts,
    orderedSet,
    parse_count,
    parse_duration,
    strip_or_none,
    unified_strdate,
    url_or_none,
    urlencode_postdata,
    urljoin,
    variadic,
)
from ..utils.traversal import traverse_obj


class BoomPlayBaseIE(InfoExtractor):
    # Calculated from const values, see lhx.AESUtils.encrypt, see public.js
    # Note that the real key/iv differs from `lhx.AESUtils.key`/`lhx.AESUtils.iv`
    _KEY = b'boomplayVr3xopAM'
    _IV = b'boomplay8xIsKTn9'
    _BASE = 'https://www.boomplay.com'
    _MEDIA_TYPES = ('songs', 'video', 'episode', 'podcasts', 'playlists', 'artists', 'albums')

    @classmethod
    def _urljoin(cls, path):
        if not hasattr(path, 'startswith') or path.startswith('javascript:'):
            return None
        return url_or_none(urljoin(base=cls._BASE, path=path))

    def _get_playurl(self, item_id, item_type):
        resp = self._download_json(
            'https://www.boomplay.com/getResourceAddr', item_id,
            note='Downloading play URL', errnote='Failed to download play URL',
            data=urlencode_postdata({
                'param': base64.b64encode(aes_cbc_encrypt_bytes(json.dumps({
                    'itemID': item_id,
                    'itemType': item_type,
                }).encode(), self._KEY, self._IV)).decode(),
            }), headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            })
        if not (source := resp.get('source')) and resp.get('code'):
            raise ExtractorError(resp.get('desc') or 'Please solve the captcha')
        return unpad_pkcs7(
            aes_cbc_decrypt_bytes(base64.b64decode(source), self._KEY, self._IV)).decode()

    def _extract_formats(self, _id, item_type='MUSIC', **kwargs):
        if url := url_or_none(self._get_playurl(_id, item_type)):
            return [{
                'format_id': '0',
                'url': url,
                'http_headers': {
                    'Origin': 'https://www.boomplay.com',
                    'Referer': 'https://www.boomplay.com',
                    'X-Boomplay-Ref': 'Boomplay_WEBV1',
                },
                **kwargs,
            }]
        else:
            self.raise_no_formats('No formats found')

    def _extract_page_metadata(self, webpage, _id):
        metadata_div = get_element_by_attribute(
            'class', r'[^\'"]*(?<=[\'"\s])summary(?=[\'"\s])[^\'"]*', webpage,
            tag='div', escape_value=False) or ''
        metadata_entries = re.findall(r'(?s)<strong>(?P<entry>.*?)</strong>', metadata_div) or []
        description = get_element_by_attribute(
            'class', r'[^\'"]*(?<=[\'"\s])description_content(?=[\'"\s])[^\'"]*', webpage,
            tag='span', escape_value=False) or 'Listen and download music for free on Boomplay!'
        description = clean_html(description.strip())
        if description == 'Listen and download music for free on Boomplay!':
            description = None

        details_section = get_element_by_attribute(
            'class', r'[^\'"]*(?<=[\'"\s])songDetailInfo(?=[\'"\s])[^\'"]*', webpage,
            tag='section', escape_value=False) or ''
        metadata_entries.extend(re.findall(r'(?s)<li>(?P<entry>.*?)</li>', details_section) or [])
        page_metadata = {
            'id': _id,
            'title': self._html_search_regex(r'<h1>([^<]+)</h1>', metadata_div, 'title', default=None),
            'thumbnail': self._html_search_meta(['og:image', 'twitter:image'],
                                                webpage, 'thumbnail', default=''),
            'like_count': parse_count(get_element_by_class('btn_favorite', metadata_div)),
            'repost_count': parse_count(get_element_by_class('btn_share', metadata_div)),
            'comment_count': parse_count(get_element_by_class('btn_comment', metadata_div)),
            'duration': parse_duration(get_element_by_class('btn_duration', metadata_div)),
            'upload_date': unified_strdate(strip_or_none(get_element_by_class('btn_pubDate', metadata_div))),
            'description': description,
        }
        for metadata_entry in metadata_entries:
            if ':' not in metadata_entry:
                continue
            k, v = clean_html(metadata_entry).split(':', 2)
            v = v.strip()
            if 'artist' in k.lower():
                page_metadata['artists'] = [v]
            elif 'album' in k.lower():
                page_metadata['album'] = v
            elif 'genre' in k.lower():
                page_metadata['genres'] = [v]
            elif 'year of release' in k.lower():
                page_metadata['release_year'] = int_or_none(v)
        return page_metadata

    def _extract_suitable_links(self, webpage, media_types):
        if not media_types:
            media_types = self._MEDIA_TYPES
        media_types = list(variadic(media_types))

        for idx, v in enumerate(media_types):
            media_types[idx] = re.escape(v) if v in self._MEDIA_TYPES else ''
        media_types = join_nonempty(*media_types, delim='|')
        return orderedSet(traverse_obj(re.finditer(
            rf'''(?x)
            <a
                (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
                    (?<=\s)href\s*=\s*(?P<_q>['"])
                        (?:
                            (?!javascript:)(?P<link>/(?:{media_types})/\d+?)
                        )
                    (?P=_q)
                (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
            ''', webpage), (..., 'link', {self._urljoin}, {self.url_result})))

    def _extract_playlist_entries(self, webpage, media_types, warn=True):
        song_list = strip_or_none(
            get_element_by_attribute(
                'class', r'[^\'"]*(?<=[\'"\s])morePart_musics(?=[\'"\s])[^\'"]*', webpage,
                tag='ol', escape_value=False)
            or get_element_by_attribute(
                'class', r'[^\'"]*(?<=[\'"\s])morePart(?=[\'"\s])[^\'"]*', webpage,
                tag='ol', escape_value=False)
            or '')

        entries = traverse_obj(re.finditer(
            r'''(?x)
            <a
                (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
                    (?<=\s)class\s*=\s*(?P<_q>['"])
                        (?:
                            [^\'"]*(?<=[\'"\s])songName(?=[\'"\s])[^\'"]*
                        )
                    (?P=_q)
                (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
            >
            ''', song_list),
            (..., 0, {extract_attributes}, 'href', {self._urljoin}, {self.url_result}))
        if not entries:
            if warn:
                self.report_warning('Failed to extract playlist entries, finding suitable links instead!')
            return self._extract_suitable_links(webpage, media_types)

        return entries


class BoomPlayMusicIE(BoomPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/songs/(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.boomplay.com/songs/165481965',
        'md5': 'c5fb4f23e6aae98064230ef3c39c2178',
        'info_dict': {
            'title': 'Rise of the Fallen Heroes',
            'ext': 'mp3',
            'id': '165481965',
            'artists': ['fatbunny'],
            'thumbnail': 'https://source.boomplaymusic.com/group10/M00/04/29/375ecda38f6f48179a93c72ab909118f_464_464.jpg',
            'channel_url': 'https://www.boomplay.com/artists/52723101',
            'duration': 125.0,
            'release_year': 2024,
            'comment_count': int,
            'like_count': int,
            'repost_count': int,
            'album': 'Legendary Battle',
            'genres': ['Metal'],
        },
    }

    def _real_extract(self, url):
        song_id = self._match_id(url)
        webpage = self._download_webpage(url, song_id)
        ld_json_meta = next(self._yield_json_ld(webpage, song_id))

        return merge_dicts(
            self._extract_page_metadata(webpage, song_id),
            traverse_obj(ld_json_meta, {
                'title': 'name',
                'thumbnail': 'image',
                'channel_url': ('byArtist', 0, '@id'),
                'artists': ('byArtist', ..., 'name'),
                'duration': ('duration', {parse_duration}),
            }), {
                'formats': self._extract_formats(song_id, 'MUSIC', vcodec='none'),
            })


class BoomPlayVideoIE(BoomPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/video/(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.boomplay.com/video/1154892',
        'md5': 'd9b67ad333d2292a82922062d065352d',
        'info_dict': {
            'id': '1154892',
            'ext': 'mp4',
            'title': 'Autumn blues',
            'thumbnail': 'https://source.boomplaymusic.com/group10/M00/10/10/2171dee9e1f8452e84021560729edb88.jpg',
            'upload_date': '20241010',
            'timestamp': 1728599214,
            'view_count': int,
            'duration': 177.0,
            'description': 'Autumn blues by Lugo',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        return merge_dicts(
            self._extract_page_metadata(webpage, video_id),
            self._search_json_ld(webpage, video_id), {
                'formats': self._extract_formats(video_id, 'VIDEO', ext='mp4'),
            })


class BoomPlayEpisodeIE(BoomPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/episode/(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.boomplay.com/episode/7132706',
        'md5': 'f26e236b764baa53d7a2cbb7e9ce6dc4',
        'info_dict': {
            'id': '7132706',
            'ext': 'mp3',
            'title': 'Letting Go',
            'repost_count': int,
            'thumbnail': 'https://source.boomplaymusic.com/group10/M00/05/06/fc535eaa25714b43a47185a9831887a5_320_320.jpg',
            'comment_count': int,
            'duration': 921.0,
            'upload_date': '20240506',
            'description': 'md5:5ec684b281fa0f9e4c31b3ee20c5e57a',
        },
    }

    def _real_extract(self, url):
        ep_id = self._match_id(url)
        webpage = self._download_webpage(url, ep_id)
        return merge_dicts(
            self._extract_page_metadata(webpage, ep_id), {
                'title': self._og_search_title(webpage, fatal=True).rsplit('|', 2)[0].strip(),
                'description': self._html_search_meta(
                    ['description', 'og:description', 'twitter:description'], webpage),
                'formats': self._extract_formats(ep_id, 'EPISODE', vcodec='none'),
            })


class BoomPlayPodcastIE(BoomPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/podcasts/(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.boomplay.com/podcasts/5372',
        'playlist_count': 200,
        'info_dict': {
            'id': '5372',
            'title': 'TED Talks Daily',
            'description': 'md5:541182e787ce8fd578c835534c907077',
            'thumbnail': 'https://source.boomplaymusic.com/group10/M00/12/22/6f9cf97ad6f846a0a7882c98dfcf4f8c_320_320.jpg',
            'repost_count': int,
            'comment_count': int,
            'like_count': int,
        },
    }

    def _real_extract(self, url):
        _id = self._match_id(url)
        webpage = self._download_webpage(url, _id)
        song_list = get_elements_by_attribute(
            'class', r'[^\'"]*(?<=[\'"\s])morePart_musics(?=[\'"\s])[^\'"]*', webpage,
            tag='ol', escape_value=False)[0]
        song_list = traverse_obj(re.finditer(
            r'''(?x)
            <(?P<tag>li)
            (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
            \sdata-id\s*=\s*(?P<_q>['"]?)(?:(?P<id>\d+))(?P=_q)''',
            song_list),
            (..., 'id', {
                lambda x: self.url_result(
                    f'https://www.boomplay.com/episode/{x}', BoomPlayEpisodeIE, x),
            }))
        return self.playlist_result(
            song_list, _id,
            playlist_title=self._og_search_title(webpage, fatal=True).rsplit('|', 2)[0].strip(),
            playlist_description=self._og_search_description(webpage, default=''),
            **self._extract_page_metadata(webpage, _id))


class BoomPlayPlaylistIE(BoomPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/(?:playlists|artists|albums)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.boomplay.com/playlists/33792494',
        'info_dict': {
            'id': '33792494',
            'title': 'Daily Trending Indonesia',
            'thumbnail': 'https://source.boomplaymusic.com/group10/M00/08/19/d05d431ee616412caeacd7f78f4f68f5_320_320.jpeg',
            'repost_count': int,
            'comment_count': int,
            'like_count': int,
            'description': 'md5:7ebdffc5137c77acb62acb3c89248445',
        },
        'playlist_count': 10,
    }, {
        'url': 'https://www.boomplay.com/artists/52723101',
        'only_matching': True,
    }, {
        'url': 'https://www.boomplay.com/albums/89611238?from=home#google_vignette',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        json_ld_metadata = next(self._yield_json_ld(webpage, playlist_id))
        # schema `MusicGroup` not supported by self._json_ld()

        return self.playlist_result(**merge_dicts(
            self._extract_page_metadata(webpage, playlist_id),
            traverse_obj(json_ld_metadata, {
                'entries': ('track', ..., 'url', {
                    functools.partial(self.url_result, ie=BoomPlayMusicIE),
                }),
                'playlist_title': 'name',
                'thumbnail': 'image',
                'artists': ('byArtist', ..., 'name'),
                'channel_url': ('byArtist', 0, '@id'),
            })))


class BoomPlayGenericPlaylistIE(BoomPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/.+'
    _TESTS = [{
        'url': 'https://www.boomplay.com/search/default/Rise%20of%20the%20Fallen%20Heroes',
        'md5': 'c5fb4f23e6aae98064230ef3c39c2178',
        'info_dict': {
            'id': '165481965',
            'ext': 'mp3',
            'title': 'Rise of the Fallen Heroes',
            'duration': 125.0,
            'genres': ['Metal'],
            'artists': ['fatbunny'],
            'thumbnail': 'https://source.boomplaymusic.com/group10/M00/04/29/375ecda38f6f48179a93c72ab909118f_464_464.jpg',
            'channel_url': 'https://www.boomplay.com/artists/52723101',
            'comment_count': int,
            'repost_count': int,
            'album': 'Legendary Battle',
            'release_year': 2024,
            'like_count': int,
        },
    }, {
        'url': 'https://www.boomplay.com/search/video/%20Autumn%20blues',
        'md5': 'd9b67ad333d2292a82922062d065352d',
        'info_dict': {
            'id': '1154892',
            'title': 'Autumn blues',
            'ext': 'mp4',
            'timestamp': 1728599214,
            'view_count': int,
            'thumbnail': 'https://source.boomplaymusic.com/group10/M00/10/10/2171dee9e1f8452e84021560729edb88.jpg',
            'description': 'Autumn blues by Lugo',
            'upload_date': '20241010',
            'duration': 177.0,
        },
        'expected_warnings': ['Failed to extract playlist entries, finding suitable links instead!'],
        'params': {'playlist_items': '1'},
    }]

    @classmethod
    def suitable(cls, url):
        if not any(ie.suitable(url) for ie in (
            BoomPlayEpisodeIE,
            BoomPlayMusicIE,
            BoomPlayPlaylistIE,
            BoomPlayPodcastIE,
            BoomPlayVideoIE,
        )):
            return super().suitable(url)
        return False

    def _real_extract(self, url):
        _id = self._generic_id(url)
        webpage = self._download_webpage(url, _id)
        # TODO: pass media types based on search types
        return self.playlist_result(
            self._extract_playlist_entries(webpage, self._MEDIA_TYPES),
            **self._extract_page_metadata(webpage, _id))


class BoomPlaySearchIE(SearchInfoExtractor):
    _SEARCH_KEY = 'boomplaysearch'
    _RETURN_TYPE = 'url'
    _TEST = {
        'url': 'boomplaysearch:rise of the fallen heroes',
        'only_matching': True,
    }

    def _search_results(self, query):
        yield self.url_result(
            f'https://www.boomplay.com/search/default/{urllib.parse.quote(query)}')
