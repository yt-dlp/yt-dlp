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
        # episode
        'url': 'https://duoplay.ee/10162/morvad-mannikulas?ep=8',
        'info_dict': {
            'id': '10162_8',
            'ext': 'mp4',
            'title': 'Timukas, teine osa',
            'thumbnail': r're:^https?://.*\.(?:png|jpg)',
            'description': 'md5:bc34b242439c04267660a93014b0a880',
            'upload_date': '20250125',
            'timestamp': 1737837000,
            'episode': 'Timukas, teine osa',
            'episode_id': '8',
            'episode_number': 8,
            'series': 'Mõrvad Männikülas',
            'series_id': '10162',
            'cast': ['Alfred Molina', 'Rossif Sutherland', 'Elle-Máijá Tailfeathers'],
            'release_year': 2022,
        },
    }, {
        # episode - no name
        'url': 'https://duoplay.ee/10162/?ep=8',
        'info_dict': {
            'id': '10162_8',
            'ext': 'mp4',
            'title': 'Timukas, teine osa',
            'thumbnail': r're:^https?://.*\.(?:png|jpg)',
            'description': 'md5:bc34b242439c04267660a93014b0a880',
            'upload_date': '20250125',
            'timestamp': 1737837000,
            'episode': 'Timukas, teine osa',
            'episode_id': '8',
            'episode_number': 8,
            'series': 'Mõrvad Männikülas',
            'series_id': '10162',
            'cast': ['Alfred Molina', 'Rossif Sutherland', 'Elle-Máijá Tailfeathers'],
            'release_year': 2022,
        },
    }, {
        # movie
        'url': 'https://duoplay.ee/7573/estonia-27-aastat-vastamata-kusimusi',
        'info_dict': {
            'id': '7573',
            'ext': 'mp4',
            'title': 'Estonia - 27 aastat vastamata küsimusi',
            'thumbnail': r're:^https?://.*\.(?:png|jpg)',
            'description': 'md5:dbdeec1771f597cdede995347d55fd35',
            'upload_date': '20250928',
            'timestamp': 1759094400,
            'release_year': 2021,
            'series': 'Estonia - 27 aastat vastamata küsimusi',
            'series_id': '7573',
            'season': 'Season 0',
            'season_number': 0,
            'episode': 'Episode 0',
            'episode_number': 0,
            'episode_id': '0',
        },
    }, {
        # movie - multiple languages
        'url': 'https://duoplay.ee/12155/lego-sobrad.-heartlake-i-muusikal',
        'info_dict': {
            'id': '12155',
            'ext': 'mp4',
            'title': 'Lego sõbrad. Heartlake\'i muusikal',
            'thumbnail': r're:^https?://.*\.(?:png|jpg)',
            'description': 'md5:05ed3934d86222becb2c2e1a11ea2a8b',
            'upload_date': '20261213',
            'timestamp': 1797179400,
            'release_year': 2026,
            'series': 'Lego sõbrad. Heartlake\'i muusikal',
            'series_id': '12155',
            'episode': 'Episode 0',
            'episode_number': 0,
            'episode_id': '0',
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
            'https://sts.euddn.net/session/register', video_id, 'Registering session',
            'Unable to register session', headers={
                'Accept': 'application/json',
                'X-Original-URI': manifest_url,
            })['session']

        episode_attr = self._parse_json(video_player.get(':episode') or '', video_id, fatal=False) or {}

        formats = self._extract_m3u8_formats(manifest_url, video_id, 'mp4', query={'s': session_token})
        for f in formats:
            # Audio quality key undefined workaround
            if f.get('vcodec') == 'none':
                f['quality'] = int(f['format_id'].split('-')[0])
            # We need to manually flag video-only formats as such
            elif '_vo.m3u8' in f['url'] and not f.get('acodec'):
                f['acodec'] = 'none'

        return {
            'id': video_id,
            'formats': formats,
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
