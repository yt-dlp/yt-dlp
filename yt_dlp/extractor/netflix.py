from .common import InfoExtractor
import json
import re
from ..utils import clean_html


def unicode_escape(string):
    return bytes(string, 'ascii').decode('unicode_escape')


def getVideoManifest(self, videoID, codecs):
    endpoint = 'https://www.netflix.com/nq/cadmium/pbo_manifests/%5E1.0.0/router'
    headers = {
        'host': 'www.netflix.com',
        'content-type': 'text/plain',
    }
    data = json.dumps({'version': 2, 'url': 'manifest', 'id': 164140345434876480, 'params': {'type': 'standard', 'manifestVersion': 'v2', 'viewableId': videoID, 'profiles': codecs, 'flavor': 'SUPPLEMENTAL', 'drmType': 'playready', 'drmVersion': 30, 'usePsshBox': True, 'isBranching': False, 'useHttpsStreams': True, 'supportsUnequalizedDownloadables': True, 'imageSubtitleHeight': 720, 'uiVersion': 'shakti-v2ecd1c2b', 'uiPlatform': 'SHAKTI', 'clientVersion': '6.0033.414.911', 'supportsPreReleasePin': True, 'supportsWatermark': True, 'deviceSecurityLevel': '3000', 'videoOutputInfo': [{'type': 'DigitalVideoOutputDescriptor', 'outputType': 'unknown', 'supportedHdcpVersions': ['2.2'], 'isHdcpEngaged':True}], 'titleSpecificData': {videoID: {'unletterboxed': False}}, 'preferAssistiveAudio': False, 'isUIAutoPlay': False, 'isNonMember': True, 'desiredVmaf': 'plus_lts', 'desiredSegmentVmaf': 'plus_lts', 'requestSegmentVmaf': False, 'supportsPartialHydration': False, 'contentPlaygraph': [], 'showAllSubDubTracks': False, 'maxSupportedLanguages': 30}})
    response = self._download_json(endpoint, videoID, data=(data.encode()), headers=headers)
    return response


def VideoInfo(self, id):
    vcodecs = [
        ["vp9-profile0-L21-dash-cenc", "vp9-profile0-L30-dash-cenc", "vp9-profile0-L31-dash-cenc", "vp9-profile0-L40-dash-cenc"],
        ["playready-h264mpl30-dash", "playready-h264mpl31-dash", "playready-h264mpl40-dash", "playready-h264hpl22-dash", "playready-h264hpl30-dash", "playready-h264hpl31-dash", "playready-h264hpl40-dash"], ["hevc-main10-L30-dash-cenc", "hevc-main10-L31-dash-cenc", "hevc-main10-L40-dash-cenc", "hevc-main10-L41-dash-cenc", "hevc-main10-L50-dash-cenc", "hevc-main10-L51-dash-cenc"],
        ["hevc-main10-L30-dash-cenc-prk", "hevc-main10-L31-dash-cenc-prk", "hevc-main10-L40-dash-cenc-prk", "hevc-main10-L41-dash-cenc-prk"],
        ["hevc-main10-L30-dash-cenc-prk-do", "hevc-main10-L31-dash-cenc-prk-do", "hevc-main10-L40-dash-cenc-prk-do", "hevc-main10-L41-dash-cenc-prk-do", "hevc-main10-L50-dash-cenc-prk-do", "hevc-main10-L51-dash-cenc-prk-do"],
        ["hevc-dv5-main10-L30-dash-cenc-prk", "hevc-dv5-main10-L31-dash-cenc-prk", "hevc-dv5-main10-L40-dash-cenc-prk", "hevc-dv5-main10-L41-dash-cenc-prk", "hevc-dv5-main10-L50-dash-cenc-prk", "hevc-dv5-main10-L51-dash-cenc-prk"],
        ["hevc-dv5-main10-L30-dash-cenc-prk-do", "hevc-dv5-main10-L31-dash-cenc-prk-do", "hevc-dv5-main10-L40-dash-cenc-prk-do", "hevc-dv5-main10-L41-dash-cenc-prk-do", "hevc-dv5-main10-L50-dash-cenc-prk-do", "hevc-dv5-main10-L51-dash-cenc-prk-do"],
        ["hevc-hdr-main10-L30-dash-cenc", "hevc-hdr-main10-L31-dash-cenc", "hevc-hdr-main10-L40-dash-cenc", "hevc-hdr-main10-L41-dash-cenc", "hevc-hdr-main10-L50-dash-cenc", "hevc-hdr-main10-L51-dash-cenc"],
        ["hevc-hdr-main10-L30-dash-cenc-prk", "hevc-hdr-main10-L31-dash-cenc-prk", "hevc-hdr-main10-L40-dash-cenc-prk", "hevc-hdr-main10-L41-dash-cenc-prk", "hevc-hdr-main10-L50-dash-cenc-prk", "hevc-hdr-main10-L51-dash-cenc-prk"],
        ["hevc-hdr-main10-L30-dash-cenc-prk-do", "hevc-hdr-main10-L31-dash-cenc-prk-do", "hevc-hdr-main10-L40-dash-cenc-prk-do", "hevc-hdr-main10-L41-dash-cenc-prk-do", "hevc-hdr-main10-L50-dash-cenc-prk-do", "hevc-hdr-main10-L51-dash-cenc-prk-do"],
        ["av1-main-L20-dash-cbcs-prk", "av1-main-L21-dash-cbcs-prk", "av1-main-L30-dash-cbcs-prk", "av1-main-L31-dash-cbcs-prk", "av1-main-L40-dash-cbcs-prk", "av1-main-L41-dash-cbcs-prk", "av1-main-L50-dash-cbcs-prk", "av1-main-L51-dash-cbcs-prk"]
    ]

    acodecs = ["heaac-2-dash", "heaac-5.1-dash", "heaac-2hq-dash", "xheaac-dash", "ddplus-2.0-dash", "ddplus-5.1-dash", "ddplus-atmos-dash"]
    scodecs = ["simplesdh", "dfxp-ls-sdh", "webvtt-lssdh-ios8", "nflx-cmisc"]
    url = []
    a = 0
    for vc in vcodecs:
        vm = getVideoManifest(self, id, vc + acodecs + scodecs)

        if "error" in vm:
            break
        else:

            if a == 0:
                for langnode in reversed(vm["result"]["audio_tracks"]):
                    for node in langnode["streams"]:

                        aurl = {
                            'url': node["urls"][0]["url"],
                            'format_id': str(node["downloadable_id"]),
                            'abr': node["bitrate"],
                            'ext': "mp3",
                            'filesize': node["size"],
                            'acodec': node['content_profile'],
                            'vcodec': "none",
                            'language': node["language"]
                        }
                        url.append(aurl)
            a = 1
        for node in vm["result"]["video_tracks"][0]["streams"]:
            vurl = {
                'url': node["urls"][0]["url"],
                'width': node['res_w'],
                'height': node['res_h'],
                'format_id': node['downloadable_id'],
                'fps': node["framerate_value"],
                'vbr': node["bitrate"],
                'ext': "mp4",
                'filesize': node["size"],
                'vcodec': node["content_profile"],
                'acodec': "none"
            }
            url.append(vurl)

    return(url)


