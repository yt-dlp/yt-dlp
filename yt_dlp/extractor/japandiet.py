import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    join_nonempty,
    parse_qs,
    smuggle_url,
    traverse_obj,
    try_call,
    unsmuggle_url,
)


def _parse_japanese_date(text):
    if not text:
        return None
    ERA_TABLE = {
        '明治': 1868,
        '大正': 1912,
        '昭和': 1926,
        '平成': 1989,
        '令和': 2019,
    }
    ERA_RE = '|'.join(map(re.escape, ERA_TABLE.keys()))
    mobj = re.search(rf'({ERA_RE})?(\d+)年(\d+)月(\d+)日', re.sub(r'[\s\u3000]+', '', text))
    if not mobj:
        return None
    era, year, month, day = mobj.groups()
    year, month, day = map(int, (year, month, day))
    if era:
        # example input: 令和5年3月34日
        # even though each era have their end, don't check here
        year += ERA_TABLE[era]
    return '%04d%02d%02d' % (year, month, day)


def _parse_japanese_duration(text):
    mobj = re.search(r'(?:(\d+)日間?)?(?:(\d+)時間?)?(?:(\d+)分)?(?:(\d+)秒)?', re.sub(r'[\s\u3000]+', '', text or ''))
    if not mobj:
        return
    days, hours, mins, secs = (int_or_none(x, default=0) for x in mobj.groups())
    return secs + mins * 60 + hours * 60 * 60 + days * 24 * 60 * 60


class ShugiinItvBaseIE(InfoExtractor):
    _INDEX_ROOMS = None

    @classmethod
    def _find_rooms(cls, webpage):
        return [{
            '_type': 'url',
            'id': x.group(1),
            'title': clean_html(x.group(2)).strip(),
            'url': smuggle_url(f'https://www.shugiintv.go.jp/jp/index.php?room_id={x.group(1)}', {'g': x.groups()}),
            'ie_key': ShugiinItvLiveIE.ie_key(),
        } for x in re.finditer(r'(?s)<a\s+href="[^"]+\?room_id=(room\d+)"\s*class="play_live".+?class="s12_14">(.+?)</td>', webpage)]

    def _fetch_rooms(self):
        if not self._INDEX_ROOMS:
            webpage = self._download_webpage(
                'https://www.shugiintv.go.jp/jp/index.php', None,
                encoding='euc-jp', note='Downloading proceedings info')
            ShugiinItvBaseIE._INDEX_ROOMS = self._find_rooms(webpage)
        return self._INDEX_ROOMS


class ShugiinItvLiveIE(ShugiinItvBaseIE):
    _VALID_URL = r'https?://(?:www\.)?shugiintv\.go\.jp/(?:jp|en)(?:/index\.php)?$'
    IE_DESC = '衆議院インターネット審議中継'

    _TESTS = [{
        'url': 'https://www.shugiintv.go.jp/jp/index.php',
        'info_dict': {
            '_type': 'playlist',
            'title': 'All proceedings for today',
        },
        # expect at least one proceedings is running
        'playlist_mincount': 1,
    }]

    @classmethod
    def suitable(cls, url):
        return super().suitable(url) and not any(x.suitable(url) for x in (ShugiinItvLiveRoomIE, ShugiinItvVodIE))

    def _real_extract(self, url):
        self.to_screen(
            'Downloading all running proceedings. To specify one proceeding, use direct link from the website')
        return self.playlist_result(self._fetch_rooms(), playlist_title='All proceedings for today')


class ShugiinItvLiveRoomIE(ShugiinItvBaseIE):
    _VALID_URL = r'https?://(?:www\.)?shugiintv\.go\.jp/(?:jp|en)/index\.php\?room_id=(?P<id>room\d+)'
    IE_DESC = '衆議院インターネット審議中継 (中継)'

    _TESTS = [{
        'url': 'https://www.shugiintv.go.jp/jp/index.php?room_id=room01',
        'info_dict': {
            'id': 'room01',
            'title': '内閣委員会',
        },
        'skip': 'this runs for a time and not every day',
    }, {
        'url': 'https://www.shugiintv.go.jp/jp/index.php?room_id=room11',
        'info_dict': {
            'id': 'room11',
            'title': '外務委員会',
        },
        'skip': 'this runs for a time and not every day',
    }]

    def _real_extract(self, url):
        url, smug = unsmuggle_url(url, default={})
        if smug.get('g'):
            room_id, title = smug['g']
        else:
            room_id = self._match_id(url)
            title = traverse_obj(self._fetch_rooms(), (lambda k, v: v['id'] == room_id, 'title'), get_all=False)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://hlslive.shugiintv.go.jp/{room_id}/amlst:{room_id}/playlist.m3u8',
            room_id, ext='mp4')

        return {
            'id': room_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': True,
        }


