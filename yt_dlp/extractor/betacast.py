import re

from .common import InfoExtractor
from ..utils import (
    format_field,
    get_element_by_class,
    get_element_by_id,
    int_or_none,
    strip_or_none,
    unescapeHTML,
    unified_strdate,
)


class BetaCastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?betacast\.(?:cc|lol|org)/watch\?.*?\bv=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.betacast.org/watch?v=3',
        'info_dict': {
            'id': '3',
            'title': 'first video',
            'ext': 'mp4',
            'thumbnail': 'https://betacast-content-evrp.wkmx.org/vi/thumb/video-635207f8b4aee8.03792079.jpg',
            'description': 'first video that you can watch',
            'uploader': 'Evie',
            'license': 'Standard BetaCast License',
            'upload_date': '20220426',
            'channel_id': 'UCOOab5RocRDa8j7EeNngq',
            'channel_url': 'https://www.betacast.org/channel/UCOOab5RocRDa8j7EeNngq',
            'channel_follower_count': int,
            'channel_is_verified': bool,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'categories': ['Entertainment'],
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).lstrip('0')

        webpage = self._download_webpage(
            f'https://www.betacast.org/watch?v={video_id}', video_id)

        title = unescapeHTML(self._search_regex(
            r'<meta name="twitter:title" content="([^"]*)', webpage, 'title', fatal=False))

        description = unescapeHTML(self._search_regex(
            r'<meta name="twitter:description" content="([^"]*)', webpage, 'description', fatal=False))

        channel_id = self._search_regex(
            r'<!-- start channel: (UC[\w-]+) -->', webpage, 'channel id', fatal=False)

        comment_count = int_or_none(self._search_regex(
            r'<strong>Comments \((\d+)\)</strong>', webpage, 'comment count', fatal=False))

        comments = []
        for author_thumbnail, author_url, author, author_is_verified, text, comment_id, like_count in re.findall(r'<img src="([^"]*)" width="48">.*?<a href="([^"]*)" dir="ltr">([^<]*)</a></?span( class="qualified-channel-title-badge">)?.*?<div class="comment-text"[^>]*>\n<p>([^<]*)</p>.*?<button.*?"reply\((\d+).*?<span style="color: green">(\d+)', re.sub('<a href="[^"]*">([^<]*)</a>', '\\1', webpage), re.DOTALL):
            comments.append({
                'author': unescapeHTML(author),
                'author_thumbnail': re.sub('^/', 'https://www.betacast.org/', unescapeHTML(author_thumbnail)),
                'author_url': re.sub('^/', 'https://www.betacast.org/', unescapeHTML(author_url)),
                'author_is_verified': author_is_verified != '',
                'id': int_or_none(comment_id),
                'text': unescapeHTML(text),
                'like_count': int_or_none(like_count),
            })

        category = self._html_search_regex(
            r'<p id="eow-category"><a href="[^"]*">([^<]*)', webpage,
            'category', fatal=False)
        categories = [category] if category else None

        return {
            'id': video_id,
            'title': title,
            'url': self._html_search_meta('twitter:player', webpage),
            'thumbnail': self._html_search_meta('twitter:image', webpage),
            'description': description,
            'uploader': get_element_by_class('yt-user-name', webpage),
            'license': strip_or_none(get_element_by_id('eow-reuse', webpage)),
            'upload_date': unified_strdate(get_element_by_id('eow-date', webpage)),
            'channel_id': channel_id,
            'channel_url': format_field(channel_id, None, 'https://www.betacast.org/channel/%s'),
            'channel_follower_count': int_or_none(get_element_by_class('subscribed', webpage)),
            'channel_is_verified': '</a><span class="yt-user-name-icon-verified">' in webpage,
            'view_count': int_or_none(get_element_by_class('watch-view-count', webpage)),
            'like_count': int_or_none(get_element_by_class('likes-count', webpage)),
            'dislike_count': int_or_none(get_element_by_class('dislikes-count', webpage)),
            'comment_count': comment_count,
            'comments': comments,
            'categories': categories,
        }
