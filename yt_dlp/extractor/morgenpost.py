import json
import re

from yt_dlp.utils import extract_attributes

from .common import InfoExtractor
from ..utils.traversal import traverse_obj


class MorgenpostIE(InfoExtractor):
    _VALID_URL = r'https://www\.morgenpost\.de/'
    _TESTS = [{
        'url': 'https://www.morgenpost.de/politik/article409798440/elon-musk-ist-auffallend-zurueckhaltend-das-hat-einen-grund.html',
        'md5': 'e2032f407cef5b43f9ae28ef178c613d',
        'info_dict': {
            'id': '0_aknfdfyy',
            'ext': 'mp4',
            'url': 'https://akcdn.vtv.funkedigital.de/akhls/p/105/sp/10500/serveFlavor/entryId/0_aknfdfyy/v/2/ev/6/flavorId/0_hqyudat2/name/a.mp4/index.m3u8',
            'title': 'Milliarden für Musk: Tesla stellt Aktienpaket in Aussicht',
            'description': 'Elon Musk muss seit Jahren um Tesla-Aktien im Milliardenwert bangen. Der Autobauer garantiert ihm jetzt ein neues Paket - sofern er noch zwei Jahre in der Chefetage bleibt.',
            'thumbnail': 'https://cdn.vtv.funkedigital.de/p/105/sp/10500/thumbnail/entry_id/0_aknfdfyy/version/100022',
            'duration': 56,
            'timestamp': 1754312799,
            'upload_date': '20250804',
            'modified_timestamp': int,
            'modified_date': str,
            'tags': 'count:9',
        },
    }]

    def _real_extract(self, url):
        # FINDING VIDEO URL
        webpage = self._download_webpage(url, url)
        for figure in re.findall(r'<figure[^>]+data-video-id=[^>]+>', webpage):
            video_id = extract_attributes(figure).get('data-video-id')
        for jsonld in self._yield_json_ld(webpage, url):
            if jsonld.get('@type') == 'Newsarticle':
                break

        # DOWNLOADING METADATA
        multirequest = self._download_json('https://front.vtv.funkedigital.de/api_v3/service/multirequest', video_id, data=json.dumps({
            '1': {'service': 'session',
                  'action': 'startWidgetSession',
                  'widgetId': '_105'},
            '2': {'service': 'baseEntry',
                  'action': 'list',
                  'ks': '{1:result:ks}',
                  'filter': {'redirectFromEntryId': video_id},
                  'responseProfile': {'type': 1, 'fields': '''id,referenceId,name,description,thumbnailUrl,dataUrl,duration,msDuration,flavorParamsIds,mediaType,
                                                                type,tags,dvrStatus,externalSourceType,status,createdAt,updatedAt,endDate,plays,views,downloadUrl,creatorId'''}},
            '3': {'service': 'baseEntry',
                  'action': 'getPlaybackContext',
                  'entryId': '{2:result:objects:0:id}',
                  'ks': '{1:result:ks}',
                  'contextDataParams': {'objectType': 'KalturaContextDataParams', 'flavorTags': 'all'}},
            'apiVersion': '3.3.0',
            'format': 1,
            'ks': '',
            'clientTag': 'html5:v3.17.5',
            'partnerId': '105',
        }).encode(), headers={'content-type': 'application/json'})
        metadata = traverse_obj(multirequest, (1, 'objects', 0))

        # DOWNLOADING LIST OF SOURCES (LIST OF M3U8 FILES)
        playbackSource = traverse_obj(multirequest, (2, 'sources', 0))
        if playbackSource['drm'] == []:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(playbackSource['url'], video_id)
        else:
            self.report_drm(video_id)

        # Helper to turn string "item, item" into list ['item', 'item']
        def strToList(string):
            return [item.strip() for item in string.split(',')]

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(metadata, {
                'title': 'name',
                'description': 'description',
                'thumbnail': 'thumbnailUrl',
                'duration': 'duration',
                'timestamp': 'createdAt',
                'modified_timestamp': 'updatedAt',
                'tags': ('tags', {strToList}),
            }),
        }
