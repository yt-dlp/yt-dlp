from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
    parse_resolution,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class SBSCoKrIE(InfoExtractor):
    IE_NAME = 'sbs.co.kr'
    _VALID_URL = [r'https?://allvod\.sbs\.co\.kr/allvod/vod(?:Package)?EndPage\.do\?(?:[^#]+&)?mdaId=(?P<id>\d+)',
                  r'https?://programs\.sbs\.co\.kr/(?:enter|drama|culture|sports|plus|mtv|kth)/[a-z0-9]+/(?:vod|clip|movie)/\d+/(?P<id>(?:OC)?\d+)']

    _TESTS = [{
        'url': 'https://programs.sbs.co.kr/enter/dongsang2/clip/52007/OC467706746?div=main_pop_clip',
        'md5': 'c3f6d45e1fb5682039d94cda23c36f19',
        'info_dict': {
            'id': 'OC467706746',
            'ext': 'mp4',
            'title': '‘아슬아슬’ 박군♥한영의 새 집 인테리어 대첩♨',
            'description': 'md5:6a71eb1979ee4a94ea380310068ccab4',
            'thumbnail': 'https://img2.sbs.co.kr/ops_clip_img/2023/10/10/34c4c0f9-a9a5-4ff6-a92e-9bb4b5f6fa65915w1280.jpg',
            'release_timestamp': 1696889400,
            'release_date': '20231009',
            'view_count': int,
            'like_count': int,
            'duration': 238,
            'age_limit': 15,
            'series': '동상이몽2_너는 내 운명',
            'episode': '레이디제인, ‘혼전임신설’ ‘3개월’ 앞당긴 결혼식 비하인드 스토리 최초 공개!',
            'episode_number': 311,
        },
    }, {
        'url': 'https://allvod.sbs.co.kr/allvod/vodPackageEndPage.do?mdaId=22000489324&combiId=PA000000284&packageType=A&isFreeYN=',
        'md5': 'bf46b2e89fda7ae7de01f5743cef7236',
        'info_dict': {
            'id': '22000489324',
            'ext': 'mp4',
            'title': '[다시보기] 트롤리 15회',
            'description': 'md5:0e55d74bef1ac55c61ae90c73ac485f4',
            'thumbnail': 'https://img2.sbs.co.kr/img/sbs_cms/WE/2023/02/14/arC1676333794938-1280-720.jpg',
            'release_timestamp': 1676325600,
            'release_date': '20230213',
            'view_count': int,
            'like_count': int,
            'duration': 5931,
            'age_limit': 15,
            'series': '트롤리',
            'episode': '이거 다 거짓말이야',
            'episode_number': 15,
        },
    }, {
        'url': 'https://programs.sbs.co.kr/enter/fourman/vod/69625/22000508948',
        'md5': '41e8ae4cc6c8424f4e4d76661a4becbf',
        'info_dict': {
            'id': '22000508948',
            'ext': 'mp4',
            'title': '[다시보기] 신발 벗고 돌싱포맨 104회',
            'description': 'md5:c6a247383c4dd661e4b956bf4d3b586e',
            'thumbnail': 'https://img2.sbs.co.kr/img/sbs_cms/WE/2023/08/30/2vb1693355446261-1280-720.jpg',
            'release_timestamp': 1693342800,
            'release_date': '20230829',
            'view_count': int,
            'like_count': int,
            'duration': 7036,
            'age_limit': 15,
            'series': '신발 벗고 돌싱포맨',
            'episode': '돌싱포맨 저격수들 등장!',
            'episode_number': 104,
        },
    }]

    def _call_api(self, video_id, rscuse=''):
        return self._download_json(
            f'https://api.play.sbs.co.kr/1.0/sbs_vodall/{video_id}', video_id,
            note=f'Downloading m3u8 information {rscuse}',
            query={
                'platform': 'pcweb',
                'protocol': 'download',
                'absolute_show': 'Y',
                'service': 'program',
                'ssl': 'Y',
                'rscuse': rscuse,
            })

    def _real_extract(self, url):
        video_id = self._match_id(url)

        details = self._call_api(video_id)
        source = traverse_obj(details, ('vod', 'source', 'mediasource', {dict})) or {}

        formats = []
        for stream in traverse_obj(details, (
            'vod', 'source', 'mediasourcelist', lambda _, v: v['mediaurl'] or v['mediarscuse'],
        ), default=[source]):
            if not stream.get('mediaurl'):
                new_source = traverse_obj(
                    self._call_api(video_id, rscuse=stream['mediarscuse']),
                    ('vod', 'source', 'mediasource', {dict})) or {}
                if new_source.get('mediarscuse') == source.get('mediarscuse') or not new_source.get('mediaurl'):
                    continue
                stream = new_source
            formats.append({
                'url': stream['mediaurl'],
                'format_id': stream.get('mediarscuse'),
                'format_note': stream.get('medianame'),
                **parse_resolution(stream.get('quality')),
                'preference': int_or_none(stream.get('mediarscuse')),
            })

        caption_url = traverse_obj(details, ('vod', 'source', 'subtitle', {url_or_none}))

        return {
            'id': video_id,
            **traverse_obj(details, ('vod', {
                'title': ('info', 'title'),
                'duration': ('info', 'duration', {int_or_none}),
                'view_count': ('info', 'viewcount', {int_or_none}),
                'like_count': ('info', 'likecount', {int_or_none}),
                'description': ('info', 'synopsis', {clean_html}),
                'episode': ('info', 'content', ('contenttitle', 'title')),
                'episode_number': ('info', 'content', 'number', {int_or_none}),
                'series': ('info', 'program', 'programtitle'),
                'age_limit': ('info', 'targetage', {int_or_none}),
                'release_timestamp': ('info', 'broaddate', {parse_iso8601}),
                'thumbnail': ('source', 'thumbnail', 'origin', {url_or_none}),
            }), get_all=False),
            'formats': formats,
            'subtitles': {'ko': [{'url': caption_url}]} if caption_url else None,
        }


