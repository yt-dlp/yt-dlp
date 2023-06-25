import itertools
import re

from .common import InfoExtractor
from ..compat import compat_str, compat_urlparse
from ..utils import (
    determine_ext,
    find_xpath_attr,
    float_or_none,
    int_or_none,
    orderedSet,
    parse_iso8601,
    traverse_obj,
    update_url_query,
    xpath_attr,
    xpath_text,
    xpath_with_ns,
)


class LivestreamIE(InfoExtractor):
    IE_NAME = 'livestream'
    _VALID_URL = r'''(?x)
        https?://(?:new\.)?livestream\.com/
        (?:accounts/(?P<account_id>\d+)|(?P<account_name>[^/]+))
        (?:/events/(?P<event_id>\d+)|/(?P<event_name>[^/]+))?
        (?:/videos/(?P<id>\d+))?
    '''
    _EMBED_REGEX = [r'<iframe[^>]+src="(?P<url>https?://(?:new\.)?livestream\.com/[^"]+/player[^"]+)"']

    _TESTS = [{
        'url': 'http://new.livestream.com/CoheedandCambria/WebsterHall/videos/4719370',
        'md5': '7876c5f5dc3e711b6b73acce4aac1527',
        'info_dict': {
            'id': '4719370',
            'ext': 'mp4',
            'title': 'Live from Webster Hall NYC',
            'timestamp': 1350008072,
            'upload_date': '20121012',
            'duration': 5968.0,
            'like_count': int,
            'view_count': int,
            'comment_count': int,
            'thumbnail': r're:^http://.*\.jpg$'
        }
    }, {
        'url': 'https://livestream.com/coheedandcambria/websterhall',
        'info_dict': {
            'id': '1585861',
            'title': 'Live From Webster Hall'
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://livestream.com/dayananda/events/7954027',
        'info_dict': {
            'title': 'Live from Mevo',
            'id': '7954027',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'https://livestream.com/accounts/82',
        'info_dict': {
            'id': '253978',
            'view_count': int,
            'title': 'trsr',
            'comment_count': int,
            'like_count': int,
            'upload_date': '20120306',
            'timestamp': 1331042383,
            'thumbnail': 'http://img.new.livestream.com/videos/0000000000000372/cacbeed6-fb68-4b5e-ad9c-e148124e68a9_640x427.jpg',
            'duration': 15.332,
            'ext': 'mp4'
        }
    }, {
        'url': 'https://new.livestream.com/accounts/362/events/3557232/videos/67864563/player?autoPlay=false&height=360&mute=false&width=640',
        'only_matching': True,
    }, {
        'url': 'http://livestream.com/bsww/concacafbeachsoccercampeonato2015',
        'only_matching': True,
    }]
    _API_URL_TEMPLATE = 'http://livestream.com/api/accounts/%s/events/%s'

    def _parse_smil_formats(self, smil, smil_url, video_id, namespace=None, f4m_params=None, transform_rtmp_url=None):
        base_ele = find_xpath_attr(
            smil, self._xpath_ns('.//meta', namespace), 'name', 'httpBase')
        base = base_ele.get('content') if base_ele is not None else 'http://livestreamvod-f.akamaihd.net/'

        formats = []
        video_nodes = smil.findall(self._xpath_ns('.//video', namespace))

        for vn in video_nodes:
            tbr = int_or_none(vn.attrib.get('system-bitrate'), 1000)
            furl = (
                update_url_query(compat_urlparse.urljoin(base, vn.attrib['src']), {
                    'v': '3.0.3',
                    'fp': 'WIN% 14,0,0,145',
                }))
            if 'clipBegin' in vn.attrib:
                furl += '&ssek=' + vn.attrib['clipBegin']
            formats.append({
                'url': furl,
                'format_id': 'smil_%d' % tbr,
                'ext': 'flv',
                'tbr': tbr,
                'preference': -1000,  # Strictly inferior than all other formats?
            })
        return formats

    def _extract_video_info(self, video_data):
        video_id = compat_str(video_data['id'])

        FORMAT_KEYS = (
            ('sd', 'progressive_url'),
            ('hd', 'progressive_url_hd'),
        )

        formats = []
        for format_id, key in FORMAT_KEYS:
            video_url = video_data.get(key)
            if video_url:
                ext = determine_ext(video_url)
                if ext == 'm3u8':
                    continue
                bitrate = int_or_none(self._search_regex(
                    r'(\d+)\.%s' % ext, video_url, 'bitrate', default=None))
                formats.append({
                    'url': video_url,
                    'format_id': format_id,
                    'tbr': bitrate,
                    'ext': ext,
                })

        smil_url = video_data.get('smil_url')
        if smil_url:
            formats.extend(self._extract_smil_formats(smil_url, video_id, fatal=False))

        m3u8_url = video_data.get('m3u8_url')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False))

        f4m_url = video_data.get('f4m_url')
        if f4m_url:
            formats.extend(self._extract_f4m_formats(
                f4m_url, video_id, f4m_id='hds', fatal=False))

        comments = [{
            'author_id': comment.get('author_id'),
            'author': comment.get('author', {}).get('full_name'),
            'id': comment.get('id'),
            'text': comment['text'],
            'timestamp': parse_iso8601(comment.get('created_at')),
        } for comment in video_data.get('comments', {}).get('data', [])]

        return {
            'id': video_id,
            'formats': formats,
            'title': video_data['caption'],
            'description': video_data.get('description'),
            'thumbnail': video_data.get('thumbnail_url'),
            'duration': float_or_none(video_data.get('duration'), 1000),
            'timestamp': parse_iso8601(video_data.get('publish_at')),
            'like_count': video_data.get('likes', {}).get('total'),
            'comment_count': video_data.get('comments', {}).get('total'),
            'view_count': video_data.get('views'),
            'comments': comments,
        }

    def _extract_stream_info(self, stream_info):
        broadcast_id = compat_str(stream_info['broadcast_id'])
        is_live = stream_info.get('is_live')

        formats = []
        smil_url = stream_info.get('play_url')
        if smil_url:
            formats.extend(self._extract_smil_formats(smil_url, broadcast_id))

        m3u8_url = stream_info.get('m3u8_url')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, broadcast_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False))

        rtsp_url = stream_info.get('rtsp_url')
        if rtsp_url:
            formats.append({
                'url': rtsp_url,
                'format_id': 'rtsp',
            })

        return {
            'id': broadcast_id,
            'formats': formats,
            'title': stream_info['stream_title'],
            'thumbnail': stream_info.get('thumbnail_url'),
            'is_live': is_live,
        }

    def _generate_event_playlist(self, event_data):
        event_id = compat_str(event_data['id'])
        account_id = compat_str(event_data['owner_account_id'])
        feed_root_url = self._API_URL_TEMPLATE % (account_id, event_id) + '/feed.json'

        stream_info = event_data.get('stream_info')
        if stream_info:
            return self._extract_stream_info(stream_info)

        last_video = None
        for i in itertools.count(1):
            if last_video is None:
                info_url = feed_root_url
            else:
                info_url = '{root}?&id={id}&newer=-1&type=video'.format(
                    root=feed_root_url, id=last_video)
            videos_info = self._download_json(
                info_url, event_id, f'Downloading page {i}')['data']
            videos_info = [v['data'] for v in videos_info if v['type'] == 'video']
            if not videos_info:
                break
            for v in videos_info:
                v_id = compat_str(v['id'])
                yield self.url_result(
                    f'http://livestream.com/accounts/{account_id}/events/{event_id}/videos/{v_id}',
                    LivestreamIE, v_id, v.get('caption'))
            last_video = videos_info[-1]['id']

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        event = mobj.group('event_id') or mobj.group('event_name')
        account = mobj.group('account_id') or mobj.group('account_name')
        api_url = f'http://livestream.com/api/accounts/{account}'

        if video_id:
            video_data = self._download_json(
                f'{api_url}/events/{event}/videos/{video_id}', video_id)
            return self._extract_video_info(video_data)
        elif event:
            event_data = self._download_json(f'{api_url}/events/{event}', None)
            return self.playlist_result(
                self._generate_event_playlist(event_data), str(event_data['id']), event_data['full_name'])

        account_data = self._download_json(api_url, None)
        items = traverse_obj(account_data, (('upcoming_events', 'past_events'), 'data', ...))
        return self.playlist_result(
            itertools.chain.from_iterable(map(self._generate_event_playlist, items)),
            account_data.get('id'), account_data.get('full_name'))


