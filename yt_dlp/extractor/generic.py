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
    _TESTS = [
        # Direct link to a video
        {
            'url': 'http://media.w3.org/2010/05/sintel/trailer.mp4',
            'md5': '67d406c2bcb6af27fa886f31aa934bbe',
            'info_dict': {
                'id': 'trailer',
                'ext': 'mp4',
                'title': 'trailer',
                'upload_date': '20100513',
                'direct': True,
                'timestamp': 1273772943.0,
            },
        },
        # Direct link to media delivered compressed (until Accept-Encoding is *)
        {
            'url': 'http://calimero.tk/muzik/FictionJunction-Parallel_Hearts.flac',
            'md5': '128c42e68b13950268b648275386fc74',
            'info_dict': {
                'id': 'FictionJunction-Parallel_Hearts',
                'ext': 'flac',
                'title': 'FictionJunction-Parallel_Hearts',
                'upload_date': '20140522',
            },
            'expected_warnings': [
                'URL could be a direct video link, returning it as such.',
            ],
            'skip': 'URL invalid',
        },
        # Direct download with broken HEAD
        {
            'url': 'http://ai-radio.org:8000/radio.opus',
            'info_dict': {
                'id': 'radio',
                'ext': 'opus',
                'title': 'radio',
            },
            'params': {
                'skip_download': True,  # infinite live stream
            },
            'expected_warnings': [
                r'501.*Not Implemented',
                r'400.*Bad Request',
            ],
        },
        # Direct link with incorrect MIME type
        {
            'url': 'http://ftp.nluug.nl/video/nluug/2014-11-20_nj14/zaal-2/5_Lennart_Poettering_-_Systemd.webm',
            'md5': '4ccbebe5f36706d85221f204d7eb5913',
            'info_dict': {
                'url': 'http://ftp.nluug.nl/video/nluug/2014-11-20_nj14/zaal-2/5_Lennart_Poettering_-_Systemd.webm',
                'id': '5_Lennart_Poettering_-_Systemd',
                'ext': 'webm',
                'title': '5_Lennart_Poettering_-_Systemd',
                'upload_date': '20141120',
                'direct': True,
                'timestamp': 1416498816.0,
            },
            'expected_warnings': [
                'URL could be a direct video link, returning it as such.',
            ],
        },
        # RSS feed
        {
            'url': 'http://phihag.de/2014/youtube-dl/rss2.xml',
            'info_dict': {
                'id': 'https://phihag.de/2014/youtube-dl/rss2.xml',
                'title': 'Zero Punctuation',
                'description': 're:.*groundbreaking video review series.*',
            },
            'playlist_mincount': 11,
        },
        # RSS feed with enclosure
        {
            'url': 'http://podcastfeeds.nbcnews.com/audio/podcast/MSNBC-MADDOW-NETCAST-M4V.xml',
            'info_dict': {
                'id': 'http://podcastfeeds.nbcnews.com/nbcnews/video/podcast/MSNBC-MADDOW-NETCAST-M4V.xml',
                'title': 'MSNBC Rachel Maddow (video)',
                'description': 're:.*her unique approach to storytelling.*',
            },
            'playlist': [{
                'info_dict': {
                    'ext': 'mov',
                    'id': 'pdv_maddow_netcast_mov-12-03-2020-223726',
                    'title': 'MSNBC Rachel Maddow (video) - 12-03-2020-223726',
                    'description': 're:.*her unique approach to storytelling.*',
                    'upload_date': '20201204',
                },
            }],
            'skip': 'Dead link',
        },
        # RSS feed with item with description and thumbnails
        {
            'url': 'https://anchor.fm/s/dd00e14/podcast/rss',
            'info_dict': {
                'id': 'https://anchor.fm/s/dd00e14/podcast/rss',
                'title': 're:.*100% Hydrogen.*',
                'description': 're:.*In this episode.*',
            },
            'playlist': [{
                'info_dict': {
                    'ext': 'm4a',
                    'id': '818a5d38-01cd-152f-2231-ee479677fa82',
                    'title': 're:Hydrogen!',
                    'description': 're:.*In this episode we are going.*',
                    'timestamp': 1567977776,
                    'upload_date': '20190908',
                    'duration': 423,
                    'thumbnail': r're:^https?://.*\.jpg$',
                    'episode_number': 1,
                    'season_number': 1,
                    'age_limit': 0,
                    'season': 'Season 1',
                    'direct': True,
                    'episode': 'Episode 1',
                },
            }],
            'params': {
                'skip_download': True,
            },
        },
        # RSS feed with enclosures and unsupported link URLs
        {
            'url': 'http://www.hellointernet.fm/podcast?format=rss',
            'info_dict': {
                'id': 'http://www.hellointernet.fm/podcast?format=rss',
                'description': 'CGP Grey and Brady Haran talk about YouTube, life, work, whatever.',
                'title': 'Hello Internet',
            },
            'playlist_mincount': 100,
        },
        # RSS feed with guid
        {
            'url': 'https://www.omnycontent.com/d/playlist/a7b4f8fe-59d9-4afc-a79a-a90101378abf/bf2c1d80-3656-4449-9d00-a903004e8f84/efbff746-e7c1-463a-9d80-a903004e8f8f/podcast.rss',
            'info_dict': {
                'id': 'https://www.omnycontent.com/d/playlist/a7b4f8fe-59d9-4afc-a79a-a90101378abf/bf2c1d80-3656-4449-9d00-a903004e8f84/efbff746-e7c1-463a-9d80-a903004e8f8f/podcast.rss',
                'description': 'md5:be809a44b63b0c56fb485caf68685520',
                'title': 'The Little Red Podcast',
            },
            'playlist_mincount': 76,
        },
        # SMIL from http://videolectures.net/promogram_igor_mekjavic_eng
        {
            'url': 'http://videolectures.net/promogram_igor_mekjavic_eng/video/1/smil.xml',
            'info_dict': {
                'id': 'smil',
                'ext': 'mp4',
                'title': 'Automatics, robotics and biocybernetics',
                'description': 'md5:815fc1deb6b3a2bff99de2d5325be482',
                'upload_date': '20130627',
                'formats': 'mincount:16',
                'subtitles': 'mincount:1',
            },
            'params': {
                'force_generic_extractor': True,
                'skip_download': True,
            },
        },
        # SMIL from http://www1.wdr.de/mediathek/video/livestream/index.html
        {
            'url': 'http://metafilegenerator.de/WDR/WDR_FS/hds/hds.smil',
            'info_dict': {
                'id': 'hds',
                'ext': 'flv',
                'title': 'hds',
                'formats': 'mincount:1',
            },
            'params': {
                'skip_download': True,
            },
        },
        # SMIL from https://www.restudy.dk/video/play/id/1637
        {
            'url': 'https://www.restudy.dk/awsmedia/SmilDirectory/video_1637.xml',
            'info_dict': {
                'id': 'video_1637',
                'ext': 'flv',
                'title': 'video_1637',
                'formats': 'mincount:3',
            },
            'params': {
                'skip_download': True,
            },
        },
        # SMIL from http://adventure.howstuffworks.com/5266-cool-jobs-iditarod-musher-video.htm
        {
            'url': 'http://services.media.howstuffworks.com/videos/450221/smil-service.smil',
            'info_dict': {
                'id': 'smil-service',
                'ext': 'flv',
                'title': 'smil-service',
                'formats': 'mincount:1',
            },
            'params': {
                'skip_download': True,
            },
        },
        # SMIL from http://new.livestream.com/CoheedandCambria/WebsterHall/videos/4719370
        {
            'url': 'http://api.new.livestream.com/accounts/1570303/events/1585861/videos/4719370.smil',
            'info_dict': {
                'id': '4719370',
                'ext': 'mp4',
                'title': '571de1fd-47bc-48db-abf9-238872a58d1f',
                'formats': 'mincount:3',
            },
            'params': {
                'skip_download': True,
            },
        },
        # XSPF playlist from http://www.telegraaf.nl/tv/nieuws/binnenland/24353229/__Tikibad_ontruimd_wegens_brand__.html
        {
            'url': 'http://www.telegraaf.nl/xml/playlist/2015/8/7/mZlp2ctYIUEB.xspf',
            'info_dict': {
                'id': 'mZlp2ctYIUEB',
                'ext': 'mp4',
                'title': 'Tikibad ontruimd wegens brand',
                'description': 'md5:05ca046ff47b931f9b04855015e163a4',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 33,
            },
            'params': {
                'skip_download': True,
            },
            'skip': '404 Not Found',
        },
        # MPD from http://dash-mse-test.appspot.com/media.html
        {
            'url': 'http://yt-dash-mse-test.commondatastorage.googleapis.com/media/car-20120827-manifest.mpd',
            'md5': '4b57baab2e30d6eb3a6a09f0ba57ef53',
            'info_dict': {
                'id': 'car-20120827-manifest',
                'ext': 'mp4',
                'title': 'car-20120827-manifest',
                'formats': 'mincount:9',
                'upload_date': '20130904',
                'timestamp': 1378272859.0,
            },
        },
        # m3u8 served with Content-Type: audio/x-mpegURL; charset=utf-8
        {
            'url': 'http://once.unicornmedia.com/now/master/playlist/bb0b18ba-64f5-4b1b-a29f-0ac252f06b68/77a785f3-5188-4806-b788-0893a61634ed/93677179-2d99-4ef4-9e17-fe70d49abfbf/content.m3u8',
            'info_dict': {
                'id': 'content',
                'ext': 'mp4',
                'title': 'content',
                'formats': 'mincount:8',
            },
            'params': {
                # m3u8 downloads
                'skip_download': True,
            },
            'skip': 'video gone',
        },
        # m3u8 served with Content-Type: text/plain
        {
            'url': 'http://www.nacentapps.com/m3u8/index.m3u8',
            'info_dict': {
                'id': 'index',
                'ext': 'mp4',
                'title': 'index',
                'upload_date': '20140720',
                'formats': 'mincount:11',
            },
            'params': {
                # m3u8 downloads
                'skip_download': True,
            },
            'skip': 'video gone',
        },
        # google redirect
        {
            'url': 'http://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=1&cad=rja&ved=0CCUQtwIwAA&url=http%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DcmQHVoWB5FY&ei=F-sNU-LLCaXk4QT52ICQBQ&usg=AFQjCNEw4hL29zgOohLXvpJ-Bdh2bils1Q&bvm=bv.61965928,d.bGE',
            'info_dict': {
                'id': 'cmQHVoWB5FY',
                'ext': 'mp4',
                'upload_date': '20130224',
                'uploader_id': '@TheVerge',
                'description': r're:^Chris Ziegler takes a look at the\.*',
                'uploader': 'The Verge',
                'title': 'First Firefox OS phones side-by-side',
            },
            'params': {
                'skip_download': False,
            },
        },
        {
            # redirect in Refresh HTTP header
            'url': 'https://www.facebook.com/l.php?u=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DpO8h3EaFRdo&h=TAQHsoToz&enc=AZN16h-b6o4Zq9pZkCCdOLNKMN96BbGMNtcFwHSaazus4JHT_MFYkAA-WARTX2kvsCIdlAIyHZjl6d33ILIJU7Jzwk_K3mcenAXoAzBNoZDI_Q7EXGDJnIhrGkLXo_LJ_pAa2Jzbx17UHMd3jAs--6j2zaeto5w9RTn8T_1kKg3fdC5WPX9Dbb18vzH7YFX0eSJmoa6SP114rvlkw6pkS1-T&s=1',
            'info_dict': {
                'id': 'pO8h3EaFRdo',
                'ext': 'mp4',
                'title': 'Tripeo Boiler Room x Dekmantel Festival DJ Set',
                'description': 'md5:6294cc1af09c4049e0652b51a2df10d5',
                'upload_date': '20150917',
                'uploader_id': 'brtvofficial',
                'uploader': 'Boiler Room',
            },
            'params': {
                'skip_download': False,
            },
        },
        {
            'url': 'http://www.hodiho.fr/2013/02/regis-plante-sa-jeep.html',
            'md5': '85b90ccc9d73b4acd9138d3af4c27f89',
            'info_dict': {
                'id': '13601338388002',
                'ext': 'mp4',
                'uploader': 'www.hodiho.fr',
                'title': 'R\u00e9gis plante sa Jeep',
            },
        },
        # bandcamp page with custom domain
        {
            'add_ie': ['Bandcamp'],
            'url': 'http://bronyrock.com/track/the-pony-mash',
            'info_dict': {
                'id': '3235767654',
                'ext': 'mp3',
                'title': 'The Pony Mash',
                'uploader': 'M_Pallante',
            },
            'skip': 'There is a limit of 200 free downloads / month for the test song',
        },
        # embed.ly video
        {
            'url': 'http://www.tested.com/science/weird/460206-tested-grinding-coffee-2000-frames-second/',
            'info_dict': {
                'id': '9ODmcdjQcHQ',
                'ext': 'mp4',
                'title': 'Tested: Grinding Coffee at 2000 Frames Per Second',
                'upload_date': '20140225',
                'description': 'md5:06a40fbf30b220468f1e0957c0f558ff',
                'uploader': 'Tested',
                'uploader_id': 'testedcom',
            },
            # No need to test YoutubeIE here
            'params': {
                'skip_download': True,
            },
        },
        # funnyordie embed
        {
            'url': 'http://www.theguardian.com/world/2014/mar/11/obama-zach-galifianakis-between-two-ferns',
            'info_dict': {
                'id': '18e820ec3f',
                'ext': 'mp4',
                'title': 'Between Two Ferns with Zach Galifianakis: President Barack Obama',
                'description': 'Episode 18: President Barack Obama sits down with Zach Galifianakis for his most memorable interview yet.',
            },
            # HEAD requests lead to endless 301, while GET is OK
            'expected_warnings': ['301'],
        },
        # RUTV embed
        {
            'url': 'http://www.rg.ru/2014/03/15/reg-dfo/anklav-anons.html',
            'info_dict': {
                'id': '776940',
                'ext': 'mp4',
                'title': 'Охотское море стало целиком российским',
                'description': 'md5:5ed62483b14663e2a95ebbe115eb8f43',
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        # TVC embed
        {
            'url': 'http://sch1298sz.mskobr.ru/dou_edu/karamel_ki/filial_galleries/video/iframe_src_http_tvc_ru_video_iframe_id_55304_isplay_false_acc_video_id_channel_brand_id_11_show_episodes_episode_id_32307_frameb/',
            'info_dict': {
                'id': '55304',
                'ext': 'mp4',
                'title': 'Дошкольное воспитание',
            },
        },
        # SportBox embed
        {
            'url': 'http://www.vestifinance.ru/articles/25753',
            'info_dict': {
                'id': '25753',
                'title': 'Прямые трансляции с Форума-выставки "Госзаказ-2013"',
            },
            'playlist': [{
                'info_dict': {
                    'id': '370908',
                    'title': 'Госзаказ. День 3',
                    'ext': 'mp4',
                },
            }, {
                'info_dict': {
                    'id': '370905',
                    'title': 'Госзаказ. День 2',
                    'ext': 'mp4',
                },
            }, {
                'info_dict': {
                    'id': '370902',
                    'title': 'Госзаказ. День 1',
                    'ext': 'mp4',
                },
            }],
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        # Myvi.ru embed
        {
            'url': 'http://www.kinomyvi.tv/news/detail/Pervij-dublirovannij-trejler--Uzhastikov-_nOw1',
            'info_dict': {
                'id': 'f4dafcad-ff21-423d-89b5-146cfd89fa1e',
                'ext': 'mp4',
                'title': 'Ужастики, русский трейлер (2015)',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 153,
            },
            'skip': 'Site dead',
        },
        # XHamster embed
        {
            'url': 'http://www.numisc.com/forum/showthread.php?11696-FM15-which-pumiscer-was-this-%28-vid-%29-%28-alfa-as-fuck-srx-%29&s=711f5db534502e22260dec8c5e2d66d8',
            'info_dict': {
                'id': 'showthread',
                'title': '[NSFL] [FM15] which pumiscer was this ( vid ) ( alfa as fuck srx )',
            },
            'playlist_mincount': 7,
            # This forum does not allow <iframe> syntaxes anymore
            # Now HTML tags are displayed as-is
            'skip': 'No videos on this page',
        },
        # Embedded TED video
        {
            'url': 'http://en.support.wordpress.com/videos/ted-talks/',
            'md5': '65fdff94098e4a607385a60c5177c638',
            'info_dict': {
                'id': '1969',
                'ext': 'mp4',
                'title': 'Hidden miracles of the natural world',
                'uploader': 'Louie Schwartzberg',
                'description': 'md5:8145d19d320ff3e52f28401f4c4283b9',
            },
        },
        # nowvideo embed hidden behind percent encoding
        {
            'url': 'http://www.waoanime.tv/the-super-dimension-fortress-macross-episode-1/',
            'md5': '2baf4ddd70f697d94b1c18cf796d5107',
            'info_dict': {
                'id': '06e53103ca9aa',
                'ext': 'flv',
                'title': 'Macross Episode 001  Watch Macross Episode 001 onl',
                'description': 'No description',
            },
        },
        # arte embed
        {
            'url': 'http://www.tv-replay.fr/redirection/20-03-14/x-enius-arte-10753389.html',
            'md5': '7653032cbb25bf6c80d80f217055fa43',
            'info_dict': {
                'id': '048195-004_PLUS7-F',
                'ext': 'flv',
                'title': 'X:enius',
                'description': 'md5:d5fdf32ef6613cdbfd516ae658abf168',
                'upload_date': '20140320',
            },
            'params': {
                'skip_download': 'Requires rtmpdump',
            },
            'skip': 'video gone',
        },
        # francetv embed
        {
            'url': 'http://www.tsprod.com/replay-du-concert-alcaline-de-calogero',
            'info_dict': {
                'id': 'EV_30231',
                'ext': 'mp4',
                'title': 'Alcaline, le concert avec Calogero',
                'description': 'md5:61f08036dcc8f47e9cfc33aed08ffaff',
                'upload_date': '20150226',
                'timestamp': 1424989860,
                'duration': 5400,
            },
            'params': {
                # m3u8 downloads
                'skip_download': True,
            },
            'expected_warnings': [
                'Forbidden',
            ],
        },
        # Condé Nast embed
        {
            'url': 'http://www.wired.com/2014/04/honda-asimo/',
            'md5': 'ba0dfe966fa007657bd1443ee672db0f',
            'info_dict': {
                'id': '53501be369702d3275860000',
                'ext': 'mp4',
                'title': 'Honda’s  New Asimo Robot Is More Human Than Ever',
            },
        },
        # Dailymotion embed
        {
            'url': 'http://www.spi0n.com/zap-spi0n-com-n216/',
            'md5': '441aeeb82eb72c422c7f14ec533999cd',
            'info_dict': {
                'id': 'k2mm4bCdJ6CQ2i7c8o2',
                'ext': 'mp4',
                'title': 'Le Zap de Spi0n n°216 - Zapping du Web',
                'description': 'md5:faf028e48a461b8b7fad38f1e104b119',
                'uploader': 'Spi0n',
                'uploader_id': 'xgditw',
                'upload_date': '20140425',
                'timestamp': 1398441542,
            },
            'add_ie': ['Dailymotion'],
        },
        # DailyMail embed
        {
            'url': 'http://www.bumm.sk/krimi/2017/07/05/biztonsagi-kamera-buktatta-le-az-agg-ferfit-utlegelo-apolot',
            'info_dict': {
                'id': '1495629',
                'ext': 'mp4',
                'title': 'Care worker punches elderly dementia patient in head 11 times',
                'description': 'md5:3a743dee84e57e48ec68bf67113199a5',
            },
            'add_ie': ['DailyMail'],
            'params': {
                'skip_download': True,
            },
        },
        # YouTube embed
        {
            'url': 'http://www.badzine.de/ansicht/datum/2014/06/09/so-funktioniert-die-neue-englische-badminton-liga.html',
            'info_dict': {
                'id': 'FXRb4ykk4S0',
                'ext': 'mp4',
                'title': 'The NBL Auction 2014',
                'uploader': 'BADMINTON England',
                'uploader_id': 'BADMINTONEvents',
                'upload_date': '20140603',
                'description': 'md5:9ef128a69f1e262a700ed83edb163a73',
            },
            'add_ie': ['Youtube'],
            'params': {
                'skip_download': True,
            },
        },
        # MTVServices embed
        {
            'url': 'http://www.vulture.com/2016/06/new-key-peele-sketches-released.html',
            'md5': 'ca1aef97695ef2c1d6973256a57e5252',
            'info_dict': {
                'id': '769f7ec0-0692-4d62-9b45-0d88074bffc1',
                'ext': 'mp4',
                'title': 'Key and Peele|October 10, 2012|2|203|Liam Neesons - Uncensored',
                'description': 'Two valets share their love for movie star Liam Neesons.',
                'timestamp': 1349922600,
                'upload_date': '20121011',
            },
        },
        # YouTube embed via <data-embed-url="">
        {
            'url': 'https://play.google.com/store/apps/details?id=com.gameloft.android.ANMP.GloftA8HM',
            'info_dict': {
                'id': '4vAffPZIT44',
                'ext': 'mp4',
                'title': 'Asphalt 8: Airborne - Update - Welcome to Dubai!',
                'uploader': 'Gameloft',
                'uploader_id': 'gameloft',
                'upload_date': '20140828',
                'description': 'md5:c80da9ed3d83ae6d1876c834de03e1c4',
            },
            'params': {
                'skip_download': True,
            },
        },
        # Flowplayer
        {
            'url': 'http://www.handjobhub.com/video/busty-blonde-siri-tit-fuck-while-wank-6313.html',
            'md5': '9d65602bf31c6e20014319c7d07fba27',
            'info_dict': {
                'id': '5123ea6d5e5a7',
                'ext': 'mp4',
                'age_limit': 18,
                'uploader': 'www.handjobhub.com',
                'title': 'Busty Blonde Siri Tit Fuck While Wank at HandjobHub.com',
            },
        },
        # MLB embed
        {
            'url': 'http://umpire-empire.com/index.php/topic/58125-laz-decides-no-thats-low/',
            'md5': '96f09a37e44da40dd083e12d9a683327',
            'info_dict': {
                'id': '33322633',
                'ext': 'mp4',
                'title': 'Ump changes call to ball',
                'description': 'md5:71c11215384298a172a6dcb4c2e20685',
                'duration': 48,
                'timestamp': 1401537900,
                'upload_date': '20140531',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        },
        # Wistia standard embed (async)
        {
            'url': 'https://www.getdrip.com/university/brennan-dunn-drip-workshop/',
            'info_dict': {
                'id': '807fafadvk',
                'ext': 'mp4',
                'title': 'Drip Brennan Dunn Workshop',
                'description': 'a JV Webinars video from getdrip-1',
                'duration': 4986.95,
                'timestamp': 1463607249,
                'upload_date': '20160518',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'webpage 404 not found',
        },
        # Soundcloud embed
        {
            'url': 'http://nakedsecurity.sophos.com/2014/10/29/sscc-171-are-you-sure-that-1234-is-a-bad-password-podcast/',
            'info_dict': {
                'id': '174391317',
                'ext': 'mp3',
                'description': 'md5:ff867d6b555488ad3c52572bb33d432c',
                'uploader': 'Sophos Security',
                'title': 'Chet Chat 171 - Oct 29, 2014',
                'upload_date': '20141029',
            },
        },
        # Soundcloud multiple embeds
        {
            'url': 'http://www.guitarplayer.com/lessons/1014/legato-workout-one-hour-to-more-fluid-performance---tab/52809',
            'info_dict': {
                'id': '52809',
                'title': 'Guitar Essentials: Legato Workout—One-Hour to Fluid Performance  | TAB + AUDIO',
            },
            'playlist_mincount': 7,
        },
        # TuneIn station embed
        {
            'url': 'http://radiocnrv.com/promouvoir-radio-cnrv/',
            'info_dict': {
                'id': '204146',
                'ext': 'mp3',
                'title': 'CNRV',
                'location': 'Paris, France',
                'is_live': True,
            },
            'params': {
                # Live stream
                'skip_download': True,
            },
        },
        # Livestream embed
        {
            'url': 'http://www.esa.int/Our_Activities/Space_Science/Rosetta/Philae_comet_touch-down_webcast',
            'info_dict': {
                'id': '67864563',
                'ext': 'flv',
                'upload_date': '20141112',
                'title': 'Rosetta #CometLanding webcast HL 10',
            },
        },
        # Another Livestream embed, without 'new.' in URL
        {
            'url': 'https://www.freespeech.org/',
            'info_dict': {
                'id': '123537347',
                'ext': 'mp4',
                'title': 're:^FSTV [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            },
            'params': {
                # Live stream
                'skip_download': True,
            },
        },
        # LazyYT
        {
            'url': 'https://skiplagged.com/',
            'info_dict': {
                'id': 'skiplagged',
                'title': 'Skiplagged: The smart way to find cheap flights',
            },
            'playlist_mincount': 1,
            'add_ie': ['Youtube'],
        },
        # Libsyn embed
        {
            'url': 'http://undergroundwellness.com/podcasts/306-5-steps-to-permanent-gut-healing/',
            'info_dict': {
                'id': '3793998',
                'ext': 'mp3',
                'upload_date': '20141126',
                'title': 'Underground Wellness Radio - Jack Tips: 5 Steps to Permanent Gut Healing',
                'thumbnail': 'https://assets.libsyn.com/secure/item/3793998/?height=90&width=90',
                'duration': 3989.0,
            },
        },
        # Cinerama player
        {
            'url': 'http://www.abc.net.au/7.30/content/2015/s4164797.htm',
            'info_dict': {
                'id': '730m_DandD_1901_512k',
                'ext': 'mp4',
                'uploader': 'www.abc.net.au',
                'title': 'Game of Thrones with dice - Dungeons and Dragons fantasy role-playing game gets new life - 19/01/2015',
            },
        },
        # embedded viddler video
        {
            'url': 'http://deadspin.com/i-cant-stop-watching-john-wall-chop-the-nuggets-with-th-1681801597',
            'info_dict': {
                'id': '4d03aad9',
                'ext': 'mp4',
                'uploader': 'deadspin',
                'title': 'WALL-TO-GORTAT',
                'timestamp': 1422285291,
                'upload_date': '20150126',
            },
            'add_ie': ['Viddler'],
        },
        # Libsyn embed
        {
            'url': 'http://thedailyshow.cc.com/podcast/episodetwelve',
            'info_dict': {
                'id': '3377616',
                'ext': 'mp3',
                'title': "The Daily Show Podcast without Jon Stewart - Episode 12: Bassem Youssef: Egypt's Jon Stewart",
                'description': 'md5:601cb790edd05908957dae8aaa866465',
                'upload_date': '20150220',
            },
            'skip': 'All The Daily Show URLs now redirect to http://www.cc.com/shows/',
        },
        # jwplayer YouTube
        {
            'url': 'http://media.nationalarchives.gov.uk/index.php/webinar-using-discovery-national-archives-online-catalogue/',
            'info_dict': {
                'id': 'Mrj4DVp2zeA',
                'ext': 'mp4',
                'upload_date': '20150212',
                'uploader': 'The National Archives UK',
                'description': 'md5:8078af856dca76edc42910b61273dbbf',
                'uploader_id': 'NationalArchives08',
                'title': 'Webinar: Using Discovery, The National Archives’ online catalogue',
            },
        },
        # jwplayer rtmp
        {
            'url': 'http://www.suffolk.edu/sjc/live.php',
            'info_dict': {
                'id': 'live',
                'ext': 'flv',
                'title': 'Massachusetts Supreme Judicial Court Oral Arguments',
                'uploader': 'www.suffolk.edu',
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'Only has video a few mornings per month, see http://www.suffolk.edu/sjc/',
        },
        # jwplayer with only the json URL
        {
            'url': 'https://www.hollywoodreporter.com/news/general-news/dunkirk-team-reveals-what-christopher-nolan-said-oscar-win-meet-your-oscar-winner-1092454',
            'info_dict': {
                'id': 'TljWkvWH',
                'ext': 'mp4',
                'upload_date': '20180306',
                'title': 'md5:91eb1862f6526415214f62c00b453936',
                'description': 'md5:73048ae50ae953da10549d1d2fe9b3aa',
                'timestamp': 1520367225,
            },
            'params': {
                'skip_download': True,
            },
        },
        # Complex jwplayer
        {
            'url': 'http://www.indiedb.com/games/king-machine/videos',
            'info_dict': {
                'id': 'videos',
                'ext': 'mp4',
                'title': 'king machine trailer 1',
                'description': 'Browse King Machine videos & audio for sweet media. Your eyes will thank you.',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
        },
        {
            # Youtube embed, formerly: Video.js embed, multiple formats
            'url': 'http://ortcam.com/solidworks-урок-6-настройка-чертежа_33f9b7351.html',
            'info_dict': {
                'id': 'yygqldloqIk',
                'ext': 'mp4',
                'title': 'SolidWorks. Урок 6 Настройка чертежа',
                'description': 'md5:baf95267792646afdbf030e4d06b2ab3',
                'upload_date': '20130314',
                'uploader': 'PROстое3D',
                'uploader_id': 'PROstoe3D',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # Video.js embed, single format
            'url': 'https://www.vooplayer.com/v3/watch/watch.php?v=NzgwNTg=',
            'info_dict': {
                'id': 'watch',
                'ext': 'mp4',
                'title': 'Step 1 -  Good Foundation',
                'description': 'md5:d1e7ff33a29fc3eb1673d6c270d344f4',
            },
            'params': {
                'skip_download': True,
            },
            'skip': '404 Not Found',
        },
        # rtl.nl embed
        {
            'url': 'http://www.rtlnieuws.nl/nieuws/buitenland/aanslagen-kopenhagen',
            'playlist_mincount': 5,
            'info_dict': {
                'id': 'aanslagen-kopenhagen',
                'title': 'Aanslagen Kopenhagen',
            },
        },
        # Zapiks embed
        {
            'url': 'http://www.skipass.com/news/116090-bon-appetit-s5ep3-baqueira-mi-cor.html',
            'info_dict': {
                'id': '118046',
                'ext': 'mp4',
                'title': 'EP3S5 - Bon Appétit - Baqueira Mi Corazon !',
            },
        },
        # Kaltura embed (different embed code)
        {
            'url': 'http://www.premierchristianradio.com/Shows/Saturday/Unbelievable/Conference-Videos/Os-Guinness-Is-It-Fools-Talk-Unbelievable-Conference-2014',
            'info_dict': {
                'id': '1_a52wc67y',
                'ext': 'flv',
                'upload_date': '20150127',
                'uploader_id': 'PremierMedia',
                'timestamp': int,
                'title': 'Os Guinness // Is It Fools Talk? // Unbelievable? Conference 2014',
            },
        },
        # Kaltura embed with single quotes
        {
            'url': 'http://fod.infobase.com/p_ViewPlaylist.aspx?AssignmentID=NUN8ZY',
            'info_dict': {
                'id': '0_izeg5utt',
                'ext': 'mp4',
                'title': '35871',
                'timestamp': 1355743100,
                'upload_date': '20121217',
                'uploader_id': 'cplapp@learn360.com',
            },
            'add_ie': ['Kaltura'],
        },
        {
            # Kaltura embedded via quoted entry_id
            'url': 'https://www.oreilly.com/ideas/my-cloud-makes-pretty-pictures',
            'info_dict': {
                'id': '0_utuok90b',
                'ext': 'mp4',
                'title': '06_matthew_brender_raj_dutt',
                'timestamp': 1466638791,
                'upload_date': '20160622',
            },
            'add_ie': ['Kaltura'],
            'expected_warnings': [
                'Could not send HEAD request',
            ],
            'params': {
                'skip_download': True,
            },
        },
        {
            # Kaltura embedded, some fileExt broken (#11480)
            'url': 'http://www.cornell.edu/video/nima-arkani-hamed-standard-models-of-particle-physics',
            'info_dict': {
                'id': '1_sgtvehim',
                'ext': 'mp4',
                'title': 'Our "Standard Models" of particle physics and cosmology',
                'description': 'md5:67ea74807b8c4fea92a6f38d6d323861',
                'timestamp': 1321158993,
                'upload_date': '20111113',
                'uploader_id': 'kps1',
            },
            'add_ie': ['Kaltura'],
        },
        {
            # Kaltura iframe embed
            'url': 'http://www.gsd.harvard.edu/event/i-m-pei-a-centennial-celebration/',
            'md5': 'ae5ace8eb09dc1a35d03b579a9c2cc44',
            'info_dict': {
                'id': '0_f2cfbpwy',
                'ext': 'mp4',
                'title': 'I. M. Pei: A Centennial Celebration',
                'description': 'md5:1db8f40c69edc46ca180ba30c567f37c',
                'upload_date': '20170403',
                'uploader_id': 'batchUser',
                'timestamp': 1491232186,
            },
            'add_ie': ['Kaltura'],
        },
        {
            # Kaltura iframe embed, more sophisticated
            'url': 'http://www.cns.nyu.edu/~eero/math-tools/Videos/lecture-05sep2017.html',
            'info_dict': {
                'id': '1_9gzouybz',
                'ext': 'mp4',
                'title': 'lecture-05sep2017',
                'description': 'md5:40f347d91fd4ba047e511c5321064b49',
                'upload_date': '20170913',
                'uploader_id': 'eps2',
                'timestamp': 1505340777,
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': ['Kaltura'],
        },
        {
            # meta twitter:player
            'url': 'http://thechive.com/2017/12/08/all-i-want-for-christmas-is-more-twerk/',
            'info_dict': {
                'id': '0_01b42zps',
                'ext': 'mp4',
                'title': 'Main Twerk (Video)',
                'upload_date': '20171208',
                'uploader_id': 'sebastian.salinas@thechive.com',
                'timestamp': 1512713057,
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': ['Kaltura'],
        },
        # referrer protected EaglePlatform embed
        {
            'url': 'https://tvrain.ru/lite/teleshow/kak_vse_nachinalos/namin-418921/',
            'info_dict': {
                'id': '582306',
                'ext': 'mp4',
                'title': 'Стас Намин: «Мы нарушили девственность Кремля»',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 3382,
                'view_count': int,
            },
            'params': {
                'skip_download': True,
            },
        },
        # ClipYou (EaglePlatform) embed (custom URL)
        {
            'url': 'http://muz-tv.ru/play/7129/',
            # Not checking MD5 as sometimes the direct HTTP link results in 404 and HLS is used
            'info_dict': {
                'id': '12820',
                'ext': 'mp4',
                'title': "'O Sole Mio",
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 216,
                'view_count': int,
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'This video is unavailable.',
        },
        # Pladform embed
        {
            'url': 'http://muz-tv.ru/kinozal/view/7400/',
            'info_dict': {
                'id': '100183293',
                'ext': 'mp4',
                'title': 'Тайны перевала Дятлова • 1 серия 2 часть',
                'description': 'Документальный сериал-расследование одной из самых жутких тайн ХХ века',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 694,
                'age_limit': 0,
            },
            'skip': 'HTTP Error 404: Not Found',
        },
        # Playwire embed
        {
            'url': 'http://www.cinemablend.com/new/First-Joe-Dirt-2-Trailer-Teaser-Stupid-Greatness-70874.html',
            'info_dict': {
                'id': '3519514',
                'ext': 'mp4',
                'title': 'Joe Dirt 2 Beautiful Loser Teaser Trailer',
                'thumbnail': r're:^https?://.*\.png$',
                'duration': 45.115,
            },
        },
        # Crooks and Liars embed
        {
            'url': 'http://crooksandliars.com/2015/04/fox-friends-says-protecting-atheists',
            'info_dict': {
                'id': '8RUoRhRi',
                'ext': 'mp4',
                'title': 'Fox & Friends Says Protecting Atheists From Discrimination Is Anti-Christian!',
                'description': 'md5:e1a46ad1650e3a5ec7196d432799127f',
                'timestamp': 1428207000,
                'upload_date': '20150405',
                'uploader': 'Heather',
            },
        },
        # Crooks and Liars external embed
        {
            'url': 'http://theothermccain.com/2010/02/02/video-proves-that-bill-kristol-has-been-watching-glenn-beck/comment-page-1/',
            'info_dict': {
                'id': 'MTE3MjUtMzQ2MzA',
                'ext': 'mp4',
                'title': 'md5:5e3662a81a4014d24c250d76d41a08d5',
                'description': 'md5:9b8e9542d6c3c5de42d6451b7d780cec',
                'timestamp': 1265032391,
                'upload_date': '20100201',
                'uploader': 'Heather',
            },
        },
        # NBC Sports vplayer embed
        {
            'url': 'http://www.riderfans.com/forum/showthread.php?121827-Freeman&s=e98fa1ea6dc08e886b1678d35212494a',
            'info_dict': {
                'id': 'ln7x1qSThw4k',
                'ext': 'flv',
                'title': "PFT Live: New leader in the 'new-look' defense",
                'description': 'md5:65a19b4bbfb3b0c0c5768bed1dfad74e',
                'uploader': 'NBCU-SPORTS',
                'upload_date': '20140107',
                'timestamp': 1389118457,
            },
            'skip': 'Invalid Page URL',
        },
        # NBC News embed
        {
            'url': 'http://www.vulture.com/2016/06/letterman-couldnt-care-less-about-late-night.html',
            'md5': '1aa589c675898ae6d37a17913cf68d66',
            'info_dict': {
                'id': 'x_dtl_oa_LettermanliftPR_160608',
                'ext': 'mp4',
                'title': 'David Letterman: A Preview',
                'description': 'A preview of Tom Brokaw\'s interview with David Letterman as part of the On Assignment series powered by Dateline. Airs Sunday June 12 at 7/6c.',
                'upload_date': '20160609',
                'timestamp': 1465431544,
                'uploader': 'NBCU-NEWS',
            },
        },
        # UDN embed
        {
            'url': 'https://video.udn.com/news/300346',
            'md5': 'fd2060e988c326991037b9aff9df21a6',
            'info_dict': {
                'id': '300346',
                'ext': 'mp4',
                'title': '中一中男師變性 全校師生力挺',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
            'expected_warnings': ['Failed to parse JSON Expecting value'],
        },
        # Kinja embed
        {
            'url': 'http://www.clickhole.com/video/dont-understand-bitcoin-man-will-mumble-explanatio-2537',
            'info_dict': {
                'id': '106351',
                'ext': 'mp4',
                'title': 'Don’t Understand Bitcoin? This Man Will Mumble An Explanation At You',
                'description': 'Migrated from OnionStudios',
                'thumbnail': r're:^https?://.*\.jpe?g$',
                'uploader': 'clickhole',
                'upload_date': '20150527',
                'timestamp': 1432744860,
            },
        },
        # SnagFilms embed
        {
            'url': 'http://whilewewatch.blogspot.ru/2012/06/whilewewatch-whilewewatch-gripping.html',
            'info_dict': {
                'id': '74849a00-85a9-11e1-9660-123139220831',
                'ext': 'mp4',
                'title': '#whilewewatch',
            },
        },
        # AdobeTVVideo embed
        {
            'url': 'https://helpx.adobe.com/acrobat/how-to/new-experience-acrobat-dc.html?set=acrobat--get-started--essential-beginners',
            'md5': '43662b577c018ad707a63766462b1e87',
            'info_dict': {
                'id': '2456',
                'ext': 'mp4',
                'title': 'New experience with Acrobat DC',
                'description': 'New experience with Acrobat DC',
                'duration': 248.667,
            },
        },
        # Another form of arte.tv embed
        {
            'url': 'http://www.tv-replay.fr/redirection/09-04-16/arte-reportage-arte-11508975.html',
            'md5': '850bfe45417ddf221288c88a0cffe2e2',
            'info_dict': {
                'id': '030273-562_PLUS7-F',
                'ext': 'mp4',
                'title': 'ARTE Reportage - Nulle part, en France',
                'description': 'md5:e3a0e8868ed7303ed509b9e3af2b870d',
                'upload_date': '20160409',
            },
        },
        # Duplicated embedded video URLs
        {
            'url': 'http://www.hudl.com/athlete/2538180/highlights/149298443',
            'info_dict': {
                'id': '149298443_480_16c25b74_2',
                'ext': 'mp4',
                'title': 'vs. Blue Orange Spring Game',
                'uploader': 'www.hudl.com',
            },
        },
        # twitter:player:stream embed
        {
            'url': 'http://www.rtl.be/info/video/589263.aspx?CategoryID=288',
            'info_dict': {
                'id': 'master',
                'ext': 'mp4',
                'title': 'Une nouvelle espèce de dinosaure découverte en Argentine',
                'uploader': 'www.rtl.be',
            },
            'params': {
                # m3u8 downloads
                'skip_download': True,
            },
        },
        # twitter:player embed
        {
            'url': 'http://www.theatlantic.com/video/index/484130/what-do-black-holes-sound-like/',
            'md5': 'a3e0df96369831de324f0778e126653c',
            'info_dict': {
                'id': '4909620399001',
                'ext': 'mp4',
                'title': 'What Do Black Holes Sound Like?',
                'description': 'what do black holes sound like',
                'upload_date': '20160524',
                'uploader_id': '29913724001',
                'timestamp': 1464107587,
                'uploader': 'TheAtlantic',
            },
            'skip': 'Private Youtube video',
        },
        # Facebook <iframe> embed
        {
            'url': 'https://www.hostblogger.de/blog/archives/6181-Auto-jagt-Betonmischer.html',
            'md5': 'fbcde74f534176ecb015849146dd3aee',
            'info_dict': {
                'id': '599637780109885',
                'ext': 'mp4',
                'title': 'Facebook video #599637780109885',
            },
        },
        # Facebook <iframe> embed, plugin video
        {
            'url': 'http://5pillarsuk.com/2017/06/07/tariq-ramadan-disagrees-with-pr-exercise-by-imams-refusing-funeral-prayers-for-london-attackers/',
            'info_dict': {
                'id': '1754168231264132',
                'ext': 'mp4',
                'title': 'About the Imams and Religious leaders refusing to perform funeral prayers for...',
                'uploader': 'Tariq Ramadan (official)',
                'timestamp': 1496758379,
                'upload_date': '20170606',
            },
            'params': {
                'skip_download': True,
            },
        },
        # Facebook API embed
        {
            'url': 'http://www.lothype.com/blue-stars-2016-preview-standstill-full-show/',
            'md5': 'a47372ee61b39a7b90287094d447d94e',
            'info_dict': {
                'id': '10153467542406923',
                'ext': 'mp4',
                'title': 'Facebook video #10153467542406923',
            },
        },
        # Wordpress "YouTube Video Importer" plugin
        {
            'url': 'http://www.lothype.com/blue-devils-drumline-stanford-lot-2016/',
            'md5': 'd16797741b560b485194eddda8121b48',
            'info_dict': {
                'id': 'HNTXWDXV9Is',
                'ext': 'mp4',
                'title': 'Blue Devils Drumline Stanford lot 2016',
                'upload_date': '20160627',
                'uploader_id': 'GENOCIDE8GENERAL10',
                'uploader': 'cylus cyrus',
            },
        },
        {
            # video stored on custom kaltura server
            'url': 'http://www.expansion.com/multimedia/videos.html?media=EQcM30NHIPv',
            'md5': '537617d06e64dfed891fa1593c4b30cc',
            'info_dict': {
                'id': '0_1iotm5bh',
                'ext': 'mp4',
                'title': 'Elecciones británicas: 5 lecciones para Rajoy',
                'description': 'md5:435a89d68b9760b92ce67ed227055f16',
                'uploader_id': 'videos.expansion@el-mundo.net',
                'upload_date': '20150429',
                'timestamp': 1430303472,
            },
            'add_ie': ['Kaltura'],
        },
        {
            # multiple kaltura embeds, nsfw
            'url': 'https://www.quartier-rouge.be/prive/femmes/kamila-avec-video-jaime-sadomie.html',
            'info_dict': {
                'id': 'kamila-avec-video-jaime-sadomie',
                'title': "Kamila avec vídeo “J'aime sadomie”",
            },
            'playlist_count': 8,
        },
        {
            # Non-standard Vimeo embed
            'url': 'https://openclassrooms.com/courses/understanding-the-web',
            'md5': '64d86f1c7d369afd9a78b38cbb88d80a',
            'info_dict': {
                'id': '148867247',
                'ext': 'mp4',
                'title': 'Understanding the web - Teaser',
                'description': 'This is "Understanding the web - Teaser" by openclassrooms on Vimeo, the home for high quality videos and the people who love them.',
                'upload_date': '20151214',
                'uploader': 'OpenClassrooms',
                'uploader_id': 'openclassrooms',
            },
            'add_ie': ['Vimeo'],
        },
        {
            # generic vimeo embed that requires original URL passed as Referer
            'url': 'http://racing4everyone.eu/2016/07/30/formula-1-2016-round12-germany/',
            'only_matching': True,
        },
        {
            'url': 'https://support.arkena.com/display/PLAY/Ways+to+embed+your+video',
            'md5': 'b96f2f71b359a8ecd05ce4e1daa72365',
            'info_dict': {
                'id': 'b41dda37-d8e7-4d3f-b1b5-9a9db578bdfe',
                'ext': 'mp4',
                'title': 'Big Buck Bunny',
                'description': 'Royalty free test video',
                'timestamp': 1432816365,
                'upload_date': '20150528',
                'is_live': False,
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': ['Arkena'],
        },
        {
            'url': 'http://nova.bg/news/view/2016/08/16/156543/%D0%BD%D0%B0-%D0%BA%D0%BE%D1%81%D1%8A%D0%BC-%D0%BE%D1%82-%D0%B2%D0%B7%D1%80%D0%B8%D0%B2-%D0%BE%D1%82%D1%86%D0%B5%D0%BF%D0%B8%D1%85%D0%B0-%D1%86%D1%8F%D0%BB-%D0%BA%D0%B2%D0%B0%D1%80%D1%82%D0%B0%D0%BB-%D0%B7%D0%B0%D1%80%D0%B0%D0%B4%D0%B8-%D0%B8%D0%B7%D1%82%D0%B8%D1%87%D0%B0%D0%BD%D0%B5-%D0%BD%D0%B0-%D0%B3%D0%B0%D0%B7-%D0%B2-%D0%BF%D0%BB%D0%BE%D0%B2%D0%B4%D0%B8%D0%B2/',
            'info_dict': {
                'id': '1c7141f46c',
                'ext': 'mp4',
                'title': 'НА КОСЪМ ОТ ВЗРИВ: Изтичане на газ на бензиностанция в Пловдив',
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': ['Vbox7'],
        },
        {
            # DBTV embeds
            'url': 'http://www.dagbladet.no/2016/02/23/nyheter/nordlys/ski/troms/ver/43254897/',
            'info_dict': {
                'id': '43254897',
                'title': 'Etter ett års planlegging, klaffet endelig alt: - Jeg måtte ta en liten dans',
            },
            'playlist_mincount': 3,
        },
        {
            # Videa embeds
            'url': 'http://forum.dvdtalk.com/movie-talk/623756-deleted-magic-star-wars-ot-deleted-alt-scenes-docu-style.html',
            'info_dict': {
                'id': '623756-deleted-magic-star-wars-ot-deleted-alt-scenes-docu-style',
                'title': 'Deleted Magic - Star Wars: OT Deleted / Alt. Scenes Docu. Style - DVD Talk Forum',
            },
            'playlist_mincount': 2,
        },
        {
            # 20 minuten embed
            'url': 'http://www.20min.ch/schweiz/news/story/So-kommen-Sie-bei-Eis-und-Schnee-sicher-an-27032552',
            'info_dict': {
                'id': '523629',
                'ext': 'mp4',
                'title': 'So kommen Sie bei Eis und Schnee sicher an',
                'description': 'md5:117c212f64b25e3d95747e5276863f7d',
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': ['TwentyMinuten'],
        },
        {
            # VideoPress embed
            'url': 'https://en.support.wordpress.com/videopress/',
            'info_dict': {
                'id': 'OcobLTqC',
                'ext': 'm4v',
                'title': 'IMG_5786',
                'timestamp': 1435711927,
                'upload_date': '20150701',
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': ['VideoPress'],
        },
        {
            # Rutube embed
            'url': 'http://magazzino.friday.ru/videos/vipuski/kazan-2',
            'info_dict': {
                'id': '9b3d5bee0a8740bf70dfd29d3ea43541',
                'ext': 'flv',
                'title': 'Магаззино: Казань 2',
                'description': 'md5:99bccdfac2269f0e8fdbc4bbc9db184a',
                'uploader': 'Магаззино',
                'upload_date': '20170228',
                'uploader_id': '996642',
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': ['Rutube'],
        },
        {
            # glomex:embed
            'url': 'https://www.skai.gr/news/world/iatrikos-syllogos-tourkias-to-turkovac-aplo-dialyma-erntogan-eiste-apateones-kai-pseytes',
            'info_dict': {
                'id': 'v-ch2nkhcirwc9-sf',
                'ext': 'mp4',
                'title': 'md5:786e1e24e06c55993cee965ef853a0c1',
                'description': 'md5:8b517a61d577efe7e36fde72fd535995',
                'timestamp': 1641885019,
                'upload_date': '20220111',
                'duration': 460000,
                'thumbnail': 'https://i3thumbs.glomex.com/dC1idjJwdndiMjRzeGwvMjAyMi8wMS8xMS8wNy8xMF8zNV82MWRkMmQ2YmU5ZTgyLmpwZw==/profile:player-960x540',
            },
        },
        {
            # megatvcom:embed
            'url': 'https://www.in.gr/2021/12/18/greece/apokalypsi-mega-poios-parelave-tin-ereyna-tsiodra-ek-merous-tis-kyvernisis-o-prothypourgos-telika-gnorize/',
            'info_dict': {
                'id': 'apokalypsi-mega-poios-parelave-tin-ereyna-tsiodra-ek-merous-tis-kyvernisis-o-prothypourgos-telika-gnorize',
                'title': 'md5:5e569cf996ec111057c2764ec272848f',
            },
            'playlist': [{
                'md5': '1afa26064ff00ccb91617957dbc73dc1',
                'info_dict': {
                    'ext': 'mp4',
                    'id': '564916',
                    'display_id': 'md5:6cdf22d3a2e7bacb274b7295089a1770',
                    'title': 'md5:33b9dd39584685b62873043670eb52a6',
                    'description': 'md5:c1db7310f390518ac36dd69d947ef1a1',
                    'timestamp': 1639753145,
                    'upload_date': '20211217',
                    'thumbnail': 'https://www.megatv.com/wp-content/uploads/2021/12/prezerakos-1024x597.jpg',
                },
            }, {
                'md5': '4a1c220695f1ef865a8b7966a53e2474',
                'info_dict': {
                    'ext': 'mp4',
                    'id': '564905',
                    'display_id': 'md5:ead15695e485e649aed2b81ebd699b88',
                    'title': 'md5:2b71fd54249a3ca34609fe39ae31c47b',
                    'description': 'md5:c42e12f638d0a97d6de4508e2c4df982',
                    'timestamp': 1639753047,
                    'upload_date': '20211217',
                    'thumbnail': 'https://www.megatv.com/wp-content/uploads/2021/12/tsiodras-mitsotakis-1024x545.jpg',
                },
            }],
        },
        {
            'url': 'https://www.ertnews.gr/video/manolis-goyalles-o-anthropos-piso-apo-ti-diadiktyaki-vasilopita/',
            'info_dict': {
                'id': '2022/tv/news-themata-ianouarios/20220114-apotis6-gouales-pita.mp4',
                'ext': 'mp4',
                'title': 'md5:df64f5b61c06d0e9556c0cdd5cf14464',
                'thumbnail': 'https://www.ert.gr/themata/photos/2021/20220114-apotis6-gouales-pita.jpg',
            },
        },
        {
            # ThePlatform embedded with whitespaces in URLs
            'url': 'http://www.golfchannel.com/topics/shows/golftalkcentral.htm',
            'only_matching': True,
        },
        {
            # Senate ISVP iframe https
            'url': 'https://www.hsgac.senate.gov/hearings/canadas-fast-track-refugee-plan-unanswered-questions-and-implications-for-us-national-security',
            'md5': 'fb8c70b0b515e5037981a2492099aab8',
            'info_dict': {
                'id': 'govtaff020316',
                'ext': 'mp4',
                'title': 'Integrated Senate Video Player',
            },
            'add_ie': ['SenateISVP'],
        },
        {
            # Limelight embeds (1 channel embed + 4 media embeds)
            'url': 'http://www.sedona.com/FacilitatorTraining2017',
            'info_dict': {
                'id': 'FacilitatorTraining2017',
                'title': 'Facilitator Training 2017',
            },
            'playlist_mincount': 5,
        },
        {
            # Limelight embed (LimelightPlayerUtil.embed)
            'url': 'https://tv5.ca/videos?v=xuu8qowr291ri',
            'info_dict': {
                'id': '95d035dc5c8a401588e9c0e6bd1e9c92',
                'ext': 'mp4',
                'title': '07448641',
                'timestamp': 1499890639,
                'upload_date': '20170712',
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': ['LimelightMedia'],
        },
        {
            'url': 'http://kron4.com/2017/04/28/standoff-with-walnut-creek-murder-suspect-ends-with-arrest/',
            'info_dict': {
                'id': 'standoff-with-walnut-creek-murder-suspect-ends-with-arrest',
                'title': 'Standoff with Walnut Creek murder suspect ends',
                'description': 'md5:3ccc48a60fc9441eeccfc9c469ebf788',
            },
            'playlist_mincount': 4,
        },
        {
            # WashingtonPost embed
            'url': 'http://www.vanityfair.com/hollywood/2017/04/donald-trump-tv-pitches',
            'info_dict': {
                'id': '8caf6e88-d0ec-11e5-90d3-34c2c42653ac',
                'ext': 'mp4',
                'title': "No one has seen the drama series based on Trump's life \u2014 until now",
                'description': 'Donald Trump wanted a weekly TV drama based on his life. It never aired. But The Washington Post recently obtained a scene from the pilot script — and enlisted actors.',
                'timestamp': 1455216756,
                'uploader': 'The Washington Post',
                'upload_date': '20160211',
            },
            'add_ie': ['WashingtonPost'],
        },
        {
            # JOJ.sk embeds
            'url': 'https://www.noviny.sk/slovensko/238543-slovenskom-sa-prehnala-vlna-silnych-burok',
            'info_dict': {
                'id': '238543-slovenskom-sa-prehnala-vlna-silnych-burok',
                'title': 'Slovenskom sa prehnala vlna silných búrok',
            },
            'playlist_mincount': 5,
            'add_ie': ['Joj'],
        },
        {
            # AMP embed (see https://www.ampproject.org/docs/reference/components/amp-video)
            'url': 'https://tvrain.ru/amp/418921/',
            'md5': 'cc00413936695987e8de148b67d14f1d',
            'info_dict': {
                'id': '418921',
                'ext': 'mp4',
                'title': 'Стас Намин: «Мы нарушили девственность Кремля»',
            },
        },
        {
            # multiple HTML5 videos on one page
            'url': 'https://www.paragon-software.com/home/rk-free/keyscenarios.html',
            'info_dict': {
                'id': 'keyscenarios',
                'title': 'Rescue Kit 14 Free Edition - Getting started',
            },
            'playlist_count': 4,
        },
        {
            # vshare embed
            'url': 'https://youtube-dl-demo.neocities.org/vshare.html',
            'md5': '17b39f55b5497ae8b59f5fbce8e35886',
            'info_dict': {
                'id': '0f64ce6',
                'title': 'vl14062007715967',
                'ext': 'mp4',
            },
        },
        {
            'url': 'http://www.heidelberg-laureate-forum.org/blog/video/lecture-friday-september-23-2016-sir-c-antony-r-hoare/',
            'md5': 'aecd089f55b1cb5a59032cb049d3a356',
            'info_dict': {
                'id': '90227f51a80c4d8f86c345a7fa62bd9a1d',
                'ext': 'mp4',
                'title': 'Lecture: Friday, September 23, 2016 - Sir Tony Hoare',
                'description': 'md5:5a51db84a62def7b7054df2ade403c6c',
                'timestamp': 1474354800,
                'upload_date': '20160920',
            },
        },
        {
            'url': 'http://www.kidzworld.com/article/30935-trolls-the-beat-goes-on-interview-skylar-astin-and-amanda-leighton',
            'info_dict': {
                'id': '1731611',
                'ext': 'mp4',
                'title': 'Official Trailer | TROLLS: THE BEAT GOES ON!',
                'description': 'md5:eb5f23826a027ba95277d105f248b825',
                'timestamp': 1516100691,
                'upload_date': '20180116',
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': ['SpringboardPlatform'],
        },
        {
            'url': 'https://www.yapfiles.ru/show/1872528/690b05d3054d2dbe1e69523aa21bb3b1.mp4.html',
            'info_dict': {
                'id': 'vMDE4NzI1Mjgt690b',
                'ext': 'mp4',
                'title': 'Котята',
            },
            'add_ie': ['YapFiles'],
            'params': {
                'skip_download': True,
            },
        },
        {
            # CloudflareStream embed
            'url': 'https://www.cloudflare.com/products/cloudflare-stream/',
            'info_dict': {
                'id': '31c9291ab41fac05471db4e73aa11717',
                'ext': 'mp4',
                'title': '31c9291ab41fac05471db4e73aa11717',
            },
            'add_ie': ['CloudflareStream'],
            'params': {
                'skip_download': True,
            },
        },
        {
            # PeerTube embed
            'url': 'https://joinpeertube.org/fr/home/',
            'info_dict': {
                'id': 'home',
                'title': 'Reprenez le contrôle de vos vidéos ! #JoinPeertube',
            },
            'playlist_count': 2,
        },
        {
            # Indavideo embed
            'url': 'https://streetkitchen.hu/receptek/igy_kell_otthon_hamburgert_sutni/',
            'info_dict': {
                'id': '1693903',
                'ext': 'mp4',
                'title': 'Így kell otthon hamburgert sütni',
                'description': 'md5:f5a730ecf900a5c852e1e00540bbb0f7',
                'timestamp': 1426330212,
                'upload_date': '20150314',
                'uploader': 'StreetKitchen',
                'uploader_id': '546363',
            },
            'add_ie': ['IndavideoEmbed'],
            'params': {
                'skip_download': True,
            },
        },
        {
            # APA embed via JWPlatform embed
            'url': 'http://www.vol.at/blue-man-group/5593454',
            'info_dict': {
                'id': 'jjv85FdZ',
                'ext': 'mp4',
                'title': '"Blau ist mysteriös": Die Blue Man Group im Interview',
                'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
                'thumbnail': r're:^https?://.*\.jpg$',
                'duration': 254,
                'timestamp': 1519211149,
                'upload_date': '20180221',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://share-videos.se/auto/video/83645793?uid=13',
            'md5': 'b68d276de422ab07ee1d49388103f457',
            'info_dict': {
                'id': '83645793',
                'title': 'Lock up and get excited',
                'ext': 'mp4',
            },
            'skip': 'TODO: fix nested playlists processing in tests',
        },
        {
            # Viqeo embeds
            'url': 'https://viqeo.tv/',
            'info_dict': {
                'id': 'viqeo',
                'title': 'All-new video platform',
            },
            'playlist_count': 6,
        },
        # {
        #     # Zype embed
        #     'url': 'https://www.cookscountry.com/episode/554-smoky-barbecue-favorites',
        #     'info_dict': {
        #         'id': '5b400b834b32992a310622b9',
        #         'ext': 'mp4',
        #         'title': 'Smoky Barbecue Favorites',
        #         'thumbnail': r're:^https?://.*\.jpe?g',
        #         'description': 'md5:5ff01e76316bd8d46508af26dc86023b',
        #         'upload_date': '20170909',
        #         'timestamp': 1504915200,
        #     },
        #     'add_ie': [ZypeIE.ie_key()],
        #     'params': {
        #         'skip_download': True,
        #     },
        # },
        {
            # videojs embed
            'url': 'https://video.sibnet.ru/shell.php?videoid=3422904',
            'info_dict': {
                'id': 'shell',
                'ext': 'mp4',
                'title': 'Доставщик пиццы спросил разрешения сыграть на фортепиано',
                'description': 'md5:89209cdc587dab1e4a090453dbaa2cb1',
                'thumbnail': r're:^https?://.*\.jpg$',
            },
            'params': {
                'skip_download': True,
            },
            'expected_warnings': ['Failed to download MPD manifest'],
        },
        {
            # DailyMotion embed with DM.player
            'url': 'https://www.beinsports.com/us/copa-del-rey/video/the-locker-room-valencia-beat-barca-in-copa/1203804',
            'info_dict': {
                'id': 'k6aKkGHd9FJs4mtJN39',
                'ext': 'mp4',
                'title': 'The Locker Room: Valencia Beat Barca In Copa del Rey Final',
                'description': 'This video is private.',
                'uploader_id': 'x1jf30l',
                'uploader': 'beIN SPORTS USA',
                'upload_date': '20190528',
                'timestamp': 1559062971,
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # tvopengr:embed
            'url': 'https://www.ethnos.gr/World/article/190604/hparosiaxekinoynoisynomiliessthgeneyhmethskiatoypolemoypanoapothnoykrania',
            'md5': 'eb0c3995d0a6f18f6538c8e057865d7d',
            'info_dict': {
                'id': '101119',
                'ext': 'mp4',
                'display_id': 'oikarpoitondiapragmateyseonhparosias',
                'title': 'md5:b979f4d640c568617d6547035528a149',
                'description': 'md5:e54fc1977c7159b01cc11cd7d9d85550',
                'timestamp': 1641772800,
                'upload_date': '20220110',
                'thumbnail': 'https://opentv-static.siliconweb.com/imgHandler/1920/70bc39fa-895b-4918-a364-c39d2135fc6d.jpg',

            },
        },
        {
            # blogger embed
            'url': 'https://blog.tomeuvizoso.net/2019/01/a-panfrost-milestone.html',
            'md5': 'f1bc19b6ea1b0fd1d81e84ca9ec467ac',
            'info_dict': {
                'id': 'BLOGGER-video-3c740e3a49197e16-796',
                'ext': 'mp4',
                'title': 'Blogger',
                'thumbnail': r're:^https?://.*',
            },
        },
        # {
        #     # TODO: find another test
        #     # http://schema.org/VideoObject
        #     'url': 'https://flipagram.com/f/nyvTSJMKId',
        #     'md5': '888dcf08b7ea671381f00fab74692755',
        #     'info_dict': {
        #         'id': 'nyvTSJMKId',
        #         'ext': 'mp4',
        #         'title': 'Flipagram by sjuria101 featuring Midnight Memories by One Direction',
        #         'description': '#love for cats.',
        #         'timestamp': 1461244995,
        #         'upload_date': '20160421',
        #     },
        #     'params': {
        #         'force_generic_extractor': True,
        #     },
        # },
        {
            # VHX Embed
            'url': 'https://demo.vhx.tv/category-c/videos/file-example-mp4-480-1-5mg-copy',
            'info_dict': {
                'id': '858208',
                'ext': 'mp4',
                'title': 'Untitled',
                'uploader_id': 'user80538407',
                'uploader': 'OTT Videos',
            },
        },
        {
            # ArcPublishing PoWa video player
            'url': 'https://www.adn.com/politics/2020/11/02/video-senate-candidates-campaign-in-anchorage-on-eve-of-election-day/',
            'md5': 'b03b2fac8680e1e5a7cc81a5c27e71b3',
            'info_dict': {
                'id': '8c99cb6e-b29c-4bc9-9173-7bf9979225ab',
                'ext': 'mp4',
                'title': 'Senate candidates wave to voters on Anchorage streets',
                'description': 'md5:91f51a6511f090617353dc720318b20e',
                'timestamp': 1604378735,
                'upload_date': '20201103',
                'duration': 1581,
            },
        },
        {
            # MyChannels SDK embed
            # https://www.24kitchen.nl/populair/deskundige-dit-waarom-sommigen-gevoelig-zijn-voor-voedselallergieen
            'url': 'https://www.demorgen.be/nieuws/burgemeester-rotterdam-richt-zich-in-videoboodschap-tot-relschoppers-voelt-het-goed~b0bcfd741/',
            'md5': '90c0699c37006ef18e198c032d81739c',
            'info_dict': {
                'id': '194165',
                'ext': 'mp4',
                'title': 'Burgemeester Aboutaleb spreekt relschoppers toe',
                'timestamp': 1611740340,
                'upload_date': '20210127',
                'duration': 159,
            },
        },
        {
            # Simplecast player embed
            'url': 'https://www.bio.org/podcast',
            'info_dict': {
                'id': 'podcast',
                'title': 'I AM BIO Podcast | BIO',
            },
            'playlist_mincount': 52,
        }, {
            # WimTv embed player
            'url': 'http://www.msmotor.tv/wearefmi-pt-2-2021/',
            'info_dict': {
                'id': 'wearefmi-pt-2-2021',
                'title': '#WEAREFMI – PT.2 – 2021 – MsMotorTV',
            },
            'playlist_count': 1,
        }, {
            # KVS Player
            'url': 'https://www.kvs-demo.com/videos/105/kelis-4th-of-july/',
            'info_dict': {
                'id': '105',
                'display_id': 'kelis-4th-of-july',
                'ext': 'mp4',
                'title': 'Kelis - 4th Of July',
                'description': 'Kelis - 4th Of July',
                'thumbnail': r're:https://(?:www\.)?kvs-demo.com/contents/videos_screenshots/0/105/preview.jpg',
            },
            'params': {
                'skip_download': True,
            },
            'expected_warnings': ['Untested major version'],
        }, {
            # KVS Player
            'url': 'https://www.kvs-demo.com/embed/105/',
            'info_dict': {
                'id': '105',
                'display_id': 'kelis-4th-of-july',
                'ext': 'mp4',
                'title': 'Kelis - 4th Of July / Embed Player',
                'thumbnail': r're:https://(?:www\.)?kvs-demo.com/contents/videos_screenshots/0/105/preview.jpg',
            },
            'params': {
                'skip_download': True,
            },
        }, {
            'url': 'https://youix.com/video/leningrad-zoj/',
            'md5': '94f96ba95706dc3880812b27b7d8a2b8',
            'info_dict': {
                'id': '18485',
                'display_id': 'leningrad-zoj',
                'ext': 'mp4',
                'title': 'Клип: Ленинград - ЗОЖ скачать, смотреть онлайн | Youix.com',
                'thumbnail': r're:https://youix.com/contents/videos_screenshots/18000/18485/preview(?:_480x320_youix_com.mp4)?\.jpg',
            },
        }, {
            # KVS Player
            'url': 'https://youix.com/embed/18485',
            'md5': '94f96ba95706dc3880812b27b7d8a2b8',
            'info_dict': {
                'id': '18485',
                'display_id': 'leningrad-zoj',
                'ext': 'mp4',
                'title': 'Ленинград - ЗОЖ',
                'thumbnail': r're:https://youix.com/contents/videos_screenshots/18000/18485/preview(?:_480x320_youix_com.mp4)?\.jpg',
            },
        }, {
            # KVS Player
            'url': 'https://bogmedia.org/videos/21217/40-nochey-40-nights-2016/',
            'md5': '94166bdb26b4cb1fb9214319a629fc51',
            'info_dict': {
                'id': '21217',
                'display_id': '40-nochey-2016',
                'ext': 'mp4',
                'title': '40 ночей (2016) - BogMedia.org',
                'description': 'md5:4e6d7d622636eb7948275432eb256dc3',
                'thumbnail': 'https://bogmedia.org/contents/videos_screenshots/21000/21217/preview_480p.mp4.jpg',
            },
        },
        {
            # KVS Player (for sites that serve kt_player.js via non-https urls)
            'url': 'http://www.camhub.world/embed/389508',
            'md5': 'fbe89af4cfb59c8fd9f34a202bb03e32',
            'info_dict': {
                'id': '389508',
                'display_id': 'syren-de-mer-onlyfans-05-07-2020have-a-happy-safe-holiday5f014e68a220979bdb8cd-source',
                'ext': 'mp4',
                'title': 'Syren De Mer onlyfans_05-07-2020Have_a_happy_safe_holiday5f014e68a220979bdb8cd_source / Embed плеер',
                'thumbnail': r're:https?://www\.camhub\.world/contents/videos_screenshots/389000/389508/preview\.mp4\.jpg',
            },
        },
        {
            # Reddit-hosted video that will redirect and be processed by RedditIE
            # Redirects to https://www.reddit.com/r/videos/comments/6rrwyj/that_small_heart_attack/
            'url': 'https://v.redd.it/zv89llsvexdz',
            'md5': '87f5f02f6c1582654146f830f21f8662',
            'info_dict': {
                'id': 'zv89llsvexdz',
                'ext': 'mp4',
                'timestamp': 1501941939.0,
                'title': 'That small heart attack.',
                'upload_date': '20170805',
                'uploader': 'Antw87',
            },
        },
        {
            # 1080p Reddit-hosted video that will redirect and be processed by RedditIE
            'url': 'https://v.redd.it/33hgok7dfbz71/',
            'md5': '7a1d587940242c9bb3bd6eb320b39258',
            'info_dict': {
                'id': '33hgok7dfbz71',
                'ext': 'mp4',
                'title': "The game Didn't want me to Knife that Guy I guess",
                'uploader': 'paraf1ve',
                'timestamp': 1636788683.0,
                'upload_date': '20211113',
            },
        },
        {
            # MainStreaming player
            'url': 'https://www.lactv.it/2021/10/03/lac-news24-la-settimana-03-10-2021/',
            'info_dict': {
                'id': 'EUlZfGWkGpOd',
                'title': 'La Settimana ',
                'description': '03 Ottobre ore 02:00',
                'ext': 'mp4',
                'live_status': 'not_live',
                'thumbnail': r're:https?://[A-Za-z0-9-]*\.msvdn.net/image/\w+/poster',
                'duration': 1512,
            },
        },
        {
            # Multiple gfycat iframe embeds
            'url': 'https://www.gezip.net/bbs/board.php?bo_table=entertaine&wr_id=613422',
            'info_dict': {
                'title': '재이, 윤, 세은 황금 드레스를 입고 빛난다',
                'id': 'board',
            },
            'playlist_count': 8,
        },
        {
            # Multiple gfycat gifs (direct links)
            'url': 'https://www.gezip.net/bbs/board.php?bo_table=entertaine&wr_id=612199',
            'info_dict': {
                'title': '옳게 된 크롭 니트 스테이씨 아이사',
                'id': 'board',
            },
            'playlist_count': 6,
        },
        {
            # Multiple gfycat embeds, with uppercase "IFR" in urls
            'url': 'https://kkzz.kr/?vid=2295',
            'info_dict': {
                'title': '지방시 앰버서더 에스파 카리나 움짤',
                'id': '?vid=2295',
            },
            'playlist_count': 9,
        },
        {
            # Panopto embeds
            'url': 'https://www.monash.edu/learning-teaching/teachhq/learning-technologies/panopto/how-to/insert-a-quiz-into-a-panopto-video',
            'info_dict': {
                'ext': 'mp4',
                'id': '0bd3f16c-824a-436a-8486-ac5900693aef',
                'title': 'Quizzes in Panopto',
            },
        },
        {
            # Ruutu embed
            'url': 'https://www.nelonen.fi/ohjelmat/madventures-suomi/2160731-riku-ja-tunna-lahtevat-peurajahtiin-tv-sta-tutun-biologin-kanssa---metsastysreissu-huipentuu-kasvissyojan-painajaiseen',
            'md5': 'a2513a98d3496099e6eced40f7e6a14b',
            'info_dict': {
                'id': '4044426',
                'ext': 'mp4',
                'title': 'Riku ja Tunna lähtevät peurajahtiin tv:stä tutun biologin kanssa – metsästysreissu huipentuu kasvissyöjän painajaiseen!',
                'thumbnail': r're:^https?://.+\.jpg$',
                'duration': 108,
                'series': 'Madventures Suomi',
                'description': 'md5:aa55b44bd06a1e337a6f1d0b46507381',
                'categories': ['Matkailu', 'Elämäntyyli'],
                'age_limit': 0,
                'upload_date': '20220308',
            },
        },
        {
            # Multiple Ruutu embeds
            'url': 'https://www.hs.fi/kotimaa/art-2000008762560.html',
            'info_dict': {
                'title': 'Koronavirus | Epidemiahuippu voi olla Suomessa ohi, mutta koronaviruksen poistamista yleisvaarallisten tautien joukosta harkitaan vasta syksyllä',
                'id': 'art-2000008762560',
            },
            'playlist_count': 3,
        },
        {
            # Ruutu embed in hs.fi with a single video
            'url': 'https://www.hs.fi/kotimaa/art-2000008793421.html',
            'md5': 'f8964e65d8fada6e8a562389bf366bb4',
            'info_dict': {
                'id': '4081841',
                'ext': 'mp4',
                'title': 'Puolustusvoimat siirsi panssariajoneuvoja harjoituksiin Niinisaloon 2.5.2022',
                'thumbnail': r're:^https?://.+\.jpg$',
                'duration': 138,
                'age_limit': 0,
                'upload_date': '20220504',
            },
        },
        {
            # Webpage contains double BOM
            'url': 'https://www.filmarkivet.se/movies/paris-d-moll/',
            'md5': 'df02cadc719dcc63d43288366f037754',
            'info_dict': {
                'id': 'paris-d-moll',
                'ext': 'mp4',
                'upload_date': '20220518',
                'title': 'Paris d-moll',
                'description': 'md5:319e37ea5542293db37e1e13072fe330',
                'thumbnail': 'https://www.filmarkivet.se/wp-content/uploads/parisdmoll2.jpg',
                'timestamp': 1652833414,
                'age_limit': 0,
            },
        },
        {
            'url': 'https://www.mollymovieclub.com/p/interstellar?s=r#details',
            'md5': '198bde8bed23d0b23c70725c83c9b6d9',
            'info_dict': {
                'id': '53602801',
                'ext': 'mpga',
                'title': 'Interstellar',
                'description': 'Listen now | Episode One',
                'thumbnail': 'md5:c30d9c83f738e16d8551d7219d321538',
                'uploader': 'Molly Movie Club',
                'uploader_id': '839621',
            },
        },
        {
            'url': 'https://www.blockedandreported.org/p/episode-117-lets-talk-about-depp?s=r',
            'md5': 'c0cc44ee7415daeed13c26e5b56d6aa0',
            'info_dict': {
                'id': '57962052',
                'ext': 'mpga',
                'title': 'md5:855b2756f0ee10f6723fa00b16266f8d',
                'description': 'md5:fe512a5e94136ad260c80bde00ea4eef',
                'thumbnail': 'md5:2218f27dfe517bb5ac16c47d0aebac59',
                'uploader': 'Blocked and Reported',
                'uploader_id': '500230',
            },
        },
        {
            'url': 'https://www.skimag.com/video/ski-people-1980/',
            'md5': '022a7e31c70620ebec18deeab376ee03',
            'info_dict': {
                'id': 'YTmgRiNU',
                'ext': 'mp4',
                'title': '1980 Ski People',
                'timestamp': 1610407738,
                'description': 'md5:cf9c3d101452c91e141f292b19fe4843',
                'thumbnail': 'https://cdn.jwplayer.com/v2/media/YTmgRiNU/poster.jpg?width=720',
                'duration': 5688.0,
                'upload_date': '20210111',
            },
        },
        {
            'note': 'JSON LD with multiple @type',
            'url': 'https://www.nu.nl/280161/video/hoe-een-bladvlo-dit-verwoestende-japanse-onkruid-moet-vernietigen.html',
            'md5': 'c7949f34f57273013fb7ccb1156393db',
            'info_dict': {
                'id': 'ipy2AcGL',
                'ext': 'mp4',
                'description': 'md5:6a9d644bab0dc2dc06849c2505d8383d',
                'thumbnail': r're:https://media\.nu\.nl/m/.+\.jpg',
                'title': 'Hoe een bladvlo dit verwoestende Japanse onkruid moet vernietigen',
                'timestamp': 1586577474,
                'upload_date': '20200411',
                'age_limit': 0,
                'duration': 111.0,
            },
        },
        {
            'note': 'JSON LD with unexpected data type',
            'url': 'https://www.autoweek.nl/autotests/artikel/porsche-911-gt3-rs-rij-impressie-2/',
            'info_dict': {
                'id': 'porsche-911-gt3-rs-rij-impressie-2',
                'ext': 'mp4',
                'title': 'Test: Porsche 911 GT3 RS',
                'description': 'Je ziet het niet, maar het is er wel. Downforce, hebben we het dan over. En in de nieuwe Porsche 911 GT3 RS is er zelfs heel veel downforce.',
                'timestamp': 1664920902,
                'upload_date': '20221004',
                'thumbnail': r're:^https://media.autoweek.nl/m/.+\.jpg$',
                'age_limit': 0,
                'direct': True,
            },
        },
        {
            'note': 'server returns data in brotli compression by default if `accept-encoding: *` is specified.',
            'url': 'https://www.extra.cz/cauky-lidi-70-dil-babis-predstavil-pohadky-prymulanek-nebo-andrejovy-nove-saty-ac867',
            'info_dict': {
                'id': 'cauky-lidi-70-dil-babis-predstavil-pohadky-prymulanek-nebo-andrejovy-nove-saty-ac867',
                'ext': 'mp4',
                'title': 'čauky lidi 70 finall',
                'description': 'čauky lidi 70 finall',
                'thumbnail': 'h',
                'upload_date': '20220606',
                'timestamp': 1654513791,
                'duration': 318.0,
                'direct': True,
                'age_limit': 0,
            },
        },
        {
            'url': 'https://shooshtime.com/videos/284002/just-out-of-the-shower-joi/',
            'md5': 'e2f0a4c329f7986280b7328e24036d60',
            'info_dict': {
                'id': '284002',
                'display_id': 'just-out-of-the-shower-joi',
                'ext': 'mp4',
                'title': 'Just Out Of The Shower JOI - Shooshtime',
                'thumbnail': 'https://i.shoosh.co/contents/videos_screenshots/284000/284002/preview.mp4.jpg',
                'height': 720,
                'age_limit': 18,
            },
        },
        {
            'note': 'Live HLS direct link',
            'url': 'https://d18j67ugtrocuq.cloudfront.net/out/v1/2767aec339144787926bd0322f72c6e9/index.m3u8',
            'info_dict': {
                'id': 'index',
                'title': r're:index',
                'ext': 'mp4',
                'live_status': 'is_live',
            },
            'params': {
                'skip_download': 'm3u8',
            },
        },
        {
            'note': 'Video.js VOD HLS',
            'url': 'https://gist.githubusercontent.com/bashonly/2aae0862c50f4a4b84f220c315767208/raw/e3380d413749dabbe804c9c2d8fd9a45142475c7/videojs_hls_test.html',
            'info_dict': {
                'id': 'videojs_hls_test',
                'title': 'video',
                'ext': 'mp4',
                'age_limit': 0,
                'duration': 1800,
            },
            'params': {
                'skip_download': 'm3u8',
            },
        },
    ]

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
            headers = m3u8_format.get('http_headers') or info.get('http_headers')
            duration = self._extract_m3u8_vod_duration(
                m3u8_format['url'], info.get('id'), note='Checking m3u8 live status',
                errnote='Failed to download m3u8 media playlist', headers=headers)
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
                    self.report_warning('The url doesn\'t specify the protocol, trying with http')
                    return self.url_result('http://' + url)
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
                raise ExtractorError(
                    f'{url!r} is not a valid URL. '
                    f'Set --default-search "ytsearch" (or run  yt-dlp "ytsearch:{url}" ) to search YouTube', expected=True)
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
            elif format_id.endswith(('mpd', 'dash+xml')) or ext == 'mpd':
                formats, subtitles = self._extract_mpd_formats_and_subtitles(url, video_id, headers=headers)
            elif format_id == 'f4m' or ext == 'f4m':
                formats = self._extract_f4m_formats(url, video_id, headers=headers)
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
                        xspf_base_url=full_response.url),
                    video_id)
            elif re.match(r'(?i)^(?:{[^}]+})?MPD$', doc.tag):
                info_dict['formats'], info_dict['subtitles'] = self._parse_mpd_formats_and_subtitles(
                    doc,
                    mpd_base_url=full_response.url.rpartition('/')[0],
                    mpd_url=url)
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
