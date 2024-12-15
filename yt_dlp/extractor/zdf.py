import re

from .common import InfoExtractor
from ..utils import (
    NO_DEFAULT,
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    merge_dicts,
    parse_codecs,
    qualities,
    traverse_obj,
    try_get,
    unified_timestamp,
    update_url_query,
    url_or_none,
    urljoin,
)


class ZDFBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['DE']
    _QUALITIES = ('auto', 'low', 'med', 'high', 'veryhigh', 'hd', 'fhd', 'uhd')

    def _download_v2_doc(self, document_id):
        return self._download_json(
            f'https://zdf-prod-futura.zdf.de/mediathekV2/document/{document_id}',
            document_id)

    def _call_api(self, url, video_id, item, api_token=None, referrer=None):
        headers = {}
        if api_token:
            headers['Api-Auth'] = f'Bearer {api_token}'
        if referrer:
            headers['Referer'] = referrer
        return self._download_json(
            url, video_id, f'Downloading JSON {item}', headers=headers)

    @staticmethod
    def _extract_subtitles(src):
        subtitles = {}
        for caption in try_get(src, lambda x: x['captions'], list) or []:
            subtitle_url = url_or_none(caption.get('uri'))
            if subtitle_url:
                lang = caption.get('language', 'deu')
                subtitles.setdefault(lang, []).append({
                    'url': subtitle_url,
                })
        return subtitles

    def _extract_format(self, video_id, formats, format_urls, meta):
        format_url = url_or_none(meta.get('url'))
        if not format_url or format_url in format_urls:
            return
        format_urls.add(format_url)

        mime_type, ext = meta.get('mimeType'), determine_ext(format_url)
        if mime_type == 'application/x-mpegURL' or ext == 'm3u8':
            new_formats = self._extract_m3u8_formats(
                format_url, video_id, 'mp4', m3u8_id='hls',
                entry_protocol='m3u8_native', fatal=False)
        elif mime_type == 'application/f4m+xml' or ext == 'f4m':
            new_formats = self._extract_f4m_formats(
                update_url_query(format_url, {'hdcore': '3.7.0'}), video_id, f4m_id='hds', fatal=False)
        elif ext == 'mpd':
            new_formats = self._extract_mpd_formats(
                format_url, video_id, mpd_id='dash', fatal=False)
        else:
            f = parse_codecs(meta.get('mimeCodec'))
            if not f and meta.get('type'):
                data = meta['type'].split('_')
                if try_get(data, lambda x: x[2]) == ext:
                    f = {'vcodec': data[0], 'acodec': data[1]}
            f.update({
                'url': format_url,
                'format_id': join_nonempty('http', meta.get('type'), meta.get('quality')),
                'tbr': int_or_none(self._search_regex(r'_(\d+)k_', format_url, 'tbr', default=None)),
            })
            new_formats = [f]
        formats.extend(merge_dicts(f, {
            'format_note': join_nonempty('quality', 'class', from_dict=meta, delim=', '),
            'language': meta.get('language'),
            'language_preference': 10 if meta.get('class') == 'main' else -10 if meta.get('class') == 'ad' else -1,
            'quality': qualities(self._QUALITIES)(meta.get('quality')),
        }) for f in new_formats)

    def _extract_ptmd(self, ptmd_url, video_id, api_token, referrer):
        ptmd = self._call_api(
            ptmd_url, video_id, 'metadata', api_token, referrer)

        content_id = ptmd.get('basename') or ptmd_url.split('/')[-1]

        formats = []
        track_uris = set()
        for p in ptmd['priorityList']:
            formitaeten = p.get('formitaeten')
            if not isinstance(formitaeten, list):
                continue
            for f in formitaeten:
                f_qualities = f.get('qualities')
                if not isinstance(f_qualities, list):
                    continue
                for quality in f_qualities:
                    tracks = try_get(quality, lambda x: x['audio']['tracks'], list)
                    if not tracks:
                        continue
                    for track in tracks:
                        self._extract_format(
                            content_id, formats, track_uris, {
                                'url': track.get('uri'),
                                'type': f.get('type'),
                                'mimeType': f.get('mimeType'),
                                'quality': quality.get('quality'),
                                'class': track.get('class'),
                                'language': track.get('language'),
                            })

        duration = float_or_none(try_get(
            ptmd, lambda x: x['attributes']['duration']['value']), scale=1000)

        return {
            'extractor_key': ZDFIE.ie_key(),
            'id': content_id,
            'duration': duration,
            'formats': formats,
            'subtitles': self._extract_subtitles(ptmd),
            '_format_sort_fields': ('tbr', 'res', 'quality', 'language_preference'),
        }

    def _extract_player(self, webpage, video_id, fatal=True):
        return self._parse_json(
            self._search_regex(
                r'(?s)data-zdfplayer-jsb=(["\'])(?P<json>{.+?})\1', webpage,
                'player JSON', default='{}' if not fatal else NO_DEFAULT,
                group='json'),
            video_id)


