from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    float_or_none,
    parse_duration,
    parse_iso8601,
    traverse_obj,
    unified_strdate,
    url_or_none
)


class News9IE(InfoExtractor):
    IE_NAME = '9News'
    _VALID_URL = r'https?://(?:www\.)?9news\.com\.au/\w+/(?:\w+/)?[^/]+/(?P<id>[^/]+)(?:$|[?#])'
    _TESTS = [{
        'url': 'https://www.9news.com.au/videos/national/fair-trading-pulls-dozens-of-toys-from-shelves/clqgc7dvj000y0jnvfism0w5m',
        'md5': 'd1a65b2e9d126e5feb9bc5cb96e62c80',
        'info_dict': {
            'id': 'clqgc7dvj000y0jnvfism0w5m',
            'ext': 'mp4',
            'title': 'Fair Trading pulls dozens of toys from shelves',
            'description': 'Fair Trading Australia have been forced to pull dozens of toys from shelves over hazard fears.',
            'thumbnail': 'md5:f4dbfe2945d01cf74f904eeb7eb40134',
            'release_date': '20231222',
            'duration': 93440
        }
    }, {
        'url': 'https://www.9news.com.au/world/tape-reveals-donald-trump-pressured-michigan-officials-not-to-certify-2020-vote-a-new-report-says/0b8b880e-7d3c-41b9-b2bd-55bc7e492259',
        'md5': 'a885c44d20898c3e70e9a53e8188cea1',
        'info_dict': {
            'id': '0b8b880e-7d3c-41b9-b2bd-55bc7e492259',
            'ext': 'mp4',
            'title': 'Tape reveals Donald Trump pressured Michigan officials not to certify 2020 vote, a new report says',
            'description': 'md5:fdd68b89e8a123a2e5ddfd7c0ab6b4a2',
            'thumbnail': 'md5:d457173a58f733426c8e27af8908e638',
            'release_date': '20231220',
            'duration': 104640
        }
    }, {
        'url': 'https://www.9news.com.au/national/outrage-as-parents-banned-from-giving-gifts-to-kindergarten-teachers/e19b49d4-a1a4-4533-9089-6e10e2d9386a',
        'info_dict': {
            'id': 'e19b49d4-a1a4-4533-9089-6e10e2d9386a',
            'ext': 'mp4',
            'title': 'Outrage as parents banned from giving gifts to kindergarten teachers',
            'description': 'md5:459b3f1caa3dda8e9f0554d1101206ef',
            'thumbnail': 'md5:95477f729d5d09b200b1b9ea465b6c02',
            'release_date': '20231222',
            'duration': 91307
        },
        'params': {
            'skip_download': True,
        },
    }]
    # pk (`policyKey`) comes from `https://players.brightcove.net/<account>/<player>_default/index.min.js``. `account` and `player` are retrieved from __INITIAL_STATE__
    _HEADERS = {'Accept': 'application/json;pk=BCpkADawqM1kowc2o3hzDhqIzvTAu6i97c6mRogi_T5NtyFeWT8NpnBZuikPxRea6jkxKRCNN6CEQys5skhkRmnGR2WRrf0KHt6SArkG1zMIUuf8FSqxT9vGkvQ'}

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)
        initial_state = self._search_json(r'var\s__INITIAL_STATE__\s*=', webpage, 'initial state', article_id)

        info = traverse_obj(initial_state, {
            'video_id': ('videoIndex', 'currentVideo', 'brightcoveId'),
            'account': ('videoIndex', 'config', 'account'),
            'player': ('videoIndex', 'config', 'player'),
            'title': ('videoIndex', 'currentVideo', 'name'),
            'description': ('videoIndex', 'currentVideo', 'description'),
            'duration': ('videoIndex', 'currentVideo', 'duration', {parse_duration}),
        }) or traverse_obj(initial_state, {
            'video_id': ('article', ..., 'media', lambda _, v: v['type'] == 'video', 'urn'),
            'account': ('videoIndex', 'config', 'video', 'account'),
            'player': ('videoIndex', 'config', 'video,' 'player'),
            'title': ('article', ..., 'headline'),
            'description': ('article', ..., 'description', {clean_html}), }, get_all=False)

        if not info.get('video_id') or not info.get('account'):
            raise ExtractorError('Unable to get the required video data')

        video_id = info.get('video_id')

        video_json = self._download_json(
            f'https://edge.api.brightcove.com/playback/v1/accounts/{info.get('account')}/videos/{video_id}',
            article_id, headers=self._HEADERS, fatal=True)

        video_info = traverse_obj(video_json, {
            'sources': ('sources', ..., {'url': ('src', {url_or_none})}),
            'subtitles': ('text_tracks', ...),
            'thumbnails': ('thumbnail_sources', ..., {'url': ('src', {url_or_none})}),
            'created_at': ('created_at', {unified_strdate}),
            'duration': ('duration', {float_or_none}),
        })

        formats = []
        subs = []
        for source in video_info.get('sources'):
            url = source.get('url')
            if 'https' not in url:
                continue
            ext = determine_ext(url)
            if source.get('type') == 'application/x-mpegurl' or ext == 'm3u8':
                format, sub = self._extract_m3u8_formats_and_subtitles(
                    url, video_id, ext='mp4', entry_protocol='m3u8_native', m3u8_id='hls', fatal=False)
                formats.extend(format)
                subs.extend(sub)
            elif source.get('type') == 'application/dash+xml' or ext == 'mpd':
                format, sub = self._extract_mpd_formats_and_subtitles(
                    url, video_id, mpd_id='dash', fatal=False)
                formats.extend(format)
                subs.extend(sub)
            else:
                formats.append({'url': url, 'ext': ext, })

        return {
            'id': article_id,
            'title': info.get('title') or self._og_search_title(webpage),
            'description': info.get('description') or self._og_search_description(webpage),
            'duration': video_info.get('duration') or info.get('duration'),
            'thumbnails': video_info.get('thumbnails'),
            'release_date': video_info.get('created_at'),
            'timestamp': parse_iso8601(video_info.get('created_at')),
            'formats': formats,
            'subtitles': subs,
        }
