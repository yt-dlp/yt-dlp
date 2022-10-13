from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    js_to_json,
    smuggle_url,
    str_or_none,
    traverse_obj,
    unescapeHTML,
)


class GeniusIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?genius\.com/videos/(?P<id>[^?/#]+)'
    _TESTS = [{
        'url': 'https://genius.com/videos/Vince-staples-breaks-down-the-meaning-of-when-sparks-fly',
        'md5': '64c2ad98cfafcfda23bfa0ad0c512f4c',
        'info_dict': {
            'id': '6313303597112',
            'ext': 'mp4',
            'title': 'Vince Staples Breaks Down The Meaning Of “When Sparks Fly”',
            'description': 'md5:bc15e00342c537c0039d414423ae5752',
            'tags': 'count:1',
            'uploader_id': '4863540648001',
            'duration': 388.416,
            'upload_date': '20221005',
            'timestamp': 1664982341,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }, {
        'url': 'https://genius.com/videos/Breaking-down-drakes-certified-lover-boy-kanye-beef-way-2-sexy-cudi',
        'md5': 'b8ed87a5efd1473bd027c20a969d4060',
        'info_dict': {
            'id': '6271792014001',
            'ext': 'mp4',
            'title': 'md5:c6355f7fa8a70bc86492a3963919fc15',
            'description': 'md5:1774638c31548b31b037c09e9b821393',
            'tags': 'count:3',
            'uploader_id': '4863540648001',
            'duration': 2685.099,
            'upload_date': '20210909',
            'timestamp': 1631209167,
            'thumbnail': r're:^https?://.*\.jpg$',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        metadata = self._search_json(
            r'<meta content="', webpage, 'metadata', display_id, transform_source=unescapeHTML)
        video_id = traverse_obj(
            metadata, ('video', 'provider_id'),
            ('dfp_kv', lambda _, x: x['name'] == 'brightcove_video_id', 'values', 0), get_all=False)
        if not video_id:
            raise ExtractorError('Brightcove video id not found in webpage')

        config = self._search_json(r'var\s*APP_CONFIG\s*=', webpage, 'config', video_id, default={})
        account_id = config.get('brightcove_account_id', '4863540648001')
        player_id = traverse_obj(
            config, 'brightcove_standard_web_player_id', 'brightcove_standard_no_autoplay_web_player_id',
            'brightcove_modal_web_player_id', 'brightcove_song_story_web_player_id', default='S1ZcmcOC1x')

        return self.url_result(
            smuggle_url(
                f'https://players.brightcove.net/{account_id}/{player_id}_default/index.html?videoId={video_id}',
                {'referrer': url}), 'BrightcoveNew', video_id)


class GeniusLyricsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?genius\.com/(?P<id>[^?/#]+)-lyrics[?/#]?'
    _TESTS = [{
        'url': 'https://genius.com/Lil-baby-heyy-lyrics',
        'playlist_mincount': 2,
        'info_dict': {
            'id': '8454545',
            'title': 'Heyy',
            'description': 'Heyy by Lil Baby',
        },
    }, {
        'url': 'https://genius.com/Outkast-two-dope-boyz-in-a-cadillac-lyrics',
        'playlist_mincount': 1,
        'info_dict': {
            'id': '36239',
            'title': 'Two Dope Boyz (In a Cadillac)',
            'description': 'Two Dope Boyz (In a Cadillac) by OutKast',
        },
    }, {
        'url': 'https://genius.com/Playboi-carti-rip-lyrics',
        'playlist_mincount': 1,
        'info_dict': {
            'id': '3710582',
            'title': 'R.I.P.',
            'description': 'R.I.P. by Playboi Carti',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        json_string = self._search_json(
            r'window\.__PRELOADED_STATE__\s*=\s*JSON\.parse\(', webpage, 'json string',
            display_id, transform_source=js_to_json, contains_pattern=r'\'{(?s:.+)}\'')
        song_info = self._parse_json(json_string, display_id)
        song_id = str_or_none(traverse_obj(song_info, ('songPage', 'song')))
        if not song_id:
            raise ExtractorError('Song id not found in webpage')

        title = traverse_obj(
            song_info, ('songPage', 'trackingData', lambda _, x: x['key'] == 'Title', 'value'),
            get_all=False, default='untitled')
        artist = traverse_obj(
            song_info, ('songPage', 'trackingData', lambda _, x: x['key'] == 'Primary Artist', 'value'),
            get_all=False, default='unknown artist')
        media = traverse_obj(
            song_info, ('entities', 'songs', song_id, 'media'), expected_type=list, default=[])

        entries = []
        for m in media:
            if m.get('type') in ('video', 'audio') and m.get('url'):
                if m.get('provider') == 'spotify':
                    self.to_screen(f'{song_id}: Skipping Spotify audio embed')
                else:
                    entries.append(self.url_result(m['url']))

        return self.playlist_result(entries, song_id, title, f'{title} by {artist}')
