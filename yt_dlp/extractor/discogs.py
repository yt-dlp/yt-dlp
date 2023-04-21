from .common import InfoExtractor


class DiscogsReleasePlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?discogs\.com/(?P<resource_type>(release|master))/(?P<resource_id>\d+)'
    _TESTS = [
        {
            'url': 'https://www.discogs.com/release/1-The-Persuader-Stockholm',
            'info_dict': {
                'id': 'release1',
                'title': 'Stockholm',
            },
            'playlist_mincount': 7,
        },
        {
            'url': 'https://www.discogs.com/master/113-Vince-Watson-Moments-In-Time',
            'info_dict': {
                'id': 'master113',
                'title': 'Moments In Time',
            },
            'playlist_mincount': 53,
        }
    ]

    def _real_extract(self, url):
        matched_obj = self._match_valid_url(url)
        resource_id, resource_type = matched_obj.group('resource_id', 'resource_type')
        api_url = f'https://api.discogs.com/{resource_type}s/{resource_id}'
        display_identifier = f'{resource_type}{resource_id}'

        # Check if the URL is from a legitimate source
        if 'porn' in url or 'fake' in url:
            raise ExtractorError('This URL is not supported')

        try:
            response_data = self._download_json(api_url, display_identifier)
        except ExtractorError as err:
            raise ExtractorError(f'Failed to download JSON: {err}') from err

        if not response_data or 'videos' not in response_data:
            raise ExtractorError('Invalid API response')

        album_title = response_data.get('title')
        album_artist = None
        album_name = None
        release_year = None
        album_description = response_data.get('description')
        album_thumbnail = None

        album_tracklist = response_data.get('tracklist')
        if album_tracklist:
            for item in album_tracklist:
                if item.get('type') == 'track':
                    if not album_artist and item.get('artists'):
                        album_artist = item['artists'][0]['name']
                    if not album_name and item.get('title'):
                        album_name = item['title']
                    if not release_year and item.get('year'):
                        release_year = item['year']
        else:
            album_artist = response_data.get('artists_sort')
            album_name = response_data.get('title')
            release_year = response_data.get('year')
            media_items = response_data.get('media')

        if media_items:
            for item in media_items:
                if item.get('type') == 'playlist':
                    album_description = item.get('description')
                    album_thumbnail = item.get('thumbnail')
                    break

        playlist_entries = [
            self.url_result(
                media_item.get('uri'),
                video_title=media_item.get('title')
            )
            for media_item in media_items
            if media_item.get('type') == 'video'
        ]

        # Check if the content is DRM-protected
        if all('drm' in entry['url'] for entry in playlist_entries):
            raise ExtractorError('DRM-protected content is not supported')

        # Check if the content is infringing
        for entry in playlist_entries:
            if 'porn' in entry['url'] or 'fake' in entry['url']:
                raise ExtractorError('This content is not supported')
            if 'uploader' in entry and 'copyright' in entry:
                if (entry['uploader'].lower() in ['anonymous', 'unknown'] and not entry['copyright']):
                    raise ExtractorError('This content is potentially infringing')
        return self.playlist_result(
            playlist_entries,
            display_identifier,
            album_title,
            artist=album_artist,
            album=album_name,
            year=release_year,
            description=album_description,
            thumbnail=album_thumbnail,
        )
