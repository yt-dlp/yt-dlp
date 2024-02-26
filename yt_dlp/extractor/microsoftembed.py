import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class MicrosoftEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?microsoft\.com/(?:[^/]+/)?videoplayer/embed/(?P<id>[a-z0-9A-Z]+)'

    _TESTS = [{
        'url': 'https://www.microsoft.com/en-us/videoplayer/embed/RWL07e',
        'md5': 'eb0ae9007f9b305f9acd0a03e74cb1a9',
        'info_dict': {
            'id': 'RWL07e',
            'title': 'Microsoft for Public Health and Social Services',
            'ext': 'mp4',
            'thumbnail': 'http://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RWL7Ju?ver=cae5',
            'age_limit': 0,
            'timestamp': 1631658316,
            'upload_date': '20210914'
        }
    }]
    _API_URL = 'https://prod-video-cms-rt-microsoft-com.akamaized.net/vhs/api/videos/'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._download_json(self._API_URL + video_id, video_id)

        formats = []
        for source_type, source in metadata['streams'].items():
            if source_type == 'smooth_Streaming':
                formats.extend(self._extract_ism_formats(source['url'], video_id, 'mss'))
            elif source_type == 'apple_HTTP_Live_Streaming':
                formats.extend(self._extract_m3u8_formats(source['url'], video_id, 'mp4'))
            elif source_type == 'mPEG_DASH':
                formats.extend(self._extract_mpd_formats(source['url'], video_id))
            else:
                formats.append({
                    'format_id': source_type,
                    'url': source['url'],
                    'height': source.get('heightPixels'),
                    'width': source.get('widthPixels'),
                })

        subtitles = {
            lang: [{
                'url': data.get('url'),
                'ext': 'vtt',
            }] for lang, data in traverse_obj(metadata, 'captions', default={}).items()
        }

        thumbnails = [{
            'url': thumb.get('url'),
            'width': thumb.get('width') or None,
            'height': thumb.get('height') or None,
        } for thumb in traverse_obj(metadata, ('snippet', 'thumbnails', ...))]
        self._remove_duplicate_formats(thumbnails)

        return {
            'id': video_id,
            'title': traverse_obj(metadata, ('snippet', 'title')),
            'timestamp': unified_timestamp(traverse_obj(metadata, ('snippet', 'activeStartDate'))),
            'age_limit': int_or_none(traverse_obj(metadata, ('snippet', 'minimumAge'))) or 0,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
        }


class MicrosoftMediusBaseIE(InfoExtractor):
    @staticmethod
    def _sub_to_dict(subtitle_list):
        subtitles = {}
        for sub in subtitle_list:
            subtitles.setdefault(sub.pop('tag', None) or 'unknown', []).append(sub)
        return subtitles

    def _extract_ism(self, ism_url, video_id):
        formats = self._extract_ism_formats(ism_url, video_id)
        for format in formats:
            if format.get('language') == 'eng' or 'English' in format.get('format_id', ''):
                format['language_preference'] = -1
            else:
                format['language_preference'] = -10
        return formats


