import datetime as dt
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    join_nonempty,
    mimetype2ext,
    parse_iso8601,
    qualities,
    smuggle_url,
    str_or_none,
    strip_or_none,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class TVerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tver\.jp/(?:(?P<type>lp|corner|series|episodes?|feature)/)+(?P<id>[a-zA-Z0-9]+)'
    _GEO_COUNTRIES = ['JP']
    _GEO_BYPASS = False
    _TESTS = [{
        'url': 'https://tver.jp/episodes/epc1hdugbk',
        'info_dict': {
            'id': 'epc1hdugbk',
            'ext': 'mp4',
            'display_id': 'ref:baeebeac-a2a6-4dbf-9eb3-c40d59b40068',
            'title': '神回だけ見せます！ #2 壮烈！車大騎馬戦（木曜スペシャル）',
            'alt_title': '神回だけ見せます！ #2 壮烈！車大騎馬戦（木曜スペシャル） 日テレ',
            'description': 'md5:2726f742d5e3886edeaf72fb6d740fef',
            'uploader_id': '0b69bd13d7a949f2a7420e982444f138',
            'channel': '日テレ',
            'channel_id': 'tver-ntv',
            'duration': 1158.024,
            'thumbnail': 'https://statics.tver.jp/images/content/thumbnail/episode/xlarge/epc1hdugbk.jpg?v=16',
            'series': '神回だけ見せます！',
            'episode': '#2 壮烈！車大騎馬戦（木曜スペシャル）',
            'episode_number': 2,
            'timestamp': 1651453200,
            'upload_date': '20220502',
            'modified_timestamp': 1736870264,
            'modified_date': '20250114',
            'live_status': 'not_live',
        },
    }, {
        'url': 'https://tver.jp/corner/f0103888',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/lp/f0033031',
        'only_matching': True,
    }, {
        'url': 'https://tver.jp/series/srtxft431v',
        'info_dict': {
            'id': 'srtxft431v',
            'title': '名探偵コナン',
        },
        'playlist_mincount': 21,
    }, {
        'url': 'https://tver.jp/series/sru35hwdd2',
        'info_dict': {
            'id': 'sru35hwdd2',
            'title': '神回だけ見せます！',
        },
        'playlist_count': 11,
    }, {
        'url': 'https://tver.jp/series/srkq2shp9d',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'
    _HEADERS = {
        'x-tver-platform-type': 'web',
        'Origin': 'https://tver.jp',
        'Referer': 'https://tver.jp/',
    }
    _PLATFORM_QUERY = {}

    def _real_initialize(self):
        session_info = self._download_json(
            'https://platform-api.tver.jp/v2/api/platform_users/browser/create',
            None, 'Creating session', data=b'device_type=pc')
        self._PLATFORM_QUERY = traverse_obj(session_info, ('result', {
            'platform_uid': 'platform_uid',
            'platform_token': 'platform_token',
        }))

    def _call_platform_api(self, path, video_id, note=None, fatal=True, query=None):
        return self._download_json(
            f'https://platform-api.tver.jp/service/api/{path}', video_id, note,
            fatal=fatal, headers=self._HEADERS, query={
                **self._PLATFORM_QUERY,
                **(query or {}),
            })

    def _yield_episode_ids_for_series(self, series_id):
        seasons_info = self._download_json(
            f'https://service-api.tver.jp/api/v1/callSeriesSeasons/{series_id}',
            series_id, 'Downloading seasons info', headers=self._HEADERS)
        for season_id in traverse_obj(
                seasons_info, ('result', 'contents', lambda _, v: v['type'] == 'season', 'content', 'id', {str})):
            episodes_info = self._call_platform_api(
                f'v1/callSeasonEpisodes/{season_id}', series_id, f'Downloading season {season_id} episodes info')
            yield from traverse_obj(episodes_info, (
                'result', 'contents', lambda _, v: v['type'] == 'episode', 'content', 'id', {str}))

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        backend = self._configuration_arg('backend', ['streaks'])[0]
        if backend not in ('brightcove', 'streaks'):
            raise ExtractorError(f'Invalid backend value: {backend}', expected=True)

        if video_type == 'series':
            series_info = self._call_platform_api(
                f'v2/callSeries/{video_id}', video_id, 'Downloading series info')
            return self.playlist_from_matches(
                self._yield_episode_ids_for_series(video_id), video_id,
                traverse_obj(series_info, ('result', 'content', 'content', 'title', {str})),
                ie=TVerIE, getter=lambda x: f'https://tver.jp/episodes/{x}')

        if video_type != 'episodes':
            webpage = self._download_webpage(url, video_id, note='Resolving to new URL')
            video_id = self._match_id(self._search_regex(
                (r'canonical"\s*href="(https?://tver\.jp/[^"]+)"', r'&link=(https?://tver\.jp/[^?&]+)[?&]'),
                webpage, 'url regex'))

        episode_info = self._call_platform_api(
            f'v1/callEpisode/{video_id}', video_id, 'Downloading episode info', fatal=False, query={
                'require_data': 'mylist,later[epefy106ur],good[epefy106ur],resume[epefy106ur]',
            })
        episode_content = traverse_obj(
            episode_info, ('result', 'episode', 'content')) or {}

        version = traverse_obj(episode_content, ('version', {str_or_none}), default='5')
        video_info = self._download_json(
            f'https://statics.tver.jp/content/episode/{video_id}.json', video_id, 'Downloading video info',
            query={'v': version}, headers={'Referer': 'https://tver.jp/'})

        episode = strip_or_none(episode_content.get('title'))
        series = str_or_none(episode_content.get('seriesTitle'))
        title = (
            join_nonempty(series, episode, delim=' ')
            or str_or_none(video_info.get('title')))
        provider = str_or_none(episode_content.get('productionProviderName'))
        onair_label = str_or_none(episode_content.get('broadcastDateLabel'))

        thumbnails = [
            {
                'id': quality,
                'url': update_url_query(
                    f'https://statics.tver.jp/images/content/thumbnail/episode/{quality}/{video_id}.jpg',
                    {'v': version}),
                'width': width,
                'height': height,
            }
            for quality, width, height in [
                ('small', 480, 270),
                ('medium', 640, 360),
                ('large', 960, 540),
                ('xlarge', 1280, 720),
            ]
        ]

        metadata = {
            'title': title,
            'series': series,
            'episode': episode,
            # an another title which is considered "full title" for some viewers
            'alt_title': join_nonempty(title, provider, onair_label, delim=' '),
            'channel': provider,
            'thumbnails': thumbnails,
            **traverse_obj(video_info, {
                'description': ('description', {str}),
                'timestamp': ('viewStatus', 'startAt', {int_or_none}),
                'episode_number': ('no', {int_or_none}),
            }),
        }

        if onair_label:
            metadata.update(self._format_broadcast_date(onair_label))

        if backend == 'brightcove':
            p_id = video_info['video']['accountID']
            r_id = traverse_obj(video_info, (
                'video', ('videoRefID', 'videoID'), {str}, any, {require('reference ID')}))
            if not r_id.isdecimal():
                r_id = f'ref:{r_id}'

            return {
                **metadata,
                '_type': 'url_transparent',
                'url': smuggle_url(
                    self.BRIGHTCOVE_URL_TEMPLATE % (p_id, r_id),
                    {'geo_countries': ['JP']}),
                'ie_key': 'BrightcoveNew',
            }

        ref_id = video_info['streaks']['videoRefID']
        if not ref_id.startswith('ref:'):
            ref_id = f'ref:{ref_id}'

        return {
            **self._extract_from_streaks_api(video_info['streaks']['projectID'], ref_id, {
                'Origin': 'https://tver.jp',
                'Referer': 'https://tver.jp/',
            }),
            **metadata,
            'id': video_id,
        }

    def _format_broadcast_date(self, onair_label):
        """
        Extracts the broadcast date from the onair label

        Truth to be said, we cannot be sure or guarantee that the broadcast date is correct
        as TVer doesn't really have consistent date format for the broadcast date.
        At best we can only assume the following:
        - If there is only year, this mean the broadcast is old.
        - If there is only month and day, this mean the broadcast is recent within the current year or the previous year.

        :param onair_label: The onair label string
        :return: A dictionary containing the formatted broadcast date or an empty dictionary if the date is not found

        """
        if not onair_label:
            return {}

        mobj = re.search(
            r'(?:(?P<year>\d{4})年)|(?:(?P<month>\d{1,2})\D(?P<day>\d{1,2})\D)', onair_label)
        if not mobj:
            return {}
        broadcast_date_info = mobj.groupdict()

        data = {
            'release_year': int_or_none(broadcast_date_info.get('year')),
        }
        day, month = (int_or_none(broadcast_date_info.get(key)) for key in ('day', 'month'))
        if day and month:
            year = data.get('release_year') or dt.datetime.now().year
            dt_ = dt.datetime.strptime(f'{year}-{month}-{day}', '%Y-%m-%d')
            # If the date is in the future, it means the broadcast date is in the previous year
            # Ref: https://github.com/yt-dlp/yt-dlp/pull/12282#issuecomment-2678132806
            if dt_ > dt.datetime.now():
                year -= 1
            data['release_timestamp'] = dt.datetime(year=year, month=month, day=day).timestamp()

        return data

    # XXX: Remove everything below and subclass TVerIE from StreaksBaseIE when #12679 is merged
    _API_URL_TEMPLATE = 'https://{}.api.streaks.jp/v1/projects/{}/medias/{}{}'

    def _extract_from_streaks_api(self, project_id, media_id, headers=None, query=None, ssai=False):
        try:
            response = self._download_json(
                self._API_URL_TEMPLATE.format('playback', project_id, media_id, ''),
                media_id, 'Downloading streaks playback API JSON',
                headers={
                    'Accept': 'application/json',
                    'Origin': 'https://players.streaks.jp',
                    **self.geo_verification_headers(),
                    **(headers or {}),
                })
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in {403, 404}:
                error = self._parse_json(e.cause.response.read().decode(), media_id, fatal=False)
                message = traverse_obj(error, ('message', {str}))
                code = traverse_obj(error, ('code', {str}))
                if code == 'REQUEST_FAILED':
                    self.raise_geo_restricted(message, countries=self._GEO_COUNTRIES)
                elif code == 'MEDIA_NOT_FOUND':
                    raise ExtractorError(message, expected=True)
                elif code or message:
                    raise ExtractorError(join_nonempty(code, message, delim=': '))
            raise

        streaks_id = response['id']
        live_status = {
            'clip': 'was_live',
            'file': 'not_live',
            'linear': 'is_live',
            'live': 'is_live',
        }.get(response.get('type'))

        audio_quality_func = qualities(('1', '0'))
        formats, subtitles = [], {}
        drm_formats = False

        for source in traverse_obj(response, ('sources', lambda _, v: v['src'])):
            if source.get('key_systems'):
                drm_formats = True
                continue

            src_url = source['src']
            is_live = live_status == 'is_live'
            ext = mimetype2ext(source.get('type'))

            if ext == 'm3u8':
                if is_live and ssai:
                    session_params = traverse_obj(
                        self._download_json(
                            self._API_URL_TEMPLATE.format('ssai', project_id, streaks_id, '/ssai/session'),
                            media_id, 'Downloading session parameters',
                            headers={'Content-Type': 'application/json'},  # XXX: geo_verification_headers ?
                            data=json.dumps({'id': source['id']}).encode()),
                        (0, 'query', {urllib.parse.parse_qs}))
                    src_url = update_url_query(src_url, session_params)

                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    src_url, media_id, 'mp4', m3u8_id='hls',
                    fatal=False, live=is_live, query=query)

                for fmt in traverse_obj(fmts, lambda _, v: v['vcodec'] == 'none'):
                    if mobj := re.match(r'hls-[a-z]+_AUDIO-(?P<quality>\d)_\d+-', fmt['format_id']):
                        fmt['quality'] = audio_quality_func(mobj.group('quality'))

            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    src_url, media_id, mpd_id='dash', fatal=False)

            else:
                self.report_warning(f'Unsupported stream type: {ext}')
                continue

            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        if not formats and drm_formats:
            self.report_drm(media_id)

        self._remove_duplicate_formats(formats)

        for subs in traverse_obj(response, (
            'tracks', lambda _, v: v['kind'] in ('subtitles', 'captions') and url_or_none(v['src']),
        )):
            lang = traverse_obj(subs, ('srclang', {str.lower})) or 'ja'
            subtitles.setdefault(lang, []).append({'url': subs['src']})

        return {
            'id': streaks_id,
            'display_id': media_id,
            'channel_id': project_id,
            'formats': formats,
            'subtitles': subtitles,
            'live_status': live_status,
            **traverse_obj(response, {
                'channel_id': ('project_id', {str}),
                'uploader_id': ('profile', {str}),
                'title': ('name', {str}),
                'description': ('description', {str}, filter),
                'duration': ('duration', {float_or_none}),
                'tags': ('tags', ..., {str}),
                'thumbnails': (('poster', 'thumbnail'), 'src', {'url': {url_or_none}}),
                'timestamp': ('created_at', {parse_iso8601}),
                'modified_timestamp': ('updated_at', {parse_iso8601}),
            }),
        }
