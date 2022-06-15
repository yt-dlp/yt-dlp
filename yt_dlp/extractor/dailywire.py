from .common import InfoExtractor


class DailyWireIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)dailywire(?:\.com)/(?:episode)/(?P<episode_name>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.dailywire.com/episode/1-fauci',
        'info_dict': {
            'id': 'ckzsl50xwqpy508502drqpb12',
            'ext': 'mp4',
            'title': '1-fauci',
        }
    }, {
        'url': 'https://www.dailywire.com/episode/ep-124-bill-maher',
        'info_dict': {
            'id': 'cl355p7u74t900894oxp1bnae',
            'ext': 'mp4',
            'title': 'Ep. 125 - William Barr ',
        }
    }]

    def _real_extract(self, url):
        slug = self._match_valid_url(url).group('episode_name')
        webpage = self._download_webpage(url, slug)

        json_data = self._search_nextjs_data(webpage, slug)
        episode_info = json_data['props']['pageProps']['episodeData']['episode']

        formats, subtitle = [], {}
        for segment in episode_info['segments']:
            subs = {}
            if segment.get('audio') == 'Access Denied' and segment.get('video') == 'Access Denied':
                continue
            if segment.get('video') != 'Access Denied':
                format_, subs = self._extract_m3u8_formats_and_subtitles(
                    segment.get('audio') or segment.get('video'), slug
                )
                formats.extend(format_)
            if segment.get('audio') != 'Access Denied':
                format_ = {
                    'url': segment.get('audio'),
                }
                formats.append(format_)

            self._merge_subtitles(subtitle, subs)

        self._sort_formats(formats)
        return {
            'id': episode_info['id'],
            'title': episode_info.get('title'),
            'formats': formats,
            'subtitles': subtitle,
            'description': episode_info.get('description'),
            'thumbnail': episode_info.get('image'),
            'is_live': episode_info.get('isLive'),
            'creator': f'{episode_info.get("first_name")} {episode_info.get("last_name")}'
        }
