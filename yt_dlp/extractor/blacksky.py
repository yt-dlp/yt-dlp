
from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    str_or_none,
    unified_strdate,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class BlackSkyIE(InfoExtractor):
    _VALID_URL = r'https://?(?:www\.)?blacksky\.community/profile/(?P<did>[^?#&]+)/post/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://blacksky.community/profile/did:plc:tpv66pk3fqlpfudmh5zi3hzo/post/3mgjxbnwktk26',
        'info_dict': {
            'id': 'did:plc:tpv66pk3fqlpfudmh5zi3hzo',
            'title': 'Post by did:plc:tpv66pk3fqlpfudmh5zi3hzo',
        },
        'playlist_count': 6,
    }, {
        # Youtube embed
        'url': 'https://blacksky.community/profile/did:plc:cs675sj2rlghz65p4hzii7b6/post/3mgaihdgzmc2v',
        'info_dict': {
            'id': 'did:plc:cs675sj2rlghz65p4hzii7b6',
            'title': 'Post by did:plc:cs675sj2rlghz65p4hzii7b6',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://blacksky.community/profile/did:plc:lsjo5pnx6byjoo27omtcoyly/post/3mfsayc6adk2w',
        'only_matching': True,
    }]

    def _parse_threads(self, data):
        for idx, post in enumerate(traverse_obj(data, ('thread', ..., 'value', 'post'))):
            embed = post.get('embed')
            if not embed:
                continue
            did = traverse_obj(post, ('author', 'did'))
            username = traverse_obj(post, ('author', 'displayName'))
            default_metadata = {
                'id': did,
                'title': f'Post by {username}' if idx == 0 else f'Comment by {username}_{idx}',
                **traverse_obj(post, ({
                    'description': ('record', 'text', {str_or_none}),
                    'thumbnail': ('thumbnail', {url_or_none}),
                    'upload_date': ('indexedAt', {unified_strdate}),
                    'like_count': ('likeCount', {int_or_none}),
                    'repost_count': ('repostCount', {int_or_none}),
                    'tags': ('labels', ..., 'val'),
                })),
                'uploader_id': did,
                'uploader_url': f'https://blacksky.community/profile/{did}',
                'http_headers': {'referer': 'https://blacksky.community/'},
            }

            fmt_urls = traverse_obj(embed,
                                    ('playlist'),
                                    ('record', 'embeds', ..., 'playlist'),
                                    ('record', 'record', 'embeds', ..., 'playlist'))
            fmt_urls = [fmt_urls] if isinstance(fmt_urls, str) else fmt_urls
            for fmt_url in fmt_urls:
                formats = self._extract_m3u8_formats(fmt_url, did, headers={'referer': 'https://blacksky.community/'})
                yield {
                    **default_metadata,
                    'formats': formats,
                }

            if external_url := traverse_obj(embed, ('external', 'uri', {url_or_none})):
                ext = determine_ext(external_url)
                if ext == 'gif':
                    yield {
                        **default_metadata,
                        'url': external_url,
                        'ext': 'gif',
                    }
                else:
                    yield self.url_result(external_url, video_id=did)

    def _real_extract(self, url):
        did, pid = self._match_valid_url(url).groups()

        def entries(did, pid):
            try:
                data = self._download_json(
                    'https://api.blacksky.community/xrpc/app.bsky.unspecced.getPostThreadV2',
                    did,
                    query={
                        'anchor': f'at://{did}/app.bsky.feed.post/{pid}',
                        'branchingFactor': 1,
                        'below': 10,
                        'sort': 'top',
                    })
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status in (401, 403):
                    self.raise_login_required()
                raise

            if data.get('hasOtherReplies'):
                # TODO: Add support for hasOtherReplies for other replies
                pass

            return self._parse_threads(data)
        return self.playlist_result(entries(did, pid), did, f'Post by {did}')
