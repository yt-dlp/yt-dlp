import re

from .adobepass import AdobePassIE
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    join_nonempty,
    parse_age_limit,
    unified_timestamp,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class GoIE(AdobePassIE):
    _SITE_INFO = {
        'abc': {
            'brand': '001',
            'requestor_id': 'dtci',
            'provider_id': 'ABC',
            'software_statement': 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI4OTcwMjlkYS0yYjM1LTQyOWUtYWQ0NS02ZjZiZjVkZTdhOTUiLCJuYmYiOjE2MjAxNzM5NjksImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNjIwMTczOTY5fQ.SC69DVJWSL8sIe-vVUrP6xS_kzHKqwz9PdKYexs_y-f7Vin6mM-7S-W1TE_-K55O0pyf-TL4xYgvm6LIye8CckG-nZfVwNPV4huduov0jmIcxCQFeUwkHULG2IaA44wfBVUBdaHgkhPweZ2amjycO_IXtez-gBXOLbE3B7Gx9j_5ISCFtyVUblThKfoGyQv6KT6t8Vpmc4ZSKCCQp74KWFFypydb9ucego1taW_nQD06Cdf4yByLd6NaTBceMcIKbug9b9gxFm3XBgJ5q3z7KGo1Kr6XalAV5j4m-fQ91wczlTilX8FM4AljMupyRM9mA_aEADILQ4hS79q4SM0w6w',
        },
        'freeform': {
            'brand': '002',
            'requestor_id': 'ABCFamily',
            'provider_id': 'ABCFamily',
            'software_statement': 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhZWM2MGYyNC0xYzRjLTQ1NzQtYjc0Zi03ZmM4N2E5YWMzMzgiLCJuYmYiOjE1ODc2NjU5MjMsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTg3NjY1OTIzfQ.flCn3dhvmvPnWmV0JV8Fm0YFyj07yPez9-n1GFEwVIm_S2wQVWbWyJhqsAyLZVFrhOMZYTqmPS3OHxGwTwXkEYn6PD7o_vIVG3oqi-Xn1m5jRt_Gazw5qEtpat6VE7bvKGSD3ZhcidOrsCk8NcYyq75u61NHDvSl81pcedJjVRVUpsqrEwmo0aVbA0C8PX3ri0mEbGvkMKvHn8E60xp-PSE-VK8SDT0plwPu_TwUszkZ6-_I8_2xcv_WBqcXFkAVg7Q-iNJXgQvmNsrpcrYuLvi6hEH4ZLtoDcXU6MhwTQAJTiHSo8x9aHX1_qFP09CzlNOFQbC2ZEJdP9SvA53SLQ',
        },
        'disneynow': {
            'brand': '011',  # also: '004', '008', '009'
            'requestor_id': 'DisneyChannels',
            'provider_id': 'DisneyChannels',
            'software_statement': 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI1MzAzNTRiOS04NDNiLTRkNjAtYTQ3ZS0yNzk1MzlkOTIyNTciLCJuYmYiOjE1NTg5ODc0NDksImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTU4OTg3NDQ5fQ.Jud6YS6-J2h0h6po0oMheDym0qRTJQGj4kzacrz4DFuEwhcBkkykW6pF5pKuAUJy9HCZ40oDAHe2KcTlDJjCZF5tDaUEfdihakZ9cC_rG7MU-QoRne8qaB_dPDKwGuk-ZyWD8eV3zwTJmbGo8hDxYTEU81YNCxwhyc_BPDr5TYiubbmpP3_pTnXmSpuL58isJ2peSKWlX9BacuXtBY25c_QnPFKk-_EETm7IHkTpDazde1QfHWGu4s4yJpKGk8RVVujVG6h6ELlL-ZeYLilBm7iS7h1TYG1u7fJhyZRL7isaom6NvAzsvN3ngss1fLwt8decP8wzdFHrbYTdTjW8qw',
            'resource_id': 'Disney',
        },
        'fxnetworks': {
            'brand': '025',  # also: '020'
            'requestor_id': 'dtci',
            'provider_id': 'fx',  # also 'fxx', 'fxm'
            'software_statement': 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIzYWRhYWZiNC02OTAxLTRlYzktOTdmNy1lYWZkZTJkODJkN2EiLCJuYmYiOjE1NjIwMjQwNzYsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTYyMDI0MDc2fQ.dhKMpZK50AObbZYrMiYPSfWtzXHUaeMP3jrIY4Cgfvh0GaEgk0Mns_zp78jypFeZgRtPVleQMQDNq2YEloRLcAGqP1aa6WVDglnK77ZWUm4IKai14Rwf3A6YBhSRoO2_lMmUGkuTf6gZY-kMIPqBYKqzTQiQl4HbniPFodIzFRiuI9QJVrkoyTGrJL4oqiX08PoFI3Z-TOti1Heu3EbFC-GveQHhlinYrzU7rbiAqLEz7FImtfBDsnXX1Y3uJDLYM3Bq4Oh0nrzTv1Fd62wNsCNErHHIbELidh1zZF0ujvt7ReuZUwAitm0UhEJ7OxNOUbEQWtae6pVNscvdvTFMpg',
        },
        'nationalgeographic': {
            'brand': '026',  # also '023'
            'requestor_id': 'dtci',
            'provider_id': 'ngc',  # also 'ngw'
            'software_statement': 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMzE4YTM1Ni05Mjc4LTQ4NjEtYTFmNi1jMTIzMzg1ZWMzYzMiLCJuYmYiOjE1NjIwMjM4MjgsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTYyMDIzODI4fQ.Le-2OzF9-jrhJ7ZfWtLWk5iSHGVZoxeU1w0_fO--Heli0OwRZsRq2slSmx-oZTzxuWmAgDEiBkWSDcDK6sM25DrCLsdsJa3MBuZ-slBRtH8aq3HpNoqqLkU-vg6gRUEKMtwBUtwCu_9aKUCayYtndWv4b1DjVQeSrteOW5NNudWVYleAe0kxeNJQHo5If9SCzDudKVJktFUjhNks4QPOC_uONPkRRlL9D0fNvtOY-LRFckfcHhf5z9l1iZjeukV0YhdKnuw1wyiaWrQXBUDiBfbkCRd2DM-KnelqPxfiXCaTjGKDURRBO3pz33ebge3IFXSiU5vl4qHQ8xvunzGpFw',
        },
    }
    _URL_PATH_RE = r'(?:video|episode|movies-and-specials)/(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})'
    _VALID_URL = [
        fr'https?://(?:www\.)?(?P<site>abc)\.com/{_URL_PATH_RE}',
        fr'https?://(?:www\.)?(?P<site>freeform)\.com/{_URL_PATH_RE}',
        fr'https?://(?:www\.)?(?P<site>disneynow)\.com/{_URL_PATH_RE}',
        fr'https?://fxnow\.(?P<site>fxnetworks)\.com/{_URL_PATH_RE}',
        fr'https?://(?:www\.)?(?P<site>nationalgeographic)\.com/tv/{_URL_PATH_RE}',
    ]
    _TESTS = [{
        'url': 'https://abc.com/episode/4192c0e6-26e5-47a8-817b-ce8272b9e440/playlist/PL551127435',
        'info_dict': {
            'id': 'VDKA10805898',
            'ext': 'mp4',
            'title': 'Switch the Flip',
            'description': 'To help get Brian’s life in order, Stewie and Brian swap bodies using a machine that Stewie invents.',
            'age_limit': 14,
            'duration': 1297,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'series': 'Family Guy',
            'season': 'Season 16',
            'season_number': 16,
            'episode': 'Episode 17',
            'episode_number': 17,
            'timestamp': 1746082800.0,
            'upload_date': '20250501',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'This video requires AdobePass MSO credentials',
    }, {
        'url': 'https://disneynow.com/episode/21029660-ba06-4406-adb0-a9a78f6e265e/playlist/PL553044961',
        'info_dict': {
            'id': 'VDKA39546942',
            'ext': 'mp4',
            'title': 'Zero Friends Again',
            'description': 'Relationships fray under the pressures of a difficult journey.',
            'age_limit': 0,
            'duration': 1721,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'series': 'Star Wars: Skeleton Crew',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 6',
            'episode_number': 6,
            'timestamp': 1746946800.0,
            'upload_date': '20250511',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'This video requires AdobePass MSO credentials',
    }, {
        'url': 'https://fxnow.fxnetworks.com/episode/09f4fa6f-c293-469e-aebe-32c9ca5842a7/playlist/PL554408064',
        'info_dict': {
            'id': 'VDKA38112033',
            'ext': 'mp4',
            'title': 'The Return of Jerry',
            'description': 'The vampires’ long-lost fifth roommate returns. Written by Paul Simms; directed by Kyle Newacheck.',
            'age_limit': 17,
            'duration': 1493,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'series': 'What We Do in the Shadows',
            'season': 'Season 6',
            'season_number': 6,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1729573200.0,
            'upload_date': '20241022',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'This video requires AdobePass MSO credentials',
    }, {
        'url': 'https://www.freeform.com/episode/bda0eaf7-761a-4838-aa44-96f794000844/playlist/PL553044961',
        'info_dict': {
            'id': 'VDKA39007340',
            'ext': 'mp4',
            'title': 'Angel\'s Landing',
            'description': 'md5:91bf084e785c968fab16734df7313446',
            'age_limit': 14,
            'duration': 2523,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'series': 'How I Escaped My Cult',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 2',
            'episode_number': 2,
            'timestamp': 1740038400.0,
            'upload_date': '20250220',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.nationalgeographic.com/tv/episode/ca694661-1186-41ae-8089-82f64d69b16d/playlist/PL554408064',
        'info_dict': {
            'id': 'VDKA39492078',
            'ext': 'mp4',
            'title': 'Heart of the Emperors',
            'description': 'md5:4fc50a2878f030bb3a7eac9124dca677',
            'age_limit': 0,
            'duration': 2775,
            'thumbnail': r're:https?://.+/.+\.jpg',
            'series': 'Secrets of the Penguins',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1745204400.0,
            'upload_date': '20250421',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.freeform.com/movies-and-specials/c38281fc-9f8f-47c7-8220-22394f9df2e1',
        'only_matching': True,
    }, {
        'url': 'https://abc.com/video/219a454a-172c-41bf-878a-d169e6bc0bdc/playlist/PL5523098420',
        'only_matching': True,
    }]

    def _extract_videos(self, brand, video_id='-1', show_id='-1'):
        display_id = video_id if video_id != '-1' else show_id
        return self._download_json(
            f'http://api.contents.watchabc.go.com/vp2/ws/contents/3000/videos/{brand}/001/-1/{show_id}/-1/{video_id}/-1/-1.json',
            display_id)['video']

    def _extract_global_var(self, name, webpage, video_id):
        return self._search_json(
            fr'window\[["\']{re.escape(name)}["\']\]\s*=',
            webpage, f'{name.strip("_")} JSON', video_id)

    def _real_extract(self, url):
        site, display_id = self._match_valid_url(url).group('site', 'id')
        webpage = self._download_webpage(url, display_id)
        config = self._extract_global_var('__CONFIG__', webpage, display_id)
        data = self._extract_global_var(config['globalVar'], webpage, display_id)
        video_id = traverse_obj(data, (
            'page', 'content', 'video', 'layout', (('video', 'id'), 'videoid'), {str}, any))
        if not video_id:
            video_id = self._search_regex([
                # data-track-video_id="VDKA39492078"
                # data-track-video_id_code="vdka39492078"
                # data-video-id="'VDKA3609139'"
                r'data-(?:track-)?video[_-]id(?:_code)?=["\']*((?:vdka|VDKA)\d+)',
                # page.analytics.videoIdCode
                r'\bvideoIdCode["\']\s*:\s*["\']((?:vdka|VDKA)\d+)'], webpage, 'video ID')

        site_info = self._SITE_INFO[site]
        brand = site_info['brand']
        video_data = self._extract_videos(brand, video_id)[0]
        video_id = video_data['id']
        title = video_data['title']

        formats = []
        subtitles = {}
        for asset in video_data.get('assets', {}).get('asset', []):
            asset_url = asset.get('value')
            if not asset_url:
                continue
            format_id = asset.get('format')
            ext = determine_ext(asset_url)
            if ext == 'm3u8':
                video_type = video_data.get('type')
                data = {
                    'video_id': video_id,
                    'video_type': video_type,
                    'brand': brand,
                    'device': '001',
                    'app_name': 'webplayer-abc',
                }
                if video_data.get('accesslevel') == '1':
                    provider_id = site_info['provider_id']
                    software_statement = traverse_obj(data, ('app', 'config', (
                        ('features', 'auth', 'softwareStatement'),
                        ('tvAuth', 'SOFTWARE_STATEMENTS', 'PRODUCTION'),
                    ), {str}, any)) or site_info['software_statement']
                    resource = site_info.get('resource_id') or self._get_mvpd_resource(
                        provider_id, title, video_id, None)
                    auth = self._extract_mvpd_auth(
                        url, video_id, site_info['requestor_id'], resource, software_statement)
                    data.update({
                        'token': auth,
                        'token_type': 'ap',
                        'adobe_requestor_id': provider_id,
                    })
                else:
                    self._initialize_geo_bypass({'countries': ['US']})
                entitlement = self._download_json(
                    'https://prod.gatekeeper.us-abc.symphony.edgedatg.go.com/vp2/ws-secure/entitlement/2020/playmanifest_secure.json',
                    video_id, data=urlencode_postdata(data))
                errors = entitlement.get('errors', {}).get('errors', [])
                if errors:
                    for error in errors:
                        if error.get('code') == 1002:
                            self.raise_geo_restricted(
                                error['message'], countries=['US'])
                    error_message = ', '.join([error['message'] for error in errors])
                    raise ExtractorError(f'{self.IE_NAME} said: {error_message}', expected=True)
                asset_url += '?' + entitlement['entitlement']['uplynkData']['sessionKey']
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    asset_url, video_id, 'mp4', m3u8_id=format_id or 'hls', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                f = {
                    'format_id': format_id,
                    'url': asset_url,
                    'ext': ext,
                }
                if re.search(r'(?:/mp4/source/|_source\.mp4)', asset_url):
                    f.update({
                        'format_id': (f'{format_id}-' if format_id else '') + 'SOURCE',
                        'quality': 1,
                    })
                else:
                    mobj = re.search(r'/(\d+)x(\d+)/', asset_url)
                    if mobj:
                        height = int(mobj.group(2))
                        f.update({
                            'format_id': join_nonempty(format_id, f'{height}P'),
                            'width': int(mobj.group(1)),
                            'height': height,
                        })
                formats.append(f)

        for cc in video_data.get('closedcaption', {}).get('src', []):
            cc_url = cc.get('value')
            if not cc_url:
                continue
            ext = determine_ext(cc_url)
            if ext == 'xml':
                ext = 'ttml'
            subtitles.setdefault(cc.get('lang'), []).append({
                'url': cc_url,
                'ext': ext,
            })

        thumbnails = []
        for thumbnail in video_data.get('thumbnails', {}).get('thumbnail', []):
            thumbnail_url = thumbnail.get('value')
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'width': int_or_none(thumbnail.get('width')),
                'height': int_or_none(thumbnail.get('height')),
            })

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('longdescription') or video_data.get('description'),
            'duration': int_or_none(video_data.get('duration', {}).get('value'), 1000),
            'age_limit': parse_age_limit(video_data.get('tvrating', {}).get('rating')),
            'episode_number': int_or_none(video_data.get('episodenumber')),
            'series': video_data.get('show', {}).get('title'),
            'season_number': int_or_none(video_data.get('season', {}).get('num')),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            'timestamp': unified_timestamp(traverse_obj(video_data, ('airdates', 'airdate', 0))),
        }
