from .common import InfoExtractor
from ..utils import (
    unified_strdate,
    xpath_text,
)


class CinchcastIE(InfoExtractor):
    _VALID_URL = r'https?://player\.cinchcast\.com/.*?(?:assetId|show_id)=(?P<id>[0-9]+)'
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>https?://player\.cinchcast\.com/.+?)\1']

    _TESTS = [{
        'url': 'http://player.cinchcast.com/?show_id=5258197&platformId=1&assetType=single',
        'info_dict': {
            'id': '5258197',
            'ext': 'mp3',
            'title': 'Train Your Brain to Up Your Game with Coach Mandy',
            'upload_date': '20130816',
        },
    }, {
        # Actual test is run in generic, look for undergroundwellness
        'url': 'http://player.cinchcast.com/?platformId=1&#038;assetType=single&#038;assetId=7141703',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        doc = self._download_xml(
            'http://www.blogtalkradio.com/playerasset/mrss?assetType=single&assetId=%s' % video_id,
            video_id)

        item = doc.find('.//item')
        title = xpath_text(item, './title', fatal=True)
        date_str = xpath_text(
            item, './{http://developer.longtailvideo.com/trac/}date')
        upload_date = unified_strdate(date_str, day_first=False)
        # duration is present but wrong
        formats = [{
            'format_id': 'main',
            'url': item.find('./{http://search.yahoo.com/mrss/}content').attrib['url'],
        }]
        backup_url = xpath_text(
            item, './{http://developer.longtailvideo.com/trac/}backupContent')
        if backup_url:
            formats.append({
                'preference': 2,  # seems to be more reliable
                'format_id': 'backup',
                'url': backup_url,
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'upload_date': upload_date,
            'formats': formats,
        }
