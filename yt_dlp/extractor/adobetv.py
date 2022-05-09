import functools
import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    float_or_none,
    int_or_none,
    ISO639Utils,
    join_nonempty,
    OnDemandPagedList,
    parse_duration,
    str_or_none,
    str_to_int,
    unified_strdate,
)


class AdobeTVBaseIE(InfoExtractor):
    def _call_api(self, path, video_id, query, note=None):
        return self._download_json(
            'http://tv.adobe.com/api/v4/' + path,
            video_id, note, query=query)['data']

    def _parse_subtitles(self, video_data, url_key):
        subtitles = {}
        for translation in video_data.get('translations', []):
            vtt_path = translation.get(url_key)
            if not vtt_path:
                continue
            lang = translation.get('language_w3c') or ISO639Utils.long2short(translation['language_medium'])
            subtitles.setdefault(lang, []).append({
                'ext': 'vtt',
                'url': vtt_path,
            })
        return subtitles

    def _parse_video_data(self, video_data):
        video_id = compat_str(video_data['id'])
        title = video_data['title']

        s3_extracted = False
        formats = []
        for source in video_data.get('videos', []):
            source_url = source.get('url')
            if not source_url:
                continue
            f = {
                'format_id': source.get('quality_level'),
                'fps': int_or_none(source.get('frame_rate')),
                'height': int_or_none(source.get('height')),
                'tbr': int_or_none(source.get('video_data_rate')),
                'width': int_or_none(source.get('width')),
                'url': source_url,
            }
            original_filename = source.get('original_filename')
            if original_filename:
                if not (f.get('height') and f.get('width')):
                    mobj = re.search(r'_(\d+)x(\d+)', original_filename)
                    if mobj:
                        f.update({
                            'height': int(mobj.group(2)),
                            'width': int(mobj.group(1)),
                        })
                if original_filename.startswith('s3://') and not s3_extracted:
                    formats.append({
                        'format_id': 'original',
                        'quality': 1,
                        'url': original_filename.replace('s3://', 'https://s3.amazonaws.com/'),
                    })
                    s3_extracted = True
            formats.append(f)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'thumbnail': video_data.get('thumbnail'),
            'upload_date': unified_strdate(video_data.get('start_date')),
            'duration': parse_duration(video_data.get('duration')),
            'view_count': str_to_int(video_data.get('playcount')),
            'formats': formats,
            'subtitles': self._parse_subtitles(video_data, 'vtt'),
        }


