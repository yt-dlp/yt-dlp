import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    filter_dict,
    get_element_by_class,
    int_or_none,
    join_nonempty,
    make_archive_id,
    orderedSet,
    parse_duration,
    remove_end,
    traverse_obj,
    try_call,
    unescapeHTML,
    unified_timestamp,
    url_or_none,
    urljoin,
    variadic,
)


class NhkBaseIE(InfoExtractor):
    _API_URL_TEMPLATE = 'https://nwapi.nhk.jp/nhkworld/%sod%slist/v7b/%s/%s/%s/all%s.json'
    _BASE_URL_REGEX = r'https?://www3\.nhk\.or\.jp/nhkworld/(?P<lang>[a-z]{2})/'

    def _call_api(self, m_id, lang, is_video, is_episode, is_clip):
        return self._download_json(
            self._API_URL_TEMPLATE % (
                'v' if is_video else 'r',
                'clip' if is_clip else 'esd',
                'episode' if is_episode else 'program',
                m_id, lang, '/all' if is_video else ''),
            m_id, query={'apikey': 'EJfK8jdS57GqlupFgAfAAwr573q01y6k'})['data']['episodes'] or []

    def _get_api_info(self, refresh=True):
        if not refresh:
            return self.cache.load('nhk', 'api_info')

        self.cache.store('nhk', 'api_info', {})
        movie_player_js = self._download_webpage(
            'https://movie-a.nhk.or.jp/world/player/js/movie-player.js', None,
            note='Downloading stream API information')
        api_info = {
            'url': self._search_regex(
                r'prod:[^;]+\bapiUrl:\s*[\'"]([^\'"]+)[\'"]', movie_player_js, None, 'stream API url'),
            'token': self._search_regex(
                r'prod:[^;]+\btoken:\s*[\'"]([^\'"]+)[\'"]', movie_player_js, None, 'stream API token'),
        }
        self.cache.store('nhk', 'api_info', api_info)
        return api_info

    def _extract_stream_info(self, vod_id):
        for refresh in (False, True):
            api_info = self._get_api_info(refresh)
            if not api_info:
                continue

            api_url = api_info.pop('url')
            meta = traverse_obj(
                self._download_json(
                    api_url, vod_id, 'Downloading stream url info', fatal=False, query={
                        **api_info,
                        'type': 'json',
                        'optional_id': vod_id,
                        'active_flg': 1,
                    }), ('meta', 0))
            stream_url = traverse_obj(
                meta, ('movie_url', ('mb_auto', 'auto_sp', 'auto_pc'), {url_or_none}), get_all=False)

            if stream_url:
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(stream_url, vod_id)
                return {
                    **traverse_obj(meta, {
                        'duration': ('duration', {int_or_none}),
                        'timestamp': ('publication_date', {unified_timestamp}),
                        'release_timestamp': ('insert_date', {unified_timestamp}),
                        'modified_timestamp': ('update_date', {unified_timestamp}),
                    }),
                    'formats': formats,
                    'subtitles': subtitles,
                }
        raise ExtractorError('Unable to extract stream url')

    def _extract_episode_info(self, url, episode=None):
        fetch_episode = episode is None
        lang, m_type, episode_id = NhkVodIE._match_valid_url(url).group('lang', 'type', 'id')
        is_video = m_type != 'audio'

        if is_video:
            episode_id = episode_id[:4] + '-' + episode_id[4:]

        if fetch_episode:
            episode = self._call_api(
                episode_id, lang, is_video, True, episode_id[:4] == '9999')[0]

        def get_clean_field(key):
            return clean_html(episode.get(key + '_clean') or episode.get(key))

        title = get_clean_field('sub_title')
        series = get_clean_field('title')

        thumbnails = []
        for s, w, h in [('', 640, 360), ('_l', 1280, 720)]:
            img_path = episode.get('image' + s)
            if not img_path:
                continue
            thumbnails.append({
                'id': f'{h}p',
                'height': h,
                'width': w,
                'url': 'https://www3.nhk.or.jp' + img_path,
            })

        episode_name = title
        if series and title:
            title = f'{series} - {title}'
        elif series and not title:
            title = series
            series = None
            episode_name = None
        else:  # title, no series
            episode_name = None

        info = {
            'id': episode_id + '-' + lang,
            'title': title,
            'description': get_clean_field('description'),
            'thumbnails': thumbnails,
            'series': series,
            'episode': episode_name,
        }

        if is_video:
            vod_id = episode['vod_id']
            info.update({
                **self._extract_stream_info(vod_id),
                'id': vod_id,
            })

        else:
            if fetch_episode:
                # From https://www3.nhk.or.jp/nhkworld/common/player/radio/inline/rod.html
                audio_path = remove_end(episode['audio']['audio'], '.m4a')
                info['formats'] = self._extract_m3u8_formats(
                    f'{urljoin("https://vod-stream.nhk.jp", audio_path)}/index.m3u8',
                    episode_id, 'm4a', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False)
                for f in info['formats']:
                    f['language'] = lang
            else:
                info.update({
                    '_type': 'url_transparent',
                    'ie_key': NhkVodIE.ie_key(),
                    'url': url,
                })
        return info


