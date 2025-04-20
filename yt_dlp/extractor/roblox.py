from .common import InfoExtractor
from ..postprocessor.ffmpeg import FFmpegPostProcessor
from ..utils import (
    ExtractorError,
    extract_attributes,
    float_or_none,
    get_element_by_id,
    get_element_by_class,
    get_element_html_by_class,
    get_element_html_by_id,
    int_or_none,
    PostProcessingError,
    strip_or_none,
    str_or_none,
    str_to_int,
    traverse_obj,
    try_call,
    unified_timestamp,
)


class RobloxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?roblox\.com/library/(?P<id>\d+)'
    _TESTS = [{
        # UGC Audio
        'url': 'https://www.roblox.com/library/7910582982/Backrooms-Ambiance-High-Quality',
        'md5': '',
        'info_dict': {
            'id': '7910582982',
            'ext': 'ogg',
            'title': 'Backrooms Ambiance (High Quality)',
            'description': 'Found an actual higher quality of the sound.',
            'uploader': 'ChaseDJ549',
            'uploader_id': '412014916',
            'categories': ['Horror'],
            'like_count': int,
            'timestamp': 1636142127,
            'modified_timestamp': 1656694893
        },
    }]

    def _real_extract(self, url):
        asset_id = self._match_id(url)
        webpage = self._download_webpage(url, asset_id)

        item_container_div = get_element_html_by_id('item-container', webpage)
        item_container_attrs = extract_attributes(item_container_div[:item_container_div.find('>')+1])
        asset_type = item_container_attrs.get('data-asset-type')
        if asset_type and (asset_type not in ('Audio', 'Video')):
            raise ExtractorError('This asset is not an audio/video', expected=True)
        asset_uploader_id, asset_uploader_name = self._search_regex(
            r'>By <a.+href=["\']https?://(?:www\.)?roblox\.com/users/(?P<id>\d+)[^"\']*["\'][^>]*>@?(?P<name>\w+)</a',
            webpage, 'asset creator', fatal=False, group=('id', 'name'))

        is_logged_out = not self._get_cookies('https://roblox.com').get('.ROBLOSECURITY')
        toolbox_result = traverse_obj(
            self._download_json(f'https://apis.roblox.com/toolbox-service/v1/items/details', asset_id, query={'assetIds': asset_id},
                                note='Downloading extra metadata JSON', errnote=False if is_logged_out else 'Unable to download extra metadata JSON',
                                fatal=False),
            ('data', ...), default={}, expected_type=dict, get_all=False)
        toolbox_asset_data = toolbox_result.get('asset') or {}
        toolbox_creator_data = toolbox_result.get('creator') or {}
        toolbox_audio_data = toolbox_asset_data.get('audioDetails') or {}

        info_dict = {
            'id': asset_id,
            'title': toolbox_asset_data.get('name') or item_container_attrs.get('data-item-name'),
            'uploader': toolbox_creator_data.get('name') or asset_uploader_name,
            'uploader_id': str_or_none(toolbox_creator_data.get('id')) or asset_uploader_id,
            # TODO: Sound effects have separate kinds of categories 
            'categories': toolbox_asset_data.get('assetGenres') or [strip_or_none(get_element_by_class('item-genre', webpage))],
            'like_count': str_to_int(extract_attributes(get_element_html_by_class('favoriteCount', webpage)).get('title')),
            'timestamp': unified_timestamp(toolbox_asset_data.get('createdUtc')),
            'modified_timestamp': unified_timestamp(toolbox_asset_data.get('updatedUtc')),  # TODO: Extract from webpage
            'track': toolbox_audio_data.get('title'),
            'artist': toolbox_audio_data.get('artist'),
            'genre': try_call(lambda: toolbox_audio_data['musicGenre'].capitalize())
        }

        cdn_result = self._download_json(
            f'https://assetdelivery.roblox.com/v1/assetId/{asset_id}',
            asset_id, note='Downloading file data JSON', headers={
                'Accept': 'application/json',
                'roblox-browser-asset-request': 'true'
            })
        asset_file_url = cdn_result.get('location')
        if not asset_file_url:
            if asset_type == 'Audio':
                media_play_icon_div = get_element_html_by_class('MediaPlayerIcon')
                if not media_play_icon_div:
                    self.raise_no_formats('This audio is unavailable', expected=True, video_id=asset_id)
                asset_file_url = self._search_regex(r'data-mediathumb-url=["\']https?://[^"\']+["\']', media_play_icon_div, 'audio preview URL')
            elif is_logged_out:  # assetdelivery API randomly requires auth cookies
                self.raise_login_required(metadata_available=True)
            else:
                self.raise_no_formats(
                    traverse_obj(cdn_result, ('errors', ..., 'message'), default='Unable to fetch asset', expected_type=str, get_all=False),
                    video_id=asset_id)

        if asset_file_url:
            # Assets have no file extension and use binary/octet-stream as Content-Type
            pp = FFmpegPostProcessor(self._downloader)
            self.to_screen(f'{asset_id}: Checking file format with ffprobe')
            try:
                metadata = pp.get_metadata_object(asset_file_url)
            except PostProcessingError as err:
                raise ExtractorError(err.msg, expected=True)

            v_stream = a_stream = {}
            for stream in metadata['streams']:
                if stream['codec_type'] == 'video':
                    v_stream = stream
                elif stream['codec_type'] == 'audio':
                    a_stream = stream

            info_dict['formats'] = [{
                'url': asset_file_url,
                'ext': 'mp4' if 'mp4' in metadata['format']['format_name'] else metadata['format']['format_name'].split(',')[-1],
                'vcodec': v_stream.get('codec_name'),
                'acodec': a_stream.get('codec_name'),
                'tbr': int_or_none(metadata['format'].get('bit_rate'), scale=1000),
                'vbr': int_or_none(v_stream.get('bit_rate'), scale=1000),
                'abr': int_or_none(a_stream.get('bit_rate'), scale=1000),
                'height': int_or_none(v_stream.get('height')),
                'width': int_or_none(v_stream.get('width')),
                'filesize': float_or_none(metadata['format'].get('size'))
            }]

        return info_dict
