import base64
import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    join_nonempty,
    mimetype2ext,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class VidflexIE(InfoExtractor):
    _DOMAINS_RE = [
        r'[^.]+\.vidflex\.tv',
        r'(?:www\.)?acactv\.ca',
        r'(?:www\.)?albertalacrossetv\.com',
        r'(?:www\.)?cjfltv\.com',
        r'(?:www\.)?figureitoutbaseball\.com',
        r'(?:www\.)?ocaalive\.com',
        r'(?:www\.)?pegasussports\.tv',
        r'(?:www\.)?praxisseries\.ca',
        r'(?:www\.)?silenticetv\.com',
        r'(?:www\.)?tuffhedemantv\.com',
        r'(?:www\.)?watchfuntv\.com',
        r'live\.ofsaa\.on\.ca',
        r'tv\.procoro\.ca',
        r'tv\.realcastmedia\.net',
        r'tv\.fringetheatre\.ca',
        r'video\.haisla\.ca',
        r'video\.hockeycanada\.ca',
        r'video\.huuayaht\.org',
        r'video\.turningpointensemble\.ca',
        r'videos\.livingworks\.net',
        r'videos\.telusworldofscienceedmonton\.ca',
        r'watch\.binghamtonbulldogs\.com',
        r'watch\.rekindle\.tv',
        r'watch\.wpca\.com',
    ]
    _VALID_URL = rf'https?://(?:{"|".join(_DOMAINS_RE)})/[a-z]{{2}}(?:-[a-z]{{2}})?/c/[\w-]+\.(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://video.hockeycanada.ca/en/c/nwt-micd-up-with-jamie-lee-rattray.107486',
        'only_matching': True,
    }, {
        # m3u8 + https
        'url': 'https://video.hockeycanada.ca/en-us/c/nwt-micd-up-with-jamie-lee-rattray.107486',
        'info_dict': {
            'id': '107486',
            'title': 'NWT: Mic’d up with Jamie Lee Rattray',
            'ext': 'mp4',
            'duration': 115,
            'timestamp': 1634310409,
            'upload_date': '20211015',
            'tags': ['English', '2021', "National Women's Team"],
            'description': 'md5:efb1cf6165b48cc3f5555c4262dd5b23',
            'thumbnail': r're:^https?://wpmedia01-a\.akamaihd\.net/en/asset/public/image/.+',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://video.hockeycanada.ca/en/c/mwc-remembering-the-wild-ride-in-riga.112307',
        'info_dict': {
            'id': '112307',
            'title': 'MWC: Remembering the wild ride in Riga',
            'ext': 'mp4',
            'duration': 322,
            'timestamp': 1716235607,
            'upload_date': '20240520',
            'tags': ['English', '2024', "National Men's Team", 'IIHF World Championship', 'Fan'],
            'description': r're:.+Canada’s National Men’s Team.+',
            'thumbnail': r're:^https?://wpmedia01-a\.akamaihd\.net/en/asset/public/image/.+',
        },
        'params': {'skip_download': True},
    }, {
        # the same video in French
        'url': 'https://video.hockeycanada.ca/fr/c/cmm-retour-sur-un-parcours-endiable-a-riga.112304',
        'info_dict': {
            'id': '112304',
            'title': 'CMM : Retour sur un parcours endiablé à Riga',
            'ext': 'mp4',
            'duration': 322,
            'timestamp': 1716235545,
            'upload_date': '20240520',
            'tags': ['French', '2024', "National Men's Team", 'IIHF World Championship', 'Fan'],
            'description': 'md5:cf825222882a3dab1cd62cffcf3b4d1f',
            'thumbnail': r're:^https?://wpmedia01-a\.akamaihd\.net/en/asset/public/image/.+',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://myfbcgreenville.vidflex.tv/en/c/may-12th-2024.658',
        'only_matching': True,
    }, {
        'url': 'https://www.figureitoutbaseball.com/en/c/fiob-podcast-14-dan-bertolini-ncaa-d1-head-coach-recorded-11-29-2018.1367',
        'only_matching': True,
    }, {
        'url': 'https://videos.telusworldofscienceedmonton.ca/en/c/the-aurora-project-timelapse-4.577',
        'only_matching': True,
    }, {
        'url': 'https://www.tuffhedemantv.com/en/c/2022-tuff-hedeman-tour-hobbs-nm-january-22.227',
        'only_matching': True,
    }, {
        'url': 'https://www.albertalacrossetv.com/en/c/up-floor-ground-balls-one-more.3449',
        'only_matching': True,
    }, {
        'url': 'https://www.silenticetv.com/en/c/jp-unlocked-day-in-the-life-of-langley-ha-15u.5197',
        'only_matching': True,
    }, {
        'url': 'https://jphl.vidflex.tv/en/c/jp-unlocked-day-in-the-life-of-langley-ha-15u.5197',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data_url = self._html_search_regex(
            r'content_api:\s*(["\'])(?P<url>https?://(?:(?!\1).)+)\1', webpage, 'content api url', group='url')
        media_config = traverse_obj(
            self._download_json(data_url, video_id),
            ('config', {base64.b64decode}, {bytes.decode}, {json.loads}, {dict}))

        return {
            'id': video_id,
            'formats': list(self._yield_formats(media_config, video_id)),
            **self._search_json_ld(
                webpage.replace('/*<![CDATA[*/', '').replace('/*]]>*/', ''), video_id),
        }

    def _yield_formats(self, media_config, video_id):
        for media_source in traverse_obj(media_config, ('media', 'source', lambda _, v: url_or_none(v['src']))):
            media_url = media_source['src']
            media_type = mimetype2ext(media_source.get('type'))

            if media_type == 'm3u8':
                yield from self._extract_m3u8_formats(media_url, video_id, fatal=False, m3u8_id='hls')
            elif media_type == 'mp4':
                bitrate = self._search_regex(r'_(\d+)k\.mp4', media_url, 'bitrate', default=None)
                yield {
                    'format_id': join_nonempty('http', bitrate),
                    'url': media_url,
                    'ext': 'mp4',
                    'tbr': int_or_none(bitrate),
                }
            else:
                yield {
                    'url': media_url,
                    'ext': media_type,
                }
