import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    parse_duration,
    traverse_obj,
    unescapeHTML,
    unified_timestamp,
    url_or_none,
    urljoin,
)


class NhkBaseIE(InfoExtractor):
    _API_URL_TEMPLATE = 'https://nwapi.nhk.jp/nhkworld/%sod%slist/v7b/%s/%s/%s/all%s.json'
    _BASE_URL_REGEX = r'https?://www3\.nhk\.or\.jp/nhkworld/(?P<lang>[a-z]{2})/ondemand'
    _TYPE_REGEX = r'/(?P<type>video|audio)/'

    def _call_api(self, m_id, lang, is_video, is_episode, is_clip):
        return self._download_json(
            self._API_URL_TEMPLATE % (
                'v' if is_video else 'r',
                'clip' if is_clip else 'esd',
                'episode' if is_episode else 'program',
                m_id, lang, '/all' if is_video else ''),
            m_id, query={'apikey': 'EJfK8jdS57GqlupFgAfAAwr573q01y6k'})['data']['episodes'] or []

    def _extract_episode_info(self, url, episode=None):
        fetch_episode = episode is None
        lang, m_type, episode_id = NhkVodIE._match_valid_url(url).groups()
        if len(episode_id) == 7:
            episode_id = episode_id[:4] + '-' + episode_id[4:]

        is_video = m_type == 'video'
        if fetch_episode:
            episode = self._call_api(
                episode_id, lang, is_video, True, episode_id[:4] == '9999')[0]
        title = episode.get('sub_title_clean') or episode['sub_title']

        def get_clean_field(key):
            return episode.get(key + '_clean') or episode.get(key)

        series = get_clean_field('title')

        thumbnails = []
        for s, w, h in [('', 640, 360), ('_l', 1280, 720)]:
            img_path = episode.get('image' + s)
            if not img_path:
                continue
            thumbnails.append({
                'id': '%dp' % h,
                'height': h,
                'width': w,
                'url': 'https://www3.nhk.or.jp' + img_path,
            })

        info = {
            'id': episode_id + '-' + lang,
            'title': '%s - %s' % (series, title) if series and title else title,
            'description': get_clean_field('description'),
            'thumbnails': thumbnails,
            'series': series,
            'episode': title,
        }
        if is_video:
            vod_id = episode['vod_id']
            info.update({
                '_type': 'url_transparent',
                'ie_key': 'Piksel',
                'url': 'https://movie-s.nhk.or.jp/v/refid/nhkworld/prefid/' + vod_id,
                'id': vod_id,
            })
        else:
            if fetch_episode:
                audio_path = episode['audio']['audio']
                info['formats'] = self._extract_m3u8_formats(
                    'https://nhkworld-vh.akamaihd.net/i%s/master.m3u8' % audio_path,
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
    # the 7-character IDs can have alphabetic chars too: assume [a-z] rather than just [a-f], eg
    _VALID_URL = r'%s%s(?P<id>[0-9a-z]{7}|[^/]+?-\d{8}-[0-9a-z]+)' % (NhkBaseIE._BASE_URL_REGEX, NhkBaseIE._TYPE_REGEX)
    # Content available only for a limited period of time. Visit
    # https://www3.nhk.or.jp/nhkworld/en/ondemand/ for working samples.
    _TESTS = [{
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/2061601/',
        'info_dict': {
            'id': 'yd8322ch',
            'ext': 'mp4',
            'description': 'md5:109c8b05d67a62d0592f2b445d2cd898',
            'title': 'GRAND SUMO Highlights - [Recap] May Tournament Day 1 (Opening Day)',
            'upload_date': '20230514',
            'timestamp': 1684083791,
            'series': 'GRAND SUMO Highlights',
            'episode': '[Recap] May Tournament Day 1 (Opening Day)',
            'thumbnail': 'https://mz-edge.stream.co.jp/thumbs/aid/t1684084443/4028649.jpg?w=1920&h=1080',
        },
    }, {
        # video clip
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/9999011/',
        'md5': '7a90abcfe610ec22a6bfe15bd46b30ca',
        'info_dict': {
            'id': 'a95j5iza',
            'ext': 'mp4',
            'title': "Dining with the Chef - Chef Saito's Family recipe: MENCHI-KATSU",
            'description': 'md5:5aee4a9f9d81c26281862382103b0ea5',
            'timestamp': 1565965194,
            'upload_date': '20190816',
            'thumbnail': 'https://mz-edge.stream.co.jp/thumbs/aid/t1567086278/3715195.jpg?w=1920&h=1080',
            'series': 'Dining with the Chef',
            'episode': 'Chef Saito\'s Family recipe: MENCHI-KATSU',
        },
    }, {
        # audio clip
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/audio/r_inventions-20201104-1/',
        'info_dict': {
            'id': 'r_inventions-20201104-1-en',
            'ext': 'm4a',
            'title': "Japan's Top Inventions - Miniature Video Cameras",
            'description': 'md5:07ea722bdbbb4936fdd360b6a480c25b',
        },
        'skip': '404 Not Found',
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
    }]

    def _real_extract(self, url):
        return self._extract_episode_info(url)


class NhkVodProgramIE(NhkBaseIE):
    _VALID_URL = r'%s/program%s(?P<id>[0-9a-z]+)(?:.+?\btype=(?P<episode_type>clip|(?:radio|tv)Episode))?' % (NhkBaseIE._BASE_URL_REGEX, NhkBaseIE._TYPE_REGEX)
    _TESTS = [{
        # video program episodes
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/program/video/sumo',
        'info_dict': {
            'id': 'sumo',
            'title': 'GRAND SUMO Highlights',
        },
        'playlist_mincount': 12,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/program/video/japanrailway',
        'info_dict': {
            'id': 'japanrailway',
            'title': 'Japan Railway Journal',
        },
        'playlist_mincount': 12,
    }, {
        # video program clips
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/program/video/japanrailway/?type=clip',
        'info_dict': {
            'id': 'japanrailway',
            'title': 'Japan Railway Journal',
        },
        'playlist_mincount': 5,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/program/video/10yearshayaomiyazaki/',
        'only_matching': True,
    }, {
        # audio program
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/program/audio/listener/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lang, m_type, program_id, episode_type = self._match_valid_url(url).groups()

        episodes = self._call_api(
            program_id, lang, m_type == 'video', False, episode_type == 'clip')

        entries = []
        for episode in episodes:
            episode_path = episode.get('url')
            if not episode_path:
                continue
            entries.append(self._extract_episode_info(
                urljoin(url, episode_path), episode))

        program_title = None
        if entries:
            program_title = entries[0].get('series')

        return self.playlist_result(entries, program_id, program_title)


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

            'chapters': 'count:12'
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
            end_time = chapter_durations[1:] + [duration]
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
    _VALID_URL = r'https?://www\.nhk\.or\.jp/school/(?P<id>%s)/?(?:[\?#].*)?$' % '|'.join(re.escape(s) for s in KNOWN_SUBJECTS)

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
    _VALID_URL = r'https?://www\.nhk\.or\.jp/school/(?P<id>(?:%s)/[a-zA-Z0-9_-]+)' % (
        '|'.join(re.escape(s) for s in NhkForSchoolSubjectIE.KNOWN_SUBJECTS)
    )
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
        'url': 'https://www.nhk.or.jp/radio/player/ondemand.html?p=0449_01_3853544',
        'skip': 'Episode expired on 2023-04-16',
        'info_dict': {
            'channel': 'NHK-FM',
            'description': 'md5:94b08bdeadde81a97df4ec882acce3e9',
            'ext': 'm4a',
            'id': '0449_01_3853544',
            'series': 'ジャズ・トゥナイト',
            'thumbnail': 'https://www.nhk.or.jp/prog/img/449/g449.jpg',
            'timestamp': 1680969600,
            'title': 'ジャズ・トゥナイト　ＮＥＷジャズ特集',
            'upload_date': '20230408',
            'release_timestamp': 1680962400,
            'release_date': '20230408',
            'was_live': True,
        },
    }, {
        # playlist, airs every weekday so it should _hopefully_ be okay forever
        'url': 'https://www.nhk.or.jp/radio/ondemand/detail.html?p=0458_01',
        'info_dict': {
            'id': '0458_01',
            'title': 'ベストオブクラシック',
            'description': '世界中の上質な演奏会をじっくり堪能する本格派クラシック番組。',
            'channel': 'NHK-FM',
            'thumbnail': 'https://www.nhk.or.jp/prog/img/458/g458.jpg',
        },
        'playlist_mincount': 3,
    }, {
        # one with letters in the id
        'url': 'https://www.nhk.or.jp/radio/player/ondemand.html?p=F300_06_3738470',
        'note': 'Expires on 2024-03-31',
        'info_dict': {
            'id': 'F300_06_3738470',
            'ext': 'm4a',
            'title': '有島武郎「一房のぶどう」',
            'description': '朗読：川野一宇（ラジオ深夜便アンカー）\r\n\r\n（2016年12月8日放送「ラジオ深夜便『アンカー朗読シリーズ』」より）',
            'channel': 'NHKラジオ第1、NHK-FM',
            'timestamp': 1635757200,
            'thumbnail': 'https://www.nhk.or.jp/radioondemand/json/F300/img/corner/box_109_thumbnail.jpg',
            'release_date': '20161207',
            'series': 'らじる文庫 by ラジオ深夜便 ',
            'release_timestamp': 1481126700,
            'upload_date': '20211101',
        }
    }, {
        # news
        'url': 'https://www.nhk.or.jp/radio/player/ondemand.html?p=F261_01_3855109',
        'skip': 'Expires on 2023-04-17',
        'info_dict': {
            'id': 'F261_01_3855109',
            'ext': 'm4a',
            'channel': 'NHKラジオ第1',
            'timestamp': 1681635900,
            'release_date': '20230416',
            'series': 'NHKラジオニュース',
            'title': '午後６時のNHKニュース',
            'thumbnail': 'https://www.nhk.or.jp/radioondemand/json/F261/img/RADIONEWS_640.jpg',
            'upload_date': '20230416',
            'release_timestamp': 1681635600,
        },
    }]

    def _extract_episode_info(self, headline, programme_id, series_meta):
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
                'title': 'file_title',
                'description': 'file_title_sub',
                'timestamp': ('open_time', {unified_timestamp}),
                'release_timestamp': ('aa_vinfo4', {lambda x: x.split('_')[0]}, {unified_timestamp}),
            }),
        }

    def _real_extract(self, url):
        site_id, corner_id, headline_id = self._match_valid_url(url).group('site', 'corner', 'headline')
        programme_id = f'{site_id}_{corner_id}'

        if site_id == 'F261':
            json_url = 'https://www.nhk.or.jp/s-media/news/news-site/list/v1/all.json'
        else:
            json_url = f'https://www.nhk.or.jp/radioondemand/json/{site_id}/bangumi_{programme_id}.json'

        meta = self._download_json(json_url, programme_id)['main']

        series_meta = traverse_obj(meta, {
            'title': 'program_name',
            'channel': 'media_name',
            'thumbnail': (('thumbnail_c', 'thumbnail_p'), {url_or_none}),
        }, get_all=False)

        if headline_id:
            return self._extract_episode_info(
                traverse_obj(meta, (
                    'detail_list', lambda _, v: v['headline_id'] == headline_id), get_all=False),
                programme_id, series_meta)

        def entries():
            for headline in traverse_obj(meta, ('detail_list', ..., {dict})):
                yield self._extract_episode_info(headline, programme_id, series_meta)

        return self.playlist_result(
            entries(), programme_id, playlist_description=meta.get('site_detail'), **series_meta)


