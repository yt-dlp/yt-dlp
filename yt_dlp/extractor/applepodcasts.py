import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    clean_podcast_url,
    int_or_none,
    parse_iso8601,
    urljoin,
)
from ..utils.traversal import traverse_obj


class ApplePodcastsBaseIE(InfoExtractor):
    _BASE_URL_REGEX = r'https?://podcasts\.apple\.com/(?:[^/]+/)?podcast(?:/[^/]+)?'
    _BASE_HTML_JSON_LOCATION = r'<script [^>]*\bid=["\']serialized-server-data["\'][^>]*>'
    _BASE_HTML_JSON_PATTERN = r'\[{(?s:.+)}\]'


class ApplePodcastsIE(ApplePodcastsBaseIE):
    _VALID_URL = ApplePodcastsBaseIE._BASE_URL_REGEX + r'.*?\bi=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://podcasts.apple.com/us/podcast/ferreck-dawn-to-the-break-of-dawn-117/id1625658232?i=1000665010654',
        'md5': '82cc219b8cc1dcf8bfc5a5e99b23b172',
        'info_dict': {
            'id': '1000665010654',
            'ext': 'mp3',
            'title': 'Ferreck Dawn - To The Break of Dawn 117',
            'episode': 'Ferreck Dawn - To The Break of Dawn 117',
            'description': 'md5:8c4f5c2c30af17ed6a98b0b9daf15b76',
            'upload_date': '20240812',
            'timestamp': 1723449600,
            'duration': 3596,
            'series': 'Ferreck Dawn - To The Break of Dawn',
            'thumbnail': 're:.+[.](png|jpe?g|webp)',
        },
    }, {
        'url': 'https://podcasts.apple.com/us/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'md5': 'baf8a6b8b8aa6062dbb4639ed73d0052',
        'info_dict': {
            'id': '1000482637777',
            'ext': 'mp3',
            'title': '207 - Whitney Webb Returns',
            'episode': '207 - Whitney Webb Returns',
            'episode_number': 207,
            'description': 'md5:75ef4316031df7b41ced4e7b987f79c6',
            'upload_date': '20200705',
            'timestamp': 1593932400,
            'duration': 5369,
            'series': 'The Tim Dillon Show',
            'thumbnail': 're:.+[.](png|jpe?g|webp)',
        },
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/id1135137367?i=1000482637777',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        server_data = self._search_json(
            ApplePodcastsBaseIE._BASE_HTML_JSON_LOCATION, webpage,
            'server data', episode_id, contains_pattern=ApplePodcastsBaseIE._BASE_HTML_JSON_PATTERN)[0]['data']
        model_data = traverse_obj(server_data, (
            'headerButtonItems', lambda _, v: v['$kind'] == 'share' and v['modelType'] == 'EpisodeLockup',
            'model', {dict}, any))

        return {
            'id': episode_id,
            **self._json_ld(
                traverse_obj(server_data, ('seoData', 'schemaContent', {dict}))
                or self._yield_json_ld(webpage, episode_id, fatal=False), episode_id, fatal=False),
            **traverse_obj(model_data, {
                'title': ('title', {str}),
                'description': ('summary', {clean_html}),
                'url': ('playAction', 'episodeOffer', 'streamUrl', {clean_podcast_url}),
                'timestamp': ('releaseDate', {parse_iso8601}),
                'duration': ('duration', {int_or_none}),
            }),
            'thumbnail': self._og_search_thumbnail(webpage),
            'vcodec': 'none',
        }


