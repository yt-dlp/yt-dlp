import itertools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    GeoRestrictedError,
    clean_html,
    get_element_by_class,
    get_elements_html_by_class,
    orderedSet,
    parse_count,
    parse_duration,
    unified_strdate,
    urlencode_postdata,
)


class BitChuteIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bitchute\.com/(?:video|embed|torrent/[^/]+)/(?P<id>[^/?#&]+)'
    _EMBED_REGEX = [rf'<(?:script|iframe)[^>]+\bsrc=(["\'])(?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://www.bitchute.com/video/UGlrF9o9b-Q/',
        'md5': '7e427d7ed7af5a75b5855705ec750e2b',
        'info_dict': {
            'id': 'UGlrF9o9b-Q',
            'ext': 'mp4',
            'title': 'This is the first video on #BitChute !',
            'description': 'md5:a0337e7b1fe39e32336974af8173a034',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'BitChute',
            'upload_date': '20170103',
        },
    }, {
        'url': 'https://www.bitchute.com/embed/lbb5G1hjPhw/',
        'only_matching': True,
    }, {
        'url': 'https://www.bitchute.com/torrent/Zee5BE49045h/szoMrox2JEI.webtorrent',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://www.bitchute.com/video/%s' % video_id, video_id, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.57 Safari/537.36',
            })

        title = self._html_extract_title(webpage) or self._og_search_title(webpage)
        format_urls = []
        for mobj in re.finditer(
                r'addWebSeed\s*\(\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage):
            format_urls.append(mobj.group('url'))
        format_urls.extend(re.findall(r'as=(https?://[^&"\']+)', webpage))

        formats = [
            {'url': format_url}
            for format_url in orderedSet(format_urls)]

        if not formats:
            entries = self._parse_html5_media_entries(
                url, webpage, video_id)
            if not entries:
                error = self._html_search_regex(r'<h1 class="page-title">([^<]+)</h1>', webpage, 'error', default='Cannot find video')
                if error == 'Video Unavailable':
                    raise GeoRestrictedError(error)
                raise ExtractorError(error, expected=True)
            formats = entries[0]['formats']

        self._check_formats(formats, video_id)
        if not formats:
            raise self.raise_no_formats('Video is unavailable', expected=True, video_id=video_id)
        self._sort_formats(formats)

        # some videos have empty string as description, default suppresses the warning
        description = self._og_search_description(webpage, default=None)
        thumbnail = self._og_search_thumbnail(webpage)
        uploader = clean_html(get_element_by_class('owner', webpage))
        publish_date = clean_html(get_element_by_class('video-publish-date', webpage))
        upload_date = unified_strdate(self._search_regex(
            r'at \d+:\d+ UTC on (.+?)\.', publish_date, 'upload date', fatal=False)
        )

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'upload_date': upload_date,
            'formats': formats,
        }


class BitChuteChannelIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bitchute\.com/channel/(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'https://www.bitchute.com/channel/bitchute/',
        'playlist_mincount': 10,
        'info_dict': {
            'id': 'bitchute',
        },
    }

    _TOKEN = 'zyG6tQcGPE5swyAEFLqKUwMuMMuF6IO2DZ6ZDQjGfsL0e4dcTLwqkTTul05Jdve7'

    def _entries(self, channel_id):
        channel_url = 'https://www.bitchute.com/channel/%s/' % channel_id
        offset = 0
        for page_num in itertools.count(1):
            data = self._download_json(
                '%sextend/' % channel_url, channel_id,
                'Downloading channel page %d' % page_num,
                data=urlencode_postdata({
                    'csrfmiddlewaretoken': self._TOKEN,
                    'name': '',
                    'offset': offset,
                }), headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Referer': channel_url,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Cookie': 'csrftoken=%s' % self._TOKEN,
                })
            if data.get('success') is not True:
                break
            html = data.get('html')
            results = []
            for video_html in get_elements_html_by_class('channel-videos-container', html):
                match = re.search(r'<a\b[^>]+\bhref=["\']/video/(?P<id>[^"\'/]+)', video_html)
                if not match:
                    continue
                video_id = match.group('id')
                results.append(self.url_result(
                    'https://www.bitchute.com/video/%s' % video_id,
                    ie=BitChuteIE.ie_key(), video_id=video_id, url_transparent=True,
                    title=clean_html(get_element_by_class('channel-videos-title', video_html)),
                    description=clean_html(get_element_by_class('channel-videos-text', video_html)),
                    duration=parse_duration(get_element_by_class('video-duration', video_html)),
                    view_count=parse_count(clean_html(get_element_by_class('video-views', video_html))),
                ))
            if not results:
                break
            offset += len(results)
            for result in results:
                yield result

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        return self.playlist_result(
            self._entries(channel_id), playlist_id=channel_id)
