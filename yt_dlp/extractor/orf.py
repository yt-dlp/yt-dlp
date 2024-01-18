import functools
import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    InAdvancePagedList,
    clean_html,
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    make_archive_id,
    mimetype2ext,
    orderedSet,
    remove_end,
    smuggle_url,
    strip_jsonp,
    try_call,
    unescapeHTML,
    unified_strdate,
    unsmuggle_url,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class ORFTVthekIE(InfoExtractor):
    IE_NAME = 'orf:tvthek'
    IE_DESC = 'ORF TVthek'
    _VALID_URL = r'(?P<url>https?://tvthek\.orf\.at/(?:(?:[^/]+/){2}){1,2}(?P<id>\d+))(/[^/]+/(?P<vid>\d+))?(?:$|[?#])'

    _TESTS = [{
        'url': 'https://tvthek.orf.at/profile/ZIB-2/1211/ZIB-2/14121079',
        'info_dict': {
            'id': '14121079',
        },
        'playlist_count': 11,
        'params': {'noplaylist': True}
    }, {
        'url': 'https://tvthek.orf.at/profile/ZIB-2/1211/ZIB-2/14121079/Umfrage-Welches-Tier-ist-Sebastian-Kurz/15083150',
        'info_dict': {
            'id': '14121079',
        },
        'playlist_count': 1,
        'params': {'playlist_items': '5'}
    }, {
        'url': 'https://tvthek.orf.at/profile/ZIB-2/1211/ZIB-2/14121079/Umfrage-Welches-Tier-ist-Sebastian-Kurz/15083150',
        'info_dict': {
            'id': '14121079',
            'playlist_count': 1
        },
        'playlist': [{
            'info_dict': {
                'id': '15083150',
                'ext': 'mp4',
                'description': 'md5:7be1c485425f5f255a5e4e4815e77d04',
                'thumbnail': 'https://api-tvthek.orf.at/uploads/media/segments/0130/59/824271ea35cd8931a0fb08ab316a5b0a1562342c.jpeg',
                'title': 'Umfrage: Welches Tier ist Sebastian Kurz?',
            }
        }],
        'playlist_count': 1,
        'params': {'noplaylist': True, 'skip_download': 'm3u8'}
    }, {
        'url': 'http://tvthek.orf.at/program/Aufgetischt/2745173/Aufgetischt-Mit-der-Steirischen-Tafelrunde/8891389',
        'playlist': [{
            'md5': '2942210346ed779588f428a92db88712',
            'info_dict': {
                'id': '8896777',
                'ext': 'mp4',
                'title': 'Aufgetischt: Mit der Steirischen Tafelrunde',
                'description': 'md5:c1272f0245537812d4e36419c207b67d',
                'duration': 2668,
                'upload_date': '20141208',
            },
        }],
        'skip': 'Blocked outside of Austria / Germany',
    }, {
        'url': 'http://tvthek.orf.at/topic/Im-Wandel-der-Zeit/8002126/Best-of-Ingrid-Thurnher/7982256',
        'info_dict': {
            'id': '7982259',
            'ext': 'mp4',
            'title': 'Best of Ingrid Thurnher',
            'upload_date': '20140527',
            'description': 'Viele Jahre war Ingrid Thurnher das "Gesicht" der ZIB 2. Vor ihrem Wechsel zur ZIB 2 im Jahr 1995 moderierte sie unter anderem "Land und Leute", "Österreich-Bild" und "Niederösterreich heute".',
        },
        'params': {
            'skip_download': True,  # rtsp downloads
        },
        'skip': 'Blocked outside of Austria / Germany',
    }, {
        'url': 'http://tvthek.orf.at/topic/Fluechtlingskrise/10463081/Heimat-Fremde-Heimat/13879132/Senioren-betreuen-Migrantenkinder/13879141',
        'only_matching': True,
    }, {
        'url': 'http://tvthek.orf.at/profile/Universum/35429',
        'only_matching': True,
    }]

    def _pagefunc(self, url, data_jsb, n, *, image=None):
        sd = data_jsb[n]
        video_id, title = str(sd['id']), sd['title']
        formats = []
        for fd in sd['sources']:
            src = url_or_none(fd.get('src'))
            if not src:
                continue
            format_id = join_nonempty('delivery', 'quality', 'quality_string', from_dict=fd)
            ext = determine_ext(src)
            if ext == 'm3u8':
                m3u8_formats = self._extract_m3u8_formats(
                    src, video_id, 'mp4', m3u8_id=format_id, fatal=False, note=f'Downloading {format_id} m3u8 manifest')
                if any('/geoprotection' in f['url'] for f in m3u8_formats):
                    self.raise_geo_restricted()
                formats.extend(m3u8_formats)
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    src, video_id, f4m_id=format_id, fatal=False))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    src, video_id, mpd_id=format_id, fatal=False, note=f'Downloading {format_id} mpd manifest'))
            else:
                formats.append({
                    'format_id': format_id,
                    'url': src,
                    'protocol': fd.get('protocol'),
                })

        # Check for geoblocking.
        # There is a property is_geoprotection, but that's always false
        geo_str = sd.get('geoprotection_string')
        http_url = next(
            (f['url'] for f in formats if re.match(r'^https?://.*\.mp4$', f['url'])),
            None) if geo_str else None
        if http_url:
            self._request_webpage(
                HEADRequest(http_url), video_id, fatal=False, note='Testing for geoblocking',
                errnote=f'This video seems to be blocked outside of {geo_str}. You may want to try the streaming-* formats')

        subtitles = {}
        for sub in sd.get('subtitles', []):
            sub_src = sub.get('src')
            if not sub_src:
                continue
            subtitles.setdefault(sub.get('lang', 'de-AT'), []).append({
                'url': sub_src,
            })

        upload_date = unified_strdate(sd.get('created_date'))

        thumbnails = []
        preview = sd.get('preview_image_url')
        if preview:
            thumbnails.append({
                'id': 'preview',
                'url': preview,
                'preference': 0,
            })
        image = sd.get('image_full_url') or image
        if image:
            thumbnails.append({
                'id': 'full',
                'url': image,
                'preference': 1,
            })

        yield {
            'id': video_id,
            'title': title,
            'webpage_url': smuggle_url(f'{url}/part/{video_id}', {'force_noplaylist': True}),
            'formats': formats,
            'subtitles': subtitles,
            'description': sd.get('description'),
            'duration': int_or_none(sd.get('duration_in_seconds')),
            'upload_date': upload_date,
            'thumbnails': thumbnails,
        }

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url)
        playlist_id, video_id, base_url = self._match_valid_url(url).group('id', 'vid', 'url')
        webpage = self._download_webpage(url, playlist_id)

        data_jsb = self._parse_json(
            self._search_regex(
                r'<div[^>]+class=(["\']).*?VideoPlaylist.*?\1[^>]+data-jsb=(["\'])(?P<json>.+?)\2',
                webpage, 'playlist', group='json'),
            playlist_id, transform_source=unescapeHTML)['playlist']['videos']

        if not self._yes_playlist(playlist_id, video_id, smuggled_data):
            data_jsb = [sd for sd in data_jsb if str(sd.get('id')) == video_id]

        playlist_count = len(data_jsb)
        image = self._og_search_thumbnail(webpage) if playlist_count == 1 else None

        page_func = functools.partial(self._pagefunc, base_url, data_jsb, image=image)
        return {
            '_type': 'playlist',
            'entries': InAdvancePagedList(page_func, playlist_count, 1),
            'id': playlist_id,
        }


