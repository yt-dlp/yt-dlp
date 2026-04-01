import json

from .common import InfoExtractor
from ..utils import (
    decode_base_n,
    int_or_none,
    remove_end,
    strip_or_none,
    traverse_obj,
    urlencode_postdata,
    url_or_none,
)

_ENCODING_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'


class ThreadsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?threads\.(?:net|com)/(?:@[^/?#]+/post|t)/(?P<id>[^/?#&]+)'
    _GRAPHQL_DOC_ID = '26742885138663415'
    _GRAPHQL_FRIENDLY_NAME = 'BarcelonaPermalinkMobilePostColumnPageQuery'
    _WEB_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
    _GRAPHQL_BOOL_PROVIDERS = (
        'BarcelonaHasDearAlgoConsumption',
        'BarcelonaIsLoggedIn',
        'BarcelonaHasEventBadge',
        'BarcelonaThreadsWebCachingImprovements',
        'BarcelonaIsSearchDiscoveryEnabled',
        'BarcelonaHasCommunities',
        'BarcelonaHasGameScoreShare',
        'BarcelonaHasPublicViewCountCard',
        'BarcelonaHasScorecardCommunity',
        'BarcelonaHasMusic',
        'BarcelonaHasGhostPostEmojiActivation',
        'BarcelonaOptionalCookiesEnabled',
        'BarcelonaHasDearAlgoWebProduction',
        'BarcelonaIsCrawler',
        'BarcelonaHasDisplayNames',
        'BarcelonaHasCommunityTopContributors',
        'BarcelonaCanSeeSponsoredContent',
        'BarcelonaShouldShowFediverseM075Features',
        'BarcelonaIsInternalUser',
    )

    _TESTS = [{
        'url': 'https://www.threads.net/@tntsportsbr/post/C6cqebdCfBi',
        'info_dict': {
            'id': 'C6cqebdCfBi',
            'ext': 'mp4',
            'title': 'md5:88b3499a0f6deea8eb9f9c3d8b19426a',
            'description': 'md5:fd7e60350eb0f58f2bbf96cd0de25bae',
            'uploader': 'TNT Sports Brasil',
            'uploader_id': 'tntsportsbr',
            'uploader_url': 'https://www.threads.net/@tntsportsbr',
            'channel': 'tntsportsbr',
            'channel_url': 'https://www.threads.net/@tntsportsbr',
            'timestamp': 1714613811,
            'upload_date': '20240502',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'barcelona://media?shortcode=C6fDehepo5D',
        'only_matching': True,
    }]

    def _extract_graphql_media(self, url, video_id, lsd):
        variables = {
            'postID': str(decode_base_n(video_id, table=_ENCODING_CHARS)),
            **{
                f'__relay_internal__pv__{provider}relayprovider': False
                for provider in self._GRAPHQL_BOOL_PROVIDERS
            },
        }
        data = self._download_json(
            'https://www.threads.net/api/graphql', video_id,
            data=urlencode_postdata({
                'lsd': lsd,
                'variables': json.dumps(variables, separators=(',', ':')),
                'doc_id': self._GRAPHQL_DOC_ID,
            }), headers={
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'https://www.threads.net',
                'Pragma': 'no-cache',
                'Referer': url,
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': self._WEB_UA,
                'X-ASBD-ID': '129477',
                'X-FB-Friendly-Name': self._GRAPHQL_FRIENDLY_NAME,
                'X-FB-LSD': lsd,
                'X-IG-App-ID': '238260118697367',
                'X-Requested-With': 'XMLHttpRequest',
            })
        return traverse_obj(data, ('data', 'media', {dict}))

    def _extract_video_entry(self, media, video_id, idx, total):
        formats = [{
            'format_id': str(fmt.get('type')) if fmt.get('type') is not None else None,
            'url': fmt.get('url'),
            'width': int_or_none(media.get('original_width')),
            'height': int_or_none(media.get('original_height')),
            'http_headers': {
                'Referer': 'https://www.threads.net/',
            },
        } for fmt in media.get('video_versions') or [] if url_or_none(fmt.get('url'))]

        if not formats:
            return None

        return {
            'id': video_id if total == 1 else f'{video_id}-{idx}',
            'formats': formats,
            'thumbnails': [{
                'url': thumb.get('url'),
                'width': int_or_none(thumb.get('width')),
                'height': int_or_none(thumb.get('height')),
            } for thumb in traverse_obj(media, ('image_versions2', 'candidates', lambda _, v: url_or_none(v['url'])))] or None,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            f'https://www.threads.net/t/{video_id}', video_id,
            headers={'User-Agent': self._WEB_UA})

        lsd = self._search_regex(
            r'"LSD",\[\],\{"token":"(\w+)"\},\d+\]', webpage,
            'LSD token', default='1')

        media = self._extract_graphql_media(url, video_id, lsd)
        if not media:
            raise self.raise_no_formats('Unable to extract post metadata from Threads API', expected=True)

        entries = list(filter(None, (
            self._extract_video_entry(item, video_id, idx, len(media.get('carousel_media') or [media]))
            for idx, item in enumerate(media.get('carousel_media') or [media], 1))))
        if not entries:
            raise self.raise_no_formats('No video formats found in this Threads post', expected=True)

        og_title = self._og_search_title(webpage, default='')
        uploader_id = traverse_obj(media, ('user', 'username')) or self._search_regex(
            r'threads\.(?:net|com)/@([^/?#]+)/', url, 'uploader id', default=None)
        if not uploader_id:
            uploader_id = self._search_regex(r'\(@([^\s)]+)\)', og_title, 'uploader id', default=None)

        info = {
            'title': strip_or_none(remove_end(self._html_extract_title(webpage), '• Threads')),
            'description': self._og_search_description(webpage, default=None),
            'uploader': self._search_regex(r'^(.*?)\s*\(@', og_title, 'uploader', default=None),
            'uploader_id': uploader_id,
            'uploader_url': f'https://www.threads.net/@{uploader_id}' if uploader_id else None,
            'channel': uploader_id,
            'channel_url': f'https://www.threads.net/@{uploader_id}' if uploader_id else None,
            'timestamp': int_or_none(media.get('taken_at')),
            'like_count': int_or_none(media.get('like_count')),
            'comment_count': int_or_none(traverse_obj(media, ('text_post_app_info', 'direct_reply_count'))),
        }

        if len(entries) == 1:
            return {
                **info,
                **entries[0],
            }

        for entry in entries:
            entry.update(info)

        return self.playlist_result(entries, video_id, info.get('title'), info.get('description'))


class ThreadsIOSIE(InfoExtractor):
    IE_DESC = 'IOS barcelona:// URL'
    _VALID_URL = r'barcelona://media\?shortcode=(?P<id>[^/?#&]+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(f'https://www.threads.net/t/{video_id}', ThreadsIE, video_id)
