import json

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, traverse_obj, try_get


class AmazonMiniTVBaseIE(InfoExtractor):
    def _get_nextjs_data(self, asin, webpage=None, note=None):
        resp = self._search_nextjs_data(webpage, asin, fatal=False) or {}

        if not resp:
            raise ExtractorError(f'Unable to {note or "NextJS data"}', expected=True)
        else:
            return resp


class AmazonMiniTVIE(AmazonMiniTVBaseIE):
    _VALID_URL = r'(?:https?://(?:www\.)?amazon\.in/minitv/tp/|amazonminitv:(?:amzn1\.dv\.gti\.)?)(?P<id>[a-f0-9-]+)'
    _TESTS = [{
        'url': 'https://www.amazon.in/minitv/tp/75fe3a75-b8fe-4499-8100-5c9424344840?referrer=https%3A%2F%2Fwww.amazon.in%2Fminitv',
        'info_dict': {
            'id': 'amzn1.dv.gti.75fe3a75-b8fe-4499-8100-5c9424344840',
            'ext': 'mp4',
            'title': 'May I Kiss You?',
            'language': 'Hindi',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:a549bfc747973e04feb707833474e59d',
            'release_timestamp': 1644710400,
            'release_date': '20220213',
            'duration': 846,
            'chapters': 'count:2',
            'series': 'Couple Goals',
            'series_id': 'amzn1.dv.gti.56521d46-b040-4fd5-872e-3e70476a04b0',
            'season': 'Season 3',
            'season_number': 3,
            'season_id': 'amzn1.dv.gti.20331016-d9b9-4968-b991-c89fa4927a36',
            'episode': 'May I Kiss You?',
            'episode_number': 2,
            'episode_id': 'amzn1.dv.gti.75fe3a75-b8fe-4499-8100-5c9424344840',
        },
    }, {
        'url': 'https://www.amazon.in/minitv/tp/280d2564-584f-452f-9c98-7baf906e01ab?referrer=https%3A%2F%2Fwww.amazon.in%2Fminitv',
        'info_dict': {
            'id': 'amzn1.dv.gti.280d2564-584f-452f-9c98-7baf906e01ab',
            'ext': 'mp4',
            'title': 'Jahaan',
            'language': 'Hindi',
            'thumbnail': r're:^https?://.*\.jpg',
            'description': 'md5:05eb765a77bf703f322f120ec6867339',
            'release_timestamp': 1647475200,
            'release_date': '20220317',
            'duration': 783,
            'chapters': [],
        },
    }, {
        'url': 'https://www.amazon.in/minitv/tp/280d2564-584f-452f-9c98-7baf906e01ab',
        'only_matching': True,
    }, {
        'url': 'amazonminitv:amzn1.dv.gti.280d2564-584f-452f-9c98-7baf906e01ab',
        'only_matching': True,
    }, {
        'url': 'amazonminitv:280d2564-584f-452f-9c98-7baf906e01ab',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        asin = f'amzn1.dv.gti.{self._match_id(url)}'
        webpage = self._download_webpage(url, asin)
        prs = self._get_nextjs_data(asin, note='Retrieve playback info', webpage=webpage)

        formats, subtitles = [], {}
        for type_, asset in prs['props']['pageProps']['ssrProps']['playbackData']['playbackAssets'].items():
            if not traverse_obj(asset, 'manifestUrl'):
                continue
            if type_ == 'hls':
                m3u8_fmts, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    asset['manifestUrl'], asin, ext='mp4', entry_protocol='m3u8_native',
                    m3u8_id=type_, fatal=False)
                formats.extend(m3u8_fmts)
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            elif type_ == 'dash':
                mpd_fmts, mpd_subs = self._extract_mpd_formats_and_subtitles(
                    asset['manifestUrl'], asin, mpd_id=type_, fatal=False)
                formats.extend(mpd_fmts)
                subtitles = self._merge_subtitles(subtitles, mpd_subs)
            else:
                self.report_warning(f'Unknown asset type: {type_}')

        title_info = prs['props']['pageProps']['ssrProps']['contentData']
        credits_time = try_get(title_info, lambda x: x['timecode']['endCreditsTime'] / 1000)
        is_episode = title_info.get('vodType') == 'EPISODE'

        return {
            'id': asin,
            'title': title_info.get('name'),
            'formats': formats,
            'subtitles': subtitles,
            'language': traverse_obj(title_info, ('audioTracks', 0)),
            'thumbnails': [{
                'id': type_,
                'url': url,
            } for type_, url in (title_info.get('images') or {}).items()],
            'description': traverse_obj(title_info, ('description', 'synopsis')),
            'release_timestamp': int_or_none(try_get(title_info, lambda x: x['publicReleaseDateUTC'] / 1000)),
            'duration': traverse_obj(title_info, ('description', 'contentLengthInSeconds')),
            'chapters': [{
                'start_time': credits_time,
                'title': 'End Credits',
            }] if credits_time else [],
            'series': title_info.get('seriesName'),
            'series_id': title_info.get('seriesId'),
            'season_number': title_info.get('seasonNumber'),
            'season_id': title_info.get('seasonId'),
            'episode': title_info.get('name') if is_episode else None,
            'episode_number': title_info.get('episodeNumber'),
            'episode_id': asin if is_episode else None,
        }
