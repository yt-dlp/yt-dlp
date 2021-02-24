# coding: utf-8
from __future__ import unicode_literals

import re

from .theplatform import ThePlatformBaseIE
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    update_url_query,
)


class MediasetIE(ThePlatformBaseIE):
    _TP_TLD = 'eu'
    _VALID_URL = r'''(?x)
                    (?:
                        mediaset:|
                        https?://
                            (?:(?:www|static3)\.)?mediasetplay\.mediaset\.it/
                            (?:
                                (?:video|on-demand|movie)/(?:[^/]+/)+[^/]+_|
                                player/index\.html\?.*?\bprogramGuid=
                            )
                    )(?P<id>[0-9A-Z]{16,})
                    '''
    _TESTS = [{
        # full episode
        'url': 'https://www.mediasetplay.mediaset.it/video/hellogoodbye/quarta-puntata_FAFU000000661824',
        'md5': '9b75534d42c44ecef7bf1ffeacb7f85d',
        'info_dict': {
            'id': 'FAFU000000661824',
            'ext': 'mp4',
            'title': 'Quarta puntata',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1414.26,
            'upload_date': '20161107',
            'series': 'Hello Goodbye',
            'timestamp': 1478532900,
            'uploader': 'Rete 4',
            'uploader_id': 'R4',
        },
    }, {
        'url': 'https://www.mediasetplay.mediaset.it/video/matrix/puntata-del-25-maggio_F309013801000501',
        'md5': '288532f0ad18307705b01e581304cd7b',
        'info_dict': {
            'id': 'F309013801000501',
            'ext': 'mp4',
            'title': 'Puntata del 25 maggio',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 6565.007,
            'upload_date': '20180526',
            'series': 'Matrix',
            'timestamp': 1527326245,
            'uploader': 'Canale 5',
            'uploader_id': 'C5',
        },
    }, {
        # clip
        'url': 'https://www.mediasetplay.mediaset.it/video/gogglebox/un-grande-classico-della-commedia-sexy_FAFU000000661680',
        'only_matching': True,
    }, {
        # iframe simple
        'url': 'https://static3.mediasetplay.mediaset.it/player/index.html?appKey=5ad3966b1de1c4000d5cec48&programGuid=FAFU000000665924&id=665924',
        'only_matching': True,
    }, {
        # iframe twitter (from http://www.wittytv.it/se-prima-mi-fidavo-zero/)
        'url': 'https://static3.mediasetplay.mediaset.it/player/index.html?appKey=5ad3966b1de1c4000d5cec48&programGuid=FAFU000000665104&id=665104',
        'only_matching': True,
    }, {
        'url': 'mediaset:FAFU000000665924',
        'only_matching': True,
    }, {
        'url': 'https://www.mediasetplay.mediaset.it/video/mediasethaacuoreilfuturo/palmieri-alicudi-lisola-dei-tre-bambini-felici--un-decreto-per-alicudi-e-tutte-le-microscuole_FD00000000102295',
        'only_matching': True,
    }, {
        'url': 'https://www.mediasetplay.mediaset.it/video/cherryseason/anticipazioni-degli-episodi-del-23-ottobre_F306837101005C02',
        'only_matching': True,
    }, {
        'url': 'https://www.mediasetplay.mediaset.it/video/tg5/ambiente-onda-umana-per-salvare-il-pianeta_F309453601079D01',
        'only_matching': True,
    }, {
        'url': 'https://www.mediasetplay.mediaset.it/video/grandefratellovip/benedetta-una-doccia-gelata_F309344401044C135',
        'only_matching': True,
    }, {
        'url': 'https://www.mediasetplay.mediaset.it/movie/herculeslaleggendahainizio/hercules-la-leggenda-ha-inizio_F305927501000102',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(ie, webpage):
        def _qs(url):
            return compat_parse_qs(compat_urllib_parse_urlparse(url).query)

        def _program_guid(qs):
            return qs.get('programGuid', [None])[0]

        entries = []
        for mobj in re.finditer(
                r'<iframe\b[^>]+\bsrc=(["\'])(?P<url>(?:https?:)?//(?:www\.)?video\.mediaset\.it/player/playerIFrame(?:Twitter)?\.shtml.*?)\1',
                webpage):
            embed_url = mobj.group('url')
            embed_qs = _qs(embed_url)
            program_guid = _program_guid(embed_qs)
            if program_guid:
                entries.append(embed_url)
                continue
            video_id = embed_qs.get('id', [None])[0]
            if not video_id:
                continue
            urlh = ie._request_webpage(
                embed_url, video_id, note='Following embed URL redirect')
            embed_url = urlh.geturl()
            program_guid = _program_guid(_qs(embed_url))
            if program_guid:
                entries.append(embed_url)
        return entries

    def _parse_smil_formats(self, smil, smil_url, video_id, namespace=None, f4m_params=None, transform_rtmp_url=None):
        for video in smil.findall(self._xpath_ns('.//video', namespace)):
            video.attrib['src'] = re.sub(r'(https?://vod05)t(-mediaset-it\.akamaized\.net/.+?.mpd)\?.+', r'\1\2', video.attrib['src'])
        return super(MediasetIE, self)._parse_smil_formats(smil, smil_url, video_id, namespace, f4m_params, transform_rtmp_url)

    def _real_extract(self, url):
        guid = self._match_id(url)
        tp_path = 'PR1GhC/media/guid/2702976343/' + guid
        info = self._extract_theplatform_metadata(tp_path, guid)

        formats = []
        subtitles = {}
        first_e = None
        for asset_type in ('SD', 'HD'):
            # TODO: fixup ISM+none manifest URLs
            for f in ('MPEG4', 'MPEG-DASH+none', 'M3U+none'):
                try:
                    tp_formats, tp_subtitles = self._extract_theplatform_smil(
                        update_url_query('http://link.theplatform.%s/s/%s' % (self._TP_TLD, tp_path), {
                            'mbr': 'true',
                            'formats': f,
                            'assetTypes': asset_type,
                        }), guid, 'Downloading %s %s SMIL data' % (f.split('+')[0], asset_type))
                except ExtractorError as e:
                    if not first_e:
                        first_e = e
                    break
                for tp_f in tp_formats:
                    tp_f['quality'] = 1 if asset_type == 'HD' else 0
                formats.extend(tp_formats)
                subtitles = self._merge_subtitles(subtitles, tp_subtitles)
        if first_e and not formats:
            raise first_e
        self._sort_formats(formats)

        fields = []
        for templ, repls in (('tvSeason%sNumber', ('', 'Episode')), ('mediasetprogram$%s', ('brandTitle', 'numberOfViews', 'publishInfo'))):
            fields.extend(templ % repl for repl in repls)
        feed_data = self._download_json(
            'https://feed.entertainment.tv.theplatform.eu/f/PR1GhC/mediaset-prod-all-programs/guid/-/' + guid,
            guid, fatal=False, query={'fields': ','.join(fields)})
        if feed_data:
            publish_info = feed_data.get('mediasetprogram$publishInfo') or {}
            info.update({
                'episode_number': int_or_none(feed_data.get('tvSeasonEpisodeNumber')),
                'season_number': int_or_none(feed_data.get('tvSeasonNumber')),
                'series': feed_data.get('mediasetprogram$brandTitle'),
                'uploader': publish_info.get('description'),
                'uploader_id': publish_info.get('channel'),
                'view_count': int_or_none(feed_data.get('mediasetprogram$numberOfViews')),
            })

        info.update({
            'id': guid,
            'formats': formats,
            'subtitles': subtitles,
        })
        return info
