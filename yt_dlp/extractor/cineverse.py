import re

from .common import InfoExtractor
from ..utils import (
    filter_dict,
    int_or_none,
    parse_age_limit,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
    url_or_none,
)


class CineverseBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://www\.(?P<host>{})'.format('|'.join(map(re.escape, (
        'cineverse.com',
        'asiancrush.com',
        'dovechannel.com',
        'screambox.com',
        'midnightpulp.com',
        'fandor.com',
        'retrocrush.tv',
    ))))


class CineverseIE(CineverseBaseIE):
    _VALID_URL = rf'{CineverseBaseIE._VALID_URL_BASE}/watch/(?P<id>[A-Z0-9]+)'
    _TESTS = [{
        'url': 'https://www.asiancrush.com/watch/DMR00018919/Women-Who-Flirt',
        'skip': 'geo-blocked',
        'info_dict': {
            'title': 'Women Who Flirt',
            'ext': 'mp4',
            'id': 'DMR00018919',
            'modified_timestamp': 1678744575289,
            'cast': ['Xun Zhou', 'Xiaoming Huang', 'Yi-Lin Sie', 'Sonia Sui', 'Quniciren'],
            'duration': 5811.597,
            'description': 'md5:892fd62a05611d394141e8394ace0bc6',
            'age_limit': 13,
        },
    }, {
        'url': 'https://www.retrocrush.tv/watch/1000000023016/Archenemy! Crystal Bowie',
        'skip': 'geo-blocked',
        'info_dict': {
            'title': 'Archenemy! Crystal Bowie',
            'ext': 'mp4',
            'id': '1000000023016',
            'episode_number': 3,
            'season_number': 1,
            'cast': ['Nachi Nozawa', 'Yoshiko Sakakibara', 'Toshiko Fujita'],
            'age_limit': 0,
            'episode': 'Episode 3',
            'season': 'Season 1',
            'duration': 1485.067,
            'description': 'Cobra meets a beautiful bounty hunter by the name of Jane Royal.',
            'series': 'Space Adventure COBRA (Original Japanese)',
        },
    }]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, default={})
        self._initialize_geo_bypass({
            'countries': smuggled_data.get('geo_countries'),
        })
        video_id = self._match_id(url)
        html = self._download_webpage(url, video_id)
        idetails = self._search_nextjs_data(html, video_id)['props']['pageProps']['idetails']

        err_code = idetails.get('err_code')
        if err_code == 1002:
            self.raise_login_required()
        elif err_code == 1200:
            self.raise_geo_restricted(
                'This video is not available from your location due to geo restriction. '
                'You may be able to bypass it by using the /details/ page instead of the /watch/ page',
                countries=smuggled_data.get('geo_countries'))

        return {
            'subtitles': filter_dict({
                'en': traverse_obj(idetails, (('cc_url_vtt', 'subtitle_url'), {'url': {url_or_none}})) or None,
            }),
            'formats': self._extract_m3u8_formats(idetails['url'], video_id),
            **traverse_obj(idetails, {
                'title': 'title',
                'id': ('details', 'item_id'),
                'description': ('details', 'description'),
                'duration': ('duration', {lambda x: x / 1000}),
                'cast': ('details', 'cast', {lambda x: x.split(', ')}),
                'modified_timestamp': ('details', 'updated_by', 0, 'update_time', 'time', {int_or_none}),
                'season_number': ('details', 'season', {int_or_none}),
                'episode_number': ('details', 'episode', {int_or_none}),
                'age_limit': ('details', 'rating_code', {parse_age_limit}),
                'series': ('details', 'series_details', 'title'),
            }),
        }


class CineverseDetailsIE(CineverseBaseIE):
    _VALID_URL = rf'{CineverseBaseIE._VALID_URL_BASE}/details/(?P<id>[A-Z0-9]+)'
    _TESTS = [{
        'url': 'https://www.retrocrush.tv/details/1000000023012/Space-Adventure-COBRA-(Original-Japanese)',
        'playlist_mincount': 30,
        'info_dict': {
            'title': 'Space Adventure COBRA (Original Japanese)',
            'id': '1000000023012',
        },
    }, {
        'url': 'https://www.asiancrush.com/details/NNVG4938/Hansel-and-Gretel',
        'info_dict': {
            'id': 'NNVG4938',
            'ext': 'mp4',
            'title': 'Hansel and Gretel',
            'description': 'md5:e3e4c35309c2e82aee044f972c2fb05d',
            'cast': ['Jeong-myeong Cheon', 'Eun Won-jae', 'Shim Eun-gyeong', 'Ji-hee Jin', 'Hee-soon Park', 'Lydia Park', 'Kyeong-ik Kim'],
            'duration': 7030.732,
        },
    }]

    def _real_extract(self, url):
        host, series_id = self._match_valid_url(url).group('host', 'id')
        html = self._download_webpage(url, series_id)
        pageprops = self._search_nextjs_data(html, series_id)['props']['pageProps']

        geo_countries = traverse_obj(pageprops, ('itemDetailsData', 'geo_country', {lambda x: x.split(', ')}))
        geoblocked = traverse_obj(pageprops, (
            'itemDetailsData', 'playback_err_msg')) == 'This title is not available in your location.'

        def item_result(item):
            item_url = f'https://www.{host}/watch/{item["item_id"]}/{item["title"]}'
            if geoblocked:
                item_url = smuggle_url(item_url, {'geo_countries': geo_countries})
            return self.url_result(item_url, CineverseIE)

        season = traverse_obj(pageprops, ('seasonEpisodes', ..., 'episodes', lambda _, v: v['item_id'] and v['title']))
        if season:
            return self.playlist_result([item_result(ep) for ep in season], playlist_id=series_id,
                                        playlist_title=traverse_obj(pageprops, ('itemDetailsData', 'title')))
        return item_result(pageprops['itemDetailsData'])
