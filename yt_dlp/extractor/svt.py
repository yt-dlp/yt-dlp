import json
import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    dict_get,
    int_or_none,
    traverse_obj,
    try_get,
    unified_timestamp,
)


class SVTBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['SE']

    def _extract_video(self, video_info, video_id):
        is_live = dict_get(video_info, ('live', 'simulcast'), default=False)
        m3u8_protocol = 'm3u8' if is_live else 'm3u8_native'
        formats = []
        subtitles = {}
        for vr in video_info['videoReferences']:
            player_type = vr.get('playerType') or vr.get('format')
            vurl = vr['url']
            ext = determine_ext(vurl)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    vurl, video_id,
                    ext='mp4', entry_protocol=m3u8_protocol,
                    m3u8_id=player_type, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    vurl + '?hdcore=3.3.0', video_id,
                    f4m_id=player_type, fatal=False))
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    vurl, video_id, mpd_id=player_type, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'format_id': player_type,
                    'url': vurl,
                })
        rights = try_get(video_info, lambda x: x['rights'], dict) or {}
        if not formats and rights.get('geoBlockedSweden'):
            self.raise_geo_restricted(
                'This video is only available in Sweden',
                countries=self._GEO_COUNTRIES, metadata_available=True)

        subtitle_references = dict_get(video_info, ('subtitles', 'subtitleReferences'))
        if isinstance(subtitle_references, list):
            for sr in subtitle_references:
                subtitle_url = sr.get('url')
                subtitle_lang = sr.get('language', 'sv')
                if subtitle_url:
                    sub = {
                        'url': subtitle_url,
                    }
                    if determine_ext(subtitle_url) == 'm3u8':
                        # XXX: no way of testing, is it ever hit?
                        sub['ext'] = 'vtt'
                    subtitles.setdefault(subtitle_lang, []).append(sub)

        title = video_info.get('title')

        series = video_info.get('programTitle')
        season_number = int_or_none(video_info.get('season'))
        episode = video_info.get('episodeTitle')
        episode_number = int_or_none(video_info.get('episodeNumber'))

        timestamp = unified_timestamp(rights.get('validFrom'))
        duration = int_or_none(dict_get(video_info, ('materialLength', 'contentDuration')))
        age_limit = None
        adult = dict_get(
            video_info, ('inappropriateForChildren', 'blockedForChildren'),
            skip_false_values=False)
        if adult is not None:
            age_limit = 18 if adult else 0

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'duration': duration,
            'timestamp': timestamp,
            'age_limit': age_limit,
            'series': series,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'is_live': is_live,
        }


