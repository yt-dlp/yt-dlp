import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
    str_to_int,
    url_or_none,
    urlencode_postdata,
)


class ManyVidsIE(InfoExtractor):
    _VALID_URL = r'(?i)https?://(?:www\.)?manyvids\.com/video/(?P<id>\d+)'
    _TESTS = [{
        # preview video
        'url': 'https://www.manyvids.com/Video/133957/everthing-about-me/',
        'md5': '03f11bb21c52dd12a05be21a5c7dcc97',
        'info_dict': {
            'id': '133957',
            'ext': 'mp4',
            'title': 'everthing about me (Preview)',
            'uploader': 'ellyxxix',
            'view_count': int,
            'like_count': int,
        },
    }, {
        # full video
        'url': 'https://www.manyvids.com/Video/935718/MY-FACE-REVEAL/',
        'md5': 'bb47bab0e0802c2a60c24ef079dfe60f',
        'info_dict': {
            'id': '935718',
            'ext': 'mp4',
            'title': 'MY FACE REVEAL',
            'description': 'md5:ec5901d41808b3746fed90face161612',
            'uploader': 'Sarah Calanthe',
            'view_count': int,
            'like_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        real_url = 'https://www.manyvids.com/video/%s/gtm.js' % (video_id, )
        try:
            webpage = self._download_webpage(real_url, video_id)
        except Exception:
            # probably useless fallback
            webpage = self._download_webpage(url, video_id)

        info = self._search_regex(
            r'''(<div\b[^>]*\bid\s*=\s*(['"])pageMetaDetails\2[^>]*>)''',
            webpage, 'meta details', default='')
        info = extract_attributes(info)

        player = self._search_regex(
            r'''(<div\b[^>]*\bid\s*=\s*(['"])rmpPlayerStream\2[^>]*>)''',
            webpage, 'player details', default='')
        player = extract_attributes(player)

        video_urls_and_ids = (
            (info.get('data-meta-video'), 'video'),
            (player.get('data-video-transcoded'), 'transcoded'),
            (player.get('data-video-filepath'), 'filepath'),
            (self._og_search_video_url(webpage, secure=False, default=None), 'og_video'),
        )

        def txt_or_none(s, default=None):
            return (s.strip() or default) if isinstance(s, str) else default

        uploader = txt_or_none(info.get('data-meta-author'))

        def mung_title(s):
            if uploader:
                s = re.sub(r'^\s*%s\s+[|-]' % (re.escape(uploader), ), '', s)
            return txt_or_none(s)

        title = (
            mung_title(info.get('data-meta-title'))
            or self._html_search_regex(
                (r'<span[^>]+class=["\']item-title[^>]+>([^<]+)',
                 r'<h2[^>]+class=["\']h2 m-0["\'][^>]*>([^<]+)'),
                webpage, 'title', default=None)
            or self._html_search_meta(
                'twitter:title', webpage, 'title', fatal=True))

        title = re.sub(r'\s*[|-]\s+ManyVids\s*$', '', title) or title

        if any(p in webpage for p in ('preview_videos', '_preview.mp4')):
            title += ' (Preview)'

        mv_token = self._search_regex(
            r'data-mvtoken=(["\'])(?P<value>(?:(?!\1).)+)\1', webpage,
            'mv token', default=None, group='value')

        if mv_token:
            # Sets some cookies
            self._download_webpage(
                'https://www.manyvids.com/includes/ajax_repository/you_had_me_at_hello.php',
                video_id, note='Setting format cookies', fatal=False,
                data=urlencode_postdata({
                    'mvtoken': mv_token,
                    'vid': video_id,
                }), headers={
                    'Referer': url,
                    'X-Requested-With': 'XMLHttpRequest'
                })

        formats = []
        for v_url, fmt in video_urls_and_ids:
            v_url = url_or_none(v_url)
            if not v_url:
                continue
            if determine_ext(v_url) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    v_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls'))
            else:
                formats.append({
                    'url': v_url,
                    'format_id': fmt,
                })

        self._remove_duplicate_formats(formats)

        for f in formats:
            if f.get('height') is None:
                f['height'] = int_or_none(
                    self._search_regex(r'_(\d{2,3}[02468])_', f['url'], 'video height', default=None))
            if '/preview/' in f['url']:
                f['format_id'] = '_'.join(filter(None, (f.get('format_id'), 'preview')))
                f['preference'] = -10
            if 'transcoded' in f['format_id']:
                f['preference'] = f.get('preference', -1) - 1

        def get_likes():
            likes = self._search_regex(
                r'''(<a\b[^>]*\bdata-id\s*=\s*(['"])%s\2[^>]*>)''' % (video_id, ),
                webpage, 'likes', default='')
            likes = extract_attributes(likes)
            return int_or_none(likes.get('data-likes'))

        def get_views():
            return str_to_int(self._html_search_regex(
                r'''(?s)<span\b[^>]*\bclass\s*=["']views-wrapper\b[^>]+>.+?<span\b[^>]+>\s*(\d[\d,.]*)\s*</span>''',
                webpage, 'view count', default=None))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': txt_or_none(info.get('data-meta-description')),
            'uploader': txt_or_none(info.get('data-meta-author')),
            'thumbnail': (
                url_or_none(info.get('data-meta-image'))
                or url_or_none(player.get('data-video-screenshot'))),
            'view_count': get_views(),
            'like_count': get_likes(),
        }
