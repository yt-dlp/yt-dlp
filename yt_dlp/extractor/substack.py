import re
import urllib.parse

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    determine_ext,
    float_or_none,
    js_to_json,
    str_or_none,
)
from ..utils.traversal import traverse_obj


class SubstackIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<username>[\w-]+)\.substack\.com/p/(?P<id>[\w-]+)'
    _TESTS = [{
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
        # An embedded public video on a regular newsletter page
        'url': 'https://jessica.substack.com/p/livestream-today-chat-with-me-and',
        'md5': '7466bdd760b8ef8a60a1336c4e86ce20',
        'info_dict': {
            'id': '86e0da19-8263-4376-a84a-76b501db12d0',
            'ext': 'mp4',
            'title': 'liz.mp4',
            'thumbnail': r're:https://substack.*\.com/video_upload/post/158453351/86e0da19-8263-4376-a84a-76b501db12d0/.*\.png',
            'duration': 3087.8333,
            'uploader_id': '535611',
        },
    }, {
        # An embedded public audio on a regular newsletter page
        'url': 'https://jessica.substack.com/p/audio-of-jd-vance-calling-rape-an?utm_source=publication-search',
        'md5': 'bd6c2a9e0c590844496db94ad7653781',
        'info_dict': {
            'id': '17e80ab3-d5d6-488e-a939-404f33c17ef5',
            'ext': 'mp3',
            'title': 'JD Vance rape inconvenient.m4a',
            'duration': 25.939592,
            'uploader_id': '535611',
        },
    }, {
        # A "podcast" page which contains embedded video
        'url': 'https://vigilantfox.substack.com/p/global-medical-tyranny-just-got-real?source=queue',
        'info_dict': {
            'id': '161501224',
            'title': 'Videos for Global Medical Tyranny Just Got Real | Daily Pulse',
        },
        'playlist': [{
            'info_dict': {
                'id': '161501224',
                'ext': 'mp3',
                'title': 'Global Medical Tyranny Just Got Real | Daily Pulse',
                'uploader_id': '975571',
                'uploader': 'The Vigilant Fox',
                'thumbnail': r're:https://substack.*video.*/video_upload/post/.+\.png',
                'description': 'The news you weren’t supposed to see.',
            },
        }, {
            'info_dict': {
                'id': '95b4b5a7-3873-465d-a6f4-8d3c499f29f2',
                'ext': 'mp4',
                'title': 'WHO.mp4',
                'uploader_id': '82027648',
                'duration': 593.3333,
                'thumbnail': r're:https://substack.*video.*/video_upload/post/.+\.png',
            },
        }, {
            'info_dict': {
                'id': '235db8bf-c6e8-439a-b51a-eb7566fc7ac1',
                'ext': 'mp4',
                'title': 'The Vigilant Fox\'s Video - Apr 16, 2025-VEED.mp4',
                'uploader_id': '82027648',
                'duration': 498.86667,
                'thumbnail': r're:https://substack.*video.*/video_upload/post/.+\.png',
            },
        }, {
            'info_dict': {
                'id': 'ef3fe4c1-d748-4665-ba9c-33396008e75b',
                'ext': 'mp4',
                'title': 'The Vigilant Fox\'s Video - Apr 16, 2025-VEED (1).mp4',
                'uploader_id': '82027648',
                'duration': 410.53333,
                'thumbnail': r're:https://substack.*video.*/video_upload/post/.+\.png',
            },
        }],
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        if not re.search(r'<script[^>]+src=["\']https://substackcdn.com/[^"\']+\.js', webpage):
            return

        mobj = re.search(r'{[^}]*\\?["\']subdomain\\?["\']\s*:\s*\\?["\'](?P<subdomain>[^\\"\']+)', webpage)
        if mobj:
            parsed = urllib.parse.urlparse(url)
            yield parsed._replace(netloc=f'{mobj.group("subdomain")}.substack.com').geturl()
            raise cls.StopExtraction

    def _extract_video_formats(self, video_id, url, query_params={}):
        formats, subtitles = [], {}
        for video_format in ('hls', 'mp4'):
            q = {'type': video_format}
            q.update(query_params)
            query_string = '&'.join(f'{k}={v}' for k, v in q.items())
            video_url = urllib.parse.urljoin(url, f'/api/v1/video/upload/{video_id}/src?{query_string}')

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
        display_id, username = self._match_valid_url(url).group('id', 'username')
        webpage = self._download_webpage(url, display_id)

        webpage_info = self._parse_json(self._search_json(
            r'window\._preloads\s*=\s*JSON\.parse\(', webpage, 'json string',
            display_id, transform_source=js_to_json, contains_pattern=r'"{(?s:.+)}"'), display_id)

        canonical_url = url
        domain = traverse_obj(webpage_info, ('domainInfo', 'customDomain', {str}))
        if domain:
            canonical_url = urllib.parse.urlparse(url)._replace(netloc=domain).geturl()

        post_type = webpage_info['post']['type']
        post_title = traverse_obj(webpage_info, ('post', 'title'))
        formats, subtitles = [], {}
        all_results = []
        result_info = {
            'id': str(webpage_info['post']['id']),
            'subtitles': subtitles,
            'title': traverse_obj(webpage_info, ('post', 'title')),
            'description': traverse_obj(webpage_info, ('post', 'description')),
            'thumbnail': traverse_obj(webpage_info, ('post', 'cover_image')),
            'uploader': traverse_obj(webpage_info, ('pub', 'name')),
            'uploader_id': str_or_none(traverse_obj(webpage_info, ('post', 'publication_id'))),
            'webpage_url': canonical_url,
        }
        # handle specific post types which are based on media
        if post_type == 'podcast':
            podcast_result = dict(result_info)
            fmt = {'url': webpage_info['post']['podcast_url']}
            if not determine_ext(fmt['url'], default_ext=None):
                # The redirected format URL expires but the original URL doesn't,
                # so we only want to extract the extension from this request
                fmt['ext'] = determine_ext(self._request_webpage(
                    HEADRequest(fmt['url']), display_id,
                    'Resolving podcast file extension',
                    'Podcast URL is invalid').url)
            podcast_result['formats'] = [fmt]
            all_results.append(podcast_result)
        if post_type == 'video':
            video_result = dict(result_info)
            formats, subtitles = self._extract_video_formats(
                webpage_info['post']['videoUpload']['id'], canonical_url)
            video_result.update({
                'formats': formats,
                'subtitles': subtitles,
            })
            all_results.append(video_result)

        # search for embedded players on the page
        found_items = []
        post_id = str(webpage_info['post']['id'])
        assert result_info['uploader_id'] is not None, 'newsletter posted without user_id'

        video_players = re.finditer(
            r'<div[^>]*data-component-name="VideoEmbedPlayer"[^>]*>',
            webpage)
        for vp in video_players:
            video_id = self._search_regex(r'id="([^"]+)"',
                                          vp.group(0),
                                          'video id', group=1).replace('media-', '')
            video_metadata_url = urllib.parse.urljoin(url, f'/api/v1/video/upload/{video_id}')
            json_vid_data = self._download_json(video_metadata_url, video_id)
            assert video_id == json_vid_data['id'], 'unexpected json metadata retrieved'
            json_vid_data['_type'] = 'video'
            found_items.append(json_vid_data)

        audio_players = re.finditer(
            r'<div[^>]*data-component-name="AudioEmbedPlayer"[^>]*>',
            webpage)
        for ap in audio_players:
            video_uri = self._search_regex(r'src="(/api/v1/audio/upload/[^"]+)"',
                                           webpage[ap.start():],
                                           'video uri', group=1)
            video_metadata_url = urllib.parse.urljoin(url, video_uri.replace('/src', ''))
            video_id = self._search_regex(r'upload/([^/]+)/src',
                                          video_uri,
                                          'video id', group=1)
            json_vid_data = self._download_json(video_metadata_url, video_id)
            assert video_id == json_vid_data['id'], 'unexpected json metadata retrieved'
            json_vid_data['_type'] = 'audio'
            json_vid_data['_uri'] = video_uri
            found_items.append(json_vid_data)

        for json_vid_data in found_items:
            video_id = json_vid_data['id']
            if 'video' in json_vid_data['_type']:
                formats, subtitles = self._extract_video_formats(
                    video_id, canonical_url,
                    query_params={'override_publication_id': result_info['uploader_id']})
            else:
                fmt = {'url': urllib.parse.urljoin(url, json_vid_data['_uri'])}
                if not determine_ext(fmt['url'], default_ext=None):
                    # The redirected format URL expires but the original URL doesn't,
                    # so we only want to extract the extension from this request
                    fmt['ext'] = determine_ext(self._request_webpage(
                        HEADRequest(fmt['url']), video_id,
                        'Resolving audio file extension',
                        'Embedded audio URL is invalid').url)
                formats.append(fmt)

            new_result = dict(result_info)
            new_result.update({
                'formats': formats,
                'subtitles': subtitles,
                'id': video_id,
                'title': json_vid_data.get('name', None),
                'description': None,
                'thumbnail': json_vid_data.get('thumbnail_url', None),
                'duration': float_or_none(json_vid_data.get('duration', None)),
                # videos can be cross-embedded, so the publication id should be of the uploader
                'uploader_id': str_or_none(json_vid_data.get('user_id', None)),
                'uploader': None,  # video uploader username is not included
            })
            all_results.append(new_result)

        if len(all_results) > 0:
            playlist_title = f'Videos for {post_title}'
            return self.playlist_result(all_results, post_id, playlist_title)
        else:
            self.raise_no_formats(f'Page type "{post_type}" contains no supported embeds')
