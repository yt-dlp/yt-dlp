from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_age_limit,
)


class ViewLiftBaseIE(InfoExtractor):
    _API_BASE = 'https://prod-api.viewlift.com/'
    _DOMAINS_REGEX = r'(?:(?:main\.)?snagfilms|snagxtreme|funnyforfree|kiddovid|winnersview|(?:monumental|lax)sportsnetwork|vayafilm|failarmy|ftfnext|lnppass\.legapallacanestro|moviespree|app\.myoutdoortv|neoufitness|pflmma|theidentitytb)\.com|(?:hoichoi|app\.horseandcountry|kronon|marquee|supercrosslive)\.tv'
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
    }
    _TOKENS = {}

    def _call_api(self, site, path, video_id, query):
        token = self._TOKENS.get(site)
        if not token:
            token_query = {'site': site}
            email, password = self._get_login_info(netrc_machine=site)
            if email:
                resp = self._download_json(
                    self._API_BASE + 'identity/signin', video_id,
                    'Logging in', query=token_query, data=json.dumps({
                        'email': email,
                        'password': password,
                    }).encode())
            else:
                resp = self._download_json(
                    self._API_BASE + 'identity/anonymous-token', video_id,
                    'Downloading authorization token', query=token_query)
            self._TOKENS[site] = token = resp['authorizationToken']
        return self._download_json(
            self._API_BASE + path, video_id,
            headers={'Authorization': token}, query=query)


class ViewLiftEmbedIE(ViewLiftBaseIE):
    IE_NAME = 'viewlift:embed'
    _VALID_URL = r'https?://(?:(?:www|embed)\.)?(?P<domain>%s)/embed/player\?.*\bfilmId=(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})' % ViewLiftBaseIE._DOMAINS_REGEX
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

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:embed\.)?(?:%s)/embed/player.+?)\1' % ViewLiftBaseIE._DOMAINS_REGEX,
            webpage)
        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        domain, film_id = re.match(self._VALID_URL, url).groups()
        site = domain.split('.')[-2]
        if site in self._SITE_MAP:
            site = self._SITE_MAP[site]
        try:
            content_data = self._call_api(
                site, 'entitlement/video/status', film_id, {
                    'id': film_id
                })['video']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                error_message = self._parse_json(e.cause.read().decode(), film_id).get('errorMessage')
                if error_message == 'User does not have a valid subscription or has not purchased this content.':
                    self.raise_login_required()
                raise ExtractorError(error_message, expected=True)
            raise
        gist = content_data['gist']
        title = gist['title']
        video_assets = content_data['streamingInfo']['videoAssets']

        formats = []
        mpeg_video_assets = video_assets.get('mpeg') or []
        for video_asset in mpeg_video_assets:
            video_asset_url = video_asset.get('url')
            if not video_asset:
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

        hls_url = video_assets.get('hls')
        if hls_url:
            formats.extend(self._extract_m3u8_formats(
                hls_url, film_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False))
        self._sort_formats(formats)

        info = {
            'id': film_id,
            'title': title,
            'description': gist.get('description'),
            'thumbnail': gist.get('videoImageUrl'),
            'duration': int_or_none(gist.get('runtime')),
            'age_limit': parse_age_limit(content_data.get('parentalRating')),
            'timestamp': int_or_none(gist.get('publishDate'), 1000),
            'formats': formats,
        }
        for k in ('categories', 'tags'):
            info[k] = [v['title'] for v in content_data.get(k, []) if v.get('title')]
        return info


class ViewLiftIE(ViewLiftBaseIE):
    IE_NAME = 'viewlift'
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
    }]

    @classmethod
    def suitable(cls, url):
        return False if ViewLiftEmbedIE.suitable(url) else super(ViewLiftIE, cls).suitable(url)

    def _real_extract(self, url):
        domain, path, display_id = re.match(self._VALID_URL, url).groups()
        site = domain.split('.')[-2]
        if site in self._SITE_MAP:
            site = self._SITE_MAP[site]
        modules = self._call_api(
            site, 'content/pages', display_id, {
                'includeContent': 'true',
                'moduleOffset': 1,
                'path': path,
                'site': site,
            })['modules']
        film_id = next(m['contentData'][0]['gist']['id'] for m in modules if m.get('moduleType') == 'VideoDetailModule')
        return {
            '_type': 'url_transparent',
            'url': 'http://%s/embed/player?filmId=%s' % (domain, film_id),
            'id': film_id,
            'display_id': display_id,
            'ie_key': 'ViewLiftEmbed',
        }
