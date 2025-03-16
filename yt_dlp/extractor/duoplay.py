from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    get_element_text_and_html_by_tag,
    int_or_none,
    join_nonempty,
    parse_qs,
    str_or_none,
    try_call,
    unified_timestamp,
)
from ..utils.traversal import traverse_obj, value


class DuoplayIE(InfoExtractor):
    _VALID_URL = r'https?://duoplay\.ee/(?P<id>\d+)(?:[/?#]|$)'
    _TESTS = [{
        'note': 'Siberi võmm S02E12',
        'url': 'https://duoplay.ee/4312/siberi-vomm?ep=24',
        'md5': '1ff59d535310ac9c5cf5f287d8f91b2d',
        'info_dict': {
            'id': '4312_24',
            'ext': 'mp4',
            'title': 'Operatsioon "Öö"',
            'thumbnail': r're:https://.+\.jpg(?:\?c=\d+)?$',
            'description': 'md5:8ef98f38569d6b8b78f3d350ccc6ade8',
            'upload_date': '20170523',
            'timestamp': 1495567800,
            'series': 'Siberi võmm',
            'series_id': '4312',
            'season': 'Season 2',
            'season_number': 2,
            'episode': 'Operatsioon "Öö"',
            'episode_number': 12,
            'episode_id': '24',
        },
        'skip': 'No video found',
    }, {
        'note': 'Empty title',
        'url': 'https://duoplay.ee/17/uhikarotid?ep=14',
        'md5': 'cba9f5dabf2582b224d80ac44fb80e47',
        'info_dict': {
            'id': '17_14',
            'ext': 'mp4',
            'title': 'Episode 14',
            'thumbnail': r're:https?://.+\.jpg',
            'description': 'md5:4719b418e058c209def41d48b601276e',
            'upload_date': '20100916',
            'timestamp': 1284661800,
            'series': 'Ühikarotid',
            'series_id': '17',
            'season': 'Season 2',
            'season_number': 2,
            'episode_id': '14',
            'release_year': 2010,
            'episode': 'Episode 14',
            'episode_number': 14,
        },
    }, {
        'note': 'Movie without expiry',
        'url': 'https://duoplay.ee/5501/pilvede-all.-neljas-ode',
        'md5': '7abf63d773a49ef7c39f2c127842b8fd',
        'info_dict': {
            'id': '5501',
            'ext': 'mp4',
            'title': 'Pilvede all. Neljas õde',
            'thumbnail': r're:https://.+\.jpg(?:\?c=\d+)?$',
            'description': 'md5:d86a70f8f31e82c369d4d4f4c79b1279',
            'cast': 'count:9',
            'upload_date': '20221214',
            'timestamp': 1671054000,
            'release_year': 2018,
        },
        'skip': 'No video found',
    }, {
        'note': 'Episode url without show name',
        'url': 'https://duoplay.ee/9644?ep=185',
        'md5': '63f324b4fe2dbd8194dca16a6d52184a',
        'info_dict': {
            'id': '9644_185',
            'ext': 'mp4',
            'title': 'Episode 185',
            'thumbnail': r're:https?://.+\.jpg',
            'description': 'md5:ed25ba4e9e5d54bc291a4a0cdd241467',
            'upload_date': '20241120',
            'timestamp': 1732077000,
            'episode': 'Episode 63',
            'episode_id': '185',
            'episode_number': 63,
            'season': 'Season 2',
            'season_number': 2,
            'series': 'Telehommik',
            'series_id': '9644',
        },
    }]

    def _real_extract(self, url):
        telecast_id = self._match_id(url)
        episode = traverse_obj(parse_qs(url), ('ep', 0, {int_or_none}, {str_or_none}))
        video_id = join_nonempty(telecast_id, episode, delim='_')
        webpage = self._download_webpage(url, video_id)
        video_player = try_call(lambda: extract_attributes(
            get_element_text_and_html_by_tag('video-player', webpage)[1]))
        if not video_player or not video_player.get('manifest-url'):
            raise ExtractorError('No video found', expected=True)

        manifest_url = video_player['manifest-url']
        session_token = self._download_json(
            'https://sts.postimees.ee/session/register', video_id, 'Registering session',
            'Unable to register session', headers={
                'Accept': 'application/json',
                'X-Original-URI': manifest_url,
            })['session']

        episode_attr = self._parse_json(video_player.get(':episode') or '', video_id, fatal=False) or {}

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(manifest_url, video_id, 'mp4', query={'s': session_token}),
            **traverse_obj(episode_attr, {
                'title': ('title', {str}),
                'description': ('synopsis', {str}),
                'thumbnail': ('images', 'original'),
                'timestamp': ('airtime', {lambda x: unified_timestamp(x + ' +0200')}),
                'cast': ('cast', filter, {lambda x: x.split(', ')}),
                'release_year': ('year', {int_or_none}),
            }),
            **(traverse_obj(episode_attr, {
                'title': (None, (('subtitle', {str}, filter), {value(f'Episode {episode}' if episode else None)})),
                'series': ('title', {str}),
                'series_id': ('telecast_id', {str_or_none}),
                'season_number': ('season_id', {int_or_none}),
                'episode': ('subtitle', {str}, filter),
                'episode_number': ('episode_nr', {int_or_none}),
                'episode_id': ('episode_id', {str_or_none}),
            }, get_all=False) if episode_attr.get('category') != 'movies' else {}),
        }
