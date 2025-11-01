import base64
import functools
import json
import re
import urllib.parse

from .common import InfoExtractor, SearchInfoExtractor
from ..aes import aes_cbc_decrypt_bytes, aes_cbc_encrypt_bytes, unpad_pkcs7
from ..utils import (
    ExtractorError,
    classproperty,
    clean_html,
    extract_attributes,
    get_elements_text_and_html_by_attribute,
    int_or_none,
    join_nonempty,
    merge_dicts,
    parse_count,
    parse_duration,
    smuggle_url,
    strip_or_none,
    unified_strdate,
    unsmuggle_url,
    url_or_none,
    urlencode_postdata,
    urljoin,
    variadic,
)
from ..utils.traversal import traverse_obj


class BoomplayBaseIE(InfoExtractor):
    # Calculated from const values, see lhx.AESUtils.encrypt in public.js
    # Note that the real key/iv differs from `lhx.AESUtils.key`/`lhx.AESUtils.iv`
    _KEY = b'boomplayVr3xopAM'
    _IV = b'boomplay8xIsKTn9'
    _BASE = 'https://www.boomplay.com'
    _MEDIA_TYPES = ('songs', 'video', 'episode', 'podcasts', 'playlists', 'artists', 'albums')
    _GEO_COUNTRIES = ['NG']

    @staticmethod
    def __yield_elements_text_and_html_by_class_and_tag(class_, tag, html):
        """
        Yields content of all element matching `tag.class_` in html
        class_ must be re escaped
        """
        # get_elements_text_and_html_by_attribute returns a generator
        return get_elements_text_and_html_by_attribute(
            attribute='class', value=rf'''[^'"]*(?<=['"\s]){class_}(?=['"\s])[^'"]*''', html=html,
            tag=tag, escape_value=False)

    @classmethod
    def __yield_elements_by_class_and_tag(cls, *args, **kwargs):
        return (content for content, _ in cls.__yield_elements_text_and_html_by_class_and_tag(*args, **kwargs))

    @classmethod
    def __yield_elements_html_by_class_and_tag(cls, *args, **kwargs):
        return (whole for _, whole in cls.__yield_elements_text_and_html_by_class_and_tag(*args, **kwargs))

    @classmethod
    def _get_elements_by_class_and_tag(cls, class_, tag, html):
        return list(cls.__yield_elements_by_class_and_tag(class_, tag, html))

    @classmethod
    def _get_element_by_class_and_tag(cls, class_, tag, html):
        return next(cls.__yield_elements_by_class_and_tag(class_, tag, html), None)

    @classmethod
    def _urljoin(cls, path):
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
        if not (source := resp.get('source')) and (code := resp.get('code')):
            if 'unavailable in your country' in (desc := resp.get('desc')) or '':
                # since NG must have failed ...
                self.raise_geo_restricted(countries=['GH', 'KE', 'TZ', 'CM', 'CI'])
            else:
                raise ExtractorError(desc or f'Failed to get play url, code: {code}')
        return unpad_pkcs7(aes_cbc_decrypt_bytes(
            base64.b64decode(source),
            self._KEY, self._IV)).decode()

    def _extract_formats(self, item_id, item_type='MUSIC', **kwargs):
        if url := url_or_none(self._get_playurl(item_id, item_type)):
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

    def _extract_page_metadata(self, webpage, item_id):
        metadata_div = self._get_element_by_class_and_tag('summary', 'div', webpage) or ''
        metadata_entries = re.findall(r'(?si)<strong>(?P<entry>.*?)</strong>', metadata_div) or []
        description = re.sub(
            r'(?i)Listen and download music for free on Boomplay!', '',
            clean_html(self._get_element_by_class_and_tag(
                'description_content', 'span', webpage)) or '') or None

        details_section = self._get_element_by_class_and_tag('songDetailInfo', 'section', webpage) or ''
        metadata_entries.extend(re.findall(r'(?si)<li>(?P<entry>.*?)</li>', details_section) or [])
        page_metadata = {
            'id': item_id,
            **self._extract_title_from_webpage(webpage),
            'thumbnail': self._html_search_meta(['og:image', 'twitter:image'],
                                                webpage, 'thumbnail', default=None),
            'like_count': parse_count(self._get_element_by_class_and_tag('btn_favorite', 'button', metadata_div)),
            'repost_count': parse_count(self._get_element_by_class_and_tag('btn_share', 'button', metadata_div)),
            'comment_count': parse_count(self._get_element_by_class_and_tag('btn_comment', 'button', metadata_div)),
            'duration': parse_duration(self._get_element_by_class_and_tag('btn_duration', 'button', metadata_div)),
            'upload_date': unified_strdate(strip_or_none(
                self._get_element_by_class_and_tag('btn_pubDate', 'button', metadata_div))),
            'description': description,
        }
        for metadata_entry in metadata_entries:
            if ':' not in metadata_entry:
                continue
            k, v = clean_html(metadata_entry).split(':', 1)
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

    def _extract_title_from_webpage(self, webpage):
        if h1_title := self._html_search_regex(r'(?i)<h1[^>]*>([^<]+)</h1>', webpage, 'title', default=None):
            return {'title': h1_title}
        else:
            return self._fix_title(
                self._html_search_meta(['og:title', 'twitter:title'], webpage, 'title', default=None)
                or self._html_search_regex(r'(?i)<title[^>]*>([^<]+)</title>', webpage, 'title', default=None))

    @staticmethod
    def _fix_title(title):
        """
        fix various types of titles(og:title, twitter:title, title tag in html head)
        """
        if not title:
            return {}

        title_patterns = (
            r'^(?P<title>(?P<artist>.+)) Songs MP3 Download, New Songs \& Albums \| Boomplay$',  # artists
            r'^(?P<artist>.+?) - (?P<title>.+) MP3\ Download \& Lyrics \| Boomplay$',  # music
            r'^Download (?P<artist>.+) album songs: (?P<title>.+?) \| Boomplay Music$',  # album
            r'^Search:(?P<title>.+) \| Boomplay Music$',  # search url
            r'^(?P<title>.+) \| Podcast \| Boomplay$',  # podcast, episode
            r'^(?P<title>.+) \| Boomplay(?: Music)?$',  # video, playlist, generic playlists
        )

        for pattern in title_patterns:
            if match := re.search(pattern, title):
                return {
                    'title': match.group('title'),
                    'artists': [match.group('artist')] if 'artist' in match.groupdict() else None,
                }

        return {'title': title}

    @classmethod
    def _extract_from_webpage(cls, url, webpage, **kwargs):
        if kwargs:
            url = smuggle_url(url, kwargs)
        return super()._extract_from_webpage(url, webpage)

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        url, smuggled_data = unsmuggle_url(url)
        media_types = variadic(smuggled_data.get('media_types', cls._MEDIA_TYPES))
        media_types = join_nonempty(*(
            re.escape(v)for v in media_types if v in cls._MEDIA_TYPES),
            delim='|')

        for mobj in re.finditer(
                rf'''(?ix)
                <a
                    (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
                        (?<=\s)href\s*=\s*(?P<_q>['"])
                            (?P<href>/(?:{media_types})/\d+/?[\-\w=?&#:;@]*)
                        (?P=_q)
                    (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
                >''', webpage):
            if url := cls._urljoin(mobj.group('href')):
                yield url

    @classmethod
    def _extract_playlist_entries(cls, webpage, media_types, warn=True):
        song_list = strip_or_none(
            cls._get_element_by_class_and_tag('morePart_musics', 'ol', webpage)
            or cls._get_element_by_class_and_tag('morePart', 'ol', webpage)
            or '')

        entries = traverse_obj(cls.__yield_elements_html_by_class_and_tag(
            'songName', 'a', song_list),
            (..., {extract_attributes}, 'href', {cls._urljoin}, {cls.url_result}))
        if not entries:
            if warn:
                cls.report_warning('Failed to extract playlist entries, finding suitable links instead!')

            def strip_ie(entry):
                # All our IEs have a _VALID_URL and set a key: don't use it
                entry.pop('ie_key', None)
                return entry

            return (strip_ie(result) for result in
                    cls._extract_from_webpage(cls._BASE, webpage, media_types=media_types))

        return entries


