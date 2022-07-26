import json
import uuid

from .common import InfoExtractor


class RedBeeIE(InfoExtractor):
    _VALID_URL = r'redbee:(?P<customer>[\w_-]+):(?P<business_unit>[\w_-]+):(?P<asset_id>[\w_-]+)'
    _DEVICE_ID = str(uuid.uuid4())
    # https://apidocs.emp.ebsd.ericsson.net
    _SERVICE_URL = 'https://exposure.api.redbee.live'

    def _get_bearer_token(self, asset_id, customer, business_unit, auth_type='anonymous', **args):
        request = {
            'deviceId': self._DEVICE_ID,
            'device': {
                'deviceId': self._DEVICE_ID,
                'name': 'Mozilla Firefox 102',
                'type': 'WEB',
            },
        }
        if auth_type == 'gigyaLogin':
            request['jwt'] = args['jwt']

        return self._download_json(
            f'{self._SERVICE_URL}/v2/customer/{customer}/businessunit/{business_unit}/auth/{auth_type}',
            asset_id, data=json.dumps(request).encode('utf-8'), headers={
                'Content-Type': 'application/json;charset=utf-8'
            })['sessionToken']

    def _get_entitlement_formats_and_subtitles(self, asset_id, customer, business_unit, bearer_token):
        api_response = self._download_json(
            f'{self._SERVICE_URL}/v2/customer/{customer}/businessunit/{business_unit}/entitlement/{asset_id}/play',
            asset_id, headers={
                'Authorization': f'Bearer {bearer_token}',
                'Accept': 'application/json, text/plain, */*'
            })

        formats, subtitles = [], {}
        for format in api_response['formats']:
            if not format.get('mediaLocator'):
                continue

            fmts, subs = [], {}
            if format.get('format') == 'DASH':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    format['mediaLocator'], asset_id, fatal=False)
            elif format.get('format') == 'SMOOTHSTREAMING':
                fmts, subs = self._extract_ism_formats_and_subtitles(
                    format['mediaLocator'], asset_id, fatal=False)
            elif format.get('format') == 'HLS':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    format['mediaLocator'], asset_id, fatal=False)

            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        self._sort_formats(formats)
        return formats, subtitles

    def _real_extract(self, url):
        customer, business_unit, asset_id = self._match_valid_url(url).group('customer', 'business_unit', 'asset_id')

        formats, subtitles = self._get_entitlement_formats_and_subtitles(
            asset_id, customer, business_unit, self._get_bearer_token(asset_id, customer, business_unit))

        return {
            'id': asset_id,
            'formats': formats,
            'subtitles': subtitles,
        }
