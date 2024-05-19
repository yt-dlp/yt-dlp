from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    mimetype2ext,
    parse_iso8601,
    strip_jsonp,
    unified_timestamp,
    url_or_none,
)


class AMPIE(InfoExtractor):  # XXX: Conventionally, base classes should end with BaseIE/InfoExtractor
    # parse Akamai Adaptive Media Player feed
    def _extract_feed_info(self, url):
        feed = self._download_json(
            url, None, 'Downloading Akamai AMP feed',
            'Unable to download Akamai AMP feed', transform_source=strip_jsonp)
        item = feed.get('channel', {}).get('item')
        if not item:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, feed['error']))

        video_id = item['guid']

        def get_media_node(name, default=None):
            media_name = 'media-%s' % name
            media_group = item.get('media-group') or item
            return media_group.get(media_name) or item.get(media_name) or item.get(name, default)

        thumbnails = []
        media_thumbnail = get_media_node('thumbnail')
        if media_thumbnail:
            if isinstance(media_thumbnail, dict):
                media_thumbnail = [media_thumbnail]
            for thumbnail_data in media_thumbnail:
                thumbnail = thumbnail_data.get('@attributes', {})
                thumbnail_url = url_or_none(thumbnail.get('url'))
                if not thumbnail_url:
                    continue
                thumbnails.append({
                    'url': self._proto_relative_url(thumbnail_url, 'http:'),
                    'width': int_or_none(thumbnail.get('width')),
                    'height': int_or_none(thumbnail.get('height')),
                })

        subtitles = {}
        media_subtitle = get_media_node('subTitle')
        if media_subtitle:
            if isinstance(media_subtitle, dict):
                media_subtitle = [media_subtitle]
            for subtitle_data in media_subtitle:
                subtitle = subtitle_data.get('@attributes', {})
                subtitle_href = url_or_none(subtitle.get('href'))
                if not subtitle_href:
                    continue
                subtitles.setdefault(subtitle.get('lang') or 'en', []).append({
                    'url': subtitle_href,
                    'ext': mimetype2ext(subtitle.get('type')) or determine_ext(subtitle_href),
                })

        formats = []
        media_content = get_media_node('content')
        if isinstance(media_content, dict):
            media_content = [media_content]
        for media_data in media_content:
            media = media_data.get('@attributes', {})
            media_url = url_or_none(media.get('url'))
            if not media_url:
                continue
            ext = mimetype2ext(media.get('type')) or determine_ext(media_url)
            if ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    media_url + '?hdcore=3.4.0&plugin=aasp-3.4.0.132.124',
                    video_id, f4m_id='hds', fatal=False))
            elif ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    media_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'format_id': media_data.get('media-category', {}).get('@attributes', {}).get('label'),
                    'url': media_url,
                    'tbr': int_or_none(media.get('bitrate')),
                    'filesize': int_or_none(media.get('fileSize')),
                    'ext': ext,
                })

        timestamp = unified_timestamp(item.get('pubDate'), ' ') or parse_iso8601(item.get('dc-date'))

        return {
            'id': video_id,
            'title': get_media_node('title'),
            'description': get_media_node('description'),
            'thumbnails': thumbnails,
            'timestamp': timestamp,
            'duration': int_or_none(media_content[0].get('@attributes', {}).get('duration')),
            'subtitles': subtitles,
            'formats': formats,
        }
