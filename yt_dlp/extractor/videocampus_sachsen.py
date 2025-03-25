import functools
import re

from .common import InfoExtractor
from ..utils import OnDemandPagedList, traverse_obj, urlencode_postdata


class VideocampusSachsenIE(InfoExtractor):
    IE_NAME = 'ViMP'
    _INSTANCES = (
        'bergauf.tv',
        'campus.demo.vimp.com',
        'corporate.demo.vimp.com',
        'dancehalldatabase.com',
        'demo.edu.medvc.eu',
        'drehzahl.tv',
        'educhannel.hs-gesundheit.de',  # Hochschule für Gesundheit NRW
        'emedia.ls.haw-hamburg.de',
        'etat.kiss.lu',
        'fabi.test.vimp.com',
        'globale-evolution.net',
        'hohu.tv',
        'htvideos.hightechhigh.org',
        'k210039.vimp.mivitec.net',
        'media.cmslegal.com',
        'media.fh-swf.de',  # Fachhochschule Südwestfalen
        'media.hs-furtwangen.de',  # Hochschule Furtwangen
        'media.hwr-berlin.de',  # Hochschule für Wirtschaft und Recht Berlin
        'mediacast.math.tku.edu.tw',
        'mediathek.dkfz.de',
        'mediathek.htw-berlin.de',  # Hochschule für Technik und Wirtschaft Berlin
        'mediathek.polizei-bw.de',
        'mediathek.rheinmaintv.de',
        'medien.hs-merseburg.de',  # Hochschule Merseburg
        'medienportal.hs-ansbach.de',  # Hochschule Ansbach
        'mitmedia.manukau.ac.nz',  # Manukau Institute of Technology Auckland (NZ)
        'mportal.europa-uni.de',  # Europa-Universität Viadrina
        'multimedia.blue',
        'oraniontest.vimp.com',
        'pacific.demo.vimp.com',
        'slctv.com',
        'streaming.prairiesouth.ca',
        'tube.isbonline.cn',
        'univideo.uni-kassel.de',  # Universität Kassel
        'ursula2.genetics.emory.edu',
        'ursulablicklevideoarchiv.com',
        'v.agrarumweltpaedagogik.at',
        'video-test.hrz.tu-chemnitz.de',
        'video.biotest.com',
        'video.desy.de',
        'video.eplay-tv.de',
        'video.fh-dortmund.de',  # Fachhochschule Dortmund
        'video.hcu-hamburg.de',  # HafenCity Universität Hamburg
        'video.hs-coburg.de',  # Hochschule Coburg
        'video.hs-nb.de',  # Hochschule Neubrandenburg
        'video.hs-offenburg.de',  # Hochschule Offenburg
        'video.hs-pforzheim.de',  # Hochschule Pforzheim
        'video.hspv.nrw.de',  # Hochschule für Polizei und öffentliche Verwaltung NRW
        'video.irtshdf.fr',
        'video.medi.ch',
        'video.tu-dortmund.de',  # Technische Universität Dortmund
        'video.tu-freiberg.de',  # Technische Universität Bergakademie Freiberg
        'video.viscom.com',
        'videocampus.sachsen.de',  # Video Campus Sachsen (gemeinsame Videoplattform sächsischer Universitäten, Hochschulen und der Berufsakademie Sachsen)
        'videoportal.uni-freiburg.de',  # Albert-Ludwigs-Universität Freiburg
        'videoportal.vm.uni-freiburg.de',  # Albert-Ludwigs-Universität Freiburg
        'videos.duoc.cl',
        'videos.uni-paderborn.de',  # Universität Paderborn
        'vimp-bemus.udk-berlin.de',
        'vimp.aekwl.de',
        'vimp.hs-mittweida.de',
        'vimp.item24.com',
        'vimp.landesfilmdienste.de',
        'vimp.oth-regensburg.de',  # Ostbayerische Technische Hochschule Regensburg
        'vimp.ph-gmuend.de',  # Pädagogische Hochschule Schwäbisch Gmünd
        'vimp.ph-heidelberg.de',  # Pädagogische Hochschule Heidelberg
        'vimp.spk-vorpommern.de',
        'vimp.volksbank-goeppingen.de',
        'vimp.weka-fachmedien.de',
        'vimpdesk.com',
        'vod.dma.swiss',
        'webtv.univ-montp3.fr',
        'www.b-tu.de/media',  # Brandenburgische Technische Universität Cottbus-Senftenberg
        'www.bergauf.tv',
        'www.bigcitytv.de',
        'www.cad-videos.de',
        'www.drehzahl.tv',
        'www.hohu.tv',
        'www.hsbi.de/medienportal',  # Hochschule Bielefeld
        'www.logistic.tv',
        'www.orvovideo.com',
        'www.printtube.co.uk',
        'www.rwe.tv',
        'www.salzi.tv',
        'www.signtube.co.uk',
        'www.twb-power.com',
        'www.videos.hfm.saarland.de',
        'www.wenglor-media.com',
        'www2.univ-sba.dz',
    )
    _VALID_URL = r'''(?x)https?://(?P<host>{})/(?:
        m/(?P<tmp_id>[0-9a-f]+)|
        (?:category/)?video/(?P<display_id>[\w-]+)/(?P<id>[0-9a-f]{{32}})|
        media/embed.*(?:\?|&)key=(?P<embed_id>[0-9a-f]{{32}}&?)
    )'''.format('|'.join(map(re.escape, _INSTANCES)))

    _TESTS = [
        # non-standard hls location
        {
            'url': 'https://video.desy.de/video/vakuum-begreifen-luftwiderstand/d60d3682854de441d0ed092e2c825f6e',
            'info_dict': {
                'id': 'd60d3682854de441d0ed092e2c825f6e',
                'title': 'Vakuum begreifen: Luftwiderstand',
                # as the url suggests the thumbnail images files live in the
                # cache, urls will change from time to time
                'thumbnail': 'https://video.desy.de/cache/c1180148290d5ce154de7f821f432b8e.png',
                'display_id': 'vakuum-begreifen-luftwiderstand',
                'ext': 'mp4',
            },
        },
        # no hls but mp4 with different qualities
        {
            'url': 'https://video.hcu-hamburg.de/video/stahl-und-holzbau-2-handout-2/29c45dae21191bce493e4ea18cc929a4',
            'info_dict': {
                'id': '29c45dae21191bce493e4ea18cc929a4',
                'title': 'Stahl- und Holzbau 2 - Handout 2',
                'thumbnail': 'https://video.hcu-hamburg.de/cache/7ae482b7ba22c01a0a2426df7da9e854.png',
                'display_id': 'stahl-und-holzbau-2-handout-2',
                'ext': 'mp4',
            },
        },
        # no player options
        {
            'url': 'https://video.tu-freiberg.de/video/schauvorlesung-/19ffd2eb8a82b080b7a23c2b70a4c1a1',
            'info_dict': {
                'id': '19ffd2eb8a82b080b7a23c2b70a4c1a1',
                'title': 'Schauvorlesung Fakultät 2 - 2024',
                'description': 'md5:229b686fd94e801d7ffef6531c8710fb',
                'thumbnail': 'https://video.tu-freiberg.de/cache/42ea37d0223e2e3905a850463bd8d6d5.png',
                'display_id': 'schauvorlesung-',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://videocampus.sachsen.de/m/e0d6c8ce6e394c188f1342f1ab7c50ed6fc4490b808699801def5cb2e46d76ca7367f622a9f516c542ffb805b24d6b643bd7c81f385acaac4c59081b87a2767b',
            'info_dict': {
                'id': 'e6b9349905c1628631f175712250f2a1',
                'title': 'Konstruktiver Entwicklungsprozess Vorlesung 7',
                'thumbnail': 'https://videocampus.sachsen.de/cache/6730fb25578cf4e00cd6afbdc977585e.png',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://videocampus.sachsen.de/video/Was-ist-selbstgesteuertes-Lernen/fc99c527e4205b121cb7c74433469262',
            'info_dict': {
                'id': 'fc99c527e4205b121cb7c74433469262',
                'title': 'Was ist selbstgesteuertes Lernen?',
                'thumbnail': 'https://videocampus.sachsen.de/cache/a7765658ac3df9e75947a4d06aef7402.png',
                'display_id': 'Was-ist-selbstgesteuertes-Lernen',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://videocampus.sachsen.de/category/video/Tutorial-zur-Nutzung-von-Adobe-Connect-aus-Veranstalter-Sicht/09d4ed029002eb1bdda610f1103dd54c/100',
            'info_dict': {
                'id': '09d4ed029002eb1bdda610f1103dd54c',
                'title': 'Tutorial zur Nutzung von Adobe Connect aus Veranstalter-Sicht',
                'thumbnail': 'https://videocampus.sachsen.de/cache/173fc4fe2133cc41b2905ca8976a4760.png',
                'display_id': 'Tutorial-zur-Nutzung-von-Adobe-Connect-aus-Veranstalter-Sicht',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://vimp.weka-fachmedien.de/video/Preisverleihung-Produkte-des-Jahres-2022/c8816f1cc942c12b6cce57c835cffd7c',
            'info_dict': {
                'id': 'c8816f1cc942c12b6cce57c835cffd7c',
                'title': 'Preisverleihung »Produkte des Jahres 2022«',
                'description': 'md5:60c347568ca89aa25b772c4ea564ebd3',
                'thumbnail': 'https://vimp.weka-fachmedien.de/cache/da9f3090e9227b25beacf67ccf94de14.png',
                'display_id': 'Preisverleihung-Produkte-des-Jahres-2022',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://videocampus.sachsen.de/media/embed?key=fc99c527e4205b121cb7c74433469262',
            'info_dict': {
                'id': 'fc99c527e4205b121cb7c74433469262',
                'title': 'Was ist selbstgesteuertes Lernen?',
                'thumbnail': 'https://videocampus.sachsen.de/cache/a7765658ac3df9e75947a4d06aef7402.png',
                'ext': 'mp4',
            },
        },
    ]

    def _real_extract(self, url):
        host, video_id, tmp_id, display_id, embed_id = self._match_valid_url(url).group(
            'host', 'id', 'tmp_id', 'display_id', 'embed_id')
        webpage = self._download_webpage(url, video_id or tmp_id, fatal=False) or ''

        formats, subtitles = [], {}
        title = description = thumbnail = None

        metadata = self._search_json(r'var\s+options\s*=\s*', webpage, 'player options', video_id or tmp_id or embed_id, default=None, fatal=False)

        if metadata:
            for source in metadata.get('sources', []):
                if source.get('type') == 'application/x-mpegURL' and source.get('src'):
                    _formats, _subtitles = self._extract_m3u8_formats_and_subtitles(source.get('src'), video_id or tmp_id or embed_id, fatal=False)
                    formats.extend(_formats)
                    subtitles.update(_subtitles)
                elif source.get('src'):
                    formats.append({'url': source.get('src')})

            thumbnail = f'https://{host}{metadata.get('poster')}'
            video_id = traverse_obj(metadata, ('videojsVimpOptions', 'Mediakey'))
        else:
            thumbnail = self._html_search_meta(('og:image', 'twitter:image'), webpage, fatal=False)
            description = self._html_search_meta(('og:description', 'twitter:description', 'description'), webpage, fatal=False)
            title = self._html_search_meta(('og:title', 'twitter:title', 'title'), webpage, fatal=False)

        if not title:
            title = self._html_search_regex(r'<h1[^>]*>([^<]+)</h1>', webpage, 'title', default=None, fatal=False)
        if not title:
            embed_data = self._download_json(f'https://{host}/media/embedCode', video_id, data=f'key={video_id}'.encode(), fatal=False)
            if embed_data:
                title = self._html_search_regex(r'title="([^"]+)"', embed_data.get('embedCode', ''), 'title', fatal=False)

        formats.append({'url': f'https://{host}/getMedium/{video_id}.mp4'})

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
        }


class ViMPPlaylistIE(InfoExtractor):
    IE_NAME = 'ViMP:Playlist'
    _VALID_URL = r'''(?x)(?P<host>https?://(?:{}))/(?:
        (?P<mode1>album)/view/aid/(?P<album_id>[0-9]+)|
        (?P<mode2>category|channel)/(?P<name>[\w-]+)/(?P<channel_id>[0-9]+)|
        (?P<mode3>tag)/(?P<tag_id>[0-9]+)
    )'''.format('|'.join(map(re.escape, VideocampusSachsenIE._INSTANCES)))

    _TESTS = [{
        'url': 'https://vimp.oth-regensburg.de/channel/Designtheorie-1-SoSe-2020/3',
        'info_dict': {
            'id': 'channel-3',
            'title': 'Designtheorie 1 SoSe 2020 - Channels - ViMP OTH Regensburg',
        },
        'playlist_mincount': 9,
    }, {
        'url': 'https://www.hsbi.de/medienportal/album/view/aid/208',
        'info_dict': {
            'id': 'album-208',
            'title': 'KG Praktikum ABT/MEC - Playlists - HSBI-Medienportal',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'https://videocampus.sachsen.de/category/online-tutorials-onyx/91',
        'info_dict': {
            'id': 'category-91',
            'title': 'Online-Seminare ONYX - BPS - Bildungseinrichtungen - VCS',
        },
        'playlist_mincount': 7,
    }, {
        'url': 'https://videocampus.sachsen.de/tag/26902',
        'info_dict': {
            'id': 'tag-26902',
            'title': 'advanced mobile and v2x communication - Tags - VCS',
        },
        'playlist_mincount': 6,
    }]
    _PAGE_SIZE = 10

    def _fetch_page(self, host, url_part, playlist_id, data, page):
        webpage = self._download_webpage(
            f'{host}/media/ajax/component/boxList/{url_part}', playlist_id,
            query={'page': page, 'page_only': 1}, data=urlencode_postdata(data))
        urls = re.findall(r'"([^"]*/video/[^"]+)"', webpage)

        for url in urls:
            yield self.url_result(host + url, VideocampusSachsenIE)

    def _real_extract(self, url):
        host, album_id, name, channel_id, tag_id, mode1, mode2, mode3 = self._match_valid_url(url).group(
            'host', 'album_id', 'name', 'channel_id', 'tag_id', 'mode1', 'mode2', 'mode3')

        mode = mode1 or mode2 or mode3
        playlist_id = album_id or channel_id or tag_id

        webpage = self._download_webpage(url, playlist_id, fatal=False) or ''
        title = (self._html_search_meta('title', webpage, fatal=False)
                 or self._html_extract_title(webpage))

        url_part = (f'aid/{album_id}' if album_id
                    else f'category/{name}/category_id/{channel_id}' if mode == 'category'
                    else f'title/{name}/channel/{channel_id}' if mode == 'channel'
                    else f'tag/{tag_id}')

        data = {
            'vars[mode]': mode,
            f'vars[{mode}]': playlist_id,
            'vars[context]': '4' if album_id else '1' if mode == 'category' else '3' if mode == 'album' else '0',
            'vars[context_id]': playlist_id,
            'vars[layout]': 'thumb',
            'vars[per_page][thumb]': str(self._PAGE_SIZE),
        }

        return self.playlist_result(
            OnDemandPagedList(functools.partial(
                self._fetch_page, host, url_part, playlist_id, data), self._PAGE_SIZE),
            playlist_title=title, id=f'{mode}-{playlist_id}')
