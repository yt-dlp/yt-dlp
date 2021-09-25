# coding: utf-8
from __future__ import unicode_literals

import re

from datetime import datetime, date

from ..utils import (
    ExtractorError,
    unified_timestamp,
    parse_duration,
    orderedSet,
    clean_html,
    js_to_json,
)
from .err import (
    ERRBaseIE,
    sanitize_title,
    json_has_value,
)


class ERRArhiivIE(ERRBaseIE):
    IE_DESC = 'arhiiv.err.ee: archived TV and radio shows, movies and documentaries produced in ETV (Estonia)'
    _VALID_URL = r'(?P<prefix>https?://arhiiv\.err\.ee)/vaata/(?P<id>[^/?#]+)'
    _TESTS = [{
        # 0 a video episode
        'url':
        'https://arhiiv.err.ee/vaata/eesti-aja-lood-okupatsioonid-muusad-soja-varjus',
        'md5': 'bc46e7b18050c5ea06cda8e28181d710',
        'info_dict': {
            'id': 'eesti-aja-lood-okupatsioonid-muusad-soja-varjus',
            'display_id': 'eesti-aja-lood-okupatsioonid-muusad-soja-varjus',
            'ext': 'mp4',
            'title': 'Eesti aja lood - Okupatsioonid - Muusad sõja varjus',
            'thumbnail':
            'https://arhiiv.err.ee//thumbnails/2009-002267-0068_0001_D10_EESTI-AJA-LOOD-OKUPATSIOONID_th.jpg',
            'description': 'md5:36772936a0982571ce23aa0dad1f6231',
            'upload_date': '20100513',
            'uploader': 'ERR',
            'timestamp': 1273709330,
        },
        'params': {
            'format': 'bestvideo',
        },
    }, {
        # 1 a single video
        'url': 'https://arhiiv.err.ee/vaata/tallinn-mai-juuni-1976',
        'md5': 'e695eb29734edd4ed7b04a02ade0bd98',
        'info_dict': {
            'id': 'tallinn-mai-juuni-1976',
            'display_id': 'tallinn-mai-juuni-1976',
            'ext': 'mp4',
            'title': 'Tallinn - Mai-juuni 1976',
            'thumbnail':
            'https://arhiiv.err.ee//thumbnails/1976-085466-0001_0002_D10_TALLINN-MAI-JUUNI-1976_th.jpg',
            'upload_date': '20190709',
            'uploader': 'ERR',
            'timestamp': 1562679643,
        },
        'params': {
            'format': 'bestvideo',
        },
    }, {
        # 1 an audio episode
        'url': 'https://arhiiv.err.ee/vaata/linnulaul-linnulaul-34-rukkiraak',
        'md5': '4f9f659c9c6c6a99c01f423895ac377e',
        'info_dict': {
            'id': 'linnulaul-linnulaul-34-rukkiraak',
            'display_id': 'linnulaul-linnulaul-34-rukkiraak',
            'ext': 'm4a',
            'title': 'Linnulaul - 34 - Rukkirääk',
            'thumbnail':
            'https://arhiiv.err.ee//thumbnails/default_audio_th.jpg',
            'description': 'md5:d41739b0c8e250a3435216afc98c8741',
            'release_date': '20020530',
            'channel': '2002 EESTI RAADIO',
            'uploader': 'ERR',
        },
        'params': {
            'format': 'bestaudio',
        },
    }]

    def _extract_properties(self, webpage):
        info = dict()
        title = self._html_search_regex(
            r'<head>[^<]*<title>([^|]+)[^<]*?</title>',
            webpage,
            'title',
            flags=re.DOTALL)
        if title:
            info['title'] = title.strip().strip('.')

        description = self._html_search_regex(
            r'<h2>\s*?Kirjeldus\s*?</h2>\s*?<p>(.*?)</p>',
            webpage,
            'description',
            flags=re.DOTALL,
            default=None)
        if description:
            info['description'] = description.strip()

        rights = self._html_search_regex(
            r'<div[^>]+id=(["\'])rights\1[^>]*>(?P<rights>.*?)</div>',
            webpage,
            'rights',
            flags=re.DOTALL,
            group='rights',
            default=None)
        if rights:
            # Remove ugly whitespace
            info['license'] = ' '.join(rights.split())

        thumbnail = self._search_regex(
            r"css\('background-image', 'url\(\"(.+?).jpg\"\)'\)",
            webpage,
            'thumbnail',
            flags=re.DOTALL,
            default=None)
        if thumbnail:
            info['thumbnail'] = thumbnail + '_th.jpg'

        res = re.findall(
            r'<th[^>]*>([^<:\*\.]+)[^<]*?</th>[^<]*?<td[^>]*>(.*?)</td>',
            webpage, re.DOTALL)
        year = None
        if res:
            for (name, value) in res:
                name = name.strip()
                value = value.strip()
                if name == 'Sarja pealkiri':
                    info['series'] = value
                elif name == 'Osa nr':
                    info['episode_number'] = int(value)
                elif name == 'Uudislugu':
                    info['description'] = value
                elif name == 'ISO':
                    info['iso'] = value
                elif name == 'Fail':
                    info['file'] = value
                elif name == 'Märksõnad':
                    # tags can be:
                    #   * simple like 'huumor';
                    #   * complex like 'intervjuud/vestlusringid';
                    #   * weird like 'meedia (raadio, tv, press)'.
                    # See e.g. 'https://arhiiv.err.ee/vaata/homme-on-esimene-aprill'
                    tags = re.sub(r'\(|\)|,|/', ' ', clean_html(value)).split()
                    if tags:
                        info['tags'] = sorted(
                            map(lambda s: s.strip().lower(), tags))
                elif name in ['Aasta', 'Võtte aasta']:
                    year = value
                elif name in ['Autorid', 'Režissöör', 'Toimetajad', 'Esinejad']:
                    if 'creator' not in info:
                        info['creator'] = set()
                    info['creator'] = info['creator'] | set(
                        re.split(r'\s*,\s*', value))
                elif name == 'Fonogrammi tootja':
                    info['channel'] = value
                    mobj = re.search(r'([0-9]{4})', value)
                    if not year and mobj:
                        year = mobj.group(0)
                elif name == 'Kestus':
                    info['duration'] = parse_duration(value)
                elif name == 'Kategooria':
                    categories = re.split(r'\s*&rarr;\s*|\s*,\s*', value)
                    info['categories'] = sorted(
                        filter(
                            lambda s: s != 'Muu',
                            set(map(lambda s: s.capitalize(),
                                    categories))))
                elif name == 'Registreerimise kuupäev':
                    try:
                        info['upload_date'] = datetime.strptime(
                            value, '%d.%m.%Y').date().strftime('%Y%m%d')
                    except ValueError as ex:
                        self._debug_message(
                            "Failed to parse upload_date '%s' %s" %
                            (value, ex))
                elif name == 'Registreerimise aeg':
                    info['timestamp'] = unified_timestamp(value)
                elif name in ['Esmaeeter', 'Eetris']:
                    try:
                        info['release_date'] = datetime.strptime(
                            value, '%d.%m.%Y').date()
                    except ValueError as ex:
                        self._debug_message(
                            "Failed to parse release_date '%s' %s" %
                            (value, ex))
                    if 'release_date' not in info:
                        try:
                            info['release_date'] = datetime.strptime(
                                value, "%B %Y").date()
                        except ValueError as ex:
                            self._debug_message(
                                "Failed to parse release_date '%s' %s" %
                                (value, ex))
                        except TypeError as ex:
                            self._debug_message(
                                "Failed to parse release_date '%s' %s" %
                                (value, ex))
                    if 'release_date' not in info:
                        # Try for a year yyyy
                        mobj = re.search(r'([0-9]{4})', value)
                        if mobj:
                            info['release_date'] = date(year=int(
                                mobj.group(0)), day=1, month=1)
                    if 'release_date' in info:
                        info['release_date'] = info['release_date'].strftime(
                            '%Y%m%d')

        if year and 'release_date' not in info:
            info['release_date'] = date(
                year=int(year), day=1, month=1).strftime('%Y%m%d')

        if 'release_date' in info and not year:
            mobj = re.match(r'\d{4}', info['release_date'])
            if mobj:
                year = mobj.group(0)

        if 'channel' not in info:
            channel = list()
            if year:
                channel.append(year)
            channel.append('ERR')
            info['channel'] = ' '.join(channel)

        info['uploader'] = 'ERR'

        if 'creator' in info:
            info['creator'] = ', '.join(sorted(info['creator']))

        if 'series' in info:
            episode = info['title']
            prefix = info['series'].upper()
            if episode.upper().startswith(prefix + ': ' + prefix):
                # ERR Arhiiv sometimes mangles episode's title by
                # adding series name twice as prefix.  This hack
                # corrects it.
                episode = episode[len(prefix + ': ' + prefix):]
            elif episode.upper().startswith(prefix):
                episode = episode[len(prefix):]

            if episode.startswith(': '):
                episode = episode[len(': '):]
            elif episode.startswith('. '):
                episode = episode[len('. '):]

            info['episode'] = episode.strip()
            if not episode:
                self.report_warning("Episode name reduced to 'none'")

        if 'episode' in info:
            info['title'] = info['series'] + ' - ' + info['episode']
        info['title'] = sanitize_title(info['title'])

        if 'series' in info and year:
            info['season'] = year

        return info

    def _extract_chapters(self, webpage, total_duration):
        res = re.findall(
            r'<tr>[^<]*<td[^>]+class=(["\'])data\1[^>]*>([^<]+)</td>'
            r'[^<]*<td[^>]+class=(["\'])data\3[^>]*>.*?</td>'
            r'[^<]*<td[^>]+class=(["\'])data\4[^>]*>(.*?)</td>[^<]*</tr>',
            webpage, re.DOTALL)
        chapters = list()
        prev_chapter = dict()
        correction = 0
        for match in res:
            chapter = dict()
            duration = parse_duration(match[1])
            if not prev_chapter:
                # ERR Arhiiv sometimes adds some arbitrary amount of seconds to
                # all timings. This hack corrects it by subtracting the first
                # chapter's start_time from all subsequent timings.
                correction = duration
            duration -= correction
            chapter['start_time'] = duration
            chapter['title'] = match[4].strip()
            if prev_chapter:
                prev_chapter['end_time'] = duration
            chapters.append(chapter)
            prev_chapter = chapter
        prev_chapter['end_time'] = total_duration

        return chapters

    def _real_extract(self, url):
        info = dict()
        url_dict = self._extract_ids(url)
        video_id = url_dict['id']
        info['display_id'] = video_id
        info['id'] = video_id
        info['webpage_url'] = url

        webpage = self._download_webpage(url, video_id)

        master_url = self._search_regex(r"var\s+src\s*=\s*'(//.+?\.m3u8)';",
                                        webpage,
                                        'master_url',
                                        flags=re.DOTALL,
                                        fatal=False)

        config = self._search_regex(r"var\s+config\s*=\s*({.+?})\s*;",
                                    webpage,
                                    'config',
                                    flags=re.DOTALL,
                                    fatal=False)
        config = self._parse_json(config, video_id, fatal=False, transform_source=js_to_json)
        if json_has_value(config, 'subtitles'):
            info['subtitles'] = self._extract_subtitles(config,
                                                        lang_property='srclang',
                                                        url_prefix=url_dict['prefix'])

        info.update(self._extract_properties(webpage))

        if not master_url:
            error_msg = 'Cannot extract master url. Video or audio %s is not available' % video_id
            if 'iso' in info or re.match(r'.*(?:TIFF|JPEG).*', info.get('file', '')):
                error_msg += ", url referres to a photo."
            raise ExtractorError(error_msg, expected=True)

        m3u8_formats = self._extract_formats(master_url, video_id)
        if m3u8_formats:
            self._sort_formats(m3u8_formats)
            info['formats'] = m3u8_formats

        if 'duration' in info:
            chapters = self._extract_chapters(webpage, info['duration'])
            if chapters:
                info['chapters'] = chapters

        self._debug_json(info, msg='INFO\n')

        return info


