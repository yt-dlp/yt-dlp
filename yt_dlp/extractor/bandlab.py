from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    format_field,
    int_or_none,
    parse_iso8601,
    parse_qs,
    truncate_string,
    url_or_none,
)
from ..utils.traversal import traverse_obj, value


class BandlabBaseIE(InfoExtractor):
    def _call_api(self, endpoint, asset_id, **kwargs):
        headers = kwargs.pop('headers', None) or {}
        return self._download_json(
            f'https://www.bandlab.com/api/v1.3/{endpoint}/{asset_id}',
            asset_id, headers={
                'accept': 'application/json',
                'referer': 'https://www.bandlab.com/',
                'x-client-id': 'BandLab-Web',
                'x-client-version': '10.1.124',
                **headers,
            }, **kwargs)

    def _parse_revision(self, revision_data, url=None):
        return {
            'vcodec': 'none',
            'media_type': 'revision',
            'extractor_key': BandlabIE.ie_key(),
            'extractor': BandlabIE.IE_NAME,
            **traverse_obj(revision_data, {
                'webpage_url': (
                    'id', ({value(url)}, {format_field(template='https://www.bandlab.com/revision/%s')}), filter, any),
                'id': (('revisionId', 'id'), {str}, any),
                'title': ('song', 'name', {str}),
                'track': ('song', 'name', {str}),
                'url': ('mixdown', 'file', {url_or_none}),
                'thumbnail': ('song', 'picture', 'url', {url_or_none}),
                'description': ('description', {str}),
                'uploader': ('creator', 'name', {str}),
                'uploader_id': ('creator', 'username', {str}),
                'timestamp': ('createdOn', {parse_iso8601}),
                'duration': ('mixdown', 'duration', {float_or_none}),
                'view_count': ('counters', 'plays', {int_or_none}),
                'like_count': ('counters', 'likes', {int_or_none}),
                'comment_count': ('counters', 'comments', {int_or_none}),
                'genres': ('genres', ..., 'name', {str}),
            }),
        }

    def _parse_track(self, track_data, url=None):
        return {
            'vcodec': 'none',
            'media_type': 'track',
            'extractor_key': BandlabIE.ie_key(),
            'extractor': BandlabIE.IE_NAME,
            **traverse_obj(track_data, {
                'webpage_url': (
                    'id', ({value(url)}, {format_field(template='https://www.bandlab.com/post/%s')}), filter, any),
                'id': (('revisionId', 'id'), {str}, any),
                'url': ('track', 'sample', 'audioUrl', {url_or_none}),
                'title': ('track', 'name', {str}),
                'track': ('track', 'name', {str}),
                'description': ('caption', {str}),
                'thumbnail': ('track', 'picture', ('original', 'url'), {url_or_none}, any),
                'view_count': ('counters', 'plays', {int_or_none}),
                'like_count': ('counters', 'likes', {int_or_none}),
                'comment_count': ('counters', 'comments', {int_or_none}),
                'duration': ('track', 'sample', 'duration', {float_or_none}),
                'uploader': ('creator', 'name', {str}),
                'uploader_id': ('creator', 'username', {str}),
                'timestamp': ('createdOn', {parse_iso8601}),
            }),
        }

    def _parse_video(self, video_data, url=None):
        return {
            'media_type': 'video',
            'extractor_key': BandlabIE.ie_key(),
            'extractor': BandlabIE.IE_NAME,
            **traverse_obj(video_data, {
                'id': ('id', {str}),
                'webpage_url': (
                    'id', ({value(url)}, {format_field(template='https://www.bandlab.com/post/%s')}), filter, any),
                'url': ('video', 'url', {url_or_none}),
                'title': ('caption', {lambda x: x.replace('\n', ' ')}, {truncate_string(left=50)}),
                'description': ('caption', {str}),
                'thumbnail': ('video', 'picture', 'url', {url_or_none}),
                'view_count': ('video', 'counters', 'plays', {int_or_none}),
                'like_count': ('video', 'counters', 'likes', {int_or_none}),
                'comment_count': ('counters', 'comments', {int_or_none}),
                'duration': ('video', 'duration', {float_or_none}),
                'uploader': ('creator', 'name', {str}),
                'uploader_id': ('creator', 'username', {str}),
            }),
        }


