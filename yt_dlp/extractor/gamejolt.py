# coding: utf-8
from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    str_or_none,
    traverse_obj,
)


class GameJoltBaseIE(InfoExtractor):
    _API_BASE = 'https://gamejolt.com/site-api/'
    def _call_api(self, endpoint, *args, **kwargs):
        return self._download_json(self._API_BASE + endpoint, *args, **kwargs)['payload']

    def _parse_post(self, post_data):
        post_id = post_data['hash']
        lead_content = self._parse_json(post_data.get('lead_content') or '{}', post_id, fatal=False) or {}
        description, full_description = post_data.get('leadStr'), None
        if post_data.get('has_article'):
            article_content = self._parse_json(
                post_data.get('article_content')
                or self._call_api('web/posts/article/' + post_data.get('id'),
                                  note='Downloading article metadata', errnote='Unable to download article metadata', fatal=False).get('article'),
                post_id, fatal=False)
            full_description = '%s\n%s' % (description, ''.join(traverse_obj(
                article_content, ('content', ..., 'content', ..., 'text'), expected_type=str, default=[]))) if article_content else None
            
        user_data = post_data.get('user') or {}
        info_dict = {
            'id': post_id,
            'title': description,
            'description': full_description or description,
            'display_id': post_data.get('slug'),
            'uploader': user_data.get('display_name') or user_data.get('name'),
            'uploader_id': user_data.get('username'),
            'uploader_url': 'https://gamejolt.com' + user_data['url'] if user_data.get('url') else None,
            'categories': traverse_obj(post_data, ('communities', ..., 'community', 'name'), expected_type=str_or_none),
            'tags': traverse_obj(
                lead_content, ('content', ..., 'content', ..., 'marks', ..., 'attrs', 'tag'), expected_type=str_or_none),
            'like_count': post_data.get('like_count'),
            'comment_count': post_data.get('comment_count'),
            'timestamp': int_or_none(post_data.get('added_on'), scale=1000),
            'release_timestamp': int_or_none(post_data.get('published_on'), scale=1000),
        }

        # TODO: Handle multiple videos/embeds?
        embed_url = traverse_obj(post_data, ('embeds', ..., 'url'), expected_type=str_or_none, get_all=False)
        if embed_url:
            return {
                '_type': 'url',
                'url': embed_url,
                **info_dict
            }

        video_data = traverse_obj(post_data, ('videos', ...), expected_type=dict, get_all=False)
        if video_data:
            formats, thumbnails = [], []
            for media in video_data.get('media', []):
                media_url, mimetype, ext, media_id = media['img_url'], media.get('filetype', ''), determine_ext(media['img_url']), media.get('type')
                if mimetype == 'application/vnd.apple.mpegurl' or ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(media_url, post_id, 'mp4', m3u8_id=media_id))
                elif mimetype == 'application/dash+xml' or ext == 'mpd':
                    formats.extend(self._extract_mpd_formats(media_url, post_id, mpd_id=media_id))
                elif 'image' in mimetype:
                    thumbnails.append({
                        'id': media_id,
                        'url': media_url,
                        'width': media.get('width'),
                        'height': media.get('height'),
                        'filesize': media.get('filesize'),
                    })
                else:
                    formats.append({
                        'format_id': media_id,
                        'url': media_url,
                        'width': media.get('width'),
                        'height': media.get('height'),
                        'filesize': media.get('filesize'),
                    })
            info_dict.update({
                'ie_key': GameJoltIE.ie_key(),
                'extractor': 'GameJolt',
                'webpage_url': str_or_none(post_data.get('url')) or 'https://gamejolt.com/p/' + post_id,
                'formats': formats,
                'thumbnails': thumbnails,
                'view_count': int_or_none(video_data.get('view_count'))
            })

        return info_dict


class GameJoltIE(GameJoltBaseIE):
    _VALID_URL = r'https?://gamejolt\.com/p/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://gamejolt.com/p/introducing-ramses-jackson-some-fnf-himbo-i-ve-been-animating-fo-c6achnzu',
        'md5': 'asdf',
        'info_dict': {
            'id': 'c6achnzu',
            'ext': 'mp4',
            'display_id': 'introducing-ramses-jackson-some-fnf-himbo-i-ve-been-animating-fo-c6achnzu',
            'title': 'a',
            'description': 'a',
            'uploader': 'Jakeneutron',
            'uploader_id': 'Jakeneutron',
            'uploader_url': 'https://gamejolt.com/@Jakeneutron',
            'categories': ['abc'],
            'tags': 'abcd',
        }
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url).split('-')[-1]
        post_data = self._call_api(
            'web/posts/view/' + post_id, post_id)['post']
        return self._parse_post(post_data)
