import os
import re
import xml.etree.ElementTree

from .ant1newsgr import Ant1NewsGrEmbedIE
from .anvato import AnvatoIE
from .apa import APAIE
from .arcpublishing import ArcPublishingIE
from .arkena import ArkenaIE
from .arte import ArteTVEmbedIE
from .bitchute import BitChuteIE
from .blogger import BloggerIE
from .brightcove import BrightcoveLegacyIE, BrightcoveNewIE
from .channel9 import Channel9IE
from .cloudflarestream import CloudflareStreamIE
from .common import InfoExtractor
from .commonprotocols import RtmpIE
from .condenast import CondeNastIE
from .dailymail import DailyMailIE
from .dailymotion import DailymotionIE
from .dbtv import DBTVIE
from .digiteka import DigitekaIE
from .drtuber import DrTuberIE
from .eagleplatform import EaglePlatformIE
from .ertgr import ERTWebtvEmbedIE
from .expressen import ExpressenIE
from .facebook import FacebookIE
from .foxnews import FoxNewsIE
from .gedidigital import GediDigitalIE
from .gfycat import GfycatIE
from .glomex import GlomexEmbedIE
from .googledrive import GoogleDriveIE
from .indavideo import IndavideoEmbedIE
from .instagram import InstagramIE
from .joj import JojIE
from .jwplatform import JWPlatformIE
from .kaltura import KalturaIE
from .kinja import KinjaEmbedIE
from .limelight import LimelightBaseIE
from .mainstreaming import MainStreamingIE
from .medialaan import MedialaanIE
from .mediaset import MediasetIE
from .mediasite import MediasiteIE
from .megaphone import MegaphoneIE
from .megatvcom import MegaTVComEmbedIE
from .mofosex import MofosexEmbedIE
from .mtv import MTVServicesEmbeddedIE
from .myvi import MyviIE
from .nbc import NBCSportsVPlayerIE
from .nexx import NexxEmbedIE, NexxIE
from .odnoklassniki import OdnoklassnikiIE
from .onionstudios import OnionStudiosIE
from .ooyala import OoyalaIE
from .panopto import PanoptoBaseIE
from .peertube import PeerTubeIE
from .piksel import PikselIE
from .pladform import PladformIE
from .pornhub import PornHubIE
from .rcs import RCSEmbedsIE
from .redtube import RedTubeIE
from .rumble import RumbleEmbedIE
from .rutube import RutubeIE
from .rutv import RUTVIE
from .ruutu import RuutuIE
from .senategov import SenateISVPIE
from .simplecast import SimplecastIE
from .soundcloud import SoundcloudEmbedIE
from .spankwire import SpankwireIE
from .sportbox import SportBoxIE
from .spotify import SpotifyBaseIE
from .springboardplatform import SpringboardPlatformIE
from .svt import SVTIE
from .teachable import TeachableIE
from .ted import TedEmbedIE
from .theplatform import ThePlatformIE
from .threeqsdn import ThreeQSDNIE
from .tiktok import TikTokIE
from .tnaflix import TNAFlixNetworkEmbedIE
from .tube8 import Tube8IE
from .tunein import TuneInBaseIE
from .tvc import TVCIE
from .tvopengr import TVOpenGrEmbedIE
from .tvp import TVPEmbedIE
from .twentymin import TwentyMinutenIE
from .udn import UDNEmbedIE
from .ustream import UstreamIE
from .vbox7 import Vbox7IE
from .vice import ViceIE
from .videa import VideaIE
from .videomore import VideomoreIE
from .videopress import VideoPressIE
from .viewlift import ViewLiftEmbedIE
from .vimeo import VHXEmbedIE, VimeoIE
from .viqeo import ViqeoIE
from .vk import VKIE
from .vshare import VShareIE
from .vzaar import VzaarIE
from .washingtonpost import WashingtonPostIE
from .webcaster import WebcasterFeedIE
from .wimtv import WimTVIE
from .wistia import WistiaIE
from .xfileshare import XFileShareIE
from .xhamster import XHamsterEmbedIE
from .yapfiles import YapFilesIE
from .youporn import YouPornIE
from .youtube import YoutubeIE
from .zype import ZypeIE
from ..compat import (
    compat_etree_fromstring,
    compat_str,
    compat_urllib_parse_unquote,
    compat_urlparse,
)
from ..utils import (
    KNOWN_EXTENSIONS,
    ExtractorError,
    HEADRequest,
    UnsupportedError,
    determine_ext,
    dict_get,
    float_or_none,
    int_or_none,
    is_html,
    js_to_json,
    merge_dicts,
    mimetype2ext,
    orderedSet,
    parse_duration,
    parse_resolution,
    sanitized_Request,
    smuggle_url,
    str_or_none,
    try_call,
    unescapeHTML,
    unified_timestamp,
    unsmuggle_url,
    url_or_none,
    xpath_attr,
    xpath_text,
    xpath_with_ns,
)


