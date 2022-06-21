import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    smuggle_url,
    unsmuggle_url,
    xpath_text,
)


class MicrosoftVirtualAcademyBaseIE(InfoExtractor):
    def _extract_base_url(self, course_id, display_id):
        return self._download_json(
            'https://api-mlxprod.microsoft.com/services/products/anonymous/%s' % course_id,
            display_id, 'Downloading course base URL')

    def _extract_chapter_and_title(self, title):
        if not title:
            return None, None
        m = re.search(r'(?P<chapter>\d+)\s*\|\s*(?P<title>.+)', title)
        return (int(m.group('chapter')), m.group('title')) if m else (None, title)


class MicrosoftVirtualAcademyIE(MicrosoftVirtualAcademyBaseIE):
    IE_NAME = 'mva'
    IE_DESC = 'Microsoft Virtual Academy videos'
    _VALID_URL = r'(?:%s:|https?://(?:mva\.microsoft|(?:www\.)?microsoftvirtualacademy)\.com/[^/]+/training-courses/[^/?#&]+-)(?P<course_id>\d+)(?::|\?l=)(?P<id>[\da-zA-Z]+_\d+)' % IE_NAME

    _TESTS = [{
        'url': 'https://mva.microsoft.com/en-US/training-courses/microsoft-azure-fundamentals-virtual-machines-11788?l=gfVXISmEB_6804984382',
        'md5': '7826c44fc31678b12ad8db11f6b5abb9',
        'info_dict': {
            'id': 'gfVXISmEB_6804984382',
            'ext': 'mp4',
            'title': 'Course Introduction',
            'formats': 'mincount:3',
            'subtitles': {
                'en': [{
                    'ext': 'ttml',
                }],
            },
        }
    }, {
        'url': 'mva:11788:gfVXISmEB_6804984382',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})

        mobj = self._match_valid_url(url)
        course_id = mobj.group('course_id')
        video_id = mobj.group('id')

        base_url = smuggled_data.get('base_url') or self._extract_base_url(course_id, video_id)

        settings = self._download_xml(
            '%s/content/content_%s/videosettings.xml?v=1' % (base_url, video_id),
            video_id, 'Downloading video settings XML')

        _, title = self._extract_chapter_and_title(xpath_text(
            settings, './/Title', 'title', fatal=True))

        formats = []

        for sources in settings.findall('.//MediaSources'):
            sources_type = sources.get('videoType')
            for source in sources.findall('./MediaSource'):
                video_url = source.text
                if not video_url or not video_url.startswith('http'):
                    continue
                if sources_type == 'smoothstreaming':
                    formats.extend(self._extract_ism_formats(
                        video_url, video_id, 'mss', fatal=False))
                    continue
                video_mode = source.get('videoMode')
                height = int_or_none(self._search_regex(
                    r'^(\d+)[pP]$', video_mode or '', 'height', default=None))
                codec = source.get('codec')
                acodec, vcodec = [None] * 2
                if codec:
                    codecs = codec.split(',')
                    if len(codecs) == 2:
                        acodec, vcodec = codecs
                    elif len(codecs) == 1:
                        vcodec = codecs[0]
                formats.append({
                    'url': video_url,
                    'format_id': video_mode,
                    'height': height,
                    'acodec': acodec,
                    'vcodec': vcodec,
                })
        self._sort_formats(formats)

        subtitles = {}
        for source in settings.findall('.//MarkerResourceSource'):
            subtitle_url = source.text
            if not subtitle_url:
                continue
            subtitles.setdefault('en', []).append({
                'url': '%s/%s' % (base_url, subtitle_url),
                'ext': source.get('type'),
            })

        return {
            'id': video_id,
            'title': title,
            'subtitles': subtitles,
            'formats': formats
        }


class MicrosoftVirtualAcademyCourseIE(MicrosoftVirtualAcademyBaseIE):
    IE_NAME = 'mva:course'
    IE_DESC = 'Microsoft Virtual Academy courses'
    _VALID_URL = r'(?:%s:|https?://(?:mva\.microsoft|(?:www\.)?microsoftvirtualacademy)\.com/[^/]+/training-courses/(?P<display_id>[^/?#&]+)-)(?P<id>\d+)' % IE_NAME

    _TESTS = [{
        'url': 'https://mva.microsoft.com/en-US/training-courses/microsoft-azure-fundamentals-virtual-machines-11788',
        'info_dict': {
            'id': '11788',
            'title': 'Microsoft Azure Fundamentals: Virtual Machines',
        },
        'playlist_count': 36,
    }, {
        # with emphasized chapters
        'url': 'https://mva.microsoft.com/en-US/training-courses/developing-windows-10-games-with-construct-2-16335',
        'info_dict': {
            'id': '16335',
            'title': 'Developing Windows 10 Games with Construct 2',
        },
        'playlist_count': 10,
    }, {
        'url': 'https://www.microsoftvirtualacademy.com/en-US/training-courses/microsoft-azure-fundamentals-virtual-machines-11788',
        'only_matching': True,
    }, {
        'url': 'mva:course:11788',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if MicrosoftVirtualAcademyIE.suitable(url) else super(
            MicrosoftVirtualAcademyCourseIE, cls).suitable(url)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        course_id = mobj.group('id')
        display_id = mobj.group('display_id')

        base_url = self._extract_base_url(course_id, display_id)

        manifest = self._download_json(
            '%s/imsmanifestlite.json' % base_url,
            display_id, 'Downloading course manifest JSON')['manifest']

        organization = manifest['organizations']['organization'][0]

        entries = []
        for chapter in organization['item']:
            chapter_number, chapter_title = self._extract_chapter_and_title(chapter.get('title'))
            chapter_id = chapter.get('@identifier')
            for item in chapter.get('item', []):
                item_id = item.get('@identifier')
                if not item_id:
                    continue
                metadata = item.get('resource', {}).get('metadata') or {}
                if metadata.get('learningresourcetype') != 'Video':
                    continue
                _, title = self._extract_chapter_and_title(item.get('title'))
                duration = parse_duration(metadata.get('duration'))
                description = metadata.get('description')
                entries.append({
                    '_type': 'url_transparent',
                    'url': smuggle_url(
                        'mva:%s:%s' % (course_id, item_id), {'base_url': base_url}),
                    'title': title,
                    'description': description,
                    'duration': duration,
                    'chapter': chapter_title,
                    'chapter_number': chapter_number,
                    'chapter_id': chapter_id,
                })

        title = organization.get('title') or manifest.get('metadata', {}).get('title')

        return self.playlist_result(entries, course_id, title)
