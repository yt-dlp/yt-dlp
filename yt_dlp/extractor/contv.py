from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
)


class CONtvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?contv\.com/details-movie/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.contv.com/details-movie/CEG10022949/days-of-thrills-&-laughter',
        'info_dict': {
            'id': 'CEG10022949',
            'ext': 'mp4',
            'title': 'Days Of Thrills & Laughter',
            'description': 'md5:5d6b3d0b1829bb93eb72898c734802eb',
            'upload_date': '20180703',
            'timestamp': 1530634789.61,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://www.contv.com/details-movie/CLIP-show_fotld_bts/fight-of-the-living-dead:-behind-the-scenes-bites',
        'info_dict': {
            'id': 'CLIP-show_fotld_bts',
            'title': 'Fight of the Living Dead: Behind the Scenes Bites',
        },
        'playlist_mincount': 7,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        details = self._download_json(
            'http://metax.contv.live.junctiontv.net/metax/2.5/details/' + video_id,
            video_id, query={'device': 'web'})

        if details.get('type') == 'episodic':
            seasons = self._download_json(
                'http://metax.contv.live.junctiontv.net/metax/2.5/seriesfeed/json/' + video_id,
                video_id)
            entries = []
            for season in seasons:
                for episode in season.get('episodes', []):
                    episode_id = episode.get('id')
                    if not episode_id:
                        continue
                    entries.append(self.url_result(
                        'https://www.contv.com/details-movie/' + episode_id,
                        CONtvIE.ie_key(), episode_id))
            return self.playlist_result(entries, video_id, details.get('title'))

        m_details = details['details']
        title = details['title']

        formats = []

        media_hls_url = m_details.get('media_hls_url')
        if media_hls_url:
            formats.extend(self._extract_m3u8_formats(
                media_hls_url, video_id, 'mp4',
                m3u8_id='hls', fatal=False))

        media_mp4_url = m_details.get('media_mp4_url')
        if media_mp4_url:
            formats.append({
                'format_id': 'http',
                'url': media_mp4_url,
            })

        subtitles = {}
        captions = m_details.get('captions') or {}
        for caption_url in captions.values():
            subtitles.setdefault('en', []).append({
                'url': caption_url
            })

        thumbnails = []
        for image in m_details.get('images', []):
            image_url = image.get('url')
            if not image_url:
                continue
            thumbnails.append({
                'url': image_url,
                'width': int_or_none(image.get('width')),
                'height': int_or_none(image.get('height')),
            })

        description = None
        for p in ('large_', 'medium_', 'small_', ''):
            d = m_details.get(p + 'description')
            if d:
                description = d
                break

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnails': thumbnails,
            'description': description,
            'timestamp': float_or_none(details.get('metax_added_on'), 1000),
            'subtitles': subtitles,
            'duration': float_or_none(m_details.get('duration'), 1000),
            'view_count': int_or_none(details.get('num_watched')),
            'like_count': int_or_none(details.get('num_fav')),
            'categories': details.get('category'),
            'tags': details.get('tags'),
            'season_number': int_or_none(details.get('season')),
            'episode_number': int_or_none(details.get('episode')),
            'release_year': int_or_none(details.get('pub_year')),
        }
