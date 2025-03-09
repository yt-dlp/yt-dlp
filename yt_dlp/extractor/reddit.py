import json
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    parse_qs,
    traverse_obj,
    truncate_string,
    try_get,
    unescapeHTML,
    update_url_query,
    url_or_none,
    urlencode_postdata,
)


class RedditIE(InfoExtractor):
    _NETRC_MACHINE = 'reddit'
    _VALID_URL = r'https?://(?:\w+\.)?reddit(?:media)?\.com/(?P<slug>(?:(?:r|user)/[^/]+/)?comments/(?P<id>[^/?#&]+))'
    _TESTS = [{
        'url': 'https://www.reddit.com/r/videos/comments/6rrwyj/that_small_heart_attack/',
        'info_dict': {
            'id': 'zv89llsvexdz',
            'ext': 'mp4',
            'display_id': '6rrwyj',
            'title': 'That small heart attack.',
            'alt_title': 'That small heart attack.',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:4',
            'timestamp': 1501941939,
            'upload_date': '20170805',
            'uploader': 'Antw87',
            'duration': 12,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'age_limit': 0,
            'channel_id': 'videos',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # 1080p fallback format
        'url': 'https://www.reddit.com/r/aww/comments/90bu6w/heat_index_was_110_degrees_so_we_offered_him_a/',
        'md5': '8b5902cfda3006bf90faea7adf765a49',
        'info_dict': {
            'id': 'gyh95hiqc0b11',
            'ext': 'mp4',
            'display_id': '90bu6w',
            'title': 'Heat index was 110 degrees so we offered him a cold drink. He went fo...',
            'alt_title': 'Heat index was 110 degrees so we offered him a cold drink. He went for a full body soak instead',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:7',
            'timestamp': 1532051078,
            'upload_date': '20180720',
            'uploader': 'FootLoosePickleJuice',
            'duration': 14,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'age_limit': 0,
            'channel_id': 'aww',
        },
    }, {
        # User post
        'url': 'https://www.reddit.com/user/creepyt0es/comments/nip71r/i_plan_to_make_more_stickers_and_prints_check/',
        'info_dict': {
            'id': 'zasobba6wp071',
            'ext': 'mp4',
            'display_id': 'nip71r',
            'title': 'I plan to make more stickers and prints! Check them out on my Etsy! O...',
            'alt_title': 'I plan to make more stickers and prints! Check them out on my Etsy! Or get them through my Patreon. Links below.',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'thumbnails': 'count:5',
            'timestamp': 1621709093,
            'upload_date': '20210522',
            'uploader': 'creepyt0es',
            'duration': 6,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'age_limit': 18,
            'channel_id': 'u_creepyt0es',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # videos embedded in reddit text post
        'url': 'https://www.reddit.com/r/KamenRider/comments/wzqkxp/finale_kamen_rider_revice_episode_50_family_to/',
        'playlist_count': 2,
        'info_dict': {
            'id': 'wzqkxp',
            'title': '[Finale] Kamen Rider Revice Episode 50 "Family to the End, Until the ...',
            'alt_title': '[Finale] Kamen Rider Revice Episode 50 "Family to the End, Until the Day We Meet Again" Discussion',
            'description': 'md5:5b7deb328062b164b15704c5fd67c335',
            'uploader': 'TheTwelveYearOld',
            'channel_id': 'KamenRider',
            'comment_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 0,
            'timestamp': 1661676059.0,
            'upload_date': '20220828',
        },
    }, {
        # crossposted reddit-hosted media
        'url': 'https://www.reddit.com/r/dumbfuckers_club/comments/zjjw82/cringe/',
        'md5': '746180895c7b75a9d6b05341f507699a',
        'info_dict': {
            'id': 'a1oneun6pa5a1',
            'ext': 'mp4',
            'display_id': 'zjjw82',
            'title': 'Cringe',
            'alt_title': 'Cringe',
            'uploader': 'Otaku-senpai69420',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'upload_date': '20221212',
            'timestamp': 1670812309,
            'duration': 16,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'age_limit': 0,
            'channel_id': 'dumbfuckers_club',
        },
    }, {
        # post link without subreddit
        'url': 'https://www.reddit.com/comments/124pp33',
        'md5': '15eec9d828adcef4468b741a7e45a395',
        'info_dict': {
            'id': 'antsenjc2jqa1',
            'ext': 'mp4',
            'display_id': '124pp33',
            'title': 'Harmless prank of some old friends',
            'alt_title': 'Harmless prank of some old friends',
            'uploader': 'Dudezila',
            'channel_id': 'ContagiousLaughter',
            'duration': 17,
            'upload_date': '20230328',
            'timestamp': 1680012043,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'age_limit': 0,
            'comment_count': int,
            'dislike_count': int,
            'like_count': int,
        },
    }, {
        # quarantined subreddit post
        'url': 'https://old.reddit.com/r/GenZedong/comments/12fujy3/based_hasan/',
        'md5': '3156ea69e3c1f1b6259683c5abd36e71',
        'info_dict': {
            'id': '8bwtclfggpsa1',
            'ext': 'mp4',
            'display_id': '12fujy3',
            'title': 'Based Hasan?',
            'alt_title': 'Based Hasan?',
            'uploader': 'KingNigelXLII',
            'channel_id': 'GenZedong',
            'duration': 16,
            'upload_date': '20230408',
            'timestamp': 1680979138,
            'age_limit': 0,
            'comment_count': int,
            'dislike_count': int,
            'like_count': int,
        },
        'skip': 'Requires account that has opted-in to the GenZedong subreddit',
    }, {
        # subtitles in HLS manifest
        'url': 'https://www.reddit.com/r/Unexpected/comments/1cl9h0u/the_insurance_claim_will_be_interesting/',
        'info_dict': {
            'id': 'a2mdj5d57qyc1',
            'ext': 'mp4',
            'display_id': '1cl9h0u',
            'title': 'The insurance claim will be interesting',
            'alt_title': 'The insurance claim will be interesting',
            'uploader': 'darrenpauli',
            'channel_id': 'Unexpected',
            'duration': 53,
            'upload_date': '20240506',
            'timestamp': 1714966382,
            'age_limit': 0,
            'comment_count': int,
            'dislike_count': int,
            'like_count': int,
            'subtitles': {'en': 'mincount:1'},
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # subtitles from caption-url
        'url': 'https://www.reddit.com/r/soccer/comments/1cxwzso/tottenham_1_0_newcastle_united_james_maddison_31/',
        'info_dict': {
            'id': 'xbmj4t3igy1d1',
            'ext': 'mp4',
            'display_id': '1cxwzso',
            'title': 'Tottenham [1] - 0 Newcastle United - James Maddison 31\'',
            'alt_title': 'Tottenham [1] - 0 Newcastle United - James Maddison 31\'',
            'uploader': 'Woodstovia',
            'channel_id': 'soccer',
            'duration': 30,
            'upload_date': '20240522',
            'timestamp': 1716373798,
            'age_limit': 0,
            'comment_count': int,
            'dislike_count': int,
            'like_count': int,
            'subtitles': {'en': 'mincount:1'},
        },
        'params': {
            'skip_download': True,
            'writesubtitles': True,
        },
    }, {
        # "gated" subreddit post
        'url': 'https://old.reddit.com/r/ketamine/comments/degtjo/when_the_k_hits/',
        'info_dict': {
            'id': 'gqsbxts133r31',
            'ext': 'mp4',
            'display_id': 'degtjo',
            'title': 'When the K hits',
            'alt_title': 'When the K hits',
            'uploader': '[deleted]',
            'channel_id': 'ketamine',
            'comment_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
            'duration': 34,
            'thumbnail': r're:https?://.+/.+\.(?:jpg|png)',
            'timestamp': 1570438713.0,
            'upload_date': '20191007',
        },
    }, {
        'url': 'https://www.reddit.com/r/videos/comments/6rrwyj',
        'only_matching': True,
    }, {
        # imgur
        'url': 'https://www.reddit.com/r/MadeMeSmile/comments/6t7wi5/wait_for_it/',
        'only_matching': True,
    }, {
        # imgur @ old reddit
        'url': 'https://old.reddit.com/r/MadeMeSmile/comments/6t7wi5/wait_for_it/',
        'only_matching': True,
    }, {
        # streamable
        'url': 'https://www.reddit.com/r/videos/comments/6t7sg9/comedians_hilarious_joke_about_the_guam_flag/',
        'only_matching': True,
    }, {
        # youtube
        'url': 'https://www.reddit.com/r/videos/comments/6t75wq/southern_man_tries_to_speak_without_an_accent/',
        'only_matching': True,
    }, {
        # reddit video @ nm reddit
        'url': 'https://nm.reddit.com/r/Cricket/comments/8idvby/lousy_cameraman_finds_himself_in_cairns_line_of/',
        'only_matching': True,
    }, {
        'url': 'https://www.redditmedia.com/r/serbia/comments/pu9wbx/ako_vu%C4%8Di%C4%87_izgubi_izbore_ja_%C4%87u_da_crknem/',
        'only_matching': True,
    }]

    def _perform_login(self, username, password):
        captcha = self._download_json(
            'https://www.reddit.com/api/requires_captcha/login.json', None,
            'Checking login requirement')['required']
        if captcha:
            raise ExtractorError('Reddit is requiring captcha before login', expected=True)
        login = self._download_json(
            f'https://www.reddit.com/api/login/{username}', None, data=urlencode_postdata({
                'op': 'login-main',
                'user': username,
                'passwd': password,
                'api_type': 'json',
            }), note='Logging in', errnote='Login request failed')
        errors = '; '.join(traverse_obj(login, ('json', 'errors', ..., 1)))
        if errors:
            raise ExtractorError(f'Unable to login, Reddit API says {errors}', expected=True)
        elif not traverse_obj(login, ('json', 'data', 'cookie', {str})):
            raise ExtractorError('Unable to login, no cookie was returned')

    def _real_initialize(self):
        # Set cookie to opt-in to age-restricted subreddits
        self._set_cookie('reddit.com', 'over18', '1')
        # Set cookie to opt-in to "gated" subreddits
        options = traverse_obj(self._get_cookies('https://www.reddit.com/'), (
            '_options', 'value', {urllib.parse.unquote}, {json.loads}, {dict})) or {}
        options['pref_gated_sr_optin'] = True
        self._set_cookie('reddit.com', '_options', urllib.parse.quote(json.dumps(options)))

    def _get_subtitles(self, video_id):
        # Fallback if there were no subtitles provided by DASH or HLS manifests
        caption_url = f'https://v.redd.it/{video_id}/wh_ben_en.vtt'
        if self._is_valid_url(caption_url, video_id, item='subtitles'):
            return {'en': [{'url': caption_url}]}

    def _real_extract(self, url):
        slug, video_id = self._match_valid_url(url).group('slug', 'id')

        try:
            data = self._download_json(
                f'https://www.reddit.com/{slug}/.json', video_id, expected_status=403)
        except ExtractorError as e:
            if isinstance(e.cause, json.JSONDecodeError):
                if self._get_cookies('https://www.reddit.com/').get('reddit_session'):
                    raise ExtractorError('Your IP address is unable to access the Reddit API', expected=True)
                self.raise_login_required('Account authentication is required')
            raise

        if traverse_obj(data, 'error') == 403:
            reason = data.get('reason')
            if reason == 'quarantined':
                self.raise_login_required('Quarantined subreddit; an account that has opted in is required')
            elif reason == 'private':
                self.raise_login_required('Private subreddit; an account that has been approved is required')
            else:
                raise ExtractorError(f'HTTP Error 403 Forbidden; reason given: {reason}')

        data = data[0]['data']['children'][0]['data']
        video_url = data['url']

        thumbnails = []

        def add_thumbnail(src):
            if not isinstance(src, dict):
                return
            thumbnail_url = url_or_none(src.get('url'))
            if not thumbnail_url:
                return
            thumbnails.append({
                'url': unescapeHTML(thumbnail_url),
                'width': int_or_none(src.get('width')),
                'height': int_or_none(src.get('height')),
                'http_headers': {'Accept': '*/*'},
            })

        for image in try_get(data, lambda x: x['preview']['images']) or []:
            if not isinstance(image, dict):
                continue
            add_thumbnail(image.get('source'))
            resolutions = image.get('resolutions')
            if isinstance(resolutions, list):
                for resolution in resolutions:
                    add_thumbnail(resolution)

        info = {
            'thumbnails': thumbnails,
            'age_limit': {True: 18, False: 0}.get(data.get('over_18')),
            **traverse_obj(data, {
                'title': ('title', {truncate_string(left=72)}),
                'alt_title': ('title', {str}),
                'description': ('selftext', {str}, filter),
                'timestamp': ('created_utc', {float_or_none}),
                'uploader': ('author', {str}),
                'channel_id': ('subreddit', {str}),
                'like_count': ('ups', {int_or_none}),
                'dislike_count': ('downs', {int_or_none}),
                'comment_count': ('num_comments', {int_or_none}),
            }),
        }

        parsed_url = urllib.parse.urlparse(video_url)

        # Check for embeds in text posts, or else raise to avoid recursing into the same reddit URL
        if 'reddit.com' in parsed_url.netloc and f'/{video_id}/' in parsed_url.path:
            entries = []
            for media in traverse_obj(data, ('media_metadata', ...), expected_type=dict):
                if not media.get('id') or media.get('e') != 'RedditVideo':
                    continue
                formats = []
                if media.get('hlsUrl'):
                    formats.extend(self._extract_m3u8_formats(
                        unescapeHTML(media['hlsUrl']), video_id, 'mp4', m3u8_id='hls', fatal=False))
                if media.get('dashUrl'):
                    formats.extend(self._extract_mpd_formats(
                        unescapeHTML(media['dashUrl']), video_id, mpd_id='dash', fatal=False))
                if formats:
                    entries.append({
                        'id': media['id'],
                        'display_id': video_id,
                        'formats': formats,
                        **info,
                    })
            if entries:
                return self.playlist_result(entries, video_id, **info)
            raise ExtractorError('No media found', expected=True)

        # Check if media is hosted on reddit:
        reddit_video = traverse_obj(data, (
            (None, ('crosspost_parent_list', ...)), ('secure_media', 'media'), 'reddit_video'), get_all=False)
        if reddit_video:
            playlist_urls = [
                try_get(reddit_video, lambda x: unescapeHTML(x[y]))
                for y in ('dash_url', 'hls_url')
            ]

            # Update video_id
            display_id = video_id
            video_id = self._search_regex(
                r'https?://v\.redd\.it/(?P<id>[^/?#&]+)', reddit_video['fallback_url'],
                'video_id', default=display_id)

            dash_playlist_url = playlist_urls[0] or f'https://v.redd.it/{video_id}/DASHPlaylist.mpd'
            hls_playlist_url = playlist_urls[1] or f'https://v.redd.it/{video_id}/HLSPlaylist.m3u8'
            qs = traverse_obj(parse_qs(hls_playlist_url), {
                'f': ('f', 0, {lambda x: ','.join([x, 'subsAll']) if x else 'hd,subsAll'}),
            })
            hls_playlist_url = update_url_query(hls_playlist_url, qs)

            formats = [{
                'url': unescapeHTML(reddit_video['fallback_url']),
                'height': int_or_none(reddit_video.get('height')),
                'width': int_or_none(reddit_video.get('width')),
                'tbr': int_or_none(reddit_video.get('bitrate_kbps')),
                'acodec': 'none',
                'vcodec': 'h264',
                'ext': 'mp4',
                'format_id': 'fallback',
                'format_note': 'DASH video, mp4_dash',
            }]
            hls_fmts, subtitles = self._extract_m3u8_formats_and_subtitles(
                hls_playlist_url, display_id, 'mp4', m3u8_id='hls', fatal=False)
            formats.extend(hls_fmts)
            dash_fmts, dash_subs = self._extract_mpd_formats_and_subtitles(
                dash_playlist_url, display_id, mpd_id='dash', fatal=False)
            formats.extend(dash_fmts)
            self._merge_subtitles(dash_subs, target=subtitles)

            return {
                **info,
                'id': video_id,
                'display_id': display_id,
                'formats': formats,
                'subtitles': subtitles or self.extract_subtitles(video_id),
                'duration': int_or_none(reddit_video.get('duration')),
            }

        if parsed_url.netloc == 'v.redd.it':
            self.raise_no_formats('This video is processing', expected=True, video_id=video_id)
            return {
                **info,
                'id': parsed_url.path.split('/')[1],
                'display_id': video_id,
            }

        # Not hosted on reddit, must continue extraction
        return {
            **info,
            'display_id': video_id,
            '_type': 'url_transparent',
            'url': video_url,
        }