class BandlabIE(BandlabBaseIE):
    _VALID_URL = [
        r'https?://(?:www\.)?bandlab.com/(?P<url_type>track|post|revision)/(?P<id>[\da-f_-]+)',
        r'https?://(?:www\.)?bandlab.com/(?P<url_type>embed)/\?(?:[^#]*&)?id=(?P<id>[\da-f-]+)',
    ]
    _EMBED_REGEX = [rf'<iframe[^>]+src=[\'"](?P<url>{_VALID_URL[1]})[\'"]']
    _TESTS = [{
        'url': 'https://www.bandlab.com/track/04b37e88dba24967b9dac8eb8567ff39_07d7f906fc96ee11b75e000d3a428fff',
        'md5': '46f7b43367dd268bbcf0bbe466753b2c',
        'info_dict': {
            'id': '02d7f906-fc96-ee11-b75e-000d3a428fff',
            'ext': 'm4a',
            'uploader_id': 'ender_milze',
            'track': 'sweet black',
            'description': 'composed by juanjn3737',
            'timestamp': 1702171963,
            'view_count': int,
            'like_count': int,
            'duration': 54.629999999999995,
            'title': 'sweet black',
            'upload_date': '20231210',
            'thumbnail': 'https://bandlabimages.azureedge.net/v1.0/songs/fa082beb-b856-4730-9170-a57e4e32cc2c/',
            'genres': ['Lofi'],
            'uploader': 'ender milze',
            'comment_count': int,
            'media_type': 'revision',
        },
    }, {
        # Same track as above but post URL
        'url': 'https://www.bandlab.com/post/07d7f906-fc96-ee11-b75e-000d3a428fff',
        'md5': '46f7b43367dd268bbcf0bbe466753b2c',
        'info_dict': {
            'id': '02d7f906-fc96-ee11-b75e-000d3a428fff',
            'ext': 'm4a',
            'uploader_id': 'ender_milze',
            'track': 'sweet black',
            'description': 'composed by juanjn3737',
            'timestamp': 1702171973,
            'view_count': int,
            'like_count': int,
            'duration': 54.629999999999995,
            'title': 'sweet black',
            'upload_date': '20231210',
            'thumbnail': 'https://bandlabimages.azureedge.net/v1.0/songs/fa082beb-b856-4730-9170-a57e4e32cc2c/',
            'genres': ['Lofi'],
            'uploader': 'ender milze',
            'comment_count': int,
            'media_type': 'revision',
        },
    }, {
        # SharedKey Example
        'url': 'https://www.bandlab.com/track/048916c2-c6da-ee11-85f9-6045bd2e11f9?sharedKey=0NNWX8qYAEmI38lWAzCNDA',
        'md5': '15174b57c44440e2a2008be9cae00250',
        'info_dict': {
            'id': '038916c2-c6da-ee11-85f9-6045bd2e11f9',
            'ext': 'm4a',
            'comment_count': int,
            'genres': ['Other'],
            'uploader_id': 'user8353034818103753',
            'thumbnail': 'https://bandlabimages.azureedge.net/v1.0/songs/51b18363-da23-4b9b-a29c-2933a3e561ca/',
            'timestamp': 1709625771,
            'track': 'PodcastMaerchen4b',
            'duration': 468.14,
            'view_count': int,
            'description': 'Podcast: Neues aus der Märchenwelt',
            'like_count': int,
            'upload_date': '20240305',
            'uploader': 'Erna Wageneder',
            'title': 'PodcastMaerchen4b',
            'media_type': 'revision',
        },
    }, {
        # Different Revision selected
        'url': 'https://www.bandlab.com/track/130343fc-148b-ea11-96d2-0003ffd1fc09?revId=110343fc-148b-ea11-96d2-0003ffd1fc09',
        'md5': '74e055ef9325d63f37088772fbfe4454',
        'info_dict': {
            'id': '110343fc-148b-ea11-96d2-0003ffd1fc09',
            'ext': 'm4a',
            'timestamp': 1588273294,
            'thumbnail': 'https://bandlabimages.azureedge.net/v1.0/users/b612e533-e4f7-4542-9f50-3fcfd8dd822c/',
            'description': 'Final Revision.',
            'title': 'Replay ( Instrumental)',
            'uploader': 'David R Sparks',
            'uploader_id': 'davesnothome69',
            'view_count': int,
            'comment_count': int,
            'track': 'Replay ( Instrumental)',
            'genres': ['Rock'],
            'upload_date': '20200430',
            'like_count': int,
            'duration': 279.43,
            'media_type': 'revision',
        },
    }, {
        # Video
        'url': 'https://www.bandlab.com/post/5cdf9036-3857-ef11-991a-6045bd36e0d9',
        'md5': '8caa2ef28e86c1dacf167293cfdbeba9',
        'info_dict': {
            'id': '5cdf9036-3857-ef11-991a-6045bd36e0d9',
            'ext': 'mp4',
            'duration': 44.705,
            'thumbnail': 'https://bandlabimages.azureedge.net/v1.0/videos/67c6cef1-cef6-40d3-831e-a55bc1dcb972/',
            'comment_count': int,
            'title': 'backing vocals',
            'uploader_id': 'marliashya',
            'uploader': 'auraa',
            'like_count': int,
            'description': 'backing vocals',
            'media_type': 'video',
        },
    }, {
        # Embed Example
        'url': 'https://www.bandlab.com/embed/?blur=false&id=014de0a4-7d82-ea11-a94c-0003ffd19c0f',
        'md5': 'a4ad05cb68c54faaed9b0a8453a8cf4a',
        'info_dict': {
            'id': '014de0a4-7d82-ea11-a94c-0003ffd19c0f',
            'ext': 'm4a',
            'comment_count': int,
            'genres': ['Electronic'],
            'uploader': 'Charlie Henson',
            'timestamp': 1587328674,
            'upload_date': '20200419',
            'view_count': int,
            'track': 'Positronic Meltdown',
            'duration': 318.55,
            'thumbnail': 'https://bandlabimages.azureedge.net/v1.0/songs/87165bc3-5439-496e-b1f7-a9f13b541ff2/',
            'description': 'Checkout my tracks at AOMX http://aomxsounds.com/',
            'uploader_id': 'microfreaks',
            'title': 'Positronic Meltdown',
            'like_count': int,
            'media_type': 'revision',
        },
    }, {
        # Track without revisions available
        'url': 'https://www.bandlab.com/track/55767ac51789ea11a94c0003ffd1fc09_2f007b0a37b94ec7a69bc25ae15108a5',
        'md5': 'f05d68a3769952c2d9257c473e14c15f',
        'info_dict': {
            'id': '55767ac51789ea11a94c0003ffd1fc09_2f007b0a37b94ec7a69bc25ae15108a5',
            'ext': 'm4a',
            'track': 'insame',
            'like_count': int,
            'duration': 84.03,
            'title': 'insame',
            'view_count': int,
            'comment_count': int,
            'uploader': 'Sorakime',
            'uploader_id': 'sorakime',
            'thumbnail': 'https://bandlabimages.azureedge.net/v1.0/users/572a351a-0f3a-4c6a-ac39-1a5defdeeb1c/',
            'timestamp': 1691162128,
            'upload_date': '20230804',
            'media_type': 'track',
        },
    }, {
        'url': 'https://www.bandlab.com/revision/014de0a4-7d82-ea11-a94c-0003ffd19c0f',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://phantomluigi.github.io/',
        'info_dict': {
            'id': 'e14223c3-7871-ef11-bdfd-000d3a980db3',
            'ext': 'm4a',
            'view_count': int,
            'upload_date': '20240913',
            'uploader_id': 'phantommusicofficial',
            'timestamp': 1726194897,
            'uploader': 'Phantom',
            'comment_count': int,
            'genres': ['Progresive Rock'],
            'description': 'md5:a38cd668f7a2843295ef284114f18429',
            'duration': 225.23,
            'like_count': int,
            'title': 'Vermilion Pt. 2 (Cover)',
            'track': 'Vermilion Pt. 2 (Cover)',
            'thumbnail': 'https://bandlabimages.azureedge.net/v1.0/songs/62b10750-7aef-4f42-ad08-1af52f577e97/',
            'media_type': 'revision',
        },
    }]

    def _real_extract(self, url):
        display_id, url_type = self._match_valid_url(url).group('id', 'url_type')

        qs = parse_qs(url)
        revision_id = traverse_obj(qs, (('revId', 'id'), 0, any))
        if url_type == 'revision':
            revision_id = display_id

        revision_data = None
        if not revision_id:
            post_data = self._call_api(
                'posts', display_id, note='Downloading post data',
                query=traverse_obj(qs, {'sharedKey': ('sharedKey', 0)}))

            revision_id = traverse_obj(post_data, (('revisionId', ('revision', 'id')), {str}, any))
            revision_data = traverse_obj(post_data, ('revision', {dict}))

            if not revision_data and not revision_id:
                post_type = post_data.get('type')
                if post_type == 'Video':
                    return self._parse_video(post_data, url=url)
                if post_type == 'Track':
                    return self._parse_track(post_data, url=url)
                raise ExtractorError(f'Could not extract data for post type {post_type!r}')

        if not revision_data:
            revision_data = self._call_api(
                'revisions', revision_id, note='Downloading revision data', query={'edit': 'false'})

        return self._parse_revision(revision_data, url=url)


