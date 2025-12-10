import os
import re
import types
import urllib.parse
import xml.etree.ElementTree

from .common import InfoExtractor
from .commonprotocols import RtmpIE
from .youtube import YoutubeIE
from ..compat import compat_etree_fromstring
from ..cookies import LenientSimpleCookie
from ..networking.exceptions import HTTPError
from ..networking.impersonate import ImpersonateTarget
from ..utils import (
    KNOWN_EXTENSIONS,
    MEDIA_EXTENSIONS,
    ExtractorError,
    UnsupportedError,
    determine_ext,
    determine_protocol,
    dict_get,
    extract_basic_auth,
    filter_dict,
    format_field,
    int_or_none,
    is_html,
    js_to_json,
    merge_dicts,
    mimetype2ext,
    orderedSet,
    parse_duration,
    parse_resolution,
    smuggle_url,
    str_or_none,
    traverse_obj,
    try_call,
    unescapeHTML,
    unified_timestamp,
    unsmuggle_url,
    update_url,
    update_url_query,
    url_or_none,
    urlhandle_detect_ext,
    urljoin,
    variadic,
    xpath_attr,
    xpath_text,
    xpath_with_ns,
)
from ..utils._utils import _UnsafeExtensionError


class GenericIE(InfoExtractor):
    IE_DESC = 'Generic downloader that works on some sites'
    _VALID_URL = r'.*'
    IE_NAME = 'generic'
    _NETRC_MACHINE = False  # Suppress username warning
    _TESTS = [{
        # Direct link
        # https://github.com/ytdl-org/youtube-dl/commit/c5fa81fe81ce05cd81c20ff4ea6dac3dccdcbf9d
        'url': 'https://media.w3.org/2010/05/sintel/trailer.mp4',
        'md5': '67d406c2bcb6af27fa886f31aa934bbe',
        'info_dict': {
            'id': 'trailer',
            'ext': 'mp4',
            'title': 'trailer',
            'direct': True,
            'timestamp': 1273772943,
            'upload_date': '20100513',
        },
    }, {
        # Direct link: No HEAD support
        # https://github.com/ytdl-org/youtube-dl/issues/4032
        'url': 'http://ai-radio.org:8000/radio.opus',
        'info_dict': {
            'id': 'radio',
            'ext': 'opus',
            'title': 'radio',
        },
        'skip': 'Invalid URL',
    }, {
        # Direct link: Incorrect MIME type
        # https://github.com/ytdl-org/youtube-dl/commit/c5fa81fe81ce05cd81c20ff4ea6dac3dccdcbf9d
        'url': 'https://ftp.nluug.nl/video/nluug/2014-11-20_nj14/zaal-2/5_Lennart_Poettering_-_Systemd.webm',
        'md5': '4ccbebe5f36706d85221f204d7eb5913',
        'info_dict': {
            'id': '5_Lennart_Poettering_-_Systemd',
            'ext': 'webm',
            'title': '5_Lennart_Poettering_-_Systemd',
            'direct': True,
            'timestamp': 1416498816,
            'upload_date': '20141120',
        },
    }, {
        # Direct link: Live HLS; https://castr.com/hlsplayer/
        # https://github.com/yt-dlp/yt-dlp/pull/6775
        'url': 'https://stream-akamai.castr.com/5b9352dbda7b8c769937e459/live_2361c920455111ea85db6911fe397b9e/index.fmp4.m3u8',
        'info_dict': {
            'id': 'index.fmp4',
            'ext': 'mp4',
            'title': str,
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Compressed when `Accept-Encoding: *`
        # https://github.com/ytdl-org/youtube-dl/commit/a074e922967fa571d4f1abb1773c711747060f00
        'url': 'http://calimero.tk/muzik/FictionJunction-Parallel_Hearts.flac',
        'info_dict': {
            'id': 'FictionJunction-Parallel_Hearts',
            'ext': 'flac',
            'title': 'FictionJunction-Parallel_Hearts',
        },
        'skip': 'Invalid URL',
    }, {
        # `Content-Encoding: br` when `Accept-Encoding: *`
        # https://github.com/yt-dlp/yt-dlp/commit/3e01ce744a981d8f19ae77ec695005e7000f4703
        'url': 'https://www.extra.cz/cauky-lidi-70-dil-babis-predstavil-pohadky-prymulanek-nebo-andrejovy-nove-saty-ac867',
        'md5': 'a9a2cad3e54f78e4680c6deef82417e9',
        'info_dict': {
            'id': 'cauky-lidi-70-dil-babis-predstavil-pohadky-prymulanek-nebo-andrejovy-nove-saty-ac867',
            'ext': 'mp4',
            'title': 'čauky lidi 70 finall',
            'description': 'md5:47b2673a5b76780d9d329783e1fbf5aa',
            'direct': True,
            'duration': 318.0,
            'thumbnail': r're:https?://media\.extra\.cz/static/img/.+\.jpg',
            'timestamp': 1654513791,
            'upload_date': '20220606',
        },
        'params': {'extractor_args': {'generic': {'impersonate': ['chrome']}}},
    }, {
        # HLS: `Content-Type: audio/mpegurl`; https://bitmovin.com/demos/stream-test
        # https://github.com/ytdl-org/youtube-dl/commit/20938f768b16c945c6041ba3c0a7ae1a4e790881
        'url': 'https://cdn.bitmovin.com/content/assets/art-of-motion-dash-hls-progressive/m3u8s/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.m3u8',
        'info_dict': {
            'id': 'f08e80da-bf1d-4e3d-8899-f0f6155f6efa',
            'ext': 'mp4',
            'title': 'f08e80da-bf1d-4e3d-8899-f0f6155f6efa',
            'duration': 211,
            'timestamp': 1737363648,
            'upload_date': '20250120',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # HLS: `Content-Type: text/plain`; https://github.com/grafov/m3u8
        # https://github.com/ytdl-org/youtube-dl/commit/edd9b71c2cca7e5a0df8799710d9ad410ec77d29
        'url': 'https://raw.githubusercontent.com/grafov/m3u8/refs/heads/master/sample-playlists/master.m3u8',
        'info_dict': {
            'id': 'master',
            'ext': 'mp4',
            'title': 'master',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # MPEG-DASH; https://bitmovin.com/demos/stream-test
        # https://github.com/ytdl-org/youtube-dl/commit/9d939cec48f06a401fb79eb078c1fc50b2aefbe1
        'url': 'https://cdn.bitmovin.com/content/assets/art-of-motion-dash-hls-progressive/mpds/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.mpd',
        'info_dict': {
            'id': 'f08e80da-bf1d-4e3d-8899-f0f6155f6efa',
            'ext': 'mp4',
            'title': 'f08e80da-bf1d-4e3d-8899-f0f6155f6efa',
            'timestamp': 1737363728,
            'upload_date': '20250120',
        },
        'params': {'skip_download': True},
    }, {
        # Live MPEG-DASH; https://livesim2.dashif.org/urlgen/create
        # https://github.com/yt-dlp/yt-dlp/pull/12256
        'url': 'https://livesim2.dashif.org/livesim2/ato_10/testpic_2s/Manifest.mpd',
        'info_dict': {
            'id': 'Manifest',
            'ext': 'mp4',
            'title': str,
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'livestream'},
    }, {
        # SMIL
        # https://github.com/ytdl-org/youtube-dl/pull/6428
        'url': 'https://api.new.livestream.com/accounts/21/events/7954027/videos/166558123.secure.smil',
        'info_dict': {
            'id': '166558123.secure',
            'ext': 'mp4',
            'title': '73fb2379-a624-4b6c-bce4-e46086007f2c',
        },
        'params': {'skip_download': 'smil'},
    }, {
        # XSPF playlist; https://shellac-archive.ch/de/index.html
        # https://github.com/ytdl-org/youtube-dl/commit/1de5cd3ba51ce67d9a1cd3b40157058e78e46692
        'url': 'https://shellac-archive.ch/repository/xspf/22-AL0019Z.xspf',
        'info_dict': {
            'id': '22-AL0019Z',
        },
        'playlist_count': 12,
        'params': {'skip_download': True},
    }, {
        # RSS feed
        # https://github.com/ytdl-org/youtube-dl/commit/c5fa81fe81ce05cd81c20ff4ea6dac3dccdcbf9d
        'url': 'http://phihag.de/2014/youtube-dl/rss2.xml',
        'info_dict': {
            'id': 'https://phihag.de/2014/youtube-dl/rss2.xml',
            'title': 'Zero Punctuation',
            'description': 'md5:512ae5f840e52eb3c0d08d4bed08eb3e',
        },
        'playlist_mincount': 11,
    }, {
        # RSS feed: Includes enclosure, description, and thumbnails
        # https://github.com/ytdl-org/youtube-dl/pull/27405
        'url': 'https://anchor.fm/s/dd00e14/podcast/rss',
        'info_dict': {
            'id': 'https://anchor.fm/s/dd00e14/podcast/rss',
            'title': '100% Hydrogen ',
            'description': 'md5:7ec96327f8b91a2549a2e74f064022a1',
        },
        'playlist_count': 1,
        'params': {'skip_download': True},
    }, {
        # RSS feed: Includes guid
        'url': 'https://www.omnycontent.com/d/playlist/a7b4f8fe-59d9-4afc-a79a-a90101378abf/bf2c1d80-3656-4449-9d00-a903004e8f84/efbff746-e7c1-463a-9d80-a903004e8f8f/podcast.rss',
        'info_dict': {
            'id': 'https://www.omnycontent.com/d/playlist/a7b4f8fe-59d9-4afc-a79a-a90101378abf/bf2c1d80-3656-4449-9d00-a903004e8f84/efbff746-e7c1-463a-9d80-a903004e8f8f/podcast.rss',
            'title': 'The Little Red Podcast',
            'description': 'md5:be809a44b63b0c56fb485caf68685520',
        },
        'playlist_mincount': 76,
    }, {
        # RSS feed: Includes enclosure and unsupported URLs
        # https://github.com/ytdl-org/youtube-dl/pull/16189
        'url': 'https://www.interfax.ru/rss.asp',
        'info_dict': {
            'id': 'https://www.interfax.ru/rss.asp',
            'title': 'Интерфакс',
            'description': 'md5:49b6b8905772efba21923942bbc0444c',
        },
        'playlist_mincount': 25,
    }, {
        # Webpage starts with a duplicate UTF-8 BOM
        # https://github.com/yt-dlp/yt-dlp/commit/80e8493ee7c3083f4e215794e4a67ba5265f24f7
        'url': 'https://www.filmarkivet.se/movies/paris-d-moll/',
        'md5': 'df02cadc719dcc63d43288366f037754',
        'info_dict': {
            'id': 'paris-d-moll',
            'ext': 'mp4',
            'title': 'Paris d-moll',
            'description': 'md5:319e37ea5542293db37e1e13072fe330',
            'thumbnail': r're:https?://www\.filmarkivet\.se/wp-content/uploads/.+\.jpg',
        },
    }, {
        # Multiple HTML5 videos
        # https://github.com/ytdl-org/youtube-dl/pull/14107
        'url': 'https://www.dagbladet.no/nyheter/etter-ett-ars-planlegging-klaffet-endelig-alt---jeg-matte-ta-en-liten-dans/60413035',
        'info_dict': {
            'id': '60413035',
            'title': 'Etter ett års planlegging, klaffet endelig alt: - Jeg måtte ta en liten dans',
            'description': 'md5:bbb4e12e42e78609a74fd421b93b1239',
            'thumbnail': r're:https?://www\.dagbladet\.no/images/.+',
        },
        'playlist_count': 2,
    }, {
        # Cinerama Player
        # https://github.com/ytdl-org/youtube-dl/commit/501f13fbf3d1f7225f91e3e0ad008df2cd3219f1
        'url': 'https://www.abc.net.au/res/libraries/cinerama2/examples/single_clip.htm',
        'info_dict': {
            'id': 'single_clip',
            'title': 'Single Clip player examples',
        },
        'playlist_count': 3,
    }, {
        # FIXME: Improve extraction
        # Flowplayer
        # https://github.com/ytdl-org/youtube-dl/commit/4d805e063c6c4ffd557d7c7cb905a3ed9c926b08
        'url': 'https://flowplayer.com/resources/demos/standard-setup',
        'info_dict': {
            'id': 'playlist',
            'ext': 'mp4',
            'title': 'playlist',
            'duration': 13,
            'timestamp': 1539082175,
            'upload_date': '20181009',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # JW Player: YouTube
        # https://github.com/ytdl-org/youtube-dl/commit/a0f719854463c6f4226e4042dfa80c1b17154e1d
        'url': 'https://media.nationalarchives.gov.uk/index.php/webinar-using-discovery-national-archives-online-catalogue/',
        'info_dict': {
            'id': 'Mrj4DVp2zeA',
            'ext': 'mp4',
            'title': 'Using Discovery, The National Archives’ online catalogue',
            'age_limit': 0,
            'availability': 'unlisted',
            'categories': ['Education'],
            'channel': 'The National Archives UK',
            'channel_follower_count': int,
            'channel_id': 'UCUuzebc1yADDJEnOLA5P9xw',
            'channel_url': 'https://www.youtube.com/channel/UCUuzebc1yADDJEnOLA5P9xw',
            'chapters': 'count:13',
            'description': 'md5:a236581cd2449dd2df4f93412f3f01c6',
            'duration': 3066,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:5',
            'thumbnail': r're:https?://i\.ytimg\.com/vi/.+',
            'timestamp': 1423757117,
            'upload_date': '20150212',
            'uploader': 'The National Archives UK',
            'uploader_id': '@TheNationalArchivesUK',
            'uploader_url': 'https://www.youtube.com/@TheNationalArchivesUK',
            'view_count': int,
        },
        'add_ie': ['Youtube'],
    }, {
        # JW Player: Complex
        # https://github.com/ytdl-org/youtube-dl/commit/a4a554a79354981fcab55de8eaab7b95a40bbb48
        'url': 'https://www.indiedb.com/games/king-machine/videos',
        'info_dict': {
            'id': 'videos-1',
            'ext': 'mp4',
            'title': 'Videos & Audio - King Machine (1)',
            'description': 'Browse King Machine videos & audio for sweet media. Your eyes will thank you.',
            'thumbnail': r're:https?://media\.indiedb\.com/cache/images/.+\.jpg',
            '_old_archive_ids': ['generic videos'],
        },
    }, {
        # JW Player: JSON Feed URL
        # https://github.com/yt-dlp/yt-dlp/issues/1476
        'url': 'https://foodschmooze.org/',
        'info_dict': {
            'id': 'z00Frhnw',
            'ext': 'mp4',
            'title': 'Grilling Beef Tenderloin',
            'description': '',
            'duration': 392.0,
            'thumbnail': r're:https?://cdn\.jwplayer\.com/v2/media/.+',
            'timestamp': 1465313685,
            'upload_date': '20160607',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # JW Player: RTMP
        # https://github.com/ytdl-org/youtube-dl/issues/11993
        'url': 'http://www.suffolk.edu/sjc/live.php',
        'info_dict': {
            'id': 'live',
            'ext': 'flv',
            'title': 'Massachusetts Supreme Judicial Court Oral Arguments',
        },
        'skip': 'Invalid URL',
    }, {
        # KVS Player v7.3.3
        # kt_player.js?v=5.1.1
        'url': 'https://bogmedia.org/videos/21217/40-nochey-2016/',
        'md5': '94166bdb26b4cb1fb9214319a629fc51',
        'info_dict': {
            'id': '21217',
            'ext': 'mp4',
            'title': '40 ночей (2016) - BogMedia.org',
            'description': 'md5:4e6d7d622636eb7948275432eb256dc3',
            'display_id': '40-nochey-2016',
            'thumbnail': r're:https?://bogmedia\.org/contents/videos_screenshots/.+\.jpg',
        },
    }, {
        # KVS Player v7.7.11
        # kt_player.js?v=5.5.1
        # https://github.com/yt-dlp/yt-dlp/commit/a318f59d14792d25b2206c3f50181e03e8716db7
        'url': 'https://youix.com/video/leningrad-zoj/',
        'md5': '94f96ba95706dc3880812b27b7d8a2b8',
        'info_dict': {
            'id': '18485',
            'ext': 'mp4',
            'title': 'Клип: Ленинград - ЗОЖ скачать, смотреть онлайн | Youix.com',
            'display_id': 'leningrad-zoj',
            'thumbnail': r're:https?://youix\.com/contents/videos_screenshots/.+\.jpg',
        },
    }, {
        # KVS Player v7.10.3
        # kt_player.js?v=12
        # https://github.com/ytdl-org/youtube-dl/commit/fc2beab0e701c497a003f11fef5c0df54fba1da3
        'url': 'https://shooshtime.com/videos/346037/fresh-out-of-the-shower/',
        'md5': 'c9a97ad528607a4516d4df83a3aeb12c',
        'info_dict': {
            'id': '346037',
            'ext': 'mp4',
            'title': 'Fresh out of the shower - Shooshtime',
            'age_limit': 18,
            'description': 'md5:efd70fd3973f8750d285c743b910580a',
            'display_id': 'fresh-out-of-the-shower',
            'thumbnail': r're:https?://i\.shoosh\.co/contents/videos_screenshots/.+\.jpg',
        },
        'expected_warnings': ['Untested major version'],
    }, {
        # FIXME: Unable to extract flashvars
        # KVS Player v7.11.4
        # kt_player.js?v=2.11.5.1
        # https://github.com/yt-dlp/yt-dlp/commit/a318f59d14792d25b2206c3f50181e03e8716db7
        'url': 'https://www.kvs-demo.com/video/105/kelis-4th-of-july/',
        'info_dict': {
            'id': '105',
            'ext': 'mp4',
            'title': 'Kelis - 4th Of July',
        },
    }, {
        # KVS Player v7.11.4
        # kt_player.js?v=6.3.2
        # https://github.com/yt-dlp/yt-dlp/commit/a318f59d14792d25b2206c3f50181e03e8716db7
        'url': 'https://www.kvs-demo.com/embed/105/',
        'md5': '1ff84c70acaddbb03288c6cc5ee1879f',
        'info_dict': {
            'id': '105',
            'ext': 'mp4',
            'title': 'Kelis - 4th Of July / Embed Player',
            'display_id': 'kelis-4th-of-july',
            'thumbnail': r're:https?://www\.kvs-demo\.com/contents/videos_screenshots/.+\.jpg',
        },
    }, {
        # twitter:player:stream
        # https://github.com/ytdl-org/youtube-dl/commit/371ddb14fe651d4a1e5a8310d6d7c0e395cd92b0
        'url': 'https://beltzlaw.com/',
        'info_dict': {
            'id': 'beltzlaw-1',
            'ext': 'mp4',
            'title': str,
            'description': str,
            'thumbnail': r're:https?://beltzlaw\.com/wp-content/uploads/.+\.jpg',
            'timestamp': int,  # varies
            'upload_date': str,
            '_old_archive_ids': ['generic beltzlaw'],
        },
    }, {
        # twitter:player
        # https://github.com/ytdl-org/youtube-dl/commit/329179073b93e37ab76e759d1fe96d8f984367f3
        'url': 'https://cine.ar/',
        'md5': 'd3e33335e339f04008690118698dfd08',
        'info_dict': {
            'id': 'cine-1',
            'ext': 'webm',
            'title': 'CINE.AR (1)',
            'description': 'md5:a4e58f9e2291c940e485f34251898c4a',
            'thumbnail': r're:https?://cine\.ar/img/.+\.png',
            '_old_archive_ids': ['generic cine'],
        },
        'params': {'format': 'webm'},
    }, {
        # JSON-LD: multiple @type
        # https://github.com/yt-dlp/yt-dlp/commit/f3c0c77304bc0e5614a65c45629de22f067685ac
        'url': 'https://www.nu.nl/280161/video/hoe-een-bladvlo-dit-verwoestende-japanse-onkruid-moet-vernietigen.html',
        'info_dict': {
            'id': 'ipy2AcGL',
            'ext': 'mp4',
            'title': 'Hoe een bladvlo dit verwoestende Japanse onkruid moet vernietigen',
            'description': 'md5:6a9d644bab0dc2dc06849c2505d8383d',
            'duration': 111.0,
            'thumbnail': r're:https?://images\.nu\.nl/.+\.jpg',
            'timestamp': 1586584674,
            'upload_date': '20200411',
        },
        'params': {'extractor_args': {'generic': {'impersonate': ['chrome']}}},
    }, {
        # JSON-LD: unexpected @type
        # https://github.com/yt-dlp/yt-dlp/pull/5145
        'url': 'https://www.autoweek.nl/autotests/artikel/porsche-911-gt3-rs-rij-impressie-2/',
        'info_dict': {
            'id': 'porsche-911-gt3-rs-rij-impressie-2',
            'ext': 'mp4',
            'title': 'Test: Porsche 911 GT3 RS - AutoWeek',
            'description': 'md5:a17b5bd84288448d8f11b838505718fc',
            'direct': True,
            'thumbnail': r're:https?://images\.autoweek\.nl/.+',
            'timestamp': 1664920902,
            'upload_date': '20221004',
        },
        'params': {'extractor_args': {'generic': {'impersonate': ['chrome']}}},
    }, {
        # JSON-LD: VideoObject
        # https://github.com/ytdl-org/youtube-dl/commit/6e6b70d65f0681317c425bfe1e157f3474afbbe8
        'url': 'https://breezy.hr/',
        'info_dict': {
            'id': 'k6gl2kt2eq',
            'ext': 'mp4',
            'title': 'Breezy HR\'s ATS helps you find & hire employees sooner',
            'average_rating': 4.5,
            'description': 'md5:eee75fdd3044c538003f3be327ba01e1',
            'duration': 60.1,
            'thumbnail': r're:https?://cdn\.prod\.website-files\.com/.+\.webp',
            'timestamp': 1485734400,
            'upload_date': '20170130',
        },
    }, {
        # Video.js: VOD HLS
        # https://github.com/yt-dlp/yt-dlp/pull/6775
        'url': 'https://gist.githubusercontent.com/bashonly/2aae0862c50f4a4b84f220c315767208/raw/e3380d413749dabbe804c9c2d8fd9a45142475c7/videojs_hls_test.html',
        'info_dict': {
            'id': 'videojs_hls_test',
            'ext': 'mp4',
            'title': 'video',
            'duration': 1800,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Video.js: YouTube
        # https://github.com/ytdl-org/youtube-dl/commit/63d990d2859d0e981da2e416097655798334431b
        'url': 'https://ortcam.com/solidworks-%d1%83%d1%80%d0%be%d0%ba-6-%d0%bd%d0%b0%d1%81%d1%82%d1%80%d0%be%d0%b9%d0%ba%d0%b0-%d1%87%d0%b5%d1%80%d1%82%d0%b5%d0%b6%d0%b0_33f9b7351.html?vid=33f9b7351',
        'info_dict': {
            'id': 'yygqldloqIk',
            'ext': 'mp4',
            'title': 'SolidWorks. Урок 6 Настройка чертежа',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Education'],
            'channel': 'PROстое3D',
            'channel_follower_count': int,
            'channel_id': 'UCy91Bug3dERhbwGh2m2Ijng',
            'channel_url': 'https://www.youtube.com/channel/UCy91Bug3dERhbwGh2m2Ijng',
            'comment_count': int,
            'description': 'md5:baf95267792646afdbf030e4d06b2ab3',
            'duration': 1160,
            'heatmap': 'count:100',
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:17',
            'thumbnail': r're:https?://i\.ytimg\.com/vi/.+',
            'timestamp': 1363263144,
            'upload_date': '20130314',
            'uploader': 'PROстое3D',
            'uploader_id': '@PROstoe3D',
            'uploader_url': 'https://www.youtube.com/@PROstoe3D',
            'view_count': int,
        },
        'add_ie': ['Youtube'],
    }, {
        # Redirect
        # https://github.com/ytdl-org/youtube-dl/issues/413
        'url': 'https://www.google.com/url?rct=j&url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DcmQHVoWB5FY',
        'info_dict': {
            'id': 'cmQHVoWB5FY',
            'ext': 'mp4',
            'title': 'First Firefox OS phones side-by-side',
            'age_limit': 0,
            'availability': 'public',
            'categories': ['Entertainment'],
            'channel': 'The Verge',
            'channel_follower_count': int,
            'channel_id': 'UCddiUEpeqJcYeBxX1IVBKvQ',
            'channel_is_verified': True,
            'channel_url': 'https://www.youtube.com/channel/UCddiUEpeqJcYeBxX1IVBKvQ',
            'comment_count': int,
            'description': 'md5:7a676046ad24d9ea55cdde4a6657c5b3',
            'duration': 207,
            'like_count': int,
            'live_status': 'not_live',
            'media_type': 'video',
            'playable_in_embed': True,
            'tags': 'count:15',
            'thumbnail': r're:https?://i\.ytimg\.com/vi/.+',
            'timestamp': 1361738430,
            'upload_date': '20130224',
            'uploader': 'The Verge',
            'uploader_id': '@TheVerge',
            'uploader_url': 'https://www.youtube.com/@TheVerge',
            'view_count': int,
        },
        'add_ie': ['Youtube'],
    }]

    def report_following_redirect(self, new_url):
        """Report information extraction."""
        self._downloader.to_screen(f'[redirect] Following redirect to {new_url}')

    def report_detected(self, name, num=1, note=None):
        if num > 1:
            name += 's'
        elif not num:
            return
        else:
            num = 'a'

        self._downloader.write_debug(f'Identified {num} {name}{format_field(note, None, "; %s")}')

    def _extra_manifest_info(self, info, manifest_url):
        fragment_query = self._configuration_arg('fragment_query', [None], casesense=True)[0]
        if fragment_query is not None:
            info['extra_param_to_segment_url'] = (
                urllib.parse.urlparse(fragment_query).query or fragment_query
                or urllib.parse.urlparse(manifest_url).query or None)

        key_query = self._configuration_arg('key_query', [None], casesense=True)[0]
        if key_query is not None:
            info['extra_param_to_key_url'] = (
                urllib.parse.urlparse(key_query).query or key_query
                or urllib.parse.urlparse(manifest_url).query or None)

        def hex_or_none(value):
            return value if re.fullmatch(r'(0x)?[\da-f]+', value, re.IGNORECASE) else None

        info['hls_aes'] = traverse_obj(self._configuration_arg('hls_key', casesense=True), {
            'uri': (0, {url_or_none}), 'key': (0, {hex_or_none}), 'iv': (1, {hex_or_none}),
        }) or None

        variant_query = self._configuration_arg('variant_query', [None], casesense=True)[0]
        if variant_query is not None:
            query = urllib.parse.parse_qs(
                urllib.parse.urlparse(variant_query).query or variant_query
                or urllib.parse.urlparse(manifest_url).query)
            for fmt in self._downloader._get_formats(info):
                fmt['url'] = update_url_query(fmt['url'], query)

        # Attempt to detect live HLS or set VOD duration
        m3u8_format = next((f for f in self._downloader._get_formats(info)
                            if determine_protocol(f) == 'm3u8_native'), None)
        if m3u8_format:
            is_live = self._configuration_arg('is_live', [None])[0]
            if is_live is not None:
                info['live_status'] = 'not_live' if is_live == 'false' else 'is_live'
                return
            headers = m3u8_format.get('http_headers') or info.get('http_headers') or {}
            display_id = info.get('id')
            urlh = self._request_webpage(
                m3u8_format['url'], display_id, 'Checking m3u8 live status', errnote=False,
                headers={**headers, 'Accept-Encoding': 'identity'}, fatal=False)
            if urlh is False:
                return
            first_bytes = urlh.read(512)
            if not first_bytes.startswith(b'#EXTM3U'):
                return
            m3u8_doc = self._webpage_read_content(
                urlh, urlh.url, display_id, prefix=first_bytes, fatal=False, errnote=False)
            if not m3u8_doc:
                return
            duration = self._parse_m3u8_vod_duration(m3u8_doc, display_id)
            if not duration:
                info['live_status'] = 'is_live'
            info['duration'] = info.get('duration') or duration

    def _extract_rss(self, url, video_id, doc):
        NS_MAP = {
            'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
        }

        entries = []
        for it in doc.findall('./channel/item'):
            next_url = next(
                (e.attrib.get('url') for e in it.findall('./enclosure')),
                xpath_text(it, 'link', fatal=False))
            if not next_url:
                continue

            guid = try_call(lambda: it.find('guid').text)
            if guid:
                next_url = smuggle_url(next_url, {'force_videoid': guid})

            def itunes(key):
                return xpath_text(it, xpath_with_ns(f'./itunes:{key}', NS_MAP), default=None)

            entries.append({
                '_type': 'url_transparent',
                'url': next_url,
                'title': try_call(lambda: it.find('title').text),
                'description': xpath_text(it, 'description', default=None),
                'timestamp': unified_timestamp(xpath_text(it, 'pubDate', default=None)),
                'duration': parse_duration(itunes('duration')),
                'thumbnail': url_or_none(xpath_attr(it, xpath_with_ns('./itunes:image', NS_MAP), 'href')),
                'episode': itunes('title'),
                'episode_number': int_or_none(itunes('episode')),
                'season_number': int_or_none(itunes('season')),
                'age_limit': {'true': 18, 'yes': 18, 'false': 0, 'no': 0}.get((itunes('explicit') or '').lower()),
            })

        return {
            '_type': 'playlist',
            'id': url,
            'title': try_call(lambda: doc.find('./channel/title').text),
            'description': try_call(lambda: doc.find('./channel/description').text),
            'entries': entries,
        }

    @classmethod
    def _kvs_get_real_url(cls, video_url, license_code):
        if not video_url.startswith('function/0/'):
            return video_url  # not obfuscated

        parsed = urllib.parse.urlparse(video_url[len('function/0/'):])
        license_token = cls._kvs_get_license_token(license_code)
        urlparts = parsed.path.split('/')

        HASH_LENGTH = 32
        hash_ = urlparts[3][:HASH_LENGTH]
        indices = list(range(HASH_LENGTH))

        # Swap indices of hash according to the destination calculated from the license token
        accum = 0
        for src in reversed(range(HASH_LENGTH)):
            accum += license_token[src]
            dest = (src + accum) % HASH_LENGTH
            indices[src], indices[dest] = indices[dest], indices[src]

        urlparts[3] = ''.join(hash_[index] for index in indices) + urlparts[3][HASH_LENGTH:]
        return urllib.parse.urlunparse(parsed._replace(path='/'.join(urlparts)))

    @staticmethod
    def _kvs_get_license_token(license_code):
        license_code = license_code.replace('$', '')
        license_values = [int(char) for char in license_code]

        modlicense = license_code.replace('0', '1')
        center = len(modlicense) // 2
        fronthalf = int(modlicense[:center + 1])
        backhalf = int(modlicense[center:])
        modlicense = str(4 * abs(fronthalf - backhalf))[:center + 1]

        return [
            (license_values[index + offset] + current) % 10
            for index, current in enumerate(map(int, modlicense))
            for offset in range(4)
        ]

    def _extract_kvs(self, url, webpage, video_id):
        flashvars = self._search_json(
            r'(?s:<script\b[^>]*>.*?var\s+flashvars\s*=)',
            webpage, 'flashvars', video_id, transform_source=js_to_json)

        # extract the part after the last / as the display_id from the
        # canonical URL.
        display_id = self._search_regex(
            r'(?:<link href="https?://[^"]+/(.+?)/?" rel="canonical"\s*/?>'
            r'|<link rel="canonical" href="https?://[^"]+/(.+?)/?"\s*/?>)',
            webpage, 'display_id', fatal=False)
        title = self._html_search_regex(r'<(?:h1|title)>(?:Video: )?(.+?)</(?:h1|title)>', webpage, 'title')

        thumbnail = flashvars['preview_url']
        if thumbnail.startswith('//'):
            protocol, _, _ = url.partition('/')
            thumbnail = protocol + thumbnail

        url_keys = list(filter(re.compile(r'^video_(?:url|alt_url\d*)$').match, flashvars.keys()))
        formats = []
        for key in url_keys:
            if '/get_file/' not in flashvars[key]:
                continue
            format_id = flashvars.get(f'{key}_text', key)
            formats.append({
                'url': urljoin(url, self._kvs_get_real_url(flashvars[key], flashvars['license_code'])),
                'format_id': format_id,
                'ext': 'mp4',
                **(parse_resolution(format_id) or parse_resolution(flashvars[key])),
                'http_headers': {'Referer': url},
            })
            if not formats[-1].get('height'):
                formats[-1]['quality'] = 1

        return {
            'id': flashvars['video_id'],
            'display_id': display_id,
            'title': title,
            'thumbnail': urljoin(url, thumbnail),
            'formats': formats,
        }

    def _real_extract(self, url):
        if url.startswith('//'):
            return self.url_result(self.http_scheme() + url)

        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme:
            default_search = self.get_param('default_search')
            if default_search is None:
                default_search = 'fixup_error'

            if default_search in ('auto', 'auto_warning', 'fixup_error'):
                if re.match(r'[^\s/]+\.[^\s/]+/', url):
                    self.report_warning('The url doesn\'t specify the protocol, trying with https')
                    return self.url_result('https://' + url)
                elif default_search != 'fixup_error':
                    if default_search == 'auto_warning':
                        if re.match(r'^(?:url|URL)$', url):
                            raise ExtractorError(
                                f'Invalid URL:  {url!r} . Call yt-dlp like this:  yt-dlp -v "https://www.youtube.com/watch?v=BaW_jenozKc"  ',
                                expected=True)
                        else:
                            self.report_warning(
                                f'Falling back to youtube search for  {url} . Set --default-search "auto" to suppress this warning.')
                    return self.url_result('ytsearch:' + url)

            if default_search in ('error', 'fixup_error'):
                raise ExtractorError(f'{url!r} is not a valid URL', expected=True)
            else:
                if ':' not in default_search:
                    default_search += ':'
                return self.url_result(default_search + url)

        original_url = url
        url, smuggled_data = unsmuggle_url(url, {})
        force_videoid = None
        is_intentional = smuggled_data.get('to_generic')
        if 'force_videoid' in smuggled_data:
            force_videoid = smuggled_data['force_videoid']
            video_id = force_videoid
        else:
            video_id = self._generic_id(url)

        # Do not impersonate by default; see https://github.com/yt-dlp/yt-dlp/issues/11335
        impersonate = self._configuration_arg('impersonate', ['false'])
        if 'false' in impersonate:
            impersonate = None

        # Some webservers may serve compressed content of rather big size (e.g. gzipped flac)
        # making it impossible to download only chunk of the file (yet we need only 512kB to
        # test whether it's HTML or not). According to yt-dlp default Accept-Encoding
        # that will always result in downloading the whole file that is not desirable.
        # Therefore for extraction pass we have to override Accept-Encoding to any in order
        # to accept raw bytes and being able to download only a chunk.
        # It may probably better to solve this by checking Content-Type for application/octet-stream
        # after a HEAD request, but not sure if we can rely on this.
        try:
            full_response = self._request_webpage(url, video_id, headers=filter_dict({
                'Accept-Encoding': 'identity',
                'Referer': smuggled_data.get('referer'),
            }), impersonate=impersonate)
        except ExtractorError as e:
            if not (isinstance(e.cause, HTTPError) and e.cause.status == 403
                    and e.cause.response.get_header('cf-mitigated') == 'challenge'
                    and e.cause.response.extensions.get('impersonate') is None):
                raise
            cf_cookie_domain = traverse_obj(
                LenientSimpleCookie(e.cause.response.get_header('set-cookie')),
                ('__cf_bm', 'domain'))
            if cf_cookie_domain:
                self.write_debug(f'Clearing __cf_bm cookie for {cf_cookie_domain}')
                self.cookiejar.clear(domain=cf_cookie_domain, path='/', name='__cf_bm')
            msg = 'Got HTTP Error 403 caused by Cloudflare anti-bot challenge; '
            if not self._downloader._impersonate_target_available(ImpersonateTarget()):
                msg += ('see  https://github.com/yt-dlp/yt-dlp#impersonation  for '
                        'how to install the required impersonation dependency, and ')
            raise ExtractorError(
                f'{msg}try again with  --extractor-args "generic:impersonate"', expected=True)

        new_url = full_response.url
        if new_url != extract_basic_auth(url)[0]:
            self.report_following_redirect(new_url)
            if force_videoid:
                new_url = smuggle_url(new_url, {'force_videoid': force_videoid})
            return self.url_result(new_url)

        info_dict = {
            'id': video_id,
            'title': self._generic_title(url),
            'timestamp': unified_timestamp(full_response.headers.get('Last-Modified')),
        }

        # Check for direct link to a video
        content_type = full_response.headers.get('Content-Type', '').lower()
        m = re.match(r'(?P<type>audio|video|application(?=/(?:ogg$|(?:vnd\.apple\.|x-)?mpegurl)))/(?P<format_id>[^;\s]+)', content_type)
        if m:
            self.report_detected('direct video link')
            headers = filter_dict({'Referer': smuggled_data.get('referer')})
            format_id = str(m.group('format_id'))
            ext = determine_ext(url, default_ext=None) or urlhandle_detect_ext(full_response)
            subtitles = {}
            if format_id.endswith('mpegurl') or ext == 'm3u8':
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(url, video_id, 'mp4', headers=headers)
            elif format_id == 'f4m' or ext == 'f4m':
                formats = self._extract_f4m_formats(url, video_id, headers=headers)
            # Don't check for DASH/mpd here, do it later w/ first_bytes. Same number of requests either way
            else:
                formats = [{
                    'format_id': format_id,
                    'url': url,
                    'ext': ext,
                    'vcodec': 'none' if m.group('type') == 'audio' else None,
                }]
                info_dict['direct'] = True
            info_dict.update({
                'formats': formats,
                'subtitles': subtitles,
                'http_headers': headers or None,
            })
            self._extra_manifest_info(info_dict, url)
            return info_dict

        if not self.get_param('test', False) and not is_intentional:
            force = self.get_param('force_generic_extractor', False)
            self.report_warning('%s generic information extractor' % ('Forcing' if force else 'Falling back on'))

        first_bytes = full_response.read(512)

        # Is it an M3U playlist?
        if first_bytes.startswith(b'#EXTM3U'):
            self.report_detected('M3U playlist')
            info_dict['formats'], info_dict['subtitles'] = self._extract_m3u8_formats_and_subtitles(url, video_id, 'mp4')
            self._extra_manifest_info(info_dict, url)
            return info_dict

        # Maybe it's a direct link to a video?
        # Be careful not to download the whole thing!
        if not is_html(first_bytes):
            self.report_warning(
                'URL could be a direct video link, returning it as such.')
            ext = determine_ext(url)
            if ext not in _UnsafeExtensionError.ALLOWED_EXTENSIONS:
                ext = 'unknown_video'
            info_dict.update({
                'direct': True,
                'url': url,
                'ext': ext,
            })
            return info_dict

        webpage = self._webpage_read_content(
            full_response, url, video_id, prefix=first_bytes)

        if '<title>DPG Media Privacy Gate</title>' in webpage:
            webpage = self._download_webpage(url, video_id)

        self.report_extraction(video_id)

        # Is it an RSS feed, a SMIL file, an XSPF playlist or a MPD manifest?
        try:
            try:
                doc = compat_etree_fromstring(webpage)
            except xml.etree.ElementTree.ParseError:
                doc = compat_etree_fromstring(webpage.encode())
            if doc.tag == 'rss':
                self.report_detected('RSS feed')
                return self._extract_rss(url, video_id, doc)
            elif doc.tag == 'SmoothStreamingMedia':
                info_dict['formats'], info_dict['subtitles'] = self._parse_ism_formats_and_subtitles(doc, url)
                self.report_detected('ISM manifest')
                return info_dict
            elif re.match(r'^(?:{[^}]+})?smil$', doc.tag):
                smil = self._parse_smil(doc, url, video_id)
                self.report_detected('SMIL file')
                return smil
            elif doc.tag == '{http://xspf.org/ns/0/}playlist':
                self.report_detected('XSPF playlist')
                return self.playlist_result(
                    self._parse_xspf(
                        doc, video_id, xspf_url=url,
                        xspf_base_url=new_url),
                    video_id)
            elif re.match(r'(?i)^(?:{[^}]+})?MPD$', doc.tag):
                info_dict['formats'], info_dict['subtitles'] = self._parse_mpd_formats_and_subtitles(
                    doc,
                    # Do not use yt_dlp.utils.base_url here since it will raise on file:// URLs
                    mpd_base_url=update_url(new_url, query=None, fragment=None).rpartition('/')[0],
                    mpd_url=url)
                info_dict['live_status'] = 'is_live' if doc.get('type') == 'dynamic' else None
                self._extra_manifest_info(info_dict, url)
                self.report_detected('DASH manifest')
                return info_dict
            elif re.match(r'^{http://ns\.adobe\.com/f4m/[12]\.0}manifest$', doc.tag):
                info_dict['formats'] = self._parse_f4m_formats(doc, url, video_id)
                self.report_detected('F4M manifest')
                return info_dict
        except xml.etree.ElementTree.ParseError:
            pass

        info_dict.update({
            # it's tempting to parse this further, but you would
            # have to take into account all the variations like
            #   Video Title - Site Name
            #   Site Name | Video Title
            #   Video Title - Tagline | Site Name
            # and so on and so forth; it's just not practical
            'title': self._generic_title('', webpage, default='video'),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'age_limit': self._rta_search(webpage),
        })

        self._downloader.write_debug('Looking for embeds')
        embeds = list(self._extract_embeds(original_url, webpage, urlh=full_response, info_dict=info_dict))
        if len(embeds) == 1:
            return merge_dicts(embeds[0], info_dict)
        elif embeds:
            return self.playlist_result(embeds, **info_dict)
        raise UnsupportedError(url)

    def _extract_embeds(self, url, webpage, *, urlh=None, info_dict={}):
        """Returns an iterator of video entries"""
        info_dict = types.MappingProxyType(info_dict)  # Prevents accidental mutation
        video_id = traverse_obj(info_dict, 'display_id', 'id') or self._generic_id(url)
        url, smuggled_data = unsmuggle_url(url, {})
        actual_url = urlh.url if urlh else url

        # Sometimes embedded video player is hidden behind percent encoding
        # (e.g. https://github.com/ytdl-org/youtube-dl/issues/2448)
        # Unescaping the whole page allows to handle those cases in a generic way
        # FIXME: unescaping the whole page may break URLs, commenting out for now.
        # There probably should be a second run of generic extractor on unescaped webpage.
        # webpage = urllib.parse.unquote(webpage)

        embeds = []
        for ie in self._downloader._ies.values():
            if ie.ie_key() in smuggled_data.get('block_ies', []):
                continue
            gen = ie.extract_from_webpage(self._downloader, url, webpage)
            current_embeds = []
            try:
                while True:
                    current_embeds.append(next(gen))
            except self.StopExtraction:
                self.report_detected(f'{ie.IE_NAME} exclusive embed', len(current_embeds),
                                     embeds and 'discarding other embeds')
                return current_embeds
            except StopIteration:
                self.report_detected(f'{ie.IE_NAME} embed', len(current_embeds))
                embeds.extend(current_embeds)

        if embeds:
            return embeds

        jwplayer_data = self._find_jwplayer_data(
            webpage, video_id, transform_source=js_to_json)
        if jwplayer_data:
            if isinstance(jwplayer_data.get('playlist'), str):
                self.report_detected('JW Player playlist')
                return [self.url_result(jwplayer_data['playlist'], 'JWPlatform')]
            try:
                info = self._parse_jwplayer_data(
                    jwplayer_data, video_id, require_title=False, base_url=url)
                if traverse_obj(info, 'formats', ('entries', ..., 'formats')):
                    self.report_detected('JW Player data')
                    return [info]
            except ExtractorError:
                # See https://github.com/ytdl-org/youtube-dl/pull/16735
                pass

        # Video.js embed
        mobj = re.search(
            r'(?s)\bvideojs\s*\(.+?([a-zA-Z0-9_$]+)\.src\s*\(\s*((?:\[.+?\]|{.+?}))\s*\)\s*;',
            webpage)
        if mobj is not None:
            varname = mobj.group(1)
            sources = variadic(self._parse_json(
                mobj.group(2), video_id, transform_source=js_to_json, fatal=False) or [])
            formats, subtitles, src = [], {}, None
            for source in sources:
                src = source.get('src')
                if not src or not isinstance(src, str):
                    continue
                src = urllib.parse.urljoin(url, src)
                src_type = source.get('type')
                if isinstance(src_type, str):
                    src_type = src_type.lower()
                ext = determine_ext(src).lower()
                if src_type == 'video/youtube':
                    return [self.url_result(src, YoutubeIE.ie_key())]
                if src_type == 'application/dash+xml' or ext == 'mpd':
                    fmts, subs = self._extract_mpd_formats_and_subtitles(
                        src, video_id, mpd_id='dash', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
                elif src_type == 'application/x-mpegurl' or ext == 'm3u8':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(
                        src, video_id, 'mp4', entry_protocol='m3u8_native',
                        m3u8_id='hls', fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)

                if not formats:
                    formats.append({
                        'url': src,
                        'ext': (mimetype2ext(src_type)
                                or ext if ext in KNOWN_EXTENSIONS else 'mp4'),
                        'http_headers': {
                            'Referer': actual_url,
                        },
                    })
            # https://docs.videojs.com/player#addRemoteTextTrack
            # https://html.spec.whatwg.org/multipage/media.html#htmltrackelement
            for sub_match in re.finditer(rf'(?s){re.escape(varname)}' + r'\.addRemoteTextTrack\(({.+?})\s*,\s*(?:true|false)\)', webpage):
                sub = self._parse_json(
                    sub_match.group(1), video_id, transform_source=js_to_json, fatal=False) or {}
                sub_src = str_or_none(sub.get('src'))
                if not sub_src:
                    continue
                subtitles.setdefault(dict_get(sub, ('language', 'srclang')) or 'und', []).append({
                    'url': urllib.parse.urljoin(url, sub_src),
                    'name': sub.get('label'),
                    'http_headers': {
                        'Referer': actual_url,
                    },
                })
            if formats or subtitles:
                self.report_detected('video.js embed')
                info_dict = {'formats': formats, 'subtitles': subtitles}
                if formats:
                    self._extra_manifest_info(info_dict, src)
                return [info_dict]

        # Look for generic KVS player (before json-ld bc of some urls that break otherwise)
        found = self._search_regex((
            r'<script\b[^>]+?\bsrc\s*=\s*(["\'])https?://(?:(?!\1)[^?#])+/kt_player\.js\?v=(?P<ver>\d+(?:\.\d+)+)\1[^>]*>',
            r'kt_player\s*\(\s*(["\'])(?:(?!\1)[\w\W])+\1\s*,\s*(["\'])https?://(?:(?!\2)[^?#])+/kt_player\.swf\?v=(?P<ver>\d+(?:\.\d+)+)\2\s*,',
        ), webpage, 'KVS player', group='ver', default=False)
        if found:
            self.report_detected('KVS Player')
            if found.split('.')[0] not in ('4', '5', '6'):
                self.report_warning(f'Untested major version ({found}) in player engine - download may fail.')
            return [self._extract_kvs(url, webpage, video_id)]

        # Looking for http://schema.org/VideoObject
        json_ld = self._search_json_ld(webpage, video_id, default={})
        if json_ld.get('url') not in (url, None):
            self.report_detected('JSON LD')
            is_direct = json_ld.get('ext') not in (None, *MEDIA_EXTENSIONS.manifests)
            return [merge_dicts({
                '_type': 'video' if is_direct else 'url_transparent',
                'url': smuggle_url(json_ld['url'], {
                    'force_videoid': video_id,
                    'to_generic': True,
                    'referer': url,
                }),
            }, json_ld)]

        def check_video(vurl):
            if YoutubeIE.suitable(vurl):
                return True
            if RtmpIE.suitable(vurl):
                return True
            vpath = urllib.parse.urlparse(vurl).path
            vext = determine_ext(vpath, None)
            return vext not in (None, 'swf', 'png', 'jpg', 'srt', 'sbv', 'sub', 'vtt', 'ttml', 'js', 'xml')

        def filter_video(urls):
            return list(filter(check_video, urls))

        # Start with something easy: JW Player in SWFObject
        found = filter_video(re.findall(r'flashvars: [\'"](?:.*&)?file=(http[^\'"&]*)', webpage))
        if found:
            self.report_detected('JW Player in SFWObject')
        else:
            # Look for gorilla-vid style embedding
            found = filter_video(re.findall(r'''(?sx)
                (?:
                    jw_plugins|
                    JWPlayerOptions|
                    jwplayer\s*\(\s*["'][^'"]+["']\s*\)\s*\.setup
                )
                .*?
                ['"]?file['"]?\s*:\s*["\'](.*?)["\']''', webpage))
            if found:
                self.report_detected('JW Player embed')
        if not found:
            # Broaden the search a little bit
            found = filter_video(re.findall(r'[^A-Za-z0-9]?(?:file|source)=(http[^\'"&]*)', webpage))
            if found:
                self.report_detected('video file')
        if not found:
            # Broaden the findall a little bit: JWPlayer JS loader
            found = filter_video(re.findall(
                r'[^A-Za-z0-9]?(?:file|video_url)["\']?:\s*["\'](http(?![^\'"]+\.[0-9]+[\'"])[^\'"]+)["\']', webpage))
            if found:
                self.report_detected('JW Player JS loader')
        if not found:
            # Flow player
            found = filter_video(re.findall(r'''(?xs)
                flowplayer\("[^"]+",\s*
                    \{[^}]+?\}\s*,
                    \s*\{[^}]+? ["']?clip["']?\s*:\s*\{\s*
                        ["']?url["']?\s*:\s*["']([^"']+)["']
            ''', webpage))
            if found:
                self.report_detected('Flow Player')
        if not found:
            # Cinerama player
            found = re.findall(
                r"cinerama\.embedPlayer\(\s*\'[^']+\',\s*'([^']+)'", webpage)
            if found:
                self.report_detected('Cinerama player')
        if not found:
            # Try to find twitter cards info
            # twitter:player:stream should be checked before twitter:player since
            # it is expected to contain a raw stream (see
            # https://dev.twitter.com/cards/types/player#On_twitter.com_via_desktop_browser)
            found = filter_video(re.findall(
                r'<meta (?:property|name)="twitter:player:stream" (?:content|value)="(.+?)"', webpage))
            if found:
                self.report_detected('Twitter card')
        if not found:
            # We look for Open Graph info:
            # We have to match any number spaces between elements, some sites try to align them, e.g.: statigr.am
            m_video_type = re.findall(r'<meta.*?property="og:video:type".*?content="video/(.*?)"', webpage)
            # We only look in og:video if the MIME type is a video, don't try if it's a Flash player:
            if m_video_type is not None:
                found = filter_video(re.findall(r'<meta.*?property="og:(?:video|audio)".*?content="(.*?)"', webpage))
                if found:
                    self.report_detected('Open Graph video info')
        if not found:
            REDIRECT_REGEX = r'[0-9]{,2};\s*(?:URL|url)=\'?([^\'"]+)'
            found = re.search(
                r'(?i)<meta\s+(?=(?:[a-z-]+="[^"]+"\s+)*http-equiv="refresh")'
                rf'(?:[a-z-]+="[^"]+"\s+)*?content="{REDIRECT_REGEX}',
                webpage)
            if not found:
                # Look also in Refresh HTTP header
                refresh_header = urlh and urlh.headers.get('Refresh')
                if refresh_header:
                    found = re.search(REDIRECT_REGEX, refresh_header)
            if found:
                new_url = urllib.parse.urljoin(url, unescapeHTML(found.group(1)))
                if new_url != url:
                    self.report_following_redirect(new_url)
                    return [self.url_result(new_url)]
                else:
                    found = None

        if not found:
            # twitter:player is a https URL to iframe player that may or may not
            # be supported by yt-dlp thus this is checked the very last (see
            # https://dev.twitter.com/cards/types/player#On_twitter.com_via_desktop_browser)
            embed_url = self._html_search_meta('twitter:player', webpage, default=None)
            if embed_url and embed_url != url:
                self.report_detected('twitter:player iframe')
                return [self.url_result(embed_url)]

        if not found:
            return []

        domain_name = self._search_regex(r'^(?:https?://)?([^/]*)/.*', url, 'video uploader', default=None)

        entries = []
        for video_url in orderedSet(found):
            video_url = video_url.encode().decode('unicode-escape')
            video_url = unescapeHTML(video_url)
            video_url = video_url.replace('\\/', '/')
            video_url = urllib.parse.urljoin(url, video_url)
            video_id = urllib.parse.unquote(os.path.basename(video_url))

            # Sometimes, jwplayer extraction will result in a YouTube URL
            if YoutubeIE.suitable(video_url):
                entries.append(self.url_result(video_url, 'Youtube'))
                continue

            video_id = os.path.splitext(video_id)[0]
            headers = {
                'referer': actual_url,
            }

            entry_info_dict = {
                'id': video_id,
                'uploader': domain_name,
                'title': info_dict['title'],
                'age_limit': info_dict['age_limit'],
                'http_headers': headers,
            }

            if RtmpIE.suitable(video_url):
                entry_info_dict.update({
                    '_type': 'url_transparent',
                    'ie_key': RtmpIE.ie_key(),
                    'url': video_url,
                })
                entries.append(entry_info_dict)
                continue

            ext = determine_ext(video_url)
            if ext == 'smil':
                entry_info_dict = {**self._extract_smil_info(video_url, video_id), **entry_info_dict}
            elif ext == 'xspf':
                return [self._extract_xspf_playlist(video_url, video_id)]
            elif ext == 'm3u8':
                entry_info_dict['formats'], entry_info_dict['subtitles'] = self._extract_m3u8_formats_and_subtitles(video_url, video_id, ext='mp4', headers=headers)
                self._extra_manifest_info(entry_info_dict, video_url)
            elif ext == 'mpd':
                entry_info_dict['formats'], entry_info_dict['subtitles'] = self._extract_mpd_formats_and_subtitles(video_url, video_id, headers=headers)
                self._extra_manifest_info(entry_info_dict, video_url)
            elif ext == 'f4m':
                entry_info_dict['formats'] = self._extract_f4m_formats(video_url, video_id, headers=headers)
            elif re.search(r'(?i)\.(?:ism|smil)/manifest', video_url) and video_url != url:
                # Just matching .ism/manifest is not enough to be reliably sure
                # whether it's actually an ISM manifest or some other streaming
                # manifest since there are various streaming URL formats
                # possible (see [1]) as well as some other shenanigans like
                # .smil/manifest URLs that actually serve an ISM (see [2]) and
                # so on.
                # Thus the most reasonable way to solve this is to delegate
                # to generic extractor in order to look into the contents of
                # the manifest itself.
                # 1. https://azure.microsoft.com/en-us/documentation/articles/media-services-deliver-content-overview/#streaming-url-formats
                # 2. https://svs.itworkscdn.net/lbcivod/smil:itwfcdn/lbci/170976.smil/Manifest
                entry_info_dict = self.url_result(
                    smuggle_url(video_url, {'to_generic': True}),
                    GenericIE.ie_key())
            else:
                entry_info_dict['url'] = video_url

            entries.append(entry_info_dict)

        if len(entries) > 1:
            for num, e in enumerate(entries, start=1):
                # 'url' results don't have a title
                if e.get('title') is not None:
                    e['title'] = '{} ({})'.format(e['title'], num)
        return entries