class GenericIE(InfoExtractor):
    IE_DESC = 'Generic downloader that works on some sites'
    _VALID_URL = r'.*'
    IE_NAME = 'generic'
    _NETRC_MACHINE = False  # Supress username warning
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
            }
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
                'URL could be a direct video link, returning it as such.'
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
            },
            'expected_warnings': [
                'URL could be a direct video link, returning it as such.'
            ]
        },
        # RSS feed
        {
            'url': 'http://phihag.de/2014/youtube-dl/rss2.xml',
            'info_dict': {
                'id': 'https://phihag.de/2014/youtube-dl/rss2.xml',
                'title': 'Zero Punctuation',
                'description': 're:.*groundbreaking video review series.*'
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
                    'id': 'c1c879525ce2cb640b344507e682c36d',
                    'title': 're:Hydrogen!',
                    'description': 're:.*In this episode we are going.*',
                    'timestamp': 1567977776,
                    'upload_date': '20190908',
                    'duration': 459,
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
                'uploader_id': 'TheVerge',
                'description': r're:^Chris Ziegler takes a look at the\.*',
                'uploader': 'The Verge',
                'title': 'First Firefox OS phones side-by-side',
            },
            'params': {
                'skip_download': False,
            }
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
            }
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
        {
            # embedded brightcove video
            # it also tests brightcove videos that need to set the 'Referer'
            # in the http requests
            'add_ie': ['BrightcoveLegacy'],
            'url': 'http://www.bfmtv.com/video/bfmbusiness/cours-bourse/cours-bourse-l-analyse-technique-154522/',
            'info_dict': {
                'id': '2765128793001',
                'ext': 'mp4',
                'title': 'Le cours de bourse : l’analyse technique',
                'description': 'md5:7e9ad046e968cb2d1114004aba466fd9',
                'uploader': 'BFM BUSINESS',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # embedded with itemprop embedURL and video id spelled as `idVideo`
            'add_id': ['BrightcoveLegacy'],
            'url': 'http://bfmbusiness.bfmtv.com/mediaplayer/chroniques/olivier-delamarche/',
            'info_dict': {
                'id': '5255628253001',
                'ext': 'mp4',
                'title': 'md5:37c519b1128915607601e75a87995fc0',
                'description': 'md5:37f7f888b434bb8f8cc8dbd4f7a4cf26',
                'uploader': 'BFM BUSINESS',
                'uploader_id': '876450612001',
                'timestamp': 1482255315,
                'upload_date': '20161220',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            # https://github.com/ytdl-org/youtube-dl/issues/2253
            'url': 'http://bcove.me/i6nfkrc3',
            'md5': '0ba9446db037002366bab3b3eb30c88c',
            'info_dict': {
                'id': '3101154703001',
                'ext': 'mp4',
                'title': 'Still no power',
                'uploader': 'thestar.com',
                'description': 'Mississauga resident David Farmer is still out of power as a result of the ice storm a month ago. To keep the house warm, Farmer cuts wood from his property for a wood burning stove downstairs.',
            },
            'add_ie': ['BrightcoveLegacy'],
            'skip': 'video gone',
        },
        {
            'url': 'http://www.championat.com/video/football/v/87/87499.html',
            'md5': 'fb973ecf6e4a78a67453647444222983',
            'info_dict': {
                'id': '3414141473001',
                'ext': 'mp4',
                'title': 'Видео. Удаление Дзагоева (ЦСКА)',
                'description': 'Онлайн-трансляция матча ЦСКА - "Волга"',
                'uploader': 'Championat',
            },
        },
        {
            # https://github.com/ytdl-org/youtube-dl/issues/3541
            'add_ie': ['BrightcoveLegacy'],
            'url': 'http://www.kijk.nl/sbs6/leermijvrouwenkennen/videos/jqMiXKAYan2S/aflevering-1',
            'info_dict': {
                'id': '3866516442001',
                'ext': 'mp4',
                'title': 'Leer mij vrouwen kennen: Aflevering 1',
                'description': 'Leer mij vrouwen kennen: Aflevering 1',
                'uploader': 'SBS Broadcasting',
            },
            'skip': 'Restricted to Netherlands',
            'params': {
                'skip_download': True,  # m3u8 download
            },
        },
        {
            # Brightcove video in <iframe>
            'url': 'http://www.un.org/chinese/News/story.asp?NewsID=27724',
            'md5': '36d74ef5e37c8b4a2ce92880d208b968',
            'info_dict': {
                'id': '5360463607001',
                'ext': 'mp4',
                'title': '叙利亚失明儿童在废墟上演唱《心跳》  呼吁获得正常童年生活',
                'description': '联合国儿童基金会中东和北非区域大使、作曲家扎德·迪拉尼（Zade Dirani）在3月15日叙利亚冲突爆发7周年纪念日之际发布了为叙利亚谱写的歌曲《心跳》（HEARTBEAT），为受到六年冲突影响的叙利亚儿童发出强烈呐喊，呼吁世界做出共同努力，使叙利亚儿童重新获得享有正常童年生活的权利。',
                'uploader': 'United Nations',
                'uploader_id': '1362235914001',
                'timestamp': 1489593889,
                'upload_date': '20170315',
            },
            'add_ie': ['BrightcoveLegacy'],
        },
        {
            # Brightcove with alternative playerID key
            'url': 'http://www.nature.com/nmeth/journal/v9/n7/fig_tab/nmeth.2062_SV1.html',
            'info_dict': {
                'id': 'nmeth.2062_SV1',
                'title': 'Simultaneous multiview imaging of the Drosophila syncytial blastoderm : Quantitative high-speed imaging of entire developing embryos with simultaneous multiview light-sheet microscopy : Nature Methods : Nature Research',
            },
            'playlist': [{
                'info_dict': {
                    'id': '2228375078001',
                    'ext': 'mp4',
                    'title': 'nmeth.2062-sv1',
                    'description': 'nmeth.2062-sv1',
                    'timestamp': 1363357591,
                    'upload_date': '20130315',
                    'uploader': 'Nature Publishing Group',
                    'uploader_id': '1964492299001',
                },
            }],
        },
        {
            # Brightcove with UUID in videoPlayer
            'url': 'http://www8.hp.com/cn/zh/home.html',
            'info_dict': {
                'id': '5255815316001',
                'ext': 'mp4',
                'title': 'Sprocket Video - China',
                'description': 'Sprocket Video - China',
                'uploader': 'HP-Video Gallery',
                'timestamp': 1482263210,
                'upload_date': '20161220',
                'uploader_id': '1107601872001',
            },
            'params': {
                'skip_download': True,  # m3u8 download
            },
            'skip': 'video rotates...weekly?',
        },
        {
            # Brightcove:new type [2].
            'url': 'http://www.delawaresportszone.com/video-st-thomas-more-earns-first-trip-to-basketball-semis',
            'md5': '2b35148fcf48da41c9fb4591650784f3',
            'info_dict': {
                'id': '5348741021001',
                'ext': 'mp4',
                'upload_date': '20170306',
                'uploader_id': '4191638492001',
                'timestamp': 1488769918,
                'title': 'VIDEO:  St. Thomas More earns first trip to basketball semis',

            },
        },
        {
            # Alternative brightcove <video> attributes
            'url': 'http://www.programme-tv.net/videos/extraits/81095-guillaume-canet-evoque-les-rumeurs-d-infidelite-de-marion-cotillard-avec-brad-pitt-dans-vivement-dimanche/',
            'info_dict': {
                'id': '81095-guillaume-canet-evoque-les-rumeurs-d-infidelite-de-marion-cotillard-avec-brad-pitt-dans-vivement-dimanche',
                'title': "Guillaume Canet évoque les rumeurs d'infidélité de Marion Cotillard avec Brad Pitt dans Vivement Dimanche, Extraits : toutes les vidéos avec Télé-Loisirs",
            },
            'playlist': [{
                'md5': '732d22ba3d33f2f3fc253c39f8f36523',
                'info_dict': {
                    'id': '5311302538001',
                    'ext': 'mp4',
                    'title': "Guillaume Canet évoque les rumeurs d'infidélité de Marion Cotillard avec Brad Pitt dans Vivement Dimanche",
                    'description': "Guillaume Canet évoque les rumeurs d'infidélité de Marion Cotillard avec Brad Pitt dans Vivement Dimanche (France 2, 5 février 2017)",
                    'timestamp': 1486321708,
                    'upload_date': '20170205',
                    'uploader_id': '800000640001',
                },
                'only_matching': True,
            }],
        },
        {
            # Brightcove with UUID in videoPlayer
            'url': 'http://www8.hp.com/cn/zh/home.html',
            'info_dict': {
                'id': '5255815316001',
                'ext': 'mp4',
                'title': 'Sprocket Video - China',
                'description': 'Sprocket Video - China',
                'uploader': 'HP-Video Gallery',
                'timestamp': 1482263210,
                'upload_date': '20161220',
                'uploader_id': '1107601872001',
            },
            'params': {
                'skip_download': True,  # m3u8 download
            },
        },
        # ooyala video
        {
            'url': 'http://www.rollingstone.com/music/videos/norwegian-dj-cashmere-cat-goes-spartan-on-with-me-premiere-20131219',
            'md5': '166dd577b433b4d4ebfee10b0824d8ff',
            'info_dict': {
                'id': 'BwY2RxaTrTkslxOfcan0UCf0YqyvWysJ',
                'ext': 'mp4',
                'title': '2cc213299525360.mov',  # that's what we get
                'duration': 238.231,
            },
            'add_ie': ['Ooyala'],
        },
        {
            # ooyala video embedded with http://player.ooyala.com/iframe.js
            'url': 'http://www.macrumors.com/2015/07/24/steve-jobs-the-man-in-the-machine-first-trailer/',
            'info_dict': {
                'id': 'p0MGJndjoG5SOKqO_hZJuZFPB-Tr5VgB',
                'ext': 'mp4',
                'title': '"Steve Jobs: Man in the Machine" trailer',
                'description': 'The first trailer for the Alex Gibney documentary "Steve Jobs: Man in the Machine."',
                'duration': 135.427,
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'movie expired',
        },
        # ooyala video embedded with http://player.ooyala.com/static/v4/production/latest/core.min.js
        {
            'url': 'http://wnep.com/2017/07/22/steampunk-fest-comes-to-honesdale/',
            'info_dict': {
                'id': 'lwYWYxYzE6V5uJMjNGyKtwwiw9ZJD7t2',
                'ext': 'mp4',
                'title': 'Steampunk Fest Comes to Honesdale',
                'duration': 43.276,
            },
            'params': {
                'skip_download': True,
            }
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
                }
            }, {
                'info_dict': {
                    'id': '370905',
                    'title': 'Госзаказ. День 2',
                    'ext': 'mp4',
                }
            }, {
                'info_dict': {
                    'id': '370902',
                    'title': 'Госзаказ. День 1',
                    'ext': 'mp4',
                }
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
            }
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
            }
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
                'skip_download': 'Requires rtmpdump'
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
                'Forbidden'
            ]
        },
        # Condé Nast embed
        {
            'url': 'http://www.wired.com/2014/04/honda-asimo/',
            'md5': 'ba0dfe966fa007657bd1443ee672db0f',
            'info_dict': {
                'id': '53501be369702d3275860000',
                'ext': 'mp4',
                'title': 'Honda’s  New Asimo Robot Is More Human Than Ever',
            }
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
            }
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
            }
        },
        # YouTube <object> embed
        {
            'url': 'http://www.improbable.com/2017/04/03/untrained-modern-youths-and-ancient-masters-in-selfie-portraits/',
            'md5': '516718101ec834f74318df76259fb3cc',
            'info_dict': {
                'id': 'msN87y-iEx0',
                'ext': 'webm',
                'title': 'Feynman: Mirrors FUN TO IMAGINE 6',
                'upload_date': '20080526',
                'description': 'md5:0ffc78ea3f01b2e2c247d5f8d1d3c18d',
                'uploader': 'Christopher Sykes',
                'uploader_id': 'ChristopherJSykes',
            },
            'add_ie': ['Youtube'],
        },
        # Camtasia studio
        {
            'url': 'http://www.ll.mit.edu/workshops/education/videocourses/antennas/lecture1/video/',
            'playlist': [{
                'md5': '0c5e352edabf715d762b0ad4e6d9ee67',
                'info_dict': {
                    'id': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final',
                    'title': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final - video1',
                    'ext': 'flv',
                    'duration': 2235.90,
                }
            }, {
                'md5': '10e4bb3aaca9fd630e273ff92d9f3c63',
                'info_dict': {
                    'id': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final_PIP',
                    'title': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final - pip',
                    'ext': 'flv',
                    'duration': 2235.93,
                }
            }],
            'info_dict': {
                'title': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final',
            }
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
            }
        },
        # Multiple brightcove videos
        # https://github.com/ytdl-org/youtube-dl/issues/2283
        {
            'url': 'http://www.newyorker.com/online/blogs/newsdesk/2014/01/always-never-nuclear-command-and-control.html',
            'info_dict': {
                'id': 'always-never',
                'title': 'Always / Never - The New Yorker',
            },
            'playlist_count': 3,
            'params': {
                'extract_flat': False,
                'skip_download': True,
            }
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
        # Wistia embed
        {
            'url': 'http://study.com/academy/lesson/north-american-exploration-failed-colonies-of-spain-france-england.html#lesson',
            'md5': '1953f3a698ab51cfc948ed3992a0b7ff',
            'info_dict': {
                'id': '6e2wtrbdaf',
                'ext': 'mov',
                'title': 'paywall_north-american-exploration-failed-colonies-of-spain-france-england',
                'description': 'a Paywall Videos video from Remilon',
                'duration': 644.072,
                'uploader': 'study.com',
                'timestamp': 1459678540,
                'upload_date': '20160403',
                'filesize': 24687186,
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
            }
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
            }
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
            }
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
        # Cinchcast embed
        {
            'url': 'http://undergroundwellness.com/podcasts/306-5-steps-to-permanent-gut-healing/',
            'info_dict': {
                'id': '7141703',
                'ext': 'mp3',
                'upload_date': '20141126',
                'title': 'Jack Tips: 5 Steps to Permanent Gut Healing',
            }
        },
        # Cinerama player
        {
            'url': 'http://www.abc.net.au/7.30/content/2015/s4164797.htm',
            'info_dict': {
                'id': '730m_DandD_1901_512k',
                'ext': 'mp4',
                'uploader': 'www.abc.net.au',
                'title': 'Game of Thrones with dice - Dungeons and Dragons fantasy role-playing game gets new life - 19/01/2015',
            }
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
            # JWPlayer config passed as variable
            'url': 'http://www.txxx.com/videos/3326530/ariele/',
            'info_dict': {
                'id': '3326530_hq',
                'ext': 'mp4',
                'title': 'ARIELE | Tube Cup',
                'uploader': 'www.txxx.com',
                'age_limit': 18,
            },
            'params': {
                'skip_download': True,
            }
        },
        {
            # JWPlatform iframe
            'url': 'https://www.covermagazine.co.uk/feature/2465255/business-protection-involved',
            'info_dict': {
                'id': 'AG26UQXM',
                'ext': 'mp4',
                'upload_date': '20160719',
                'timestamp': 468923808,
                'title': '2016_05_18 Cover L&G Business Protection V1 FINAL.mp4',
            },
            'add_ie': [JWPlatformIE.ie_key()],
        },
        {
            # Video.js embed, multiple formats
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
        },
        # rtl.nl embed
        {
            'url': 'http://www.rtlnieuws.nl/nieuws/buitenland/aanslagen-kopenhagen',
            'playlist_mincount': 5,
            'info_dict': {
                'id': 'aanslagen-kopenhagen',
                'title': 'Aanslagen Kopenhagen',
            }
        },
        # Zapiks embed
        {
            'url': 'http://www.skipass.com/news/116090-bon-appetit-s5ep3-baqueira-mi-cor.html',
            'info_dict': {
                'id': '118046',
                'ext': 'mp4',
                'title': 'EP3S5 - Bon Appétit - Baqueira Mi Corazon !',
            }
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
                'Could not send HEAD request'
            ],
            'params': {
                'skip_download': True,
            }
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
                'title': "Fox & Friends Says Protecting Atheists From Discrimination Is Anti-Christian!",
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
        # Brightcove URL in single quotes
        {
            'url': 'http://www.sportsnet.ca/baseball/mlb/sn-presents-russell-martin-world-citizen/',
            'md5': '4ae374f1f8b91c889c4b9203c8c752af',
            'info_dict': {
                'id': '4255764656001',
                'ext': 'mp4',
                'title': 'SN Presents: Russell Martin, World Citizen',
                'description': 'To understand why he was the Toronto Blue Jays’ top off-season priority is to appreciate his background and upbringing in Montreal, where he first developed his baseball skills. Written and narrated by Stephen Brunt.',
                'uploader': 'Rogers Sportsnet',
                'uploader_id': '1704050871',
                'upload_date': '20150525',
                'timestamp': 1432570283,
            },
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
            }
        },
        # SnagFilms embed
        {
            'url': 'http://whilewewatch.blogspot.ru/2012/06/whilewewatch-whilewewatch-gripping.html',
            'info_dict': {
                'id': '74849a00-85a9-11e1-9660-123139220831',
                'ext': 'mp4',
                'title': '#whilewewatch',
            }
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
        # BrightcoveInPageEmbed embed
        {
            'url': 'http://www.geekandsundry.com/tabletop-bonus-wils-final-thoughts-on-dread/',
            'info_dict': {
                'id': '4238694884001',
                'ext': 'flv',
                'title': 'Tabletop: Dread, Last Thoughts',
                'description': 'Tabletop: Dread, Last Thoughts',
                'duration': 51690,
            },
        },
        # Brightcove embed, with no valid 'renditions' but valid 'IOSRenditions'
        # This video can't be played in browsers if Flash disabled and UA set to iPhone, which is actually a false alarm
        {
            'url': 'https://dl.dropboxusercontent.com/u/29092637/interview.html',
            'info_dict': {
                'id': '4785848093001',
                'ext': 'mp4',
                'title': 'The Cardinal Pell Interview',
                'description': 'Sky News Contributor Andrew Bolt interviews George Pell in Rome, following the Cardinal\'s evidence before the Royal Commission into Child Abuse. ',
                'uploader': 'GlobeCast Australia - GlobeStream',
                'uploader_id': '2733773828001',
                'upload_date': '20160304',
                'timestamp': 1457083087,
            },
            'params': {
                # m3u8 downloads
                'skip_download': True,
            },
        },
        {
            # Brightcove embed with whitespace around attribute names
            'url': 'http://www.stack.com/video/3167554373001/learn-to-hit-open-three-pointers-with-damian-lillard-s-baseline-drift-drill',
            'info_dict': {
                'id': '3167554373001',
                'ext': 'mp4',
                'title': "Learn to Hit Open Three-Pointers With Damian Lillard's Baseline Drift Drill",
                'description': 'md5:57bacb0e0f29349de4972bfda3191713',
                'uploader_id': '1079349493',
                'upload_date': '20140207',
                'timestamp': 1391810548,
            },
            'params': {
                'skip_download': True,
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
            'add_ie': ['BrightcoveLegacy'],
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
            'add_ie': [ArkenaIE.ie_key()],
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
            'add_ie': [Vbox7IE.ie_key()],
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
            'add_ie': [TwentyMinutenIE.ie_key()],
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
            'add_ie': [VideoPressIE.ie_key()],
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
            'add_ie': [RutubeIE.ie_key()],
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
            }]
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
            'add_ie': [SenateISVPIE.ie_key()],
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
            'add_ie': [WashingtonPostIE.ie_key()],
        },
        {
            # Mediaset embed
            'url': 'http://www.tgcom24.mediaset.it/politica/serracchiani-voglio-vivere-in-una-societa-aperta-reazioni-sproporzionate-_3071354-201702a.shtml',
            'info_dict': {
                'id': '720642',
                'ext': 'mp4',
                'title': 'Serracchiani: "Voglio vivere in una società aperta, con tutela del patto di fiducia"',
            },
            'params': {
                'skip_download': True,
            },
            'add_ie': [MediasetIE.ie_key()],
        },
        {
            # JOJ.sk embeds
            'url': 'https://www.noviny.sk/slovensko/238543-slovenskom-sa-prehnala-vlna-silnych-burok',
            'info_dict': {
                'id': '238543-slovenskom-sa-prehnala-vlna-silnych-burok',
                'title': 'Slovenskom sa prehnala vlna silných búrok',
            },
            'playlist_mincount': 5,
            'add_ie': [JojIE.ie_key()],
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
            # vzaar embed
            'url': 'http://help.vzaar.com/article/165-embedding-video',
            'md5': '7e3919d9d2620b89e3e00bec7fe8c9d4',
            'info_dict': {
                'id': '8707641',
                'ext': 'mp4',
                'title': 'Building A Business Online: Principal Chairs Q & A',
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
            }
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
            }
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
            'add_ie': [SpringboardPlatformIE.ie_key()],
        },
        {
            'url': 'https://www.yapfiles.ru/show/1872528/690b05d3054d2dbe1e69523aa21bb3b1.mp4.html',
            'info_dict': {
                'id': 'vMDE4NzI1Mjgt690b',
                'ext': 'mp4',
                'title': 'Котята',
            },
            'add_ie': [YapFilesIE.ie_key()],
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
            'add_ie': [CloudflareStreamIE.ie_key()],
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
            'add_ie': [IndavideoEmbedIE.ie_key()],
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
                'ext': 'mp4'
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
        {
            # Squarespace video embed, 2019-08-28
            'url': 'http://ootboxford.com',
            'info_dict': {
                'id': 'Tc7b_JGdZfw',
                'title': 'Out of the Blue, at Childish Things 10',
                'ext': 'mp4',
                'description': 'md5:a83d0026666cf5ee970f8bd1cfd69c7f',
                'uploader_id': 'helendouglashouse',
                'uploader': 'Helen & Douglas House',
                'upload_date': '20140328',
            },
            'params': {
                'skip_download': True,
            },
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

            }
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
        },
        {
            # Sibnet embed (https://help.sibnet.ru/?sibnet_video_embed)
            'url': 'https://phpbb3.x-tk.ru/bbcode-video-sibnet-t24.html',
            'only_matching': True,
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
                'thumbnail': 'https://kvs-demo.com/contents/videos_screenshots/0/105/preview.jpg',
            },
            'params': {
                'skip_download': True,
            },
        }, {
            # KVS Player
            'url': 'https://www.kvs-demo.com/embed/105/',
            'info_dict': {
                'id': '105',
                'display_id': 'kelis-4th-of-july',
                'ext': 'mp4',
                'title': 'Kelis - 4th Of July / Embed Player',
                'thumbnail': 'https://kvs-demo.com/contents/videos_screenshots/0/105/preview.jpg',
            },
            'params': {
                'skip_download': True,
            },
        }, {
            # KVS Player
            'url': 'https://thisvid.com/videos/french-boy-pantsed/',
            'md5': '3397979512c682f6b85b3b04989df224',
            'info_dict': {
                'id': '2400174',
                'display_id': 'french-boy-pantsed',
                'ext': 'mp4',
                'title': 'French Boy Pantsed - ThisVid.com',
                'thumbnail': 'https://media.thisvid.com/contents/videos_screenshots/2400000/2400174/preview.mp4.jpg',
            }
        }, {
            # KVS Player
            'url': 'https://thisvid.com/embed/2400174/',
            'md5': '3397979512c682f6b85b3b04989df224',
            'info_dict': {
                'id': '2400174',
                'display_id': 'french-boy-pantsed',
                'ext': 'mp4',
                'title': 'French Boy Pantsed - ThisVid.com',
                'thumbnail': 'https://media.thisvid.com/contents/videos_screenshots/2400000/2400174/preview.mp4.jpg',
            }
        }, {
            # KVS Player
            'url': 'https://youix.com/video/leningrad-zoj/',
            'md5': '94f96ba95706dc3880812b27b7d8a2b8',
            'info_dict': {
                'id': '18485',
                'display_id': 'leningrad-zoj',
                'ext': 'mp4',
                'title': 'Клип: Ленинград - ЗОЖ скачать, смотреть онлайн | Youix.com',
                'thumbnail': 'https://youix.com/contents/videos_screenshots/18000/18485/preview_480x320_youix_com.mp4.jpg',
            }
        }, {
            # KVS Player
            'url': 'https://youix.com/embed/18485',
            'md5': '94f96ba95706dc3880812b27b7d8a2b8',
            'info_dict': {
                'id': '18485',
                'display_id': 'leningrad-zoj',
                'ext': 'mp4',
                'title': 'Ленинград - ЗОЖ',
                'thumbnail': 'https://youix.com/contents/videos_screenshots/18000/18485/preview_480x320_youix_com.mp4.jpg',
            }
        }, {
            # KVS Player
            'url': 'https://bogmedia.org/videos/21217/40-nochey-40-nights-2016/',
            'md5': '94166bdb26b4cb1fb9214319a629fc51',
            'info_dict': {
                'id': '21217',
                'display_id': '40-nochey-40-nights-2016',
                'ext': 'mp4',
                'title': '40 ночей (2016) - BogMedia.org',
                'thumbnail': 'https://bogmedia.org/contents/videos_screenshots/21000/21217/preview_480p.mp4.jpg',
            }
        },
        {
            # KVS Player (for sites that serve kt_player.js via non-https urls)
            'url': 'http://www.camhub.world/embed/389508',
            'md5': 'fbe89af4cfb59c8fd9f34a202bb03e32',
            'info_dict': {
                'id': '389508',
                'display_id': 'syren-de-mer-onlyfans-05-07-2020have-a-happy-safe-holiday5f014e68a220979bdb8cd-source',
                'ext': 'mp4',
                'title': 'Syren De Mer  onlyfans_05-07-2020Have_a_happy_safe_holiday5f014e68a220979bdb8cd_source / Embed плеер',
                'thumbnail': 'http://www.camhub.world/contents/videos_screenshots/389000/389508/preview.mp4.jpg',
            }
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
                'uploader': 'Antw87'
            }
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
                'upload_date': '20211113'
            }
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
                'duration': 1512
            }
        },
        {
            # Multiple gfycat iframe embeds
            'url': 'https://www.gezip.net/bbs/board.php?bo_table=entertaine&wr_id=613422',
            'info_dict': {
                'title': '재이, 윤, 세은 황금 드레스를 입고 빛난다',
                'id': 'board'
            },
            'playlist_count': 8,
        },
        {
            # Multiple gfycat gifs (direct links)
            'url': 'https://www.gezip.net/bbs/board.php?bo_table=entertaine&wr_id=612199',
            'info_dict': {
                'title': '옳게 된 크롭 니트 스테이씨 아이사',
                'id': 'board'
            },
            'playlist_count': 6
        },
        {
            # Multiple gfycat embeds, with uppercase "IFR" in urls
            'url': 'https://kkzz.kr/?vid=2295',
            'info_dict': {
                'title': '지방시 앰버서더 에스파 카리나 움짤',
                'id': '?vid=2295'
            },
            'playlist_count': 9
        },
        {
            # Panopto embeds
            'url': 'https://www.monash.edu/learning-teaching/teachhq/learning-technologies/panopto/how-to/insert-a-quiz-into-a-panopto-video',
            'info_dict': {
                'title': 'Insert a quiz into a Panopto video',
                'id': 'insert-a-quiz-into-a-panopto-video'
            },
            'playlist_count': 1
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
                'id': 'art-2000008762560'
            },
            'playlist_count': 3
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
            }
        }
    ]

    def report_following_redirect(self, new_url):
        """Report information extraction."""
        self._downloader.to_screen('[redirect] Following redirect to %s' % new_url)

    def report_detected(self, name):
        self._downloader.write_debug(f'Identified a {name}')

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

    def _extract_camtasia(self, url, video_id, webpage):
        """ Returns None if no camtasia video can be found. """

        camtasia_cfg = self._search_regex(
            r'fo\.addVariable\(\s*"csConfigFile",\s*"([^"]+)"\s*\);',
            webpage, 'camtasia configuration file', default=None)
        if camtasia_cfg is None:
            return None

        title = self._html_search_meta('DC.title', webpage, fatal=True)

        camtasia_url = compat_urlparse.urljoin(url, camtasia_cfg)
        camtasia_cfg = self._download_xml(
            camtasia_url, video_id,
            note='Downloading camtasia configuration',
            errnote='Failed to download camtasia configuration')
        fileset_node = camtasia_cfg.find('./playlist/array/fileset')

        entries = []
        for n in fileset_node.getchildren():
            url_n = n.find('./uri')
            if url_n is None:
                continue

            entries.append({
                'id': os.path.splitext(url_n.text.rpartition('/')[2])[0],
                'title': f'{title} - {n.tag}',
                'url': compat_urlparse.urljoin(url, url_n.text),
                'duration': float_or_none(n.find('./duration').text),
            })

        return {
            '_type': 'playlist',
            'entries': entries,
            'title': title,
        }

    def _kvs_getrealurl(self, video_url, license_code):
        if not video_url.startswith('function/0/'):
            return video_url  # not obfuscated

        url_path, _, url_query = video_url.partition('?')
        urlparts = url_path.split('/')[2:]
        license = self._kvs_getlicensetoken(license_code)
        newmagic = urlparts[5][:32]

        for o in range(len(newmagic) - 1, -1, -1):
            new = ''
            l = (o + sum(int(n) for n in license[o:])) % 32

            for i in range(0, len(newmagic)):
                if i == o:
                    new += newmagic[l]
                elif i == l:
                    new += newmagic[o]
                else:
                    new += newmagic[i]
            newmagic = new

        urlparts[5] = newmagic + urlparts[5][32:]
        return '/'.join(urlparts) + '?' + url_query

    def _kvs_getlicensetoken(self, license):
        modlicense = license.replace('$', '').replace('0', '1')
        center = int(len(modlicense) / 2)
        fronthalf = int(modlicense[:center + 1])
        backhalf = int(modlicense[center:])

        modlicense = str(4 * abs(fronthalf - backhalf))
        retval = ''
        for o in range(0, center + 1):
            for i in range(1, 5):
                retval += str((int(license[o + i]) + int(modlicense[o])) % 10)
        return retval

    def _real_extract(self, url):
        if url.startswith('//'):
            return self.url_result(self.http_scheme() + url)

        parsed_url = compat_urlparse.urlparse(url)
        if not parsed_url.scheme:
            default_search = self.get_param('default_search')
            if default_search is None:
                default_search = 'fixup_error'

            if default_search in ('auto', 'auto_warning', 'fixup_error'):
                if re.match(r'^[^\s/]+\.[^\s/]+/', url):
                    self.report_warning('The url doesn\'t specify the protocol, trying with http')
                    return self.url_result('http://' + url)
                elif default_search != 'fixup_error':
                    if default_search == 'auto_warning':
                        if re.match(r'^(?:url|URL)$', url):
                            raise ExtractorError(
                                'Invalid URL:  %r . Call yt-dlp like this:  yt-dlp -v "https://www.youtube.com/watch?v=BaW_jenozKc"  ' % url,
                                expected=True)
                        else:
                            self.report_warning(
                                'Falling back to youtube search for  %s . Set --default-search "auto" to suppress this warning.' % url)
                    return self.url_result('ytsearch:' + url)

            if default_search in ('error', 'fixup_error'):
                raise ExtractorError(
                    '%r is not a valid URL. '
                    'Set --default-search "ytsearch" (or run  yt-dlp "ytsearch:%s" ) to search YouTube'
                    % (url, url), expected=True)
            else:
                if ':' not in default_search:
                    default_search += ':'
                return self.url_result(default_search + url)

        url, smuggled_data = unsmuggle_url(url)
        force_videoid = None
        is_intentional = smuggled_data and smuggled_data.get('to_generic')
        if smuggled_data and 'force_videoid' in smuggled_data:
            force_videoid = smuggled_data['force_videoid']
            video_id = force_videoid
        else:
            video_id = self._generic_id(url)

        self.to_screen('%s: Requesting header' % video_id)

        head_req = HEADRequest(url)
        head_response = self._request_webpage(
            head_req, video_id,
            note=False, errnote='Could not send HEAD request to %s' % url,
            fatal=False)

        if head_response is not False:
            # Check for redirect
            new_url = head_response.geturl()
            if url != new_url:
                self.report_following_redirect(new_url)
                if force_videoid:
                    new_url = smuggle_url(
                        new_url, {'force_videoid': force_videoid})
                return self.url_result(new_url)

        full_response = None
        if head_response is False:
            request = sanitized_Request(url)
            request.add_header('Accept-Encoding', '*')
            full_response = self._request_webpage(request, video_id)
            head_response = full_response

        info_dict = {
            'id': video_id,
            'title': self._generic_title(url),
            'timestamp': unified_timestamp(head_response.headers.get('Last-Modified'))
        }

        # Check for direct link to a video
        content_type = head_response.headers.get('Content-Type', '').lower()
        m = re.match(r'^(?P<type>audio|video|application(?=/(?:ogg$|(?:vnd\.apple\.|x-)?mpegurl)))/(?P<format_id>[^;\s]+)', content_type)
        if m:
            self.report_detected('direct video link')
            format_id = compat_str(m.group('format_id'))
            subtitles = {}
            if format_id.endswith('mpegurl'):
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(url, video_id, 'mp4')
            elif format_id.endswith('mpd') or format_id.endswith('dash+xml'):
                formats, subtitles = self._extract_mpd_formats_and_subtitles(url, video_id)
            elif format_id == 'f4m':
                formats = self._extract_f4m_formats(url, video_id)
            else:
                formats = [{
                    'format_id': format_id,
                    'url': url,
                    'vcodec': 'none' if m.group('type') == 'audio' else None
                }]
                info_dict['direct'] = True
            self._sort_formats(formats)
            info_dict['formats'] = formats
            info_dict['subtitles'] = subtitles
            return info_dict

        if not self.get_param('test', False) and not is_intentional:
            force = self.get_param('force_generic_extractor', False)
            self.report_warning(
                '%s on generic information extractor.' % ('Forcing' if force else 'Falling back'))

        if not full_response:
            request = sanitized_Request(url)
            # Some webservers may serve compressed content of rather big size (e.g. gzipped flac)
            # making it impossible to download only chunk of the file (yet we need only 512kB to
            # test whether it's HTML or not). According to yt-dlp default Accept-Encoding
            # that will always result in downloading the whole file that is not desirable.
            # Therefore for extraction pass we have to override Accept-Encoding to any in order
            # to accept raw bytes and being able to download only a chunk.
            # It may probably better to solve this by checking Content-Type for application/octet-stream
            # after HEAD request finishes, but not sure if we can rely on this.
            request.add_header('Accept-Encoding', '*')
            full_response = self._request_webpage(request, video_id)

        first_bytes = full_response.read(512)

        # Is it an M3U playlist?
        if first_bytes.startswith(b'#EXTM3U'):
            self.report_detected('M3U playlist')
            info_dict['formats'], info_dict['subtitles'] = self._extract_m3u8_formats_and_subtitles(url, video_id, 'mp4')
            self._sort_formats(info_dict['formats'])
            return info_dict

        # Maybe it's a direct link to a video?
        # Be careful not to download the whole thing!
        if not is_html(first_bytes):
            self.report_warning(
                'URL could be a direct video link, returning it as such.')
            info_dict.update({
                'direct': True,
                'url': url,
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
                doc = compat_etree_fromstring(webpage.encode('utf-8'))
            if doc.tag == 'rss':
                self.report_detected('RSS feed')
                return self._extract_rss(url, video_id, doc)
            elif doc.tag == 'SmoothStreamingMedia':
                info_dict['formats'], info_dict['subtitles'] = self._parse_ism_formats_and_subtitles(doc, url)
                self.report_detected('ISM manifest')
                self._sort_formats(info_dict['formats'])
                return info_dict
            elif re.match(r'^(?:{[^}]+})?smil$', doc.tag):
                smil = self._parse_smil(doc, url, video_id)
                self.report_detected('SMIL file')
                self._sort_formats(smil['formats'])
                return smil
            elif doc.tag == '{http://xspf.org/ns/0/}playlist':
                self.report_detected('XSPF playlist')
                return self.playlist_result(
                    self._parse_xspf(
                        doc, video_id, xspf_url=url,
                        xspf_base_url=full_response.geturl()),
                    video_id)
            elif re.match(r'(?i)^(?:{[^}]+})?MPD$', doc.tag):
                info_dict['formats'], info_dict['subtitles'] = self._parse_mpd_formats_and_subtitles(
                    doc,
                    mpd_base_url=full_response.geturl().rpartition('/')[0],
                    mpd_url=url)
                self.report_detected('DASH manifest')
                self._sort_formats(info_dict['formats'])
                return info_dict
            elif re.match(r'^{http://ns\.adobe\.com/f4m/[12]\.0}manifest$', doc.tag):
                info_dict['formats'] = self._parse_f4m_formats(doc, url, video_id)
                self.report_detected('F4M manifest')
                self._sort_formats(info_dict['formats'])
                return info_dict
        except xml.etree.ElementTree.ParseError:
            pass

        # Is it a Camtasia project?
        camtasia_res = self._extract_camtasia(url, video_id, webpage)
        if camtasia_res is not None:
            self.report_detected('Camtasia video')
            return camtasia_res

        # Sometimes embedded video player is hidden behind percent encoding
        # (e.g. https://github.com/ytdl-org/youtube-dl/issues/2448)
        # Unescaping the whole page allows to handle those cases in a generic way
        # FIXME: unescaping the whole page may break URLs, commenting out for now.
        # There probably should be a second run of generic extractor on unescaped webpage.
        # webpage = compat_urllib_parse_unquote(webpage)

        # Unescape squarespace embeds to be detected by generic extractor,
        # see https://github.com/ytdl-org/youtube-dl/issues/21294
        webpage = re.sub(
            r'<div[^>]+class=[^>]*?\bsqs-video-wrapper\b[^>]*>',
            lambda x: unescapeHTML(x.group(0)), webpage)

        # it's tempting to parse this further, but you would
        # have to take into account all the variations like
        #   Video Title - Site Name
        #   Site Name | Video Title
        #   Video Title - Tagline | Site Name
        # and so on and so forth; it's just not practical
        video_title = (self._og_search_title(webpage, default=None)
                       or self._html_extract_title(webpage, 'video title', default='video'))

        # Try to detect age limit automatically
        age_limit = self._rta_search(webpage)
        # And then there are the jokers who advertise that they use RTA,
        # but actually don't.
        AGE_LIMIT_MARKERS = [
            r'Proudly Labeled <a href="http://www\.rtalabel\.org/" title="Restricted to Adults">RTA</a>',
        ]
        if any(re.search(marker, webpage) for marker in AGE_LIMIT_MARKERS):
            age_limit = 18

        # video uploader is domain name
        video_uploader = self._search_regex(
            r'^(?:https?://)?([^/]*)/.*', url, 'video uploader')

        video_description = self._og_search_description(webpage, default=None)
        video_thumbnail = self._og_search_thumbnail(webpage, default=None)

        info_dict.update({
            'title': video_title,
            'description': video_description,
            'thumbnail': video_thumbnail,
            'age_limit': age_limit,
        })

        self._downloader.write_debug('Looking for video embeds')

        # Look for Brightcove Legacy Studio embeds
        bc_urls = BrightcoveLegacyIE._extract_brightcove_urls(webpage)
        if bc_urls:
            entries = [{
                '_type': 'url',
                'url': smuggle_url(bc_url, {'Referer': url}),
                'ie_key': 'BrightcoveLegacy'
            } for bc_url in bc_urls]

            return {
                '_type': 'playlist',
                'title': video_title,
                'id': video_id,
                'entries': entries,
            }

        # Look for Brightcove New Studio embeds
        bc_urls = BrightcoveNewIE._extract_urls(self, webpage)
        if bc_urls:
            return self.playlist_from_matches(
                bc_urls, video_id, video_title,
                getter=lambda x: smuggle_url(x, {'referrer': url}),
                ie='BrightcoveNew')

        # Look for Nexx embeds
        nexx_urls = NexxIE._extract_urls(webpage)
        if nexx_urls:
            return self.playlist_from_matches(nexx_urls, video_id, video_title, ie=NexxIE.ie_key())

        # Look for Nexx iFrame embeds
        nexx_embed_urls = NexxEmbedIE._extract_urls(webpage)
        if nexx_embed_urls:
            return self.playlist_from_matches(nexx_embed_urls, video_id, video_title, ie=NexxEmbedIE.ie_key())

        # Look for ThePlatform embeds
        tp_urls = ThePlatformIE._extract_urls(webpage)
        if tp_urls:
            return self.playlist_from_matches(tp_urls, video_id, video_title, ie='ThePlatform')

        arc_urls = ArcPublishingIE._extract_urls(webpage)
        if arc_urls:
            return self.playlist_from_matches(arc_urls, video_id, video_title, ie=ArcPublishingIE.ie_key())

        mychannels_urls = MedialaanIE._extract_urls(webpage)
        if mychannels_urls:
            return self.playlist_from_matches(
                mychannels_urls, video_id, video_title, ie=MedialaanIE.ie_key())

        # Look for embedded rtl.nl player
        matches = re.findall(
            r'<iframe[^>]+?src="((?:https?:)?//(?:(?:www|static)\.)?rtl\.nl/(?:system/videoplayer/[^"]+(?:video_)?)?embed[^"]+)"',
            webpage)
        if matches:
            return self.playlist_from_matches(matches, video_id, video_title, ie='RtlNl')

        vimeo_urls = VimeoIE._extract_urls(url, webpage)
        if vimeo_urls:
            return self.playlist_from_matches(vimeo_urls, video_id, video_title, ie=VimeoIE.ie_key())

        vhx_url = VHXEmbedIE._extract_url(url, webpage)
        if vhx_url:
            return self.url_result(vhx_url, VHXEmbedIE.ie_key())

        # Invidious Instances
        # https://github.com/yt-dlp/yt-dlp/issues/195
        # https://github.com/iv-org/invidious/pull/1730
        youtube_url = self._search_regex(
            r'<link rel="alternate" href="(https://www\.youtube\.com/watch\?v=[0-9A-Za-z_-]{11})"',
            webpage, 'youtube link', default=None)
        if youtube_url:
            return self.url_result(youtube_url, YoutubeIE.ie_key())

        # Look for YouTube embeds
        youtube_urls = YoutubeIE._extract_urls(webpage)
        if youtube_urls:
            return self.playlist_from_matches(
                youtube_urls, video_id, video_title, ie=YoutubeIE.ie_key())

        matches = DailymotionIE._extract_urls(webpage)
        if matches:
            return self.playlist_from_matches(matches, video_id, video_title)

        # Look for embedded Dailymotion playlist player (#3822)
        m = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?dailymotion\.[a-z]{2,3}/widget/jukebox\?.+?)\1', webpage)
        if m:
            playlists = re.findall(
                r'list\[\]=/playlist/([^/]+)/', unescapeHTML(m.group('url')))
            if playlists:
                return self.playlist_from_matches(
                    playlists, video_id, video_title, lambda p: '//dailymotion.com/playlist/%s' % p)

        # Look for DailyMail embeds
        dailymail_urls = DailyMailIE._extract_urls(webpage)
        if dailymail_urls:
            return self.playlist_from_matches(
                dailymail_urls, video_id, video_title, ie=DailyMailIE.ie_key())

        # Look for Teachable embeds, must be before Wistia
        teachable_url = TeachableIE._extract_url(webpage, url)
        if teachable_url:
            return self.url_result(teachable_url)

        # Look for embedded Wistia player
        wistia_urls = WistiaIE._extract_urls(webpage)
        if wistia_urls:
            playlist = self.playlist_from_matches(wistia_urls, video_id, video_title, ie=WistiaIE.ie_key())
            for entry in playlist['entries']:
                entry.update({
                    '_type': 'url_transparent',
                    'uploader': video_uploader,
                })
            return playlist

        # Look for SVT player
        svt_url = SVTIE._extract_url(webpage)
        if svt_url:
            return self.url_result(svt_url, 'SVT')

        # Look for Bandcamp pages with custom domain
        mobj = re.search(r'<meta property="og:url"[^>]*?content="(.*?bandcamp\.com.*?)"', webpage)
        if mobj is not None:
            burl = unescapeHTML(mobj.group(1))
            # Don't set the extractor because it can be a track url or an album
            return self.url_result(burl)

        # Look for embedded Vevo player
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:cache\.)?vevo\.com/.+?)\1', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'))

        # Look for embedded Viddler player
        mobj = re.search(
            r'<(?:iframe[^>]+?src|param[^>]+?value)=(["\'])(?P<url>(?:https?:)?//(?:www\.)?viddler\.com/(?:embed|player)/.+?)\1',
            webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'))

        # Look for NYTimes player
        mobj = re.search(
            r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//graphics8\.nytimes\.com/bcvideo/[^/]+/iframe/embed\.html.+?)\1>',
            webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'))

        # Look for Libsyn player
        mobj = re.search(
            r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//html5-player\.libsyn\.com/embed/.+?)\1', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'))

        # Look for Ooyala videos
        mobj = (re.search(r'player\.ooyala\.com/[^"?]+[?#][^"]*?(?:embedCode|ec)=(?P<ec>[^"&]+)', webpage)
                or re.search(r'OO\.Player\.create\([\'"].*?[\'"],\s*[\'"](?P<ec>.{32})[\'"]', webpage)
                or re.search(r'OO\.Player\.create\.apply\(\s*OO\.Player\s*,\s*op\(\s*\[\s*[\'"][^\'"]*[\'"]\s*,\s*[\'"](?P<ec>.{32})[\'"]', webpage)
                or re.search(r'SBN\.VideoLinkset\.ooyala\([\'"](?P<ec>.{32})[\'"]\)', webpage)
                or re.search(r'data-ooyala-video-id\s*=\s*[\'"](?P<ec>.{32})[\'"]', webpage))
        if mobj is not None:
            embed_token = self._search_regex(
                r'embedToken[\'"]?\s*:\s*[\'"]([^\'"]+)',
                webpage, 'ooyala embed token', default=None)
            return OoyalaIE._build_url_result(smuggle_url(
                mobj.group('ec'), {
                    'domain': url,
                    'embed_token': embed_token,
                }))

        # Look for multiple Ooyala embeds on SBN network websites
        mobj = re.search(r'SBN\.VideoLinkset\.entryGroup\((\[.*?\])', webpage)
        if mobj is not None:
            embeds = self._parse_json(mobj.group(1), video_id, fatal=False)
            if embeds:
                return self.playlist_from_matches(
                    embeds, video_id, video_title,
                    getter=lambda v: OoyalaIE._url_for_embed_code(smuggle_url(v['provider_video_id'], {'domain': url})), ie='Ooyala')

        # Look for Aparat videos
        mobj = re.search(r'<iframe .*?src="(http://www\.aparat\.com/video/[^"]+)"', webpage)
        if mobj is not None:
            return self.url_result(mobj.group(1), 'Aparat')

        # Look for MPORA videos
        mobj = re.search(r'<iframe .*?src="(http://mpora\.(?:com|de)/videos/[^"]+)"', webpage)
        if mobj is not None:
            return self.url_result(mobj.group(1), 'Mpora')

        # Look for embedded Facebook player
        facebook_urls = FacebookIE._extract_urls(webpage)
        if facebook_urls:
            return self.playlist_from_matches(facebook_urls, video_id, video_title)

        # Look for embedded VK player
        mobj = re.search(r'<iframe[^>]+?src=(["\'])(?P<url>https?://vk\.com/video_ext\.php.+?)\1', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'VK')

        # Look for embedded Odnoklassniki player
        odnoklassniki_url = OdnoklassnikiIE._extract_url(webpage)
        if odnoklassniki_url:
            return self.url_result(odnoklassniki_url, OdnoklassnikiIE.ie_key())

        # Look for sibnet embedded player
        sibnet_urls = VKIE._extract_sibnet_urls(webpage)
        if sibnet_urls:
            return self.playlist_from_matches(sibnet_urls, video_id, video_title)

        # Look for embedded ivi player
        mobj = re.search(r'<embed[^>]+?src=(["\'])(?P<url>https?://(?:www\.)?ivi\.ru/video/player.+?)\1', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'Ivi')

        # Look for embedded Huffington Post player
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>https?://embed\.live\.huffingtonpost\.com/.+?)\1', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'HuffPost')

        # Look for embed.ly
        mobj = re.search(r'class=["\']embedly-card["\'][^>]href=["\'](?P<url>[^"\']+)', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'))
        mobj = re.search(r'class=["\']embedly-embed["\'][^>]src=["\'][^"\']*url=(?P<url>[^&]+)', webpage)
        if mobj is not None:
            return self.url_result(compat_urllib_parse_unquote(mobj.group('url')))

        # Look for funnyordie embed
        matches = re.findall(r'<iframe[^>]+?src="(https?://(?:www\.)?funnyordie\.com/embed/[^"]+)"', webpage)
        if matches:
            return self.playlist_from_matches(
                matches, video_id, video_title, getter=unescapeHTML, ie='FunnyOrDie')

        # Look for Simplecast embeds
        simplecast_urls = SimplecastIE._extract_urls(webpage)
        if simplecast_urls:
            return self.playlist_from_matches(
                simplecast_urls, video_id, video_title)

        # Look for BBC iPlayer embed
        matches = re.findall(r'setPlaylist\("(https?://www\.bbc\.co\.uk/iplayer/[^/]+/[\da-z]{8})"\)', webpage)
        if matches:
            return self.playlist_from_matches(matches, video_id, video_title, ie='BBCCoUk')

        # Look for embedded RUTV player
        rutv_url = RUTVIE._extract_url(webpage)
        if rutv_url:
            return self.url_result(rutv_url, 'RUTV')

        # Look for embedded TVC player
        tvc_url = TVCIE._extract_url(webpage)
        if tvc_url:
            return self.url_result(tvc_url, 'TVC')

        # Look for embedded SportBox player
        sportbox_urls = SportBoxIE._extract_urls(webpage)
        if sportbox_urls:
            return self.playlist_from_matches(sportbox_urls, video_id, video_title, ie=SportBoxIE.ie_key())

        # Look for embedded Spotify player
        spotify_urls = SpotifyBaseIE._extract_embed_urls(webpage)
        if spotify_urls:
            return self.playlist_from_matches(spotify_urls, video_id, video_title)

        # Look for embedded XHamster player
        xhamster_urls = XHamsterEmbedIE._extract_urls(webpage)
        if xhamster_urls:
            return self.playlist_from_matches(xhamster_urls, video_id, video_title, ie='XHamsterEmbed')

        # Look for embedded TNAFlixNetwork player
        tnaflix_urls = TNAFlixNetworkEmbedIE._extract_urls(webpage)
        if tnaflix_urls:
            return self.playlist_from_matches(tnaflix_urls, video_id, video_title, ie=TNAFlixNetworkEmbedIE.ie_key())

        # Look for embedded PornHub player
        pornhub_urls = PornHubIE._extract_urls(webpage)
        if pornhub_urls:
            return self.playlist_from_matches(pornhub_urls, video_id, video_title, ie=PornHubIE.ie_key())

        # Look for embedded DrTuber player
        drtuber_urls = DrTuberIE._extract_urls(webpage)
        if drtuber_urls:
            return self.playlist_from_matches(drtuber_urls, video_id, video_title, ie=DrTuberIE.ie_key())

        # Look for embedded RedTube player
        redtube_urls = RedTubeIE._extract_urls(webpage)
        if redtube_urls:
            return self.playlist_from_matches(redtube_urls, video_id, video_title, ie=RedTubeIE.ie_key())

        # Look for embedded Tube8 player
        tube8_urls = Tube8IE._extract_urls(webpage)
        if tube8_urls:
            return self.playlist_from_matches(tube8_urls, video_id, video_title, ie=Tube8IE.ie_key())

        # Look for embedded Mofosex player
        mofosex_urls = MofosexEmbedIE._extract_urls(webpage)
        if mofosex_urls:
            return self.playlist_from_matches(mofosex_urls, video_id, video_title, ie=MofosexEmbedIE.ie_key())

        # Look for embedded Spankwire player
        spankwire_urls = SpankwireIE._extract_urls(webpage)
        if spankwire_urls:
            return self.playlist_from_matches(spankwire_urls, video_id, video_title, ie=SpankwireIE.ie_key())

        # Look for embedded YouPorn player
        youporn_urls = YouPornIE._extract_urls(webpage)
        if youporn_urls:
            return self.playlist_from_matches(youporn_urls, video_id, video_title, ie=YouPornIE.ie_key())

        # Look for embedded Tvigle player
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//cloud\.tvigle\.ru/video/.+?)\1', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'Tvigle')

        # Look for embedded TED player
        ted_urls = TedEmbedIE._extract_urls(webpage)
        if ted_urls:
            return self.playlist_from_matches(ted_urls, video_id, video_title, ie=TedEmbedIE.ie_key())

        # Look for embedded Ustream videos
        ustream_url = UstreamIE._extract_url(webpage)
        if ustream_url:
            return self.url_result(ustream_url, UstreamIE.ie_key())

        # Look for embedded arte.tv player
        arte_urls = ArteTVEmbedIE._extract_urls(webpage)
        if arte_urls:
            return self.playlist_from_matches(arte_urls, video_id, video_title)

        # Look for embedded francetv player
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?://)?embed\.francetv\.fr/\?ue=.+?)\1',
            webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'))

        # Look for embedded Myvi.ru player
        myvi_url = MyviIE._extract_url(webpage)
        if myvi_url:
            return self.url_result(myvi_url)

        # Look for embedded soundcloud player
        soundcloud_urls = SoundcloudEmbedIE._extract_urls(webpage)
        if soundcloud_urls:
            return self.playlist_from_matches(soundcloud_urls, video_id, video_title, getter=unescapeHTML)

        # Look for tunein player
        tunein_urls = TuneInBaseIE._extract_urls(webpage)
        if tunein_urls:
            return self.playlist_from_matches(tunein_urls, video_id, video_title)

        # Look for embedded mtvservices player
        mtvservices_url = MTVServicesEmbeddedIE._extract_url(webpage)
        if mtvservices_url:
            return self.url_result(mtvservices_url, ie='MTVServicesEmbedded')

        # Look for embedded yahoo player
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>https?://(?:screen|movies)\.yahoo\.com/.+?\.html\?format=embed)\1',
            webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'Yahoo')

        # Look for embedded sbs.com.au player
        mobj = re.search(
            r'''(?x)
            (?:
                <meta\s+property="og:video"\s+content=|
                <iframe[^>]+?src=
            )
            (["\'])(?P<url>https?://(?:www\.)?sbs\.com\.au/ondemand/video/.+?)\1''',
            webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'SBS')

        # Look for embedded Cinchcast player
        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>https?://player\.cinchcast\.com/.+?)\1',
            webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'Cinchcast')

        mobj = re.search(
            r'<iframe[^>]+?src=(["\'])(?P<url>https?://m(?:lb)?\.mlb\.com/shared/video/embed/embed\.html\?.+?)\1',
            webpage)
        if not mobj:
            mobj = re.search(
                r'data-video-link=["\'](?P<url>http://m\.mlb\.com/video/[^"\']+)',
                webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'MLB')

        mobj = re.search(
            r'<(?:iframe|script)[^>]+?src=(["\'])(?P<url>%s)\1' % CondeNastIE.EMBED_URL,
            webpage)
        if mobj is not None:
            return self.url_result(self._proto_relative_url(mobj.group('url'), scheme='http:'), 'CondeNast')

        mobj = re.search(
            r'<iframe[^>]+src="(?P<url>https?://(?:new\.)?livestream\.com/[^"]+/player[^"]+)"',
            webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'Livestream')

        # Look for Zapiks embed
        mobj = re.search(
            r'<iframe[^>]+src="(?P<url>https?://(?:www\.)?zapiks\.fr/index\.php\?.+?)"', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'), 'Zapiks')

        # Look for Kaltura embeds
        kaltura_urls = KalturaIE._extract_urls(webpage)
        if kaltura_urls:
            return self.playlist_from_matches(
                kaltura_urls, video_id, video_title,
                getter=lambda x: smuggle_url(x, {'source_url': url}),
                ie=KalturaIE.ie_key())

        # Look for EaglePlatform embeds
        eagleplatform_url = EaglePlatformIE._extract_url(webpage)
        if eagleplatform_url:
            return self.url_result(smuggle_url(eagleplatform_url, {'referrer': url}), EaglePlatformIE.ie_key())

        # Look for ClipYou (uses EaglePlatform) embeds
        mobj = re.search(
            r'<iframe[^>]+src="https?://(?P<host>media\.clipyou\.ru)/index/player\?.*\brecord_id=(?P<id>\d+).*"', webpage)
        if mobj is not None:
            return self.url_result('eagleplatform:%(host)s:%(id)s' % mobj.groupdict(), 'EaglePlatform')

        # Look for Pladform embeds
        pladform_url = PladformIE._extract_url(webpage)
        if pladform_url:
            return self.url_result(pladform_url)

        # Look for Videomore embeds
        videomore_url = VideomoreIE._extract_url(webpage)
        if videomore_url:
            return self.url_result(videomore_url)

        # Look for Webcaster embeds
        webcaster_url = WebcasterFeedIE._extract_url(self, webpage)
        if webcaster_url:
            return self.url_result(webcaster_url, ie=WebcasterFeedIE.ie_key())

        # Look for Playwire embeds
        mobj = re.search(
            r'<script[^>]+data-config=(["\'])(?P<url>(?:https?:)?//config\.playwire\.com/.+?)\1', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'))

        # Look for Crooks and Liars embeds
        mobj = re.search(
            r'<(?:iframe[^>]+src|param[^>]+value)=(["\'])(?P<url>(?:https?:)?//embed\.crooksandliars\.com/(?:embed|v)/.+?)\1', webpage)
        if mobj is not None:
            return self.url_result(mobj.group('url'))

        # Look for NBC Sports VPlayer embeds
        nbc_sports_url = NBCSportsVPlayerIE._extract_url(webpage)
        if nbc_sports_url:
            return self.url_result(nbc_sports_url, 'NBCSportsVPlayer')

        # Look for NBC News embeds
        nbc_news_embed_url = re.search(
            r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//www\.nbcnews\.com/widget/video-embed/[^"\']+)\1', webpage)
        if nbc_news_embed_url:
            return self.url_result(nbc_news_embed_url.group('url'), 'NBCNews')

        # Look for Google Drive embeds
        google_drive_url = GoogleDriveIE._extract_url(webpage)
        if google_drive_url:
            return self.url_result(google_drive_url, 'GoogleDrive')

        # Look for UDN embeds
        mobj = re.search(
            r'<iframe[^>]+src="(?:https?:)?(?P<url>%s)"' % UDNEmbedIE._PROTOCOL_RELATIVE_VALID_URL, webpage)
        if mobj is not None:
            return self.url_result(
                compat_urlparse.urljoin(url, mobj.group('url')), 'UDNEmbed')

        # Look for Senate ISVP iframe
        senate_isvp_url = SenateISVPIE._search_iframe_url(webpage)
        if senate_isvp_url:
            return self.url_result(senate_isvp_url, 'SenateISVP')

        # Look for Kinja embeds
        kinja_embed_urls = KinjaEmbedIE._extract_urls(webpage, url)
        if kinja_embed_urls:
            return self.playlist_from_matches(
                kinja_embed_urls, video_id, video_title)

        # Look for OnionStudios embeds
        onionstudios_url = OnionStudiosIE._extract_url(webpage)
        if onionstudios_url:
            return self.url_result(onionstudios_url)

        # Look for Blogger embeds
        blogger_urls = BloggerIE._extract_urls(webpage)
        if blogger_urls:
            return self.playlist_from_matches(blogger_urls, video_id, video_title, ie=BloggerIE.ie_key())

        # Look for ViewLift embeds
        viewlift_url = ViewLiftEmbedIE._extract_url(webpage)
        if viewlift_url:
            return self.url_result(viewlift_url)

        # Look for JWPlatform embeds
        jwplatform_urls = JWPlatformIE._extract_urls(webpage)
        if jwplatform_urls:
            return self.playlist_from_matches(jwplatform_urls, video_id, video_title, ie=JWPlatformIE.ie_key())

        # Look for Digiteka embeds
        digiteka_url = DigitekaIE._extract_url(webpage)
        if digiteka_url:
            return self.url_result(self._proto_relative_url(digiteka_url), DigitekaIE.ie_key())

        # Look for Arkena embeds
        arkena_url = ArkenaIE._extract_url(webpage)
        if arkena_url:
            return self.url_result(arkena_url, ArkenaIE.ie_key())

        # Look for Piksel embeds
        piksel_url = PikselIE._extract_url(webpage)
        if piksel_url:
            return self.url_result(piksel_url, PikselIE.ie_key())

        # Look for Limelight embeds
        limelight_urls = LimelightBaseIE._extract_urls(webpage, url)
        if limelight_urls:
            return self.playlist_result(
                limelight_urls, video_id, video_title, video_description)

        # Look for Anvato embeds
        anvato_urls = AnvatoIE._extract_urls(self, webpage, video_id)
        if anvato_urls:
            return self.playlist_result(
                anvato_urls, video_id, video_title, video_description)

        # Look for AdobeTVVideo embeds
        mobj = re.search(
            r'<iframe[^>]+src=[\'"]((?:https?:)?//video\.tv\.adobe\.com/v/\d+[^"]+)[\'"]',
            webpage)
        if mobj is not None:
            return self.url_result(
                self._proto_relative_url(unescapeHTML(mobj.group(1))),
                'AdobeTVVideo')

        # Look for Vine embeds
        mobj = re.search(
            r'<iframe[^>]+src=[\'"]((?:https?:)?//(?:www\.)?vine\.co/v/[^/]+/embed/(?:simple|postcard))',
            webpage)
        if mobj is not None:
            return self.url_result(
                self._proto_relative_url(unescapeHTML(mobj.group(1))), 'Vine')

        # Look for VODPlatform embeds
        mobj = re.search(
            r'<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//(?:(?:www\.)?vod-platform\.net|embed\.kwikmotion\.com)/[eE]mbed/.+?)\1',
            webpage)
        if mobj is not None:
            return self.url_result(
                self._proto_relative_url(unescapeHTML(mobj.group('url'))), 'VODPlatform')

        # Look for Mangomolo embeds
        mobj = re.search(
            r'''(?x)<iframe[^>]+src=(["\'])(?P<url>(?:https?:)?//
                (?:
                    admin\.mangomolo\.com/analytics/index\.php/customers/embed|
                    player\.mangomolo\.com/v1
                )/
                (?:
                    video\?.*?\bid=(?P<video_id>\d+)|
                    (?:index|live)\?.*?\bchannelid=(?P<channel_id>(?:[A-Za-z0-9+/=]|%2B|%2F|%3D)+)
                ).+?)\1''', webpage)
        if mobj is not None:
            info = {
                '_type': 'url_transparent',
                'url': self._proto_relative_url(unescapeHTML(mobj.group('url'))),
                'title': video_title,
                'description': video_description,
                'thumbnail': video_thumbnail,
                'uploader': video_uploader,
            }
            video_id = mobj.group('video_id')
            if video_id:
                info.update({
                    'ie_key': 'MangomoloVideo',
                    'id': video_id,
                })
            else:
                info.update({
                    'ie_key': 'MangomoloLive',
                    'id': mobj.group('channel_id'),
                })
            return info

        # Look for Instagram embeds
        instagram_embed_url = InstagramIE._extract_embed_url(webpage)
        if instagram_embed_url is not None:
            return self.url_result(
                self._proto_relative_url(instagram_embed_url), InstagramIE.ie_key())

        # Look for 3Q SDN embeds
        threeqsdn_url = ThreeQSDNIE._extract_url(webpage)
        if threeqsdn_url:
            return {
                '_type': 'url_transparent',
                'ie_key': ThreeQSDNIE.ie_key(),
                'url': self._proto_relative_url(threeqsdn_url),
                'title': video_title,
                'description': video_description,
                'thumbnail': video_thumbnail,
                'uploader': video_uploader,
            }

        # Look for VBOX7 embeds
        vbox7_url = Vbox7IE._extract_url(webpage)
        if vbox7_url:
            return self.url_result(vbox7_url, Vbox7IE.ie_key())

        # Look for DBTV embeds
        dbtv_urls = DBTVIE._extract_urls(webpage)
        if dbtv_urls:
            return self.playlist_from_matches(dbtv_urls, video_id, video_title, ie=DBTVIE.ie_key())

        # Look for Videa embeds
        videa_urls = VideaIE._extract_urls(webpage)
        if videa_urls:
            return self.playlist_from_matches(videa_urls, video_id, video_title, ie=VideaIE.ie_key())

        # Look for 20 minuten embeds
        twentymin_urls = TwentyMinutenIE._extract_urls(webpage)
        if twentymin_urls:
            return self.playlist_from_matches(
                twentymin_urls, video_id, video_title, ie=TwentyMinutenIE.ie_key())

        # Look for VideoPress embeds
        videopress_urls = VideoPressIE._extract_urls(webpage)
        if videopress_urls:
            return self.playlist_from_matches(
                videopress_urls, video_id, video_title, ie=VideoPressIE.ie_key())

        # Look for Rutube embeds
        rutube_urls = RutubeIE._extract_urls(webpage)
        if rutube_urls:
            return self.playlist_from_matches(
                rutube_urls, video_id, video_title, ie=RutubeIE.ie_key())

        # Look for Glomex embeds
        glomex_urls = list(GlomexEmbedIE._extract_urls(webpage, url))
        if glomex_urls:
            return self.playlist_from_matches(
                glomex_urls, video_id, video_title, ie=GlomexEmbedIE.ie_key())

        # Look for megatv.com embeds
        megatvcom_urls = list(MegaTVComEmbedIE._extract_urls(webpage))
        if megatvcom_urls:
            return self.playlist_from_matches(
                megatvcom_urls, video_id, video_title, ie=MegaTVComEmbedIE.ie_key())

        # Look for ant1news.gr embeds
        ant1newsgr_urls = list(Ant1NewsGrEmbedIE._extract_urls(webpage))
        if ant1newsgr_urls:
            return self.playlist_from_matches(
                ant1newsgr_urls, video_id, video_title, ie=Ant1NewsGrEmbedIE.ie_key())

        # Look for WashingtonPost embeds
        wapo_urls = WashingtonPostIE._extract_urls(webpage)
        if wapo_urls:
            return self.playlist_from_matches(
                wapo_urls, video_id, video_title, ie=WashingtonPostIE.ie_key())

        # Look for Mediaset embeds
        mediaset_urls = MediasetIE._extract_urls(self, webpage)
        if mediaset_urls:
            return self.playlist_from_matches(
                mediaset_urls, video_id, video_title, ie=MediasetIE.ie_key())

        # Look for JOJ.sk embeds
        joj_urls = JojIE._extract_urls(webpage)
        if joj_urls:
            return self.playlist_from_matches(
                joj_urls, video_id, video_title, ie=JojIE.ie_key())

        # Look for megaphone.fm embeds
        mpfn_urls = MegaphoneIE._extract_urls(webpage)
        if mpfn_urls:
            return self.playlist_from_matches(
                mpfn_urls, video_id, video_title, ie=MegaphoneIE.ie_key())

        # Look for vzaar embeds
        vzaar_urls = VzaarIE._extract_urls(webpage)
        if vzaar_urls:
            return self.playlist_from_matches(
                vzaar_urls, video_id, video_title, ie=VzaarIE.ie_key())

        channel9_urls = Channel9IE._extract_urls(webpage)
        if channel9_urls:
            return self.playlist_from_matches(
                channel9_urls, video_id, video_title, ie=Channel9IE.ie_key())

        vshare_urls = VShareIE._extract_urls(webpage)
        if vshare_urls:
            return self.playlist_from_matches(
                vshare_urls, video_id, video_title, ie=VShareIE.ie_key())

        # Look for Mediasite embeds
        mediasite_urls = MediasiteIE._extract_urls(webpage)
        if mediasite_urls:
            entries = [
                self.url_result(smuggle_url(
                    compat_urlparse.urljoin(url, mediasite_url),
                    {'UrlReferrer': url}), ie=MediasiteIE.ie_key())
                for mediasite_url in mediasite_urls]
            return self.playlist_result(entries, video_id, video_title)

        springboardplatform_urls = SpringboardPlatformIE._extract_urls(webpage)
        if springboardplatform_urls:
            return self.playlist_from_matches(
                springboardplatform_urls, video_id, video_title,
                ie=SpringboardPlatformIE.ie_key())

        yapfiles_urls = YapFilesIE._extract_urls(webpage)
        if yapfiles_urls:
            return self.playlist_from_matches(
                yapfiles_urls, video_id, video_title, ie=YapFilesIE.ie_key())

        vice_urls = ViceIE._extract_urls(webpage)
        if vice_urls:
            return self.playlist_from_matches(
                vice_urls, video_id, video_title, ie=ViceIE.ie_key())

        xfileshare_urls = XFileShareIE._extract_urls(webpage)
        if xfileshare_urls:
            return self.playlist_from_matches(
                xfileshare_urls, video_id, video_title, ie=XFileShareIE.ie_key())

        cloudflarestream_urls = CloudflareStreamIE._extract_urls(webpage)
        if cloudflarestream_urls:
            return self.playlist_from_matches(
                cloudflarestream_urls, video_id, video_title, ie=CloudflareStreamIE.ie_key())

        peertube_urls = PeerTubeIE._extract_urls(webpage, url)
        if peertube_urls:
            return self.playlist_from_matches(
                peertube_urls, video_id, video_title, ie=PeerTubeIE.ie_key())

        indavideo_urls = IndavideoEmbedIE._extract_urls(webpage)
        if indavideo_urls:
            return self.playlist_from_matches(
                indavideo_urls, video_id, video_title, ie=IndavideoEmbedIE.ie_key())

        apa_urls = APAIE._extract_urls(webpage)
        if apa_urls:
            return self.playlist_from_matches(
                apa_urls, video_id, video_title, ie=APAIE.ie_key())

        foxnews_urls = FoxNewsIE._extract_urls(webpage)
        if foxnews_urls:
            return self.playlist_from_matches(
                foxnews_urls, video_id, video_title, ie=FoxNewsIE.ie_key())

        sharevideos_urls = [sharevideos_mobj.group('url') for sharevideos_mobj in re.finditer(
            r'<iframe[^>]+?\bsrc\s*=\s*(["\'])(?P<url>(?:https?:)?//embed\.share-videos\.se/auto/embed/\d+\?.*?\buid=\d+.*?)\1',
            webpage)]
        if sharevideos_urls:
            return self.playlist_from_matches(
                sharevideos_urls, video_id, video_title)

        viqeo_urls = ViqeoIE._extract_urls(webpage)
        if viqeo_urls:
            return self.playlist_from_matches(
                viqeo_urls, video_id, video_title, ie=ViqeoIE.ie_key())

        expressen_urls = ExpressenIE._extract_urls(webpage)
        if expressen_urls:
            return self.playlist_from_matches(
                expressen_urls, video_id, video_title, ie=ExpressenIE.ie_key())

        zype_urls = ZypeIE._extract_urls(webpage)
        if zype_urls:
            return self.playlist_from_matches(
                zype_urls, video_id, video_title, ie=ZypeIE.ie_key())

        gedi_urls = GediDigitalIE._extract_urls(webpage)
        if gedi_urls:
            return self.playlist_from_matches(
                gedi_urls, video_id, video_title, ie=GediDigitalIE.ie_key())

        # Look for RCS media group embeds
        rcs_urls = RCSEmbedsIE._extract_urls(webpage)
        if rcs_urls:
            return self.playlist_from_matches(
                rcs_urls, video_id, video_title, ie=RCSEmbedsIE.ie_key())

        wimtv_urls = WimTVIE._extract_urls(webpage)
        if wimtv_urls:
            return self.playlist_from_matches(
                wimtv_urls, video_id, video_title, ie=WimTVIE.ie_key())

        bitchute_urls = BitChuteIE._extract_urls(webpage)
        if bitchute_urls:
            return self.playlist_from_matches(
                bitchute_urls, video_id, video_title, ie=BitChuteIE.ie_key())

        rumble_urls = RumbleEmbedIE._extract_urls(webpage)
        if len(rumble_urls) == 1:
            return self.url_result(rumble_urls[0], RumbleEmbedIE.ie_key())
        if rumble_urls:
            return self.playlist_from_matches(
                rumble_urls, video_id, video_title, ie=RumbleEmbedIE.ie_key())

        # Look for (tvopen|ethnos).gr embeds
        tvopengr_urls = list(TVOpenGrEmbedIE._extract_urls(webpage))
        if tvopengr_urls:
            return self.playlist_from_matches(tvopengr_urls, video_id, video_title, ie=TVOpenGrEmbedIE.ie_key())

        # Look for ert.gr webtv embeds
        ertwebtv_urls = list(ERTWebtvEmbedIE._extract_urls(webpage))
        if len(ertwebtv_urls) == 1:
            return self.url_result(self._proto_relative_url(ertwebtv_urls[0]), video_title=video_title, url_transparent=True)
        elif ertwebtv_urls:
            return self.playlist_from_matches(ertwebtv_urls, video_id, video_title, ie=ERTWebtvEmbedIE.ie_key())

        tvp_urls = TVPEmbedIE._extract_urls(webpage)
        if tvp_urls:
            return self.playlist_from_matches(tvp_urls, video_id, video_title, ie=TVPEmbedIE.ie_key())

        # Look for MainStreaming embeds
        mainstreaming_urls = MainStreamingIE._extract_urls(webpage)
        if mainstreaming_urls:
            return self.playlist_from_matches(mainstreaming_urls, video_id, video_title, ie=MainStreamingIE.ie_key())

        # Look for Gfycat Embeds
        gfycat_urls = GfycatIE._extract_urls(webpage)
        if gfycat_urls:
            return self.playlist_from_matches(gfycat_urls, video_id, video_title, ie=GfycatIE.ie_key())

        panopto_urls = PanoptoBaseIE._extract_urls(webpage)
        if panopto_urls:
            return self.playlist_from_matches(panopto_urls, video_id, video_title)

        # Look for Ruutu embeds
        ruutu_urls = RuutuIE._extract_urls(webpage)
        if ruutu_urls:
            return self.playlist_from_matches(ruutu_urls, video_id, video_title)

        # Look for Tiktok embeds
        tiktok_urls = TikTokIE._extract_urls(webpage)
        if tiktok_urls:
            return self.playlist_from_matches(tiktok_urls, video_id, video_title)

        # Look for HTML5 media
        entries = self._parse_html5_media_entries(url, webpage, video_id, m3u8_id='hls')
        if entries:
            self.report_detected('HTML5 media')
            if len(entries) == 1:
                entries[0].update({
                    'id': video_id,
                    'title': video_title,
                })
            else:
                for num, entry in enumerate(entries, start=1):
                    entry.update({
                        'id': f'{video_id}-{num}',
                        'title': '%s (%d)' % (video_title, num),
                    })
            for entry in entries:
                self._sort_formats(entry['formats'])
            return self.playlist_result(entries, video_id, video_title)

        jwplayer_data = self._find_jwplayer_data(
            webpage, video_id, transform_source=js_to_json)
        if jwplayer_data:
            if isinstance(jwplayer_data.get('playlist'), str):
                self.report_detected('JW Player playlist')
                return {
                    **info_dict,
                    '_type': 'url',
                    'ie_key': JWPlatformIE.ie_key(),
                    'url': jwplayer_data['playlist'],
                }
            try:
                info = self._parse_jwplayer_data(
                    jwplayer_data, video_id, require_title=False, base_url=url)
                self.report_detected('JW Player data')
                return merge_dicts(info, info_dict)
            except ExtractorError:
                # See https://github.com/ytdl-org/youtube-dl/pull/16735
                pass

        # Video.js embed
        mobj = re.search(
            r'(?s)\bvideojs\s*\(.+?([a-zA-Z0-9_$]+)\.src\s*\(\s*((?:\[.+?\]|{.+?}))\s*\)\s*;',
            webpage)
        if mobj is not None:
            varname = mobj.group(1)
            sources = self._parse_json(
                mobj.group(2), video_id, transform_source=js_to_json,
                fatal=False) or []
            if not isinstance(sources, list):
                sources = [sources]
            formats = []
            subtitles = {}
            for source in sources:
                src = source.get('src')
                if not src or not isinstance(src, compat_str):
                    continue
                src = compat_urlparse.urljoin(url, src)
                src_type = source.get('type')
                if isinstance(src_type, compat_str):
                    src_type = src_type.lower()
                ext = determine_ext(src).lower()
                if src_type == 'video/youtube':
                    return self.url_result(src, YoutubeIE.ie_key())
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
                else:
                    formats.append({
                        'url': src,
                        'ext': (mimetype2ext(src_type)
                                or ext if ext in KNOWN_EXTENSIONS else 'mp4'),
                        'http_headers': {
                            'Referer': full_response.geturl(),
                        },
                    })
            # https://docs.videojs.com/player#addRemoteTextTrack
            # https://html.spec.whatwg.org/multipage/media.html#htmltrackelement
            for sub_match in re.finditer(rf'(?s){re.escape(varname)}' r'\.addRemoteTextTrack\(({.+?})\s*,\s*(?:true|false)\)', webpage):
                sub = self._parse_json(
                    sub_match.group(1), video_id, transform_source=js_to_json, fatal=False) or {}
                src = str_or_none(sub.get('src'))
                if not src:
                    continue
                subtitles.setdefault(dict_get(sub, ('language', 'srclang')) or 'und', []).append({
                    'url': compat_urlparse.urljoin(url, src),
                    'name': sub.get('label'),
                    'http_headers': {
                        'Referer': full_response.geturl(),
                    },
                })
            if formats or subtitles:
                self.report_detected('video.js embed')
                self._sort_formats(formats)
                info_dict['formats'] = formats
                info_dict['subtitles'] = subtitles
                return info_dict

        # Looking for http://schema.org/VideoObject
        json_ld = self._search_json_ld(webpage, video_id, default={})
        if json_ld.get('url') not in (url, None):
            self.report_detected('JSON LD')
            if determine_ext(json_ld['url']) == 'm3u8':
                json_ld['formats'], json_ld['subtitles'] = self._extract_m3u8_formats_and_subtitles(
                    json_ld['url'], video_id, 'mp4')
                json_ld.pop('url')
                self._sort_formats(json_ld['formats'])
            else:
                json_ld['_type'] = 'url_transparent'
                json_ld['url'] = smuggle_url(json_ld['url'], {'force_videoid': video_id, 'to_generic': True})
            return merge_dicts(json_ld, info_dict)

        def check_video(vurl):
            if YoutubeIE.suitable(vurl):
                return True
            if RtmpIE.suitable(vurl):
                return True
            vpath = compat_urlparse.urlparse(vurl).path
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
            # Look for generic KVS player
            found = re.search(r'<script [^>]*?src="https?://.+?/kt_player\.js\?v=(?P<ver>(?P<maj_ver>\d+)(\.\d+)+)".*?>', webpage)
            if found:
                self.report_detected('KWS Player')
                if found.group('maj_ver') not in ['4', '5']:
                    self.report_warning('Untested major version (%s) in player engine--Download may fail.' % found.group('ver'))
                flashvars = re.search(r'(?ms)<script.*?>.*?var\s+flashvars\s*=\s*(\{.*?\});.*?</script>', webpage)
                flashvars = self._parse_json(flashvars.group(1), video_id, transform_source=js_to_json)

                # extract the part after the last / as the display_id from the
                # canonical URL.
                display_id = self._search_regex(
                    r'(?:<link href="https?://[^"]+/(.+?)/?" rel="canonical"\s*/?>'
                    r'|<link rel="canonical" href="https?://[^"]+/(.+?)/?"\s*/?>)',
                    webpage, 'display_id', fatal=False
                )
                title = self._html_search_regex(r'<(?:h1|title)>(?:Video: )?(.+?)</(?:h1|title)>', webpage, 'title')

                thumbnail = flashvars['preview_url']
                if thumbnail.startswith('//'):
                    protocol, _, _ = url.partition('/')
                    thumbnail = protocol + thumbnail

                url_keys = list(filter(re.compile(r'video_url|video_alt_url\d*').fullmatch, flashvars.keys()))
                formats = []
                for key in url_keys:
                    if '/get_file/' not in flashvars[key]:
                        continue
                    format_id = flashvars.get(f'{key}_text', key)
                    formats.append({
                        'url': self._kvs_getrealurl(flashvars[key], flashvars['license_code']),
                        'format_id': format_id,
                        'ext': 'mp4',
                        **(parse_resolution(format_id) or parse_resolution(flashvars[key]))
                    })
                    if not formats[-1].get('height'):
                        formats[-1]['quality'] = 1

                self._sort_formats(formats)

                return {
                    'id': flashvars['video_id'],
                    'display_id': display_id,
                    'title': title,
                    'thumbnail': thumbnail,
                    'formats': formats,
                }
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
            # We have to match any number spaces between elements, some sites try to align them (eg.: statigr.am)
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
                r'(?:[a-z-]+="[^"]+"\s+)*?content="%s' % REDIRECT_REGEX,
                webpage)
            if not found:
                # Look also in Refresh HTTP header
                refresh_header = head_response.headers.get('Refresh')
                if refresh_header:
                    found = re.search(REDIRECT_REGEX, refresh_header)
            if found:
                new_url = compat_urlparse.urljoin(url, unescapeHTML(found.group(1)))
                if new_url != url:
                    self.report_following_redirect(new_url)
                    return {
                        '_type': 'url',
                        'url': new_url,
                    }
                else:
                    found = None

        if not found:
            # twitter:player is a https URL to iframe player that may or may not
            # be supported by yt-dlp thus this is checked the very last (see
            # https://dev.twitter.com/cards/types/player#On_twitter.com_via_desktop_browser)
            embed_url = self._html_search_meta('twitter:player', webpage, default=None)
            if embed_url and embed_url != url:
                self.report_detected('twitter:player iframe')
                return self.url_result(embed_url)

        if not found:
            raise UnsupportedError(url)

        entries = []
        for video_url in orderedSet(found):
            video_url = unescapeHTML(video_url)
            video_url = video_url.replace('\\/', '/')
            video_url = compat_urlparse.urljoin(url, video_url)
            video_id = compat_urllib_parse_unquote(os.path.basename(video_url))

            # Sometimes, jwplayer extraction will result in a YouTube URL
            if YoutubeIE.suitable(video_url):
                entries.append(self.url_result(video_url, 'Youtube'))
                continue

            # here's a fun little line of code for you:
            video_id = os.path.splitext(video_id)[0]
            headers = {
                'referer': full_response.geturl()
            }

            entry_info_dict = {
                'id': video_id,
                'uploader': video_uploader,
                'title': video_title,
                'age_limit': age_limit,
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
                return self.playlist_result(self._extract_xspf_playlist(video_url, video_id), video_id)
            elif ext == 'm3u8':
                entry_info_dict['formats'], entry_info_dict['subtitles'] = self._extract_m3u8_formats_and_subtitles(video_url, video_id, ext='mp4', headers=headers)
            elif ext == 'mpd':
                entry_info_dict['formats'], entry_info_dict['subtitles'] = self._extract_mpd_formats_and_subtitles(video_url, video_id, headers=headers)
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

            if entry_info_dict.get('formats'):
                self._sort_formats(entry_info_dict['formats'])

            entries.append(entry_info_dict)

        if len(entries) == 1:
            return merge_dicts(entries[0], info_dict)
        else:
            for num, e in enumerate(entries, start=1):
                # 'url' results don't have a title
                if e.get('title') is not None:
                    e['title'] = '%s (%d)' % (e['title'], num)
            return {
                '_type': 'playlist',
                'entries': entries,
            }
