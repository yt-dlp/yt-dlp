from .common import InfoExtractor
from ..utils import (
    int_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none
)


class YappyIE(InfoExtractor):
    _VALID_URL = r'https?://yappy\.media/video/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://yappy.media/video/47fea6d8586f48d1a0cf96a7342aabd2',
        'info_dict': {
            'id': '47fea6d8586f48d1a0cf96a7342aabd2',
            'ext': 'mp4',
            'title': 'Куда нажимать? Как снимать? Смотри видос и погнали!🤘🏻',
            'timestamp': 1661893200,
            'description': 'Куда нажимать? Как снимать? Смотри видос и погнали!🤘🏻',
            'thumbnail': 'https://cdn-st.ritm.media/static/pic/thumbnails/0c7c4d73388f47848acaf540d2e2bb8c-thumbnail.jpg',
            'upload_date': '20220830',
            'view_count': int,
            'like_count': int,
            'uploader_id': '59a0c8c485e5410b9c43474bf4c6a373',
            'categories': ['Образование и наука', 'Лайфхак', 'Технологии', 'Арт/искусство'],
            'repost_count': int,
            'uploader': 'YAPPY',
        }
    }, {
        'url': 'https://yappy.media/video/3862451954ad4bd58ae2ccefddb0bd33',
        'info_dict': {
            'id': '3862451954ad4bd58ae2ccefddb0bd33',
            'ext': 'mp4',
            'title': 'Опиши свой характер 3 словами🙃\n#психология #дружба #отношения',
            'timestamp': 1674726985,
            'like_count': int,
            'description': 'Опиши свой характер 3 словами🙃\n#психология #дружба #отношения',
            'uploader_id': '6793ee3581974a3586fc01e157de6c99',
            'view_count': int,
            'repost_count': int,
            'uploader': 'LENA SHTURMAN',
            'upload_date': '20230126',
            'thumbnail': 'https://cdn-st.ritm.media/static/pic/user_thumbnails/6e76bb4bbad640b6/9ec84c115b2b1967/1674716171.jpg',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_ld = self._search_json_ld(webpage, video_id)
        nextjs_data = self._search_nextjs_data(webpage, video_id)['props']['pageProps']

        media_url = url_or_none(
            traverse_obj(nextjs_data, (('data', 'OpenGraphParameters'), 'link'), get_all=False))
        has_watermark = str(media_url).endswith('wm.mp4')

        formats = [{
            'url': url_or_none(media_url),
            'ext': 'mp4',
            'format_note': 'Watermarked' if has_watermark else None,
            'preference': -10 if has_watermark else None
        }]

        if has_watermark and media_url:
            formats.append({
                'url': url_or_none(str(media_url).replace('-wm.mp4', '.mp4')),
                'ext': 'mp4'
            })

        if traverse_obj(nextjs_data, (('data', 'OpenGraphParameters'), 'audio'), get_all=False):
            formats.append({
                'url': traverse_obj(
                    nextjs_data, (('data', 'OpenGraphParameters'), 'audio', 'link'), get_all=False) or None,
                'ext': 'mp3',
                'vcodec': 'none'
            })

        return {
            'id': video_id,
            'title': (json_ld.get('description')
                      or self._html_search_meta(['og:title'], webpage)
                      or self._html_extract_title(webpage)),
            'formats': formats,
            'thumbnail': (traverse_obj(nextjs_data, (('data', 'OpenGraphParameters'), 'thumbnail'), get_all=False)
                          or self._html_search_meta(['og:image', 'og:image:secure_url'], webpage)),
            'description': (traverse_obj(nextjs_data, (('data', 'OpenGraphParameters'), 'description'), get_all=False)
                            or json_ld.get('description')
                            or self._html_search_meta(['description', 'og:description'], webpage)),
            'timestamp': (unified_timestamp(
                traverse_obj(nextjs_data, (('data', 'OpenGraphParameters'), 'publishedAt'), get_all=False))
                or json_ld.get('timestamp')),
            'view_count': int_or_none(
                traverse_obj(nextjs_data, (('data', 'OpenGraphParameters'), 'viewsCount'), get_all=False)
                or json_ld.get('view_count')),
            'like_count': int_or_none(traverse_obj(
                nextjs_data, (('data', 'OpenGraphParameters'), 'likesCount'), get_all=False)),
            'uploader': traverse_obj(
                nextjs_data, (('data', 'OpenGraphParameters'), 'creator', 'firstName'), get_all=False),
            'uploader_id': traverse_obj(
                nextjs_data, (('data', 'OpenGraphParameters'), 'creator', ('uuid', 'nickname')), get_all=False),
            'categories': traverse_obj(
                nextjs_data, (('data', 'OpenGraphParameters'), 'categories', ..., 'name')) or None,
            'repost_count': int_or_none(traverse_obj(
                nextjs_data, (('data', 'OpenGraphParameters'), 'sharingCount'), get_all=False))
        }
