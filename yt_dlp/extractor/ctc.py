from .common import InfoExtractor
from ..utils import (
    traverse_obj, 
    int_or_none
)

class CTCIE(InfoExtractor):
    IE_NAME = 'ctc'
    _VALID_URL = (
        r'https?://ctc\.ru/projects/filmi/(?P<project_name>[^/]+)/?(?:video/?)?$'
        r'|https?://ctc\.ru/projects/(?P<category>show|multiki|serials)/(?P<project_name2>[^/]+)/video/'
        r'(?:$'
        r'|(?P<season_number>\d+)-sezon/(?P<episode_number>\d+)-(?:vypusk|serija)/?$'
        r'|promo/[^/]+/?$'
        r')'
    )
    _GEO_COUNTRIES = ['RU']

    def _real_extract(self, url):
        url_slug = url.split("https://ctc.ru/")[1]

        item_response = self._download_json(
            f'https://ctc.ru/api/page/v1/{url_slug}', url_slug,
            note='Downloading item data', headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0"
            }
        )

        track_hub_id = str(traverse_obj(item_response, ('content', 0, 'trackHubId'), expected_type=int))
        if not track_hub_id:
            self.raise_no_formats('trackHubId not found')

        video_url = traverse_obj(
                item_response, ('content', 0, 'videoUrl'), get_all=False
            ) or traverse_obj(
                item_response, ('content', 0, 'trackUrl'), get_all=False
        )
        stream_response = self._download_json(
            video_url.replace("/player/", "/playlist/"), 
            track_hub_id,
            note='Downloading stream data', headers={
                'X-Referer': 'https://ctc.ru',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0',
            }
        )

        if traverse_obj(stream_response, ('playlist', 'items', 0, 'errors', 0, 'code')) == 102:
            self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
        elif traverse_obj(stream_response, ('playlist', 'items', 0, 'errors', 0, 'code')) == 103:
            self.raise_login_required(msg='This video is only available for registered users with the required subscription')

        formats = []
        for stream in traverse_obj(stream_response, ('playlist', 'items', 0, 'streams')):
            protocol = stream.get('protocol')
            video_id = traverse_obj(stream_response, ('playlist', 'items', 0, 'track_id'))

            fmts = []
            if protocol == 'HLS':
                fmts, _ = self._extract_m3u8_formats_and_subtitles(
                    stream.get('url'), video_id, ext='mp4', preference=1, m3u8_id="video/hls", fatal=False)
            formats.extend(fmts)

        return {
            'formats': formats,
            'id': track_hub_id,
            'title': ": ".join(filter(None, [
                traverse_obj(stream_response, ('playlist', 'items', 0, 'project_name')),
                traverse_obj(stream_response, ('playlist', 'items', 0, 'episode_name'))
            ])),
            **traverse_obj(item_response, {
                'description': ('content', 0, 'description'),
            }),
            **traverse_obj(stream_response, {
                'episode': ('playlist', 'items', 0, 'episode_name'),
                'duration': ('playlist', 'items', 0, 'duration'),
                'thumbnail': ('playlist', 'items', 0, 'thumbnail_url'),
                'season': ('playlist', 'items', 0, 'season_name'),
                'age_limit': ('playlist', 'items', 0, 'min_age'),
            }),
            'season_number': int_or_none(self._match_valid_url(url).group('season_number')),
            'episode_number': int_or_none(self._match_valid_url(url).group('episode_number')),
        }


class CTCSeasonIE(InfoExtractor):
    IE_NAME = 'ctc:season'
    _VALID_URL = (
        r'https?://ctc\.ru/projects/(?P<category>show|multiki|serials)/'
        r'(?P<project_name>[^/]+)/video/(?P<season_number>\d+)-sezon/?$'
    )
    _GEO_COUNTRIES = ['RU']

    def _real_extract(self, url):
        url_slug = url.split("https://ctc.ru/")[1]
        
        season_data = self._download_json(f'https://ctc.ru/api/page/v1/{url_slug}', url_slug)

        entries = [{
            '_type': 'url',
            'title': episode.get('title'),
            'url': f"https://ctc.ru{episode.get('popupUrl')}",
            'ie_key': CTCIE.ie_key(),
            'season_number': self._match_valid_url(url).group('season_number'),
            'episode_number': self._search_regex(
                r'/(?P<episode>\d+)-(vypusk|serija)/', 
                episode.get('popupUrl'), 
                'episode number', 
            )
        } for episode in traverse_obj(season_data, ('content', 1, 'widgets')) if episode.get('popupUrl')]

        return {
            '_type': 'playlist',    
            'entries': entries,
            **traverse_obj(season_data, {
                'id': ('content', 9, 'entityId'),
                'title': ('content', 0, 'widgets', 1, 'title'),
                'season_number': self._match_valid_url(url).group('season_number'),
                'series': ('content', 0, 'widgets', 1, 'title'),
                'description': ('content', 0, 'widgets', 1, 'description'),
            }),
        }


class CTCSeriesIE(InfoExtractor):
    IE_NAME = 'ctc:series'
    _VALID_URL = (
        r'https?://ctc\.ru/projects/(?P<category>show|multiki|serials)/'
        r'(?P<slug>[^/]+)/?$'
    )
    _GEO_COUNTRIES = ['RU']

    def _real_extract(self, url):
        url_slug = url.split("https://ctc.ru/")[1]

        series_data = self._download_json(f'https://ctc.ru/api/page/v1/{url_slug}', url_slug)

        # cartoons doesn't indicate in the url what type it is, so
        # if it's a movie, then redirect it to CTCIE
        if traverse_obj(series_data, ('content', 5, 'tabs')) == []:
            return self.url_result(f'https://ctc.ru/{url_slug}/video')

        entries = [{
            '_type': 'url',
            'title': season.get('title'),
            'url': f'https://ctc.ru{season.get("url")}',
            'ie_key': CTCSeasonIE.ie_key(),
            'season_number': self._search_regex(
                r'/(?P<episode>\d+)-sezon/', 
                season.get("url"), 
                'season number', 
            ),
            'series': season.get('title'),
        } for season in traverse_obj(series_data, ('content', 1, 'tabs')) if season.get("url").endswith("sezon/")]

        return {
            '_type': 'playlist',
            'entries': entries,
            **traverse_obj(series_data, {
                'id': ('content', 0, 'projectId'),
                'title': ('content', 0, 'widgets', 1, 'title'),
                'series': ('content', 0, 'widgets', 1, 'title'),
                'description': ('content', 0, 'widgets', 1, 'description')
            }),
        }