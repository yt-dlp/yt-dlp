import re

from .common import InfoExtractor
from ..utils import (
    dict_get,
    ExtractorError,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    try_get,
    unescapeHTML,
)


class PikselIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://
        (?:
            (?:
                player\.
                    (?:
                        olympusattelecom|
                        vibebyvista
                    )|
                (?:api|player)\.multicastmedia|
                (?:api-ovp|player)\.piksel
            )\.com|
            (?:
                mz-edge\.stream\.co|
                movie-s\.nhk\.or
            )\.jp|
            vidego\.baltimorecity\.gov
        )/v/(?:refid/(?P<refid>[^/]+)/prefid/)?(?P<id>[\w-]+)'''
    _EMBED_REGEX = [r'<iframe[^>]+src=["\'](?P<url>(?:https?:)?//player\.piksel\.com/v/[a-z0-9]+)']
    _TESTS = [
        {
            'url': 'http://player.piksel.com/v/ums2867l',
            'md5': '34e34c8d89dc2559976a6079db531e85',
            'info_dict': {
                'id': 'ums2867l',
                'ext': 'mp4',
                'title': 'GX-005 with Caption',
                'timestamp': 1481335659,
                'upload_date': '20161210'
            }
        },
        {
            # Original source: http://www.uscourts.gov/cameras-courts/state-washington-vs-donald-j-trump-et-al
            'url': 'https://player.piksel.com/v/v80kqp41',
            'md5': '753ddcd8cc8e4fa2dda4b7be0e77744d',
            'info_dict': {
                'id': 'v80kqp41',
                'ext': 'mp4',
                'title': 'WAW- State of Washington vs. Donald J. Trump, et al',
                'description': 'State of Washington vs. Donald J. Trump, et al, Case Number 17-CV-00141-JLR, TRO Hearing, Civil Rights Case, 02/3/2017, 1:00 PM (PST), Seattle Federal Courthouse, Seattle, WA, Judge James L. Robart presiding.',
                'timestamp': 1486171129,
                'upload_date': '20170204'
            }
        },
        {
            # https://www3.nhk.or.jp/nhkworld/en/ondemand/video/2019240/
            'url': 'http://player.piksel.com/v/refid/nhkworld/prefid/nw_vod_v_en_2019_240_20190823233000_02_1566873477',
            'only_matching': True,
        }
    ]

    def _call_api(self, app_token, resource, display_id, query, fatal=True):
        response = (self._download_json(
            'http://player.piksel.com/ws/ws_%s/api/%s/mode/json/apiv/5' % (resource, app_token),
            display_id, query=query, fatal=fatal) or {}).get('response')
        failure = try_get(response, lambda x: x['failure']['reason'])
        if failure:
            if fatal:
                raise ExtractorError(failure, expected=True)
            self.report_warning(failure)
        return response

    def _real_extract(self, url):
        ref_id, display_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, display_id)
        app_token = self._search_regex([
            r'clientAPI\s*:\s*"([^"]+)"',
            r'data-de-api-key\s*=\s*"([^"]+)"'
        ], webpage, 'app token')
        query = {'refid': ref_id, 'prefid': display_id} if ref_id else {'v': display_id}
        program = self._call_api(
            app_token, 'program', display_id, query)['WsProgramResponse']['program']
        video_id = program['uuid']
        video_data = program['asset']
        title = video_data['title']
        asset_type = dict_get(video_data, ['assetType', 'asset_type'])

        formats = []

        def process_asset_file(asset_file):
            if not asset_file:
                return
            # TODO: extract rtmp formats
            http_url = asset_file.get('http_url')
            if not http_url:
                return
            tbr = None
            vbr = int_or_none(asset_file.get('videoBitrate'), 1024)
            abr = int_or_none(asset_file.get('audioBitrate'), 1024)
            if asset_type == 'video':
                tbr = vbr + abr
            elif asset_type == 'audio':
                tbr = abr

            formats.append({
                'format_id': join_nonempty('http', tbr),
                'url': unescapeHTML(http_url),
                'vbr': vbr,
                'abr': abr,
                'width': int_or_none(asset_file.get('videoWidth')),
                'height': int_or_none(asset_file.get('videoHeight')),
                'filesize': int_or_none(asset_file.get('filesize')),
                'tbr': tbr,
            })

        def process_asset_files(asset_files):
            for asset_file in (asset_files or []):
                process_asset_file(asset_file)

        process_asset_files(video_data.get('assetFiles'))
        process_asset_file(video_data.get('referenceFile'))
        if not formats:
            asset_id = video_data.get('assetid') or program.get('assetid')
            if asset_id:
                process_asset_files(try_get(self._call_api(
                    app_token, 'asset_file', display_id, {
                        'assetid': asset_id,
                    }, False), lambda x: x['WsAssetFileResponse']['AssetFiles']))

        m3u8_url = dict_get(video_data, [
            'm3u8iPadURL',
            'ipadM3u8Url',
            'm3u8AndroidURL',
            'm3u8iPhoneURL',
            'iphoneM3u8Url'])
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False))

        smil_url = dict_get(video_data, ['httpSmil', 'hdSmil', 'rtmpSmil'])
        if smil_url:
            transform_source = None
            if ref_id == 'nhkworld':
                # TODO: figure out if this is something to be fixed in urljoin,
                # _parse_smil_formats or keep it here
                transform_source = lambda x: x.replace('src="/', 'src="').replace('/media"', '/media/"')
            formats.extend(self._extract_smil_formats(
                re.sub(r'/od/[^/]+/', '/od/http/', smil_url), video_id,
                transform_source=transform_source, fatal=False))

        subtitles = {}
        for caption in video_data.get('captions', []):
            caption_url = caption.get('url')
            if caption_url:
                subtitles.setdefault(caption.get('locale', 'en'), []).append({
                    'url': caption_url})

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'thumbnail': video_data.get('thumbnailUrl'),
            'timestamp': parse_iso8601(video_data.get('dateadd')),
            'formats': formats,
            'subtitles': subtitles,
            '_format_sort_fields': ('tbr', ),  # Incomplete resolution information
        }