class ZDFIE(ZDFBaseIE):
    _VALID_URL = r'https?://www\.zdf\.de/(?:[^/]+/)*(?P<id>[^/?#&]+)\.html'
    _TESTS = [{
        # Same as https://www.phoenix.de/sendungen/ereignisse/corona-nachgehakt/wohin-fuehrt-der-protest-in-der-pandemie-a-2050630.html
        'url': 'https://www.zdf.de/politik/phoenix-sendungen/wohin-fuehrt-der-protest-in-der-pandemie-100.html',
        'md5': '34ec321e7eb34231fd88616c65c92db0',
        'info_dict': {
            'id': '210222_phx_nachgehakt_corona_protest',
            'ext': 'mp4',
            'title': 'Wohin führt der Protest in der Pandemie?',
            'description': 'md5:7d643fe7f565e53a24aac036b2122fbd',
            'duration': 1691,
            'timestamp': 1613948400,
            'upload_date': '20210221',
        },
        'skip': 'No longer available: "Diese Seite wurde leider nicht gefunden"',
    }, {
        # Same as https://www.3sat.de/film/ab-18/10-wochen-sommer-108.html
        'url': 'https://www.zdf.de/dokumentation/ab-18/10-wochen-sommer-102.html',
        'md5': '0aff3e7bc72c8813f5e0fae333316a1d',
        'info_dict': {
            'id': '141007_ab18_10wochensommer_film',
            'ext': 'mp4',
            'title': 'Ab 18! - 10 Wochen Sommer',
            'description': 'md5:8253f41dc99ce2c3ff892dac2d65fe26',
            'duration': 2660,
            'timestamp': 1608604200,
            'upload_date': '20201222',
        },
        'skip': 'No longer available: "Diese Seite wurde leider nicht gefunden"',
    }, {
        'url': 'https://www.zdf.de/nachrichten/heute-journal/heute-journal-vom-30-12-2021-100.html',
        'info_dict': {
            'id': '211230_sendung_hjo',
            'ext': 'mp4',
            'description': 'md5:47dff85977bde9fb8cba9e9c9b929839',
            'duration': 1890.0,
            'upload_date': '20211230',
            'chapters': list,
            'thumbnail': 'md5:e65f459f741be5455c952cd820eb188e',
            'title': 'heute journal vom 30.12.2021',
            'timestamp': 1640897100,
        },
        'skip': 'No longer available: "Diese Seite wurde leider nicht gefunden"',
    }, {
        'url': 'https://www.zdf.de/dokumentation/terra-x/die-magie-der-farben-von-koenigspurpur-und-jeansblau-100.html',
        'info_dict': {
            'id': '151025_magie_farben2_tex',
            'ext': 'mp4',
            'title': 'Die Magie der Farben (2/2)',
            'description': 'md5:a89da10c928c6235401066b60a6d5c1a',
            'duration': 2615,
            'timestamp': 1465021200,
            'upload_date': '20160604',
            'thumbnail': 'https://www.zdf.de/assets/mauve-im-labor-100~768x432?cb=1464909117806',
        },
    }, {
        'url': 'https://www.zdf.de/funk/druck-11790/funk-alles-ist-verzaubert-102.html',
        'md5': '57af4423db0455a3975d2dc4578536bc',
        'info_dict': {
            'ext': 'mp4',
            'id': 'video_funk_1770473',
            'duration': 1278,
            'description': 'Die Neue an der Schule verdreht Ismail den Kopf.',
            'title': 'Alles ist verzaubert',
            'timestamp': 1635520560,
            'upload_date': '20211029',
            'thumbnail': 'https://www.zdf.de/assets/teaser-funk-alles-ist-verzaubert-102~1920x1080?cb=1663848412907',
        },
    }, {
        # Same as https://www.phoenix.de/sendungen/dokumentationen/gesten-der-maechtigen-i-a-89468.html?ref=suche
        'url': 'https://www.zdf.de/politik/phoenix-sendungen/die-gesten-der-maechtigen-100.html',
        'only_matching': True,
    }, {
        # Same as https://www.3sat.de/film/spielfilm/der-hauptmann-100.html
        'url': 'https://www.zdf.de/filme/filme-sonstige/der-hauptmann-112.html',
        'only_matching': True,
    }, {
        # Same as https://www.3sat.de/wissen/nano/nano-21-mai-2019-102.html, equal media ids
        'url': 'https://www.zdf.de/wissen/nano/nano-21-mai-2019-102.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/service-und-hilfe/die-neue-zdf-mediathek/zdfmediathek-trailer-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/filme/taunuskrimi/die-lebenden-und-die-toten-1---ein-taunuskrimi-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/dokumentation/planet-e/planet-e-uebersichtsseite-weitere-dokumentationen-von-planet-e-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/arte/todliche-flucht/page-video-artede-toedliche-flucht-16-100.html',
        'info_dict': {
            'id': 'video_artede_083871-001-A',
            'ext': 'mp4',
            'title': 'Tödliche Flucht (1/6)',
            'description': 'md5:e34f96a9a5f8abd839ccfcebad3d5315',
            'duration': 3193.0,
            'timestamp': 1641355200,
            'upload_date': '20220105',
        },
        'skip': 'No longer available "Diese Seite wurde leider nicht gefunden"',
    }, {
        'url': 'https://www.zdf.de/serien/soko-stuttgart/das-geld-anderer-leute-100.html',
        'info_dict': {
            'id': '191205_1800_sendung_sok8',
            'ext': 'mp4',
            'title': 'Das Geld anderer Leute',
            'description': 'md5:cb6f660850dc5eb7d1ab776ea094959d',
            'duration': 2581.0,
            'timestamp': 1675160100,
            'upload_date': '20230131',
            'thumbnail': 'https://epg-image.zdf.de/fotobase-webdelivery/images/e2d7e55a-09f0-424e-ac73-6cac4dd65f35?layout=2400x1350',
        },
    }, {
        'url': 'https://www.zdf.de/dokumentation/terra-x/unser-gruener-planet-wuesten-doku-100.html',
        'info_dict': {
            'id': '220605_dk_gruener_planet_wuesten_tex',
            'ext': 'mp4',
            'title': 'Unser grüner Planet - Wüsten',
            'description': 'md5:4fc647b6f9c3796eea66f4a0baea2862',
            'duration': 2613.0,
            'timestamp': 1654450200,
            'upload_date': '20220605',
            'format_note': 'uhd, main',
            'thumbnail': 'https://www.zdf.de/assets/saguaro-kakteen-102~3840x2160?cb=1655910690796',
        },
    }]

    def _extract_entry(self, url, player, content, video_id):
        title = content.get('title') or content['teaserHeadline']

        t = content['mainVideoContent']['http://zdf.de/rels/target']
        ptmd_path = traverse_obj(t, (
            (('streams', 'default'), None),
            ('http://zdf.de/rels/streams/ptmd', 'http://zdf.de/rels/streams/ptmd-template'),
        ), get_all=False)
        if not ptmd_path:
            raise ExtractorError('Could not extract ptmd_path')

        info = self._extract_ptmd(
            urljoin(url, ptmd_path.replace('{playerId}', 'android_native_5')), video_id, player['apiToken'], url)

        thumbnails = []
        layouts = try_get(
            content, lambda x: x['teaserImageRef']['layouts'], dict)
        if layouts:
            for layout_key, layout_url in layouts.items():
                layout_url = url_or_none(layout_url)
                if not layout_url:
                    continue
                thumbnail = {
                    'url': layout_url,
                    'format_id': layout_key,
                }
                mobj = re.search(r'(?P<width>\d+)x(?P<height>\d+)', layout_key)
                if mobj:
                    thumbnail.update({
                        'width': int(mobj.group('width')),
                        'height': int(mobj.group('height')),
                    })
                thumbnails.append(thumbnail)

        chapter_marks = t.get('streamAnchorTag') or []
        chapter_marks.append({'anchorOffset': int_or_none(t.get('duration'))})
        chapters = [{
            'start_time': chap.get('anchorOffset'),
            'end_time': next_chap.get('anchorOffset'),
            'title': chap.get('anchorLabel'),
        } for chap, next_chap in zip(chapter_marks, chapter_marks[1:])]

        return merge_dicts(info, {
            'title': title,
            'description': content.get('leadParagraph') or content.get('teasertext'),
            'duration': int_or_none(t.get('duration')),
            'timestamp': unified_timestamp(content.get('editorialDate')),
            'thumbnails': thumbnails,
            'chapters': chapters or None,
        })

    def _extract_regular(self, url, player, video_id):
        content = self._call_api(
            player['content'], video_id, 'content', player['apiToken'], url)
        return self._extract_entry(player['content'], player, content, video_id)

    def _extract_mobile(self, video_id):
        video = self._download_v2_doc(video_id)

        formats = []
        formitaeten = try_get(video, lambda x: x['document']['formitaeten'], list)
        document = formitaeten and video['document']
        if formitaeten:
            title = document['titel']
            content_id = document['basename']

            format_urls = set()
            for f in formitaeten or []:
                self._extract_format(content_id, formats, format_urls, f)

        thumbnails = []
        teaser_bild = document.get('teaserBild')
        if isinstance(teaser_bild, dict):
            for thumbnail_key, thumbnail in teaser_bild.items():
                thumbnail_url = try_get(
                    thumbnail, lambda x: x['url'], str)
                if thumbnail_url:
                    thumbnails.append({
                        'url': thumbnail_url,
                        'id': thumbnail_key,
                        'width': int_or_none(thumbnail.get('width')),
                        'height': int_or_none(thumbnail.get('height')),
                    })

        return {
            'id': content_id,
            'title': title,
            'description': document.get('beschreibung'),
            'duration': int_or_none(document.get('length')),
            'timestamp': unified_timestamp(document.get('date')) or unified_timestamp(
                try_get(video, lambda x: x['meta']['editorialDate'], str)),
            'thumbnails': thumbnails,
            'subtitles': self._extract_subtitles(document),
            'formats': formats,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id, fatal=False)
        if webpage:
            player = self._extract_player(webpage, url, fatal=False)
            if player:
                return self._extract_regular(url, player, video_id)

        return self._extract_mobile(video_id)


