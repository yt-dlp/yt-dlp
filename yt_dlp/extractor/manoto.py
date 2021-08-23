# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class ManotoTVIE(InfoExtractor):
    IE_NAME = 'Manoto TV (Episode)'
    _VALID_URL = r'https?://(?:www\.)?manototv\.com/episode/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.manototv.com/episode/12576',
        'info_dict': {
            'id': '12576',
            'title': 'Seh Mah Taatili',
            'description': 'مجموعه ای از فیلم های سینمای کلاسیک ایران',
            'thumbnail': r're:^https?://.*\.jpeg$',
            'ext': 'm3u8',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        episode_json = self._download_json('https://dak1vd5vmi7x6.cloudfront.net/api/v1/publicrole/showmodule/episodedetails?id=' + video_id, video_id)
        details = episode_json.get('details', {})
        title = details.get('analyticsEpisodeTitle')
        video_url = details.get('videoM3u8Url')
        description = details.get('showSynopsis')
        thumbnail = details.get('episodelandscapeImgIxUrl')
        ext = 'm3u8'
        formats = self._extract_m3u8_formats(video_url, video_id, ext)
        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'ext': ext,
            'formats': formats,
        }


class ManotoTVShowIE(InfoExtractor):
    IE_NAME = 'Manoto TV (Show / Playlist)'
    _VALID_URL = r'https?://(?:www\.)?manototv\.com/show/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.manototv.com/show/2526',
        'playlist_mincount': 68,
        'info_dict': {
            'id': '2526',
            'title': 'فیلم های ایرانی',
            'description': 'مجموعه ای از فیلم های سینمای کلاسیک ایران',
            # 'thumbnail': r're:^https?://.*\.png$',
        },
    }]

    def _real_extract(self, url):
        show_id = self._match_id(url)
        show_json = self._download_json('https://dak1vd5vmi7x6.cloudfront.net/api/v1/publicrole/showmodule/details?id=' + show_id, show_id)
        show_details = show_json.get('details', {})
        title = show_details.get('showTitle')
        description = show_details.get('showSynopsis')
        # thumbnail = show_details.get('overlayImgIxUrl')

        series_json = self._download_json('https://dak1vd5vmi7x6.cloudfront.net/api/v1/publicrole/showmodule/serieslist?id=' + show_id, show_id)
        series_details = series_json.get('details', {})
        playlist_id = str(series_details.get('list', [])[0].get('id'))

        playlist_json = self._download_json('https://dak1vd5vmi7x6.cloudfront.net/api/v1/publicrole/showmodule/episodelist?id=' + playlist_id, playlist_id)
        playlist_details = playlist_json.get('details', {})
        playlist = playlist_details.get('list', [])

        entries = [
            self.url_result(
                'https://www.manototv.com/episode/%s' % item['slideID'], ie=ManotoTVIE.ie_key(), video_id=item['slideID'])
            for item in playlist]
        return self.playlist_result(entries, show_id, title, description)


class ManotoTVLiveIE(InfoExtractor):
    IE_NAME = 'Manoto TV Live'
    _VALID_URL = r'https?://(?:www\.)?manototv\.com/live/'
    _TEST = {
        'url': 'https://www.manototv.com/live/',
        'info_dict': {
            'id': 'live',
            'title': 'Manoto TV Live',
            'ext': 'm3u8',
        }
    }

    def _real_extract(self, url):
        video_id = 'live'
        json = self._download_json('https://dak1vd5vmi7x6.cloudfront.net/api/v1/publicrole/livemodule/details', video_id)
        details = json.get('details', {})
        video_url = details.get('liveUrl')
        ext = 'm3u8'
        formats = self._extract_m3u8_formats(video_url, video_id, ext)
        return {
            'id': video_id,
            'title': 'Manoto TV Live',
            'ext': ext,
            'formats': formats,
        }
