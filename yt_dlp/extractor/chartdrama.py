from .common import InfoExtractor


class ChartDramaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?chartdrama\.com/p/(?P<id>\d+)/(?P<slug>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.chartdrama.com/p/4107/every-night-she-makes-the-ceo-fall?ep=1',
        'info_dict': {
            'id': '4107',
            'title': 'Every Night, She Makes the CEO Fall',
            'ext': 'mp4',
        },
        'playlist_mincount': 1,
    }]

    def _real_extract(self, url):
        source_book_id, slug = self._match_valid_url(url).group('id', 'slug')
        display_id = source_book_id

        watch_data = self._download_json(
            f'https://www.chartdrama.com/api/watch/{source_book_id}/{slug}',
            display_id)

        drama_id = watch_data['dramaId']
        title = watch_data.get('title') or display_id
        synopsis = watch_data.get('synopsis')
        thumbnail = watch_data.get('cover')
        tags = watch_data.get('tags')

        episodes_data = self._download_json(
            f'https://www.chartdrama.com/api/drama/{drama_id}/episodes',
            display_id)

        entries = []
        for item in episodes_data.get('items', []):
            m3u8_url = item.get('url')
            if not m3u8_url:
                continue
            ep_num = item.get('ep')
            ep_id = f'{display_id}-{ep_num}' if ep_num is not None else m3u8_url

            formats = self._extract_m3u8_formats(
                m3u8_url, ep_id, ext='mp4',
                headers={'Referer': 'https://www.chartdrama.com/'})

            episode_title = title
            if ep_num is not None:
                episode_title = f'{title} - Episode {ep_num}'

            entries.append({
                'id': ep_id,
                'title': episode_title,
                'series': title,
                'episode_number': ep_num,
                'description': synopsis,
                'thumbnail': thumbnail,
                'tags': tags,
                'formats': formats,
            })

        return self.playlist_result(entries, display_id, title, playlist_count=len(entries))
