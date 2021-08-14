# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
    unified_strdate,
)

import itertools


class VoicyBaseIE(InfoExtractor):
    # every queries are assumed to be a playlist
    def _extract_from_playlist_data(self, value):
        voice_id = compat_str(value['PlaylistId'])
        upload_date = unified_strdate(value['Published'], False)
        items = [self._extract_single_article(voice_data) for voice_data in value['VoiceData']]
        return {
            '_type': 'playlist',
            'entries': items,
            'id': voice_id,
            'title': compat_str(value['PlaylistName']),
            'uploader': value['SpeakerName'],
            'uploader_id': compat_str(value['SpeakerId']),
            'channel': value['ChannelName'],
            'channel_id': compat_str(value['ChannelId']),
            'upload_date': upload_date,
        }

    # NOTE: "article" in voicy = "track" in CDs = "chapter" in DVDs
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
        self._sort_formats(formats)
        return {
            'id': compat_str(entry['ArticleId']),
            'title': entry['ArticleTitle'],
            'description': entry['MediaName'],
            'voice_id': compat_str(entry['VoiceId']),
            'chapter_id': compat_str(entry['ChapterId']),
            'formats': formats,
        }

    def _call_api(self, url, video_id, **kwargs):
        response = self._download_json(url, video_id, **kwargs)
        if response['Status'] != 0:
            message = traverse_obj(response, ('Value', 'Error', 'Message'), expected_type=compat_str)
            if not message:
                message = 'There was a error in the response: %d' % response['Status']
            raise ExtractorError(message, expected=False)
        return response['Value']


class VoicyIE(VoicyBaseIE):
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

    # every queries are assumed to be a playlist
    def _real_extract(self, url):
        mobj = self._VALID_URL_RE.match(url)
        assert mobj
        voice_id = mobj.group('id')
        channel_id = mobj.group('channel_id')
        url, article_list = unsmuggle_url(url)
        if not article_list:
            article_list = self._call_api(self.ARTICLE_LIST_API_URL % (channel_id, voice_id), voice_id)
        return self._extract_from_playlist_data(article_list)


class VoicyChannelIE(VoicyBaseIE):
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
        return not VoicyIE.suitable(url) and super(VoicyChannelIE, cls).suitable(url)

    def _entries(self, channel_id):
        pager = ''
        for count in itertools.count(1):
            article_list = self._call_api(self.PROGRAM_LIST_API_URL % (channel_id, pager), channel_id, note='Paging #%d' % count)
            playlist_data = article_list['PlaylistData']
            if not playlist_data:
                break
            yield from playlist_data
            last = playlist_data[-1]
            pager = '&pid=%d&p_date=%s&play_count=%s' % (last['PlaylistId'], last['Published'], last['PlayCount'])

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        articles = self._entries(channel_id)

        title = traverse_obj(articles, (0, 'ChannelName'), expected_type=compat_str)
        if not title:
            spaker_name = traverse_obj(articles, (0, 'SpeakerName'), expected_type=compat_str)
            if spaker_name:
                title = 'Uploads from %s' % spaker_name
        if not title:
            title = 'Uploads from channel ID %s' % channel_id

        playlist = [
            self.url_result(smuggle_url('https://voicy.jp/channel/%s/%d' % (channel_id, value['PlaylistId']), value), VoicyIE.ie_key())
            for value in articles]
        return {
            '_type': 'playlist',
            'entries': playlist,
            'id': channel_id,
            'title': title,
            'channel': channel_id,
            'channel_id': channel_id,
        }
