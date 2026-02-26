from .zdf import ZDFBaseIE
from ..utils import (
    int_or_none,
    merge_dicts,
    parse_iso8601,
)
from ..utils.traversal import require, traverse_obj


class DreiSatIE(ZDFBaseIE):
    IE_NAME = '3sat'
    _VALID_URL = r'https?://(?:www\.)?3sat\.de/(?:[^/?#]+/)*(?P<id>[^/?#&]+)\.html'
    _TESTS = [{
        'url': 'https://www.3sat.de/dokumentation/reise/traumziele-suedostasiens-die-philippinen-und-vietnam-102.html',
        'info_dict': {
            'id': '231124_traumziele_philippinen_und_vietnam_dokreise',
            'ext': 'mp4',
            'title': 'Traumziele Südostasiens (1/2): Die Philippinen und Vietnam',
            'description': 'md5:26329ce5197775b596773b939354079d',
            'duration': 2625.0,
            'thumbnail': 'https://www.3sat.de/assets/traumziele-suedostasiens-die-philippinen-und-vietnam-100~original?cb=1699870351148',
            'episode': 'Traumziele Südostasiens (1/2): Die Philippinen und Vietnam',
            'episode_id': 'POS_cc7ff51c-98cf-4d12-b99d-f7a551de1c95',
            'timestamp': 1747920900,
            'upload_date': '20250522',
        },
    }, {
        'url': 'https://www.3sat.de/film/ab-18/ab-18---mein-fremdes-ich-100.html',
        'md5': 'f92638413a11d759bdae95c9d8ec165c',
        'info_dict': {
            'id': '221128_mein_fremdes_ich2_ab18',
            'ext': 'mp4',
            'title': 'Ab 18! - Mein fremdes Ich',
            'description': 'md5:cae0c0b27b7426d62ca0dda181738bf0',
            'duration': 2625.0,
            'thumbnail': 'https://www.3sat.de/assets/ab-18---mein-fremdes-ich-106~original?cb=1666081865812',
            'episode': 'Ab 18! - Mein fremdes Ich',
            'episode_id': 'POS_6225d1ca-a0d5-45e3-870b-e783ee6c8a3f',
            'timestamp': 1695081600,
            'upload_date': '20230919',
        },
    }, {
        'url': 'https://www.3sat.de/gesellschaft/37-grad-leben/aus-dem-leben-gerissen-102.html',
        'md5': 'a903eaf8d1fd635bd3317cd2ad87ec84',
        'info_dict': {
            'id': '250323_0903_sendung_sgl',
            'ext': 'mp4',
            'title': 'Plötzlich ohne dich',
            'description': 'md5:380cc10659289dd91510ad8fa717c66b',
            'duration': 1620.0,
            'thumbnail': 'https://www.3sat.de/assets/37-grad-leben-106~original?cb=1645537156810',
            'episode': 'Plötzlich ohne dich',
            'episode_id': 'POS_faa7a93c-c0f2-4d51-823f-ce2ac3ee191b',
            'timestamp': 1743162540,
            'upload_date': '20250328',
        },
    }, {
        # Video with chapters
        'url': 'https://www.3sat.de/kultur/buchmesse/dein-buch-das-beste-von-der-leipziger-buchmesse-2025-teil-1-100.html',
        'md5': '6b95790ce52e75f0d050adcdd2711ee6',
        'info_dict': {
            'id': '250330_dein_buch1_bum',
            'ext': 'mp4',
            'title': 'dein buch  - Das Beste von der Leipziger Buchmesse 2025 - Teil 1',
            'description': 'md5:bae51bfc22f15563ce3acbf97d2e8844',
            'duration': 5399.0,
            'thumbnail': 'https://www.3sat.de/assets/buchmesse-kerkeling-100~original?cb=1747256996338',
            'chapters': 'count:24',
            'episode': 'dein buch  - Das Beste von der Leipziger Buchmesse 2025 - Teil 1',
            'episode_id': 'POS_1ef236cc-b390-401e-acd0-4fb4b04315fb',
            'timestamp': 1743327000,
            'upload_date': '20250330',
        },
    }, {
        # Same as https://www.zdf.de/filme/filme-sonstige/der-hauptmann-112.html
        'url': 'https://www.3sat.de/film/spielfilm/der-hauptmann-100.html',
        'only_matching': True,
    }, {
        # Same as https://www.zdf.de/wissen/nano/nano-21-mai-2019-102.html, equal media ids
        'url': 'https://www.3sat.de/wissen/nano/nano-21-mai-2019-102.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player = self._search_json(
            r'data-zdfplayer-jsb=(["\'])', webpage, 'player JSON', video_id)
        player_url = player['content']
        api_token = f'Bearer {player["apiToken"]}'

        content = self._call_api(player_url, video_id, 'video metadata', api_token)

        video_target = content['mainVideoContent']['http://zdf.de/rels/target']
        ptmd_path = traverse_obj(video_target, (
            (('streams', 'default'), None),
            ('http://zdf.de/rels/streams/ptmd', 'http://zdf.de/rels/streams/ptmd-template'),
            {str}, any, {require('ptmd path')}))
        ptmd_url = self._expand_ptmd_template(player_url, ptmd_path)
        aspect_ratio = self._parse_aspect_ratio(video_target.get('aspectRatio'))
        info = self._extract_ptmd(ptmd_url, video_id, api_token, aspect_ratio)

        return merge_dicts(info, {
            **traverse_obj(content, {
                'title': (('title', 'teaserHeadline'), {str}, any),
                'episode': (('title', 'teaserHeadline'), {str}, any),
                'description': (('leadParagraph', 'teasertext'), {str}, any),
                'timestamp': ('editorialDate', {parse_iso8601}),
            }),
            **traverse_obj(video_target, {
                'duration': ('duration', {int_or_none}),
                'chapters': ('streamAnchorTag', {self._extract_chapters}),
            }),
            'thumbnails': self._extract_thumbnails(traverse_obj(content, ('teaserImageRef', 'layouts', {dict}))),
            **traverse_obj(content, ('programmeItem', 0, 'http://zdf.de/rels/target', {
                'series_id': ('http://zdf.de/rels/cmdm/series', 'seriesUuid', {str}),
                'series': ('http://zdf.de/rels/cmdm/series', 'seriesTitle', {str}),
                'season': ('http://zdf.de/rels/cmdm/season', 'seasonTitle', {str}),
                'season_number': ('http://zdf.de/rels/cmdm/season', 'seasonNumber', {int_or_none}),
                'season_id': ('http://zdf.de/rels/cmdm/season', 'seasonUuid', {str}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'episode_id': ('contentId', {str}),
            })),
        })
