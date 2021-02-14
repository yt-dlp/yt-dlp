# coding: utf-8
from __future__ import unicode_literals

import itertools
from .common import InfoExtractor


class StoryFireIE(InfoExtractor):
    _VALID_URL = r'(?:(?:https?://(?:www\.)?storyfire\.com/video-details)|(?:https://storyfire.app.link))/(?P<id>[^/\s]+)'
    _TESTS = [{
        'url': 'https://storyfire.com/video-details/5df1d132b6378700117f9181',
        'md5': '560953bfca81a69003cfa5e53ac8a920',
        'info_dict': {
            'id': '5df1d132b6378700117f9181',
            'ext': 'mp4',
            'title': 'Buzzfeed Teaches You About Memes',
            'uploader_id': 'ntZAJFECERSgqHSxzonV5K2E89s1',
            'timestamp': 1576129028,
            'description': 'Mocking Buzzfeed\'s meme lesson. Reuploaded from YouTube because of their new policies',
            'uploader': 'whang!',
            'upload_date': '20191212',
        },
        'params': {'format': 'bestvideo'}  # There are no merged formats in the playlist.
    }, {
        'url': 'https://storyfire.app.link/5GxAvWOQr8',  # Alternate URL format, with unrelated short ID
        'md5': '7a2dc6d60c4889edfed459c620fe690d',
        'info_dict': {
            'id': '5f1e11ecd78a57b6c702001d',
            'ext': 'm4a',
            'title': 'Weird Nintendo Prototype Leaks',
            'description': 'A stream taking a look at some weird Nintendo Prototypes with Luigi in Mario 64 and weird Yoshis',
            'timestamp': 1595808576,
            'upload_date': '20200727',
            'uploader': 'whang!',
            'uploader_id': 'ntZAJFECERSgqHSxzonV5K2E89s1',
        },
        'params': {'format': 'bestaudio'}  # Verifying audio extraction

    }]

    _aformats = {
        'audio-medium-audio': {'acodec': 'aac', 'abr': 125, 'preference': -10},
        'audio-high-audio': {'acodec': 'aac', 'abr': 254, 'preference': -1},
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # Extracting the json blob is mandatory to proceed with extraction.
        jsontext = self._html_search_regex(
            r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
            webpage, 'json_data')

        json = self._parse_json(jsontext, video_id)

        # The currentVideo field in the json is mandatory
        # because it contains the only link to the m3u playlist
        video = json['props']['initialState']['video']['currentVideo']
        videourl = video['vimeoVideoURL']  # Video URL is mandatory

        # Extract other fields from the json in an error tolerant fashion
        # ID may be incorrect (on short URL format), correct it.
        parsed_id = video.get('_id')
        if parsed_id:
            video_id = parsed_id

        title = video.get('title')
        description = video.get('description')

        thumbnail = video.get('storyImage')
        views = video.get('views')
        likes = video.get('likesCount')
        comments = video.get('commentsCount')
        duration = video.get('videoDuration')
        publishdate = video.get('publishDate')  # Apparently epoch time, day only

        uploader = video.get('username')
        uploader_id = video.get('hostID')
        # Construct an uploader URL
        uploader_url = None
        if uploader_id:
            uploader_url = "https://storyfire.com/user/%s/video" % uploader_id

        # Collect root playlist to determine formats
        formats = self._extract_m3u8_formats(
            videourl, video_id, 'mp4', 'm3u8_native')

        # Modify formats to fill in missing information about audio codecs
        for format in formats:
            aformat = self._aformats.get(format['format_id'])
            if aformat:
                format['acodec'] = aformat['acodec']
                format['abr'] = aformat['abr']
                format['preference'] = aformat['preference']
                format['ext'] = 'm4a'

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'ext': "mp4",
            'url': videourl,
            'formats': formats,

            'thumbnail': thumbnail,
            'view_count': views,
            'like_count': likes,
            'comment_count': comments,
            'duration': duration,
            'timestamp': publishdate,

            'uploader': uploader,
            'uploader_id': uploader_id,
            'uploader_url': uploader_url,

        }


class StoryFireUserIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?storyfire\.com/user/(?P<id>[^/\s]+)/video'
    _TESTS = [{
        'url': 'https://storyfire.com/user/ntZAJFECERSgqHSxzonV5K2E89s1/video',
        'info_dict': {
            'id': 'ntZAJFECERSgqHSxzonV5K2E89s1',
            'title': 'whang!',
        },
        'playlist_mincount': 18
    }, {
        'url': 'https://storyfire.com/user/UQ986nFxmAWIgnkZQ0ftVhq4nOk2/video',
        'info_dict': {
            'id': 'UQ986nFxmAWIgnkZQ0ftVhq4nOk2',
            'title': 'McJuggerNuggets',
        },
        'playlist_mincount': 143

    }]

    # Generator for fetching playlist items
    def _enum_videos(self, baseurl, user_id, firstjson):
        totalVideos = int(firstjson['videosCount'])
        haveVideos = 0
        json = firstjson

        for page in itertools.count(1):
            for video in json['videos']:
                id = video['_id']
                url = "https://storyfire.com/video-details/%s" % id
                haveVideos += 1
                yield {
                    '_type': 'url',
                    'id': id,
                    'url': url,
                    'ie_key': 'StoryFire',

                    'title': video.get('title'),
                    'description': video.get('description'),
                    'view_count': video.get('views'),
                    'comment_count': video.get('commentsCount'),
                    'duration': video.get('videoDuration'),
                    'timestamp': video.get('publishDate'),
                }
            # Are there more pages we could fetch?
            if haveVideos < totalVideos:
                pageurl = baseurl + ("%i" % haveVideos)
                json = self._download_json(pageurl, user_id,
                                           note='Downloading page %s' % page)

                # Are there any videos in the new json?
                videos = json.get('videos')
                if not videos or len(videos) == 0:
                    break  # no videos

            else:
                break  # We have fetched all the videos, stop

    def _real_extract(self, url):
        user_id = self._match_id(url)

        baseurl = "https://storyfire.com/app/publicVideos/%s?skip=" % user_id

        # Download first page to ensure it can be downloaded, and get user information if available.
        firstpage = baseurl + "0"
        firstjson = self._download_json(firstpage, user_id)

        title = None
        videos = firstjson.get('videos')
        if videos and len(videos):
            title = videos[1].get('username')

        return {
            '_type': 'playlist',
            'entries': self._enum_videos(baseurl, user_id, firstjson),
            'id': user_id,
            'title': title,
        }


class StoryFireSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?storyfire\.com/write/series/stories/(?P<id>[^/\s]+)'
    _TESTS = [{
        'url': 'https://storyfire.com/write/series/stories/-Lq6MsuIHLODO6d2dDkr/',
        'info_dict': {
            'id': '-Lq6MsuIHLODO6d2dDkr',
        },
        'playlist_mincount': 13
    }, {
        'url': 'https://storyfire.com/write/series/stories/the_mortal_one/',
        'info_dict': {
            'id': 'the_mortal_one',
        },
        'playlist_count': 0  # This playlist has entries, but no videos.
    }, {
        'url': 'https://storyfire.com/write/series/stories/story_time',
        'info_dict': {
            'id': 'story_time',
        },
        'playlist_mincount': 10
    }]

    # Generator for returning playlist items
    # This object is substantially different than the one in the user videos page above
    def _enum_videos(self, jsonlist):
        for video in jsonlist:
            id = video['_id']
            if video.get('hasVideo'):  # Boolean element
                url = "https://storyfire.com/video-details/%s" % id
                yield {
                    '_type': 'url',
                    'id': id,
                    'url': url,
                    'ie_key': 'StoryFire',

                    'title': video.get('title'),
                    'description': video.get('description'),
                    'view_count': video.get('views'),
                    'likes_count': video.get('likesCount'),
                    'comment_count': video.get('commentsCount'),
                    'duration': video.get('videoDuration'),
                    'timestamp': video.get('publishDate'),
                }

    def _real_extract(self, url):
        list_id = self._match_id(url)

        listurl = "https://storyfire.com/app/seriesStories/%s/list" % list_id
        json = self._download_json(listurl, list_id)

        return {
            '_type': 'playlist',
            'entries': self._enum_videos(json),
            'id': list_id
        }
