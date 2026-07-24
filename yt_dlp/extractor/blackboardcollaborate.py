import urllib.parse

from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    float_or_none,
    int_or_none,
    join_nonempty,
    jwt_decode_hs256,
    mimetype2ext,
    parse_iso8601,
    parse_qs,
    smuggle_url,
    str_or_none,
    unsmuggle_url,
    url_or_none,
    urlencode_postdata,
    value,
)
from ..utils.traversal import traverse_obj


class BlackboardCollaborateIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                        https?://
                        (?P<region>[a-z]+)(?:-lti)?\.bbcollab\.com/
                        (?:
                            collab/ui/session/playback/load|
                            recording
                        )/
                        (?P<id>[^/?#]+)'''
    _TESTS = [
        {
            'url': 'https://us-lti.bbcollab.com/collab/ui/session/playback/load/0a633b6a88824deb8c918f470b22b256',
            'md5': 'bb7a055682ee4f25fdb5838cdf014541',
            'info_dict': {
                'id': '0a633b6a88824deb8c918f470b22b256',
                'title': 'HESI A2 Information Session - Thursday, May 6, 2021 - recording_1',
                'ext': 'mp4',
                'duration': 1896,
                'timestamp': 1620333295,
                'upload_date': '20210506',
                'subtitles': {
                    'live_chat': 'mincount:1',
                },
            },
        },
        {
            'url': 'https://eu.bbcollab.com/collab/ui/session/playback/load/4bde2dee104f40289a10f8e554270600',
            'md5': '108db6a8f83dcb0c2a07793649581865',
            'info_dict': {
                'id': '4bde2dee104f40289a10f8e554270600',
                'title': 'Meeting - Azerbaycanca erize formasi',
                'ext': 'mp4',
                'duration': 880,
                'timestamp': 1671176868,
                'upload_date': '20221216',
            },
        },
        {
            'url': 'https://eu.bbcollab.com/recording/f83be390ecff46c0bf7dccb9dddcf5f6',
            'md5': 'e3b0b88ddf7847eae4b4c0e2d40b83a5',
            'info_dict': {
                'id': 'f83be390ecff46c0bf7dccb9dddcf5f6',
                'title': 'Keynote lecture by Laura Carvalho - recording_1',
                'ext': 'mp4',
                'duration': 5506,
                'timestamp': 1662721705,
                'upload_date': '20220909',
                'subtitles': {
                    'live_chat': 'mincount:1',
                },
            },
        },
        {
            'url': 'https://eu.bbcollab.com/recording/c3e1e7c9e83d4cd9981c93c74888d496',
            'md5': 'fdb2d8c43d66fbc0b0b74ef5e604eb1f',
            'info_dict': {
                'id': 'c3e1e7c9e83d4cd9981c93c74888d496',
                'title': 'International Ally User Group - recording_18',
                'ext': 'mp4',
                'duration': 3479,
                'timestamp': 1721919621,
                'upload_date': '20240725',
                'subtitles': {
                    'en': 'mincount:1',
                    'live_chat': 'mincount:1',
                },
            },
        },
        {
            'url': 'https://us.bbcollab.com/collab/ui/session/playback/load/76761522adfe4345a0dee6794bbcabda',
            'only_matching': True,
        },
        {
            'url': 'https://ca.bbcollab.com/collab/ui/session/playback/load/b6399dcb44df4f21b29ebe581e22479d',
            'only_matching': True,
        },
        {
            'url': 'https://eu.bbcollab.com/recording/51ed7b50810c4444a106e48cefb3e6b5',
            'only_matching': True,
        },
        {
            'url': 'https://au.bbcollab.com/collab/ui/session/playback/load/2bccf7165d7c419ab87afc1ec3f3bb15',
            'only_matching': True,
        },
    ]

    def _call_api(self, region, video_id, path=None, token=None, note=None, fatal=False):
        # Ref: https://github.com/blackboard/BBDN-Collab-Postman-REST
        return self._download_json(
            join_nonempty(f'https://{region}.bbcollab.com/collab/api/csa/recordings', video_id, path, delim='/'),
            video_id, note or 'Downloading JSON metadata', fatal=fatal,
            headers={'Authorization': f'Bearer {token}'} if token else None)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        region = mobj.group('region')
        video_id = mobj.group('id')
        token = parse_qs(url).get('authToken', [None])[-1]

        video_info = self._call_api(region, video_id, path='data/secure', token=token, note='Trying auth token')
        if video_info:
            video_extra = self._call_api(region, video_id, token=token, note='Retrieving extra attributes')
        else:
            video_info = self._call_api(region, video_id, path='data', note='Trying fallback', fatal=True)
            video_extra = {}

        formats = traverse_obj(video_info, ('extStreams', lambda _, v: url_or_none(v['streamUrl']), {
            'url': 'streamUrl',
            'ext': ('contentType', {mimetype2ext}),
            'aspect_ratio': ('aspectRatio', {float_or_none}),
        }))

        if filesize := traverse_obj(video_extra, ('storageSize', {int_or_none})):
            for fmt in formats:
                fmt['filesize'] = filesize

        subtitles = {}
        for subs in traverse_obj(video_info, ('subtitles', lambda _, v: url_or_none(v['url']))):
            subtitles.setdefault(subs.get('lang') or 'und', []).append({
                'name': traverse_obj(subs, ('label', {str})),
                'url': subs['url'],
            })

        for live_chat_url in traverse_obj(video_info, ('chats', ..., 'url', {url_or_none})):
            subtitles.setdefault('live_chat', []).append({'url': live_chat_url})

        return {
            **traverse_obj(video_info, {
                'title': ('name', {str}),
                'timestamp': ('created', {parse_iso8601}),
                'duration': ('duration', {int_or_none(scale=1000)}),
            }),
            'formats': formats,
            'id': video_id,
            'subtitles': subtitles,
        }


class BlackboardCollaborateLaunchIE(InfoExtractor):
    _VALID_URL = r'https?://[a-z]+\.bbcollab\.com/launch/(?P<id>[^/?#]+)'

    _TESTS = [
        {
            'url': 'https://au.bbcollab.com/launch/eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJiYkNvbGxhYkFwaSIsInN1YiI6ImJiQ29sbGFiQXBpIiwiZXhwIjoxNzQwNDE2NDgzLCJpYXQiOjE3NDA0MTYxODMsInJlc291cmNlQWNjZXNzVGlja2V0Ijp7InJlc291cmNlSWQiOiI3MzI4YzRjZTNmM2U0ZTcwYmY3MTY3N2RkZTgzMzk2NSIsImNvbnN1bWVySWQiOiJhM2Q3NGM0Y2QyZGU0MGJmODFkMjFlODNlMmEzNzM5MCIsInR5cGUiOiJSRUNPUkRJTkciLCJyZXN0cmljdGlvbiI6eyJ0eXBlIjoiVElNRSIsImV4cGlyYXRpb25Ib3VycyI6MCwiZXhwaXJhdGlvbk1pbnV0ZXMiOjUsIm1heFJlcXVlc3RzIjotMX0sImRpc3Bvc2l0aW9uIjoiTEFVTkNIIiwibGF1bmNoVHlwZSI6bnVsbCwibGF1bmNoQ29tcG9uZW50IjpudWxsLCJsYXVuY2hQYXJhbUtleSI6bnVsbH19.xuELw4EafEwUMoYcCHidGn4Tw9O1QCbYHzYGJUl0kKk',
            'only_matching': True,
        },
        {
            'url': 'https://us.bbcollab.com/launch/eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJiYkNvbGxhYkFwaSIsInN1YiI6ImJiQ29sbGFiQXBpIiwiZXhwIjoxNjk0NDgxOTc3LCJpYXQiOjE2OTQ0ODE2NzcsInJlc291cmNlQWNjZXNzVGlja2V0Ijp7InJlc291cmNlSWQiOiI3YWU0MTFhNTU3NjU0OWFiOTZlYjVmMTM1YmY3MWU5MCIsImNvbnN1bWVySWQiOiJBRUU2MEI4MDI2QzM3ODU2RjMwMzNEN0ZEOTQzMTFFNSIsInR5cGUiOiJSRUNPUkRJTkciLCJyZXN0cmljdGlvbiI6eyJ0eXBlIjoiVElNRSIsImV4cGlyYXRpb25Ib3VycyI6MCwiZXhwaXJhdGlvbk1pbnV0ZXMiOjUsIm1heFJlcXVlc3RzIjotMX0sImRpc3Bvc2l0aW9uIjoiTEFVTkNIIiwibGF1bmNoVHlwZSI6bnVsbCwibGF1bmNoQ29tcG9uZW50IjpudWxsLCJsYXVuY2hQYXJhbUtleSI6bnVsbH19.yOhRZNaIjXYoMYMpcTzgjZJCnIFaYf2cAzbco8OAxlY',
            'only_matching': True,
        },
        {
            'url': 'https://eu.bbcollab.com/launch/eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJiYkNvbGxhYkFwaSIsInN1YiI6ImJiQ29sbGFiQXBpIiwiZXhwIjoxNzUyNjgyODYwLCJpYXQiOjE3NTI2ODI1NjAsInJlc291cmNlQWNjZXNzVGlja2V0Ijp7InJlc291cmNlSWQiOiI4MjQzYjFiODg2Nzk0NTZkYjkwN2NmNDZmZmE1MmFhZiIsImNvbnN1bWVySWQiOiI5ZTY4NzYwZWJiNzM0MzRiYWY3NTQyZjA1YmJkOTMzMCIsInR5cGUiOiJSRUNPUkRJTkciLCJyZXN0cmljdGlvbiI6eyJ0eXBlIjoiVElNRSIsImV4cGlyYXRpb25Ib3VycyI6MCwiZXhwaXJhdGlvbk1pbnV0ZXMiOjUsIm1heFJlcXVlc3RzIjotMX0sImRpc3Bvc2l0aW9uIjoiTEFVTkNIIiwibGF1bmNoVHlwZSI6bnVsbCwibGF1bmNoQ29tcG9uZW50IjpudWxsLCJsYXVuY2hQYXJhbUtleSI6bnVsbH19.Xj4ymojYLwZ1vKPKZ-KxjpqQvFXoJekjRaG0npngwWs',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        token = self._match_id(url)
        video_id = jwt_decode_hs256(token)['resourceAccessTicket']['resourceId']

        redirect_url = self._request_webpage(url, video_id).url
        if self.suitable(redirect_url):
            raise UnsupportedError(redirect_url)
        return self.url_result(redirect_url, BlackboardCollaborateIE, video_id)


class BlackboardClassCollaborateIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<region>[a-z]+)-lti\.bbcollab\.com/collab/ui/scheduler/lti'

    _TESTS = [
        {
            'url': 'https://eu-lti.bbcollab.com/collab/ui/scheduler/lti?token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJiYkNvbGxhYkFwaSIsInJvbGUiOjksImxhdW5jaFBhcmFtRGRiS2V5IjoiODcyYzEzYzctNWY1Yy00ODI1LWE2ZTktZDY1MzJlYjFhODFjIiwiaXNzIjoiYmJDb2xsYWJBcGkiLCJjb250ZXh0IjoiODUxYTE0OGMzZDFjNDE5MWEyZmE1NzljY2ZiMzY1YjAiLCJsYXVuY2hQYXJhbUtleSI6IjNiOTIxZmFhNTNlODRhNGY5OGE2ZDY2MDk1YjQ4Njc2IiwiZXhwIjoxNzQwNTAwNjA2LCJ0eXBlIjoyLCJpYXQiOjE3NDA0MTQyMDYsInVzZXIiOiI3M2ZkZTY4NDk4MTA0ODZhYWRmMWY5MDNkZTRmNmZmZiIsImNvbnN1bWVyIjoiNjMzNmZjZWQxYmI1NGQwYWI0M2Y2MmI4OGRiNzBiZTMifQ==.At95iQ_tarijE_v4WGvpaMBsTyZ3ariAgkfsyrYJ1Eg',
            'only_matching': True,
        },
    ]

    def _call_api(self, region, video_id=None, path=None, token=None, note='Downloading JSON metadata', fatal=True):
        return self._download_json(
            f'https://{region}.bbcollab.com/collab/api/csa/recordings/{join_nonempty(video_id, path, delim="/")}',
            video_id or jwt_decode_hs256(token)['context'], note=note, fatal=fatal,
            headers={'Authorization': f'Bearer {token}'} if token else '')

    def _entries(self, data, region, token):
        for item in traverse_obj(data, ('results', ...)):
            yield self.url_result(self._call_api(region, item['id'], 'url', token)['url'], BlackboardCollaborateLaunchIE, **traverse_obj(item, {
                'id': ('id', {str_or_none}),
                'view_count': ('playbackCount', {int_or_none}),
                'duration': ('duration', {int_or_none(scale=1000)}),
                'availability': ('publicLinkAllowed', {self._parse_availability}),
            }))

    def _parse_availability(self, public_link_allowed):
        if public_link_allowed:
            return 'public'
        else:
            return 'needs_auth'

    def _real_extract(self, url):
        url, data = unsmuggle_url(url, {})
        region = self._match_valid_url(url)['region']
        token = parse_qs(url).get('token')[-1]

        playlist_info = self._call_api(region, token=token, note='Downloading playlist information')

        return self.playlist_result(
            entries=self._entries(playlist_info, region, token),
            playlist_count=playlist_info.get('size'),
            **data,
        )


class BlackboardCollaborateUltraSingleCourseIE(InfoExtractor):
    """
    Match various URL formats including:
    * host/webapps/collab-ultra/tool/collabultra?course_id=course_id or
    * host/webapps/collab-ultra/tool/collabultra/lti/launch?course_id=course_id
    * host/webapps/blackboard/execute/courseMain?course_id=course_id
    * host/ultra/courses/course_id/cl/outline
    * host/webapps/blackboard/execute/announcement?course_id=course_id
    * host/webapps/blackboard/content/listContent.jsp?course_id=course_id
    """
    _VALID_URL = r'''(?x)
                        https://[\w\.]+/(?:
                         (?:webapps/
                           (?:collab-ultra/tool/collabultra(?:/lti/launch)?
                             |blackboard/(?:execute/(?:courseMain|announcement)|content/listContent.jsp)))
                        |(?:ultra/courses/(?P<course_id>[\d_]+)/cl/outline))'''

    _TESTS = [
        {
            'url': 'https://umb.umassonline.net/webapps/collab-ultra/tool/collabultra/lti/launch?course_id=_70544_1',
            'only_matching': True,
        },
        {
            'url': 'https://online.uwl.ac.uk/webapps/blackboard/execute/courseMain?course_id=_1445',
            'only_matching': True,
        },
        {
            'url': 'https://lms.mu.edu.sa/webapps/collab-ultra/tool/collabultra?course_id=_65252_1&mode=cpview',
            'only_matching': True,
        },
        {
            'url': 'https://blackboard.salford.ac.uk/ultra/courses/_175809_1/cl/outline',
            'only_matching': True,
        },
        {
            'url': 'https://blackboard.example.com/webapps/blackboard/execute/announcement?method=search&context=course_entry&course_id=_123456_1',
            'only_matching': True,
        },
        {
            'url': 'https://vuws.westernsydney.edu.au/webapps/blackboard/content/listContent.jsp?course_id= _41005_1&content_id=_7747469_1',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        course_id = parse_qs(url).get('course_id')[-1] or self._match_valid_url(url)['course_id']
        host = urllib.parse.urlparse(url).hostname

        course_data = self._download_webpage(
            f'https://{host}/webapps/collab-ultra/tool/collabultra/lti/launch?course_id={course_id}',
            course_id, note='Downloading course data')

        attrs = self._hidden_inputs(course_data)
        endpoint = self._html_search_regex(r'<form[^>]+action="([^"]+)"', course_data, 'form_action')
        redirect_url = self._request_webpage(endpoint, course_id, 'Getting authentication token',
                                             data=urlencode_postdata(attrs)).url

        # Ref: https://developer.blackboard.com/portal/displayApi
        course_info = self._download_json(f'https://{host}/learn/api/v1/courses/{course_id}', course_id,
                                          note='Downloading extra metadata', fatal=False)

        if self.suitable(redirect_url):
            raise UnsupportedError(redirect_url)

        return self.url_result(smuggle_url(
            redirect_url,
            traverse_obj(course_info, {
                'title': (('name', 'displayName'), {str}, any),
                'id': (('id', 'displayId', 'courseId'), {str}, any),
                'url': (('guestAccessUrl', 'externalAccessUrl', {value(join_nonempty('https://', host, course_info['homePageUrl'], delim=''))}), {url_or_none}, any),
                'description': ('description', {str}),
                'modified_timestamp': ('modifiedDate', {parse_iso8601}),
            }),
        ), ie=BlackboardClassCollaborateIE, video_id=None)


class BlackboardCollaborateUltraAllCoursesIE(InfoExtractor):
    _VALID_URL = r'https://[\w\.]+/ultra/institution-page'

    _TESTS = [
        {
            'url': 'https://umb.umassonline.net/ultra/institution-page',
            'only_matching': True,
        },
        {
            'url': 'https://online.uwl.ac.uk/ultra/institution-page',
            'only_matching': True,
        },
        {
            'url': 'https://lms.mu.edu.sa/ultra/institution-page',
            'only_matching': True,
        },
        {
            'url': 'https://nestor.rug.nl/ultra/institution-page',
            'only_matching': True,
        },
    ]

    def _download_course_list(self, host, offset):
        # Ref: https://developer.blackboard.com/portal/displayApi
        return self._download_json(
            f'https://{host}/learn/api/v1/users/me/memberships?fields=course&includeCount=true&offset={offset}',
            video_id=None, note='Finding courses')

    def _entries(self, data, host):
        for item in traverse_obj(data, (..., 'course')):
            if item['isAvailable']:
                yield self.url_result(
                    ie=BlackboardCollaborateUltraSingleCourseIE,
                    **traverse_obj(item, {
                        'id': ('id', {str}, any),
                        'display_id': ('courseId', 'displayId', {str}, any),
                        'description': ('description', {str}),
                        'title': ('displayName', 'name', {str}, any),
                        'availability': ('isAllowGuests', {bool}, any),
                        'url': ('guestAccessUrl', 'externalAccessUrl',
                                {value(join_nonempty('https://', host, item['homePageUrl'], delim=''))},
                                {url_or_none}, any),
                    }))

    def _real_extract(self, url):
        host = urllib.parse.urlparse(url).hostname
        first_page = self._download_course_list(host, 0)
        results = first_page['results']
        number_of_courses = traverse_obj(first_page, ('paging', 'count'))
        courses_found = number_of_courses

        while number_of_courses > courses_found:
            current_page = self._download_course_list(host, number_of_courses)
            results.append(*current_page['results'])
            courses_found += len(current_page['results'])

        return self.playlist_result(self._entries(results, host))
