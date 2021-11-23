# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_qs,
    qualities,
    try_get,
    unified_strdate,
    url_or_none,
)


class ArteTVBaseIE(InfoExtractor):
    _ARTE_LANGUAGES = 'fr|de|en|es|it|pl'
    _API_BASE = 'https://api.arte.tv/api/player/v1'


class ArteTVIE(ArteTVBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:www\.)?arte\.tv/(?P<lang>%(langs)s)/videos|
                            api\.arte\.tv/api/player/v\d+/config/(?P<lang_2>%(langs)s)
                        )
                        /(?P<id>\d{6}-\d{3}-[AF])
                    ''' % {'langs': ArteTVBaseIE._ARTE_LANGUAGES}
    _TESTS = [{
        'url': 'https://www.arte.tv/de/videos/092724-001-A/lasst-mich-schlafen/',
        'info_dict': {
            'id': '092724-001-A',
            'ext': 'mp4',
            'title': 'Lasst mich schlafen!',
            'alt_title': 'Wie schlafen wir?',
            'description': 'Gegen Abend signalisiert die biologische Uhr dem Körper durch das Ausschütten von Melatonin, dass es Zeit ist, '
                           'herunterzufahren. Doch was geschieht dabei im Gehirn? Der Schlafforscher Raphael Heinzer vom Schlafforschungsze'
                           'ntrum Lausanne will dies herausfinden und beobachtet die Hirnströme in den verschiedenen Schlafphasen.',
            'upload_date': '20200224'
        },
    }, {
        'url': 'https://www.arte.tv/de/videos/030273-820-A/arte-reportage',
        'info_dict': {
            'id': '030273-820-A',
            'ext': 'mp4',
            'title': 'ARTE Reportage',
            'alt_title': 'Sudan: Die Tigray fliehen aus Äthiopien',
            'description': 'Sudan: In nur wenigen Stunden verloren viele Bewohner aus der Region Tigray alles im Konflikt gegen die Regierun'
                           'g.In diesem Konflikt geht es um die jahrzehntealten Spannungen zwischen den gut 80 Ethnien im Land. / Elfenbeink'
                           'üste: Die 1.000 Einwohner des Dorfs Trinlé-Diapleu integrieren Patienten eines Psychiatrischen Zentrums in ihr D'
                           'orfleben, um ihnen bei der Genesung zu helfen.\n\n(1): Sudan: Die Tigray fliehen aus ÄthiopienIn nur wenigen Stu'
                           'nden verloren viele Bewohner aus der Region Tigray alles im Konflikt gegen die Regierung.Ärzte und Bauern, Stude'
                           'nten und Händler, ganze Familien aus der Region Tigray mussten im Konflikt gegen die Regierung fliehen. In ihrer'
                           ' Heimatregion hatten Tigray Rebellen die Regierung herausgefordert und die schlug hart zurück. In diesem Konflik'
                           't geht es um die jahrzehntealten Spannungen zwischen den gut 80 Ethnien im Land, es geht um politischen Einfluss'
                           ' und um Landbesitz. Auch dem neuen und zunächst international hoch gelobten Ministerpräsidenten Abiy Ahmed Ali i'
                           'st es nicht gelungen, die Ethnien untereinander zu befrieden. Unsere Reporter begleiteten die Flüchtlinge aus Ät'
                           'hiopien im Sudan in ein Flüchtlingscamp in der Wüste, die meisten verbringen die ersten Nächte dort unter freiem'
                           ' Himmel.(2): Elfenbeinküste: Das Dorf, das psychisch Kranken hilftDie 1.000 Einwohner des Dorfs Trinlé-Diapleu h'
                           'elfen Patienten in ihrem Psychiatrie Zentrum gesund zu werden.In Trinlé-Diapleu leben die psychisch Kranken nich'
                           't abgetrennt von den Leuten im Dorf, ganz im Gegenteil: Die Patienten des Psychiatrischen Zentrums Victor Houali'
                           ' werden gleich nach ihrer Ankunft behutsam in das Dorfleben integriert. Das Prinzip der offenen Psychiatrie, in '
                           'dieser Form wohl nicht nur in der Elfenbeinküste einmalig, haben zwei Ärzte der in Frankreich sehr bekannten Cli'
                           'nique de La Borde, Philippe Bichon und Frédérique Drogoul, in den 80er Jahren hier eingeführt. Auch Patienten mi'
                           't Psychosen und Wahnvorstellungen oder schwere Fälle von Schizophrenie heilen sie hier mit der Hilfe von Medikam'
                           'enten, Therapiegesprächen und Mitmenschlichkeit. Für viele Kranke in der Elfenbeinküste ist das Victor Houali di'
                           'e letzte Hoffnung auf Genesung.',
            'upload_date': '20210716'
        }
    }, {
        'url': 'https://www.arte.tv/en/videos/088501-000-A/mexico-stealing-petrol-to-survive/',
        'info_dict': {
            'id': '088501-000-A',
            'ext': 'mp4',
            'title': 'Mexico: Stealing Petrol to Survive',
            'alt_title': 'ARTE Reportage',
            'description': 'In Mexico, the black market in oil is more lucrative than drugs. Poor families drill into pipelines and syphon of'
                           'f the petrol that finds its way to illegal gas stations. The illicit trade in gasoline is highly dangerous and co'
                           'sts Mexico 3 billion euros a year.',
            'upload_date': '20190628',
        },
    }, {
        'url': 'https://www.arte.tv/pl/videos/100103-000-A/usa-dyskryminacja-na-porodowce/',
        'only_matching': True,
    }, {
        'url': 'https://api.arte.tv/api/player/v2/config/de/100605-013-A',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        lang = mobj.group('lang') or mobj.group('lang_2')

        info = self._download_json(
            '%s/config/%s/%s' % (self._API_BASE, lang, video_id), video_id)
        player_info = info['videoJsonPlayer']

        vsr = try_get(player_info, lambda x: x['VSR'], dict)
        if not vsr:
            error = None
            if try_get(player_info, lambda x: x['custom_msg']['type']) == 'error':
                error = try_get(
                    player_info, lambda x: x['custom_msg']['msg'], compat_str)
            if not error:
                error = 'Video %s is not available' % player_info.get('VID') or video_id
            raise ExtractorError(error, expected=True)

        upload_date_str = player_info.get('shootingDate')
        if not upload_date_str:
            upload_date_str = (player_info.get('VRA') or player_info.get('VDA') or '').split(' ')[0]

        title = (player_info.get('VTI') or player_info['VID']).strip()
        subtitle = player_info.get('VSU', '').strip()
        if subtitle:
            title += ' - %s' % subtitle

        qfunc = qualities(['MQ', 'HQ', 'EQ', 'SQ'])

        LANGS = {
            'fr': 'F',
            'de': 'A',
            'en': 'E[ANG]',
            'es': 'E[ESP]',
            'it': 'E[ITA]',
            'pl': 'E[POL]',
        }

        langcode = LANGS.get(lang, lang)

        formats = []
        for format_id, format_dict in vsr.items():
            f = dict(format_dict)
            format_url = url_or_none(f.get('url'))
            streamer = f.get('streamer')
            if not format_url and not streamer:
                continue
            versionCode = f.get('versionCode')
            l = re.escape(langcode)

            # Language preference from most to least priority
            # Reference: section 6.8 of
            # https://www.arte.tv/sites/en/corporate/files/complete-technical-guidelines-arte-geie-v1-07-1.pdf
            PREFERENCES = (
                # original version in requested language, without subtitles
                r'VO{0}$'.format(l),
                # original version in requested language, with partial subtitles in requested language
                r'VO{0}-ST{0}$'.format(l),
                # original version in requested language, with subtitles for the deaf and hard-of-hearing in requested language
                r'VO{0}-STM{0}$'.format(l),
                # non-original (dubbed) version in requested language, without subtitles
                r'V{0}$'.format(l),
                # non-original (dubbed) version in requested language, with subtitles partial subtitles in requested language
                r'V{0}-ST{0}$'.format(l),
                # non-original (dubbed) version in requested language, with subtitles for the deaf and hard-of-hearing in requested language
                r'V{0}-STM{0}$'.format(l),
                # original version in requested language, with partial subtitles in different language
                r'VO{0}-ST(?!{0}).+?$'.format(l),
                # original version in requested language, with subtitles for the deaf and hard-of-hearing in different language
                r'VO{0}-STM(?!{0}).+?$'.format(l),
                # original version in different language, with partial subtitles in requested language
                r'VO(?:(?!{0}).+?)?-ST{0}$'.format(l),
                # original version in different language, with subtitles for the deaf and hard-of-hearing in requested language
                r'VO(?:(?!{0}).+?)?-STM{0}$'.format(l),
                # original version in different language, without subtitles
                r'VO(?:(?!{0}))?$'.format(l),
                # original version in different language, with partial subtitles in different language
                r'VO(?:(?!{0}).+?)?-ST(?!{0}).+?$'.format(l),
                # original version in different language, with subtitles for the deaf and hard-of-hearing in different language
                r'VO(?:(?!{0}).+?)?-STM(?!{0}).+?$'.format(l),
            )

            for pref, p in enumerate(PREFERENCES):
                if re.match(p, versionCode):
                    lang_pref = len(PREFERENCES) - pref
                    break
            else:
                lang_pref = -1

            media_type = f.get('mediaType')
            if media_type == 'hls':
                m3u8_formats = self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id=format_id, fatal=False)
                for m3u8_format in m3u8_formats:
                    m3u8_format['language_preference'] = lang_pref
                formats.extend(m3u8_formats)
                continue

            format = {
                'format_id': format_id,
                'language_preference': lang_pref,
                'format_note': '%s, %s' % (f.get('versionCode'), f.get('versionLibelle')),
                'width': int_or_none(f.get('width')),
                'height': int_or_none(f.get('height')),
                'tbr': int_or_none(f.get('bitrate')),
                'quality': qfunc(f.get('quality')),
            }

            if media_type == 'rtmp':
                format['url'] = f['streamer']
                format['play_path'] = 'mp4:' + f['url']
                format['ext'] = 'flv'
            else:
                format['url'] = f['url']

            formats.append(format)

        # For this extractor, quality only represents the relative quality
        # with respect to other formats with the same resolution
        self._sort_formats(formats, ('res', 'quality'))

        extracted_metadata = {
            'id': player_info.get('VID') or video_id,
            'title': title,
            'upload_date': unified_strdate(upload_date_str),
            'thumbnail': player_info.get('programImage') or player_info.get('VTU', {}).get('IUR'),
            'formats': formats,
        }
        if player_info.get('subtitle', '').strip():
            extracted_metadata['alt_title'] = player_info.get('subtitle', '').strip()
        description = "%s\n\n%s" % (player_info.get('V7T', '').strip(), player_info.get('VDE', '').strip())
        if description.strip():
            extracted_metadata['description'] = description.strip()
        return extracted_metadata


class ArteTVEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?arte\.tv/player/v\d+/index\.php\?.*?\bjson_url=.+'
    _TESTS = [{
        'url': 'https://www.arte.tv/player/v5/index.php?json_url=https%3A%2F%2Fapi.arte.tv%2Fapi%2Fplayer%2Fv2%2Fconfig%2Fde%2F100605-013-A&lang=de&autoplay=true&mute=0100605-013-A',
        'info_dict': {
            'id': '100605-013-A',
            'ext': 'mp4',
            'title': 'United we Stream November Lockdown Edition #13',
            'description': 'md5:be40b667f45189632b78c1425c7c2ce1',
            'upload_date': '20201116',
        },
    }, {
        'url': 'https://www.arte.tv/player/v3/index.php?json_url=https://api.arte.tv/api/player/v2/config/de/100605-013-A',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return [url for _, url in re.findall(
            r'<(?:iframe|script)[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?arte\.tv/player/v\d+/index\.php\?.*?\bjson_url=.+?)\1',
            webpage)]

    def _real_extract(self, url):
        qs = parse_qs(url)
        json_url = qs['json_url'][0]
        video_id = ArteTVIE._match_id(json_url)
        return self.url_result(
            json_url, ie=ArteTVIE.ie_key(), video_id=video_id)


class ArteTVPlaylistIE(ArteTVBaseIE):
    _VALID_URL = r'https?://(?:www\.)?arte\.tv/(?P<lang>%s)/videos/(?P<id>RC-\d{6})' % ArteTVBaseIE._ARTE_LANGUAGES
    _TESTS = [{
        'url': 'https://www.arte.tv/en/videos/RC-016954/earn-a-living/',
        'info_dict': {
            'id': 'RC-016954',
            'title': 'Earn a Living',
            'description': 'md5:d322c55011514b3a7241f7fb80d494c2',
        },
        'playlist_mincount': 6,
    }, {
        'url': 'https://www.arte.tv/pl/videos/RC-014123/arte-reportage/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lang, playlist_id = self._match_valid_url(url).groups()
        collection = self._download_json(
            '%s/collectionData/%s/%s?source=videos'
            % (self._API_BASE, lang, playlist_id), playlist_id)
        entries = []
        for video in collection['videos']:
            if not isinstance(video, dict):
                continue
            video_url = url_or_none(video.get('url')) or url_or_none(video.get('jsonUrl'))
            if not video_url:
                continue
            video_id = video.get('programId')
            entries.append({
                '_type': 'url_transparent',
                'url': video_url,
                'id': video_id,
                'title': video.get('title'),
                'alt_title': video.get('subtitle'),
                'thumbnail': url_or_none(try_get(video, lambda x: x['mainImage']['url'], compat_str)),
                'duration': int_or_none(video.get('durationSeconds')),
                'view_count': int_or_none(video.get('views')),
                'ie_key': ArteTVIE.ie_key(),
            })
        title = collection.get('title')
        description = collection.get('shortDescription') or collection.get('teaserText')
        return self.playlist_result(entries, playlist_id, title, description)