class BoomplayMusicIE(BoomplayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/songs/(?P<id>\d+)'
    _TESTS = [{
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
    }]

    def _real_extract(self, url):
        song_id = self._match_id(url)
        webpage = self._download_webpage(url, song_id)
        ld_json_meta = next(self._yield_json_ld(webpage, song_id))
        # TODO: extract comments(and lyrics? they don't have timestamps)
        # example: https://www.boomplay.com/songs/96352673?from=home
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


class BoomplayVideoIE(BoomplayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/video/(?P<id>\d+)'
    _TESTS = [{
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
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        return merge_dicts(
            self._extract_page_metadata(webpage, video_id),
            self._search_json_ld(webpage, video_id), {
                'formats': self._extract_formats(video_id, 'VIDEO', ext='mp4'),
            })


class BoomplayEpisodeIE(BoomplayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/episode/(?P<id>\d+)'
    _TESTS = [{
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
    }]

    def _real_extract(self, url):
        ep_id = self._match_id(url)
        webpage = self._download_webpage(url, ep_id)
        return merge_dicts(
            self._extract_page_metadata(webpage, ep_id), {
                'description': self._html_search_meta(
                    ['description', 'og:description', 'twitter:description'], webpage),
                'formats': self._extract_formats(ep_id, 'EPISODE', vcodec='none'),
            })


class BoomplayPodcastIE(BoomplayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/podcasts/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.boomplay.com/podcasts/5372',
        'playlist_count': 200,
        'info_dict': {
            'id': '5372',
            'title': 'TED Talks Daily',
            'description': r're:(?s)Every weekday, TED Talks Daily brings you the latest talks .{328} learn something new\.$',
            'thumbnail': 'https://source.boomplaymusic.com/group10/M00/12/22/6f9cf97ad6f846a0a7882c98dfcf4f8c_320_320.jpg',
            'repost_count': int,
            'comment_count': int,
            'like_count': int,
        },
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        song_list = self._get_element_by_class_and_tag('morePart_musics', 'ol', webpage)
        song_list = traverse_obj(re.finditer(
            r'''(?ix)
            <li
                (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
                    \sdata-id\s*=\s*
                        (?P<_q>['"]?)
                            (?P<id>\d+)
                        (?P=_q)
                (?:\s(?:[^>"']|"[^"]*"|'[^']*')*)?
            >''',
            song_list),
            (..., 'id', {
                lambda x: self.url_result(
                    f'https://www.boomplay.com/episode/{x}', BoomplayEpisodeIE, x),
            }))
        return self.playlist_result(
            song_list, playlist_id,
            **self._extract_page_metadata(webpage, playlist_id))


class BoomplayPlaylistIE(BoomplayBaseIE):
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
                    functools.partial(self.url_result, ie=BoomplayMusicIE),
                }),
                'playlist_title': 'name',
                'thumbnail': 'image',
                'artists': ('byArtist', ..., 'name'),
                'channel_url': ('byArtist', 0, '@id'),
            })))


