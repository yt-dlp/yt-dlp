from .common import InfoExtractor
import json
import re
from ..utils import (clean_html, try_get, traverse_obj, url_or_none, int_or_none, str_or_none, parse_duration)


def unicode_escape(string):
    return bytes(string, 'ascii').decode('unicode_escape')


def getVideoManifest(self, videoID, codecs, note):
    endpoint = 'https://www.netflix.com/nq/cadmium/pbo_manifests/%5E1.0.0/router'
    headers = {
        'host': 'www.netflix.com',
        'content-type': 'text/plain',
    }
    data = json.dumps({'version': 2, 'url': 'manifest', 'id': 164140345434876480, 'params': {'type': 'standard', 'manifestVersion': 'v2', 'viewableId': videoID, 'profiles': codecs, 'flavor': 'SUPPLEMENTAL', 'drmType': 'playready', 'drmVersion': 30, 'usePsshBox': True, 'isBranching': False, 'useHttpsStreams': True, 'supportsUnequalizedDownloadables': True, 'imageSubtitleHeight': 720, 'uiVersion': 'shakti-v2ecd1c2b', 'uiPlatform': 'SHAKTI', 'clientVersion': '6.0033.414.911', 'supportsPreReleasePin': True, 'supportsWatermark': True, 'deviceSecurityLevel': '3000', 'videoOutputInfo': [{'type': 'DigitalVideoOutputDescriptor', 'outputType': 'unknown', 'supportedHdcpVersions': ['2.2'], 'isHdcpEngaged':True}], 'titleSpecificData': {videoID: {'unletterboxed': False}}, 'preferAssistiveAudio': False, 'isUIAutoPlay': False, 'isNonMember': True, 'desiredVmaf': 'plus_lts', 'desiredSegmentVmaf': 'plus_lts', 'requestSegmentVmaf': False, 'supportsPartialHydration': False, 'contentPlaygraph': [], 'showAllSubDubTracks': True, 'maxSupportedLanguages': 30}})
    response = self._download_json(endpoint, videoID, data=(data.encode()), headers=headers, note=note)
    return response


