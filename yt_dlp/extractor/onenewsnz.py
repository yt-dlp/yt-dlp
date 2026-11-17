from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class OneNewsNZIE(InfoExtractor):
    IE_NAME = '1News'
    IE_DESC = '1news.co.nz article videos'
    _VALID_URL = r'https?://(?:www\.)?(?:1|one)news\.co\.nz/\d+/\d+/\d+/(?P<id>[^/?#&]+)'
    _TESTS = [
        {   # Brightcove video
            'url': 'https://www.1news.co.nz/2022/09/29/cows-painted-green-on-parliament-lawn-in-climate-protest/',
            'info_dict': {
                'id': 'cows-painted-green-on-parliament-lawn-in-climate-protest',
                'title': '\'Cows\' painted green on Parliament lawn in climate protest',
            },
            'playlist': [{
                'info_dict': {
                    'id': '6312993358112',
                    'title': 'Activists dressed as cows painted green outside Parliament in climate protest',
                    'ext': 'mp4',
                    'tags': 'count:6',
                    'uploader_id': '963482464001',
                    'timestamp': 1664416255,
                    'upload_date': '20220929',
                    'duration': 38.272,
                    'thumbnail': r're:^https?://.*\.jpg$',
                    'description': 'Greenpeace accused the Government of "greenwashing" instead of taking climate action.',
                },
            }],
        }, {
            # YouTube video
            'url': 'https://www.1news.co.nz/2022/09/30/now-is-the-time-to-care-about-womens-rugby/',
            'info_dict': {
                'id': 'now-is-the-time-to-care-about-womens-rugby',
                'title': 'Now is the time to care about women\'s rugby',
            },
            'playlist': [{
                'info_dict': {
                    'id': 's4wEB9neTfU',
                    'title': 'Why I love women’s rugby: Black Fern Ruahei Demant',
                    'ext': 'mp4',
                    'channel_follower_count': int,
                    'channel_url': 'https://www.youtube.com/channel/UC2BQ3U9IxoYIJyulv0bN5PQ',
                    'tags': 'count:12',
                    'uploader': 'Re: News',
                    'upload_date': '20211215',
                    'uploader_id': 'UC2BQ3U9IxoYIJyulv0bN5PQ',
                    'uploader_url': 'http://www.youtube.com/channel/UC2BQ3U9IxoYIJyulv0bN5PQ',
                    'channel_id': 'UC2BQ3U9IxoYIJyulv0bN5PQ',
                    'channel': 'Re: News',
                    'like_count': int,
                    'thumbnail': 'https://i.ytimg.com/vi/s4wEB9neTfU/maxresdefault.jpg',
                    'age_limit': 0,
                    'view_count': int,
                    'categories': ['Sports'],
                    'duration': 222,
                    'description': 'md5:8874410e5740ed1d8fd0df839f849813',
                    'availability': 'public',
                    'playable_in_embed': True,
                    'live_status': 'not_live',
                },
            }],
        }, {
            # 2 Brightcove videos
            'url': 'https://www.1news.co.nz/2022/09/29/raw-videos-capture-hurricane-ians-fury-as-it-slams-florida/',
            'info_dict': {
                'id': 'raw-videos-capture-hurricane-ians-fury-as-it-slams-florida',
                'title': 'Raw videos capture Hurricane Ian\'s fury as it slams Florida',
            },
            'playlist_mincount': 2,
        }, {
            'url': 'https://www.onenews.co.nz/2022/09/29/cows-painted-green-on-parliament-lawn-in-climate-protest/',
            'only_matching': True,
        }]

    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/0xpHIR6IB_default/index.html?videoId=%s'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        fusion_metadata = self._search_json(r'Fusion\.globalContent\s*=', webpage, 'fusion metadata', display_id)

        entries = []
        for item in traverse_obj(fusion_metadata, 'content_elements') or []:
            item_type = traverse_obj(item, 'subtype')
            if item_type == 'video':
                brightcove_config = traverse_obj(item, ('embed', 'config'))
                brightcove_url = self.BRIGHTCOVE_URL_TEMPLATE % (
                    traverse_obj(brightcove_config, 'brightcoveAccount') or '963482464001',
                    traverse_obj(brightcove_config, 'brightcoveVideoId'),
                )
                entries.append(self.url_result(brightcove_url, BrightcoveNewIE))
            elif item_type == 'youtube':
                video_id_or_url = traverse_obj(item, ('referent', 'id'), ('raw_oembed', '_id'))
                if video_id_or_url:
                    entries.append(self.url_result(video_id_or_url, ie='Youtube'))

        if not entries:
            raise ExtractorError('This article does not have a video.', expected=True)

        playlist_title = (
            traverse_obj(fusion_metadata, ('headlines', 'basic'))
            or self._generic_title('', webpage)
        )
        return self.playlist_result(entries, display_id, playlist_title)
