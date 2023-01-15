import time
import datetime

from .common import InfoExtractor

class SportDeutschlandIE(InfoExtractor):
    _VALID_URL = r'https?://sportdeutschland\.tv/(?P<id>(?:[^/]+/)?[^?#/&]+)'
    _TESTS = [{
        'url': 'https://sportdeutschland.tv/badminton/re-live-deutsche-meisterschaften-2020-halbfinals?playlistId=0',
        'info_dict': {
            'id': '5318cac0275701382770543d7edaf0a0',
            'ext': 'mp4',
            'title': 'Re-live: Deutsche Meisterschaften 2020 - Halbfinals - Teil 1',
            'duration': 16106.36,
        },
        'params': {
            'noplaylist': True,
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://sportdeutschland.tv/badminton/re-live-deutsche-meisterschaften-2020-halbfinals?playlistId=0',
        'info_dict': {
            'id': 'c6e2fdd01f63013854c47054d2ab776f',
            'title': 'Re-live: Deutsche Meisterschaften 2020 - Halbfinals',
            'description': 'md5:5263ff4c31c04bb780c9f91130b48530',
            'duration': 31397,
        },
        'playlist_count': 2,
    }, {
        'url': 'https://sportdeutschland.tv/freeride-world-tour-2021-fieberbrunn-oesterreich',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        meta = self._download_json(
            'https://api.sportdeutschland.tv/api/stateless/frontend/assets/' + display_id,
            display_id, query={'access_token': 'true'})

        asset_id = meta.get('id') or meta.get('uuid')
        profile = meta.get('profile')

        info = {
            'id': asset_id,
            'title': (meta.get('title') or meta.get('name')).strip(),
            'description': meta.get('description'),
            'channel': profile.get('name'),
            'channel_id': profile.get('id'),
            'channel_url': 'https://sportdeutschland.tv/' + profile.get('slug'),
            'is_live': meta.get('currently_live'),
            'was_live': meta.get('was_live')
        }

        videos = meta.get('videos') or []
        
        if len(videos) > 1:
            info.update({
                '_type': 'multi_video',
                'entries': self.processVideoOrStream(asset_id, video)
            } for video in enumerate(videos))

        elif len(videos) == 1:
            info.update(
                self.processVideoOrStream(asset_id, videos[0])
            )


        livestream = meta.get('livestream')

        if livestream is not None:
            info.update(
                self.processVideoOrStream(asset_id, livestream)
            )


        return info


    def processVideoOrStream(self, asset_id, video):
        video_id = video.get('id')
        video_src = video.get('src')
        video_type = video.get('type')

        token_data = self._download_json(
            'https://api.sportdeutschland.tv/api/frontend/asset-token/' + asset_id
            + '?type=' + video_type
            + '&playback_id=' + video_src,
            video_id
            )

        m3u8_url = "https://stream.mux.com/" + video_src + '.m3u8?token=' + token_data.get('token')
        formats = self._extract_m3u8_formats(m3u8_url, video_id)

        videoData = {
            'display_id': video_id,
            'formats': formats,
        }
        if video_type == 'mux_vod':
            videoData.update({
                'duration': video.get('duration'),
                'timestamp': time.mktime(datetime.datetime.fromisoformat(video.get('created_at')).timetuple())
            })

        return videoData