class AdobeTVEmbedIE(AdobeTVBaseIE):
    IE_NAME = 'adobetv:embed'
    _VALID_URL = r'https?://tv\.adobe\.com/embed/\d+/(?P<id>\d+)'
    _TEST = {
        'url': 'https://tv.adobe.com/embed/22/4153',
        'md5': 'c8c0461bf04d54574fc2b4d07ac6783a',
        'info_dict': {
            'id': '4153',
            'ext': 'flv',
            'title': 'Creating Graphics Optimized for BlackBerry',
            'description': 'md5:eac6e8dced38bdaae51cd94447927459',
            'thumbnail': r're:https?://.*\.jpg$',
            'upload_date': '20091109',
            'duration': 377,
            'view_count': int,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_data = self._call_api(
            'episode/' + video_id, video_id, {'disclosure': 'standard'})[0]
        return self._parse_video_data(video_data)


class AdobeTVIE(AdobeTVBaseIE):
    IE_NAME = 'adobetv'
    _VALID_URL = r'https?://tv\.adobe\.com/(?:(?P<language>fr|de|es|jp)/)?watch/(?P<show_urlname>[^/]+)/(?P<id>[^/]+)'

    _TEST = {
        'url': 'http://tv.adobe.com/watch/the-complete-picture-with-julieanne-kost/quick-tip-how-to-draw-a-circle-around-an-object-in-photoshop/',
        'md5': '9bc5727bcdd55251f35ad311ca74fa1e',
        'info_dict': {
            'id': '10981',
            'ext': 'mp4',
            'title': 'Quick Tip - How to Draw a Circle Around an Object in Photoshop',
            'description': 'md5:99ec318dc909d7ba2a1f2b038f7d2311',
            'thumbnail': r're:https?://.*\.jpg$',
            'upload_date': '20110914',
            'duration': 60,
            'view_count': int,
        },
    }

    def _real_extract(self, url):
        language, show_urlname, urlname = self._match_valid_url(url).groups()
        if not language:
            language = 'en'

        video_data = self._call_api(
            'episode/get', urlname, {
                'disclosure': 'standard',
                'language': language,
                'show_urlname': show_urlname,
                'urlname': urlname,
            })[0]
        return self._parse_video_data(video_data)


class AdobeTVPlaylistBaseIE(AdobeTVBaseIE):
    _PAGE_SIZE = 25

    def _fetch_page(self, display_id, query, page):
        page += 1
        query['page'] = page
        for element_data in self._call_api(
                self._RESOURCE, display_id, query, 'Download Page %d' % page):
            yield self._process_data(element_data)

    def _extract_playlist_entries(self, display_id, query):
        return OnDemandPagedList(functools.partial(
            self._fetch_page, display_id, query), self._PAGE_SIZE)


class AdobeTVShowIE(AdobeTVPlaylistBaseIE):
    IE_NAME = 'adobetv:show'
    _VALID_URL = r'https?://tv\.adobe\.com/(?:(?P<language>fr|de|es|jp)/)?show/(?P<id>[^/]+)'

    _TEST = {
        'url': 'http://tv.adobe.com/show/the-complete-picture-with-julieanne-kost',
        'info_dict': {
            'id': '36',
            'title': 'The Complete Picture with Julieanne Kost',
            'description': 'md5:fa50867102dcd1aa0ddf2ab039311b27',
        },
        'playlist_mincount': 136,
    }
    _RESOURCE = 'episode'
    _process_data = AdobeTVBaseIE._parse_video_data

    def _real_extract(self, url):
        language, show_urlname = self._match_valid_url(url).groups()
        if not language:
            language = 'en'
        query = {
            'disclosure': 'standard',
            'language': language,
            'show_urlname': show_urlname,
        }

        show_data = self._call_api(
            'show/get', show_urlname, query)[0]

        return self.playlist_result(
            self._extract_playlist_entries(show_urlname, query),
            str_or_none(show_data.get('id')),
            show_data.get('show_name'),
            show_data.get('show_description'))


class AdobeTVChannelIE(AdobeTVPlaylistBaseIE):
    IE_NAME = 'adobetv:channel'
    _VALID_URL = r'https?://tv\.adobe\.com/(?:(?P<language>fr|de|es|jp)/)?channel/(?P<id>[^/]+)(?:/(?P<category_urlname>[^/]+))?'

    _TEST = {
        'url': 'http://tv.adobe.com/channel/development',
        'info_dict': {
            'id': 'development',
        },
        'playlist_mincount': 96,
    }
    _RESOURCE = 'show'

    def _process_data(self, show_data):
        return self.url_result(
            show_data['url'], 'AdobeTVShow', str_or_none(show_data.get('id')))

    def _real_extract(self, url):
        language, channel_urlname, category_urlname = self._match_valid_url(url).groups()
        if not language:
            language = 'en'
        query = {
            'channel_urlname': channel_urlname,
            'language': language,
        }
        if category_urlname:
            query['category_urlname'] = category_urlname

        return self.playlist_result(
            self._extract_playlist_entries(channel_urlname, query),
            channel_urlname)


class AdobeTVVideoIE(AdobeTVBaseIE):
    IE_NAME = 'adobetv:video'
    _VALID_URL = r'https?://video\.tv\.adobe\.com/v/(?P<id>\d+)'

    _TEST = {
        # From https://helpx.adobe.com/acrobat/how-to/new-experience-acrobat-dc.html?set=acrobat--get-started--essential-beginners
        'url': 'https://video.tv.adobe.com/v/2456/',
        'md5': '43662b577c018ad707a63766462b1e87',
        'info_dict': {
            'id': '2456',
            'ext': 'mp4',
            'title': 'New experience with Acrobat DC',
            'description': 'New experience with Acrobat DC',
            'duration': 248.667,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_data = self._parse_json(self._search_regex(
            r'var\s+bridge\s*=\s*([^;]+);', webpage, 'bridged data'), video_id)
        title = video_data['title']

        formats = []
        sources = video_data.get('sources') or []
        for source in sources:
            source_src = source.get('src')
            if not source_src:
                continue
            formats.append({
                'filesize': int_or_none(source.get('kilobytes') or None, invscale=1000),
                'format_id': join_nonempty(source.get('format'), source.get('label')),
                'height': int_or_none(source.get('height') or None),
                'tbr': int_or_none(source.get('bitrate') or None),
                'width': int_or_none(source.get('width') or None),
                'url': source_src,
            })
        self._sort_formats(formats)

        # For both metadata and downloaded files the duration varies among
        # formats. I just pick the max one
        duration = max(filter(None, [
            float_or_none(source.get('duration'), scale=1000)
            for source in sources]))

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': video_data.get('description'),
            'thumbnail': video_data.get('video', {}).get('poster'),
            'duration': duration,
            'subtitles': self._parse_subtitles(video_data, 'vttPath'),
        }