class ORFRadioIE(InfoExtractor):
    IE_NAME = 'orf:radio'

    STATION_INFO = {
        'fm4': ('fm4', 'fm4', 'orffm4'),
        'noe': ('noe', 'oe2n', 'orfnoe'),
        'wien': ('wie', 'oe2w', 'orfwie'),
        'burgenland': ('bgl', 'oe2b', 'orfbgl'),
        'ooe': ('ooe', 'oe2o', 'orfooe'),
        'steiermark': ('stm', 'oe2st', 'orfstm'),
        'kaernten': ('ktn', 'oe2k', 'orfktn'),
        'salzburg': ('sbg', 'oe2s', 'orfsbg'),
        'tirol': ('tir', 'oe2t', 'orftir'),
        'vorarlberg': ('vbg', 'oe2v', 'orfvbg'),
        'oe3': ('oe3', 'oe3', 'orfoe3'),
        'oe1': ('oe1', 'oe1', 'orfoe1'),
    }
    _STATION_RE = '|'.join(map(re.escape, STATION_INFO.keys()))

    _VALID_URL = rf'''(?x)
        https?://(?:
            (?P<station>{_STATION_RE})\.orf\.at/player|
            radiothek\.orf\.at/(?P<station2>{_STATION_RE})
        )/(?P<date>[0-9]+)/(?P<show>\w+)'''

    _TESTS = [{
        'url': 'https://radiothek.orf.at/ooe/20220801/OGMO',
        'info_dict': {
            'id': 'OGMO',
            'title': 'Guten Morgen OÖ',
            'description': 'md5:a3f6083399ef92b8cbe2d421b180835a',
        },
        'playlist': [{
            'md5': 'f33147d954a326e338ea52572c2810e8',
            'info_dict': {
                'id': '2022-08-01_0459_tl_66_7DaysMon1_319062',
                'ext': 'mp3',
                'title': 'Guten Morgen OÖ',
                'upload_date': '20220801',
                'duration': 18000,
                'timestamp': 1659322789,
                'description': 'md5:a3f6083399ef92b8cbe2d421b180835a',
            }
        }]
    }, {
        'url': 'https://ooe.orf.at/player/20220801/OGMO',
        'info_dict': {
            'id': 'OGMO',
            'title': 'Guten Morgen OÖ',
            'description': 'md5:a3f6083399ef92b8cbe2d421b180835a',
        },
        'playlist': [{
            'md5': 'f33147d954a326e338ea52572c2810e8',
            'info_dict': {
                'id': '2022-08-01_0459_tl_66_7DaysMon1_319062',
                'ext': 'mp3',
                'title': 'Guten Morgen OÖ',
                'upload_date': '20220801',
                'duration': 18000,
                'timestamp': 1659322789,
                'description': 'md5:a3f6083399ef92b8cbe2d421b180835a',
            }
        }]
    }, {
        'url': 'http://fm4.orf.at/player/20170107/4CC',
        'only_matching': True,
    }, {
        'url': 'https://noe.orf.at/player/20200423/NGM',
        'only_matching': True,
    }, {
        'url': 'https://wien.orf.at/player/20200423/WGUM',
        'only_matching': True,
    }, {
        'url': 'https://burgenland.orf.at/player/20200423/BGM',
        'only_matching': True,
    }, {
        'url': 'https://steiermark.orf.at/player/20200423/STGMS',
        'only_matching': True,
    }, {
        'url': 'https://kaernten.orf.at/player/20200423/KGUMO',
        'only_matching': True,
    }, {
        'url': 'https://salzburg.orf.at/player/20200423/SGUM',
        'only_matching': True,
    }, {
        'url': 'https://tirol.orf.at/player/20200423/TGUMO',
        'only_matching': True,
    }, {
        'url': 'https://vorarlberg.orf.at/player/20200423/VGUM',
        'only_matching': True,
    }, {
        'url': 'https://oe3.orf.at/player/20200424/3WEK',
        'only_matching': True,
    }, {
        'url': 'http://oe1.orf.at/player/20170108/456544',
        'md5': '34d8a6e67ea888293741c86a099b745b',
        'info_dict': {
            'id': '2017-01-08_0759_tl_51_7DaysSun6_256141',
            'ext': 'mp3',
            'title': 'Morgenjournal',
            'duration': 609,
            'timestamp': 1483858796,
            'upload_date': '20170108',
        },
        'skip': 'Shows from ORF radios are only available for 7 days.'
    }]

    def _entries(self, data, station):
        _, loop_station, old_ie = self.STATION_INFO[station]
        for info in data['streams']:
            item_id = info.get('loopStreamId')
            if not item_id:
                continue
            video_id = item_id.replace('.mp3', '')
            yield {
                'id': video_id,
                'ext': 'mp3',
                'url': f'https://loopstream01.apa.at/?channel={loop_station}&id={item_id}',
                '_old_archive_ids': [make_archive_id(old_ie, video_id)],
                'title': data.get('title'),
                'description': clean_html(data.get('subtitle')),
                'duration': try_call(lambda: (info['end'] - info['start']) / 1000),
                'timestamp': int_or_none(info.get('start'), scale=1000),
                'series': data.get('programTitle'),
            }

    def _real_extract(self, url):
        station, station2, show_date, show_id = self._match_valid_url(url).group('station', 'station2', 'date', 'show')
        api_station, _, _ = self.STATION_INFO[station or station2]
        data = self._download_json(
            f'http://audioapi.orf.at/{api_station}/api/json/current/broadcast/{show_id}/{show_date}', show_id)

        return self.playlist_result(
            self._entries(data, station or station2), show_id, data.get('title'), clean_html(data.get('subtitle')))


