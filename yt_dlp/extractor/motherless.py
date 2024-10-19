import datetime as dt
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    remove_end,
    str_to_int,
    unified_strdate,
)


class MotherlessIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?motherless\.com/(?:g/[a-z0-9_]+/|G[VIG]?[A-F0-9]+/)?(?P<id>[A-F0-9]+)'
    _TESTS = [{
        'url': 'http://motherless.com/EE97006',
        'md5': 'cb5e7438f7a3c4e886b7bccc1292a3bc',
        'info_dict': {
            'id': 'EE97006',
            'ext': 'mp4',
            'title': 'Dogging blond Brit getting glazed (comp)',
            'categories': ['UK', 'slag', 'whore', 'dogging', 'cunt', 'cumhound', 'big tits', 'Pearl Necklace'],
            'upload_date': '20230519',
            'uploader_id': 'deathbird',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
            'comment_count': int,
            'view_count': int,
            'like_count': int,
        },
        'params': {
            # Incomplete cert chains
            'nocheckcertificate': True,
        },
    }, {
        'url': 'http://motherless.com/532291B',
        'md5': 'bc59a6b47d1f958e61fbd38a4d31b131',
        'info_dict': {
            'id': '532291B',
            'ext': 'mp4',
            'title': 'Amazing girl playing the omegle game, PERFECT!',
            'categories': ['Amateur', 'webcam', 'omegle', 'pink', 'young', 'masturbate', 'teen',
                           'game', 'hairy'],
            'upload_date': '20140622',
            'uploader_id': 'Sulivana7x',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
        },
        'skip': '404',
    }, {
        'url': 'http://motherless.com/g/cosplay/633979F',
        'md5': '0b2a43f447a49c3e649c93ad1fafa4a0',
        'info_dict': {
            'id': '633979F',
            'ext': 'mp4',
            'title': 'Turtlette',
            'categories': ['superheroine heroine superher'],
            'upload_date': '20140827',
            'uploader_id': 'shade0230',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
            'like_count': int,
            'comment_count': int,
            'view_count': int,
        },
        'params': {
            'nocheckcertificate': True,
        },
    }, {
        'url': 'http://motherless.com/8B4BBC1',
        'info_dict': {
            'id': '8B4BBC1',
            'ext': 'mp4',
            'title': 'VIDEO00441.mp4',
            'categories': [],
            'upload_date': '20160214',
            'uploader_id': 'NMWildGirl',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
            'like_count': int,
            'comment_count': int,
            'view_count': int,
        },
        'params': {
            'nocheckcertificate': True,
        },
    }, {
        # see https://motherless.com/videos/recent for recent videos with
        # uploaded date in "ago" format
        'url': 'https://motherless.com/3C3E2CF',
        'info_dict': {
            'id': '3C3E2CF',
            'ext': 'mp4',
            'title': 'a/ Hot Teens',
            'categories': list,
            'upload_date': '20210104',
            'uploader_id': 'anonymous',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
            'like_count': int,
            'comment_count': int,
            'view_count': int,
        },
        'params': {
            'nocheckcertificate': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        if any(p in webpage for p in (
                '<title>404 - MOTHERLESS.COM<',
                ">The page you're looking for cannot be found.<")):
            raise ExtractorError(f'Video {video_id} does not exist', expected=True)

        if '>The content you are trying to view is for friends only.' in webpage:
            raise ExtractorError(f'Video {video_id} is for friends only', expected=True)

        title = self._html_search_regex(
            (r'(?s)<div[^>]+\bclass=["\']media-meta-title[^>]+>(.+?)</div>',
             r'id="view-upload-title">\s+([^<]+)<'), webpage, 'title')
        video_url = (self._html_search_regex(
            (r'setup\(\{\s*["\']file["\']\s*:\s*(["\'])(?P<url>(?:(?!\1).)+)\1',
             r'fileurl\s*=\s*(["\'])(?P<url>(?:(?!\1).)+)\1'),
            webpage, 'video URL', default=None, group='url')
            or f'http://cdn4.videos.motherlessmedia.com/videos/{video_id}.mp4?fs=opencloud')
        age_limit = self._rta_search(webpage)
        view_count = str_to_int(self._html_search_regex(
            (r'>([\d,.]+)\s+Views<', r'<strong>Views</strong>\s+([^<]+)<'),
            webpage, 'view count', fatal=False))
        like_count = str_to_int(self._html_search_regex(
            (r'>([\d,.]+)\s+Favorites<',
             r'<strong>Favorited</strong>\s+([^<]+)<'),
            webpage, 'like count', fatal=False))

        upload_date = unified_strdate(self._search_regex(
            r'class=["\']count[^>]+>(\d+\s+[a-zA-Z]{3}\s+\d{4})<', webpage,
            'upload date', default=None))
        if not upload_date:
            uploaded_ago = self._search_regex(
                r'>\s*(\d+[hd])\s+[aA]go\b', webpage, 'uploaded ago',
                default=None)
            if uploaded_ago:
                delta = int(uploaded_ago[:-1])
                _AGO_UNITS = {
                    'h': 'hours',
                    'd': 'days',
                }
                kwargs = {_AGO_UNITS.get(uploaded_ago[-1]): delta}
                upload_date = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(**kwargs)).strftime('%Y%m%d')

        comment_count = len(re.findall(r'''class\s*=\s*['"]media-comment-contents\b''', webpage))
        uploader_id = self._html_search_regex(
            (r'''<span\b[^>]+\bclass\s*=\s*["']username\b[^>]*>([^<]+)</span>''',
             r'''(?s)['"](?:media-meta-member|thumb-member-username)\b[^>]+>\s*<a\b[^>]+\bhref\s*=\s*['"]/m/([^"']+)'''),
            webpage, 'uploader_id', fatal=False)
        categories = self._html_search_meta('keywords', webpage, default='')
        categories = [cat.strip() for cat in categories.split(',') if cat.strip()]

        return {
            'id': video_id,
            'title': title,
            'upload_date': upload_date,
            'uploader_id': uploader_id,
            'thumbnail': self._og_search_thumbnail(webpage),
            'categories': categories,
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'age_limit': age_limit,
            'url': video_url,
        }


class MotherlessPaginatedIE(InfoExtractor):
    _EXTRA_QUERY = {}
    _PAGE_SIZE = 60

    def _correct_path(self, url, item_id):
        raise NotImplementedError('This method must be implemented by subclasses')

    def _extract_entries(self, webpage, base):
        for mobj in re.finditer(r'href="[^"]*(?P<href>/[A-F0-9]+)"\s+title="(?P<title>[^"]+)',
                                webpage):
            video_url = urllib.parse.urljoin(base, mobj.group('href'))
            video_id = MotherlessIE.get_temp_id(video_url)

            if video_id:
                yield self.url_result(video_url, MotherlessIE, video_id, mobj.group('title'))

    def _real_extract(self, url):
        item_id = self._match_id(url)
        real_url = self._correct_path(url, item_id)
        webpage = self._download_webpage(real_url, item_id, 'Downloading page 1')

        def get_page(idx):
            page = idx + 1
            current_page = webpage if not idx else self._download_webpage(
                real_url, item_id, note=f'Downloading page {page}', query={'page': page, **self._EXTRA_QUERY})
            yield from self._extract_entries(current_page, real_url)

        return self.playlist_result(
            OnDemandPagedList(get_page, self._PAGE_SIZE), item_id,
            remove_end(self._html_extract_title(webpage), ' | MOTHERLESS.COM ™'))


class MotherlessGroupIE(MotherlessPaginatedIE):
    _VALID_URL = r'https?://(?:www\.)?motherless\.com/g[vifm]?/(?P<id>[a-z0-9_]+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'http://motherless.com/gv/movie_scenes',
        'info_dict': {
            'id': 'movie_scenes',
            'title': 'Movie Scenes - Videos - Hot and sexy scenes from "regular" movies... Beautiful actresses fully',
        },
        'playlist_mincount': 540,
    }, {
        'url': 'http://motherless.com/g/sex_must_be_funny',
        'info_dict': {
            'id': 'sex_must_be_funny',
            'title': 'Sex must be funny',
        },
        'playlist_count': 0,
    }, {
        'url': 'https://motherless.com/gv/beautiful_cock',
        'info_dict': {
            'id': 'beautiful_cock',
            'title': 'Beautiful Cock',
        },
        'playlist_mincount': 2040,
    }]

    def _correct_path(self, url, item_id):
        return urllib.parse.urljoin(url, f'/gv/{item_id}')


