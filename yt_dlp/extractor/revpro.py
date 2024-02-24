import functools

from .common import InfoExtractor
from .vimeo import VHXEmbedIE
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_by_id,
    get_elements_html_by_class,
    int_or_none,
    traverse_obj,
    unified_strdate,
    urlencode_postdata,
)


class RevProIE(InfoExtractor):
    _LOGIN_URL = 'https://www.revproondemand.com/login'
    _NETRC_MACHINE = 'revpro'

    _VALID_URL = r'https?://(?:www\.)?revproondemand\.com/(?:[^/]+/)*videos/(?P<id>[^/]+)/?$'


    def _get_authenticity_token(self, display_id):
        signin_page = self._download_webpage(
            self._LOGIN_URL, display_id, note='Getting authenticity token')
        return self._html_search_regex(
            r'name=["\']authenticity_token["\'] value=["\'](.+?)["\']',
            signin_page, 'authenticity_token')

    def _login(self, display_id):
        username, password = self._get_login_info()
        if not username:
            return True

        response = self._download_webpage(
            self._LOGIN_URL, display_id, note='Logging in', fatal=False,
            data=urlencode_postdata({
                'email': username,
                'password': password,
                'authenticity_token': self._get_authenticity_token(display_id),
                'utf8': True
            }))

        user_has_subscription = self._search_regex(
            r'user_has_subscription:\s*["\'](.+?)["\']', response, 'subscription status', default='none')
        if user_has_subscription.lower() == 'true':
            return
        elif user_has_subscription.lower() == 'false':
            return 'Account is not subscribed'
        else:
            return 'Incorrect username/password'

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = None
        if self._get_cookies('https://www.revproondemand.com').get('_session'):
            webpage = self._download_webpage(url, display_id)
        if not webpage or '<div id="watch-unauthorized"' in webpage:
            login_err = self._login(display_id)
            webpage = self._download_webpage(url, display_id)
            if login_err and '<div id="watch-unauthorized"' in webpage:
                if login_err is True:
                    self.raise_login_required(method='any')
                raise ExtractorError(login_err, expected=True)

        embed_url = self._search_regex(r'embed_url:\s*["\'](.+?)["\']', webpage, 'embed url')
        thumbnail = self._og_search_thumbnail(webpage)
        watch_info = get_element_by_id('watch-info', webpage) or ''

        title = clean_html(get_element_by_class('video-title', watch_info))
        season_episode = get_element_by_class(
            'site-font-secondary-color', get_element_by_class('text', watch_info))
        episode_number = int_or_none(self._search_regex(
            r'Episode (\d+)', season_episode or '', 'episode', default=None))

        return {
            '_type': 'url_transparent',
            'ie_key': VHXEmbedIE.ie_key(),
            'url': VHXEmbedIE._smuggle_referrer(embed_url, 'https://www.revproondemand.com'),
            'id': self._search_regex(r'embed\.vhx\.tv/videos/(.+?)\?', embed_url, 'id'),
            'display_id': display_id,
            'title': title,
            'description': self._html_search_meta('description', webpage, fatal=False),
            'thumbnail': thumbnail.split('?')[0] if thumbnail else None,  # Ignore crop/downscale
            'series': clean_html(get_element_by_class('series-title', watch_info)),
            'episode_number': episode_number,
            'episode': title if episode_number else None,
            'season_number': int_or_none(self._search_regex(
                r'Season (\d+),', season_episode or '', 'season', default=None)),
            'release_date': unified_strdate(self._search_regex(
                r'data-meta-field-name=["\']release_dates["\'] data-meta-field-value=["\'](.+?)["\']',
                watch_info, 'release date', default=None)),
        }


class RevProSeasonIE(InfoExtractor):
    _PAGE_SIZE = 24
    _VALID_URL = r'https?://(?:www\.)?revproondemand\.com/(?P<id>[^\/$&?#]+)(?:/?$|/season:(?P<season>[0-9]+)/?$)'

    def _fetch_page(self, url, season_id, page):
        page += 1
        webpage = self._download_webpage(
            f'{url}?page={page}', season_id, note=f'Downloading page {page}', expected_status={400})
        yield from [self.url_result(item_url, RevProIE) for item_url in traverse_obj(
            get_elements_html_by_class('browse-item-link', webpage), (..., {extract_attributes}, 'href'))]

    def _real_extract(self, url):
        season_id = self._match_id(url)
        season_num = self._match_valid_url(url).group('season') or 1
        season_title = season_id.replace('-', ' ').title()

        return self.playlist_result(
            OnDemandPagedList(functools.partial(self._fetch_page, url, season_id), self._PAGE_SIZE),
            f'{season_id}-season-{season_num}', f'{season_title} - Season {season_num}')