class MicrosoftMediusIE(MicrosoftMediusBaseIE):
    _VALID_URL = r'https?://medius\.microsoft\.com/[^?#]+/(?P<id>[0-9a-f\-]+)'

    _TESTS = [{
        'url': 'https://medius.microsoft.com/Embed/video-nc/9640d86c-f513-4889-959e-5dace86e7d2b',
        'info_dict': {
            'id': '9640d86c-f513-4889-959e-5dace86e7d2b',
            'ext': 'ismv',
            'title': 'Rapidly code, test and ship from secure cloud developer environments',
            'description': 'md5:33c8e4facadc438613476eea24165f71',
            'thumbnail': r're:https://mediusimg\.event\.microsoft\.com/video-\d+/thumbnail\.jpg.*',
            'subtitles': 'count:30',
        },
        'params': {'listsubtitles': True},
    }, {
        'url': 'https://medius.microsoft.com/Embed/video-nc/81215af5-c813-4dcd-aede-94f4e1a7daa3',
        'info_dict': {
            'id': '81215af5-c813-4dcd-aede-94f4e1a7daa3',
            'ext': 'ismv',
            'title': 'Microsoft Build opening',
            'description': 'md5:43455096141077a1f23144cab8cec1cb',
            'thumbnail': r're:https://mediusimg\.event\.microsoft\.com/video-\d+/thumbnail\.jpg.*',
            'subtitles': 'count:31',
        },
        'params': {'listsubtitles': True},
    }]

    def _extract_subtitle(self, webpage, video_id):
        captions = traverse_obj(
            self._search_json(r'const\s+captionsConfiguration\s*=\s*', webpage, 'captions', video_id, default=False),
            ('languageList', ..., {
                'url': ('src', {url_or_none}),
                'tag': ('srclang', {str}),
                'name': ('kind', {str}),
            }))

        captions = captions or traverse_obj(
            re.findall(r'var\s+file\s+=\s+\{[^}]+\'(https://[^\']+\.vtt\?[^\']+)', webpage),
            (lambda _, v: url_or_none(v), {lambda x: {'url': x, 'tag': x.split('.vtt?')[0].split('_')[-1]}}))

        return self._sub_to_dict(captions)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        ism_url = self._search_regex(r'StreamUrl\s*=\s*"([^"]+manifest)"', webpage, 'ism url')

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'formats': self._extract_ism(ism_url, video_id),
            'thumbnail': self._og_search_thumbnail(webpage),
            'subtitles': self._extract_subtitle(webpage, video_id),
        }


class MicrosoftLearnIE(MicrosoftMediusBaseIE):
    _VALID_URL = r'https?://learn\.microsoft\.com/(?:[\w\-]+/)?(?P<type>events|shows)/(?P<series>[\w\-]+)(?:/(?P<id>[^?#/]+))?'

    _TESTS = [{
        'url': 'https://learn.microsoft.com/en-us/events/build-2022/ts01-rapidly-code-test-ship-from-secure-cloud-developer-environments',
        'info_dict': {
            'id': '9640d86c-f513-4889-959e-5dace86e7d2b',
            'ext': 'ismv',
            'title': 'Rapidly code, test and ship from secure cloud developer environments - Events',
            'description': 'md5:f26c1a85d41c1cffd27a0279254a25c3',
            'timestamp': 1653408600,
            'upload_date': '20220524',
            'thumbnail': r're:https://mediusimg\.event\.microsoft\.com/video-\d+/thumbnail\.jpg.*',
        },
    }, {
        'url': 'https://learn.microsoft.com/en-us/events/build-2022',
        'info_dict': {
            'id': 'build-2022',
            'title': 'Microsoft Build 2022 - Events',
            'description': 'md5:c16b43848027df837b22c6fbac7648d3',
        },
        'playlist_count': 201,
    }, {
        'url': 'https://learn.microsoft.com/en-us/shows/bash-for-beginners/what-is-the-difference-between-a-terminal-and-a-shell-2-of-20-bash-for-beginners/',
        'info_dict': {
            'id': 'd44e1a03-a0e5-45c2-9496-5c9fa08dc94c',
            'ext': 'ismv',
            'title': 'What is the Difference Between a Terminal and a Shell? (Part 2 of 20)',
            'description': 'md5:7bbbfb593d21c2cf2babc3715ade6b88',
            'timestamp': 1676339547,
            'upload_date': '20230214',
            'thumbnail': r're:https://learn\.microsoft\.com/video/media/.*\.png',
            'subtitles': 'count:14',
        },
        'params': {'listsubtitles': True},
    }, {
        'url': 'https://learn.microsoft.com/en-us/shows/bash-for-beginners',
        'info_dict': {
            'id': 'bash-for-beginners',
            'title': 'Bash for Beginners',
            'description': 'md5:16a91c07222117d1e00912f0dbc02c2c',
        },
        'playlist_count': 20,
    }]

    def _entries(self, url_base, video_id):
        skip = 0
        while True:
            playlist_info = self._download_json(url_base, video_id, f'Downloading entries {skip}', query={
                'locale': 'en-us',
                '$skip': skip,
            })
            items = traverse_obj(playlist_info, (
                'results', ..., 'url', {lambda x: self.url_result(f'https://learn.microsoft.com/en-us{x}')}))
            yield from items
            skip += len(items)
            if skip >= playlist_info['count'] or not items:
                break

    def _real_extract(self, url):
        video_type, series, slug = self._match_valid_url(url).groups()
        video_id = slug or series
        webpage = self._download_webpage(url, video_id)

        metainfo = {
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
        }

        if not slug:
            url_base = f'https://learn.microsoft.com/api/contentbrowser/search/{video_type}/{series}/{"sessions" if video_type == "events" else "episodes"}'
            return self.playlist_result(self._entries(url_base, video_id), video_id, **metainfo)

        if video_type == 'events':
            return self.url_result(
                self._search_regex(r'<meta\s+name="externalVideoUrl"\s+content="([^"]+)"', webpage, 'videoUrl'), url_transparent=True, **metainfo, **{
                    'timestamp': parse_iso8601(self._search_regex(
                        r'<meta\s+name="startDate"\s+content="([^"]+)"', webpage, 'date', default=None)),
                })

        entry_id = self._search_regex(r'<meta name="entryId" content="([^"]+)"', webpage, 'entryId')
        video_info = self._download_json(
            f'https://learn.microsoft.com/api/video/public/v1/entries/{entry_id}', video_id)
        return {
            'id': entry_id,
            'formats': self._extract_ism(video_info['publicVideo']['adaptiveVideoUrl'], video_id),
            'subtitles': self._sub_to_dict(traverse_obj(video_info, ('publicVideo', 'captions', ..., {
                'tag': ('language', {str}),
                'url': ('url', {url_or_none}),
            }))),
            **metainfo,
            **traverse_obj(video_info, {
                'timestamp': ('createTime', {parse_iso8601}),
                'thumbnails': ('publicVideo', 'thumbnailOtherSizes', ..., {lambda x: {'url': x}}),
            }),
        }