class NetflixIE(InfoExtractor):
    _VALID_URL = 'https?://(?:www\\.)?netflix\\.com/(?:.+)/title/(?P<id>[0-9]+)'
    _TESTS = [
        {'url': 'https://www.netflix.com/it/title/81435227',
         'md5': '39e039c8e670210277c9d7c9c5dd9630',
         'info_dict': {
             'id': '81441302',
             'ext': 'mp4',
             'title': 'Trailer: Un padre',
             'duration': 152,
             'release_timestamp': 1620649800000,
             'categories': ['TRAILER']
         }},
        {'url': 'https://www.netflix.com/it/title/81252357',
         'md5': '0ebf264c4ed3ee8ed684da8c7ce3cb60',
         'info_dict': {
             'id': '81510852',
             'ext': 'mp4',
             'title': 'Trailer: Don\'t Look Up',
             'duration': 148,
             'release_timestamp': 1637078400000,
             'categories': ['TRAILER']
         }}
    ]

    def _real_extract(self, url):
        content_id = self._match_id(url)
        headers = {'host': 'www.netflix.com',
                   'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.62',
                   'origin': 'https://www.netflix.com',
                   }
        webpage = self._download_webpage(url, content_id, headers=headers)
        reactJS = clean_html(re.findall('<script>window\\.netflix = window\\.netflix.*;</script>', webpage)[0])
        reactJSON = self._search_regex('netflix\\.reactContext\\ \\=(.*)[;]', reactJS, 'JSON from webpage')
        reactJSON = re.sub('\\\\(x[A-Z0-9]{2})', '\\\\\\\\\\g<1>', reactJSON, 0, re.MULTILINE)
        json_list = json.loads(reactJSON)
        if 'title' in json_list:
            idList = json_list['models']['nmTitleUI']['data']['sectionData'][2]['data']['supplementalVideos']
            pl = {'_type': 'playlist',
                  'title': unicode_escape(json_list['models']['nmTitleUI']['data']['sectionData'][0]['data']['title']),
                  'id': content_id,
                  'entries': []}
            for element in idList:
                item = {'_type': 'video', 'id': str(element['id']),
                        'title': unicode_escape(element['title']),
                        'formats': VideoInfo(self, element['id']),
                        'release_timestamp': element['availabilityStartDate'],
                        'duration': element['runtime'],
                        'categories': [
                    element['subType']]}
                pl['entries'].append(item)
            else:
                return pl

        self.report_warning('Extractor Error')
        if 'models' in json_list:
            self.report_warning('Specify your locale in the url')
        return {'error': 'error'}
