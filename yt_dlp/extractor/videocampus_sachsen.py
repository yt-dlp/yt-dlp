import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    ExtractorError,
    urlencode_postdata,
)


class VideocampusSachsenIE(InfoExtractor):
    IE_NAME = 'ViMP'
    _INSTANCES = (
        'bergauf.tv',
        'campus.demo.vimp.com',
        'corporate.demo.vimp.com',
        'dancehalldatabase.com',
        'drehzahl.tv',
        'educhannel.hs-gesundheit.de',
        'emedia.ls.haw-hamburg.de',
        'globale-evolution.net',
        'hohu.tv',
        'htvideos.hightechhigh.org',
        'k210039.vimp.mivitec.net',
        'media.cmslegal.com',
        'media.hs-furtwangen.de',
        'media.hwr-berlin.de',
        'mediathek.dkfz.de',
        'mediathek.htw-berlin.de',
        'mediathek.polizei-bw.de',
        'medien.hs-merseburg.de',
        'mportal.europa-uni.de',
        'pacific.demo.vimp.com',
        'slctv.com',
        'streaming.prairiesouth.ca',
        'tube.isbonline.cn',
        'univideo.uni-kassel.de',
        'ursula2.genetics.emory.edu',
        'ursulablicklevideoarchiv.com',
        'v.agrarumweltpaedagogik.at',
        'video.eplay-tv.de',
        'video.fh-dortmund.de',
        'video.hs-offenburg.de',
        'video.hs-pforzheim.de',
        'video.hspv.nrw.de',
        'video.irtshdf.fr',
        'video.pareygo.de',
        'video.tu-freiberg.de',
        'videocampus.sachsen.de',
        'videoportal.uni-freiburg.de',
        'videoportal.vm.uni-freiburg.de',
        'videos.duoc.cl',
        'videos.uni-paderborn.de',
        'vimp-bemus.udk-berlin.de',
        'vimp.aekwl.de',
        'vimp.hs-mittweida.de',
        'vimp.oth-regensburg.de',
        'vimp.ph-heidelberg.de',
        'vimp.sma-events.com',
        'vimp.weka-fachmedien.de',
        'webtv.univ-montp3.fr',
        'www.b-tu.de/media',
        'www.bergauf.tv',
        'www.bigcitytv.de',
        'www.cad-videos.de',
        'www.drehzahl.tv',
        'www.fh-bielefeld.de/medienportal',
        'www.hohu.tv',
        'www.orvovideo.com',
        'www.rwe.tv',
        'www.salzi.tv',
        'www.wenglor-media.com',
        'www2.univ-sba.dz',
    )
    _VALID_URL = r'''(?x)https?://(?P<host>%s)/(?:
        m/(?P<tmp_id>[0-9a-f]+)|
        (?:category/)?video/(?P<display_id>[\w-]+)/(?P<id>[0-9a-f]{32})|
        media/embed.*(?:\?|&)key=(?P<embed_id>[0-9a-f]{32}&?)
    )''' % ('|'.join(map(re.escape, _INSTANCES)))

    _TESTS = [
        {
            'url': 'https://videocampus.sachsen.de/m/e0d6c8ce6e394c188f1342f1ab7c50ed6fc4490b808699801def5cb2e46d76ca7367f622a9f516c542ffb805b24d6b643bd7c81f385acaac4c59081b87a2767b',
            'info_dict': {
                'id': 'e6b9349905c1628631f175712250f2a1',
                'title': 'Konstruktiver Entwicklungsprozess Vorlesung 7',
                'description': 'Konstruktiver Entwicklungsprozess Vorlesung 7',
                'thumbnail': 'https://videocampus.sachsen.de/cache/1a985379ad3aecba8097a6902c7daa4e.jpg',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://videocampus.sachsen.de/video/Was-ist-selbstgesteuertes-Lernen/fc99c527e4205b121cb7c74433469262',
            'info_dict': {
                'id': 'fc99c527e4205b121cb7c74433469262',
                'title': 'Was ist selbstgesteuertes Lernen?',
                'description': 'md5:196aa3b0509a526db62f84679522a2f5',
                'thumbnail': 'https://videocampus.sachsen.de/cache/6f4a85096ba24cb398e6ce54446b57ae.jpg',
                'display_id': 'Was-ist-selbstgesteuertes-Lernen',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://videocampus.sachsen.de/category/video/Tutorial-zur-Nutzung-von-Adobe-Connect-aus-Veranstalter-Sicht/09d4ed029002eb1bdda610f1103dd54c/100',
            'info_dict': {
                'id': '09d4ed029002eb1bdda610f1103dd54c',
                'title': 'Tutorial zur Nutzung von Adobe Connect aus Veranstalter-Sicht',
                'description': 'md5:3d379ca3cc17b9da6784d7f58cca4d58',
                'thumbnail': 'https://videocampus.sachsen.de/cache/2452498fe8c2d5a7dc79a05d30f407b6.jpg',
                'display_id': 'Tutorial-zur-Nutzung-von-Adobe-Connect-aus-Veranstalter-Sicht',
                'ext': 'mp4',
            },
        },
        {
            'url': 'https://www2.univ-sba.dz/video/Presentation-de-la-Faculte-de-droit-et-des-sciences-politiques-Journee-portes-ouvertes-202122/0183356e41af7bfb83d7667b20d9b6a3',
            'info_dict': {
                'url': 'https://www2.univ-sba.dz/getMedium/0183356e41af7bfb83d7667b20d9b6a3.mp4',
                'id': '0183356e41af7bfb83d7667b20d9b6a3',
                'title': 'Présentation de la Faculté de droit et des sciences politiques - Journée portes ouvertes 2021/22',
                'description': 'md5:508958bd93e0ca002ac731d94182a54f',
                'thumbnail': 'https://www2.univ-sba.dz/cache/4d5d4a0b4189271a8cc6cb5328e14769.jpg',
                'display_id': 'Presentation-de-la-Faculte-de-droit-et-des-sciences-politiques-Journee-portes-ouvertes-202122',
                'ext': 'mp4',
            }
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
                'ext': 'mp4',
            },
        },
    ]

    def _real_extract(self, url):
        host, video_id, tmp_id, display_id, embed_id = self._match_valid_url(url).group(
            'host', 'id', 'tmp_id', 'display_id', 'embed_id')
        webpage = self._download_webpage(url, video_id or tmp_id, fatal=False) or ''

        if not video_id:
            video_id = embed_id or self._html_search_regex(
                rf'src="https?://{host}/media/embed.*(?:\?|&)key=([0-9a-f]+)&?',
                webpage, 'video_id')

        if not (display_id or tmp_id):
            # Title, description from embedded page's meta wouldn't be correct
            title = self._html_search_regex(r'<video-js[^>]* data-piwik-title="([^"<]+)"', webpage, 'title', fatal=False)
            description = None
            thumbnail = None
        else:
            title = self._html_search_meta(('og:title', 'twitter:title', 'title'), webpage, fatal=False)
            description = self._html_search_meta(
                ('og:description', 'twitter:description', 'description'), webpage, fatal=False)
            thumbnail = self._html_search_meta(('og:image', 'twitter:image'), webpage, fatal=False)

        formats, subtitles = [], {}
        try:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                f'https://{host}/media/hlsMedium/key/{video_id}/format/auto/ext/mp4/learning/0/path/m3u8',
                video_id, 'mp4', m3u8_id='hls', fatal=True)
        except ExtractorError as e:
            if not isinstance(e.cause, compat_HTTPError) or e.cause.code not in (404, 500):
                raise

        formats.append({'url': f'https://{host}/getMedium/{video_id}.mp4'})
        self._sort_formats(formats)

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
    _VALID_URL = r'''(?x)(?P<host>https?://(?:%s))/(?:
        album/view/aid/(?P<album_id>[0-9]+)|(?P<c_mode>category|channel)/(?P<c_name>[\w-]+)/(?P<c_id>[0-9]+)
        )''' % ('|'.join(map(re.escape, VideocampusSachsenIE._INSTANCES)))

    _TESTS = [{
        'url': 'https://vimp.oth-regensburg.de/channel/Designtheorie-1-SoSe-2020/3',
        'info_dict': {
            'id': 'channel-3',
            'title': 'Designtheorie 1 SoSe 2020 :: Channels :: ViMP OTH Regensburg',
        },
        'playlist_mincount': 9,
    }, {
        'url': 'https://www.fh-bielefeld.de/medienportal/album/view/aid/208',
        'info_dict': {
            'id': 'album-208',
            'title': 'KG Praktikum ABT/MEC :: Playlists :: FH-Medienportal',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'https://videocampus.sachsen.de/category/online-tutorials-onyx/91',
        'info_dict': {
            'id': 'category-91',
            'title': 'Online-Seminare ONYX - BPS - Bildungseinrichtungen - VCS',
        },
        'playlist_mincount': 7,
    }]

    def _real_extract(self, url):
        host, album_id, c_mode, c_name, c_id = self._match_valid_url(url).group(
            'host', 'album_id', 'c_mode', 'c_name', 'c_id')

        webpage = self._download_webpage(url, album_id or c_id, fatal=False) or ''
        title = (self._html_search_meta('title', webpage, fatal=False)
                 or self._html_extract_title(webpage))

        if album_id:
            mode = 'album'
            mode_id = '4'
            content_id = album_id
            url_part = f'aid/{album_id}'
        else:
            url_parts = ('category', 'category_id') if c_mode == 'category' else ('title', 'channel')

            mode = c_mode
            mode_id = '1' if c_mode == 'category' else '3'
            content_id = c_id
            url_part = f'{url_parts[0]}/{c_name}/{url_parts[1]}/{c_id}'

        data = {
            'vars[mode]': mode,
            f'vars[{mode}]': content_id,
            'vars[context]': mode_id,
            'vars[context_id]': content_id,
            'vars[layout]': 'thumb',
            'vars[per_page][thumb]': '10',
        }

        urls, i = [], 1
        while True:
            current_page = self._download_webpage(
                f'{host}/media/ajax/component/boxList/{url_part}?page={i}&page_only=1',
                content_id, data=urlencode_postdata(data))
            current_urls = re.findall(r'"(.+?/video/.+?)"', current_page)

            # Request returns last n video URLs if existing pages have been "used up"
            if urls[-1:] != current_urls[-1:]:
                urls += current_urls
                i += 1
            else:
                break

        return self.playlist_result(
            (self.url_result(host + url, VideocampusSachsenIE) for url in urls),
            playlist_title=title, id=f'{mode}-{content_id}')
