from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import urljoin


class NhkBaseIE(InfoExtractor):
    _API_URL_TEMPLATE = 'https://api.nhk.or.jp/nhkworld/%sod%slist/v7a/%s/%s/%s/all%s.json'
    _BASE_URL_REGEX = r'https?://www3\.nhk\.or\.jp/nhkworld/(?P<lang>[a-z]{2})/ondemand'
    _TYPE_REGEX = r'/(?P<type>video|audio)/'

    def _call_api(self, m_id, lang, is_video, is_episode, is_clip):
        return self._download_json(
            self._API_URL_TEMPLATE % (
                'v' if is_video else 'r',
                'clip' if is_clip else 'esd',
                'episode' if is_episode else 'program',
                m_id, lang, '/all' if is_video else ''),
            m_id, query={'apikey': 'EJfK8jdS57GqlupFgAfAAwr573q01y6k'})['data']['episodes'] or []

    def _extract_episode_info(self, url, episode=None):
        fetch_episode = episode is None
        lang, m_type, episode_id = NhkVodIE._match_valid_url(url).groups()
        if episode_id.isdigit():
            episode_id = episode_id[:4] + '-' + episode_id[4:]

        is_video = m_type == 'video'
        if fetch_episode:
            episode = self._call_api(
                episode_id, lang, is_video, True, episode_id[:4] == '9999')[0]
        title = episode.get('sub_title_clean') or episode['sub_title']

        def get_clean_field(key):
            return episode.get(key + '_clean') or episode.get(key)

        series = get_clean_field('title')

        thumbnails = []
        for s, w, h in [('', 640, 360), ('_l', 1280, 720)]:
            img_path = episode.get('image' + s)
            if not img_path:
                continue
            thumbnails.append({
                'id': '%dp' % h,
                'height': h,
                'width': w,
                'url': 'https://www3.nhk.or.jp' + img_path,
            })

        info = {
            'id': episode_id + '-' + lang,
            'title': '%s - %s' % (series, title) if series and title else title,
            'description': get_clean_field('description'),
            'thumbnails': thumbnails,
            'series': series,
            'episode': title,
        }
        if is_video:
            vod_id = episode['vod_id']
            info.update({
                '_type': 'url_transparent',
                'ie_key': 'Piksel',
                'url': 'https://player.piksel.com/v/refid/nhkworld/prefid/' + vod_id,
                'id': vod_id,
            })
        else:
            if fetch_episode:
                audio_path = episode['audio']['audio']
                info['formats'] = self._extract_m3u8_formats(
                    'https://nhkworld-vh.akamaihd.net/i%s/master.m3u8' % audio_path,
                    episode_id, 'm4a', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False)
                for f in info['formats']:
                    f['language'] = lang
                self._sort_formats(info['formats'])
            else:
                info.update({
                    '_type': 'url_transparent',
                    'ie_key': NhkVodIE.ie_key(),
                    'url': url,
                })
        return info


class NhkVodIE(NhkBaseIE):
    _VALID_URL = r'%s%s(?P<id>\d{7}|[^/]+?-\d{8}-[0-9a-z]+)' % (NhkBaseIE._BASE_URL_REGEX, NhkBaseIE._TYPE_REGEX)
    # Content available only for a limited period of time. Visit
    # https://www3.nhk.or.jp/nhkworld/en/ondemand/ for working samples.
    _TESTS = [{
        # video clip
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/9999011/',
        'md5': '7a90abcfe610ec22a6bfe15bd46b30ca',
        'info_dict': {
            'id': 'a95j5iza',
            'ext': 'mp4',
            'title': "Dining with the Chef - Chef Saito's Family recipe: MENCHI-KATSU",
            'description': 'md5:5aee4a9f9d81c26281862382103b0ea5',
            'timestamp': 1565965194,
            'upload_date': '20190816',
        },
    }, {
        # audio clip
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/audio/r_inventions-20201104-1/',
        'info_dict': {
            'id': 'r_inventions-20201104-1-en',
            'ext': 'm4a',
            'title': "Japan's Top Inventions - Miniature Video Cameras",
            'description': 'md5:07ea722bdbbb4936fdd360b6a480c25b',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/video/2015173/',
        'only_matching': True,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/audio/plugin-20190404-1/',
        'only_matching': True,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/fr/ondemand/audio/plugin-20190404-1/',
        'only_matching': True,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/audio/j_art-20150903-1/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._extract_episode_info(url)


class NhkVodProgramIE(NhkBaseIE):
    _VALID_URL = r'%s/program%s(?P<id>[0-9a-z]+)(?:.+?\btype=(?P<episode_type>clip|(?:radio|tv)Episode))?' % (NhkBaseIE._BASE_URL_REGEX, NhkBaseIE._TYPE_REGEX)
    _TESTS = [{
        # video program episodes
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/program/video/japanrailway',
        'info_dict': {
            'id': 'japanrailway',
            'title': 'Japan Railway Journal',
        },
        'playlist_mincount': 1,
    }, {
        # video program clips
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/program/video/japanrailway/?type=clip',
        'info_dict': {
            'id': 'japanrailway',
            'title': 'Japan Railway Journal',
        },
        'playlist_mincount': 5,
    }, {
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/program/video/10yearshayaomiyazaki/',
        'only_matching': True,
    }, {
        # audio program
        'url': 'https://www3.nhk.or.jp/nhkworld/en/ondemand/program/audio/listener/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        lang, m_type, program_id, episode_type = self._match_valid_url(url).groups()

        episodes = self._call_api(
            program_id, lang, m_type == 'video', False, episode_type == 'clip')

        entries = []
        for episode in episodes:
            episode_path = episode.get('url')
            if not episode_path:
                continue
            entries.append(self._extract_episode_info(
                urljoin(url, episode_path), episode))

        program_title = None
        if entries:
            program_title = entries[0].get('series')

        return self.playlist_result(entries, program_id, program_title)