class BandlabPlaylistIE(BandlabBaseIE):
    _VALID_URL = [
        r'https?://(?:www\.)?bandlab.com/(?:[\w]+/)?(?P<type>albums|collections)/(?P<id>[\da-f-]+)',
        r'https?://(?:www\.)?bandlab.com/(?P<type>embed)/collection/\?(?:[^#]*&)?id=(?P<id>[\da-f-]+)',
    ]
    _EMBED_REGEX = [rf'<iframe[^>]+src=[\'"](?P<url>{_VALID_URL[1]})[\'"]']
    _TESTS = [{
        'url': 'https://www.bandlab.com/davesnothome69/albums/89b79ea6-de42-ed11-b495-00224845aac7',
        'info_dict': {
            'thumbnail': 'https://bl-prod-images.azureedge.net/v1.3/albums/69507ff3-579a-45be-afca-9e87eddec944/',
            'release_date': '20221003',
            'title': 'Remnants',
            'album': 'Remnants',
            'like_count': int,
            'album_type': 'LP',
            'description': 'A collection of some feel good, rock hits.',
            'comment_count': int,
            'view_count': int,
            'id': '89b79ea6-de42-ed11-b495-00224845aac7',
            'uploader': 'David R Sparks',
            'uploader_id': 'davesnothome69',
        },
        'playlist_count': 10,
    }, {
        'url': 'https://www.bandlab.com/slytheband/collections/955102d4-1040-ef11-86c3-000d3a42581b',
        'info_dict': {
            'id': '955102d4-1040-ef11-86c3-000d3a42581b',
            'timestamp': 1720762659,
            'view_count': int,
            'title': 'My Shit 🖤',
            'uploader_id': 'slytheband',
            'uploader': '𝓢𝓛𝓨',
            'upload_date': '20240712',
            'like_count': int,
            'thumbnail': 'https://bandlabimages.azureedge.net/v1.0/collections/2c64ca12-b180-4b76-8587-7a8da76bddc8/',
        },
        'playlist_count': 15,
    }, {
        # Embeds can contain both albums and collections with the same URL pattern. This is an album
        'url': 'https://www.bandlab.com/embed/collection/?id=12cc6f7f-951b-ee11-907c-00224844f303',
        'info_dict': {
            'id': '12cc6f7f-951b-ee11-907c-00224844f303',
            'release_date': '20230706',
            'description': 'This is a collection of songs I created when I had an Amiga computer.',
            'view_count': int,
            'title': 'Mark Salud The Amiga Collection',
            'uploader_id': 'mssirmooth1962',
            'comment_count': int,
            'thumbnail': 'https://bl-prod-images.azureedge.net/v1.3/albums/d618bd7b-0537-40d5-bdd8-61b066e77d59/',
            'like_count': int,
            'uploader': 'Mark Salud',
            'album': 'Mark Salud The Amiga Collection',
            'album_type': 'LP',
        },
        'playlist_count': 24,
    }, {
        # Tracks without revision id
        'url': 'https://www.bandlab.com/embed/collection/?id=e98aafb5-d932-ee11-b8f0-00224844c719',
        'info_dict': {
            'like_count': int,
            'uploader_id': 'sorakime',
            'comment_count': int,
            'uploader': 'Sorakime',
            'view_count': int,
            'description': 'md5:4ec31c568a5f5a5a2b17572ea64c3825',
            'release_date': '20230812',
            'title': 'Art',
            'album': 'Art',
            'album_type': 'Album',
            'id': 'e98aafb5-d932-ee11-b8f0-00224844c719',
            'thumbnail': 'https://bl-prod-images.azureedge.net/v1.3/albums/20c890de-e94a-4422-828a-2da6377a13c8/',
        },
        'playlist_count': 13,
    }, {
        'url': 'https://www.bandlab.com/albums/89b79ea6-de42-ed11-b495-00224845aac7',
        'only_matching': True,
    }]

    def _entries(self, album_data):
        for post in traverse_obj(album_data, ('posts', lambda _, v: v['type'])):
            post_type = post['type']
            if post_type == 'Revision':
                yield self._parse_revision(post.get('revision'))
            elif post_type == 'Track':
                yield self._parse_track(post)
            elif post_type == 'Video':
                yield self._parse_video(post)
            else:
                self.report_warning(f'Skipping unknown post type: "{post_type}"')

    def _real_extract(self, url):
        playlist_id, playlist_type = self._match_valid_url(url).group('id', 'type')

        endpoints = {
            'albums': ['albums'],
            'collections': ['collections'],
            'embed': ['collections', 'albums'],
        }.get(playlist_type)
        for endpoint in endpoints:
            playlist_data = self._call_api(
                endpoint, playlist_id, note=f'Downloading {endpoint[:-1]} data',
                fatal=False, expected_status=404)
            if not playlist_data.get('errorCode'):
                playlist_type = endpoint
                break
        if error_code := playlist_data.get('errorCode'):
            raise ExtractorError(f'Could not find playlist data. Error code: "{error_code}"')

        return self.playlist_result(
            self._entries(playlist_data), playlist_id,
            **traverse_obj(playlist_data, {
                'title': ('name', {str}),
                'description': ('description', {str}),
                'uploader': ('creator', 'name', {str}),
                'uploader_id': ('creator', 'username', {str}),
                'timestamp': ('createdOn', {parse_iso8601}),
                'release_date': ('releaseDate', {lambda x: x.replace('-', '')}, filter),
                'thumbnail': ('picture', ('original', 'url'), {url_or_none}, any),
                'like_count': ('counters', 'likes', {int_or_none}),
                'comment_count': ('counters', 'comments', {int_or_none}),
                'view_count': ('counters', 'plays', {int_or_none}),
            }),
            **(traverse_obj(playlist_data, {
                'album': ('name', {str}),
                'album_type': ('type', {str}),
            }) if playlist_type == 'albums' else {}))
