import re
from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    get_element_by_class,
    int_or_none,
    join_nonempty,
    js_to_json,
    merge_dicts,
    mimetype2ext,
    parse_duration,
    traverse_obj,
    unified_timestamp,
)


class GediDigitalIE(InfoExtractor):
    _VALID_URL = r'''(?x:
        (?P<url>
            https?://(?:www\.)?
            (?:
                lastampa
                |ilsecoloxix
                |huffingtonpost
                |\w+\.gelocal
                |espresso\.repubblica
            )\.it
            (?:/[^/]+){1,2}(?P<date>[\d/]{12})(?P<type>audio|video|playlist)/[^/]+-
            (?P<id>\d{5,})
        )(?:\#(?P<trtId>([\w-]+:)+\d{5,}))?)'''
    _EMBED_REGEX = [rf'<iframe[^>]+src=[\'"]{_VALID_URL}']
    _TESTS = [{
        # old video, only http mp4 available
        'url': 'https://www.lastampa.it/politica/2020/09/22/video/il_paradosso_delle_regionali_ecco_perche_la_lega_vince_ma_sembra_aver_perso-375544/',
        # old url: 'https://video.lastampa.it/politica/il-paradosso-delle-regionali-la-lega-vince-ma-sembra-aver-perso/121559/121683'
        'info_dict': {
            'id': '375544',
            'ext': 'mp4',
            'title': 'Il paradosso delle Regionali: ecco perché la Lega vince ma sembra aver perso',
            'description': 'md5:56d4dc2d81923f524dd0f8247f06eeaa',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?\.jpg',
            'duration': 125,
            'timestamp': 1600788078,
            'upload_date': '20200922',
            'formats': 'count:2',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # new video: more formats available
        'url': 'https://www.lastampa.it/esteri/2022/12/12/video/scandalo_qatargate_ecco_chi_sono_i_parlamentari_coinvolti_e_cosa_rischiano-12408715/?ref=LSHSTD-BH-I0-PM6-S2-T1',
        'info_dict': {
            'id': '12408715',
            'ext': 'mp4',
            'title': 'Scandalo Qatargate, ecco chi sono i parlamentari coinvolti e cosa rischiano',
            'description': 'md5:3213071f7d82d38300c4f22d4d47dddc',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?\.jpg',
            'duration': 122,
            'timestamp': 1670866318,
            'upload_date': '20221212',
            'formats': 'count:10',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # only audio
        'url': 'https://ilpiccolo.gelocal.it/onepodcast/deejay/2022/12/08/audio/episodio_6_lingegnere-10858264/',
        'info_dict': {
            'id': 'deejay:podcast:348159',
            'ext': 'm4a',
            'title': 'Episodio 6: L’ingegnere',
            'description': 'md5:ba4a655f864fb998f3fdba807ed85a66',
            'thumbnail': r're:^https://.+?800x800\.jpg',
            'duration': 3571,
            'timestamp': 1670472004,
            'upload_date': '20221208',
            'formats': 'count:3',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # audio playlist (podcast and alike)
        'url': 'https://www.lastampa.it/rubriche/daytime/2022/05/09/playlist/daytime-3447164',
        'info_dict': {
            'id': '3447164',
            'title': 'DayTime',
        },
        'playlist_count_min': 100,
    }, {
        # playlist with single episode selection
        'url': 'https://www.lastampa.it/rubriche/daytime/2022/05/09/playlist/daytime-3447164#gnn:audio:5427139',
        'info_dict': {
            'id': 'gnn:audio:5427139',
            'ext': 'm4a',
            'title': 'Una legge di civiltà',
            'description': 'md5:963f7397192d33f05b321f00f4a60e30',
            'thumbnail': r're:^https://.+?thumb-full.+?\.jpg',
            'duration': 322,
            'timestamp': 1656374400,
            'upload_date': '20220628',
            'formats': 'count:3',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # new url for video in GediDigitalLegacy
        'url': 'https://espresso.repubblica.it/video/2020/10/08/video/festival_emergency_villa_la_buona_informazione_aiuta_la_salute_-321887259/',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://nixxo.github.io/yt-dpl-test-pages/gedidigital-iframes.html',
        'info_dict': {
            'id': '12408715',
            'ext': 'mp4',
            'title': 'Scandalo Qatargate, ecco chi sono i parlamentari coinvolti e cosa rischiano',
            'description': 'md5:3213071f7d82d38300c4f22d4d47dddc',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?\.jpg',
            'duration': 122,
            'timestamp': 1670866318,
            'upload_date': '20221212',
            'formats': 'count:10',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        url, media_type, media_id, track_id = self._match_valid_url(url).group(
            'url', 'type', 'id', 'trtId')

        webpage = self._download_webpage(url.replace('/embed/', '/'), media_id)

        formats = []
        if media_type == 'video':
            media_data = self._search_json(
                r'BrightcoveVideoPlayerOptions\s*=', webpage, 'media_data', media_id,
                transform_source=lambda s: js_to_json(s.replace('\'[{', '[{').replace('}]\'', '}]')))
            for fmt in media_data.get('videoSrc'):
                if 'src' not in fmt or 'type' not in fmt:
                    continue
                ext = mimetype2ext(fmt['type'])
                if ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(fmt['src'], media_id, m3u8_id='hls'))
                elif ext == 'mp4':
                    vbr = int_or_none(self._search_regex(
                        r'video-rrtv-(\d+)', fmt['src'], 'vbr', default=None))
                    formats.append({
                        'format_id': join_nonempty('mp4', vbr),
                        'url': fmt['src'],
                        'vbr': vbr,
                    })

        if media_type in ('audio', 'playlist', 'podcast'):
            # update the media_id (needed for podcasts)
            media_id = self._search_regex(r'data=[\'"]audioSource(\d+)[\'"]', webpage, 'media_id', default=media_id)

            media_data = self._search_json(
                rf'audioSource{media_id}\s*=', webpage, 'media_data', media_id,
                contains_pattern=r'\[(?s:.+)\];', transform_source=js_to_json)
            if media_type == 'audio':
                track_id = traverse_obj(media_data, (0, 'trtId'), (0, 'original_id'))

            playlist_entries = []
            for episode in media_data:
                if track_id == traverse_obj(episode, 'trtId', 'original_id'):
                    if episode.get('audio_url_hls'):
                        formats.extend(self._extract_m3u8_formats(
                            episode['audio_url_hls'], media_id, m3u8_id='audio-hls'))
                    elif 'm3u8' == determine_ext(episode.get('audio_url')):
                        formats.extend(self._extract_m3u8_formats(
                            episode['audio_url'], media_id, m3u8_id='audio-hls'))
                    elif 'mp3' == determine_ext(episode.get('audio_url')):
                        formats.append({
                            'format_id': 'audio-mp3',
                            'url': episode['audio_url'],
                            'acodec': 'mp3',
                            'vcodec': 'none',
                        })
                    else:
                        self.raise_no_formats("Audio format not recognized")
                    media_data = episode
                    break
                elif not track_id:
                    # if no specific episode is selected return a playlist
                    playlist_entries.append(self.url_result(
                        f'{url}#{traverse_obj(episode, "trtId", "original_id")}'))

            if playlist_entries:
                return self.playlist_result(
                    playlist_entries, playlist_id=media_id,
                    playlist_title=self._generic_title(url, webpage))

        media_data = merge_dicts(media_data, self._search_json_ld(webpage, media_id, default={}))

        return {
            'id': track_id or media_id,
            'title': traverse_obj(media_data, 'videoTitle', 'title'),
            'description': (clean_html(get_element_by_class('story__summary', webpage)
                                       or get_element_by_class('detail_summary', webpage))
                            or media_data.get('description')),
            'duration': int_or_none(media_data.get('videoLenght')
                                    or parse_duration(media_data.get('duration'))
                                    or media_data.get('duration')),
            'thumbnail': traverse_obj(media_data, 'posterSrc', 'image', ('thumbnails', 0, 'url')),
            'timestamp': (media_data.get('timestamp')
                          or unified_timestamp(media_data.get('pubdate') or media_data.get('pub_date'))),
            'formats': formats,
        }


class RepubblicaTVIE(GediDigitalIE):
    _VALID_URL = r'(?P<url>https?://(?P<type>video)\.repubblica\.it(?:/[^/]+){2,4}/(?P<id>\d+))(?:\#(?P<trtId>([\w-]+:)+\d{5,}))?'
    _EMBED_REGEX = [rf'<gdwc-video-component[^>]+data-src="{_VALID_URL}']
    _TESTS = [{
        'url': 'https://video.repubblica.it/metropolis/metropolis232-cavoletti-da-bruxelles-manovra-migranti-qatargate-ue-chiama-italia-ospiti-provenzano-giarrusso-e-de-giovanni-con-cuzzocrea-e-folli/434120/435073',
        'info_dict': {
            'id': '435073',
            'ext': 'mp4',
            'title': '[REP-TV] Metropolis 232 -  Cavoletti da Bruxelles  Manovra  migranti  Qatargate  Ue chiama Italia  Ospiti  Provenzano  Giarrusso e De Giovanni  Con Cuzzocrea e Folli (integrale) (434120-435073)',
            'description': 'md5:a7ff102b51bbf46765316fad1e3d32f2',
            'thumbnail': r're:^https://.+?thumb-full.+?\.jpg',
            'duration': 1452,
            'timestamp': 1671044772,
            'upload_date': '20221214',
            'formats': 'count:6',
        },
        'params': {
            'skip_download': True,
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://genova.repubblica.it/cronaca/2022/12/22/news/genova_palazzo_ducale_fondi_pnrr_cultura-380257726/?ref=RHLF-BG-I380293053-P13-S1-T1&__vfz=medium%3Dsharebar',
        'info_dict': {
            'id': '434699',
            'ext': 'mp4',
            'title': '[REP-TV] Genova  pioggia di soldi dal Pnrr per il Palazzo Ducale e il restauro della Torre Grimaldina (434699-435663)',
            'description': 'md5:b86313bc45c7c6967a40df16db490a84',
            'thumbnail': r're:^https://www\.repstatic\.it/.+-thumb-full-.+\.jpg',
            'duration': 121,
            'upload_date': '20221222',
            'timestamp': 1671723271,
        },
        'params': {
            'skip_download': True,
        },
    }]


class RepubblicaTVPodcastIE(GediDigitalIE):
    _VALID_URL = r'(?P<url>https?://(?:www\.)?repubblica\.it/(?P<type>podcast)/(?P<id>[\w-]+))(?:\#(?P<trtId>([\w-]+:)+\d{5,}))?'
    _TESTS = [{
        'url': 'https://www.repubblica.it/podcast/la-giornata',
        'info_dict': {
            'id': '2170',
            'title': 'La giornata - Podcast - La Repubblica',
        },
        'playlist_count_min': 30,
    }, {
        # single episode
        'url': 'https://www.repubblica.it/podcast/la-giornata#rep-locali:articolo:383127029',
        'info_dict': {
            'id': 'rep-locali:articolo:383127029',
            'ext': 'm4a',
            'title': 'La maternità va alla guerra',
            'description': 'md5:38c3488ae796f28c12fa2a7c812c0583',
            'thumbnail': r're:^https://www\.repstatic\.it/.+/img/.+\.jpg',
            'duration': 503,
            'timestamp': 1673481600,
            'upload_date': '20230112',
            'formats': 'count:3',
        },
        'params': {
            'skip_download': True,
        },
    }]


class GediDigitalLegacyIE(InfoExtractor):
    # Legacy extractor only present for accessing media via this url,
    # it will probably be gradually eliminated like other websites
    _VALID_URL = r'''(?x)https?://video\.
        (?:
            espresso\.repubblica\.it/tutti-i-video
            |huffingtonpost\.it(?:/embed)?
        )(?:/[^/]+){1,3}/(?P<id>\d+)(?:$|[?&].*)'''
    _TESTS = [{
        'url': 'https://video.espresso.repubblica.it/tutti-i-video/01-ted-villa/14772',
        'info_dict': {
            'id': '14772',
            'ext': 'mp4',
            'title': 'Festival EMERGENCY, Villa: «La buona informazione aiuta la salute»',
            'description': 'md5:de5a05a8aeae772941aa9fe0c9702f0c',
            'thumbnail': r're:^https://www\.repstatic\.it/video/photo/.+?-thumb-full-.+?\.jpg$',
            'duration': 1328,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://video.huffingtonpost.it/politica/cotticelli-non-so-cosa-mi-sia-successo-sto-cercando-di-capire-se-ho-avuto-un-malore/29312/29276',
        'matching_only': True,
    }]

    @staticmethod
    def _clean_formats(formats):
        format_urls = set()
        clean_formats = []
        for f in formats:
            if f['url'] not in format_urls:
                if f.get('audio_ext') != 'none' and not f.get('acodec'):
                    continue
                format_urls.add(f['url'])
                clean_formats.append(f)
        formats[:] = clean_formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        title = self._html_search_meta(
            ['twitter:title', 'og:title'], webpage, fatal=True)
        player_data = re.findall(
            r"PlayerFactory\.setParam\('(?P<type>format|param)',\s*'(?P<name>[^']+)',\s*'(?P<val>[^']+)'\);",
            webpage)

        formats = []
        duration = thumb = None
        for t, n, v in player_data:
            if t == 'format':
                if n in ('video-hds-vod-ec', 'video-hls-vod-ec', 'video-viralize', 'video-youtube-pfp'):
                    continue
                elif n.endswith('-vod-ak'):
                    formats.extend(self._extract_akamai_formats(
                        v, video_id, {'http': 'media.gedidigital.it'}))
                else:
                    ext = determine_ext(v)
                    if ext == 'm3u8':
                        formats.extend(self._extract_m3u8_formats(
                            v, video_id, 'mp4', 'm3u8_native', m3u8_id=n, fatal=False))
                        continue
                    f = {
                        'format_id': n,
                        'url': v,
                    }
                    if ext == 'mp3':
                        abr = int_or_none(self._search_regex(
                            r'-mp3-audio-(\d+)', v, 'abr', default=None))
                        f.update({
                            'abr': abr,
                            'tbr': abr,
                            'acodec': ext,
                            'vcodec': 'none'
                        })
                    else:
                        mobj = re.match(r'^video-rrtv-(\d+)(?:-(\d+))?$', n)
                        if mobj:
                            f.update({
                                'height': int(mobj.group(1)),
                                'vbr': int_or_none(mobj.group(2)),
                            })
                        if not f.get('vbr'):
                            f['vbr'] = int_or_none(self._search_regex(
                                r'-video-rrtv-(\d+)', v, 'abr', default=None))
                    formats.append(f)
            elif t == 'param':
                if n in ['image_full', 'image']:
                    thumb = v
                elif n == 'videoDuration':
                    duration = int_or_none(v)

        self._clean_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': self._html_search_meta(
                ['twitter:description', 'og:description', 'description'], webpage),
            'thumbnail': thumb or self._og_search_thumbnail(webpage),
            'formats': formats,
            'duration': duration,
        }
