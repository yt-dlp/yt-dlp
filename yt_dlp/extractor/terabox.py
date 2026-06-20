import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class TeraBoxIE(InfoExtractor):
    IE_NAME = 'terabox'
    IE_DESC = 'TeraBox shared video links'

    _VALID_URL = r'https?://(?:www\.)?(?:terabox(?:app)?\.com|1024tera\.com|teraboxurl\.com|freeterabox\.com|nephobox\.com|4funbox\.com|mirrobox\.com|momerybox\.com|tibibox\.com|sendcmb\.com)/(?:s/|sharing/link\?surl=)(?P<id>[A-Za-z0-9_-]+)'

    _TESTS = [{
        'url': 'https://terabox.com/s/1GL046gf5vYj3Lg0mAiKzcw',
        'info_dict': {
            'id': '1GL046gf5vYj3Lg0mAiKzcw',
            'ext': 'mp4',
            'title': str,
            'thumbnail': r're:^https?://.+',
        },
        'skip': 'Requires cookies',
    }, {
        'url': 'https://www.1024tera.com/sharing/link?surl=GL046gf5vYj3Lg0mAiKzcw',
        'only_matching': True,
    }, {
        'url': 'https://freeterabox.com/s/1GL046gf5vYj3Lg0mAiKzcw',
        'only_matching': True,
    }, {
        'url': 'https://teraboxapp.com/s/1GL046gf5vYj3Lg0mAiKzcw',
        'only_matching': True,
    }]

    _DOMAINS = [
        'www.terabox.com',
        'www.1024tera.com',
        'teraboxapp.com',
        'freeterabox.com',
        'nephobox.com',
        '4funbox.com',
        'mirrobox.com',
        'momerybox.com',
        'tibibox.com',
        'sendcmb.com',
    ]

    def _get_surl(self, url):
        """Extract the surl/shorturl token from the URL."""
        mobj = re.search(r'/s/([A-Za-z0-9_-]+)', url)
        if mobj:
            return mobj.group(1)
        mobj = re.search(r'[?&]surl=([A-Za-z0-9_-]+)', url)
        if mobj:
            return mobj.group(1)
        return self._match_id(url)

    def _get_base_domain(self, url):
        """Determine the API base domain from the URL."""
        for domain in self._DOMAINS:
            if domain in url:
                return domain
        return 'www.1024tera.com'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        surl = self._get_surl(url)
        base_domain = self._get_base_domain(url)

        self._download_webpage(
            url, video_id,
            note='Downloading share page',
            errnote='Unable to download share page',
        )

        share_info = self._download_json(
            f'https://{base_domain}/api/shorturlinfo',
            video_id,
            note='Downloading share info',
            errnote='Unable to download share info',
            query={'shorturl': surl, 'root': '1'},
            fatal=False,
        )

        if not share_info:
            share_info = self._download_json(
                f'https://{base_domain}/share/list',
                video_id,
                note='Downloading share list (fallback)',
                errnote='Unable to download share list',
                query={
                    'shorturl': surl,
                    'root': '1',
                    'page': '1',
                    'num': '20',
                    'order': 'time',
                },
                fatal=False,
            )

        errno = traverse_obj(share_info, 'errno')
        if not share_info or errno not in (0, None):
            errmsg = traverse_obj(share_info, 'errmsg', default='')

            if errno in (-6, 4):
                raise ExtractorError(
                    'This link requires authentication. '
                    'Use --cookies-from-browser or --cookies to provide TeraBox cookies',
                    expected=True,
                )
            elif errno == -9:
                raise ExtractorError(
                    'This file is no longer available (deleted or expired)',
                    expected=True,
                )
            raise ExtractorError(
                f'TeraBox API error {errno}: {errmsg}',
                expected=True,
            )

        file_list = (
            traverse_obj(share_info, ('list', ...))
            or traverse_obj(share_info, ('info', ...))
            or []
        )

        video_info = None
        for item in file_list:
            # category: 1 = video, 12 = video variant
            if (not int_or_none(item.get('isdir'))
                    and str_or_none(item.get('category')) in ('1', '12')):
                video_info = item
                break

        if not video_info and file_list:
            video_info = file_list[0]

        if not video_info:
            raise ExtractorError('No video file found in this share link', expected=True)

        fs_id = str_or_none(video_info.get('fs_id'))
        title = str_or_none(
            video_info.get('server_filename')
            or video_info.get('filename'),
        ) or video_id

        # Remove common video file extensions from title
        title = re.sub(r'\.(mp4|mkv|avi|mov|flv|wmv|webm|m4v)$', '', title, flags=re.IGNORECASE)

        thumbnail = traverse_obj(video_info, (
            'thumbs', ('url3', 'url2', 'url1'),
            {url_or_none}, any,
        ))

        dlink = url_or_none(video_info.get('dlink'))

        if not dlink and fs_id:
            sign = traverse_obj(share_info, ('sign', {str}), default='')
            timestamp = traverse_obj(share_info, ('timestamp', {str_or_none}), default='')

            filemetas = self._download_json(
                f'https://{base_domain}/api/filemetas',
                video_id,
                note='Downloading file metadata',
                errnote='Unable to download file metadata',
                query={
                    'shorturl': surl,
                    'sign': sign,
                    'timestamp': timestamp,
                    'fsids': f'[{fs_id}]',
                    'dlink': '1',
                    'thumb': '1',
                    'needmedia': '1',
                },
                fatal=False,
            )

            if traverse_obj(filemetas, 'errno') == 0:
                meta = traverse_obj(filemetas, ('info', 0))
                if meta:
                    dlink = url_or_none(meta.get('dlink'))
                    thumbnail = thumbnail or traverse_obj(meta, (
                        'thumbs', ('url3', 'url2'), {url_or_none}, any,
                    ))

        if not dlink:
            raise ExtractorError(
                'Could not extract the download link. '
                'Use --cookies-from-browser or --cookies to provide TeraBox cookies',
                expected=True,
            )

        return {
            'id': fs_id or video_id,
            'title': title,
            'thumbnail': thumbnail,
            'filesize': int_or_none(video_info.get('size')),
            'formats': [{
                'url': dlink,
                'ext': 'mp4',
                'format_id': 'direct',
                'quality': 1,
                'http_headers': {
                    'Referer': f'https://{base_domain}/',
                },
            }],
        }