def VideoInfo(self, id):
    vcodecs = {
        "VP9": ["vp9-profile0-L21-dash-cenc", "vp9-profile0-L30-dash-cenc", "vp9-profile0-L31-dash-cenc", "vp9-profile0-L40-dash-cenc"],
        "H264": ["playready-h264mpl30-dash", "playready-h264mpl31-dash", "playready-h264mpl40-dash", "playready-h264hpl22-dash", "playready-h264hpl30-dash", "playready-h264hpl31-dash", "playready-h264hpl40-dash"],
        "HEVC-MAIN10-DASH-CENC": ["hevc-main10-L30-dash-cenc", "hevc-main10-L31-dash-cenc", "hevc-main10-L40-dash-cenc", "hevc-main10-L41-dash-cenc", "hevc-main10-L50-dash-cenc", "hevc-main10-L51-dash-cenc"],
        "HEVC-MAIN10-DASH-CENC-PRK": ["hevc-main10-L30-dash-cenc-prk", "hevc-main10-L31-dash-cenc-prk", "hevc-main10-L40-dash-cenc-prk", "hevc-main10-L41-dash-cenc-prk"],
        "HEVC-MAIN10-DASH-CENC-PRK-DO": ["hevc-main10-L30-dash-cenc-prk-do", "hevc-main10-L31-dash-cenc-prk-do", "hevc-main10-L40-dash-cenc-prk-do", "hevc-main10-L41-dash-cenc-prk-do", "hevc-main10-L50-dash-cenc-prk-do", "hevc-main10-L51-dash-cenc-prk-do"],
        "HEVC-DV5-MAIN10-DASH-CENC-PRK": ["hevc-dv5-main10-L30-dash-cenc-prk", "hevc-dv5-main10-L31-dash-cenc-prk", "hevc-dv5-main10-L40-dash-cenc-prk", "hevc-dv5-main10-L41-dash-cenc-prk", "hevc-dv5-main10-L50-dash-cenc-prk", "hevc-dv5-main10-L51-dash-cenc-prk"],
        "HEVC-DV5-MAIN10-DASH-CENC-PRK-DO": ["hevc-dv5-main10-L30-dash-cenc-prk-do", "hevc-dv5-main10-L31-dash-cenc-prk-do", "hevc-dv5-main10-L40-dash-cenc-prk-do", "hevc-dv5-main10-L41-dash-cenc-prk-do", "hevc-dv5-main10-L50-dash-cenc-prk-do", "hevc-dv5-main10-L51-dash-cenc-prk-do"],
        "HEVC-HDR-MAIN10-DASH-CENC": ["hevc-hdr-main10-L30-dash-cenc", "hevc-hdr-main10-L31-dash-cenc", "hevc-hdr-main10-L40-dash-cenc", "hevc-hdr-main10-L41-dash-cenc", "hevc-hdr-main10-L50-dash-cenc", "hevc-hdr-main10-L51-dash-cenc"],
        "HEVC-HDR-MAIN10-DASH-CENC-PRK": ["hevc-hdr-main10-L30-dash-cenc-prk", "hevc-hdr-main10-L31-dash-cenc-prk", "hevc-hdr-main10-L40-dash-cenc-prk", "hevc-hdr-main10-L41-dash-cenc-prk", "hevc-hdr-main10-L50-dash-cenc-prk", "hevc-hdr-main10-L51-dash-cenc-prk"],
        "HEVC-HDR-MAIN10-DASH-CENC-PRK-DO": ["hevc-hdr-main10-L30-dash-cenc-prk-do", "hevc-hdr-main10-L31-dash-cenc-prk-do", "hevc-hdr-main10-L40-dash-cenc-prk-do", "hevc-hdr-main10-L41-dash-cenc-prk-do", "hevc-hdr-main10-L50-dash-cenc-prk-do", "hevc-hdr-main10-L51-dash-cenc-prk-do"],
        "AV1": ["av1-main-L20-dash-cbcs-prk", "av1-main-L21-dash-cbcs-prk", "av1-main-L30-dash-cbcs-prk", "av1-main-L31-dash-cbcs-prk", "av1-main-L40-dash-cbcs-prk", "av1-main-L41-dash-cbcs-prk", "av1-main-L50-dash-cbcs-prk", "av1-main-L51-dash-cbcs-prk"]
    }

    vcodeclist = {
        "vp9": ["vp9-profile0-L21-dash-cenc", "vp9-profile0-L30-dash-cenc", "vp9-profile0-L31-dash-cenc", "vp9-profile0-L40-dash-cenc"],
        "h264": ["playready-h264mpl30-dash", "playready-h264mpl31-dash", "playready-h264mpl40-dash", "playready-h264hpl22-dash", "playready-h264hpl30-dash", "playready-h264hpl31-dash", "playready-h264hpl40-dash"],
        "h265": ["hevc-main10-L30-dash-cenc", "hevc-main10-L31-dash-cenc", "hevc-main10-L40-dash-cenc", "hevc-main10-L41-dash-cenc", "hevc-main10-L50-dash-cenc", "hevc-main10-L51-dash-cenc", "hevc-main10-L30-dash-cenc-prk", "hevc-main10-L31-dash-cenc-prk", "hevc-main10-L40-dash-cenc-prk", "hevc-main10-L41-dash-cenc-prk", "hevc-main10-L30-dash-cenc-prk-do", "hevc-main10-L31-dash-cenc-prk-do", "hevc-main10-L40-dash-cenc-prk-do", "hevc-main10-L41-dash-cenc-prk-do", "hevc-main10-L50-dash-cenc-prk-do", "hevc-main10-L51-dash-cenc-prk-do", "hevc-dv5-main10-L30-dash-cenc-prk", "hevc-dv5-main10-L31-dash-cenc-prk", "hevc-dv5-main10-L40-dash-cenc-prk", "hevc-dv5-main10-L41-dash-cenc-prk", "hevc-dv5-main10-L50-dash-cenc-prk", "hevc-dv5-main10-L51-dash-cenc-prk", "hevc-dv5-main10-L30-dash-cenc-prk-do", "hevc-dv5-main10-L31-dash-cenc-prk-do", "hevc-dv5-main10-L40-dash-cenc-prk-do", "hevc-dv5-main10-L41-dash-cenc-prk-do", "hevc-dv5-main10-L50-dash-cenc-prk-do", "hevc-dv5-main10-L51-dash-cenc-prk-do", "hevc-hdr-main10-L30-dash-cenc", "hevc-hdr-main10-L31-dash-cenc", "hevc-hdr-main10-L40-dash-cenc", "hevc-hdr-main10-L41-dash-cenc", "hevc-hdr-main10-L50-dash-cenc", "hevc-hdr-main10-L51-dash-cenc", "hevc-hdr-main10-L30-dash-cenc-prk", "hevc-hdr-main10-L31-dash-cenc-prk", "hevc-hdr-main10-L40-dash-cenc-prk", "hevc-hdr-main10-L41-dash-cenc-prk", "hevc-hdr-main10-L50-dash-cenc-prk", "hevc-hdr-main10-L51-dash-cenc-prk", "hevc-hdr-main10-L30-dash-cenc-prk-do", "hevc-hdr-main10-L31-dash-cenc-prk-do", "hevc-hdr-main10-L40-dash-cenc-prk-do", "hevc-hdr-main10-L41-dash-cenc-prk-do", "hevc-hdr-main10-L50-dash-cenc-prk-do", "hevc-hdr-main10-L51-dash-cenc-prk-do"],
        "av01": ["av1-main-L20-dash-cbcs-prk", "av1-main-L21-dash-cbcs-prk", "av1-main-L30-dash-cbcs-prk", "av1-main-L31-dash-cbcs-prk", "av1-main-L40-dash-cbcs-prk", "av1-main-L41-dash-cbcs-prk", "av1-main-L50-dash-cbcs-prk", "av1-main-L51-dash-cbcs-prk"]

    }

    def vprofile_to_vcodec(profile):
        for key, value in vcodeclist.items():
            if profile in value:
                return key
        return profile

    def aprofile_to_acodec(profile, ext):
        if "aac" in profile.lower():
            return ("aac")
        if "ddplus" in profile.lower():
            return ("eac3")
        if ext:
            return "mp4"
        else:
            return(profile)

    acodecs = ["heaac-2-dash", "heaac-5.1-dash", "heaac-2hq-dash", "xheaac-dash", "ddplus-2.0-dash", "ddplus-5.1-dash", "ddplus-atmos-dash"]
    scodecs = ["simplesdh", "dfxp-ls-sdh", "webvtt-lssdh-ios8", "nflx-cmisc"]
    url = []
    a = 0
    for vc in vcodecs:
        vm = getVideoManifest(self, id, vcodecs[vc] + acodecs + scodecs, note="Trying Video Profiles: " + vc)
        if "error" in vm:
            continue
        else:
            if a == 0:
                for langnode in reversed(traverse_obj(vm, ("result", "audio_tracks"), default={})):
                    ac = try_get(langnode, lambda x: x["codecName"])
                    for node in traverse_obj(langnode, ("streams"), default={}):
                        aurl = {
                            'url': url_or_none(try_get(node, lambda x: x["urls"][0]["url"])),
                            'format_id': str_or_none(try_get(node, lambda x: x["downloadable_id"])),
                            'abr': try_get(node, lambda x: x["bitrate"]),
                            'ext': aprofile_to_acodec(ac or (try_get(node, lambda x: x["content_profile"])), ext=True),
                            'filesize': try_get(node, lambda x: x["size"]),
                            'acodec': aprofile_to_acodec(ac or (try_get(node, lambda x: x["content_profile"])), ext=False),
                            'vcodec': "none",
                            'language': try_get(node, lambda x: x["language"])
                        }
                        url.append(aurl)
            a = 1
        for node in traverse_obj(vm, ("result", "video_tracks", 0, "streams"), default={}):
            vurl = {
                'url': url_or_none(try_get(node, lambda x: x["urls"][0]["url"])),
                'width': try_get(node, lambda x: x["res_w"]),
                'height': try_get(node, lambda x: x["res_h"]),
                'format_id': try_get(node, lambda x: x["downloadable_id"]),
                'fps': try_get(node, lambda x: x["framerate_value"]),
                'vbr': try_get(node, lambda x: x["bitrate"]),
                'ext': "mp4",
                'filesize': try_get(node, lambda x: x["size"]),
                'vcodec': vprofile_to_vcodec(try_get(node, lambda x: x["content_profile"])),
                'acodec': "none",
                'quality': int_or_none(try_get(node, lambda x: x["vmaf"])),
            }
            url.append(vurl)
    return(url)


