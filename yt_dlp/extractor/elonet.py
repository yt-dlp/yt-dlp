# coding: utf-8
from __future__ import unicode_literals

import os
import re
import tempfile

from .common import InfoExtractor
from ..utils import (
    base_url,
    ExtractorError,
    try_get,
)
from ..compat import compat_str
from ..downloader.hls import HlsFD


class ElonetIE(InfoExtractor):
    _VALID_URL = r'https?://elonet\.finna\.fi/Record/kavi\.elonet_elokuva_(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_107867',
        'md5': '8efc954b96c543711707f87de757caea',
        'info_dict': {
            'id': '107867',
            'ext': 'mp4',
            'title': 'Valkoinen peura',
            'description': 'Valkoinen peura (1952) on Erik Blombergin ohjaama ja yhdessä Mirjami Kuosmasen kanssa käsikirjoittama tarunomainen kertomus valkoisen peuran hahmossa lii...',
            'thumbnail': 'https://elonet.finna.fi/Cover/Show?id=kavi.elonet_elokuva_107867&index=0&size=large',
        },
    }

    def _download_m3u8_chunked_subtitle(self, chunklist_url):
        """
        Download VTT subtitles from pieces in manifest URL.
        Return a string containing joined chunks with extra headers removed.
        """
        with tempfile.NamedTemporaryFile(delete=True) as outfile:
            fname = outfile.name
        hlsdl = HlsFD(self._downloader, {})
        hlsdl.download(compat_str(fname), {"url": chunklist_url})
        with open(fname, 'r') as fin:
            # Remove (some) headers
            fdata = re.sub(r'X-TIMESTAMP-MAP.*\n+|WEBVTT\n+', '', fin.read())
        os.remove(fname)
        return "WEBVTT\n\n" + fdata

    def _parse_m3u8_subtitles(self, m3u8_doc, m3u8_url):
        """
        Parse subtitles from HLS / m3u8 manifest.
        """
        subtitles = {}
        baseurl = m3u8_url[:m3u8_url.rindex('/') + 1]
        for line in m3u8_doc.split('\n'):
            if 'EXT-X-MEDIA:TYPE=SUBTITLES' in line:
                lang = self._search_regex(
                    r'LANGUAGE="(.+?)"', line, 'lang', default=False)
                uri = self._search_regex(
                    r'URI="(.+?)"', line, 'uri', default=False)
                if lang and uri:
                    data = self._download_m3u8_chunked_subtitle(baseurl + uri)
                    subtitles[lang] = [{'ext': 'vtt', 'data': data}]
        return subtitles

    def _parse_mpd_subtitles(self, mpd_doc):
        """
        Parse subtitles from MPD manifest.
        """
        ns = '{urn:mpeg:dash:schema:mpd:2011}'
        subtitles = {}
        for aset in mpd_doc.findall(".//%sAdaptationSet[@mimeType='text/vtt']" % (ns)):
            lang = aset.attrib.get('lang', 'unk')
            url = aset.find("./%sRepresentation/%sBaseURL" % (ns, ns)).text
            subtitles[lang] = [{'ext': 'vtt', 'url': url}]
        return subtitles

    def _get_subtitles(self, fmt, doc, url):
        if fmt == 'm3u8':
            subs = self._parse_m3u8_subtitles(doc, url)
        elif fmt == 'mpd':
            subs = self._parse_mpd_subtitles(doc)
        else:
            self._downloader.report_warning(
                "Cannot download subtitles from '%s' streams." % (fmt))
            subs = {}
        return subs

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(
            r'<meta .*property="og&#x3A;title" .*content="(.+?)"', webpage, 'title')
        description = self._html_search_regex(
            r'<meta .*property="og&#x3A;description" .*content="(.+?)"', webpage, 'description')
        thumbnail = self._html_search_regex(
            r'<meta .*property="og&#x3A;image" .*content="(.+?)"', webpage, 'thumbnail')

        json_s = self._html_search_regex(
            r'data-video-sources="(.+?)"', webpage, 'json')
        src = try_get(
            self._parse_json(json_s, video_id),
            lambda x: x[0]["src"], compat_str)
        formats = []
        if re.search(r'\.m3u8\??', src):
            fmt = 'm3u8'
            res = self._download_webpage_handle(
                # elonet servers have certificate problems
                src.replace('https:', 'http:'), video_id,
                note='Downloading m3u8 information',
                errnote='Failed to download m3u8 information')
            if res:
                doc, urlh = res
                url = urlh.geturl()
                formats = self._parse_m3u8_formats(doc, url)
                for f in formats:
                    f['ext'] = 'mp4'
        elif re.search(r'\.mpd\??', src):
            fmt = 'mpd'
            res = self._download_xml_handle(
                src, video_id,
                note='Downloading MPD manifest',
                errnote='Failed to download MPD manifest')
            if res:
                doc, urlh = res
                url = base_url(urlh.geturl())
                formats = self._parse_mpd_formats(doc, mpd_base_url=url)
        else:
            raise ExtractorError("Unknown streaming format")

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'subtitles': self.extract_subtitles(fmt, doc, url),
        }
