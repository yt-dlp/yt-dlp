from .common import InfoExtractor


class RtlPlusPodcastExtractorIE(InfoExtractor):
    # _VALID_URL = r'https?://(?:www\.)?plus\.rtl\.de/podcast/(?P<podcastid>\w+)/(?P<id>\w+)'
    _VALID_URL = r'https?://(?:www\.)?plus\.rtl\.de/podcast/it-gefluester-swkanad6uxwwh/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://plus.rtl.de/podcast/it-gefluester-swkanad6uxwwh/revolution-im-business-kuenstliche-intelligenz-im-fokus-vpyvzbrxkkx39',
        'md5': '0051094e27f498c655cf0747f10995f2',
        'info_dict': {
            # For videos, only the 'id' and 'ext' fields are required to RUN the test:
            'id': 'rrn:podcast:external:episode:vpyvzbrxkkx39',
            'ext': 'mp3',
            # Then if the test run fails, it will output the missing/incorrect fields.
            # Properties can be added as:
            # * A value, e.g.
                'title': 'Revolution im Business: Künstliche Intelligenz im Fokus',
            # * MD5 checksum; start the string with 'md5:', e.g.
                'description': 'md5:c6f32c36570c3a0a776bfd5ae3ed0e88',
            # * A regular expression; start the string with 're:', e.g.
            #     'thumbnail': r're:^https?://.*\.jpg$',
            # * A count of elements in a list; start the string with 'count:', e.g.
            #     'tags': 'count:10',
            # * Any Python type, e.g.
            #     'view_count': int,
        }
    }]

    def _real_extract(self, url):
        video_slug = self._match_id(url)
        # TODO: a token can be obtained from https://auth.rtl.de/auth/realms/rtlplus/protocol/openid-connect/token
        TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJ4N1RJT2o1bXd3T0daLS1fOVdjcmhDbzdHemVCTDgwOWQxZlByN29wUThBIn0.eyJleHAiOjE3MDU0MzQ5MjksImlhdCI6MTcwNTQyMDUyOSwianRpIjoiZDQ5ZTkyZjgtZWRiZi00NmU4LWIxNTctYTUyOGZlYjU5ZjgyIiwiaXNzIjoiaHR0cHM6Ly9hdXRoLnJ0bC5kZS9hdXRoL3JlYWxtcy9ydGxwbHVzIiwic3ViIjoiNWYyODFmOTAtOWM5OS00MzcwLWFmZDYtMTM1N2ZlMDc2N2YxIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoiYW5vbnltb3VzLXVzZXIiLCJhbGxvd2VkLW9yaWdpbnMiOlsiKiJdLCJzY29wZSI6IiIsImNsaWVudEhvc3QiOiI5MS4xNjQuNS4xOTkiLCJjbGllbnRJZCI6ImFub255bW91cy11c2VyIiwiaXNHdWVzdCI6dHJ1ZSwicGVybWlzc2lvbnMiOnsiZ2VuZXJhbCI6eyJwb3J0YWJpbGl0eSI6ZmFsc2UsImFscGhhViI6dHJ1ZSwibWF4QW1vdW50T2ZQcm9maWxlcyI6NCwibWF4TXBhUHJvZmlsZXMiOjQsInNldFBpbiI6ZmFsc2UsIm1heERvd25sb2FkRGV2aWNlcyI6MCwiYWNjZXNzUHJlU2FsZSI6ZmFsc2V9LCJzdHJlYW1pbmciOnsidm9kQWNjZXNzVG9GcmVlQ29udGVudCI6dHJ1ZSwidm9kQWNjZXNzVG9QYXlDb250ZW50IjpmYWxzZSwibGl2ZXN0cmVhbUFjY2Vzc1RvRnJlZVR2IjpmYWxzZSwibGl2ZXN0cmVhbUFjY2Vzc1RvUGF5VHYiOmZhbHNlLCJsaXZlc3RyZWFtQWNjZXNzVG9GYXN0Ijp0cnVlLCJ2b2RRdWFsaXR5IjoiTE9XIiwibGl2ZVF1YWxpdHkiOiJMT1ciLCJmYXN0UXVhbGl0eSI6IkxPVyIsIm1heFBhcmFsbGVsU3RyZWFtcyI6MSwibGl2ZWV2ZW50QWNjZXNzVG9GcmVlVHYiOnRydWUsImxpdmVldmVudEFjY2Vzc1RvUGF5VHYiOmZhbHNlfSwid2F0Y2hGZWF0dXJlcyI6eyJjb250ZW50RG93bmxvYWQiOmZhbHNlLCJvcmlnaW5hbFZlcnNpb24iOmZhbHNlLCJjb250aW51ZVdhdGNoaW5nIjpmYWxzZSwic2tpcEFkIjpmYWxzZSwiZG9sYnkiOmZhbHNlLCJib29rbWFya1dhdGNoIjpmYWxzZX0sImFkdmVydGlzaW5nIjp7Im1heFByZVJvbGxzIjozLCJtaWRSb2xscyI6dHJ1ZSwicG9zdFJvbGxzIjp0cnVlLCJjaGFwdGVycyI6dHJ1ZSwic3BlY2lhbEFkcyI6ZmFsc2UsImJyZWFrQWRzIjpmYWxzZSwiYWRTY2hlbWUiOiJhZGFfZnJlZSIsInRlZFBheUFkdmVydGlzZW1lbnQiOmZhbHNlfSwibXVzaWMiOnsiYWNjZXNzTXVzaWNDb250ZW50IjpmYWxzZSwiYWNjZXNzTXVzaWNDb250ZW50T3RoZXJQcm9maWxlcyI6ZmFsc2UsImRlZXplck9mZmVyQ29kZSI6LTEsImRlZXplclRyaWFsT2ZmZXJDb2RlIjotMSwiZGVlemVyTWF4UGFyYWxsZWxTdHJlYW1zIjowLCJ2aWV3TXVzaWNDb250ZW50Ijp0cnVlLCJtYXhEZWV6ZXJEb3dubG9hZERldmljZXMiOjAsIm1heERlZXplckRvd25sb2FkRGV2aWNlc090aGVyUHJvZmlsZXMiOjB9LCJwb2RjYXN0cyI6eyJib29rbWFya1BvZGNhc3RzIjpmYWxzZSwiYWNjZXNzRnJlZVBvZGNhc3RzIjp0cnVlLCJhY2Nlc3NQcmVtaXVtUG9kY2FzdHMiOmZhbHNlLCJmb2xsb3dQb2RjYXN0cyI6ZmFsc2UsImRvd25sb2FkUG9kY2FzdHMiOmZhbHNlLCJjb250aW51ZUxpc3RlbmluZ1BvZGNhc3RzIjpmYWxzZX0sInJhZGlvIjp7ImFjY2Vzc1JhZGlvQ29udGVudCI6dHJ1ZX0sIm1hZ2F6aW5lIjp7ImFydGljbGVDcmVkaXRzIjowLCJhY2Nlc3NNYWdhemluZUFydGljbGVzIjpmYWxzZSwiYnJhbmRTdWJzY3JpcHRpb25TbG90cyI6MCwiYm9va21hcmtNYWdhemluZSI6ZmFsc2V9LCJhdWRpb2Jvb2tzIjp7ImNhblJlZGVlbUNyZWRpdCI6ZmFsc2UsImNhblJlZGVlbUNyZWRpdE90aGVyUHJvZmlsZXMiOmZhbHNlLCJhY2Nlc3NEZWV6ZXJBdWRpb2Jvb2tzIjpmYWxzZSwiYWNjZXNzRGVlemVyQXVkaW9ib29rc090aGVyUHJvZmlsZXMiOmZhbHNlLCJhY2Nlc3NQcmhBdWRpb2Jvb2tzIjpmYWxzZSwiYWNjZXNzUHJoQXVkaW9ib29rc090aGVyUHJvZmlsZXMiOmZhbHNlLCJhY2Nlc3NCb3VnaHRQcmhBdWRpb2Jvb2tzIjpmYWxzZSwiYWNjZXNzQm91Z2h0UHJoQXVkaW9ib29rc090aGVyUHJvZmlsZXMiOmZhbHNlLCJwcmhDcmVkaXRzIjowLCJwcmhNYXhQYXJhbGxlbFN0cmVhbXMiOjB9LCJ0b2dnbyI6eyJza2lwQWR2ZXJ0aXNpbmciOmZhbHNlfX0sImNsaWVudEFkZHJlc3MiOiI5MS4xNjQuNS4xOTkifQ.mZTkPjVYFreAK79jqX5jv6Yujh7bPt-nYNRGJpJHyFRUhAn0cywEIvnjXNvHlx2fCE0aGmG4H9tvPX-kyittyi_wANkOEs4DNSI_IwQrCiyXC1kQnQscVkbnXTly1AGHhEtMeCNlf16k8v7CyF-cDTet_1FmKOXdPCMnH3wppJoLjPvP0tadwbF0sFOUuaIn4bnZEkDoF-7S9B-jcHHQ-Z4ZaElqkf4gJ4qZNEuHiYdbw3fPOn6LQHbxSPKIl9rZnUzzOQr-3EkrTFgAdVCPcIqfQR0qRIILw9odxsYRwLAcdy85bbokOEhZ-yrQFkGWccZ_sCeAK96H6LVpWkS5YA"
        HEADERS = {
            'rtlplus-client-Id': 'rci:rtlplus:web',
            'rtlplus-client-Version': '2024.1.16.2',
            'Authorization': f'Bearer {TOKEN}'
        }

        # TODO: get the URL from the webpage
        URL = 'https://cdn.gateway.now-plus-prod.aws-cbc.cloud/graphql?operationName=PodcastEpisode&variables=%7B%22id%22:%22vpyvzbrxkkx39%22,%22take%22:1%7D&extensions=%7B%22persistedQuery%22:%7B%22version%22:1,%22sha256Hash%22:%222693e24ad538a69c8698cf1fcbf984cfa49c7592cf5404cb4369167eab694ee0%22%7D%7D'
        # https://cdn.gateway.now-plus-prod.aws-cbc.cloud/graphql?operationName=PodcastEpisode&variables=
        # {"id":"vpyvzbrxkkx39","take":1}&extensions={"persistedQuery":{"version":1,"sha256Hash":"2693e24ad538a69c8698cf1fcbf984cfa49c7592cf5404cb4369167eab694ee0"}}

        webpage = self._download_webpage(URL, video_slug, headers=HEADERS)
        # print(webpage)

        json = self._parse_json(webpage, video_slug)
        assert json
        data = json['data']

        return {
            # TODO: It looks like even though the correct URL is returned, yt-dlp messes up the download.
            # It works with wget, so it's not an auth problem.
            'url': data['podcastEpisode']['url'],
            'id': data['podcastEpisode']['id'],
            'title': data['podcastEpisode']['title'],
            'description': data['podcastEpisode']['description'],
            # TODO more properties (see yt_dlp/extractor/common.py)
        }