class BoomplayGenericPlaylistIE(BoomplayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?boomplay\.com/.+'
    _TESTS = [{
        'url': 'https://www.boomplay.com/new-songs',
        'playlist_mincount': 20,
        'info_dict': {
            'id': 'new-songs',
            'title': 'New Songs',
            'thumbnail': 'http://www.boomplay.com/pc/img/og_default_v3.jpg',
        },
    }, {
        'url': 'https://www.boomplay.com/trending-songs',
        'playlist_mincount': 20,
        'info_dict': {
            'id': 'trending-songs',
            'title': 'Trending Songs',
            'thumbnail': 'http://www.boomplay.com/pc/img/og_default_v3.jpg',
        },
    }]

    @classmethod
    def suitable(cls, url):
        return super().suitable(url) and all(not ie.suitable(url) for ie in (
            BoomplayEpisodeIE,
            BoomplayMusicIE,
            BoomplayPlaylistIE,
            BoomplayPodcastIE,
            BoomplaySearchURLIE,
            BoomplayVideoIE,
        ))

    def _real_extract(self, url):
        playlist_id = self._generic_id(url)
        webpage = self._download_webpage(url, playlist_id)
        return self.playlist_result(
            self._extract_playlist_entries(webpage, self._MEDIA_TYPES),
            **self._extract_page_metadata(webpage, playlist_id))


class BoomplaySearchURLIE(BoomplayBaseIE):
    _TESTS = [{
        'url': 'https://www.boomplay.com/search/default/%20Rise%20of%20the%20Falletesn%20Heroes%20fatbunny',
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
        'params': {'playlist_items': '1'},
    }]

    @classproperty
    def _VALID_URL(cls):
        return r'https?://(?:www\.)?boomplay\.com/search/(?P<media_type>default|video|episode|podcasts|playlists|artists|albums)/(?P<query>[^?&#/]+)'

    def _real_extract(self, url):
        media_type, query = self._match_valid_url(url).group('media_type', 'query')
        if media_type == 'default':
            media_type = 'songs'
        webpage = self._download_webpage(url, query)
        return self.playlist_result(
            self._extract_playlist_entries(webpage, media_type, warn=media_type == 'songs'),
            **self._extract_page_metadata(webpage, query))


class BoomplaySearchIE(SearchInfoExtractor):
    _SEARCH_KEY = 'boomplaysearch'
    _RETURN_TYPE = 'url'
    _TESTS = [{
        'url': 'boomplaysearch:rise of the fallen heroes',
        'only_matching': True,
    }]

    def _search_results(self, query):
        yield self.url_result(
            f'https://www.boomplay.com/search/default/{urllib.parse.quote(query)}',
            BoomplaySearchURLIE)
