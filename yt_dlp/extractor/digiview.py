import urllib.parse

from yt_dlp.utils import int_or_none

from ..networking import Request

from .youtube import YoutubeIE


class DigiviewIE(YoutubeIE):
    IE_DESC = 'Digiview'
    IE_NAME = 'digiview'
    _VALID_URL = r'https?://(?:www\.)?ladigitale\.dev/digiview/#/v/(?P<id>[0-9a-f]+)'
    _TESTS = [
        {
            # normal video
            'url': 'https://ladigitale.dev/digiview/#/v/663e17b35e979',
            'md5': 'acdf2c99c1e4d67664c9fbc5695986a9',
            'info_dict': {
                'id': 'BaW_jenozKc',
                'ext': 'mp4',
                'title': 'youtube-dl test video "\'/\\ä↭𝕐',
                'channel': 'Philipp Hagemeister',
                'channel_id': 'UCLqxVugv74EIW3VWh2NOa3Q',
                'channel_url': r're:https?://(?:www\.)?youtube\.com/channel/UCLqxVugv74EIW3VWh2NOa3Q',
                'upload_date': '20121002',
                'description': 'md5:8fb536f4877b8a7455c2ec23794dbc22',
                'categories': ['Science & Technology'],
                'tags': ['youtube-dl'],
                'duration': 10,
                'view_count': int,
                'like_count': int,
                'availability': 'public',
                'playable_in_embed': True,
                'thumbnail': 'https://i.ytimg.com/vi/BaW_jenozKc/maxresdefault.jpg',
                'live_status': 'not_live',
                'age_limit': 0,
                'comment_count': int,
                'channel_follower_count': int,
                'uploader': 'Philipp Hagemeister',
                'uploader_url': 'https://www.youtube.com/@PhilippHagemeister',
                'uploader_id': '@PhilippHagemeister',
                'heatmap': 'count:100',
            }
        },
        {
            # cut video
            'url': 'https://ladigitale.dev/digiview/#/v/663e17f2f3f18',
            'md5': 'acdf2c99c1e4d67664c9fbc5695986a9',
            'info_dict': {
                'id': 'BaW_jenozKc',
                'ext': 'mp4',
                'title': 'youtube-dl test video "\'/\\ä↭𝕐',
                'channel': 'Philipp Hagemeister',
                'channel_id': 'UCLqxVugv74EIW3VWh2NOa3Q',
                'channel_url': r're:https?://(?:www\.)?youtube\.com/channel/UCLqxVugv74EIW3VWh2NOa3Q',
                'upload_date': '20121002',
                'description': 'md5:8fb536f4877b8a7455c2ec23794dbc22',
                'categories': ['Science & Technology'],
                'tags': ['youtube-dl'],
                'duration': 3,
                'view_count': int,
                'like_count': int,
                'availability': 'public',
                'playable_in_embed': True,
                'thumbnail': 'https://i.ytimg.com/vi/BaW_jenozKc/maxresdefault.jpg',
                'live_status': 'not_live',
                'age_limit': 0,
                'comment_count': int,
                'channel_follower_count': int,
                'uploader': 'Philipp Hagemeister',
                'uploader_url': 'https://www.youtube.com/@PhilippHagemeister',
                'uploader_id': '@PhilippHagemeister',
                'heatmap': 'count:100',
            }
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage_data = self._download_json(
            Request(
                'https://ladigitale.dev/digiview/inc/recuperer_video.php',
                data=urllib.parse.urlencode({'id': video_id}).encode(),
                method='POST',
            ),
            video_id,
        )

        youtube_ie = YoutubeIE()
        youtube_ie.set_downloader(self._downloader)
        info = youtube_ie._real_extract(webpage_data['videoId'])

        # replace the YouTube metadata by the Digiview one
        info['title'] = webpage_data.get('titre') or info['title']
        info['description'] = webpage_data.get('description') or info['description']

        ffmpeg_args = []

        start_time = int_or_none(webpage_data.get('debut'))
        if start_time is not None and start_time != 0:
            ffmpeg_args.extend(['-ss', str(start_time)])

        end_time = int_or_none(webpage_data.get('fin'))
        if end_time is not None and end_time != info['duration']:
            ffmpeg_args.extend(['-t', str(end_time - (start_time or 0))])

        if ffmpeg_args and self._downloader:
            # cut the video if specified in the Digiview webpage
            ppargs = self._downloader.params.get("postprocessor_args")
            ppargs.setdefault("merger", []).extend(ffmpeg_args)

        return info
