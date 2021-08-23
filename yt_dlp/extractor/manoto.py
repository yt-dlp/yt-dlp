# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor, traverse_obj, clean_html


_API_URL = 'https://dak1vd5vmi7x6.cloudfront.net/api/v1/publicrole/{}/{}?id={}'
EXT = 'mp4'

class ManotoTVIE(InfoExtractor):
    IE_NAME = 'Manoto TV (Episode)'
    _VALID_URL = r'https?://(?:www\.)?manototv\.com/episode/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.manototv.com/episode/12576',
        'info_dict': {
            'id': '12576',
            'series': 'فیلم های ایرانی',
            'season_number': 0,
            'episode_number': 0,
            'episode_id': 'Seh Mah Taatili',
            'duration': 5400,
            'view_count': 10550,
            'categories': ['سرگرمی'],
            'title': 'سه ماه تعطیلی',
            'description': 'سه ماه تعطیلی فیلمی به کارگردانی و نویسندگی شاپور قریب ساختهٔ سال ۱۳۵۶ است.',
            'thumbnail': r're:^https?://.*\.jpeg$',
            'ext': EXT
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        episode_json = self._download_json(_API_URL.format('showmodule', 'episodedetails', video_id), video_id)
        details = episode_json.get('details', {})
        season_number = details.get('analyticsSeasonNumber')
        if not(season_number.isdigit()):
            season_number = 0
        episode_number = details.get('episodeNumber')
        if not(episode_number.isdigit()):
            episode_number = 0
        formats = self._extract_m3u8_formats(details.get('videoM3u8Url'), video_id, EXT)
        return {
            'id': video_id,
            'series': details.get('showTitle'),
            'season_number': int(season_number),
            'episode_number': int(episode_number),
            'episode_id': details.get('analyticsEpisodeTitle'),
            'duration': details.get('durationInMinutes') * 60,
            'view_count': details.get('viewCount'),
            'categories': [details.get('videoCategory')],
            'title': details.get('episodeTitle'),
            'description': clean_html(details.get('episodeDescription')),
            'thumbnail': details.get('episodelandscapeImgIxUrl'),
            'ext': EXT,
            'formats': formats,
        }


class ManotoTVShowIE(InfoExtractor):
    IE_NAME = 'Manoto TV (Show)'
    _VALID_URL = r'https?://(?:www\.)?manototv\.com/show/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.manototv.com/show/2526',
        'playlist_mincount': 68,
        'info_dict': {
            'id': '2526',
            'title': 'فیلم های ایرانی',
            'description': 'مجموعه ای از فیلم های سینمای کلاسیک ایران',
        },
    }]

    def _real_extract(self, url):
        show_id = self._match_id(url)
        show_json = self._download_json(_API_URL.format('showmodule', 'details', show_id), show_id)
        show_details = show_json.get('details', {})
        title = show_details.get('showTitle')
        description = show_details.get('showSynopsis')

        series_json = self._download_json(_API_URL.format('showmodule', 'serieslist', show_id), show_id)
        playlist_id = str(traverse_obj(series_json, ('details', 'list', 0, 'id')))

        playlist_json = self._download_json(_API_URL.format('showmodule', 'episodelist', playlist_id), playlist_id)
        playlist = traverse_obj(playlist_json, ('details', 'list')) or []

        entries = [
            self.url_result(
                'https://www.manototv.com/episode/%s' % item['slideID'], ie=ManotoTVIE.ie_key(), video_id=item['slideID'])
            for item in playlist]
        return self.playlist_result(entries, show_id, title, description)


class ManotoTVLiveIE(InfoExtractor):
    IE_NAME = 'Manoto TV (Live)'
    _VALID_URL = r'https?://(?:www\.)?manototv\.com/live/'
    _TEST = {
        'url': 'https://www.manototv.com/live/',
        'info_dict': {
            'id': 'live',
            'title': 'Manoto TV Live',
            'ext': EXT,
            'is_live': True,
        }
    }

    def _real_extract(self, url):
        video_id = 'live'
        json = self._download_json(_API_URL.format('livemodule', 'details', ''), video_id)
        details = json.get('details', {})
        video_url = details.get('liveUrl')
        formats = self._extract_m3u8_formats(video_url, video_id, EXT, live=True)
        return {
            'id': video_id,
            'title': 'Manoto TV Live',
            'ext': EXT,
            'formats': formats,
        }
