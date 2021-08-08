from __future__ import unicode_literals

from .common import InfoExtractor
from .cbs import CBSBaseIE
from ..utils import (
    ExtractorError,
    int_or_none,
    update_url_query,
)


class ParamountPlusIE(CBSBaseIE):
    _VALID_URL = r'''(?x)
        (?:
            paramountplus:|
            https?://(?:www\.)?(?:
                paramountplus\.com/(?:shows/[^/]+/video|movies/[^/]+)/
        )(?P<id>[\w-]+))'''

    _TESTS = [{
        'url': 'https://www.paramountplus.com/shows/catdog/video/Oe44g5_NrlgiZE3aQVONleD6vXc8kP0k/catdog-climb-every-catdog-the-canine-mutiny/',
        'info_dict': {
            'id': 'Oe44g5_NrlgiZE3aQVONleD6vXc8kP0k',
            'ext': 'mp4',
            'title': 'CatDog - Climb Every CatDog/The Canine Mutiny',
            'description': 'md5:7ac835000645a69933df226940e3c859',
            'duration': 1418,
            'timestamp': 920264400,
            'upload_date': '19990301',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        '_skip': 'Blocked outside the US',
    }, {
        'url': 'https://www.paramountplus.com/shows/tooning-out-the-news/video/6hSWYWRrR9EUTz7IEe5fJKBhYvSUfexd/7-23-21-week-in-review-rep-jahana-hayes-howard-fineman-sen-michael-bennet-sheera-frenkel-cecilia-kang-/',
        'info_dict': {
            'id': '6hSWYWRrR9EUTz7IEe5fJKBhYvSUfexd',
            'ext': 'mp4',
            'title': '7/23/21 WEEK IN REVIEW (Rep. Jahana Hayes/Howard Fineman/Sen. Michael Bennet/Sheera Frenkel & Cecilia Kang)',
            'description': 'md5:f4adcea3e8b106192022e121f1565bae',
            'duration': 2506,
            'timestamp': 1627063200,
            'upload_date': '20210723',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            'skip_download': 'm3u8',
        },
        '_skip': 'Blocked outside the US',
    }, {
        'url': 'https://www.paramountplus.com/shows/all-rise/video/QmR1WhNkh1a_IrdHZrbcRklm176X_rVc/all-rise-space/',
        'only_matching': True,
    }, {
        'url': 'https://www.paramountplus.com/movies/million-dollar-american-princesses-meghan-and-harry/C0LpgNwXYeB8txxycdWdR9TjxpJOsdCq',
        'only_matching': True,
    }]

    def _extract_video_info(self, content_id, site='cbs', mpx_acc=2198311517):
        items_data = self._download_json(
            'https://www.paramountplus.com/apps-api/v2.0/androidtv/video/cid/%s.json' % content_id,
            content_id, query={'locale': 'en-us', 'at': 'ABCqWNNSwhIqINWIIAG+DFzcFUvF8/vcN6cNyXFFfNzWAIvXuoVgX+fK4naOC7V8MLI='})
        tp_path = 'dJ5BDC/media/guid/%d/%s' % (mpx_acc, content_id)
        tp_release_url = 'https://link.theplatform.com/s/' + tp_path

        asset_types = []
        subtitles = {}
        formats = []
        last_e = None
        for item in items_data['itemList']:
            asset_type = item['assetType']
            query = {
                'format': 'SMIL',
            }
            if asset_type in asset_types:
                continue
            asset_types.append(asset_type)
            query['formats'] = 'MPEG4,M3U'
            try:
                tp_formats, tp_subtitles = self._extract_theplatform_smil(
                    update_url_query(tp_release_url, query), content_id,
                    'Downloading %s SMIL data' % asset_type)
            except ExtractorError as e:
                last_e = e
                query['formats'] = ''  # blank query to check if expired
                try:
                    tp_formats, tp_subtitles = self._extract_theplatform_smil(
                        update_url_query(tp_release_url, query), content_id,
                        'Downloading %s SMIL data, trying again with another format' % asset_type)
                except ExtractorError as e:
                    last_e = e
                    continue
            formats.extend(tp_formats)
            subtitles = self._merge_subtitles(subtitles, tp_subtitles)
        if last_e and not formats:
            self.raise_no_formats(last_e, True, content_id)
        self._sort_formats(formats)

        info = self._extract_theplatform_metadata(tp_path, content_id)
        info.update({
            'formats': formats,
            'subtitles': subtitles,
            'id': content_id,
            'title': item.get('title'),
            'series': item.get('seriesTitle'),
            'season_number': int_or_none(item.get('seasonNum')),
            'episode_number': int_or_none(item.get('episodeNum')),
            'duration': int_or_none(item.get('duration'), 1000),
            'thumbnail': item.get('thumbnail')
        })
        return info

    def _real_extract(self, url):
        content_id = self._match_id(url)
        return self._extract_video_info(content_id)


class ParamountPlusSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?paramountplus\.com/shows/(?P<id>[a-zA-Z0-9-_]+)/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://www.paramountplus.com/shows/drake-josh',
        'playlist_mincount': 50,
        'info_dict': {
            'id': 'drake-josh',
        }
    }, {
        'url': 'https://www.paramountplus.com/shows/hawaii_five_0/',
        'playlist_mincount': 240,
        'info_dict': {
            'id': 'hawaii_five_0',
        }
    }, {
        'url': 'https://www.paramountplus.com/shows/spongebob-squarepants/',
        'playlist_mincount': 248,
        'info_dict': {
            'id': 'spongebob-squarepants',
        }
    }]
    _API_URL = 'https://www.paramountplus.com/shows/{}/xhr/episodes/page/0/size/100000/xs/0/season/0/'

    def _entries(self, show_name):
        show_json = self._download_json(self._API_URL.format(show_name), video_id=show_name)
        if show_json.get('success'):
            for episode in show_json['result']['data']:
                yield self.url_result(
                    'https://www.paramountplus.com%s' % episode['url'],
                    ie=ParamountPlusIE.ie_key(), video_id=episode['content_id'])

    def _real_extract(self, url):
        show_name = self._match_id(url)
        return self.playlist_result(self._entries(show_name), playlist_id=show_name)
