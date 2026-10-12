
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
)


class KinescopeBaseIE(InfoExtractor):

    def _get_video_info(self, media_id, token, fatal=False, **kwargs):
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        video_info = self._download_json(f'https://api.kinescope.io/v1/videos/{media_id}',
                                         media_id, fatal=fatal, headers=headers, **kwargs)
        if traverse_obj(video_info, 'error'):
            raise self._error_or_warning(ExtractorError(
                f'Kinescope said: {video_info["error"]}', expected=True), fatal=fatal)
        return video_info or {}

    def _get_formats(self, video_info, fatal=False, **kwargs):
        if traverse_obj(video_info, 'error'):
            raise self._error_or_warning(ExtractorError(
                f'Kinescope said: {video_info["error"]}', expected=True), fatal=fatal)
        else:
            formats = []
            for item in traverse_obj(video_info, ('data', 'assets')):
                formats.append({
                    'url': item.get('download_link'),
                    'format_id': item.get('quality'),
                    'ext': item.get('filetype'),
                    'resolution': item.get('resolution'),
                })
        return formats or {}
