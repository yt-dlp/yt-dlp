from .common import InfoExtractor
from ..utils import (
    clean_html,
    dict_get,
    get_element_by_class,
    int_or_none,
    unified_strdate,
    url_or_none,
)


class Alsace20TVBaseIE(InfoExtractor):
    def _extract_video(self, video_id, url=None):
        info = self._download_json(
            'https://www.alsace20.tv/visionneuse/visio_v9_js.php?key=%s&habillage=0&mode=html' % (video_id, ),
            video_id) or {}
        title = info.get('titre')

        formats = []
        for res, fmt_url in (info.get('files') or {}).items():
            formats.extend(
                self._extract_smil_formats(fmt_url, video_id, fatal=False)
                if '/smil:_' in fmt_url
                else self._extract_mpd_formats(fmt_url, video_id, mpd_id=res, fatal=False))
        self._sort_formats(formats)

        webpage = (url and self._download_webpage(url, video_id, fatal=False)) or ''
        thumbnail = url_or_none(dict_get(info, ('image', 'preview', )) or self._og_search_thumbnail(webpage))
        upload_date = self._search_regex(r'/(\d{6})_', thumbnail, 'upload_date', default=None)
        upload_date = unified_strdate('20%s-%s-%s' % (upload_date[:2], upload_date[2:4], upload_date[4:])) if upload_date else None
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': clean_html(get_element_by_class('wysiwyg', webpage)),
            'upload_date': upload_date,
            'thumbnail': thumbnail,
            'duration': int_or_none(self._og_search_property('video:duration', webpage) if webpage else None),
            'view_count': int_or_none(info.get('nb_vues')),
        }


class Alsace20TVIE(Alsace20TVBaseIE):
    _VALID_URL = r'https?://(?:www\.)?alsace20\.tv/(?:[\w-]+/)+[\w-]+-(?P<id>[\w]+)'
    _TESTS = [{
        'url': 'https://www.alsace20.tv/VOD/Actu/JT/Votre-JT-jeudi-3-fevrier-lyNHCXpYJh.html',
        'info_dict': {
            'id': 'lyNHCXpYJh',
            'ext': 'mp4',
            'description': 'md5:fc0bc4a0692d3d2dba4524053de4c7b7',
            'title': 'Votre JT du jeudi 3 février',
            'upload_date': '20220203',
            'thumbnail': r're:https?://.+\.jpg',
            'duration': 1073,
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._extract_video(video_id, url)


class Alsace20TVEmbedIE(Alsace20TVBaseIE):
    _VALID_URL = r'https?://(?:www\.)?alsace20\.tv/emb/(?P<id>[\w]+)'
    _TESTS = [{
        'url': 'https://www.alsace20.tv/emb/lyNHCXpYJh',
        # 'md5': 'd91851bf9af73c0ad9b2cdf76c127fbb',
        'info_dict': {
            'id': 'lyNHCXpYJh',
            'ext': 'mp4',
            'title': 'Votre JT du jeudi 3 février',
            'upload_date': '20220203',
            'thumbnail': r're:https?://.+\.jpg',
            'view_count': int,
        },
        'params': {
            'format': 'bestvideo',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._extract_video(video_id)
