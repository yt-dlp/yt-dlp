from .common import InfoExtractor


class TelegramEmbedIE(InfoExtractor):
    IE_NAME = 'telegram:embed'
    _VALID_URL = r'https?:\/\/t\.me\/(?P<channel_name>.*?)\/(?P<id>\d+)($|\W)'
    _TEST = {
        'url': 'https://t.me/europa_press/613',
        'info_dict': {
            'id': '613',
            'ext': 'mp4',
            'title': 'Europa Press',
            'description': 'Así de rápido fluye la lava en La Palma. Las autoridades destacan el "importante" avance '
                           'de la colada sur (un kilómetro y medio en solo 24 horas), que va hacia la costa quemando '
                           'invernaderos y viviendas bit.ly/3pRQv9J ',
            'thumbnail': r're:^https?:\/\/cdn.*?telesco\.pe\/file\/\w+',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id=video_id)

        title = self._html_search_meta(['og:title', 'twitter:title'], webpage, fatal=True)

        description = self._html_search_meta(['og:description', 'twitter:description'], webpage, fatal=True)

        webpage_embed = self._download_webpage(f'{url}?embed=1', video_id=video_id)

        thumbnail = self._search_regex(r'tgme_widget_message_video_thumb".*?background\-image\:url\(\'(.*?)\'\)',
                                       webpage_embed, 'thumbnail')

        source = self._search_regex('<video.*?src=\"(.*?)\"', webpage_embed, 'source')

        formats = [{
            'ext': 'mp4',
            'format_id': video_id,
            'url': self._proto_relative_url(source),
            'vcodec': 'none'}]

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
        }