class NhkVodIE(NhkBaseIE):
    _VALID_URL = [
        rf'{NhkBaseIE._BASE_URL_REGEX}shows/(?:(?P<type>video)/)?(?P<id>\d{{4}}[\da-z]\d+)/?(?:$|[?#])',
        rf'{NhkBaseIE._BASE_URL_REGEX}(?:ondemand|shows)/(?P<type>audio)/(?P<id>[^/?#]+?-\d{{8}}-[\da-z]+)',
        rf'{NhkBaseIE._BASE_URL_REGEX}ondemand/(?P<type>video)/(?P<id>\d{{4}}[\da-z]\d+)',  # deprecated
    ]
    # Content available only for a limited period of time. Visit
    # https://www3.nhk.or.jp/nhkworld/en/ondemand/ for working samples.
    _TESTS = [{
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/2049126/',
        'info_dict': {
            'id': 'nw_vod_v_en_2049_126_20230413233000_01_1681398302',
            'ext': 'mp4',
            'title': 'Japan Railway Journal - The Tohoku Shinkansen: Full Speed Ahead',
            'description': 'md5:49f7c5b206e03868a2fdf0d0814b92f6',
            'thumbnail': r're:https://.+/.+\.jpg',
            'episode': 'The Tohoku Shinkansen: Full Speed Ahead',
            'series': 'Japan Railway Journal',
            'modified_timestamp': 1707217907,
            'timestamp': 1681428600,
            'release_timestamp': 1693883728,
            'duration': 1679,
            'upload_date': '20230413',
            'modified_date': '20240206',
            'release_date': '20230905',
        },
    }, {
        # video clip
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/9999011/',
        'md5': '153c3016dfd252ba09726588149cf0e7',
        'info_dict': {
            'id': 'lpZXIwaDE6_Z-976CPsFdxyICyWUzlT5',
            'ext': 'mp4',
            'title': 'Dining with the Chef - Chef Saito\'s Family recipe: MENCHI-KATSU',
            'description': 'md5:5aee4a9f9d81c26281862382103b0ea5',
            'thumbnail': r're:https://.+/.+\.jpg',
            'series': 'Dining with the Chef',
            'episode': 'Chef Saito\'s Family recipe: MENCHI-KATSU',
            'duration': 148,
            'upload_date': '20190816',
            'release_date': '20230902',
            'release_timestamp': 1693619292,
            'modified_timestamp': 1707217907,
            'modified_date': '20240206',
            'timestamp': 1565997540,
        },
    }, {
        # radio
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/audio/livinginjapan-20231001-1/',
        'info_dict': {
            'id': 'livinginjapan-20231001-1-en',
            'ext': 'm4a',
            'title': 'Living in Japan - Tips for Travelers to Japan / Ramen Vending Machines',
            'series': 'Living in Japan',
            'description': 'md5:0a0e2077d8f07a03071e990a6f51bfab',
            'thumbnail': r're:https://.+/.+\.jpg',
            'episode': 'Tips for Travelers to Japan / Ramen Vending Machines',
        },
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/2015173/',
        'only_matching': True,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/audio/plugin-20190404-1/',
        'only_matching': True,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/fr/ondemand/audio/plugin-20190404-1/',
        'only_matching': True,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/audio/j_art-20150903-1/',
        'only_matching': True,
    }, {
        # video, alphabetic character in ID #29670
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/9999a34/',
        'info_dict': {
            'id': 'qfjay6cg',
            'ext': 'mp4',
            'title': 'DESIGN TALKS plus - Fishermen’s Finery',
            'description': 'md5:8a8f958aaafb0d7cb59d38de53f1e448',
            'thumbnail': r're:^https?:/(/[a-z0-9.-]+)+\.jpg\?w=1920&h=1080$',
            'upload_date': '20210615',
            'timestamp': 1623722008,
        },
        'skip': '404 Not Found',
    }, {
        # japanese-language, longer id than english
        'url': 'https://www3.nhk.or.jp/nhkworld/ja/ondemand/video/0020271111/',
        'info_dict': {
            'id': 'nw_ja_v_jvod_ohayou_20231008',
            'ext': 'mp4',
            'title': 'おはよう日本（7時台） - 10月8日放送',
            'series': 'おはよう日本（7時台）',
            'episode': '10月8日放送',
            'thumbnail': r're:https://.+/.+\.jpg',
            'description': 'md5:9c1d6cbeadb827b955b20e99ab920ff0',
        },
        'skip': 'expires 2023-10-15',
    }, {
        # a one-off (single-episode series). title from the api is just '<p></p>'
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/3004952/',
        'info_dict': {
            'id': 'nw_vod_v_en_3004_952_20230723091000_01_1690074552',
            'ext': 'mp4',
            'title': 'Barakan Discovers - AMAMI OSHIMA: Isson\'s Treasure Isla',
            'description': 'md5:5db620c46a0698451cc59add8816b797',
            'thumbnail': r're:https://.+/.+\.jpg',
            'release_date': '20230905',
            'timestamp': 1690103400,
            'duration': 2939,
            'release_timestamp': 1693898699,
            'upload_date': '20230723',
            'modified_timestamp': 1707217907,
            'modified_date': '20240206',
            'episode': 'AMAMI OSHIMA: Isson\'s Treasure Isla',
            'series': 'Barakan Discovers',
        },
    }, {
        # /ondemand/video/ url with alphabetical character in 5th position of id
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/9999a07/',
        'info_dict': {
            'id': 'nw_c_en_9999-a07',
            'ext': 'mp4',
            'episode': 'Mini-Dramas on SDGs: Ep 1 Close the Gender Gap [Director\'s Cut]',
            'series': 'Mini-Dramas on SDGs',
            'modified_date': '20240206',
            'title': 'Mini-Dramas on SDGs - Mini-Dramas on SDGs: Ep 1 Close the Gender Gap [Director\'s Cut]',
            'description': 'md5:3f9dcb4db22fceb675d90448a040d3f6',
            'timestamp': 1621962360,
            'duration': 189,
            'release_date': '20230903',
            'modified_timestamp': 1707217907,
            'upload_date': '20210525',
            'thumbnail': r're:https://.+/.+\.jpg',
            'release_timestamp': 1693713487,
        },
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/9999d17/',
        'info_dict': {
            'id': 'nw_c_en_9999-d17',
            'ext': 'mp4',
            'title': 'Flowers of snow blossom - The 72 Pentads of Yamato',
            'description': 'Today’s focus: Snow',
            'release_timestamp': 1693792402,
            'release_date': '20230904',
            'upload_date': '20220128',
            'timestamp': 1643370960,
            'thumbnail': r're:https://.+/.+\.jpg',
            'duration': 136,
            'series': '',
            'modified_date': '20240206',
            'modified_timestamp': 1707217907,
        },
    }, {
        # new /shows/ url format
        'url': 'https://www3.nhk.or.jp/nhkworld/en/shows/2032307/',
        'info_dict': {
            'id': 'nw_vod_v_en_2032_307_20240321113000_01_1710990282',
            'ext': 'mp4',
            'title': 'Japanology Plus - 20th Anniversary Special Part 1',
            'description': 'md5:817d41fc8e54339ad2a916161ea24faf',
            'episode': '20th Anniversary Special Part 1',
            'series': 'Japanology Plus',
            'thumbnail': r're:https://.+/.+\.jpg',
            'duration': 1680,
            'timestamp': 1711020600,
            'upload_date': '20240321',
            'release_timestamp': 1711022683,
            'release_date': '20240321',
            'modified_timestamp': 1711031012,
            'modified_date': '20240321',
        },
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/shows/3020025/',
        'info_dict': {
            'id': 'nw_vod_v_en_3020_025_20230325144000_01_1679723944',
            'ext': 'mp4',
            'title': '100 Ideas to Save the World - Working Styles Evolve',
            'description': 'md5:9e6c7778eaaf4f7b4af83569649f84d9',
            'episode': 'Working Styles Evolve',
            'series': '100 Ideas to Save the World',
            'thumbnail': r're:https://.+/.+\.jpg',
            'duration': 899,
            'upload_date': '20230325',
            'timestamp': 1679755200,
            'release_date': '20230905',
            'release_timestamp': 1693880540,
            'modified_date': '20240206',
            'modified_timestamp': 1707217907,
        },
    }, {
        # new /shows/audio/ url format
        'url': 'https://www3.nhk.or.jp/nhkworld/en/shows/audio/livinginjapan-20231001-1/',
        'only_matching': True,
    }, {
        # valid url even if can't be found in wild; support needed for clip entries extraction
        'url': 'https://www3.nhk.or.jp/nhkworld/en/shows/9999o80/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._extract_episode_info(url)


class NhkVodProgramIE(NhkBaseIE):
    _VALID_URL = rf'''(?x)
        {NhkBaseIE._BASE_URL_REGEX}(?:shows|tv)/
        (?:(?P<type>audio)/programs/)?(?P<id>\w+)/?
        (?:\?(?:[^#]+&)?type=(?P<episode_type>clip|(?:radio|tv)Episode))?'''
    _TESTS = [{
        # video program episodes
        'url': 'https://www3.nhk.or.jp/nhkworld/en/shows/sumo/',
        'info_dict': {
            'id': 'sumo',
            'title': 'GRAND SUMO Highlights',
            'description': 'md5:fc20d02dc6ce85e4b72e0273aa52fdbf',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/shows/japanrailway/',
        'info_dict': {
            'id': 'japanrailway',
            'title': 'Japan Railway Journal',
            'description': 'md5:ea39d93af7d05835baadf10d1aae0e3f',
        },
        'playlist_mincount': 12,
    }, {
        # video program clips
        'url': 'https://www3.nhk.or.jp/nhkworld/en/shows/japanrailway/?type=clip',
        'info_dict': {
            'id': 'japanrailway',
            'title': 'Japan Railway Journal',
            'description': 'md5:ea39d93af7d05835baadf10d1aae0e3f',
        },
        'playlist_mincount': 12,
    }, {
        # audio program
        'url': 'https://www3.nhk.or.jp/nhkworld/en/shows/audio/programs/livinginjapan/',
        'info_dict': {
            'id': 'livinginjapan',
            'title': 'Living in Japan',
            'description': 'md5:665bb36ec2a12c5a7f598ee713fc2b54',
        },
        'playlist_mincount': 12,
    }, {
        # /tv/ program url
        'url': 'https://www3.nhk.or.jp/nhkworld/en/tv/designtalksplus/',
        'info_dict': {
            'id': 'designtalksplus',
            'title': 'DESIGN TALKS plus',
            'description': 'md5:47b3b3a9f10d4ac7b33b53b70a7d2837',
        },
        'playlist_mincount': 20,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/shows/10yearshayaomiyazaki/',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if NhkVodIE.suitable(url) else super().suitable(url)

    def _extract_meta_from_class_elements(self, class_values, html):
        for class_value in class_values:
            if value := clean_html(get_element_by_class(class_value, html)):
                return value

    def _real_extract(self, url):
        lang, m_type, program_id, episode_type = self._match_valid_url(url).group('lang', 'type', 'id', 'episode_type')
        episodes = self._call_api(
            program_id, lang, m_type != 'audio', False, episode_type == 'clip')

        def entries():
            for episode in episodes:
                if episode_path := episode.get('url'):
                    yield self._extract_episode_info(urljoin(url, episode_path), episode)

        html = self._download_webpage(url, program_id)
        program_title = self._extract_meta_from_class_elements([
            'p-programDetail__title',  # /ondemand/program/
            'pProgramHero__logoText',  # /shows/
            'tAudioProgramMain__title',  # /shows/audio/programs/
            'p-program-name'], html)  # /tv/
        program_description = self._extract_meta_from_class_elements([
            'p-programDetail__text',  # /ondemand/program/
            'pProgramHero__description',  # /shows/
            'tAudioProgramMain__info',  # /shows/audio/programs/
            'p-program-description'], html)  # /tv/

        return self.playlist_result(entries(), program_id, program_title, program_description)


class NhkForSchoolBangumiIE(InfoExtractor):
    _VALID_URL = r'https?://www2\.nhk\.or\.jp/school/movie/(?P<type>bangumi|clip)\.cgi\?das_id=(?P<id>[a-zA-Z0-9_-]+)'
    _TESTS = [{
        'url': 'https://www2.nhk.or.jp/school/movie/bangumi.cgi?das_id=D0005150191_00000',
        'info_dict': {
            'id': 'D0005150191_00003',
            'title': 'にている かな',
            'duration': 599.999,
            'timestamp': 1396414800,

            'upload_date': '20140402',
            'ext': 'mp4',

            'chapters': 'count:12',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        program_type, video_id = self._match_valid_url(url).groups()

        webpage = self._download_webpage(
            f'https://www2.nhk.or.jp/school/movie/{program_type}.cgi?das_id={video_id}', video_id)

        # searches all variables
        base_values = {g.group(1): g.group(2) for g in re.finditer(r'var\s+([a-zA-Z_]+)\s*=\s*"([^"]+?)";', webpage)}
        # and programObj values too
        program_values = {g.group(1): g.group(3) for g in re.finditer(r'(?:program|clip)Obj\.([a-zA-Z_]+)\s*=\s*(["\'])([^"]+?)\2;', webpage)}
        # extract all chapters
        chapter_durations = [parse_duration(g.group(1)) for g in re.finditer(r'chapterTime\.push\(\'([0-9:]+?)\'\);', webpage)]
        chapter_titles = [' '.join([g.group(1) or '', unescapeHTML(g.group(2))]).strip() for g in re.finditer(r'<div class="cpTitle"><span>(scene\s*\d+)?</span>([^<]+?)</div>', webpage)]

        # this is how player_core.js is actually doing (!)
        version = base_values.get('r_version') or program_values.get('version')
        if version:
            video_id = f'{video_id.split("_")[0]}_{version}'

        formats = self._extract_m3u8_formats(
            f'https://nhks-vh.akamaihd.net/i/das/{video_id[0:8]}/{video_id}_V_000.f4v/master.m3u8',
            video_id, ext='mp4', m3u8_id='hls')

        duration = parse_duration(base_values.get('r_duration'))

        chapters = None
        if chapter_durations and chapter_titles and len(chapter_durations) == len(chapter_titles):
            start_time = chapter_durations
            end_time = [*chapter_durations[1:], duration]
            chapters = [{
                'start_time': s,
                'end_time': e,
                'title': t,
            } for s, e, t in zip(start_time, end_time, chapter_titles)]

        return {
            'id': video_id,
            'title': program_values.get('name'),
            'duration': parse_duration(base_values.get('r_duration')),
            'timestamp': unified_timestamp(base_values['r_upload']),
            'formats': formats,
            'chapters': chapters,
        }


class NhkForSchoolSubjectIE(InfoExtractor):
    IE_DESC = 'Portal page for each school subjects, like Japanese (kokugo, 国語) or math (sansuu/suugaku or 算数・数学)'
    KNOWN_SUBJECTS = (
        'rika', 'syakai', 'kokugo',
        'sansuu', 'seikatsu', 'doutoku',
        'ongaku', 'taiiku', 'zukou',
        'gijutsu', 'katei', 'sougou',
        'eigo', 'tokkatsu',
        'tokushi', 'sonota',
    )
    _VALID_URL = r'https?://www\.nhk\.or\.jp/school/(?P<id>{})/?(?:[\?#].*)?$'.format(
        '|'.join(re.escape(s) for s in KNOWN_SUBJECTS))

    _TESTS = [{
        'url': 'https://www.nhk.or.jp/school/sougou/',
        'info_dict': {
            'id': 'sougou',
            'title': '総合的な学習の時間',
        },
        'playlist_mincount': 16,
    }, {
        'url': 'https://www.nhk.or.jp/school/rika/',
        'info_dict': {
            'id': 'rika',
            'title': '理科',
        },
        'playlist_mincount': 15,
    }]

    def _real_extract(self, url):
        subject_id = self._match_id(url)
        webpage = self._download_webpage(url, subject_id)

        return self.playlist_from_matches(
            re.finditer(rf'href="((?:https?://www\.nhk\.or\.jp)?/school/{re.escape(subject_id)}/[^/]+/)"', webpage),
            subject_id,
            self._html_search_regex(r'(?s)<span\s+class="subjectName">\s*<img\s*[^<]+>\s*([^<]+?)</span>', webpage, 'title', fatal=False),
            lambda g: urljoin(url, g.group(1)))


class NhkForSchoolProgramListIE(InfoExtractor):
    _VALID_URL = r'https?://www\.nhk\.or\.jp/school/(?P<id>(?:{})/[a-zA-Z0-9_-]+)'.format(
        '|'.join(re.escape(s) for s in NhkForSchoolSubjectIE.KNOWN_SUBJECTS))
    _TESTS = [{
        'url': 'https://www.nhk.or.jp/school/sougou/q/',
        'info_dict': {
            'id': 'sougou/q',
            'title': 'Ｑ～こどものための哲学',
        },
        'playlist_mincount': 20,
    }]

    def _real_extract(self, url):
        program_id = self._match_id(url)

        webpage = self._download_webpage(f'https://www.nhk.or.jp/school/{program_id}/', program_id)

        title = (self._generic_title('', webpage)
                 or self._html_search_regex(r'<h3>([^<]+?)とは？\s*</h3>', webpage, 'title', fatal=False))
        title = re.sub(r'\s*\|\s*NHK\s+for\s+School\s*$', '', title) if title else None
        description = self._html_search_regex(
            r'(?s)<div\s+class="programDetail\s*">\s*<p>[^<]+</p>',
            webpage, 'description', fatal=False, group=0)

        bangumi_list = self._download_json(
            f'https://www.nhk.or.jp/school/{program_id}/meta/program.json', program_id)
        # they're always bangumi
        bangumis = [
            self.url_result(f'https://www2.nhk.or.jp/school/movie/bangumi.cgi?das_id={x}')
            for x in traverse_obj(bangumi_list, ('part', ..., 'part-video-dasid')) or []]

        return self.playlist_result(bangumis, program_id, title, description)


class NhkRadiruIE(InfoExtractor):
    _GEO_COUNTRIES = ['JP']
    IE_DESC = 'NHK らじる (Radiru/Rajiru)'
    _VALID_URL = r'https?://www\.nhk\.or\.jp/radio/(?:player/ondemand|ondemand/detail)\.html\?p=(?P<site>[\da-zA-Z]+)_(?P<corner>[\da-zA-Z]+)(?:_(?P<headline>[\da-zA-Z]+))?'
    _TESTS = [{
        'url': 'https://www.nhk.or.jp/radio/player/ondemand.html?p=LG96ZW5KZ4_01_4251382',
        'skip': 'Episode expires on 2025-07-14',
        'info_dict': {
            'title': 'クラシックの庭\u3000特集「ドボルザークを聴く」（１）交響曲を中心に',
            'id': 'LG96ZW5KZ4_01_4251382',
            'ext': 'm4a',
            'description': 'md5:652d3c38a25b77959c716421eba1617a',
            'uploader': 'NHK FM・東京',
            'channel': 'NHK FM・東京',
            'duration': 6597.0,
            'thumbnail': 'https://www.nhk.jp/static/assets/images/radioseries/rs/LG96ZW5KZ4/LG96ZW5KZ4-eyecatch_a67c6e949325016c0724f2ed3eec8a2f.jpg',
            'categories': ['音楽', 'クラシック・オペラ'],
            'cast': ['田添菜穂子'],
            'series': 'クラシックの庭',
            'series_id': 'LG96ZW5KZ4',
            'episode': '特集「ドボルザークを聴く」(1)交響曲を中心に',
            'episode_id': 'QP1Q2ZXZY3',
            'timestamp': 1751871000,
            'upload_date': '20250707',
            'release_timestamp': 1751864403,
            'release_date': '20250707',
        },
    }, {
        # playlist, airs every weekday so it should _hopefully_ be okay forever
        'url': 'https://www.nhk.or.jp/radio/ondemand/detail.html?p=Z9L1V2M24L_01',
        'info_dict': {
            'id': 'Z9L1V2M24L_01',
            'title': 'ベストオブクラシック',
            'description': '世界中の上質な演奏会をじっくり堪能する本格派クラシック番組。',
            'thumbnail': 'https://www.nhk.jp/static/assets/images/radioseries/rs/Z9L1V2M24L/Z9L1V2M24L-eyecatch_83ed28b4782907998875965fee60a351.jpg',
            'series_id': 'Z9L1V2M24L_01',
            'uploader': 'NHK FM',
            'channel': 'NHK FM',
            'series': 'ベストオブクラシック',
        },
        'playlist_mincount': 3,
    }, {
        # news
        'url': 'https://www.nhk.or.jp/radio/player/ondemand.html?p=18439M2W42_02_4251212',
        'skip': 'Expires on 2025-07-15',
        'info_dict': {
            'id': '18439M2W42_02_4251212',
            'ext': 'm4a',
            'title': 'マイあさ! 午前5時のNHKニュース 2025年7月8日',
            'uploader': 'NHKラジオ第1',
            'channel': 'NHKラジオ第1',
            'thumbnail': 'https://www.nhk.or.jp/radioondemand/json/18439M2W42/img/series_945_thumbnail.jpg',
            'series': 'NHKラジオニュース',
            'timestamp': 1751919420,
            'upload_date': '20250707',
            'release_timestamp': 1751918400,
            'release_date': '20250707',
        },
    }, {
        # fallback when extended metadata fails
        'url': 'https://www.nhk.or.jp/radio/player/ondemand.html?p=J8792PY43V_20_4253945',
        'skip': 'Expires on 2025-09-01',
        'info_dict': {
            'id': 'J8792PY43V_20_4253945',
            'ext': 'm4a',
            'title': '「後絶たない筋肉増強剤の使用」ワールドリポート',
            'description': '大濱 敦（ソウル支局）',
            'uploader': 'NHK R1',
            'channel': 'NHK R1',
            'thumbnail': 'https://www.nhk.or.jp/radioondemand/json/J8792PY43V/img/corner/box_31_thumbnail.jpg',
            'series': 'マイあさ！ ワールドリポート',
            'series_id': 'J8792PY43V_20',
            'timestamp': 1751837100,
            'upload_date': '20250706',
            'release_timestamp': 1751835600,
            'release_date': '20250706',

        },
        'expected_warnings': ['Failed to download extended metadata: HTTP Error 404: Not Found'],
    }]

    _API_URL_TMPL = None

    # The `_format_*` and `_make_*` functions are ported from: https://www.nhk.or.jp/radio/assets/js/timetable_detail_new.js

    def _format_act_list(self, act_list):
        role_groups = {}
        for act in traverse_obj(act_list, (..., {dict})):
            role = act.get('role')
            if role not in role_groups:
                role_groups[role] = []
            role_groups[role].append(act)

        formatted_roles = []
        for role, acts in role_groups.items():
            for i, act in enumerate(acts):
                res = f'【{role}】' if i == 0 and role is not None else ''
                if title := act.get('title'):
                    res += f'{title}…'
                formatted_roles.append(join_nonempty(res, act.get('name'), delim=''))
        return join_nonempty(*formatted_roles, delim='，')

    def _make_artists(self, track, key):
        artists = []
        for artist in traverse_obj(track, (key, ..., {dict})):
            if res := join_nonempty(*traverse_obj(artist, ((
                ('role', filter, {'{}…'.format}),
                ('part', filter, {'（{}）'.format}),
                ('name', filter),
            ), {str})), delim=''):
                artists.append(res)

        return '、'.join(artists) or None

    def _make_duration(self, track, key):
        d = traverse_obj(track, (key, {parse_duration}))
        if d is None:
            return None
        hours, remainder = divmod(d, 3600)
        minutes, seconds = divmod(remainder, 60)
        res = '（'
        if hours > 0:
            res += f'{int(hours)}時間'
        if minutes > 0:
            res += f'{int(minutes)}分'
        res += f'{int(seconds):02}秒）'
        return res

    def _format_music_list(self, music_list):
        tracks = []
        for track in traverse_obj(music_list, (..., {dict})):
            track_details = traverse_obj(track, ((
                ('name', filter, {'「{}」'.format}),
                ('lyricist', filter, {'{}:作詞'.format}),
                ('composer', filter, {'{}:作曲'.format}),
                ('arranger', filter, {'{}:編曲'.format}),
            ), {str}))

            track_details.append(self._make_artists(track, 'byArtist'))
            track_details.append(self._make_duration(track, 'duration'))

            if label := join_nonempty('label', 'code', delim=' ', from_dict=track):
                track_details.append(f'＜{label}＞')
            if location := traverse_obj(track, ('location', {str})):
                track_details.append(f'～{location}～')
            tracks.append(join_nonempty(*track_details, delim='\n'))
        return '\n\n'.join(tracks)

    def _format_description(self, response):
        detailed_description = traverse_obj(response, ('detailedDescription', {dict})) or {}
        return join_nonempty(
            join_nonempty('epg80', 'epg200', delim='\n\n', from_dict=detailed_description),
            traverse_obj(response, ('misc', 'actList', {self._format_act_list})),
            traverse_obj(response, ('misc', 'musicList', {self._format_music_list})),
            delim='\n\n')

    def _get_thumbnails(self, data, keys, name=None, preference=-1):
        thumbnails = []
        for size, thumb in traverse_obj(data, (
            *variadic(keys, (str, bytes, dict, set)), {dict.items},
            lambda _, v: v[0] != 'copyright' and url_or_none(v[1]['url']),
        )):
            thumbnails.append({
                'url': thumb['url'],
                'width': int_or_none(thumb.get('width')),
                'height': int_or_none(thumb.get('height')),
                'preference': preference,
                'id': join_nonempty(name, size),
            })
            preference -= 1
        return thumbnails

    def _extract_extended_metadata(self, episode_id, aa_vinfo):
        service, _, area = traverse_obj(aa_vinfo, (2, {str}, {lambda x: (x or '').partition(',')}))
        date_id = aa_vinfo[3]

        detail_url = try_call(
            lambda: self._API_URL_TMPL.format(broadcastEventId=join_nonempty(service, area, date_id)))
        if not detail_url:
            return {}

        response = self._download_json(
            detail_url, episode_id, 'Downloading extended metadata',
            'Failed to download extended metadata', fatal=False, expected_status=400)
        if not response:
            return {}

        if error := traverse_obj(response, ('error', {dict})):
            self.report_warning(
                'Failed to get extended metadata. API returned '
                f'Error {join_nonempty("statuscode", "message", from_dict=error, delim=": ")}')
            return {}

        station = traverse_obj(response, ('publishedOn', 'broadcastDisplayName', {str}))

        thumbnails = []
        thumbnails.extend(self._get_thumbnails(response, ('about', 'eyecatch')))
        for num, dct in enumerate(traverse_obj(response, ('about', 'eyecatchList', ...))):
            thumbnails.extend(self._get_thumbnails(dct, None, join_nonempty('list', num), -2))
        thumbnails.extend(
            self._get_thumbnails(response, ('about', 'partOfSeries', 'eyecatch'), 'series', -3))

        return filter_dict({
            'description': self._format_description(response),
            'cast': traverse_obj(response, ('misc', 'actList', ..., 'name', {str})),
            'thumbnails': thumbnails,
            **traverse_obj(response, {
                'title': ('name', {str}),
                'timestamp': ('endDate', {unified_timestamp}),
                'release_timestamp': ('startDate', {unified_timestamp}),
                'duration': ('duration', {parse_duration}),
            }),
            **traverse_obj(response, ('identifierGroup', {
                'series': ('radioSeriesName', {str}),
                'series_id': ('radioSeriesId', {str}),
                'episode': ('radioEpisodeName', {str}),
                'episode_id': ('radioEpisodeId', {str}),
                'categories': ('genre', ..., ['name1', 'name2'], {str}, all, {orderedSet}),
            })),
            'channel': station,
            'uploader': station,
        })

    def _extract_episode_info(self, episode, programme_id, series_meta):
        episode_id = f'{programme_id}_{episode["id"]}'
        aa_vinfo = traverse_obj(episode, ('aa_contents_id', {lambda x: x.split(';')}))
        extended_metadata = self._extract_extended_metadata(episode_id, aa_vinfo)
        fallback_start_time, _, fallback_end_time = traverse_obj(
            aa_vinfo, (4, {str}, {lambda x: (x or '').partition('_')}))

        return {
            **series_meta,
            'id': episode_id,
            'formats': self._extract_m3u8_formats(episode.get('stream_url'), episode_id, fatal=False),
            'container': 'm4a_dash',  # force fixup, AAC-only HLS
            'was_live': True,
            'title': episode.get('program_title'),
            'description': episode.get('program_sub_title'),  # fallback
            'timestamp': unified_timestamp(fallback_end_time),
            'release_timestamp': unified_timestamp(fallback_start_time),
            **extended_metadata,
        }

    def _extract_news_info(self, headline, programme_id, series_meta):
        episode_id = f'{programme_id}_{headline["headline_id"]}'
        episode = traverse_obj(headline, ('file_list', 0, {dict}))

        return {
            **series_meta,
            'id': episode_id,
            'formats': self._extract_m3u8_formats(episode.get('file_name'), episode_id, fatal=False),
            'container': 'm4a_dash',  # force fixup, AAC-only HLS
            'was_live': True,
            'series': series_meta.get('title'),
            'thumbnail': url_or_none(headline.get('headline_image')) or series_meta.get('thumbnail'),
            **traverse_obj(episode, {
                'title': ('file_title', {str}),
                'description': ('file_title_sub', {str}),
                'timestamp': ('open_time', {unified_timestamp}),
                'release_timestamp': ('aa_vinfo4', {lambda x: x.split('_')[0]}, {unified_timestamp}),
            }),
        }

    def _real_initialize(self):
        if self._API_URL_TMPL:
            return
        api_config = self._download_xml(
            'https://www.nhk.or.jp/radio/config/config_web.xml', None, 'Downloading API config', fatal=False)
        NhkRadiruIE._API_URL_TMPL = try_call(lambda: f'https:{api_config.find(".//url_program_detail").text}')

    def _real_extract(self, url):
        site_id, corner_id, headline_id = self._match_valid_url(url).group('site', 'corner', 'headline')
        programme_id = f'{site_id}_{corner_id}'

        # XXX: News programmes use the old API
        # Can't move this to NhkRadioNewsPageIE because news items still use the normal URL format
        if site_id == '18439M2W42':
            meta = self._download_json(
                'https://www.nhk.or.jp/s-media/news/news-site/list/v1/all.json', programme_id)['main']
            series_meta = traverse_obj(meta, {
                'title': ('program_name', {str}),
                'channel': ('media_name', {str}),
                'uploader': ('media_name', {str}),
                'thumbnail': (('thumbnail_c', 'thumbnail_p'), {url_or_none}),
            }, get_all=False)

            if headline_id:
                headline = traverse_obj(
                    meta, ('detail_list', lambda _, v: v['headline_id'] == headline_id, any))
                if not headline:
                    raise ExtractorError('Content not found; it has most likely expired', expected=True)
                return self._extract_news_info(headline, programme_id, series_meta)

            def news_entries():
                for headline in traverse_obj(meta, ('detail_list', ..., {dict})):
                    yield self._extract_news_info(headline, programme_id, series_meta)

            return self.playlist_result(
                news_entries(), programme_id, description=meta.get('site_detail'), **series_meta)

        meta = self._download_json(
            'https://www.nhk.or.jp/radio-api/app/v1/web/ondemand/series', programme_id, query={
                'site_id': site_id,
                'corner_site_id': corner_id,
            })

        fallback_station = join_nonempty('NHK', traverse_obj(meta, ('radio_broadcast', {str})), delim=' ')
        series_meta = {
            'series': join_nonempty('title', 'corner_name', delim=' ', from_dict=meta),
            'series_id': programme_id,
            'thumbnail': traverse_obj(meta, ('thumbnail_url', {url_or_none})),
            'channel': fallback_station,
            'uploader': fallback_station,
        }

        if headline_id:
            episode = traverse_obj(meta, ('episodes', lambda _, v: v['id'] == int(headline_id), any))
            if not episode:
                raise ExtractorError('Content not found; it has most likely expired', expected=True)
            return self._extract_episode_info(episode, programme_id, series_meta)

        def entries():
            for episode in traverse_obj(meta, ('episodes', ..., {dict})):
                yield self._extract_episode_info(episode, programme_id, series_meta)

        return self.playlist_result(
            entries(), programme_id, title=series_meta.get('series'),
            description=meta.get('series_description'), **series_meta)


class NhkRadioNewsPageIE(InfoExtractor):
    _VALID_URL = r'https?://www\.nhk\.or\.jp/radionews/?(?:$|[?#])'
    _TESTS = [{
        # airs daily, on-the-hour most hours
        'url': 'https://www.nhk.or.jp/radionews/',
        'playlist_mincount': 5,
        'info_dict': {
            'id': '18439M2W42_01',
            'thumbnail': 'https://www.nhk.or.jp/radioondemand/json/18439M2W42/img/series_945_thumbnail.jpg',
            'description': 'md5:bf2c5b397e44bc7eb26de98d8f15d79d',
            'channel': 'NHKラジオ第1',
            'uploader': 'NHKラジオ第1',
            'title': 'NHKラジオニュース',
        },
    }]

    def _real_extract(self, url):
        return self.url_result('https://www.nhk.or.jp/radio/ondemand/detail.html?p=18439M2W42_01', NhkRadiruIE)


class NhkRadiruLiveIE(InfoExtractor):
    _GEO_COUNTRIES = ['JP']
    _VALID_URL = r'https?://www\.nhk\.or\.jp/radio/player/\?ch=(?P<id>r[12]|fm)'
    _TESTS = [{
        # radio 1, no area specified
        'url': 'https://www.nhk.or.jp/radio/player/?ch=r1',
        'info_dict': {
            'id': 'bs-r1-130',
            'title': 're:^NHKラジオ第1・東京.+$',
            'ext': 'm4a',
            'thumbnail': 'https://www.nhk.jp/assets/images/broadcastservice/bs/r1/r1-logo.svg',
            'live_status': 'is_live',
            '_old_archive_ids': ['nhkradirulive r1-tokyo'],
        },
    }, {
        # radio 2, area specified
        # (the area doesnt actually matter, r2 is national)
        'url': 'https://www.nhk.or.jp/radio/player/?ch=r2',
        'params': {'extractor_args': {'nhkradirulive': {'area': ['fukuoka']}}},
        'info_dict': {
            'id': 'bs-r2-400',
            'title': 're:^NHKラジオ第2.+$',
            'ext': 'm4a',
            'thumbnail': 'https://www.nhk.jp/assets/images/broadcastservice/bs/r2/r2-logo.svg',
            'live_status': 'is_live',
            '_old_archive_ids': ['nhkradirulive r2-fukuoka'],
        },
    }, {
        # fm, area specified
        'url': 'https://www.nhk.or.jp/radio/player/?ch=fm',
        'params': {'extractor_args': {'nhkradirulive': {'area': ['sapporo']}}},
        'info_dict': {
            'id': 'bs-r3-010',
            'title': 're:^NHK FM・札幌.+$',
            'ext': 'm4a',
            'thumbnail': 'https://www.nhk.jp/assets/images/broadcastservice/bs/r3/r3-logo.svg',
            'live_status': 'is_live',
            '_old_archive_ids': ['nhkradirulive fm-sapporo'],
        },
    }]

    _NOA_STATION_IDS = {'r1': 'r1', 'r2': 'r2', 'fm': 'r3'}

    def _real_extract(self, url):
        station = self._match_id(url)
        area = self._configuration_arg('area', ['tokyo'])[0]

        config = self._download_xml(
            'https://www.nhk.or.jp/radio/config/config_web.xml', station, 'Downloading area information')
        data = config.find(f'.//data//area[.="{area}"]/..')

        if not data:
            raise ExtractorError('Invalid area. Valid areas are: {}'.format(', '.join(
                [i.text for i in config.findall('.//data//area')])), expected=True)

        noa_info = self._download_json(
            f'https:{config.find(".//url_program_noa").text}'.format(area=data.find('areakey').text),
            station, note=f'Downloading {area} station metadata', fatal=False)
        broadcast_service = traverse_obj(noa_info, (self._NOA_STATION_IDS.get(station), 'publishedOn'))

        return {
            **traverse_obj(broadcast_service, {
                'title': ('broadcastDisplayName', {str}),
                'id': ('id', {str}),
            }),
            '_old_archive_ids': [make_archive_id(self, join_nonempty(station, area))],
            'thumbnails': traverse_obj(broadcast_service, ('logo', ..., {
                'url': 'url',
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
            })),
            'formats': self._extract_m3u8_formats(data.find(f'{station}hls').text, station),
            'is_live': True,
        }
