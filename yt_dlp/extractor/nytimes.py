# coding: utf-8
from __future__ import unicode_literals

import hmac
import hashlib
import base64

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    js_to_json,
    mimetype2ext,
    parse_iso8601,
    remove_start,
)


class NYTimesBaseIE(InfoExtractor):
    _SECRET = b'pX(2MbU2);4N{7J8)>YwKRJ+/pQ3JkiU2Q^V>mFYv6g6gYvt6v'

    def _extract_video_from_id(self, video_id):
        # Authorization generation algorithm is reverse engineered from `signer` in
        # http://graphics8.nytimes.com/video/vhs/vhs-2.x.min.js
        path = '/svc/video/api/v3/video/' + video_id
        hm = hmac.new(self._SECRET, (path + ':vhs').encode(), hashlib.sha512).hexdigest()
        video_data = self._download_json('http://www.nytimes.com' + path, video_id, 'Downloading video JSON', headers={
            'Authorization': 'NYTV ' + base64.b64encode(hm.encode()).decode(),
            'X-NYTV': 'vhs',
        }, fatal=False)
        if not video_data:
            video_data = self._download_json(
                'http://www.nytimes.com/svc/video/api/v2/video/' + video_id,
                video_id, 'Downloading video JSON')

        title = video_data['headline']

        def get_file_size(file_size):
            if isinstance(file_size, int):
                return file_size
            elif isinstance(file_size, dict):
                return int(file_size.get('value', 0))
            else:
                return None

        urls = []
        formats = []
        subtitles = {}
        for video in video_data.get('renditions', []):
            video_url = video.get('url')
            format_id = video.get('type')
            if not video_url or format_id == 'thumbs' or video_url in urls:
                continue
            urls.append(video_url)
            ext = mimetype2ext(video.get('mimetype')) or determine_ext(video_url)
            if ext == 'm3u8':
                m3u8_fmts, m3u8_subs = self._extract_m3u8_formats_and_subtitles(
                    video_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id=format_id or 'hls', fatal=False)
                formats.extend(m3u8_fmts)
                subtitles = self._merge_subtitles(subtitles, m3u8_subs)
            elif ext == 'mpd':
                continue
            #     formats.extend(self._extract_mpd_formats(
            #         video_url, video_id, format_id or 'dash', fatal=False))
            else:
                formats.append({
                    'url': video_url,
                    'format_id': format_id,
                    'vcodec': video.get('videoencoding') or video.get('video_codec'),
                    'width': int_or_none(video.get('width')),
                    'height': int_or_none(video.get('height')),
                    'filesize': get_file_size(video.get('file_size') or video.get('fileSize')),
                    'tbr': int_or_none(video.get('bitrate'), 1000) or None,
                    'ext': ext,
                })
        self._sort_formats(formats)

        thumbnails = []
        for image in video_data.get('images', []):
            image_url = image.get('url')
            if not image_url:
                continue
            thumbnails.append({
                'url': 'http://www.nytimes.com/' + image_url,
                'width': int_or_none(image.get('width')),
                'height': int_or_none(image.get('height')),
            })

        publication_date = video_data.get('publication_date')
        timestamp = parse_iso8601(publication_date[:-8]) if publication_date else None

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('summary'),
            'timestamp': timestamp,
            'uploader': video_data.get('byline'),
            'duration': float_or_none(video_data.get('duration'), 1000),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
        }


