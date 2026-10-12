import re
import urllib.parse

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    determine_ext,
    str_or_none,
)
from ..utils.traversal import traverse_obj


class SubstackIE(InfoExtractor):
    _VALID_URL = r'https?://([\w-]+\.)?substack\.com(?P<uploader>/@\w+)?/(p|note)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://substack.com/@globalgeopolitic/note/c-234377485',
        'md5': 'f33a61d6c6ee1190954cbe1c38ea7ed3',
        'info_dict': {
            'id': '234377485',
            'ext': 'mp4',
            'title': 'Decoding power and defying narratives, an independent geopolitical analysis exposing hidden agendas and challenging mainstream views. Think critically, freely, and beyond the headlines.',
            'description': 'md5:baa260ccbca4ffd1eb2acf4a3e15f57a',
            'thumbnail': 'md5:94d144e7621d05401eccc6f4fdad6b4f',
            'uploader': 'Global GeoPolitics',
            'uploader_id': '247935545',
        },
    }, {
        'url': 'https://haleynahman.substack.com/p/i-made-a-vlog?s=r',
        'md5': 'f27e4fc6252001d48d479f45e65cdfd5',
        'info_dict': {
            'id': '47660949',
            'ext': 'mp4',
            'title': 'I MADE A VLOG',
            'description': 'md5:9248af9a759321e1027226f988f54d96',
            'thumbnail': 'md5:bec758a34d8ee9142d43bcebdf33af18',
            'uploader': 'Maybe Baby',
            'uploader_id': '33628',
        },
    }, {
        'url': 'https://haleynahman.substack.com/p/-dear-danny-i-found-my-boyfriends?s=r',
        'md5': '0a63eacec877a1171a62cfa69710fcea',
        'info_dict': {
            'id': '51045592',
            'ext': 'mpga',
            'title': "🎧 Dear Danny: I found my boyfriend's secret Twitter account",
            'description': 'md5:a57f2439319e56e0af92dd0c95d75797',
            'thumbnail': 'md5:daa40b6b79249417c14ff8103db29639',
            'uploader': 'Maybe Baby',
            'uploader_id': '33628',
        },
    }, {
        'url': 'https://andrewzimmern.substack.com/p/mussels-with-black-bean-sauce-recipe',
        'md5': 'fd3c07077b02444ff0130715b5f632bb',
        'info_dict': {
            'id': '47368578',
            'ext': 'mp4',
            'title': 'Mussels with Black Bean Sauce: Recipe of the Week #7',
            'description': 'md5:b96234a2906c7d854d5229818d889515',
            'thumbnail': 'md5:e30bfaa9da40e82aa62354263a9dd232',
            'uploader': "Andrew Zimmern's Spilled Milk ",
            'uploader_id': '577659',
        },
    }, {
        # Podcast that needs its file extension resolved to mp3
        'url': 'https://persuasion1.substack.com/p/summers',
        'md5': '1456a755d46084744facdfac9edf900f',
        'info_dict': {
            'id': '141970405',
            'ext': 'mp3',
            'title': 'Larry Summers on What Went Wrong on Campus',
            'description': 'Yascha Mounk and Larry Summers also discuss the promise and perils of artificial intelligence.',
            'thumbnail': r're:https://substackcdn\.com/image/.+\.jpeg',
            'uploader': 'Persuasion',
            'uploader_id': '61579',
        },
    }, {
        # Podcast with video where podcast_url is not resolvable
        'url': 'https://mellowkat.substack.com/p/theyre-all-compromised-wake-up',
        'md5': '7627f28352ed05c4cfc799bb1fc5822c',
        'info_dict': {
            'id': '180331920',
            'ext': 'mp4',
            'title': 'They\'re ALL compromised. Wake up.',
            'description': 'Watch now | Left vs. Right is theater. Many more links in this post! Click "view post" to read.',
            'thumbnail': r're:https://substackcdn\.com/image/.+\.png',
            'uploader': 'MellowKat\'s Newsletter',
            'uploader_id': '1075591',
        },
        'expected_warnings': ['Podcast URL is invalid'],
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.mollymovieclub.com/p/interstellar',
        'info_dict': {
            'id': '53602801',
            'ext': 'mpga',
            'title': 'Interstellar',
            'description': 'Listen now | Episode One',
            'thumbnail': r're:https?://.+\.jpeg',
            'uploader': 'Molly Movie Club',
            'uploader_id': '839621',
        },
    }, {
        'url': 'https://www.blockedandreported.org/p/episode-117-lets-talk-about-depp',
        'info_dict': {
            'id': '57962052',
            'ext': 'mpga',
            'title': 'md5:855b2756f0ee10f6723fa00b16266f8d',
            'description': 'The takes the takes the takes',
            'thumbnail': r're:https?://.+\.jpeg',
            'uploader': 'Blocked and Reported',
            'uploader_id': '500230',
        },
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        if not re.search(r'<script[^>]+src=["\']https://substackcdn.com/[^"\']+\.js', webpage):
            return

        if re.search(r'https?://([\w-]+\.)?substack\.com/@\w+/(p|note)/[\w-]+', url):
            yield url
            return

        mobj = re.search(r'{[^}]*\\?["\']subdomain\\?["\']\s*:\s*\\?["\'](?P<subdomain>[^\\"\']+)', webpage)
        if mobj:
            parsed = urllib.parse.urlparse(url)
            yield parsed._replace(netloc=f'{mobj.group("subdomain")}.substack.com').geturl()
            raise cls.StopExtraction

    def _extract_video_formats(self, video_id, url):
        formats, subtitles = [], {}
        for video_format in ('hls', 'mp4'):
            video_url = urllib.parse.urljoin(url, f'/api/v1/video/upload/{video_id}/src?type={video_format}')

            if video_format == 'hls':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(video_url, video_id, 'mp4', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': video_url,
                    'ext': video_format,
                })

        return formats, subtitles

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        webpage_info = self._parse_json(self._search_json(
            r'window\._preloads\s*=\s*JSON\.parse\(', webpage, 'json string',
            display_id, contains_pattern=r'"{(?s:.+)}"'), display_id)

        canonical_url = url
        domain = traverse_obj(webpage_info, ('domainInfo', 'customDomain', {str}))
        if domain:
            canonical_url = urllib.parse.urlparse(url)._replace(netloc=domain).geturl()

        title = None
        uploader = None
        uploader_id = None
        description = None
        thumbnail = None
        formats, subtitles = [], {}

        post = None
        post_type = ''
        if 'feedData' in webpage_info and 'post' not in webpage_info:
            post_type = 'feed'
        else:
            post = webpage_info['post']
            post_type = str(post['type'])
            if 'video_upload_id' in post:
                # Full credit to https://github.com/rdamas @ https://github.com/yt-dlp/yt-dlp/pull/13759
                formats, subtitles = self._extract_video_formats(post['video_upload_id'], canonical_url)
                post_type = None

        if post is not None and 'podcast_url' in post:
            # Full credit to https://github.com/rdamas @ https://github.com/yt-dlp/yt-dlp/pull/13759
            ext = None
            fmt = {'url': post['podcast_url']}
            if not (ext := determine_ext(fmt['url'], default_ext=None)):
                fatal = not formats
                podcast_url_src = self._request_webpage(HEADRequest(fmt['url']), display_id,
                                                        'Resolving podcast file extension',
                                                        'Podcast URL is invalid', fatal=fatal)
                if podcast_url_src:
                    ext = determine_ext(podcast_url_src.url)
            if ext is not None:
                fmt['ext'] = ext
                formats.append(fmt)
        elif post_type == 'video':
            if 'videoUpload' in post:
                formats, subtitles = self._extract_video_formats(str(post['videoUpload']['id']), canonical_url)
            else:
                formats, subtitles = self._extract_video_formats(str(post['mediaUpload']['id']), canonical_url)
        elif post_type == 'feed':
            post = webpage_info['feedData']['feedItem']
            if 'post' in post and post['post'] is not None:
                post = post['post']
            else:
                post = post['comment']
                if 'bio' in post:
                    title = traverse_obj(post, ('bio',))
                if 'name' in post:
                    uploader = traverse_obj(post, ('name',))
                if 'user_id' in post:
                    uploader_id = str(traverse_obj(post, ('user_id',)))
                if 'body' in post:
                    description = traverse_obj(post, ('body',))
                if 'photo_url' in post:
                    thumbnail = traverse_obj(post, ('photo_url',))
                post['attachments'][0]['id'] = str(post['id'])
                post = post['attachments'][0]
            if 'videoUpload' in post:
                formats, subtitles = self._extract_video_formats(str(post['videoUpload']['id']), canonical_url)
            else:
                formats, subtitles = self._extract_video_formats(str(post['mediaUpload']['id']), canonical_url)
        elif post_type is not None:
            self.raise_no_formats(f'Page type "{post_type}" is not supported')
            return {}

        if not formats:
            # Full credit to https://github.com/rdamas @ https://github.com/yt-dlp/yt-dlp/pull/13759
            self.raise_no_formats(f'Page type "{post_type}" is not supported')
            return {}

        if title is None:
            title = traverse_obj(post, ('title',))
        if uploader is None:
            uploader = traverse_obj(post, ('name',))
        if uploader_id is None:
            uploader_id = str_or_none(traverse_obj(post, ('publication_id',)))
        if description is None:
            description = traverse_obj(post, ('description',))
        if thumbnail is None:
            thumbnail = traverse_obj(post, ('cover_image',))

        return {
            'id': str(traverse_obj(post, ('id',))),
            'formats': formats,
            'subtitles': subtitles,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'webpage_url': canonical_url,
        }