class NetflixIE(InfoExtractor):
    _VALID_URL = 'https?://(?:www\\.)?netflix\\.com/(?:.+)/title/(?P<id>[0-9]+)'
    _TESTS = [
        {'url': 'https://www.netflix.com/it-en/title/81435227',
         'md5': '31b52548908fdb2b7eee02b42c65be99',
         'info_dict': {
             'id': '81441302',
             'ext': 'mp4',
             'title': 'Trailer: Fatherhood',
             'duration': 152,
             'release_timestamp': 1620649800000,
             'categories': ['TRAILER']
         }},
        {'url': 'https://www.netflix.com/it-en/title/81252357',
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
        reactJSON = self._search_regex('netflix\\.reactContext\\ \\=(.*)[;]', reactJS, 'JSON from webpage',fatal=False)
        reactJSON = re.sub('\\\\(x[A-Z0-9]{2})', '\\\\\\\\\\g<1>', reactJSON, 0, re.MULTILINE)
        json_list = json.loads(reactJSON)
        if 'title' in json_list:
            idList = traverse_obj(json_list, ("models", "nmTitleUI", 'data', "sectionData", 2, "data", "supplementalVideos"), default={})
            pl = {'_type': 'playlist',
                  'title': unicode_escape(str_or_none(try_get(json_list, lambda x: x['models']['nmTitleUI']['data']['sectionData'][0]['data']['title']))),
                  'id': content_id,
                  'entries': []}
            for element in idList:
                item = {'_type': 'video',
                        'id': str_or_none(try_get(element, lambda x: x["id"])),
                        'title': unicode_escape(try_get(element, lambda x: x["title"])),
                        'formats': VideoInfo(self, try_get(element, lambda x: x["id"])),
                        'release_timestamp': try_get(element, lambda x: x["availabilityStartDate"]),
                        'duration': parse_duration(try_get(element, lambda x: x["runtime"])),
                        'categories': try_get(element, lambda x: x["subType"])}
                pl['entries'].append(item)
            else:
                return pl

        self.report_warning('Extractor Error')
        if 'models' in json_list:
            self.report_warning('Specify your locale in the url')
        return None