class NYTimesIE(NYTimesBaseIE):
    _VALID_URL = r'https?://(?:(?:www\.)?nytimes\.com/video/(?:[^/]+/)+?|graphics8\.nytimes\.com/bcvideo/\d+(?:\.\d+)?/iframe/embed\.html\?videoId=)(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://www.nytimes.com/video/opinion/100000002847155/verbatim-what-is-a-photocopier.html?playlistId=100000001150263',
        'md5': 'd665342765db043f7e225cff19df0f2d',
        'info_dict': {
            'id': '100000002847155',
            'ext': 'mov',
            'title': 'Verbatim: What Is a Photocopier?',
            'description': 'md5:93603dada88ddbda9395632fdc5da260',
            'timestamp': 1398631707,
            'upload_date': '20140427',
            'uploader': 'Brett Weiner',
            'duration': 419,
        }
    }, {
        'url': 'http://www.nytimes.com/video/travel/100000003550828/36-hours-in-dubai.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        return self._extract_video_from_id(video_id)


class NYTimesArticleIE(NYTimesBaseIE):
    _VALID_URL = r'https?://(?:www\.)?nytimes\.com/(.(?<!video))*?/(?:[^/]+/)*(?P<id>[^.]+)(?:\.html)?'
    _TESTS = [{
        'url': 'http://www.nytimes.com/2015/04/14/business/owner-of-gravity-payments-a-credit-card-processor-is-setting-a-new-minimum-wage-70000-a-year.html?_r=0',
        'md5': 'e2076d58b4da18e6a001d53fd56db3c9',
        'info_dict': {
            'id': '100000003628438',
            'ext': 'mov',
            'title': 'New Minimum Wage: $70,000 a Year',
            'description': 'Dan Price, C.E.O. of Gravity Payments, surprised his 120-person staff by announcing that he planned over the next three years to raise the salary of every employee to $70,000 a year.',
            'timestamp': 1429033037,
            'upload_date': '20150414',
            'uploader': 'Matthew Williams',
        }
    }, {
        'url': 'http://www.nytimes.com/2016/10/14/podcasts/revelations-from-the-final-weeks.html',
        'md5': 'e0d52040cafb07662acf3c9132db3575',
        'info_dict': {
            'id': '100000004709062',
            'title': 'The Run-Up: ‘He Was Like an Octopus’',
            'ext': 'mp3',
            'description': 'md5:fb5c6b93b12efc51649b4847fe066ee4',
            'series': 'The Run-Up',
            'episode': '‘He Was Like an Octopus’',
            'episode_number': 20,
            'duration': 2130,
        }
    }, {
        'url': 'http://www.nytimes.com/2016/10/16/books/review/inside-the-new-york-times-book-review-the-rise-of-hitler.html',
        'info_dict': {
            'id': '100000004709479',
            'title': 'The Rise of Hitler',
            'ext': 'mp3',
            'description': 'md5:bce877fd9e3444990cb141875fab0028',
            'creator': 'Pamela Paul',
            'duration': 3475,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.nytimes.com/news/minute/2014/03/17/times-minute-whats-next-in-crimea/?_php=true&_type=blogs&_php=true&_type=blogs&_r=1',
        'only_matching': True,
    }]

    def _extract_podcast_from_json(self, json, page_id, webpage):
        podcast_audio = self._parse_json(
            json, page_id, transform_source=js_to_json)

        audio_data = podcast_audio['data']
        track = audio_data['track']

        episode_title = track['title']
        video_url = track['source']

        description = track.get('description') or self._html_search_meta(
            ['og:description', 'twitter:description'], webpage)

        podcast_title = audio_data.get('podcast', {}).get('title')
        title = ('%s: %s' % (podcast_title, episode_title)
                 if podcast_title else episode_title)

        episode = audio_data.get('podcast', {}).get('episode') or ''
        episode_number = int_or_none(self._search_regex(
            r'[Ee]pisode\s+(\d+)', episode, 'episode number', default=None))

        return {
            'id': remove_start(podcast_audio.get('target'), 'FT') or page_id,
            'url': video_url,
            'title': title,
            'description': description,
            'creator': track.get('credit'),
            'series': podcast_title,
            'episode': episode_title,
            'episode_number': episode_number,
            'duration': int_or_none(track.get('duration')),
        }

    def _real_extract(self, url):
        page_id = self._match_id(url)

        webpage = self._download_webpage(url, page_id)

        video_id = self._search_regex(
            r'data-videoid=["\'](\d+)', webpage, 'video id',
            default=None, fatal=False)
        if video_id is not None:
            return self._extract_video_from_id(video_id)

        podcast_data = self._search_regex(
            (r'NYTD\.FlexTypes\.push\s*\(\s*({.+?})\s*\)\s*;\s*</script',
             r'NYTD\.FlexTypes\.push\s*\(\s*({.+})\s*\)\s*;'),
            webpage, 'podcast data')
        return self._extract_podcast_from_json(podcast_data, page_id, webpage)


class NYTimesCookingIE(NYTimesBaseIE):
    _VALID_URL = r'https?://cooking\.nytimes\.com/(?:guid|recip)es/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://cooking.nytimes.com/recipes/1017817-cranberry-curd-tart',
        'md5': 'dab81fa2eaeb3f9ed47498bdcfcdc1d3',
        'info_dict': {
            'id': '100000004756089',
            'ext': 'mov',
            'timestamp': 1479383008,
            'uploader': 'By SHAW LASH, ADAM SAEWITZ and JAMES HERRON',
            'title': 'Cranberry Tart',
            'upload_date': '20161117',
            'description': 'If you are a fan of lemon curd or the classic French tarte au citron, you will love this cranberry version.',
        },
    }, {
        'url': 'https://cooking.nytimes.com/guides/13-how-to-cook-a-turkey',
        'md5': '4b2e8c70530a89b8d905a2b572316eb8',
        'info_dict': {
            'id': '100000003951728',
            'ext': 'mov',
            'timestamp': 1445509539,
            'description': 'Turkey guide',
            'upload_date': '20151022',
            'title': 'Turkey',
        }
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)

        webpage = self._download_webpage(url, page_id)

        video_id = self._search_regex(
            r'data-video-id=["\'](\d+)', webpage, 'video id')

        return self._extract_video_from_id(video_id)
