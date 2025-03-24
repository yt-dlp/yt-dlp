import datetime
import json
import re

from .common import InfoExtractor
from ..utils import ExtractorError, parse_iso8601

# NOTE: Private videos can be downloaded by adding --add-header "authorization: Bearer abcxyz",
# but won't work with --cookies-from-browser and --cookies file.txt


class VanilloIE(InfoExtractor):
    _VALID_URL = r'https?://(?:dev\.|beta\.)?vanillo\.tv/(?:v|embed)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://vanillo.tv/v/iaCi-oTmmGY',
        'info_dict': {
            'id': 'iaCi-oTmmGY',
            'title': 'Wawa',
            'description': '',
            'thumbnail': 'https://images.vanillo.tv/V6mYuajeHGsSSPRJKCdRAvvWgHFVGZ00g-ne3TZevss/h:300/aHR0cHM6Ly9pbWFnZXMuY2RuLnZhbmlsbG8udHYvdGh1bWJuYWlsL1RhUGE3TEJFTVBlS205elh2ZWdzLmF2aWY',
            'uploader_url': 'M7A',
            'upload_date': '20240309',  # YYYYMMDD format, server API provides 2024-03-09T07:56:35.636Z
            'duration': 5.71,
            'view_count': 205,
            'comment_count': 2,
            'like_count': 4,
            'dislike_count': 0,
            'average_rating': 4.2,
            'categories': ['film_and_animation'],
            'tags': ['Wawa', 'wawa', 'Wa Wa', 'wa wa', 'WaWa', 'wAwA', 'wA Wa'],
        },
    }, {
        'url': 'https://vanillo.tv/v/RhSueuQZiKF',
        'info_dict': {
            'id': 'RhSueuQZiKF',
            'title': 'What\'s New on Vanillo - Fall Update',
            'description': '',
            'thumbnail': 'https://images.vanillo.tv/7Qfelvn1-4waFjX3rIc1FkfpB9jOJqqLlvieD5i3mlA/h:300/aHR0cHM6Ly9pbWFnZXMuY2RuLnZhbmlsbG8udHYvdGh1bWJuYWlsL3JsMmR5ajJFcnozMEphSUd0bTZyLmF2aWY',
            'uploader_url': 'Vanillo',
            'upload_date': '20231020',  # YYYYMMDD format, server API provides 2023-10-20T04:53:13.718Z
            'duration': 99.35,
            'view_count': 368,
            'comment_count': 2,
            'like_count': 20,
            'dislike_count': 0,
            'average_rating': 4.2,
            'categories': ['film_and_animation'],
            'tags': ['fall', 'update', 'fall update', 'autumn', 'autumn update', 'vanillo', 'new features', 'new', 'features', 'exciting', 'language', 'switch', 'english', 'descriptive audio', 'descriptive', 'audio', 'qualities', 'higher', 'process', 'processing', 'faster', 'fast', '2x', '4x', 'twice', 'speed', 'speedy', 'quick', 'chapters'],
        },
        'playlist_mincount': 1,
    }]

    def _get_replies(self, comment_id, limit=3):
        replies = []
        replies_url = f'https://api.vanillo.tv/v1/comments/{comment_id}/replies?limit={limit}&reviewing=false'
        try:
            replies_data = self._download_json(
                replies_url, comment_id, note=f'Downloading replies for comment {comment_id}', fatal=False)
        except ExtractorError:
            return replies
        if replies_data.get('status') != 'success':
            return replies
        for reply in replies_data.get('data', {}).get('comments', []):
            transformed = {
                'id': reply.get('id'),
                'author': reply.get('profile', {}).get('username'),
                'author_id': reply.get('profile', {}).get('id'),
                'text': reply.get('text'),
                'timestamp': parse_iso8601(reply.get('createdAt')),
            }
            replies.append(transformed)
        return replies

    def _get_comments(self, video_id, limit=10):
        all_comments = []
        page_key = None
        # Loop to download all comments using pageKey
        while True:
            url = f'https://api.vanillo.tv/v1/videos/{video_id}/comments?limit={limit}&reviewing=false&filter=high_to_low_score'
            if page_key:
                url += f'&pageKey={page_key}'
            try:
                comments_data = self._download_json(url, video_id, note='Downloading comments', fatal=False)
            except ExtractorError:
                break
            if comments_data.get('status') != 'success':
                break
            data = comments_data.get('data', {})
            comments = data.get('comments', [])
            if not comments:
                break
            # For each comment, download replies (if any)
            for comment in comments:
                transformed = {
                    'id': comment.get('id'),
                    'author': comment.get('profile', {}).get('username'),
                    'author_id': comment.get('profile', {}).get('id'),
                    'text': comment.get('text'),
                    'timestamp': parse_iso8601(comment.get('createdAt')),
                    'replies': self._get_replies(comment.get('id')),
                }
                all_comments.append(transformed)
            page_key = data.get('nextPageKey')
            if not page_key:
                break
        return all_comments

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # 1) Retrieve video info (metadata)
        video_info_url = f'https://api.vanillo.tv/v1/videos/{video_id}?groups=uploader,profile.full'
        try:
            video_info = self._download_json(video_info_url, video_id, note='Downloading video info')
        except ExtractorError as e:
            # Try to get an HTTP code from the error cause or message
            http_code = getattr(e.cause, 'code', None)
            if http_code is None and 'HTTP Error 404' in str(e):
                http_code = 404
            if http_code == 404:
                self.raise_login_required(
                    '404: Could be a Private video. Authorization is required for this URL and can be passed with the --add-header "authorization: Bearer abcxyz" option. '
                    'The --cookies and --cookies-from-browser option will not work', method=None)
            elif http_code == 403:
                raise ExtractorError('Your Internet provider is likely blocked. Try another ISP or use VPN', expected=True)
            raise

        if video_info.get('status') != 'success':
            raise ExtractorError('Video info API returned an error', expected=True)
        data = video_info.get('data', {})
        title = data.get('title') or video_id
        description = data.get('description')
        thumbnail = data.get('thumbnail')

        uploader = data.get('uploader', {})
        uploader_url = uploader.get('url')

        # 2) Fix the ISO date to remove leftover data
        upload_date_raw = data.get('publishedAt')
        upload_date = None
        if upload_date_raw:
            # Remove fractional seconds and any extra data after 'Z'
            upload_date_raw = re.sub(r'\.\d+', '', upload_date_raw)
            upload_date_raw = re.sub(r'Z.*$', 'Z', upload_date_raw)
            try:
                parsed_date = datetime.datetime.fromisoformat(upload_date_raw.replace('Z', '+00:00'))
                upload_date = parsed_date.strftime('%Y%m%d')
            except ValueError:
                pass

        duration = data.get('duration')

        # 3) Convert numeric fields
        def safe_int(val):
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        view_count = safe_int(data.get('views'))
        comment_count = safe_int(data.get('totalComments'))
        like_count = safe_int(data.get('likes'))
        dislike_count = safe_int(data.get('dislikes'))

        average_rating = None
        if like_count is not None and dislike_count is not None:
            total = like_count + dislike_count
            if total > 0:
                average_rating = round((like_count / total) * 5, 1)

        categories = data.get('category')
        if categories and not isinstance(categories, list):
            categories = [categories]
        tags = data.get('tags')

        # 4) Get watch token (required for accessing manifests)
        watch_token_url = 'https://api.vanillo.tv/v1/watch'
        post_data = json.dumps({'videoId': video_id}).encode('utf-8')
        watch_token_resp = self._download_json(
            watch_token_url, video_id,
            note='Downloading watch token',
            data=post_data,
            headers={'Content-Type': 'application/json'})
        watch_token = watch_token_resp.get('data', {}).get('watchToken')
        if not watch_token:
            raise ExtractorError('Failed to retrieve watch token', expected=True)

        # 5) Get the HLS & DASH manifest URLs using the watch token
        manifests_url = f'https://api.vanillo.tv/v1/watch/manifests?watchToken={watch_token}'
        manifests = self._download_json(manifests_url, video_id, note='Downloading manifests')
        hls_url = manifests.get('data', {}).get('media', {}).get('hls')
        # dash_url = manifests.get('data', {}).get('media', {}).get('dash')

        # 6) Extract available formats and subtitles using combined helper methods
        subtitles = {}
        formats = []
        if hls_url:
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                hls_url, video_id, ext='mp4', m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        # DASH provides comically gigantic files. Disabling.
        # example - 1.7 mb file becomes 15.1 mb, thus short videos for no reason become 100+gb
        # same for audio tracks, thus RAM usage will be high, and merged file will be even bigger.
        '''
        if dash_url:
            fmts, subs = self._extract_mpd_formats_and_subtitles(
                dash_url, video_id, mpd_id='dash', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        '''

        # 7) Download all comments using pagination with pageKey
        if self._downloader.params.get('getcomments'):
            comments = self._get_comments(video_id, limit=10)
        else:
            comments = None

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'subtitles': subtitles,
            'comments': comments,
            'uploader_url': uploader_url,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'comment_count': comment_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'average_rating': average_rating,
            'categories': categories,
            'tags': tags,
        }


class VanilloPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:dev\.|beta\.)?vanillo\.tv/playlist/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://vanillo.tv/playlist/wn9_PM-DTPypZeNy32EE1A',
        'info_dict': {
            'id': 'wn9_PM-DTPypZeNy32EE1A',
            'title': 'Staff Picks',
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        # First, download playlist metadata
        playlist_api_url = f'https://api.vanillo.tv/v1/playlists/{playlist_id}'
        playlist_info = self._download_json(playlist_api_url, playlist_id, note='Downloading playlist metadata', fatal=False)
        playlist_data = playlist_info.get('data', {}).get('playlist', {})
        playlist_title = playlist_data.get('name') or playlist_id
        playlist_description = playlist_data.get('description')
        video_count = playlist_data.get('videoCount') or 20

        # Then, download the videos using the videoCount as the limit
        api_url = f'https://api.vanillo.tv/v1/playlists/{playlist_id}/videos?offset=0&limit={video_count}'
        playlist_data = self._download_json(api_url, playlist_id, note='Downloading playlist videos')
        videos = playlist_data.get('data', {}).get('videos', [])
        entries = []
        for video in videos:
            vid = video.get('id')
            if not vid:
                continue
            video_url = f'https://vanillo.tv/v/{vid}'
            entries.append(self.url_result(video_url, VanilloIE.ie_key()))
        info = self.playlist_result(entries, playlist_id, playlist_title=playlist_title)
        if playlist_description:
            info['description'] = playlist_description
        return info


class VanilloUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:dev\.|beta\.)?vanillo\.tv/u/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://vanillo.tv/u/f9pKNFrUSG6Qo3pJ4UlGbQ',
        'info_dict': {
            'id': 'f9pKNFrUSG6Qo3pJ4UlGbQ',
            'title': 'User BakhosVillager videos',
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        entries = []
        offset = 0
        while True:
            # Loop to paginate through all user videos
            api_url = f'https://api.vanillo.tv/v1/profiles/{user_id}/videos?offset={offset}&limit=20&groups=videos.all'
            user_data = self._download_json(api_url, user_id, note='Downloading user videos', fatal=False)
            videos = user_data.get('data', {}).get('videos', [])
            if not videos:
                break
            for video in videos:
                vid = video.get('id')
                if not vid:
                    continue
                video_url = f'https://vanillo.tv/v/{vid}'
                entries.append(self.url_result(video_url, VanilloIE.ie_key()))
            if len(videos) < 20:
                break
            offset += 20
        return self.playlist_result(entries, user_id, playlist_title=f'User {user_id} videos')
