import itertools
import re
from datetime import datetime
from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import ExtractorError


class LocalsIE(InfoExtractor):
    _VALID_URL = r'(?P<url>(?P<host>https?://(?P<community>[^\.]+)\.(?:locals|rumble)\.com)(?:/u?post/(?P<id>\d+)/.*|/content/(?P<content>[^/]+)/.*))'
    _TESTS = [{
        'url': 'https://santasurfing.locals.com/post/4451827/maui-updates-and-we-thank-you-very-much',
        'md5': '7155608f5c00daff36bd0ac832a3822a',
        'info_dict': {
            'id': '4451827',
            'ext': 'mp4',
            'title': 'Maui Updates and We Thank You Very Much!',
            'timestamp': 1692309600.0,
            'channel': 'SantaSurfingAdm',
            'channel_url': 'https://santasurfing.locals.com/member/SantaSurfingAdm',
            'duration': 30,
            'uploader': 'SantaSurfingAdm',
            'upload_date': '20230818',
            'media_type': 'trailer',
            'thumbnail': r're:^https?://.*\.jpeg$',
        }
    }, {
        'url': 'https://kat.locals.com/upost/151097/ayyyy-i-m-now-on-locals-i-ll-be-posting-all-kinds-of-stuff-i-that-i-never-would-to-my-social-me',
        'md5': 'ce1a2362c19fe781e011b005a381a3f9',
        'info_dict': {
            'id': '151097',
            'ext': 'mp4',
            'duration': 78,
            'title': 'I may be way too proud of this video…',
            'timestamp': 1600984800.0,
            'channel': 'KatTimpf',
            'channel_url': 'https://kat.locals.com/member/KatTimpf',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'KatTimpf',
            'upload_date': '20200924',
            'media_type': 'episode',

        }
    }, {
        'url': 'https://happyclubwithaudrey.locals.com/post/4144524/happy-club-intro',
        'md5': '1f4cf7b9cda0c6b9cab1f8fbfe71d972',
        'info_dict': {
            'id': '4144524',
            'ext': 'mp4',
            'title': 'Happy Club Intro',
            'timestamp': 1686607200.0,
            'channel': 'Audrey Meisner',
            'channel_url': 'https://happyclubwithaudrey.locals.com/member/audreyfun',
            'duration': 72,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Audrey Meisner',
            'upload_date': '20230612',
            'media_type': 'episode',
        }
    }]

    def entries(self, url, community):
        for page in itertools.count(1):
            try:
                webpage = self._download_webpage(f'{url}?page={page}', community, note='Downloading page %d' % page)
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                    break
                raise

            urls = re.findall(r'data-post-url="([^">]+)"', webpage)
            if len(urls) == 0:
                break

            for video_url in urls:
                yield self.url_result(video_url)

    def _real_extract(self, url):
        url, host, community, video_id, content = self._match_valid_url(url).groups()

        # if the page is not a /post/ get playlist entries
        if video_id is None:
            return self.playlist_result(self.entries(url, community), playlist_id=community + '_' + content)

        webpage = self._download_webpage(url, video_id)

        # regex for channel name, channel url and date
        post_matches = re.search(
            r'<span class="username">[^<]*<a[^>]*href="(?P<url>[^"]+)"[^<]*<span>[^<]*<span[^>]*>(?P<channel>[^<]+)</span>[\s\S]*?<div class="info">(?P<date>[^<]+)</div>',
            webpage)

        try:
            date = datetime.strptime(post_matches.group('date'), "%B %d, %Y")
        except ValueError:
            # extracting the time probably failed because the element had a relative time like "2 hours ago"
            # so we assume it was posted today
            date = datetime.today()

        timestamp = date.timestamp()
        upload_date = date.strftime("%Y%m%d")

        title = self._html_search_regex(r'<div[^>]+class="title"[^>]*>(?P<title>[^<]*)</div>', webpage, 'title',
                                        fatal=False)

        is_podcast = (webpage.find('initAudioControl') > -1)
        if is_podcast:
            # locals does not have live podcast and no thumbnails for podcasts
            thumbnails = None
            is_live = False

            # this is not in the webpage
            duration = None
            media_type = None

            # regex for source and type
            audio_matches = re.search(
                r'<audio[^>]*>[^<]*<source[^>]*src="(?P<source>[^"]*)"[^>]*type="audio/(?P<type>[^"]*)"',
                webpage)

            formats = [{
                'url': host + audio_matches.group('source'),
                'ext': audio_matches.group('type'),
                'acodec': audio_matches.group('type'),
                'vcodec': 'none'
            }]
        else:
            thumbnail = self._html_search_regex(
                r'<div[^>]+class="[^"]*video-preview[^"]*"[^>]*background:url\(\'(?P<thumbnail>[^\']+)\'\)', webpage,
                'thumbnail', fatal=False)
            thumbnails = [{'url': thumbnail}]

            # regex for duration, is_live, is_preview and format m3u8_source
            video_matches = re.search(
                r'<video[^>]*data-duration="(?P<duration>\d+)"[^>]*data-is-live="(?P<is_live>\d)"[^>]*data-preview="(?P<is_preview>[^"]+)"[^>]*>[^<]*<source[^>]*data-src="(?P<m3u8_source>[^"]*)"',
                webpage)

            is_live = video_matches.group('is_live') == '1'
            duration = int(video_matches.group('duration'))

            media_type = 'episode'
            if video_matches.group('is_preview') == 'true':
                media_type = 'trailer'
                duration = 30

            m3u8_url = host + video_matches.group('m3u8_source')
            formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls', live=is_live, fatal=True)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnails': thumbnails,
            'timestamp': timestamp,
            'channel': post_matches.group('channel'),
            'channel_url': host + post_matches.group('url'),
            'duration': duration,
            'uploader': post_matches.group('channel'),
            'is_live': is_live,
            'media_type': media_type,
            'upload_date': upload_date,
        }
