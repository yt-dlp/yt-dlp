import json

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_age_limit,
    traverse_obj,
)


class ViewLiftBaseIE(InfoExtractor):
    _API_BASE = 'https://prod-api.viewlift.com/'
    _DOMAINS_REGEX = r'(?:(?:main\.)?snagfilms|snagxtreme|funnyforfree|kiddovid|winnersview|(?:monumental|lax)sportsnetwork|vayafilm|failarmy|ftfnext|lnppass\.legapallacanestro|moviespree|app\.myoutdoortv|neoufitness|pflmma|theidentitytb|chorki)\.com|(?:hoichoi|app\.horseandcountry|kronon|marquee|supercrosslive)\.tv'
    _SITE_MAP = {
        'ftfnext': 'lax',
        'funnyforfree': 'snagfilms',
        'hoichoi': 'hoichoitv',
        'kiddovid': 'snagfilms',
        'laxsportsnetwork': 'lax',
        'legapallacanestro': 'lnp',
        'marquee': 'marquee-tv',
        'monumentalsportsnetwork': 'monumental-network',
        'moviespree': 'bingeflix',
        'pflmma': 'pfl',
        'snagxtreme': 'snagfilms',
        'theidentitytb': 'tampabay',
        'vayafilm': 'snagfilms',
        'chorki': 'prothomalo',
    }
    _TOKENS = {}

    def _fetch_token(self, site, url):
        if self._TOKENS.get(site):
            return

        cookies = self._get_cookies(url)
        if cookies and cookies.get('token'):
            self._TOKENS[site] = self._search_regex(r'22authorizationToken\%22:\%22([^\%]+)\%22', cookies['token'].value, 'token')
        if not self._TOKENS.get(site):
            self.raise_login_required('Cookies (not necessarily logged in) are needed to download from this website', method='cookies')

    def _call_api(self, site, path, video_id, url, query):
        self._fetch_token(site, url)
        try:
            return self._download_json(
                self._API_BASE + path, video_id, headers={'Authorization': self._TOKENS.get(site)}, query=query)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                webpage = e.cause.response.read().decode()
                try:
                    error_message = traverse_obj(json.loads(webpage), 'errorMessage', 'message')
                except json.JSONDecodeError:
                    raise ExtractorError(f'{site} said: {webpage}', cause=e.cause)
                if error_message:
                    if 'has not purchased' in error_message:
                        self.raise_login_required(method='cookies')
                    raise ExtractorError(error_message, expected=True)
            raise


