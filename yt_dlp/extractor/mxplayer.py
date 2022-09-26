from .common import InfoExtractor
from ..compat import compat_str
from ..utils import try_get
from ..utils import traverse_obj


class MxplayerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/(?P<type>movie|show/[-\w]+/[-\w]+)/(?P<display_id>[-\w]+)-(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/show/watch-my-girlfriend-is-an-alien-hindi-dubbed/season-1/episode-1-online-9d2013d31d5835bb8400e3b3c5e7bb72',
        'info_dict': {
            'id': '9d2013d31d5835bb8400e3b3c5e7bb72',
            'display_id': 'episode-1-online',
            'ext': 'mp4',
            'title': 'Episode 1',
            'description': "Watch Season 1, Episode 1 of the show My Girlfriend Is an Alien (Hindi Dubbed).'",
            'season_number': 1,
            'episode_number': 1,
            'duration': 2451,
            'season': 'Season 1',
            'series': 'My Girlfriend Is An Alien (Hindi Dubbed)',
            'episode': 'Episode 1'
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/movie/watch-knock-knock-hindi-dubbed-movie-online-b9fa28df3bfb8758874735bbd7d2655a?watch=true',
        'info_dict': {
            'id': 'b9fa28df3bfb8758874735bbd7d2655a',
            'display_id': 'episode-1-online',
            'ext': 'mp4',
            'title': 'Knock Knock (Hindi Dubbed)',
            'description': 'Evan, a devoted husband, and father, invites double trouble as he allows two girls to seek shelter at his place. His sweet gesture takes the shape of a dangerous cat and mouse game.',
            'season_number': None,
            'episode_number': None,
            'duration': 5970,
            'season': None,
            'series': None,
            'episode': None
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
        'skip': 'No longer available',
    }, {
        'url': 'https://www.mxplayer.in/show/watch-shaitaan/season-1/the-infamous-taxi-gang-of-meerut-online-45055d5bcff169ad48f2ad7552a83d6c',
        'info_dict': {
            'id': '45055d5bcff169ad48f2ad7552a83d6c',
            'ext': 'mp4',
            'title': 'The infamous taxi gang of Meerut',
            'description': "A notorious gang of taxi drivers in and around Meerut, engage in a series of brutal homicides across the state. The gang carefully hunts for a vulnerable passenger, preferably a foreigner or a NRI, takes them to a deserted place, murders them and disposes the bodies after looting their possessions. 'Shaitaan' brings you some of the most infamous crimes in the country and probes into the psychology of the minds that commit such crimes.",
            'season_number': 1,
            'episode_number': 1,
            'duration': 2332,
            'season': 'Season 1',
            'series': 'Shaitaan',
            'episode': 'Episode 1'
        },
        'params': {
            'format': 'best',
            'skip_download': True,
        },
        'skip': 'No longer available.'
    }, {
        'url': 'https://www.mxplayer.in/show/watch-aashram/chapter-1/duh-swapna-online-d445579792b0135598ba1bc9088a84cb',
        'info_dict': {
            'id': 'd445579792b0135598ba1bc9088a84cb',
            'display_id': 'duh-swapna-online',
            'ext': 'mp4',
            'title': 'Duh Swapna',
            'description': 'Episode 3: Pammi takes Satti on a tour of the Aashram and shows him what Baba has actually done for the poor, that has never been done by anyone. Tension rises in Lochan family as Pammi declares she wants to become a Sadhvi and join the Aashram. Besotted and motivated with the words of righteous postmortem specialist Dr. Natasha, S.I Ujagar Singh decides to pursue the skeleton case along with constable Sadhu.',
            'season_number': 1,
            'episode_number': 3,
            'duration': 2568,
            'season': 'Season 1',
            'series': 'Aashram',
            'episode': 'Episode 3'
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/show/watch-dangerous/season-1/chapter-1-online-5a351b4f9fb69436f6bd6ae3a1a75292',
        'info_dict': {
            'id': '5a351b4f9fb69436f6bd6ae3a1a75292',
            'display_id': 'chapter-1-online',
            'ext': 'mp4',
            'title': 'Chapter 1',
            'description': "Episode 1: Neha begins investigating the kidnapping of her ex-boyfriend Aditya Dhanraj's wife Dia. She finds evidence of a troubled marriage between the two.",
            'season_number': 1,
            'episode_number': 1,
            'duration': 1305,
            'season': 'Season 1',
            'series': 'Dangerous',
            'episode': 'Episode 1'
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/movie/watch-the-attacks-of-2611-movie-online-0452f0d80226c398d63ce7e3ea40fa2d',
        'info_dict': {
            'id': '0452f0d80226c398d63ce7e3ea40fa2d',
            'ext': 'mp4',
            'title': 'The Attacks of 26/11',
            'description': 'Ten terrorists travel to India and launch several attacks at various places in South Mumbai. Subsequently, the Mumbai Police arrests Ajmal Kasab, one of the terrorists.',
            'season_number': None,
            'episode_number': None,
            'duration': 6085,
            'season': None,
            'series': None,
            'episode': None
        },
        'params': {
            'format': 'best',
            'skip_download': True,
        },
        'skip': 'No longer available. Cannot be played on browser'
    }, {
        'url': 'https://www.mxplayer.in/movie/watch-kitne-door-kitne-paas-movie-online-a9e9c76c566205955f70d8b2cb88a6a2',
        'info_dict': {
            'id': 'a9e9c76c566205955f70d8b2cb88a6a2',
            'display_id': 'watch-kitne-door-kitne-paas-movie-online',
            'title': 'Kitne Door Kitne Paas',
            'duration': 8458,
            'ext': 'mp4',
            'description': 'Jatin and Karishma, who meet each other on a plane to India, are set to marry the partners chosen by their respective parents. However, they find themselves attracted to each other.',
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }, {
        'url': 'https://www.mxplayer.in/show/watch-ek-thi-begum-hindi/season-2/game-of-power-online-5e5305c28f1409847cdc4520b6ad77cf',
        'info_dict': {
            'id': '5e5305c28f1409847cdc4520b6ad77cf',
            'display_id': 'game-of-power-online',
            'title': 'Game Of Power',
            'duration': 1845,
            'ext': 'mp4',
            'description': 'Cops arrest Ashraf assuming a prostitute. But she gets away with her new identity, Leela Paswan. Maqsood dumps Nana Mhatre and appoints Shaqeel Ansari as a new Bombay chief. For society, he is a sophisticated businessman. The rift between the new chief minister, Yashwant Patil and Shaqeel Ansari begins with a failed business deal. Ashwin Surve, a daredevil young gangster challenges established gangs of Maqsood & Bhai Chavan. He wants to enter in the drug business. But the only supplier Nari Khan supplies stuff only to Maqsood gang and no one else. ACP Qureshi arrests Bhai Chavan and turns his focus on people close to Zaheer and Ashraf. Ashraf faces a narrow escape from Qureshi and decides to take up her new identity beyond just fake documents.',
            'series': 'Ek Thi Begum (Hindi)',
            'season': 'Season 2',
            'season_number': 2,
            'episode': 'Episode 2',
            'episode_number': 2,
        },
        'params': {
            'format': 'bv',
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_type, display_id, video_id = self._match_valid_url(url).groups()

        if 'show' in video_type:
            video_type = 'episode'

        data_json = self._download_json(
            f'https://api.mxplay.com/v1/web/detail/video?type={video_type}&id={video_id}', display_id
        )

        formats = []
        subtitles = {}
        series, season, season_number, episode_number = None, None, None, None

        if video_type == 'episode':
            series = traverse_obj(data_json, ('container', 'container', 'title'))
            season = traverse_obj(data_json, ('container', 'title'))
            episode_number = data_json.get('sequence')
            season_number = int(self._search_regex(r'Season (\d+)', season, 'Season Number'))

        for stream_type in 'dash', 'hls':
            playlist_url = 'https://llvod.mxplay.com/{}'.format(data_json['stream'][stream_type]['high'])

            if stream_type == 'dash':
                frmts, subs = self._extract_mpd_formats_and_subtitles(playlist_url, display_id, fatal=False)
            else:
                frmts, subs = self._extract_m3u8_formats_and_subtitles(playlist_url, display_id, fatal=False)

            formats.extend(frmts)
            self._merge_subtitles(subs, target=subtitles)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': data_json['title'],
            'formats': formats,
            'subtitles': subtitles,
            'display_id': display_id,
            'duration': data_json.get('duration'),
            'series': series,
            'description': data_json.get('description'),
            'season': season,
            'season_number': season_number,
            'episode_number': episode_number,
        }


class MxplayerShowIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/show/(?P<display_id>[-\w]+)-(?P<id>\w+)/?(?:$|[#?])'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/show/watch-chakravartin-ashoka-samrat-series-online-a8f44e3cc0814b5601d17772cedf5417',
        'playlist_mincount': 440,
        'info_dict': {
            'id': 'a8f44e3cc0814b5601d17772cedf5417',
            'title': 'Watch Chakravartin Ashoka Samrat Series Online',
        }
    }]

    _API_SHOW_URL = "https://api.mxplay.com/v1/web/detail/tab/tvshowseasons?type=tv_show&id={}&device-density=2&platform=com.mxplay.desktop&content-languages=hi,en"
    _API_EPISODES_URL = "https://api.mxplay.com/v1/web/detail/tab/tvshowepisodes?type=season&id={}&device-density=1&platform=com.mxplay.desktop&content-languages=hi,en&{}"

    def _entries(self, show_id):
        show_json = self._download_json(
            self._API_SHOW_URL.format(show_id),
            video_id=show_id, headers={'Referer': 'https://mxplayer.in'})
        page_num = 0
        for season in show_json.get('items') or []:
            season_id = try_get(season, lambda x: x['id'], compat_str)
            next_url = ''
            while next_url is not None:
                page_num += 1
                season_json = self._download_json(
                    self._API_EPISODES_URL.format(season_id, next_url),
                    video_id=season_id,
                    headers={'Referer': 'https://mxplayer.in'},
                    note='Downloading JSON metadata page %d' % page_num)
                for episode in season_json.get('items') or []:
                    video_url = episode['webUrl']
                    yield self.url_result(
                        'https://mxplayer.in%s' % video_url,
                        ie=MxplayerIE.ie_key(), video_id=video_url.split('-')[-1])
                next_url = season_json.get('next')

    def _real_extract(self, url):
        display_id, show_id = self._match_valid_url(url).groups()
        return self.playlist_result(
            self._entries(show_id), playlist_id=show_id,
            playlist_title=display_id.replace('-', ' ').title())