class MotherlessGalleryIE(MotherlessPaginatedIE):
    _VALID_URL = r'https?://(?:www\.)?motherless\.com/G[VIG]?(?P<id>[A-F0-9]+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://motherless.com/GV338999F',
        'info_dict': {
            'id': '338999F',
            'title': 'Random',
        },
        'playlist_mincount': 171,
    }, {
        'url': 'https://motherless.com/GVABD6213',
        'info_dict': {
            'id': 'ABD6213',
            'title': 'Cuties',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://motherless.com/GVBCF7622',
        'info_dict': {
            'id': 'BCF7622',
            'title': 'Vintage',
        },
        'playlist_count': 0,
    }, {
        'url': 'https://motherless.com/G035DE2F',
        'info_dict': {
            'id': '035DE2F',
            'title': 'General',
        },
        'playlist_mincount': 420,
    }]

    def _correct_path(self, url, item_id):
        return urllib.parse.urljoin(url, f'/GV{item_id}')


class MotherlessUploaderIE(MotherlessPaginatedIE):
    _VALID_URL = r'https?://(?:www\.)?motherless\.com/u/(?P<id>\w+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://motherless.com/u/Mrgo4hrs2023',
        'info_dict': {
            'id': 'Mrgo4hrs2023',
            'title': "Mrgo4hrs2023's Uploads - Videos",
        },
        'playlist_mincount': 32,
    }, {
        'url': 'https://motherless.com/u/Happy_couple?t=v',
        'info_dict': {
            'id': 'Happy_couple',
            'title': "Happy_couple's Uploads - Videos",
        },
        'playlist_mincount': 8,
    }]

    _EXTRA_QUERY = {'t': 'v'}

    def _correct_path(self, url, item_id):
        return urllib.parse.urljoin(url, f'/u/{item_id}?t=v')