class SBSCoKrAllvodProgramIE(InfoExtractor):
    IE_NAME = 'sbs.co.kr:allvod_program'
    _VALID_URL = r'https?://allvod\.sbs\.co\.kr/allvod/vod(?:Free)?ProgramDetail\.do\?(?:[^#]+&)?pgmId=(?P<id>P?\d+)'

    _TESTS = [{
        'url': 'https://allvod.sbs.co.kr/allvod/vodFreeProgramDetail.do?type=legend&pgmId=22000010159&listOrder=vodCntAsc',
        'info_dict': {
            '_type': 'playlist',
            'id': '22000010159',
        },
        'playlist_count': 18,
    }, {
        'url': 'https://allvod.sbs.co.kr/allvod/vodProgramDetail.do?pgmId=P460810577',
        'info_dict': {
            '_type': 'playlist',
            'id': 'P460810577',
        },
        'playlist_count': 13,
    }]

    def _real_extract(self, url):
        program_id = self._match_id(url)

        details = self._download_json(
            'https://allvod.sbs.co.kr/allvod/vodProgramDetail/vodProgramDetailAjax.do',
            program_id, note='Downloading program details',
            query={
                'pgmId': program_id,
                'currentCount': '10000',
            })

        return self.playlist_result(
            [self.url_result(f'https://allvod.sbs.co.kr/allvod/vodEndPage.do?mdaId={video_id}', SBSCoKrIE)
             for video_id in traverse_obj(details, ('list', ..., 'mdaId'))], program_id)


class SBSCoKrProgramsVodIE(InfoExtractor):
    IE_NAME = 'sbs.co.kr:programs_vod'
    _VALID_URL = r'https?://programs\.sbs\.co\.kr/(?:enter|drama|culture|sports|plus|mtv)/(?P<id>[a-z0-9]+)/vods'

    _TESTS = [{
        'url': 'https://programs.sbs.co.kr/culture/morningwide/vods/65007',
        'info_dict': {
            '_type': 'playlist',
            'id': '00000210215',
        },
        'playlist_mincount': 9782,
    }, {
        'url': 'https://programs.sbs.co.kr/enter/dongsang2/vods/52006',
        'info_dict': {
            '_type': 'playlist',
            'id': '22000010476',
        },
        'playlist_mincount': 312,
    }]

    def _real_extract(self, url):
        program_slug = self._match_id(url)

        program_id = self._download_json(
            f'https://static.apis.sbs.co.kr/program-api/1.0/menu/{program_slug}', program_slug,
            note='Downloading program menu data')['program']['programid']

        return self.url_result(
            f'https://allvod.sbs.co.kr/allvod/vodProgramDetail.do?pgmId={program_id}', SBSCoKrAllvodProgramIE)
