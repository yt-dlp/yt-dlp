from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    LazyList,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    parse_qs,
    str_or_none,
    traverse_obj,
    update_url_query,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class RoosterTeethBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'roosterteeth'
    _API_BASE = 'https://svod-be.roosterteeth.com'
    _API_BASE_URL = f'{_API_BASE}/api/v1'

    def _perform_login(self, username, password):
        if self._get_cookies(self._API_BASE_URL).get('rt_access_token'):
            return

        try:
            self._download_json(
                'https://auth.roosterteeth.com/oauth/token',
                None, 'Logging in', data=urlencode_postdata({
                    'client_id': '4338d2b4bdc8db1239360f28e72f0d9ddb1fd01e7a38fbb07b4b1f4ba4564cc5',
                    'grant_type': 'password',
                    'username': username,
                    'password': password,
                }))
        except ExtractorError as e:
            msg = 'Unable to login'
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                resp = self._parse_json(e.cause.response.read().decode(), None, fatal=False)
                if resp:
                    error = resp.get('extra_info') or resp.get('error_description') or resp.get('error')
                    if error:
                        msg += ': ' + error
            self.report_warning(msg)

    def _extract_video_info(self, data):
        thumbnails = []
        for image in traverse_obj(data, ('included', 'images')):
            if image.get('type') not in ('episode_image', 'bonus_feature_image'):
                continue
            thumbnails.extend([{
                'id': name,
                'url': url,
            } for name, url in (image.get('attributes') or {}).items() if url_or_none(url)])

        attributes = data.get('attributes') or {}
        title = traverse_obj(attributes, 'title', 'display_title')
        sub_only = attributes.get('is_sponsors_only')

        return {
            'id': str(data.get('id')),
            'display_id': attributes.get('slug'),
            'title': title,
            'description': traverse_obj(attributes, 'description', 'caption'),
            'series': attributes.get('show_title'),
            'season_number': int_or_none(attributes.get('season_number')),
            'season_id': attributes.get('season_id'),
            'episode': title,
            'episode_number': int_or_none(attributes.get('number')),
            'episode_id': str_or_none(data.get('uuid')),
            'channel_id': attributes.get('channel_id'),
            'duration': int_or_none(attributes.get('length')),
            'release_timestamp': parse_iso8601(attributes.get('original_air_date')),
            'thumbnails': thumbnails,
            'availability': self._availability(
                needs_premium=sub_only, needs_subscription=sub_only, needs_auth=sub_only,
                is_private=False, is_unlisted=False),
            'tags': attributes.get('genres')
        }


