from .common import InfoExtractor
from ..utils import float_or_none, xpath_text


class NuevoBaseIE(InfoExtractor):
    def _extract_nuevo(self, config_url, video_id, headers={}):
        config = self._download_xml(
            config_url, video_id, transform_source=lambda s: s.strip(),
            headers=headers)

        title = xpath_text(config, './title', 'title', fatal=True).strip()
        video_id = xpath_text(config, './mediaid', default=video_id)
        thumbnail = xpath_text(config, ['./image', './thumb'])
        duration = float_or_none(xpath_text(config, './duration'))

        formats = []
        for element_name, format_id in (('file', 'sd'), ('filehd', 'hd')):
            video_url = xpath_text(config, element_name)
            if video_url:
                formats.append({
                    'url': video_url,
                    'format_id': format_id,
                })
        self._check_formats(formats, video_id)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats
        }