class SVTIE(SVTBaseIE):
    _VALID_URL = r'https?://(?:www\.)?svt\.se/wd\?(?:.*?&)?widgetId=(?P<widget_id>\d+)&.*?\barticleId=(?P<id>\d+)'
    _EMBED_REGEX = [rf'(?:<iframe src|href)="(?P<url>{_VALID_URL}[^"]*)"']
    _TEST = {
        'url': 'http://www.svt.se/wd?widgetId=23991&sectionId=541&articleId=2900353&type=embed&contextSectionId=123&autostart=false',
        'md5': '33e9a5d8f646523ce0868ecfb0eed77d',
        'info_dict': {
            'id': '2900353',
            'ext': 'mp4',
            'title': 'Stjärnorna skojar till det - under SVT-intervjun',
            'duration': 27,
            'age_limit': 0,
        },
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        widget_id = mobj.group('widget_id')
        article_id = mobj.group('id')

        info = self._download_json(
            f'http://www.svt.se/wd?widgetId={widget_id}&articleId={article_id}&format=json&type=embed&output=json',
            article_id)

        info_dict = self._extract_video(info['video'], article_id)
        info_dict['title'] = info['context']['title']
        return info_dict


class SVTPlayBaseIE(SVTBaseIE):
    _SVTPLAY_RE = r'root\s*\[\s*(["\'])_*svtplay\1\s*\]\s*=\s*(?P<json>{.+?})\s*;\s*\n'


class SVTPlayIE(SVTPlayBaseIE):
    IE_DESC = 'SVT Play and Öppet arkiv'
    _VALID_URL = r'''(?x)
                    (?:
                        (?:
                            svt:|
                            https?://(?:www\.)?svt\.se/barnkanalen/barnplay/[^/]+/
                        )
                        (?P<svt_id>[^/?#&]+)|
                        https?://(?:www\.)?(?:svtplay|oppetarkiv)\.se/(?:video|klipp|kanaler)/(?P<id>[^/?#&]+)
                        (?:.*?(?:modalId|id)=(?P<modal_id>[\da-zA-Z-]+))?
                    )
                    '''
    _TESTS = [{
        'url': 'https://www.svtplay.se/video/30479064',
        'md5': '2382036fd6f8c994856c323fe51c426e',
        'info_dict': {
            'id': '8zVbDPA',
            'ext': 'mp4',
            'title': 'Designdrömmar i Stenungsund',
            'timestamp': 1615770000,
            'upload_date': '20210315',
            'duration': 3519,
            'thumbnail': r're:^https?://(?:.*[\.-]jpg|www.svtstatic.se/image/.*)$',
            'age_limit': 0,
            'subtitles': {
                'sv': [{
                    'ext': 'vtt',
                }],
            },
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'skip': 'Episode is no longer available',
    }, {
        'url': 'https://www.svtplay.se/video/emBxBQj',
        'md5': '2382036fd6f8c994856c323fe51c426e',
        'info_dict': {
            'id': 'eyBd9aj',
            'ext': 'mp4',
            'title': '1. Farlig kryssning',
            'timestamp': 1491019200,
            'upload_date': '20170401',
            'duration': 2566,
            'thumbnail': r're:^https?://(?:.*[\.-]jpg|www.svtstatic.se/image/.*)$',
            'age_limit': 0,
            'episode': '1. Farlig kryssning',
            'series': 'Rederiet',
            'subtitles': {
                'sv': 'count:3',
            },
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://www.svtplay.se/video/jz2rYz7/anders-hansen-moter/james-fallon?info=visa',
        'info_dict': {
            'id': 'jvXAGVb',
            'ext': 'mp4',
            'title': 'James Fallon',
            'timestamp': 1673917200,
            'upload_date': '20230117',
            'duration': 1081,
            'thumbnail': r're:^https?://(?:.*[\.-]jpg|www.svtstatic.se/image/.*)$',
            'age_limit': 0,
            'episode': 'James Fallon',
            'series': 'Anders Hansen möter...',
        },
        'params': {
            'skip_download': 'dash',
        },
    }, {
        'url': 'https://www.svtplay.se/video/30479064/husdrommar/husdrommar-sasong-8-designdrommar-i-stenungsund?modalId=8zVbDPA',
        'only_matching': True,
    }, {
        'url': 'https://www.svtplay.se/video/30684086/rapport/rapport-24-apr-18-00-7?id=e72gVpa',
        'only_matching': True,
    }, {
        # geo restricted to Sweden
        'url': 'http://www.oppetarkiv.se/video/5219710/trollflojten',
        'only_matching': True,
    }, {
        'url': 'http://www.svtplay.se/klipp/9023742/stopptid-om-bjorn-borg',
        'only_matching': True,
    }, {
        'url': 'https://www.svtplay.se/kanaler/svt1',
        'only_matching': True,
    }, {
        'url': 'svt:1376446-003A',
        'only_matching': True,
    }, {
        'url': 'svt:14278044',
        'only_matching': True,
    }, {
        'url': 'https://www.svt.se/barnkanalen/barnplay/kar/eWv5MLX/',
        'only_matching': True,
    }, {
        'url': 'svt:eWv5MLX',
        'only_matching': True,
    }]

    def _extract_by_video_id(self, video_id, webpage=None):
        data = self._download_json(
            f'https://api.svt.se/videoplayer-api/video/{video_id}',
            video_id, headers=self.geo_verification_headers())
        info_dict = self._extract_video(data, video_id)
        if not info_dict.get('title'):
            title = dict_get(info_dict, ('episode', 'series'))
            if not title and webpage:
                title = re.sub(
                    r'\s*\|\s*.+?$', '', self._og_search_title(webpage))
            if not title:
                title = video_id
            info_dict['title'] = title
        return info_dict

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        svt_id = mobj.group('svt_id') or mobj.group('modal_id')

        if svt_id:
            return self._extract_by_video_id(svt_id)

        webpage = self._download_webpage(url, video_id)

        data = self._parse_json(
            self._search_regex(
                self._SVTPLAY_RE, webpage, 'embedded data', default='{}',
                group='json'),
            video_id, fatal=False)

        thumbnail = self._og_search_thumbnail(webpage)

        if data:
            video_info = try_get(
                data, lambda x: x['context']['dispatcher']['stores']['VideoTitlePageStore']['data']['video'],
                dict)
            if video_info:
                info_dict = self._extract_video(video_info, video_id)
                info_dict.update({
                    'title': data['context']['dispatcher']['stores']['MetaStore']['title'],
                    'thumbnail': thumbnail,
                })
                return info_dict

            svt_id = try_get(
                data, lambda x: x['statistics']['dataLake']['content']['id'],
                str)

        if not svt_id:
            nextjs_data = self._search_nextjs_data(webpage, video_id, fatal=False)
            svt_id = traverse_obj(nextjs_data, (
                'props', 'urqlState', ..., 'data', {json.loads}, 'detailsPageByPath',
                'video', 'svtId', {str}), get_all=False)

        if not svt_id:
            svt_id = self._search_regex(
                (r'<video[^>]+data-video-id=["\']([\da-zA-Z-]+)',
                 r'<[^>]+\bdata-rt=["\']top-area-play-button["\'][^>]+\bhref=["\'][^"\']*video/[\w-]+/[^"\']*\b(?:modalId|id)=([\w-]+)'),
                webpage, 'video id')

        info_dict = self._extract_by_video_id(svt_id, webpage)
        info_dict['thumbnail'] = thumbnail

        return info_dict


class SVTSeriesIE(SVTPlayBaseIE):
    _VALID_URL = r'https?://(?:www\.)?svtplay\.se/(?P<id>[^/?&#]+)(?:.+?\btab=(?P<season_slug>[^&#]+))?'
    _TESTS = [{
        'url': 'https://www.svtplay.se/rederiet',
        'info_dict': {
            'id': '14445680',
            'title': 'Rederiet',
            'description': 'md5:d9fdfff17f5d8f73468176ecd2836039',
        },
        'playlist_mincount': 318,
    }, {
        'url': 'https://www.svtplay.se/rederiet?tab=season-2-14445680',
        'info_dict': {
            'id': 'season-2-14445680',
            'title': 'Rederiet - Säsong 2',
            'description': 'md5:d9fdfff17f5d8f73468176ecd2836039',
        },
        'playlist_mincount': 12,
    }]

    @classmethod
    def suitable(cls, url):
        return False if SVTIE.suitable(url) or SVTPlayIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        series_slug, season_id = self._match_valid_url(url).groups()

        series = self._download_json(
            'https://api.svt.se/contento/graphql', series_slug,
            'Downloading series page', query={
                'query': '''{
  listablesBySlug(slugs: ["%s"]) {
    associatedContent(include: [productionPeriod, season]) {
      items {
        item {
          ... on Episode {
            videoSvtId
          }
        }
      }
      id
      name
    }
    id
    longDescription
    name
    shortDescription
  }
}''' % series_slug,  # noqa: UP031
            })['data']['listablesBySlug'][0]

        season_name = None

        entries = []
        for season in series['associatedContent']:
            if not isinstance(season, dict):
                continue
            if season_id:
                if season.get('id') != season_id:
                    continue
                season_name = season.get('name')
            items = season.get('items')
            if not isinstance(items, list):
                continue
            for item in items:
                video = item.get('item') or {}
                content_id = video.get('videoSvtId')
                if not content_id or not isinstance(content_id, str):
                    continue
                entries.append(self.url_result(
                    'svt:' + content_id, SVTPlayIE.ie_key(), content_id))

        title = series.get('name')
        season_name = season_name or season_id

        if title and season_name:
            title = f'{title} - {season_name}'
        elif season_id:
            title = season_id

        return self.playlist_result(
            entries, season_id or series.get('id'), title,
            dict_get(series, ('longDescription', 'shortDescription')))


class SVTPageIE(SVTBaseIE):
    _VALID_URL = r'https?://(?:www\.)?svt\.se/(?:[^/?#]+/)*(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://www.svt.se/nyheter/lokalt/skane/viktor-18-forlorade-armar-och-ben-i-sepsis-vill-ateruppta-karaten-och-bli-svetsare',
        'info_dict': {
            'title': 'Viktor, 18, förlorade armar och ben i sepsis – vill återuppta karaten och bli svetsare',
            'id': 'viktor-18-forlorade-armar-och-ben-i-sepsis-vill-ateruppta-karaten-och-bli-svetsare',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://www.svt.se/nyheter/lokalt/skane/forsvarsmakten-om-trafikkaoset-pa-e22-kunde-inte-varit-dar-snabbare',
        'info_dict': {
            'id': 'jXvk42E',
            'title': 'Försvarsmakten om trafikkaoset på E22: Kunde inte varit där snabbare',
            'ext': 'mp4',
            'duration': 80,
            'age_limit': 0,
            'timestamp': 1704370009,
            'episode': 'Försvarsmakten om trafikkaoset på E22: Kunde inte varit där snabbare',
            'series': 'Lokala Nyheter Skåne',
            'upload_date': '20240104',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.svt.se/nyheter/svtforum/2023-tungt-ar-for-svensk-media',
        'info_dict': {
            'title': '2023 tungt år för svensk media',
            'id': 'ewqAZv4',
            'ext': 'mp4',
            'duration': 3074,
            'age_limit': 0,
            'series': '',
            'timestamp': 1702980479,
            'upload_date': '20231219',
            'episode': 'Mediestudier',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.svt.se/sport/ishockey/bakom-masken-lehners-kamp-mot-mental-ohalsa',
        'info_dict': {
            'id': '25298267',
            'title': 'Bakom masken – Lehners kamp mot mental ohälsa',
        },
        'playlist_count': 4,
        'skip': 'Video is gone',
    }, {
        'url': 'https://www.svt.se/nyheter/utrikes/svenska-andrea-ar-en-mil-fran-branderna-i-kalifornien',
        'info_dict': {
            'id': '24243746',
            'title': 'Svenska Andrea redo att fly sitt hem i Kalifornien',
        },
        'playlist_count': 2,
        'skip': 'Video is gone',
    }, {
        # only programTitle
        'url': 'http://www.svt.se/sport/ishockey/jagr-tacklar-giroux-under-intervjun',
        'info_dict': {
            'id': '8439V2K',
            'ext': 'mp4',
            'title': 'Stjärnorna skojar till det - under SVT-intervjun',
            'duration': 27,
            'age_limit': 0,
        },
        'skip': 'Video is gone',
    }, {
        'url': 'https://www.svt.se/nyheter/lokalt/vast/svt-testar-tar-nagon-upp-skrapet-1',
        'only_matching': True,
    }, {
        'url': 'https://www.svt.se/vader/manadskronikor/maj2018',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if SVTIE.suitable(url) or SVTPlayIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)
        title = self._og_search_title(webpage)

        urql_state = self._search_json(
            r'window\.svt\.nyh\.urqlState\s*=', webpage, 'json data', display_id)

        data = traverse_obj(urql_state, (..., 'data', {str}, {json.loads}), get_all=False) or {}

        def entries():
            for video_id in set(traverse_obj(data, (
                'page', (('topMedia', 'svtId'), ('body', ..., 'video', 'svtId')), {str},
            ))):
                info = self._extract_video(
                    self._download_json(f'https://api.svt.se/video/{video_id}', video_id), video_id)
                info['title'] = title
                yield info

        return self.playlist_result(entries(), display_id, title)
