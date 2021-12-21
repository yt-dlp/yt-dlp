# coding: utf-8
from .common import InfoExtractor
from .vimeo import VHXEmbedIE
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    urlencode_postdata,
    get_element_by_id,
    get_element_by_class,
    get_elements_by_class,
    clean_html,
    unified_strdate
)


class DropoutIE(InfoExtractor):
    _LOGIN_URL = 'https://www.dropout.tv/login'
    _LOGOUT_URL = 'https://www.dropout.tv/logout'
    _NETRC_MACHINE = 'dropout'

    _VALID_URL = r'https?://(?:www\.)?dropout\.tv/(?:[^/]+/)*videos/(?P<id>[^/]+)/?$'
    _TESTS = [
        {
            'url': 'https://www.dropout.tv/game-changer/season:2/videos/yes-or-no',
            'note': 'Episode in a series',
            'md5': '5e000fdfd8d8fa46ff40456f1c2af04a',
            'info_dict': {
                'id': '738153',
                'display_id': 'yes-or-no',
                'ext': 'mp4',
                'title': 'Yes or No',
                'description': 'Ally, Brennan, and Zac are asked a simple question, but is there a correct answer?',
                'release_date': '20200508',
                'thumbnail': 'https://vhx.imgix.net/chuncensoredstaging/assets/351e3f24-c4a3-459a-8b79-dc80f1e5b7fd.jpg',
                'series': 'Game Changer',
                'season_number': 2,
                'season': 'Season 2',
                'episode_number': 6,
                'episode': 'Episode 6',
                'duration': 1180,
                'uploader_id': 'user80538407',
                'uploader_url': 'https://vimeo.com/user80538407',
                'uploader': 'OTT Videos'
            },
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest']
        },
        {
            'url': 'https://www.dropout.tv/dimension-20-fantasy-high/season:1/videos/episode-1',
            'note': 'Episode in a series (missing release_date)',
            'md5': '712caf7c191f1c47c8f1879520c2fa5c',
            'info_dict': {
                'id': '320562',
                'display_id': 'episode-1',
                'ext': 'mp4',
                'title': 'The Beginning Begins',
                'description': 'The cast introduces their PCs, including a neurotic elf, a goblin PI, and a corn-worshipping cleric.',
                'thumbnail': 'https://vhx.imgix.net/chuncensoredstaging/assets/4421ed0d-f630-4c88-9004-5251b2b8adfa.jpg',
                'series': 'Dimension 20: Fantasy High',
                'season_number': 1,
                'season': 'Season 1',
                'episode_number': 1,
                'episode': 'Episode 1',
                'duration': 6838,
                'uploader_id': 'user80538407',
                'uploader_url': 'https://vimeo.com/user80538407',
                'uploader': 'OTT Videos'
            },
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest']
        },
        {
            'url': 'https://www.dropout.tv/videos/misfits-magic-holiday-special',
            'note': 'Episode not in a series',
            'md5': 'c30fa18999c5880d156339f13c953a26',
            'info_dict': {
                'id': '1915774',
                'display_id': 'misfits-magic-holiday-special',
                'ext': 'mp4',
                'title': 'Misfits & Magic Holiday Special',
                'description': 'The magical misfits spend Christmas break at Gowpenny, with an unwelcome visitor.',
                'release_date': '20211215',
                'thumbnail': 'https://vhx.imgix.net/chuncensoredstaging/assets/d91ea8a6-b250-42ed-907e-b30fb1c65176-8e24b8e5.jpg',
                'duration': 11698,
                'uploader_id': 'user80538407',
                'uploader_url': 'https://vimeo.com/user80538407',
                'uploader': 'OTT Videos'
            },
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest']
        }
    ]

    def _get_authenticity_token(self, id: str = None):
        signin_page = self._download_webpage(self._LOGIN_URL, id,
                                             note='Getting authenticity token')
        authenticity_token = self._html_search_regex(
            r'name=["\']authenticity_token["\'] value=["\'](.+?)["\']',
            signin_page, 'authenticity_token')
        return authenticity_token

    def _login(self, id: str = None):
        username, password = self._get_login_info()
        if not (username and password):
            self.raise_login_required(method='password')

        payload = {
            'email': username,
            'password': password,
            'authenticity_token': self._get_authenticity_token(id),
            'utf8': True
        }
        response = self._download_webpage(self._LOGIN_URL, id, note='Logging in',
                                          data=urlencode_postdata(payload))

        user_has_subscription = self._search_regex(r'user_has_subscription: ["\'](.+?)["\']',
                                                   response, 'subscription_status', default='none')
        if user_has_subscription.lower() == 'true':
            return response  # This is what we want
        if user_has_subscription.lower() == 'false':
            raise ExtractorError(msg='Account is not subscribed')
        else:
            raise ExtractorError(msg='Incorrect username/password')

    def _real_extract(self, url):
        display_id = self._match_id(url)
        try:
            self._login(display_id)
            webpage = self._download_webpage(url, display_id, note='Downloading video webpage')
        finally:
            self._download_webpage(self._LOGOUT_URL, display_id, note='Logging out')

        embed_url = self._search_regex(r'embed_url: ["\'](.+?)["\']', webpage, 'embed_url')
        thumbnail = self._og_search_thumbnail(webpage)
        thumbnail = thumbnail.split('?')[0] if thumbnail else None  # Ignore crop/downscale
        watch_info = get_element_by_id('watch-info', webpage) or ''
        season_episode = (get_element_by_class('site-font-secondary-color',
                                               get_element_by_class('text', watch_info))
                          or '').strip()

        return {
            '_type': 'url_transparent',
            'ie_key': VHXEmbedIE.ie_key(),
            'url': embed_url,
            'id': self._search_regex(r'embed.vhx.tv/videos/(.+?)\?', embed_url, 'id'),
            'display_id': display_id,
            'description': self._html_search_meta('description', webpage,
                                                  display_name='description', fatal=False),
            'thumbnail': thumbnail,
            'title': clean_html(get_element_by_class('video-title', watch_info)),
            'release_date': unified_strdate(self._search_regex(
                                            r'data-meta-field-name=["\']release_dates["\'] data-meta-field-value=["\'](.+?)["\']',
                                            watch_info, 'release_date', default=None)),
            'series': clean_html(get_element_by_class('series-title', watch_info)),
            'season_number': int_or_none(self._search_regex(r'Season (\d+),', season_episode,
                                                            'season', default=None)),
            'episode_number': int_or_none(self._search_regex(r'Episode (\d+)', season_episode,
                                                             'episode', default=None))
        }


class DropoutSeasonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?dropout\.tv/(?P<id>[^\/$&?#]+)(?:/?$|/season:[0-9]+/?$)'
    _TESTS = [
        {
            'url': 'https://www.dropout.tv/dimension-20-fantasy-high/season:1',
            'note': 'Multi-season series with the season in the url',
            'playlist_count': 17,
            'info_dict': {
                'id': 'dimension-20-fantasy-high-season-1',
                'title': 'Dimension 20 Fantasy High - Season 1'
            }
        },
        {
            'url': 'https://www.dropout.tv/dimension-20-fantasy-high',
            'note': 'Multi-season series with the season not in the url',
            'playlist_count': 17,
            'info_dict': {
                'id': 'dimension-20-fantasy-high-season-1',
                'title': 'Dimension 20 Fantasy High - Season 1'
            }
        },
        {
            'url': 'https://www.dropout.tv/dimension-20-shriek-week',
            'note': 'Single-season series',
            'playlist_count': 4,
            'info_dict': {
                'id': 'dimension-20-shriek-week-season-1',
                'title': 'Dimension 20 Shriek Week - Season 1'
            }
        }
    ]

    def _real_extract(self, url):
        season_id = self._match_id(url)
        season_title = season_id.replace('-', ' ').title()
        webpage = self._download_webpage(url, season_id)

        entries = [
            self.url_result(
                url=self._search_regex(r'a href=["\'](.+?)["\'] class=["\']browse-item-link["\']',
                                       item, 'item_url'),
                ie=DropoutIE.ie_key()
            ) for item in get_elements_by_class('js-collection-item', webpage)
        ]

        seasons = (get_element_by_class('select-dropdown-wrapper', webpage) or '').strip().replace('\n', '')
        current_season = self._search_regex(r'<option(?:.+?)selected>[ ]+(.+?)[ ]+</option>',
                                            seasons, 'current_season', default=None)

        return {
            '_type': 'playlist',
            'id': join_nonempty(season_id, current_season.lower().replace(' ', '-')),
            'title': join_nonempty(season_title, current_season, delim=' - '),
            'playlist_count': len(entries),
            'entries': entries
        }