class ORFPodcastIE(InfoExtractor):
    IE_NAME = 'orf:podcast'
    _STATION_RE = '|'.join(map(re.escape, (
        'bgl', 'fm4', 'ktn', 'noe', 'oe1', 'oe3',
        'ooe', 'sbg', 'stm', 'tir', 'tv', 'vbg', 'wie')))
    _VALID_URL = rf'https?://sound\.orf\.at/podcast/(?P<station>{_STATION_RE})/(?P<show>[\w-]+)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://sound.orf.at/podcast/oe3/fruehstueck-bei-mir/nicolas-stockhammer-15102023',
        'md5': '526a5700e03d271a1505386a8721ab9b',
        'info_dict': {
            'id': 'nicolas-stockhammer-15102023',
            'ext': 'mp3',
            'title': 'Nicolas Stockhammer (15.10.2023)',
            'duration': 3396.0,
            'series': 'Frühstück bei mir',
        },
        'skip': 'ORF podcasts are only available for a limited time'
    }]

    def _real_extract(self, url):
        station, show, show_id = self._match_valid_url(url).group('station', 'show', 'id')
        data = self._download_json(
            f'https://audioapi.orf.at/radiothek/api/2.0/podcast/{station}/{show}/{show_id}', show_id)

        return {
            'id': show_id,
            'ext': 'mp3',
            'vcodec': 'none',
            **traverse_obj(data, ('payload', {
                'url': ('enclosures', 0, 'url'),
                'ext': ('enclosures', 0, 'type', {mimetype2ext}),
                'title': 'title',
                'description': ('description', {clean_html}),
                'duration': ('duration', {functools.partial(float_or_none, scale=1000)}),
                'series': ('podcast', 'title'),
            })),
        }