# example API answer:
# {
#     "data": {
#         "podcastEpisode": {
#             "__typename": "PodcastEpisode",
#             "id": "rrn:podcast:external:episode:vpyvzbrxkkx39",
#             "title": "Revolution im Business: Künstliche Intelligenz im Fokus",
#             "description": "In dieser Folge tauchen wir in die Welt der künstlichen Intelligenz im Unternehmensumfeld ein. Gemeinsam mit SYNAXON-Vorstand Frank Roebers werfen wir einen Blick auf die vielfältigen Anwendungsgebiete von Künstlicher Intelligenz in Unternehmen und diskutieren, wie diese Technologien transformative Veränderungen bewirken können. Die Folge bietet nicht nur einen Überblick über aktuelle KI-Trends, sondern beleuchtet auch die Herausforderungen und ethischen Aspekte, die mit dem verstärkten Einsatz von KI verbunden sind. Frank teilt seine Expertise und Erfahrungen, um uns einen umfassenden Einblick in die Zukunft der Unternehmenswelt durch Künstliche Intelligenz zu geben. Begleitet uns auf dieser spannenden Reise in die Welt der Technologie!",
#             "type": "PODCAST_EPISODE",
#             "episodeType": "FULL",
#             "url": "https://it-gefluester.podcaster.de/it-gefluester/media/Podcast_Frank_Roebers_KI_Im_Unternehmen_122023_-_28-12-23-_22-14.mp3",
#             "duration": 2413,
#             "releaseDate": "2024-01-15T05:00:00.000Z",
#             "episodePosition": "FIRST",
#             "mediaTier": "FREE",
#             "image": {
#                 "imageFormat": {
#                     "url": "https://media.plus.rtl.de/podcast/revolution-im-business-kuenstliche-intelligenz-im-fokus-b2adud99hw2so.png",
#                     "__typename": "ImageFormat"
#                 },
#                 "small": {
#                     "width": 500,
#                     "height": 500,
#                     "url": "https://media.plus.rtl.de/podcast/revolution-im-business-kuenstliche-intelligenz-im-fokus-b2adud99hw2so.png?tr=w-500,h-500",
#                     "__typename": "ImageFormat"
#                 },
#                 "__typename": "UploadFile"
#             },
#             "seo": {
#                 "index": true,
#                 "title": "Revolution im Business: Künstliche Intelligenz im Fokus | RTL+",
#                 "description": "Revolution im Business: Künstliche Intelligenz im Fokus aus IT-Geflüster ► Alle Folgen auf RTL+ Podcast!",
#                 "__typename": "Seo"
#             },
#             "seasonNumber": 1,
#             "episodeNumber": 1,
#             "canonicalPath": "/podcast/it-gefluester-swkanad6uxwwh/revolution-im-business-kuenstliche-intelligenz-im-fokus-vpyvzbrxkkx39",
#             "canonicalUrl": "https://plus.rtl.de/podcast/it-gefluester-swkanad6uxwwh/revolution-im-business-kuenstliche-intelligenz-im-fokus-vpyvzbrxkkx39"
#         }
#     },
#     "extensions": {
#         "traceId": "64e4c007ebac8d583fef9f3c3e162921"
#     }
# }
