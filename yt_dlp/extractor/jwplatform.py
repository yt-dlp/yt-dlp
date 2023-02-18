import re

from .common import InfoExtractor
from ..utils import unsmuggle_url


class JWPlatformIE(InfoExtractor):
    _VALID_URL = r'(?:https?://(?:content\.jwplatform|cdn\.jwplayer)\.com/(?:(?:feed|player|thumb|preview|manifest)s|jw6|v2/media)/|jwplatform:)(?P<id>[a-zA-Z0-9]{8})'
    _TESTS = [{
        'url': 'http://content.jwplatform.com/players/nPripu9l-ALJ3XQCI.js',
        'md5': 'fa8899fa601eb7c83a64e9d568bdf325',
        'info_dict': {
            'id': 'nPripu9l',
            'ext': 'mov',
            'title': 'Big Buck Bunny Trailer',
            'description': 'Big Buck Bunny is a short animated film by the Blender Institute. It is made using free and open source software.',
            'upload_date': '20081127',
            'timestamp': 1227796140,
        }
    }, {
        'url': 'https://cdn.jwplayer.com/players/nPripu9l-ALJ3XQCI.js',
        'only_matching': True,
    }]

    _WEBPAGE_TESTS = [{
        # JWPlatform iframe
        'url': 'https://www.covermagazine.co.uk/feature/2465255/business-protection-involved',
        'info_dict': {
            'id': 'AG26UQXM',
            'ext': 'mp4',
            'upload_date': '20160719',
            'timestamp': 1468923808,
            'title': '2016_05_18 Cover L&G Business Protection V1 FINAL.mp4',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/AG26UQXM/poster.jpg?width=720',
            'description': '',
            'duration': 294.0,
        },
    }, {
        # Player url not surrounded by quotes
        'url': 'https://www.deutsche-kinemathek.de/en/online/streaming/darling-berlin',
        'info_dict': {
            'id': 'R10NQdhY',
            'title': 'Playgirl',
            'ext': 'mp4',
            'upload_date': '20220624',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/R10NQdhY/poster.jpg?width=720',
            'timestamp': 1656064800,
            'description': 'BRD 1966, Will Tremper',
            'duration': 5146.0,
        },
        'params': {'allowed_extractors': ['generic', 'jwplatform']},
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        for tag, key in ((r'(?:script|iframe)', 'src'), ('input', 'value')):
            # <input value=URL> is used by hyland.com
            # if we find <iframe>, dont look for <input>
            ret = re.findall(
                r'<%s[^>]+?%s=["\']?((?:https?:)?//(?:content\.jwplatform|cdn\.jwplayer)\.com/players/[a-zA-Z0-9]{8})' % (tag, key),
                webpage)
            if ret:
                return ret
        mobj = re.search(r'<div\b[^>]* data-video-jw-id="([a-zA-Z0-9]{8})"', webpage)
        if mobj:
            return [f'jwplatform:{mobj.group(1)}']

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        self._initialize_geo_bypass({
            'countries': smuggled_data.get('geo_countries'),
        })
        video_id = self._match_id(url)
        json_data = self._download_json('https://cdn.jwplayer.com/v2/media/' + video_id, video_id)
        return self._parse_jwplayer_data(json_data, video_id)


class LeFigaroVideoEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://video\.lefigaro\.fr/embed/[^?#]+/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://video.lefigaro.fr/embed/figaro/video/les-francais-ne-veulent-ils-plus-travailler-suivez-en-direct-le-club-le-figaro-idees/',
        'md5': 'e94de44cd80818084352fcf8de1ce82c',
        'info_dict': {
            'id': 'g9j7Eovo',
            'title': 'Les Français ne veulent-ils plus travailler ? Retrouvez Le Club Le Figaro Idées',
            'description': 'md5:862b8813148ba4bf10763a65a69dfe41',
            'upload_date': '20230216',
            'timestamp': 1676581615,
            'duration': 3076,
            'thumbnail': r're:^https?://[^?#]+\.(?:jpeg|jpg)',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://video.lefigaro.fr/embed/figaro/video/intelligence-artificielle-faut-il-sen-mefier/',
        'md5': '0b3f10332b812034b3a3eda1ef877c5f',
        'info_dict': {
            'id': 'LeAgybyc',
            'title': 'Intelligence artificielle : faut-il s’en méfier ?',
            'description': 'md5:249d136e3e5934a67c8cb704f8abf4d2',
            'upload_date': '20230124',
            'timestamp': 1674584477,
            'duration': 860,
            'thumbnail': r're:^https?://[^?#]+\.(?:jpeg|jpg)',
            'ext': 'mp4',
        },
    }]

    _WEBPAGE_TESTS = [{
        'url': 'https://video.lefigaro.fr/figaro/video/suivez-en-direct-le-club-le-figaro-international-avec-philippe-gelie-9/',
        'md5': '3972ddf2d5f8b98699f191687258e2f9',
        'info_dict': {
            'id': 'QChnbPYA',
            'title': 'Où en est le couple franco-allemand ? Retrouvez Le Club Le Figaro International',
            'description': 'md5:6f47235b7e7c93b366fd8ebfa10572ac',
            'upload_date': '20230123',
            'timestamp': 1674503575,
            'duration': 3153,
            'thumbnail': r're:^https?://[^?#]+\.(?:jpeg|jpg)',
            'age_limit': 0,
            'ext': 'mp4',
        },
    }, {
        'url': 'https://video.lefigaro.fr/figaro/video/la-philosophe-nathalie-sarthou-lajus-est-linvitee-du-figaro-live/',
        'md5': '3ac0a0769546ee6be41ab52caea5d9a9',
        'info_dict': {
            'id': 'QJzqoNbf',
            'title': 'La philosophe Nathalie Sarthou-Lajus est l’invitée du Figaro Live',
            'description': 'md5:c586793bb72e726c83aa257f99a8c8c4',
            'upload_date': '20230217',
            'timestamp': 1676661986,
            'duration': 1558,
            'thumbnail': r're:^https?://[^?#]+\.(?:jpeg|jpg)',
            'age_limit': 0,
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        player_data = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['pageData']['playerData']

        return self.url_result(
            f'jwplatform:{player_data["videoId"]}', title=player_data.get('title'),
            description=player_data.get('description'), thumbnail=player_data.get('poster'))
