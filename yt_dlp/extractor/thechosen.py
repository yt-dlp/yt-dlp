from .common import InfoExtractor
from .frontro import FrontroGroupBaseIE
from ..utils import (
    determine_ext,
    int_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class TheChosenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?watch\.thechosen\.tv/(?:video|watch)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://watch.thechosen.tv/video/184683594325',
        'md5': '3f878b689588c71b38ec9943c54ff5b0',
        'info_dict': {
            'id': '184683594325',
            'ext': 'mp4',
            'title': 'Season 3 Episode 2: Two by Two',
            'description': 'md5:174c373756ecc8df46b403f4fcfbaf8c',
            'duration': 4212,
            'thumbnail': 'https://cas.global.ssl.fastly.net/hls-10-4/184683594325/thumbnail.png',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://watch.thechosen.tv/video/184683596189',
        'md5': 'd581562f9d29ce82f5b7770415334151',
        'info_dict': {
            'id': '184683596189',
            'ext': 'mp4',
            'title': 'Season 4 Episode 8: Humble',
            'description': 'md5:20a57bead43da1cf77cd5b0fe29bbc76',
            'duration': 5092,
            'thumbnail': 'https://cdn.thechosen.media/videos/cmkvu7nn500nhfm0wpgmm6180/thumbnail.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://watch.thechosen.tv/video/184683621748',
        'info_dict': {
            'id': '184683621748',
            'ext': 'mp4',
            'title': 'Season 5 Episode 2: House of Cards',
            'description': 'md5:55b389cbb4b7a01d8c2d837102905617',
            'duration': 3086,
            'thumbnail': 'https://cdn.thechosen.media/videos/cmkolt4el000afd5zd6x0aeph/thumbnail.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://watch.thechosen.tv/video/184683621750',
        'info_dict': {
            'id': '184683621750',
            'ext': 'mp4',
            'title': 'Season 5 Episode 3:  Woes',
            'description': 'md5:90ca3cc41316a965fd1cd3d5b3458784',
            'duration': 3519,
            'thumbnail': 'https://cdn.thechosen.media/videos/cmkoltsl8000dfd5z3luid3mg/thumbnail.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._download_json(f'https://api.watch.thechosen.tv/v1/videos/{video_id}', video_id)

        formats, subtitles = [], {}
        for fmt_url in traverse_obj(metadata, ('details', 'video', ..., 'url', {url_or_none})):
            ext = determine_ext(fmt_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(fmt_url, video_id, 'mp4', fatal=False)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(fmt_url, video_id, fatal=False)
            else:
                self.report_warning(f'Skipping unsupported format extension "{ext}"', video_id=video_id)
                continue
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        thumbnails = []
        for thumb_id, thumb_url in traverse_obj(metadata, (
            ('thumbs', 'thumbnails'), {dict.items}, lambda _, v: url_or_none(v[1]),
        )):
            thumbnails.append({
                'id': thumb_id,
                'url': thumb_url,
            })

        return {
            'id': video_id,
            **traverse_obj(metadata, ({
                'title': ('title', {str}),
                'description': ('description', {str}),
                'duration': ('duration', {int_or_none}),
            })),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }


class TheChosenGroupIE(FrontroGroupBaseIE):
    _WORKING = False
    _CHANNEL_ID = '12884901895'
    _VIDEO_EXTRACTOR = TheChosenIE
    _VIDEO_URL_TMPL = 'https://watch.thechosen.tv/watch/%s'

    _VALID_URL = r'https?://(?:www\.)?watch\.thechosen\.tv/group/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://watch.thechosen.tv/group/309237658592',
        'info_dict': {
            'id': '309237658592',
            'title': 'Season 3',
            'timestamp': 1746203969,
            'upload_date': '20250502',
            'modified_timestamp': int,
            'modified_date': str,
        },
        'playlist_count': 8,
    }]
