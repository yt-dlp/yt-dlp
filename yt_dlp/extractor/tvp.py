# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    get_element_by_attribute,
    orderedSet,
)


class TVPIE(InfoExtractor):
    IE_NAME = 'tvp'
    IE_DESC = 'Telewizja Polska'
    _VALID_URL = r'https?://[^/]+\.tvp\.(?:pl|info)/(?:video/(?:[^,\s]*,)*|(?:(?!\d+/)[^/]+/)*)(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://vod.tvp.pl/video/czas-honoru,i-seria-odc-13,194536',
        'md5': 'a21eb0aa862f25414430f15fdfb9e76c',
        'info_dict': {
            'id': '194536',
            'ext': 'mp4',
            'title': 'Czas honoru, odc. 13 – Władek',
            'description': 'md5:437f48b93558370b031740546b696e24',
        },
    }, {
        'url': 'http://www.tvp.pl/there-can-be-anything-so-i-shortened-it/17916176',
        'md5': 'b0005b542e5b4de643a9690326ab1257',
        'info_dict': {
            'id': '17916176',
            'ext': 'mp4',
            'title': 'TVP Gorzów pokaże filmy studentów z podroży dookoła świata',
            'description': 'TVP Gorzów pokaże filmy studentów z podroży dookoła świata',
        },
    }, {
        # page id is not the same as video id(#7799)
        'url': 'https://wiadomosci.tvp.pl/33908820/28092017-1930',
        'md5': '84cd3c8aec4840046e5ab712416b73d0',
        'info_dict': {
            'id': '33908820',
            'ext': 'mp4',
            'title': 'Wiadomości, 28.09.2017, 19:30',
            'description': 'Wydanie główne codziennego serwisu informacyjnego.'
        },
        'skip': 'HTTP Error 404: Not Found',
    }, {
        'url': 'http://vod.tvp.pl/seriale/obyczajowe/na-sygnale/sezon-2-27-/odc-39/17834272',
        'only_matching': True,
    }, {
        'url': 'http://wiadomosci.tvp.pl/25169746/24052016-1200',
        'only_matching': True,
    }, {
        'url': 'http://krakow.tvp.pl/25511623/25lecie-mck-wyjatkowe-miejsce-na-mapie-krakowa',
        'only_matching': True,
    }, {
        'url': 'http://teleexpress.tvp.pl/25522307/wierni-wzieli-udzial-w-procesjach',
        'only_matching': True,
    }, {
        'url': 'http://sport.tvp.pl/25522165/krychowiak-uspokaja-w-sprawie-kontuzji-dwa-tygodnie-to-maksimum',
        'only_matching': True,
    }, {
        'url': 'http://www.tvp.info/25511919/trwa-rewolucja-wladza-zdecydowala-sie-na-pogwalcenie-konstytucji',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)
        video_id = self._search_regex([
            r'<iframe[^>]+src="[^"]*?object_id=(\d+)',
            r"object_id\s*:\s*'(\d+)'",
            r'data-video-id="(\d+)"'], webpage, 'video id', default=page_id)
        return {
            '_type': 'url_transparent',
            'url': 'tvp:' + video_id,
            'description': self._og_search_description(
                webpage, default=None) or self._html_search_meta(
                'description', webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'ie_key': 'TVPEmbed',
        }


class TVPEmbedIE(InfoExtractor):
    IE_NAME = 'tvp:embed'
    IE_DESC = 'Telewizja Polska'
    _VALID_URL = r'''(?x)
        (?:
            tvp:
            |https?://
                (?:[^/]+\.)?
                (?:tvp(?:parlament)?\.pl|tvp\.info|polandin\.com)/
                (?:sess/
                        (?:tvplayer\.php\?.*?object_id
                        |TVPlayer2/(?:embed|api)\.php\?.*[Ii][Dd])
                    |shared/details\.php\?.*?object_id)
                =)
        (?P<id>\d+)
    '''

    _TESTS = [{
        'url': 'tvp:194536',
        'info_dict': {
            'id': '194536',
            'ext': 'mp4',
            'title': 'Czas honoru, odc. 13 – Władek',
            'description': 'md5:76649d2014f65c99477be17f23a4dead',
            'age_limit': 12,
        },
    }, {
        'url': 'https://www.tvp.pl/sess/tvplayer.php?object_id=51247504&amp;autoplay=false',
        'info_dict': {
            'id': '51247504',
            'ext': 'mp4',
            'title': 'Razmova 091220',
        },
    }, {
        # TVPlayer2 embed URL
        'url': 'https://tvp.info/sess/TVPlayer2/embed.php?ID=50595757',
        'only_matching': True,
    }, {
        'url': 'https://wiadomosci.tvp.pl/sess/TVPlayer2/api.php?id=51233452',
        'only_matching': True,
    }, {
        # pulsembed on dziennik.pl
        'url': 'https://www.tvp.pl/shared/details.php?copy_id=52205981&object_id=52204505&autoplay=false&is_muted=false&allowfullscreen=true&template=external-embed/video/iframe-video.html',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage, **kw):
        return [m.group('embed') for m in re.finditer(
            r'(?x)<iframe[^>]+?src=(["\'])(?P<embed>%s)' % TVPEmbedIE._VALID_URL[4:],
            webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # it could be anything that is a valid JS function name
        callback = random.choice((
            'jebac_pis',
            'jebacpis',
            'ziobro',
            'sasin70',
            'sasin_przejebal_70_milionow_PLN',
            'tvp_is_a_state_propaganda_service',
        ))

        webpage = self._download_webpage(
            ('https://www.tvp.pl/sess/TVPlayer2/api.php?id=%s'
             + '&@method=getTvpConfig&@callback=%s') % (video_id, callback), video_id)

        # stripping JSONP padding
        datastr = webpage[15 + len(callback):-3]
        if datastr.startswith('null,'):
            error = self._parse_json(datastr[5:], video_id)
            raise ExtractorError(error[0]['desc'])

        content = self._parse_json(datastr, video_id)['content']
        info = content['info']
        is_live = try_get(info, lambda x: x['isLive'], bool)

        formats = []
        for file in content['files']:
            video_url = file.get('url')
            if not video_url:
                continue
            if video_url.endswith('.m3u8'):
                formats.extend(self._extract_m3u8_formats(video_url, video_id, m3u8_id='hls', fatal=False, live=is_live))
            elif video_url.endswith('.mpd'):
                if is_live:
                    # doesn't work with either ffmpeg or native downloader
                    continue
                formats.extend(self._extract_mpd_formats(video_url, video_id, mpd_id='dash', fatal=False))
            elif video_url.endswith('.f4m'):
                formats.extend(self._extract_f4m_formats(video_url, video_id, f4m_id='hds', fatal=False))
            elif video_url.endswith('.ism/manifest'):
                formats.extend(self._extract_ism_formats(video_url, video_id, ism_id='mss', fatal=False))
            else:
                # mp4, wmv or something
                quality = file.get('quality', {})
                formats.append({
                    'format_id': 'direct',
                    'url': video_url,
                    'ext': determine_ext(video_url, file['type']),
                    'fps': int_or_none(quality.get('fps')),
                    'tbr': int_or_none(quality.get('bitrate')),
                    'width': int_or_none(quality.get('width')),
                    'height': int_or_none(quality.get('height')),
                })

        self._sort_formats(formats)

        title = dict_get(info, ('subtitle', 'title', 'seoTitle'))
        description = dict_get(info, ('description', 'seoDescription'))
        thumbnails = []
        for thumb in content.get('posters') or ():
            thumb_url = thumb.get('src')
            if not thumb_url or '{width}' in thumb_url or '{height}' in thumb_url:
                continue
            thumbnails.append({
                'url': thumb.get('src'),
                'width': thumb.get('width'),
                'height': thumb.get('height'),
            })
        age_limit = try_get(info, lambda x: x['ageGroup']['minAge'], int)
        if age_limit == 1:
            age_limit = 0
        duration = try_get(info, lambda x: x['duration'], int) if not is_live else None

        subtitles = {}
        for sub in content.get('subtitles') or []:
            if not sub.get('url'):
                continue
            subtitles.setdefault(sub['lang'], []).append({
                'url': sub['url'],
                'ext': sub.get('type'),
            })

        info_dict = {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnails': thumbnails,
            'age_limit': age_limit,
            'is_live': is_live,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
        }

        # vod.tvp.pl
        if info.get('vortalName') == 'vod':
            info_dict.update({
                'title': '%s, %s' % (info.get('title'), info.get('subtitle')),
                'series': info.get('title'),
                'season': info.get('season'),
                'episode_number': info.get('episode'),
            })

        return info_dict


class TVPWebsiteIE(InfoExtractor):
    IE_NAME = 'tvp:series'
    _VALID_URL = r'https?://vod\.tvp\.pl/website/(?P<display_id>[^,]+),(?P<id>\d+)'

    _TESTS = [{
        # series
        'url': 'https://vod.tvp.pl/website/lzy-cennet,38678312/video',
        'info_dict': {
            'id': '38678312',
        },
        'playlist_count': 115,
    }, {
        # film
        'url': 'https://vod.tvp.pl/website/gloria,35139666',
        'info_dict': {
            'id': '36637049',
            'ext': 'mp4',
            'title': 'Gloria, Gloria',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['TVPEmbed'],
    }, {
        'url': 'https://vod.tvp.pl/website/lzy-cennet,38678312',
        'only_matching': True,
    }]

    def _entries(self, display_id, playlist_id):
        url = 'https://vod.tvp.pl/website/%s,%s/video' % (display_id, playlist_id)
        for page_num in itertools.count(1):
            page = self._download_webpage(
                url, display_id, 'Downloading page %d' % page_num,
                query={'page': page_num})

            video_ids = orderedSet(re.findall(
                r'<a[^>]+\bhref=["\']/video/%s,[^,]+,(\d+)' % display_id,
                page))

            if not video_ids:
                break

            for video_id in video_ids:
                yield self.url_result(
                    'tvp:%s' % video_id, ie=TVPEmbedIE.ie_key(),
                    video_id=video_id)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id, playlist_id = mobj.group('display_id', 'id')
        return self.playlist_result(
            self._entries(display_id, playlist_id), playlist_id)
