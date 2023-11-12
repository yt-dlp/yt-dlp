from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    parse_count,
    unified_timestamp,
    remove_end,
    determine_ext,
)
import re
import random


class NitterIE(InfoExtractor):
    # Taken from https://github.com/zedeus/nitter/wiki/Instances

    NON_HTTP_INSTANCES = (
        '3nzoldnxplag42gqjs23xvghtzf6t6yzssrtytnntc6ppc7xxuoneoad.onion',
        'nitter.l4qlywnpwqsluw65ts7md3khrivpirse744un3x7mlskqauz5pyuzgqd.onion',
        'nitter7bryz3jv7e3uekphigvmoyoem4al3fynerxkj22dmoxoq553qd.onion',
        'npf37k3mtzwxreiw52ccs5ay4e6qt2fkcs2ndieurdyn2cuzzsfyfvid.onion',
        'nitter.v6vgyqpa7yefkorazmg5d5fimstmvm2vtbirt6676mt7qmllrcnwycqd.onion',
        'i23nv6w3juvzlw32xzoxcqzktegd4i4fu3nmnc2ewv4ggiu4ledwklad.onion',
        '26oq3gioiwcmfojub37nz5gzbkdiqp7fue5kvye7d4txv4ny6fb4wwid.onion',
        'vfaomgh4jxphpbdfizkm5gbtjahmei234giqj4facbwhrfjtcldauqad.onion',
        'iwgu3cv7ywf3gssed5iqtavmrlszgsxazkmwwnt4h2kdait75thdyrqd.onion',
        'erpnncl5nhyji3c32dcfmztujtl3xaddqb457jsbkulq24zqq7ifdgad.onion',
        'ckzuw5misyahmg7j5t5xwwuj3bwy62jfolxyux4brfflramzsvvd3syd.onion',
        'jebqj47jgxleaiosfcxfibx2xdahjettuydlxbg64azd4khsxv6kawid.onion',
        'nttr2iupbb6fazdpr2rgbooon2tzbbsvvkagkgkwohhodjzj43stxhad.onion',
        'nitraeju2mipeziu2wtcrqsxg7h62v5y4eqgwi75uprynkj74gevvuqd.onion',
        'nitter.lqs5fjmajyp7rvp4qvyubwofzi6d4imua7vs237rkc4m5qogitqwrgyd.onion',
        'ibsboeui2im5o7dxnik3s5yghufumgy5abevtij5nbizequfpu4qi4ad.onion',
        'ec5nvbycpfa5k6ro77blxgkyrzbkv7uy6r5cngcbkadtjj2733nm3uyd.onion',

        'nitter.i2p',
        'u6ikd6zndl3c4dsdq4mmujpntgeevdk5qzkfb57r4tnfeccrn2qa.b32.i2p',

        'nitterlgj3n5fgwesu3vxc5h67ruku33nqaoeoocae2mvlzhsu6k7fqd.onion',
    )

    HTTP_INSTANCES = (
        'nitter.lacontrevoie.fr',
        'nitter.fdn.fr',
        'nitter.1d4.us',
        'nitter.kavin.rocks',
        'nitter.unixfox.eu',
        'nitter.domain.glass',
        'nitter.namazso.eu',
        'birdsite.xanny.family',
        'nitter.moomoo.me',
        'bird.trom.tf',
        'nitter.it',
        'twitter.censors.us',
        'nitter.grimneko.de',
        'twitter.076.ne.jp',
        'nitter.fly.dev',
        'notabird.site',
        'nitter.weiler.rocks',
        'nitter.sethforprivacy.com',
        'nitter.cutelab.space',
        'nitter.nl',
        'nitter.mint.lgbt',
        'nitter.bus-hit.me',
        'nitter.esmailelbob.xyz',
        'tw.artemislena.eu',
        'nitter.winscloud.net',
        'nitter.tiekoetter.com',
        'nitter.spaceint.fr',
        'nitter.privacy.com.de',
        'nitter.poast.org',
        'nitter.bird.froth.zone',
        'nitter.dcs0.hu',
        'twitter.dr460nf1r3.org',
        'nitter.garudalinux.org',
        'twitter.femboy.hu',
        'nitter.cz',
        'nitter.privacydev.net',
        'nitter.evil.site',
        'tweet.lambda.dance',
        'nitter.kylrth.com',
        'nitter.foss.wtf',
        'nitter.priv.pw',
        'nitter.tokhmi.xyz',
        'nitter.catalyst.sx',
        'unofficialbird.com',
        'nitter.projectsegfau.lt',
        'nitter.eu.projectsegfau.lt',
        'singapore.unofficialbird.com',
        'canada.unofficialbird.com',
        'india.unofficialbird.com',
        'nederland.unofficialbird.com',
        'uk.unofficialbird.com',
        'n.l5.ca',
        'nitter.slipfox.xyz',
        'nitter.soopy.moe',
        'nitter.qwik.space',
        'read.whatever.social',
        'nitter.rawbit.ninja',
        'nt.vern.cc',
        'ntr.odyssey346.dev',
        'nitter.ir',
        'nitter.privacytools.io',
        'nitter.sneed.network',
        'n.sneed.network',
        'nitter.manasiwibi.com',
        'nitter.smnz.de',
        'nitter.twei.space',
        'nitter.inpt.fr',
        'nitter.d420.de',
        'nitter.caioalonso.com',
        'nitter.at',
        'nitter.drivet.xyz',
        'nitter.pw',
        'nitter.nicfab.eu',
        'bird.habedieeh.re',
        'nitter.hostux.net',
        'nitter.adminforge.de',
        'nitter.platypush.tech',
        'nitter.mask.sh',
        'nitter.pufe.org',
        'nitter.us.projectsegfau.lt',
        'nitter.arcticfoxes.net',
        't.com.sb',
        'nitter.kling.gg',
        'nitter.ktachibana.party',
        'nitter.riverside.rocks',
        'nitter.girlboss.ceo',
        'nitter.lunar.icu',
        'twitter.moe.ngo',
        'nitter.freedit.eu',
        'ntr.frail.duckdns.org',
        'nitter.librenode.org',
        'n.opnxng.com',
        'nitter.plus.st',
    )

    DEAD_INSTANCES = (
        # maintenance
        'nitter.ethibox.fr',

        # official, rate limited
        'nitter.net',
        # offline
        'is-nitter.resolv.ee',
        'lu-nitter.resolv.ee',
        'nitter.13ad.de',
        'nitter.40two.app',
        'nitter.cattube.org',
        'nitter.cc',
        'nitter.dark.fail',
        'nitter.himiko.cloud',
        'nitter.koyu.space',
        'nitter.mailstation.de',
        'nitter.mastodont.cat',
        'nitter.tedomum.net',
        'nitter.tokhmi.xyz',
        'nitter.weaponizedhumiliation.com',
        'nitter.vxempire.xyz',
        'tweet.lambda.dance',
        'nitter.ca',
        'nitter.42l.fr',
        'nitter.pussthecat.org',
        'nitter.nixnet.services',
        'nitter.eu',
        'nitter.actionsack.com',
        'nitter.hu',
        'twitr.gq',
        'nittereu.moomoo.me',
        'bird.from.tf',
        'twitter.grimneko.de',
        'nitter.alefvanoon.xyz',
        'n.hyperborea.cloud',
        'twitter.mstdn.social',
        'nitter.silkky.cloud',
        'nttr.stream',
        'fuckthesacklers.network',
        'nitter.govt.land',
        'nitter.datatunnel.xyz',
        'de.nttr.stream',
        'twtr.bch.bar',
        'nitter.exonip.de',
        'nitter.mastodon.pro',
        'nitter.notraxx.ch',
        'nitter.skrep.in',
        'nitter.snopyta.org',
    )

    INSTANCES = NON_HTTP_INSTANCES + HTTP_INSTANCES + DEAD_INSTANCES

    _INSTANCES_RE = f'(?:{"|".join(map(re.escape, INSTANCES))})'
    _VALID_URL = fr'https?://{_INSTANCES_RE}/(?P<uploader_id>.+)/status/(?P<id>[0-9]+)(#.)?'
    current_instance = random.choice(HTTP_INSTANCES)

    _TESTS = [
        {
            # GIF (wrapped in mp4)
            'url': f'https://{current_instance}/firefox/status/1314279897502629888#m',
            'info_dict': {
                'id': '1314279897502629888',
                'ext': 'mp4',
                'title': 'md5:7890a9277da4639ab624dd899424c5d8',
                'description': 'md5:5fea96a4d3716c350f8b95b21b3111fe',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Firefox 🔥',
                'uploader_id': 'firefox',
                'uploader_url': f'https://{current_instance}/firefox',
                'upload_date': '20201008',
                'timestamp': 1602183720,
                'like_count': int,
                'repost_count': int,
                'comment_count': int,
            },
        }, {  # normal video
            'url': f'https://{current_instance}/Le___Doc/status/1299715685392756737#m',
            'info_dict': {
                'id': '1299715685392756737',
                'ext': 'mp4',
                'title': 're:^.* - "Je ne prédis jamais rien"\nD Raoult, Août 2020...',
                'description': '"Je ne prédis jamais rien"\nD Raoult, Août 2020...',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 're:^Le *Doc',
                'uploader_id': 'Le___Doc',
                'uploader_url': f'https://{current_instance}/Le___Doc',
                'upload_date': '20200829',
                'timestamp': 1598711340,
                'view_count': int,
                'like_count': int,
                'repost_count': int,
                'comment_count': int,
            },
        }, {  # video embed in a "Streaming Political Ads" box
            'url': f'https://{current_instance}/mozilla/status/1321147074491092994#m',
            'info_dict': {
                'id': '1321147074491092994',
                'ext': 'mp4',
                'title': 'md5:8290664aabb43b9189145c008386bf12',
                'description': 'md5:9cf2762d49674bc416a191a689fb2aaa',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Mozilla',
                'uploader_id': 'mozilla',
                'uploader_url': f'https://{current_instance}/mozilla',
                'upload_date': '20201027',
                'timestamp': 1603820940,
                'view_count': int,
                'like_count': int,
                'repost_count': int,
                'comment_count': int,
            },
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
        }, {  # not the first tweet but main-tweet
            'url': f'https://{current_instance}/firefox/status/1354848277481414657#m',
            'info_dict': {
                'id': '1354848277481414657',
                'ext': 'mp4',
                'title': 'md5:bef647f03bd1c6b15b687ea70dfc9700',
                'description': 'md5:5efba25e2f9dac85ebcd21160cb4341f',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Firefox 🔥',
                'uploader_id': 'firefox',
                'uploader_url': f'https://{current_instance}/firefox',
                'upload_date': '20210128',
                'timestamp': 1611855960,
                'view_count': int,
                'like_count': int,
                'repost_count': int,
                'comment_count': int,
            }
        }, {  # no OpenGraph title
            'url': f'https://{current_instance}/LocalBateman/status/1678455464038735895#m',
            'info_dict': {
                'id': '1678455464038735895',
                'ext': 'mp4',
                'title': 'Your Typical Local Man - Local man, what did Romanians ever do to you?',
                'description': 'Local man, what did Romanians ever do to you?',
                'thumbnail': r're:^https?://.*\.jpg$',
                'uploader': 'Your Typical Local Man',
                'uploader_id': 'LocalBateman',
                'uploader_url': f'https://{current_instance}/LocalBateman',
                'upload_date': '20230710',
                'timestamp': 1689009900,
                'view_count': int,
                'like_count': int,
                'repost_count': int,
                'comment_count': int,
            },
            'expected_warnings': ['Ignoring subtitle tracks found in the HLS manifest'],
            'params': {'skip_download': 'm3u8'},
        }
    ]

    def _real_extract(self, url):
        video_id, uploader_id = self._match_valid_url(url).group('id', 'uploader_id')
        parsed_url = compat_urlparse.urlparse(url)
        base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'

        self._set_cookie(parsed_url.netloc, 'hlsPlayback', 'on')
        full_webpage = webpage = self._download_webpage(url, video_id)

        main_tweet_start = full_webpage.find('class="main-tweet"')
        if main_tweet_start > 0:
            webpage = full_webpage[main_tweet_start:]

        video_url = '%s%s' % (base_url, self._html_search_regex(
            r'(?:<video[^>]+data-url|<source[^>]+src)="([^"]+)"', webpage, 'video url'))
        ext = determine_ext(video_url)

        if ext == 'unknown_video':
            formats = self._extract_m3u8_formats(video_url, video_id, ext='mp4')
        else:
            formats = [{
                'url': video_url,
                'ext': ext
            }]

        title = description = self._og_search_description(full_webpage, default=None) or self._html_search_regex(
            r'<div class="tweet-content[^>]+>([^<]+)</div>', webpage, 'title', fatal=False)

        uploader_id = self._html_search_regex(
            r'<a class="username"[^>]+title="@([^"]+)"', webpage, 'uploader id', fatal=False) or uploader_id

        uploader = self._html_search_regex(
            r'<a class="fullname"[^>]+title="([^"]+)"', webpage, 'uploader name', fatal=False)
        if uploader:
            title = f'{uploader} - {title}'

        counts = {
            f'{x[0]}_count': self._html_search_regex(
                fr'<span[^>]+class="icon-{x[1]}[^>]*></span>([^<]*)</div>',
                webpage, f'{x[0]} count', fatal=False)
            for x in (('view', 'play'), ('like', 'heart'), ('repost', 'retweet'), ('comment', 'comment'))
        }
        counts = {field: 0 if count == '' else parse_count(count) for field, count in counts.items()}

        thumbnail = (
            self._html_search_meta('og:image', full_webpage, 'thumbnail url')
            or remove_end('%s%s' % (base_url, self._html_search_regex(
                r'<video[^>]+poster="([^"]+)"', webpage, 'thumbnail url', fatal=False)), '%3Asmall'))

        thumbnails = [
            {'id': id, 'url': f'{thumbnail}%3A{id}'}
            for id in ('thumb', 'small', 'large', 'medium', 'orig')
        ]

        date = self._html_search_regex(
            r'<span[^>]+class="tweet-date"[^>]*><a[^>]+title="([^"]+)"',
            webpage, 'upload date', default='').replace('·', '')

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'timestamp': unified_timestamp(date),
            'uploader_id': uploader_id,
            'uploader_url': f'{base_url}/{uploader_id}',
            'formats': formats,
            'thumbnails': thumbnails,
            'thumbnail': thumbnail,
            **counts,
        }
