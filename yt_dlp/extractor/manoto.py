from .common import InfoExtractor
from ..utils import clean_html, int_or_none, traverse_obj

_API_URL = 'https://dak1vd5vmi7x6.cloudfront.net/api/v1/publicrole/{}/{}?id={}'


class ManotoTVIE(InfoExtractor):
    IE_DESC = 'Manoto TV (Episode)'
    _VALID_URL = r'https?://(?:www\.)?manototv\.com/episode/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.manototv.com/episode/8475',
        'info_dict': {
            'id': '8475',
            'series': 'خانه های رویایی با برادران اسکات',
            'season_number': 7,
            'episode_number': 25,
            'episode_id': 'My Dream Home S7: Carol & John',
            'duration': 3600,
            'categories': ['سرگرمی'],
            'title': 'کارول و جان',
            'description': 'md5:d0fff1f8ba5c6775d312a00165d1a97e',
            'thumbnail': r're:^https?://.*\.(jpeg|png|jpg)$',
            'ext': 'mp4'
        },
        'params': {
            'skip_download': 'm3u8',
        }
    }, {
        'url': 'https://www.manototv.com/episode/12576',
        'info_dict': {
            'id': '12576',
            'series': 'فیلم های ایرانی',
            'episode_id': 'Seh Mah Taatili',
            'duration': 5400,
            'view_count': int,
            'categories': ['سرگرمی'],
            'title': 'سه ماه تعطیلی',
            'description': 'سه ماه تعطیلی فیلمی به کارگردانی و نویسندگی شاپور قریب ساختهٔ سال ۱۳۵۶ است.',
            'thumbnail': r're:^https?://.*\.(jpeg|png|jpg)$',
            'ext': 'mp4'
        },
        'params': {
            'skip_download': 'm3u8',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        episode_json = self._download_json(_API_URL.format('showmodule', 'episodedetails', video_id), video_id)
        details = episode_json.get('details', {})
        formats = self._extract_m3u8_formats(details.get('videoM3u8Url'), video_id, 'mp4')
        return {
            'id': video_id,
            'series': details.get('showTitle'),
            'season_number': int_or_none(details.get('analyticsSeasonNumber')),
            'episode_number': int_or_none(details.get('episodeNumber')),
            'episode_id': details.get('analyticsEpisodeTitle'),
            'duration': int_or_none(details.get('durationInMinutes'), invscale=60),
            'view_count': details.get('viewCount'),
            'categories': [details.get('videoCategory')],
            'title': details.get('episodeTitle'),
            'description': clean_html(details.get('episodeDescription')),
            'thumbnail': details.get('episodelandscapeImgIxUrl'),
            'formats': formats,
        }


class ManotoTVShowIE(InfoExtractor):
    IE_DESC = 'Manoto TV (Show)'
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
    IE_DESC = 'Manoto TV (Live)'
    _VALID_URL = r'https?://(?:www\.)?manototv\.com/live/'
    _TEST = {
        'url': 'https://www.manototv.com/live/',
        'info_dict': {
            'id': 'live',
            'title': 'Manoto TV Live',
            'ext': 'mp4',
            'is_live': True,
        },
        'params': {
            'skip_download': 'm3u8',
        }
    }

    def _real_extract(self, url):
        video_id = 'live'
        json = self._download_json(_API_URL.format('livemodule', 'details', ''), video_id)
        details = json.get('details', {})
        video_url = details.get('liveUrl')
        formats = self._extract_m3u8_formats(video_url, video_id, 'mp4', live=True)
        return {
            'id': video_id,
            'title': 'Manoto TV Live',
            'is_live': True,
            'formats': formats,
        }
