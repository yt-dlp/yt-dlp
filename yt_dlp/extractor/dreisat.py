from .zdf import ZDFBaseIE
from ..utils import (
    NO_DEFAULT,
    ExtractorError,
    int_or_none,
    merge_dicts,
    traverse_obj,
    try_get,
    unified_timestamp,
)


class DreiSatIE(ZDFBaseIE):
    IE_NAME = '3sat'
    _VALID_URL = r'https?://(?:www\.)?3sat\.de/(?:[^/]+/)*(?P<id>[^/?#&]+)\.html'
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
            'timestamp': 1738593000,
            'upload_date': '20250203',
        },
    }, {
        'url': 'https://www.3sat.de/film/ab-18/ab-18---mein-fremdes-ich-100.html',
        'md5': '66cb9013ce37f6e008dc99bfcf1356bc',
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
        'md5': '69f276184c9a24147e4baae728fbc3c4',
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
        # Same as https://www.zdf.de/filme/filme-sonstige/der-hauptmann-112.html
        'url': 'https://www.3sat.de/film/spielfilm/der-hauptmann-100.html',
        'only_matching': True,
    }, {
        # Same as https://www.zdf.de/wissen/nano/nano-21-mai-2019-102.html, equal media ids
        'url': 'https://www.3sat.de/wissen/nano/nano-21-mai-2019-102.html',
        'only_matching': True,
    }]

    def _extract_player(self, webpage, video_id, fatal=True):
        return self._parse_json(
            self._search_regex(
                r'(?s)data-zdfplayer-jsb=(["\'])(?P<json>{.+?})\1', webpage,
                'player JSON', default='{}' if not fatal else NO_DEFAULT,
                group='json'),
            video_id)

    def _extract_regular(self, url, player, video_id):
        player_url = player['content']
        api_token = f'Bearer {player["apiToken"]}'

        content = self._call_api(player_url, video_id, 'video metadata', api_token)
        return self._extract_entry(player_url, api_token, content, video_id)

    def _extract_entry(self, url, api_token, content, video_id):
        title = content.get('title') or content['teaserHeadline']

        t = content['mainVideoContent']['http://zdf.de/rels/target']
        ptmd_path = traverse_obj(t, (
            (('streams', 'default'), None),
            ('http://zdf.de/rels/streams/ptmd', 'http://zdf.de/rels/streams/ptmd-template'),
        ), get_all=False)
        if not ptmd_path:
            raise ExtractorError('Could not extract ptmd_path')

        info = self._extract_ptmd(url, ptmd_path, video_id, api_token)
        layouts = try_get(
            content, lambda x: x['teaserImageRef']['layouts'], dict)
        thumbnails = self._extract_thumbnails(layouts)

        chapter_marks = t.get('streamAnchorTag') or []
        chapter_marks.append({'anchorOffset': int_or_none(t.get('duration'))})
        chapters = [{
            'start_time': chap.get('anchorOffset'),
            'end_time': next_chap.get('anchorOffset'),
            'title': chap.get('anchorLabel'),
        } for chap, next_chap in zip(chapter_marks, chapter_marks[1:])]

        return merge_dicts(info, {
            'title': title,
            'description': content.get('leadParagraph') or content.get('teasertext'),
            'duration': int_or_none(t.get('duration')),
            'timestamp': unified_timestamp(content.get('editorialDate')),
            'thumbnails': thumbnails,
            'chapters': chapters or None,
            'episode': title,
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

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        player = self._extract_player(webpage, url)
        return self._extract_regular(url, player, video_id)