class NhkRadioNewsPageIE(InfoExtractor):
    _VALID_URL = r'https?://www\.nhk\.or\.jp/radionews/?(?:$|[?#])'
    _TESTS = [{
        # airs daily, on-the-hour most hours
        'url': 'https://www.nhk.or.jp/radionews/',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'F261_01',
            'thumbnail': 'https://www.nhk.or.jp/radioondemand/json/F261/img/RADIONEWS_640.jpg',
            'description': 'md5:bf2c5b397e44bc7eb26de98d8f15d79d',
            'channel': 'NHKラジオ第1',
            'title': 'NHKラジオニュース',
        }
    }]

    def _real_extract(self, url):
        return self.url_result('https://www.nhk.or.jp/radio/ondemand/detail.html?p=F261_01', NhkRadiruIE)


class NhkRadiruLiveIE(InfoExtractor):
    _GEO_COUNTRIES = ['JP']
    _VALID_URL = r'https?://www\.nhk\.or\.jp/radio/player/\?ch=(?P<id>r[12]|fm)'
    _TESTS = [{
        # radio 1, no area specified
        'url': 'https://www.nhk.or.jp/radio/player/?ch=r1',
        'info_dict': {
            'id': 'r1-tokyo',
            'title': 're:^ＮＨＫネットラジオ第1 東京.+$',
            'ext': 'm4a',
            'thumbnail': 'https://www.nhk.or.jp/common/img/media/r1-200x200.png',
            'live_status': 'is_live',
        },
    }, {
        # radio 2, area specified
        # (the area doesnt actually matter, r2 is national)
        'url': 'https://www.nhk.or.jp/radio/player/?ch=r2',
        'params': {'extractor_args': {'nhkradirulive': {'area': ['fukuoka']}}},
        'info_dict': {
            'id': 'r2-fukuoka',
            'title': 're:^ＮＨＫネットラジオ第2 福岡.+$',
            'ext': 'm4a',
            'thumbnail': 'https://www.nhk.or.jp/common/img/media/r2-200x200.png',
            'live_status': 'is_live',
        },
    }, {
        # fm, area specified
        'url': 'https://www.nhk.or.jp/radio/player/?ch=fm',
        'params': {'extractor_args': {'nhkradirulive': {'area': ['sapporo']}}},
        'info_dict': {
            'id': 'fm-sapporo',
            'title': 're:^ＮＨＫネットラジオＦＭ 札幌.+$',
            'ext': 'm4a',
            'thumbnail': 'https://www.nhk.or.jp/common/img/media/fm-200x200.png',
            'live_status': 'is_live',
        }
    }]

    _NOA_STATION_IDS = {'r1': 'n1', 'r2': 'n2', 'fm': 'n3'}

    def _real_extract(self, url):
        station = self._match_id(url)
        area = self._configuration_arg('area', ['tokyo'])[0]

        config = self._download_xml(
            'https://www.nhk.or.jp/radio/config/config_web.xml', station, 'Downloading area information')
        data = config.find(f'.//data//area[.="{area}"]/..')

        if not data:
            raise ExtractorError('Invalid area. Valid areas are: %s' % ', '.join(
                [i.text for i in config.findall('.//data//area')]), expected=True)

        noa_info = self._download_json(
            f'https:{config.find(".//url_program_noa").text}'.format(area=data.find('areakey').text),
            station, note=f'Downloading {area} station metadata')
        present_info = traverse_obj(noa_info, ('nowonair_list', self._NOA_STATION_IDS.get(station), 'present'))

        return {
            'title': ' '.join(traverse_obj(present_info, (('service', 'area',), 'name', {str}))),
            'id': join_nonempty(station, area),
            'thumbnails': traverse_obj(present_info, ('service', 'images', ..., {
                'url': 'url',
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
            })),
            'formats': self._extract_m3u8_formats(data.find(f'{station}hls').text, station),
            'is_live': True,
        }
