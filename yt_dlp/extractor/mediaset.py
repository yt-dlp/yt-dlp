import functools
import re

from .theplatform import ThePlatformBaseIE
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    OnDemandPagedList,
    int_or_none,
    try_get,
    update_url_query,
    urljoin,
)


class MediasetIE(ThePlatformBaseIE):
    _TP_TLD = 'eu'
    _GUID_RE = r'F[0-9A-Z]{15}'
    _VALID_URL = rf'''(?x)
                    (?:
                        mediaset:|
                        https?://
                            (?:\w+\.)+mediaset\.it/
                            (?:
                                (?:video|on-demand|movie)/(?:[^/]+/)+[^/]+_|
                                player/(?:v\d+/)?index\.html\?\S*?\bprogramGuid=
                            )
                    )(?P<id>{_GUID_RE})
                    '''

    _EMBED_REGEX = [
        rf'<iframe[^>]+src=[\'"](?P<url>(?:https?:)?//(?:\w+\.)+mediaset\.it/player/(?:v\d+/)?index\.html\?\S*?programGuid={_GUID_RE})[\'"&]'
    ]
    _TESTS = [{
        # full episode
        'url': 'https://mediasetinfinity.mediaset.it/video/mrwronglezionidamore/episodio-1_F310575103000102',
        'md5': 'a7e75c6384871f322adb781d3bd72c26',
        'info_dict': {
            'id': 'F310575103000102',
            'ext': 'mp4',
            'title': 'Episodio 1',
            'description': 'md5:e8017b7d7194e9bfb75299c2b8d81e02',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2682.0,
            'upload_date': '20210530',
            'series': 'Mr Wrong - Lezioni d\'amore',
            'timestamp': 1622413946,
            'uploader': 'Canale 5',
            'uploader_id': 'C5',
            'season': 'Season 1',
            'episode': 'Episode 1',
            'season_number': 1,
            'episode_number': 1,
            'chapters': [{'start_time': 0.0, 'end_time': 439.88}, {'start_time': 439.88, 'end_time': 1685.84}, {'start_time': 1685.84, 'end_time': 2682.0}],
        },
    }, {
        'url': 'https://mediasetinfinity.mediaset.it/video/matrix/puntata-del-25-maggio_F309013801000501',
        'md5': '1276f966ac423d16ba255ce867de073e',
        'info_dict': {
            'id': 'F309013801000501',
            'ext': 'mp4',
            'title': 'Puntata del 25 maggio',
            'description': 'md5:ee2e456e3eb1dba5e814596655bb5296',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 6565.008,
            'upload_date': '20200903',
            'series': 'Matrix',
            'timestamp': 1599172492,
            'uploader': 'Canale 5',
            'uploader_id': 'C5',
            'season': 'Season 5',
            'episode': 'Episode 5',
            'season_number': 5,
            'episode_number': 5,
            'chapters': [{'start_time': 0.0, 'end_time': 3409.08}, {'start_time': 3409.08, 'end_time': 6565.008}],
            'categories': ['Informazione'],
        },
    }, {
        # DRM
        'url': 'https://mediasetinfinity.mediaset.it/movie/selvaggi/selvaggi_F006474501000101',
        'info_dict': {
            'id': 'F006474501000101',
            'ext': 'mp4',
            'title': 'Selvaggi',
            'description': 'md5:cfdedbbfdd12d4d0e5dcf1fa1b75284f',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 5233.01,
            'upload_date': '20210729',
            'timestamp': 1627594716,
            'uploader': 'Cine34',
            'uploader_id': 'B6',
            'chapters': [{'start_time': 0.0, 'end_time': 1938.56}, {'start_time': 1938.56, 'end_time': 5233.01}],
        },
        'params': {
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'None of the available releases match the specified AssetType, ProtectionScheme, and/or Format preferences',
            'Content behind paywall and DRM',
        ],
        'skip': True,
    }, {
        # old domain
        'url': 'https://www.mediasetplay.mediaset.it/video/mrwronglezionidamore/episodio-1_F310575103000102',
        'only_matching': True,
    }, {
        # iframe
        'url': 'https://static3.mediasetplay.mediaset.it/player/index.html?appKey=5ad3966b1de1c4000d5cec48&programGuid=FAFU000000665924&id=665924',
        'only_matching': True,
    }, {
        'url': 'mediaset:FAFU000000665924',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        # Mediaset embed
        'url': 'http://www.tgcom24.mediaset.it/politica/serracchiani-voglio-vivere-in-una-societa-aperta-reazioni-sproporzionate-_3071354-201702a.shtml',
        'info_dict': {
            'id': 'FD00000000004929',
            'ext': 'mp4',
            'title': 'Serracchiani: "Voglio vivere in una società aperta, con tutela del patto di fiducia"',
            'duration': 67.013,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Mediaset Play',
            'uploader_id': 'QY',
            'upload_date': '20201005',
            'timestamp': 1601866168,
            'chapters': [],
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Dead link',
    }, {
        # WittyTV embed
        'url': 'https://www.wittytv.it/mauriziocostanzoshow/ultima-puntata-venerdi-25-novembre/',
        'info_dict': {
            'id': 'F312172801000801',
            'ext': 'mp4',
            'title': 'Ultima puntata - Venerdì 25 novembre',
            'description': 'Una serata all\'insegna della musica e del buonumore ma non priva di spunti di riflessione',
            'duration': 6203.01,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Canale 5',
            'uploader_id': 'C5',
            'upload_date': '20221126',
            'timestamp': 1669428689,
            'chapters': list,
            'series': 'Maurizio Costanzo Show',
            'season': 'Season 12',
            'season_number': 12,
            'episode': 'Episode 8',
            'episode_number': 8,
            'categories': ['Intrattenimento'],
        },
        'params': {
            'skip_download': True,
        }
    }]

    def _parse_smil_formats_and_subtitles(
            self, smil, smil_url, video_id, namespace=None, f4m_params=None, transform_rtmp_url=None):
        for video in smil.findall(self._xpath_ns('.//video', namespace)):
            video.attrib['src'] = re.sub(r'(https?://vod05)t(-mediaset-it\.akamaized\.net/.+?.mpd)\?.+', r'\1\2', video.attrib['src'])
        return super(MediasetIE, self)._parse_smil_formats_and_subtitles(
            smil, smil_url, video_id, namespace, f4m_params, transform_rtmp_url)

    def _check_drm_formats(self, tp_formats, video_id):
        has_nondrm, drm_manifest = False, ''
        for f in tp_formats:
            if '_sampleaes/' in (f.get('manifest_url') or ''):
                drm_manifest = drm_manifest or f['manifest_url']
                f['has_drm'] = True
            if not f.get('has_drm') and f.get('manifest_url'):
                has_nondrm = True

        nodrm_manifest = re.sub(r'_sampleaes/(\w+)_fp_', r'/\1_no_', drm_manifest)
        if has_nondrm or nodrm_manifest == drm_manifest:
            return

        tp_formats.extend(self._extract_m3u8_formats(
            nodrm_manifest, video_id, m3u8_id='hls', fatal=False) or [])

    def _real_extract(self, url):
        guid = self._match_id(url)
        tp_path = f'PR1GhC/media/guid/2702976343/{guid}'
        info = self._extract_theplatform_metadata(tp_path, guid)

        formats = []
        subtitles = {}
        first_e = geo_e = None
        asset_type = 'geoNo:HD,browser,geoIT|geoNo:HD,geoIT|geoNo:SD,browser,geoIT|geoNo:SD,geoIT|geoNo|HD|SD'
        # TODO: fixup ISM+none manifest URLs
        for f in ('MPEG4', 'MPEG-DASH', 'M3U'):
            try:
                tp_formats, tp_subtitles = self._extract_theplatform_smil(
                    update_url_query(f'http://link.theplatform.{self._TP_TLD}/s/{tp_path}', {
                        'mbr': 'true',
                        'formats': f,
                        'assetTypes': asset_type,
                    }), guid, f'Downloading {f.split("+")[0]} SMIL data')
            except ExtractorError as e:
                if e.orig_msg == 'None of the available releases match the specified AssetType, ProtectionScheme, and/or Format preferences':
                    e.orig_msg = 'This video is DRM protected'
                if not geo_e and isinstance(e, GeoRestrictedError):
                    geo_e = e
                if not first_e:
                    first_e = e
                continue
            self._check_drm_formats(tp_formats, guid)
            formats.extend(tp_formats)
            subtitles = self._merge_subtitles(subtitles, tp_subtitles)

        # check for errors and report them
        if (first_e or geo_e) and not formats:
            raise geo_e or first_e

        feed_data = self._download_json(
            f'https://feed.entertainment.tv.theplatform.eu/f/PR1GhC/mediaset-prod-all-programs-v2/guid/-/{guid}',
            guid, fatal=False)
        if feed_data:
            publish_info = feed_data.get('mediasetprogram$publishInfo') or {}
            thumbnails = feed_data.get('thumbnails') or {}
            thumbnail = None
            for key, value in thumbnails.items():
                if key.startswith('image_keyframe_poster-'):
                    thumbnail = value.get('url')
                    break

            info.update({
                'description': info.get('description') or feed_data.get('description') or feed_data.get('longDescription'),
                'uploader': publish_info.get('description'),
                'uploader_id': publish_info.get('channel'),
                'view_count': int_or_none(feed_data.get('mediasetprogram$numberOfViews')),
                'thumbnail': thumbnail,
            })

            if feed_data.get('programType') == 'episode':
                info.update({
                    'episode_number': int_or_none(
                        feed_data.get('tvSeasonEpisodeNumber')),
                    'season_number': int_or_none(
                        feed_data.get('tvSeasonNumber')),
                    'series': feed_data.get('mediasetprogram$brandTitle'),
                })

        info.update({
            'id': guid,
            'formats': formats,
            'subtitles': subtitles,
        })
        return info


class MediasetShowIE(MediasetIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'''(?x)
                    (?:
                        https?://
                            (\w+\.)+mediaset\.it/
                            (?:
                                (?:fiction|programmi-tv|serie-tv|kids)/(?:.+?/)?
                                    (?:[a-z-]+)_SE(?P<id>\d{12})
                                    (?:,ST(?P<st>\d{12}))?
                                    (?:,sb(?P<sb>\d{9}))?$
                            )
                    )
                    '''
    _TESTS = [{
        # TV Show webpage (general webpage)
        'url': 'https://mediasetinfinity.mediaset.it/programmi-tv/leiene/leiene_SE000000000061',
        'info_dict': {
            'id': '000000000061',
            'title': 'Le Iene 2022/2023',
        },
        'playlist_mincount': 6,
    }, {
        # TV Show webpage (specific season)
        'url': 'https://mediasetinfinity.mediaset.it/programmi-tv/leiene/leiene_SE000000000061,ST000000002763',
        'info_dict': {
            'id': '000000002763',
            'title': 'Le Iene 2021/2022',
        },
        'playlist_mincount': 7,
    }, {
        # TV Show specific playlist (with multiple pages)
        'url': 'https://mediasetinfinity.mediaset.it/programmi-tv/leiene/iservizi_SE000000000061,ST000000002763,sb100013375',
        'info_dict': {
            'id': '100013375',
            'title': 'I servizi',
        },
        'playlist_mincount': 50,
    }]

    _BY_SUBBRAND = 'https://feed.entertainment.tv.theplatform.eu/f/PR1GhC/mediaset-prod-all-programs-v2?byCustomValue={subBrandId}{%s}&sort=:publishInfo_lastPublished|desc,tvSeasonEpisodeNumber|desc&range=%d-%d'
    _PAGE_SIZE = 25

    def _fetch_page(self, sb, page):
        lower_limit = page * self._PAGE_SIZE + 1
        upper_limit = lower_limit + self._PAGE_SIZE - 1
        content = self._download_json(
            self._BY_SUBBRAND % (sb, lower_limit, upper_limit), sb)
        for entry in content.get('entries') or []:
            yield self.url_result(
                'mediaset:' + entry['guid'],
                playlist_title=entry['mediasetprogram$subBrandDescription'])

    def _real_extract(self, url):
        playlist_id, st, sb = self._match_valid_url(url).group('id', 'st', 'sb')
        if not sb:
            page = self._download_webpage(url, st or playlist_id)
            entries = [self.url_result(urljoin('https://mediasetinfinity.mediaset.it', url))
                       for url in re.findall(r'href="([^<>=]+SE\d{12},ST\d{12},sb\d{9})">[^<]+<', page)]
            title = self._html_extract_title(page).split('|')[0].strip()
            return self.playlist_result(entries, st or playlist_id, title)

        entries = OnDemandPagedList(
            functools.partial(self._fetch_page, sb),
            self._PAGE_SIZE)
        title = try_get(entries, lambda x: x[0]['playlist_title'])

        return self.playlist_result(entries, sb, title)