class ERRArhiivPlaylistIE(ERRBaseIE):
    IE_DESC = 'arhiiv.err.ee: playlists and search results'
    _ERRARHIIV_SERVICES = 'seeria|samast-seeriast|sarnased|otsi|tapsem-otsing|show-category-single-files'
    _VALID_URL = r'(?P<prefix>https?://arhiiv\.err\.ee)/(?P<service>%(services)s)[/?#]*(?P<id>[^/?#]*)' % {
        'services': _ERRARHIIV_SERVICES
    }
    _TESTS = [{
        'url': 'https://arhiiv.err.ee/seeria/linnuaabits/info/0/default/koik',
        'info_dict': {
            'id': 'linnuaabits',
            'title': "Linnuaabits",
        },
        'playlist_mincount': 71,
    }, {
        'url': 'https://arhiiv.err.ee/seeria/linnulaul',
        'info_dict': {
            'id': 'linnulaul',
            'title': "Linnulaul",
        },
        'playlist_mincount': 10,
    }, {
        'url':
        'https://arhiiv.err.ee/seeria/eesti-aja-lood-okupatsioonid/info/0/default/koik',
        'info_dict': {
            'id': 'eesti-aja-lood-okupatsioonid',
            'title': "Eesti aja lood - Okupatsioonid",
        },
        'playlist_mincount': 46,
    }, {
        'url':
        'https://arhiiv.err.ee/samast-seeriast/ak-filmikroonika-1958-1991-linnuturg-keskturul/default/1',
        'info_dict': {
            'id': 'ak-filmikroonika-1958-1991',
            'title': "AK filmikroonika 1958-1991",
        },
        'playlist_count': 10,
    }, {
        'url':
        'https://arhiiv.err.ee/sarnased/ensv-ensv-kaadri-taga/default/1',
        'info_dict': {
            'id': 'ensv',
            'title': "EnsV - Sarnased saated",
        },
        'playlist_count': 10,
    }, {
        'url': 'https://arhiiv.err.ee/otsi/reliikvia/default/koik',
        'info_dict': {
            'id': None,
            'title': "Otsingutulemused reliikvia",
        },
        'playlist_mincount': 161,
    }, {
        'url': 'https://arhiiv.err.ee/otsi/reliikvia/default/3',
        'info_dict': {
            'id': None,
            'title': "Otsingutulemused reliikvia",
        },
        'playlist_mincount': 10,
    }, {
        'url':
        'https://arhiiv.err.ee/tapsem-otsing?searchphrase=kahur&searchfrom_video=video&searchfrom_audio=audio',
        'info_dict': {
            'id': None,
            'title': "Otsingutulemused",
        },
        'playlist_mincount': 10,
    }]

    def _guess_id_from_title(self, title):
        if not title:
            return None
        playlist_id = ' '.join(title.split())\
                         .lower()\
                         .replace('õ', 'o')\
                         .replace('ö', 'o')\
                         .replace('ä', 'a')\
                         .replace('ü', 'u')\
                         .replace(' ', '-')
        playlist_id = re.sub(r'[,.:;+?!\'"*\\/|]', '', playlist_id)
        return playlist_id

    def _real_extract(self, url):
        url_dict = self._extract_ids(url)
        service = url_dict['service']
        playlist_id = url_dict['id'] if service in [
            'seeria', 'show-category-single-files'
        ] else None
        prefix = url_dict['prefix']
        webpage = self._download_webpage(url, playlist_id)
        title = self._html_search_regex(
            r'<head>[^<]*<title>([^|]+)[^<]*?</title>',
            webpage,
            'title',
            flags=re.DOTALL,
            fatal=False)
        if title:
            title = title.strip().strip('.')

        if title and not playlist_id and service not in [
                'otsi', 'tapsem-otsing', 'show-category-single-files'
        ]:
            playlist_id = self._guess_id_from_title(title)

        if title and service == 'sarnased':
            title += ' - Sarnased saated'

        title = sanitize_title(title)

        res = re.findall(
            r'<h2[^>]*>[^<]*<a\s+href=(["\'])(/vaata/[^"\']+)\1[^>]*>',
            webpage, re.DOTALL)

        url_list = orderedSet([prefix + match[1] for match in res])

        entries = [self.url_result(item_url, ie='ERRArhiiv') for item_url in url_list]

        return self.playlist_result(entries, playlist_id, title)
