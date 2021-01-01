# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    int_or_none,
    NO_DEFAULT,
    orderedSet,
    parse_codecs,
    qualities,
    try_get,
    unified_timestamp,
    update_url_query,
    url_or_none,
    urljoin,
)


class ZDFBaseIE(InfoExtractor):
    def _call_api(self, url, player, referrer, video_id, item):
        return self._download_json(
            url, video_id, 'Downloading JSON %s' % item,
            headers={
                'Referer': referrer,
                'Api-Auth': 'Bearer %s' % player['apiToken'],
            })

    def _extract_player(self, webpage, video_id, fatal=True):
        return self._parse_json(
            self._search_regex(
                r'(?s)data-zdfplayer-jsb=(["\'])(?P<json>{.+?})\1', webpage,
                'player JSON', default='{}' if not fatal else NO_DEFAULT,
                group='json'),
            video_id)


class ZDFIE(ZDFBaseIE):
    IE_NAME = "ZDF-3sat"
    _VALID_URL = r'https?://www\.(zdf|3sat)\.de/(?:[^/]+/)*(?P<id>[^/?]+)\.html'
    _QUALITIES = ('auto', 'low', 'med', 'high', 'veryhigh', 'hd')
    _GEO_COUNTRIES = ['DE']

    _TESTS = [{
        'url': 'https://www.3sat.de/wissen/wissenschaftsdoku/luxusgut-lebensraum-100.html',
        'info_dict': {
            'id': 'luxusgut-lebensraum-100',
            'ext': 'mp4',
            'title': 'Luxusgut Lebensraum',
            'description': 'md5:5c09b2f45ac3bc5233d1b50fc543d061',
            'duration': 2601,
            'timestamp': 1566497700,
            'upload_date': '20190822',
        }
    }, {
        'url': 'https://www.zdf.de/dokumentation/terra-x/die-magie-der-farben-von-koenigspurpur-und-jeansblau-100.html',
        'info_dict': {
            'id': 'die-magie-der-farben-von-koenigspurpur-und-jeansblau-100',
            'ext': 'mp4',
            'title': 'Die Magie der Farben (2/2)',
            'description': 'md5:a89da10c928c6235401066b60a6d5c1a',
            'duration': 2615,
            'timestamp': 1465021200,
            'upload_date': '20160604',
        },
    }, {
        'url': 'https://www.zdf.de/service-und-hilfe/die-neue-zdf-mediathek/zdfmediathek-trailer-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/filme/taunuskrimi/die-lebenden-und-die-toten-1---ein-taunuskrimi-100.html',
        'only_matching': True,
    }, {
        'url': 'https://www.zdf.de/dokumentation/planet-e/planet-e-uebersichtsseite-weitere-dokumentationen-von-planet-e-100.html',
        'only_matching': True,
    }]

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
        if not format_url:
            return
        if format_url in format_urls:
            return
        format_urls.add(format_url)
        mime_type = meta.get('mimeType')
        ext = determine_ext(format_url)
        if mime_type == 'application/x-mpegURL' or ext == 'm3u8':
            formats.extend(self._extract_m3u8_formats(
                format_url, video_id, 'mp4', m3u8_id='hls',
                entry_protocol='m3u8_native', fatal=False))
        elif mime_type == 'application/f4m+xml' or ext == 'f4m':
            formats.extend(self._extract_f4m_formats(
                update_url_query(format_url, {'hdcore': '3.7.0'}), video_id, f4m_id='hds', fatal=False))
        else:
            f = parse_codecs(meta.get('mimeCodec'))
            format_id = ['http']
            for p in (meta.get('type'), meta.get('quality')):
                if p and isinstance(p, compat_str):
                    format_id.append(p)
            f.update({
                'url': format_url,
                'format_id': '-'.join(format_id),
                'format_note': meta.get('quality'),
                'language': meta.get('language'),
                'quality': qualities(self._QUALITIES)(meta.get('quality')),
                'preference': -10,
            })
            formats.append(f)

    def _extract_entry(self, url, player, content, video_id):
        title = content.get('title') or content['teaserHeadline']

        t = content['mainVideoContent']['http://zdf.de/rels/target']

        ptmd_path = t.get('http://zdf.de/rels/streams/ptmd')

        if not ptmd_path:
            ptmd_path = t[
                'http://zdf.de/rels/streams/ptmd-template'].replace(
                '{playerId}', 'ngplayer_2_4')

        ptmd = self._call_api(
            urljoin(url, ptmd_path), player, url, video_id, 'metadata')

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
                            video_id, formats, track_uris, {
                                'url': track.get('uri'),
                                'type': f.get('type'),
                                'mimeType': f.get('mimeType'),
                                'quality': quality.get('quality'),
                                'language': track.get('language'),
                            })
        self._sort_formats(formats)

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

        return {
            'id': video_id,
            'title': title,
            'description': content.get('leadParagraph') or content.get('teasertext'),
            'duration': int_or_none(t.get('duration')),
            'timestamp': unified_timestamp(content.get('editorialDate')),
            'thumbnails': thumbnails,
            'subtitles': self._extract_subtitles(ptmd),
            'formats': formats,
        }

    def _extract_regular(self, url, player, video_id):
        content = self._call_api(
            player['content'], player, url, video_id, 'content')
        return self._extract_entry(player['content'], player, content, video_id)

    def _extract_mobile(self, video_id):
        document = self._download_json(
            'https://zdf-cdn.live.cellular.de/mediathekV2/document/%s' % video_id,
            video_id)['document']

        title = document['titel']

        formats = []
        format_urls = set()
        for f in document['formitaeten']:
            self._extract_format(video_id, formats, format_urls, f)
        self._sort_formats(formats)

        thumbnails = []
        teaser_bild = document.get('teaserBild')
        if isinstance(teaser_bild, dict):
            for thumbnail_key, thumbnail in teaser_bild.items():
                thumbnail_url = try_get(
                    thumbnail, lambda x: x['url'], compat_str)
                if thumbnail_url:
                    thumbnails.append({
                        'url': thumbnail_url,
                        'id': thumbnail_key,
                        'width': int_or_none(thumbnail.get('width')),
                        'height': int_or_none(thumbnail.get('height')),
                    })

        return {
            'id': video_id,
            'title': title,
            'description': document.get('beschreibung'),
            'duration': int_or_none(document.get('length')),
            'timestamp': unified_timestamp(try_get(
                document, lambda x: x['meta']['editorialDate'], compat_str)),
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
            'title': 'das aktuelle sportstudio | ZDF',
        },
        'playlist_mincount': 23,
    }, {
        'url': 'https://www.zdf.de/dokumentation/planet-e',
        'info_dict': {
            'id': 'planet-e',
            'title': 'planet e.',
        },
        'playlist_mincount': 50,
    }, {
        'url': 'https://www.zdf.de/filme/taunuskrimi/',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if ZDFIE.suitable(url) else super(ZDFChannelIE, cls).suitable(url)

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        webpage = self._download_webpage(url, channel_id)

        entries = [
            self.url_result(item_url, ie=ZDFIE.ie_key())
            for item_url in orderedSet(re.findall(
                r'data-plusbar-url=["\'](http.+?\.html)', webpage))]

        return self.playlist_result(
            entries, channel_id, self._og_search_title(webpage, fatal=False))

        r"""
        player = self._extract_player(webpage, channel_id)

        channel_id = self._search_regex(
            r'docId\s*:\s*(["\'])(?P<id>(?!\1).+?)\1', webpage,
            'channel id', group='id')

        channel = self._call_api(
            'https://api.zdf.de/content/documents/%s.json' % channel_id,
            player, url, channel_id)

        items = []
        for module in channel['module']:
            for teaser in try_get(module, lambda x: x['teaser'], list) or []:
                t = try_get(
                    teaser, lambda x: x['http://zdf.de/rels/target'], dict)
                if not t:
                    continue
                items.extend(try_get(
                    t,
                    lambda x: x['resultsWithVideo']['http://zdf.de/rels/search/results'],
                    list) or [])
            items.extend(try_get(
                module,
                lambda x: x['filterRef']['resultsWithVideo']['http://zdf.de/rels/search/results'],
                list) or [])

        entries = []
        entry_urls = set()
        for item in items:
            t = try_get(item, lambda x: x['http://zdf.de/rels/target'], dict)
            if not t:
                continue
            sharing_url = t.get('http://zdf.de/rels/sharing-url')
            if not sharing_url or not isinstance(sharing_url, compat_str):
                continue
            if sharing_url in entry_urls:
                continue
            entry_urls.add(sharing_url)
            entries.append(self.url_result(
                sharing_url, ie=ZDFIE.ie_key(), video_id=t.get('id')))

        return self.playlist_result(entries, channel_id, channel.get('title'))
        """