class ZDFChannelIE(ZDFBaseIE):
    _VALID_URL = r'https?://www\.zdf\.de/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.zdf.de/sport/das-aktuelle-sportstudio',
        'info_dict': {
            'id': 'das-aktuelle-sportstudio',
            'title': 'das aktuelle sportstudio',
        },
        'playlist_mincount': 18,
    }, {
        'url': 'https://www.zdf.de/dokumentation/planet-e',
        'info_dict': {
            'id': 'planet-e',
            'title': 'planet e.',
            'description': 'md5:87e3b9c66a63cf1407ee443d2c4eb88e',
        },
        'playlist_mincount': 50,
    }, {
        'url': 'https://www.zdf.de/gesellschaft/aktenzeichen-xy-ungeloest',
        'info_dict': {
            'id': 'aktenzeichen-xy-ungeloest',
            'title': 'Aktenzeichen XY... Ungelöst',
            'description': 'md5:623ede5819c400c6d04943fa8100e6e7',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://www.zdf.de/serien/taunuskrimi/',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if ZDFIE.suitable(url) else super().suitable(url)

    def _og_search_title(self, webpage, fatal=False):
        title = super()._og_search_title(webpage, fatal=fatal)
        return re.split(r'\s+[-|]\s+ZDF(?:mediathek)?$', title or '')[0] or None

    def _get_playlist_description(self, page_data):
        headline = traverse_obj(page_data, ('shortText', 'headline'))
        text = traverse_obj(page_data, ('shortText', 'text'))
        if headline is not None and text is not None:
            return f'{headline}\n\n{text}'
        return headline or text

    def _convert_thumbnails(self, thumbnails):
        return traverse_obj(thumbnails, (
            ..., {
                'url': ('url', {url_or_none}),
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
            }))

    def _teaser_to_url_result(self, teaser):
        return self.url_result(
            ie=ZDFIE.ie_key(),
            **traverse_obj(teaser, {
                'url': ('sharingUrl', {url_or_none}),
                'id': ('id'),
                'title': ('titel'),
                'thumbnails': ('teaserBild', {self._convert_thumbnails}),
                'description': ('beschreibung'),
                'duration': ('length', {float_or_none}),
                'media_type': (('currentVideoType', 'contentType'), any),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode_number': ('episodeNumber', {int_or_none}),
            }))

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        webpage = self._download_webpage(url, channel_id)
        document_id = self._search_regex(
            r'docId\s*:\s*(["\'])(?P<doc_id>(?:(?!\1).)+)\1', webpage, 'document id', group='doc_id')

        data = self._download_v2_doc(document_id)

        main_video = traverse_obj(data, (
            'cluster', lambda _, cluster: cluster['type'] == 'teaserContent',
            'teaser', lambda _, teaser: teaser['type'] == 'video', any))

        if not self._yes_playlist(channel_id, main_video and main_video['id']):
            return self._teaser_to_url_result(main_video)

        playlist_videos = traverse_obj(data, (
            'cluster', lambda _, cluster: cluster['type'] == 'teaser',
            # If 'brandId' differs, it is a 'You might also like' video. Filter these out.
            'teaser', lambda _, teaser: teaser['type'] == 'video' and teaser['brandId'] == document_id))

        thumbnails = traverse_obj(
            data, ('document', 'image'), ('document', 'teaserBild'), ('stageHeader', 'image'))

        return self.playlist_result(
            (self._teaser_to_url_result(video) for video in playlist_videos),
            playlist_id=channel_id,
            playlist_title=self._og_search_title(webpage, fatal=False),
            description=self._get_playlist_description(data),
            thumbnails=self._convert_thumbnails(thumbnails))
