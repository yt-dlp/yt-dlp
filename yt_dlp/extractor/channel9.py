from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
    qualities,
    unescapeHTML,
)


class Channel9IE(InfoExtractor):
    IE_DESC = 'Channel 9'
    IE_NAME = 'channel9'
    _VALID_URL = r'https?://(?:www\.)?(?:channel9\.msdn\.com|s\.ch9\.ms)/(?P<contentpath>.+?)(?P<rss>/RSS)?/?(?:[?#&]|$)'

    _TESTS = [{
        'url': 'http://channel9.msdn.com/Events/TechEd/Australia/2013/KOS002',
        'md5': '32083d4eaf1946db6d454313f44510ca',
        'info_dict': {
            'id': '6c413323-383a-49dc-88f9-a22800cab024',
            'ext': 'wmv',
            'title': 'Developer Kick-Off Session: Stuff We Love',
            'description': 'md5:b80bf9355a503c193aff7ec6cd5a7731',
            'duration': 4576,
            'thumbnail': r're:https?://.*\.jpg',
            'timestamp': 1377717420,
            'upload_date': '20130828',
            'session_code': 'KOS002',
            'session_room': 'Arena 1A',
            'session_speakers': 'count:5',
        },
    }, {
        'url': 'http://channel9.msdn.com/posts/Self-service-BI-with-Power-BI-nuclear-testing',
        'md5': 'dcf983ee6acd2088e7188c3cf79b46bc',
        'info_dict': {
            'id': 'fe8e435f-bb93-4e01-8e97-a28c01887024',
            'ext': 'wmv',
            'title': 'Self-service BI with Power BI - nuclear testing',
            'description': 'md5:2d17fec927fc91e9e17783b3ecc88f54',
            'duration': 1540,
            'thumbnail': r're:https?://.*\.jpg',
            'timestamp': 1386381991,
            'upload_date': '20131207',
            'authors': ['Mike Wilmot'],
        },
    }, {
        # low quality mp4 is best
        'url': 'https://channel9.msdn.com/Events/CPP/CppCon-2015/Ranges-for-the-Standard-Library',
        'info_dict': {
            'id': '33ad69d2-6a4e-4172-83a1-a523013dec76',
            'ext': 'mp4',
            'title': 'Ranges for the Standard Library',
            'description': 'md5:9895e0a9fd80822d2f01c454b8f4a372',
            'duration': 5646,
            'thumbnail': r're:https?://.*\.jpg',
            'upload_date': '20150930',
            'timestamp': 1443640735,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://channel9.msdn.com/Events/DEVintersection/DEVintersection-2016/RSS',
        'info_dict': {
            'id': 'Events/DEVintersection/DEVintersection-2016',
            'title': 'DEVintersection 2016 Orlando Sessions',
        },
        'playlist_mincount': 14,
    }, {
        'url': 'https://channel9.msdn.com/Niners/Splendid22/Queue/76acff796e8f411184b008028e0d492b/RSS',
        'only_matching': True,
    }, {
        'url': 'https://channel9.msdn.com/Events/Speakers/scott-hanselman/RSS?UrlSafeName=scott-hanselman',
        'only_matching': True,
    }]

    _RSS_URL = 'http://channel9.msdn.com/%s/RSS'

    @staticmethod
    def _extract_urls(webpage):
        return re.findall(
            r'<iframe[^>]+src=["\'](https?://channel9\.msdn\.com/(?:[^/]+/)+)player\b',
            webpage)

    def _extract_list(self, video_id, rss_url=None):
        if not rss_url:
            rss_url = self._RSS_URL % video_id
        rss = self._download_xml(rss_url, video_id, 'Downloading RSS')
        entries = [self.url_result(session_url.text, 'Channel9')
                   for session_url in rss.findall('./channel/item/link')]
        title_text = rss.find('./channel/title').text
        return self.playlist_result(entries, video_id, title_text)

    def _real_extract(self, url):
        content_path, rss = self._match_valid_url(url).groups()

        if rss:
            return self._extract_list(content_path, url)

        webpage = self._download_webpage(
            url, content_path, 'Downloading web page')

        episode_data = self._search_regex(
            r"data-episode='([^']+)'", webpage, 'episode data', default=None)
        if episode_data:
            episode_data = self._parse_json(unescapeHTML(
                episode_data), content_path)
            content_id = episode_data['contentId']
            is_session = '/Sessions(' in episode_data['api']
            content_url = 'https://channel9.msdn.com/odata' + episode_data['api'] + '?$select=Captions,CommentCount,MediaLengthInSeconds,PublishedDate,Rating,RatingCount,Title,VideoMP4High,VideoMP4Low,VideoMP4Medium,VideoPlayerPreviewImage,VideoWMV,VideoWMVHQ,Views,'
            if is_session:
                content_url += 'Code,Description,Room,Slides,Speakers,ZipFile&$expand=Speakers'
            else:
                content_url += 'Authors,Body&$expand=Authors'
            content_data = self._download_json(content_url, content_id)
            title = content_data['Title']

            QUALITIES = (
                'mp3',
                'wmv', 'mp4',
                'wmv-low', 'mp4-low',
                'wmv-mid', 'mp4-mid',
                'wmv-high', 'mp4-high',
            )

            quality_key = qualities(QUALITIES)

            def quality(quality_id, format_url):
                return (len(QUALITIES) if '_Source.' in format_url
                        else quality_key(quality_id))

            formats = []
            urls = set()

            SITE_QUALITIES = {
                'MP3': 'mp3',
                'MP4': 'mp4',
                'Low Quality WMV': 'wmv-low',
                'Low Quality MP4': 'mp4-low',
                'Mid Quality WMV': 'wmv-mid',
                'Mid Quality MP4': 'mp4-mid',
                'High Quality WMV': 'wmv-high',
                'High Quality MP4': 'mp4-high',
            }

            formats_select = self._search_regex(
                r'(?s)<select[^>]+name=["\']format[^>]+>(.+?)</select', webpage,
                'formats select', default=None)
            if formats_select:
                for mobj in re.finditer(
                        r'<option\b[^>]+\bvalue=(["\'])(?P<url>(?:(?!\1).)+)\1[^>]*>\s*(?P<format>[^<]+?)\s*<',
                        formats_select):
                    format_url = mobj.group('url')
                    if format_url in urls:
                        continue
                    urls.add(format_url)
                    format_id = mobj.group('format')
                    quality_id = SITE_QUALITIES.get(format_id, format_id)
                    formats.append({
                        'url': format_url,
                        'format_id': quality_id,
                        'quality': quality(quality_id, format_url),
                        'vcodec': 'none' if quality_id == 'mp3' else None,
                    })

            API_QUALITIES = {
                'VideoMP4Low': 'mp4-low',
                'VideoWMV': 'wmv-mid',
                'VideoMP4Medium': 'mp4-mid',
                'VideoMP4High': 'mp4-high',
                'VideoWMVHQ': 'wmv-hq',
            }

            for format_id, q in API_QUALITIES.items():
                q_url = content_data.get(format_id)
                if not q_url or q_url in urls:
                    continue
                urls.add(q_url)
                formats.append({
                    'url': q_url,
                    'format_id': q,
                    'quality': quality(q, q_url),
                })

            slides = content_data.get('Slides')
            zip_file = content_data.get('ZipFile')

            if not formats and not slides and not zip_file:
                self.raise_no_formats(
                    'None of recording, slides or zip are available for %s' % content_path)
            self._sort_formats(formats)

            subtitles = {}
            for caption in content_data.get('Captions', []):
                caption_url = caption.get('Url')
                if not caption_url:
                    continue
                subtitles.setdefault(caption.get('Language', 'en'), []).append({
                    'url': caption_url,
                    'ext': 'vtt',
                })

            common = {
                'id': content_id,
                'title': title,
                'description': clean_html(content_data.get('Description') or content_data.get('Body')),
                'thumbnail': content_data.get('VideoPlayerPreviewImage'),
                'duration': int_or_none(content_data.get('MediaLengthInSeconds')),
                'timestamp': parse_iso8601(content_data.get('PublishedDate')),
                'avg_rating': int_or_none(content_data.get('Rating')),
                'rating_count': int_or_none(content_data.get('RatingCount')),
                'view_count': int_or_none(content_data.get('Views')),
                'comment_count': int_or_none(content_data.get('CommentCount')),
                'subtitles': subtitles,
            }
            if is_session:
                speakers = []
                for s in content_data.get('Speakers', []):
                    speaker_name = s.get('FullName')
                    if not speaker_name:
                        continue
                    speakers.append(speaker_name)

                common.update({
                    'session_code': content_data.get('Code'),
                    'session_room': content_data.get('Room'),
                    'session_speakers': speakers,
                })
            else:
                authors = []
                for a in content_data.get('Authors', []):
                    author_name = a.get('DisplayName')
                    if not author_name:
                        continue
                    authors.append(author_name)
                common['authors'] = authors

            contents = []

            if slides:
                d = common.copy()
                d.update({'title': title + '-Slides', 'url': slides})
                contents.append(d)

            if zip_file:
                d = common.copy()
                d.update({'title': title + '-Zip', 'url': zip_file})
                contents.append(d)

            if formats:
                d = common.copy()
                d.update({'title': title, 'formats': formats})
                contents.append(d)
            return self.playlist_result(contents)
        else:
            return self._extract_list(content_path)