class RoosterTeethIE(RoosterTeethBaseIE):
    _VALID_URL = r'https?://(?:.+?\.)?roosterteeth\.com/(?:episode|watch)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://roosterteeth.com/episode/million-dollars-but-season-2-million-dollars-but-the-game-announcement',
        'info_dict': {
            'id': '9156',
            'display_id': 'million-dollars-but-season-2-million-dollars-but-the-game-announcement',
            'ext': 'mp4',
            'title': 'Million Dollars, But... The Game Announcement',
            'description': 'md5:168a54b40e228e79f4ddb141e89fe4f5',
            'thumbnail': r're:^https?://.*\.png$',
            'series': 'Million Dollars, But...',
            'episode': 'Million Dollars, But... The Game Announcement',
            'tags': ['Game Show', 'Sketch'],
            'season_number': 2,
            'availability': 'public',
            'episode_number': 10,
            'episode_id': '00374575-464e-11e7-a302-065410f210c4',
            'season': 'Season 2',
            'season_id': 'ffa27d48-464d-11e7-a302-065410f210c4',
            'channel_id': '92b6bb21-91d2-4b1b-bf95-3268fa0d9939',
            'duration': 145,
            'release_timestamp': 1462982400,
            'release_date': '20160511',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://roosterteeth.com/watch/rwby-bonus-25',
        'info_dict': {
            'id': '40432',
            'display_id': 'rwby-bonus-25',
            'title': 'Grimm',
            'description': 'md5:f30ff570741213418a8d2c19868b93ab',
            'episode': 'Grimm',
            'channel_id': '92f780eb-ebfe-4bf5-a3b5-c6ad5460a5f1',
            'thumbnail': r're:^https?://.*\.(png|jpe?g)$',
            'ext': 'mp4',
            'availability': 'public',
            'episode_id': 'f8117b13-f068-499e-803e-eec9ea2dec8c',
            'episode_number': 3,
            'tags': ['Animation'],
            'season_id': '4b8f0a9e-12c4-41ed-8caa-fed15a85bab8',
            'season': 'Season 1',
            'series': 'RWBY: World of Remnant',
            'season_number': 1,
            'duration': 216,
            'release_timestamp': 1413489600,
            'release_date': '20141016',
        },
        'params': {'skip_download': True},
    }, {
        # only works with video_data['attributes']['url'] m3u8 url
        'url': 'https://www.roosterteeth.com/watch/achievement-hunter-achievement-hunter-fatality-walkthrough-deathstroke-lex-luthor-captain-marvel-green-lantern-and-wonder-woman',
        'info_dict': {
            'id': '25394',
            'ext': 'mp4',
            'title': 'Fatality Walkthrough: Deathstroke, Lex Luthor, Captain Marvel, Green Lantern, and Wonder Woman',
            'description': 'md5:91bb934698344fb9647b1c7351f16964',
            'availability': 'public',
            'thumbnail': r're:^https?://.*\.(png|jpe?g)$',
            'episode': 'Fatality Walkthrough: Deathstroke, Lex Luthor, Captain Marvel, Green Lantern, and Wonder Woman',
            'episode_number': 71,
            'episode_id': 'ffaec998-464d-11e7-a302-065410f210c4',
            'season': 'Season 2008',
            'tags': ['Gaming'],
            'series': 'Achievement Hunter',
            'display_id': 'md5:4465ce4f001735f9d7a2ae529a543d31',
            'season_id': 'ffa13340-464d-11e7-a302-065410f210c4',
            'season_number': 2008,
            'channel_id': '2cb2a70c-be50-46f5-93d7-84a1baabb4f7',
            'duration': 189,
            'release_timestamp': 1228317300,
            'release_date': '20081203',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'http://achievementhunter.roosterteeth.com/episode/off-topic-the-achievement-hunter-podcast-2016-i-didn-t-think-it-would-pass-31',
        'only_matching': True,
    }, {
        'url': 'http://funhaus.roosterteeth.com/episode/funhaus-shorts-2016-austin-sucks-funhaus-shorts',
        'only_matching': True,
    }, {
        'url': 'http://screwattack.roosterteeth.com/episode/death-battle-season-3-mewtwo-vs-shadow',
        'only_matching': True,
    }, {
        'url': 'http://theknow.roosterteeth.com/episode/the-know-game-news-season-1-boring-steam-sales-are-better',
        'only_matching': True,
    }, {
        # only available for FIRST members
        'url': 'http://roosterteeth.com/episode/rt-docs-the-world-s-greatest-head-massage-the-world-s-greatest-head-massage-an-asmr-journey-part-one',
        'only_matching': True,
    }, {
        'url': 'https://roosterteeth.com/watch/million-dollars-but-season-2-million-dollars-but-the-game-announcement',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        api_episode_url = f'{self._API_BASE_URL}/watch/{display_id}'

        try:
            video_data = self._download_json(
                api_episode_url + '/videos', display_id, 'Downloading video JSON metadata',
                headers={'Client-Type': 'web'})['data'][0]  # web client-type yields ad-free streams
            m3u8_url = video_data['attributes']['url']
            # XXX: additional ad-free URL at video_data['links']['download'] but often gives 403 errors
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                if self._parse_json(e.cause.response.read().decode(), display_id).get('access') is False:
                    self.raise_login_required(
                        '%s is only available for FIRST members' % display_id)
            raise

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, display_id, 'mp4', 'm3u8_native', m3u8_id='hls')

        episode = self._download_json(
            api_episode_url, display_id,
            'Downloading episode JSON metadata')['data'][0]

        return {
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            **self._extract_video_info(episode)
        }


class RoosterTeethSeriesIE(RoosterTeethBaseIE):
    _VALID_URL = r'https?://(?:.+?\.)?roosterteeth\.com/series/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://roosterteeth.com/series/rwby?season=7',
        'playlist_count': 13,
        'info_dict': {
            'id': 'rwby-7',
            'title': 'RWBY - Season 7',
        }
    }, {
        'url': 'https://roosterteeth.com/series/role-initiative',
        'playlist_mincount': 16,
        'info_dict': {
            'id': 'role-initiative',
            'title': 'Role Initiative',
        }
    }, {
        'url': 'https://roosterteeth.com/series/let-s-play-minecraft?season=9',
        'playlist_mincount': 50,
        'info_dict': {
            'id': 'let-s-play-minecraft-9',
            'title': 'Let\'s Play Minecraft - Season 9',
        }
    }]

    def _entries(self, series_id, season_number):
        display_id = join_nonempty(series_id, season_number)
        # TODO: extract bonus material
        for data in self._download_json(
                f'{self._API_BASE_URL}/shows/{series_id}/seasons?order=asc&order_by', display_id)['data']:
            idx = traverse_obj(data, ('attributes', 'number'))
            if season_number and idx != season_number:
                continue
            season_url = update_url_query(urljoin(self._API_BASE, data['links']['episodes']), {'per_page': 1000})
            season = self._download_json(season_url, display_id, f'Downloading season {idx} JSON metadata')['data']
            for episode in season:
                yield self.url_result(
                    f'https://www.roosterteeth.com{episode["canonical_links"]["self"]}',
                    RoosterTeethIE.ie_key(),
                    **self._extract_video_info(episode))

    def _real_extract(self, url):
        series_id = self._match_id(url)
        season_number = traverse_obj(parse_qs(url), ('season', 0), expected_type=int_or_none)

        entries = LazyList(self._entries(series_id, season_number))
        return self.playlist_result(
            entries,
            join_nonempty(series_id, season_number),
            join_nonempty(entries[0].get('series'), season_number, delim=' - Season '))
