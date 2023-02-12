from .common import InfoExtractor
from ..utils import traverse_obj, url_or_none, int_or_none, unified_timestamp, float_or_none

_HANIME_BASE_URL: str = "https://hanime.tv"
_CDN_BASE_URL: str = "https://m3u8s.highwinds-cdn.com/api/v9/m3u8s"


class HanimeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hanime\.tv/videos/hentai/(?P<id>[a-z-0-9]+)'
    _TESTS = [{
        'url': f'{_HANIME_BASE_URL}/videos/hentai/jewelry-1',
        'md5': 'b04594683cc4e334abfcc664294756b0',
        'info_dict': {
            'id': 'jewelry-1',
            'ext': 'm3u8',
            'title': 'Jewelry 1',
            'age_limit': 18,
            'thumbnail': "https://git-posters.pages.dev/images/jewelry-1-xgDqYIRFqN.jpg",
            'description': 'Eating a meal together, cozy and warm, legs under the kotatsu… '
                           'Whether we’re angry or laughing or just zoning out and watching TV… '
                           'Even the silly little things… Our love is so precious. I wouldn’t '
                           'change a thing.\n\nA loving couple is the world’s greatest treasure.',
            'uploader': 'Bootleg',
            'uploader_id': 7,
            'timestamp': 1516440389,
            'upload_date': '20180120',
            'release_timestamp': 1515078000,
            'release_date': '20180104',
            'uploader_url': f'{_HANIME_BASE_URL}/browse/brands/bootleg',
            'duration': 1005.461,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'webpage_url': f'{_HANIME_BASE_URL}/videos/hentai/jewelry-1',
            'tags': ['creampie', 'vanilla', 'uncensored', 'hd', 'facial', 'blow job'],
            'availability': 'public',
            'formats': [
                {
                    'url': f'{_CDN_BASE_URL}/mhb33v3jdA28hrh5t23pgnAt07Zvt6qmxf2602v61yzgt5hms6bcq.m3u8',
                    'width': 640,
                    'height': 360,
                    'format_id': 'cf-hls-1718-jewelry-1-v1x-360',
                    'filesize_approx': 33554432,
                }, {
                    'url': f'{_CDN_BASE_URL}/j432dj885r55mb2gy14Ak90g03Ztl6hrfl4h0q3tnh4hwrfnt628m.m3u8',
                    'width': 854,
                    'height': 480,
                    'format_id': 'cf-hls-1718-jewelry-1-v1x-480',
                    'filesize_approx': 41943040,
                }, {
                    'url': f'{_CDN_BASE_URL}/6kj5r809cpzxxb7d7bdp37cqqmZhsy66q2vf2qvjjfxlh3m0ht1x1.m3u8',
                    'width': 1280,
                    'height': 720,
                    'format_id': 'cf-hls-1718-jewelry-1-v1x-720',
                    'filesize_approx': 85983232,
                }
            ]
        }
    }]

    @staticmethod
    def _get_description(_meta: dict) -> str | None:
        if description := traverse_obj(_meta, ('hentai_video', 'description'), expected_type=str):
            return description.replace('<p>', '').replace('</p>', '')

    @staticmethod
    def _get_uploader_url(_meta: dict) -> str | None:
        if brand_slug := traverse_obj(_meta, ('brand', 'slug'), expected_type=str):
            return f'{_HANIME_BASE_URL}/browse/brands/{brand_slug}'

    @staticmethod
    def _get_tags(_meta: dict) -> list[str] | None:
        if tags := traverse_obj(_meta, ('hentai_video', 'hentai_tags'), expected_type=list):
            return [tag.get('text') for tag in tags if tag.get('text')]

    @staticmethod
    def _get_formats(_streams: list[dict]) -> list[dict] | None:
        return [dict(
            url=stream.get('url'),
            width=int(stream.get('width')),
            height=int(stream.get('height')),
            format_id=stream.get('slug'),
            filesize_approx=int(stream.get('filesize_mbs', 0) * 1024 ** 2)
        ) for stream in _streams if stream.get('is_guest_allowed')]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        meta: dict = self._download_json(f'{_HANIME_BASE_URL}/api/v8/video?id={video_id}', video_id=video_id)
        streams: list = traverse_obj(meta, ('videos_manifest', 'servers', 0, 'streams'), expected_type=list, default=[])

        return dict(
            id=video_id,
            title=traverse_obj(meta, ('hentai_video', 'name'), expected_type=str),
            age_limit=18,
            thumbnail=traverse_obj(meta, ('hentai_video', 'poster_url'), expected_type=url_or_none),
            description=HanimeIE._get_description(meta),
            duration=float_or_none(streams[0].get('duration_in_ms'), scale=1000),
            uploader=traverse_obj(meta, ('brand', 'title'), expected_type=str),
            uploader_id=traverse_obj(meta, ('brand', 'id'), expected_type=int),
            uploader_url=url_or_none(HanimeIE._get_uploader_url(meta)),
            timestamp=unified_timestamp(traverse_obj(meta, ('hentai_video', 'created_at'), expected_type=str)),
            release_timestamp=unified_timestamp(traverse_obj(meta, ('hentai_video', 'released_at'), expected_type=str)),
            view_count=traverse_obj(meta, ('hentai_video', 'views'), expected_type=int_or_none),
            like_count=traverse_obj(meta, ('hentai_video', 'likes'), expected_type=int_or_none),
            dislike_count=traverse_obj(meta, ('hentai_video', 'dislikes'), expected_type=int_or_none),
            webpage_url=url,
            tags=HanimeIE._get_tags(meta),
            availability='public',
            formats=HanimeIE._get_formats(streams),
        )
