from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, mimetype2ext, traverse_obj


class BerufeTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?web\.arbeitsagentur\.de/berufetv/[a-z\-/]+/film;filmId=(?P<id>[a-zA-Z\d\-_]+)'
    _TESTS = [{
        'url': 'https://web.arbeitsagentur.de/berufetv/studienberufe/wirtschaftswissenschaften/wirtschaftswissenschaften-volkswirtschaft/film;filmId=DvKC3DUpMKvUZ_6fEnfg3u',
        'md5': '041b6432ec8e6838f84a5c30f31cc795',
        'info_dict': {
            'id': 'DvKC3DUpMKvUZ_6fEnfg3u',
            'ext': 'mp4',
            'title': 'Volkswirtschaftslehre',
            'description': 'md5:6bd87d0c63163480a6489a37526ee1c1',
            'categories': ['Studien&shy;beruf'],
            'tags': ['Studienfilm'],
            'duration': 602.440,
            'thumbnail': 'https://asset-out-cdn.video-cdn.net/private/videos/DvKC3DUpMKvUZ_6fEnfg3u/thumbnails/active',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        movie_metadata = self._download_json(
            'https://rest.arbeitsagentur.de/infosysbub/berufetv/pc/v1/film-metadata',
            video_id, 'Downloading JSON metadata',
            headers={'X-API-Key': '79089773-4892-4386-86e6-e8503669f426'}, fatal=False)

        meta = next(
            item for item in movie_metadata.get('metadaten') if video_id == item.get('miId')
        ) if movie_metadata else {}

        video = self._download_json(
            'https://d.video-cdn.net/play/player/8YRzUk6pTzmBdrsLe9Y88W/video/%s' % (video_id),
            video_id, 'Downloading video JSON')

        video_sources = traverse_obj(video, ['videoSources', 'html'])

        if not video_sources:
            raise ExtractorError('Failed to obtain video source list')

        formats = []
        subtitles = {}

        for key, source in video_sources.items():
            if key == 'auto':
                m3u8_url = source[0]['source']
                fmts, subs = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id)
                formats += fmts
                subtitles = subs
            else:
                formats.append({
                    'url': source[0]['source'],
                    'ext': mimetype2ext(source[0]['mimeType']),
                    'format_id': key,
                })

        video_tracks = video.get('videoTracks') or []
        for track in video_tracks:
            if track.get('type') != 'SUBTITLES':
                continue
            subtitles[track['language']] = [{
                'url': track['source'],
                'name': track['label'],
                'ext': 'vtt'
            }]

        return {
            'id': video_id,
            'title': meta.get('titel') or traverse_obj(video, ['videoMetaData', 'title']),
            'description': meta.get('beschreibung'),
            'thumbnail': 'https://asset-out-cdn.video-cdn.net/private/videos/%s/thumbnails/active' % (video_id),
            'duration': video.get('duration') / 1000,
            'categories': [meta.get('kategorie')],
            'tags': meta.get('themengebiete'),
            'subtitles': subtitles,
            'formats': formats,
        }