class MicrosoftBuildIE(MicrosoftMediusBaseIE):
    _VALID_URL = [
        r'https?://build\.microsoft\.com/[\w\-]+/sessions/(?P<id>[0-9a-f\-]+)',
        r'https?://build\.microsoft\.com/[\w\-]+/(?P<id>sessions)/?(?:[?#]|$)',
    ]

    _TESTS = [{
        'url': 'https://build.microsoft.com/en-US/sessions/49e81029-20f0-485b-b641-73b7f9622656?source=sessions',
        'info_dict': {
            'id': '81215af5-c813-4dcd-aede-94f4e1a7daa3',
            'ext': 'ismv',
            'title': 'Microsoft Build opening',
            'description': 'md5:756ab1fb60bdc6923d627803694e9cc5',
            'timestamp': 1684857600,
            'upload_date': '20230523',
            'thumbnail': r're:https://mediusimg\.event\.microsoft\.com/video-\d+/thumbnail\.jpg.*',
        },
    }, {
        'url': 'https://build.microsoft.com/en-US/sessions',
        'info_dict': {
            'id': 'sessions',
        },
        'playlist_mincount': 418,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        entries = [
            self.url_result(video_info['onDemand'], url_transparent=True, **traverse_obj(video_info, {
                'id': ('sessionId', {str}),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': ('startDateTime', {parse_iso8601}),
            }))
            for video_info in self._download_json(
                'https://api.build.microsoft.com/api/session/all/en-US', video_id, 'Downloading video info')
        ]
        if video_id == 'sessions':
            return self.playlist_result(entries, video_id)
        else:
            return traverse_obj(entries, (lambda _, v: v['id'] == video_id), get_all=False)