class ORFIPTVIE(InfoExtractor):
    IE_NAME = 'orf:iptv'
    IE_DESC = 'iptv.ORF.at'
    _VALID_URL = r'https?://iptv\.orf\.at/(?:#/)?stories/(?P<id>\d+)'

    _TEST = {
        'url': 'http://iptv.orf.at/stories/2275236/',
        'md5': 'c8b22af4718a4b4af58342529453e3e5',
        'info_dict': {
            'id': '350612',
            'ext': 'flv',
            'title': 'Weitere Evakuierungen um Vulkan Calbuco',
            'description': 'md5:d689c959bdbcf04efeddedbf2299d633',
            'duration': 68.197,
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20150425',
        },
    }

    def _real_extract(self, url):
        story_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://iptv.orf.at/stories/%s' % story_id, story_id)

        video_id = self._search_regex(
            r'data-video(?:id)?="(\d+)"', webpage, 'video id')

        data = self._download_json(
            'http://bits.orf.at/filehandler/static-api/json/current/data.json?file=%s' % video_id,
            video_id)[0]

        duration = float_or_none(data['duration'], 1000)

        video = data['sources']['default']
        load_balancer_url = video['loadBalancerUrl']
        abr = int_or_none(video.get('audioBitrate'))
        vbr = int_or_none(video.get('bitrate'))
        fps = int_or_none(video.get('videoFps'))
        width = int_or_none(video.get('videoWidth'))
        height = int_or_none(video.get('videoHeight'))
        thumbnail = video.get('preview')

        rendition = self._download_json(
            load_balancer_url, video_id, transform_source=strip_jsonp)

        f = {
            'abr': abr,
            'vbr': vbr,
            'fps': fps,
            'width': width,
            'height': height,
        }

        formats = []
        for format_id, format_url in rendition['redirect'].items():
            if format_id == 'rtmp':
                ff = f.copy()
                ff.update({
                    'url': format_url,
                    'format_id': format_id,
                })
                formats.append(ff)
            elif determine_ext(format_url) == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    format_url, video_id, f4m_id=format_id))
            elif determine_ext(format_url) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', m3u8_id=format_id))
            else:
                continue

        title = remove_end(self._og_search_title(webpage), ' - iptv.ORF.at')
        description = self._og_search_description(webpage)
        upload_date = unified_strdate(self._html_search_meta(
            'dc.date', webpage, 'upload date'))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'duration': duration,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'formats': formats,
        }


