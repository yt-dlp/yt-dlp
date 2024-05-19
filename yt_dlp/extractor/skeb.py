from .common import InfoExtractor
from ..utils import ExtractorError, determine_ext, parse_qs, traverse_obj


class SkebIE(InfoExtractor):
    _VALID_URL = r'https?://skeb\.jp/@[^/]+/works/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://skeb.jp/@riiru_wm/works/10',
        'info_dict': {
            'id': '466853',
            'title': '内容はおまかせします！ by 姫ノ森りぃる@一周年',
            'description': 'md5:1ec50901efc3437cfbfe3790468d532d',
            'uploader': '姫ノ森りぃる@一周年',
            'uploader_id': 'riiru_wm',
            'age_limit': 0,
            'tags': [],
            'url': r're:https://skeb.+',
            'thumbnail': r're:https://skeb.+',
            'subtitles': {
                'jpn': [{
                    'url': r're:https://skeb.+',
                    'ext': 'vtt'
                }]
            },
            'width': 720,
            'height': 405,
            'duration': 313,
            'fps': 30,
            'ext': 'mp4',
        },
    }, {
        'url': 'https://skeb.jp/@furukawa_nob/works/3',
        'info_dict': {
            'id': '489408',
            'title': 'いつもお世話になってお... by 古川ノブ@音楽とVlo...',
            'description': 'md5:5adc2e41d06d33b558bf7b1faeb7b9c2',
            'uploader': '古川ノブ@音楽とVlogのVtuber',
            'uploader_id': 'furukawa_nob',
            'age_limit': 0,
            'tags': [
                'よろしく', '大丈夫', 'お願い', 'でした',
                '是非', 'O', 'バー', '遊び', 'おはよう',
                'オーバ', 'ボイス',
            ],
            'url': r're:https://skeb.+',
            'thumbnail': r're:https://skeb.+',
            'subtitles': {
                'jpn': [{
                    'url': r're:https://skeb.+',
                    'ext': 'vtt'
                }]
            },
            'duration': 98,
            'ext': 'mp3',
            'vcodec': 'none',
            'abr': 128,
        },
    }, {
        'url': 'https://skeb.jp/@mollowmollow/works/6',
        'info_dict': {
            'id': '6',
            'title': 'ヒロ。\n\n私のキャラク... by 諸々',
            'description': 'md5:aa6cbf2ba320b50bce219632de195f07',
            '_type': 'playlist',
            'entries': [{
                'id': '486430',
                'title': 'ヒロ。\n\n私のキャラク... by 諸々',
                'description': 'md5:aa6cbf2ba320b50bce219632de195f07',
            }, {
                'id': '486431',
                'title': 'ヒロ。\n\n私のキャラク... by 諸々',
            }]
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        nuxt_data = self._search_nuxt_data(self._download_webpage(url, video_id), video_id)

        parent = {
            'id': video_id,
            'title': nuxt_data.get('title'),
            'description': nuxt_data.get('description'),
            'uploader': traverse_obj(nuxt_data, ('creator', 'name')),
            'uploader_id': traverse_obj(nuxt_data, ('creator', 'screen_name')),
            'age_limit': 18 if nuxt_data.get('nsfw') else 0,
            'tags': nuxt_data.get('tag_list'),
        }

        entries = []
        for item in nuxt_data.get('previews') or []:
            vid_url = item.get('url')
            given_ext = traverse_obj(item, ('information', 'extension'))
            preview_ext = determine_ext(vid_url, default_ext=None)
            if not preview_ext:
                content_disposition = parse_qs(vid_url)['response-content-disposition'][0]
                preview_ext = self._search_regex(
                    r'filename="[^"]+\.([^\.]+?)"', content_disposition,
                    'preview file extension', fatal=False, group=1)
            if preview_ext not in ('mp4', 'mp3'):
                continue
            if not vid_url or not item.get('id'):
                continue
            width, height = traverse_obj(item, ('information', 'width')), traverse_obj(item, ('information', 'height'))
            if width is not None and height is not None:
                # the longest side is at most 720px for non-client viewers
                max_size = max(width, height)
                width, height = list(x * 720 // max_size for x in (width, height))
            entries.append({
                **parent,
                'id': str(item['id']),
                'url': vid_url,
                'thumbnail': item.get('poster_url'),
                'subtitles': {
                    'jpn': [{
                        'url': item.get('vtt_url'),
                        'ext': 'vtt',
                    }]
                } if item.get('vtt_url') else None,
                'width': width,
                'height': height,
                'duration': traverse_obj(item, ('information', 'duration')),
                'fps': traverse_obj(item, ('information', 'frame_rate')),
                'ext': preview_ext or given_ext,
                'vcodec': 'none' if preview_ext == 'mp3' else None,
                # you'll always get 128kbps MP3 for non-client viewers
                'abr': 128 if preview_ext == 'mp3' else None,
            })

        if not entries:
            raise ExtractorError('No video/audio attachment found in this commission.', expected=True)
        elif len(entries) == 1:
            return entries[0]
        else:
            parent.update({
                '_type': 'playlist',
                'entries': entries,
            })
            return parent
