# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    dict_get,
    int_or_none,
    unified_timestamp,
    str_or_none,
    strip_or_none,
    try_get,
)


class SVTBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['SE']

    def _extract_video(self, video_info, video_id):
        is_live = dict_get(video_info, ('live', 'simulcast'), default=False)
        m3u8_protocol = 'm3u8' if is_live else 'm3u8_native'
        formats = []
        for vr in video_info['videoReferences']:
            player_type = vr.get('playerType') or vr.get('format')
            vurl = vr['url']
            ext = determine_ext(vurl)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    vurl, video_id,
                    ext='mp4', entry_protocol=m3u8_protocol,
                    m3u8_id=player_type, fatal=False))
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    vurl + '?hdcore=3.3.0', video_id,
                    f4m_id=player_type, fatal=False))
            elif ext == 'mpd':
                if player_type == 'dashhbbtv':
                    formats.extend(self._extract_mpd_formats(
                        vurl, video_id, mpd_id=player_type, fatal=False))
            else:
                formats.append({
                    'format_id': player_type,
                    'url': vurl,
                })
        rights = try_get(video_info, lambda x: x['rights'], dict) or {}
        if not formats and rights.get('geoBlockedSweden'):
            self.raise_geo_restricted(
                'This video is only available in Sweden',
                countries=self._GEO_COUNTRIES)
        self._sort_formats(formats)

        subtitles = {}
        subtitle_references = dict_get(video_info, ('subtitles', 'subtitleReferences'))
        if isinstance(subtitle_references, list):
            for sr in subtitle_references:
                subtitle_url = sr.get('url')
                subtitle_lang = sr.get('language', 'sv')
                if subtitle_url:
                    if determine_ext(subtitle_url) == 'm3u8':
                        # TODO(yan12125): handle WebVTT in m3u8 manifests
                        continue

                    subtitles.setdefault(subtitle_lang, []).append({'url': subtitle_url})

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

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'(?:<iframe src|href)="(?P<url>%s[^"]*)"' % SVTIE._VALID_URL, webpage)
        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        widget_id = mobj.group('widget_id')
        article_id = mobj.group('id')

        info = self._download_json(
            'http://www.svt.se/wd?widgetId=%s&articleId=%s&format=json&type=embed&output=json' % (widget_id, article_id),
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
                    )
                    '''
    _TESTS = [{
        'url': 'https://www.svtplay.se/video/26194546/det-har-ar-himlen',
        'md5': '2382036fd6f8c994856c323fe51c426e',
        'info_dict': {
            'id': 'jNwpV9P',
            'ext': 'mp4',
            'title': 'Det här är himlen',
            'timestamp': 1586044800,
            'upload_date': '20200405',
            'duration': 3515,
            'thumbnail': r're:^https?://(?:.*[\.-]jpg|www.svtstatic.se/image/.*)$',
            'age_limit': 0,
            'subtitles': {
                'sv': [{
                    'ext': 'vtt',
                }]
            },
        },
        'params': {
            'format': 'bestvideo',
            # skip for now due to download test asserts that segment is > 10000 bytes and svt uses
            # init segments that are smaller
            # AssertionError: Expected test_SVTPlay_jNwpV9P.mp4 to be at least 9.77KiB, but it's only 864.00B
            'skip_download': True,
        },
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

    def _adjust_title(self, info):
        if info['is_live']:
            info['title'] = self._live_title(info['title'])

    def _extract_by_video_id(self, video_id, webpage=None):
        data = self._download_json(
            'https://api.svt.se/videoplayer-api/video/%s' % video_id,
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
        self._adjust_title(info_dict)
        return info_dict

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id, svt_id = mobj.group('id', 'svt_id')

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
                self._adjust_title(info_dict)
                return info_dict

            svt_id = try_get(
                data, lambda x: x['statistics']['dataLake']['content']['id'],
                compat_str)

        if not svt_id:
            svt_id = self._search_regex(
                (r'<video[^>]+data-video-id=["\']([\da-zA-Z-]+)',
                 r'["\']videoSvtId["\']\s*:\s*["\']([\da-zA-Z-]+)',
                 r'"content"\s*:\s*{.*?"id"\s*:\s*"([\da-zA-Z-]+)"',
                 r'["\']svtId["\']\s*:\s*["\']([\da-zA-Z-]+)'),
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
        return False if SVTIE.suitable(url) or SVTPlayIE.suitable(url) else super(SVTSeriesIE, cls).suitable(url)

    def _real_extract(self, url):
        series_slug, season_id = re.match(self._VALID_URL, url).groups()

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
}''' % series_slug,
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
                if not content_id or not isinstance(content_id, compat_str):
                    continue
                entries.append(self.url_result(
                    'svt:' + content_id, SVTPlayIE.ie_key(), content_id))

        title = series.get('name')
        season_name = season_name or season_id

        if title and season_name:
            title = '%s - %s' % (title, season_name)
        elif season_id:
            title = season_id

        return self.playlist_result(
            entries, season_id or series.get('id'), title,
            dict_get(series, ('longDescription', 'shortDescription')))


class SVTPageIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?svt\.se/(?P<path>(?:[^/]+/)*(?P<id>[^/?&#]+))'
    _TESTS = [{
        'url': 'https://www.svt.se/sport/ishockey/bakom-masken-lehners-kamp-mot-mental-ohalsa',
        'info_dict': {
            'id': '25298267',
            'title': 'Bakom masken – Lehners kamp mot mental ohälsa',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://www.svt.se/nyheter/utrikes/svenska-andrea-ar-en-mil-fran-branderna-i-kalifornien',
        'info_dict': {
            'id': '24243746',
            'title': 'Svenska Andrea redo att fly sitt hem i Kalifornien',
        },
        'playlist_count': 2,
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
    }, {
        'url': 'https://www.svt.se/nyheter/lokalt/vast/svt-testar-tar-nagon-upp-skrapet-1',
        'only_matching': True,
    }, {
        'url': 'https://www.svt.se/vader/manadskronikor/maj2018',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if SVTIE.suitable(url) or SVTPlayIE.suitable(url) else super(SVTPageIE, cls).suitable(url)

    def _real_extract(self, url):
        path, display_id = re.match(self._VALID_URL, url).groups()

        article = self._download_json(
            'https://api.svt.se/nss-api/page/' + path, display_id,
            query={'q': 'articles'})['articles']['content'][0]

        entries = []

        def _process_content(content):
            if content.get('_type') in ('VIDEOCLIP', 'VIDEOEPISODE'):
                video_id = compat_str(content['image']['svtId'])
                entries.append(self.url_result(
                    'svt:' + video_id, SVTPlayIE.ie_key(), video_id))

        for media in article.get('media', []):
            _process_content(media)

        for obj in article.get('structuredBody', []):
            _process_content(obj.get('content') or {})

        return self.playlist_result(
            entries, str_or_none(article.get('id')),
            strip_or_none(article.get('title')))
