# coding: utf-8

from ..utils import (
    ExtractorError,
    int_or_none,
    traverse_obj,
    qualities,
    url_or_none,
)
from .common import (
    InfoExtractor,
    compat_urllib_parse_unquote,
)


class DouyinIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?douyin\.com/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.douyin.com/video/6961737553342991651',
        'md5': '10523312c8b8100f353620ac9dc8f067',
        'info_dict': {
            'id': '6961737553342991651',
            'ext': 'mp4',
            'title': '#杨超越  小小水手带你去远航❤️',
            'uploader': '杨超越',
            'upload_date': '20210513',
            'timestamp': 1620905839,
            'uploader_id': '110403406559',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://www.douyin.com/video/6982497745948921092',
        'md5': 'd78408c984b9b5102904cf6b6bc2d712',
        'info_dict': {
            'id': '6982497745948921092',
            'ext': 'mp4',
            'title': '这个夏日和小羊@杨超越 一起遇见白色幻想',
            'uploader': '杨超越工作室',
            'upload_date': '20210708',
            'timestamp': 1625739481,
            'uploader_id': '408654318141572',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://www.douyin.com/video/6953975910773099811',
        'md5': '72e882e24f75064c218b76c8b713c185',
        'info_dict': {
            'id': '6953975910773099811',
            'ext': 'mp4',
            'title': '#一起看海  出现在你的夏日里',
            'uploader': '杨超越',
            'upload_date': '20210422',
            'timestamp': 1619098692,
            'uploader_id': '110403406559',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://www.douyin.com/video/6950251282489675042',
        'md5': 'b4db86aec367ef810ddd38b1737d2fed',
        'info_dict': {
            'id': '6950251282489675042',
            'ext': 'mp4',
            'title': '哈哈哈，成功了哈哈哈哈哈哈',
            'uploader': '杨超越',
            'upload_date': '20210412',
            'timestamp': 1618231483,
            'uploader_id': '110403406559',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'https://www.douyin.com/video/6963263655114722595',
        'md5': '1abe1c477d05ee62efb40bf2329957cf',
        'info_dict': {
            'id': '6963263655114722595',
            'ext': 'mp4',
            'title': '#哪个爱豆的105度最甜 换个角度看看我哈哈',
            'uploader': '杨超越',
            'upload_date': '20210517',
            'timestamp': 1621261163,
            'uploader_id': '110403406559',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'comment_count': int,
        }
    }]
    _APP_VERSION = '9.6.0'
    _MANIFEST_APP_VERSION = '960'
    QUALITIES = ('360p', '540p', '720p')

    def _extract_aweme(self, aweme_id):
        query = {
            'aweme_id': aweme_id,
            'version_name': self._APP_VERSION,
            'version_code': self._MANIFEST_APP_VERSION,
            'build_number': self._APP_VERSION,
            'manifest_version_code': self._MANIFEST_APP_VERSION,
            'update_version_code': self._MANIFEST_APP_VERSION,
            'openudid': ''.join(random.choice('0123456789abcdef') for i in range(16)),
            'uuid': ''.join([random.choice(string.digits) for num in range(16)]),
            '_rticket': int(time.time() * 1000),
            'ts': int(time.time()),
            'device_brand': 'Google',
            'device_type': 'Pixel 4',
            'device_platform': 'android',
            'resolution': '1080*1920',
            'dpi': 420,
            'os_version': '10',
            'os_api': '29',
            'app_name': 'aweme',
            'app_type': 'normal',
            'app_language': 'en',
            'language': 'en',
            'channel': 'googleplay',
            'ac': 'wifi',
            'is_my_cn': 1,
            'aid': 1128,
            'ssmix': 'a',
            'as': 'a1qwert123',
            'cp': 'cbfhckdckkde1',
        }
        
        aweme_detail = self._download_json(
            'https://aweme.snssdk.com/aweme/v1/aweme/detail/', aweme_id,
            'Downloading video details', 'Unable to download video details', query=query)['aweme_detail']
        video_info = aweme_detail['video']

        def parse_url_key(url_key):
            format_id, codec, res, bitrate = self._search_regex(
                r'v[^_]+_(?P<id>(?P<codec>[^_]+)_(?P<res>\d+p)_(?P<bitrate>\d+))', url_key,
                'url key', default=(None, None, None, None), group=('id', 'codec', 'res', 'bitrate'))
            if not format_id:
                return {}, None
            return {
                'format_id': format_id,
                'vcodec': 'h265' if codec == 'bytevc1' else codec,
                'tbr': int_or_none(bitrate, scale=1000) or None,
                'quality': qualities(self.QUALITIES)(res),
            }, res

        known_resolutions = {}

        def extract_addr(addr, add_meta={}):
            parsed_meta, res = parse_url_key(addr.get('url_key', ''))
            if res:
                known_resolutions.setdefault(res, {}).setdefault('height', add_meta.get('height'))
                known_resolutions[res].setdefault('width', add_meta.get('width'))
                parsed_meta.update(known_resolutions.get(res, {}))
                add_meta.setdefault('height', int_or_none(res[:-1]))
            return [{
                'url': url,
                'filesize': int_or_none(addr.get('data_size')),
                'ext': 'mp4',
                'acodec': 'aac',
                **add_meta, **parsed_meta
            } for url in addr.get('url_list') or []]

        # Hack: Add direct video links first to prioritize them when removing duplicate formats
        formats = []
        if video_info.get('play_addr'):
            formats.extend(extract_addr(video_info['play_addr'], {
                'format_id': 'play_addr',
                'format_note': 'Direct video',
                'vcodec': 'h265' if traverse_obj(
                    video_info, 'is_bytevc1', 'is_h265') else 'h264',  # Always h264?
                'width': video_info.get('width'),
                'height': video_info.get('height'),
            }))
        if video_info.get('download_addr'):
            formats.extend(extract_addr(video_info['download_addr'], {
                'format_id': 'download_addr',
                'format_note': 'Download video%s' % (', watermarked' if video_info.get('has_watermark') else ''),
                'vcodec': 'h264',
                'width': video_info.get('width'),
                'height': video_info.get('height'),
                'source_preference': -2 if video_info.get('has_watermark') else -1,
            }))
        if video_info.get('play_addr_h264'):
            formats.extend(extract_addr(video_info['play_addr_h264'], {
                'format_id': 'play_addr_h264',
                'format_note': 'Direct video',
                'vcodec': 'h264',
            }))
        if video_info.get('play_addr_bytevc1'):
            formats.extend(extract_addr(video_info['play_addr_bytevc1'], {
                'format_id': 'play_addr_bytevc1',
                'format_note': 'Direct video',
                'vcodec': 'h265',
            }))

        for bitrate in video_info.get('bit_rate', []):
            if bitrate.get('play_addr'):
                formats.extend(extract_addr(bitrate['play_addr'], {
                    'format_id': bitrate.get('gear_name'),
                    'format_note': 'Playback video',
                    'tbr': try_get(bitrate, lambda x: x['bit_rate'] / 1000),
                    'vcodec': 'h265' if traverse_obj(
                        bitrate, 'is_bytevc1', 'is_h265') else 'h264',
                    'fps': bitrate.get('FPS'),
                }))

        self._remove_duplicate_formats(formats)
        self._sort_formats(formats, ('quality', 'source', 'codec', 'size', 'br'))

        thumbnails = []
        for cover_id in ('cover', 'ai_dynamic_cover', 'animated_cover', 'ai_dynamic_cover_bak',
                         'origin_cover', 'dynamic_cover'):
            cover = video_info.get(cover_id)
            if cover:
                for cover_url in cover['url_list']:
                    thumbnails.append({
                        'id': cover_id,
                        'url': cover_url,
                    })

        stats_info = aweme_detail.get('statistics', {})
        author_info = aweme_detail.get('author', {})
        music_info = aweme_detail.get('music', {})
        user_id = str_or_none(author_info.get('nickname'))

        contained_music_track = traverse_obj(
            music_info, ('matched_song', 'title'), ('matched_pgc_sound', 'title'), expected_type=str)
        contained_music_author = traverse_obj(
            music_info, ('matched_song', 'author'), ('matched_pgc_sound', 'author'), 'author', expected_type=str)

        is_generic_og_trackname = music_info.get('is_original_sound') and music_info.get('title') == 'original sound - %s' % music_info.get('owner_handle')
        if is_generic_og_trackname:
            music_track, music_author = contained_music_track or 'original sound', contained_music_author
        else:
            music_track, music_author = music_info.get('title'), music_info.get('author')

        return {
            'id': aweme_id,
            'title': aweme_detail['desc'],
            'description': aweme_detail['desc'],
            'view_count': int_or_none(stats_info.get('play_count')),
            'like_count': int_or_none(stats_info.get('digg_count')),
            'repost_count': int_or_none(stats_info.get('share_count')),
            'comment_count': int_or_none(stats_info.get('comment_count')),
            'uploader': str_or_none(author_info.get('unique_id')),
            'creator': user_id,
            'uploader_id': str_or_none(author_info.get('uid')),
            'uploader_url': f'https://www.tiktok.com/@{user_id}' if user_id else None,
            'track': music_track,
            'album': str_or_none(music_info.get('album')) or None,
            'artist': music_author,
            'timestamp': int_or_none(aweme_detail.get('create_time')),
            'formats': formats,
            'thumbnails': thumbnails,
            'duration': int_or_none(traverse_obj(video_info, 'duration', ('download_addr', 'duration')), scale=1000)
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            return self._extract_aweme(video_id)
        except ExtractorError as e:
            self.report_warning(f'{e}; Retrying with webpage')

        webpage = self._download_webpage(url, video_id)
        render_data = self._parse_json(
            self._search_regex(
                r'<script [^>]*\bid=[\'"]RENDER_DATA[\'"][^>]*>(%7B.+%7D)</script>',
                webpage, 'render data'),
            video_id, transform_source=compat_urllib_parse_unquote)
        details = traverse_obj(render_data, (..., 'aweme', 'detail'), get_all=False)

        thumbnails = [{'url': self._proto_relative_url(url)} for url in traverse_obj(
            details, ('video', ('cover', 'dynamicCover', 'originCover')), expected_type=url_or_none, default=[])]

        common = {
            'width': traverse_obj(details, ('video', 'width'), expected_type=int),
            'height': traverse_obj(details, ('video', 'height'), expected_type=int),
            'ext': 'mp4',
        }
        formats = [{**common, 'url': self._proto_relative_url(url)} for url in traverse_obj(
            details, ('video', 'playAddr', ..., 'src'), expected_type=url_or_none, default=[]) if url]
        self._remove_duplicate_formats(formats)

        download_url = traverse_obj(details, ('download', 'url'), expected_type=url_or_none)
        if download_url:
            formats.append({
                **common,
                'format_id': 'download',
                'url': self._proto_relative_url(download_url),
                'quality': 1,
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': details.get('desc') or self._html_search_meta('title', webpage),
            'formats': formats,
            'thumbnails': thumbnails,
            'uploader': traverse_obj(details, ('authorInfo', 'nickname'), expected_type=str),
            'uploader_id': traverse_obj(details, ('authorInfo', 'uid'), expected_type=str),
            'uploader_url': 'https://www.douyin.com/user/%s' % traverse_obj(
                details, ('authorInfo', 'secUid'), expected_type=str),
            'timestamp': int_or_none(details.get('createTime')),
            'duration': traverse_obj(details, ('video', 'duration'), expected_type=int),
            'view_count': traverse_obj(details, ('stats', 'playCount'), expected_type=int),
            'like_count': traverse_obj(details, ('stats', 'diggCount'), expected_type=int),
            'repost_count': traverse_obj(details, ('stats', 'shareCount'), expected_type=int),
            'comment_count': traverse_obj(details, ('stats', 'commentCount'), expected_type=int),
        }
