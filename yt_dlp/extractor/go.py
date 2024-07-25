import re

from .adobepass import AdobePassIE
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    join_nonempty,
    parse_age_limit,
    remove_end,
    remove_start,
    traverse_obj,
    try_get,
    unified_timestamp,
    urlencode_postdata,
)


class GoIE(AdobePassIE):
    _SITE_INFO = {
        'abc': {
            'brand': '001',
            'requestor_id': 'ABC',
        },
        'freeform': {
            'brand': '002',
            'requestor_id': 'ABCFamily',
        },
        'watchdisneychannel': {
            'brand': '004',
            'resource_id': 'Disney',
        },
        'watchdisneyjunior': {
            'brand': '008',
            'resource_id': 'DisneyJunior',
        },
        'watchdisneyxd': {
            'brand': '009',
            'resource_id': 'DisneyXD',
        },
        'disneynow': {
            'brand': '011',
            'resource_id': 'Disney',
        },
        'fxnow.fxnetworks': {
            'brand': '025',
            'requestor_id': 'dtci',
        },
    }
    _VALID_URL = r'''(?x)
                    https?://
                        (?P<sub_domain>
                            (?:{}\.)?go|fxnow\.fxnetworks|
                            (?:www\.)?(?:abc|freeform|disneynow)
                        )\.com/
                        (?:
                            (?:[^/]+/)*(?P<id>[Vv][Dd][Kk][Aa]\w+)|
                            (?:[^/]+/)*(?P<display_id>[^/?\#]+)
                        )
                    '''.format(r'\.|'.join(list(_SITE_INFO.keys())))
    _TESTS = [{
        'url': 'http://abc.go.com/shows/designated-survivor/video/most-recent/VDKA3807643',
        'info_dict': {
            'id': 'VDKA3807643',
            'ext': 'mp4',
            'title': 'The Traitor in the White House',
            'description': 'md5:05b009d2d145a1e85d25111bd37222e8',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'This content is no longer available.',
    }, {
        'url': 'https://disneynow.com/shows/big-hero-6-the-series',
        'info_dict': {
            'title': 'Doraemon',
            'id': 'SH55574025',
        },
        'playlist_mincount': 51,
    }, {
        'url': 'http://freeform.go.com/shows/shadowhunters/episodes/season-2/1-this-guilty-blood',
        'info_dict': {
            'id': 'VDKA3609139',
            'title': 'This Guilty Blood',
            'description': 'md5:f18e79ad1c613798d95fdabfe96cd292',
            'age_limit': 14,
            'episode': 'Episode 1',
            'upload_date': '20170102',
            'season': 'Season 2',
            'thumbnail': 'http://cdn1.edgedatg.com/aws/v2/abcf/Shadowhunters/video/201/ae5f75608d86bf88aa4f9f4aa76ab1b7/579x325-Q100_ae5f75608d86bf88aa4f9f4aa76ab1b7.jpg',
            'duration': 2544,
            'season_number': 2,
            'series': 'Shadowhunters',
            'episode_number': 1,
            'timestamp': 1483387200,
            'ext': 'mp4',
        },
        'params': {
            'geo_bypass_ip_block': '3.244.239.0/24',
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://abc.com/shows/the-rookie/episode-guide/season-04/12-the-knock',
        'info_dict': {
            'id': 'VDKA26050359',
            'title': 'The Knock',
            'description': 'md5:0c2947e3ada4c31f28296db7db14aa64',
            'age_limit': 14,
            'ext': 'mp4',
            'thumbnail': 'http://cdn1.edgedatg.com/aws/v2/abc/TheRookie/video/412/daf830d06e83b11eaf5c0a299d993ae3/1556x876-Q75_daf830d06e83b11eaf5c0a299d993ae3.jpg',
            'episode': 'Episode 12',
            'season_number': 4,
            'season': 'Season 4',
            'timestamp': 1642975200,
            'episode_number': 12,
            'upload_date': '20220123',
            'series': 'The Rookie',
            'duration': 2572,
        },
        'params': {
            'geo_bypass_ip_block': '3.244.239.0/24',
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://fxnow.fxnetworks.com/shows/better-things/video/vdka12782841',
        'info_dict': {
            'id': 'VDKA12782841',
            'title': 'First Look: Better Things - Season 2',
            'description': 'md5:fa73584a95761c605d9d54904e35b407',
            'ext': 'mp4',
            'age_limit': 14,
            'upload_date': '20170825',
            'duration': 161,
            'series': 'Better Things',
            'thumbnail': 'http://cdn1.edgedatg.com/aws/v2/fx/BetterThings/video/12782841/b6b05e58264121cc2c98811318e6d507/1556x876-Q75_b6b05e58264121cc2c98811318e6d507.jpg',
            'timestamp': 1503661074,
        },
        'params': {
            'geo_bypass_ip_block': '3.244.239.0/24',
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://abc.go.com/shows/the-catch/episode-guide/season-01/10-the-wedding',
        'only_matching': True,
    }, {
        'url': 'http://abc.go.com/shows/world-news-tonight/episode-guide/2017-02/17-021717-intense-stand-off-between-man-with-rifle-and-police-in-oakland',
        'only_matching': True,
    }, {
        # brand 004
        'url': 'http://disneynow.go.com/shows/big-hero-6-the-series/season-01/episode-10-mr-sparkles-loses-his-sparkle/vdka4637915',
        'only_matching': True,
    }, {
        # brand 008
        'url': 'http://disneynow.go.com/shows/minnies-bow-toons/video/happy-campers/vdka4872013',
        'only_matching': True,
    }, {
        'url': 'https://disneynow.com/shows/minnies-bow-toons/video/happy-campers/vdka4872013',
        'only_matching': True,
    }, {
        'url': 'https://www.freeform.com/shows/cruel-summer/episode-guide/season-01/01-happy-birthday-jeanette-turner',
        'only_matching': True,
    }]

    def _extract_videos(self, brand, video_id='-1', show_id='-1'):
        display_id = video_id if video_id != '-1' else show_id
        return self._download_json(
            f'http://api.contents.watchabc.go.com/vp2/ws/contents/3000/videos/{brand}/001/-1/{show_id}/-1/{video_id}/-1/-1.json',
            display_id)['video']

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        sub_domain = remove_start(remove_end(mobj.group('sub_domain') or '', '.go'), 'www.')
        video_id, display_id = mobj.group('id', 'display_id')
        site_info = self._SITE_INFO.get(sub_domain, {})
        brand = site_info.get('brand')
        if not video_id or not site_info:
            webpage = self._download_webpage(url, display_id or video_id)
            data = self._parse_json(
                self._search_regex(
                    r'["\']__abc_com__["\']\s*\]\s*=\s*({.+?})\s*;', webpage,
                    'data', default='{}'),
                display_id or video_id, fatal=False)
            # https://abc.com/shows/modern-family/episode-guide/season-01/101-pilot
            layout = try_get(data, lambda x: x['page']['content']['video']['layout'], dict)
            video_id = None
            if layout:
                video_id = try_get(
                    layout,
                    (lambda x: x['videoid'], lambda x: x['video']['id']),
                    str)
            if not video_id:
                video_id = self._search_regex(
                    (
                        # There may be inner quotes, e.g. data-video-id="'VDKA3609139'"
                        # from http://freeform.go.com/shows/shadowhunters/episodes/season-2/1-this-guilty-blood
                        r'data-video-id=["\']*(VDKA\w+)',
                        # page.analytics.videoIdCode
                        r'\bvideoIdCode["\']\s*:\s*["\']((?:vdka|VDKA)\w+)',
                        # https://abc.com/shows/the-rookie/episode-guide/season-02/03-the-bet
                        r'\b(?:video)?id["\']\s*:\s*["\'](VDKA\w+)',
                    ), webpage, 'video id', default=video_id)
            if not site_info:
                brand = self._search_regex(
                    (r'data-brand=\s*["\']\s*(\d+)',
                     r'data-page-brand=\s*["\']\s*(\d+)'), webpage, 'brand',
                    default='004')
                site_info = next(
                    si for _, si in self._SITE_INFO.items()
                    if si.get('brand') == brand)
            if not video_id:
                # show extraction works for Disney, DisneyJunior and DisneyXD
                # ABC and Freeform has different layout
                show_id = self._search_regex(r'data-show-id=["\']*(SH\d+)', webpage, 'show id')
                videos = self._extract_videos(brand, show_id=show_id)
                show_title = self._search_regex(r'data-show-title="([^"]+)"', webpage, 'show title', fatal=False)
                entries = []
                for video in videos:
                    entries.append(self.url_result(
                        video['url'], 'Go', video.get('id'), video.get('title')))
                entries.reverse()
                return self.playlist_result(entries, show_id, show_title)
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
                    'video_id': video_data['id'],
                    'video_type': video_type,
                    'brand': brand,
                    'device': '001',
                }
                if video_data.get('accesslevel') == '1':
                    requestor_id = site_info.get('requestor_id', 'DisneyChannels')
                    resource = site_info.get('resource_id') or self._get_mvpd_resource(
                        requestor_id, title, video_id, None)
                    auth = self._extract_mvpd_auth(
                        url, video_id, requestor_id, resource)
                    data.update({
                        'token': auth,
                        'token_type': 'ap',
                        'adobe_requestor_id': requestor_id,
                    })
                else:
                    self._initialize_geo_bypass({'countries': ['US']})
                entitlement = self._download_json(
                    'https://api.entitlement.watchabc.go.com/vp2/ws-secure/entitlement/2020/authorize.json',
                    video_id, data=urlencode_postdata(data))
                errors = entitlement.get('errors', {}).get('errors', [])
                if errors:
                    for error in errors:
                        if error.get('code') == 1002:
                            self.raise_geo_restricted(
                                error['message'], countries=['US'])
                    error_message = ', '.join([error['message'] for error in errors])
                    raise ExtractorError(f'{self.IE_NAME} said: {error_message}', expected=True)
                asset_url += '?' + entitlement['uplynkData']['sessionKey']
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
