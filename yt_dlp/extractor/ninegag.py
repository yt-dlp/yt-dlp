from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    traverse_obj,
    unescapeHTML,
    url_or_none,
)


class NineGagIE(InfoExtractor):
    IE_NAME = '9gag'
    IE_DESC = '9GAG'
    _VALID_URL = r'https?://(?:www\.)?9gag\.com/gag/(?P<id>[^/?&#]+)'

    _TESTS = [{
        'url': 'https://9gag.com/gag/ae5Ag7B',
        'info_dict': {
            'id': 'ae5Ag7B',
            'ext': 'webm',
            'title': 'Capybara Agility Training',
            'upload_date': '20191108',
            'timestamp': 1573237208,
            'thumbnail': 'https://img-9gag-fun.9cache.com/photo/ae5Ag7B_460s.jpg',
            'categories': ['Awesome'],
            'tags': ['Awesome'],
            'duration': 44,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
        }
    }, {
        # HTML escaped title
        'url': 'https://9gag.com/gag/av5nvyb',
        'only_matching': True,
    }, {
        # Non Anonymous Uploader
        'url': 'https://9gag.com/gag/ajgp66G',
        'info_dict': {
            'id': 'ajgp66G',
            'ext': 'webm',
            'title': 'Master Shifu! Or Splinter! You decide:',
            'upload_date': '20220806',
            'timestamp': 1659803411,
            'thumbnail': 'https://img-9gag-fun.9cache.com/photo/ajgp66G_460s.jpg',
            'categories': ['Funny'],
            'tags': ['Funny'],
            'duration': 26,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'uploader': 'Peter Klaus',
            'uploader_id': 'peterklaus12',
            'uploader_url': 'https://9gag.com/u/peterklaus12',
        }
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url)
        post = self._download_json(
            'https://9gag.com/v1/post', post_id, query={
                'id': post_id
            })['data']['post']

        if post.get('type') != 'Animated':
            raise ExtractorError(
                'The given url does not contain a video',
                expected=True)

        duration = None
        formats = []
        thumbnails = []
        for key, image in (post.get('images') or {}).items():
            image_url = url_or_none(image.get('url'))
            if not image_url:
                continue
            ext = determine_ext(image_url)
            image_id = key.strip('image')
            common = {
                'url': image_url,
                'width': int_or_none(image.get('width')),
                'height': int_or_none(image.get('height')),
            }
            if ext in ('jpg', 'png'):
                webp_url = image.get('webpUrl')
                if webp_url:
                    t = common.copy()
                    t.update({
                        'id': image_id + '-webp',
                        'url': webp_url,
                    })
                    thumbnails.append(t)
                common.update({
                    'id': image_id,
                    'ext': ext,
                })
                thumbnails.append(common)
            elif ext in ('webm', 'mp4'):
                if not duration:
                    duration = int_or_none(image.get('duration'))
                common['acodec'] = 'none' if image.get('hasAudio') == 0 else None
                for vcodec in ('vp8', 'vp9', 'h265'):
                    c_url = image.get(vcodec + 'Url')
                    if not c_url:
                        continue
                    c_f = common.copy()
                    c_f.update({
                        'format_id': image_id + '-' + vcodec,
                        'url': c_url,
                        'vcodec': vcodec,
                    })
                    formats.append(c_f)
                common.update({
                    'ext': ext,
                    'format_id': image_id,
                })
                formats.append(common)

        section = traverse_obj(post, ('postSection', 'name'))

        tags = None
        post_tags = post.get('tags')
        if post_tags:
            tags = []
            for tag in post_tags:
                tag_key = tag.get('key')
                if not tag_key:
                    continue
                tags.append(tag_key)

        return {
            'id': post_id,
            'title': unescapeHTML(post.get('title')),
            'timestamp': int_or_none(post.get('creationTs')),
            'duration': duration,
            'uploader': traverse_obj(post, ('creator', 'fullName')),
            'uploader_id': traverse_obj(post, ('creator', 'username')),
            'uploader_url': url_or_none(traverse_obj(post, ('creator', 'profileUrl'))),
            'formats': formats,
            'thumbnails': thumbnails,
            'like_count': int_or_none(post.get('upVoteCount')),
            'dislike_count': int_or_none(post.get('downVoteCount')),
            'comment_count': int_or_none(post.get('commentsCount')),
            'age_limit': 18 if post.get('nsfw') == 1 else None,
            'categories': [section] if section else None,
            'tags': tags,
        }
