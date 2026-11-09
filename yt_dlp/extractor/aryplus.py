from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class ARYPlusBaseIE(InfoExtractor):
    _API_BASE = 'https://be.aryplus.tv'
    _IMG_BASE = 'https://images.aryplus.tv'
    _API_KEY = 'ak_37515186786306625012043079404171'

    def _call_api(self, endpoint, video_id, note='Downloading API JSON', query=None):
        headers = {
            'x-api-key': self._API_KEY,
            'Origin': 'https://aryplus.tv',
            'Referer': 'https://aryplus.tv/',
        }
        return self._download_json(
            f'{self._API_BASE}{endpoint}', video_id, note=note,
            headers=headers, query=query)

    def _fix_image_url(self, path):
        if not path:
            return None
        if path.startswith(('http://', 'https://')):
            return path
        return f'{self._IMG_BASE}/{path.lstrip("/")}'


class ARYPlusIE(ARYPlusBaseIE):
    IE_NAME = 'aryplus'
    _VALID_URL = r'https?://(?:www\.)?aryplus\.tv/(?:video/v[12]/(?:drm/)?(?P<platform>[0-9]+)/(?P<id>[a-f0-9]+)(?:/(?P<series_id>[a-f0-9]+))?|watch/v[12]/(?P<single_id>[a-f0-9]+))'

    _TESTS = [{
        'url': 'https://aryplus.tv/video/v2/3/6a6e0b1e9bc4b079859bc14b/6a57868b5bf57c474cc00a50',
        'info_dict': {
            'id': '6a6e0b1e9bc4b079859bc14b',
            'ext': 'mp4',
            'title': 'Episode 1',
            'description': 'md5:4f666fb01c940e7800a07c43a0e56a37',
            'duration': 2273,
            'episode_number': 1,
            'episode': 'Episode 1',
            'series_id': '6a57868b5bf57c474cc00a50',
            'thumbnail': r're:^https?://.*\.webp$',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://aryplus.tv/watch/v1/6aea0c13c1b320805cff33cb',
        'info_dict': {
            'id': '6aea0c13c1b320805cff33cb',
            'ext': 'mp4',
            'title': 'Mera Ghar',
            'description': 'md5:2167d32e92c2bfba91730bb544ae5d0e',
            'thumbnail': r're:^https?://.*',
            'cast': ['Zubab Rana', 'Shahroz Sabzwari', 'Uzma Hassan'],
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        platform = mobj.group('platform')
        series_id = mobj.group('series_id')
        single_id = mobj.group('single_id')

        # Third-party embeds (YouTube / DailyMotion)
        if platform == '1':
            return self.url_result(f'https://www.youtube.com/watch?v={video_id}', 'Youtube', video_id)
        elif platform == '2':
            return self.url_result(f'https://www.dailymotion.com/video/{video_id}', 'Dailymotion', video_id)

        # Single video watch route: /watch/v1/:channel
        if single_id:
            video_id = single_id
            series_data = self._call_api(f'/api/series/{video_id}', video_id, note='Downloading video metadata')

            if series_data.get('drmEnabled'):
                self.report_drm(video_id)

            video_source = series_data.get('seiresCDN') or series_data.get('seiresCDNWebLink')
            web_key = series_data.get('seiresCDNWebKey')

            if not video_source or web_key:
                # May require signed link
                if web_key and series_data.get('seiresCDNWebLink'):
                    live_links = self._call_api(
                        '/sharer/livelinks_new', video_id,
                        note='Downloading signed stream link',
                        query={'key': web_key, 'path': series_data['seiresCDNWebLink']})
                    video_source = traverse_obj(live_links, (0, 'signed_url'))

            if not video_source:
                # Fallback to episode list
                ep_data = self._call_api(f'/api/cdn/{video_id}', video_id, note='Downloading episode stream data')
                episodes = ep_data.get('episode') or []
                if episodes:
                    ep = episodes[0]
                    video_source = ep.get('videoSource')
                    if ep.get('drmEnabled'):
                        self.report_drm(video_id)

            if not video_source:
                raise ExtractorError('No video stream found for this video', expected=True)

            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                video_source, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)

            thumbnails = []
            for img_key in ('imageCoverDesktop', 'imageCoverMobile', 'imagePoster', 'imageCoverBig', 'imageCoverExtra'):
                img_url = self._fix_image_url(series_data.get(img_key))
                if img_url:
                    thumbnails.append({'url': img_url})

            cast = series_data.get('cast')
            cast_list = [c.strip() for c in cast if isinstance(c, str) and c.strip()] if isinstance(cast, list) else None

            return {
                'id': video_id,
                'title': series_data.get('title'),
                'description': series_data.get('description'),
                'duration': int_or_none(series_data.get('duration')),
                'formats': formats,
                'subtitles': subtitles,
                'thumbnails': thumbnails,
                'cast': cast_list,
                'release_date': series_data.get('releaseDate'),
            }

        # Episode route: /video/v1/... or /video/v2/...
        ep_json = self._call_api(f'/api/cdn/ep/{video_id}', video_id, note='Downloading episode metadata')
        episode = ep_json.get('episode')
        if not episode:
            raise ExtractorError('Episode not found or unavailable', expected=True)

        if episode.get('drmEnabled'):
            self.report_drm(video_id)

        video_source = episode.get('videoSource')
        if not video_source:
            raise ExtractorError('No playable stream found for this episode', expected=True)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video_source, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)

        thumbnails = []
        for img_key in ('imagePath', 'imagePathV2'):
            img_url = self._fix_image_url(episode.get(img_key))
            if img_url:
                thumbnails.append({'url': img_url})

        return {
            'id': video_id,
            'title': episode.get('title'),
            'description': episode.get('description'),
            'duration': int_or_none(episode.get('videoLength')),
            'episode_number': int_or_none(episode.get('videoEpNumber')),
            'series_id': series_id or episode.get('seriesId'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
        }


class ARYPlusSeriesIE(ARYPlusBaseIE):
    IE_NAME = 'aryplus:series'
    _VALID_URL = r'https?://(?:www\.)?aryplus\.tv/series/(?P<id>[a-f0-9]+)'

    _TESTS = [{
        'url': 'https://aryplus.tv/series/6a57868b5bf57c474cc00a50',
        'info_dict': {
            'id': '6a57868b5bf57c474cc00a50',
            'title': 'Dar-E-Nijaat',
            'description': 'md5:9b6254ef7fbf1592a35624d3e64e936a',
        },
        'playlist_mincount': 20,
    }]

    def _real_extract(self, url):
        series_id = self._match_id(url)
        series_data = self._call_api(f'/api/series/{series_id}', series_id, note='Downloading series metadata')

        # If it's actually a single video or live channel
        series_type = series_data.get('seriesType')
        if series_type == 'singleVideo':
            return self.url_result(f'https://aryplus.tv/watch/v1/{series_id}', ARYPlusIE.ie_key(), series_id)
        elif series_type in ('live', 'live-event'):
            return self.url_result(f'https://aryplus.tv/live/v1/{series_id}', ARYPlusLiveIE.ie_key(), series_id)

        series_title = series_data.get('title')
        series_desc = series_data.get('description')

        # Fetch episodes (first try all from /api/cdn/<id>)
        cdn_data = self._call_api(f'/api/cdn/{series_id}', series_id, note='Downloading episodes list')
        episodes = cdn_data.get('episode') or []

        # If hasNextPage is True or pagination is used, paginate through pages
        if cdn_data.get('hasNextPage'):
            page = 2
            total_pages = cdn_data.get('totalPages') or 1
            while page <= total_pages:
                page_data = self._call_api(
                    f'/api/v2/cdn/pg/{series_id}', series_id,
                    note=f'Downloading episodes page {page}/{total_pages}',
                    query={'page': page, 'limit': 50, 'sort': 'asc'})
                page_episodes = page_data.get('episode') or []
                if not page_episodes:
                    break
                episodes.extend(page_episodes)
                if not page_data.get('hasNextPage'):
                    break
                page += 1

        entries = []
        for ep in episodes:
            ep_id = ep.get('_id')
            if not ep_id:
                continue
            ep_title = ep.get('title')
            entries.append(self.url_result(
                f'https://aryplus.tv/video/v2/3/{ep_id}/{series_id}',
                ie=ARYPlusIE.ie_key(),
                video_id=ep_id,
                video_title=ep_title,
            ))

        return self.playlist_result(
            entries,
            playlist_id=series_id,
            playlist_title=series_title,
            playlist_description=series_desc,
        )


class ARYPlusLiveIE(ARYPlusBaseIE):
    IE_NAME = 'aryplus:live'
    _VALID_URL = r'https?://(?:www\.)?aryplus\.tv/(?:live|live-event)/v[12]/(?P<id>[a-f0-9]+)'

    _TESTS = []

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        channel_data = self._call_api(f'/api/series/{channel_id}', channel_id, note='Downloading channel metadata')

        if channel_data.get('drmEnabled'):
            self.report_drm(channel_id)

        video_source = None
        web_key = channel_data.get('seiresCDNWebKey')
        web_link = channel_data.get('seiresCDNWebLink')

        if web_key and web_link:
            live_links = self._call_api(
                '/sharer/livelinks_new', channel_id,
                note='Downloading live stream link',
                query={'key': web_key, 'path': web_link})
            video_source = traverse_obj(live_links, (0, 'signed_url'))

        if not video_source:
            video_source = channel_data.get('seiresCDN') or web_link

        if not video_source:
            raise ExtractorError('Live stream is currently offline or unavailable', expected=True)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video_source, channel_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)

        thumbnails = []
        for img_key in ('imageCoverDesktop', 'imageCoverMobile', 'imagePoster'):
            img_url = self._fix_image_url(channel_data.get(img_key))
            if img_url:
                thumbnails.append({'url': img_url})

        return {
            'id': channel_id,
            'title': channel_data.get('title'),
            'description': channel_data.get('description'),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'is_live': True,
        }


class ARYPlusShortsIE(ARYPlusBaseIE):
    IE_NAME = 'aryplus:shorts'
    _VALID_URL = r'https?://(?:www\.)?aryplus\.tv/shorts/(?P<id>[a-f0-9]+)'

    _TESTS = [{
        'url': 'https://aryplus.tv/shorts/6a4d257d67472344b84e615b',
        'info_dict': {
            'id': '6a4d257d67472344b84e615b',
            'ext': 'mp4',
            'title': 'GMP',
            'description': '▫️ Show',
            'duration': 81,
            'thumbnail': r're:^https?://.*\.webp$',
            'view_count': int,
            'like_count': int,
            'timestamp': 1783440765,
            'upload_date': '20260707',
            'tags': ['Drama'],
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        short_id = self._match_id(url)
        short_data = self._call_api(f'/api/v2/shorts/{short_id}', short_id, note='Downloading short video metadata')

        video_source = short_data.get('videoUrl')
        if not video_source:
            raise ExtractorError('Short video stream not found', expected=True)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video_source, short_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)

        thumbnail = self._fix_image_url(short_data.get('thumbnailUrl'))

        return {
            'id': short_id,
            'title': short_data.get('title'),
            'description': short_data.get('description'),
            'duration': int_or_none(short_data.get('duration')),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': thumbnail,
            'view_count': int_or_none(short_data.get('viewsCount')),
            'like_count': int_or_none(short_data.get('likesCount')),
            'timestamp': parse_iso8601(short_data.get('createdAt')),
            'tags': short_data.get('tags'),
        }
