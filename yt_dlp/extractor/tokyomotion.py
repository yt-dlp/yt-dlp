import datetime
import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    float_or_none,
    int_or_none,
    orderedSet,
    qualities,
    str_to_int,
)


class TokyoMotionIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tokyomotion\.net/video/(?P<id>\d+)(?:/[^/?#&]+)?'
    _TESTS = [
        {
            'url': 'https://www.tokyomotion.net/video/5580910/sexy-girls-dance-sayaka-tashiro',
            'info_dict': {
                'id': '5580910',
                'ext': 'mp4',
                'title': 'Sexy Girls Dance Sayaka Tashiro',
                'description': 'Sexy Girls Dance Sayaka Tashiro',
                'thumbnail': r're:https?://cdn\.tokyo-motion\.net/media/videos/tmb174/5580910/default\.jpg',
                'duration': 396,
                'uploader': 'yuuj_i333',
                'uploader_id': 'yuuj_i333',
                'width': 640,
                'height': 360,
                'age_limit': 18,
                'view_count': int,
                'tags': ['ミニスカ'],
            },
            'params': {'skip_download': True},
            'skip': 'Website blocks automated requests intermittently',
        },
        {
            'url': 'https://www.tokyomotion.net/video/5528180/swimsuit',
            'info_dict': {
                'id': '5528180',
                'ext': 'mp4',
                'title': 'swimsuit',
                'description': 'swimsuit',
                'thumbnail': r're:https?://cdn\.tokyo-motion\.net/media/videos/tmb172/5528180/default\.jpg',
                'duration': 1855,
                'uploader': 'lengxiaosa',
                'uploader_id': 'lengxiaosa',
                'width': 854,
                'height': 480,
                'age_limit': 18,
                'view_count': int,
                'tags': ['着エロ', 'iv'],
            },
            'params': {'skip_download': True},
            'skip': 'Website blocks automated requests intermittently',
        },
        {
            'url': 'https://www.tokyomotion.net/video/1234567/some-title',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(webpage)

        quality = qualities(('sd', 'hd'))
        referer_headers = {'Referer': url}
        formats = []
        for source in re.finditer(r'<source[^>]+>', webpage):
            attrs = extract_attributes(source.group(0))
            src = attrs.get('src')
            if not src:
                continue
            fmt = {
                'url': self._proto_relative_url(src),
                'ext': (attrs.get('type') or 'mp4').split('/')[-1],
            }
            label = attrs.get('title') or attrs.get('label') or attrs.get('data-res')
            if label:
                norm_label = label.lower()
                fmt.update(
                    {
                        'format_id': norm_label,
                        'format_note': label,
                    },
                )
                quality_value = quality(norm_label)
                if quality_value is not None:
                    fmt['quality'] = quality_value
            fmt['http_headers'] = referer_headers
            formats.append(fmt)

        if not formats:
            self.raise_no_formats('No downloadable formats found', expected=True)

        self._remove_duplicate_formats(formats)

        thumbnails = []
        video_tag = self._search_regex(r'(<video[^>]+id=["\']vjsplayer["\'][^>]*>)', webpage, 'video tag', default=None)
        if video_tag:
            video_attrs = extract_attributes(video_tag)
            for key in ('poster', 'slideimage'):
                thumb_url = video_attrs.get(key)
                if not thumb_url:
                    continue
                thumb_entry = {
                    'url': self._proto_relative_url(thumb_url),
                    'http_headers': referer_headers,
                }
                if key.lower() == 'slideimage':
                    thumb_entry.update({'id': key, 'preference': -100, 'format_note': 'sprite'})
                thumbnails.append(thumb_entry)

        thumbnail = self._proto_relative_url(self._og_search_thumbnail(webpage))
        if thumbnails:
            thumbnail = thumbnails[0]['url']
        elif thumbnail:
            thumbnails = [{'url': thumbnail, 'http_headers': referer_headers}]

        duration = float_or_none(
            self._html_search_meta(('video:duration', 'duration'), webpage, fatal=False, default=None),
        )
        if duration is None:
            duration = float_or_none(
                self._og_search_property('video:duration', webpage, default=None, fatal=False),
            )
        if duration is not None:
            duration = int(duration)

        tags = orderedSet(
            filter(
                None,
                (
                    tag.strip()
                    for tag in re.findall(r'<meta[^>]+property=["\']video:tag["\'][^>]+content=["\']([^"\']+)', webpage)
                ),
            ),
        )

        view_count = str_to_int(
            self._search_regex(
                r'<div class="pull-right big-views[^>]*>.*?<span[^>]*>[^<]*</span>,\s*<span[^>]*>([\d,]+)</span>\s*views',
                webpage,
                'view count',
                default=None,
                flags=re.DOTALL,
            ),
        )
        if view_count is None:
            view_count = str_to_int(
                self._search_regex(
                    r'<span[^>]+class="text-white"[^>]*>([\d,]+)</span>\s*views',
                    webpage,
                    'view count',
                    default=None,
                ),
            )

        uploader = self._html_search_regex(
            r'<div class="pull-left user-container">.*?<span>([^<]+)',
            webpage,
            'uploader',
            default=None,
            flags=re.DOTALL,
        )
        if uploader:
            uploader = uploader.strip()

        description = self._og_search_description(webpage)

        video_width = int_or_none(
            self._search_regex(r'var\s+video_width\s*=\s*"(\d+)"', webpage, 'video width', default=None),
        )
        video_height = int_or_none(
            self._search_regex(r'var\s+video_height\s*=\s*"(\d+)"', webpage, 'video height', default=None),
        )

        upload_date = None
        upload_timestamp = None
        relative_time = self._search_regex(
            r'>\s*(?:about\s+)?(\d+)\s+(minute|hour|day)s?\s+ago\s*<',
            webpage,
            'upload time',
            default=None,
            group=(1, 2),
            flags=re.IGNORECASE,
        )
        if relative_time:
            amount, unit = relative_time
            seconds_per_unit = {
                'minute': 60,
                'hour': 3600,
                'day': 86400,
            }
            delta_seconds = int(amount) * seconds_per_unit[unit.lower()]
            upload_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=delta_seconds)
            upload_timestamp = int(upload_dt.timestamp())
            upload_date = upload_dt.strftime('%Y%m%d')

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'thumbnails': thumbnails or None,
            'duration': duration,
            'tags': tags or None,
            'view_count': view_count,
            'uploader': uploader,
            'uploader_id': uploader,
            'width': video_width,
            'height': video_height,
            'timestamp': upload_timestamp,
            'upload_date': upload_date,
            'age_limit': 18,
            'formats': formats,
            'http_headers': referer_headers,
        }
