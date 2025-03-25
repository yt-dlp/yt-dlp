from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    int_or_none,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class MSNIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|preview)\.)?msn\.com/(?P<locale>[a-z]{2}-[a-z]{2})/(?:[^/?#]+/)+(?P<display_id>[^/?#]+)/[a-z]{2}-(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        'url': 'https://www.msn.com/en-gb/video/news/president-macron-interrupts-trump-over-ukraine-funding/vi-AA1zMcD7',
        'info_dict': {
            'id': 'AA1zMcD7',
            'ext': 'mp4',
            'display_id': 'president-macron-interrupts-trump-over-ukraine-funding',
            'title': 'President Macron interrupts Trump over Ukraine funding',
            'description': 'md5:5fd3857ac25849e7a56cb25fbe1a2a8b',
            'uploader': 'k! News UK',
            'uploader_id': 'BB1hz5Rj',
            'duration': 59,
            'thumbnail': 'https://img-s-msn-com.akamaized.net/tenant/amp/entityid/AA1zMagX.img',
            'tags': 'count:14',
            'timestamp': 1740510914,
            'upload_date': '20250225',
            'release_timestamp': 1740513600,
            'release_date': '20250225',
            'modified_timestamp': 1741413241,
            'modified_date': '20250308',
        },
    }, {
        'url': 'https://www.msn.com/en-gb/video/watch/films-success-saved-adam-pearsons-acting-career/vi-AA1znZGE?ocid=hpmsn',
        'info_dict': {
            'id': 'AA1znZGE',
            'ext': 'mp4',
            'display_id': 'films-success-saved-adam-pearsons-acting-career',
            'title': "Films' success saved Adam Pearson's acting career",
            'description': 'md5:98c05f7bd9ab4f9c423400f62f2d3da5',
            'uploader': 'Sky News',
            'uploader_id': 'AA2eki',
            'duration': 52,
            'thumbnail': 'https://img-s-msn-com.akamaized.net/tenant/amp/entityid/AA1zo7nU.img',
            'timestamp': 1739993965,
            'upload_date': '20250219',
            'release_timestamp': 1739977753,
            'release_date': '20250219',
            'modified_timestamp': 1742076259,
            'modified_date': '20250315',
        },
    }, {
        'url': 'https://www.msn.com/en-us/entertainment/news/rock-frontman-replacements-you-might-not-know-happened/vi-AA1yLVcD',
        'info_dict': {
            'id': 'AA1yLVcD',
            'ext': 'mp4',
            'display_id': 'rock-frontman-replacements-you-might-not-know-happened',
            'title': 'Rock Frontman Replacements You Might Not Know Happened',
            'description': 'md5:451a125496ff0c9f6816055bb1808da9',
            'uploader': 'Grunge (Video)',
            'uploader_id': 'BB1oveoV',
            'duration': 596,
            'thumbnail': 'https://img-s-msn-com.akamaized.net/tenant/amp/entityid/AA1yM4OJ.img',
            'timestamp': 1739223456,
            'upload_date': '20250210',
            'release_timestamp': 1739219731,
            'release_date': '20250210',
            'modified_timestamp': 1741427272,
            'modified_date': '20250308',
        },
    }, {
        # Dailymotion Embed
        'url': 'https://www.msn.com/de-de/nachrichten/other/the-first-descendant-gameplay-trailer-zu-serena-der-neuen-gefl%C3%BCgelten-nachfahrin/vi-AA1B1d06',
        'info_dict': {
            'id': 'x9g6oli',
            'ext': 'mp4',
            'title': 'The First Descendant: Gameplay-Trailer zu Serena, der neuen geflügelten Nachfahrin',
            'description': '',
            'uploader': 'MeinMMO',
            'uploader_id': 'x2mvqi4',
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'duration': 60,
            'thumbnail': 'https://s1.dmcdn.net/v/Y3fO61drj56vPB9SS/x1080',
            'tags': ['MeinMMO', 'The First Descendant'],
            'timestamp': 1742124877,
            'upload_date': '20250316',
        },
    }, {
        # Youtube Embed
        'url': 'https://www.msn.com/en-gb/video/webcontent/web-content/vi-AA1ybFaJ',
        'info_dict': {
            'id': 'kQSChWu95nE',
            'ext': 'mp4',
            'title': '7 Daily Habits to Nurture Your Personal Growth',
            'description': 'md5:6f233c68341b74dee30c8c121924e827',
            'uploader': 'TopThink',
            'uploader_id': '@TopThink',
            'uploader_url': 'https://www.youtube.com/@TopThink',
            'channel': 'TopThink',
            'channel_id': 'UCMlGmHokrQRp-RaNO7aq4Uw',
            'channel_url': 'https://www.youtube.com/channel/UCMlGmHokrQRp-RaNO7aq4Uw',
            'channel_is_verified': True,
            'channel_follower_count': int,
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'age_limit': 0,
            'duration': 705,
            'thumbnail': 'https://i.ytimg.com/vi/kQSChWu95nE/maxresdefault.jpg',
            'categories': ['Howto & Style'],
            'tags': ['topthink', 'top think', 'personal growth'],
            'timestamp': 1722711620,
            'upload_date': '20240803',
            'playable_in_embed': True,
            'availability': 'public',
            'live_status': 'not_live',
        },
    }, {
        # Article with social embed
        'url': 'https://www.msn.com/en-in/news/techandscience/watch-earth-sets-and-rises-behind-moon-in-breathtaking-blue-ghost-video/ar-AA1zKoAc',
        'info_dict': {
            'id': 'AA1zKoAc',
            'title': 'Watch: Earth sets and rises behind Moon in breathtaking Blue Ghost video',
            'description': 'md5:0ad51cfa77e42e7f0c46cf98a619dbbf',
            'uploader': 'India Today',
            'uploader_id': 'AAyFWG',
            'tags': 'count:11',
            'timestamp': 1740485034,
            'upload_date': '20250225',
            'release_timestamp': 1740484875,
            'release_date': '20250225',
            'modified_timestamp': 1740488561,
            'modified_date': '20250225',
        },
        'playlist_count': 1,
    }]

    def _real_extract(self, url):
        locale, display_id, page_id = self._match_valid_url(url).group('locale', 'display_id', 'id')

        json_data = self._download_json(
            f'https://assets.msn.com/content/view/v2/Detail/{locale}/{page_id}', page_id)

        common_metadata = traverse_obj(json_data, {
            'title': ('title', {str}),
            'description': (('abstract', ('body', {clean_html})), {str}, filter, any),
            'timestamp': ('createdDateTime', {parse_iso8601}),
            'release_timestamp': ('publishedDateTime', {parse_iso8601}),
            'modified_timestamp': ('updatedDateTime', {parse_iso8601}),
            'thumbnail': ('thumbnail', 'image', 'url', {url_or_none}),
            'duration': ('videoMetadata', 'playTime', {int_or_none}),
            'tags': ('keywords', ..., {str}),
            'uploader': ('provider', 'name', {str}),
            'uploader_id': ('provider', 'id', {str}),
        })

        page_type = json_data['type']
        source_url = traverse_obj(json_data, ('sourceHref', {url_or_none}))
        if page_type == 'video':
            if traverse_obj(json_data, ('thirdPartyVideoPlayer', 'enabled')) and source_url:
                return self.url_result(source_url)
            formats = []
            subtitles = {}
            for file in traverse_obj(json_data, ('videoMetadata', 'externalVideoFiles', lambda _, v: url_or_none(v['url']))):
                file_url = file['url']
                ext = determine_ext(file_url)
                if ext == 'm3u8':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        file_url, page_id, 'mp4', m3u8_id='hls', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                elif ext == 'mpd':
                    fmts, subs = self._extract_mpd_formats_and_subtitles(
                        file_url, page_id, mpd_id='dash', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                else:
                    formats.append(
                        traverse_obj(file, {
                            'url': 'url',
                            'format_id': ('format', {str}),
                            'filesize': ('fileSize', {int_or_none}),
                            'height': ('height', {int_or_none}),
                            'width': ('width', {int_or_none}),
                        }))
            for caption in traverse_obj(json_data, ('videoMetadata', 'closedCaptions', lambda _, v: url_or_none(v['href']))):
                lang = caption.get('locale') or 'en-us'
                subtitles.setdefault(lang, []).append({
                    'url': caption['href'],
                    'ext': 'ttml',
                })

            return {
                'id': page_id,
                'display_id': display_id,
                'formats': formats,
                'subtitles': subtitles,
                **common_metadata,
            }
        elif page_type == 'webcontent':
            if not source_url:
                raise ExtractorError('Could not find source URL')
            return self.url_result(source_url)
        elif page_type == 'article':
            entries = []
            for embed_url in traverse_obj(json_data, ('socialEmbeds', ..., 'postUrl', {url_or_none})):
                entries.append(self.url_result(embed_url))

            return self.playlist_result(entries, page_id, **common_metadata)

        raise ExtractorError(f'Unsupported page type: {page_type}')