class ViewLiftEmbedIE(ViewLiftBaseIE):
    IE_NAME = 'viewlift:embed'
    _VALID_URL = r'https?://(?:(?:www|embed)\.)?(?P<domain>%s)/embed/player\?.*\bfilmId=(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})' % ViewLiftBaseIE._DOMAINS_REGEX
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:embed\.)?(?:%s)/embed/player.+?)\1' % ViewLiftBaseIE._DOMAINS_REGEX]
    _TESTS = [{
        'url': 'http://embed.snagfilms.com/embed/player?filmId=74849a00-85a9-11e1-9660-123139220831&w=500',
        'md5': '2924e9215c6eff7a55ed35b72276bd93',
        'info_dict': {
            'id': '74849a00-85a9-11e1-9660-123139220831',
            'ext': 'mp4',
            'title': '#whilewewatch',
            'description': 'md5:b542bef32a6f657dadd0df06e26fb0c8',
            'timestamp': 1334350096,
            'upload_date': '20120413',
        }
    }, {
        # invalid labels, 360p is better that 480p
        'url': 'http://www.snagfilms.com/embed/player?filmId=17ca0950-a74a-11e0-a92a-0026bb61d036',
        'md5': '882fca19b9eb27ef865efeeaed376a48',
        'info_dict': {
            'id': '17ca0950-a74a-11e0-a92a-0026bb61d036',
            'ext': 'mp4',
            'title': 'Life in Limbo',
        },
        'skip': 'The video does not exist',
    }, {
        'url': 'http://www.snagfilms.com/embed/player?filmId=0000014c-de2f-d5d6-abcf-ffef58af0017',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, film_id = self._match_valid_url(url).groups()
        site = domain.split('.')[-2]
        if site in self._SITE_MAP:
            site = self._SITE_MAP[site]

        content_data = self._call_api(
            site, 'entitlement/video/status', film_id, url, {
                'id': film_id
            })['video']
        gist = content_data['gist']
        title = gist['title']
        video_assets = content_data['streamingInfo']['videoAssets']

        hls_url = video_assets.get('hls')
        formats, subtitles = [], {}
        if hls_url:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                hls_url, film_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)

        for video_asset in video_assets.get('mpeg') or []:
            video_asset_url = video_asset.get('url')
            if not video_asset_url:
                continue
            bitrate = int_or_none(video_asset.get('bitrate'))
            height = int_or_none(self._search_regex(
                r'^_?(\d+)[pP]$', video_asset.get('renditionValue'),
                'height', default=None))
            formats.append({
                'url': video_asset_url,
                'format_id': 'http%s' % ('-%d' % bitrate if bitrate else ''),
                'tbr': bitrate,
                'height': height,
                'vcodec': video_asset.get('codec'),
            })

        subs = {}
        for sub in traverse_obj(content_data, ('contentDetails', 'closedCaptions')) or []:
            sub_url = sub.get('url')
            if not sub_url:
                continue
            subs.setdefault(sub.get('language', 'English'), []).append({
                'url': sub_url,
            })

        return {
            'id': film_id,
            'title': title,
            'description': gist.get('description'),
            'thumbnail': gist.get('videoImageUrl'),
            'duration': int_or_none(gist.get('runtime')),
            'age_limit': parse_age_limit(content_data.get('parentalRating')),
            'timestamp': int_or_none(gist.get('publishDate'), 1000),
            'formats': formats,
            'subtitles': self._merge_subtitles(subs, subtitles),
            'categories': traverse_obj(content_data, ('categories', ..., 'title')),
            'tags': traverse_obj(content_data, ('tags', ..., 'title')),
        }


class ViewLiftIE(ViewLiftBaseIE):
    IE_NAME = 'viewlift'
    _API_BASE = 'https://prod-api-cached-2.viewlift.com/'
    _VALID_URL = r'https?://(?:www\.)?(?P<domain>%s)(?P<path>(?:/(?:films/title|show|(?:news/)?videos?|watch))?/(?P<id>[^?#]+))' % ViewLiftBaseIE._DOMAINS_REGEX
    _TESTS = [{
        'url': 'http://www.snagfilms.com/films/title/lost_for_life',
        'md5': '19844f897b35af219773fd63bdec2942',
        'info_dict': {
            'id': '0000014c-de2f-d5d6-abcf-ffef58af0017',
            'display_id': 'lost_for_life',
            'ext': 'mp4',
            'title': 'Lost for Life',
            'description': 'md5:ea10b5a50405ae1f7b5269a6ec594102',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 4489,
            'categories': 'mincount:3',
            'age_limit': 14,
            'upload_date': '20150421',
            'timestamp': 1429656820,
        }
    }, {
        'url': 'http://www.snagfilms.com/show/the_world_cut_project/india',
        'md5': 'e6292e5b837642bbda82d7f8bf3fbdfd',
        'info_dict': {
            'id': '00000145-d75c-d96e-a9c7-ff5c67b20000',
            'display_id': 'the_world_cut_project/india',
            'ext': 'mp4',
            'title': 'India',
            'description': 'md5:5c168c5a8f4719c146aad2e0dfac6f5f',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 979,
            'timestamp': 1399478279,
            'upload_date': '20140507',
        }
    }, {
        'url': 'http://main.snagfilms.com/augie_alone/s_2_ep_12_love',
        'info_dict': {
            'id': '00000148-7b53-de26-a9fb-fbf306f70020',
            'display_id': 'augie_alone/s_2_ep_12_love',
            'ext': 'mp4',
            'title': 'S. 2 Ep. 12 - Love',
            'description': 'Augie finds love.',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 107,
            'upload_date': '20141012',
            'timestamp': 1413129540,
            'age_limit': 17,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://main.snagfilms.com/films/title/the_freebie',
        'only_matching': True,
    }, {
        # Film is not playable in your area.
        'url': 'http://www.snagfilms.com/films/title/inside_mecca',
        'only_matching': True,
    }, {
        # Film is not available.
        'url': 'http://www.snagfilms.com/show/augie_alone/flirting',
        'only_matching': True,
    }, {
        'url': 'http://www.winnersview.com/videos/the-good-son',
        'only_matching': True,
    }, {
        # Was once Kaltura embed
        'url': 'https://www.monumentalsportsnetwork.com/videos/john-carlson-postgame-2-25-15',
        'only_matching': True,
    }, {
        'url': 'https://www.marquee.tv/watch/sadlerswells-sacredmonsters',
        'only_matching': True,
    }, {  # Free film with langauge code
        'url': 'https://www.hoichoi.tv/bn/films/title/shuyopoka',
        'info_dict': {
            'id': '7a7a9d33-1f4c-4771-9173-ee4fb6dbf196',
            'ext': 'mp4',
            'title': 'Shuyopoka',
            'description': 'md5:e28f2fb8680096a69c944d37c1fa5ffc',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20211006',
            'series': None
        },
        'params': {'skip_download': True},
    }, {  # Free film
        'url': 'https://www.hoichoi.tv/films/title/dadu-no1',
        'info_dict': {
            'id': '0000015b-b009-d126-a1db-b81ff3780000',
            'ext': 'mp4',
            'title': 'Dadu No.1',
            'description': 'md5:605cba408e51a79dafcb824bdeded51e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20210827',
            'series': None
        },
        'params': {'skip_download': True},
    }, {  # Free episode
        'url': 'https://www.hoichoi.tv/webseries/case-jaundice-s01-e01',
        'info_dict': {
            'id': 'f779e07c-30c8-459c-8612-5a834ab5e5ba',
            'ext': 'mp4',
            'title': 'Humans Vs. Corona',
            'description': 'md5:ca30a682b4528d02a3eb6d0427dd0f87',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20210830',
            'series': 'Case Jaundice'
        },
        'params': {'skip_download': True},
    }, {  # Free video
        'url': 'https://www.hoichoi.tv/videos/1549072415320-six-episode-02-hindi',
        'info_dict': {
            'id': 'b41fa1ce-aca6-47b6-b208-283ff0a2de30',
            'ext': 'mp4',
            'title': 'Woman in red - Hindi',
            'description': 'md5:9d21edc1827d32f8633eb67c2054fc31',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20211006',
            'series': 'Six (Hindi)'
        },
        'params': {'skip_download': True},
    }, {  # Free episode
        'url': 'https://www.hoichoi.tv/shows/watch-asian-paints-moner-thikana-online-season-1-episode-1',
        'info_dict': {
            'id': '1f45d185-8500-455c-b88d-13252307c3eb',
            'ext': 'mp4',
            'title': 'Jisshu Sengupta',
            'description': 'md5:ef6ffae01a3d83438597367400f824ed',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20211004',
            'series': 'Asian Paints Moner Thikana'
        },
        'params': {'skip_download': True},
    }, {  # Free series
        'url': 'https://www.hoichoi.tv/shows/watch-moner-thikana-bengali-web-series-online',
        'playlist_mincount': 5,
        'info_dict': {
            'id': 'watch-moner-thikana-bengali-web-series-online',
        },
    }, {  # Premium series
        'url': 'https://www.hoichoi.tv/shows/watch-byomkesh-bengali-web-series-online',
        'playlist_mincount': 14,
        'info_dict': {
            'id': 'watch-byomkesh-bengali-web-series-online',
        },
    }, {  # Premium movie
        'url': 'https://www.hoichoi.tv/movies/detective-2020',
        'only_matching': True
    }, {  # Chorki Premium series
        'url': 'https://www.chorki.com/bn/series/sinpaat',
        'playlist_mincount': 7,
        'info_dict': {
            'id': 'bn/series/sinpaat',
        },
    }, {  # Chorki free movie
        'url': 'https://www.chorki.com/bn/videos/bangla-movie-bikkhov',
        'info_dict': {
            'id': '564e755b-f5c7-4515-aee6-8959bee18c93',
            'title': 'Bikkhov',
            'ext': 'mp4',
            'upload_date': '20230824',
            'timestamp': 1692860553,
            'categories': ['Action Movies', 'Salman Special'],
            'tags': 'count:14',
            'thumbnail': 'https://snagfilms-a.akamaihd.net/dd078ff5-b16e-45e4-9723-501b56b9df0a/images/2023/08/24/1692860450729_1920x1080_16x9Images.jpg',
            'display_id': 'bn/videos/bangla-movie-bikkhov',
            'description': 'md5:71492b086450625f4374a3eb824f27dc',
            'duration': 8002,
        },
        'params': {
            'skip_download': True,
        },
    }, {  # Chorki Premium movie
        'url': 'https://www.chorki.com/bn/videos/something-like-an-autobiography',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if ViewLiftEmbedIE.suitable(url) else super(ViewLiftIE, cls).suitable(url)

    def _show_entries(self, domain, seasons):
        for season in seasons:
            for episode in season.get('episodes') or []:
                path = traverse_obj(episode, ('gist', 'permalink'))
                if path:
                    yield self.url_result(f'https://www.{domain}{path}', ie=self.ie_key())

    def _real_extract(self, url):
        domain, path, display_id = self._match_valid_url(url).groups()
        site = domain.split('.')[-2]
        if site in self._SITE_MAP:
            site = self._SITE_MAP[site]
        modules = self._call_api(
            site, 'content/pages', display_id, url, {
                'includeContent': 'true',
                'moduleOffset': 1,
                'path': path,
                'site': site,
            })['modules']

        seasons = next((m['contentData'][0]['seasons'] for m in modules if m.get('moduleType') == 'ShowDetailModule'), None)
        if seasons:
            return self.playlist_result(self._show_entries(domain, seasons), display_id)

        film_id = next(m['contentData'][0]['gist']['id'] for m in modules if m.get('moduleType') == 'VideoDetailModule')
        return {
            '_type': 'url_transparent',
            'url': 'http://%s/embed/player?filmId=%s' % (domain, film_id),
            'id': film_id,
            'display_id': display_id,
            'ie_key': 'ViewLiftEmbed',
        }
