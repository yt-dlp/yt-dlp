from __future__ import unicode_literals

from .theplatform import ThePlatformFeedIE
from ..utils import (
    ExtractorError,
    int_or_none,
    find_xpath_attr,
    xpath_element,
    xpath_text,
    update_url_query,
)


class CBSBaseIE(ThePlatformFeedIE):
    def _parse_smil_subtitles(self, smil, namespace=None, subtitles_lang='en'):
        subtitles = {}
        for k, ext in [('sMPTE-TTCCURL', 'tt'), ('ClosedCaptionURL', 'ttml'), ('webVTTCaptionURL', 'vtt')]:
            cc_e = find_xpath_attr(smil, self._xpath_ns('.//param', namespace), 'name', k)
            if cc_e is not None:
                cc_url = cc_e.get('value')
                if cc_url:
                    subtitles.setdefault(subtitles_lang, []).append({
                        'ext': ext,
                        'url': cc_url,
                    })
        return subtitles


class CBSIE(CBSBaseIE):
    _VALID_URL = r'(?:cbs:|https?://(?:www\.)?(?:(?:cbs|paramountplus)\.com/shows/[^/]+/video|colbertlateshow\.com/(?:video|podcasts))/)(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://www.cbs.com/shows/garth-brooks/video/_u7W953k6la293J7EPTd9oHkSPs6Xn6_/connect-chat-feat-garth-brooks/',
        'info_dict': {
            'id': '_u7W953k6la293J7EPTd9oHkSPs6Xn6_',
            'ext': 'mp4',
            'title': 'Connect Chat feat. Garth Brooks',
            'description': 'Connect with country music singer Garth Brooks, as he chats with fans on Wednesday November 27, 2013. Be sure to tune in to Garth Brooks: Live from Las Vegas, Friday November 29, at 9/8c on CBS!',
            'duration': 1495,
            'timestamp': 1385585425,
            'upload_date': '20131127',
            'uploader': 'CBSI-NEW',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        '_skip': 'Blocked outside the US',
    }, {
        'url': 'http://colbertlateshow.com/video/8GmB0oY0McANFvp2aEffk9jZZZ2YyXxy/the-colbeard/',
        'only_matching': True,
    }, {
        'url': 'http://www.colbertlateshow.com/podcasts/dYSwjqPs_X1tvbV_P2FcPWRa_qT6akTC/in-the-bad-room-with-stephen/',
        'only_matching': True,
    }, {
        'url': 'https://www.paramountplus.com/shows/all-rise/video/QmR1WhNkh1a_IrdHZrbcRklm176X_rVc/all-rise-space/',
        'only_matching': True,
    }]

    def _extract_video_info(self, content_id, site='cbs', mpx_acc=2198311517):
        items_data = self._download_xml(
            'https://can.cbs.com/thunder/player/videoPlayerService.php',
            content_id, query={'partner': site, 'contentId': content_id})
        video_data = xpath_element(items_data, './/item')
        title = xpath_text(video_data, 'videoTitle', 'title') or xpath_text(video_data, 'videotitle', 'title')
        tp_path = 'dJ5BDC/media/guid/%d/%s' % (mpx_acc, content_id)
        tp_release_url = 'https://link.theplatform.com/s/' + tp_path

        asset_types = []
        subtitles = {}
        formats = []
        last_e = None
        for item in items_data.findall('.//item'):
            asset_type = xpath_text(item, 'assetType')
            if not asset_type or asset_type in asset_types or 'HLS_FPS' in asset_type or 'DASH_CENC' in asset_type:
                continue
            asset_types.append(asset_type)
            query = {
                'mbr': 'true',
                'assetTypes': asset_type,
            }
            if asset_type.startswith('HLS') or asset_type in ('OnceURL', 'StreamPack'):
                query['formats'] = 'MPEG4,M3U'
            elif asset_type in ('RTMP', 'WIFI', '3G'):
                query['formats'] = 'MPEG4,FLV'
            try:
                tp_formats, tp_subtitles = self._extract_theplatform_smil(
                    update_url_query(tp_release_url, query), content_id,
                    'Downloading %s SMIL data' % asset_type)
            except ExtractorError as e:
                last_e = e
                continue
            formats.extend(tp_formats)
            subtitles = self._merge_subtitles(subtitles, tp_subtitles)
        if last_e and not formats:
            raise last_e
        self._sort_formats(formats)

        info = self._extract_theplatform_metadata(tp_path, content_id)
        info.update({
            'id': content_id,
            'title': title,
            'series': xpath_text(video_data, 'seriesTitle'),
            'season_number': int_or_none(xpath_text(video_data, 'seasonNumber')),
            'episode_number': int_or_none(xpath_text(video_data, 'episodeNumber')),
            'duration': int_or_none(xpath_text(video_data, 'videoLength'), 1000),
            'thumbnail': xpath_text(video_data, 'previewImageURL'),
            'formats': formats,
            'subtitles': subtitles,
        })
        return info

    def _real_extract(self, url):
        content_id = self._match_id(url)
        return self._extract_video_info(content_id)
