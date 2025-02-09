from .adobepass import AdobePassIE
from ..networking import HEADRequest
from ..utils import (
    extract_attributes,
    float_or_none,
    get_element_html_by_class,
    int_or_none,
    merge_dicts,
    parse_age_limit,
    remove_end,
    str_or_none,
    traverse_obj,
    unescapeHTML,
    unified_timestamp,
    update_url_query,
    url_or_none,
)


class BravoTVIE(AdobePassIE):
    _VALID_URL = r'https?://(?:www\.)?(?P<site>bravotv|oxygen)\.com/(?:[^/]+/)+(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.bravotv.com/top-chef/season-16/episode-15/videos/the-top-chef-season-16-winner-is',
        'info_dict': {
            'id': '3923059',
            'ext': 'mp4',
            'title': 'The Top Chef Season 16 Winner Is...',
            'description': 'Find out who takes the title of Top Chef!',
            'upload_date': '20190314',
            'timestamp': 1552591860,
            'season_number': 16,
            'episode_number': 15,
            'series': 'Top Chef',
            'episode': 'The Top Chef Season 16 Winner Is...',
            'duration': 190.357,
            'season': 'Season 16',
            'thumbnail': r're:^https://.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.bravotv.com/top-chef/season-20/episode-1/london-calling',
        'info_dict': {
            'id': '9000234570',
            'ext': 'mp4',
            'title': 'London Calling',
            'description': 'md5:5af95a8cbac1856bd10e7562f86bb759',
            'upload_date': '20230310',
            'timestamp': 1678410000,
            'season_number': 20,
            'episode_number': 1,
            'series': 'Top Chef',
            'episode': 'London Calling',
            'duration': 3266.03,
            'season': 'Season 20',
            'chapters': 'count:7',
            'thumbnail': r're:^https://.+\.jpg',
            'age_limit': 14,
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'This video requires AdobePass MSO credentials',
    }, {
        'url': 'https://www.oxygen.com/in-ice-cold-blood/season-1/closing-night',
        'info_dict': {
            'id': '3692045',
            'ext': 'mp4',
            'title': 'Closing Night',
            'description': 'md5:3170065c5c2f19548d72a4cbc254af63',
            'upload_date': '20180401',
            'timestamp': 1522623600,
            'season_number': 1,
            'episode_number': 1,
            'series': 'In Ice Cold Blood',
            'episode': 'Closing Night',
            'duration': 2629.051,
            'season': 'Season 1',
            'chapters': 'count:6',
            'thumbnail': r're:^https://.+\.jpg',
            'age_limit': 14,
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'This video requires AdobePass MSO credentials',
    }, {
        'url': 'https://www.oxygen.com/in-ice-cold-blood/season-2/episode-16/videos/handling-the-horwitz-house-after-the-murder-season-2',
        'info_dict': {
            'id': '3974019',
            'ext': 'mp4',
            'title': '\'Handling The Horwitz House After The Murder (Season 2, Episode 16)',
            'description': 'md5:f9d638dd6946a1c1c0533a9c6100eae5',
            'upload_date': '20190617',
            'timestamp': 1560790800,
            'season_number': 2,
            'episode_number': 16,
            'series': 'In Ice Cold Blood',
            'episode': '\'Handling The Horwitz House After The Murder (Season 2, Episode 16)',
            'duration': 68.235,
            'season': 'Season 2',
            'thumbnail': r're:^https://.+\.jpg',
            'age_limit': 14,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.bravotv.com/below-deck/season-3/ep-14-reunion-part-1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        site, display_id = self._match_valid_url(url).group('site', 'id')
        webpage = self._download_webpage(url, display_id)
        settings = self._search_json(
            r'<script[^>]+data-drupal-selector="drupal-settings-json"[^>]*>', webpage, 'settings', display_id)
        tve = extract_attributes(get_element_html_by_class('tve-video-deck-app', webpage) or '')
        query = {
            'manifest': 'm3u',
            'formats': 'm3u,mpeg4',
        }

        if tve:
            account_pid = tve.get('data-mpx-media-account-pid') or 'HNK2IC'
            account_id = tve['data-mpx-media-account-id']
            metadata = self._parse_json(
                tve.get('data-normalized-video', ''), display_id, fatal=False, transform_source=unescapeHTML)
            video_id = tve.get('data-guid') or metadata['guid']
            if tve.get('data-entitlement') == 'auth':
                auth = traverse_obj(settings, ('tve_adobe_auth', {dict})) or {}
                site = remove_end(site, 'tv')
                release_pid = tve['data-release-pid']
                resource = self._get_mvpd_resource(
                    tve.get('data-adobe-pass-resource-id') or auth.get('adobePassResourceId') or site,
                    tve['data-title'], release_pid, tve.get('data-rating'))
                query.update({
                    'switch': 'HLSServiceSecure',
                    'auth': self._extract_mvpd_auth(
                        url, release_pid, auth.get('adobePassRequestorId') or site, resource),
                })

        else:
            ls_playlist = traverse_obj(settings, ('ls_playlist', ..., {dict}), get_all=False) or {}
            account_pid = ls_playlist.get('mpxMediaAccountPid') or 'PHSl-B'
            account_id = ls_playlist['mpxMediaAccountId']
            video_id = ls_playlist['defaultGuid']
            metadata = traverse_obj(
                ls_playlist, ('videos', lambda _, v: v['guid'] == video_id, {dict}), get_all=False)

        tp_url = f'https://link.theplatform.com/s/{account_pid}/media/guid/{account_id}/{video_id}'
        tp_metadata = self._download_json(
            update_url_query(tp_url, {'format': 'preview'}), video_id, fatal=False)

        chapters = traverse_obj(tp_metadata, ('chapters', ..., {
            'start_time': ('startTime', {float_or_none(scale=1000)}),
            'end_time': ('endTime', {float_or_none(scale=1000)}),
        }))
        # prune pointless single chapters that span the entire duration from short videos
        if len(chapters) == 1 and not traverse_obj(chapters, (0, 'end_time')):
            chapters = None

        m3u8_url = self._request_webpage(HEADRequest(
            update_url_query(f'{tp_url}/stream.m3u8', query)), video_id, 'Checking m3u8 URL').url
        if 'mpeg_cenc' in m3u8_url:
            self.report_drm(video_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'chapters': chapters,
            **merge_dicts(traverse_obj(tp_metadata, {
                'title': 'title',
                'description': 'description',
                'duration': ('duration', {float_or_none(scale=1000)}),
                'timestamp': ('pubDate', {float_or_none(scale=1000)}),
                'season_number': (('pl1$seasonNumber', 'nbcu$seasonNumber'), {int_or_none}),
                'episode_number': (('pl1$episodeNumber', 'nbcu$episodeNumber'), {int_or_none}),
                'series': (('pl1$show', 'nbcu$show'), (None, ...), {str}),
                'episode': (('title', 'pl1$episodeNumber', 'nbcu$episodeNumber'), {str_or_none}),
                'age_limit': ('ratings', ..., 'rating', {parse_age_limit}),
            }, get_all=False), traverse_obj(metadata, {
                'title': 'title',
                'description': 'description',
                'duration': ('durationInSeconds', {int_or_none}),
                'timestamp': ('airDate', {unified_timestamp}),
                'thumbnail': ('thumbnailUrl', {url_or_none}),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'episode': 'episodeTitle',
                'series': 'show',
            })),
        }
