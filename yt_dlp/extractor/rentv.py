from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    int_or_none,
    url_or_none,
)


class RENTVIE(InfoExtractor):
    _VALID_URL = r'(?:rentv:|https?://(?:www\.)?ren\.tv/(?:player|video/epizod)/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://ren.tv/video/epizod/118577',
        'md5': 'd91851bf9af73c0ad9b2cdf76c127fbb',
        'info_dict': {
            'id': '118577',
            'ext': 'mp4',
            'title': 'Документальный спецпроект: "Промывка мозгов. Технологии XXI века"',
            'timestamp': 1472230800,
            'upload_date': '20160826',
        }
    }, {
        'url': 'http://ren.tv/player/118577',
        'only_matching': True,
    }, {
        'url': 'rentv:118577',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('http://ren.tv/player/' + video_id, video_id)
        config = self._parse_json(self._search_regex(
            r'config\s*=\s*({.+})\s*;', webpage, 'config'), video_id)
        title = config['title']
        formats = []
        for video in config['src']:
            src = url_or_none(video.get('src'))
            if not src:
                continue
            ext = determine_ext(src)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    src, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': src,
                })
        self._sort_formats(formats)
        return {
            'id': video_id,
            'title': title,
            'description': config.get('description'),
            'thumbnail': config.get('image'),
            'duration': int_or_none(config.get('duration')),
            'timestamp': int_or_none(config.get('date')),
            'formats': formats,
        }


class RENTVArticleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ren\.tv/novosti/\d{4}-\d{2}-\d{2}/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'http://ren.tv/novosti/2016-10-26/video-mikroavtobus-popavshiy-v-dtp-s-gruzovikami-v-podmoskove-prevratilsya-v',
        'md5': 'ebd63c4680b167693745ab91343df1d6',
        'info_dict': {
            'id': '136472',
            'ext': 'mp4',
            'title': 'Видео: микроавтобус, попавший в ДТП с грузовиками в Подмосковье, превратился в груду металла',
            'description': 'Жертвами столкновения двух фур и микроавтобуса, по последним данным, стали семь человек.',
        }
    }, {
        # TODO: invalid m3u8
        'url': 'http://ren.tv/novosti/2015-09-25/sluchaynyy-prohozhiy-poymal-avtougonshchika-v-murmanske-video',
        'info_dict': {
            'id': 'playlist',
            'ext': 'mp4',
            'title': 'Случайный прохожий поймал автоугонщика в Мурманске. ВИДЕО | РЕН ТВ',
            'uploader': 'ren.tv',
        },
        'params': {
            # m3u8 downloads
            'skip_download': True,
        },
        'skip': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        drupal_settings = self._parse_json(self._search_regex(
            r'jQuery\.extend\(Drupal\.settings\s*,\s*({.+?})\);',
            webpage, 'drupal settings'), display_id)

        entries = []
        for config_profile in drupal_settings.get('ren_jwplayer', {}).values():
            media_id = config_profile.get('mediaid')
            if not media_id:
                continue
            media_id = compat_str(media_id)
            entries.append(self.url_result('rentv:' + media_id, 'RENTV', media_id))
        return self.playlist_result(entries, display_id)