class ApplePodcastsPlaylistIE(ApplePodcastsBaseIE):
    # Apple podcast items are partially described in the embedded json from main page (last episodes only) therefore API calls are mandatory to get a full list

    _VALID_URL = ApplePodcastsBaseIE._BASE_URL_REGEX + r'/id(?P<id>\d+)(?!\?i=\d+)$'
    _TESTS = [{
        'url': 'https://podcasts.apple.com/fr/podcast/id1691740320',
        'info_dict': {
            'id': '1691740320',
            'title': 'LEGEND',
            'playlist_uploader': 'Guillaume Pley',
        },
        'playlist_mincount': 400,
        'playlist_entries': [
            {
                'id': '1000718966711',
                'title': 'MICHAEL YOUN : LES MOMENTS LES PLUS FOUS DE SES 25 ANS DE CARRIÈRE (MORNING LIVE, FATAL 2…)',
                'uploader': 'Guillaume Pley',
                'description': 'Retrouvez la boutique LEGEND ➡️: https://shop.legend-group.fr/\nMerci à Michaël Youn d\'être venu nous voir sur LEGEND. Il est venu nous raconter plus de 25 ans de carrière, en tant qu’acteur, réalisateur et artiste. Il a été révélé par l\'émission Morning Live sur M6, il nous a livré les anecdotes les plus folles qu’il a vécues à cette époque. Il est aussi venu nous raconter comment il a rencontré sa femme et ce que ses enfants ont changé dans sa vie.\nPour voir la bande annonce du film « Certains l’aiment chauve » déjà disponible au cinéma ➡️ https://www.allocine.fr/film/fichefilm_gen_cfilm=1000007354.html\nRetrouvez l\'interview complète sur YouTube ➡️ https://youtu.be/_TXBz1dSfBw\nPour toutes demandes de partenariats : legend@influxcrew.com\nRetrouvez-nous sur tous les réseaux LEGEND !\nFacebook : https://www.facebook.com/legendmediafr\nInstagram : https://www.instagram.com/legendmedia/\nTikTok : https://www.tiktok.com/@legend\nTwitter : https://twitter.com/legendmediafr\nSnapchat : https://t.snapchat.com/CgEvsbWV\n Hébergé par Acast. Visitez acast.com/privacy pour plus d\'informations.',
                'release_timestamp': 1753434168,
                'duration': 6856,
                'url': 'https://podcasts.apple.com/fr/podcast/michael-youn-les-moments-les-plus-fous-de-ses-25-ans/id1691740320?i=1000718966711',
            },
            {
                'id': '1000718672235',
                'title': 'AMBULANCIER DU SAMU: SES INTERVENTIONS IMPROBABLES (SUIC*DES, FAUX MALADES, ENFANTS DR0GUÉS)',
                'uploader': 'Guillaume Pley',
                'description': 'Retrouvez la boutique LEGEND ➡️: https://shop.legend-group.fr/\nMerci à Thomas d’être passé nous voir chez LEGEND ! Thomas est ambulancier et urgentiste au SMUR depuis 10 ans. Il est venu partager avec nous ses anecdotes les plus marquantes.\nIl a vécu des interventions difficiles, comme sur une scène de crime où une mère avait tué ses deux enfants, ou encore ce jour où il a pris en charge une victime coupée en deux par un hachoir.\nMais son métier, c’est aussi des moments plus légers, parfois même drôles, comme cette fois où il a dû intervenir sur le tournage d’un film X pour secourir des acteurs.\nPour toutes demandes de partenariats : legend@influxcrew.com\nRetrouvez-nous sur tous les réseaux LEGEND !\nRetrouvez l\'interview complète sur YouTube ➡️ https://youtu.be/ye5cVoc7hIc\nFacebook : https://www.facebook.com/legendmediafr\nInstagram : https://www.instagram.com/legendmedia/\nTikTok : https://www.tiktok.com/@legend\nTwitter : https://twitter.com/legendmediafr\nSnapchat : https://t.snapchat.com/CgEvsbWV\n Hébergé par Acast. Visitez acast.com/privacy pour plus d\'informations.',
                'release_timestamp': 1753272000,
                'duration': 4165,
                'url': 'https://podcasts.apple.com/fr/podcast/ambulancier-du-samu-ses-interventions-improbables-suic/id1691740320?i=1000718672235',
            },
        ],
    }]

    # Extract token (supposedly JWT) from javascript
    # Note: javascript file number/names and token variable name may change
    def _extract_token(self, webpage):
        js_urls = re.findall(r'<script[^>]+src=["\'](/assets/[^"\']+\.js)["\']', webpage)
        js_urls = [urljoin('https://podcasts.apple.com', u) for u in js_urls]

        auth_token = None
        for js_url in js_urls:
            js_code = self._download_webpage(js_url, 'Generic authorization token', fatal=False, note=f'Scanning {js_url}')
            if not js_code:
                continue
            match = re.search(r'const\s+mc="((?:eyJ)[^"]+)"', js_code)
            if match:
                auth_token = match.group(1)
                break

        if not auth_token:
            raise ExtractorError('Generic authorization token not found in any JS files')

        return auth_token

    # Call backend API pages and merge them as a single list
    def _unpaginate_episodes(self, playlist_id, token):
        base_url = 'https://amp-api.podcasts.apple.com/v1/catalog/fr/podcasts/'
        headers = {
            'Authorization': f'Bearer {token}',
            'Origin': 'https://podcasts.apple.com',
        }

        all_episodes = []
        offset = 0
        limit = 25  # Limit in use by website but other values seem to be accepted

        while True:
            episodes_url = f'{base_url}{playlist_id}/episodes?l=fr-FR&offset={offset}&limit={limit}'
            episodes_json = self._download_json(episodes_url, playlist_id, headers=headers, note=f'Downloading episodes offset {offset}')
            all_episodes.extend(episodes_json.get('data', []))
            if 'next' not in episodes_json:
                break
            offset += limit

        return all_episodes

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        server_data = self._search_json(
            ApplePodcastsBaseIE._BASE_HTML_JSON_LOCATION, webpage,
            'server data', playlist_id, contains_pattern=ApplePodcastsBaseIE._BASE_HTML_JSON_PATTERN)[0]['data']
        playlist_data = traverse_obj(server_data,
                                     (..., lambda _, v: v.get('contentType') == 'showHeaderRegular', 'items', 0),
                                     expected_type=dict, get_all=False)

        entries = []
        for e in self._unpaginate_episodes(playlist_id, self._extract_token(webpage)):
            episode_data = traverse_obj(e, {
                'id': ('id', {str}),
                'title': ('attributes', 'name', {str}),
                'uploader': ('attributes', 'artistName', {str}),
                'description': ('attributes', 'description', 'standard', {str}),
                'url': ('attributes', 'url', {clean_podcast_url}),
                'release_timestamp': ('attributes', 'releaseDateTime', {parse_iso8601}),
                'duration': ('attributes', 'durationInMilliseconds', {lambda x: int(x) // 1000}),
                'thumbnail_template': ('artwork', 'url', {str}),
                'thumb_width': ('artwork', 'width', {int}),
                'thumb_height': ('artwork', 'height', {int}),
            })

            if not episode_data.get('url'):
                continue

            entries.append({
                           '_type': 'url',
                           'ie_key': 'ApplePodcasts',
                           **episode_data,
                           })

        return self.playlist_result(entries,
                                    playlist_id,
                                    **traverse_obj(playlist_data, {
                                        'playlist_title': ('title', {str}),
                                        'playlist_description': ('description', {str}),
                                        'playlist_uploader': ('providerTitle', {str}),
                                    }))
