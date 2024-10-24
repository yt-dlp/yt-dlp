import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    extract_attributes,
    get_element_by_class,
    get_element_text_and_html_by_tag,
    parse_duration,
    traverse_obj,
    try_call,
    url_or_none,
)


class NekoHackerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nekohacker\.com/(?P<id>(?!free-dl)[\w-]+)'
    _TESTS = [{
        'url': 'https://nekohacker.com/nekoverse/',
        'info_dict': {
            'id': 'nekoverse',
            'title': 'Nekoverse',
        },
        'playlist': [
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2022/11/01-Spaceship.mp3',
                'md5': '44223701ebedba0467ebda4cc07fb3aa',
                'info_dict': {
                    'id': '1712',
                    'ext': 'mp3',
                    'title': 'Spaceship',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2022/11/Nekoverse_Artwork-1024x1024.jpg',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'release_date': '20221101',
                    'album': 'Nekoverse',
                    'artist': 'Neko Hacker',
                    'track': 'Spaceship',
                    'track_number': 1,
                    'duration': 195.0,
                },
            },
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2022/11/02-City-Runner.mp3',
                'md5': '8f853c71719389d32bbbd3f1a87b3f08',
                'info_dict': {
                    'id': '1713',
                    'ext': 'mp3',
                    'title': 'City Runner',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2022/11/Nekoverse_Artwork-1024x1024.jpg',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'release_date': '20221101',
                    'album': 'Nekoverse',
                    'artist': 'Neko Hacker',
                    'track': 'City Runner',
                    'track_number': 2,
                    'duration': 148.0,
                },
            },
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2022/11/03-Nature-Talk.mp3',
                'md5': '5a8a8ae852720cee4c0ac95c7d1a7450',
                'info_dict': {
                    'id': '1714',
                    'ext': 'mp3',
                    'title': 'Nature Talk',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2022/11/Nekoverse_Artwork-1024x1024.jpg',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'release_date': '20221101',
                    'album': 'Nekoverse',
                    'artist': 'Neko Hacker',
                    'track': 'Nature Talk',
                    'track_number': 3,
                    'duration': 174.0,
                },
            },
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2022/11/04-Crystal-World.mp3',
                'md5': 'd8e59a48061764e50d92386a294abd50',
                'info_dict': {
                    'id': '1715',
                    'ext': 'mp3',
                    'title': 'Crystal World',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2022/11/Nekoverse_Artwork-1024x1024.jpg',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'release_date': '20221101',
                    'album': 'Nekoverse',
                    'artist': 'Neko Hacker',
                    'track': 'Crystal World',
                    'track_number': 4,
                    'duration': 199.0,
                },
            },
        ],
    }, {
        'url': 'https://nekohacker.com/susume/',
        'info_dict': {
            'id': 'susume',
            'title': '進め！むじなカンパニー',
        },
        'playlist': [
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2021/01/進め！むじなカンパニー-feat.-六科なじむ-CV_-日高里菜-割戶真友-CV_-金元寿子-軽井沢ユキ-CV_-上坂すみれ-出稼ぎガルシア-CV_-金子彩花-.mp3',
                'md5': 'fb13f008aa81f26ba48f91fd2d6186ce',
                'info_dict': {
                    'id': '711',
                    'ext': 'mp3',
                    'title': 'md5:1a5fcbc96ca3c3265b1c6f9f79f30fd0',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2021/01/OP表-1024x1024.png',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'release_date': '20210115',
                    'album': '進め！むじなカンパニー',
                    'artist': 'Neko Hacker',
                    'track': 'md5:1a5fcbc96ca3c3265b1c6f9f79f30fd0',
                    'track_number': 1,
                },
            },
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2021/01/むじな-de-なじむ-feat.-六科なじむ-CV_-日高里菜-.mp3',
                'md5': '028803f70241df512b7764e73396fdd1',
                'info_dict': {
                    'id': '709',
                    'ext': 'mp3',
                    'title': 'むじな de なじむ feat. 六科なじむ (CV: 日高里菜 )',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2021/01/OP表-1024x1024.png',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'release_date': '20210115',
                    'album': '進め！むじなカンパニー',
                    'artist': 'Neko Hacker',
                    'track': 'むじな de なじむ feat. 六科なじむ (CV: 日高里菜 )',
                    'track_number': 2,
                },
            },
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2021/01/進め！むじなカンパニー-instrumental.mp3',
                'md5': 'adde9e9a16e1da5e602b579c247d0fb9',
                'info_dict': {
                    'id': '710',
                    'ext': 'mp3',
                    'title': '進め！むじなカンパニー (instrumental)',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2021/01/OP表-1024x1024.png',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'release_date': '20210115',
                    'album': '進め！むじなカンパニー',
                    'artist': 'Neko Hacker',
                    'track': '進め！むじなカンパニー (instrumental)',
                    'track_number': 3,
                },
            },
            {
                'url': 'https://nekohacker.com/wp-content/uploads/2021/01/むじな-de-なじむ-instrumental.mp3',
                'md5': 'ebb0443039cf5f9ff7fd557ed9b23599',
                'info_dict': {
                    'id': '712',
                    'ext': 'mp3',
                    'title': 'むじな de なじむ (instrumental)',
                    'thumbnail': 'https://nekohacker.com/wp-content/uploads/2021/01/OP表-1024x1024.png',
                    'vcodec': 'none',
                    'acodec': 'mp3',
                    'release_date': '20210115',
                    'album': '進め！むじなカンパニー',
                    'artist': 'Neko Hacker',
                    'track': 'むじな de なじむ (instrumental)',
                    'track_number': 4,
                },
            },
        ],
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)
        playlist = get_element_by_class('playlist', webpage)

        if not playlist:
            iframe = try_call(lambda: get_element_text_and_html_by_tag('iframe', webpage)[1]) or ''
            iframe_src = url_or_none(extract_attributes(iframe).get('src'))
            if not iframe_src:
                raise ExtractorError('No playlist or embed found in webpage')
            elif re.match(r'https?://(?:\w+\.)?spotify\.com/', iframe_src):
                raise ExtractorError('Spotify embeds are not supported', expected=True)
            return self.url_result(url, 'Generic')

        entries = []
        for track_number, track in enumerate(re.findall(r'(<li[^>]+data-audiopath[^>]+>)', playlist), 1):
            entry = traverse_obj(extract_attributes(track), {
                'url': ('data-audiopath', {url_or_none}),
                'ext': ('data-audiopath', {determine_ext}),
                'id': 'data-trackid',
                'title': 'data-tracktitle',
                'track': 'data-tracktitle',
                'album': 'data-albumtitle',
                'duration': ('data-tracktime', {parse_duration}),
                'release_date': ('data-releasedate', {lambda x: re.match(r'\d{8}', x.replace('.', ''))}, 0),
                'thumbnail': ('data-albumart', {url_or_none}),
            })
            entries.append({
                **entry,
                'track_number': track_number,
                'artist': 'Neko Hacker',
                'vcodec': 'none',
                'acodec': 'mp3' if entry['ext'] == 'mp3' else None,
            })

        return self.playlist_result(entries, playlist_id, traverse_obj(entries, (0, 'album')))
