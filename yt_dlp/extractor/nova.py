import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    js_to_json,
    strip_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class NovaEmbedIE(InfoExtractor):
    _DOMAINS = [
        r'media(?:tn)?\.cms\.nova\.cz',
        r'media\.cms\.(?:markiza|tvnoviny)\.sk',
    ]
    _VALID_URL = [rf'https?://{domain}/embed/(?P<id>[^/?#&"\']+)' for domain in _DOMAINS]
    _EMBED_REGEX = [rf'(?x)<iframe[^>]+\b(?:data-)?src=["\'](?P<url>{url})' for url in _VALID_URL]
    _TESTS = [{
        'url': 'https://media.cms.nova.cz/embed/8o0n0r?autoplay=1',
        'info_dict': {
            'id': '8o0n0r',
            'title': '2180. díl',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2578,
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['DRM protected', 'Requested format is not available'],
    }, {
        'url': 'https://media.cms.nova.cz/embed/KybpWYvcgOa',
        'info_dict': {
            'id': 'KybpWYvcgOa',
            'ext': 'mp4',
            'title': 'Borhyová oslavila 60? Soutěžící z pořadu odboural moderátora Ondřeje Sokola',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 114,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://mediatn.cms.nova.cz/embed/EU5ELEsmOHt?autoplay=1',
        'info_dict': {
            'id': 'EU5ELEsmOHt',
            'ext': 'mp4',
            'title': 'Haptické křeslo, bionická ruka nebo roboti. Reportérka se podívala na Týden inovací',
            'thumbnail': r're:^https?://cloudia\.cms\.nova\.cz/.+',
            'duration': 1780,
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _WEBPAGE_TESTS = [{
        'url': 'http://www.markiza.sk/soubiz/zahranicny/1923705_oteckovia-maju-svoj-den-ti-slavni-nie-su-o-nic-menej-rozkosni',
        'md5': 'a478390ea7f36aeb36004a107db8b031',
        'info_dict': {
            'id': '4q3zP2DsORO',
            'ext': 'mp4',
            'title': 'Oteckovia 110',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2603,
        },
    }, {
        'url': 'https://tvnoviny.sk/domace/clanok/141815-byvaly-sportovec-udajne-vyrabal-mast-z-marihuany-sud-mu-vymeral-20-rocny-trest-a-vzal-aj-rodinny-dom',
        'md5': '51de0754352a36b4d623f98c9636a5e1',
        'info_dict': {
            'id': '2LcfYRqGuYP',
            'ext': 'mp4',
            'title': 'Marihuanový mastičkár si vypočul vysoký trest a prepad majetku',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 119,
        },
    }, {
        'url': 'https://tvnoviny.sk/domace/clanok/144055-robert-z-kosic-dostal-najnizsi-mozny-trest-za-to-co-spravil-je-to-aj-tak-vela-tvrdia-blizki',
        'md5': 'c9a8467b37951877336a9ae6309558b0',
        'info_dict': {
            'id': '82N7FrJK7cR',
            'ext': 'mp4',
            'title': 'Robovi z Košíc znížili trest za marihuanu, odsúdili ho na päť rokov',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 152,
        },
    }, {
        'url': 'https://tvnoviny.sk/domace/clanok/338907-preco-sa-mnozia-utoky-tinedzerov-podla-psychologiciek-je-za-tym-rastuca-frustracia',
        'md5': '869b589e99d7c19dd66f024a7d088502',
        'info_dict': {
            'id': 'DeiezcjCJmg',
            'ext': 'mp4',
            'title': '2022-11-03-TN-2-Nasilie-medzi-mladymi',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 142,
        },
    }, {
        'url': 'http://tvnoviny.sk/domace/clanok/890183-vlada-chysta-postavit-novu-nemocnicu-v-presove-informoval-premier-robert-fico',
        'md5': 'b9ef0b4917deee2c930f2248b568a90c',
        'info_dict': {
            'id': '7VCyuyfGsNZ',
            'ext': 'mp4',
            'title': '2024-04-15-PTN-1-Co-caka-zdravotnictvo',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 137,
        },
    }, {
        'url': 'https://www.markiza.sk/live/1-markiza',
        'info_dict': {
            'id': 'markiza-live',
            'ext': 'mp4',
            'title': r're:^CRA Markiza SD \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'thumbnail': r're:^https?://cloudia\.cms\.markiza\.sk/.+',
            'live_status': 'is_live',
        },
    }, {
        'url': 'http://www.tvnoviny.sk/domace/1923887_po-smrti-manzela-ju-cakalo-poriadne-prekvapenie',
        'md5': 'e3e0f1e98172ea64147cada308276df8',
        'info_dict': {
            'id': 'JxqRvQkFwHK',
            'ext': 'mp4',
            'title': 'Po smrti manžela ju čakalo prekvapenie',
            'thumbnail': r're:^https?://.*\.(?:jpg)',
            'duration': 108,
        },
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/reflex/zo-zakulisia/84651_pribeh-alzbetky',
        'md5': 'b40d04d5cb4cf529e2ff14d6726a3548',
        'info_dict': {
            'id': '9ZnlOQp2MRa',
            'ext': 'mp4',
            'title': 'Príbeh Alžbetky',
            'thumbnail': r're:^https?://.*\.(?:jpg)',
            'duration': 361,
        },
    }, {
        'url': 'https://www.markiza.sk/relacie/superstar/clanok/549972-v-zakulisi-superstar-to-bolo-obcas-drsne-moderator-priznal-ze-musel-pouzit-aj-hrubu-silu',
        'info_dict': {
            'id': '549972-v-zakulisi-superstar-to-bolo-obcas-drsne-moderator-priznal-ze-musel-pouzit-aj-hrubu-silu',
            'title': 'V zákulisí SuperStar to bolo občas drsné. Moderátor priznal, že musel použiť aj hrubú silu | TV Markíza',
            'description': 'md5:02e240e302bddfd0cd352bc886d95161',
            'thumbnail': r're:^https?://cmesk-ott-images-avod\.ssl\.cdn\.cra\.cz/.+',
            'age_limit': 0,
        },
        'playlist_count': 2,
    }, {
        'url': 'https://voyo.markiza.sk/filmy/6702-vysnivana-svadba',
        'info_dict': {
            'id': '20kSOHBD8DQ',
            'title': 'Vysnívaná svadba - 0000',
            'thumbnail': r're:^https?://.*\.(?:jpg)',
            'duration': 4924,
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Requested format is not available',
            'This video is DRM protected',
        ],
        'skip': 'premium member only',
    }, {
        # Another URLs:
        #   http://videoarchiv.markiza.sk/video/84723
        'url': 'http://videoarchiv.markiza.sk/video/oteckovia/84723_oteckovia-109',
        'info_dict': {
            'id': '2a5fQmhjvYm',
            'title': 'Oteckovia 109',
            'thumbnail': r're:^https?://.*\.(?:jpg)',
            'duration': 2759,
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Requested format is not available',
            'This video is DRM protected',
        ],
        'skip': 'premium member only',
    }, {
        'url': 'https://voyo.markiza.sk/filmy/1377-frajeri-vo-vegas#player-fullscreen',
        'info_dict': {
            'id': '1377-frajeri-vo-vegas#player-fullscreen',
            'title': 'Frajeri vo Vegas | Voyo',
            'description': 'md5:7f16168f669f144986d862312949627c',
            'thumbnail': r're:^https?://cmesk-ott-images-svod\.ssl\.cdn\.cra\.cz/.+',
            'age_limit': 0,
        },
        'playlist': [{
            'info_dict': {
                'id': 'K8H4IvKNBbw',
                'ext': 'mp4',
                'title': 'frajeri-vo-vegas-hd-15_frajeri-trailer',
                'duration': 90,
                'thumbnail': r're:^https?://.*\.(?:jpg)',
            },
        },
            # BUG: The 2nd item (CDjGcqcCYKy) is the movie itself and it's DRM-protected.
            #      The "ext" field can neither be here nor omitted.
        ],
        'playlist_count': 2,
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': [
            'Requested format is not available',
            'This video is DRM protected',
        ],
        'skip': 'premium member only',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        if 'player_not_logged_in' in webpage:
            self.raise_login_required()

        has_drm = False
        duration = None
        is_live = False
        formats = []

        def process_format_list(format_list, format_id=''):
            nonlocal formats, has_drm
            if not isinstance(format_list, list):
                format_list = [format_list]
            for format_dict in format_list:
                if not isinstance(format_dict, dict):
                    continue
                if (not self.get_param('allow_unplayable_formats')
                        and traverse_obj(format_dict, ('drm', 'keySystem'))):
                    has_drm = True
                    continue
                format_url = url_or_none(format_dict.get('src'))
                format_type = format_dict.get('type')
                ext = determine_ext(format_url)
                if (format_type == 'application/x-mpegURL'
                        or format_id == 'HLS' or ext == 'm3u8'):
                    formats.extend(self._extract_m3u8_formats(
                        format_url, video_id, 'mp4',
                        entry_protocol='m3u8_native', m3u8_id='hls',
                        fatal=False, headers={'Referer': url}))
                elif (format_type == 'application/dash+xml'
                      or format_id == 'DASH' or ext == 'mpd'):
                    formats.extend(self._extract_mpd_formats(
                        format_url, video_id, mpd_id='dash', fatal=False, headers={'Referer': url}))
                else:
                    formats.append({
                        'url': format_url,
                    })

        player = self._search_json(
            r'player:', webpage, 'player', video_id, fatal=False, end_pattern=r';\s*</script>')
        if player:
            for src in traverse_obj(player, ('lib', 'source', 'sources', ...)):
                process_format_list(src)
            duration = traverse_obj(player, ('sourceInfo', 'duration', {int_or_none}))
            is_live = player.get('isLive', False)
        if not formats and not has_drm:
            # older code path, in use before August 2023
            player = self._parse_json(
                self._search_regex(
                    (r'(?:(?:replacePlaceholders|processAdTagModifier).*?:\s*)?(?:replacePlaceholders|processAdTagModifier)\s*\(\s*(?P<json>{.*?})\s*\)(?:\s*\))?\s*,',
                     r'Player\.init\s*\([^,]+,(?P<cndn>\s*\w+\s*\?)?\s*(?P<json>{(?(cndn).+?|.+)})\s*(?(cndn):|,\s*{.+?}\s*\)\s*;)'),
                    webpage, 'player', group='json'), video_id)
            if player:
                for format_id, format_list in player['tracks'].items():
                    process_format_list(format_list, format_id)
                duration = int_or_none(player.get('duration'))

        if not formats and has_drm:
            self.report_drm(video_id)

        title = strip_or_none(self._og_search_title(
            webpage, default=None) or self._search_regex(
            (r'<value>(?P<title>[^<]+)',
             r'videoTitle\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1'), webpage,
            'title', group='value'))
        thumbnail = self._og_search_thumbnail(
            webpage, default=None) or self._search_regex(
            r'poster\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1', webpage,
            'thumbnail', fatal=False, group='value')
        duration = int_or_none(self._search_regex(
            r'videoDuration\s*:\s*(\d+)', webpage, 'duration',
            default=duration))

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats,
            'http_headers': {'Referer': url},
            'is_live': is_live,
        }


class NovaIE(InfoExtractor):
    IE_DESC = 'TN.cz, Prásk.tv, Nova.cz, Novaplus.cz, FANDA.tv, Krásná.cz and Doma.cz'
    _VALID_URL = r'https?://(?:[^.]+\.)?(?P<site>tv(?:noviny)?|tn|novaplus|vymena|fanda|krasna|doma|prask)\.nova\.cz/(?:[^/]+/)+(?P<id>[^/]+?)(?:\.html|/|$)'
    _TESTS = [{
        'url': 'http://tn.nova.cz/clanek/tajemstvi-ukryte-v-podzemi-specialni-nemocnice-v-prazske-krci.html#player_13260',
        'md5': 'da8f3f1fcdaf9fb0f112a32a165760a3',
        'info_dict': {
            'id': '8OvQqEvV3MW',
            'display_id': '8OvQqEvV3MW',
            'ext': 'mp4',
            'title': 'Podzemní nemocnice v pražské Krči',
            'description': 'md5:f0a42dd239c26f61c28f19e62d20ef53',
            'thumbnail': r're:^https?://.*\.(?:jpg)',
            'duration': 151,
        },
    }, {
        'url': 'http://fanda.nova.cz/clanek/fun-and-games/krvavy-epos-zaklinac-3-divoky-hon-vychazi-vyhrajte-ho-pro-sebe.html',
        'info_dict': {
            'id': '1753621',
            'ext': 'mp4',
            'title': 'Zaklínač 3: Divoký hon',
            'description': 're:.*Pokud se stejně jako my nemůžete.*',
            'thumbnail': r're:https?://.*\.jpg(\?.*)?',
            'upload_date': '20150521',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
        'skip': 'gone',
    }, {
        # media.cms.nova.cz embed
        'url': 'https://novaplus.nova.cz/porad/ulice/epizoda/18760-2180-dil',
        'info_dict': {
            'id': '8o0n0r',
            'ext': 'mp4',
            'title': '2180. díl',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2578,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [NovaEmbedIE.ie_key()],
        'skip': 'CHYBA 404: STRÁNKA NENALEZENA',
    }, {
        'url': 'http://sport.tn.nova.cz/clanek/sport/hokej/nhl/zivot-jde-dal-hodnotil-po-vyrazeni-z-playoff-jiri-sekac.html',
        'only_matching': True,
    }, {
        'url': 'http://fanda.nova.cz/clanek/fun-and-games/krvavy-epos-zaklinac-3-divoky-hon-vychazi-vyhrajte-ho-pro-sebe.html',
        'only_matching': True,
    }, {
        'url': 'http://doma.nova.cz/clanek/zdravi/prijdte-se-zapsat-do-registru-kostni-drene-jiz-ve-stredu-3-cervna.html',
        'only_matching': True,
    }, {
        'url': 'http://prask.nova.cz/clanek/novinky/co-si-na-sobe-nase-hvezdy-nechaly-pojistit.html',
        'only_matching': True,
    }, {
        'url': 'http://tv.nova.cz/clanek/novinky/zivot-je-zivot-bondovsky-trailer.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        site = mobj.group('site')

        webpage = self._download_webpage(url, display_id)

        description = clean_html(self._og_search_description(webpage, default=None))
        if site == 'novaplus':
            upload_date = unified_strdate(self._search_regex(
                r'(\d{1,2}-\d{1,2}-\d{4})$', display_id, 'upload date', default=None))
        elif site == 'fanda':
            upload_date = unified_strdate(self._search_regex(
                r'<span class="date_time">(\d{1,2}\.\d{1,2}\.\d{4})', webpage, 'upload date', default=None))
        else:
            upload_date = None

        # novaplus
        embed_id = self._search_regex(
            r'<iframe[^>]+\bsrc=["\'](?:https?:)?//media(?:tn)?\.cms\.nova\.cz/embed/([^/?#&"\']+)',
            webpage, 'embed url', default=None)
        if embed_id:
            return {
                '_type': 'url_transparent',
                'url': f'https://media.cms.nova.cz/embed/{embed_id}',
                'ie_key': NovaEmbedIE.ie_key(),
                'id': embed_id,
                'description': description,
                'upload_date': upload_date,
            }

        video_id = self._search_regex(
            [r"(?:media|video_id)\s*:\s*'(\d+)'",
             r'media=(\d+)',
             r'id="article_video_(\d+)"',
             r'id="player_(\d+)"'],
            webpage, 'video id')

        config_url = self._search_regex(
            r'src="(https?://(?:tn|api)\.nova\.cz/bin/player/videojs/config\.php\?[^"]+)"',
            webpage, 'config url', default=None)
        config_params = {}

        if not config_url:
            player = self._parse_json(
                self._search_regex(
                    r'(?s)Player\s*\(.+?\s*,\s*({.+?\bmedia\b["\']?\s*:\s*["\']?\d+.+?})\s*\)', webpage,
                    'player', default='{}'),
                video_id, transform_source=js_to_json, fatal=False)
            if player:
                config_url = url_or_none(player.get('configUrl'))
                params = player.get('configParams')
                if isinstance(params, dict):
                    config_params = params

        if not config_url:
            DEFAULT_SITE_ID = '23000'
            SITES = {
                'tvnoviny': DEFAULT_SITE_ID,
                'novaplus': DEFAULT_SITE_ID,
                'vymena': DEFAULT_SITE_ID,
                'krasna': DEFAULT_SITE_ID,
                'fanda': '30',
                'tn': '30',
                'doma': '30',
            }

            site_id = self._search_regex(
                r'site=(\d+)', webpage, 'site id', default=None) or SITES.get(
                site, DEFAULT_SITE_ID)

            config_url = 'https://api.nova.cz/bin/player/videojs/config.php'
            config_params = {
                'site': site_id,
                'media': video_id,
                'quality': 3,
                'version': 1,
            }

        config = self._download_json(
            config_url, display_id,
            'Downloading config JSON', query=config_params,
            transform_source=lambda s: s[s.index('{'):s.rindex('}') + 1])

        mediafile = config['mediafile']
        video_url = mediafile['src']

        m = re.search(r'^(?P<url>rtmpe?://[^/]+/(?P<app>[^/]+?))/&*(?P<playpath>.+)$', video_url)
        if m:
            formats = [{
                'url': m.group('url'),
                'app': m.group('app'),
                'play_path': m.group('playpath'),
                'player_path': 'http://tvnoviny.nova.cz/static/shared/app/videojs/video-js.swf',
                'ext': 'flv',
            }]
        else:
            formats = [{
                'url': video_url,
            }]

        title = mediafile.get('meta', {}).get('title') or self._og_search_title(webpage)
        thumbnail = config.get('poster')

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'upload_date': upload_date,
            'thumbnail': thumbnail,
            'formats': formats,
        }
