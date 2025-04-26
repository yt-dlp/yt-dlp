
from .common import ExtractorError, InfoExtractor
from ..utils import determine_ext, join_nonempty
from ..utils.traversal import traverse_obj


class PlayerFmIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www.)?player.fm/(?:series)?/[a-z\d-]+/(?P<id>[a-z\d-]+)'
    _TESTS = [{
        'url': 'https://player.fm/series/chapo-trap-house/movie-mindset-33-casino-feat-felix',
        'info_dict': {
            'id': 'movie-mindset-33-casino-feat-felix',
            'thumbnail': r're:^https://.*\.(jpg|png)',
            'title': 'Movie Mindset 33 - Casino feat. Felix',
            'creators': ['Chapo Trap House'],
            'description': 'The first episode of this season of Movie Mindset is free for all listeners as always. To listen to the rest of the season, subscribe at <a href="http://www.patreon.com/chapotraphouse">www.patreon.com/chapotraphouse</a> When you love movies, you’ve got to watch them. There’s no other way…Movie Mindset Season 3 commences with our first ever single feature on the most referenced movie in Chapo Trap House history: Martin Scorsese’s masterpiece Casino. Will and Hesse are joined by Felix to take a kaleidoscopic and dizzying dive into the inferno of American greed that is Las Vegas. Anchored by a triumvirate of all career great performances from Robert De Niro, Sharon Stone and Joe Pesci in FULL PSYCHO MODE, Casino is by equal turns hilarious and stomach turning and stands alone as Scorsese’s grandest and most generous examination of evil and the tragic flaws that doom us all. Should you listen even if you haven’t seen this movie? Why take a chance? At least that the way we feel about it.',
            'duration': 6830,
            'ext': 'mp3',
        },
    }, {
        'url': 'https://player.fm/series/nbc-nightly-news-with-lester-holt/thursday-april-24-2025',
        'info_dict': {
            'id': 'thursday-april-24-2025',
            'thumbnail': r're:^https://.*\.(jpg|png)',
            'title': 'Thursday, April 24, 2025',
            'creators': ['Lester Holt, NBC News'],
            'description': '<p>Trump urges Putin to \'STOP\' after deadly Russian strike on Ukraine; More than 90,000 people have paid their respects to Pope Francis; Miami shooting leaves three injured; and more on tonight’s broadcast.</p>',
            'duration': 1250,
            'ext': 'mp3',
        },
    }, {
        'url': 'https://player.fm/series/soccer-101/ep-109-its-kicking-off-how-have-the-rules-for-kickoff-changed-what-are-the-best-approaches-to-getting-the-game-underway-and-how-could-we-improve-on-the-present-system',
        'info_dict': {
            'id': 'ep-109-its-kicking-off-how-have-the-rules-for-kickoff-changed-what-are-the-best-approaches-to-getting-the-game-underway-and-how-could-we-improve-on-the-present-system',
            'thumbnail': r're:^https://.*\.(jpg|png)',
            'title': '#109 It\'s kicking off! How have the rules for kickoff changed, what are the best approaches to getting the game underway, and how could we improve on the present system?',
            'creators': ['TSS'],
            'description': '<p>Ryan is joined by Joe and Taylor to answer the age old question (in your best Jerry Seinfeld impression), "What\'s the deal with kickoff?!" How does a game get underway, how have the rules regarding kickoff evolved since the mid-1800s, what are the different approaches to getting your tactics right from kickoff, how could we improve upon the current system, and much much more!</p><p>The Soccer 101 theme, and plenty of other excellent music, can be found right here: <a href="https://aerialist.bandcamp.com/">https://aerialist.bandcamp.com</a>.</p>',
            'duration': 1765,
            'ext': 'mp3',
        },
    }]

    def _real_extract(self, url):
        # podcast url is always after last backlash
        video_id = self._match_id(url)
        data = self._download_json(url + '.json', None)

        title = data.get('title')
        description = data.get('description')
        duration = data.get('duration')
        thumbnail = traverse_obj(data, ('image', 'url'), ('series', 'image', 'url'))
        creators = [traverse_obj(data, ('series', 'author'))]

        video_url = join_nonempty('https', self._search_regex(r'redirect.mp3/(.*)', data['url'], 'redirect'), delim='://')
        if not video_url:
            raise ExtractorError('URL to podcast not found', expected=True)
        formats = [{
            'url': video_url,
            'ext': determine_ext(video_url, default_ext=''),
        }]
        return {
            'id': video_id,
            'thumbnail': thumbnail,
            'title': title,
            'creators': creators,
            'description': description,
            'duration': duration,
            'formats': formats,
        }