# The original version of Livestream uses a different system
class LivestreamOriginalIE(InfoExtractor):
    IE_NAME = 'livestream:original'
    _VALID_URL = r'''(?x)https?://original\.livestream\.com/
        (?P<user>[^/\?#]+)(?:/(?P<type>video|folder)
        (?:(?:\?.*?Id=|/)(?P<id>.*?)(&|$))?)?
        '''
    _TESTS = [{
        'url': 'http://original.livestream.com/dealbook/video?clipId=pla_8aa4a3f1-ba15-46a4-893b-902210e138fb',
        'info_dict': {
            'id': 'pla_8aa4a3f1-ba15-46a4-893b-902210e138fb',
            'ext': 'mp4',
            'title': 'Spark 1 (BitCoin) with Cameron Winklevoss & Tyler Winklevoss of Winklevoss Capital',
            'duration': 771.301,
            'view_count': int,
        },
    }, {
        'url': 'https://original.livestream.com/newplay/folder?dirId=a07bf706-d0e4-4e75-a747-b021d84f2fd3',
        'info_dict': {
            'id': 'a07bf706-d0e4-4e75-a747-b021d84f2fd3',
        },
        'playlist_mincount': 4,
    }, {
        # live stream
        'url': 'http://original.livestream.com/znsbahamas',
        'only_matching': True,
    }]

    def _extract_video_info(self, user, video_id):
        api_url = 'http://x%sx.api.channel.livestream.com/2.0/clipdetails?extendedInfo=true&id=%s' % (user, video_id)
        info = self._download_xml(api_url, video_id)

        item = info.find('channel').find('item')
        title = xpath_text(item, 'title')
        media_ns = {'media': 'http://search.yahoo.com/mrss'}
        thumbnail_url = xpath_attr(
            item, xpath_with_ns('media:thumbnail', media_ns), 'url')
        duration = float_or_none(xpath_attr(
            item, xpath_with_ns('media:content', media_ns), 'duration'))
        ls_ns = {'ls': 'http://api.channel.livestream.com/2.0'}
        view_count = int_or_none(xpath_text(
            item, xpath_with_ns('ls:viewsCount', ls_ns)))

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail_url,
            'duration': duration,
            'view_count': view_count,
        }

    def _extract_video_formats(self, video_data, video_id):
        formats = []

        progressive_url = video_data.get('progressiveUrl')
        if progressive_url:
            formats.append({
                'url': progressive_url,
                'format_id': 'http',
            })

        m3u8_url = video_data.get('httpUrl')
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False))

        rtsp_url = video_data.get('rtspUrl')
        if rtsp_url:
            formats.append({
                'url': rtsp_url,
                'format_id': 'rtsp',
            })

        return formats

    def _extract_folder(self, url, folder_id):
        webpage = self._download_webpage(url, folder_id)
        paths = orderedSet(re.findall(
            r'''(?x)(?:
                <li\s+class="folder">\s*<a\s+href="|
                <a\s+href="(?=https?://livestre\.am/)
            )([^"]+)"''', webpage))

        entries = [{
            '_type': 'url',
            'url': compat_urlparse.urljoin(url, p),
        } for p in paths]

        return self.playlist_result(entries, folder_id)

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        user = mobj.group('user')
        url_type = mobj.group('type')
        content_id = mobj.group('id')
        if url_type == 'folder':
            return self._extract_folder(url, content_id)
        else:
            # this url is used on mobile devices
            stream_url = 'http://x%sx.api.channel.livestream.com/3.0/getstream.json' % user
            info = {}
            if content_id:
                stream_url += '?id=%s' % content_id
                info = self._extract_video_info(user, content_id)
            else:
                content_id = user
                webpage = self._download_webpage(url, content_id)
                info = {
                    'title': self._og_search_title(webpage),
                    'description': self._og_search_description(webpage),
                    'thumbnail': self._search_regex(r'channelLogo\.src\s*=\s*"([^"]+)"', webpage, 'thumbnail', None),
                }
            video_data = self._download_json(stream_url, content_id)
            is_live = video_data.get('isLive')
            info.update({
                'id': content_id,
                'title': info['title'],
                'formats': self._extract_video_formats(video_data, content_id),
                'is_live': is_live,
            })
            return info


# The server doesn't support HEAD request, the generic extractor can't detect
# the redirection
class LivestreamShortenerIE(InfoExtractor):
    IE_NAME = 'livestream:shortener'
    IE_DESC = False  # Do not list
    _VALID_URL = r'https?://livestre\.am/(?P<id>.+)'

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        id = mobj.group('id')
        webpage = self._download_webpage(url, id)

        return self.url_result(self._og_search_url(webpage))
