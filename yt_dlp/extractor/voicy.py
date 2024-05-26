import itertools

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    smuggle_url,
    str_or_none,
    traverse_obj,
    unified_strdate,
    unsmuggle_url,
)


class VoicyBaseIE(InfoExtractor):
    def _extract_from_playlist_data(self, value):
        voice_id = compat_str(value.get('PlaylistId'))
        upload_date = unified_strdate(value.get('Published'), False)
        items = [self._extract_single_article(voice_data) for voice_data in value['VoiceData']]
        return {
            '_type': 'multi_video',
            'entries': items,
            'id': voice_id,
            'title': compat_str(value.get('PlaylistName')),
            'uploader': value.get('SpeakerName'),
            'uploader_id': str_or_none(value.get('SpeakerId')),
            'channel': value.get('ChannelName'),
            'channel_id': str_or_none(value.get('ChannelId')),
            'upload_date': upload_date,
        }

    def _extract_single_article(self, entry):
        formats = [{
            'url': entry['VoiceHlsFile'],
            'format_id': 'hls',
            'ext': 'm4a',
            'acodec': 'aac',
            'vcodec': 'none',
            'protocol': 'm3u8_native',
        }, {
            'url': entry['VoiceFile'],
            'format_id': 'mp3',
            'ext': 'mp3',
            'acodec': 'mp3',
            'vcodec': 'none',
        }]
        return {
            'id': compat_str(entry.get('ArticleId')),
            'title': entry.get('ArticleTitle'),
            'description': entry.get('MediaName'),
            'formats': formats,
        }

    def _call_api(self, url, video_id, **kwargs):
        response = self._download_json(url, video_id, **kwargs)
        if response.get('Status') != 0:
            message = traverse_obj(response, ('Value', 'Error', 'Message'), expected_type=compat_str)
            if not message:
                message = 'There was a error in the response: %d' % response.get('Status')
            raise ExtractorError(message, expected=False)
        return response.get('Value')


class VoicyIE(VoicyBaseIE):
    _WORKING = False
    IE_NAME = 'voicy'
    _VALID_URL = r'https?://voicy\.jp/channel/(?P<channel_id>\d+)/(?P<id>\d+)'
    ARTICLE_LIST_API_URL = 'https://vmw.api.voicy.jp/articles_list?channel_id=%s&pid=%s'
    _TESTS = [{
        'url': 'https://voicy.jp/channel/1253/122754',
        'info_dict': {
            'id': '122754',
            'title': '1/21(木)声日記：ついに原稿終わった！！',
            'uploader': 'ちょまど@ ITエンジニアなオタク',
            'uploader_id': '7339',
        },
        'playlist_mincount': 9,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        assert mobj
        voice_id = mobj.group('id')
        channel_id = mobj.group('channel_id')
        url, article_list = unsmuggle_url(url)
        if not article_list:
            article_list = self._call_api(self.ARTICLE_LIST_API_URL % (channel_id, voice_id), voice_id)
        return self._extract_from_playlist_data(article_list)


class VoicyChannelIE(VoicyBaseIE):
    _WORKING = False
    IE_NAME = 'voicy:channel'
    _VALID_URL = r'https?://voicy\.jp/channel/(?P<id>\d+)'
    PROGRAM_LIST_API_URL = 'https://vmw.api.voicy.jp/program_list/all?channel_id=%s&limit=20&public_type=3%s'
    _TESTS = [{
        'url': 'https://voicy.jp/channel/1253/',
        'info_dict': {
            'id': '7339',
            'title': 'ゆるふわ日常ラジオ #ちょまラジ',
            'uploader': 'ちょまど@ ITエンジニアなオタク',
            'uploader_id': '7339',
        },
        'playlist_mincount': 54,
    }]

    @classmethod
    def suitable(cls, url):
        return not VoicyIE.suitable(url) and super().suitable(url)

    def _entries(self, channel_id):
        pager = ''
        for count in itertools.count(1):
            article_list = self._call_api(self.PROGRAM_LIST_API_URL % (channel_id, pager), channel_id, note='Paging #%d' % count)
            playlist_data = article_list.get('PlaylistData')
            if not playlist_data:
                break
            yield from playlist_data
            last = playlist_data[-1]
            pager = '&pid=%d&p_date=%s&play_count=%s' % (last['PlaylistId'], last['Published'], last['PlayCount'])

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        articles = self._entries(channel_id)

        first_article = next(articles, None)
        title = traverse_obj(first_article, ('ChannelName', ), expected_type=compat_str)
        speaker_name = traverse_obj(first_article, ('SpeakerName', ), expected_type=compat_str)
        if not title and speaker_name:
            title = 'Uploads from %s' % speaker_name
        if not title:
            title = 'Uploads from channel ID %s' % channel_id

        articles = itertools.chain([first_article], articles) if first_article else articles

        playlist = (
            self.url_result(smuggle_url('https://voicy.jp/channel/%s/%d' % (channel_id, value['PlaylistId']), value), VoicyIE.ie_key())
            for value in articles)
        return {
            '_type': 'playlist',
            'entries': playlist,
            'id': channel_id,
            'title': title,
            'channel': speaker_name,
            'channel_id': channel_id,
        }