class ORFFM4StoryIE(InfoExtractor):
    IE_NAME = 'orf:fm4:story'
    IE_DESC = 'fm4.orf.at stories'
    _VALID_URL = r'https?://fm4\.orf\.at/stories/(?P<id>\d+)'

    _TEST = {
        'url': 'http://fm4.orf.at/stories/2865738/',
        'playlist': [{
            'md5': 'e1c2c706c45c7b34cf478bbf409907ca',
            'info_dict': {
                'id': '547792',
                'ext': 'flv',
                'title': 'Manu Delago und Inner Tongue live',
                'description': 'Manu Delago und Inner Tongue haben bei der FM4 Soundpark Session live alles gegeben. Hier gibt es Fotos und die gesamte Session als Video.',
                'duration': 1748.52,
                'thumbnail': r're:^https?://.*\.jpg$',
                'upload_date': '20170913',
            },
        }, {
            'md5': 'c6dd2179731f86f4f55a7b49899d515f',
            'info_dict': {
                'id': '547798',
                'ext': 'flv',
                'title': 'Manu Delago und Inner Tongue live (2)',
                'duration': 1504.08,
                'thumbnail': r're:^https?://.*\.jpg$',
                'upload_date': '20170913',
                'description': 'Manu Delago und Inner Tongue haben bei der FM4 Soundpark Session live alles gegeben. Hier gibt es Fotos und die gesamte Session als Video.',
            },
        }],
    }

    def _real_extract(self, url):
        story_id = self._match_id(url)
        webpage = self._download_webpage(url, story_id)

        entries = []
        all_ids = orderedSet(re.findall(r'data-video(?:id)?="(\d+)"', webpage))
        for idx, video_id in enumerate(all_ids):
            data = self._download_json(
                'http://bits.orf.at/filehandler/static-api/json/current/data.json?file=%s' % video_id,
                video_id)[0]

            duration = float_or_none(data['duration'], 1000)

            video = data['sources']['q8c']
            load_balancer_url = video['loadBalancerUrl']
            abr = int_or_none(video.get('audioBitrate'))
            vbr = int_or_none(video.get('bitrate'))
            fps = int_or_none(video.get('videoFps'))
            width = int_or_none(video.get('videoWidth'))
            height = int_or_none(video.get('videoHeight'))
            thumbnail = video.get('preview')

            rendition = self._download_json(
                load_balancer_url, video_id, transform_source=strip_jsonp)

            f = {
                'abr': abr,
                'vbr': vbr,
                'fps': fps,
                'width': width,
                'height': height,
            }

            formats = []
            for format_id, format_url in rendition['redirect'].items():
                if format_id == 'rtmp':
                    ff = f.copy()
                    ff.update({
                        'url': format_url,
                        'format_id': format_id,
                    })
                    formats.append(ff)
                elif determine_ext(format_url) == 'f4m':
                    formats.extend(self._extract_f4m_formats(
                        format_url, video_id, f4m_id=format_id))
                elif determine_ext(format_url) == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        format_url, video_id, 'mp4', m3u8_id=format_id))
                else:
                    continue

            title = remove_end(self._og_search_title(webpage), ' - fm4.ORF.at')
            if idx >= 1:
                # Titles are duplicates, make them unique
                title += ' (' + str(idx + 1) + ')'
            description = self._og_search_description(webpage)
            upload_date = unified_strdate(self._html_search_meta(
                'dc.date', webpage, 'upload date'))

            entries.append({
                'id': video_id,
                'title': title,
                'description': description,
                'duration': duration,
                'thumbnail': thumbnail,
                'upload_date': upload_date,
                'formats': formats,
            })

        return self.playlist_result(entries)
