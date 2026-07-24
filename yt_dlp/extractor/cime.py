from .common import InfoExtractor


class CiMeBaseIE(InfoExtractor):
    def _extract_rune_data(self, url, video_id):
        webpage = self._download_webpage(url, video_id)

        json_string = self._search_regex(
            r"window\.__RUNE_DATA__.*?JSON\.parse\('(\{[\s\S]+?\})'\)",
            webpage,
            'rune data',
        )

        json_string = json_string.replace('\\\\', '\\').replace("\\'", "'")

        return self._parse_json(json_string, video_id)


class CiMeLiveIE(CiMeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?ci\.me/@(?P<id>[^/]+)/live'
    _TESTS = [
        {
            'url': 'https://ci.me/@yeoniizz/live',
            'info_dict': {
                'id': '1004851',
                'ext': 'mp4',
                'title': '[2일차] 새벽 먹는 커비 등쟝',
                'uploader': 'Yeoniizz',
                'live_status': 'is_live'},
            'skip': 'The channel is not currently live'}]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        rune_data = self._extract_rune_data(url, video_id)

        args = rune_data.get('args', {})
        first_arg = args[0]
        body_data = first_arg.get('bodyData', {})

        live_data = body_data.get('live', {})
        channel_data = live_data.get('channel', {})
        playback_data = live_data.get('playback', {})

        uploader = channel_data.get('name', {}) or channel_data.get('slug', {})
        title = live_data.get('title') or channel_data.get('description') or f'{uploader or video_id} Live Stream'
        is_live = channel_data.get('isLive')

        m3u8_url = live_data.get('playbackUrl') or playback_data.get('url')
        if not m3u8_url:
            raise self.raise_login_required('Stream is offline or playback URL is missing')

        formats = self._extract_m3u8_formats(
            m3u8_url,
            video_id,
            ext='mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls',
            live=is_live,
        )

        return {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'is_live': is_live,
            'formats': formats,
        }


class CiMeVodIE(CiMeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?ci\.me/@(?P<uploader>[^/]+)/vods/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://ci.me/@ninosunday/vods/14364',
            'info_dict': {
                'id': '14364',
                'ext': 'mp4',
                'title': '니노와 옛날이야기',
                'uploader': '니노 선데이'},
            'params': {
                'skip_download': True}},
        {
            'url': 'https://ci.me/@irocloud/vods/14036',
            'info_dict': {
                'id': '14036',
                'ext': 'mp4',
                'title': '둥실둥실 잡담💭',
                'uploader': '이로 클라우드'},
            'params': {
                'skip_download': True}}]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        rune_data = self._extract_rune_data(url, video_id)

        args = rune_data.get('args', {})
        first_arg = args[0]
        body_data = first_arg.get('bodyData', {})

        vod_data = body_data.get('vod', {})
        channel_data = vod_data.get('channel', {})
        playback_data = vod_data.get('playback', {})

        uploader = channel_data.get('name', {}) or channel_data.get('slug', {})
        title = vod_data.get('title') or channel_data.get('description') or f'{video_id} VOD'

        m3u8_url = vod_data.get('playbackUrl') or playback_data.get('url')
        if not m3u8_url:
            raise self.raise_login_required('Playback URL is missing or deleted')

        formats = self._extract_m3u8_formats(
            m3u8_url,
            video_id,
            ext='mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls',
        )

        return {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'formats': formats,
        }


class CiMeClipIE(CiMeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?ci\.me/clips/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [
        {
            'url': 'https://ci.me/clips/1800',
            'md5': 'd7fdf93e05f1f15a4ffe12527416a87a',
            'info_dict': {
                'id': '1800',
                'ext': 'mp4',
                'title': '[토토씨 참가곡] 가지마',
                'uploader': '로보 프로스터'}},
        {
            'url': 'https://ci.me/clips/3059',
            'md5': 'e9de7e5d2a6cdb12f34420cac378be52',
            'info_dict': {
                'id': '3059',
                'ext': 'mp4',
                'title': '오토 러브송',
                'uploader': '오토 레이니'}}]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        rune_data = self._extract_rune_data(url, video_id)

        args = rune_data.get('args', {})
        first_arg = args[0]
        body_data = first_arg.get('bodyData', {})

        clips_data = body_data.get('clips', {})
        req_clip = clips_data[0]
        channel_data = req_clip.get('channel', {})
        playback_data = req_clip.get('playback', {})

        uploader = channel_data.get('name', {}) or channel_data.get('slug', {})
        title = req_clip.get('title') or f'Clip {video_id}'

        clip_url = playback_data.get('url')
        if not clip_url:
            raise self.raise_login_required('Clip URL is missing or deleted')

        return {
            'id': video_id,
            'title': title,
            'uploader': uploader,
            'url': clip_url,
            'ext': 'mp4',
        }
