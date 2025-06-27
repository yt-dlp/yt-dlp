import json
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_iso8601,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class BoxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^.]+\.)?(?P<service>app|ent)\.box\.com/s/(?P<shared_name>[^/?#]+)(?:/file/(?P<id>\d+))?'
    _TESTS = [{
        'url': 'https://mlssoccer.app.box.com/s/0evd2o3e08l60lr4ygukepvnkord1o1x/file/510727257538',
        'md5': '1f81b2fd3960f38a40a3b8823e5fcd43',
        'info_dict': {
            'id': '510727257538',
            'ext': 'mp4',
            'title': 'Garber   St. Louis will be 28th MLS team  +scarving.mp4',
            'uploader': '',
            'timestamp': 1566320259,
            'upload_date': '20190820',
            'uploader_id': '235196876',
        },
        'params': {'skip_download': 'dash fragment too small'},
    }, {
        'url': 'https://utexas.app.box.com/s/2x6vanv85fdl8j2eqlcxmv0gp1wvps6e',
        'info_dict': {
            'id': '787379022466',
            'ext': 'mp4',
            'title': 'Webinar recording: Take the Leap!.mp4',
            'uploader': 'Patricia Mosele',
            'timestamp': 1615824864,
            'upload_date': '20210315',
            'uploader_id': '239068974',
        },
        'params': {'skip_download': 'dash fragment too small'},
    }, {
        'url': 'https://thejacksonlaboratory.ent.box.com/s/2x09dm6vcg6y28o0oox1so4l0t8wzt6l/file/1536173056065',
        'info_dict': {
            'id': '1536173056065',
            'ext': 'mp4',
            'uploader_id': '18523128264',
            'uploader': 'Lexi Hennigan',
            'title': 'iPSC Symposium recording part 1.mp4',
            'timestamp': 1716228343,
            'upload_date': '20240520',
        },
        'params': {'skip_download': 'dash fragment too small'},
    }]

    def _real_extract(self, url):
        shared_name, file_id, service = self._match_valid_url(url).group('shared_name', 'id', 'service')
        webpage = self._download_webpage(url, file_id or shared_name)

        if not file_id:
            post_stream_data = self._search_json(
                r'Box\.postStreamData\s*=', webpage, 'Box post-stream data', shared_name)
            shared_item = traverse_obj(
                post_stream_data, ('/app-api/enduserapp/shared-item', {dict})) or {}
            if shared_item.get('itemType') != 'file':
                raise ExtractorError('The requested resource is not a file', expected=True)

            file_id = str(shared_item['itemID'])

        request_token = self._search_json(
            r'Box\.config\s*=', webpage, 'Box config', file_id)['requestToken']
        access_token = self._download_json(
            f'https://{service}.box.com/app-api/enduserapp/elements/tokens', file_id,
            'Downloading token JSON metadata',
            data=json.dumps({'fileIDs': [file_id]}).encode(), headers={
                'Content-Type': 'application/json',
                'X-Request-Token': request_token,
                'X-Box-EndUser-API': 'sharedName=' + shared_name,
            })[file_id]['read']
        shared_link = f'https://{service}.box.com/s/{shared_name}'
        f = self._download_json(
            'https://api.box.com/2.0/files/' + file_id, file_id,
            'Downloading file JSON metadata', headers={
                'Authorization': 'Bearer ' + access_token,
                'BoxApi': 'shared_link=' + shared_link,
                'X-Rep-Hints': '[dash]',  # TODO: extract `hls` formats
            }, query={
                'fields': 'authenticated_download_url,created_at,created_by,description,extension,is_download_available,name,representations,size',
            })
        title = f['name']

        query = {
            'access_token': access_token,
            'shared_link': shared_link,
        }

        formats = []

        for url_tmpl in traverse_obj(f, (
            'representations', 'entries', lambda _, v: v['representation'] == 'dash',
            'content', 'url_template', {url_or_none},
        )):
            manifest_url = update_url_query(url_tmpl.replace('{+asset_path}', 'manifest.mpd'), query)
            fmts = self._extract_mpd_formats(manifest_url, file_id)
            for fmt in fmts:
                fmt['extra_param_to_segment_url'] = urllib.parse.urlparse(manifest_url).query
            formats.extend(fmts)

        creator = f.get('created_by') or {}

        return {
            'id': file_id,
            'title': title,
            'formats': formats,
            'description': f.get('description') or None,
            'uploader': creator.get('name'),
            'timestamp': parse_iso8601(f.get('created_at')),
            'uploader_id': creator.get('id'),
        }