class ShugiinItvVodIE(ShugiinItvBaseIE):
    _VALID_URL = r'https?://(?:www\.)?shugiintv\.go\.jp/(?:jp|en)/index\.php\?ex=VL(?:\&[^=]+=[^&]*)*\&deli_id=(?P<id>\d+)'
    IE_DESC = '衆議院インターネット審議中継 (ビデオライブラリ)'
    _TESTS = [{
        'url': 'https://www.shugiintv.go.jp/jp/index.php?ex=VL&media_type=&deli_id=53846',
        'info_dict': {
            'id': '53846',
            'title': 'ウクライナ大統領国会演説（オンライン）',
            'release_date': '20220323',
            'chapters': 'count:4',
        },
    }, {
        'url': 'https://www.shugiintv.go.jp/en/index.php?ex=VL&media_type=&deli_id=53846',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            f'https://www.shugiintv.go.jp/jp/index.php?ex=VL&media_type=&deli_id={video_id}', video_id,
            encoding='euc-jp')

        m3u8_url = self._search_regex(
            r'id="vtag_src_base_vod"\s*value="(http.+?\.m3u8)"', webpage, 'm3u8 url')
        m3u8_url = re.sub(r'^http://', 'https://', m3u8_url)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, ext='mp4')

        title = self._html_search_regex(
            (r'<td\s+align="left">(.+)\s*\(\d+分\)',
             r'<TD.+?<IMG\s*src=".+?/spacer\.gif".+?height="15">(.+?)<IMG'), webpage, 'title', fatal=False)

        release_date = _parse_japanese_date(self._html_search_regex(
            r'開会日</td>\s*<td.+?/td>\s*<TD>(.+?)</TD>',
            webpage, 'title', fatal=False))

        chapters = []
        for chp in re.finditer(r'(?i)<A\s+HREF="([^"]+?)"\s*class="play_vod">(?!<img)(.+)</[Aa]>', webpage):
            chapters.append({
                'title': clean_html(chp.group(2)).strip(),
                'start_time': try_call(lambda: float(parse_qs(chp.group(1))['time'][0].strip())),
            })
        # NOTE: there are blanks at the first and the end of the videos,
        # so getting/providing the video duration is not possible
        # also, the exact end_time for the last chapter is unknown (we can get at most minutes of granularity)
        last_tr = re.findall(r'(?s)<TR\s*class="s14_24">(.+?)</TR>', webpage)[-1]
        if last_tr and chapters:
            last_td = re.findall(r'<TD.+?</TD>', last_tr)[-1]
            if last_td:
                chapters[-1]['end_time'] = chapters[-1]['start_time'] + _parse_japanese_duration(clean_html(last_td))

        return {
            'id': video_id,
            'title': title,
            'release_date': release_date,
            'chapters': chapters,
            'formats': formats,
            'subtitles': subtitles,
        }


class SangiinInstructionIE(InfoExtractor):
    _VALID_URL = r'https?://www\.webtv\.sangiin\.go\.jp/webtv/index\.php'
    IE_DESC = False  # this shouldn't be listed as a supported site

    def _real_extract(self, url):
        raise ExtractorError(
            'Copy the link from the button below the video description/player '
            'and use that link to download. If there is no button in the frame, '
            'get the URL of the frame showing the video.', expected=True)


class SangiinIE(InfoExtractor):
    _VALID_URL = r'https?://www\.webtv\.sangiin\.go\.jp/webtv/detail\.php\?sid=(?P<id>\d+)'
    IE_DESC = '参議院インターネット審議中継 (archive)'

    _TESTS = [{
        'url': 'https://www.webtv.sangiin.go.jp/webtv/detail.php?sid=7052',
        'info_dict': {
            'id': '7052',
            'title': '2022年10月7日 本会議',
            'description': 'md5:0a5fed523f95c88105a0b0bf1dd71489',
            'upload_date': '20221007',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.webtv.sangiin.go.jp/webtv/detail.php?sid=7037',
        'info_dict': {
            'id': '7037',
            'title': '2022年10月3日 開会式',
            'upload_date': '20221003',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.webtv.sangiin.go.jp/webtv/detail.php?sid=7076',
        'info_dict': {
            'id': '7076',
            'title': '2022年10月27日 法務委員会',
            'upload_date': '20221027',
            'ext': 'mp4',
            'is_live': True,
        },
        'skip': 'this live is turned into archive after it ends',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        date = self._html_search_regex(
            r'<dt[^>]*>\s*開会日\s*</dt>\s*<dd[^>]*>\s*(.+?)\s*</dd>', webpage,
            'date', fatal=False)
        upload_date = _parse_japanese_date(date)

        title = self._html_search_regex(
            r'<dt[^>]*>\s*会議名\s*</dt>\s*<dd[^>]*>\s*(.+?)\s*</dd>', webpage,
            'date', fatal=False)

        # some videos don't have the elements, so assume it's missing
        description = self._html_search_regex(
            r'会議の経過\s*</h3>\s*<span[^>]*>(.+?)</span>', webpage,
            'description', default=None)

        # this row appears only when it's livestream
        is_live = bool(self._html_search_regex(
            r'<dt[^>]*>\s*公報掲載時刻\s*</dt>\s*<dd[^>]*>\s*(.+?)\s*</dd>', webpage,
            'is_live', default=None))

        m3u8_url = self._search_regex(
            r'var\s+videopath\s*=\s*(["\'])([^"\']+)\1', webpage,
            'm3u8 url', group=2)

        formats, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, 'mp4')

        return {
            'id': video_id,
            'title': join_nonempty(date, title, delim=' '),
            'description': description,
            'upload_date': upload_date,
            'formats': formats,
            'subtitles': subs,
            'is_live': is_live,
        }
