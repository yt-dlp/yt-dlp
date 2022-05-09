import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    extract_attributes,
    ExtractorError,
    join_nonempty,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class AnimeOnDemandIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?anime-on-demand\.de/anime/(?P<id>\d+)'
    _LOGIN_URL = 'https://www.anime-on-demand.de/users/sign_in'
    _APPLY_HTML5_URL = 'https://www.anime-on-demand.de/html5apply'
    _NETRC_MACHINE = 'animeondemand'
    # German-speaking countries of Europe
    _GEO_COUNTRIES = ['AT', 'CH', 'DE', 'LI', 'LU']
    _TESTS = [{
        # jap, OmU
        'url': 'https://www.anime-on-demand.de/anime/161',
        'info_dict': {
            'id': '161',
            'title': 'Grimgar, Ashes and Illusions (OmU)',
            'description': 'md5:6681ce3c07c7189d255ac6ab23812d31',
        },
        'playlist_mincount': 4,
    }, {
        # Film wording is used instead of Episode, ger/jap, Dub/OmU
        'url': 'https://www.anime-on-demand.de/anime/39',
        'only_matching': True,
    }, {
        # Episodes without titles, jap, OmU
        'url': 'https://www.anime-on-demand.de/anime/162',
        'only_matching': True,
    }, {
        # ger/jap, Dub/OmU, account required
        'url': 'https://www.anime-on-demand.de/anime/169',
        'only_matching': True,
    }, {
        # Full length film, non-series, ger/jap, Dub/OmU, account required
        'url': 'https://www.anime-on-demand.de/anime/185',
        'only_matching': True,
    }, {
        # Flash videos
        'url': 'https://www.anime-on-demand.de/anime/12',
        'only_matching': True,
    }]

    def _perform_login(self, username, password):
        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login page')

        if '>Our licensing terms allow the distribution of animes only to German-speaking countries of Europe' in login_page:
            self.raise_geo_restricted(
                '%s is only available in German-speaking countries of Europe' % self.IE_NAME)

        login_form = self._form_hidden_inputs('new_user', login_page)

        login_form.update({
            'user[login]': username,
            'user[password]': password,
        })

        post_url = self._search_regex(
            r'<form[^>]+action=(["\'])(?P<url>.+?)\1', login_page,
            'post url', default=self._LOGIN_URL, group='url')

        if not post_url.startswith('http'):
            post_url = urljoin(self._LOGIN_URL, post_url)

        response = self._download_webpage(
            post_url, None, 'Logging in',
            data=urlencode_postdata(login_form), headers={
                'Referer': self._LOGIN_URL,
            })

        if all(p not in response for p in ('>Logout<', 'href="/users/sign_out"')):
            error = self._search_regex(
                r'<p[^>]+\bclass=(["\'])(?:(?!\1).)*\balert\b(?:(?!\1).)*\1[^>]*>(?P<error>.+?)</p>',
                response, 'error', default=None, group='error')
            if error:
                raise ExtractorError('Unable to login: %s' % error, expected=True)
            raise ExtractorError('Unable to log in')

    def _real_extract(self, url):
        anime_id = self._match_id(url)

        webpage = self._download_webpage(url, anime_id)

        if 'data-playlist=' not in webpage:
            self._download_webpage(
                self._APPLY_HTML5_URL, anime_id,
                'Activating HTML5 beta', 'Unable to apply HTML5 beta')
            webpage = self._download_webpage(url, anime_id)

        csrf_token = self._html_search_meta(
            'csrf-token', webpage, 'csrf token', fatal=True)

        anime_title = self._html_search_regex(
            r'(?s)<h1[^>]+itemprop="name"[^>]*>(.+?)</h1>',
            webpage, 'anime name')
        anime_description = self._html_search_regex(
            r'(?s)<div[^>]+itemprop="description"[^>]*>(.+?)</div>',
            webpage, 'anime description', default=None)

        def extract_info(html, video_id, num=None):
            title, description = [None] * 2
            formats = []

            for input_ in re.findall(
                    r'<input[^>]+class=["\'].*?streamstarter[^>]+>', html):
                attributes = extract_attributes(input_)
                title = attributes.get('data-dialog-header')
                playlist_urls = []
                for playlist_key in ('data-playlist', 'data-otherplaylist', 'data-stream'):
                    playlist_url = attributes.get(playlist_key)
                    if isinstance(playlist_url, compat_str) and re.match(
                            r'/?[\da-zA-Z]+', playlist_url):
                        playlist_urls.append(attributes[playlist_key])
                if not playlist_urls:
                    continue

                lang = attributes.get('data-lang')
                lang_note = attributes.get('value')

                for playlist_url in playlist_urls:
                    kind = self._search_regex(
                        r'videomaterialurl/\d+/([^/]+)/',
                        playlist_url, 'media kind', default=None)
                    format_id = join_nonempty(lang, kind) if lang or kind else str(num)
                    format_note = join_nonempty(kind, lang_note, delim=', ')
                    item_id_list = []
                    if format_id:
                        item_id_list.append(format_id)
                    item_id_list.append('videomaterial')
                    playlist = self._download_json(
                        urljoin(url, playlist_url), video_id,
                        'Downloading %s JSON' % ' '.join(item_id_list),
                        headers={
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-CSRF-Token': csrf_token,
                            'Referer': url,
                            'Accept': 'application/json, text/javascript, */*; q=0.01',
                        }, fatal=False)
                    if not playlist:
                        continue
                    stream_url = url_or_none(playlist.get('streamurl'))
                    if stream_url:
                        rtmp = re.search(
                            r'^(?P<url>rtmpe?://(?P<host>[^/]+)/(?P<app>.+/))(?P<playpath>mp[34]:.+)',
                            stream_url)
                        if rtmp:
                            formats.append({
                                'url': rtmp.group('url'),
                                'app': rtmp.group('app'),
                                'play_path': rtmp.group('playpath'),
                                'page_url': url,
                                'player_url': 'https://www.anime-on-demand.de/assets/jwplayer.flash-55abfb34080700304d49125ce9ffb4a6.swf',
                                'rtmp_real_time': True,
                                'format_id': 'rtmp',
                                'ext': 'flv',
                            })
                            continue
                    start_video = playlist.get('startvideo', 0)
                    playlist = playlist.get('playlist')
                    if not playlist or not isinstance(playlist, list):
                        continue
                    playlist = playlist[start_video]
                    title = playlist.get('title')
                    if not title:
                        continue
                    description = playlist.get('description')
                    for source in playlist.get('sources', []):
                        file_ = source.get('file')
                        if not file_:
                            continue
                        ext = determine_ext(file_)
                        format_id = join_nonempty(
                            lang, kind,
                            'hls' if ext == 'm3u8' else None,
                            'dash' if source.get('type') == 'video/dash' or ext == 'mpd' else None)
                        if ext == 'm3u8':
                            file_formats = self._extract_m3u8_formats(
                                file_, video_id, 'mp4',
                                entry_protocol='m3u8_native', m3u8_id=format_id, fatal=False)
                        elif source.get('type') == 'video/dash' or ext == 'mpd':
                            continue
                            file_formats = self._extract_mpd_formats(
                                file_, video_id, mpd_id=format_id, fatal=False)
                        else:
                            continue
                        for f in file_formats:
                            f.update({
                                'language': lang,
                                'format_note': format_note,
                            })
                        formats.extend(file_formats)

            return {
                'title': title,
                'description': description,
                'formats': formats,
            }

        def extract_entries(html, video_id, common_info, num=None):
            info = extract_info(html, video_id, num)

            if info['formats']:
                self._sort_formats(info['formats'])
                f = common_info.copy()
                f.update(info)
                yield f

            # Extract teaser/trailer only when full episode is not available
            if not info['formats']:
                m = re.search(
                    r'data-dialog-header=(["\'])(?P<title>.+?)\1[^>]+href=(["\'])(?P<href>.+?)\3[^>]*>(?P<kind>Teaser|Trailer)<',
                    html)
                if m:
                    f = common_info.copy()
                    f.update({
                        'id': '%s-%s' % (f['id'], m.group('kind').lower()),
                        'title': m.group('title'),
                        'url': urljoin(url, m.group('href')),
                    })
                    yield f

        def extract_episodes(html):
            for num, episode_html in enumerate(re.findall(
                    r'(?s)<h3[^>]+class="episodebox-title".+?>Episodeninhalt<', html), 1):
                episodebox_title = self._search_regex(
                    (r'class="episodebox-title"[^>]+title=(["\'])(?P<title>.+?)\1',
                     r'class="episodebox-title"[^>]+>(?P<title>.+?)<'),
                    episode_html, 'episodebox title', default=None, group='title')
                if not episodebox_title:
                    continue

                episode_number = int(self._search_regex(
                    r'(?:Episode|Film)\s*(\d+)',
                    episodebox_title, 'episode number', default=num))
                episode_title = self._search_regex(
                    r'(?:Episode|Film)\s*\d+\s*-\s*(.+)',
                    episodebox_title, 'episode title', default=None)

                video_id = 'episode-%d' % episode_number

                common_info = {
                    'id': video_id,
                    'series': anime_title,
                    'episode': episode_title,
                    'episode_number': episode_number,
                }

                for e in extract_entries(episode_html, video_id, common_info):
                    yield e

        def extract_film(html, video_id):
            common_info = {
                'id': anime_id,
                'title': anime_title,
                'description': anime_description,
            }
            for e in extract_entries(html, video_id, common_info):
                yield e

        def entries():
            has_episodes = False
            for e in extract_episodes(webpage):
                has_episodes = True
                yield e

            if not has_episodes:
                for e in extract_film(webpage, anime_id):
                    yield e

        return self.playlist_result(
            entries(), anime_id, anime_title, anime_description)
