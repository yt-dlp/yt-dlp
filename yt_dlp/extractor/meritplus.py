from .common import InfoExtractor
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    traverse_obj,
    url_or_none,
)


class MeritPlusIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[\w-]+\.)?meritplus\.com/(?:c/)?(?P<type>[a-z]+)/(?P<ep>[^/]+\?episodeId=)?(?P<id>[^/&\?]+)'
    _TESTS = [{
        'url': 'https://www.meritplus.com/c/s/VQ2aB6Sp?episodeId=uNLp2Rgg&play=1',
        'info_dict': {
            'id': 'uNLp2Rgg',
            'ext': 'mp4',
            'title': 'Right to Stand Your Ground | Dr. Phil Primetime',
            'description': r're:^Employees who fought back against robbers, unruly customers, and',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/uNLp2Rgg/poster.jpg?width=1920',
            'duration': 2519.0,
            'tags': 'count:14',
            'timestamp': 1724716800,
            'upload_date': '20240827',
            'series': 'Dr. Phil Primetime',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 79',
            'episode_number': 79,
        },
    }, {
        'url': 'https://www.meritplus.com/c/m/ebVUK1wS?r=ok5bikOE',
        'info_dict': {
            'id': 'ebVUK1wS',
            'ext': 'mp4',
            'title': 'PBR Teams 2024: Gambler Days | Day 1',
            'description': r're:^Get ready for Gambler Days with the PBR! Watch elite riders battle',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/ebVUK1wS/poster.jpg?width=1920',
            'duration': 10876.0,
            'tags': 'count:7',
            'timestamp': 1724461200,
            'upload_date': '20240824',
        },
    }, {
        'url': 'https://www.meritplus.com/m/AzVJ4sEH/bull-rider-najiah-knight-the-cowgirl-way?r=uzD8QNRj',
        'info_dict': {
            'id': 'AzVJ4sEH',
            'ext': 'mp4',
            'title': 'Bull Rider Najiah Knight | The Cowgirl Way',
            'description': r're:^Najiah Knight is rewriting the rules and inspiring future Cowgirls',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/AzVJ4sEH/poster.jpg?width=1920',
            'duration': 300.0,
            'tags': ['The Cowgirl Way', 'seriesId_uzD8QNRj', 'PBR'],
            'timestamp': 1720195320,
            'upload_date': '20240705',
        },
    }, {
        'url': 'https://www.meritplus.com/c/sns/jryHEWXj',
        'info_dict': {
            'id': 'jryHEWXj',
            'title': 'Morning on Merit Street',
            'description': r're:^Award winning journalist Dominique Sachse and co-host Fanchon Stinger',
            'thumbnail': 'https://assets.mediabackstage.com/merit_prod/thumbnails/moms_thumbnail_1920x1080-1708708358462.jpg',
        },
        'playlist_count': 5,
    }, {
        'url': 'https://www.meritplus.com/c/s/eAzd5bqW',
        'info_dict': {
            'id': 'eAzd5bqW',
            'title': 'Crime Stories with Nancy Grace',
            'description': r're:^Nancy Grace explores the inside story of true crimes and cold cases',
            'thumbnail': 'https://assets.mediabackstage.com/merit_prod%2Fthumbnails%2Fnancygrace_thumbnail_1920x1080-1721658217049.jpg',
        },
        'playlist_count': 15,
    }]

    def _real_extract(self, url):
        video_id, c_type, is_episode = self._match_valid_url(url).group('id', 'type', 'ep')
        if is_episode or c_type == 'm':
            json = self._download_json(f'https://cdn.jwplayer.com/v2/media/{video_id}', video_id)
        else:
            json = self._download_json(f'https://cdn.jwplayer.com/v2/playlists/{video_id}?format=json&page_limit=500', video_id)

        entries = []
        for video in json.get('playlist', []):
            thumbnails, formats, subtitles = [], [], {}
            for image in video.get('images', []):
                thumbnails.append({
                    'url': url_or_none(image.get('src')),
                    'width': image.get('width'),
                })
            for caption in video.get('tracks', []):
                if caption.get('kind') == 'captions':
                    subtitles.setdefault(caption.get('label', 'und'), []).append({
                        'url': caption.get('file'),
                        'name': caption.get('label'),
                    })
            for source in video.get('sources', []):
                if media_url := url_or_none(source.get('file')):
                    if determine_ext(media_url) == 'm3u8':
                        hls_fmts, hls_subs = self._extract_m3u8_formats_and_subtitles(
                            media_url, video['mediaid'], fatal=None)
                        formats.extend(hls_fmts)
                        self._merge_subtitles(hls_subs, target=subtitles)
                    else:
                        formats.append(traverse_obj(source, {
                            'format_id': ('label', {lambda v: 'audio' if 'Audio' in v else v}),
                            'url': ('file', {str}),
                            'height': ('height', {int_or_none}),
                            'width': ('width', {int_or_none}),
                            'filesize': ('filesize', {int}),
                            'fps': ('framerate', {float_or_none}),
                            'tbr': ('bitrate', {lambda v: int_or_none(v, 1000)}),
                            'acodec': ('label', {lambda v: 'aac' if 'AAC' in v else None}),
                            'vcodec': ('type', {lambda v: 'none' if 'audio' in v else None}),
                        }))

            entries.append({**traverse_obj(video, {
                'id': ('mediaid', {str}),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': ('pubdate', {int}),
                'tags': ('tags', {lambda v: v.split(',') if v else None}),
                'series': ('programName', {lambda v: v or None}),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'cast': ('cast', {lambda v: v.split(',') if v else None}),
                'duration': ('duration', {float_or_none}),
                'is_live': ('is_live', {lambda v: bool(v)}),
                'webpage_url': ('mediaid', {lambda v: url + (f'?episodeId={v}' if v not in url else '')}),
                'thumbnail': ('image', {lambda v: url_or_none(v) if not thumbnails else None}),
            }),
                'thumbnails': thumbnails,
                'formats': formats,
                'subtitles': subtitles,
            })

        if len(entries) == 1:
            return entries[0]
        elif len(entries) > 1:
            description = join_nonempty('shortDescription', 'description', delim=' ', from_dict=json)
            thumbnail = traverse_obj(json, (('imgHomeRailThumb16x9', 'imgFeaturedTvBanner16x9'),
                                            {url_or_none}), get_all=False)
            return self.playlist_result(entries, id=json['seriesId'], title=json['title'],
                                        description=description, thumbnail=thumbnail)
        else:
            self.raise_no_formats('No video formats found!')
