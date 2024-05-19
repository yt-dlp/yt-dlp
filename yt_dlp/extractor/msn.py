import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    unescapeHTML,
)


class MSNIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:(?:www|preview)\.)?msn\.com/(?:[^/]+/)+(?P<display_id>[^/]+)/[a-z]{2}-(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        'url': 'https://www.msn.com/en-in/money/video/7-ways-to-get-rid-of-chest-congestion/vi-BBPxU6d',
        'md5': '087548191d273c5c55d05028f8d2cbcd',
        'info_dict': {
            'id': 'BBPxU6d',
            'display_id': '7-ways-to-get-rid-of-chest-congestion',
            'ext': 'mp4',
            'title': 'Seven ways to get rid of chest congestion',
            'description': '7 Ways to Get Rid of Chest Congestion',
            'duration': 88,
            'uploader': 'Health',
            'uploader_id': 'BBPrMqa',
        },
    }, {
        # Article, multiple Dailymotion Embeds
        'url': 'https://www.msn.com/en-in/money/sports/hottest-football-wags-greatest-footballers-turned-managers-and-more/ar-BBpc7Nl',
        'info_dict': {
            'id': 'BBpc7Nl',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'http://www.msn.com/en-ae/news/offbeat/meet-the-nine-year-old-self-made-millionaire/ar-BBt6ZKf',
        'only_matching': True,
    }, {
        'url': 'http://www.msn.com/en-ae/video/watch/obama-a-lot-of-people-will-be-disappointed/vi-AAhxUMH',
        'only_matching': True,
    }, {
        # geo restricted
        'url': 'http://www.msn.com/en-ae/foodanddrink/joinourtable/the-first-fart-makes-you-laugh-the-last-fart-makes-you-cry/vp-AAhzIBU',
        'only_matching': True,
    }, {
        'url': 'http://www.msn.com/en-ae/entertainment/bollywood/watch-how-salman-khan-reacted-when-asked-if-he-would-apologize-for-his-‘raped-woman’-comment/vi-AAhvzW6',
        'only_matching': True,
    }, {
        # Vidible(AOL) Embed
        'url': 'https://www.msn.com/en-us/money/other/jupiter-is-about-to-come-so-close-you-can-see-its-moons-with-binoculars/vi-AACqsHR',
        'only_matching': True,
    }, {
        # Dailymotion Embed
        'url': 'https://www.msn.com/es-ve/entretenimiento/watch/winston-salem-paire-refait-des-siennes-en-perdant-sa-raquette-au-service/vp-AAG704L',
        'only_matching': True,
    }, {
        # YouTube Embed
        'url': 'https://www.msn.com/en-in/money/news/meet-vikram-%E2%80%94-chandrayaan-2s-lander/vi-AAGUr0v',
        'only_matching': True,
    }, {
        # NBCSports Embed
        'url': 'https://www.msn.com/en-us/money/football_nfl/week-13-preview-redskins-vs-panthers/vi-BBXsCDb',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id, page_id = self._match_valid_url(url).groups()

        webpage = self._download_webpage(url, display_id)

        entries = []
        for _, metadata in re.findall(r'data-metadata\s*=\s*(["\'])(?P<data>.+?)\1', webpage):
            video = self._parse_json(unescapeHTML(metadata), display_id)

            provider_id = video.get('providerId')
            player_name = video.get('playerName')
            if player_name and provider_id:
                entry = None
                if player_name == 'AOL':
                    if provider_id.startswith('http'):
                        provider_id = self._search_regex(
                            r'https?://delivery\.vidible\.tv/video/redirect/([0-9a-f]{24})',
                            provider_id, 'vidible id')
                    entry = self.url_result(
                        'aol-video:' + provider_id, 'Aol', provider_id)
                elif player_name == 'Dailymotion':
                    entry = self.url_result(
                        'https://www.dailymotion.com/video/' + provider_id,
                        'Dailymotion', provider_id)
                elif player_name == 'YouTube':
                    entry = self.url_result(
                        provider_id, 'Youtube', provider_id)
                elif player_name == 'NBCSports':
                    entry = self.url_result(
                        'http://vplayer.nbcsports.com/p/BxmELC/nbcsports_embed/select/media/' + provider_id,
                        'NBCSportsVPlayer', provider_id)
                if entry:
                    entries.append(entry)
                    continue

            video_id = video['uuid']
            title = video['title']

            formats = []
            for file_ in video.get('videoFiles', []):
                format_url = file_.get('url')
                if not format_url:
                    continue
                if 'format=m3u8-aapl' in format_url:
                    # m3u8_native should not be used here until
                    # https://github.com/ytdl-org/youtube-dl/issues/9913 is fixed
                    formats.extend(self._extract_m3u8_formats(
                        format_url, display_id, 'mp4',
                        m3u8_id='hls', fatal=False))
                elif 'format=mpd-time-csf' in format_url:
                    formats.extend(self._extract_mpd_formats(
                        format_url, display_id, 'dash', fatal=False))
                elif '.ism' in format_url:
                    if format_url.endswith('.ism'):
                        format_url += '/manifest'
                    formats.extend(self._extract_ism_formats(
                        format_url, display_id, 'mss', fatal=False))
                else:
                    format_id = file_.get('formatCode')
                    formats.append({
                        'url': format_url,
                        'ext': 'mp4',
                        'format_id': format_id,
                        'width': int_or_none(file_.get('width')),
                        'height': int_or_none(file_.get('height')),
                        'vbr': int_or_none(self._search_regex(r'_(\d+)\.mp4', format_url, 'vbr', default=None)),
                        'quality': 1 if format_id == '1001' else None,
                    })

            subtitles = {}
            for file_ in video.get('files', []):
                format_url = file_.get('url')
                format_code = file_.get('formatCode')
                if not format_url or not format_code:
                    continue
                if compat_str(format_code) == '3100':
                    subtitles.setdefault(file_.get('culture', 'en'), []).append({
                        'ext': determine_ext(format_url, 'ttml'),
                        'url': format_url,
                    })

            entries.append({
                'id': video_id,
                'display_id': display_id,
                'title': title,
                'description': video.get('description'),
                'thumbnail': video.get('headlineImage', {}).get('url'),
                'duration': int_or_none(video.get('durationSecs')),
                'uploader': video.get('sourceFriendly'),
                'uploader_id': video.get('providerId'),
                'creator': video.get('creator'),
                'subtitles': subtitles,
                'formats': formats,
            })

        if not entries:
            error = unescapeHTML(self._search_regex(
                r'data-error=(["\'])(?P<error>.+?)\1',
                webpage, 'error', group='error'))
            raise ExtractorError('%s said: %s' % (self.IE_NAME, error), expected=True)

        return self.playlist_result(entries, page_id)
