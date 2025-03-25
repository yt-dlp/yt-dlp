# Changelog

<!--
# To create a release, dispatch the https://github.com/yt-dlp/yt-dlp/actions/workflows/release.yml workflow on master
-->

### 2025.03.25

#### Core changes
- [Fix attribute error on failed VT init](https://github.com/yt-dlp/yt-dlp/commit/b872ffec50fd50f790a5a490e006a369a28a3df3) ([#12696](https://github.com/yt-dlp/yt-dlp/issues/12696)) by [Grub4K](https://github.com/Grub4K)
- **utils**: `js_to_json`: [Make function less fatal](https://github.com/yt-dlp/yt-dlp/commit/9491b44032b330e05bd5eaa546187005d1e8538e) ([#12715](https://github.com/yt-dlp/yt-dlp/issues/12715)) by [seproDev](https://github.com/seproDev)

#### Extractor changes
- [Fix sorting of HLS audio formats by `GROUP-ID`](https://github.com/yt-dlp/yt-dlp/commit/86ab79e1a5182092321102adf6ca34195803b878) ([#12714](https://github.com/yt-dlp/yt-dlp/issues/12714)) by [bashonly](https://github.com/bashonly)
- **17live**: vod: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/3396eb50dcd245b49c0f4aecd6e80ec914095d16) ([#12723](https://github.com/yt-dlp/yt-dlp/issues/12723)) by [subrat-lima](https://github.com/subrat-lima)
- **9now.com.au**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/9d5e6de2e7a47226d1f72c713ad45c88ba01db68) ([#12702](https://github.com/yt-dlp/yt-dlp/issues/12702)) by [bashonly](https://github.com/bashonly)
- **chzzk**: video: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/e2dfccaf808b406d5bcb7dd04ae9ce420752dd6f) ([#12692](https://github.com/yt-dlp/yt-dlp/issues/12692)) by [bashonly](https://github.com/bashonly), [dirkf](https://github.com/dirkf)
- **deezer**: [Remove extractors](https://github.com/yt-dlp/yt-dlp/commit/be5af3f9e91747768c2b41157851bfbe14c663f7) ([#12704](https://github.com/yt-dlp/yt-dlp/issues/12704)) by [seproDev](https://github.com/seproDev)
- **generic**: [Fix MPD base URL parsing](https://github.com/yt-dlp/yt-dlp/commit/5086d4aed6aeb3908c62f49e2d8f74cc0cb05110) ([#12718](https://github.com/yt-dlp/yt-dlp/issues/12718)) by [fireattack](https://github.com/fireattack)
- **streaks**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/801afeac91f97dc0b58cd39cc7e8c50f619dc4e1) ([#12679](https://github.com/yt-dlp/yt-dlp/issues/12679)) by [doe1080](https://github.com/doe1080)
- **tver**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/66e0bab814e4a52ef3e12d81123ad992a29df50e) ([#12659](https://github.com/yt-dlp/yt-dlp/issues/12659)) by [arabcoders](https://github.com/arabcoders), [bashonly](https://github.com/bashonly)
- **viki**: [Remove extractors](https://github.com/yt-dlp/yt-dlp/commit/fe4f14b8369038e7c58f7de546d76de1ce3a91ce) ([#12703](https://github.com/yt-dlp/yt-dlp/issues/12703)) by [seproDev](https://github.com/seproDev)
- **vrsquare**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/b7fbb5a0a16a8e8d3e29c29e26ebed677d0d6ea3) ([#12515](https://github.com/yt-dlp/yt-dlp/issues/12515)) by [doe1080](https://github.com/doe1080)
- **youtube**
    - [Fix PhantomJS nsig fallback](https://github.com/yt-dlp/yt-dlp/commit/4054a2b623bd1e277b49d2e9abc3d112a4b1c7be) ([#12728](https://github.com/yt-dlp/yt-dlp/issues/12728)) by [bashonly](https://github.com/bashonly)
    - [Fix signature and nsig extraction for player `363db69b`](https://github.com/yt-dlp/yt-dlp/commit/b9c979461b244713bf42691a5bc02834e2ba4b2c) ([#12725](https://github.com/yt-dlp/yt-dlp/issues/12725)) by [bashonly](https://github.com/bashonly)

#### Networking changes
- **Request Handler**: curl_cffi: [Support `curl_cffi` 0.10.x](https://github.com/yt-dlp/yt-dlp/commit/9bf23902ceb948b9685ce1dab575491571720fc6) ([#12670](https://github.com/yt-dlp/yt-dlp/issues/12670)) by [Grub4K](https://github.com/Grub4K)

#### Misc. changes
- **cleanup**: Miscellaneous: [9dde546](https://github.com/yt-dlp/yt-dlp/commit/9dde546e7ee3e1515d88ee3af08b099351455dc0) by [seproDev](https://github.com/seproDev)

### 2025.03.21

#### Core changes
- [Fix external downloader availability when using `--ffmpeg-location`](https://github.com/yt-dlp/yt-dlp/commit/9f77e04c76e36e1cbbf49bc9eb385fa6ef804b67) ([#12318](https://github.com/yt-dlp/yt-dlp/issues/12318)) by [Kenshin9977](https://github.com/Kenshin9977)
- [Load plugins on demand](https://github.com/yt-dlp/yt-dlp/commit/4445f37a7a66b248dbd8376c43137e6e441f138e) ([#11305](https://github.com/yt-dlp/yt-dlp/issues/11305)) by [coletdjnz](https://github.com/coletdjnz), [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan) (With fixes in [c034d65](https://github.com/yt-dlp/yt-dlp/commit/c034d655487be668222ef9476a16f374584e49a7))
- [Support emitting ConEmu progress codes](https://github.com/yt-dlp/yt-dlp/commit/f7a1f2d8132967a62b0f6d5665c6d2dde2d42c09) ([#10649](https://github.com/yt-dlp/yt-dlp/issues/10649)) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- **azmedien**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/26a502fc727d0e91b2db6bf4a112823bcc672e85) ([#12375](https://github.com/yt-dlp/yt-dlp/issues/12375)) by [goggle](https://github.com/goggle)
- **bilibiliplaylist**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/f5fb2229e66cf59d5bf16065bc041b42a28354a0) ([#12690](https://github.com/yt-dlp/yt-dlp/issues/12690)) by [bashonly](https://github.com/bashonly)
- **bunnycdn**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/3a1583ca75fb523cbad0e5e174387ea7b477d175) ([#11586](https://github.com/yt-dlp/yt-dlp/issues/11586)) by [Grub4K](https://github.com/Grub4K), [seproDev](https://github.com/seproDev)
- **canalsurmas**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/01a8be4c23f186329d85f9c78db34a55f3294ac5) ([#12497](https://github.com/yt-dlp/yt-dlp/issues/12497)) by [Arc8ne](https://github.com/Arc8ne)
- **cda**: [Fix login support](https://github.com/yt-dlp/yt-dlp/commit/be0d819e1103195043f6743650781f0d4d343f6d) ([#12552](https://github.com/yt-dlp/yt-dlp/issues/12552)) by [rysson](https://github.com/rysson)
- **cultureunplugged**: [Extend `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/3042afb5fe342d3a00de76704cd7de611acc350e) ([#12486](https://github.com/yt-dlp/yt-dlp/issues/12486)) by [seproDev](https://github.com/seproDev)
- **dailymotion**: [Improve embed detection](https://github.com/yt-dlp/yt-dlp/commit/ad60137c141efa5023fbc0ac8579eaefe8b3d8cc) ([#12464](https://github.com/yt-dlp/yt-dlp/issues/12464)) by [seproDev](https://github.com/seproDev)
- **gem.cbc.ca**: [Fix login support](https://github.com/yt-dlp/yt-dlp/commit/eb1417786a3027b1e7290ec37ef6aaece50ebed0) ([#12414](https://github.com/yt-dlp/yt-dlp/issues/12414)) by [bashonly](https://github.com/bashonly)
- **globo**: [Fix subtitles extraction](https://github.com/yt-dlp/yt-dlp/commit/0e1697232fcbba7551f983fd1ba93bb445cbb08b) ([#12270](https://github.com/yt-dlp/yt-dlp/issues/12270)) by [pedro](https://github.com/pedro)
- **instagram**
    - [Add `app_id` extractor-arg](https://github.com/yt-dlp/yt-dlp/commit/a90641c8363fa0c10800b36eb6b01ee22d3a9409) ([#12359](https://github.com/yt-dlp/yt-dlp/issues/12359)) by [chrisellsworth](https://github.com/chrisellsworth)
    - [Fix extraction of older private posts](https://github.com/yt-dlp/yt-dlp/commit/a59abe0636dc49b22a67246afe35613571b86f05) ([#12451](https://github.com/yt-dlp/yt-dlp/issues/12451)) by [bashonly](https://github.com/bashonly)
    - [Improve error handling](https://github.com/yt-dlp/yt-dlp/commit/480125560a3b9972d29ae0da850aba8109e6bd41) ([#12410](https://github.com/yt-dlp/yt-dlp/issues/12410)) by [bashonly](https://github.com/bashonly)
    - story: [Support `--no-playlist`](https://github.com/yt-dlp/yt-dlp/commit/65c3c58c0a67463a150920203cec929045c95a24) ([#12397](https://github.com/yt-dlp/yt-dlp/issues/12397)) by [fireattack](https://github.com/fireattack)
- **jamendo**: [Fix thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/89a68c4857ddbaf937ff22f12648baaf6b5af840) ([#12622](https://github.com/yt-dlp/yt-dlp/issues/12622)) by [bashonly](https://github.com/bashonly), [JChris246](https://github.com/JChris246)
- **ketnet**: [Remove extractor](https://github.com/yt-dlp/yt-dlp/commit/bbada3ec0779422cde34f1ce3dcf595da463b493) ([#12628](https://github.com/yt-dlp/yt-dlp/issues/12628)) by [MichaelDeBoey](https://github.com/MichaelDeBoey)
- **lbry**
    - [Make m3u8 format extraction non-fatal](https://github.com/yt-dlp/yt-dlp/commit/9807181cfbf87bfa732f415c30412bdbd77cbf81) ([#12463](https://github.com/yt-dlp/yt-dlp/issues/12463)) by [bashonly](https://github.com/bashonly)
    - [Raise appropriate error for non-media files](https://github.com/yt-dlp/yt-dlp/commit/7126b472601814b7fd8c9de02069e8fff1764891) ([#12462](https://github.com/yt-dlp/yt-dlp/issues/12462)) by [bashonly](https://github.com/bashonly)
- **loco**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/983095485c731240aae27c950cb8c24a50827b56) ([#12667](https://github.com/yt-dlp/yt-dlp/issues/12667)) by [DTrombett](https://github.com/DTrombett)
- **magellantv**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/172d5fcd778bf2605db7647ebc56b29ed18d24ac) ([#12505](https://github.com/yt-dlp/yt-dlp/issues/12505)) by [seproDev](https://github.com/seproDev)
- **mitele**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/7223d29569a48a35ad132a508c115973866838d3) ([#12689](https://github.com/yt-dlp/yt-dlp/issues/12689)) by [bashonly](https://github.com/bashonly)
- **msn**: [Rework extractor](https://github.com/yt-dlp/yt-dlp/commit/4815dac131d42c51e12c1d05232db0bbbf607329) ([#12513](https://github.com/yt-dlp/yt-dlp/issues/12513)) by [seproDev](https://github.com/seproDev), [thedenv](https://github.com/thedenv)
- **n1**: [Fix extraction of newer articles](https://github.com/yt-dlp/yt-dlp/commit/9d70abe4de401175cbbaaa36017806f16b2df9af) ([#12514](https://github.com/yt-dlp/yt-dlp/issues/12514)) by [u-spec-png](https://github.com/u-spec-png)
- **nbcstations**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/ebac65aa9e0bf9a97c24d00f7977900d2577364b) ([#12534](https://github.com/yt-dlp/yt-dlp/issues/12534)) by [refack](https://github.com/refack)
- **niconico**
    - [Fix format sorting](https://github.com/yt-dlp/yt-dlp/commit/7508e34f203e97389f1d04db92140b13401dd724) ([#12442](https://github.com/yt-dlp/yt-dlp/issues/12442)) by [xpadev-net](https://github.com/xpadev-net)
    - live: [Fix thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/c2e6e1d5f77f3b720a6266f2869eb750d20e5dc1) ([#12419](https://github.com/yt-dlp/yt-dlp/issues/12419)) by [bashonly](https://github.com/bashonly)
- **openrec**: [Fix `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/17504f253564cfad86244de2b6346d07d2300ca5) ([#12608](https://github.com/yt-dlp/yt-dlp/issues/12608)) by [fireattack](https://github.com/fireattack)
- **pinterest**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/bd0a66816934de70312eea1e71c59c13b401dc3a) ([#12538](https://github.com/yt-dlp/yt-dlp/issues/12538)) by [mikf](https://github.com/mikf)
- **playsuisse**: [Fix login support](https://github.com/yt-dlp/yt-dlp/commit/6933f5670cea9c3e2fb16c1caa1eda54d13122c5) ([#12444](https://github.com/yt-dlp/yt-dlp/issues/12444)) by [bashonly](https://github.com/bashonly)
- **reddit**: [Truncate title](https://github.com/yt-dlp/yt-dlp/commit/d9a53cc1e6fd912daf500ca4f19e9ca88994dbf9) ([#12567](https://github.com/yt-dlp/yt-dlp/issues/12567)) by [seproDev](https://github.com/seproDev)
- **rtp**: [Rework extractor](https://github.com/yt-dlp/yt-dlp/commit/8eb9c1bf3b9908cca22ef043602aa24fb9f352c6) ([#11638](https://github.com/yt-dlp/yt-dlp/issues/11638)) by [pferreir](https://github.com/pferreir), [red-acid](https://github.com/red-acid), [seproDev](https://github.com/seproDev), [somini](https://github.com/somini), [vallovic](https://github.com/vallovic)
- **softwhiteunderbelly**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/652827d5a076c9483c36654ad2cf3fe46219baf4) ([#12281](https://github.com/yt-dlp/yt-dlp/issues/12281)) by [benfaerber](https://github.com/benfaerber)
- **soop**: [Fix timestamp extraction](https://github.com/yt-dlp/yt-dlp/commit/8305df00012ff8138a6ff95279d06b54ac607f63) ([#12609](https://github.com/yt-dlp/yt-dlp/issues/12609)) by [msikma](https://github.com/msikma)
- **soundcloud**
    - [Extract tags](https://github.com/yt-dlp/yt-dlp/commit/9deed13d7cce6d3647379e50589c92de89227509) ([#12420](https://github.com/yt-dlp/yt-dlp/issues/12420)) by [bashonly](https://github.com/bashonly)
    - [Fix thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/6deeda5c11f34f613724fa0627879f0d607ba1b4) ([#12447](https://github.com/yt-dlp/yt-dlp/issues/12447)) by [bashonly](https://github.com/bashonly)
- **tiktok**
    - [Improve error handling](https://github.com/yt-dlp/yt-dlp/commit/99ea2978757a431eeb2a265b3395ccbe4ce202cf) ([#12445](https://github.com/yt-dlp/yt-dlp/issues/12445)) by [bashonly](https://github.com/bashonly)
    - [Truncate title](https://github.com/yt-dlp/yt-dlp/commit/83b119dadb0f267f1fb66bf7ed74c097349de79e) ([#12566](https://github.com/yt-dlp/yt-dlp/issues/12566)) by [seproDev](https://github.com/seproDev)
- **tv8.it**: [Add live and playlist extractors](https://github.com/yt-dlp/yt-dlp/commit/2ee3a0aff9be2be3bea60640d3d8a0febaf0acb6) ([#12569](https://github.com/yt-dlp/yt-dlp/issues/12569)) by [DTrombett](https://github.com/DTrombett)
- **tvw**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/42b7440963866e31ff84a5b89030d1c596fa2e6e) ([#12271](https://github.com/yt-dlp/yt-dlp/issues/12271)) by [fries1234](https://github.com/fries1234)
- **twitter**
    - [Fix syndication token generation](https://github.com/yt-dlp/yt-dlp/commit/b8b47547049f5ebc3dd680fc7de70ed0ca9c0d70) ([#12537](https://github.com/yt-dlp/yt-dlp/issues/12537)) by [bashonly](https://github.com/bashonly)
    - [Truncate title](https://github.com/yt-dlp/yt-dlp/commit/06f6de78db2eceeabd062ab1a3023e0ff9d4df53) ([#12560](https://github.com/yt-dlp/yt-dlp/issues/12560)) by [seproDev](https://github.com/seproDev)
- **vk**: [Improve metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/05c8023a27dd37c49163c0498bf98e3e3c1cb4b9) ([#12510](https://github.com/yt-dlp/yt-dlp/issues/12510)) by [seproDev](https://github.com/seproDev)
- **vrtmax**: [Rework extractor](https://github.com/yt-dlp/yt-dlp/commit/df9ebeec00d658693252978d1ffb885e67aa6ab6) ([#12479](https://github.com/yt-dlp/yt-dlp/issues/12479)) by [bergoid](https://github.com/bergoid), [MichaelDeBoey](https://github.com/MichaelDeBoey), [seproDev](https://github.com/seproDev)
- **weibo**: [Support playlists](https://github.com/yt-dlp/yt-dlp/commit/0bb39788626002a8a67e925580227952c563c8b9) ([#12284](https://github.com/yt-dlp/yt-dlp/issues/12284)) by [4ft35t](https://github.com/4ft35t)
- **wsj**: [Support opinion URLs and impersonation](https://github.com/yt-dlp/yt-dlp/commit/7f3006eb0c0659982bb956d71b0bc806bcb0a5f2) ([#12431](https://github.com/yt-dlp/yt-dlp/issues/12431)) by [refack](https://github.com/refack)
- **youtube**
    - [Fix nsig and signature extraction for player `643afba4`](https://github.com/yt-dlp/yt-dlp/commit/9b868518a15599f3d7ef5a1c730dda164c30da9b) ([#12684](https://github.com/yt-dlp/yt-dlp/issues/12684)) by [bashonly](https://github.com/bashonly), [seproDev](https://github.com/seproDev)
    - [Player client maintenance](https://github.com/yt-dlp/yt-dlp/commit/3380febe9984c21c79c3147c1d390a4cf339bc4c) ([#12603](https://github.com/yt-dlp/yt-dlp/issues/12603)) by [seproDev](https://github.com/seproDev)
    - [Split into package](https://github.com/yt-dlp/yt-dlp/commit/4432a9390c79253ac830702b226d2e558b636725) ([#12557](https://github.com/yt-dlp/yt-dlp/issues/12557)) by [coletdjnz](https://github.com/coletdjnz)
    - [Warn on DRM formats](https://github.com/yt-dlp/yt-dlp/commit/e67d786c7cc87bd449d22e0ddef08306891c1173) ([#12593](https://github.com/yt-dlp/yt-dlp/issues/12593)) by [coletdjnz](https://github.com/coletdjnz)
    - [Warn on missing formats due to SSAP](https://github.com/yt-dlp/yt-dlp/commit/79ec2fdff75c8c1bb89b550266849ad4dec48dd3) ([#12483](https://github.com/yt-dlp/yt-dlp/issues/12483)) by [coletdjnz](https://github.com/coletdjnz)

#### Networking changes
- [Add `keep_header_casing` extension](https://github.com/yt-dlp/yt-dlp/commit/7d18fed8f1983fe6de4ddc810dfb2761ba5744ac) ([#11652](https://github.com/yt-dlp/yt-dlp/issues/11652)) by [coletdjnz](https://github.com/coletdjnz), [Grub4K](https://github.com/Grub4K)
- [Always add unsupported suffix on version mismatch](https://github.com/yt-dlp/yt-dlp/commit/95f8df2f796d0048119615200758199aedcd7cf4) ([#12626](https://github.com/yt-dlp/yt-dlp/issues/12626)) by [Grub4K](https://github.com/Grub4K)

#### Misc. changes
- **cleanup**: Miscellaneous: [f36e4b6](https://github.com/yt-dlp/yt-dlp/commit/f36e4b6e65cb8403791aae2f520697115cb88dec) by [dirkf](https://github.com/dirkf), [gamer191](https://github.com/gamer191), [Grub4K](https://github.com/Grub4K), [seproDev](https://github.com/seproDev)
- **test**: [Show all differences for `expect_value` and `expect_dict`](https://github.com/yt-dlp/yt-dlp/commit/a3e0c7d3b267abdf3933b709704a28d43bb46503) ([#12334](https://github.com/yt-dlp/yt-dlp/issues/12334)) by [Grub4K](https://github.com/Grub4K)

### 2025.02.19

#### Core changes
- **jsinterp**
    - [Add `js_number_to_string`](https://github.com/yt-dlp/yt-dlp/commit/0d9f061d38c3a4da61972e2adad317079f2f1c84) ([#12110](https://github.com/yt-dlp/yt-dlp/issues/12110)) by [Grub4K](https://github.com/Grub4K)
    - [Improve zeroise](https://github.com/yt-dlp/yt-dlp/commit/4ca8c44a073d5aa3a3e3112c35b2b23d6ce25ac6) ([#12313](https://github.com/yt-dlp/yt-dlp/issues/12313)) by [seproDev](https://github.com/seproDev)

#### Extractor changes
- **acast**: [Support shows.acast.com URLs](https://github.com/yt-dlp/yt-dlp/commit/57c717fee4bfbc9309845bbb48901b72e4b69304) ([#12223](https://github.com/yt-dlp/yt-dlp/issues/12223)) by [barsnick](https://github.com/barsnick)
- **cwtv**
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/18a28514e306e822eab4f3a79c76d515bf076406) ([#12207](https://github.com/yt-dlp/yt-dlp/issues/12207)) by [arantius](https://github.com/arantius)
    - movie: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/03c3d705778c07739e0034b51490877cffdc0983) ([#12227](https://github.com/yt-dlp/yt-dlp/issues/12227)) by [bashonly](https://github.com/bashonly)
- **digiview**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/f53553087d3fde9dcd61d6e9f98caf09db1d8ef2) ([#9902](https://github.com/yt-dlp/yt-dlp/issues/9902)) by [lfavole](https://github.com/lfavole)
- **dropbox**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/861aeec449c8f3c062d962945b234ff0341f61f3) ([#12228](https://github.com/yt-dlp/yt-dlp/issues/12228)) by [bashonly](https://github.com/bashonly)
- **francetv**
    - site
        - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/817483ccc68aed6049ed9c4a2ffae44ca82d2b1c) ([#12236](https://github.com/yt-dlp/yt-dlp/issues/12236)) by [bashonly](https://github.com/bashonly)
        - [Fix livestream extraction](https://github.com/yt-dlp/yt-dlp/commit/1295bbedd45fa8d9bc3f7a194864ae280297848e) ([#12316](https://github.com/yt-dlp/yt-dlp/issues/12316)) by [bashonly](https://github.com/bashonly)
- **francetvinfo.fr**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/5c4c2ddfaa47988b4d50c1ad4988badc0b4f30c2) ([#12402](https://github.com/yt-dlp/yt-dlp/issues/12402)) by [bashonly](https://github.com/bashonly)
- **gem.cbc.ca**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/5271ef48c6f61c145e03e18e960995d2e651d205) ([#12404](https://github.com/yt-dlp/yt-dlp/issues/12404)) by [bashonly](https://github.com/bashonly), [dirkf](https://github.com/dirkf)
- **generic**: [Extract `live_status` for DASH manifest URLs](https://github.com/yt-dlp/yt-dlp/commit/19edaa44fcd375f54e63d6227b092f5252d3e889) ([#12256](https://github.com/yt-dlp/yt-dlp/issues/12256)) by [mp3butcher](https://github.com/mp3butcher)
- **globo**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/f8d0161455f00add65585ca1a476a7b5d56f5f96) ([#11795](https://github.com/yt-dlp/yt-dlp/issues/11795)) by [slipinthedove](https://github.com/slipinthedove), [YoshiTabletopGamer](https://github.com/YoshiTabletopGamer)
- **goplay**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/d59f14a0a7a8b55e6bf468237def62b73ab4a517) ([#12237](https://github.com/yt-dlp/yt-dlp/issues/12237)) by [alard](https://github.com/alard)
- **pbs**: [Support www.thirteen.org URLs](https://github.com/yt-dlp/yt-dlp/commit/9fb8ab2ff67fb699f60cce09163a580976e90c0e) ([#11191](https://github.com/yt-dlp/yt-dlp/issues/11191)) by [rohieb](https://github.com/rohieb)
- **reddit**: [Bypass gated subreddit warning](https://github.com/yt-dlp/yt-dlp/commit/6ca23ffaa4663cb552f937f0b1e9769b66db11bd) ([#12335](https://github.com/yt-dlp/yt-dlp/issues/12335)) by [bashonly](https://github.com/bashonly)
- **twitter**: [Fix syndication token generation](https://github.com/yt-dlp/yt-dlp/commit/14cd7f3443c6da4d49edaefcc12da9dee86e243e) ([#12107](https://github.com/yt-dlp/yt-dlp/issues/12107)) by [Grub4K](https://github.com/Grub4K), [pjrobertson](https://github.com/pjrobertson)
- **youtube**
    - [Retry on more critical requests](https://github.com/yt-dlp/yt-dlp/commit/d48e612609d012abbea3785be4d26d78a014abb2) ([#12339](https://github.com/yt-dlp/yt-dlp/issues/12339)) by [coletdjnz](https://github.com/coletdjnz)
    - [nsig workaround for `tce` player JS](https://github.com/yt-dlp/yt-dlp/commit/ec17fb16e8d69d4e3e10fb73bf3221be8570dfee) ([#12401](https://github.com/yt-dlp/yt-dlp/issues/12401)) by [bashonly](https://github.com/bashonly)
- **zdf**: [Extract more metadata](https://github.com/yt-dlp/yt-dlp/commit/241ace4f104d50fdf7638f9203927aefcf57a1f7) ([#9565](https://github.com/yt-dlp/yt-dlp/issues/9565)) by [StefanLobbenmeier](https://github.com/StefanLobbenmeier) (With fixes in [e7882b6](https://github.com/yt-dlp/yt-dlp/commit/e7882b682b959e476d8454911655b3e9b14c79b2) by [bashonly](https://github.com/bashonly))

#### Downloader changes
- **hls**
    - [Fix `BYTERANGE` logic](https://github.com/yt-dlp/yt-dlp/commit/10b7ff68e98f17655e31952f6e17120b2d7dda96) ([#11972](https://github.com/yt-dlp/yt-dlp/issues/11972)) by [entourage8](https://github.com/entourage8)
    - [Support `--write-pages` for m3u8 media playlists](https://github.com/yt-dlp/yt-dlp/commit/be69468752ff598cacee57bb80533deab2367a5d) ([#12333](https://github.com/yt-dlp/yt-dlp/issues/12333)) by [bashonly](https://github.com/bashonly)
    - [Support `hls_media_playlist_data` format field](https://github.com/yt-dlp/yt-dlp/commit/c987be0acb6872c6561f28aa28171e803393d851) ([#12322](https://github.com/yt-dlp/yt-dlp/issues/12322)) by [bashonly](https://github.com/bashonly)

#### Misc. changes
- [Improve Issue/PR templates](https://github.com/yt-dlp/yt-dlp/commit/517ddf3c3f12560ab93e3d36244dc82db9f97818) ([#11499](https://github.com/yt-dlp/yt-dlp/issues/11499)) by [seproDev](https://github.com/seproDev) (With fixes in [4ecb833](https://github.com/yt-dlp/yt-dlp/commit/4ecb833472c90e078567b561fb7c089f1aa9587b) by [bashonly](https://github.com/bashonly))
- **cleanup**: Miscellaneous: [4985a40](https://github.com/yt-dlp/yt-dlp/commit/4985a4041770eaa0016271809a1fd950dc809a55) by [dirkf](https://github.com/dirkf), [Grub4K](https://github.com/Grub4K), [StefanLobbenmeier](https://github.com/StefanLobbenmeier)
- **docs**: [Add note to `supportedsites.md`](https://github.com/yt-dlp/yt-dlp/commit/01a63629a21781458dcbd38779898e117678f5ff) ([#12382](https://github.com/yt-dlp/yt-dlp/issues/12382)) by [seproDev](https://github.com/seproDev)
- **test**: download: [Validate and sort info dict fields](https://github.com/yt-dlp/yt-dlp/commit/208163447408c78673b08c172beafe5c310fb167) ([#12299](https://github.com/yt-dlp/yt-dlp/issues/12299)) by [bashonly](https://github.com/bashonly), [pzhlkj6612](https://github.com/pzhlkj6612)

### 2025.01.26

#### Core changes
- [Fix float comparison values in format filters](https://github.com/yt-dlp/yt-dlp/commit/f7d071e8aa3bf67ed7e0f881e749ca9ab50b3f8f) ([#11880](https://github.com/yt-dlp/yt-dlp/issues/11880)) by [bashonly](https://github.com/bashonly), [Dioarya](https://github.com/Dioarya)
- **utils**: `sanitize_path`: [Fix some incorrect behavior](https://github.com/yt-dlp/yt-dlp/commit/fc12e724a3b4988cfc467d2981887dde48c26b69) ([#11923](https://github.com/yt-dlp/yt-dlp/issues/11923)) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- **1tv**: [Support sport1tv.ru domain](https://github.com/yt-dlp/yt-dlp/commit/61ae5dc34ac775d6c122575e21ef2153b1273a2b) ([#11889](https://github.com/yt-dlp/yt-dlp/issues/11889)) by [kvk-2015](https://github.com/kvk-2015)
- **abematv**: [Support season extraction](https://github.com/yt-dlp/yt-dlp/commit/c709cc41cbc16edc846e0a431cfa8508396d4cb6) ([#11771](https://github.com/yt-dlp/yt-dlp/issues/11771)) by [middlingphys](https://github.com/middlingphys)
- **bilibili**
    - [Support space `/lists/` URLs](https://github.com/yt-dlp/yt-dlp/commit/465167910407449354eb48e9861efd0819f53eb5) ([#11964](https://github.com/yt-dlp/yt-dlp/issues/11964)) by [c-basalt](https://github.com/c-basalt)
    - [Support space video list extraction without login](https://github.com/yt-dlp/yt-dlp/commit/78912ed9c81f109169b828c397294a6cf8eacf41) ([#12089](https://github.com/yt-dlp/yt-dlp/issues/12089)) by [grqz](https://github.com/grqz)
- **bilibilidynamic**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/9676b05715b61c8c5dd5598871e60d8807fb1a86) ([#11838](https://github.com/yt-dlp/yt-dlp/issues/11838)) by [finch71](https://github.com/finch71), [grqz](https://github.com/grqz)
- **bluesky**: [Prefer source format](https://github.com/yt-dlp/yt-dlp/commit/ccda63934df7de2823f0834218c4254c7c4d2e4c) ([#12154](https://github.com/yt-dlp/yt-dlp/issues/12154)) by [0x9fff00](https://github.com/0x9fff00)
- **crunchyroll**: [Remove extractors](https://github.com/yt-dlp/yt-dlp/commit/ff44ed53061e065804da6275d182d7928cc03a5e) ([#12195](https://github.com/yt-dlp/yt-dlp/issues/12195)) by [seproDev](https://github.com/seproDev)
- **dropout**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/164368610456e2d96b279f8b120dea08f7b1d74f) ([#12102](https://github.com/yt-dlp/yt-dlp/issues/12102)) by [bashonly](https://github.com/bashonly)
- **eggs**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/20c765d02385a105c8ef13b6f7a737491d29c19a) ([#11904](https://github.com/yt-dlp/yt-dlp/issues/11904)) by [seproDev](https://github.com/seproDev), [subsense](https://github.com/subsense)
- **funimation**: [Remove extractors](https://github.com/yt-dlp/yt-dlp/commit/cdcf1e86726b8fa44f7e7126bbf1c18e1798d25c) ([#12167](https://github.com/yt-dlp/yt-dlp/issues/12167)) by [doe1080](https://github.com/doe1080)
- **goodgame**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/e7cc02b14d8d323f805d14325a9c95593a170d28) ([#12173](https://github.com/yt-dlp/yt-dlp/issues/12173)) by [NecroRomnt](https://github.com/NecroRomnt)
- **lbry**: [Support signed URLs](https://github.com/yt-dlp/yt-dlp/commit/de30f652ffb7623500215f5906844f2ae0d92c7b) ([#12138](https://github.com/yt-dlp/yt-dlp/issues/12138)) by [seproDev](https://github.com/seproDev)
- **naver**: [Fix m3u8 formats extraction](https://github.com/yt-dlp/yt-dlp/commit/b3007c44cdac38187fc6600de76959a7079a44d1) ([#12037](https://github.com/yt-dlp/yt-dlp/issues/12037)) by [kclauhk](https://github.com/kclauhk)
- **nest**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/1ef3ee7500c4ab8c26f7fdc5b0ad1da4d16eec8e) ([#11747](https://github.com/yt-dlp/yt-dlp/issues/11747)) by [pabs3](https://github.com/pabs3), [seproDev](https://github.com/seproDev)
- **niconico**: series: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/bc88b904cd02314da41ce1b2fdf046d0680fe965) ([#11822](https://github.com/yt-dlp/yt-dlp/issues/11822)) by [test20140](https://github.com/test20140)
- **nrk**
    - [Extract more formats](https://github.com/yt-dlp/yt-dlp/commit/89198bb23b4d03e0473ac408bfb50d67c2f71165) ([#12069](https://github.com/yt-dlp/yt-dlp/issues/12069)) by [hexahigh](https://github.com/hexahigh)
    - [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/45732e2590a1bd0bc9608f5eb68c59341ca84f02) ([#12193](https://github.com/yt-dlp/yt-dlp/issues/12193)) by [hexahigh](https://github.com/hexahigh)
- **patreon**: [Extract attachment filename as `alt_title`](https://github.com/yt-dlp/yt-dlp/commit/e2e73b5c65593ec0a5e685663e6ec0f4aaffc1f1) ([#12000](https://github.com/yt-dlp/yt-dlp/issues/12000)) by [msm595](https://github.com/msm595)
- **pbs**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/13825ab77815ee6e1603abbecbb9f3795057b93c) ([#12024](https://github.com/yt-dlp/yt-dlp/issues/12024)) by [dirkf](https://github.com/dirkf), [krandor](https://github.com/krandor), [n10dollar](https://github.com/n10dollar)
- **piramidetv**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/af2c821d74049b519895288aca23cee81fc4b049) ([#10777](https://github.com/yt-dlp/yt-dlp/issues/10777)) by [HobbyistDev](https://github.com/HobbyistDev), [kclauhk](https://github.com/kclauhk), [seproDev](https://github.com/seproDev)
- **redgifs**: [Support `/ifr/` URLs](https://github.com/yt-dlp/yt-dlp/commit/4850ce91d163579fa615c3c0d44c9bd64682c22b) ([#11805](https://github.com/yt-dlp/yt-dlp/issues/11805)) by [invertico](https://github.com/invertico)
- **rtvslo.si**: show: [Extract more metadata](https://github.com/yt-dlp/yt-dlp/commit/3fc46086562857d5493cbcff687f76e4e4ed303f) ([#12136](https://github.com/yt-dlp/yt-dlp/issues/12136)) by [cotko](https://github.com/cotko)
- **senategov**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/68221ecc87c6a3f3515757bac2a0f9674a38e3f2) ([#9361](https://github.com/yt-dlp/yt-dlp/issues/9361)) by [Grabien](https://github.com/Grabien), [seproDev](https://github.com/seproDev)
- **soundcloud**
    - [Extract more metadata](https://github.com/yt-dlp/yt-dlp/commit/6d304133ab32bcd1eb78ff1467f1a41dd9b66c33) ([#11945](https://github.com/yt-dlp/yt-dlp/issues/11945)) by [7x11x13](https://github.com/7x11x13)
    - user: [Add `/comments` page support](https://github.com/yt-dlp/yt-dlp/commit/7bfb4f72e490310d2681c7f4815218a2ebbc73ee) ([#11999](https://github.com/yt-dlp/yt-dlp/issues/11999)) by [7x11x13](https://github.com/7x11x13)
- **subsplash**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/5d904b077d2f58ae44bdf208d2dcfcc3ff8347f5) ([#11054](https://github.com/yt-dlp/yt-dlp/issues/11054)) by [seproDev](https://github.com/seproDev), [subrat-lima](https://github.com/subrat-lima)
- **theatercomplextownppv**: [Support `live` URLs](https://github.com/yt-dlp/yt-dlp/commit/797d2472a299692e01ad1500e8c3b7bc1daa7fe4) ([#11720](https://github.com/yt-dlp/yt-dlp/issues/11720)) by [bashonly](https://github.com/bashonly)
- **vimeo**: [Fix thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/9ff330948c92f6b2e1d9c928787362ab19cd6c62) ([#12142](https://github.com/yt-dlp/yt-dlp/issues/12142)) by [jixunmoe](https://github.com/jixunmoe)
- **vimp**: Playlist: [Add support for tags](https://github.com/yt-dlp/yt-dlp/commit/d4f5be1735c8feaeb3308666e0b878e9782f529d) ([#11688](https://github.com/yt-dlp/yt-dlp/issues/11688)) by [FestplattenSchnitzel](https://github.com/FestplattenSchnitzel)
- **weibo**: [Extend `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/a567f97b62ae9f6d6f5a9376c361512ab8dceda2) ([#12088](https://github.com/yt-dlp/yt-dlp/issues/12088)) by [4ft35t](https://github.com/4ft35t)
- **xhamster**: [Various improvements](https://github.com/yt-dlp/yt-dlp/commit/3b99a0f0e07f0120ab416f34a8f5ab75d4fdf1d1) ([#11738](https://github.com/yt-dlp/yt-dlp/issues/11738)) by [knackku](https://github.com/knackku)
- **xiaohongshu**: [Extract more formats](https://github.com/yt-dlp/yt-dlp/commit/f9f24ae376a9eaca777816479a4a29f6f0ce7681) ([#12147](https://github.com/yt-dlp/yt-dlp/issues/12147)) by [seproDev](https://github.com/seproDev)
- **youtube**
    - [Download `tv` client Innertube config](https://github.com/yt-dlp/yt-dlp/commit/326fb1ffaf4e8349f1fe8ba2a81839652e044bff) ([#12168](https://github.com/yt-dlp/yt-dlp/issues/12168)) by [coletdjnz](https://github.com/coletdjnz)
    - [Extract `media_type` for livestreams](https://github.com/yt-dlp/yt-dlp/commit/421bc72103d1faed473a451299cd17d6abb433bb) ([#11605](https://github.com/yt-dlp/yt-dlp/issues/11605)) by [nosoop](https://github.com/nosoop)
    - [Restore convenience workarounds](https://github.com/yt-dlp/yt-dlp/commit/f0d4b8a5d6354b294bc9631cf15a7160b7bad5de) ([#12181](https://github.com/yt-dlp/yt-dlp/issues/12181)) by [bashonly](https://github.com/bashonly)
    - [Update `ios` player client](https://github.com/yt-dlp/yt-dlp/commit/de82acf8769282ce321a86737ecc1d4bef0e82a7) ([#12155](https://github.com/yt-dlp/yt-dlp/issues/12155)) by [b5i](https://github.com/b5i)
    - [Use different PO token for GVS and Player](https://github.com/yt-dlp/yt-dlp/commit/6b91d232e316efa406035915532eb126fbaeea38) ([#12090](https://github.com/yt-dlp/yt-dlp/issues/12090)) by [coletdjnz](https://github.com/coletdjnz)
    - tab: [Improve shorts title extraction](https://github.com/yt-dlp/yt-dlp/commit/76ac023ff02f06e8c003d104f02a03deeddebdcd) ([#11997](https://github.com/yt-dlp/yt-dlp/issues/11997)) by [bashonly](https://github.com/bashonly), [d3d9](https://github.com/d3d9)
- **zdf**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/bb69f5dab79fb32c4ec0d50e05f7fa26d05d54ba) ([#11041](https://github.com/yt-dlp/yt-dlp/issues/11041)) by [InvalidUsernameException](https://github.com/InvalidUsernameException)

#### Misc. changes
- **cleanup**: Miscellaneous: [3b45319](https://github.com/yt-dlp/yt-dlp/commit/3b4531934465580be22937fecbb6e1a3a9e2334f) by [bashonly](https://github.com/bashonly), [lonble](https://github.com/lonble), [pjrobertson](https://github.com/pjrobertson), [seproDev](https://github.com/seproDev)

### 2025.01.15

#### Extractor changes
- **youtube**: [Do not use `web_creator` as a default client](https://github.com/yt-dlp/yt-dlp/commit/c8541f8b13e743fcfa06667530d13fee8686e22a) ([#12087](https://github.com/yt-dlp/yt-dlp/issues/12087)) by [bashonly](https://github.com/bashonly)

### 2025.01.12

#### Core changes
- [Fix filename sanitization with `--no-windows-filenames`](https://github.com/yt-dlp/yt-dlp/commit/8346b549150003df988538e54c9d8bc4de568979) ([#11988](https://github.com/yt-dlp/yt-dlp/issues/11988)) by [bashonly](https://github.com/bashonly)
- [Validate retries values are non-negative](https://github.com/yt-dlp/yt-dlp/commit/1f4e1e85a27c5b43e34d7706cfd88ffce1b56a4a) ([#11927](https://github.com/yt-dlp/yt-dlp/issues/11927)) by [Strkmn](https://github.com/Strkmn)

#### Extractor changes
- **drtalks**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/1f489f4a45691cac3f9e787d22a3a8a086229ba6) ([#10831](https://github.com/yt-dlp/yt-dlp/issues/10831)) by [pzhlkj6612](https://github.com/pzhlkj6612), [seproDev](https://github.com/seproDev)
- **plvideo**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/3c14e9191f3035b9a729d1d87bc0381f42de57cf) ([#10657](https://github.com/yt-dlp/yt-dlp/issues/10657)) by [Sanceilaks](https://github.com/Sanceilaks), [seproDev](https://github.com/seproDev)
- **vine**: [Remove extractors](https://github.com/yt-dlp/yt-dlp/commit/e2ef4fece6c9742d1733e3bae408c4787765f78c) ([#11700](https://github.com/yt-dlp/yt-dlp/issues/11700)) by [allendema](https://github.com/allendema)
- **xiaohongshu**: [Extend `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/763ed06ee69f13949397897bd42ff2ec3dc3d384) ([#11806](https://github.com/yt-dlp/yt-dlp/issues/11806)) by [HobbyistDev](https://github.com/HobbyistDev)
- **youtube**
    - [Fix DASH formats incorrectly skipped in some situations](https://github.com/yt-dlp/yt-dlp/commit/0b6b7742c2e7f2a1fcb0b54ef3dd484bab404b3f) ([#11910](https://github.com/yt-dlp/yt-dlp/issues/11910)) by [coletdjnz](https://github.com/coletdjnz)
    - [Refactor cookie auth](https://github.com/yt-dlp/yt-dlp/commit/75079f4e3f7dce49b61ef01da7adcd9876a0ca3b) ([#11989](https://github.com/yt-dlp/yt-dlp/issues/11989)) by [coletdjnz](https://github.com/coletdjnz)
    - [Use `tv` instead of `mweb` client by default](https://github.com/yt-dlp/yt-dlp/commit/712d2abb32f59b2d246be2901255f84f1a4c30b3) ([#12059](https://github.com/yt-dlp/yt-dlp/issues/12059)) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- **cleanup**: Miscellaneous: [dade5e3](https://github.com/yt-dlp/yt-dlp/commit/dade5e35c89adaad04408bfef766820dbca06ebe) by [grqz](https://github.com/grqz), [Grub4K](https://github.com/Grub4K), [seproDev](https://github.com/seproDev)

### 2024.12.23

#### Core changes
- [Don't sanitize filename on Unix when `--no-windows-filenames`](https://github.com/yt-dlp/yt-dlp/commit/6fc85f617a5850307fd5b258477070e6ee177796) ([#9591](https://github.com/yt-dlp/yt-dlp/issues/9591)) by [pukkandan](https://github.com/pukkandan)
- **update**
    - [Check 64-bitness when upgrading ARM builds](https://github.com/yt-dlp/yt-dlp/commit/b91c3925c2059970daa801cb131c0c2f4f302e72) ([#11819](https://github.com/yt-dlp/yt-dlp/issues/11819)) by [bashonly](https://github.com/bashonly)
    - [Fix endless update loop for `linux_exe` builds](https://github.com/yt-dlp/yt-dlp/commit/3d3ee458c1fe49dd5ebd7651a092119d23eb7000) ([#11827](https://github.com/yt-dlp/yt-dlp/issues/11827)) by [bashonly](https://github.com/bashonly)

#### Extractor changes
- **soundcloud**: [Various fixes](https://github.com/yt-dlp/yt-dlp/commit/d298693b1b266d198e8eeecb90ea17c4a031268f) ([#11820](https://github.com/yt-dlp/yt-dlp/issues/11820)) by [bashonly](https://github.com/bashonly)
- **youtube**
    - [Add age-gate workaround for some embeddable videos](https://github.com/yt-dlp/yt-dlp/commit/09a6c687126f04e243fcb105a828787efddd1030) ([#11821](https://github.com/yt-dlp/yt-dlp/issues/11821)) by [bashonly](https://github.com/bashonly)
    - [Fix `uploader_id` extraction](https://github.com/yt-dlp/yt-dlp/commit/1a8851b689763e5173b96f70f8a71df0e4a44b66) ([#11818](https://github.com/yt-dlp/yt-dlp/issues/11818)) by [bashonly](https://github.com/bashonly)
    - [Player client maintenance](https://github.com/yt-dlp/yt-dlp/commit/65cf46cddd873fd229dbb0fc0689bca4c201c6b6) ([#11893](https://github.com/yt-dlp/yt-dlp/issues/11893)) by [bashonly](https://github.com/bashonly)
    - [Skip iOS formats that require PO Token](https://github.com/yt-dlp/yt-dlp/commit/9f42e68a74f3f00b0253fe70763abd57cac4237b) ([#11890](https://github.com/yt-dlp/yt-dlp/issues/11890)) by [coletdjnz](https://github.com/coletdjnz)

### 2024.12.13

#### Extractor changes
- **patreon**: campaign: [Support /c/ URLs](https://github.com/yt-dlp/yt-dlp/commit/bc262bcad4d3683ceadf61a7eb87e233e72adef3) ([#11756](https://github.com/yt-dlp/yt-dlp/issues/11756)) by [bashonly](https://github.com/bashonly)
- **soundcloud**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/f4d3e9e6dc25077b79849a31a2f67f93fdc01e62) ([#11777](https://github.com/yt-dlp/yt-dlp/issues/11777)) by [bashonly](https://github.com/bashonly)
- **youtube**
    - [Fix `release_date` extraction](https://github.com/yt-dlp/yt-dlp/commit/d5e2a379f2adcb28bc48c7d9e90716d7278f89d2) ([#11759](https://github.com/yt-dlp/yt-dlp/issues/11759)) by [MutantPiggieGolem1](https://github.com/MutantPiggieGolem1)
    - [Fix signature function extraction for `2f1832d2`](https://github.com/yt-dlp/yt-dlp/commit/5460cd91891bf613a2065e2fc278d9903c37a127) ([#11801](https://github.com/yt-dlp/yt-dlp/issues/11801)) by [bashonly](https://github.com/bashonly)
    - [Prioritize original language over auto-dubbed audio](https://github.com/yt-dlp/yt-dlp/commit/dc3c4fddcc653989dae71fc563d82a308fc898cc) ([#11803](https://github.com/yt-dlp/yt-dlp/issues/11803)) by [bashonly](https://github.com/bashonly)
    - search_url: [Fix playlist searches](https://github.com/yt-dlp/yt-dlp/commit/f6c73aad5f1a67544bea137ebd9d1e22e0e56567) ([#11782](https://github.com/yt-dlp/yt-dlp/issues/11782)) by [Crypto90](https://github.com/Crypto90)

#### Misc. changes
- **cleanup**: [Make more playlist entries lazy](https://github.com/yt-dlp/yt-dlp/commit/54216696261bc07cacd9a837c501d9e0b7fed09e) ([#11763](https://github.com/yt-dlp/yt-dlp/issues/11763)) by [seproDev](https://github.com/seproDev)

### 2024.12.06

#### Core changes
- **cookies**: [Add `--cookies-from-browser` support for MS Store Firefox](https://github.com/yt-dlp/yt-dlp/commit/354cb4026cf2191e1a130ec2a627b95cabfbc60a) ([#11731](https://github.com/yt-dlp/yt-dlp/issues/11731)) by [wesson09](https://github.com/wesson09)

#### Extractor changes
- **bilibili**: [Fix HD formats extraction](https://github.com/yt-dlp/yt-dlp/commit/fca3eb5f8be08d5fab2e18b45b7281a12e566725) ([#11734](https://github.com/yt-dlp/yt-dlp/issues/11734)) by [grqz](https://github.com/grqz)
- **soundcloud**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/2feb28028ee48f2185d2d95076e62accb09b9e2e) ([#11742](https://github.com/yt-dlp/yt-dlp/issues/11742)) by [bashonly](https://github.com/bashonly)
- **youtube**
    - [Fix `n` sig extraction for player `3bb1f723`](https://github.com/yt-dlp/yt-dlp/commit/a95ee6d8803fca9157adecf63732ab58bf87fd88) ([#11750](https://github.com/yt-dlp/yt-dlp/issues/11750)) by [bashonly](https://github.com/bashonly) (With fixes in [4bd2655](https://github.com/yt-dlp/yt-dlp/commit/4bd2655398aed450456197a6767639114a24eac2))
    - [Fix signature function extraction](https://github.com/yt-dlp/yt-dlp/commit/4c85ccd1366c88cf93982f8350f58eed17355981) ([#11751](https://github.com/yt-dlp/yt-dlp/issues/11751)) by [bashonly](https://github.com/bashonly)
    - [Player client maintenance](https://github.com/yt-dlp/yt-dlp/commit/2e49c789d3eebc39af8910705d65a98bca0e4c4f) ([#11724](https://github.com/yt-dlp/yt-dlp/issues/11724)) by [bashonly](https://github.com/bashonly)

### 2024.12.03

#### Core changes
- [Add `playlist_webpage_url` field](https://github.com/yt-dlp/yt-dlp/commit/7d6c259a03bc4707a319e5e8c6eff0278707874b) ([#11613](https://github.com/yt-dlp/yt-dlp/issues/11613)) by [seproDev](https://github.com/seproDev)

#### Extractor changes
- [Handle fragmented formats in `_remove_duplicate_formats`](https://github.com/yt-dlp/yt-dlp/commit/e0500cbf796323551bbabe5b8ed8c75a511ba47a) ([#11637](https://github.com/yt-dlp/yt-dlp/issues/11637)) by [Grub4K](https://github.com/Grub4K)
- **bilibili**
    - [Always try to extract HD formats](https://github.com/yt-dlp/yt-dlp/commit/dc1687648077c5bf64863b307ecc5ab7e029bd8d) ([#10559](https://github.com/yt-dlp/yt-dlp/issues/10559)) by [grqz](https://github.com/grqz)
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/239f5f36fe04603bec59c8b975f6a792f10246db) ([#11667](https://github.com/yt-dlp/yt-dlp/issues/11667)) by [grqz](https://github.com/grqz) (With fixes in [f05a1cd](https://github.com/yt-dlp/yt-dlp/commit/f05a1cd1492fc98dc8d80d2081d632a1879913d2) by [bashonly](https://github.com/bashonly), [grqz](https://github.com/grqz))
    - [Fix subtitles and chapters extraction](https://github.com/yt-dlp/yt-dlp/commit/a13a336aa6f906812701abec8101b73b73db8ff7) ([#11708](https://github.com/yt-dlp/yt-dlp/issues/11708)) by [xiaomac](https://github.com/xiaomac)
- **chaturbate**: [Fix support for non-public streams](https://github.com/yt-dlp/yt-dlp/commit/4b5eec0aaa7c02627f27a386591b735b90e681a8) ([#11624](https://github.com/yt-dlp/yt-dlp/issues/11624)) by [jkruse](https://github.com/jkruse)
- **dacast**: [Fix HLS AES formats extraction](https://github.com/yt-dlp/yt-dlp/commit/0a0d80800b9350d1a4c4b18d82cfb77ffbc3c507) ([#11644](https://github.com/yt-dlp/yt-dlp/issues/11644)) by [bashonly](https://github.com/bashonly)
- **dropbox**: [Fix password-protected video extraction](https://github.com/yt-dlp/yt-dlp/commit/00dcde728635633eee969ad4d498b9f233c4a94e) ([#11636](https://github.com/yt-dlp/yt-dlp/issues/11636)) by [bashonly](https://github.com/bashonly)
- **duoplay**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/62cba8a1bedbfc0ddde7267ae57b72bf5f7ea7b1) ([#11588](https://github.com/yt-dlp/yt-dlp/issues/11588)) by [bashonly](https://github.com/bashonly), [glensc](https://github.com/glensc)
- **facebook**: [Support more groups URLs](https://github.com/yt-dlp/yt-dlp/commit/e0f1ae813b36e783e2348ba2a1566e12f5cd8f6e) ([#11576](https://github.com/yt-dlp/yt-dlp/issues/11576)) by [grqz](https://github.com/grqz)
- **instagram**: [Support `share` URLs](https://github.com/yt-dlp/yt-dlp/commit/360aed810ad85db950df586282d256516c98cd2d) ([#11677](https://github.com/yt-dlp/yt-dlp/issues/11677)) by [grqz](https://github.com/grqz)
- **microsoftembed**: [Make format extraction non fatal](https://github.com/yt-dlp/yt-dlp/commit/2bea7936323ca4b6f3b9b1fdd892566223e30efa) ([#11654](https://github.com/yt-dlp/yt-dlp/issues/11654)) by [seproDev](https://github.com/seproDev)
- **mitele**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/cd0f934604587ed793e9177f6a127e5dcf99a7dd) ([#11683](https://github.com/yt-dlp/yt-dlp/issues/11683)) by [DarkZeros](https://github.com/DarkZeros)
- **stripchat**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/16336c51d0848a6868a4fa04e749fa03548b4913) ([#11596](https://github.com/yt-dlp/yt-dlp/issues/11596)) by [gitninja1234](https://github.com/gitninja1234)
- **tiktok**: [Deprioritize animated thumbnails](https://github.com/yt-dlp/yt-dlp/commit/910ecc422930bca14e2abe4986f5f92359e3cea8) ([#11645](https://github.com/yt-dlp/yt-dlp/issues/11645)) by [bashonly](https://github.com/bashonly)
- **vk**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/c038a7b187ba24360f14134842a7a2cf897c33b1) ([#11715](https://github.com/yt-dlp/yt-dlp/issues/11715)) by [bashonly](https://github.com/bashonly)
- **youtube**
    - [Adjust player clients for site changes](https://github.com/yt-dlp/yt-dlp/commit/0d146c1e36f467af30e87b7af651bdee67b73500) ([#11663](https://github.com/yt-dlp/yt-dlp/issues/11663)) by [bashonly](https://github.com/bashonly)
    - tab: [Fix playlists tab extraction](https://github.com/yt-dlp/yt-dlp/commit/fe70f20aedf528fdee332131bc9b6710e54e6f10) ([#11615](https://github.com/yt-dlp/yt-dlp/issues/11615)) by [seproDev](https://github.com/seproDev)

#### Networking changes
- **Request Handler**: websockets: [Support websockets 14.0+](https://github.com/yt-dlp/yt-dlp/commit/c7316373c0a886f65a07a51e50ee147bb3294c85) ([#11616](https://github.com/yt-dlp/yt-dlp/issues/11616)) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- **cleanup**
    - [Bump ruff to 0.8.x](https://github.com/yt-dlp/yt-dlp/commit/d8fb3490863653182864d2a53522f350d67a9ff8) ([#11608](https://github.com/yt-dlp/yt-dlp/issues/11608)) by [seproDev](https://github.com/seproDev)
    - Miscellaneous
        - [ccf0a6b](https://github.com/yt-dlp/yt-dlp/commit/ccf0a6b86b7f68a75463804fe485ec240b8635f0) by [bashonly](https://github.com/bashonly), [pzhlkj6612](https://github.com/pzhlkj6612)
        - [2b67ac3](https://github.com/yt-dlp/yt-dlp/commit/2b67ac300ac8b44368fb121637d1743cea8c5b6b) by [bashonly](https://github.com/bashonly), [seproDev](https://github.com/seproDev)

### 2024.11.18

#### Important changes
- **Login with OAuth is no longer supported for YouTube**
Due to a change made by the site, yt-dlp is no longer able to support OAuth login for YouTube. [Read more](https://github.com/yt-dlp/yt-dlp/issues/11462#issuecomment-2471703090)

#### Core changes
- [Catch broken Cryptodome installations](https://github.com/yt-dlp/yt-dlp/commit/b83ca24eb72e1e558b0185bd73975586c0bc0546) ([#11486](https://github.com/yt-dlp/yt-dlp/issues/11486)) by [seproDev](https://github.com/seproDev)
- **utils**
    - [Fix `join_nonempty`, add `**kwargs` to `unpack`](https://github.com/yt-dlp/yt-dlp/commit/39d79c9b9cf23411d935910685c40aa1a2fdb409) ([#11559](https://github.com/yt-dlp/yt-dlp/issues/11559)) by [Grub4K](https://github.com/Grub4K)
    - `subs_list_to_dict`: [Add `lang` default parameter](https://github.com/yt-dlp/yt-dlp/commit/c014fbcddcb4c8f79d914ac5bb526758b540ea33) ([#11508](https://github.com/yt-dlp/yt-dlp/issues/11508)) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- [Allow `ext` override for thumbnails](https://github.com/yt-dlp/yt-dlp/commit/eb64ae7d5def6df2aba74fb703e7f168fb299865) ([#11545](https://github.com/yt-dlp/yt-dlp/issues/11545)) by [bashonly](https://github.com/bashonly)
- **adobepass**: [Fix provider requests](https://github.com/yt-dlp/yt-dlp/commit/85fdc66b6e01d19a94b4f39b58e3c0cf23600902) ([#11472](https://github.com/yt-dlp/yt-dlp/issues/11472)) by [bashonly](https://github.com/bashonly)
- **archive.org**: [Fix comments extraction](https://github.com/yt-dlp/yt-dlp/commit/f2a4983df7a64c4e93b56f79dbd16a781bd90206) ([#11527](https://github.com/yt-dlp/yt-dlp/issues/11527)) by [jshumphrey](https://github.com/jshumphrey)
- **bandlab**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/6365e92589e4bc17b8fffb0125a716d144ad2137) ([#11535](https://github.com/yt-dlp/yt-dlp/issues/11535)) by [seproDev](https://github.com/seproDev)
- **chaturbate**
    - [Extract from API and support impersonation](https://github.com/yt-dlp/yt-dlp/commit/720b3dc453c342bc2e8df7dbc0acaab4479de46c) ([#11555](https://github.com/yt-dlp/yt-dlp/issues/11555)) by [powergold1](https://github.com/powergold1) (With fixes in [7cecd29](https://github.com/yt-dlp/yt-dlp/commit/7cecd299e4a5ef1f0f044b2fedc26f17e41f15e3) by [seproDev](https://github.com/seproDev))
    - [Support alternate domains](https://github.com/yt-dlp/yt-dlp/commit/a9f85670d03ab993dc589f21a9ffffcad61392d5) ([#10595](https://github.com/yt-dlp/yt-dlp/issues/10595)) by [manavchaudhary1](https://github.com/manavchaudhary1)
- **cloudflarestream**: [Avoid extraction via videodelivery.net](https://github.com/yt-dlp/yt-dlp/commit/2db8c2e7d57a1784b06057c48e3e91023720d195) ([#11478](https://github.com/yt-dlp/yt-dlp/issues/11478)) by [hugovdev](https://github.com/hugovdev)
- **ctvnews**
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/f351440f1dc5b3dfbfc5737b037a869d946056fe) ([#11534](https://github.com/yt-dlp/yt-dlp/issues/11534)) by [bashonly](https://github.com/bashonly), [jshumphrey](https://github.com/jshumphrey)
    - [Fix playlist ID extraction](https://github.com/yt-dlp/yt-dlp/commit/f9d98509a898737c12977b2e2117277bada2c196) ([#8892](https://github.com/yt-dlp/yt-dlp/issues/8892)) by [qbnu](https://github.com/qbnu)
- **digitalconcerthall**: [Support login with access/refresh tokens](https://github.com/yt-dlp/yt-dlp/commit/f7257588bdff5f0b0452635a66b253a783c97357) ([#11571](https://github.com/yt-dlp/yt-dlp/issues/11571)) by [bashonly](https://github.com/bashonly)
- **facebook**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/bacc31b05a04181b63100c481565256b14813a5e) ([#11513](https://github.com/yt-dlp/yt-dlp/issues/11513)) by [bashonly](https://github.com/bashonly)
- **gamedevtv**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/be3579aaf0c3b71a0a3195e1955415d5e4d6b3d8) ([#11368](https://github.com/yt-dlp/yt-dlp/issues/11368)) by [bashonly](https://github.com/bashonly), [stratus-ss](https://github.com/stratus-ss)
- **goplay**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/6b43a8d84b881d769b480ba6e20ec691e9d1b92d) ([#11466](https://github.com/yt-dlp/yt-dlp/issues/11466)) by [bashonly](https://github.com/bashonly), [SamDecrock](https://github.com/SamDecrock)
- **kenh14**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/eb15fd5a32d8b35ef515f7a3d1158c03025648ff) ([#3996](https://github.com/yt-dlp/yt-dlp/issues/3996)) by [krichbanana](https://github.com/krichbanana), [pzhlkj6612](https://github.com/pzhlkj6612)
- **litv**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/e079ffbda66de150c0a9ebef05e89f61bb4d5f76) ([#11071](https://github.com/yt-dlp/yt-dlp/issues/11071)) by [jiru](https://github.com/jiru)
- **mixchmovie**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/0ec9bfed4d4a52bfb4f8733da1acf0aeeae21e6b) ([#10897](https://github.com/yt-dlp/yt-dlp/issues/10897)) by [Sakura286](https://github.com/Sakura286)
- **patreon**: [Fix comments extraction](https://github.com/yt-dlp/yt-dlp/commit/1d253b0a27110d174c40faf8fb1c999d099e0cde) ([#11530](https://github.com/yt-dlp/yt-dlp/issues/11530)) by [bashonly](https://github.com/bashonly), [jshumphrey](https://github.com/jshumphrey)
- **pialive**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/d867f99622ef7fba690b08da56c39d739b822bb7) ([#10811](https://github.com/yt-dlp/yt-dlp/issues/10811)) by [ChocoLZS](https://github.com/ChocoLZS)
- **radioradicale**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/70c55cb08f780eab687e881ef42bb5c6007d290b) ([#5607](https://github.com/yt-dlp/yt-dlp/issues/5607)) by [a13ssandr0](https://github.com/a13ssandr0), [pzhlkj6612](https://github.com/pzhlkj6612)
- **reddit**: [Improve error handling](https://github.com/yt-dlp/yt-dlp/commit/7ea2787920cccc6b8ea30791993d114fbd564434) ([#11573](https://github.com/yt-dlp/yt-dlp/issues/11573)) by [bashonly](https://github.com/bashonly)
- **redgifsuser**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/d215fba7edb69d4fa665f43663756fd260b1489f) ([#11531](https://github.com/yt-dlp/yt-dlp/issues/11531)) by [jshumphrey](https://github.com/jshumphrey)
- **rutube**: [Rework extractors](https://github.com/yt-dlp/yt-dlp/commit/e398217aae19bb25f91797bfbe8a3243698d7f45) ([#11480](https://github.com/yt-dlp/yt-dlp/issues/11480)) by [seproDev](https://github.com/seproDev)
- **sonylivseries**: [Add `sort_order` extractor-arg](https://github.com/yt-dlp/yt-dlp/commit/2009cb27e17014787bf63eaa2ada51293d54f22a) ([#11569](https://github.com/yt-dlp/yt-dlp/issues/11569)) by [bashonly](https://github.com/bashonly)
- **soop**: [Fix thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/c699bafc5038b59c9afe8c2e69175fb66424c832) ([#11545](https://github.com/yt-dlp/yt-dlp/issues/11545)) by [bashonly](https://github.com/bashonly)
- **spankbang**: [Support browser impersonation](https://github.com/yt-dlp/yt-dlp/commit/8388ec256f7753b02488788e3cfa771f6e1db247) ([#11542](https://github.com/yt-dlp/yt-dlp/issues/11542)) by [jshumphrey](https://github.com/jshumphrey)
- **spreaker**
    - [Support episode pages and access keys](https://github.com/yt-dlp/yt-dlp/commit/c39016f66df76d14284c705736ca73db8055d8de) ([#11489](https://github.com/yt-dlp/yt-dlp/issues/11489)) by [julionc](https://github.com/julionc)
    - [Support podcast and feed pages](https://github.com/yt-dlp/yt-dlp/commit/c6737310619022248f5d0fd13872073cac168453) ([#10968](https://github.com/yt-dlp/yt-dlp/issues/10968)) by [subrat-lima](https://github.com/subrat-lima)
- **youtube**
    - [Player client maintenance](https://github.com/yt-dlp/yt-dlp/commit/637d62a3a9fc723d68632c1af25c30acdadeeb85) ([#11528](https://github.com/yt-dlp/yt-dlp/issues/11528)) by [bashonly](https://github.com/bashonly), [seproDev](https://github.com/seproDev)
    - [Remove broken OAuth support](https://github.com/yt-dlp/yt-dlp/commit/52c0ffe40ad6e8404d93296f575007b05b04c686) ([#11558](https://github.com/yt-dlp/yt-dlp/issues/11558)) by [bashonly](https://github.com/bashonly)
    - tab: [Fix podcasts tab extraction](https://github.com/yt-dlp/yt-dlp/commit/37cd7660eaff397c551ee18d80507702342b0c2b) ([#11567](https://github.com/yt-dlp/yt-dlp/issues/11567)) by [seproDev](https://github.com/seproDev)

#### Misc. changes
- **build**
    - [Bump PyInstaller version pin to `>=6.11.1`](https://github.com/yt-dlp/yt-dlp/commit/f9c8deb4e5887ff5150e911ac0452e645f988044) ([#11507](https://github.com/yt-dlp/yt-dlp/issues/11507)) by [bashonly](https://github.com/bashonly)
    - [Enable attestations for trusted publishing](https://github.com/yt-dlp/yt-dlp/commit/f13df591d4d7ca8e2f31b35c9c91e69ba9e9b013) ([#11420](https://github.com/yt-dlp/yt-dlp/issues/11420)) by [bashonly](https://github.com/bashonly)
    - [Pin `websockets` version to >=13.0,<14](https://github.com/yt-dlp/yt-dlp/commit/240a7d43c8a67ffb86d44dc276805aa43c358dcc) ([#11488](https://github.com/yt-dlp/yt-dlp/issues/11488)) by [bashonly](https://github.com/bashonly)
- **cleanup**
    - [Deprecate more compat functions](https://github.com/yt-dlp/yt-dlp/commit/f95a92b3d0169a784ee15a138fbe09d82b2754a1) ([#11439](https://github.com/yt-dlp/yt-dlp/issues/11439)) by [seproDev](https://github.com/seproDev)
    - [Remove dead extractors](https://github.com/yt-dlp/yt-dlp/commit/10fc719bc7f1eef469389c5219102266ef411f29) ([#11566](https://github.com/yt-dlp/yt-dlp/issues/11566)) by [doe1080](https://github.com/doe1080)
    - Miscellaneous: [da252d9](https://github.com/yt-dlp/yt-dlp/commit/da252d9d322af3e2178ac5eae324809502a0a862) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K), [seproDev](https://github.com/seproDev)

### 2024.11.04

#### Important changes
- **Beginning with this release, yt-dlp's Python dependencies *must* be installed using the `default` group**
If you're installing yt-dlp with pip/pipx or requiring yt-dlp in your own Python project, you'll need to specify `yt-dlp[default]` if you want to also install yt-dlp's optional dependencies (which were previously included by default). [Read more](https://github.com/yt-dlp/yt-dlp/pull/11255)
- **The minimum *required* Python version has been raised to 3.9**
Python 3.8 reached its end-of-life on 2024.10.07, and yt-dlp has now removed support for it. As an unfortunate side effect, the official `yt-dlp.exe` and `yt-dlp_x86.exe` binaries are no longer supported on Windows 7. [Read more](https://github.com/yt-dlp/yt-dlp/issues/10086)

#### Core changes
- [Allow thumbnails with `.jpe` extension](https://github.com/yt-dlp/yt-dlp/commit/5bc5fb2835ea59bdf326bd12176d74d2c7348a95) ([#11408](https://github.com/yt-dlp/yt-dlp/issues/11408)) by [bashonly](https://github.com/bashonly)
- [Expand paths in `--plugin-dirs`](https://github.com/yt-dlp/yt-dlp/commit/914af9a0cf51c9a3f74aa88d952bee8334c67511) ([#11334](https://github.com/yt-dlp/yt-dlp/issues/11334)) by [bashonly](https://github.com/bashonly)
- [Fix `--netrc` empty string parsing for Python <=3.10](https://github.com/yt-dlp/yt-dlp/commit/88402b714ec124633933737bc156b172a3dec3d6) ([#11414](https://github.com/yt-dlp/yt-dlp/issues/11414)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
- [Populate format sorting fields before dependent fields](https://github.com/yt-dlp/yt-dlp/commit/5c880ef42e9c2b2fc412f6d69dad37d34fb75a62) ([#11353](https://github.com/yt-dlp/yt-dlp/issues/11353)) by [Grub4K](https://github.com/Grub4K)
- [Prioritize AV1](https://github.com/yt-dlp/yt-dlp/commit/3945677a75e94a1fecc085432d791e1c21220cd3) ([#11153](https://github.com/yt-dlp/yt-dlp/issues/11153)) by [seproDev](https://github.com/seproDev)
- [Remove Python 3.8 support](https://github.com/yt-dlp/yt-dlp/commit/d784464399b600ba9516bbcec6286f11d68974dd) ([#11321](https://github.com/yt-dlp/yt-dlp/issues/11321)) by [bashonly](https://github.com/bashonly)
- **aes**: [Fix GCM pad length calculation](https://github.com/yt-dlp/yt-dlp/commit/beae2db127d3b5017cbcf685da9de7a9ef496541) ([#11438](https://github.com/yt-dlp/yt-dlp/issues/11438)) by [seproDev](https://github.com/seproDev)
- **cookies**: [Support chrome table version 24](https://github.com/yt-dlp/yt-dlp/commit/4613096f2e6eab9dcbac0e98b6cec760bbc99375) ([#11425](https://github.com/yt-dlp/yt-dlp/issues/11425)) by [kesor](https://github.com/kesor), [seproDev](https://github.com/seproDev)
- **utils**
    - [Allow partial application for more functions](https://github.com/yt-dlp/yt-dlp/commit/b6dc2c49e8793c6dfa21275e61caf49ec1148b81) ([#11391](https://github.com/yt-dlp/yt-dlp/issues/11391)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K) (With fixes in [422195e](https://github.com/yt-dlp/yt-dlp/commit/422195ec70a00b0d2002b238cacbae7790c57fdf) by [Grub4K](https://github.com/Grub4K))
    - [Fix `find_element` by class](https://github.com/yt-dlp/yt-dlp/commit/f93c16395cea1fe9ffc3c594d3e019c3b214544c) ([#11402](https://github.com/yt-dlp/yt-dlp/issues/11402)) by [bashonly](https://github.com/bashonly)
    - [Fix and improve `find_element` and `find_elements`](https://github.com/yt-dlp/yt-dlp/commit/b103aca24d35b72b405c340357dc01a0ed534281) ([#11443](https://github.com/yt-dlp/yt-dlp/issues/11443)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- [Resolve `language` to ISO639-2 for ISM formats](https://github.com/yt-dlp/yt-dlp/commit/21cdcf03a237a0c4979c941d5a5385cae44c7906) ([#11359](https://github.com/yt-dlp/yt-dlp/issues/11359)) by [bashonly](https://github.com/bashonly)
- **ardmediathek**: [Extract chapters](https://github.com/yt-dlp/yt-dlp/commit/59f8dd8239c31f00b708da53b39b1e2e9409b6e6) ([#11442](https://github.com/yt-dlp/yt-dlp/issues/11442)) by [iw0nderhow](https://github.com/iw0nderhow)
- **bfmtv**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/754940e9a558565d6bd3c0c529802569b1d0ae4e) ([#11444](https://github.com/yt-dlp/yt-dlp/issues/11444)) by [seproDev](https://github.com/seproDev)
- **bluesky**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/5c7a5aaab27e9c3cb367b663a6136ca58866e547) ([#11055](https://github.com/yt-dlp/yt-dlp/issues/11055)) by [MellowKyler](https://github.com/MellowKyler), [seproDev](https://github.com/seproDev)
- **ccma**: [Support new 3cat.cat domain](https://github.com/yt-dlp/yt-dlp/commit/330335386d4f7603d92d6796798375336005275e) ([#11222](https://github.com/yt-dlp/yt-dlp/issues/11222)) by [JoseAngelB](https://github.com/JoseAngelB)
- **chzzk**: video: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/9c6534da81e485b2325b3489ee4128943e6d3e4b) ([#11228](https://github.com/yt-dlp/yt-dlp/issues/11228)) by [hui1601](https://github.com/hui1601)
- **cnn**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/9acf79c91a8c6c55ca972747c6858e784e2da351) ([#10185](https://github.com/yt-dlp/yt-dlp/issues/10185)) by [kylegustavo](https://github.com/kylegustavo), [seproDev](https://github.com/seproDev)
- **dailymotion**
    - [Improve embed extraction](https://github.com/yt-dlp/yt-dlp/commit/a403dcf9be20b49cbb3017328f4aaa352fb6d685) ([#10843](https://github.com/yt-dlp/yt-dlp/issues/10843)) by [bashonly](https://github.com/bashonly), [pzhlkj6612](https://github.com/pzhlkj6612)
    - [Support shortened URLs](https://github.com/yt-dlp/yt-dlp/commit/d1358231371f20fa23020fa9176be3b56119873e) ([#11374](https://github.com/yt-dlp/yt-dlp/issues/11374)) by [bashonly](https://github.com/bashonly), [seproDev](https://github.com/seproDev)
- **facebook**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/ec9b25043f399de6a591d8370d32bf0e66c117f2) ([#11343](https://github.com/yt-dlp/yt-dlp/issues/11343)) by [kclauhk](https://github.com/kclauhk)
- **generic**: [Do not impersonate by default](https://github.com/yt-dlp/yt-dlp/commit/c29f5a7fae93a08f3cfbb6127b2faa75145b06a0) ([#11336](https://github.com/yt-dlp/yt-dlp/issues/11336)) by [bashonly](https://github.com/bashonly)
- **nfl**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/838f4385de8300a4dd4e7ffbbf0e5b7b85fb52c2) ([#11409](https://github.com/yt-dlp/yt-dlp/issues/11409)) by [bashonly](https://github.com/bashonly)
- **niconicouser**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/6abef74232c0fc695cd803c18ae446cacb129389) ([#11324](https://github.com/yt-dlp/yt-dlp/issues/11324)) by [Wesley107772](https://github.com/Wesley107772)
- **soundcloud**: [Extract artists](https://github.com/yt-dlp/yt-dlp/commit/f101e5d34c97c608156ad5396714c2a2edca966a) ([#11377](https://github.com/yt-dlp/yt-dlp/issues/11377)) by [seproDev](https://github.com/seproDev)
- **tumblr**: [Support more URLs](https://github.com/yt-dlp/yt-dlp/commit/b03267bf0675eeb8df5baf1daac7cf67840c91a5) ([#6057](https://github.com/yt-dlp/yt-dlp/issues/6057)) by [selfisekai](https://github.com/selfisekai), [seproDev](https://github.com/seproDev)
- **twitter**: [Remove cookies migration workaround](https://github.com/yt-dlp/yt-dlp/commit/76802f461332d444e596437c42374fa237fa5174) ([#11392](https://github.com/yt-dlp/yt-dlp/issues/11392)) by [bashonly](https://github.com/bashonly)
- **vimeo**: [Fix API retries](https://github.com/yt-dlp/yt-dlp/commit/57212a5f97ce367590aaa5c3e9a135eead8f81f7) ([#11351](https://github.com/yt-dlp/yt-dlp/issues/11351)) by [bashonly](https://github.com/bashonly)
- **yle_areena**: [Support live events](https://github.com/yt-dlp/yt-dlp/commit/a6783a3b9905e547f6c1d4df9d7c7999feda8afa) ([#11358](https://github.com/yt-dlp/yt-dlp/issues/11358)) by [bashonly](https://github.com/bashonly), [CounterPillow](https://github.com/CounterPillow)
- **youtube**: [Adjust OAuth refresh token handling](https://github.com/yt-dlp/yt-dlp/commit/d569a8845254d90ce13ad74ae76695e8d6441068) ([#11414](https://github.com/yt-dlp/yt-dlp/issues/11414)) by [bashonly](https://github.com/bashonly)

#### Misc. changes
- **build**
    - [Disable attestations for trusted publishing](https://github.com/yt-dlp/yt-dlp/commit/428ffb75aa3534b275cf54de42693a4d261519da) ([#11418](https://github.com/yt-dlp/yt-dlp/issues/11418)) by [bashonly](https://github.com/bashonly)
    - [Move optional dependencies to the `default` group](https://github.com/yt-dlp/yt-dlp/commit/87884f15580910e4e0fe0e1db73508debc657471) ([#11255](https://github.com/yt-dlp/yt-dlp/issues/11255)) by [bashonly](https://github.com/bashonly)
    - [Use Ubuntu 20.04 and Python 3.9 for Linux ARM builds](https://github.com/yt-dlp/yt-dlp/commit/dd2e24446954246a2ec4d4a7e95531f52a14b351) ([#8638](https://github.com/yt-dlp/yt-dlp/issues/8638)) by [bashonly](https://github.com/bashonly)
- **cleanup**
    - Miscellaneous
        - [ea9e35d](https://github.com/yt-dlp/yt-dlp/commit/ea9e35d85fba5eab341cdcaf1eaed69b57f7e465) by [bashonly](https://github.com/bashonly)
        - [c998238](https://github.com/yt-dlp/yt-dlp/commit/c998238c2e76c62d1d29962c6e8ebe916cc7913b) by [bashonly](https://github.com/bashonly), [KBelmin](https://github.com/KBelmin)
        - [197d0b0](https://github.com/yt-dlp/yt-dlp/commit/197d0b03b6a3c8fe4fa5ace630eeffec629bf72c) by [avagordon01](https://github.com/avagordon01), [bashonly](https://github.com/bashonly), [grqz](https://github.com/grqz), [Grub4K](https://github.com/Grub4K), [seproDev](https://github.com/seproDev)
- **devscripts**: `make_changelog`: [Parse full commit message for fixes](https://github.com/yt-dlp/yt-dlp/commit/0a3991edae0e10f2ea41ece9fdea5e48f789f1de) ([#11366](https://github.com/yt-dlp/yt-dlp/issues/11366)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)

### 2024.10.22

#### Important changes
- **Following this release, yt-dlp's Python dependencies *must* be installed using the `default` group**
If you're installing yt-dlp with pip/pipx or requiring yt-dlp in your own Python project, you'll need to specify `yt-dlp[default]` if you want to also install yt-dlp's optional dependencies (which were previously included by default). [Read more](https://github.com/yt-dlp/yt-dlp/pull/11255)
- **py2exe is no longer supported**
This release's `yt-dlp_min.exe` will be the last, and it's actually a PyInstaller-bundled executable so that yt-dlp users updating their py2exe build with `-U` will be automatically migrated. [Read more](https://github.com/yt-dlp/yt-dlp/issues/10087)

#### Core changes
- [Add extractor helpers](https://github.com/yt-dlp/yt-dlp/commit/d710a6ca7c622705c0c8c8a3615916f531137d5d) ([#10653](https://github.com/yt-dlp/yt-dlp/issues/10653)) by [Grub4K](https://github.com/Grub4K)
- [Add option `--plugin-dirs`](https://github.com/yt-dlp/yt-dlp/commit/0f593dca9fa995d88eb763170a932da61c8f24dc) ([#11277](https://github.com/yt-dlp/yt-dlp/issues/11277)) by [coletdjnz](https://github.com/coletdjnz), [imranh2](https://github.com/imranh2)
- **cookies**: [Fix compatibility for Python <=3.9 in traceback](https://github.com/yt-dlp/yt-dlp/commit/c5f0f58efd8c3930de8202c15a5c53b1b635bd51) by [Grub4K](https://github.com/Grub4K)
- **utils**
    - `Popen`: [Reset PyInstaller environment](https://github.com/yt-dlp/yt-dlp/commit/fbc66e3ab35743cc847a21223c67d88bb463cd9c) ([#11258](https://github.com/yt-dlp/yt-dlp/issues/11258)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
    - `sanitize_path`: [Reimplement function](https://github.com/yt-dlp/yt-dlp/commit/85b87c991af25dcb35630fa94580fd418e78ee33) ([#11198](https://github.com/yt-dlp/yt-dlp/issues/11198)) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- **adobepass**: [Use newer user-agent for provider redirect request](https://github.com/yt-dlp/yt-dlp/commit/dcfeea4dd5e5686821350baa6c7767a011944867) ([#11250](https://github.com/yt-dlp/yt-dlp/issues/11250)) by [bashonly](https://github.com/bashonly)
- **afreecatv**: [Adapt extractors to new sooplive.co.kr domain](https://github.com/yt-dlp/yt-dlp/commit/46fe60ff19395698a87113b2944453779e04ab9d) ([#11266](https://github.com/yt-dlp/yt-dlp/issues/11266)) by [63427083](https://github.com/63427083), [bashonly](https://github.com/bashonly)
- **cda**: [Support folders](https://github.com/yt-dlp/yt-dlp/commit/c4d95f67ddc522297bb1fea875255cf94b34d595) ([#10786](https://github.com/yt-dlp/yt-dlp/issues/10786)) by [pktiuk](https://github.com/pktiuk)
- **cwtv**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/9d43dcb2c5c38f443f84dfc126cd32720e1a1ad6) ([#11230](https://github.com/yt-dlp/yt-dlp/issues/11230)) by [bashonly](https://github.com/bashonly)
- **drtv**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/f4338714241b11d9d43768ae71a25f5e952f677d) ([#11141](https://github.com/yt-dlp/yt-dlp/issues/11141)) by [444995](https://github.com/444995)
- **funk**: [Extend `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/8de431ec97a4b62b73df8f686b6e21e462775336) ([#11269](https://github.com/yt-dlp/yt-dlp/issues/11269)) by [seproDev](https://github.com/seproDev)
- **gem.cbc.ca**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/40054cb4a7ebbea30d335d444e6f58b298a3baa0) ([#11196](https://github.com/yt-dlp/yt-dlp/issues/11196)) by [DavidSkrundz](https://github.com/DavidSkrundz)
- **generic**: [Impersonate browser by default](https://github.com/yt-dlp/yt-dlp/commit/edfd095b1917701c5046bd51f9542897c17d41a7) ([#11206](https://github.com/yt-dlp/yt-dlp/issues/11206)) by [Grub4K](https://github.com/Grub4K)
- **imgur**
    - [Fix thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/87408ccfd772ddf31a8323d8151c24f9577cbc9f) ([#11298](https://github.com/yt-dlp/yt-dlp/issues/11298)) by [seproDev](https://github.com/seproDev)
    - [Support new URL format](https://github.com/yt-dlp/yt-dlp/commit/5af774d7a36c00bea618c7047c9326532cd3f616) ([#11075](https://github.com/yt-dlp/yt-dlp/issues/11075)) by [Deer-Spangle](https://github.com/Deer-Spangle)
- **patreon**: campaign: [Stricter URL matching](https://github.com/yt-dlp/yt-dlp/commit/babb70960595e2146f06f81affc29c7e713e34e2) ([#11235](https://github.com/yt-dlp/yt-dlp/issues/11235)) by [bashonly](https://github.com/bashonly)
- **reddit**: [Detect and raise when login is required](https://github.com/yt-dlp/yt-dlp/commit/cba7868502f04175fecf9ab3e363296aee7ebec2) ([#11202](https://github.com/yt-dlp/yt-dlp/issues/11202)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **substack**: [Resolve podcast file extensions](https://github.com/yt-dlp/yt-dlp/commit/3148c1822f66533998278f0a1cf842b9bea1526a) ([#11275](https://github.com/yt-dlp/yt-dlp/issues/11275)) by [bashonly](https://github.com/bashonly)
- **telecinco**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/0b7ec08816fb196cd41d392f8331b4eb8366c4f8) ([#11142](https://github.com/yt-dlp/yt-dlp/issues/11142)) by [bashonly](https://github.com/bashonly), [DarkZeros](https://github.com/DarkZeros)
- **tubitv**: [Strip extra whitespace from titles](https://github.com/yt-dlp/yt-dlp/commit/e68b4c19af122876561a41f2dd8093fae7b417c7) ([#10795](https://github.com/yt-dlp/yt-dlp/issues/10795)) by [allendema](https://github.com/allendema)
- **tver**: [Support series URLs](https://github.com/yt-dlp/yt-dlp/commit/ceaea731b6e314dbbdfb2e358d7677785ed0b4fc) ([#9507](https://github.com/yt-dlp/yt-dlp/issues/9507)) by [pzhlkj6612](https://github.com/pzhlkj6612), [vvto33](https://github.com/vvto33)
- **twitter**: spaces: [Allow extraction when not logged in](https://github.com/yt-dlp/yt-dlp/commit/679c68240a26481ea7c07cc0c014745631ea8481) ([#11289](https://github.com/yt-dlp/yt-dlp/issues/11289)) by [rubyevadestaxes](https://github.com/rubyevadestaxes)
- **weverse**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/5310fa87f6cb7f66bf42e2520878952fbf6b1652) ([#11215](https://github.com/yt-dlp/yt-dlp/issues/11215)) by [bashonly](https://github.com/bashonly)
- **youtube**
    - [Fix `comment_count` extraction](https://github.com/yt-dlp/yt-dlp/commit/7af1ddaaf2a6a0a750373a9ab53c7770af4f9fe4) ([#11274](https://github.com/yt-dlp/yt-dlp/issues/11274)) by [bashonly](https://github.com/bashonly)
    - [Remove broken `android_producer` client](https://github.com/yt-dlp/yt-dlp/commit/fed53d70bdb7d3e37ef63dd7fcf0ef74356167fd) ([#11297](https://github.com/yt-dlp/yt-dlp/issues/11297)) by [bashonly](https://github.com/bashonly)
    - [Remove broken age-restriction workaround](https://github.com/yt-dlp/yt-dlp/commit/ec2f4bf0823a13043f98f5bd0bf6677837bf09dc) ([#11297](https://github.com/yt-dlp/yt-dlp/issues/11297)) by [bashonly](https://github.com/bashonly)
    - [Support logging in with OAuth](https://github.com/yt-dlp/yt-dlp/commit/b8635c1d4779da195e71aa281f73aaad702c935e) ([#11001](https://github.com/yt-dlp/yt-dlp/issues/11001)) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- **build**
    - [Migrate `py2exe` builds to `win_exe`](https://github.com/yt-dlp/yt-dlp/commit/a886cf3e900f4a2ec00af705f883539269545609) ([#11256](https://github.com/yt-dlp/yt-dlp/issues/11256)) by [bashonly](https://github.com/bashonly)
    - [Use `macos-13` image for macOS builds](https://github.com/yt-dlp/yt-dlp/commit/64d84d75ca8c19ec06558cc7c511f5f4f7a822bc) ([#11236](https://github.com/yt-dlp/yt-dlp/issues/11236)) by [bashonly](https://github.com/bashonly)
    - `make_lazy_extractors`: [Force running without plugins](https://github.com/yt-dlp/yt-dlp/commit/1a830394a21a81a3e9918f9e175abc9fbb21f089) ([#11205](https://github.com/yt-dlp/yt-dlp/issues/11205)) by [Grub4K](https://github.com/Grub4K)
- **cleanup**: Miscellaneous: [67adeb7](https://github.com/yt-dlp/yt-dlp/commit/67adeb7bab00662ba55d473e405b301abb42fe61) by [bashonly](https://github.com/bashonly), [DTrombett](https://github.com/DTrombett), [grqz](https://github.com/grqz), [Grub4K](https://github.com/Grub4K), [KarboniteKream](https://github.com/KarboniteKream), [mikkovedru](https://github.com/mikkovedru), [seproDev](https://github.com/seproDev)
- **test**: [Allow running tests explicitly](https://github.com/yt-dlp/yt-dlp/commit/16eb28026a2ddf5608d0a628ef15949b8d3805a9) ([#11203](https://github.com/yt-dlp/yt-dlp/issues/11203)) by [Grub4K](https://github.com/Grub4K)

### 2024.10.07

#### Core changes
- **cookies**: [Fix cookie load error handling](https://github.com/yt-dlp/yt-dlp/commit/e59c82a74cda5139eb3928c75b0bd45484dbe7f0) ([#11140](https://github.com/yt-dlp/yt-dlp/issues/11140)) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- **applepodcasts**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/6328e2e67a4e126e08af382e6a387073082d5c5f) ([#10903](https://github.com/yt-dlp/yt-dlp/issues/10903)) by [coreywright](https://github.com/coreywright)
- **cwtv**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/4b7bec66d8100978b82bb24110ed44e2a7749931) ([#11135](https://github.com/yt-dlp/yt-dlp/issues/11135)) by [kclauhk](https://github.com/kclauhk)
- **instagram**
    - [Do not hardcode user-agent](https://github.com/yt-dlp/yt-dlp/commit/079a7bc334281d3c13d347770ae5f9f2b7da471a) ([#11155](https://github.com/yt-dlp/yt-dlp/issues/11155)) by [poyhen](https://github.com/poyhen)
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/cf85cba5d9496bd2689e1070005b4d1b4cd3dc6d) ([#11156](https://github.com/yt-dlp/yt-dlp/issues/11156)) by [tetra-fox](https://github.com/tetra-fox)
- **noodlemagazine**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/ccb23e1bac9768d1c70535beb744e668ed4a2720) ([#11144](https://github.com/yt-dlp/yt-dlp/issues/11144)) by [BallzCrasher](https://github.com/BallzCrasher)
- **patreon**: [Extract all m3u8 formats for locked posts](https://github.com/yt-dlp/yt-dlp/commit/f91645aceaf13926cf35be2c1dfef61b3aab97fb) ([#11138](https://github.com/yt-dlp/yt-dlp/issues/11138)) by [bashonly](https://github.com/bashonly)
- **youtube**: [Change default player clients to `ios,mweb`](https://github.com/yt-dlp/yt-dlp/commit/de2062753a188060d76f587e45becce61fe399f9) ([#11190](https://github.com/yt-dlp/yt-dlp/issues/11190)) by [seproDev](https://github.com/seproDev)

#### Postprocessor changes
- **xattrmetadata**: [Try to write each attribute](https://github.com/yt-dlp/yt-dlp/commit/3a193346eeb27ac2959ff30c370adb899ec94732) ([#11115](https://github.com/yt-dlp/yt-dlp/issues/11115)) by [eric321](https://github.com/eric321)

#### Misc. changes
- **ci**: [Rerun failed tests](https://github.com/yt-dlp/yt-dlp/commit/b31b81d85f00601710d4fac590c3e4efb4133283) ([#11143](https://github.com/yt-dlp/yt-dlp/issues/11143)) by [Grub4K](https://github.com/Grub4K)
- **cleanup**: Miscellaneous: [1a176d8](https://github.com/yt-dlp/yt-dlp/commit/1a176d874e6772cd898ce507379ea388e96ee3f7) by [bashonly](https://github.com/bashonly)

### 2024.09.27

#### Important changes
- **The minimum *recommended* Python version has been raised to 3.9**
Since Python 3.8 will reach end-of-life in October 2024, support for it will be dropped soon. [Read more](https://github.com/yt-dlp/yt-dlp/issues/10086)

#### Core changes
- [Allow `none` arg to negate `--convert-subs` and `--convert-thumbnails`](https://github.com/yt-dlp/yt-dlp/commit/c08e0b20b5edd8957b8318716bc14e896d1b96f4) ([#11066](https://github.com/yt-dlp/yt-dlp/issues/11066)) by [kieraneglin](https://github.com/kieraneglin)
- [Fix format sorting bug with vp9.2 vcodec](https://github.com/yt-dlp/yt-dlp/commit/8f4ea14680c7865d8ffac10a9174205d1d84ada7) ([#10884](https://github.com/yt-dlp/yt-dlp/issues/10884)) by [rakslice](https://github.com/rakslice)
- [Raise minimum recommended Python version to 3.9](https://github.com/yt-dlp/yt-dlp/commit/cca534cd9e6850c70244f225a4a1895ef4bcdbec) ([#11098](https://github.com/yt-dlp/yt-dlp/issues/11098)) by [bashonly](https://github.com/bashonly)
- **cookies**: [Improve error message for Windows `--cookies-from-browser chrome` issue](https://github.com/yt-dlp/yt-dlp/commit/b397a64691421ace5df09457c2a764821a2dc6f2) ([#11090](https://github.com/yt-dlp/yt-dlp/issues/11090)) by [seproDev](https://github.com/seproDev)
- **utils**: `mimetype2ext`: [Recognize `aacp` as `aac`](https://github.com/yt-dlp/yt-dlp/commit/cc85596d5b59f0c14e9381b3675f619c1e12e597) ([#10860](https://github.com/yt-dlp/yt-dlp/issues/10860)) by [bashonly](https://github.com/bashonly)

#### Extractor changes
- [Fix JW Player format parsing](https://github.com/yt-dlp/yt-dlp/commit/409f8e9e3b4bde81ef76fc563256f876d2ff8099) ([#10956](https://github.com/yt-dlp/yt-dlp/issues/10956)) by [seproDev](https://github.com/seproDev)
- [Handle decode errors when reading responses](https://github.com/yt-dlp/yt-dlp/commit/325001317d97f4545d66fac44c4ba772c6f45f22) ([#10868](https://github.com/yt-dlp/yt-dlp/issues/10868)) by [bashonly](https://github.com/bashonly)
- **abc.net.au**: iview, showseries: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/7f909046f4dc0fba472b4963145aef6e0d42491b) ([#11101](https://github.com/yt-dlp/yt-dlp/issues/11101)) by [bashonly](https://github.com/bashonly)
- **adn**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/cc88a54bb1ef285154775f8a6a413335ce4c71ce) ([#10749](https://github.com/yt-dlp/yt-dlp/issues/10749)) by [infanf](https://github.com/infanf)
- **asobistage**: [Support redirected URLs](https://github.com/yt-dlp/yt-dlp/commit/a7d3235c84dac57a127cbe0ff38f7f7c2fdd8fa0) ([#10768](https://github.com/yt-dlp/yt-dlp/issues/10768)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **bandcamp**: user: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/5d0176547f16a3642cd71627126e9dfc24981e20) ([#10328](https://github.com/yt-dlp/yt-dlp/issues/10328)) by [bashonly](https://github.com/bashonly), [quad](https://github.com/quad)
- **beacon**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/b4760c778d0c92c6e3f2bc8346cd72c8f08595ae) ([#9901](https://github.com/yt-dlp/yt-dlp/issues/9901)) by [Deukhoofd](https://github.com/Deukhoofd)
- **bilibili**
    - [Fix chapters and subtitles extraction](https://github.com/yt-dlp/yt-dlp/commit/a2000bc85730c950351d78bb818493dc39dca3cb) ([#11099](https://github.com/yt-dlp/yt-dlp/issues/11099)) by [bashonly](https://github.com/bashonly)
    - [Fix festival URL support](https://github.com/yt-dlp/yt-dlp/commit/b43bd864851f2862e26caa85461c5d825d49d463) ([#10740](https://github.com/yt-dlp/yt-dlp/issues/10740)) by [bashonly](https://github.com/bashonly), [grqz](https://github.com/grqz)
- **biliintl**: [Fix referer header](https://github.com/yt-dlp/yt-dlp/commit/a06bb586795ebab87a2356923acfc674d6f0e152) ([#11003](https://github.com/yt-dlp/yt-dlp/issues/11003)) by [Khaoklong51](https://github.com/Khaoklong51)
- **dropbox**: [Fix password-protected video support](https://github.com/yt-dlp/yt-dlp/commit/63da31b3b29af90062d8a72a905ffe4b5e499042) ([#10735](https://github.com/yt-dlp/yt-dlp/issues/10735)) by [ndyanx](https://github.com/ndyanx)
- **ertgr**: [Fix video extraction](https://github.com/yt-dlp/yt-dlp/commit/416686ed0cf792ec44ab059f3b229dd776077e14) ([#11091](https://github.com/yt-dlp/yt-dlp/issues/11091)) by [seproDev](https://github.com/seproDev)
- **eurosport**: [Support local URL variants](https://github.com/yt-dlp/yt-dlp/commit/f0bb28504c8c2b75ee3e5796aed50de2a7f90a1b) ([#10785](https://github.com/yt-dlp/yt-dlp/issues/10785)) by [seproDev](https://github.com/seproDev)
- **facebook**
    - ads: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/d62fef7e07d454c0d2ba2d69fb96d691dba1ded0) ([#10704](https://github.com/yt-dlp/yt-dlp/issues/10704)) by [kclauhk](https://github.com/kclauhk)
    - reel: [Improve metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/0e1b941c6b2caa688b0d3332e723d16dbafa4311) by [lengzuo](https://github.com/lengzuo)
- **germanupa**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/124f058b546d652a359c67025bb479789bfbef0b) ([#10538](https://github.com/yt-dlp/yt-dlp/issues/10538)) by [grqz](https://github.com/grqz)
- **hgtvde**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/a555389c9bb32e589e00b4664974423fb7b04dcd) ([#10992](https://github.com/yt-dlp/yt-dlp/issues/10992)) by [bashonly](https://github.com/bashonly), [rdamas](https://github.com/rdamas)
- **huya**: video: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/25c1cdaa2650563494d3bf00a38f72d0d9486bff) ([#10686](https://github.com/yt-dlp/yt-dlp/issues/10686)) by [hugepower](https://github.com/hugepower)
- **iprima**: [Fix zoom URL support](https://github.com/yt-dlp/yt-dlp/commit/4a27b8f092f7f7c10b7a334d3535c97c2af02f0a) ([#10959](https://github.com/yt-dlp/yt-dlp/issues/10959)) by [otovalek](https://github.com/otovalek)
- **khanacademy**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/0fba08485b6445b72b5b63ae23ca2a73fa5d967f) ([#10913](https://github.com/yt-dlp/yt-dlp/issues/10913)) by [seproDev](https://github.com/seproDev)
- **kick**
    - clips: [Support new URL format](https://github.com/yt-dlp/yt-dlp/commit/0aa4426e9a35f7f8e184f1f2082b3b313c1448f7) ([#11107](https://github.com/yt-dlp/yt-dlp/issues/11107)) by [bashonly](https://github.com/bashonly)
    - vod: [Support new URL format](https://github.com/yt-dlp/yt-dlp/commit/173d54c151b987409e3eb09552d8d89ed8fc50f7) ([#10988](https://github.com/yt-dlp/yt-dlp/issues/10988)) by [bashonly](https://github.com/bashonly), [grqz](https://github.com/grqz)
- **kika**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/e6f48ca80821939c1fd11ec2a0cdbf2fba9b258a) ([#5788](https://github.com/yt-dlp/yt-dlp/issues/5788)) by [1100101](https://github.com/1100101)
- **lnkgo**: [Remove extractor](https://github.com/yt-dlp/yt-dlp/commit/fa83d0b36bc43d30fe9241c1e923f4614864b758) ([#10904](https://github.com/yt-dlp/yt-dlp/issues/10904)) by [naglis](https://github.com/naglis)
- **loom**: [Fix m3u8 formats extraction](https://github.com/yt-dlp/yt-dlp/commit/7509d692b37a7ec6230ea75bfe1e44a8de5eefce) ([#10760](https://github.com/yt-dlp/yt-dlp/issues/10760)) by [kclauhk](https://github.com/kclauhk)
- **mediaklikk**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/e2b3634e299be9c16a247ece3b1858d83889c324) ([#11083](https://github.com/yt-dlp/yt-dlp/issues/11083)) by [szantnerb](https://github.com/szantnerb)
- **mojevideo**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/28b0ecba2af5b4919f198474b3d00a76ef322c31) ([#11019](https://github.com/yt-dlp/yt-dlp/issues/11019)) by [04-pasha-04](https://github.com/04-pasha-04), [pzhlkj6612](https://github.com/pzhlkj6612)
- **niconico**: [Fix m3u8 formats extraction](https://github.com/yt-dlp/yt-dlp/commit/eabb4680fdb09ba1f48d174a700a2e3b43f82add) ([#11103](https://github.com/yt-dlp/yt-dlp/issues/11103)) by [bashonly](https://github.com/bashonly)
- **nzz**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/4a9bc8c3630378bc29f0266126b503f6190c0430) ([#10461](https://github.com/yt-dlp/yt-dlp/issues/10461)) by [1-Byte](https://github.com/1-Byte)
- **patreoncampaign**: [Support API URLs](https://github.com/yt-dlp/yt-dlp/commit/232e6db30c474d1b387e405342f34173ceeaf832) ([#10734](https://github.com/yt-dlp/yt-dlp/issues/10734)) by [bashonly](https://github.com/bashonly), [hibes](https://github.com/hibes)
- **pinterest**: [Extend `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/c8c078fe28b0ffc15ef9646346c00c592fe71a78) ([#10867](https://github.com/yt-dlp/yt-dlp/issues/10867)) by [bashonly](https://github.com/bashonly), [sahilsinghss73](https://github.com/sahilsinghss73)
- **radiko**: [Extract unique `id` values](https://github.com/yt-dlp/yt-dlp/commit/c8d096c5ce111411fbdbe2abb8fed54f317a6182) ([#10726](https://github.com/yt-dlp/yt-dlp/issues/10726)) by [garret1317](https://github.com/garret1317)
- **rtp**: [Support more subpages](https://github.com/yt-dlp/yt-dlp/commit/d02df303d8e49390599db9f34482697e4d1cf5b2) ([#10787](https://github.com/yt-dlp/yt-dlp/issues/10787)) by [Demon000](https://github.com/Demon000)
- **rumblechannel**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/ad0b857f459a6d390fbf124183916218c52f223a) ([#11049](https://github.com/yt-dlp/yt-dlp/issues/11049)) by [tony-hn](https://github.com/tony-hn)
- **rutube**: [Support livestreams](https://github.com/yt-dlp/yt-dlp/commit/41be32e78c3845000dbac188ffb90ea3ea7c4dfa) ([#10844](https://github.com/yt-dlp/yt-dlp/issues/10844)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **samplefocus**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/46f4c80bc363ee8116c33d37f65202e6c3470954) ([#10947](https://github.com/yt-dlp/yt-dlp/issues/10947)) by [seproDev](https://github.com/seproDev)
- **screenrec**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/36f9e602ad55679764bc75a4f67f7562b1d6adcf) ([#10917](https://github.com/yt-dlp/yt-dlp/issues/10917)) by [naglis](https://github.com/naglis)
- **sen**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/41a241ca6ffb95b3d9aaf4f42106ca8cba9af1a6) ([#10952](https://github.com/yt-dlp/yt-dlp/issues/10952)) by [seproDev](https://github.com/seproDev)
- **servus**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/300c91274f7ea5b1b0528fc5ee11cf1a61d4079e) ([#10944](https://github.com/yt-dlp/yt-dlp/issues/10944)) by [seproDev](https://github.com/seproDev)
- **snapchatspotlight**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/b37417e4f934fd8909788b493d017777155b0ae5) ([#11030](https://github.com/yt-dlp/yt-dlp/issues/11030)) by [seproDev](https://github.com/seproDev)
- **svtpage**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/5a8a05aebb49693e78e1123015837ed5e961ff76) ([#11010](https://github.com/yt-dlp/yt-dlp/issues/11010)) by [diman8](https://github.com/diman8)
- **tenplay**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/d8d473002b654ab0e7b97ead869f58b4361eeae1) ([#10928](https://github.com/yt-dlp/yt-dlp/issues/10928)) by [aarubui](https://github.com/aarubui)
- **tiktok**: [Fix web formats extraction](https://github.com/yt-dlp/yt-dlp/commit/3ad0b7f422d547204df687b6d0b2d9110fff3990) ([#11074](https://github.com/yt-dlp/yt-dlp/issues/11074)) by [bashonly](https://github.com/bashonly)
- **twitter**: spaces: [Support video spaces](https://github.com/yt-dlp/yt-dlp/commit/bef1d4d6fc9493fda7f75e2289c07c507d10092f) ([#10789](https://github.com/yt-dlp/yt-dlp/issues/10789)) by [bashonly](https://github.com/bashonly)
- **vidflex**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/e978c312d6550a6ae4c9df18001afb1b420cb72f) ([#10002](https://github.com/yt-dlp/yt-dlp/issues/10002)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **vimeo**
    - [Always try to extract original format](https://github.com/yt-dlp/yt-dlp/commit/4115c24d157c5b5f63089d75c4e0f51d1f8b4489) ([#10721](https://github.com/yt-dlp/yt-dlp/issues/10721)) by [bashonly](https://github.com/bashonly) (With fixes in [e8e6a98](https://github.com/yt-dlp/yt-dlp/commit/e8e6a982a1b659eed434d225d7922f632bac6568) by [seproDev](https://github.com/seproDev))
    - [Fix HLS audio format sorting](https://github.com/yt-dlp/yt-dlp/commit/a1b4ac2b8ed8e6eaa56044d439f1e0d00c2ba218) ([#11082](https://github.com/yt-dlp/yt-dlp/issues/11082)) by [fireattack](https://github.com/fireattack)
- **watchespn**: [Improve auth support](https://github.com/yt-dlp/yt-dlp/commit/7adff8caf152dcf96d03aff69ed8545c0a63567c) ([#10910](https://github.com/yt-dlp/yt-dlp/issues/10910)) by [ischmidt20](https://github.com/ischmidt20)
- **wistia**: [Support password-protected videos](https://github.com/yt-dlp/yt-dlp/commit/9f5c9a90898c5a1e672922d9cd799716c73cee34) ([#11100](https://github.com/yt-dlp/yt-dlp/issues/11100)) by [bashonly](https://github.com/bashonly)
- **ximalaya**: [Add VIP support](https://github.com/yt-dlp/yt-dlp/commit/3dfd720d098b4d49d69cfc77e6376f22bcd90934) ([#10832](https://github.com/yt-dlp/yt-dlp/issues/10832)) by [seproDev](https://github.com/seproDev), [xingchensong](https://github.com/xingchensong)
- **xinpianchang**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/3aa0156e05662923d130ddbc1c82596e38c01a00) ([#10950](https://github.com/yt-dlp/yt-dlp/issues/10950)) by [seproDev](https://github.com/seproDev)
- **yleareena**: [Support podcasts](https://github.com/yt-dlp/yt-dlp/commit/48d629d461e05b1b19f5e53dc959bb9ebe95da42) ([#11104](https://github.com/yt-dlp/yt-dlp/issues/11104)) by [bashonly](https://github.com/bashonly)
- **youtube**
    - [Add `po_token`, `visitor_data`, `data_sync_id` extractor args](https://github.com/yt-dlp/yt-dlp/commit/3a3bd00037e9908e87da4fa9f2ad772aa34dc60e) ([#10648](https://github.com/yt-dlp/yt-dlp/issues/10648)) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz), [seproDev](https://github.com/seproDev) (With fixes in [fa2be9a](https://github.com/yt-dlp/yt-dlp/commit/fa2be9a7c63babede07480151363e54eee5702bd) by [bashonly](https://github.com/bashonly))
    - [Support excluding `player_client`s in extractor-arg](https://github.com/yt-dlp/yt-dlp/commit/49f3741a820ed142f6866317c2e7d247b130960e) ([#10710](https://github.com/yt-dlp/yt-dlp/issues/10710)) by [bashonly](https://github.com/bashonly)
    - clip: [Prioritize `https` formats](https://github.com/yt-dlp/yt-dlp/commit/1d84b780cf33a1d84756825ac23f990a905703df) ([#11102](https://github.com/yt-dlp/yt-dlp/issues/11102)) by [bashonly](https://github.com/bashonly)
    - tab: [Fix shorts tab extraction](https://github.com/yt-dlp/yt-dlp/commit/9431777b4c37129a6093080c77ca59960afbb9d7) ([#10938](https://github.com/yt-dlp/yt-dlp/issues/10938)) by [seproDev](https://github.com/seproDev)

#### Networking changes
- [Fix handler not being added to RequestError](https://github.com/yt-dlp/yt-dlp/commit/d1c4d88b2d912e8da5e76db455562ca63b1af690) ([#10955](https://github.com/yt-dlp/yt-dlp/issues/10955)) by [coletdjnz](https://github.com/coletdjnz)
- [Pin `curl-cffi` version to < 0.7.2](https://github.com/yt-dlp/yt-dlp/commit/5bb1aa04dafce13ba9de707ea53169fab58b5207) ([#11092](https://github.com/yt-dlp/yt-dlp/issues/11092)) by [bashonly](https://github.com/bashonly)
- **Request Handler**: websockets: [Upgrade websockets to 13.0](https://github.com/yt-dlp/yt-dlp/commit/6f9e6537434562d513d0c9b68ced8a61ade94a64) ([#10815](https://github.com/yt-dlp/yt-dlp/issues/10815)) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- **build**
    - [Bump PyInstaller version pin to `>=6.10.0`](https://github.com/yt-dlp/yt-dlp/commit/fb8b7f226d251e521a89b23c415e249e5b788e5c) ([#10709](https://github.com/yt-dlp/yt-dlp/issues/10709)) by [bashonly](https://github.com/bashonly)
    - [Pin `delocate` version for `macos`](https://github.com/yt-dlp/yt-dlp/commit/7e41628ff523b3fe373b0981a5db441358980dab) ([#10901](https://github.com/yt-dlp/yt-dlp/issues/10901)) by [bashonly](https://github.com/bashonly)
- **ci**
    - [Add comment sanitization workflow](https://github.com/yt-dlp/yt-dlp/commit/b6200bdcf3a9415ae36859188f9a57e3e461c696) ([#10915](https://github.com/yt-dlp/yt-dlp/issues/10915)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
    - [Add issue tracker anti-spam protection](https://github.com/yt-dlp/yt-dlp/commit/ad9a8115aa29a1a95c961b16fcf129a228d98f50) ([#10861](https://github.com/yt-dlp/yt-dlp/issues/10861)) by [bashonly](https://github.com/bashonly)
- **cleanup**: Miscellaneous: [c6387ab](https://github.com/yt-dlp/yt-dlp/commit/c6387abc1af9842bb0541288a5610abba9b1ab51) by [bashonly](https://github.com/bashonly), [Codenade](https://github.com/Codenade), [coletdjnz](https://github.com/coletdjnz), [grqz](https://github.com/grqz), [Grub4K](https://github.com/Grub4K), [pzhlkj6612](https://github.com/pzhlkj6612), [seproDev](https://github.com/seproDev)

### 2024.08.06

#### Core changes
- **jsinterp**: [Improve `slice` implementation](https://github.com/yt-dlp/yt-dlp/commit/bb8bf1db993f59752d20b73b861bd55e40cf0e31) ([#10664](https://github.com/yt-dlp/yt-dlp/issues/10664)) by [seproDev](https://github.com/seproDev)

#### Extractor changes
- **discoveryplusitaly**: [Support sport and olympics URLs](https://github.com/yt-dlp/yt-dlp/commit/e7d73bc4531ee3f91a46b15e218dcc1fbeb6226c) ([#10655](https://github.com/yt-dlp/yt-dlp/issues/10655)) by [bashonly](https://github.com/bashonly)
- **gem.cbc.ca**: live: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/fc5eecfa31c9571b6031cc3968aaa0394be55d7a) ([#10565](https://github.com/yt-dlp/yt-dlp/issues/10565)) by [bashonly](https://github.com/bashonly), [scribblemaniac](https://github.com/scribblemaniac)
- **niconico**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/4d9231208332d4c32364b8cd814bff8b20232cae) ([#10677](https://github.com/yt-dlp/yt-dlp/issues/10677)) by [bashonly](https://github.com/bashonly)
- **olympics**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/919540a9644e55deb78cdd6751757ec8fdaf76f4) ([#10625](https://github.com/yt-dlp/yt-dlp/issues/10625)) by [bashonly](https://github.com/bashonly)
- **youku**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/0088c6de23d832b117061a33e984dc452d992e9c) ([#10626](https://github.com/yt-dlp/yt-dlp/issues/10626)) by [hugepower](https://github.com/hugepower)
- **youtube**
    - [Change default player clients to `ios,web_creator`](https://github.com/yt-dlp/yt-dlp/commit/406f4c2e47502fffc1b0c210b4ee6487c89a44cb) ([#10674](https://github.com/yt-dlp/yt-dlp/issues/10674)) by [bashonly](https://github.com/bashonly)
    - [Fix `n` function name extraction for player `b12cc44b`](https://github.com/yt-dlp/yt-dlp/commit/c86891eb9434b4d7eec426d38c0c625b5e13cb2f) ([#10668](https://github.com/yt-dlp/yt-dlp/issues/10668)) by [seproDev](https://github.com/seproDev)

### 2024.08.01

#### Core changes
- **utils**: `unified_timestamp`: [Recognize Sunday](https://github.com/yt-dlp/yt-dlp/commit/6daf2c27c0464fba98337be30de0b66d520d0db1) ([#10589](https://github.com/yt-dlp/yt-dlp/issues/10589)) by [bashonly](https://github.com/bashonly)

#### Extractor changes
- **abematv**: [Fix availability extraction](https://github.com/yt-dlp/yt-dlp/commit/ef36d517f9b05785d61abca7691d9ab7d63cc75c) ([#10569](https://github.com/yt-dlp/yt-dlp/issues/10569)) by [middlingphys](https://github.com/middlingphys)
- **cbc.ca**: player: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/94a1c5e642e468cebeb51f74c6c220434cb47d96) ([#10302](https://github.com/yt-dlp/yt-dlp/issues/10302)) by [bashonly](https://github.com/bashonly), [trainman261](https://github.com/trainman261)
- **discoveryplus**: [Support olympics URLs](https://github.com/yt-dlp/yt-dlp/commit/0b7728618417e1aa382722a4d29b916b594d4459) ([#10566](https://github.com/yt-dlp/yt-dlp/issues/10566)) by [bashonly](https://github.com/bashonly)
- **kick**: clips: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/bb3936ae2b3ce96d0b53f9e17cad1082058f032b) ([#10572](https://github.com/yt-dlp/yt-dlp/issues/10572)) by [luvyana](https://github.com/luvyana)
- **learningonscreen**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/fe15d3178e242803ae7a934b90137f13598eba2e) ([#10590](https://github.com/yt-dlp/yt-dlp/issues/10590)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
- **mediaklikk**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/7e3e4779ad13e4511c9ba3869879e53f0267bd7a) ([#10605](https://github.com/yt-dlp/yt-dlp/issues/10605)) by [szantnerb](https://github.com/szantnerb)
- **mlbtv**: [Fix makeup game extraction](https://github.com/yt-dlp/yt-dlp/commit/4b69e1b53ea21e631cd5dd68ff531e2f1671ec17) ([#10607](https://github.com/yt-dlp/yt-dlp/issues/10607)) by [bashonly](https://github.com/bashonly)
- **olympics**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/2f1ddfe12a2c174bc777264c5c8ffe7ca0922d94) ([#10604](https://github.com/yt-dlp/yt-dlp/issues/10604)) by [bashonly](https://github.com/bashonly)
- **tva**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/28d485714fef88937c82635438afba5db81f9089) ([#10567](https://github.com/yt-dlp/yt-dlp/issues/10567)) by [bashonly](https://github.com/bashonly)
- **tver**: [Support olympic URLs](https://github.com/yt-dlp/yt-dlp/commit/5260696b1cba77161828941fdb38f09f14ac6c60) ([#10600](https://github.com/yt-dlp/yt-dlp/issues/10600)) by [vvto33](https://github.com/vvto33)
- **vimeo**: review: [Fix password-protected video extraction](https://github.com/yt-dlp/yt-dlp/commit/2b6df93a243bdfb9d6bb5c1e18020625cd02d465) ([#10598](https://github.com/yt-dlp/yt-dlp/issues/10598)) by [bashonly](https://github.com/bashonly)
- **youtube**
    - [Change default player clients to `ios,tv`](https://github.com/yt-dlp/yt-dlp/commit/efb42763dec23ccf6a2e3bac3afbfefce8efd012) ([#10457](https://github.com/yt-dlp/yt-dlp/issues/10457)) by [seproDev](https://github.com/seproDev)
    - [Fix `n` function name extraction for player `20dfca59`](https://github.com/yt-dlp/yt-dlp/commit/011b4a04db2a636c3ef0a0ad4e2d3ae482c9fd76) ([#10611](https://github.com/yt-dlp/yt-dlp/issues/10611)) by [bashonly](https://github.com/bashonly)
    - [Fix age-verification workaround](https://github.com/yt-dlp/yt-dlp/commit/d19fcb934269465fd707e68a87f735ec6983e93d) ([#10610](https://github.com/yt-dlp/yt-dlp/issues/10610)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
    - [Player client maintenance](https://github.com/yt-dlp/yt-dlp/commit/0e539617a41913c7da1edd74fb6543c10ad727b3) ([#10573](https://github.com/yt-dlp/yt-dlp/issues/10573)) by [bashonly](https://github.com/bashonly)

#### Misc. changes
- **cleanup**: Miscellaneous: [ffd7781](https://github.com/yt-dlp/yt-dlp/commit/ffd7781d6588926f820b44a34b9e6e3068fb9f97) by [bashonly](https://github.com/bashonly)

### 2024.07.25

#### Extractor changes
- **abematv**: [Adapt key retrieval to request handler framework](https://github.com/yt-dlp/yt-dlp/commit/a3bab4752a2b3d56e5a59b4e0411bb8f695c010b) ([#10491](https://github.com/yt-dlp/yt-dlp/issues/10491)) by [bashonly](https://github.com/bashonly)
- **facebook**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/1a34a802f44a1dab8f642c79c3cc810e21541d3b) ([#10531](https://github.com/yt-dlp/yt-dlp/issues/10531)) by [bashonly](https://github.com/bashonly)
- **mlbtv**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/f0993391e6052ec8f7aacc286609564f226943b9) ([#10515](https://github.com/yt-dlp/yt-dlp/issues/10515)) by [bashonly](https://github.com/bashonly)
- **tiktok**: [Fix and deprioritize JSON subtitles](https://github.com/yt-dlp/yt-dlp/commit/2f97779f335ac069ecccd9c7bf81abf4a83cfe7a) ([#10516](https://github.com/yt-dlp/yt-dlp/issues/10516)) by [bashonly](https://github.com/bashonly)
- **vimeo**: [Fix chapters extraction](https://github.com/yt-dlp/yt-dlp/commit/a0a1bc3d8d8e3bb9a48a06e835815a0460e90e77) ([#10544](https://github.com/yt-dlp/yt-dlp/issues/10544)) by [bashonly](https://github.com/bashonly)
- **youtube**: [Fix `n` function name extraction for player `3400486c`](https://github.com/yt-dlp/yt-dlp/commit/713b4cd18f00556771af8cfdd9cea6cc1a09e948) ([#10542](https://github.com/yt-dlp/yt-dlp/issues/10542)) by [bashonly](https://github.com/bashonly)

#### Misc. changes
- **build**: [Pin `setuptools` version](https://github.com/yt-dlp/yt-dlp/commit/e046db8a116b1c320d4785daadd48ea0b22a3987) ([#10493](https://github.com/yt-dlp/yt-dlp/issues/10493)) by [bashonly](https://github.com/bashonly)

### 2024.07.16

#### Core changes
- [Fix `noprogress` if `test=True` with `--quiet` and `--verbose`](https://github.com/yt-dlp/yt-dlp/commit/66ce3d76d87af3f81cc9dfec4be4704016cb1cdb) ([#10454](https://github.com/yt-dlp/yt-dlp/issues/10454)) by [Grub4K](https://github.com/Grub4K)
- [Support `auto-tty` and `no_color-tty` for `--color`](https://github.com/yt-dlp/yt-dlp/commit/d9cbced493cae2008508d94a2db5dd98be7c01fc) ([#10453](https://github.com/yt-dlp/yt-dlp/issues/10453)) by [Grub4K](https://github.com/Grub4K)
- **update**: [Fix network error handling](https://github.com/yt-dlp/yt-dlp/commit/ed1b9ed93dd90d2cc960c0d8eaa9d919db224203) ([#10486](https://github.com/yt-dlp/yt-dlp/issues/10486)) by [bashonly](https://github.com/bashonly)
- **utils**: `parse_codecs`: [Fix parsing of mixed case codec strings](https://github.com/yt-dlp/yt-dlp/commit/cc0070f6496e501d77352bad475fb02d6a86846a) by [bashonly](https://github.com/bashonly)

#### Extractor changes
- **adn**: [Adjust for .com domain change](https://github.com/yt-dlp/yt-dlp/commit/959b7a379b8e5da059d110a63339c964b6265736) ([#10399](https://github.com/yt-dlp/yt-dlp/issues/10399)) by [infanf](https://github.com/infanf)
- **afreecatv**: [Fix login and use `legacy_ssl`](https://github.com/yt-dlp/yt-dlp/commit/4cd41469243624d90b7a2009b95cbe0609343efe) ([#10440](https://github.com/yt-dlp/yt-dlp/issues/10440)) by [bashonly](https://github.com/bashonly)
- **box**: [Support enterprise URLs](https://github.com/yt-dlp/yt-dlp/commit/705f5b84dec75cc7af97f42fd1530e8062735970) ([#10419](https://github.com/yt-dlp/yt-dlp/issues/10419)) by [seproDev](https://github.com/seproDev)
- **digitalconcerthall**: [Extract HEVC and FLAC formats](https://github.com/yt-dlp/yt-dlp/commit/e62fa6b0e0186f8c5666c2c5ab64cf191abdafc1) ([#10470](https://github.com/yt-dlp/yt-dlp/issues/10470)) by [bashonly](https://github.com/bashonly)
- **dplay**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/39e6c4cb44b9292e89ac0afec3cd0afc2ae8775f) ([#10471](https://github.com/yt-dlp/yt-dlp/issues/10471)) by [bashonly](https://github.com/bashonly)
- **epidemicsound**: [Support sound effects URLs](https://github.com/yt-dlp/yt-dlp/commit/8531d2b03bac9cc746f2ee8098aaf8f115505f5b) ([#10436](https://github.com/yt-dlp/yt-dlp/issues/10436)) by [iancmy](https://github.com/iancmy)
- **generic**: [Fix direct video link extensions](https://github.com/yt-dlp/yt-dlp/commit/b9afb99e7c34d0eb15ddc6689cd7d20eebfda68e) ([#10468](https://github.com/yt-dlp/yt-dlp/issues/10468)) by [bashonly](https://github.com/bashonly)
- **picarto**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/bacd18b7df08b4995644fd12cee1f8c8e8636bc7) ([#10414](https://github.com/yt-dlp/yt-dlp/issues/10414)) by [Frankgoji](https://github.com/Frankgoji)
- **soundcloud**: permalink, user: [Extract tracks only](https://github.com/yt-dlp/yt-dlp/commit/22870b81bad97dfa6307a7add44753b2dffc76a9) ([#10463](https://github.com/yt-dlp/yt-dlp/issues/10463)) by [DunnesH](https://github.com/DunnesH)
- **tiktok**: live: [Fix room ID extraction](https://github.com/yt-dlp/yt-dlp/commit/d2189d3d36987ebeac426fd70a60a5fe86325a2b) ([#10408](https://github.com/yt-dlp/yt-dlp/issues/10408)) by [mokrueger](https://github.com/mokrueger)
- **tv5monde**: [Support browser impersonation](https://github.com/yt-dlp/yt-dlp/commit/9b95a6765a5f6325af99c4aca961587f0c426e8c) ([#10417](https://github.com/yt-dlp/yt-dlp/issues/10417)) by [bashonly](https://github.com/bashonly) (With fixes in [cc1a309](https://github.com/yt-dlp/yt-dlp/commit/cc1a3098c00995c6aebc2a16bd1050a66bad64db))
- **youtube**
    - [Avoid poToken experiment player responses](https://github.com/yt-dlp/yt-dlp/commit/8b8b442cb005a8d85315f301615f83fb736b967a) ([#10456](https://github.com/yt-dlp/yt-dlp/issues/10456)) by [seproDev](https://github.com/seproDev) (With fixes in [16da8ef](https://github.com/yt-dlp/yt-dlp/commit/16da8ef9937ff76632dfef02e5062c5ba99c8ea2))
    - [Invalidate nsig cache from < 2024.07.09](https://github.com/yt-dlp/yt-dlp/commit/04e17ba20a139f1b3e30ec4bafa3fba26888f0b3) ([#10401](https://github.com/yt-dlp/yt-dlp/issues/10401)) by [bashonly](https://github.com/bashonly)
    - [Reduce android client priority](https://github.com/yt-dlp/yt-dlp/commit/b85eef0a615a01304f88a3847309c667e09a20df) ([#10467](https://github.com/yt-dlp/yt-dlp/issues/10467)) by [seproDev](https://github.com/seproDev)

#### Networking changes
- [Add `legacy_ssl` request extension](https://github.com/yt-dlp/yt-dlp/commit/150ecc45d9cacc919550c13b04fd998ac5103a6b) ([#10448](https://github.com/yt-dlp/yt-dlp/issues/10448)) by [coletdjnz](https://github.com/coletdjnz)
- **Request Handler**: curl_cffi: [Support `curl_cffi` 0.7.X](https://github.com/yt-dlp/yt-dlp/commit/42bfca00a6b460fc053514cdd7ac6f5b5daddf0c) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- **build**
    - [Include `curl_cffi` in `yt-dlp_linux`](https://github.com/yt-dlp/yt-dlp/commit/4521f30d1479315cd5c3bf4abdad19391952df98) by [bashonly](https://github.com/bashonly)
    - [Pin `curl-cffi` to 0.5.10 for Windows](https://github.com/yt-dlp/yt-dlp/commit/ac30941ae682f71eab010877c9a977736a61d3cf) by [bashonly](https://github.com/bashonly)
- **cleanup**: Miscellaneous: [89a161e](https://github.com/yt-dlp/yt-dlp/commit/89a161e8c62569a662deda1c948664152efcb6b4) by [bashonly](https://github.com/bashonly)

### 2024.07.09

#### Core changes
- [Do not alter default format selection when simulated](https://github.com/yt-dlp/yt-dlp/commit/0b570f2a90ce2363ba06089217514d644e7be2e0) ([#9862](https://github.com/yt-dlp/yt-dlp/issues/9862)) by [seproDev](https://github.com/seproDev)

#### Extractor changes
- **youtube**: [Remove broken `n` function extraction fallback](https://github.com/yt-dlp/yt-dlp/commit/7ead7332af69422cee931aec3faa277288e9e212) ([#10396](https://github.com/yt-dlp/yt-dlp/issues/10396)) by [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)

### 2024.07.08

#### Core changes
- **jsinterp**: [Implement `Function.prototype` resolving for `call` and `apply`](https://github.com/yt-dlp/yt-dlp/commit/6c056ea7aeb03660281653a9668547f2548f194f) ([#10392](https://github.com/yt-dlp/yt-dlp/issues/10392)) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- **soundcloud**: [Fix rate-limit handling](https://github.com/yt-dlp/yt-dlp/commit/4b50b292cc98534fb8c7cdf0ae5cb85862f7ebfc) ([#10389](https://github.com/yt-dlp/yt-dlp/issues/10389)) by [bashonly](https://github.com/bashonly)
- **youtube**: [Fix JS `n` function name extraction](https://github.com/yt-dlp/yt-dlp/commit/297b0a379282a15c80d82d51f3757c961db2dae1) ([#10390](https://github.com/yt-dlp/yt-dlp/issues/10390)) by [bashonly](https://github.com/bashonly), [seproDev](https://github.com/seproDev)

### 2024.07.07

#### Important changes
- Security: [[ie/douyutv] Do not use dangerous javascript source/URL](https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-3v33-3wmw-3785)
    - A dependency on potentially malicious third-party JavaScript code has been removed from the Douyu extractors

#### Core changes
- [Address gaps in allowed extensions](https://github.com/yt-dlp/yt-dlp/commit/2469119490d7e0397ebbf5c5ae327316f955eef2) ([#10362](https://github.com/yt-dlp/yt-dlp/issues/10362)) by [bashonly](https://github.com/bashonly)
- [Fix `--ignore-no-formats-error`](https://github.com/yt-dlp/yt-dlp/commit/cc767e9490056efaaa11c186b0d032e4b4969180) ([#10345](https://github.com/yt-dlp/yt-dlp/issues/10345)) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- **abematv**: [Extract availability](https://github.com/yt-dlp/yt-dlp/commit/2a1a1b8e67e864289ac7ba5d05ec63dbb19a639f) ([#10348](https://github.com/yt-dlp/yt-dlp/issues/10348)) by [middlingphys](https://github.com/middlingphys)
- **chzzk**: [Extract with API v3](https://github.com/yt-dlp/yt-dlp/commit/4862a29854d4044120e3f97b52199711ad04bee1) ([#10363](https://github.com/yt-dlp/yt-dlp/issues/10363)) by [hui1601](https://github.com/hui1601)
- **douyutv**: [Do not use dangerous javascript source/URL](https://github.com/yt-dlp/yt-dlp/commit/6075a029dba70a89675ae1250e7cdfd91f0eba41) ([#10347](https://github.com/yt-dlp/yt-dlp/issues/10347)) by [LeSuisse](https://github.com/LeSuisse)
- **jiosaavn**: playlist: [Support featured playlists](https://github.com/yt-dlp/yt-dlp/commit/f0f867f008a1728f5f6ac1224b9e014b5d27f817) ([#10382](https://github.com/yt-dlp/yt-dlp/issues/10382)) by [harbhim](https://github.com/harbhim)
- **vidyard**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/00766ece0c5c7a80781a4ff677198c5fb69d9dc0) ([#10155](https://github.com/yt-dlp/yt-dlp/issues/10155)) by [exterrestris](https://github.com/exterrestris)
- **vimeo**: [Fix password-protected video extraction](https://github.com/yt-dlp/yt-dlp/commit/c1c9bb4adb42d0d93a2fb5d93a7de0a87b6ba884) ([#10341](https://github.com/yt-dlp/yt-dlp/issues/10341)) by [bashonly](https://github.com/bashonly)
- **vtv**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/987a1f94c24275f2b0cd82e719956687415dd732) ([#10173](https://github.com/yt-dlp/yt-dlp/issues/10173)) by [DinhHuy2010](https://github.com/DinhHuy2010)
- **yle_areena**
    - [Fix metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/4cdc976bd861b5835601ae402bef543eacd88f3d) ([#10380](https://github.com/yt-dlp/yt-dlp/issues/10380)) by [seproDev](https://github.com/seproDev)
    - [Fix subtitle extraction](https://github.com/yt-dlp/yt-dlp/commit/0d174e8bed32081eb38ef7f5d1a1282ae154f517) ([#10379](https://github.com/yt-dlp/yt-dlp/issues/10379)) by [Grub4K](https://github.com/Grub4K)

#### Misc. changes
- **cleanup**: Miscellaneous: [b337d29](https://github.com/yt-dlp/yt-dlp/commit/b337d2989ce0614651d363383f6f743d977248ef) by [bashonly](https://github.com/bashonly)

### 2024.07.02

#### Core changes
- [Fix `--compat-opt allow-unsafe-ext`](https://github.com/yt-dlp/yt-dlp/commit/773bbb181506856ffda95496ab60c1c9603f1f71) ([#10336](https://github.com/yt-dlp/yt-dlp/issues/10336)) by [bashonly](https://github.com/bashonly), [rdamas](https://github.com/rdamas)

#### Extractor changes
- **banbye**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/7509791385ba88cb7ec0ab17e826681f4af4b66e) ([#10332](https://github.com/yt-dlp/yt-dlp/issues/10332)) by [PatrykMis](https://github.com/PatrykMis), [seproDev](https://github.com/seproDev)
- **murrtube**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/6403530e2dfe259a87afe444708c4f3024cc45b8) ([#9249](https://github.com/yt-dlp/yt-dlp/issues/9249)) by [DrakoCpp](https://github.com/DrakoCpp)
- **zaiko**: [Support JWT video URLs](https://github.com/yt-dlp/yt-dlp/commit/7799e518956387bb3c1064c9beae26eab8d5044a) ([#10130](https://github.com/yt-dlp/yt-dlp/issues/10130)) by [pzhlkj6612](https://github.com/pzhlkj6612)

#### Postprocessor changes
- **embedthumbnail**: [Fix embedding with mutagen](https://github.com/yt-dlp/yt-dlp/commit/d502f4c6d95b74896f40070d07229997f0850f31) ([#10337](https://github.com/yt-dlp/yt-dlp/issues/10337)) by [bashonly](https://github.com/bashonly)

#### Misc. changes
- **cleanup**: Miscellaneous: [93d33cb](https://github.com/yt-dlp/yt-dlp/commit/93d33cb29af9e2e84369ac43589d50ce8e0160ef) by [bashonly](https://github.com/bashonly)

### 2024.07.01

#### Important changes
- Security: [[CVE-2024-38519](https://nvd.nist.gov/vuln/detail/CVE-2024-38519)] [Properly sanitize file-extension to prevent file system modification and RCE](https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-79w7-vh3h-8g4j)
    - Unsafe extensions are now blocked from being downloaded

#### Core changes
- [Add `playlist_channel` and `playlist_channel_id` fields](https://github.com/yt-dlp/yt-dlp/commit/55e3e6fd21e741ec5ae3d8624de5e5ea345810eb) ([#10266](https://github.com/yt-dlp/yt-dlp/issues/10266)) by [bashonly](https://github.com/bashonly)
- [Disallow unsafe extensions (CVE-2024-38519)](https://github.com/yt-dlp/yt-dlp/commit/5ce582448ececb8d9c30c8c31f58330090ced03a) by [Grub4K](https://github.com/Grub4K)
- **cookies**: [Fix `--cookies-from-browser` DE detection on Linux](https://github.com/yt-dlp/yt-dlp/commit/a8520244b8642880e4d35925e9e49eff94d548de) ([#10237](https://github.com/yt-dlp/yt-dlp/issues/10237)) by [peisenwang](https://github.com/peisenwang)

#### Extractor changes
- **afreecatv**
    - [Support browser impersonation](https://github.com/yt-dlp/yt-dlp/commit/e8352ad6599de7b5371dc39a1a1edc7890aaedb4) ([#10174](https://github.com/yt-dlp/yt-dlp/issues/10174)) by [hui1601](https://github.com/hui1601)
    - catchstory: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/054a3ba7d1293f9fbe21800d62d1e5ddcbded238) ([#10235](https://github.com/yt-dlp/yt-dlp/issues/10235)) by [hui1601](https://github.com/hui1601)
- **bilibili**: [Support legacy formats](https://github.com/yt-dlp/yt-dlp/commit/1d6ab17d0752ee9cf19e3e63c7dec7b600d3f228) ([#9117](https://github.com/yt-dlp/yt-dlp/issues/9117)) by [c-basalt](https://github.com/c-basalt), [GD-Slime](https://github.com/GD-Slime)
- **bitchute**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/5b1a2aa978d0074cee278e7659f32f52ecc4ab53) ([#10301](https://github.com/yt-dlp/yt-dlp/issues/10301)) by [seproDev](https://github.com/seproDev)
- **brightcove**: [Upgrade requests to HTTPS](https://github.com/yt-dlp/yt-dlp/commit/90c3721a322756bb7f4ca10ceb73744500bee37e) ([#10202](https://github.com/yt-dlp/yt-dlp/issues/10202)) by [bashonly](https://github.com/bashonly)
- **cloudflarestream**: [Fix `_VALID_URL` and embed extraction](https://github.com/yt-dlp/yt-dlp/commit/7aa322c02cec54eb77154a89da7e400194f0bd03) ([#10215](https://github.com/yt-dlp/yt-dlp/issues/10215)) by [bashonly](https://github.com/bashonly)
- **cloudycdn**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/b758877afa225747fba81c8a580e27583a231734) ([#10271](https://github.com/yt-dlp/yt-dlp/issues/10271)) by [Caesim404](https://github.com/Caesim404)
- **digitalconcerthall**: [Rework extractor](https://github.com/yt-dlp/yt-dlp/commit/2a4f2e82dbeeb0c9130883c83dac689d5260c871) ([#10152](https://github.com/yt-dlp/yt-dlp/issues/10152)) by [seproDev](https://github.com/seproDev), [tippfehlr](https://github.com/tippfehlr)
- **facebook**: reel: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/8ca1d57ed08d00efa117820a5a82f763b20e2d1d) ([#10232](https://github.com/yt-dlp/yt-dlp/issues/10232)) by [bashonly](https://github.com/bashonly)
- **francetv**
    - [Detect and raise errors for DRM](https://github.com/yt-dlp/yt-dlp/commit/3690c2f59827c79a1bbe388a7c1ae75db7477db2) ([#10165](https://github.com/yt-dlp/yt-dlp/issues/10165)) by [bashonly](https://github.com/bashonly)
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/081708d6074dfbb907e25af61ba530bba0d4b31d) ([#10177](https://github.com/yt-dlp/yt-dlp/issues/10177)) by [bashonly](https://github.com/bashonly)
- **generic**: [Add `key_query` extractor-arg](https://github.com/yt-dlp/yt-dlp/commit/5dbac313ae4e3e8521dfe2e1a6a048a98ff4b4fe) by [bashonly](https://github.com/bashonly)
- **graspop**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/1d369b4096d79233e0ac2c93762746a64d7a69c8) ([#10268](https://github.com/yt-dlp/yt-dlp/issues/10268)) by [Niluge-KiWi](https://github.com/Niluge-KiWi)
- **jiocinema**: series: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/61714f46956f61612032bba857aed7ad1387eccd) ([#10139](https://github.com/yt-dlp/yt-dlp/issues/10139)) by [varunchopra](https://github.com/varunchopra)
- **khanacademy**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/4093eb1fcc29a0e2aea9adfcba479787d9ae0c0c) ([#9136](https://github.com/yt-dlp/yt-dlp/issues/9136)) by [c-basalt](https://github.com/c-basalt)
- **laracasts**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/b8da8a98f897599095d4ef1644b8c5fd39921118) ([#10055](https://github.com/yt-dlp/yt-dlp/issues/10055)) by [ASertacAkkaya](https://github.com/ASertacAkkaya), [seproDev](https://github.com/seproDev)
- **matchtv**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/f3411af12e209bc5624e1ac31271b8aabe2d3c90) ([#10190](https://github.com/yt-dlp/yt-dlp/issues/10190)) by [megumintyan](https://github.com/megumintyan)
- **mediasite**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/0953209a857c51648aee89d205c086b0e1dd3864) ([#10273](https://github.com/yt-dlp/yt-dlp/issues/10273)) by [bashonly](https://github.com/bashonly)
- **microsoftembed**: [Add extractors for dev materials](https://github.com/yt-dlp/yt-dlp/commit/9200bc70c94546b2191bb6fbfc9cea98a919cc56) ([#9177](https://github.com/yt-dlp/yt-dlp/issues/9177)) by [c-basalt](https://github.com/c-basalt)
- **mlbtv**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/61edf57f8f13f6dfd81154174e647eb5fdd26089) ([#10296](https://github.com/yt-dlp/yt-dlp/issues/10296)) by [bashonly](https://github.com/bashonly)
- **neteasemusic**: [Extract more formats from new API](https://github.com/yt-dlp/yt-dlp/commit/7a03f88c40b80d3cf54f68edd9d4bdd6aa527570) ([#10258](https://github.com/yt-dlp/yt-dlp/issues/10258)) by [hafeoz](https://github.com/hafeoz)
- **nhkradiru**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/b8e2a5e0e1030076f833917906e19bb6c7b318f6) ([#10106](https://github.com/yt-dlp/yt-dlp/issues/10106)) by [garret1317](https://github.com/garret1317)
- **nuum**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/aefede25561a06cba398d4f593eee2fbe942693b) ([#10316](https://github.com/yt-dlp/yt-dlp/issues/10316)) by [DmitryScaletta](https://github.com/DmitryScaletta)
- **orf**
    - on
        - [Add `prefer_segments_playlist` extractor-arg](https://github.com/yt-dlp/yt-dlp/commit/e6a22834df1776ec4e486526f6df2bf53cb7e06f) ([#10314](https://github.com/yt-dlp/yt-dlp/issues/10314)) by [seproDev](https://github.com/seproDev)
        - [Support segmented episodes](https://github.com/yt-dlp/yt-dlp/commit/8b46ad4d8b8ee8c5472af0cde863baa89ca3f425) ([#10053](https://github.com/yt-dlp/yt-dlp/issues/10053)) by [seproDev](https://github.com/seproDev)
- **patreoncampaign**: [Fix `campaign_id` extraction](https://github.com/yt-dlp/yt-dlp/commit/2e5a47da400b645aadbda6afd1156bd89c744f48) ([#10070](https://github.com/yt-dlp/yt-dlp/issues/10070)) by [bashonly](https://github.com/bashonly)
- **podbayfm**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/d4b52ce3fcb8d9578ed12365648eaba8718c603e) ([#10195](https://github.com/yt-dlp/yt-dlp/issues/10195)) by [bashonly](https://github.com/bashonly), [seproDev](https://github.com/seproDev)
- **pokergo**: [Make metadata extraction non-fatal](https://github.com/yt-dlp/yt-dlp/commit/36e8dd832579b5375a0f6626af4268b86b4eb21a) ([#10319](https://github.com/yt-dlp/yt-dlp/issues/10319)) by [axpauls](https://github.com/axpauls)
- **qqmusic**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/4f5d7be3c5590bb257d8ff521572aee9839ab754) ([#9768](https://github.com/yt-dlp/yt-dlp/issues/9768)) by [c-basalt](https://github.com/c-basalt)
- **rtvslo.si**: show: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/92a1c4abaeeba9a69d611c57b73555cb1a1f00ad) ([#8418](https://github.com/yt-dlp/yt-dlp/issues/8418)) by [JSubelj](https://github.com/JSubelj), [seproDev](https://github.com/seproDev)
- **soundcloud**: [Fix `download` format extraction](https://github.com/yt-dlp/yt-dlp/commit/e53e56b73543799638fa6abb0c78f8b091aa84e1) ([#10125](https://github.com/yt-dlp/yt-dlp/issues/10125)) by [bashonly](https://github.com/bashonly)
- **sproutvideo**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/d6c2c2bc84f1434255be5c73baeb17d893d2c0d4) ([#10098](https://github.com/yt-dlp/yt-dlp/issues/10098)) by [bashonly](https://github.com/bashonly), [TheZ3ro](https://github.com/TheZ3ro)
- **tiktok**
    - [Detect and raise when login is required](https://github.com/yt-dlp/yt-dlp/commit/ea88129784fcbb6987161df9ba05909325d8e2e9) ([#10124](https://github.com/yt-dlp/yt-dlp/issues/10124)) by [bashonly](https://github.com/bashonly)
    - [Fix API extraction](https://github.com/yt-dlp/yt-dlp/commit/96472d72f29550c25c5dcedcde02c38c192b0011) ([#10216](https://github.com/yt-dlp/yt-dlp/issues/10216)) by [bashonly](https://github.com/bashonly)
- **tubitv**
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/bef9a9e5361fd7a72e21d0f1a8c8afb70d89e8c5) ([#9975](https://github.com/yt-dlp/yt-dlp/issues/9975)) by [chilinux](https://github.com/chilinux)
    - series: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/d7d861811c15585a4f7ec9d5ae68d2ac28de28a0) ([#10116](https://github.com/yt-dlp/yt-dlp/issues/10116)) by [bashonly](https://github.com/bashonly)
- **vimeo**: [Support browser impersonation](https://github.com/yt-dlp/yt-dlp/commit/d4b99a233314bf31f9c842035ea9884673d5313a) ([#10327](https://github.com/yt-dlp/yt-dlp/issues/10327)) by [bashonly](https://github.com/bashonly)
- **youtube**
    - [Extract all formats from multi-language m3u8s](https://github.com/yt-dlp/yt-dlp/commit/9bd85019931927a99b0fe0dc58ac51acca9fbe72) ([#9875](https://github.com/yt-dlp/yt-dlp/issues/9875)) by [bashonly](https://github.com/bashonly), [clienthax](https://github.com/clienthax)
    - [Skip formats if nsig decoding fails](https://github.com/yt-dlp/yt-dlp/commit/800ec085ccf98420584d8bb38c20a2c079669b09) ([#10223](https://github.com/yt-dlp/yt-dlp/issues/10223)) by [bashonly](https://github.com/bashonly)
    - [Suppress "Unavailable videos are hidden" warning](https://github.com/yt-dlp/yt-dlp/commit/24f3097ea9a470a984d0454dc013cafa2325f5f8) ([#10159](https://github.com/yt-dlp/yt-dlp/issues/10159)) by [mgedmin](https://github.com/mgedmin)
    - tab: [Fix channel metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/a0d9967f6822fc279e86bce33464194985148727) ([#10071](https://github.com/yt-dlp/yt-dlp/issues/10071)) by [bashonly](https://github.com/bashonly), [shoxie007](https://github.com/shoxie007)

#### Downloader changes
- **hls**: [Apply `extra_param_to_key_url` from info dict](https://github.com/yt-dlp/yt-dlp/commit/ca8885edd93bdf8912af6c22ee335b6222cb9ba9) by [bashonly](https://github.com/bashonly)

#### Postprocessor changes
- **embedthumbnail**: [Fix postprocessor](https://github.com/yt-dlp/yt-dlp/commit/f2a4ea1794718e4dc0148bc172cb877f1080903b) ([#10248](https://github.com/yt-dlp/yt-dlp/issues/10248)) by [Grub4K](https://github.com/Grub4K)

#### Networking changes
- **Request Handler**: requests: [Bump minimum `requests` version to 2.32.2](https://github.com/yt-dlp/yt-dlp/commit/db50f19d76c6870a5a13d0cab9287d684fd7449a) ([#10079](https://github.com/yt-dlp/yt-dlp/issues/10079)) by [bashonly](https://github.com/bashonly)

#### Misc. changes
- **build**
    - [Bump Pyinstaller to `>=6.7.0` for all builds](https://github.com/yt-dlp/yt-dlp/commit/5fdd13006a1c5d78642c8d3c4c7df0448273c2ae) ([#10069](https://github.com/yt-dlp/yt-dlp/issues/10069)) by [bashonly](https://github.com/bashonly), [seproDev](https://github.com/seproDev)
    - [Cache dependencies for `macos` job](https://github.com/yt-dlp/yt-dlp/commit/46c1b7cfec1d0e6155083ca7e6948674c64ecb97) ([#10088](https://github.com/yt-dlp/yt-dlp/issues/10088)) by [bashonly](https://github.com/bashonly)
    - [Use `macos-12` image for `yt-dlp_macos`](https://github.com/yt-dlp/yt-dlp/commit/03334d639d5282cd4107edb32c623ba400262fc4) ([#10063](https://github.com/yt-dlp/yt-dlp/issues/10063)) by [bashonly](https://github.com/bashonly)
- **cleanup**
    - [Add more ruff rules](https://github.com/yt-dlp/yt-dlp/commit/add96eb9f84cfffe85682bf2fb85135746994ee8) ([#10149](https://github.com/yt-dlp/yt-dlp/issues/10149)) by [seproDev](https://github.com/seproDev)
    - [Bump ruff to 0.5.x](https://github.com/yt-dlp/yt-dlp/commit/7814c50948a2b9a4c746441ecbc509ae563d5d1f) ([#10282](https://github.com/yt-dlp/yt-dlp/issues/10282)) by [seproDev](https://github.com/seproDev)
    - Miscellaneous: [6aaf96a](https://github.com/yt-dlp/yt-dlp/commit/6aaf96a3d6e7d0d426e97e11a2fcf52fda00e733) by [bashonly](https://github.com/bashonly), [c-basalt](https://github.com/c-basalt), [jucor](https://github.com/jucor), [seproDev](https://github.com/seproDev)
- **test**: download: [Raise on network errors](https://github.com/yt-dlp/yt-dlp/commit/54a63e80af82791d2f0985bd0176bb182963fd5f) ([#10283](https://github.com/yt-dlp/yt-dlp/issues/10283)) by [bashonly](https://github.com/bashonly), [seproDev](https://github.com/seproDev)

### 2024.05.27

#### Extractor changes
- [Fix parsing of base URL in SMIL manifest](https://github.com/yt-dlp/yt-dlp/commit/26603d0b34898818992bee4598e0607c07059511) ([#9225](https://github.com/yt-dlp/yt-dlp/issues/9225)) by [seproDev](https://github.com/seproDev)
- **peertube**: [Support livestreams](https://github.com/yt-dlp/yt-dlp/commit/12b248ce60be1aa1362edd839d915bba70dbee4b) ([#10044](https://github.com/yt-dlp/yt-dlp/issues/10044)) by [bashonly](https://github.com/bashonly), [trueauracoral](https://github.com/trueauracoral)
- **piksel**: [Update domain](https://github.com/yt-dlp/yt-dlp/commit/ae2194e1dd4a99d32eb3cab7c48a0ff03101ef3b) ([#9223](https://github.com/yt-dlp/yt-dlp/issues/9223)) by [seproDev](https://github.com/seproDev)
- **tiktok**: user: [Fix extraction loop](https://github.com/yt-dlp/yt-dlp/commit/c53c2e40fde8f2e15c7c62f8ca1a5d9e90ddc079) ([#10035](https://github.com/yt-dlp/yt-dlp/issues/10035)) by [bashonly](https://github.com/bashonly)

#### Misc. changes
- **cleanup**: Miscellaneous: [5e3e19c](https://github.com/yt-dlp/yt-dlp/commit/5e3e19c93c52830da98d9d1ed84ea7a559efefbd) by [bashonly](https://github.com/bashonly)

### 2024.05.26

#### Core changes
- [Better warning when requested subs format not found](https://github.com/yt-dlp/yt-dlp/commit/7e4259dff0b681a3f0e8a930799ce0394328c86e) ([#9873](https://github.com/yt-dlp/yt-dlp/issues/9873)) by [DaPotato69](https://github.com/DaPotato69)
- [Merged with youtube-dl a08f2b7](https://github.com/yt-dlp/yt-dlp/commit/a4da9db87b6486b270c15dfa07ab5bfedc83f6bd) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
- [Warn if lack of ffmpeg alters format selection](https://github.com/yt-dlp/yt-dlp/commit/96da9525043f78aca4544d01761b13b2140e9ae6) ([#9805](https://github.com/yt-dlp/yt-dlp/issues/9805)) by [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)
- **cookies**
    - [Add `--cookies-from-browser` support for Whale](https://github.com/yt-dlp/yt-dlp/commit/dd9ad97b1fbdd36c086b8ba82328a4d954f78f8e) ([#9649](https://github.com/yt-dlp/yt-dlp/issues/9649)) by [roeniss](https://github.com/roeniss)
    - [Get chrome session cookies with `--cookies-from-browser`](https://github.com/yt-dlp/yt-dlp/commit/f1f158976e38d38a260762accafe7bbe6d451151) ([#9747](https://github.com/yt-dlp/yt-dlp/issues/9747)) by [StefanLobbenmeier](https://github.com/StefanLobbenmeier)
- **windows**: [Improve shell quoting and tests](https://github.com/yt-dlp/yt-dlp/commit/64766459e37451b665c1464073c28361fbcf1c25) ([#9802](https://github.com/yt-dlp/yt-dlp/issues/9802)) by [Grub4K](https://github.com/Grub4K) (With fixes in [7e26bd5](https://github.com/yt-dlp/yt-dlp/commit/7e26bd53f9c5893518fde81dfd0079ec08dd841e))

#### Extractor changes
- [Add POST data hash to `--write-pages` filenames](https://github.com/yt-dlp/yt-dlp/commit/61b17437dc14a1c7e90ff48a6198df77828c6df4) ([#9879](https://github.com/yt-dlp/yt-dlp/issues/9879)) by [minamotorin](https://github.com/minamotorin) (With fixes in [c999bac](https://github.com/yt-dlp/yt-dlp/commit/c999bac02c5a4f755b2a82488a975e91c988ffd8) by [bashonly](https://github.com/bashonly))
- [Make `_search_nextjs_data` non fatal](https://github.com/yt-dlp/yt-dlp/commit/3ee1194288981c4f2c4abd8315326de0c424d2ce) ([#8937](https://github.com/yt-dlp/yt-dlp/issues/8937)) by [Grub4K](https://github.com/Grub4K)
- **afreecatv**: live: [Add `cdn` extractor-arg](https://github.com/yt-dlp/yt-dlp/commit/315b3544296bb83012e20ee3af9d3cbf5600dd1c) ([#9666](https://github.com/yt-dlp/yt-dlp/issues/9666)) by [bashonly](https://github.com/bashonly)
- **alura**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/fc2879ecb05aaad36869609d154e4321362c1f63) ([#9658](https://github.com/yt-dlp/yt-dlp/issues/9658)) by [hugohaa](https://github.com/hugohaa)
- **artetv**: [Label forced subtitles](https://github.com/yt-dlp/yt-dlp/commit/7b5674949fd03a33b47b67b31d56a5adf1c48c91) ([#9945](https://github.com/yt-dlp/yt-dlp/issues/9945)) by [vtexier](https://github.com/vtexier)
- **bbc**: [Fix and extend extraction](https://github.com/yt-dlp/yt-dlp/commit/7975ddf245d22af034d5b983eeb1c5ec6c2ce053) ([#9705](https://github.com/yt-dlp/yt-dlp/issues/9705)) by [dirkf](https://github.com/dirkf), [kylegustavo](https://github.com/kylegustavo), [pukkandan](https://github.com/pukkandan)
- **bilibili**: [Fix `--geo-verification-proxy` support](https://github.com/yt-dlp/yt-dlp/commit/2338827072dacab0f15348b70aec8685feefc8d1) ([#9817](https://github.com/yt-dlp/yt-dlp/issues/9817)) by [fireattack](https://github.com/fireattack)
- **bilibilispacevideo**
    - [Better error message](https://github.com/yt-dlp/yt-dlp/commit/06d52c87314e0bbc16c43c405090843885577b88) ([#9839](https://github.com/yt-dlp/yt-dlp/issues/9839)) by [fireattack](https://github.com/fireattack)
    - [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/4cc99d7b6cce8b39506ead01407445d576b63ee4) ([#9905](https://github.com/yt-dlp/yt-dlp/issues/9905)) by [c-basalt](https://github.com/c-basalt)
- **boosty**: [Add cookies support](https://github.com/yt-dlp/yt-dlp/commit/145dc6f6563e80d2da1b3e9aea2ffa795b71622c) ([#9522](https://github.com/yt-dlp/yt-dlp/issues/9522)) by [RasmusAntons](https://github.com/RasmusAntons)
- **brilliantpala**: [Fix login](https://github.com/yt-dlp/yt-dlp/commit/eead3bbc01f6529862bdad1f0b2adeabda4f006e) ([#9788](https://github.com/yt-dlp/yt-dlp/issues/9788)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **canalalpha**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/00a9f2e1f7fa69499221f2e8dd73a08efeef79bc) ([#9675](https://github.com/yt-dlp/yt-dlp/issues/9675)) by [kclauhk](https://github.com/kclauhk)
- **cbc.ca**: player: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/c8bf48f3a8fa29587e7c73ef5a7710385a5ea725) ([#9866](https://github.com/yt-dlp/yt-dlp/issues/9866)) by [carusocr](https://github.com/carusocr)
- **cda**: [Fix age-gated web extraction](https://github.com/yt-dlp/yt-dlp/commit/6d8a53d870ff6795f509085bfbf3981417999038) ([#9939](https://github.com/yt-dlp/yt-dlp/issues/9939)) by [dirkf](https://github.com/dirkf), [emqi](https://github.com/emqi), [Podiumnoche](https://github.com/Podiumnoche), [Szpachlarz](https://github.com/Szpachlarz)
- **commonmistakes**: [Raise error on blob URLs](https://github.com/yt-dlp/yt-dlp/commit/98d71d8c5e5dab08b561ee6f137e968d2a004262) ([#9897](https://github.com/yt-dlp/yt-dlp/issues/9897)) by [seproDev](https://github.com/seproDev)
- **crunchyroll**
    - [Always make metadata available](https://github.com/yt-dlp/yt-dlp/commit/cb2fb4a643949322adba561ca73bcba3221ec0c5) ([#9772](https://github.com/yt-dlp/yt-dlp/issues/9772)) by [bashonly](https://github.com/bashonly)
    - [Fix auth and remove cookies support](https://github.com/yt-dlp/yt-dlp/commit/ff38a011d57b763f3a69bebd25a5dc9044a717ce) ([#9749](https://github.com/yt-dlp/yt-dlp/issues/9749)) by [bashonly](https://github.com/bashonly)
    - [Fix stream extraction](https://github.com/yt-dlp/yt-dlp/commit/f2816634e3be88fe158b342ee33918de3c272a54) ([#10005](https://github.com/yt-dlp/yt-dlp/issues/10005)) by [bashonly](https://github.com/bashonly)
    - [Support browser impersonation](https://github.com/yt-dlp/yt-dlp/commit/5904853ae5788509fdc4892cb7ecdfa9ae7f78e6) ([#9857](https://github.com/yt-dlp/yt-dlp/issues/9857)) by [bashonly](https://github.com/bashonly)
- **dangalplay**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/0d067e77c3f5527946fb0c22ee1c7011994cba40) ([#10021](https://github.com/yt-dlp/yt-dlp/issues/10021)) by [bashonly](https://github.com/bashonly)
- **discoveryplus**: [Fix dmax.de and related extractors](https://github.com/yt-dlp/yt-dlp/commit/90d2da311bbb5dc06f385ee428c7e4590936e995) ([#10020](https://github.com/yt-dlp/yt-dlp/issues/10020)) by [bashonly](https://github.com/bashonly)
- **eplus**: [Handle URLs without videos](https://github.com/yt-dlp/yt-dlp/commit/351dc0bc334c4e1b5f00c152818c3ec0ed71f788) ([#9855](https://github.com/yt-dlp/yt-dlp/issues/9855)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **europarlwebstream**: [Support new URL format](https://github.com/yt-dlp/yt-dlp/commit/800a43983e5fb719526ce4cb3956216085c63268) ([#9647](https://github.com/yt-dlp/yt-dlp/issues/9647)) by [seproDev](https://github.com/seproDev), [voidful](https://github.com/voidful)
- **facebook**: [Fix DASH formats extraction](https://github.com/yt-dlp/yt-dlp/commit/e3b42d8b1b8bcfff7ba146c19fc3f6f6ba843cea) ([#9734](https://github.com/yt-dlp/yt-dlp/issues/9734)) by [bashonly](https://github.com/bashonly)
- **godresource**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/65e709d23530959075816e966c42179ad46e8e3b) ([#9629](https://github.com/yt-dlp/yt-dlp/issues/9629)) by [HobbyistDev](https://github.com/HobbyistDev)
- **googledrive**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/85ec2a337ac325cf6427cbafd56f0a034c1a5218) ([#9908](https://github.com/yt-dlp/yt-dlp/issues/9908)) by [WyohKnott](https://github.com/WyohKnott)
- **hearthisat**: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/5bbfdb7c999b22f1aeca0c3489c167d6eb73013b) ([#9949](https://github.com/yt-dlp/yt-dlp/issues/9949)) by [bohwaz](https://github.com/bohwaz), [seproDev](https://github.com/seproDev)
- **hytale**: [Use `CloudflareStreamIE` explicitly](https://github.com/yt-dlp/yt-dlp/commit/31b417e1d1ccc67d5c027bf8878f483dc34cb118) ([#9672](https://github.com/yt-dlp/yt-dlp/issues/9672)) by [llamasblade](https://github.com/llamasblade)
- **instagram**: [Support `/reels/` URLs](https://github.com/yt-dlp/yt-dlp/commit/06cb0638392b607b47d3c2ac48eb2ebecb0f060d) ([#9539](https://github.com/yt-dlp/yt-dlp/issues/9539)) by [amir16yp](https://github.com/amir16yp)
- **jiocinema**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/1463945ae5fb05986a0bd1aa02e41d1a08d93a02) ([#10026](https://github.com/yt-dlp/yt-dlp/issues/10026)) by [bashonly](https://github.com/bashonly)
- **jiosaavn**: [Extract via API and fix playlists](https://github.com/yt-dlp/yt-dlp/commit/0c21c53885cf03f4040467ae8c44d7ff51016116) ([#9656](https://github.com/yt-dlp/yt-dlp/issues/9656)) by [bashonly](https://github.com/bashonly)
- **lci**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/5a2eebc76770fca91ffabeff658d560f716fec80) ([#10025](https://github.com/yt-dlp/yt-dlp/issues/10025)) by [ocococococ](https://github.com/ocococococ)
- **mixch**: [Extract comments](https://github.com/yt-dlp/yt-dlp/commit/b38018b781b062d5169d104ab430489aef8e7f1e) ([#9860](https://github.com/yt-dlp/yt-dlp/issues/9860)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **moviepilot**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/296df0da1d38a44d34c99b60a18066c301774537) ([#9366](https://github.com/yt-dlp/yt-dlp/issues/9366)) by [panatexxa](https://github.com/panatexxa)
- **netease**: program: [Improve `--no-playlist` message](https://github.com/yt-dlp/yt-dlp/commit/73f12119b52d98281804b0c072b2ed6aa841ec88) ([#9488](https://github.com/yt-dlp/yt-dlp/issues/9488)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **nfb**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/0a1a8e3005f66c44bf67633dccd4df19c3fccd1a) ([#9650](https://github.com/yt-dlp/yt-dlp/issues/9650)) by [rrgomes](https://github.com/rrgomes)
- **ntslive**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/be7db1a5a8c483726c511c30ea4689cbb8b27962) ([#9641](https://github.com/yt-dlp/yt-dlp/issues/9641)) by [lostfictions](https://github.com/lostfictions)
- **orf**: on: [Improve extraction](https://github.com/yt-dlp/yt-dlp/commit/0dd53faeca2ba0ce138e4092d07b5f2dbf2422f9) ([#9677](https://github.com/yt-dlp/yt-dlp/issues/9677)) by [TuxCoder](https://github.com/TuxCoder)
- **orftvthek**: [Remove extractor](https://github.com/yt-dlp/yt-dlp/commit/3779f2a307ba3ef1d28e107cdd71b221dfb4eb36) ([#10011](https://github.com/yt-dlp/yt-dlp/issues/10011)) by [seproDev](https://github.com/seproDev)
- **patreon**
    - [Extract multiple embeds](https://github.com/yt-dlp/yt-dlp/commit/036e0d92c6052465673d459678322ea03e61483d) ([#9850](https://github.com/yt-dlp/yt-dlp/issues/9850)) by [bashonly](https://github.com/bashonly)
    - [Fix Vimeo embed extraction](https://github.com/yt-dlp/yt-dlp/commit/c9ce57d9bf51541da2381d99bc096a9d0ddf1f27) ([#9712](https://github.com/yt-dlp/yt-dlp/issues/9712)) by [bashonly](https://github.com/bashonly)
- **piapro**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/3ba8de62d61d782256f5c1e9939a0762039657de) ([#9311](https://github.com/yt-dlp/yt-dlp/issues/9311)) by [FinnRG](https://github.com/FinnRG), [seproDev](https://github.com/seproDev)
- **pornhub**: [Fix login by email address](https://github.com/yt-dlp/yt-dlp/commit/518c1afc1592cae3e4eb39dc646b5bc059333112) ([#9914](https://github.com/yt-dlp/yt-dlp/issues/9914)) by [feederbox826](https://github.com/feederbox826)
- **qub**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/6b54cccdcb892bca3e55993480d8b86f1c7e6da6) ([#7019](https://github.com/yt-dlp/yt-dlp/issues/7019)) by [alexhuot1](https://github.com/alexhuot1), [dirkf](https://github.com/dirkf)
- **reddit**: [Fix subtitles extraction](https://github.com/yt-dlp/yt-dlp/commit/82f4f4444e26daf35b7302c406fe2312f78f619e) ([#10006](https://github.com/yt-dlp/yt-dlp/issues/10006)) by [kclauhk](https://github.com/kclauhk)
- **soundcloud**
    - [Add `formats` extractor-arg](https://github.com/yt-dlp/yt-dlp/commit/beaf832c7a9d57833f365ce18f6115b88071b296) ([#10004](https://github.com/yt-dlp/yt-dlp/issues/10004)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
    - [Extract `genres`](https://github.com/yt-dlp/yt-dlp/commit/231c2eacc41b06b65c63edf94c0d04768a5da607) ([#9821](https://github.com/yt-dlp/yt-dlp/issues/9821)) by [bashonly](https://github.com/bashonly)
- **taptap**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/63b569bc5e7d461753637a20ad84a575adee4c0a) ([#9776](https://github.com/yt-dlp/yt-dlp/issues/9776)) by [c-basalt](https://github.com/c-basalt)
- **tele5**: [Overhaul extractor](https://github.com/yt-dlp/yt-dlp/commit/c92e4e625e9e6bbbbf8e3b20c3e7ebe57c16072d) ([#10024](https://github.com/yt-dlp/yt-dlp/issues/10024)) by [bashonly](https://github.com/bashonly)
- **theatercomplextown**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/8056a3026ed6ec6a6d0ed56fdd7ebcd16e928341) ([#9754](https://github.com/yt-dlp/yt-dlp/issues/9754)) by [bashonly](https://github.com/bashonly)
- **tiktok**
    - [Add `device_id` extractor-arg](https://github.com/yt-dlp/yt-dlp/commit/3584b8390bd21c0393a3079eeee71aed56a1c1d8) ([#9951](https://github.com/yt-dlp/yt-dlp/issues/9951)) by [bashonly](https://github.com/bashonly)
    - [Extract all web formats](https://github.com/yt-dlp/yt-dlp/commit/4ccd73fea0f6f4be343e1ec7f22dd03799addcf8) ([#9960](https://github.com/yt-dlp/yt-dlp/issues/9960)) by [bashonly](https://github.com/bashonly)
    - [Extract via mobile API only if extractor-arg is passed](https://github.com/yt-dlp/yt-dlp/commit/41ba4a808b597a3afed78c89675a30deb6844450) ([#9938](https://github.com/yt-dlp/yt-dlp/issues/9938)) by [bashonly](https://github.com/bashonly)
    - [Fix subtitles extraction](https://github.com/yt-dlp/yt-dlp/commit/eef1e9f44ff14c5e65b759bb1eafa3946cdaf719) ([#9961](https://github.com/yt-dlp/yt-dlp/issues/9961)) by [bashonly](https://github.com/bashonly)
    - collection: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/119d41f27061d220d276a2d38cfc8d873437452a) ([#9986](https://github.com/yt-dlp/yt-dlp/issues/9986)) by [bashonly](https://github.com/bashonly), [imanoreotwe](https://github.com/imanoreotwe)
    - user: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/347f13dd9bccc2b4db3ea25689410d45d8370ed4) ([#9661](https://github.com/yt-dlp/yt-dlp/issues/9661)) by [bashonly](https://github.com/bashonly)
- **tv5monde**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/6db96268c521e945d42649607db1574f5d92e082) ([#9143](https://github.com/yt-dlp/yt-dlp/issues/9143)) by [alard](https://github.com/alard), [seproDev](https://github.com/seproDev)
- **twitter**
    - [Fix auth for x.com migration](https://github.com/yt-dlp/yt-dlp/commit/3e35aa32c74bc108375be8c8b6b3bfc90dfff1b4) ([#9952](https://github.com/yt-dlp/yt-dlp/issues/9952)) by [bashonly](https://github.com/bashonly)
    - [Support x.com URLs](https://github.com/yt-dlp/yt-dlp/commit/4813173e4544f125d6f2afc31e600727d761b8dd) ([#9926](https://github.com/yt-dlp/yt-dlp/issues/9926)) by [bashonly](https://github.com/bashonly)
- **vk**: [Improve format extraction](https://github.com/yt-dlp/yt-dlp/commit/df5c9e733aaba703cf285c0372b6d61629330c82) ([#9885](https://github.com/yt-dlp/yt-dlp/issues/9885)) by [seproDev](https://github.com/seproDev)
- **wrestleuniverse**: [Avoid partial stream formats](https://github.com/yt-dlp/yt-dlp/commit/c4853655cb9a793129280806af643de43c48f4d5) ([#9800](https://github.com/yt-dlp/yt-dlp/issues/9800)) by [bashonly](https://github.com/bashonly)
- **xiaohongshu**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/a2e9031605d87c469be9ce98dbbdf4960b727338) ([#9646](https://github.com/yt-dlp/yt-dlp/issues/9646)) by [HobbyistDev](https://github.com/HobbyistDev)
- **xvideos**: quickies: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/b207d26f83fb8ab0ce56df74dff43ff583a3264f) ([#9834](https://github.com/yt-dlp/yt-dlp/issues/9834)) by [JakeFinley96](https://github.com/JakeFinley96)
- **youporn**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/351368cb9a6731b886a58f5a10fd6b302bbe47be) ([#8827](https://github.com/yt-dlp/yt-dlp/issues/8827)) by [The-MAGI](https://github.com/The-MAGI)
- **youtube**
    - [Add `mediaconnect` client](https://github.com/yt-dlp/yt-dlp/commit/cf212d0a331aba05c32117573f760cdf3af8c62f) ([#9546](https://github.com/yt-dlp/yt-dlp/issues/9546)) by [clienthax](https://github.com/clienthax)
    - [Extract upload timestamp if available](https://github.com/yt-dlp/yt-dlp/commit/96a134dea6397a5f2131947c427aac52c8b4e677) ([#9856](https://github.com/yt-dlp/yt-dlp/issues/9856)) by [coletdjnz](https://github.com/coletdjnz)
    - [Fix comments extraction](https://github.com/yt-dlp/yt-dlp/commit/8e15177b4113c355989881e4e030f695a9b59c3a) ([#9775](https://github.com/yt-dlp/yt-dlp/issues/9775)) by [bbilly1](https://github.com/bbilly1), [jakeogh](https://github.com/jakeogh), [minamotorin](https://github.com/minamotorin), [shoxie007](https://github.com/shoxie007)
    - [Remove `android` from default clients](https://github.com/yt-dlp/yt-dlp/commit/12d8ea8246fa901de302ff5cc748caddadc82f41) ([#9553](https://github.com/yt-dlp/yt-dlp/issues/9553)) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz)
- **zenyandex**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/c4b87dd885ee5391e5f481e7c8bd550a7c543623) ([#9813](https://github.com/yt-dlp/yt-dlp/issues/9813)) by [src-tinkerer](https://github.com/src-tinkerer)

#### Networking changes
- [Add `extensions` attribute to `Response`](https://github.com/yt-dlp/yt-dlp/commit/bec9a59e8ec82c18e3bf9268eaa436793dd52e35) ([#9756](https://github.com/yt-dlp/yt-dlp/issues/9756)) by [bashonly](https://github.com/bashonly)
- **Request Handler**
    - requests
        - [Patch support for `requests` 2.32.2+](https://github.com/yt-dlp/yt-dlp/commit/3f7999533ebe41c2a579d91b4e4cb211cfcd3bc0) ([#9992](https://github.com/yt-dlp/yt-dlp/issues/9992)) by [Grub4K](https://github.com/Grub4K)
        - [Update to `requests` 2.32.0](https://github.com/yt-dlp/yt-dlp/commit/c36513f1be2ef3d3cec864accbffda1afaa06ffd) ([#9980](https://github.com/yt-dlp/yt-dlp/issues/9980)) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- [Add `hatch`, `ruff`, `pre-commit` and improve dev docs](https://github.com/yt-dlp/yt-dlp/commit/e897bd8292a41999cf51dba91b390db5643c72db) ([#7409](https://github.com/yt-dlp/yt-dlp/issues/7409)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K), [seproDev](https://github.com/seproDev)
- **build**
    - [Migrate `linux_exe` to static musl builds](https://github.com/yt-dlp/yt-dlp/commit/ac817bc83efd939dca3e40c4b527d0ccfc77172b) ([#9811](https://github.com/yt-dlp/yt-dlp/issues/9811)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
    - [Normalize `curl_cffi` group to `curl-cffi`](https://github.com/yt-dlp/yt-dlp/commit/02483bea1c4dbe1bace8ca4d19700104fbb8a00f) ([#9698](https://github.com/yt-dlp/yt-dlp/issues/9698)) by [bashonly](https://github.com/bashonly) (With fixes in [89f535e](https://github.com/yt-dlp/yt-dlp/commit/89f535e2656964b4061c25a7739d4d6ba0a30568))
    - [Run `macos_legacy` job on `macos-12`](https://github.com/yt-dlp/yt-dlp/commit/1a366403d9c26b992faa77e00f4d02ead57559e3) ([#9804](https://github.com/yt-dlp/yt-dlp/issues/9804)) by [bashonly](https://github.com/bashonly)
    - [`macos` job requires `setuptools<70`](https://github.com/yt-dlp/yt-dlp/commit/78c57cc0e0998b8ed90e4306f410aa4be4115cd7) ([#9993](https://github.com/yt-dlp/yt-dlp/issues/9993)) by [bashonly](https://github.com/bashonly)
- **cleanup**
    - [Remove questionable extractors](https://github.com/yt-dlp/yt-dlp/commit/01395a34345d1c6ba1b73ca92f94dd200dc45341) ([#9911](https://github.com/yt-dlp/yt-dlp/issues/9911)) by [seproDev](https://github.com/seproDev)
    - Miscellaneous: [5c019f6](https://github.com/yt-dlp/yt-dlp/commit/5c019f6328ad40d66561eac3c4de0b3cd070d0f6), [ae2af11](https://github.com/yt-dlp/yt-dlp/commit/ae2af1104f80caf2f47544763a33db2c17a3e1de) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K), [seproDev](https://github.com/seproDev)
- **test**
    - [Add HTTP proxy tests](https://github.com/yt-dlp/yt-dlp/commit/3c7a287e281d9f9a353dce8902ff78a84c24a040) ([#9578](https://github.com/yt-dlp/yt-dlp/issues/9578)) by [coletdjnz](https://github.com/coletdjnz)
    - [Fix connect timeout test](https://github.com/yt-dlp/yt-dlp/commit/53b4d44f55cca66ac33dab092ef2a30b1164b684) ([#9906](https://github.com/yt-dlp/yt-dlp/issues/9906)) by [coletdjnz](https://github.com/coletdjnz)

### 2024.04.09

#### Important changes
- Security: [[CVE-2024-22423](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-22423)] [Prevent RCE when using `--exec` with `%q` on Windows](https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-hjq6-52gw-2g7p)
    - The shell escape function now properly escapes `%`, `\` and `\n`.
    - `utils.Popen` has been patched accordingly.

#### Core changes
- [Add new option `--progress-delta`](https://github.com/yt-dlp/yt-dlp/commit/9590cc6b4768e190183d7d071a6c78170889116a) ([#9082](https://github.com/yt-dlp/yt-dlp/issues/9082)) by [Grub4K](https://github.com/Grub4K)
- [Add new options `--impersonate` and `--list-impersonate-targets`](https://github.com/yt-dlp/yt-dlp/commit/0b81d4d252bd065ccd352722987ea34fe17f9244) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz), [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan)
- [Add option `--no-break-on-existing`](https://github.com/yt-dlp/yt-dlp/commit/16be117729150b2784f3b17755c886cb0cf73374) ([#9610](https://github.com/yt-dlp/yt-dlp/issues/9610)) by [bashonly](https://github.com/bashonly)
- [Fix `filesize_approx` calculation](https://github.com/yt-dlp/yt-dlp/commit/86e3b82261e8ebc6c6707c09544c9dfb8907c0fd) ([#9560](https://github.com/yt-dlp/yt-dlp/issues/9560)) by [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)
- [Infer `acodec` for single-codec containers](https://github.com/yt-dlp/yt-dlp/commit/86a972033e05fea80e5fe7f2aff6723dbe2f3952) by [pukkandan](https://github.com/pukkandan)
- [Prevent RCE when using `--exec` with `%q` (CVE-2024-22423)](https://github.com/yt-dlp/yt-dlp/commit/ff07792676f404ffff6ee61b5638c9dc1a33a37a) by [Grub4K](https://github.com/Grub4K)
- **cookies**: [Add `--cookies-from-browser` support for Firefox Flatpak](https://github.com/yt-dlp/yt-dlp/commit/2ab2651a4a7be18939e2b4cb21be79fe477c797a) ([#9619](https://github.com/yt-dlp/yt-dlp/issues/9619)) by [un-def](https://github.com/un-def)
- **utils**
    - `traverse_obj`
        - [Allow unbranching using `all` and `any`](https://github.com/yt-dlp/yt-dlp/commit/3699eeb67cad333272b14a42dd3843d93fda1a2e) ([#9571](https://github.com/yt-dlp/yt-dlp/issues/9571)) by [Grub4K](https://github.com/Grub4K)
        - [Convenience improvements](https://github.com/yt-dlp/yt-dlp/commit/32abfb00bdbd119ca675fdc6d1719331f0a2741a) ([#9577](https://github.com/yt-dlp/yt-dlp/issues/9577)) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- [Add extractor impersonate API](https://github.com/yt-dlp/yt-dlp/commit/50c29352312f5662acf9a64b0012766f5c40af61) ([#9474](https://github.com/yt-dlp/yt-dlp/issues/9474)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan)
- **afreecatv**
    - [Overhaul extractor](https://github.com/yt-dlp/yt-dlp/commit/9415f1a5ef88482ebafe3083e8bcb778ac512df7) ([#9566](https://github.com/yt-dlp/yt-dlp/issues/9566)) by [bashonly](https://github.com/bashonly), [Tomoka1](https://github.com/Tomoka1)
    - live: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/9073ae6458f4c6a832aa832c67174c61852869be) ([#9348](https://github.com/yt-dlp/yt-dlp/issues/9348)) by [hui1601](https://github.com/hui1601)
- **asobistage**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/0284f1fee202302a78888420f933deae19d9f4e1) ([#8735](https://github.com/yt-dlp/yt-dlp/issues/8735)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **box**: [Support URLs without file IDs](https://github.com/yt-dlp/yt-dlp/commit/07f5b2f7570fd9ac85aed17f4c0118f6eac77beb) ([#9504](https://github.com/yt-dlp/yt-dlp/issues/9504)) by [shreyasminocha](https://github.com/shreyasminocha)
- **cbc.ca**: player: [Support new URL format](https://github.com/yt-dlp/yt-dlp/commit/b49d5ffc53a72d8245ba319ff07bdc5b8c6a4f0c) ([#9561](https://github.com/yt-dlp/yt-dlp/issues/9561)) by [trainman261](https://github.com/trainman261)
- **crunchyroll**
    - [Extract `vo_adaptive_hls` formats by default](https://github.com/yt-dlp/yt-dlp/commit/be77923ffe842f667971019460f6005f3cad01eb) ([#9447](https://github.com/yt-dlp/yt-dlp/issues/9447)) by [bashonly](https://github.com/bashonly)
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/954e57e405f79188450eb30103a9308732cd318f) ([#9615](https://github.com/yt-dlp/yt-dlp/issues/9615)) by [bytedream](https://github.com/bytedream)
- **dropbox**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/a48cc86d6f6b20427553620c2ddb990ede6a4b41) ([#9627](https://github.com/yt-dlp/yt-dlp/issues/9627)) by [bashonly](https://github.com/bashonly)
- **fathom**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/bc2b8c0596fd6b75af24822c4f0f1da6783d71f7) ([#9495](https://github.com/yt-dlp/yt-dlp/issues/9495)) by [src-tinkerer](https://github.com/src-tinkerer)
- **gofile**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/0da66980d3193cad3dae0120cddddbfcabddf7a1) ([#9446](https://github.com/yt-dlp/yt-dlp/issues/9446)) by [jazz1611](https://github.com/jazz1611)
- **imgur**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/86d2f4d24849af0d1f3af7c0e2ac43bf8a058f74) ([#9471](https://github.com/yt-dlp/yt-dlp/issues/9471)) by [trwstin](https://github.com/trwstin)
- **jiosaavn**
    - [Extract artists](https://github.com/yt-dlp/yt-dlp/commit/0ae16ceb1846cc4e609b70ce7c5d8e7458efceb2) ([#9612](https://github.com/yt-dlp/yt-dlp/issues/9612)) by [bashonly](https://github.com/bashonly)
    - [Fix format extensions](https://github.com/yt-dlp/yt-dlp/commit/443e206ec41e64ca2aef61d8ef91640fb69b3113) ([#9609](https://github.com/yt-dlp/yt-dlp/issues/9609)) by [bashonly](https://github.com/bashonly)
    - [Support playlists](https://github.com/yt-dlp/yt-dlp/commit/2e94602f241f6e41bdc48576c61089435529339b) ([#9622](https://github.com/yt-dlp/yt-dlp/issues/9622)) by [bashonly](https://github.com/bashonly)
- **joqrag**: [Fix live status detection](https://github.com/yt-dlp/yt-dlp/commit/f2fd449b46c4058222e1744f7a35caa20b2d003d) ([#9624](https://github.com/yt-dlp/yt-dlp/issues/9624)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **kick**: [Support browser impersonation](https://github.com/yt-dlp/yt-dlp/commit/c8a61a910096c77ce08dad5e1b2fbda5eb964156) ([#9611](https://github.com/yt-dlp/yt-dlp/issues/9611)) by [bashonly](https://github.com/bashonly)
- **loom**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/f859ed3ba1e8b129ae6a467592c65687e73fbca1) ([#8686](https://github.com/yt-dlp/yt-dlp/issues/8686)) by [bashonly](https://github.com/bashonly), [hruzgar](https://github.com/hruzgar)
- **medici**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/4cd9e251b9abada107b10830de997bf4d79ca369) ([#9518](https://github.com/yt-dlp/yt-dlp/issues/9518)) by [Offert4324](https://github.com/Offert4324)
- **mixch**
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/4c3b7a0769706f7f0ea24adf1f219d5ae82d2b07) ([#9608](https://github.com/yt-dlp/yt-dlp/issues/9608)) by [bashonly](https://github.com/bashonly), [nipotan](https://github.com/nipotan)
    - archive: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/c59de48e2bb4c681b03b93b584a05f52609ce4a0) ([#8761](https://github.com/yt-dlp/yt-dlp/issues/8761)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **nhk**: [Fix NHK World extractors](https://github.com/yt-dlp/yt-dlp/commit/4af9d5c2f6aa81403ae2a8a5ae3cc824730f0b86) ([#9623](https://github.com/yt-dlp/yt-dlp/issues/9623)) by [bashonly](https://github.com/bashonly)
- **patreon**: [Do not extract dead embed URLs](https://github.com/yt-dlp/yt-dlp/commit/36b240f9a72af57eb2c9d927ebb7fd1c917ebf18) ([#9613](https://github.com/yt-dlp/yt-dlp/issues/9613)) by [johnvictorfs](https://github.com/johnvictorfs)
- **radio1be**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/36baaa10e06715ccba06b78885b2042c4844c826) ([#9122](https://github.com/yt-dlp/yt-dlp/issues/9122)) by [HobbyistDev](https://github.com/HobbyistDev)
- **sharepoint**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/ff349ff94aae0b2b148bd3670f7c91d39c2f1d8e) ([#6531](https://github.com/yt-dlp/yt-dlp/issues/6531)) by [bashonly](https://github.com/bashonly), [C0D3D3V](https://github.com/C0D3D3V)
- **sonylivseries**: [Fix season extraction](https://github.com/yt-dlp/yt-dlp/commit/f2868b26e917354203f82a370ad2396646edb813) ([#9423](https://github.com/yt-dlp/yt-dlp/issues/9423)) by [bashonly](https://github.com/bashonly)
- **soundcloud**
    - [Adjust format sorting](https://github.com/yt-dlp/yt-dlp/commit/a2d0840739cddd585d24e0ce4796394fc8a4fa2e) ([#9584](https://github.com/yt-dlp/yt-dlp/issues/9584)) by [bashonly](https://github.com/bashonly)
    - [Support cookies](https://github.com/yt-dlp/yt-dlp/commit/97362712a1f2b04e735bdf54f749ad99165a62fe) ([#9586](https://github.com/yt-dlp/yt-dlp/issues/9586)) by [bashonly](https://github.com/bashonly)
    - [Support retries for API rate-limit](https://github.com/yt-dlp/yt-dlp/commit/246571ae1d867df8bf31a056bdf3bbbfd398366a) ([#9585](https://github.com/yt-dlp/yt-dlp/issues/9585)) by [bashonly](https://github.com/bashonly)
- **thisoldhouse**: [Support Brightcove embeds](https://github.com/yt-dlp/yt-dlp/commit/0df63cce69026d2f4c0cbb4dd36163e83eac93dc) ([#9576](https://github.com/yt-dlp/yt-dlp/issues/9576)) by [bashonly](https://github.com/bashonly)
- **tiktok**
    - [Fix API extraction](https://github.com/yt-dlp/yt-dlp/commit/cb61e20c266facabb7a30f9ce53bd79dfc158475) ([#9548](https://github.com/yt-dlp/yt-dlp/issues/9548)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
    - [Prefer non-bytevc2 formats](https://github.com/yt-dlp/yt-dlp/commit/63f685f341f35f6f02b0368d1ba53bdb5b520410) ([#9575](https://github.com/yt-dlp/yt-dlp/issues/9575)) by [bashonly](https://github.com/bashonly)
    - [Restore `carrier_region` API parameter](https://github.com/yt-dlp/yt-dlp/commit/fc53ec13ff1ee926a3e533a68cfca8acc887b661) ([#9637](https://github.com/yt-dlp/yt-dlp/issues/9637)) by [bashonly](https://github.com/bashonly)
    - [Update API hostname](https://github.com/yt-dlp/yt-dlp/commit/8c05b3ebae23c5b444857549a85b84004c01a536) ([#9444](https://github.com/yt-dlp/yt-dlp/issues/9444)) by [bashonly](https://github.com/bashonly)
- **twitch**: [Extract AV1 and HEVC formats](https://github.com/yt-dlp/yt-dlp/commit/02f93ff51b3ff9436d60c4993562b366eaae8851) ([#9158](https://github.com/yt-dlp/yt-dlp/issues/9158)) by [kasper93](https://github.com/kasper93)
- **vkplay**: [Fix `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/b15b0c1d2106437ec61a5c436c543e8760eac160) ([#9636](https://github.com/yt-dlp/yt-dlp/issues/9636)) by [bashonly](https://github.com/bashonly)
- **xvideos**: [Support new URL format](https://github.com/yt-dlp/yt-dlp/commit/aa7e9ae4f48276bd5d0173966c77db9484f65a0a) ([#9502](https://github.com/yt-dlp/yt-dlp/issues/9502)) by [sta1us](https://github.com/sta1us)
- **youtube**
    - [Calculate more accurate `filesize`](https://github.com/yt-dlp/yt-dlp/commit/a25a424323267e3f6f9f63c0b62df499bd7b8d46) by [pukkandan](https://github.com/pukkandan)
    - [Update `android` params](https://github.com/yt-dlp/yt-dlp/commit/e7b17fce14775bd2448695c8eb7379b8d31d3537) by [pukkandan](https://github.com/pukkandan)
    - search: [Fix params for uncensored results](https://github.com/yt-dlp/yt-dlp/commit/17d248a58781e2588d18a5ebe00c441d10011fcd) ([#9456](https://github.com/yt-dlp/yt-dlp/issues/9456)) by [alb](https://github.com/alb), [pukkandan](https://github.com/pukkandan)

#### Downloader changes
- **ffmpeg**: [Accept output args from info dict](https://github.com/yt-dlp/yt-dlp/commit/9c42b7eef547e826e9fcc7beb6706a2523949d05) ([#9278](https://github.com/yt-dlp/yt-dlp/issues/9278)) by [bashonly](https://github.com/bashonly)

#### Networking changes
- [Respect `SSLKEYLOGFILE` environment variable](https://github.com/yt-dlp/yt-dlp/commit/79a451e5763eda8b10d00684d5d3378f3255ee01) ([#9543](https://github.com/yt-dlp/yt-dlp/issues/9543)) by [luiso1979](https://github.com/luiso1979)
- **Request Handler**
    - curlcffi: [Add support for `curl_cffi`](https://github.com/yt-dlp/yt-dlp/commit/52f5be1f1e0dc45bb397ab950f564721976a39bf) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz), [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan)
    - websockets: [Workaround race condition causing issues on PyPy](https://github.com/yt-dlp/yt-dlp/commit/e5d4f11104ce7ea1717a90eea82c0f7d230ea5d5) ([#9514](https://github.com/yt-dlp/yt-dlp/issues/9514)) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- **build**
    - [Do not include `curl_cffi` in `macos_legacy`](https://github.com/yt-dlp/yt-dlp/commit/b19ae095fdddd43c2a2c67d10fbe0d9a645bb98f) ([#9653](https://github.com/yt-dlp/yt-dlp/issues/9653)) by [bashonly](https://github.com/bashonly)
    - [Optional dependencies cleanup](https://github.com/yt-dlp/yt-dlp/commit/58dd0f8d1eee6bc9fdc57f1923bed772fa3c946d) ([#9550](https://github.com/yt-dlp/yt-dlp/issues/9550)) by [bashonly](https://github.com/bashonly)
    - [Print SHA sums to GHA logs](https://github.com/yt-dlp/yt-dlp/commit/e8032503b9517465b0e86d776fc1e60d8795d673) ([#9582](https://github.com/yt-dlp/yt-dlp/issues/9582)) by [bashonly](https://github.com/bashonly)
    - [Update changelog for tarball and sdist](https://github.com/yt-dlp/yt-dlp/commit/17b96974a334688f76b57d350e07cae8cda46877) ([#9425](https://github.com/yt-dlp/yt-dlp/issues/9425)) by [bashonly](https://github.com/bashonly)
- **cleanup**
    - [Standardize `import datetime as dt`](https://github.com/yt-dlp/yt-dlp/commit/c305a25c1b16bcf7a5ec499c3b786ed1e2c748da) ([#8978](https://github.com/yt-dlp/yt-dlp/issues/8978)) by [pukkandan](https://github.com/pukkandan)
    - ie: [No `from` stdlib imports in extractors](https://github.com/yt-dlp/yt-dlp/commit/e3a3ed8a981d9395c4859b6ef56cd02bc3148db2) by [pukkandan](https://github.com/pukkandan)
    - Miscellaneous: [216f6a3](https://github.com/yt-dlp/yt-dlp/commit/216f6a3cb57824e6a3c859649ce058c199b1b247) by [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan)
- **docs**
    - [Update yt-dlp tagline](https://github.com/yt-dlp/yt-dlp/commit/388c979ac63a8774339fac2516fe1cc852b4276e) ([#9481](https://github.com/yt-dlp/yt-dlp/issues/9481)) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz), [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)
    - [Various manpage fixes](https://github.com/yt-dlp/yt-dlp/commit/df0e138fc02ae2764a44f2f59fc93c756c4d3ee2) by [leoheitmannruiz](https://github.com/leoheitmannruiz)
- **test**
    - [Workaround websocket server hanging](https://github.com/yt-dlp/yt-dlp/commit/f849d77ab54788446b995d256e1ee0894c4fb927) ([#9467](https://github.com/yt-dlp/yt-dlp/issues/9467)) by [coletdjnz](https://github.com/coletdjnz)
    - `traversal`: [Separate traversal tests](https://github.com/yt-dlp/yt-dlp/commit/979ce2e786f2ee3fc783b6dc1ef4188d8805c923) ([#9574](https://github.com/yt-dlp/yt-dlp/issues/9574)) by [Grub4K](https://github.com/Grub4K)

### 2024.03.10

#### Core changes
- [Add `--compat-options 2023`](https://github.com/yt-dlp/yt-dlp/commit/3725b4f0c93ca3943e6300013a9670e4ab757fda) ([#9084](https://github.com/yt-dlp/yt-dlp/issues/9084)) by [Grub4K](https://github.com/Grub4K) (With fixes in [ffff1bc](https://github.com/yt-dlp/yt-dlp/commit/ffff1bc6598fc7a9258e51bc153cab812467f9f9) by [pukkandan](https://github.com/pukkandan))
- [Create `ydl._request_director` when needed](https://github.com/yt-dlp/yt-dlp/commit/069b2aedae2279668b6051627a81fc4fbd9c146a) by [pukkandan](https://github.com/pukkandan) (With fixes in [dbd8b1b](https://github.com/yt-dlp/yt-dlp/commit/dbd8b1bff9afd8f05f982bcd52c20bc173c266ca) by [Grub4k](https://github.com/Grub4k))
- [Don't select storyboard formats as fallback](https://github.com/yt-dlp/yt-dlp/commit/d63eae7e7ffb1f3e733e552b9e5e82355bfba214) by [bashonly](https://github.com/bashonly)
- [Handle `--load-info-json` format selection errors](https://github.com/yt-dlp/yt-dlp/commit/263a4b55ac17a796e8991ca8d2d86a3c349f8a60) ([#9392](https://github.com/yt-dlp/yt-dlp/issues/9392)) by [bashonly](https://github.com/bashonly)
- [Warn user when not launching through shell on Windows](https://github.com/yt-dlp/yt-dlp/commit/6a6cdcd1824a14e3b336332c8f31f65497b8c4b8) ([#9250](https://github.com/yt-dlp/yt-dlp/issues/9250)) by [Grub4K](https://github.com/Grub4K), [seproDev](https://github.com/seproDev)
- **cookies**
    - [Fix `--cookies-from-browser` for `snap` Firefox](https://github.com/yt-dlp/yt-dlp/commit/cbed249aaa053a3f425b9bafc97f8dbd71c44487) ([#9016](https://github.com/yt-dlp/yt-dlp/issues/9016)) by [Grub4K](https://github.com/Grub4K)
    - [Fix `--cookies-from-browser` with macOS Firefox profiles](https://github.com/yt-dlp/yt-dlp/commit/85b33f5c163f60dbd089a6b9bc2ba1366d3ddf93) ([#8909](https://github.com/yt-dlp/yt-dlp/issues/8909)) by [RalphORama](https://github.com/RalphORama)
    - [Improve error message for Windows `--cookies-from-browser chrome` issue](https://github.com/yt-dlp/yt-dlp/commit/2792092afd367e39251ace1fb2819c855ab8919f) ([#9080](https://github.com/yt-dlp/yt-dlp/issues/9080)) by [Grub4K](https://github.com/Grub4K)
- **plugins**: [Handle `PermissionError`](https://github.com/yt-dlp/yt-dlp/commit/9a8afadd172b7cab143f0049959fa64973589d94) ([#9229](https://github.com/yt-dlp/yt-dlp/issues/9229)) by [pukkandan](https://github.com/pukkandan), [syntaxsurge](https://github.com/syntaxsurge)
- **utils**
    - [Improve `repr` of `DateRange`, `match_filter_func`](https://github.com/yt-dlp/yt-dlp/commit/45491a2a30da4d1723cfa9288cb664813bb09afb) by [pukkandan](https://github.com/pukkandan)
    - `traverse_obj`: [Support `xml.etree.ElementTree.Element`](https://github.com/yt-dlp/yt-dlp/commit/ffbd4f2a02fee387ea5e0a267ce32df5259111ac) ([#8911](https://github.com/yt-dlp/yt-dlp/issues/8911)) by [Grub4K](https://github.com/Grub4K)
- **webvtt**: [Don't parse single fragment files](https://github.com/yt-dlp/yt-dlp/commit/f24e44e8cbd88ce338d52f594a19330f64d38b50) ([#9034](https://github.com/yt-dlp/yt-dlp/issues/9034)) by [seproDev](https://github.com/seproDev)

#### Extractor changes
- [Migrate commonly plural fields to lists](https://github.com/yt-dlp/yt-dlp/commit/104a7b5a46dc1805157fb4cc11c05876934d37c1) ([#8917](https://github.com/yt-dlp/yt-dlp/issues/8917)) by [llistochek](https://github.com/llistochek), [pukkandan](https://github.com/pukkandan) (With fixes in [b136e2a](https://github.com/yt-dlp/yt-dlp/commit/b136e2af341f7a88028aea4c5cd50efe2fa9b182) by [bashonly](https://github.com/bashonly))
- [Support multi-period MPD streams](https://github.com/yt-dlp/yt-dlp/commit/4ce57d3b873c2887814cbec03d029533e82f7db5) ([#6654](https://github.com/yt-dlp/yt-dlp/issues/6654)) by [alard](https://github.com/alard), [pukkandan](https://github.com/pukkandan)
- **abematv**
    - [Fix extraction with cache](https://github.com/yt-dlp/yt-dlp/commit/c51316f8a69fbd0080f2720777d42ab438e254a3) ([#8895](https://github.com/yt-dlp/yt-dlp/issues/8895)) by [sefidel](https://github.com/sefidel)
    - [Support login for playlists](https://github.com/yt-dlp/yt-dlp/commit/8226a3818f804478c756cf460baa9bf3a3b062a5) ([#8901](https://github.com/yt-dlp/yt-dlp/issues/8901)) by [sefidel](https://github.com/sefidel)
- **adn**
    - [Add support for German site](https://github.com/yt-dlp/yt-dlp/commit/5eb1458be4767385a9bf1d570ff08e46100cbaa2) ([#8708](https://github.com/yt-dlp/yt-dlp/issues/8708)) by [infanf](https://github.com/infanf)
    - [Improve auth error handling](https://github.com/yt-dlp/yt-dlp/commit/9526b1f179d19f75284eceaa5e0ee381af18cf19) ([#9068](https://github.com/yt-dlp/yt-dlp/issues/9068)) by [infanf](https://github.com/infanf)
- **aenetworks**: [Rating should be optional for AP extraction](https://github.com/yt-dlp/yt-dlp/commit/014cb5774d7afe624b6eb4e07f7be924b9e5e186) ([#9005](https://github.com/yt-dlp/yt-dlp/issues/9005)) by [agibson-fl](https://github.com/agibson-fl)
- **altcensored**: channel: [Fix playlist extraction](https://github.com/yt-dlp/yt-dlp/commit/e28e135d6fd6a430fed3e20dfe1a8c8bbc5f9185) ([#9297](https://github.com/yt-dlp/yt-dlp/issues/9297)) by [marcdumais](https://github.com/marcdumais)
- **amadeustv**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/e641aab7a61df7406df60ebfe0c77bd5186b2b41) ([#8744](https://github.com/yt-dlp/yt-dlp/issues/8744)) by [ArnauvGilotra](https://github.com/ArnauvGilotra)
- **ant1newsgrembed**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/1ed5ee2f045f717e814f84ba461dadc58e712266) ([#9191](https://github.com/yt-dlp/yt-dlp/issues/9191)) by [seproDev](https://github.com/seproDev)
- **archiveorg**: [Fix format URL encoding](https://github.com/yt-dlp/yt-dlp/commit/3894ab9574748188bbacbd925a3971eda6fa2bb0) ([#9279](https://github.com/yt-dlp/yt-dlp/issues/9279)) by [bashonly](https://github.com/bashonly)
- **ard**
    - mediathek
        - [Revert to using old id](https://github.com/yt-dlp/yt-dlp/commit/b6951271ac014761c9c317b9cecd5e8e139cfa7c) ([#8916](https://github.com/yt-dlp/yt-dlp/issues/8916)) by [Grub4K](https://github.com/Grub4K)
        - [Support cookies to verify age](https://github.com/yt-dlp/yt-dlp/commit/c099ec9392b0283dde34b290d1a04158ad8eb882) ([#9037](https://github.com/yt-dlp/yt-dlp/issues/9037)) by [StefanLobbenmeier](https://github.com/StefanLobbenmeier)
- **art19**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/999ea80beb053491089d256104c4188aced3110f) ([#9099](https://github.com/yt-dlp/yt-dlp/issues/9099)) by [seproDev](https://github.com/seproDev)
- **artetv**: [Separate closed captions](https://github.com/yt-dlp/yt-dlp/commit/393b487a4ea391c44e811505ec98531031d7e81e) ([#8231](https://github.com/yt-dlp/yt-dlp/issues/8231)) by [Nicals](https://github.com/Nicals), [seproDev](https://github.com/seproDev)
- **asobichannel**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/12f042740550c06552819374e2251deb7a519bab) ([#8700](https://github.com/yt-dlp/yt-dlp/issues/8700)) by [Snack-X](https://github.com/Snack-X)
- **bigo**: [Fix JSON extraction](https://github.com/yt-dlp/yt-dlp/commit/85a2d07c1f82c2082b568963d1c32ad3fc848f61) ([#8893](https://github.com/yt-dlp/yt-dlp/issues/8893)) by [DmitryScaletta](https://github.com/DmitryScaletta)
- **bilibili**
    - [Add referer header and fix metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/1713c882730a928ac344c099874d2093fc2c8b51) ([#8832](https://github.com/yt-dlp/yt-dlp/issues/8832)) by [SirElderling](https://github.com/SirElderling) (With fixes in [f1570ab](https://github.com/yt-dlp/yt-dlp/commit/f1570ab84d5f49564256c620063d2d3e9ed4acf0) by [TobiX](https://github.com/TobiX))
    - [Support `--no-playlist`](https://github.com/yt-dlp/yt-dlp/commit/e439693f729daf6fb15457baea1bca10ef5da34d) ([#9139](https://github.com/yt-dlp/yt-dlp/issues/9139)) by [c-basalt](https://github.com/c-basalt)
- **bilibilisearch**: [Set cookie to fix extraction](https://github.com/yt-dlp/yt-dlp/commit/ffa017cfc5973b265c92248546fcf5020dc43eaf) ([#9119](https://github.com/yt-dlp/yt-dlp/issues/9119)) by [c-basalt](https://github.com/c-basalt)
- **biliintl**: [Fix and improve subtitles extraction](https://github.com/yt-dlp/yt-dlp/commit/cf6413e840476c15e5b166dc2f7cc2a90a4a9aad) ([#7077](https://github.com/yt-dlp/yt-dlp/issues/7077)) by [dirkf](https://github.com/dirkf), [HobbyistDev](https://github.com/HobbyistDev), [itachi-19](https://github.com/itachi-19), [seproDev](https://github.com/seproDev)
- **boosty**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/540b68298192874c75ad5ee4589bed64d02a7d55) ([#9144](https://github.com/yt-dlp/yt-dlp/issues/9144)) by [un-def](https://github.com/un-def)
- **ccma**: [Extract 1080p DASH formats](https://github.com/yt-dlp/yt-dlp/commit/4253e3b7f483127bd812bdac02466f4a5b47ff34) ([#9130](https://github.com/yt-dlp/yt-dlp/issues/9130)) by [seproDev](https://github.com/seproDev)
- **cctv**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/6ad11fef65474bcf70f3a8556850d93c141e44a2) ([#9325](https://github.com/yt-dlp/yt-dlp/issues/9325)) by [src-tinkerer](https://github.com/src-tinkerer)
- **chzzk**
    - [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/ba6b0c8261e9f0a6373885736ff90a89dd1fb614) ([#8887](https://github.com/yt-dlp/yt-dlp/issues/8887)) by [DmitryScaletta](https://github.com/DmitryScaletta)
    - live: [Support `--wait-for-video`](https://github.com/yt-dlp/yt-dlp/commit/804f2366117b7065552a1c3cddb9ec19b688a5c1) ([#9309](https://github.com/yt-dlp/yt-dlp/issues/9309)) by [hui1601](https://github.com/hui1601)
- **cineverse**: [Detect when login required](https://github.com/yt-dlp/yt-dlp/commit/fc2cc626f07328a6c71b5e21853e4cfa7b1e6256) ([#9081](https://github.com/yt-dlp/yt-dlp/issues/9081)) by [garret1317](https://github.com/garret1317)
- **cloudflarestream**
    - [Extract subtitles](https://github.com/yt-dlp/yt-dlp/commit/4d9dc0abe24ad5d9d22a16f40fc61137dcd103f7) ([#9007](https://github.com/yt-dlp/yt-dlp/issues/9007)) by [Bibhav48](https://github.com/Bibhav48)
    - [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/f3d5face83f948c24bcb91e06d4fa6e8622d7d79) ([#9280](https://github.com/yt-dlp/yt-dlp/issues/9280)) by [bashonly](https://github.com/bashonly)
    - [Improve embed detection](https://github.com/yt-dlp/yt-dlp/commit/464c919ea82aefdf35f138a1ab2dd0bb8fb7fd0e) ([#9287](https://github.com/yt-dlp/yt-dlp/issues/9287)) by [bashonly](https://github.com/bashonly)
- **cloudycdn, lsm**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/5dda3b291f59f388f953337e9fb09a94b64aaf34) ([#8643](https://github.com/yt-dlp/yt-dlp/issues/8643)) by [Caesim404](https://github.com/Caesim404)
- **cnbc**: [Overhaul extractors](https://github.com/yt-dlp/yt-dlp/commit/998dffb5a2343ec709b3d6bbf2bf019649080239) ([#8741](https://github.com/yt-dlp/yt-dlp/issues/8741)) by [gonzalezjo](https://github.com/gonzalezjo), [Noor-5](https://github.com/Noor-5), [ruiminggu](https://github.com/ruiminggu), [seproDev](https://github.com/seproDev), [zhijinwuu](https://github.com/zhijinwuu)
- **craftsy**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/96f3924bac174f2fd401f86f78e77d7e0c5ee008) ([#9384](https://github.com/yt-dlp/yt-dlp/issues/9384)) by [bashonly](https://github.com/bashonly)
- **crooksandliars**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/03536126d32bd861e38536371f0cd5f1b71dcb7a) ([#9192](https://github.com/yt-dlp/yt-dlp/issues/9192)) by [seproDev](https://github.com/seproDev)
- **crtvg**: [Fix `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/785ab1af7f131e73444634ad57b39478651a43d3) ([#9404](https://github.com/yt-dlp/yt-dlp/issues/9404)) by [Xpl0itU](https://github.com/Xpl0itU)
- **dailymotion**: [Support search](https://github.com/yt-dlp/yt-dlp/commit/11ffa92a61e5847b3dfa8975f91ecb3ac2178841) ([#8292](https://github.com/yt-dlp/yt-dlp/issues/8292)) by [drzraf](https://github.com/drzraf), [seproDev](https://github.com/seproDev)
- **douyin**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/9ff946645568e71046487571eefa9cb524a5189b) ([#9239](https://github.com/yt-dlp/yt-dlp/issues/9239)) by [114514ns](https://github.com/114514ns), [bashonly](https://github.com/bashonly) (With fixes in [e546e5d](https://github.com/yt-dlp/yt-dlp/commit/e546e5d3b33a50075e574a2e7b8eda7ea874d21e) by [bashonly](https://github.com/bashonly))
- **duboku**: [Fix m3u8 formats extraction](https://github.com/yt-dlp/yt-dlp/commit/d3d4187da90a6b85f4ebae4bb07693cc9b412d75) ([#9161](https://github.com/yt-dlp/yt-dlp/issues/9161)) by [DmitryScaletta](https://github.com/DmitryScaletta)
- **dumpert**: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/eedb38ce4093500e19279d50b708fb9c18bf4dbf) ([#9320](https://github.com/yt-dlp/yt-dlp/issues/9320)) by [rvsit](https://github.com/rvsit)
- **elementorembed**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/6171b050d70435008e64fa06aa6f19c4e5bec75f) ([#8948](https://github.com/yt-dlp/yt-dlp/issues/8948)) by [pompos02](https://github.com/pompos02), [seproDev](https://github.com/seproDev)
- **eporner**: [Extract AV1 formats](https://github.com/yt-dlp/yt-dlp/commit/96d0f8c1cb8aec250c5614bfde6b5fb95f10819b) ([#9028](https://github.com/yt-dlp/yt-dlp/issues/9028)) by [michal-repo](https://github.com/michal-repo)
- **errjupiter**
    - [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/a514cc2feb1c3b265b19acab11487acad8bb3ab0) ([#8549](https://github.com/yt-dlp/yt-dlp/issues/8549)) by [glensc](https://github.com/glensc)
    - [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/80ed8bdeba5a945f127ef9ab055a4823329a1210) ([#9218](https://github.com/yt-dlp/yt-dlp/issues/9218)) by [glensc](https://github.com/glensc)
- **facebook**
    - [Add new ID format](https://github.com/yt-dlp/yt-dlp/commit/cf9af2c7f1fedd881a157b3fbe725e5494b00924) ([#3824](https://github.com/yt-dlp/yt-dlp/issues/3824)) by [kclauhk](https://github.com/kclauhk), [Wikidepia](https://github.com/Wikidepia)
    - [Improve extraction](https://github.com/yt-dlp/yt-dlp/commit/2e30b5567b5c6113d46b39163db5b044aea8667e) by [jingtra](https://github.com/jingtra), [ringus1](https://github.com/ringus1)
    - [Improve thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/3c4d3ee491b0ec22ed3cade51d943d3d27141ba7) ([#9060](https://github.com/yt-dlp/yt-dlp/issues/9060)) by [kclauhk](https://github.com/kclauhk)
    - [Set format HTTP chunk size](https://github.com/yt-dlp/yt-dlp/commit/5b68c478fb0b93ea6b8fac23f50e12217fa063db) ([#9058](https://github.com/yt-dlp/yt-dlp/issues/9058)) by [bashonly](https://github.com/bashonly), [kclauhk](https://github.com/kclauhk)
    - [Support events](https://github.com/yt-dlp/yt-dlp/commit/9b5efaf86b99a2664fff9fc725d275f766c3221d) ([#9055](https://github.com/yt-dlp/yt-dlp/issues/9055)) by [kclauhk](https://github.com/kclauhk)
    - [Support permalink URLs](https://github.com/yt-dlp/yt-dlp/commit/87286e93af949c4e6a0f8ba34af6a1ab5aa102b6) ([#9061](https://github.com/yt-dlp/yt-dlp/issues/9061)) by [kclauhk](https://github.com/kclauhk)
    - ads: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/a40b0070c2a00d3ed839897462171a82323aa875) ([#8870](https://github.com/yt-dlp/yt-dlp/issues/8870)) by [kclauhk](https://github.com/kclauhk)
- **flextv**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/4f043479090dc8a7e06e0bb53691e5414320dfb2) ([#9178](https://github.com/yt-dlp/yt-dlp/issues/9178)) by [DmitryScaletta](https://github.com/DmitryScaletta)
- **floatplane**: [Improve metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/9cd90447907a59c8a2727583f4a755fb23ed8cd3) ([#8934](https://github.com/yt-dlp/yt-dlp/issues/8934)) by [chtk](https://github.com/chtk)
- **francetv**
    - [Fix DAI livestreams](https://github.com/yt-dlp/yt-dlp/commit/e4fbe5f886a6693f2466877c12e99c30c5442ace) ([#9380](https://github.com/yt-dlp/yt-dlp/issues/9380)) by [bashonly](https://github.com/bashonly)
    - [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/9749ac7fecbfda391afbadf2870797ce0e382622) ([#9333](https://github.com/yt-dlp/yt-dlp/issues/9333)) by [bashonly](https://github.com/bashonly)
    - [Fix m3u8 formats extraction](https://github.com/yt-dlp/yt-dlp/commit/ede624d1db649f5a4b61f8abbb746f365322de27) ([#9347](https://github.com/yt-dlp/yt-dlp/issues/9347)) by [bashonly](https://github.com/bashonly)
- **funk**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/cd0443fb14e2ed805abb02792473457553a123d1) ([#9194](https://github.com/yt-dlp/yt-dlp/issues/9194)) by [seproDev](https://github.com/seproDev)
- **generic**: [Follow https redirects properly](https://github.com/yt-dlp/yt-dlp/commit/c8c9039e640495700f76a13496e3418bdd4382ba) ([#9121](https://github.com/yt-dlp/yt-dlp/issues/9121)) by [seproDev](https://github.com/seproDev)
- **getcourseru**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/4310b6650eeb5630295f4591b37720877878c57a) ([#8873](https://github.com/yt-dlp/yt-dlp/issues/8873)) by [divStar](https://github.com/divStar), [seproDev](https://github.com/seproDev)
- **gofile**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/77c2472ca1ef9050a66aa68bc5fa1bee88706c66) ([#9074](https://github.com/yt-dlp/yt-dlp/issues/9074)) by [jazz1611](https://github.com/jazz1611)
- **googledrive**: [Fix source file extraction](https://github.com/yt-dlp/yt-dlp/commit/5498729c59b03a9511c64552da3ba2f802166f8d) ([#8990](https://github.com/yt-dlp/yt-dlp/issues/8990)) by [jazz1611](https://github.com/jazz1611)
- **goplay**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/7e90e34fa4617b53f8c8a9e69f460508cb1f51b0) ([#6654](https://github.com/yt-dlp/yt-dlp/issues/6654)) by [alard](https://github.com/alard)
- **gopro**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/4a07a455bbf7acf87550053bbba949c828e350ba) ([#9019](https://github.com/yt-dlp/yt-dlp/issues/9019)) by [stilor](https://github.com/stilor)
- **ilpost**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/aa5dcc4ee65916a36cbe1b1b5b29b9110c3163ed) ([#9001](https://github.com/yt-dlp/yt-dlp/issues/9001)) by [CapacitorSet](https://github.com/CapacitorSet)
- **jiosaavnsong**: [Support more bitrates](https://github.com/yt-dlp/yt-dlp/commit/5154dc0a687528f995cde22b5ff63f82c740e98a) ([#8834](https://github.com/yt-dlp/yt-dlp/issues/8834)) by [alien-developers](https://github.com/alien-developers), [bashonly](https://github.com/bashonly)
- **kukululive**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/20cdad5a2c0499d5a6746f5466a2ab0c97b75884) ([#8877](https://github.com/yt-dlp/yt-dlp/issues/8877)) by [DmitryScaletta](https://github.com/DmitryScaletta)
- **lefigarovideoembed**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/9401736fd08767c58af45a1e36ff5929c5fa1ac9) ([#9198](https://github.com/yt-dlp/yt-dlp/issues/9198)) by [seproDev](https://github.com/seproDev)
- **linkedin**: [Fix metadata and extract subtitles](https://github.com/yt-dlp/yt-dlp/commit/017adb28e7fe7b8c8fc472332d86740f31141519) ([#9056](https://github.com/yt-dlp/yt-dlp/issues/9056)) by [barsnick](https://github.com/barsnick)
- **magellantv**: [Support episodes](https://github.com/yt-dlp/yt-dlp/commit/3dc9232e1aa58fe3c2d8cafb50e8162d6f0e891e) ([#9199](https://github.com/yt-dlp/yt-dlp/issues/9199)) by [seproDev](https://github.com/seproDev)
- **magentamusik**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/5e2e24b2c5795756d81785b06b10723ddb6db7b2) ([#7790](https://github.com/yt-dlp/yt-dlp/issues/7790)) by [pwaldhauer](https://github.com/pwaldhauer), [seproDev](https://github.com/seproDev)
- **medaltv**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/02e343f6ef6d7b3f9087ff69e4a1db0b4b4a5c5d) ([#9098](https://github.com/yt-dlp/yt-dlp/issues/9098)) by [Danish-H](https://github.com/Danish-H)
- **mlbarticle**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/50e06e21a68e336198198bda332b8e7d2314f201) ([#9021](https://github.com/yt-dlp/yt-dlp/issues/9021)) by [HobbyistDev](https://github.com/HobbyistDev)
- **motherless**: [Support uploader playlists](https://github.com/yt-dlp/yt-dlp/commit/9f1e9dab21bbe651544c8f4663b0e615dc450e4d) ([#8994](https://github.com/yt-dlp/yt-dlp/issues/8994)) by [dasidiot](https://github.com/dasidiot)
- **mujrozhlas**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/4170b3d7120e06db3391eef39c5add18a1ddf2c3) ([#9306](https://github.com/yt-dlp/yt-dlp/issues/9306)) by [bashonly](https://github.com/bashonly)
- **mx3**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/5a63454b3637b3603434026cddfeac509218b90e) ([#8736](https://github.com/yt-dlp/yt-dlp/issues/8736)) by [martinxyz](https://github.com/martinxyz)
- **naver**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/a281beba8d8f007cf220f96dd1d9412bb070c7d8) ([#8883](https://github.com/yt-dlp/yt-dlp/issues/8883)) by [seproDev](https://github.com/seproDev)
- **nebula**: [Support podcasts](https://github.com/yt-dlp/yt-dlp/commit/0de09c5b9ed619d4a93d7c451c6ddff0381de808) ([#9140](https://github.com/yt-dlp/yt-dlp/issues/9140)) by [c-basalt](https://github.com/c-basalt), [seproDev](https://github.com/seproDev)
- **nerdcubedfeed**: [Overhaul extractor](https://github.com/yt-dlp/yt-dlp/commit/29a74a6126101aabaa1726ae41b1ca55cf26e7a7) ([#9269](https://github.com/yt-dlp/yt-dlp/issues/9269)) by [seproDev](https://github.com/seproDev)
- **newgrounds**
    - [Fix login and clean up extraction](https://github.com/yt-dlp/yt-dlp/commit/0fcefb92f3ebfc5cada19c1e85a715f020d0f333) ([#9356](https://github.com/yt-dlp/yt-dlp/issues/9356)) by [Grub4K](https://github.com/Grub4K), [mrmedieval](https://github.com/mrmedieval)
    - user: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/3e083191cdc34dd8c482da9a9b4bc682f824cb9d) ([#9046](https://github.com/yt-dlp/yt-dlp/issues/9046)) by [u-spec-png](https://github.com/u-spec-png)
- **nfb**: [Add support for onf.ca and series](https://github.com/yt-dlp/yt-dlp/commit/4b8b0dded8c65cd5b2ab2e858058ba98c9bf49ff) ([#8997](https://github.com/yt-dlp/yt-dlp/issues/8997)) by [bashonly](https://github.com/bashonly), [rrgomes](https://github.com/rrgomes)
- **nhkradiru**: [Extract extended description](https://github.com/yt-dlp/yt-dlp/commit/4392447d9404e3c25cfeb8f5bdfff31b0448da39) ([#9162](https://github.com/yt-dlp/yt-dlp/issues/9162)) by [garret1317](https://github.com/garret1317)
- **nhkradirulive**: [Make metadata extraction non-fatal](https://github.com/yt-dlp/yt-dlp/commit/5af1f19787f7d652fce72dd3ab9536cdd980fe85) ([#8956](https://github.com/yt-dlp/yt-dlp/issues/8956)) by [garret1317](https://github.com/garret1317)
- **niconico**
    - [Remove legacy danmaku extraction](https://github.com/yt-dlp/yt-dlp/commit/974d444039c8bbffb57265c6792cd52d169fe1b9) ([#9209](https://github.com/yt-dlp/yt-dlp/issues/9209)) by [pzhlkj6612](https://github.com/pzhlkj6612)
    - [Support DMS formats](https://github.com/yt-dlp/yt-dlp/commit/aa13a8e3dd3b698cc40ec438988b1ad834e11a41) ([#9282](https://github.com/yt-dlp/yt-dlp/issues/9282)) by [pzhlkj6612](https://github.com/pzhlkj6612), [xpadev-net](https://github.com/xpadev-net) (With fixes in [40966e8](https://github.com/yt-dlp/yt-dlp/commit/40966e8da27bbf770dacf9be9363fcc3ad72cc9f) by [pzhlkj6612](https://github.com/pzhlkj6612))
- **ninaprotocol**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/62c65bfaf81e04e6746f6fdbafe384eb3edddfbc) ([#8946](https://github.com/yt-dlp/yt-dlp/issues/8946)) by [RaduManole](https://github.com/RaduManole), [seproDev](https://github.com/seproDev)
- **ninenews**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/43694ce13c5a9f1afca8b02b8b2b9b1576d6503d) ([#8840](https://github.com/yt-dlp/yt-dlp/issues/8840)) by [SirElderling](https://github.com/SirElderling)
- **nova**: [Fix embed extraction](https://github.com/yt-dlp/yt-dlp/commit/c168d8791d0974a8a8fcb3b4a4bc2d830df51622) ([#9221](https://github.com/yt-dlp/yt-dlp/issues/9221)) by [seproDev](https://github.com/seproDev)
- **ntvru**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/7a29cbbd5fd7363e7e8535ee1506b7052465d13f) ([#9276](https://github.com/yt-dlp/yt-dlp/issues/9276)) by [bashonly](https://github.com/bashonly), [dirkf](https://github.com/dirkf)
- **nuum**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/acaf806c15f0a802ba286c23af02a10cf4bd4731) ([#8868](https://github.com/yt-dlp/yt-dlp/issues/8868)) by [DmitryScaletta](https://github.com/DmitryScaletta), [seproDev](https://github.com/seproDev)
- **nytimes**
    - [Extract timestamp](https://github.com/yt-dlp/yt-dlp/commit/05420227aaab60a39c0f9ade069c5862be36b1fa) ([#9142](https://github.com/yt-dlp/yt-dlp/issues/9142)) by [SirElderling](https://github.com/SirElderling)
    - [Overhaul extractors](https://github.com/yt-dlp/yt-dlp/commit/07256b9fee23960799024b95d5972abc7174aa81) ([#9075](https://github.com/yt-dlp/yt-dlp/issues/9075)) by [SirElderling](https://github.com/SirElderling)
- **onefootball**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/644738ddaa45428cb0babd41ead22454e5a2545e) ([#9222](https://github.com/yt-dlp/yt-dlp/issues/9222)) by [seproDev](https://github.com/seproDev)
- **openrec**: [Pass referer for m3u8 formats](https://github.com/yt-dlp/yt-dlp/commit/f591e605dfee4085ec007d6d056c943cbcacc429) ([#9253](https://github.com/yt-dlp/yt-dlp/issues/9253)) by [fireattack](https://github.com/fireattack)
- **orf**: on: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/a0d50aabc5462aee302bd3f2663d3a3554875789) ([#9113](https://github.com/yt-dlp/yt-dlp/issues/9113)) by [HobbyistDev](https://github.com/HobbyistDev)
- **patreon**: [Fix embedded HLS extraction](https://github.com/yt-dlp/yt-dlp/commit/f0e8bc7c60b61fe18b63116c975609d76b904771) ([#8993](https://github.com/yt-dlp/yt-dlp/issues/8993)) by [johnvictorfs](https://github.com/johnvictorfs)
- **peertube**: [Update instances](https://github.com/yt-dlp/yt-dlp/commit/35d96982f1033e36215d323317981ee17e8ab0d5) ([#9070](https://github.com/yt-dlp/yt-dlp/issues/9070)) by [Chocobozzz](https://github.com/Chocobozzz)
- **piapro**: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/8e6e3651727b0b85764857fc6329fe5e0a3f00de) ([#8999](https://github.com/yt-dlp/yt-dlp/issues/8999)) by [FinnRG](https://github.com/FinnRG)
- **playsuisse**: [Add login support](https://github.com/yt-dlp/yt-dlp/commit/cae6e461073fb7c32fd32052a3e6721447c469bc) ([#9077](https://github.com/yt-dlp/yt-dlp/issues/9077)) by [chkuendig](https://github.com/chkuendig)
- **pornhub**: [Fix login support](https://github.com/yt-dlp/yt-dlp/commit/de954c1b4d3a6db8a6525507e65303c7bb03f39f) ([#9227](https://github.com/yt-dlp/yt-dlp/issues/9227)) by [feederbox826](https://github.com/feederbox826)
- **pr0gramm**: [Enable POL filter and provide tags without login](https://github.com/yt-dlp/yt-dlp/commit/5f25f348f9eb5db842b1ec6799f95bebb7ba35a7) ([#9051](https://github.com/yt-dlp/yt-dlp/issues/9051)) by [Grub4K](https://github.com/Grub4K)
- **prankcastpost**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/a2bac6b7adb7b0e955125838e20bb39eece630ce) ([#8933](https://github.com/yt-dlp/yt-dlp/issues/8933)) by [columndeeply](https://github.com/columndeeply)
- **radiko**: [Extract more metadata](https://github.com/yt-dlp/yt-dlp/commit/e3ce2b385ec1f03fac9d4210c57fda77134495fc) ([#9115](https://github.com/yt-dlp/yt-dlp/issues/9115)) by [YoshichikaAAA](https://github.com/YoshichikaAAA)
- **rai**
    - [Filter unavailable formats](https://github.com/yt-dlp/yt-dlp/commit/f78814923748277e7067b796f25870686fb46205) ([#9189](https://github.com/yt-dlp/yt-dlp/issues/9189)) by [nixxo](https://github.com/nixxo)
    - [Fix m3u8 formats extraction](https://github.com/yt-dlp/yt-dlp/commit/8f423cf8051fbfeedd57cca00d106012e6e86a97) ([#9291](https://github.com/yt-dlp/yt-dlp/issues/9291)) by [nixxo](https://github.com/nixxo)
- **redcdnlivx, sejm**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/fcaa2e735b00b15a2b0d9f55f4187c654b4b5b39) ([#8676](https://github.com/yt-dlp/yt-dlp/issues/8676)) by [selfisekai](https://github.com/selfisekai)
- **redtube**
    - [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/c91d8b1899403daff6fc15206ad32de8db17fb8f) ([#9076](https://github.com/yt-dlp/yt-dlp/issues/9076)) by [jazz1611](https://github.com/jazz1611)
    - [Support redtube.com.br URLs](https://github.com/yt-dlp/yt-dlp/commit/4a6ff0b47a700dee3ee5c54804c31965308479ae) ([#9103](https://github.com/yt-dlp/yt-dlp/issues/9103)) by [jazz1611](https://github.com/jazz1611)
- **ridehome**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/cd7086c0d54ec1d7e02a30bd5bd934bdb2c54642) ([#8875](https://github.com/yt-dlp/yt-dlp/issues/8875)) by [SirElderling](https://github.com/SirElderling)
- **rinsefmartistplaylist**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/1a36dbad712d359ec1c5b73d9bbbe562c03e9660) ([#8794](https://github.com/yt-dlp/yt-dlp/issues/8794)) by [SirElderling](https://github.com/SirElderling)
- **roosterteeth**
    - [Add Brightcove fallback](https://github.com/yt-dlp/yt-dlp/commit/b2cc150ad83ba20ceb2d6e73d09854eed3c2d05c) ([#9403](https://github.com/yt-dlp/yt-dlp/issues/9403)) by [bashonly](https://github.com/bashonly)
    - [Extract ad-free streams](https://github.com/yt-dlp/yt-dlp/commit/dd29e6e5fdf0f3758cb0829e73749832768f1a4e) ([#9355](https://github.com/yt-dlp/yt-dlp/issues/9355)) by [jkmartindale](https://github.com/jkmartindale)
    - [Extract release date and timestamp](https://github.com/yt-dlp/yt-dlp/commit/dfd8c0b69683b1c11beea039a96dd2949026c1d7) ([#9393](https://github.com/yt-dlp/yt-dlp/issues/9393)) by [bashonly](https://github.com/bashonly)
    - [Support bonus features](https://github.com/yt-dlp/yt-dlp/commit/8993721ecb34867b52b79f6e92b233008d1cbe78) ([#9406](https://github.com/yt-dlp/yt-dlp/issues/9406)) by [Bl4Cc4t](https://github.com/Bl4Cc4t)
- **rule34video**
    - [Extract `creators`](https://github.com/yt-dlp/yt-dlp/commit/3d9dc2f3590e10abf1561ebdaed96734a740587c) ([#9258](https://github.com/yt-dlp/yt-dlp/issues/9258)) by [gmes78](https://github.com/gmes78)
    - [Extract more metadata](https://github.com/yt-dlp/yt-dlp/commit/fee2d8d9c38f9b5f0a8df347c1e698983339c34d) ([#7416](https://github.com/yt-dlp/yt-dlp/issues/7416)) by [gmes78](https://github.com/gmes78)
    - [Fix `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/c0ecceeefe6ebd27452d9d8f20658f83ae121d04) ([#9044](https://github.com/yt-dlp/yt-dlp/issues/9044)) by [gmes78](https://github.com/gmes78)
- **rumblechannel**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/0023af81fbce01984f35b34ecaf8562739831227) ([#9092](https://github.com/yt-dlp/yt-dlp/issues/9092)) by [Pranaxcau](https://github.com/Pranaxcau), [vista-narvas](https://github.com/vista-narvas)
- **screencastify**: [Update `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/0bee29493ca8f91a0055a3706c7c94f5860188df) ([#9232](https://github.com/yt-dlp/yt-dlp/issues/9232)) by [seproDev](https://github.com/seproDev)
- **svtpage**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/ddd4b5e10a653bee78e656107710021c1b82934c) ([#8938](https://github.com/yt-dlp/yt-dlp/issues/8938)) by [diman8](https://github.com/diman8)
- **swearnet**: [Raise for login required](https://github.com/yt-dlp/yt-dlp/commit/b05640d532c43a52c0a0da096bb2dbd51e105ec0) ([#9281](https://github.com/yt-dlp/yt-dlp/issues/9281)) by [bashonly](https://github.com/bashonly)
- **tiktok**: [Fix webpage extraction](https://github.com/yt-dlp/yt-dlp/commit/d9b4154cbcb979d7e30af3a73b1bee422aae5aa3) ([#9327](https://github.com/yt-dlp/yt-dlp/issues/9327)) by [bashonly](https://github.com/bashonly)
- **trtworld**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/8ab84650837e58046430c9f4b615c56a8886e071) ([#8701](https://github.com/yt-dlp/yt-dlp/issues/8701)) by [ufukk](https://github.com/ufukk)
- **tvp**: [Support livestreams](https://github.com/yt-dlp/yt-dlp/commit/882e3b753c79c7799ce135c3a5edb72494b576af) ([#8860](https://github.com/yt-dlp/yt-dlp/issues/8860)) by [selfisekai](https://github.com/selfisekai)
- **twitch**: [Fix m3u8 extraction](https://github.com/yt-dlp/yt-dlp/commit/5b8c69ae04444a4c80a5a99917e40f75a116c3b8) ([#8960](https://github.com/yt-dlp/yt-dlp/issues/8960)) by [DmitryScaletta](https://github.com/DmitryScaletta)
- **twitter**
    - [Extract bitrate for HLS audio formats](https://github.com/yt-dlp/yt-dlp/commit/28e53d60df9b8aadd52a93504e30e885c9c35262) ([#9257](https://github.com/yt-dlp/yt-dlp/issues/9257)) by [bashonly](https://github.com/bashonly)
    - [Extract numeric `channel_id`](https://github.com/yt-dlp/yt-dlp/commit/55f1833376505ed1e4be0516b09bb3ea4425e8a4) ([#9263](https://github.com/yt-dlp/yt-dlp/issues/9263)) by [bashonly](https://github.com/bashonly)
- **txxx**: [Extract thumbnails](https://github.com/yt-dlp/yt-dlp/commit/d79c7e9937c388c68b722ab7450960e43ef776d6) ([#9063](https://github.com/yt-dlp/yt-dlp/issues/9063)) by [shmohawk](https://github.com/shmohawk)
- **utreon**: [Support playeur.com](https://github.com/yt-dlp/yt-dlp/commit/41d6b61e9852a5b97f47cc8a7718b31fb23f0aea) ([#9182](https://github.com/yt-dlp/yt-dlp/issues/9182)) by [DmitryScaletta](https://github.com/DmitryScaletta)
- **vbox7**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/67bb70cd700c8d4c3149cd9e0539a5f32c3d1ce6) ([#9100](https://github.com/yt-dlp/yt-dlp/issues/9100)) by [seproDev](https://github.com/seproDev)
- **viewlift**: [Add support for chorki.com](https://github.com/yt-dlp/yt-dlp/commit/41b6cdb4197aaf7ad82bdad6885eb5d5c64acd74) ([#9095](https://github.com/yt-dlp/yt-dlp/issues/9095)) by [NurTasin](https://github.com/NurTasin)
- **vimeo**
    - [Extract `live_status` and `release_timestamp`](https://github.com/yt-dlp/yt-dlp/commit/f0426e9ca57dd14b82e6c13afc17947614f1e8eb) ([#9290](https://github.com/yt-dlp/yt-dlp/issues/9290)) by [pzhlkj6612](https://github.com/pzhlkj6612)
    - [Fix API headers](https://github.com/yt-dlp/yt-dlp/commit/8e765755f7f4909e1b535e61b7376b2d66e1ba6a) ([#9125](https://github.com/yt-dlp/yt-dlp/issues/9125)) by [bashonly](https://github.com/bashonly)
    - [Fix login](https://github.com/yt-dlp/yt-dlp/commit/2e8de097ad82da378e97005e8f1ff7e5aebca585) ([#9274](https://github.com/yt-dlp/yt-dlp/issues/9274)) by [bashonly](https://github.com/bashonly)
- **viously**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/95e82347b398d8bb160767cdd975edecd62cbabd) ([#8927](https://github.com/yt-dlp/yt-dlp/issues/8927)) by [nbr23](https://github.com/nbr23), [seproDev](https://github.com/seproDev)
- **youtube**
    - [Better error when all player responses are skipped](https://github.com/yt-dlp/yt-dlp/commit/5eedc208ec89d6284777060c94aadd06502338b9) ([#9083](https://github.com/yt-dlp/yt-dlp/issues/9083)) by [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan)
    - [Bump Android and iOS client versions](https://github.com/yt-dlp/yt-dlp/commit/413d3675804599bc8fe419c19e36490fd8f0b30f) ([#9317](https://github.com/yt-dlp/yt-dlp/issues/9317)) by [bashonly](https://github.com/bashonly)
    - [Further bump client versions](https://github.com/yt-dlp/yt-dlp/commit/7aad06541e543fa3452d3d2513e6f079aad1f99b) ([#9395](https://github.com/yt-dlp/yt-dlp/issues/9395)) by [bashonly](https://github.com/bashonly)
    - tab: [Fix `tags` extraction](https://github.com/yt-dlp/yt-dlp/commit/8828f4576bd862438d4fbf634f1d6ab18a217b0e) ([#9413](https://github.com/yt-dlp/yt-dlp/issues/9413)) by [x11x](https://github.com/x11x)
- **zenporn**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/f00c0def7434fac3c88503c2a77c4b2419b8e5ca) ([#8509](https://github.com/yt-dlp/yt-dlp/issues/8509)) by [SirElderling](https://github.com/SirElderling)
- **zetland**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/2f4b57594673035a59d72f7667588da848820034) ([#9116](https://github.com/yt-dlp/yt-dlp/issues/9116)) by [HobbyistDev](https://github.com/HobbyistDev)

#### Downloader changes
- **http**: [Reset resume length to handle `FileNotFoundError`](https://github.com/yt-dlp/yt-dlp/commit/2d91b9845621639c53dca7ee9d3d954f3624ba18) ([#8399](https://github.com/yt-dlp/yt-dlp/issues/8399)) by [boredzo](https://github.com/boredzo)

#### Networking changes
- [Remove `_CompatHTTPError`](https://github.com/yt-dlp/yt-dlp/commit/811d298b231cfa29e75c321b23a91d1c2b17602c) ([#8871](https://github.com/yt-dlp/yt-dlp/issues/8871)) by [coletdjnz](https://github.com/coletdjnz)
- **Request Handler**
    - [Remove additional logging handlers on close](https://github.com/yt-dlp/yt-dlp/commit/0085e2bab8465ee7d46d16fcade3ed5e96cc8a48) ([#9032](https://github.com/yt-dlp/yt-dlp/issues/9032)) by [coletdjnz](https://github.com/coletdjnz)
    - requests: [Apply `remove_dot_segments` to absolute redirect locations](https://github.com/yt-dlp/yt-dlp/commit/35f4f764a786685ea45d84abe1cf1ad3847f4c97) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- **build**
    - [Add `default` optional dependency group](https://github.com/yt-dlp/yt-dlp/commit/cf91400a1dd6cc99b11a6d163e1af73b64d618c9) ([#9295](https://github.com/yt-dlp/yt-dlp/issues/9295)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
    - [Add transitional `setup.py` and `pyinst.py`](https://github.com/yt-dlp/yt-dlp/commit/0abf2f1f153ab47990edbeee3477dc55f74c7f89) ([#9296](https://github.com/yt-dlp/yt-dlp/issues/9296)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan)
    - [Bump `actions/upload-artifact` to v4 and adjust workflows](https://github.com/yt-dlp/yt-dlp/commit/3876429d72afb35247f4b2531eb9b16cfc7e0968) by [bashonly](https://github.com/bashonly)
    - [Bump `conda-incubator/setup-miniconda` to v3](https://github.com/yt-dlp/yt-dlp/commit/b0059f0413a6ba6ab0a3aec1f00188ce083cd8bf) by [bashonly](https://github.com/bashonly)
    - [Fix `secretstorage` for ARM builds](https://github.com/yt-dlp/yt-dlp/commit/920397634d1e84e76d2cb897bd6d69ba0c6bd5ca) by [bashonly](https://github.com/bashonly)
    - [Migrate to `pyproject.toml` and `hatchling`](https://github.com/yt-dlp/yt-dlp/commit/775cde82dc5b1dc64ab0539a92dd8c7ba6c0ad33) by [bashonly](https://github.com/bashonly) (With fixes in [43cfd46](https://github.com/yt-dlp/yt-dlp/commit/43cfd462c0d01eff22c1d4290aeb96eb1ea2c0e1))
    - [Move bundle scripts into `bundle` submodule](https://github.com/yt-dlp/yt-dlp/commit/a1b778428991b1779203bac243ef4e9b6baea90c) by [bashonly](https://github.com/bashonly)
    - [Support failed build job re-runs](https://github.com/yt-dlp/yt-dlp/commit/eabbccc439720fba381919a88be4fe4d96464cbd) ([#9277](https://github.com/yt-dlp/yt-dlp/issues/9277)) by [bashonly](https://github.com/bashonly)
    - Makefile
        - [Add automated `CODE_FOLDERS` and `CODE_FILES`](https://github.com/yt-dlp/yt-dlp/commit/868d2f60a7cb59b410c8cbfb452cbdb072687b81) by [bashonly](https://github.com/bashonly)
        - [Ensure compatibility with BSD `make`](https://github.com/yt-dlp/yt-dlp/commit/beaa1a44554d04d9fe63a743a5bb4431ca778f28) ([#9210](https://github.com/yt-dlp/yt-dlp/issues/9210)) by [bashonly](https://github.com/bashonly) (With fixes in [73fcfa3](https://github.com/yt-dlp/yt-dlp/commit/73fcfa39f59113a8728249de2c4cee3025f17dc2))
        - [Fix man pages generated by `pandoc>=3`](https://github.com/yt-dlp/yt-dlp/commit/fb44020fa98e47620b3aa1dab94b4c5b7bfb40bd) ([#7047](https://github.com/yt-dlp/yt-dlp/issues/7047)) by [t-nil](https://github.com/t-nil)
- **ci**: [Bump `actions/setup-python` to v5](https://github.com/yt-dlp/yt-dlp/commit/b14e818b37f62e3224da157b3ad768b3f0815fcd) by [bashonly](https://github.com/bashonly)
- **cleanup**
    - [Build files cleanup](https://github.com/yt-dlp/yt-dlp/commit/867f637b95b342e1cb9f1dc3c6cf0ffe727187ce) by [bashonly](https://github.com/bashonly)
    - [Fix infodict returned fields](https://github.com/yt-dlp/yt-dlp/commit/f4f9f6d00edcac6d4eb2b3fb78bf81326235d492) ([#8906](https://github.com/yt-dlp/yt-dlp/issues/8906)) by [seproDev](https://github.com/seproDev)
    - [Fix typo in README.md](https://github.com/yt-dlp/yt-dlp/commit/292d60b1ed3b9fe5bcb2775a894cca99b0f9473e) ([#8894](https://github.com/yt-dlp/yt-dlp/issues/8894)) by [antonkesy](https://github.com/antonkesy)
    - [Mark broken and remove dead extractors](https://github.com/yt-dlp/yt-dlp/commit/df773c3d5d1cc1f877cf8582f0072e386fc49318) ([#9238](https://github.com/yt-dlp/yt-dlp/issues/9238)) by [seproDev](https://github.com/seproDev)
    - [Match both `http` and `https` in `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/a687226b48f71b874fa18b0165ec528d591f53fb) ([#8968](https://github.com/yt-dlp/yt-dlp/issues/8968)) by [seproDev](https://github.com/seproDev)
    - [Remove unused code](https://github.com/yt-dlp/yt-dlp/commit/ed3bb2b0a12c44334e0d09481752dabf2ca1dc13) ([#8968](https://github.com/yt-dlp/yt-dlp/issues/8968)) by [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)
    - Miscellaneous
        - [93240fc](https://github.com/yt-dlp/yt-dlp/commit/93240fc1848de4a94f25844c96e0dcd282ef1d3b) by [bashonly](https://github.com/bashonly), [Grub4k](https://github.com/Grub4k), [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)
        - [615a844](https://github.com/yt-dlp/yt-dlp/commit/615a84447e8322720be77a0e64298d7f42848693) by [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)
- **devscripts**
    - `install_deps`: [Add script and migrate to it](https://github.com/yt-dlp/yt-dlp/commit/b8a433aaca86b15cb9f1a451b0f69371d2fc22a9) by [bashonly](https://github.com/bashonly)
    - `tomlparse`: [Add makeshift toml parser](https://github.com/yt-dlp/yt-dlp/commit/fd647775e27e030ab17387c249e2ebeba68f8ff0) by [Grub4K](https://github.com/Grub4K)
- **docs**: [Misc Cleanup](https://github.com/yt-dlp/yt-dlp/commit/47ab66db0f083a76c7fba0f6e136b21dd5a93e3b) ([#8977](https://github.com/yt-dlp/yt-dlp/issues/8977)) by [Arthurszzz](https://github.com/Arthurszzz), [bashonly](https://github.com/bashonly), [Grub4k](https://github.com/Grub4k), [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)
- **test**
    - [Skip source address tests if the address cannot be bound to](https://github.com/yt-dlp/yt-dlp/commit/69d31914952dd33082ac7019c6f76b43c45b9d06) ([#8900](https://github.com/yt-dlp/yt-dlp/issues/8900)) by [coletdjnz](https://github.com/coletdjnz)
    - websockets: [Fix timeout test on Windows](https://github.com/yt-dlp/yt-dlp/commit/ac340d0745a9de5d494033e3507ef624ba25add3) ([#9344](https://github.com/yt-dlp/yt-dlp/issues/9344)) by [seproDev](https://github.com/seproDev)

### 2023.12.30

#### Core changes
- [Fix format selection parse error for CPython 3.12](https://github.com/yt-dlp/yt-dlp/commit/00cdda4f6fe18712ced13dbc64b7ea10f323e268) ([#8797](https://github.com/yt-dlp/yt-dlp/issues/8797)) by [Grub4K](https://github.com/Grub4K)
- [Let `read_stdin` obey `--quiet`](https://github.com/yt-dlp/yt-dlp/commit/a174c453ee1e853c584ceadeac17eef2bd433dc5) by [pukkandan](https://github.com/pukkandan)
- [Merged with youtube-dl be008e6](https://github.com/yt-dlp/yt-dlp/commit/65de7d204ce88c0225df1321060304baab85dbd8) by [bashonly](https://github.com/bashonly), [dirkf](https://github.com/dirkf), [Grub4K](https://github.com/Grub4K)
- [Parse `release_year` from `release_date`](https://github.com/yt-dlp/yt-dlp/commit/1732eccc0a40256e076bf0435a29f0f1d8419280) ([#8524](https://github.com/yt-dlp/yt-dlp/issues/8524)) by [seproDev](https://github.com/seproDev)
- [Release workflow and Updater cleanup](https://github.com/yt-dlp/yt-dlp/commit/632b8ee54eb2df8ac6e20746a0bd95b7ebb053aa) ([#8640](https://github.com/yt-dlp/yt-dlp/issues/8640)) by [bashonly](https://github.com/bashonly)
- [Remove Python 3.7 support](https://github.com/yt-dlp/yt-dlp/commit/f4b95acafcd69a50040730dfdf732e797278fdcc) ([#8361](https://github.com/yt-dlp/yt-dlp/issues/8361)) by [bashonly](https://github.com/bashonly)
- [Support `NO_COLOR` environment variable](https://github.com/yt-dlp/yt-dlp/commit/a0b19d319a6ce8b7059318fa17a34b144fde1785) ([#8385](https://github.com/yt-dlp/yt-dlp/issues/8385)) by [Grub4K](https://github.com/Grub4K), [prettykool](https://github.com/prettykool)
- **outtmpl**: [Support multiplication](https://github.com/yt-dlp/yt-dlp/commit/993edd3f6e17e966c763bc86dc34125445cec6b6) by [pukkandan](https://github.com/pukkandan)
- **utils**: `traverse_obj`: [Move `is_user_input` into output template](https://github.com/yt-dlp/yt-dlp/commit/0b6f829b1dfda15d3c1d7d1fbe4ea6102c26dd24) ([#8673](https://github.com/yt-dlp/yt-dlp/issues/8673)) by [Grub4K](https://github.com/Grub4K)
- **webvtt**: [Allow spaces before newlines for CueBlock](https://github.com/yt-dlp/yt-dlp/commit/15f22b4880b6b3f71f350c64d70976ae65b9f1ca) ([#7681](https://github.com/yt-dlp/yt-dlp/issues/7681)) by [TSRBerry](https://github.com/TSRBerry) (With fixes in [298230e](https://github.com/yt-dlp/yt-dlp/commit/298230e550886b746c266724dd701d842ca2696e) by [pukkandan](https://github.com/pukkandan))

#### Extractor changes
- [Add `media_type` field](https://github.com/yt-dlp/yt-dlp/commit/e370f9ec36972d06100a3db893b397bfc1b07b4d) by [trainman261](https://github.com/trainman261)
- [Extract from `media` elements in SMIL manifests](https://github.com/yt-dlp/yt-dlp/commit/ddb2d7588bea48bae965dbfabe6df6550c9d3d43) ([#8504](https://github.com/yt-dlp/yt-dlp/issues/8504)) by [seproDev](https://github.com/seproDev)
- **abematv**: [Fix season metadata](https://github.com/yt-dlp/yt-dlp/commit/cc07f5cc85d9e2a6cd0bedb9d961665eea0d6047) ([#8607](https://github.com/yt-dlp/yt-dlp/issues/8607)) by [middlingphys](https://github.com/middlingphys)
- **allstar**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/3237f8ba29fe13bf95ff42b1e48b5b5109715feb) ([#8274](https://github.com/yt-dlp/yt-dlp/issues/8274)) by [S-Aarab](https://github.com/S-Aarab)
- **altcensored**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/3f90813f0617e0d21302398010de7496c9ae36aa) ([#8291](https://github.com/yt-dlp/yt-dlp/issues/8291)) by [drzraf](https://github.com/drzraf)
- **ard**: [Overhaul extractors](https://github.com/yt-dlp/yt-dlp/commit/5f009a094f0e8450792b097c4c8273622778052d) ([#8878](https://github.com/yt-dlp/yt-dlp/issues/8878)) by [seproDev](https://github.com/seproDev)
- **ardbetamediathek**: [Fix series extraction](https://github.com/yt-dlp/yt-dlp/commit/1f8bd8eba82ba10ddb49ee7cc0be4540dab103d5) ([#8687](https://github.com/yt-dlp/yt-dlp/issues/8687)) by [lstrojny](https://github.com/lstrojny)
- **bbc**
    - [Extract more formats](https://github.com/yt-dlp/yt-dlp/commit/c919b68f7e79ea5010f75f648d3c9e45405a8011) ([#8321](https://github.com/yt-dlp/yt-dlp/issues/8321)) by [barsnick](https://github.com/barsnick), [dirkf](https://github.com/dirkf)
    - [Fix JSON parsing bug](https://github.com/yt-dlp/yt-dlp/commit/19741ab8a401ec64d5e84fdbfcfb141d105e7bc8) by [bashonly](https://github.com/bashonly)
- **bfmtv**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/4903f452b68efb62dadf22e81be8c7934fc743e7) ([#8651](https://github.com/yt-dlp/yt-dlp/issues/8651)) by [bashonly](https://github.com/bashonly)
- **bilibili**: [Support courses and interactive videos](https://github.com/yt-dlp/yt-dlp/commit/9f09bdcfcb8e2b4b2decdc30d35d34b993bc7a94) ([#8343](https://github.com/yt-dlp/yt-dlp/issues/8343)) by [c-basalt](https://github.com/c-basalt)
- **bitchute**: [Fix and improve metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/b1a1ec1540605d2ea7abdb63336ffb1c56bf6316) ([#8507](https://github.com/yt-dlp/yt-dlp/issues/8507)) by [SirElderling](https://github.com/SirElderling)
- **box**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/5a230233d6fce06f4abd1fce0dc92b948e6f780b) ([#8649](https://github.com/yt-dlp/yt-dlp/issues/8649)) by [bashonly](https://github.com/bashonly)
- **bundestag**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/00a3e47bf5440c96025a76e08337ff2a475ed83e) ([#8783](https://github.com/yt-dlp/yt-dlp/issues/8783)) by [Grub4K](https://github.com/Grub4K)
- **drtv**: [Set default ext for m3u8 formats](https://github.com/yt-dlp/yt-dlp/commit/f96ab86cd837b1b5823baa87d144e15322ee9298) ([#8590](https://github.com/yt-dlp/yt-dlp/issues/8590)) by [seproDev](https://github.com/seproDev)
- **duoplay**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/66a0127d45033c698bdbedf162cddc55d9e7b906) ([#8542](https://github.com/yt-dlp/yt-dlp/issues/8542)) by [glensc](https://github.com/glensc)
- **eplus**: [Add login support and DRM detection](https://github.com/yt-dlp/yt-dlp/commit/d5d1517e7d838500800d193ac3234b06e89654cd) ([#8661](https://github.com/yt-dlp/yt-dlp/issues/8661)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **facebook**
    - [Fix Memories extraction](https://github.com/yt-dlp/yt-dlp/commit/c39358a54bc6675ae0c50b81024e5a086e41656a) ([#8681](https://github.com/yt-dlp/yt-dlp/issues/8681)) by [kclauhk](https://github.com/kclauhk)
    - [Improve subtitles extraction](https://github.com/yt-dlp/yt-dlp/commit/9cafb9ff17e14475a35c9a58b5bb010c86c9db4b) ([#8296](https://github.com/yt-dlp/yt-dlp/issues/8296)) by [kclauhk](https://github.com/kclauhk)
- **floatplane**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/628fa244bbce2ad39775a5959e99588f30cac152) ([#8639](https://github.com/yt-dlp/yt-dlp/issues/8639)) by [seproDev](https://github.com/seproDev)
- **francetv**: [Improve metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/71f28097fec1c9e029f74b68a4eadc8915399840) ([#8409](https://github.com/yt-dlp/yt-dlp/issues/8409)) by [Fymyte](https://github.com/Fymyte)
- **instagram**: [Fix stories extraction](https://github.com/yt-dlp/yt-dlp/commit/50eaea9fd7787546b53660e736325fa31c77765d) ([#8843](https://github.com/yt-dlp/yt-dlp/issues/8843)) by [bashonly](https://github.com/bashonly)
- **joqrag**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/db8b4edc7d0bd27da462f6fe82ff6e13e3d68a04) ([#8384](https://github.com/yt-dlp/yt-dlp/issues/8384)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **litv**: [Fix premium content extraction](https://github.com/yt-dlp/yt-dlp/commit/f45c4efcd928a173e1300a8f1ce4258e70c969b1) ([#8842](https://github.com/yt-dlp/yt-dlp/issues/8842)) by [bashonly](https://github.com/bashonly)
- **maariv**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/c5f01bf7d4b9426c87c3f8248de23934a56579e0) ([#8331](https://github.com/yt-dlp/yt-dlp/issues/8331)) by [amir16yp](https://github.com/amir16yp)
- **mediastream**: [Fix authenticated format extraction](https://github.com/yt-dlp/yt-dlp/commit/b03c89309eb141be1a1eceeeb7475dd3b7529ad9) ([#8657](https://github.com/yt-dlp/yt-dlp/issues/8657)) by [NickCis](https://github.com/NickCis)
- **nebula**: [Overhaul extractors](https://github.com/yt-dlp/yt-dlp/commit/45d82be65f71bb05506bd55376c6fdb36bc54142) ([#8566](https://github.com/yt-dlp/yt-dlp/issues/8566)) by [elyse0](https://github.com/elyse0), [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)
- **nintendo**: [Fix Nintendo Direct extraction](https://github.com/yt-dlp/yt-dlp/commit/1d24da6c899ef280d8b0a48a5e280ecd5d39cdf4) ([#8609](https://github.com/yt-dlp/yt-dlp/issues/8609)) by [Grub4K](https://github.com/Grub4K)
- **ondemandkorea**: [Fix upgraded format extraction](https://github.com/yt-dlp/yt-dlp/commit/04a5e06350e3ef7c03f94f2f3f90dd96c6411152) ([#8677](https://github.com/yt-dlp/yt-dlp/issues/8677)) by [seproDev](https://github.com/seproDev)
- **pr0gramm**: [Support variant formats and subtitles](https://github.com/yt-dlp/yt-dlp/commit/f98a3305eb124a0c375d03209d5c5a64fe1766c8) ([#8674](https://github.com/yt-dlp/yt-dlp/issues/8674)) by [Grub4K](https://github.com/Grub4K)
- **rinsefm**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/c91af948e43570025e4aa887e248fd025abae394) ([#8778](https://github.com/yt-dlp/yt-dlp/issues/8778)) by [hashFactory](https://github.com/hashFactory)
- **rudovideo**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/0d531c35eca4c2eb36e160530a7a333edbc727cc) ([#8664](https://github.com/yt-dlp/yt-dlp/issues/8664)) by [nicodato](https://github.com/nicodato)
- **theguardian**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/1fa3f24d4b5d22176b11d78420f1f4b64a5af0a8) ([#8535](https://github.com/yt-dlp/yt-dlp/issues/8535)) by [SirElderling](https://github.com/SirElderling)
- **theplatform**: [Extract more metadata](https://github.com/yt-dlp/yt-dlp/commit/7e09c147fdccb44806bbf601573adc4b77210a89) ([#8635](https://github.com/yt-dlp/yt-dlp/issues/8635)) by [trainman261](https://github.com/trainman261)
- **twitcasting**: [Detect livestreams via API and `show` page](https://github.com/yt-dlp/yt-dlp/commit/585d0ed9abcfcb957f2b2684b8ad43c3af160383) ([#8601](https://github.com/yt-dlp/yt-dlp/issues/8601)) by [bashonly](https://github.com/bashonly), [JC-Chung](https://github.com/JC-Chung)
- **twitcastinguser**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/ff2fde1b8f922fd34bae6172602008cd67c07c93) ([#8650](https://github.com/yt-dlp/yt-dlp/issues/8650)) by [bashonly](https://github.com/bashonly)
- **twitter**
    - [Extract stale tweets](https://github.com/yt-dlp/yt-dlp/commit/1c54a98e19d047e7c15184237b6ef8ad50af489c) ([#8724](https://github.com/yt-dlp/yt-dlp/issues/8724)) by [bashonly](https://github.com/bashonly)
    - [Prioritize m3u8 formats](https://github.com/yt-dlp/yt-dlp/commit/e7d22348e77367740da78a3db27167ecf894b7c9) ([#8826](https://github.com/yt-dlp/yt-dlp/issues/8826)) by [bashonly](https://github.com/bashonly)
    - [Work around API rate-limit](https://github.com/yt-dlp/yt-dlp/commit/116c268438ea4d3738f6fa502c169081ca8f0ee7) ([#8825](https://github.com/yt-dlp/yt-dlp/issues/8825)) by [bashonly](https://github.com/bashonly)
    - broadcast: [Extract `concurrent_view_count`](https://github.com/yt-dlp/yt-dlp/commit/6fe82491ed622b948c512cf4aab46ac3a234ae0a) ([#8600](https://github.com/yt-dlp/yt-dlp/issues/8600)) by [sonmezberkay](https://github.com/sonmezberkay)
- **vidly**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/34df1c1f60fa652c0a6a5c712b06c10e45daf6b7) ([#8612](https://github.com/yt-dlp/yt-dlp/issues/8612)) by [seproDev](https://github.com/seproDev)
- **vocaroo**: [Do not use deprecated `getheader`](https://github.com/yt-dlp/yt-dlp/commit/f223b1b0789f65e06619dcc9fc9e74f50d259379) ([#8606](https://github.com/yt-dlp/yt-dlp/issues/8606)) by [qbnu](https://github.com/qbnu)
- **vvvvid**: [Set user-agent to fix extraction](https://github.com/yt-dlp/yt-dlp/commit/1725e943b0e8a8b585305660d4611e684374409c) ([#8615](https://github.com/yt-dlp/yt-dlp/issues/8615)) by [Kyraminol](https://github.com/Kyraminol)
- **youtube**
    - [Fix `like_count` extraction](https://github.com/yt-dlp/yt-dlp/commit/6b5d93b0b0240e287389d1d43b2d5293e18aa4cc) ([#8763](https://github.com/yt-dlp/yt-dlp/issues/8763)) by [Ganesh910](https://github.com/Ganesh910)
    - [Improve detection of faulty HLS formats](https://github.com/yt-dlp/yt-dlp/commit/bb5a54e6db2422bbd155d93a0e105b6616c09467) ([#8646](https://github.com/yt-dlp/yt-dlp/issues/8646)) by [bashonly](https://github.com/bashonly)
    - [Return empty playlist when channel/tab has no videos](https://github.com/yt-dlp/yt-dlp/commit/044886c220620a7679109e92352890e18b6079e3) by [pukkandan](https://github.com/pukkandan)
    - [Support cf.piped.video](https://github.com/yt-dlp/yt-dlp/commit/6a9c7a2b52655bacfa7ab2da24fd0d14a6fff495) ([#8514](https://github.com/yt-dlp/yt-dlp/issues/8514)) by [OIRNOIR](https://github.com/OIRNOIR)
- **zingmp3**: [Add support for radio and podcasts](https://github.com/yt-dlp/yt-dlp/commit/64de1a4c25bada90374b88d7353754fe8fbfcc51) ([#7189](https://github.com/yt-dlp/yt-dlp/issues/7189)) by [hatienl0i261299](https://github.com/hatienl0i261299)

#### Postprocessor changes
- **ffmpegmetadata**: [Embed stream metadata in single format downloads](https://github.com/yt-dlp/yt-dlp/commit/deeb13eae82e60f82a2c0c5861f460399a997528) ([#8647](https://github.com/yt-dlp/yt-dlp/issues/8647)) by [bashonly](https://github.com/bashonly)

#### Networking changes
- [Strip whitespace around header values](https://github.com/yt-dlp/yt-dlp/commit/196eb0fe77b78e2e5ca02c506c3837c2b1a7964c) ([#8802](https://github.com/yt-dlp/yt-dlp/issues/8802)) by [coletdjnz](https://github.com/coletdjnz)
- **Request Handler**: websockets: [Migrate websockets to networking framework](https://github.com/yt-dlp/yt-dlp/commit/ccfd70f4c24b579c72123ca76ab50164f8f122b7) ([#7720](https://github.com/yt-dlp/yt-dlp/issues/7720)) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- **ci**
    - [Concurrency optimizations](https://github.com/yt-dlp/yt-dlp/commit/f124fa458826308afc86cf364c509f857686ecfd) ([#8614](https://github.com/yt-dlp/yt-dlp/issues/8614)) by [Grub4K](https://github.com/Grub4K)
    - [Run core tests only for core changes](https://github.com/yt-dlp/yt-dlp/commit/13b3cb3c2b7169a1e17d6fc62593bf744170521c) ([#8841](https://github.com/yt-dlp/yt-dlp/issues/8841)) by [Grub4K](https://github.com/Grub4K)
- **cleanup**
    - [Fix spelling of `IE_NAME`](https://github.com/yt-dlp/yt-dlp/commit/bc4ab17b38f01000d99c5c2bedec89721fee65ec) ([#8810](https://github.com/yt-dlp/yt-dlp/issues/8810)) by [barsnick](https://github.com/barsnick)
    - [Remove dead extractors](https://github.com/yt-dlp/yt-dlp/commit/9751a457cfdb18bf99d9ee0d10e4e6a594502bbf) ([#8604](https://github.com/yt-dlp/yt-dlp/issues/8604)) by [seproDev](https://github.com/seproDev)
    - Miscellaneous: [f9fb3ce](https://github.com/yt-dlp/yt-dlp/commit/f9fb3ce86e3c6a0c3c33b45392b8d7288bceba76) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan), [seproDev](https://github.com/seproDev)
- **devscripts**: `run_tests`: [Create Python script](https://github.com/yt-dlp/yt-dlp/commit/2d1d683a541d71f3d3bb999dfe8eeb1976fb91ce) ([#8720](https://github.com/yt-dlp/yt-dlp/issues/8720)) by [Grub4K](https://github.com/Grub4K) (With fixes in [225cf2b](https://github.com/yt-dlp/yt-dlp/commit/225cf2b830a1de2c5eacd257edd2a01aed1e1114))
- **docs**: [Update youtube-dl merge commit in `README.md`](https://github.com/yt-dlp/yt-dlp/commit/f10589e3453009bb523f55849bba144c9b91cf2a) by [bashonly](https://github.com/bashonly)
- **test**: networking: [Update tests for OpenSSL 3.2](https://github.com/yt-dlp/yt-dlp/commit/37755a037e612bfc608c3d4722e8ef2ce6a022ee) ([#8814](https://github.com/yt-dlp/yt-dlp/issues/8814)) by [bashonly](https://github.com/bashonly)

### 2023.11.16

#### Extractor changes
- **abc.net.au**: iview, showseries: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/15cb3528cbda7b6198f49a6b5953c226d701696b) ([#8586](https://github.com/yt-dlp/yt-dlp/issues/8586)) by [bashonly](https://github.com/bashonly)
- **beatbump**: [Update `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/21dc069bea2d4d99345dd969e098f4535c751d45) ([#8576](https://github.com/yt-dlp/yt-dlp/issues/8576)) by [seproDev](https://github.com/seproDev)
- **dailymotion**: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/a489f071508ec5caf5f32052d142afe86c28df7a) ([#7692](https://github.com/yt-dlp/yt-dlp/issues/7692)) by [TravisDupes](https://github.com/TravisDupes)
- **drtv**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/0783fd558ed0d3a8bc754beb75a406256f8b97b2) ([#8484](https://github.com/yt-dlp/yt-dlp/issues/8484)) by [almx](https://github.com/almx), [seproDev](https://github.com/seproDev)
- **eltrecetv**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/dcfad52812aa8ce007cefbfbe63f58b49f6b1046) ([#8216](https://github.com/yt-dlp/yt-dlp/issues/8216)) by [elivinsky](https://github.com/elivinsky)
- **jiosaavn**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/b530118e7f48232cacf8050d79a6b20bdfcf5468) ([#8307](https://github.com/yt-dlp/yt-dlp/issues/8307)) by [awalgarg](https://github.com/awalgarg)
- **njpwworld**: [Remove](https://github.com/yt-dlp/yt-dlp/commit/e569c2d1f4b665795a2b64f0aaf7f76930664233) ([#8570](https://github.com/yt-dlp/yt-dlp/issues/8570)) by [aarubui](https://github.com/aarubui)
- **tv5mondeplus**: [Extract subtitles](https://github.com/yt-dlp/yt-dlp/commit/0f634dba3afdc429ece8839b02f6d56c27b7973a) ([#4209](https://github.com/yt-dlp/yt-dlp/issues/4209)) by [FrankZ85](https://github.com/FrankZ85)
- **twitcasting**: [Fix livestream detection](https://github.com/yt-dlp/yt-dlp/commit/2325d03aa7bb80f56ba52cd6992258e44727b424) ([#8574](https://github.com/yt-dlp/yt-dlp/issues/8574)) by [JC-Chung](https://github.com/JC-Chung)
- **zenyandex**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/5efe68b73cbf6e907c2e6a3aa338664385084184) ([#8454](https://github.com/yt-dlp/yt-dlp/issues/8454)) by [starius](https://github.com/starius)

#### Misc. changes
- **build**: [Make `secretstorage` an optional dependency](https://github.com/yt-dlp/yt-dlp/commit/24f827875c6ba513f12ed09a3aef2bbed223760d) ([#8585](https://github.com/yt-dlp/yt-dlp/issues/8585)) by [bashonly](https://github.com/bashonly)

### 2023.11.14

#### Important changes
- **The release channels have been adjusted!**
    * [`master`](https://github.com/yt-dlp/yt-dlp-master-builds) builds are made after each push, containing the latest fixes (but also possibly bugs). This was previously the `nightly` channel.
    * [`nightly`](https://github.com/yt-dlp/yt-dlp-nightly-builds) builds are now made once a day, if there were any changes.
- Security: [[CVE-2023-46121](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-46121)] Patch [Generic Extractor MITM Vulnerability via Arbitrary Proxy Injection](https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-3ch3-jhc6-5r8x)
    - Disallow smuggling of arbitrary `http_headers`; extractors now only use specific headers

#### Core changes
- [Add `--compat-option manifest-filesize-approx`](https://github.com/yt-dlp/yt-dlp/commit/10025b715ea01489557eb2c5a3cc04d361fcdb52) ([#8356](https://github.com/yt-dlp/yt-dlp/issues/8356)) by [bashonly](https://github.com/bashonly)
- [Fix format sorting with `--load-info-json`](https://github.com/yt-dlp/yt-dlp/commit/595ea4a99b726b8fe9463e7853b7053978d0544e) ([#8521](https://github.com/yt-dlp/yt-dlp/issues/8521)) by [bashonly](https://github.com/bashonly)
- [Include build origin in verbose output](https://github.com/yt-dlp/yt-dlp/commit/20314dd46f25e0e0a7e985a7804049aefa8b909f) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
- [Only ensure playlist thumbnail dir if writing thumbs](https://github.com/yt-dlp/yt-dlp/commit/a40e0b37dfc8c26916b0e01aa3f29f3bc42250b6) ([#8373](https://github.com/yt-dlp/yt-dlp/issues/8373)) by [bashonly](https://github.com/bashonly)
- **update**: [Overhaul self-updater](https://github.com/yt-dlp/yt-dlp/commit/0b6ad22e6a432006a75df968f0283e6c6b3cfae6) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- [Do not smuggle `http_headers`](https://github.com/yt-dlp/yt-dlp/commit/f04b5bedad7b281bee9814686bba1762bae092eb) by [coletdjnz](https://github.com/coletdjnz)
- [Do not test truth value of `xml.etree.ElementTree.Element`](https://github.com/yt-dlp/yt-dlp/commit/d4f14a72dc1dd79396e0e80980268aee902b61e4) ([#8582](https://github.com/yt-dlp/yt-dlp/issues/8582)) by [bashonly](https://github.com/bashonly)
- **brilliantpala**: [Fix cookies support](https://github.com/yt-dlp/yt-dlp/commit/9b5bedf13a3323074daceb0ec6ebb3cc6e0b9684) ([#8352](https://github.com/yt-dlp/yt-dlp/issues/8352)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **generic**: [Improve direct video link ext detection](https://github.com/yt-dlp/yt-dlp/commit/4ce2f29a50fcfb9920e6f2ffe42192945a2bad7e) ([#8340](https://github.com/yt-dlp/yt-dlp/issues/8340)) by [bashonly](https://github.com/bashonly)
- **laxarxames**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/312a2d1e8bc247264f9d85c5ec764e33aa0133b5) ([#8412](https://github.com/yt-dlp/yt-dlp/issues/8412)) by [aniolpages](https://github.com/aniolpages)
- **n-tv.de**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/8afd9468b0c822843bc480d366d1c86698daabfb) ([#8414](https://github.com/yt-dlp/yt-dlp/issues/8414)) by [1100101](https://github.com/1100101)
- **neteasemusic**: [Improve metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/46acc418a53470b7f32581b3309c3cb87aa8488d) ([#8531](https://github.com/yt-dlp/yt-dlp/issues/8531)) by [LoserFox](https://github.com/LoserFox)
- **nhk**: [Improve metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/54579be4364e148277c32e20a5c3efc2c3f52f5b) ([#8388](https://github.com/yt-dlp/yt-dlp/issues/8388)) by [garret1317](https://github.com/garret1317)
- **novaembed**: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/3ff494f6f41c27549420fa88be27555bd449ffdc) ([#8368](https://github.com/yt-dlp/yt-dlp/issues/8368)) by [peci1](https://github.com/peci1)
- **npo**: [Send `POST` request to streams API endpoint](https://github.com/yt-dlp/yt-dlp/commit/8e02a4dcc800f9444e9d461edc41edd7b662f435) ([#8413](https://github.com/yt-dlp/yt-dlp/issues/8413)) by [bartbroere](https://github.com/bartbroere)
- **ondemandkorea**: [Overhaul extractor](https://github.com/yt-dlp/yt-dlp/commit/05adfd883a4f2ecae0267e670a62a2e45c351aeb) ([#8386](https://github.com/yt-dlp/yt-dlp/issues/8386)) by [seproDev](https://github.com/seproDev)
- **orf**: podcast: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/6ba3085616652cbf05d1858efc321fdbfc4c6119) ([#8486](https://github.com/yt-dlp/yt-dlp/issues/8486)) by [Esokrates](https://github.com/Esokrates)
- **polskieradio**: audition: [Fix playlist extraction](https://github.com/yt-dlp/yt-dlp/commit/464327acdb353ceb91d2115163a5a9621b22fe0d) ([#8459](https://github.com/yt-dlp/yt-dlp/issues/8459)) by [shubhexists](https://github.com/shubhexists)
- **qdance**: [Update `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/177f0d963e4b9db749805c482e6f288354c8be84) ([#8426](https://github.com/yt-dlp/yt-dlp/issues/8426)) by [bashonly](https://github.com/bashonly)
- **radiocomercial**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/ef12dbdcd3e7264bd3d744c1e3107597bd23ad35) ([#8508](https://github.com/yt-dlp/yt-dlp/issues/8508)) by [SirElderling](https://github.com/SirElderling)
- **sbs.co.kr**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/25a4bd345a0dcfece6fef752d4537eb403da94d9) ([#8326](https://github.com/yt-dlp/yt-dlp/issues/8326)) by [seproDev](https://github.com/seproDev)
- **theatercomplextown**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/2863fcf2b6876d0c7965ff7d6d9242eea653dc6b) ([#8560](https://github.com/yt-dlp/yt-dlp/issues/8560)) by [bashonly](https://github.com/bashonly)
- **thisav**: [Remove](https://github.com/yt-dlp/yt-dlp/commit/cb480e390d85fb3a598c1b6d5eef3438ce729fc9) ([#8346](https://github.com/yt-dlp/yt-dlp/issues/8346)) by [bashonly](https://github.com/bashonly)
- **thisoldhouse**: [Add login support](https://github.com/yt-dlp/yt-dlp/commit/c76c96677ff6a056f5844a568ef05ee22c46d6f4) ([#8561](https://github.com/yt-dlp/yt-dlp/issues/8561)) by [bashonly](https://github.com/bashonly)
- **twitcasting**: [Fix livestream extraction](https://github.com/yt-dlp/yt-dlp/commit/7b8b1cf5eb8bf44ce70bc24e1f56f0dba2737e98) ([#8427](https://github.com/yt-dlp/yt-dlp/issues/8427)) by [JC-Chung](https://github.com/JC-Chung), [saintliao](https://github.com/saintliao)
- **twitter**
    - broadcast
        - [Improve metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/7d337ca977d73a0a6c07ab481ed8faa8f6ff8726) ([#8383](https://github.com/yt-dlp/yt-dlp/issues/8383)) by [HitomaruKonpaku](https://github.com/HitomaruKonpaku)
        - [Support `--wait-for-video`](https://github.com/yt-dlp/yt-dlp/commit/f6e97090d2ed9e05441ab0f4bec3559b816d7a00) ([#8475](https://github.com/yt-dlp/yt-dlp/issues/8475)) by [bashonly](https://github.com/bashonly)
- **weibo**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/15b252dfd2c6807fe57afc5a95e59abadb32ccd2) ([#8463](https://github.com/yt-dlp/yt-dlp/issues/8463)) by [c-basalt](https://github.com/c-basalt)
- **weverse**: [Fix login error handling](https://github.com/yt-dlp/yt-dlp/commit/4a601c9eff9fb42e24a4c8da3fa03628e035b35b) ([#8458](https://github.com/yt-dlp/yt-dlp/issues/8458)) by [seproDev](https://github.com/seproDev)
- **youtube**: [Check newly uploaded iOS HLS formats](https://github.com/yt-dlp/yt-dlp/commit/ef79d20dc9d27ac002a7196f073b37f2f2721aed) ([#8336](https://github.com/yt-dlp/yt-dlp/issues/8336)) by [bashonly](https://github.com/bashonly)
- **zoom**: [Extract combined view formats](https://github.com/yt-dlp/yt-dlp/commit/3906de07551fedb00b789345bf24cc27d6ddf128) ([#7847](https://github.com/yt-dlp/yt-dlp/issues/7847)) by [Mipsters](https://github.com/Mipsters)

#### Downloader changes
- **aria2c**: [Remove duplicate `--file-allocation=none`](https://github.com/yt-dlp/yt-dlp/commit/21b25281c51523620706b11bfc1c4a889858e1f2) ([#8332](https://github.com/yt-dlp/yt-dlp/issues/8332)) by [CrendKing](https://github.com/CrendKing)
- **dash**: [Force native downloader for `--live-from-start`](https://github.com/yt-dlp/yt-dlp/commit/2622c804d1a5accc3045db398e0fc52074f4bdb3) ([#8339](https://github.com/yt-dlp/yt-dlp/issues/8339)) by [bashonly](https://github.com/bashonly)

#### Networking changes
- **Request Handler**: requests: [Add handler for `requests` HTTP library (#3668)](https://github.com/yt-dlp/yt-dlp/commit/8a8b54523addf46dfd50ef599761a81bc22362e6) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz), [Grub4K](https://github.com/Grub4K) (With fixes in [4e38e2a](https://github.com/yt-dlp/yt-dlp/commit/4e38e2ae9d7380015349e6aee59c78bb3938befd))

    Adds support for HTTPS proxies and persistent connections (keep-alive)

#### Misc. changes
- **build**
    - [Include secretstorage in Linux builds](https://github.com/yt-dlp/yt-dlp/commit/9970d74c8383432c6c8779aa47d3253dcf412b14) by [bashonly](https://github.com/bashonly)
    - [Overhaul and unify release workflow](https://github.com/yt-dlp/yt-dlp/commit/1d03633c5a1621b9f3a756f0a4f9dc61fab3aeaa) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
- **ci**
    - [Bump `actions/checkout` to v4](https://github.com/yt-dlp/yt-dlp/commit/5438593a35b7b042fc48fe29cad0b9039f07c9bb) by [bashonly](https://github.com/bashonly)
    - [Run core tests with dependencies](https://github.com/yt-dlp/yt-dlp/commit/700444c23ddb65f618c2abd942acdc0c58c650b1) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz)
- **cleanup**
    - [Fix changelog typo](https://github.com/yt-dlp/yt-dlp/commit/a9d3f4b20a3533d2a40104c85bc2cc6c2564c800) by [bashonly](https://github.com/bashonly)
    - [Update documentation for master and nightly channels](https://github.com/yt-dlp/yt-dlp/commit/a00af29853b8c7350ce086f4cab8c2c9cf2fcf1d) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
    - Miscellaneous: [b012271](https://github.com/yt-dlp/yt-dlp/commit/b012271d01b59759e4eefeab0308698cd9e7224c) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz), [dirkf](https://github.com/dirkf), [gamer191](https://github.com/gamer191), [Grub4K](https://github.com/Grub4K), [seproDev](https://github.com/seproDev)
- **test**: update: [Implement simple updater unit tests](https://github.com/yt-dlp/yt-dlp/commit/87264d4fdadcddd91289b968dd0e4bf58d449267) by [bashonly](https://github.com/bashonly)

### 2023.10.13

#### Core changes
- [Ensure thumbnail output directory exists](https://github.com/yt-dlp/yt-dlp/commit/2acd1d555ef89851c73773776715d3de9a0e30b9) ([#7985](https://github.com/yt-dlp/yt-dlp/issues/7985)) by [Riteo](https://github.com/Riteo)
- **utils**
    - `js_to_json`: [Fix `Date` constructor parsing](https://github.com/yt-dlp/yt-dlp/commit/9d7ded6419089c1bf252496073f73ad90ed71004) ([#8295](https://github.com/yt-dlp/yt-dlp/issues/8295)) by [awalgarg](https://github.com/awalgarg), [Grub4K](https://github.com/Grub4K)
    - `write_xattr`: [Use `os.setxattr` if available](https://github.com/yt-dlp/yt-dlp/commit/84e26038d4002e763ea51ca1bdce4f7e63c540bf) ([#8205](https://github.com/yt-dlp/yt-dlp/issues/8205)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- **artetv**: [Support age-restricted content](https://github.com/yt-dlp/yt-dlp/commit/09f815ad52843219a7ee3f2a0dddf6c250c91f0c) ([#8301](https://github.com/yt-dlp/yt-dlp/issues/8301)) by [StefanLobbenmeier](https://github.com/StefanLobbenmeier)
- **jtbc**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/b286ec68f1f28798b3e371f888a2ed97d399cf77) ([#8314](https://github.com/yt-dlp/yt-dlp/issues/8314)) by [seproDev](https://github.com/seproDev)
- **mbn**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/e030b6b6fba7b2f4614ad2ab9f7649d40a2dd305) ([#8312](https://github.com/yt-dlp/yt-dlp/issues/8312)) by [seproDev](https://github.com/seproDev)
- **nhk**: [Fix Japanese-language VOD extraction](https://github.com/yt-dlp/yt-dlp/commit/4de94b9e165bfd6421a692f5f2eabcdb08edcb71) ([#8309](https://github.com/yt-dlp/yt-dlp/issues/8309)) by [garret1317](https://github.com/garret1317)
- **radiko**: [Fix bug with `downloader_options`](https://github.com/yt-dlp/yt-dlp/commit/b9316642313bbc9e209ac0d2276d37ba60bceb49) by [bashonly](https://github.com/bashonly)
- **tenplay**: [Add support for seasons](https://github.com/yt-dlp/yt-dlp/commit/88a99c87b680ae59002534a517e191f46c42cbd4) ([#7939](https://github.com/yt-dlp/yt-dlp/issues/7939)) by [midnightveil](https://github.com/midnightveil)
- **youku**: [Improve tudou.com support](https://github.com/yt-dlp/yt-dlp/commit/b7098d46b552a9322c6cea39ba80be5229f922de) ([#8160](https://github.com/yt-dlp/yt-dlp/issues/8160)) by [naginatana](https://github.com/naginatana)
- **youtube**: [Fix bug with `--extractor-retries inf`](https://github.com/yt-dlp/yt-dlp/commit/feebf6d02fc9651331eee2af5e08e6112288163b) ([#8328](https://github.com/yt-dlp/yt-dlp/issues/8328)) by [Grub4K](https://github.com/Grub4K)

#### Downloader changes
- **fragment**: [Improve progress calculation](https://github.com/yt-dlp/yt-dlp/commit/1c51c520f7b511ebd9e4eb7322285a8c31eedbbd) ([#8241](https://github.com/yt-dlp/yt-dlp/issues/8241)) by [Grub4K](https://github.com/Grub4K)

#### Misc. changes
- **cleanup**: Miscellaneous: [b634ba7](https://github.com/yt-dlp/yt-dlp/commit/b634ba742d8f38ce9ecfa0546485728b0c6c59d1) by [bashonly](https://github.com/bashonly), [gamer191](https://github.com/gamer191)

### 2023.10.07

#### Extractor changes
- **abc.net.au**: iview: [Improve `episode` extraction](https://github.com/yt-dlp/yt-dlp/commit/a9efb4b8d74f3583450ffda0ee57259a47d39c70) ([#8201](https://github.com/yt-dlp/yt-dlp/issues/8201)) by [xofe](https://github.com/xofe)
- **erocast**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/47c598783c98c179e04dd12c2a3fee0f3dc53087) ([#8264](https://github.com/yt-dlp/yt-dlp/issues/8264)) by [madewokherd](https://github.com/madewokherd)
- **gofile**: [Fix token cookie bug](https://github.com/yt-dlp/yt-dlp/commit/0730d5a966fa8a937d84bfb7f68be5198acb039b) by [bashonly](https://github.com/bashonly)
- **iq.com**: [Fix extraction and subtitles](https://github.com/yt-dlp/yt-dlp/commit/35d9cbaf9638ccc9daf8a863063b2e7c135bc664) ([#8260](https://github.com/yt-dlp/yt-dlp/issues/8260)) by [AS6939](https://github.com/AS6939)
- **lbry**
    - [Add playlist support](https://github.com/yt-dlp/yt-dlp/commit/48cceec1ddb8649b5e771df8df79eb9c39c82b90) ([#8213](https://github.com/yt-dlp/yt-dlp/issues/8213)) by [bashonly](https://github.com/bashonly), [drzraf](https://github.com/drzraf), [Grub4K](https://github.com/Grub4K)
    - [Extract `uploader_id`](https://github.com/yt-dlp/yt-dlp/commit/0e722f2f3ca42e634fd7b06ee70b16bf833ce132) ([#8244](https://github.com/yt-dlp/yt-dlp/issues/8244)) by [drzraf](https://github.com/drzraf)
- **litv**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/91a670a4f7babe9c8aa2018f57d8c8952a6f49d8) ([#7785](https://github.com/yt-dlp/yt-dlp/issues/7785)) by [jiru](https://github.com/jiru)
- **neteasemusic**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/f980df734cf5c0eaded2f7b38c6c60bccfeebb48) ([#8181](https://github.com/yt-dlp/yt-dlp/issues/8181)) by [c-basalt](https://github.com/c-basalt)
- **nhk**: [Fix VOD extraction](https://github.com/yt-dlp/yt-dlp/commit/e831c80e8b2fc025b3b67d82974cc59e3526fdc8) ([#8249](https://github.com/yt-dlp/yt-dlp/issues/8249)) by [garret1317](https://github.com/garret1317)
- **radiko**: [Improve extraction](https://github.com/yt-dlp/yt-dlp/commit/2ad3873f0dfa9285c91d2160e36c039e69d597c7) ([#8221](https://github.com/yt-dlp/yt-dlp/issues/8221)) by [garret1317](https://github.com/garret1317)
- **substack**
    - [Fix download cookies bug](https://github.com/yt-dlp/yt-dlp/commit/2f2dda3a7e85148773da3cdbc03ac9949ec1bc45) ([#8219](https://github.com/yt-dlp/yt-dlp/issues/8219)) by [handlerug](https://github.com/handlerug)
    - [Fix embed extraction](https://github.com/yt-dlp/yt-dlp/commit/fbcc299bd8a19cf8b3c8805d6c268a9110230973) ([#8218](https://github.com/yt-dlp/yt-dlp/issues/8218)) by [handlerug](https://github.com/handlerug)
- **theta**: [Remove extractors](https://github.com/yt-dlp/yt-dlp/commit/792f1e64f6a2beac51e85408d142b3118115c4fd) ([#8251](https://github.com/yt-dlp/yt-dlp/issues/8251)) by [alerikaisattera](https://github.com/alerikaisattera)
- **wrestleuniversevod**: [Call API with device ID](https://github.com/yt-dlp/yt-dlp/commit/b095fd3fa9d58a65dc9b830bd63b9d909422aa86) ([#8272](https://github.com/yt-dlp/yt-dlp/issues/8272)) by [bashonly](https://github.com/bashonly)
- **xhamster**: user: [Support creator urls](https://github.com/yt-dlp/yt-dlp/commit/cc8d8441524ec3442d7c0d3f8f33f15b66aa06f3) ([#8232](https://github.com/yt-dlp/yt-dlp/issues/8232)) by [Grub4K](https://github.com/Grub4K)
- **youtube**
    - [Fix `heatmap` extraction](https://github.com/yt-dlp/yt-dlp/commit/03e85ea99db76a2fddb65bf46f8819bda780aaf3) ([#8299](https://github.com/yt-dlp/yt-dlp/issues/8299)) by [bashonly](https://github.com/bashonly)
    - [Raise a warning for `Incomplete Data` instead of an error](https://github.com/yt-dlp/yt-dlp/commit/eb5bdbfa70126c7d5355cc0954b63720522e462c) ([#8238](https://github.com/yt-dlp/yt-dlp/issues/8238)) by [coletdjnz](https://github.com/coletdjnz)

#### Misc. changes
- **cleanup**
    - [Update extractor tests](https://github.com/yt-dlp/yt-dlp/commit/19c90e405b4137c06dfe6f9aaa02396df0da93e5) ([#7718](https://github.com/yt-dlp/yt-dlp/issues/7718)) by [trainman261](https://github.com/trainman261)
    - Miscellaneous: [377e85a](https://github.com/yt-dlp/yt-dlp/commit/377e85a1797db9e98b78b38203ed9d4ded229991) by [dirkf](https://github.com/dirkf), [gamer191](https://github.com/gamer191), [Grub4K](https://github.com/Grub4K)

### 2023.09.24

#### Important changes
- **The minimum *recommended* Python version has been raised to 3.8**
Since Python 3.7 has reached end-of-life, support for it will be dropped soon. [Read more](https://github.com/yt-dlp/yt-dlp/issues/7803)
- Security: [[CVE-2023-40581](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-40581)] [Prevent RCE when using `--exec` with `%q` on Windows](https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-42h4-v29r-42qg)
    - The shell escape function is now using `""` instead of `\"`.
    - `utils.Popen` has been patched to properly quote commands.

#### Core changes
- [Fix HTTP headers and cookie handling](https://github.com/yt-dlp/yt-dlp/commit/6c5211cebeacfc53ad5d5ddf4a659be76039656f) by [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan)
- [Fix `--check-formats`](https://github.com/yt-dlp/yt-dlp/commit/8cb7fc44db010e965d808ee679ef0725cb6e147c) by [pukkandan](https://github.com/pukkandan)
- [Fix support for upcoming Python 3.12](https://github.com/yt-dlp/yt-dlp/commit/836e06d246512f286f30c1371b2c54b72c9ecd93) ([#8130](https://github.com/yt-dlp/yt-dlp/issues/8130)) by [Grub4K](https://github.com/Grub4K)
- [Merged with youtube-dl 66ab08](https://github.com/yt-dlp/yt-dlp/commit/9d6254069c75877bc88bc3584f4326fb1853a543) by [coletdjnz](https://github.com/coletdjnz)
- [Prevent RCE when using `--exec` with `%q` (CVE-2023-40581)](https://github.com/yt-dlp/yt-dlp/commit/de015e930747165dbb8fcd360f8775fd973b7d6e) by [Grub4K](https://github.com/Grub4K)
- [Raise minimum recommended Python version to 3.8](https://github.com/yt-dlp/yt-dlp/commit/61bdf15fc7400601c3da1aa7a43917310a5bf391) ([#8183](https://github.com/yt-dlp/yt-dlp/issues/8183)) by [Grub4K](https://github.com/Grub4K)
- [`FFmpegFixupM3u8PP` may need to run with ffmpeg](https://github.com/yt-dlp/yt-dlp/commit/f73c11803579889dc8e1c99e25dba9a22fef39d8) by [pukkandan](https://github.com/pukkandan)
- **compat**
    - [Add `types.NoneType`](https://github.com/yt-dlp/yt-dlp/commit/e0c4db04dc82a699bdabd9821ddc239ebe17d30a) by [pukkandan](https://github.com/pukkandan) (With fixes in [25b6e8f](https://github.com/yt-dlp/yt-dlp/commit/25b6e8f94679b4458550702b46e61249b875a4fd))
    - [Deprecate old functions](https://github.com/yt-dlp/yt-dlp/commit/3d2623a898196640f7cc0fc8b70118ff19e6925d) ([#2861](https://github.com/yt-dlp/yt-dlp/issues/2861)) by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
    - [Ensure submodules are imported correctly](https://github.com/yt-dlp/yt-dlp/commit/a250b247334ce9f641e709cbb64974da6034a2b3) by [pukkandan](https://github.com/pukkandan)
- **cookies**: [Containers JSON should be opened as utf-8](https://github.com/yt-dlp/yt-dlp/commit/dab87ca23650fd87184ff5286b53e6985b59f71d) ([#7800](https://github.com/yt-dlp/yt-dlp/issues/7800)) by [bashonly](https://github.com/bashonly)
- **dependencies**: [Handle deprecation of `sqlite3.version`](https://github.com/yt-dlp/yt-dlp/commit/35f9a306e6934793cff100200cd03f288ec33f11) ([#8167](https://github.com/yt-dlp/yt-dlp/issues/8167)) by [bashonly](https://github.com/bashonly)
- **outtmpl**: [Fix replacement for `playlist_index`](https://github.com/yt-dlp/yt-dlp/commit/a264433c9fba147ecae2420091614186cfeeb895) by [pukkandan](https://github.com/pukkandan)
- **utils**
    - [Add temporary shim for logging](https://github.com/yt-dlp/yt-dlp/commit/1b392f905d20ef1f1b300b180f867d43c9ce49b8) by [pukkandan](https://github.com/pukkandan)
    - [Improve `parse_duration`](https://github.com/yt-dlp/yt-dlp/commit/af86873218c24c3859ccf575a87f2b00a73b49d0) by [bashonly](https://github.com/bashonly)
    - HTTPHeaderDict: [Handle byte values](https://github.com/yt-dlp/yt-dlp/commit/3f7965105d8d2048359e67c1e8b8ebd51588143b) by [pukkandan](https://github.com/pukkandan)
    - `clean_podcast_url`: [Handle more trackers](https://github.com/yt-dlp/yt-dlp/commit/2af4eeb77246b8183aae75a0a8d19f18c08115b2) ([#7556](https://github.com/yt-dlp/yt-dlp/issues/7556)) by [bashonly](https://github.com/bashonly), [mabdelfattah](https://github.com/mabdelfattah)
    - `js_to_json`: [Handle `Array` objects](https://github.com/yt-dlp/yt-dlp/commit/52414d64ca7b92d3f83964cdd68247989b0c4625) by [Grub4K](https://github.com/Grub4K), [std-move](https://github.com/std-move)

#### Extractor changes
- [Extract subtitles from SMIL manifests](https://github.com/yt-dlp/yt-dlp/commit/550e65410a7a1b105923494ac44460a4dc1a15d9) ([#7667](https://github.com/yt-dlp/yt-dlp/issues/7667)) by [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan)
- [Fix `--load-pages`](https://github.com/yt-dlp/yt-dlp/commit/81b4712bca608b9015aa68a4d96661d56e9cb894) by [pukkandan](https://github.com/pukkandan)
- [Make `_search_nuxt_data` more lenient](https://github.com/yt-dlp/yt-dlp/commit/904a19ee93195ce0bd4b08bd22b186120afb5b17) by [std-move](https://github.com/std-move)
- **abematv**
    - [Fix proxy handling](https://github.com/yt-dlp/yt-dlp/commit/497bbbbd7328cb705f70eced94dbd90993819a46) ([#8046](https://github.com/yt-dlp/yt-dlp/issues/8046)) by [SevenLives](https://github.com/SevenLives)
    - [Temporary fix for protocol handler](https://github.com/yt-dlp/yt-dlp/commit/9f66247289b9f8ecf931833b3f5f127274dd2161) by [pukkandan](https://github.com/pukkandan)
- **amazonminitv**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/538d37671a17e0782d17f08df17800e2e3bd57c8) by [bashonly](https://github.com/bashonly), [GautamMKGarg](https://github.com/GautamMKGarg)
- **antenna**: [Support antenna.gr](https://github.com/yt-dlp/yt-dlp/commit/665876034c8d3c031443f6b4958bed02ccdf4164) ([#7584](https://github.com/yt-dlp/yt-dlp/issues/7584)) by [stdedos](https://github.com/stdedos)
- **artetv**: [Fix HLS formats extraction](https://github.com/yt-dlp/yt-dlp/commit/c2da0b5ea215298135f76e3dc14b972a3c4afacb) by [bashonly](https://github.com/bashonly)
- **axs**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/aee6b9b88c0bcccf27fd23b7e00fc0b7b168928f) ([#8094](https://github.com/yt-dlp/yt-dlp/issues/8094)) by [barsnick](https://github.com/barsnick)
- **banbye**: [Support video ids containing a hyphen](https://github.com/yt-dlp/yt-dlp/commit/578a82e497502b951036ce9da6fe0dac6937ac27) ([#8059](https://github.com/yt-dlp/yt-dlp/issues/8059)) by [kshitiz305](https://github.com/kshitiz305)
- **bbc**: [Extract tracklist as chapters](https://github.com/yt-dlp/yt-dlp/commit/eda0e415d26eb084e570cf5372d38ee1f616b70f) ([#7788](https://github.com/yt-dlp/yt-dlp/issues/7788)) by [garret1317](https://github.com/garret1317)
- **bild.de**: [Extract HLS formats](https://github.com/yt-dlp/yt-dlp/commit/b4c1c408c63724339eb12b16c91b253a7ee62cfa) ([#8032](https://github.com/yt-dlp/yt-dlp/issues/8032)) by [barsnick](https://github.com/barsnick)
- **bilibili**
    - [Add support for series, favorites and watch later](https://github.com/yt-dlp/yt-dlp/commit/9e68747f9607f05e92bb7d9b6e79d678b50070e1) ([#7518](https://github.com/yt-dlp/yt-dlp/issues/7518)) by [c-basalt](https://github.com/c-basalt)
    - [Extract Dolby audio formats](https://github.com/yt-dlp/yt-dlp/commit/b84fda7388dd20d38921e23b469147f3957c1812) ([#8142](https://github.com/yt-dlp/yt-dlp/issues/8142)) by [ClosedPort22](https://github.com/ClosedPort22)
    - [Extract `format_id`](https://github.com/yt-dlp/yt-dlp/commit/5336bf57a7061e0955a37f0542fc8ebf50d55b17) ([#7555](https://github.com/yt-dlp/yt-dlp/issues/7555)) by [c-basalt](https://github.com/c-basalt)
- **bilibilibangumi**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/bdd0b75e3f41ff35440eda6d395008beef19ef2f) ([#7337](https://github.com/yt-dlp/yt-dlp/issues/7337)) by [GD-Slime](https://github.com/GD-Slime)
- **bpb**: [Overhaul extractor](https://github.com/yt-dlp/yt-dlp/commit/f659e6439444ac64305b5c80688cd82f59d2279c) ([#8119](https://github.com/yt-dlp/yt-dlp/issues/8119)) by [Grub4K](https://github.com/Grub4K)
- **brilliantpala**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/92feb5654c5a4c81ba872904a618700fcbb3e546) ([#6680](https://github.com/yt-dlp/yt-dlp/issues/6680)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **canal1, caracoltvplay**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/b3febedbeb662dfdf9b5c1d5799039ad4fc969de) ([#7151](https://github.com/yt-dlp/yt-dlp/issues/7151)) by [elyse0](https://github.com/elyse0)
- **cbc**: [Ignore any 426 from API](https://github.com/yt-dlp/yt-dlp/commit/9bf14be775289bd88cc1f5c89fd761ae51879484) ([#7689](https://github.com/yt-dlp/yt-dlp/issues/7689)) by [makew0rld](https://github.com/makew0rld)
- **cbcplayer**: [Extract HLS formats and subtitles](https://github.com/yt-dlp/yt-dlp/commit/339c339fec095ff4141b20e6aa83629117fb26df) ([#7484](https://github.com/yt-dlp/yt-dlp/issues/7484)) by [trainman261](https://github.com/trainman261)
- **cbcplayerplaylist**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/ed711897814f3ee0b1822e4205e74133467e8f1c) ([#7870](https://github.com/yt-dlp/yt-dlp/issues/7870)) by [trainman261](https://github.com/trainman261)
- **cineverse**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/15591940ff102d1ae337d603a46d8f238c83a61f) ([#8146](https://github.com/yt-dlp/yt-dlp/issues/8146)) by [garret1317](https://github.com/garret1317)
- **crunchyroll**: [Remove initial state extraction](https://github.com/yt-dlp/yt-dlp/commit/9b16762f48914de9ac914601769c76668e433325) ([#7632](https://github.com/yt-dlp/yt-dlp/issues/7632)) by [Grub4K](https://github.com/Grub4K)
- **douyutv**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/21f40e75dfc0055ea9cdbd7fe2c46c6f9b561afd) ([#7652](https://github.com/yt-dlp/yt-dlp/issues/7652)) by [c-basalt](https://github.com/c-basalt)
- **dropbox**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/b9f2bc2dbed2323734a0d18e65e1e2e23dc833d8) ([#7926](https://github.com/yt-dlp/yt-dlp/issues/7926)) by [bashonly](https://github.com/bashonly), [denhotte](https://github.com/denhotte), [nathantouze](https://github.com/nathantouze) (With fixes in [099fb1b](https://github.com/yt-dlp/yt-dlp/commit/099fb1b35cf835303306549f5113d1802d79c9c7) by [bashonly](https://github.com/bashonly))
- **eplus**: inbound: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/295fbb3ae3a7d0dd50e286be5c487cf145ed5778) ([#5782](https://github.com/yt-dlp/yt-dlp/issues/5782)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **expressen**: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/a5e264d74b4bd60c6e7ec4e38f1a23af4e420531) ([#8153](https://github.com/yt-dlp/yt-dlp/issues/8153)) by [kylegustavo](https://github.com/kylegustavo)
- **facebook**
    - [Add dash manifest URL](https://github.com/yt-dlp/yt-dlp/commit/a854fbec56d5004f5147116a41d1dd050632a579) ([#7743](https://github.com/yt-dlp/yt-dlp/issues/7743)) by [ringus1](https://github.com/ringus1)
    - [Fix webpage extraction](https://github.com/yt-dlp/yt-dlp/commit/d3d81cc98f554d0adb87d24bfd6fabaaa803944d) ([#7890](https://github.com/yt-dlp/yt-dlp/issues/7890)) by [ringus1](https://github.com/ringus1)
    - [Improve format sorting](https://github.com/yt-dlp/yt-dlp/commit/308936619c8a4f3a52d73c829c2006ff6c55fea2) ([#8074](https://github.com/yt-dlp/yt-dlp/issues/8074)) by [fireattack](https://github.com/fireattack)
    - reel: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/bb5d84c9d2f1e978c3eddfb5ccbe138036682a36) ([#7564](https://github.com/yt-dlp/yt-dlp/issues/7564)) by [bashonly](https://github.com/bashonly), [demon071](https://github.com/demon071)
- **fox**: [Support foxsports.com](https://github.com/yt-dlp/yt-dlp/commit/30b29f37159e9226e2f2d5434c9a4096ac4efa2e) ([#7724](https://github.com/yt-dlp/yt-dlp/issues/7724)) by [ischmidt20](https://github.com/ischmidt20)
- **funker530**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/0ce1f48bf1cb78d40d734ce73ee1c90eccf92274) ([#8040](https://github.com/yt-dlp/yt-dlp/issues/8040)) by [04-pasha-04](https://github.com/04-pasha-04)
- **generic**
    - [Fix KVS thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/53675852195d8dd859555d4789944a6887171ff8) by [bashonly](https://github.com/bashonly)
    - [Fix generic title for embeds](https://github.com/yt-dlp/yt-dlp/commit/994f7ef8e6003f4b7b258528755d0b6adcc31714) by [pukkandan](https://github.com/pukkandan)
- **gofile**: [Update token](https://github.com/yt-dlp/yt-dlp/commit/99c99c7185f5d8e9b3699a6fc7f86ec663d7b97e) by [bashonly](https://github.com/bashonly)
- **hotstar**
    - [Extract `release_year`](https://github.com/yt-dlp/yt-dlp/commit/7237c8dca0590aa7438ade93f927df88c9381ec7) ([#7869](https://github.com/yt-dlp/yt-dlp/issues/7869)) by [Rajeshwaran2001](https://github.com/Rajeshwaran2001)
    - [Make metadata extraction non-fatal](https://github.com/yt-dlp/yt-dlp/commit/30ea88591b728cca0896018dbf67c2298070c669) by [bashonly](https://github.com/bashonly)
    - [Support `/clips/` URLs](https://github.com/yt-dlp/yt-dlp/commit/86eeb044c2342d68c6ef177577f87852e6badd85) ([#7710](https://github.com/yt-dlp/yt-dlp/issues/7710)) by [bashonly](https://github.com/bashonly)
- **hungama**: [Overhaul extractors](https://github.com/yt-dlp/yt-dlp/commit/4b3a6ef1b3e235ba9a45142830b6edb357c71696) ([#7757](https://github.com/yt-dlp/yt-dlp/issues/7757)) by [bashonly](https://github.com/bashonly), [Yalab7](https://github.com/Yalab7)
- **indavideoembed**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/63e0c5748c0eb461a2ccca4181616eb930b4b750) ([#8129](https://github.com/yt-dlp/yt-dlp/issues/8129)) by [aky-01](https://github.com/aky-01)
- **iprima**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/568f08051841aedea968258889539741e26009e9) ([#7216](https://github.com/yt-dlp/yt-dlp/issues/7216)) by [std-move](https://github.com/std-move)
- **lbry**: [Fix original format extraction](https://github.com/yt-dlp/yt-dlp/commit/127a22460658ac39cbe5c4b3fb88d578363e0dfa) ([#7711](https://github.com/yt-dlp/yt-dlp/issues/7711)) by [bashonly](https://github.com/bashonly)
- **lecturio**: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/efa2339502a37cf13ae7f143bd8b2c28f452d1cd) ([#7649](https://github.com/yt-dlp/yt-dlp/issues/7649)) by [simon300000](https://github.com/simon300000)
- **magellantv**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/f4ea501551526ebcb54d19b84cf0ebe798583a85) ([#7616](https://github.com/yt-dlp/yt-dlp/issues/7616)) by [bashonly](https://github.com/bashonly)
- **massengeschmack.tv**: [Fix title extraction](https://github.com/yt-dlp/yt-dlp/commit/81f46ac573dc443ad48560f308582a26784d3015) ([#7813](https://github.com/yt-dlp/yt-dlp/issues/7813)) by [sb0stn](https://github.com/sb0stn)
- **media.ccc.de**: lists: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/cf11b40ac40e3d23a6352753296f3a732886efb9) ([#8144](https://github.com/yt-dlp/yt-dlp/issues/8144)) by [Rohxn16](https://github.com/Rohxn16)
- **mediaite**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/630a55df8de7747e79aa680959d785dfff2c4b76) ([#7923](https://github.com/yt-dlp/yt-dlp/issues/7923)) by [Grabien](https://github.com/Grabien)
- **mediaklikk**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/6e07e4bc7e59f5bdb60e93c011e57b18b009f2b5) ([#8086](https://github.com/yt-dlp/yt-dlp/issues/8086)) by [bashonly](https://github.com/bashonly), [zhallgato](https://github.com/zhallgato)
- **mediastream**: [Make embed extraction non-fatal](https://github.com/yt-dlp/yt-dlp/commit/635ae31f68a3ac7f6393d59657ed711e34ee3552) by [bashonly](https://github.com/bashonly)
- **mixcloud**: [Update API URL](https://github.com/yt-dlp/yt-dlp/commit/7b71643cc986de9a3768dac4ac9b64f4d05e7f5e) ([#8114](https://github.com/yt-dlp/yt-dlp/issues/8114)) by [garret1317](https://github.com/garret1317)
- **monstercat**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/eaee21bf71889d495076037cbe590c8c0b21ef3a) ([#8133](https://github.com/yt-dlp/yt-dlp/issues/8133)) by [garret1317](https://github.com/garret1317)
- **motortrendondemand**: [Update `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/c03a58ec9933e4a42c2d8fa80b8a0ddb2cde64e6) ([#7683](https://github.com/yt-dlp/yt-dlp/issues/7683)) by [AmirAflak](https://github.com/AmirAflak)
- **museai**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/65cfa2b057d7946fbe322155a778fe206556d0c6) ([#7614](https://github.com/yt-dlp/yt-dlp/issues/7614)) by [bashonly](https://github.com/bashonly)
- **mzaalo**: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/d7aee8e310b2c4f21d50aac0b420e1b3abde21a4) by [bashonly](https://github.com/bashonly)
- **n1info**: article: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/8ac5b6d96ae5c60cd5ae2495949e0068a6754c45) ([#7373](https://github.com/yt-dlp/yt-dlp/issues/7373)) by [u-spec-png](https://github.com/u-spec-png)
- **nfl.com**: plus, replay: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/1eaca74bc2ca0f5b1ec532f24c61de44f2e8cb2d) ([#7838](https://github.com/yt-dlp/yt-dlp/issues/7838)) by [bashonly](https://github.com/bashonly)
- **niconicochannelplus**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/698beb9a497f51693e64d167e572ff9efa4bc25f) ([#5686](https://github.com/yt-dlp/yt-dlp/issues/5686)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **nitter**: [Fix title extraction fallback](https://github.com/yt-dlp/yt-dlp/commit/a83da3717d30697102e76f63a6f29d77f9373c2a) ([#8102](https://github.com/yt-dlp/yt-dlp/issues/8102)) by [ApoorvShah111](https://github.com/ApoorvShah111)
- **noodlemagazine**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/bae4834245a708fff97219849ec880c319c88bc6) ([#7830](https://github.com/yt-dlp/yt-dlp/issues/7830)) by [RedDeffender](https://github.com/RedDeffender) (With fixes in [69dbfe0](https://github.com/yt-dlp/yt-dlp/commit/69dbfe01c47cd078682a87f179f5846e2679e927) by [bashonly](https://github.com/bashonly))
- **novaembed**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/2269065ad60cb0ab62408ae6a7b20283e5252232) ([#7910](https://github.com/yt-dlp/yt-dlp/issues/7910)) by [std-move](https://github.com/std-move)
- **patreoncampaign**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/11de6fec9c9b8d34d1f90c8e6218ec58a3471b58) ([#7664](https://github.com/yt-dlp/yt-dlp/issues/7664)) by [bashonly](https://github.com/bashonly)
- **pbs**: [Add extractor `PBSKidsIE`](https://github.com/yt-dlp/yt-dlp/commit/6d6081dda1290a85bdab6717f239289e3aa74c8e) ([#7602](https://github.com/yt-dlp/yt-dlp/issues/7602)) by [snixon](https://github.com/snixon)
- **piapro**: [Support `/content` URL](https://github.com/yt-dlp/yt-dlp/commit/1bcb9fe8715b1f288efc322be3de409ee0597080) ([#7592](https://github.com/yt-dlp/yt-dlp/issues/7592)) by [FinnRG](https://github.com/FinnRG)
- **piaulizaportal**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/6636021206dad17c7745ae6bce6cb73d6f2ef319) ([#7903](https://github.com/yt-dlp/yt-dlp/issues/7903)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **picartovod**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/db9743894071760f994f640a4c24358f749a78c0) ([#7727](https://github.com/yt-dlp/yt-dlp/issues/7727)) by [Frankgoji](https://github.com/Frankgoji)
- **pornbox**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/40999467f72db074a3f13057da9bf82a857530fe) ([#7386](https://github.com/yt-dlp/yt-dlp/issues/7386)) by [niemands](https://github.com/niemands)
- **pornhub**: [Update access cookies for UK](https://github.com/yt-dlp/yt-dlp/commit/1d3d579c2142f69831b6ae140e1d8e824e07fa0e) ([#7591](https://github.com/yt-dlp/yt-dlp/issues/7591)) by [zhong-yiyu](https://github.com/zhong-yiyu)
- **pr0gramm**: [Rewrite extractor](https://github.com/yt-dlp/yt-dlp/commit/b532556d0a85e7d76f8f0880861232fb706ddbc5) ([#8151](https://github.com/yt-dlp/yt-dlp/issues/8151)) by [Grub4K](https://github.com/Grub4K)
- **radiofrance**: [Add support for livestreams, podcasts, playlists](https://github.com/yt-dlp/yt-dlp/commit/ba8e9eb2c8bbb699f314169fab8e544437ad731e) ([#7006](https://github.com/yt-dlp/yt-dlp/issues/7006)) by [elyse0](https://github.com/elyse0)
- **rbgtum**: [Fix extraction and support new URL format](https://github.com/yt-dlp/yt-dlp/commit/5fccabac27ca3c1165ade1b0df6fbadc24258dc2) ([#7690](https://github.com/yt-dlp/yt-dlp/issues/7690)) by [simon300000](https://github.com/simon300000)
- **reddit**
    - [Extract subtitles](https://github.com/yt-dlp/yt-dlp/commit/20c3c9b433dd47faf0dbde6b46e4e34eb76109a5) by [bashonly](https://github.com/bashonly)
    - [Fix thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/9a04113dfbb69b904e4e2bea736da293505786b8) by [bashonly](https://github.com/bashonly)
- **rtvslo**: [Fix format extraction](https://github.com/yt-dlp/yt-dlp/commit/94389b225d9bcf29aa7ba8afaf1bbd7c62204eae) ([#8131](https://github.com/yt-dlp/yt-dlp/issues/8131)) by [bashonly](https://github.com/bashonly)
- **rule34video**: [Extract tags](https://github.com/yt-dlp/yt-dlp/commit/58493923e9b6f774947a2131e5258e9f3cf816be) ([#7117](https://github.com/yt-dlp/yt-dlp/issues/7117)) by [soundchaser128](https://github.com/soundchaser128)
- **rumble**: [Fix embed extraction](https://github.com/yt-dlp/yt-dlp/commit/23d829a3420450bcfb0788e6fb2cf4f6acdbe596) ([#8035](https://github.com/yt-dlp/yt-dlp/issues/8035)) by [trislee](https://github.com/trislee)
- **s4c**
    - [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/b9de629d78ce31699f2de886071dc257830f9676) ([#7730](https://github.com/yt-dlp/yt-dlp/issues/7730)) by [ifan-t](https://github.com/ifan-t)
    - [Add series support and extract subs/thumbs](https://github.com/yt-dlp/yt-dlp/commit/fe371dcf0ba5ce8d42480eade54eeeac99ab3cb0) ([#7776](https://github.com/yt-dlp/yt-dlp/issues/7776)) by [ifan-t](https://github.com/ifan-t)
- **sohu**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/5be7e978867b5f66ad6786c674d79d40e950ae16) ([#7628](https://github.com/yt-dlp/yt-dlp/issues/7628)) by [bashonly](https://github.com/bashonly), [c-basalt](https://github.com/c-basalt)
- **stageplus**: [Fix m3u8 extraction](https://github.com/yt-dlp/yt-dlp/commit/56b3dc03354b75be995759d8441d2754c0442b9a) ([#7929](https://github.com/yt-dlp/yt-dlp/issues/7929)) by [bashonly](https://github.com/bashonly)
- **streamanity**: [Remove](https://github.com/yt-dlp/yt-dlp/commit/2cfe221fbbe46faa3f46552c08d947a51f424903) ([#7571](https://github.com/yt-dlp/yt-dlp/issues/7571)) by [alerikaisattera](https://github.com/alerikaisattera)
- **svtplay**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/2301b5c1b77a65abbb46b72f91e1e4666fd5d985) ([#7789](https://github.com/yt-dlp/yt-dlp/issues/7789)) by [dirkf](https://github.com/dirkf), [wader](https://github.com/wader)
- **tbsjp**: [Add episode, program, playlist extractors](https://github.com/yt-dlp/yt-dlp/commit/876b70c8edf4c0147f180bd981fbc4d625cbfb9c) ([#7765](https://github.com/yt-dlp/yt-dlp/issues/7765)) by [garret1317](https://github.com/garret1317)
- **tiktok**
    - [Fix audio-only format extraction](https://github.com/yt-dlp/yt-dlp/commit/b09bd0c19648f60c59fb980cd454cb0069959fb9) ([#7712](https://github.com/yt-dlp/yt-dlp/issues/7712)) by [bashonly](https://github.com/bashonly)
    - [Fix webpage extraction](https://github.com/yt-dlp/yt-dlp/commit/069cbece9dba6384f1cc5fcfc7ce562a31af42fc) by [bashonly](https://github.com/bashonly)
- **triller**: [Fix unlisted video extraction](https://github.com/yt-dlp/yt-dlp/commit/39837ae3199aa934299badbd0d63243ed639e6c8) ([#7670](https://github.com/yt-dlp/yt-dlp/issues/7670)) by [bashonly](https://github.com/bashonly)
- **tv5mondeplus**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/7d3d658f4c558ee7d72b1c01b46f2126948681cd) ([#7952](https://github.com/yt-dlp/yt-dlp/issues/7952)) by [dirkf](https://github.com/dirkf), [korli](https://github.com/korli)
- **twitcasting**
    - [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/cebbd33b1c678149fc8f0e254db6fc0da317ea80) ([#8120](https://github.com/yt-dlp/yt-dlp/issues/8120)) by [c-basalt](https://github.com/c-basalt)
    - [Support `--wait-for-video`](https://github.com/yt-dlp/yt-dlp/commit/c1d71d0d9f41db5e4306c86af232f5f6220a130b) ([#7975](https://github.com/yt-dlp/yt-dlp/issues/7975)) by [at-wat](https://github.com/at-wat)
- **twitter**
    - [Add fallback, improve error handling](https://github.com/yt-dlp/yt-dlp/commit/6014355c6142f68e20c8374e3787e5b5820f19e2) ([#7621](https://github.com/yt-dlp/yt-dlp/issues/7621)) by [bashonly](https://github.com/bashonly)
    - [Fix GraphQL and legacy API](https://github.com/yt-dlp/yt-dlp/commit/92315c03774cfabb3a921884326beb4b981f786b) ([#7516](https://github.com/yt-dlp/yt-dlp/issues/7516)) by [bashonly](https://github.com/bashonly)
    - [Fix retweet extraction and syndication API](https://github.com/yt-dlp/yt-dlp/commit/a006ce2b27357c15792eb5c18f06765e640b801c) ([#8016](https://github.com/yt-dlp/yt-dlp/issues/8016)) by [bashonly](https://github.com/bashonly)
    - [Revert 92315c03774cfabb3a921884326beb4b981f786b](https://github.com/yt-dlp/yt-dlp/commit/b03fa7834579a01cc5fba48c0e73488a16683d48) by [pukkandan](https://github.com/pukkandan)
    - spaces
        - [Fix format protocol](https://github.com/yt-dlp/yt-dlp/commit/613dbce177d34ffc31053e8e01acf4bb107bcd1e) ([#7550](https://github.com/yt-dlp/yt-dlp/issues/7550)) by [bashonly](https://github.com/bashonly)
        - [Pass referer header to downloader](https://github.com/yt-dlp/yt-dlp/commit/c6ef553792ed48462f9fd0e78143bef6b1a71c2e) by [bashonly](https://github.com/bashonly)
- **unsupported**: [List more sites with DRM](https://github.com/yt-dlp/yt-dlp/commit/e7057383380d7d53815f8feaf90ca3dcbde88983) by [pukkandan](https://github.com/pukkandan)
- **videa**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/98eac0e6ba0e510ae7dfdfd249d42ee71fb272b1) ([#8003](https://github.com/yt-dlp/yt-dlp/issues/8003)) by [aky-01](https://github.com/aky-01), [hatsomatt](https://github.com/hatsomatt)
- **vrt**: [Update token signing key](https://github.com/yt-dlp/yt-dlp/commit/325191d0c9bf3fe257b8a7c2eb95080f44f6ddfc) ([#7519](https://github.com/yt-dlp/yt-dlp/issues/7519)) by [Zprokkel](https://github.com/Zprokkel)
- **wat.tv**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/7cccab79e7d00ed965b48b8cefce1da8a0513409) ([#7898](https://github.com/yt-dlp/yt-dlp/issues/7898)) by [davinkevin](https://github.com/davinkevin)
- **wdr**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/5d0395498d7065aa5e55bac85fa9354b4b0d48eb) ([#7979](https://github.com/yt-dlp/yt-dlp/issues/7979)) by [szabyg](https://github.com/szabyg)
- **web.archive**: vlive: [Remove extractor](https://github.com/yt-dlp/yt-dlp/commit/9652bca1bd02f6bc1b8cb1e186f2ccbf32225561) ([#8132](https://github.com/yt-dlp/yt-dlp/issues/8132)) by [bashonly](https://github.com/bashonly)
- **weibo**: [Fix extractor and support user extraction](https://github.com/yt-dlp/yt-dlp/commit/69b03f84f8378b0b5a2fbae56f9b7d860b2f529e) ([#7657](https://github.com/yt-dlp/yt-dlp/issues/7657)) by [c-basalt](https://github.com/c-basalt)
- **weverse**: [Support extraction without auth](https://github.com/yt-dlp/yt-dlp/commit/c2d8ee0000302aba63476b7d5bd8793e57b6c8c6) ([#7924](https://github.com/yt-dlp/yt-dlp/issues/7924)) by [seproDev](https://github.com/seproDev)
- **wimbledon**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/a15fcd299e767a510debd8dc1646fe863b96ce0e) ([#7551](https://github.com/yt-dlp/yt-dlp/issues/7551)) by [nnoboa](https://github.com/nnoboa)
- **wrestleuniverseppv**: [Fix HLS AES key extraction](https://github.com/yt-dlp/yt-dlp/commit/dae349da97cafe7357106a8f3187fd48a2ad1210) by [bashonly](https://github.com/bashonly)
- **youtube**
    - [Add `player_params` extractor arg](https://github.com/yt-dlp/yt-dlp/commit/ba06d77a316650ff057347d224b5afa8b203ad65) ([#7719](https://github.com/yt-dlp/yt-dlp/issues/7719)) by [coletdjnz](https://github.com/coletdjnz)
    - [Fix `player_params` arg being converted to lowercase](https://github.com/yt-dlp/yt-dlp/commit/546b2c28a106cf8101d481b215b676d1b091d276) by [coletdjnz](https://github.com/coletdjnz)
    - [Fix consent cookie](https://github.com/yt-dlp/yt-dlp/commit/378ae9f9fb8e8c86e6ac89c4c5b815b48ce93620) ([#7774](https://github.com/yt-dlp/yt-dlp/issues/7774)) by [coletdjnz](https://github.com/coletdjnz)
    - tab: [Detect looping feeds](https://github.com/yt-dlp/yt-dlp/commit/1ba6fe9db5f660d5538588315c23ad6cf0371c5f) ([#6621](https://github.com/yt-dlp/yt-dlp/issues/6621)) by [coletdjnz](https://github.com/coletdjnz)
- **zaiko**: [Improve thumbnail extraction](https://github.com/yt-dlp/yt-dlp/commit/ecef42c3adbcb6a84405139047923c4967316f28) ([#8054](https://github.com/yt-dlp/yt-dlp/issues/8054)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **zee5**: [Update access token endpoint](https://github.com/yt-dlp/yt-dlp/commit/a0de8bb8601146b8f87bf7cd562eef8bfb4690be) ([#7914](https://github.com/yt-dlp/yt-dlp/issues/7914)) by [bashonly](https://github.com/bashonly)
- **zoom**: [Extract duration](https://github.com/yt-dlp/yt-dlp/commit/66cc64ff6696f9921ff112a278542f8d999ffea4) by [bashonly](https://github.com/bashonly)

#### Downloader changes
- **external**
    - [Fix ffmpeg input from stdin](https://github.com/yt-dlp/yt-dlp/commit/e57eb98222d29cc4c09ee975d3c492274a6e5be3) ([#7655](https://github.com/yt-dlp/yt-dlp/issues/7655)) by [bashonly](https://github.com/bashonly)
    - [Fixes to cookie handling](https://github.com/yt-dlp/yt-dlp/commit/42ded0a429c20ec13dc006825e1508d9a02f0ad4) by [bashonly](https://github.com/bashonly)

#### Postprocessor changes
- **embedthumbnail**: [Support `m4v`](https://github.com/yt-dlp/yt-dlp/commit/8a4cd12c8f8e93292e3e95200b9d17a3af39624c) ([#7583](https://github.com/yt-dlp/yt-dlp/issues/7583)) by [Neurognostic](https://github.com/Neurognostic)

#### Networking changes
- [Add module](https://github.com/yt-dlp/yt-dlp/commit/c365dba8430ee33abda85d31f95128605bf240eb) ([#2861](https://github.com/yt-dlp/yt-dlp/issues/2861)) by [pukkandan](https://github.com/pukkandan)
- [Add request handler preference framework](https://github.com/yt-dlp/yt-dlp/commit/db7b054a6111ca387220d0eb87bf342f9c130eb8) ([#7603](https://github.com/yt-dlp/yt-dlp/issues/7603)) by [coletdjnz](https://github.com/coletdjnz)
- [Add strict Request extension checking](https://github.com/yt-dlp/yt-dlp/commit/86aea0d3a213da3be1da638b9b828e6f0ee1d59f) ([#7604](https://github.com/yt-dlp/yt-dlp/issues/7604)) by [coletdjnz](https://github.com/coletdjnz)
- [Fix POST requests with zero-length payloads](https://github.com/yt-dlp/yt-dlp/commit/71baa490ebd3655746430f208a9b605d120cd315) ([#7648](https://github.com/yt-dlp/yt-dlp/issues/7648)) by [bashonly](https://github.com/bashonly)
- [Fix `--legacy-server-connect`](https://github.com/yt-dlp/yt-dlp/commit/75dc8e673b481a82d0688aeec30f6c65d82bb359) ([#7645](https://github.com/yt-dlp/yt-dlp/issues/7645)) by [bashonly](https://github.com/bashonly)
- [Fix various socks proxy bugs](https://github.com/yt-dlp/yt-dlp/commit/20fbbd9249a2f26c7ae579bde5ba5d69aa8fac69) ([#8065](https://github.com/yt-dlp/yt-dlp/issues/8065)) by [coletdjnz](https://github.com/coletdjnz)
- [Ignore invalid proxies in env](https://github.com/yt-dlp/yt-dlp/commit/bbeacff7fcaa3b521066088a5ccbf34ef5070d1d) ([#7704](https://github.com/yt-dlp/yt-dlp/issues/7704)) by [coletdjnz](https://github.com/coletdjnz)
- [Rewrite architecture](https://github.com/yt-dlp/yt-dlp/commit/227bf1a33be7b89cd7d44ad046844c4ccba104f4) ([#2861](https://github.com/yt-dlp/yt-dlp/issues/2861)) by [coletdjnz](https://github.com/coletdjnz)
- **Request Handler**
    - urllib
        - [Remove dot segments during URL normalization](https://github.com/yt-dlp/yt-dlp/commit/4bf912282a34b58b6b35d8f7e6be535770c89c76) ([#7662](https://github.com/yt-dlp/yt-dlp/issues/7662)) by [coletdjnz](https://github.com/coletdjnz)
        - [Simplify gzip decoding](https://github.com/yt-dlp/yt-dlp/commit/59e92b1f1833440bb2190f847eb735cf0f90bc85) ([#7611](https://github.com/yt-dlp/yt-dlp/issues/7611)) by [Grub4K](https://github.com/Grub4K) (With fixes in [77bff23](https://github.com/yt-dlp/yt-dlp/commit/77bff23ee97565bab2e0d75b893a21bf7983219a))

#### Misc. changes
- **build**: [Make sure deprecated modules are added](https://github.com/yt-dlp/yt-dlp/commit/131d132da5c98c6c78bd7eed4b37f4458561b3d9) by [pukkandan](https://github.com/pukkandan)
- **cleanup**
    - [Add color to `download-archive` message](https://github.com/yt-dlp/yt-dlp/commit/2b029ca0a9f9105c4f7626993fa60e54c9782749) ([#5138](https://github.com/yt-dlp/yt-dlp/issues/5138)) by [aaruni96](https://github.com/aaruni96), [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan)
    - Miscellaneous
        - [6148833](https://github.com/yt-dlp/yt-dlp/commit/6148833f5ceb7674142ddb8d761ffe03cee7df69), [62b5c94](https://github.com/yt-dlp/yt-dlp/commit/62b5c94cadaa5f596dc1a7083db9db12efe357be) by [pukkandan](https://github.com/pukkandan)
        - [5ca095c](https://github.com/yt-dlp/yt-dlp/commit/5ca095cbcde3e32642a4fe5b2d69e8e3c785a021) by [barsnick](https://github.com/barsnick), [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz), [gamer191](https://github.com/gamer191), [Grub4K](https://github.com/Grub4K), [sqrtNOT](https://github.com/sqrtNOT)
        - [088add9](https://github.com/yt-dlp/yt-dlp/commit/088add9567d39b758737e4299a0e619fd89d2e8f) by [Grub4K](https://github.com/Grub4K)
- **devscripts**: `make_changelog`: [Fix changelog grouping and add networking group](https://github.com/yt-dlp/yt-dlp/commit/30ba233d4cee945756ed7344e7ddb3a90d2ae608) ([#8124](https://github.com/yt-dlp/yt-dlp/issues/8124)) by [Grub4K](https://github.com/Grub4K)
- **docs**: [Update collaborators](https://github.com/yt-dlp/yt-dlp/commit/1be0a96a4d14f629097509fcc89d15f69a8243c7) by [Grub4K](https://github.com/Grub4K)
- **test**
    - [Add tests for socks proxies](https://github.com/yt-dlp/yt-dlp/commit/fcd6a76adc49d5cd8783985c7ce35384b72e545f) ([#7908](https://github.com/yt-dlp/yt-dlp/issues/7908)) by [coletdjnz](https://github.com/coletdjnz)
    - [Fix `httplib_validation_errors` test for old Python versions](https://github.com/yt-dlp/yt-dlp/commit/95abea9a03289da1384e5bda3d590223ccc0a238) ([#7677](https://github.com/yt-dlp/yt-dlp/issues/7677)) by [coletdjnz](https://github.com/coletdjnz)
    - [Fix `test_load_certifi`](https://github.com/yt-dlp/yt-dlp/commit/de20687ee6b742646128a7629b57096631a20619) by [pukkandan](https://github.com/pukkandan)
    - download: [Test for `expected_exception`](https://github.com/yt-dlp/yt-dlp/commit/661c9a1d029296b28e0b2f8be8a72a43abaf6536) by [at-wat](https://github.com/at-wat)

### 2023.07.06

#### Important changes
- Security: [[CVE-2023-35934](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-35934)] Fix [Cookie leak](https://github.com/yt-dlp/yt-dlp/security/advisories/GHSA-v8mc-9377-rwjj)
    - `--add-header Cookie:` is deprecated and auto-scoped to input URL domains
    - Cookies are scoped when passed to external downloaders
    - Add `cookies` field to info.json and deprecate `http_headers.Cookie`

#### Core changes
- [Allow extractors to mark formats as potentially DRM](https://github.com/yt-dlp/yt-dlp/commit/bc344cd456380999c1ee74554dfd432a38f32ec7) ([#7396](https://github.com/yt-dlp/yt-dlp/issues/7396)) by [pukkandan](https://github.com/pukkandan)
- [Bugfix for b4e0d75848e9447cee2cd3646ce54d4744a7ff56](https://github.com/yt-dlp/yt-dlp/commit/e59e20744eb32ce4b6ea0dece7c673be8376a710) by [pukkandan](https://github.com/pukkandan)
- [Change how `Cookie` headers are handled](https://github.com/yt-dlp/yt-dlp/commit/3121512228487c9c690d3d39bfd2579addf96e07) by [Grub4K](https://github.com/Grub4K)
- [Prevent `Cookie` leaks on HTTP redirect](https://github.com/yt-dlp/yt-dlp/commit/f8b4bcc0a791274223723488bfbfc23ea3276641) by [coletdjnz](https://github.com/coletdjnz)
- **formats**: [Fix best fallback for storyboards](https://github.com/yt-dlp/yt-dlp/commit/906c0bdcd8974340d619e99ccd613c163eb0d0c2) by [pukkandan](https://github.com/pukkandan)
- **outtmpl**: [Pad `playlist_index` etc even when with internal formatting](https://github.com/yt-dlp/yt-dlp/commit/47bcd437247152e0af5b3ebc5592db7bb66855c2) by [pukkandan](https://github.com/pukkandan)
- **utils**: clean_podcast_url: [Handle protocol in redirect URL](https://github.com/yt-dlp/yt-dlp/commit/91302ed349f34dc26cc1d661bb45a4b71f4417f7) by [pukkandan](https://github.com/pukkandan)

#### Extractor changes
- **abc**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/8f05fbae2a79ce0713077ccc68b354e63216bf20) ([#7434](https://github.com/yt-dlp/yt-dlp/issues/7434)) by [meliber](https://github.com/meliber)
- **AdultSwim**: [Extract subtitles from m3u8](https://github.com/yt-dlp/yt-dlp/commit/5e16cf92eb496b7c1541a6b1d727cb87542984db) ([#7421](https://github.com/yt-dlp/yt-dlp/issues/7421)) by [nnoboa](https://github.com/nnoboa)
- **crunchyroll**: music: [Fix `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/5b4b92769afcc398475e481bfa839f1158902fe9) ([#7439](https://github.com/yt-dlp/yt-dlp/issues/7439)) by [AmanSal1](https://github.com/AmanSal1), [rdamas](https://github.com/rdamas)
- **Douyin**: [Fix extraction from webpage](https://github.com/yt-dlp/yt-dlp/commit/a2be9781fbf4d7e4db245c277ca2ecc41cf3a7b2) by [bashonly](https://github.com/bashonly)
- **googledrive**: [Fix source format extraction](https://github.com/yt-dlp/yt-dlp/commit/3b7f5300c577fef40464d46d4e4037a69d51fe82) ([#7395](https://github.com/yt-dlp/yt-dlp/issues/7395)) by [RfadnjdExt](https://github.com/RfadnjdExt)
- **kick**: [Fix `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/ef8509c300ea50da86aea447eb214d3d6f6db6bb) by [bashonly](https://github.com/bashonly)
- **qdance**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/f0a1ff118145b6449982ba401f9a9f656ecd8062) ([#7420](https://github.com/yt-dlp/yt-dlp/issues/7420)) by [bashonly](https://github.com/bashonly)
- **sbs**: [Python 3.7 compat](https://github.com/yt-dlp/yt-dlp/commit/f393bbe724b1fc6c7f754a5da507e807b2b40ad2) by [pukkandan](https://github.com/pukkandan)
- **stacommu**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/af1fd12f675220df6793fc019dff320bc76e8080) ([#7432](https://github.com/yt-dlp/yt-dlp/issues/7432)) by [urectanc](https://github.com/urectanc)
- **twitter**
    - [Fix unauthenticated extraction](https://github.com/yt-dlp/yt-dlp/commit/49296437a8e5fa91dacb5446e51ab588474c85d3) ([#7476](https://github.com/yt-dlp/yt-dlp/issues/7476)) by [bashonly](https://github.com/bashonly)
    - spaces: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/1cffd621cb371f1563563cfb2fe37d137e8a7bee) ([#7512](https://github.com/yt-dlp/yt-dlp/issues/7512)) by [bashonly](https://github.com/bashonly)
- **vidlii**: [Handle relative URLs](https://github.com/yt-dlp/yt-dlp/commit/ad8902f616ad2541f9b9626738f1393fad89a64c) by [pukkandan](https://github.com/pukkandan)
- **vk**: VKPlay, VKPlayLive: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/8776349ef6b1f644584a92dfa00a05208a48edc4) ([#7358](https://github.com/yt-dlp/yt-dlp/issues/7358)) by [c-basalt](https://github.com/c-basalt)
- **youtube**
    - [Add extractor-arg `formats`](https://github.com/yt-dlp/yt-dlp/commit/58786a10f212bd63f9ad1d0b4d9e4d31c3b385e2) by [pukkandan](https://github.com/pukkandan)
    - [Avoid false DRM detection](https://github.com/yt-dlp/yt-dlp/commit/94ed638a437fc766699d440e978982e24ce6a30a) ([#7396](https://github.com/yt-dlp/yt-dlp/issues/7396)) by [pukkandan](https://github.com/pukkandan)
    - [Fix comments' `is_favorited`](https://github.com/yt-dlp/yt-dlp/commit/89bed013741a776506f60380b7fd89d27d0710b4) ([#7390](https://github.com/yt-dlp/yt-dlp/issues/7390)) by [bbilly1](https://github.com/bbilly1)
    - [Ignore incomplete data for comment threads by default](https://github.com/yt-dlp/yt-dlp/commit/4dc4d8473c085900edc841c87c20041233d25b1f) ([#7475](https://github.com/yt-dlp/yt-dlp/issues/7475)) by [coletdjnz](https://github.com/coletdjnz)
    - [Process `post_live` over 2 hours](https://github.com/yt-dlp/yt-dlp/commit/d949c10c45bfc359bdacd52e6a180169b8128958) by [pukkandan](https://github.com/pukkandan)
    - stories: [Remove](https://github.com/yt-dlp/yt-dlp/commit/90db9a3c00ca80492c6a58c542e4cbf4c2710866) ([#7459](https://github.com/yt-dlp/yt-dlp/issues/7459)) by [pukkandan](https://github.com/pukkandan)
    - tab: [Support shorts-only playlists](https://github.com/yt-dlp/yt-dlp/commit/fcbc9ed760be6e3455bbadfaf277b4504b06f068) ([#7425](https://github.com/yt-dlp/yt-dlp/issues/7425)) by [coletdjnz](https://github.com/coletdjnz)

#### Downloader changes
- **aria2c**: [Add `--no-conf`](https://github.com/yt-dlp/yt-dlp/commit/8a8af356e3bba98a7f7d333aff0777d5d92130c8) by [pukkandan](https://github.com/pukkandan)
- **external**: [Scope cookies](https://github.com/yt-dlp/yt-dlp/commit/1ceb657bdd254ad961489e5060f2ccc7d556b729) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz)
- **http**: [Avoid infinite loop when no data is received](https://github.com/yt-dlp/yt-dlp/commit/662ef1e910b72e57957f06589925b2332ba52821) by [pukkandan](https://github.com/pukkandan)

#### Misc. changes
- [Add CodeQL workflow](https://github.com/yt-dlp/yt-dlp/commit/6355b5f1e1e8e7f4ef866d71d51e03baf0e82f17) ([#7497](https://github.com/yt-dlp/yt-dlp/issues/7497)) by [jorgectf](https://github.com/jorgectf)
- **cleanup**: Miscellaneous: [337734d](https://github.com/yt-dlp/yt-dlp/commit/337734d4a8a6500bc65434843db346b5cbd05e81) by [pukkandan](https://github.com/pukkandan)
- **docs**: [Minor fixes](https://github.com/yt-dlp/yt-dlp/commit/b532a3481046e1eabb6232ee8196fb696c356ff6) by [pukkandan](https://github.com/pukkandan)
- **make_changelog**: [Skip reverted commits](https://github.com/yt-dlp/yt-dlp/commit/fa44802809d189fca0f4782263d48d6533384503) by [pukkandan](https://github.com/pukkandan)

### 2023.06.22

#### Core changes
- [Fix bug in db3ad8a67661d7b234a6954d9c6a4a9b1749f5eb](https://github.com/yt-dlp/yt-dlp/commit/d7cd97e8d8d42b500fea9abb2aa4ac9b0f98b2ad) by [pukkandan](https://github.com/pukkandan)
- [Improve `--download-sections`](https://github.com/yt-dlp/yt-dlp/commit/b4e0d75848e9447cee2cd3646ce54d4744a7ff56) by [pukkandan](https://github.com/pukkandan)
    - Support negative time-ranges
    - Add `*from-url` to obey time-ranges in URL
- [Indicate `filesize` approximated from `tbr` better](https://github.com/yt-dlp/yt-dlp/commit/0dff8e4d1e6e9fb938f4256ea9af7d81f42fd54f) by [pukkandan](https://github.com/pukkandan)

#### Extractor changes
- [Support multiple `_VALID_URL`s](https://github.com/yt-dlp/yt-dlp/commit/5fd8367496b42c7b900b896a0d5460561a2859de) ([#5812](https://github.com/yt-dlp/yt-dlp/issues/5812)) by [nixxo](https://github.com/nixxo)
- **dplay**: GlobalCyclingNetworkPlus: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/774aa09dd6aa61ced9ec818d1f67e53414d22762) ([#7360](https://github.com/yt-dlp/yt-dlp/issues/7360)) by [bashonly](https://github.com/bashonly)
- **dropout**: [Fix season extraction](https://github.com/yt-dlp/yt-dlp/commit/db22142f6f817ff673d417b4b78e8db497bf8ab3) ([#7304](https://github.com/yt-dlp/yt-dlp/issues/7304)) by [OverlordQ](https://github.com/OverlordQ)
- **motherless**: [Add gallery support, fix groups](https://github.com/yt-dlp/yt-dlp/commit/f2ff0f6f1914b82d4a51681a72cc0828115dcb4a) ([#7211](https://github.com/yt-dlp/yt-dlp/issues/7211)) by [rexlambert22](https://github.com/rexlambert22), [Ti4eeT4e](https://github.com/Ti4eeT4e)
- **nebula**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/3f756c8c4095b942cf49788eb0862ceaf57847f2) ([#7156](https://github.com/yt-dlp/yt-dlp/issues/7156)) by [Lamieur](https://github.com/Lamieur), [rohieb](https://github.com/rohieb)
- **rheinmaintv**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/98cb1eda7a4cf67c96078980dbd63e6c06ad7f7c) ([#7311](https://github.com/yt-dlp/yt-dlp/issues/7311)) by [barthelmannk](https://github.com/barthelmannk)
- **youtube**
    - [Add `ios` to default clients used](https://github.com/yt-dlp/yt-dlp/commit/1e75d97db21152acc764b30a688e516f04b8a142) by [pukkandan](https://github.com/pukkandan)
        - IOS is affected neither by 403 nor by nsig so helps mitigate them preemptively
        - IOS also has higher bit-rate 'premium' formats though they are not labeled as such
    - [Improve description parsing performance](https://github.com/yt-dlp/yt-dlp/commit/71dc18fa29263a1ff0472c23d81bfc8dd4422d48) ([#7315](https://github.com/yt-dlp/yt-dlp/issues/7315)) by [berkanteber](https://github.com/berkanteber), [pukkandan](https://github.com/pukkandan)
    - [Improve nsig function name extraction](https://github.com/yt-dlp/yt-dlp/commit/cd810afe2ac5567c822b7424800fc470ef2d0045) by [pukkandan](https://github.com/pukkandan)
    - [Workaround 403 for android formats](https://github.com/yt-dlp/yt-dlp/commit/81ca451480051d7ce1a31c017e005358345a9149) by [pukkandan](https://github.com/pukkandan)

#### Misc. changes
- [Revert "Add automatic duplicate issue detection"](https://github.com/yt-dlp/yt-dlp/commit/a4486bfc1dc7057efca9dd3fe70d7fa25c56f700) by [pukkandan](https://github.com/pukkandan)
- **cleanup**
    - Miscellaneous
        - [7f9c6a6](https://github.com/yt-dlp/yt-dlp/commit/7f9c6a63b16e145495479e9f666f5b9e2ee69e2f) by [bashonly](https://github.com/bashonly)
        - [812cdfa](https://github.com/yt-dlp/yt-dlp/commit/812cdfa06c33a40e73a8e04b3e6f42c084666a43) by [pukkandan](https://github.com/pukkandan)

### 2023.06.21

#### Important changes
- YouTube: Improved throttling and signature fixes

#### Core changes
- [Add `--compat-option playlist-match-filter`](https://github.com/yt-dlp/yt-dlp/commit/93b39cdbd9dcf351bfa0c4ee252805b4617fdca9) by [pukkandan](https://github.com/pukkandan)
- [Add `--no-quiet`](https://github.com/yt-dlp/yt-dlp/commit/d669772c65e8630162fd6555d0a578b246591921) by [pukkandan](https://github.com/pukkandan)
- [Add option `--color`](https://github.com/yt-dlp/yt-dlp/commit/8417f26b8a819cd7ffcd4e000ca3e45033e670fb) ([#6904](https://github.com/yt-dlp/yt-dlp/issues/6904)) by [Grub4K](https://github.com/Grub4K)
- [Add option `--netrc-cmd`](https://github.com/yt-dlp/yt-dlp/commit/db3ad8a67661d7b234a6954d9c6a4a9b1749f5eb) ([#6682](https://github.com/yt-dlp/yt-dlp/issues/6682)) by [NDagestad](https://github.com/NDagestad), [pukkandan](https://github.com/pukkandan)
- [Add option `--xff`](https://github.com/yt-dlp/yt-dlp/commit/c16644642b08e2bf4130a6c5fa01395d8718c990) by [pukkandan](https://github.com/pukkandan)
- [Auto-select default format in `-f-`](https://github.com/yt-dlp/yt-dlp/commit/372a0f3b9dadd1e52234b498aa4c7040ef868c7d) ([#7101](https://github.com/yt-dlp/yt-dlp/issues/7101)) by [ivanskodje](https://github.com/ivanskodje), [pukkandan](https://github.com/pukkandan)
- [Deprecate internal `Youtubedl-no-compression` header](https://github.com/yt-dlp/yt-dlp/commit/955c89584b66fcd0fcfab3e611f1edeb1ca63886) ([#6876](https://github.com/yt-dlp/yt-dlp/issues/6876)) by [coletdjnz](https://github.com/coletdjnz)
- [Do not translate newlines in `--print-to-file`](https://github.com/yt-dlp/yt-dlp/commit/9874e82b5a61582169300bea561b3e8899ad1ef7) by [pukkandan](https://github.com/pukkandan)
- [Ensure pre-processor errors do not block `--print`](https://github.com/yt-dlp/yt-dlp/commit/f005a35aa7e4f67a0c603a946c0dd714c151b2d6) by [pukkandan](https://github.com/pukkandan) (With fixes in [17ba434](https://github.com/yt-dlp/yt-dlp/commit/17ba4343cf99701692a7f4798fd42b50f644faba))
- [Fix `filepath` being copied to underlying format dict](https://github.com/yt-dlp/yt-dlp/commit/84078a8b38f403495d00b46654c8750774d821de) by [pukkandan](https://github.com/pukkandan)
- [Improve HTTP redirect handling](https://github.com/yt-dlp/yt-dlp/commit/08916a49c777cb6e000eec092881eb93ec22076c) ([#7094](https://github.com/yt-dlp/yt-dlp/issues/7094)) by [coletdjnz](https://github.com/coletdjnz)
- [Populate `filename` and `urls` fields at all stages of `--print`](https://github.com/yt-dlp/yt-dlp/commit/170605840ea9d5ad75da6576485ea7d125b428ee) by [pukkandan](https://github.com/pukkandan) (With fixes in [b5f61b6](https://github.com/yt-dlp/yt-dlp/commit/b5f61b69d4561b81fc98c226b176f0c15493e688))
- [Relaxed validation for numeric format filters](https://github.com/yt-dlp/yt-dlp/commit/c3f624ef0a5d7a6ae1c5ffeb243087e9fc7d79dc) by [pukkandan](https://github.com/pukkandan)
- [Support decoding multiple content encodings](https://github.com/yt-dlp/yt-dlp/commit/daafbf49b3482edae4d70dd37070be99742a926e) ([#7142](https://github.com/yt-dlp/yt-dlp/issues/7142)) by [coletdjnz](https://github.com/coletdjnz)
- [Support loading info.json with a list at it's root](https://github.com/yt-dlp/yt-dlp/commit/ab1de9cb1e39cf421c2b7dc6756c6ff1955bb313) by [pukkandan](https://github.com/pukkandan)
- [Workaround erroneous urllib Windows proxy parsing](https://github.com/yt-dlp/yt-dlp/commit/3f66b6fe50f8d5b545712f8b19d5ae62f5373980) ([#7092](https://github.com/yt-dlp/yt-dlp/issues/7092)) by [coletdjnz](https://github.com/coletdjnz)
- **cookies**
    - [Defer extraction of v11 key from keyring](https://github.com/yt-dlp/yt-dlp/commit/9b7a48abd1b187eae1e3f6c9839c47d43ccec00b) by [Grub4K](https://github.com/Grub4K)
    - [Move `YoutubeDLCookieJar` to cookies module](https://github.com/yt-dlp/yt-dlp/commit/b87e01c123fd560b6a674ce00f45a9459d82d98a) ([#7091](https://github.com/yt-dlp/yt-dlp/issues/7091)) by [coletdjnz](https://github.com/coletdjnz)
    - [Support custom Safari cookies path](https://github.com/yt-dlp/yt-dlp/commit/a58182b75a05fe0a10c5e94a536711d3ade19c20) ([#6783](https://github.com/yt-dlp/yt-dlp/issues/6783)) by [NextFire](https://github.com/NextFire)
    - [Update for chromium changes](https://github.com/yt-dlp/yt-dlp/commit/b38d4c941d1993ab27e4c0f8e024e23c2ec0f8f8) ([#6897](https://github.com/yt-dlp/yt-dlp/issues/6897)) by [mbway](https://github.com/mbway)
- **Cryptodome**: [Fix `__bool__`](https://github.com/yt-dlp/yt-dlp/commit/98ac902c4979e4529b166e873473bef42baa2e3e) by [pukkandan](https://github.com/pukkandan)
- **jsinterp**
    - [Do not compile regex](https://github.com/yt-dlp/yt-dlp/commit/7aeda6cc9e73ada0b0a0b6a6748c66bef63a20a8) by [pukkandan](https://github.com/pukkandan)
    - [Fix division](https://github.com/yt-dlp/yt-dlp/commit/b4a252fba81f53631c07ca40ce7583f5d19a8a36) ([#7279](https://github.com/yt-dlp/yt-dlp/issues/7279)) by [bashonly](https://github.com/bashonly)
    - [Fix global object extraction](https://github.com/yt-dlp/yt-dlp/commit/01aba2519a0884ef17d5f85608dbd2a455577147) by [pukkandan](https://github.com/pukkandan)
    - [Handle `NaN` in bitwise operators](https://github.com/yt-dlp/yt-dlp/commit/1d7656184c6b8aa46b29149893894b3c24f1df00) by [pukkandan](https://github.com/pukkandan)
    - [Handle negative numbers better](https://github.com/yt-dlp/yt-dlp/commit/7cf51f21916292cd80bdeceb37489f5322f166dd) by [pukkandan](https://github.com/pukkandan)
- **outtmpl**
    - [Allow `\n` in replacements and default.](https://github.com/yt-dlp/yt-dlp/commit/78fde6e3398ff11e5d383a66b28664badeab5180) by [pukkandan](https://github.com/pukkandan)
    - [Fix some minor bugs](https://github.com/yt-dlp/yt-dlp/commit/ebe1b4e34f43c3acad30e4bcb8484681a030c114) by [pukkandan](https://github.com/pukkandan) (With fixes in [1619ab3](https://github.com/yt-dlp/yt-dlp/commit/1619ab3e67d8dc4f86fc7ed292c79345bc0d91a0))
    - [Support `str.format` syntax inside replacements](https://github.com/yt-dlp/yt-dlp/commit/ec9311c41b111110bc52cfbd6ea682c6fb23f77a) by [pukkandan](https://github.com/pukkandan)
- **update**
    - [Better error handling](https://github.com/yt-dlp/yt-dlp/commit/d2e84d5eb01c66fc5304e8566348d65a7be24ed7) by [pukkandan](https://github.com/pukkandan)
    - [Do not restart into versions without `--update-to`](https://github.com/yt-dlp/yt-dlp/commit/02948a17d903f544363bb20b51a6d8baed7bba08) by [pukkandan](https://github.com/pukkandan)
    - [Implement `--update-to` repo](https://github.com/yt-dlp/yt-dlp/commit/665472a7de3880578c0b7b3f95c71570c056368e) by [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan)
- **upstream**
    - [Merged with youtube-dl 07af47](https://github.com/yt-dlp/yt-dlp/commit/42f2d40b475db66486a4b4fe5b56751a640db5db) by [pukkandan](https://github.com/pukkandan)
    - [Merged with youtube-dl d1c6c5](https://github.com/yt-dlp/yt-dlp/commit/4823ec9f461512daa1b8ab362893bb86a6320b26) by [pukkandan](https://github.com/pukkandan) (With fixes in [edbe5b5](https://github.com/yt-dlp/yt-dlp/commit/edbe5b589dd0860a67b4e03f58db3cd2539d91c2) by [bashonly](https://github.com/bashonly))
- **utils**
    - `FormatSorter`: [Improve `size` and `br`](https://github.com/yt-dlp/yt-dlp/commit/eedda5252c05327748dede204a8fccafa0288118) by [pukkandan](https://github.com/pukkandan), [u-spec-png](https://github.com/u-spec-png)
    - `js_to_json`: [Implement template strings](https://github.com/yt-dlp/yt-dlp/commit/0898c5c8ccadfc404472456a7a7751b72afebadd) ([#6623](https://github.com/yt-dlp/yt-dlp/issues/6623)) by [Grub4K](https://github.com/Grub4K)
    - `locked_file`: [Fix for virtiofs](https://github.com/yt-dlp/yt-dlp/commit/45998b3e371b819ce0dbe50da703809a048cc2fe) ([#6840](https://github.com/yt-dlp/yt-dlp/issues/6840)) by [brandon-dacrib](https://github.com/brandon-dacrib)
    - `strftime_or_none`: [Handle negative timestamps](https://github.com/yt-dlp/yt-dlp/commit/a35af4306d24c56c6358f89cdf204860d1cd62b4) by [dirkf](https://github.com/dirkf), [pukkandan](https://github.com/pukkandan)
    - `traverse_obj`
        - [Allow iterables in traversal](https://github.com/yt-dlp/yt-dlp/commit/21b5ec86c2c37d10c5bb97edd7051d3aac16bb3e) ([#6902](https://github.com/yt-dlp/yt-dlp/issues/6902)) by [Grub4K](https://github.com/Grub4K)
        - [More fixes](https://github.com/yt-dlp/yt-dlp/commit/b079c26f0af8085bccdadc72c61c8164ca5ab0f8) ([#6959](https://github.com/yt-dlp/yt-dlp/issues/6959)) by [Grub4K](https://github.com/Grub4K)
    - `write_string`: [Fix noconsole behavior](https://github.com/yt-dlp/yt-dlp/commit/3b479100df02e20dd949e046003ae96ddbfced57) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- [Do not exit early for unsuitable `url_result`](https://github.com/yt-dlp/yt-dlp/commit/baa922b5c74b10e3b86ff5e6cf6529b3aae8efab) by [pukkandan](https://github.com/pukkandan)
- [Do not warn for invalid chapter data in description](https://github.com/yt-dlp/yt-dlp/commit/84ffeb7d5e72e3829319ba7720a8480fc4c7503b) by [pukkandan](https://github.com/pukkandan)
- [Extract more metadata from ISM](https://github.com/yt-dlp/yt-dlp/commit/f68434cc74cfd3db01b266476a2eac8329fbb267) by [pukkandan](https://github.com/pukkandan)
- **abematv**: [Add fallback for title and description extraction and extract more metadata](https://github.com/yt-dlp/yt-dlp/commit/c449c0655d7c8549e6e1389c26b628053b253d39) ([#6994](https://github.com/yt-dlp/yt-dlp/issues/6994)) by [Lesmiscore](https://github.com/Lesmiscore)
- **acast**: [Support embeds](https://github.com/yt-dlp/yt-dlp/commit/c91ac833ea99b00506e470a44cf930e4e23378c9) ([#7212](https://github.com/yt-dlp/yt-dlp/issues/7212)) by [pabs3](https://github.com/pabs3)
- **adobepass**: [Handle `Charter_Direct` MSO as `Spectrum`](https://github.com/yt-dlp/yt-dlp/commit/ea0570820336a0fe9c3b530d1b0d1e59313274f4) ([#6824](https://github.com/yt-dlp/yt-dlp/issues/6824)) by [bashonly](https://github.com/bashonly)
- **aeonco**: [Support Youtube embeds](https://github.com/yt-dlp/yt-dlp/commit/ed81b74802b4247ee8d9dc0ef87eb52baefede1c) ([#6591](https://github.com/yt-dlp/yt-dlp/issues/6591)) by [alexklapheke](https://github.com/alexklapheke)
- **afreecatv**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/fdd69db38924c38194ef236b26325d66ac815c88) ([#6283](https://github.com/yt-dlp/yt-dlp/issues/6283)) by [blmarket](https://github.com/blmarket)
- **ARDBetaMediathek**: [Add thumbnail](https://github.com/yt-dlp/yt-dlp/commit/f78eb41e1c0f1dcdb10317358a26bf541dc7ee15) ([#6890](https://github.com/yt-dlp/yt-dlp/issues/6890)) by [StefanLobbenmeier](https://github.com/StefanLobbenmeier)
- **bibeltv**: [Fix extraction, support live streams and series](https://github.com/yt-dlp/yt-dlp/commit/4ad58667c102bd82a7c4cca8aa395ec1682e3b4c) ([#6505](https://github.com/yt-dlp/yt-dlp/issues/6505)) by [flashdagger](https://github.com/flashdagger)
- **bilibili**
    - [Support festival videos](https://github.com/yt-dlp/yt-dlp/commit/ab29e47029e2f5b48abbbab78e82faf7cf6e9506) ([#6547](https://github.com/yt-dlp/yt-dlp/issues/6547)) by [qbnu](https://github.com/qbnu)
    - SpaceVideo: [Extract signature](https://github.com/yt-dlp/yt-dlp/commit/6f10cdcf7eeaeae5b75e0a4428cd649c156a2d83) ([#7149](https://github.com/yt-dlp/yt-dlp/issues/7149)) by [elyse0](https://github.com/elyse0)
- **biliIntl**: [Add comment extraction](https://github.com/yt-dlp/yt-dlp/commit/b093c38cc9f26b59a8504211d792f053142c847d) ([#6079](https://github.com/yt-dlp/yt-dlp/issues/6079)) by [HobbyistDev](https://github.com/HobbyistDev)
- **bitchute**: [Add more fallback subdomains](https://github.com/yt-dlp/yt-dlp/commit/0c4e0fbcade0fc92d14c2a6d63e360fe067f6192) ([#6907](https://github.com/yt-dlp/yt-dlp/issues/6907)) by [Neurognostic](https://github.com/Neurognostic)
- **booyah**: [Remove extractor](https://github.com/yt-dlp/yt-dlp/commit/f7f7a877bf8e87fd4eb0ad2494ad948ca7691114) by [pukkandan](https://github.com/pukkandan)
- **BrainPOP**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/979568f26ece80bca72b48f0dd57d676e431059a) ([#6106](https://github.com/yt-dlp/yt-dlp/issues/6106)) by [MinePlayersPE](https://github.com/MinePlayersPE)
- **bravotv**
    - [Detect DRM](https://github.com/yt-dlp/yt-dlp/commit/1fe5bf240e6ade487d18079a62aa36bcc440a27a) ([#7171](https://github.com/yt-dlp/yt-dlp/issues/7171)) by [bashonly](https://github.com/bashonly)
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/06966cb8966b9aa4f60ab9c44c182a057d4ca3a3) ([#6568](https://github.com/yt-dlp/yt-dlp/issues/6568)) by [bashonly](https://github.com/bashonly)
- **camfm**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/4cbfa570a1b9bd65b0f48770693377e8d842dcb0) ([#7083](https://github.com/yt-dlp/yt-dlp/issues/7083)) by [garret1317](https://github.com/garret1317)
- **cbc**
    - [Fix live extractor, playlist `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/7a7b1376fbce0067cf37566bb47131bc0022638d) ([#6625](https://github.com/yt-dlp/yt-dlp/issues/6625)) by [makew0rld](https://github.com/makew0rld)
    - [Ignore 426 from API](https://github.com/yt-dlp/yt-dlp/commit/4afb208cf07b59291ae3b0c4efc83945ee5b8812) ([#6781](https://github.com/yt-dlp/yt-dlp/issues/6781)) by [jo-nike](https://github.com/jo-nike)
    - gem: [Update `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/871c907454693940cb56906ed9ea49fcb7154829) ([#6499](https://github.com/yt-dlp/yt-dlp/issues/6499)) by [makeworld-the-better-one](https://github.com/makeworld-the-better-one)
- **cbs**: [Add `ParamountPressExpress` extractor](https://github.com/yt-dlp/yt-dlp/commit/44369c9afa996e14e9f466754481d878811b5b4a) ([#6604](https://github.com/yt-dlp/yt-dlp/issues/6604)) by [bashonly](https://github.com/bashonly)
- **cbsnews**: [Overhaul extractors](https://github.com/yt-dlp/yt-dlp/commit/f6e43d6fa9804c24525e1fed0a87782754dab7ed) ([#6681](https://github.com/yt-dlp/yt-dlp/issues/6681)) by [bashonly](https://github.com/bashonly)
- **chilloutzone**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/6f4fc5660f40f3458882a8f51601eae4af7be609) ([#6445](https://github.com/yt-dlp/yt-dlp/issues/6445)) by [bashonly](https://github.com/bashonly)
- **clipchamp**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/2f07c4c1da4361af213e5791279b9d152d2e4ce3) ([#6978](https://github.com/yt-dlp/yt-dlp/issues/6978)) by [bashonly](https://github.com/bashonly)
- **comedycentral**: [Add support for movies](https://github.com/yt-dlp/yt-dlp/commit/66468bbf49562ff82670cbbd456c5e8448a6df34) ([#7108](https://github.com/yt-dlp/yt-dlp/issues/7108)) by [sqrtNOT](https://github.com/sqrtNOT)
- **crtvg**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/26c517b29c8727e47948d6fff749d5297f0efb60) ([#7168](https://github.com/yt-dlp/yt-dlp/issues/7168)) by [ItzMaxTV](https://github.com/ItzMaxTV)
- **crunchyroll**: [Rework with support for movies, music and artists](https://github.com/yt-dlp/yt-dlp/commit/032de83ea9ff2f4977d9c71a93bbc1775597b762) ([#6237](https://github.com/yt-dlp/yt-dlp/issues/6237)) by [Grub4K](https://github.com/Grub4K)
- **dacast**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/c25cac2f8e5fbac2737a426d7778fd2f0efc5381) ([#6896](https://github.com/yt-dlp/yt-dlp/issues/6896)) by [bashonly](https://github.com/bashonly)
- **daftsex**: [Update domain and embed player url](https://github.com/yt-dlp/yt-dlp/commit/fc5a7f9b27d2a89b1f3ca7d33a95301c21d832cd) ([#5966](https://github.com/yt-dlp/yt-dlp/issues/5966)) by [JChris246](https://github.com/JChris246)
- **DigitalConcertHall**: [Support films](https://github.com/yt-dlp/yt-dlp/commit/55ed4ff73487feb3177b037dfc2ea527e777da3e) ([#7202](https://github.com/yt-dlp/yt-dlp/issues/7202)) by [ItzMaxTV](https://github.com/ItzMaxTV)
- **discogs**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/6daaf21092888beff11b807cd46f832f1f9c46a0) ([#6624](https://github.com/yt-dlp/yt-dlp/issues/6624)) by [rjy](https://github.com/rjy)
- **dlf**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/b423b6a48e0b19260bc95ab7d72d2138d7f124dc) ([#6697](https://github.com/yt-dlp/yt-dlp/issues/6697)) by [nick-cd](https://github.com/nick-cd)
- **drtv**: [Fix radio page extraction](https://github.com/yt-dlp/yt-dlp/commit/9a06b7b1891b48cebbe275652ae8025a36d97d97) ([#6552](https://github.com/yt-dlp/yt-dlp/issues/6552)) by [viktor-enzell](https://github.com/viktor-enzell)
- **Dumpert**: [Fix m3u8 and support new URL pattern](https://github.com/yt-dlp/yt-dlp/commit/f8ae441501596733e2b967430471643a1d7cacb8) ([#6091](https://github.com/yt-dlp/yt-dlp/issues/6091)) by [DataGhost](https://github.com/DataGhost), [pukkandan](https://github.com/pukkandan)
- **elevensports**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/ecfe47973f6603b5367fe2cc3c65274627d94516) ([#7172](https://github.com/yt-dlp/yt-dlp/issues/7172)) by [ItzMaxTV](https://github.com/ItzMaxTV)
- **ettutv**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/83465fc4100a2fb2c188898fbc2f3021f6a9b4dd) ([#6579](https://github.com/yt-dlp/yt-dlp/issues/6579)) by [elyse0](https://github.com/elyse0)
- **europarl**: [Rewrite extractor](https://github.com/yt-dlp/yt-dlp/commit/03789976d301eaed3e957dbc041573098f6af059) ([#7114](https://github.com/yt-dlp/yt-dlp/issues/7114)) by [HobbyistDev](https://github.com/HobbyistDev)
- **eurosport**: [Improve `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/45e87ea106ad37b2a002663fa30ee41ce97b16cd) ([#7076](https://github.com/yt-dlp/yt-dlp/issues/7076)) by [HobbyistDev](https://github.com/HobbyistDev)
- **facebook**: [Fix metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/3b52a606881e6adadc33444abdeacce562b79330) ([#6856](https://github.com/yt-dlp/yt-dlp/issues/6856)) by [ringus1](https://github.com/ringus1)
- **foxnews**: [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/97d60ad8cd6c99f01e463a9acfce8693aff2a609) ([#7222](https://github.com/yt-dlp/yt-dlp/issues/7222)) by [bashonly](https://github.com/bashonly)
- **funker530**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/cab94a0cd8b6d3fffed5a6faff030274adbed182) ([#7291](https://github.com/yt-dlp/yt-dlp/issues/7291)) by [Cyberes](https://github.com/Cyberes)
- **generic**
    - [Accept values for `fragment_query`, `variant_query`](https://github.com/yt-dlp/yt-dlp/commit/5cc0a8fd2e9fec50026fb92170b57993af939e4a) ([#6600](https://github.com/yt-dlp/yt-dlp/issues/6600)) by [bashonly](https://github.com/bashonly) (With fixes in [9bfe0d1](https://github.com/yt-dlp/yt-dlp/commit/9bfe0d15bd7dbdc6b0e6378fa9f5e2e289b2373b))
    - [Add extractor-args `hls_key`, `variant_query`](https://github.com/yt-dlp/yt-dlp/commit/c2e0fc40a73dd85ab3920f977f579d475e66ef59) ([#6567](https://github.com/yt-dlp/yt-dlp/issues/6567)) by [bashonly](https://github.com/bashonly)
    - [Attempt to detect live HLS](https://github.com/yt-dlp/yt-dlp/commit/93e7c6995e07dafb9dcc06c0d06acf6c5bdfecc5) ([#6775](https://github.com/yt-dlp/yt-dlp/issues/6775)) by [bashonly](https://github.com/bashonly)
- **genius**: [Add support for articles](https://github.com/yt-dlp/yt-dlp/commit/460da07439718d9af1e3661da2a23e05a913a2e6) ([#6474](https://github.com/yt-dlp/yt-dlp/issues/6474)) by [bashonly](https://github.com/bashonly)
- **globalplayer**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/30647668a92a0ca5cd108776804baac0996bd9f7) ([#6903](https://github.com/yt-dlp/yt-dlp/issues/6903)) by [garret1317](https://github.com/garret1317)
- **gmanetwork**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/2d97d154fe4fb84fe2ed3a4e1ed5819e89b71e88) ([#5945](https://github.com/yt-dlp/yt-dlp/issues/5945)) by [HobbyistDev](https://github.com/HobbyistDev)
- **gronkh**: [Extract duration and chapters](https://github.com/yt-dlp/yt-dlp/commit/9c92b803fa24e48543ce969468d5404376e315b7) ([#6817](https://github.com/yt-dlp/yt-dlp/issues/6817)) by [satan1st](https://github.com/satan1st)
- **hentaistigma**: [Remove extractor](https://github.com/yt-dlp/yt-dlp/commit/04f8018a0544736a18494bc3899d06b05b78fae6) by [pukkandan](https://github.com/pukkandan)
- **hidive**: [Fix login](https://github.com/yt-dlp/yt-dlp/commit/e6ab678e36c40ded0aae305bbb866cdab554d417) by [pukkandan](https://github.com/pukkandan)
- **hollywoodreporter**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/6bdb64e2a2a6d504d8ce1dc830fbfb8a7f199c63) ([#6614](https://github.com/yt-dlp/yt-dlp/issues/6614)) by [bashonly](https://github.com/bashonly)
- **hotstar**: [Support `/shows/` URLs](https://github.com/yt-dlp/yt-dlp/commit/7f8ddebbb51c9fd4a347306332a718ba41b371b8) ([#7225](https://github.com/yt-dlp/yt-dlp/issues/7225)) by [bashonly](https://github.com/bashonly)
- **hrefli**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/7e35526d5b970a034b9d76215ee3e4bd7631edcd) ([#6762](https://github.com/yt-dlp/yt-dlp/issues/6762)) by [selfisekai](https://github.com/selfisekai)
- **idolplus**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/5c14b213679ed4401288bdc86ae696932e219222) ([#6732](https://github.com/yt-dlp/yt-dlp/issues/6732)) by [ping](https://github.com/ping)
- **iq**: [Set more language codes](https://github.com/yt-dlp/yt-dlp/commit/2d5cae9636714ff922d28c548c349d5f2b48f317) ([#6476](https://github.com/yt-dlp/yt-dlp/issues/6476)) by [D0LLYNH0](https://github.com/D0LLYNH0)
- **iwara**
    - [Accept old URLs](https://github.com/yt-dlp/yt-dlp/commit/ab92d8651c48d247dfb7d3f0a824cc986e47c7ed) by [Lesmiscore](https://github.com/Lesmiscore)
    - [Fix authentication](https://github.com/yt-dlp/yt-dlp/commit/0a5d7c39e17bb9bd50c9db42bcad40eb82d7f784) ([#7137](https://github.com/yt-dlp/yt-dlp/issues/7137)) by [toomyzoom](https://github.com/toomyzoom)
    - [Fix format sorting](https://github.com/yt-dlp/yt-dlp/commit/56793f74c36899742d7abd52afb0deca97d469e1) ([#6651](https://github.com/yt-dlp/yt-dlp/issues/6651)) by [hasezoey](https://github.com/hasezoey)
    - [Fix typo](https://github.com/yt-dlp/yt-dlp/commit/d1483ec693c79f0b4ddf493870bcb840aca4da08) by [Lesmiscore](https://github.com/Lesmiscore)
    - [Implement login](https://github.com/yt-dlp/yt-dlp/commit/21b9413cf7dd4830b2ece57af21589dd4538fc52) ([#6721](https://github.com/yt-dlp/yt-dlp/issues/6721)) by [toomyzoom](https://github.com/toomyzoom)
    - [Overhaul extractors](https://github.com/yt-dlp/yt-dlp/commit/c14af7a741931b364bab3d9546c0f4359f318f8c) ([#6557](https://github.com/yt-dlp/yt-dlp/issues/6557)) by [Lesmiscore](https://github.com/Lesmiscore)
    - [Report private videos](https://github.com/yt-dlp/yt-dlp/commit/95a383be1b6fb00c92ee3fb091732c4f6009acb6) ([#6641](https://github.com/yt-dlp/yt-dlp/issues/6641)) by [Lesmiscore](https://github.com/Lesmiscore)
- **JStream**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/3459d3c5af3b2572ed51e8ecfda6c11022a838c6) ([#6252](https://github.com/yt-dlp/yt-dlp/issues/6252)) by [Lesmiscore](https://github.com/Lesmiscore)
- **jwplatform**: [Update `_extract_embed_urls`](https://github.com/yt-dlp/yt-dlp/commit/cf9fd52fabe71d6e7c30d3ea525029ffa561fc9c) ([#6383](https://github.com/yt-dlp/yt-dlp/issues/6383)) by [carusocr](https://github.com/carusocr)
- **kick**: [Make initial request non-fatal](https://github.com/yt-dlp/yt-dlp/commit/0a6918a4a1431960181d8c50e0bbbcb0afbaff9a) by [bashonly](https://github.com/bashonly)
- **LastFM**: [Rewrite playlist extraction](https://github.com/yt-dlp/yt-dlp/commit/026435714cb7c39613a0d7d2acd15d3823b78d94) ([#6379](https://github.com/yt-dlp/yt-dlp/issues/6379)) by [hatienl0i261299](https://github.com/hatienl0i261299), [pukkandan](https://github.com/pukkandan)
- **lbry**: [Extract original quality formats](https://github.com/yt-dlp/yt-dlp/commit/44c0d66442b568d9e1359e669d8b029b08a77fa7) ([#7257](https://github.com/yt-dlp/yt-dlp/issues/7257)) by [bashonly](https://github.com/bashonly)
- **line**: [Remove extractors](https://github.com/yt-dlp/yt-dlp/commit/faa0332ed69e070cf3bd31390589a596e962f392) ([#6734](https://github.com/yt-dlp/yt-dlp/issues/6734)) by [sian1468](https://github.com/sian1468)
- **livestream**: [Support videos with account id](https://github.com/yt-dlp/yt-dlp/commit/bfdf144c7e5d7a93fbfa9d8e65598c72bf2b542a) ([#6324](https://github.com/yt-dlp/yt-dlp/issues/6324)) by [theperfectpunk](https://github.com/theperfectpunk)
- **medaltv**: [Fix clips](https://github.com/yt-dlp/yt-dlp/commit/1e3c2b6ec28d7ab5e31341fa93c47b65be4fbff4) ([#6502](https://github.com/yt-dlp/yt-dlp/issues/6502)) by [xenova](https://github.com/xenova)
- **mediastream**: [Improve `WinSports` and embed extraction](https://github.com/yt-dlp/yt-dlp/commit/03025b6e105139d01cd415ddc51fd692957fd2ba) ([#6426](https://github.com/yt-dlp/yt-dlp/issues/6426)) by [bashonly](https://github.com/bashonly)
- **mgtv**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/59d9fe08312bbb76ee26238d207a8ca35410a48d) ([#7234](https://github.com/yt-dlp/yt-dlp/issues/7234)) by [bashonly](https://github.com/bashonly)
- **Mzaalo**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/dc3c44f349ba85af320e706e2a27ad81a78b1c6e) ([#7163](https://github.com/yt-dlp/yt-dlp/issues/7163)) by [ItzMaxTV](https://github.com/ItzMaxTV)
- **nbc**: [Fix `NBCStations` direct mp4 formats](https://github.com/yt-dlp/yt-dlp/commit/9be0fe1fd967f62cbf3c60bd14e1021a70abc147) ([#6637](https://github.com/yt-dlp/yt-dlp/issues/6637)) by [bashonly](https://github.com/bashonly)
- **nebula**: [Add `beta.nebula.tv`](https://github.com/yt-dlp/yt-dlp/commit/cbfe2e5cbe0f4649a91e323a82b8f5f774f36662) ([#6516](https://github.com/yt-dlp/yt-dlp/issues/6516)) by [unbeatable-101](https://github.com/unbeatable-101)
- **nekohacker**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/489f51279d00318018478fd7461eddbe3b45297e) ([#7003](https://github.com/yt-dlp/yt-dlp/issues/7003)) by [hasezoey](https://github.com/hasezoey)
- **nhk**
    - [Add `NhkRadiru` extractor](https://github.com/yt-dlp/yt-dlp/commit/8f0be90ecb3b8d862397177bb226f17b245ef933) ([#6819](https://github.com/yt-dlp/yt-dlp/issues/6819)) by [garret1317](https://github.com/garret1317)
    - [Fix API extraction](https://github.com/yt-dlp/yt-dlp/commit/f41b949a2ef646fbc36375febbe3f0c19d742c0f) ([#7180](https://github.com/yt-dlp/yt-dlp/issues/7180)) by [menschel](https://github.com/menschel), [sjthespian](https://github.com/sjthespian)
    - `NhkRadiruLive`: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/81c8b9bdd9841b72cbfc1bbff9dab5fb4aa038b0) ([#7332](https://github.com/yt-dlp/yt-dlp/issues/7332)) by [garret1317](https://github.com/garret1317)
- **niconico**
    - [Download comments from the new endpoint](https://github.com/yt-dlp/yt-dlp/commit/52ecc33e221f7de7eb6fed6c22489f0c5fdd2c6d) ([#6773](https://github.com/yt-dlp/yt-dlp/issues/6773)) by [Lesmiscore](https://github.com/Lesmiscore)
    - live: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/f8f9250fe280d37f0988646cd5cc0072f4d33a6d) ([#5764](https://github.com/yt-dlp/yt-dlp/issues/5764)) by [Lesmiscore](https://github.com/Lesmiscore)
    - series: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/c86e433c35fe5da6cb29f3539eef97497f84ed38) ([#6898](https://github.com/yt-dlp/yt-dlp/issues/6898)) by [sqrtNOT](https://github.com/sqrtNOT)
- **nubilesporn**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/d4e6ef40772e0560a8ed33b844ef7549e86837be) ([#6231](https://github.com/yt-dlp/yt-dlp/issues/6231)) by [permunkle](https://github.com/permunkle)
- **odnoklassniki**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/1a2eb5bda51d8b7a78a65acebf72a0dcf9da196b) ([#7217](https://github.com/yt-dlp/yt-dlp/issues/7217)) by [bashonly](https://github.com/bashonly)
- **opencast**
    - [Add ltitools to `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/3588be59cee429a0ab5c4ceb2f162298bb44147d) ([#6371](https://github.com/yt-dlp/yt-dlp/issues/6371)) by [C0D3D3V](https://github.com/C0D3D3V)
    - [Fix format bug](https://github.com/yt-dlp/yt-dlp/commit/89dbf0848370deaa55af88c3593a2a264124caf5) ([#6512](https://github.com/yt-dlp/yt-dlp/issues/6512)) by [C0D3D3V](https://github.com/C0D3D3V)
- **owncloud**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/c6d4b82a8b8bce59b1c9ce5e6d349ea428dac0a7) ([#6533](https://github.com/yt-dlp/yt-dlp/issues/6533)) by [C0D3D3V](https://github.com/C0D3D3V)
- **Parler**: [Rewrite extractor](https://github.com/yt-dlp/yt-dlp/commit/80ea6d3dea8483cddd39fc89b5ee1fc06670c33c) ([#6446](https://github.com/yt-dlp/yt-dlp/issues/6446)) by [JChris246](https://github.com/JChris246)
- **pgatour**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/3ae182ad89e1427ff7b1684d6a44ff93fa857a0c) ([#6613](https://github.com/yt-dlp/yt-dlp/issues/6613)) by [bashonly](https://github.com/bashonly)
- **playsuisse**: [Support new url format](https://github.com/yt-dlp/yt-dlp/commit/94627c5dde12a72766bdba36e056916c29c40ed1) ([#6528](https://github.com/yt-dlp/yt-dlp/issues/6528)) by [sbor23](https://github.com/sbor23)
- **polskieradio**: [Improve extractors](https://github.com/yt-dlp/yt-dlp/commit/738c90a463257634455ada3e5c18b714c531dede) ([#5948](https://github.com/yt-dlp/yt-dlp/issues/5948)) by [selfisekai](https://github.com/selfisekai)
- **pornez**: [Support new URL formats](https://github.com/yt-dlp/yt-dlp/commit/cbdf9408e6f1e35e98fd6477b3d6902df5b8a47f) ([#6792](https://github.com/yt-dlp/yt-dlp/issues/6792)) by [zhgwn](https://github.com/zhgwn)
- **pornhub**: [Set access cookies to fix extraction](https://github.com/yt-dlp/yt-dlp/commit/62beefa818c75c20b6941389bb197051554a5d41) ([#6685](https://github.com/yt-dlp/yt-dlp/issues/6685)) by [arobase-che](https://github.com/arobase-che), [Schmoaaaaah](https://github.com/Schmoaaaaah)
- **rai**: [Rewrite extractors](https://github.com/yt-dlp/yt-dlp/commit/c6d3f81a4077aaf9cffc6aa2d0dec92f38e74bb0) ([#5940](https://github.com/yt-dlp/yt-dlp/issues/5940)) by [danog](https://github.com/danog), [nixxo](https://github.com/nixxo)
- **recurbate**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/c2502cfed91415c7ccfff925fd3404d230046484) ([#6297](https://github.com/yt-dlp/yt-dlp/issues/6297)) by [mrscrapy](https://github.com/mrscrapy)
- **reddit**
    - [Add login support](https://github.com/yt-dlp/yt-dlp/commit/4d9280c9c853733534dda60486fa949bcca36c9e) ([#6950](https://github.com/yt-dlp/yt-dlp/issues/6950)) by [bashonly](https://github.com/bashonly)
    - [Support cookies and short URLs](https://github.com/yt-dlp/yt-dlp/commit/7a6f6f24592a8065376f11a58e44878807732cf6) ([#6825](https://github.com/yt-dlp/yt-dlp/issues/6825)) by [bashonly](https://github.com/bashonly)
- **rokfin**: [Re-construct manifest url](https://github.com/yt-dlp/yt-dlp/commit/7a6c8a0807941dd24fbf0d6172e811884f98e027) ([#6507](https://github.com/yt-dlp/yt-dlp/issues/6507)) by [vampirefrog](https://github.com/vampirefrog)
- **rottentomatoes**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/2d306c03d6f2697fcbabb7da35aa62cc078359d3) ([#6844](https://github.com/yt-dlp/yt-dlp/issues/6844)) by [JChris246](https://github.com/JChris246)
- **rozhlas**
    - [Extract manifest formats](https://github.com/yt-dlp/yt-dlp/commit/e4cf7741f9302b3faa092962f2895b55cb3d89bb) ([#6590](https://github.com/yt-dlp/yt-dlp/issues/6590)) by [bashonly](https://github.com/bashonly)
    - `MujRozhlas`: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/c2b801fea59628d5c873e06a0727fbf2051bbd1f) ([#7129](https://github.com/yt-dlp/yt-dlp/issues/7129)) by [stanoarn](https://github.com/stanoarn)
- **rtvc**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/9b30cd3dfce83c2f0201b28a7a3ef44ab9722664) ([#6578](https://github.com/yt-dlp/yt-dlp/issues/6578)) by [elyse0](https://github.com/elyse0)
- **rumble**
    - [Detect timeline format](https://github.com/yt-dlp/yt-dlp/commit/78bc1868ff3352108ab2911033d1ac67a55f151e) by [pukkandan](https://github.com/pukkandan)
    - [Fix videos without quality selection](https://github.com/yt-dlp/yt-dlp/commit/6994afc030d2a786d8032075ed71a14d7eac5a4f) by [pukkandan](https://github.com/pukkandan)
- **sbs**: [Overhaul extractor for new API](https://github.com/yt-dlp/yt-dlp/commit/6a765f135ccb654861336ea27a2c1c24ea8e286f) ([#6839](https://github.com/yt-dlp/yt-dlp/issues/6839)) by [bashonly](https://github.com/bashonly), [dirkf](https://github.com/dirkf), [vidiot720](https://github.com/vidiot720)
- **shemaroome**: [Pass `stream_key` header to downloader](https://github.com/yt-dlp/yt-dlp/commit/7bc92517463f5766e9d9b92c3823b5cf403c0e3d) ([#7224](https://github.com/yt-dlp/yt-dlp/issues/7224)) by [bashonly](https://github.com/bashonly)
- **sonyliv**: [Fix login with token](https://github.com/yt-dlp/yt-dlp/commit/4815d35c191e7d375b94492a6486dd2ba43a8954) ([#7223](https://github.com/yt-dlp/yt-dlp/issues/7223)) by [bashonly](https://github.com/bashonly)
- **stageplus**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/e5265dc6517478e589ee3c1ff0cb19bdf4e35ce1) ([#6838](https://github.com/yt-dlp/yt-dlp/issues/6838)) by [bashonly](https://github.com/bashonly)
- **stripchat**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/f9213f8a2d7ba46b912afe1dd3ce6bb700a33d72) ([#7306](https://github.com/yt-dlp/yt-dlp/issues/7306)) by [foreignBlade](https://github.com/foreignBlade)
- **substack**: [Fix extraction](https://github.com/yt-dlp/yt-dlp/commit/12037d8b0a578fcc78a5c8f98964e48ee6060e25) ([#7218](https://github.com/yt-dlp/yt-dlp/issues/7218)) by [bashonly](https://github.com/bashonly)
- **sverigesradio**: [Support slug URLs](https://github.com/yt-dlp/yt-dlp/commit/5ee9a7d6e18ceea956e831994cf11c423979354f) ([#7220](https://github.com/yt-dlp/yt-dlp/issues/7220)) by [bashonly](https://github.com/bashonly)
- **tagesschau**: [Fix single audio urls](https://github.com/yt-dlp/yt-dlp/commit/af7585c824a1e405bd8afa46d87b4be322edc93c) ([#6626](https://github.com/yt-dlp/yt-dlp/issues/6626)) by [flashdagger](https://github.com/flashdagger)
- **teamcoco**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/c459d45dd4d417fb80a52e1a04e607776a44baa4) ([#6437](https://github.com/yt-dlp/yt-dlp/issues/6437)) by [bashonly](https://github.com/bashonly)
- **telecaribe**: [Expand livestream support](https://github.com/yt-dlp/yt-dlp/commit/69b2f838d3d3e37dc17367ef64d978db1bea45cf) ([#6601](https://github.com/yt-dlp/yt-dlp/issues/6601)) by [bashonly](https://github.com/bashonly)
- **tencent**: [Fix fatal metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/971d901d129403e875a04dd92109507a03fbc070) ([#7219](https://github.com/yt-dlp/yt-dlp/issues/7219)) by [bashonly](https://github.com/bashonly)
- **thesun**: [Update `_VALID_URL`](https://github.com/yt-dlp/yt-dlp/commit/0181b9a1b31db3fde943f7cd3fe9662f23bff292) ([#6522](https://github.com/yt-dlp/yt-dlp/issues/6522)) by [hatienl0i261299](https://github.com/hatienl0i261299)
- **tiktok**
    - [Extract 1080p adaptive formats](https://github.com/yt-dlp/yt-dlp/commit/c2a1bdb00931969193f2a31ea27b9c66a07aaec2) ([#7228](https://github.com/yt-dlp/yt-dlp/issues/7228)) by [bashonly](https://github.com/bashonly)
    - [Fix and improve metadata extraction](https://github.com/yt-dlp/yt-dlp/commit/925936908a3c3ee0e508621db14696b9f6a8b563) ([#6777](https://github.com/yt-dlp/yt-dlp/issues/6777)) by [bashonly](https://github.com/bashonly)
    - [Fix mp3 formats](https://github.com/yt-dlp/yt-dlp/commit/8ceb07e870424c219dced8f4348729553f05c5cc) ([#6615](https://github.com/yt-dlp/yt-dlp/issues/6615)) by [bashonly](https://github.com/bashonly)
    - [Fix resolution extraction](https://github.com/yt-dlp/yt-dlp/commit/ab6057ec80aa75db6303b8206916d00c376c622c) ([#7237](https://github.com/yt-dlp/yt-dlp/issues/7237)) by [puc9](https://github.com/puc9)
    - [Improve `TikTokLive` extractor](https://github.com/yt-dlp/yt-dlp/commit/216bcb66d7dce0762767d751dad10650cb57da9d) ([#6520](https://github.com/yt-dlp/yt-dlp/issues/6520)) by [bashonly](https://github.com/bashonly)
- **triller**: [Support short URLs, detect removed videos](https://github.com/yt-dlp/yt-dlp/commit/33b737bedf8383c0d00d4e1d06a5273dcdfdb756) ([#6636](https://github.com/yt-dlp/yt-dlp/issues/6636)) by [bashonly](https://github.com/bashonly)
- **tv4**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/125ffaa1737dd04716f2f6fbb0595ad3eb7a4b1c) ([#5649](https://github.com/yt-dlp/yt-dlp/issues/5649)) by [dirkf](https://github.com/dirkf), [TxI5](https://github.com/TxI5)
- **tvp**: [Use new API](https://github.com/yt-dlp/yt-dlp/commit/0c7ce146e4d2a84e656d78f6857952bfd25ab389) ([#6989](https://github.com/yt-dlp/yt-dlp/issues/6989)) by [selfisekai](https://github.com/selfisekai)
- **tvplay**: [Remove outdated domains](https://github.com/yt-dlp/yt-dlp/commit/937264419f9bf375d5656785ae6e53282587c15d) ([#7106](https://github.com/yt-dlp/yt-dlp/issues/7106)) by [ivanskodje](https://github.com/ivanskodje)
- **twitch**
    - [Extract original size thumbnail](https://github.com/yt-dlp/yt-dlp/commit/80b732b7a9585b2a61e456dc0d2d014a439cbaee) ([#6629](https://github.com/yt-dlp/yt-dlp/issues/6629)) by [JC-Chung](https://github.com/JC-Chung)
    - [Fix `is_live`](https://github.com/yt-dlp/yt-dlp/commit/0551511b45f7847f40e4314aa9e624e80d086539) ([#6500](https://github.com/yt-dlp/yt-dlp/issues/6500)) by [elyse0](https://github.com/elyse0)
    - [Support mobile clips](https://github.com/yt-dlp/yt-dlp/commit/02312c03cf53eb1da24c9ad022ee79af26060733) ([#6699](https://github.com/yt-dlp/yt-dlp/issues/6699)) by [bepvte](https://github.com/bepvte)
    - [Update `_CLIENT_ID` and add extractor-arg](https://github.com/yt-dlp/yt-dlp/commit/01231feb142e80828985aabdec04ac608e3d43e2) ([#7200](https://github.com/yt-dlp/yt-dlp/issues/7200)) by [bashonly](https://github.com/bashonly)
    - vod: [Support links from schedule tab](https://github.com/yt-dlp/yt-dlp/commit/dbce5afa6bb61f6272ade613f2e9a3d66b88c7ea) ([#7071](https://github.com/yt-dlp/yt-dlp/issues/7071)) by [falbrechtskirchinger](https://github.com/falbrechtskirchinger)
- **twitter**
    - [Add login support](https://github.com/yt-dlp/yt-dlp/commit/d1795f4a6af99c976c9d3ea2dabe5cf4f8965d3c) ([#7258](https://github.com/yt-dlp/yt-dlp/issues/7258)) by [bashonly](https://github.com/bashonly)
    - [Default to GraphQL, handle auth errors](https://github.com/yt-dlp/yt-dlp/commit/147e62fc584c3ea6fdb09bb7a47905df68553a22) ([#6957](https://github.com/yt-dlp/yt-dlp/issues/6957)) by [bashonly](https://github.com/bashonly)
    - spaces: [Add `release_timestamp`](https://github.com/yt-dlp/yt-dlp/commit/1c16d9df5330819cc79ad588b24aa5b72765c168) ([#7186](https://github.com/yt-dlp/yt-dlp/issues/7186)) by [CeruleanSky](https://github.com/CeruleanSky)
- **urplay**: [Extract all subtitles](https://github.com/yt-dlp/yt-dlp/commit/7bcd4813215ac98daa4949af2ffc677c78307a38) ([#7309](https://github.com/yt-dlp/yt-dlp/issues/7309)) by [hoaluvn](https://github.com/hoaluvn)
- **voot**: [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/4f7b11cc1c1cebf598107e00cd7295588ed484da) ([#7227](https://github.com/yt-dlp/yt-dlp/issues/7227)) by [bashonly](https://github.com/bashonly)
- **vrt**: [Overhaul extractors](https://github.com/yt-dlp/yt-dlp/commit/1a7dcca378e80a387923ee05c250d8ba122441c6) ([#6244](https://github.com/yt-dlp/yt-dlp/issues/6244)) by [bashonly](https://github.com/bashonly), [bergoid](https://github.com/bergoid), [jeroenj](https://github.com/jeroenj)
- **weverse**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/b844a3f8b16500663e7ab6c6ec061cc9b30f71ac) ([#6711](https://github.com/yt-dlp/yt-dlp/issues/6711)) by [bashonly](https://github.com/bashonly) (With fixes in [fd5d93f](https://github.com/yt-dlp/yt-dlp/commit/fd5d93f7040f9776fd541f4e4079dad7d3b3fb4f))
- **wevidi**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/1ea15603d852971ed7d92f4de12808b27b3d9370) ([#6868](https://github.com/yt-dlp/yt-dlp/issues/6868)) by [truedread](https://github.com/truedread)
- **weyyak**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/6dc00acf0f1f1107a626c21befd1691403e6aeeb) ([#7124](https://github.com/yt-dlp/yt-dlp/issues/7124)) by [ItzMaxTV](https://github.com/ItzMaxTV)
- **whyp**: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/2c566ed14101673c651c08c306c30fa5b4010b85) ([#6803](https://github.com/yt-dlp/yt-dlp/issues/6803)) by [CoryTibbettsDev](https://github.com/CoryTibbettsDev)
- **wrestleuniverse**
    - [Fix cookies support](https://github.com/yt-dlp/yt-dlp/commit/c8561c6d03f025268d6d3972abeb47987c8d7cbb) by [bashonly](https://github.com/bashonly)
    - [Fix extraction, add login](https://github.com/yt-dlp/yt-dlp/commit/ef8fb7f029b816dfc95600727d84400591a3b5c5) ([#6982](https://github.com/yt-dlp/yt-dlp/issues/6982)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
- **wykop**: [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/aed945e1b9b7d3af2a907e1a12e6508cc81d6a20) ([#6140](https://github.com/yt-dlp/yt-dlp/issues/6140)) by [selfisekai](https://github.com/selfisekai)
- **ximalaya**: [Sort playlist entries](https://github.com/yt-dlp/yt-dlp/commit/8790ea7b2536332777bce68590386b1aa935fac7) ([#7292](https://github.com/yt-dlp/yt-dlp/issues/7292)) by [linsui](https://github.com/linsui)
- **YahooGyaOIE, YahooGyaOPlayerIE**: [Delete extractors due to website close](https://github.com/yt-dlp/yt-dlp/commit/68be95bd0ca3f76aa63c9812935bd826b3a42e53) ([#6218](https://github.com/yt-dlp/yt-dlp/issues/6218)) by [Lesmiscore](https://github.com/Lesmiscore)
- **yappy**: YappyProfile: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/6f69101dc912690338d32e2aab085c32e44eba3f) ([#7346](https://github.com/yt-dlp/yt-dlp/issues/7346)) by [7vlad7](https://github.com/7vlad7)
- **youku**: [Improve error message](https://github.com/yt-dlp/yt-dlp/commit/ef0848abd425dfda6db62baa8d72897eefb0007f) ([#6690](https://github.com/yt-dlp/yt-dlp/issues/6690)) by [carusocr](https://github.com/carusocr)
- **youporn**: [Extract m3u8 formats](https://github.com/yt-dlp/yt-dlp/commit/ddae33754ae1f32dd9c64cf895c47d20f6b5f336) by [pukkandan](https://github.com/pukkandan)
- **youtube**
    - [Add client name to `format_note` when `-v`](https://github.com/yt-dlp/yt-dlp/commit/c795c39f27244cbce846067891827e4847036441) ([#6254](https://github.com/yt-dlp/yt-dlp/issues/6254)) by [Lesmiscore](https://github.com/Lesmiscore), [pukkandan](https://github.com/pukkandan)
    - [Add extractor-arg `include_duplicate_formats`](https://github.com/yt-dlp/yt-dlp/commit/86cb922118b236306310a72657f70426c20e28bb) by [pukkandan](https://github.com/pukkandan)
    - [Bypass throttling for `-f17`](https://github.com/yt-dlp/yt-dlp/commit/c9abebb851e6188cb34b9eb744c1863dd46af919) by [pukkandan](https://github.com/pukkandan)
    - [Construct fragment list lazily](https://github.com/yt-dlp/yt-dlp/commit/2a23d92d9ec44a0168079e38bcf3d383e5c4c7bb) by [pukkandan](https://github.com/pukkandan) (With fixes in [e389d17](https://github.com/yt-dlp/yt-dlp/commit/e389d172b6f42e4f332ae679dc48543fb7b9b61d))
    - [Define strict uploader metadata mapping](https://github.com/yt-dlp/yt-dlp/commit/7666b93604b97e9ada981c6b04ccf5605dd1bd44) ([#6384](https://github.com/yt-dlp/yt-dlp/issues/6384)) by [coletdjnz](https://github.com/coletdjnz)
    - [Determine audio language using automatic captions](https://github.com/yt-dlp/yt-dlp/commit/ff9b0e071ffae5543cc309e6f9e647ac51e5846e) by [pukkandan](https://github.com/pukkandan)
    - [Extract `channel_is_verified`](https://github.com/yt-dlp/yt-dlp/commit/8213ce28a485e200f6a7e1af1434a987c8e702bd) ([#7213](https://github.com/yt-dlp/yt-dlp/issues/7213)) by [coletdjnz](https://github.com/coletdjnz)
    - [Extract `heatmap` data](https://github.com/yt-dlp/yt-dlp/commit/5caf30dbc34f10b0be60676fece635b5c59f0d72) ([#7100](https://github.com/yt-dlp/yt-dlp/issues/7100)) by [tntmod54321](https://github.com/tntmod54321)
    - [Extract more metadata for comments](https://github.com/yt-dlp/yt-dlp/commit/c35448b7b14113b35c4415dbfbf488c4731f006f) ([#7179](https://github.com/yt-dlp/yt-dlp/issues/7179)) by [coletdjnz](https://github.com/coletdjnz)
    - [Extract uploader metadata for feed/playlist items](https://github.com/yt-dlp/yt-dlp/commit/93e12ed76ef49252dc6869b59d21d0777e5e11af) by [coletdjnz](https://github.com/coletdjnz)
    - [Fix comment loop detection for pinned comments](https://github.com/yt-dlp/yt-dlp/commit/141a8dff98874a426d7fbe772e0a8421bb42656f) ([#6714](https://github.com/yt-dlp/yt-dlp/issues/6714)) by [coletdjnz](https://github.com/coletdjnz)
    - [Fix continuation loop with no comments](https://github.com/yt-dlp/yt-dlp/commit/18f8fba7c89a87f99cc3313a1795848867e84fff) ([#7148](https://github.com/yt-dlp/yt-dlp/issues/7148)) by [coletdjnz](https://github.com/coletdjnz)
    - [Fix parsing `comment_count`](https://github.com/yt-dlp/yt-dlp/commit/071670cbeaa01ddf2cc20a95ae6da25f8f086431) ([#6523](https://github.com/yt-dlp/yt-dlp/issues/6523)) by [nick-cd](https://github.com/nick-cd)
    - [Handle incomplete initial data from watch page](https://github.com/yt-dlp/yt-dlp/commit/607510b9f2f67bfe7d33d74031a5c1fe22a24862) ([#6510](https://github.com/yt-dlp/yt-dlp/issues/6510)) by [coletdjnz](https://github.com/coletdjnz)
    - [Ignore wrong fps of some formats](https://github.com/yt-dlp/yt-dlp/commit/97afb093d4cbe5df889145afa5f9ede4535e93e4) by [pukkandan](https://github.com/pukkandan)
    - [Misc cleanup](https://github.com/yt-dlp/yt-dlp/commit/14a14335b280766fbf5a469ae26836d6c1fe450a) by [coletdjnz](https://github.com/coletdjnz)
    - [Prioritize premium formats](https://github.com/yt-dlp/yt-dlp/commit/51a07b0dca4c079d58311c19b6d1c097c24bb021) by [pukkandan](https://github.com/pukkandan)
    - [Revert default formats to `https`](https://github.com/yt-dlp/yt-dlp/commit/c6786ff3baaf72a5baa4d56d34058e54cbcf8ceb) by [pukkandan](https://github.com/pukkandan)
    - [Support podcasts and releases tabs](https://github.com/yt-dlp/yt-dlp/commit/447afb9eaa65bc677e3245c83e53a8e69c174a3c) by [coletdjnz](https://github.com/coletdjnz)
    - [Support shorter relative time format](https://github.com/yt-dlp/yt-dlp/commit/2fb35f6004c7625f0dd493da4a5abf0690f7777c) ([#7191](https://github.com/yt-dlp/yt-dlp/issues/7191)) by [coletdjnz](https://github.com/coletdjnz)
    - music_search_url: [Extract title](https://github.com/yt-dlp/yt-dlp/commit/69a40e4a7f6caa5662527ebd2f3c4e8aa02857a2) ([#7102](https://github.com/yt-dlp/yt-dlp/issues/7102)) by [kangalio](https://github.com/kangalio)
- **zaiko**
    - [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/345b4c0aedd9d19898ce00d5cef35fe0d277a052) ([#7254](https://github.com/yt-dlp/yt-dlp/issues/7254)) by [c-basalt](https://github.com/c-basalt)
    - ZaikoETicket: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/5cc09c004bd5edbbada9b041c08a720cadc4f4df) ([#7347](https://github.com/yt-dlp/yt-dlp/issues/7347)) by [pzhlkj6612](https://github.com/pzhlkj6612)
- **zdf**: [Fix formats extraction](https://github.com/yt-dlp/yt-dlp/commit/ee0ed0338df328cd986f97315c8162b5a151476d) by [bashonly](https://github.com/bashonly)
- **zee5**: [Fix extraction of new content](https://github.com/yt-dlp/yt-dlp/commit/9d7fde89a40360396f0baa2ee8bf507f92108b32) ([#7280](https://github.com/yt-dlp/yt-dlp/issues/7280)) by [bashonly](https://github.com/bashonly)
- **zingmp3**: [Fix and improve extractors](https://github.com/yt-dlp/yt-dlp/commit/17d7ca84ea723c20668bd9bfa938be7ea0e64f6b) ([#6367](https://github.com/yt-dlp/yt-dlp/issues/6367)) by [hatienl0i261299](https://github.com/hatienl0i261299)
- **zoom**
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/79c77e85b70ae3b9942d5a88c14d021a9bd24222) ([#6741](https://github.com/yt-dlp/yt-dlp/issues/6741)) by [shreyasminocha](https://github.com/shreyasminocha)
    - [Fix share URL extraction](https://github.com/yt-dlp/yt-dlp/commit/90c1f5120694105496a6ad9e3ecfc6c25de6cae1) ([#6789](https://github.com/yt-dlp/yt-dlp/issues/6789)) by [bashonly](https://github.com/bashonly)

#### Downloader changes
- **curl**: [Fix progress reporting](https://github.com/yt-dlp/yt-dlp/commit/66aeaac9aa30b5959069ba84e53a5508232deb38) by [pukkandan](https://github.com/pukkandan)
- **fragment**: [Do not sleep between fragments](https://github.com/yt-dlp/yt-dlp/commit/424f3bf03305088df6e01d62f7311be8601ad3f4) by [pukkandan](https://github.com/pukkandan)

#### Postprocessor changes
- [Fix chapters if duration is not extracted](https://github.com/yt-dlp/yt-dlp/commit/01ddec7e661bf90dc4c34e6924eb9d7629886cef) ([#6037](https://github.com/yt-dlp/yt-dlp/issues/6037)) by [bashonly](https://github.com/bashonly)
- [Print newline for `--progress-template`](https://github.com/yt-dlp/yt-dlp/commit/13ff78095372fd98900a32572cf817994c07ccb5) by [pukkandan](https://github.com/pukkandan)
- **EmbedThumbnail, FFmpegMetadata**: [Fix error on attaching thumbnails and info json for mkv/mka](https://github.com/yt-dlp/yt-dlp/commit/0f0875ed555514f32522a0f30554fb08825d5124) ([#6647](https://github.com/yt-dlp/yt-dlp/issues/6647)) by [Lesmiscore](https://github.com/Lesmiscore)
- **FFmpegFixupM3u8PP**: [Check audio codec before fixup](https://github.com/yt-dlp/yt-dlp/commit/3f7e2bd80e3c5d8a1682f20a1b245fcd974f295d) ([#6778](https://github.com/yt-dlp/yt-dlp/issues/6778)) by [bashonly](https://github.com/bashonly)
- **FixupDuplicateMoov**: [Fix bug in triggering](https://github.com/yt-dlp/yt-dlp/commit/26010b5cec50193b98ad7845d1d77450f9f14c2b) by [pukkandan](https://github.com/pukkandan)

#### Misc. changes
- [Add automatic duplicate issue detection](https://github.com/yt-dlp/yt-dlp/commit/15b2d3db1d40b0437fca79d8874d392aa54b3cdd) by [pukkandan](https://github.com/pukkandan)
- **build**
    - [Fix macOS target](https://github.com/yt-dlp/yt-dlp/commit/44a79958f0b596ee71e1eb25f158610aada29d1b) by [Grub4K](https://github.com/Grub4K)
    - [Implement build verification using `--update-to`](https://github.com/yt-dlp/yt-dlp/commit/b73193c99aa23b135732408a5fcf655c68d731c6) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
    - [Pin `pyinstaller` version for MacOS](https://github.com/yt-dlp/yt-dlp/commit/427a8fafbb0e18c28d0ed7960be838d7b26b88d3) by [pukkandan](https://github.com/pukkandan)
    - [Various build workflow improvements](https://github.com/yt-dlp/yt-dlp/commit/c4efa0aefec8daef1de62fd1693f13edf3c8b03c) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K)
- **cleanup**
    - Miscellaneous
        - [6f2287c](https://github.com/yt-dlp/yt-dlp/commit/6f2287cb18cbfb27518f068d868fa9390fee78ad) by [pukkandan](https://github.com/pukkandan)
        - [ad54c91](https://github.com/yt-dlp/yt-dlp/commit/ad54c9130e793ce433bf9da334fa80df9f3aee58) by [freezboltz](https://github.com/freezboltz), [mikf](https://github.com/mikf), [pukkandan](https://github.com/pukkandan)
- **cleanup, utils**: [Split into submodules](https://github.com/yt-dlp/yt-dlp/commit/69bec6730ec9d724bcedeab199d9d684d61423ba) ([#7090](https://github.com/yt-dlp/yt-dlp/issues/7090)) by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
- **cli_to_api**: [Add script](https://github.com/yt-dlp/yt-dlp/commit/46f1370e9af6f8af8762f67e27e5acb8f0c48a47) by [pukkandan](https://github.com/pukkandan)
- **devscripts**: `make_changelog`: [Various improvements](https://github.com/yt-dlp/yt-dlp/commit/23c39a4beadee382060bb47fdaa21316ca707d38) by [Grub4K](https://github.com/Grub4K)
- **docs**: [Misc improvements](https://github.com/yt-dlp/yt-dlp/commit/c8bc203fbf3bb09914e53f0833eed622ab7edbb9) by [pukkandan](https://github.com/pukkandan)

### 2023.03.04

#### Extractor changes
- bilibili
    - [Fix for downloading wrong subtitles](https://github.com/yt-dlp/yt-dlp/commit/8a83baaf218ab89e6e7faa76b7c7be3a2ec19e3a) ([#6358](https://github.com/yt-dlp/yt-dlp/issues/6358)) by [LXYan2333](https://github.com/LXYan2333)
- ESPNcricinfo
    - [Handle new URL pattern](https://github.com/yt-dlp/yt-dlp/commit/640c934823fc2d1ec77ec932566078014058635f) ([#6321](https://github.com/yt-dlp/yt-dlp/issues/6321)) by [venkata-krishnas](https://github.com/venkata-krishnas)
- lefigaro
    - [Add extractors](https://github.com/yt-dlp/yt-dlp/commit/eb8fd6d044e8926532772b72be0645c6b8ecb3aa) ([#6309](https://github.com/yt-dlp/yt-dlp/issues/6309)) by [elyse0](https://github.com/elyse0)
- lumni
    - [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/1f8489cccbdc6e96027ef527b88717458f0900e8) ([#6302](https://github.com/yt-dlp/yt-dlp/issues/6302)) by [carusocr](https://github.com/carusocr)
- Prankcast
    - [Fix tags](https://github.com/yt-dlp/yt-dlp/commit/ed4cc4ea793314c50ae3f82e98248c1de1c25694) ([#6316](https://github.com/yt-dlp/yt-dlp/issues/6316)) by [columndeeply](https://github.com/columndeeply)
- rutube
    - [Extract chapters from description](https://github.com/yt-dlp/yt-dlp/commit/22ccd5420b3eb0782776071f12cccd1fedaa1fd0) ([#6345](https://github.com/yt-dlp/yt-dlp/issues/6345)) by [mushbite](https://github.com/mushbite)
- SportDeutschland
    - [Rewrite extractor](https://github.com/yt-dlp/yt-dlp/commit/45db357289b4e1eec09093c8bc5446520378f426) by [pukkandan](https://github.com/pukkandan)
- telecaribe
    - [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/b40471282286bd2b09c485bf79afd271d229272c) ([#6311](https://github.com/yt-dlp/yt-dlp/issues/6311)) by [elyse0](https://github.com/elyse0)
- tubetugraz
    - [Support `--twofactor` (#6424)](https://github.com/yt-dlp/yt-dlp/commit/f44cb4e77bb9be8be291d02ab6f79dc0b4c0d4a1) ([#6427](https://github.com/yt-dlp/yt-dlp/issues/6427)) by [Ferdi265](https://github.com/Ferdi265)
- tunein
    - [Fix extractors](https://github.com/yt-dlp/yt-dlp/commit/46580ced56c90b559885aded6aa8f46f20a9cdce) ([#6310](https://github.com/yt-dlp/yt-dlp/issues/6310)) by [elyse0](https://github.com/elyse0)
- twitch
    - [Update for GraphQL API changes](https://github.com/yt-dlp/yt-dlp/commit/4a6272c6d1bff89969b67cd22b26ebe6d7e72279) ([#6318](https://github.com/yt-dlp/yt-dlp/issues/6318)) by [elyse0](https://github.com/elyse0)
- twitter
    - [Fix retweet extraction](https://github.com/yt-dlp/yt-dlp/commit/cf605226521e99c89fc8dff26a319025810e63a0) ([#6422](https://github.com/yt-dlp/yt-dlp/issues/6422)) by [selfisekai](https://github.com/selfisekai)
- xvideos
    - quickies: [Add extractor](https://github.com/yt-dlp/yt-dlp/commit/283a0b5bc511f3b350eead4488158f50c20ec526) ([#6414](https://github.com/yt-dlp/yt-dlp/issues/6414)) by [Yakabuff](https://github.com/Yakabuff)

#### Misc. changes
- build
    - [Fix publishing to PyPI and homebrew](https://github.com/yt-dlp/yt-dlp/commit/55676fe498345a389a2539d8baaba958d6d61c3e) by [bashonly](https://github.com/bashonly)
    - [Only archive if `vars.ARCHIVE_REPO` is set](https://github.com/yt-dlp/yt-dlp/commit/08ff6d59f97b5f5f0128f6bf6fbef56fd836cc52) by [Grub4K](https://github.com/Grub4K)
- cleanup
    - Miscellaneous: [392389b](https://github.com/yt-dlp/yt-dlp/commit/392389b7df7b818f794b231f14dc396d4875fbad) by [pukkandan](https://github.com/pukkandan)
- devscripts
    - `make_changelog`: [Stop at `Release ...` commit](https://github.com/yt-dlp/yt-dlp/commit/7accdd9845fe7ce9d0aa5a9d16faaa489c1294eb) by [pukkandan](https://github.com/pukkandan)

### 2023.03.03

#### Important changes
- **A new release type has been added!**
    * [`nightly`](https://github.com/yt-dlp/yt-dlp/releases/tag/nightly) builds will be made after each push, containing the latest fixes (but also possibly bugs).
    * When using `--update`/`-U`, a release binary will only update to its current channel (either `stable` or `nightly`).
    * The `--update-to` option has been added allowing the user more control over program upgrades (or downgrades).
    * `--update-to` can change the release channel (`stable`, `nightly`) and also upgrade or downgrade to specific tags.
    * **Usage**: `--update-to CHANNEL`, `--update-to TAG`, `--update-to CHANNEL@TAG`
- **YouTube throttling fixes!**

#### Core changes
- [Add option `--break-match-filters`](https://github.com/yt-dlp/yt-dlp/commit/fe2ce85aff0aa03735fc0152bb8cb9c3d4ef0753) by [pukkandan](https://github.com/pukkandan)
- [Fix `--break-on-existing` with `--lazy-playlist`](https://github.com/yt-dlp/yt-dlp/commit/d21056f4cf0a1623daa107f9181074f5725ac436) by [pukkandan](https://github.com/pukkandan)
- dependencies
    - [Simplify `Cryptodome`](https://github.com/yt-dlp/yt-dlp/commit/65f6e807804d2af5e00f2aecd72bfc43af19324a) by [pukkandan](https://github.com/pukkandan)
- jsinterp
    - [Handle `Date` at epoch 0](https://github.com/yt-dlp/yt-dlp/commit/9acf1ee25f7ad3920ede574a9de95b8c18626af4) by [pukkandan](https://github.com/pukkandan)
- plugins
    - [Don't look in `.egg` directories](https://github.com/yt-dlp/yt-dlp/commit/b059188383eee4fa336ef728dda3ff4bb7335625) by [pukkandan](https://github.com/pukkandan)
- update
    - [Add option `--update-to`, including to nightly](https://github.com/yt-dlp/yt-dlp/commit/77df20f14cc9ed41dfe3a1fe2d77fd27f5365a94) ([#6220](https://github.com/yt-dlp/yt-dlp/issues/6220)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan)
- utils
    - `LenientJSONDecoder`: [Parse unclosed objects](https://github.com/yt-dlp/yt-dlp/commit/cc09083636ce21e58ff74f45eac2dbda507462b0) by [pukkandan](https://github.com/pukkandan)
    - `Popen`: [Shim undocumented `text_mode` property](https://github.com/yt-dlp/yt-dlp/commit/da8e2912b165005f76779a115a071cd6132ceedf) by [Grub4K](https://github.com/Grub4K)

#### Extractor changes
- [Fix DRM detection in m3u8](https://github.com/yt-dlp/yt-dlp/commit/43a3eaf96393b712d60cbcf5c6cb1e90ed7f42f5) by [pukkandan](https://github.com/pukkandan)
- generic
    - [Detect manifest links via extension](https://github.com/yt-dlp/yt-dlp/commit/b38cae49e6f4849c8ee2a774bdc3c1c647ae5f0e) by [bashonly](https://github.com/bashonly)
    - [Handle basic-auth when checking redirects](https://github.com/yt-dlp/yt-dlp/commit/8e9fe43cd393e69fa49b3d842aa3180c1d105b8f) by [pukkandan](https://github.com/pukkandan)
- GoogleDrive
    - [Fix some audio](https://github.com/yt-dlp/yt-dlp/commit/4d248e29d20d983ededab0b03d4fe69dff9eb4ed) by [pukkandan](https://github.com/pukkandan)
- iprima
    - [Fix extractor](https://github.com/yt-dlp/yt-dlp/commit/9fddc12ab022a31754e0eaa358fc4e1dfa974587) ([#6291](https://github.com/yt-dlp/yt-dlp/issues/6291)) by [std-move](https://github.com/std-move)
- mediastream
    - [Improve WinSports support](https://github.com/yt-dlp/yt-dlp/commit/2d5a8c5db2bd4ff1c2e45e00cd890a10f8ffca9e) ([#6401](https://github.com/yt-dlp/yt-dlp/issues/6401)) by [bashonly](https://github.com/bashonly)
- ntvru
    - [Extract HLS and DASH formats](https://github.com/yt-dlp/yt-dlp/commit/77d6d136468d0c23c8e79bc937898747804f585a) ([#6403](https://github.com/yt-dlp/yt-dlp/issues/6403)) by [bashonly](https://github.com/bashonly)
- tencent
    - [Add more formats and info](https://github.com/yt-dlp/yt-dlp/commit/18d295c9e0f95adc179eef345b7af64d6372db78) ([#5950](https://github.com/yt-dlp/yt-dlp/issues/5950)) by [Hill-98](https://github.com/Hill-98)
- yle_areena
    - [Extract non-Kaltura videos](https://github.com/yt-dlp/yt-dlp/commit/40d77d89027cd0e0ce31d22aec81db3e1d433900) ([#6402](https://github.com/yt-dlp/yt-dlp/issues/6402)) by [bashonly](https://github.com/bashonly)
- youtube
    - [Construct dash formats with `range` query](https://github.com/yt-dlp/yt-dlp/commit/5038f6d713303e0967d002216e7a88652401c22a) by [pukkandan](https://github.com/pukkandan) (With fixes in [f34804b](https://github.com/yt-dlp/yt-dlp/commit/f34804b2f920f62a6e893a14a9e2a2144b14dd23) by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz))
    - [Detect and break on looping comments](https://github.com/yt-dlp/yt-dlp/commit/7f51861b1820c37b157a239b1fe30628d907c034) ([#6301](https://github.com/yt-dlp/yt-dlp/issues/6301)) by [coletdjnz](https://github.com/coletdjnz)
    - [Extract channel `view_count` when `/about` tab is passed](https://github.com/yt-dlp/yt-dlp/commit/31e183557fcd1b937582f9429f29207c1261f501) by [pukkandan](https://github.com/pukkandan)

#### Misc. changes
- build
    - [Add `cffi` as a dependency for `yt_dlp_linux`](https://github.com/yt-dlp/yt-dlp/commit/776d1c3f0c9b00399896dd2e40e78e9a43218109) by [bashonly](https://github.com/bashonly)
    - [Automated builds and nightly releases](https://github.com/yt-dlp/yt-dlp/commit/29cb20bd563c02671b31dd840139e93dd37150a1) ([#6220](https://github.com/yt-dlp/yt-dlp/issues/6220)) by [bashonly](https://github.com/bashonly), [Grub4K](https://github.com/Grub4K) (With fixes in [bfc861a](https://github.com/yt-dlp/yt-dlp/commit/bfc861a91ee65c9b0ac169754f512e052c6827cf) by [pukkandan](https://github.com/pukkandan))
    - [Sign SHA files and release public key](https://github.com/yt-dlp/yt-dlp/commit/12647e03d417feaa9ea6a458bea5ebd747494a53) by [Grub4K](https://github.com/Grub4K)
- cleanup
    - [Fix `Changelog`](https://github.com/yt-dlp/yt-dlp/commit/17ca19ab60a6a13eb8a629c51442b5248b0d8394) by [pukkandan](https://github.com/pukkandan)
    - jsinterp: [Give functions names to help debugging](https://github.com/yt-dlp/yt-dlp/commit/b2e0343ba0fc5d8702e90f6ba2b71358e2677e0b) by [pukkandan](https://github.com/pukkandan)
    - Miscellaneous: [4815bbf](https://github.com/yt-dlp/yt-dlp/commit/4815bbfc41cf641e4a0650289dbff968cb3bde76), [5b28cef](https://github.com/yt-dlp/yt-dlp/commit/5b28cef72db3b531680d89c121631c73ae05354f) by [pukkandan](https://github.com/pukkandan)
- devscripts
    - [Script to generate changelog](https://github.com/yt-dlp/yt-dlp/commit/d400e261cf029a3f20d364113b14de973be75404) ([#6220](https://github.com/yt-dlp/yt-dlp/issues/6220)) by [Grub4K](https://github.com/Grub4K) (With fixes in [9344964](https://github.com/yt-dlp/yt-dlp/commit/93449642815a6973a4b09b289982ca7e1f961b5f))

### 2023.02.17

* Merge youtube-dl: Upto [commit/2dd6c6e](https://github.com/ytdl-org/youtube-dl/commit/2dd6c6e)
* Fix `--concat-playlist`
* Imply `--no-progress` when `--print`
* Improve default subtitle language selection by [sdht0](https://github.com/sdht0)
* Make `title` completely non-fatal
* Sanitize formats before sorting by [pukkandan](https://github.com/pukkandan)
* Support module level `__bool__` and `property`
* [dependencies] Standardize `Cryptodome` imports
* [hls] Allow extractors to provide AES key by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly)
* [ExtractAudio] Handle outtmpl without ext by [carusocr](https://github.com/carusocr)
* [extractor/common] Fix `_search_nuxt_data` by [LowSuggestion912](https://github.com/LowSuggestion912)
* [extractor/generic] Avoid catastrophic backtracking in KVS regex by [bashonly](https://github.com/bashonly)
* [jsinterp] Support `if` statements
* [plugins] Fix zip search paths
* [utils] `traverse_obj`:  Various improvements by [Grub4K](https://github.com/Grub4K)
* [utils] `traverse_obj`: Fix more bugs
* [utils] `traverse_obj`: Fix several behavioral problems by [Grub4K](https://github.com/Grub4K)
* [utils] Don't use Content-length with encoding by [felixonmars](https://github.com/felixonmars)
* [utils] Fix `time_seconds` to use the provided TZ by [Grub4K](https://github.com/Grub4K), [Lesmiscore](https://github.com/Lesmiscore)
* [utils] Fix race condition in `make_dir` by [aionescu](https://github.com/aionescu)
* [utils] Use local kernel32 for file locking on Windows by [Grub4K](https://github.com/Grub4K)
* [compat_utils] Improve `passthrough_module`
* [compat_utils] Simplify `EnhancedModule`
* [build] Update pyinstaller
* [pyinst] Fix for pyinstaller 5.8
* [devscripts] Provide `pyinstaller` hooks
* [devscripts/pyinstaller] Analyze sub-modules of `Cryptodome`
* [cleanup] Misc fixes and cleanup
* [extractor/anchorfm] Add episode extractor by [HobbyistDev](https://github.com/HobbyistDev), [bashonly](https://github.com/bashonly)
* [extractor/boxcast] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/ebay] Add extractor by [JChris246](https://github.com/JChris246)
* [extractor/hypergryph] Add extractor by [HobbyistDev](https://github.com/HobbyistDev), [bashonly](https://github.com/bashonly)
* [extractor/NZOnScreen] Add extractor by [gregsadetsky](https://github.com/gregsadetsky), [pukkandan](https://github.com/pukkandan)
* [extractor/rozhlas] Add extractor RozhlasVltavaIE by [amra](https://github.com/amra)
* [extractor/tempo] Add IVXPlayer extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/txxx] Add extractors by [chio0hai](https://github.com/chio0hai)
* [extractor/vocaroo] Add extractor by [SuperSonicHub1](https://github.com/SuperSonicHub1), [qbnu](https://github.com/qbnu)
* [extractor/wrestleuniverse] Add extractors by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly)
* [extractor/yappy] Add extractor by [HobbyistDev](https://github.com/HobbyistDev), [dirkf](https://github.com/dirkf)
* [extractor/youtube] **Fix `uploader_id` extraction** by [bashonly](https://github.com/bashonly)
* [extractor/youtube] Add hyperpipe instances by [Generator](https://github.com/Generator)
* [extractor/youtube] Handle `consent.youtube`
* [extractor/youtube] Support `/live/` URL
* [extractor/youtube] Update invidious and piped instances by [rohieb](https://github.com/rohieb)
* [extractor/91porn] Fix title and comment extraction by [pmitchell86](https://github.com/pmitchell86)
* [extractor/AbemaTV] Cache user token whenever appropriate by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/bfmtv] Support `rmc` prefix by [carusocr](https://github.com/carusocr)
* [extractor/biliintl] Add intro and ending chapters by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/clyp] Support `wav` by [qulaz](https://github.com/qulaz)
* [extractor/crunchyroll] Add intro chapter by [ByteDream](https://github.com/ByteDream)
* [extractor/crunchyroll] Better message for premium videos
* [extractor/crunchyroll] Fix incorrect premium-only error by [Grub4K](https://github.com/Grub4K)
* [extractor/DouyuTV] Use new API by [hatienl0i261299](https://github.com/hatienl0i261299)
* [extractor/embedly] Embedded links may be for other extractors
* [extractor/freesound] Workaround invalid URL in webpage by [rebane2001](https://github.com/rebane2001)
* [extractor/GoPlay] Use new API by [jeroenj](https://github.com/jeroenj)
* [extractor/Hidive] Fix subtitles and age-restriction by [chexxor](https://github.com/chexxor)
* [extractor/huya] Support HD streams by [felixonmars](https://github.com/felixonmars)
* [extractor/moviepilot] Fix extractor by [panatexxa](https://github.com/panatexxa)
* [extractor/nbc] Fix `NBC` and `NBCStations` extractors by [bashonly](https://github.com/bashonly)
* [extractor/nbc] Fix XML parsing by [bashonly](https://github.com/bashonly)
* [extractor/nebula] Remove broken cookie support by [hheimbuerger](https://github.com/hheimbuerger)
* [extractor/nfl] Add `NFLPlus` extractors by [bashonly](https://github.com/bashonly)
* [extractor/niconico] Add support for like history by [Matumo](https://github.com/Matumo), [pukkandan](https://github.com/pukkandan)
* [extractor/nitter] Update instance list by [OIRNOIR](https://github.com/OIRNOIR)
* [extractor/npo] Fix extractor and add HD support by [seproDev](https://github.com/seproDev)
* [extractor/odkmedia] Add `OnDemandChinaEpisodeIE` by [HobbyistDev](https://github.com/HobbyistDev), [pukkandan](https://github.com/pukkandan)
* [extractor/pornez] Handle relative URLs in iframe by [JChris246](https://github.com/JChris246)
* [extractor/radiko] Fix format sorting for Time Free by [road-master](https://github.com/road-master)
* [extractor/rcs] Fix extractors by [nixxo](https://github.com/nixxo), [pukkandan](https://github.com/pukkandan)
* [extractor/reddit] Support user posts by [OMEGARAZER](https://github.com/OMEGARAZER)
* [extractor/rumble] Fix format sorting by [pukkandan](https://github.com/pukkandan)
* [extractor/servus] Rewrite extractor by [Ashish0804](https://github.com/Ashish0804), [FrankZ85](https://github.com/FrankZ85), [StefanLobbenmeier](https://github.com/StefanLobbenmeier)
* [extractor/slideslive] Fix slides and chapters/duration by [bashonly](https://github.com/bashonly)
* [extractor/SportDeutschland] Fix extractor by [FriedrichRehren](https://github.com/FriedrichRehren)
* [extractor/Stripchat] Fix extractor by [JChris246](https://github.com/JChris246), [bashonly](https://github.com/bashonly)
* [extractor/tnaflix] Fix extractor by [bashonly](https://github.com/bashonly), [oxamun](https://github.com/oxamun)
* [extractor/tvp] Support `stream.tvp.pl` by [selfisekai](https://github.com/selfisekai)
* [extractor/twitter] Fix `--no-playlist` and add media `view_count` when using GraphQL by [Grub4K](https://github.com/Grub4K)
* [extractor/twitter] Fix graphql extraction on some tweets by [selfisekai](https://github.com/selfisekai)
* [extractor/vimeo] Fix `playerConfig` extraction by [LeoniePhiline](https://github.com/LeoniePhiline), [bashonly](https://github.com/bashonly)
* [extractor/viu] Add `ViuOTTIndonesiaIE` extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/vk] Fix playlists for new API by [the-marenga](https://github.com/the-marenga)
* [extractor/vlive] Replace with `VLiveWebArchiveIE` by [seproDev](https://github.com/seproDev)
* [extractor/ximalaya] Update album `_VALID_URL` by [carusocr](https://github.com/carusocr)
* [extractor/zdf] Use android API endpoint for UHD downloads by [seproDev](https://github.com/seproDev)
* [extractor/drtv] Fix bug in [ab4cbef](https://github.com/yt-dlp/yt-dlp/commit/ab4cbef) by [bashonly](https://github.com/bashonly)


### 2023.01.06

* Fix config locations by [Grub4K](https://github.com/Grub4K), [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [downloader/aria2c] Disable native progress
* [utils] `mimetype2ext`: `weba` is not standard
* [utils] `windows_enable_vt_mode`: Better error handling
* [build] Add minimal `pyproject.toml`
* [update] Fix updater file removal on windows by [Grub4K](https://github.com/Grub4K)
* [cleanup] Misc fixes and cleanup
* [extractor/aitube] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/drtv] Add series extractors by [FrederikNS](https://github.com/FrederikNS)
* [extractor/volejtv] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/xanimu] Add extractor by [JChris246](https://github.com/JChris246)
* [extractor/youtube] Retry manifest refresh for live-from-start by [mzhou](https://github.com/mzhou)
* [extractor/biliintl] Add `/media` to `VALID_URL` by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/biliIntl] Add fallback to `video_data` by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/crunchyroll:show] Add `language` to entries by [Chrissi2812](https://github.com/Chrissi2812)
* [extractor/joj] Fix extractor by [OndrejBakan](https://github.com/OndrejBakan), [pukkandan](https://github.com/pukkandan)
* [extractor/nbc] Update graphql query by [jacobtruman](https://github.com/jacobtruman)
* [extractor/reddit] Add subreddit as `channel_id` by [gschizas](https://github.com/gschizas)
* [extractor/tiktok] Add `TikTokLive` extractor by [JC-Chung](https://github.com/JC-Chung)

### 2023.01.02

* **Improve plugin architecture** by [Grub4K](https://github.com/Grub4K), [coletdjnz](https://github.com/coletdjnz), [flashdagger](https://github.com/flashdagger), [pukkandan](https://github.com/pukkandan)
    * Plugins can be loaded in any distribution of yt-dlp (binary, pip, source, etc.) and can be distributed and installed as packages. See [the readme](https://github.com/yt-dlp/yt-dlp/tree/05997b6e98e638d97d409c65bb5eb86da68f3b64#plugins) for more information
* Add `--compat-options 2021,2022`
    * This allows devs to change defaults and make other potentially breaking changes more easily. If you need everything to work exactly as-is, put Use `--compat 2022` in your config to guard against future compat changes.
* [downloader/aria2c] Native progress for aria2c via RPC by [Lesmiscore](https://github.com/Lesmiscore), [pukkandan](https://github.com/pukkandan)
* Merge youtube-dl: Upto [commit/195f22f](https://github.com/ytdl-org/youtube-dl/commit/195f22f6) by [Grub4K](https://github.com/Grub4K), [pukkandan](https://github.com/pukkandan)
* Add pre-processor stage `video`
* Let `--parse/replace-in-metadata` run at any post-processing stage
* Add `--enable-file-urls` by [coletdjnz](https://github.com/coletdjnz)
* Add new field `aspect_ratio`
* Add `ac4` to known codecs
* Add `weba` to known extensions
* [FFmpegVideoConvertor] Add `gif` to `--recode-video`
* Add message when there are no subtitles/thumbnails
* Deprioritize HEVC-over-FLV formats by [Lesmiscore](https://github.com/Lesmiscore)
* Make early reject of `--match-filter` stricter
* Fix `--cookies-from-browser` CLI parsing
* Fix `original_url` in playlists
* Fix bug in writing playlist info-json
* Fix bugs in `PlaylistEntries`
* [downloader/ffmpeg] Fix headers for video+audio formats by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly)
* [extractor] Add a way to distinguish IEs that returns only videos
* [extractor] Implement universal format sorting and deprecate `_sort_formats`
* [extractor] Let `_extract_format` functions obey `--ignore-no-formats`
* [extractor/generic] Add `fragment_query` extractor arg for DASH and HLS by [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan)
* [extractor/generic] Decode unicode-escaped embed URLs by [bashonly](https://github.com/bashonly)
* [extractor/generic] Don't report redirect to https
* [extractor/generic] Fix JSON LD manifest extraction by [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan)
* [extractor/generic] Use `Accept-Encoding: identity` for initial request by [coletdjnz](https://github.com/coletdjnz)
* [FormatSort] Add `mov` to `vext`
* [jsinterp] Escape regex that looks like nested set
* [webvtt] Handle premature EOF by [flashdagger](https://github.com/flashdagger)
* [utils] `classproperty`: Add cache support
* [utils] `get_exe_version`: Detect broken executables by [dirkf](https://github.com/dirkf), [pukkandan](https://github.com/pukkandan)
* [utils] `js_to_json`: Fix bug in [f55523c](https://github.com/yt-dlp/yt-dlp/commit/f55523c) by [ChillingPepper](https://github.com/ChillingPepper), [pukkandan](https://github.com/pukkandan)
* [utils] Make `ExtractorError` mutable
* [utils] Move `FileDownloader.parse_bytes` into utils
* [utils] Move format sorting code into `utils`
* [utils] `windows_enable_vt_mode`: Proper implementation by [Grub4K](https://github.com/Grub4K)
* [update] Workaround [#5632](https://github.com/yt-dlp/yt-dlp/issues/5632)
* [docs] Improvements
* [cleanup] Misc fixes and cleanup
* [cleanup] Use `random.choices` by [freezboltz](https://github.com/freezboltz)
* [extractor/airtv] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/amazonminitv] Add extractors by [GautamMKGarg](https://github.com/GautamMKGarg), [nyuszika7h](https://github.com/nyuszika7h)
* [extractor/beatbump] Add extractors by [Bobscorn](https://github.com/Bobscorn), [pukkandan](https://github.com/pukkandan)
* [extractor/europarl] Add EuroParlWebstream extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/kanal2] Add extractor by [bashonly](https://github.com/bashonly), [glensc](https://github.com/glensc), [pukkandan](https://github.com/pukkandan)
* [extractor/kankanews] Add extractor by [synthpop123](https://github.com/synthpop123)
* [extractor/kick] Add extractor by [bashonly](https://github.com/bashonly)
* [extractor/mediastream] Add extractor by [HobbyistDev](https://github.com/HobbyistDev), [elyse0](https://github.com/elyse0)
* [extractor/noice] Add NoicePodcast extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/oneplace] Add OnePlacePodcast extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/rumble] Add RumbleIE extractor by [flashdagger](https://github.com/flashdagger)
* [extractor/screencastify] Add extractor by [bashonly](https://github.com/bashonly)
* [extractor/trtcocuk] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/Veoh] Add user extractor by [tntmod54321](https://github.com/tntmod54321)
* [extractor/videoken] Add extractors by [bashonly](https://github.com/bashonly)
* [extractor/webcamerapl] Add extractor by [milkknife](https://github.com/milkknife)
* [extractor/amazon] Add `AmazonReviews` extractor by [bashonly](https://github.com/bashonly)
* [extractor/netverse] Add `NetverseSearch` extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/vimeo] Add `VimeoProIE` by [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan)
* [extractor/xiami] Remove extractors by [synthpop123](https://github.com/synthpop123)
* [extractor/youtube] Add `piped.video` by [Bnyro](https://github.com/Bnyro)
* [extractor/youtube] Consider language in format de-duplication
* [extractor/youtube] Extract DRC formats
* [extractor/youtube] Fix `ytuser:`
* [extractor/youtube] Fix bug in handling of music URLs
* [extractor/youtube] Subtitles cannot be translated to `und`
* [extractor/youtube:tab] Extract metadata from channel items by [coletdjnz](https://github.com/coletdjnz)
* [extractor/ARD] Add vtt subtitles by [CapacitorSet](https://github.com/CapacitorSet)
* [extractor/ArteTV] Extract chapters by [bashonly](https://github.com/bashonly), [iw0nderhow](https://github.com/iw0nderhow)
* [extractor/bandcamp] Add `album_artist` by [stelcodes](https://github.com/stelcodes)
* [extractor/bilibili] Fix `--no-playlist` for anthology
* [extractor/bilibili] Improve `_VALID_URL` by [skbeh](https://github.com/skbeh)
* [extractor/biliintl:series] Make partial download of series faster
* [extractor/BiliLive] Fix extractor
* [extractor/brightcove] Add `BrightcoveNewBaseIE` and fix embed extraction
* [extractor/cda] Support premium and misc improvements by [selfisekai](https://github.com/selfisekai)
* [extractor/ciscowebex] Support password-protected videos by [damianoamatruda](https://github.com/damianoamatruda)
* [extractor/curiositystream] Fix auth by [mnn](https://github.com/mnn)
* [extractor/embedly] Handle vimeo embeds
* [extractor/fifa] Fix Preplay extraction by [dirkf](https://github.com/dirkf)
* [extractor/foxsports] Fix extractor by [bashonly](https://github.com/bashonly)
* [extractor/gronkh] Fix `_VALID_URL` by [muddi900](https://github.com/muddi900)
* [extractor/hotstar] Improve format metadata
* [extractor/iqiyi] Fix `Iq` JS regex by [bashonly](https://github.com/bashonly)
* [extractor/la7] Improve extractor by [nixxo](https://github.com/nixxo)
* [extractor/mediaset] Better embed detection and error messages by [nixxo](https://github.com/nixxo)
* [extractor/mixch] Support `--wait-for-video`
* [extractor/naver] Improve `_VALID_URL` for `NaverNowIE` by [bashonly](https://github.com/bashonly)
* [extractor/naver] Treat fan subtitles as separate language
* [extractor/netverse] Extract comments by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/nosnl] Add support for /video by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/odnoklassniki] Extract subtitles by [bashonly](https://github.com/bashonly)
* [extractor/pinterest] Fix extractor by [bashonly](https://github.com/bashonly)
* [extractor/plutotv] Fix videos with non-zero start by [digitall](https://github.com/digitall)
* [extractor/polskieradio] Adapt to next.js redesigns by [selfisekai](https://github.com/selfisekai)
* [extractor/reddit] Add vcodec to fallback format by [chengzhicn](https://github.com/chengzhicn)
* [extractor/reddit] Extract crossposted media by [bashonly](https://github.com/bashonly)
* [extractor/reddit] Extract video embeds in text posts by [bashonly](https://github.com/bashonly)
* [extractor/rutube] Support private videos by [mexus](https://github.com/mexus)
* [extractor/sibnet] Separate from VKIE
* [extractor/slideslive] Fix extractor by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly)
* [extractor/slideslive] Support embeds and slides by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan)
* [extractor/soundcloud] Support user permalink by [nosoop](https://github.com/nosoop)
* [extractor/spankbang] Fix extractor by [JChris246](https://github.com/JChris246)
* [extractor/stv] Detect DRM
* [extractor/swearnet] Fix description bug
* [extractor/tencent] Fix geo-restricted video by [elyse0](https://github.com/elyse0)
* [extractor/tiktok] Fix subs, `DouyinIE`, improve `_VALID_URL` by [bashonly](https://github.com/bashonly)
* [extractor/tiktok] Update `_VALID_URL`, add `api_hostname` arg by [bashonly](https://github.com/bashonly)
* [extractor/tiktok] Update API hostname by [redraskal](https://github.com/redraskal)
* [extractor/twitcasting] Fix videos with password by [Spicadox](https://github.com/Spicadox), [bashonly](https://github.com/bashonly)
* [extractor/twitter] Heed `--no-playlist` for multi-video tweets by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly)
* [extractor/twitter] Refresh guest token when expired by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly)
* [extractor/twitter:spaces] Add `Referer` to m3u8 by [nixxo](https://github.com/nixxo)
* [extractor/udemy] Fix lectures that have no URL and detect DRM
* [extractor/unsupported] Add more URLs
* [extractor/urplay] Support for audio-only formats by [barsnick](https://github.com/barsnick)
* [extractor/wistia] Improve extension detection by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan)
* [extractor/yle_areena] Support restricted videos by [docbender](https://github.com/docbender)
* [extractor/youku] Fix extractor by [KurtBestor](https://github.com/KurtBestor)
* [extractor/youporn] Fix metadata by [marieell](https://github.com/marieell)
* [extractor/redgifs] Fix bug in [8c188d5](https://github.com/yt-dlp/yt-dlp/commit/8c188d5d09177ed213a05c900d3523867c5897fd)


### 2022.11.11

* Merge youtube-dl: Upto [commit/de39d12](https://github.com/ytdl-org/youtube-dl/commit/de39d128)
* Backport SSL configuration from Python 3.10 by [coletdjnz](https://github.com/coletdjnz)
* Do more processing in `--flat-playlist`
* Fix `--list` options not implying `-s` in some cases by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly)
* Fix end time of clips by [cruel-efficiency](https://github.com/cruel-efficiency)
* Fix for `formats=None`
* Write API params in debug head
* [outtmpl] Ensure ASCII in json and add option for Unicode
* [SponsorBlock] Add `type` field, obey `--retry-sleep extractor`, relax duration check for large segments
* [SponsorBlock] **Support `chapter` category** by [ajayyy](https://github.com/ajayyy), [pukkandan](https://github.com/pukkandan)
* [ThumbnailsConvertor] Fix filename escaping by [dirkf](https://github.com/dirkf), [pukkandan](https://github.com/pukkandan)
* [ModifyChapters] Handle the entire video being marked for removal
* [embedthumbnail] Fix thumbnail name in mp3 by [How-Bout-No](https://github.com/How-Bout-No)
* [downloader/fragment] HLS download can continue without first fragment
* [cookies] Improve `LenientSimpleCookie` by [Grub4K](https://github.com/Grub4K)
* [jsinterp] Improve separating regex
* [extractor/common] Fix `fatal=False` for `_search_nuxt_data`
* [extractor/common] Improve `_generic_title`
* [extractor/common] Fix `json_ld` type checks by [Grub4K](https://github.com/Grub4K)
* [extractor/generic] Separate embed extraction into own function
* [extractor/generic:quoted-html] Add extractor by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor/unsupported] Raise error on known DRM-only sites by [coletdjnz](https://github.com/coletdjnz)
* [utils] `js_to_json`: Improve escape handling by [Grub4K](https://github.com/Grub4K)
* [utils] `strftime_or_none`: Workaround Python bug on Windows
* [utils] `traverse_obj`: Always return list when branching, allow `re.Match` objects by [Grub4K](https://github.com/Grub4K)
* [build, test] Harden workflows' security by [sashashura](https://github.com/sashashura)
* [build] `py2exe`: Migrate to freeze API by [SG5](https://github.com/SG5), [pukkandan](https://github.com/pukkandan)
* [build] Create `armv7l` and `aarch64` releases by [MrOctopus](https://github.com/MrOctopus), [pukkandan](https://github.com/pukkandan)
* [build] Make linux binary truly standalone using `conda` by [mlampe](https://github.com/mlampe)
* [build] Replace `set-output` with `GITHUB_OUTPUT` by [Lesmiscore](https://github.com/Lesmiscore)
* [update] Use error code `100` for update errors
* [compat] Fix `shutils.move` in restricted ACL mode on BSD by [ClosedPort22](https://github.com/ClosedPort22), [pukkandan](https://github.com/pukkandan)
* [docs, devscripts] Document `pyinst`'s argument passthrough by [jahway603](https://github.com/jahway603)
* [test] Allow `extract_flat` in download tests by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [cleanup] Misc fixes and cleanup by [pukkandan](https://github.com/pukkandan), [Alienmaster](https://github.com/Alienmaster)
* [extractor/aeon] Add extractor by [DoubleCouponDay](https://github.com/DoubleCouponDay)
* [extractor/agora] Add extractors by [selfisekai](https://github.com/selfisekai)
* [extractor/camsoda] Add extractor by [zulaport](https://github.com/zulaport)
* [extractor/cinetecamilano] Add extractor by [timendum](https://github.com/timendum)
* [extractor/deuxm] Add extractors by [CrankDatSouljaBoy](https://github.com/CrankDatSouljaBoy)
* [extractor/genius] Add extractors by [bashonly](https://github.com/bashonly)
* [extractor/japandiet] Add extractors by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/listennotes] Add extractor by [lksj](https://github.com/lksj), [pukkandan](https://github.com/pukkandan)
* [extractor/nos.nl] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/oftv] Add extractors by [DoubleCouponDay](https://github.com/DoubleCouponDay)
* [extractor/podbayfm] Add extractor by [schnusch](https://github.com/schnusch)
* [extractor/qingting] Add extractor by [bashonly](https://github.com/bashonly), [changren-wcr](https://github.com/changren-wcr)
* [extractor/screen9] Add extractor by [tpikonen](https://github.com/tpikonen)
* [extractor/swearnet] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/YleAreena] Add extractor by [pukkandan](https://github.com/pukkandan), [vitkhab](https://github.com/vitkhab)
* [extractor/zeenews] Add extractor by [m4tu4g](https://github.com/m4tu4g), [pukkandan](https://github.com/pukkandan)
* [extractor/youtube:tab] **Update tab handling for redesign** by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
    * Channel URLs download all uploads of the channel as multiple playlists, separated by tab
* [extractor/youtube] Differentiate between no comments and disabled comments by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube] Extract `concurrent_view_count` for livestreams by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube] Fix `duration` for premieres by [nosoop](https://github.com/nosoop)
* [extractor/youtube] Fix `live_status` by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor/youtube] Ignore incomplete data error for comment replies by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube] Improve chapter parsing from description
* [extractor/youtube] Mark videos as fully watched by [bsun0000](https://github.com/bsun0000)
* [extractor/youtube] Update piped instances by [Generator](https://github.com/Generator)
* [extractor/youtube] Update playlist metadata extraction for new layout by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube:tab] Fix video metadata from tabs by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube:tab] Let `approximate_date` return timestamp
* [extractor/americastestkitchen] Fix extractor by [bashonly](https://github.com/bashonly)
* [extractor/bbc] Support onion domains by [DoubleCouponDay](https://github.com/DoubleCouponDay)
* [extractor/bilibili] Add chapters and misc cleanup by [lockmatrix](https://github.com/lockmatrix), [pukkandan](https://github.com/pukkandan)
* [extractor/bilibili] Fix BilibiliIE and Bangumi extractors by [lockmatrix](https://github.com/lockmatrix), [pukkandan](https://github.com/pukkandan)
* [extractor/bitchute] Better error for geo-restricted videos by [flashdagger](https://github.com/flashdagger)
* [extractor/bitchute] Improve `BitChuteChannelIE` by [flashdagger](https://github.com/flashdagger), [pukkandan](https://github.com/pukkandan)
* [extractor/bitchute] Simplify extractor by [flashdagger](https://github.com/flashdagger), [pukkandan](https://github.com/pukkandan)
* [extractor/cda] Support login through API by [selfisekai](https://github.com/selfisekai)
* [extractor/crunchyroll] Beta is now the only layout by [tejing1](https://github.com/tejing1)
* [extractor/detik] Avoid unnecessary extraction
* [extractor/doodstream] Remove extractor
* [extractor/dplay] Add MotorTrendOnDemand extractor by [bashonly](https://github.com/bashonly)
* [extractor/epoch] Support videos without data-trailer by [gibson042](https://github.com/gibson042), [pukkandan](https://github.com/pukkandan)
* [extractor/fox] Extract thumbnail by [vitkhab](https://github.com/vitkhab)
* [extractor/foxnews] Add `FoxNewsVideo` extractor
* [extractor/hotstar] Add season support by [m4tu4g](https://github.com/m4tu4g)
* [extractor/hotstar] Refactor v1 API calls
* [extractor/iprima] Make json+ld non-fatal by [bashonly](https://github.com/bashonly)
* [extractor/iq] Increase phantomjs timeout
* [extractor/kaltura] Support playlists by [jwoglom](https://github.com/jwoglom), [pukkandan](https://github.com/pukkandan)
* [extractor/lbry] Authenticate with cookies by [flashdagger](https://github.com/flashdagger)
* [extractor/livestreamfails] Support posts by [invertico](https://github.com/invertico)
* [extractor/mlb] Add `MLBArticle` extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/mxplayer] Improve extractor by [m4tu4g](https://github.com/m4tu4g)
* [extractor/niconico] Always use HTTPS for requests
* [extractor/nzherald] Support new video embed by [coletdjnz](https://github.com/coletdjnz)
* [extractor/odnoklassniki] Support boosty.to embeds by [Lesmiscore](https://github.com/Lesmiscore), [megapro17](https://github.com/megapro17), [pukkandan](https://github.com/pukkandan)
* [extractor/paramountplus] Update API token by [bashonly](https://github.com/bashonly)
* [extractor/reddit] Add fallback format by [bashonly](https://github.com/bashonly)
* [extractor/redgifs] Fix extractors by [bashonly](https://github.com/bashonly), [pukkandan](https://github.com/pukkandan)
* [extractor/redgifs] Refresh auth token for 401 by [endotronic](https://github.com/endotronic), [pukkandan](https://github.com/pukkandan)
* [extractor/rumble] Add HLS formats and extract more metadata by [flashdagger](https://github.com/flashdagger)
* [extractor/sbs] Improve `_VALID_URL` by [bashonly](https://github.com/bashonly)
* [extractor/skyit] Fix extractors by [nixxo](https://github.com/nixxo)
* [extractor/stripchat] Fix hostname for HLS stream by [zulaport](https://github.com/zulaport)
* [extractor/stripchat] Improve error message by [freezboltz](https://github.com/freezboltz)
* [extractor/telegram] Add playlist support and more metadata by [bashonly](https://github.com/bashonly), [bsun0000](https://github.com/bsun0000)
* [extractor/Tnaflix] Fix for HTTP 500 by [SG5](https://github.com/SG5), [pukkandan](https://github.com/pukkandan)
* [extractor/tubitv] Better DRM detection by [bashonly](https://github.com/bashonly)
* [extractor/tvp] Update extractors by [selfisekai](https://github.com/selfisekai)
* [extractor/twitcasting] Fix `data-movie-playlist` extraction by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/twitter] Add onion site to `_VALID_URL` by [DoubleCouponDay](https://github.com/DoubleCouponDay)
* [extractor/twitter] Add Spaces extractor and GraphQL API by [Grub4K](https://github.com/Grub4K), [bashonly](https://github.com/bashonly), [nixxo](https://github.com/nixxo), [pukkandan](https://github.com/pukkandan)
* [extractor/twitter] Support multi-video posts by [Grub4K](https://github.com/Grub4K)
* [extractor/uktvplay] Fix `_VALID_URL`
* [extractor/viu] Support subtitles of on-screen text by [tkgmomosheep](https://github.com/tkgmomosheep)
* [extractor/VK] Fix playlist URLs by [the-marenga](https://github.com/the-marenga)
* [extractor/vlive] Extract `release_timestamp`
* [extractor/voot] Improve `_VALID_URL` by [freezboltz](https://github.com/freezboltz)
* [extractor/wordpress:mb.miniAudioPlayer] Add embed extractor by [coletdjnz](https://github.com/coletdjnz)
* [extractor/YoutubeWebArchive] Improve metadata extraction by [coletdjnz](https://github.com/coletdjnz)
* [extractor/zee5] Improve `_VALID_URL` by [m4tu4g](https://github.com/m4tu4g)
* [extractor/zenyandex] Fix extractors by [lksj](https://github.com/lksj), [puc9](https://github.com/puc9), [pukkandan](https://github.com/pukkandan)


### 2022.10.04

* Allow a `set` to be passed as `download_archive` by [pukkandan](https://github.com/pukkandan), [bashonly](https://github.com/bashonly)
* Allow open ranges for time ranges by [Lesmiscore](https://github.com/Lesmiscore)
* Allow plugin extractors to replace the built-in ones
* Don't download entire video when no matching `--download-sections`
* Fix `--config-location -`
* Improve [5736d79](https://github.com/yt-dlp/yt-dlp/pull/5044/commits/5736d79172c47ff84740d5720467370a560febad)
* Fix for when playlists don't have `webpage_url`
* Support environment variables in `--ffmpeg-location`
* Workaround `libc_ver` not be available on Windows Store version of Python
* [outtmpl] Curly braces to filter keys by [pukkandan](https://github.com/pukkandan)
* [outtmpl] Make `%s` work in strfformat for all systems
* [jsinterp] Workaround operator associativity issue
* [cookies] Let `_get_mac_keyring_password` fail gracefully
* [cookies] Parse cookies leniently by [Grub4K](https://github.com/Grub4K)
* [phantomjs] Fix bug in [587021c](https://github.com/yt-dlp/yt-dlp/commit/587021cd9f717181b44e881941aca3f8d753758b) by [elyse0](https://github.com/elyse0)
* [downloader/aria2c] Fix filename containing leading whitespace by [std-move](https://github.com/std-move)
* [downloader/ism] Support ec-3 codec by [nixxo](https://github.com/nixxo)
* [extractor] Fix `fatal=False` in `RetryManager`
* [extractor] Improve json-ld extraction
* [extractor] Make `_search_json` able to parse lists
* [extractor] Escape `%` in `representation_id` of m3u8
* [extractor/generic] Pass through referer from json-ld
* [utils] `base_url`: URL paths can contain `&` by [elyse0](https://github.com/elyse0)
* [utils] `js_to_json`: Improve
* [utils] `Popen.run`: Fix default return in binary mode
* [utils] `traverse_obj`: Rewrite, document and add tests by [Grub4K](https://github.com/Grub4K)
* [devscripts] `make_lazy_extractors`: Fix for Docker by [josanabr](https://github.com/josanabr)
* [docs] Misc Improvements
* [cleanup] Misc fixes and cleanup by [pukkandan](https://github.com/pukkandan), [gamer191](https://github.com/gamer191)
* [extractor/24tv.ua] Add extractors by [coletdjnz](https://github.com/coletdjnz)
* [extractor/BerufeTV] Add extractor by [Fabi019](https://github.com/Fabi019)
* [extractor/booyah] Add extractor by [HobbyistDev](https://github.com/HobbyistDev), [elyse0](https://github.com/elyse0)
* [extractor/bundesliga] Add extractor by [Fabi019](https://github.com/Fabi019)
* [extractor/GoPlay] Add extractor by [CNugteren](https://github.com/CNugteren), [basrieter](https://github.com/basrieter), [jeroenj](https://github.com/jeroenj)
* [extractor/iltalehti] Add extractor by [tpikonen](https://github.com/tpikonen)
* [extractor/IsraelNationalNews] Add extractor by [Bobscorn](https://github.com/Bobscorn)
* [extractor/mediaworksnzvod] Add extractor by [coletdjnz](https://github.com/coletdjnz)
* [extractor/MicrosoftEmbed] Add extractor by [DoubleCouponDay](https://github.com/DoubleCouponDay)
* [extractor/nbc] Add NBCStations extractor by [bashonly](https://github.com/bashonly)
* [extractor/onenewsnz] Add extractor by [coletdjnz](https://github.com/coletdjnz)
* [extractor/prankcast] Add extractor by [HobbyistDev](https://github.com/HobbyistDev), [columndeeply](https://github.com/columndeeply)
* [extractor/Smotrim] Add extractor by [Lesmiscore](https://github.com/Lesmiscore), [nikita-moor](https://github.com/nikita-moor)
* [extractor/tencent] Add Iflix extractor by [elyse0](https://github.com/elyse0)
* [extractor/unscripted] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/adobepass] Add MSO AlticeOne (Optimum TV) by [CplPwnies](https://github.com/CplPwnies)
* [extractor/youtube] **Download `post_live` videos from start** by [Lesmiscore](https://github.com/Lesmiscore), [pukkandan](https://github.com/pukkandan)
* [extractor/youtube] Add support for Shorts audio pivot feed by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor/youtube] Detect `lazy-load-for-videos` embeds
* [extractor/youtube] Do not warn on duplicate chapters
* [extractor/youtube] Fix video like count extraction by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube] Support changing extraction language by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube:tab] Improve continuation items extraction
* [extractor/youtube:tab] Support `reporthistory` page
* [extractor/amazonstore] Fix JSON extraction by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor/amazonstore] Retry to avoid captcha page by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/animeondemand] Remove extractor by [TokyoBlackHole](https://github.com/TokyoBlackHole)
* [extractor/anvato] Fix extractor and refactor by [bashonly](https://github.com/bashonly)
* [extractor/artetv] Remove duplicate stream urls by [Grub4K](https://github.com/Grub4K)
* [extractor/audioboom] Support direct URLs and refactor by [pukkandan](https://github.com/pukkandan), [tpikonen](https://github.com/tpikonen)
* [extractor/bandcamp] Extract `uploader_url`
* [extractor/bilibili] Add space.bilibili extractors by [lockmatrix](https://github.com/lockmatrix)
* [extractor/BilibiliSpace] Fix extractor and better error message by [lockmatrix](https://github.com/lockmatrix)
* [extractor/BiliIntl] Support uppercase lang in `_VALID_URL` by [coletdjnz](https://github.com/coletdjnz)
* [extractor/BiliIntlSeries] Fix `_VALID_URL`
* [extractor/bongacams] Update `_VALID_URL` by [0xGodspeed](https://github.com/0xGodspeed)
* [extractor/crunchyroll:beta] Improve handling of hardsubs by [Grub4K](https://github.com/Grub4K)
* [extractor/detik] Generalize extractors by [HobbyistDev](https://github.com/HobbyistDev), [coletdjnz](https://github.com/coletdjnz)
* [extractor/dplay:italy] Add default authentication by [Timendum](https://github.com/Timendum)
* [extractor/heise] Fix extractor by [coletdjnz](https://github.com/coletdjnz)
* [extractor/holodex] Fix `_VALID_URL` by [LiviaMedeiros](https://github.com/LiviaMedeiros)
* [extractor/hrfensehen] Fix extractor by [snapdgn](https://github.com/snapdgn)
* [extractor/hungama] Add subtitle by [GautamMKGarg](https://github.com/GautamMKGarg), [pukkandan](https://github.com/pukkandan)
* [extractor/instagram] Extract more metadata by [pritam20ps05](https://github.com/pritam20ps05)
* [extractor/JWPlatform] Fix extractor by [coletdjnz](https://github.com/coletdjnz)
* [extractor/malltv] Fix video_id extraction by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/MLBTV] Detect live streams
* [extractor/motorsport] Support native embeds
* [extractor/Mxplayer] Fix extractor by [itachi-19](https://github.com/itachi-19)
* [extractor/nebula] Add nebula.tv by [tannertechnology](https://github.com/tannertechnology)
* [extractor/nfl] Fix extractor by [bashonly](https://github.com/bashonly)
* [extractor/ondemandkorea] Update `jw_config` regex by [julien-hadleyjack](https://github.com/julien-hadleyjack)
* [extractor/paramountplus] Better DRM detection by [bashonly](https://github.com/bashonly)
* [extractor/patreon] Sort formats
* [extractor/rcs] Fix embed extraction by [coletdjnz](https://github.com/coletdjnz)
* [extractor/redgifs] Fix extractor by [jhwgh1968](https://github.com/jhwgh1968)
* [extractor/rutube] Fix `_EMBED_REGEX` by [coletdjnz](https://github.com/coletdjnz)
* [extractor/RUTV] Fix warnings for livestreams by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/soundcloud:search] More metadata in `--flat-playlist` by [SuperSonicHub1](https://github.com/SuperSonicHub1)
* [extractor/telegraaf] Use mobile GraphQL API endpoint by [coletdjnz](https://github.com/coletdjnz)
* [extractor/tennistv] Fix timestamp by [zenerdi0de](https://github.com/zenerdi0de)
* [extractor/tiktok] Fix TikTokIE by [bashonly](https://github.com/bashonly)
* [extractor/triller] Fix auth token by [bashonly](https://github.com/bashonly)
* [extractor/trovo] Fix extractors by [Mehavoid](https://github.com/Mehavoid)
* [extractor/tv2] Support new url format by [tobi1805](https://github.com/tobi1805)
* [extractor/web.archive:youtube] Fix `_YT_INITIAL_PLAYER_RESPONSE_RE`
* [extractor/wistia] Add support for channels by [coletdjnz](https://github.com/coletdjnz)
* [extractor/wistia] Match IDs in embed URLs by [bashonly](https://github.com/bashonly)
* [extractor/wordpress:playlist] Add generic embed extractor by [coletdjnz](https://github.com/coletdjnz)
* [extractor/yandexvideopreview] Update `_VALID_URL` by [Grub4K](https://github.com/Grub4K)
* [extractor/zee5] Fix `_VALID_URL` by [m4tu4g](https://github.com/m4tu4g)
* [extractor/zee5] Generate device ids by [freezboltz](https://github.com/freezboltz)


### 2022.09.01

* Add option `--use-extractors`
* Merge youtube-dl: Upto [commit/ed5c44e](https://github.com/ytdl-org/youtube-dl/commit/ed5c44e7)
* Add yt-dlp version to infojson
* Fix `--break-per-url --max-downloads`
* Fix bug in `--alias`
* [cookies] Support firefox container in `--cookies-from-browser` by [bashonly](https://github.com/bashonly), [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [downloader/external] Smarter detection of executable
* [extractor/generic] Don't return JW player without formats
* [FormatSort] Fix `aext` for `--prefer-free-formats`
* [jsinterp] Various improvements by [pukkandan](https://github.com/pukkandan), [dirkf](https://github.com/dirkf), [elyse0](https://github.com/elyse0)
* [cache] Mechanism to invalidate old cache
* [utils] Add `deprecation_warning`
* [utils] Add `orderedSet_from_options`
* [utils] `Popen`: Restore `LD_LIBRARY_PATH` when using PyInstaller by [Lesmiscore](https://github.com/Lesmiscore)
* [build] `make tar` should not follow `DESTDIR` by [satan1st](https://github.com/satan1st)
* [build] Update pyinstaller by [shirt-dev](https://github.com/shirt-dev)
* [test] Fix `test_youtube_signature`
* [cleanup] Misc fixes and cleanup by [DavidH-2022](https://github.com/DavidH-2022), [MrRawes](https://github.com/MrRawes), [pukkandan](https://github.com/pukkandan)
* [extractor/epoch] Add extractor by [tejasa97](https://github.com/tejasa97)
* [extractor/eurosport] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/IslamChannel] Add extractors by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/newspicks] Add extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/triller] Add extractor by [bashonly](https://github.com/bashonly)
* [extractor/VQQ] Add extractors by [elyse0](https://github.com/elyse0)
* [extractor/youtube] Improvements to nsig extraction
* [extractor/youtube] Fix bug in format sorting
* [extractor/youtube] Update iOS Innertube clients by [SamantazFox](https://github.com/SamantazFox)
* [extractor/youtube] Use device-specific user agent by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube] Add `--compat-option no-youtube-prefer-utc-upload-date` by [coletdjnz](https://github.com/coletdjnz)
* [extractor/arte] Bug fix by [cgrigis](https://github.com/cgrigis)
* [extractor/bilibili] Extract `flac` with premium account by [jackyyf](https://github.com/jackyyf)
* [extractor/BiliBiliSearch] Don't sort by date
* [extractor/BiliBiliSearch] Fix infinite loop
* [extractor/bitchute] Mark errors as expected
* [extractor/crunchyroll:beta] Use anonymous access by [tejing1](https://github.com/tejing1)
* [extractor/huya] Fix stream extraction by [ohaiibuzzle](https://github.com/ohaiibuzzle)
* [extractor/medaltv] Fix extraction by [xenova](https://github.com/xenova)
* [extractor/mediaset] Fix embed extraction
* [extractor/mixcloud] All formats are audio-only
* [extractor/rtbf] Fix jwt extraction by [elyse0](https://github.com/elyse0)
* [extractor/screencastomatic] Support `--video-password` by [shreyasminocha](https://github.com/shreyasminocha)
* [extractor/stripchat] Don't modify input URL by [dfaker](https://github.com/dfaker)
* [extractor/uktv] Improve `_VALID_URL` by [dirkf](https://github.com/dirkf)
* [extractor/vimeo:user] Fix `_VALID_URL`


### 2022.08.19

* Fix bug in `--download-archive`
* [jsinterp] **Fix for new youtube players** and related improvements by [dirkf](https://github.com/dirkf), [pukkandan](https://github.com/pukkandan)
* [phantomjs] Add function to execute JS without a DOM by [MinePlayersPE](https://github.com/MinePlayersPE), [pukkandan](https://github.com/pukkandan)
* [build] Exclude devscripts from installs by [Lesmiscore](https://github.com/Lesmiscore)
* [cleanup] Misc fixes and cleanup
* [extractor/youtube] **Add fallback to phantomjs** for nsig
* [extractor/youtube] Fix error reporting of "Incomplete data"
* [extractor/youtube] Improve format sorting for IOS formats
* [extractor/youtube] Improve signature caching
* [extractor/instagram] Fix extraction by [bashonly](https://github.com/bashonly), [pritam20ps05](https://github.com/pritam20ps05)
* [extractor/rai] Minor fix by [nixxo](https://github.com/nixxo)
* [extractor/rtbf] Fix stream extractor by [elyse0](https://github.com/elyse0)
* [extractor/SovietsCloset] Fix extractor by [ChillingPepper](https://github.com/ChillingPepper)
* [extractor/zattoo] Fix Zattoo resellers by [goggle](https://github.com/goggle)

### 2022.08.14

* Merge youtube-dl: Upto [commit/d231b56](https://github.com/ytdl-org/youtube-dl/commit/d231b56)
* [jsinterp] Handle **new youtube signature functions**
* [jsinterp] Truncate error messages
* [extractor] Fix format sorting of `channels`
* [ffmpeg] Disable avconv unless `--prefer-avconv`
* [ffmpeg] Smarter detection of ffprobe filename
* [embedthumbnail] Detect `libatomicparsley.so`
* [ThumbnailsConvertor] Fix conversion after `fixup_webp`
* [utils] Fix `get_compatible_ext`
* [build] Fix changelog
* [update] Set executable bit-mask by [pukkandan](https://github.com/pukkandan), [Lesmiscore](https://github.com/Lesmiscore)
* [devscripts] Fix import
* [docs] Consistent use of `e.g.` by [Lesmiscore](https://github.com/Lesmiscore)
* [cleanup] Misc fixes and cleanup
* [extractor/moview] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/parler] Add extractor by [palewire](https://github.com/palewire)
* [extractor/patreon] Ignore erroneous media attachments by [coletdjnz](https://github.com/coletdjnz)
* [extractor/truth] Add extractor by [palewire](https://github.com/palewire)
* [extractor/aenetworks] Add formats parameter by [jacobtruman](https://github.com/jacobtruman)
* [extractor/crunchyroll] Improve `_VALID_URL`s
* [extractor/doodstream] Add `wf` domain by [aldoridhoni](https://github.com/aldoridhoni)
* [extractor/facebook] Add reel support by [bashonly](https://github.com/bashonly)
* [extractor/MLB] New extractor by [ischmidt20](https://github.com/ischmidt20)
* [extractor/rai] Misc fixes by [nixxo](https://github.com/nixxo)
* [extractor/toggo] Improve `_VALID_URL` by [masta79](https://github.com/masta79)
* [extractor/tubitv] Extract additional formats by [shirt-dev](https://github.com/shirt-dev)
* [extractor/zattoo] Potential fix for resellers


### 2022.08.08

* **Remove Python 3.6 support**
* Determine merge container better by [pukkandan](https://github.com/pukkandan), [selfisekai](https://github.com/selfisekai)
* Framework for embed detection by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* Merge youtube-dl: Upto [commit/adb5294](https://github.com/ytdl-org/youtube-dl/commit/adb5294)
* `--compat-option no-live-chat` should disable danmaku
* Fix misleading DRM message
* Import ctypes only when necessary
* Minor bugfixes
* Reject entire playlists faster with `--match-filter`
* Remove filtered entries from `-J`
* Standardize retry mechanism
* Validate `--merge-output-format`
* [downloader] Add average speed to final progress line
* [extractor] Add field `audio_channels`
* [extractor] Support multiple archive ids for one video
* [ffmpeg] Set `ffmpeg_location` in a contextvar
* [FFmpegThumbnailsConvertor] Fix conversion from GIF
* [MetadataParser] Don't set `None` when the field didn't match
* [outtmpl] Smarter replacing of unsupported characters
* [outtmpl] Treat empty values as None in filenames
* [utils] sanitize_open: Allow any IO stream as stdout
* [build, devscripts] Add devscript to set a build variant
* [build] Improve build process by [shirt-dev](https://github.com/shirt-dev)
* [build] Update pyinstaller
* [devscripts] Create `utils` and refactor
* [docs] Clarify `best*`
* [docs] Fix bug report issue template
* [docs] Fix capitalization in references by [christoph-heinrich](https://github.com/christoph-heinrich)
* [cleanup, mhtml] Use imghdr
* [cleanup, utils] Consolidate known media extensions
* [cleanup] Misc fixes and cleanup
* [extractor/angel] Add extractor by [AxiosDeminence](https://github.com/AxiosDeminence)
* [extractor/dplay] Add MotorTrend extractor by [Sipherdrakon](https://github.com/Sipherdrakon)
* [extractor/harpodeon] Add extractor by [eren-kemer](https://github.com/eren-kemer)
* [extractor/holodex] Add extractor by [pukkandan](https://github.com/pukkandan), [sqrtNOT](https://github.com/sqrtNOT)
* [extractor/kompas] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/rai] Add raisudtirol extractor by [nixxo](https://github.com/nixxo)
* [extractor/tempo] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/youtube] **Fixes for third party client detection** by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube] Add `live_status=post_live` by [lazypete365](https://github.com/lazypete365)
* [extractor/youtube] Extract more format info
* [extractor/youtube] Parse translated subtitles only when requested
* [extractor/youtube, extractor/twitch] Allow waiting for channels to become live
* [extractor/youtube, webvtt] Extract auto-subs from livestream VODs by [fstirlitz](https://github.com/fstirlitz), [pukkandan](https://github.com/pukkandan)
* [extractor/AbemaTVTitle] Implement paging by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/archiveorg] Improve handling of formats by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor/arte] Fix title extraction
* [extractor/arte] **Move to v2 API** by [fstirlitz](https://github.com/fstirlitz), [pukkandan](https://github.com/pukkandan)
* [extractor/bbc] Fix news articles by [ajj8](https://github.com/ajj8)
* [extractor/camtasia] Separate into own extractor by [coletdjnz](https://github.com/coletdjnz)
* [extractor/cloudflarestream] Fix video_id padding by [haobinliang](https://github.com/haobinliang)
* [extractor/crunchyroll] Fix conversion of thumbnail from GIF
* [extractor/crunchyroll] Handle missing metadata correctly by [Burve](https://github.com/Burve), [pukkandan](https://github.com/pukkandan)
* [extractor/crunchyroll:beta] Extract timestamp and fix tests by [tejing1](https://github.com/tejing1)
* [extractor/crunchyroll:beta] Use streams API by [tejing1](https://github.com/tejing1)
* [extractor/doodstream] Support more domains by [Galiley](https://github.com/Galiley)
* [extractor/ESPN] Extract duration by [ischmidt20](https://github.com/ischmidt20)
* [extractor/FIFA] Change API endpoint by [Bricio](https://github.com/Bricio), [yashkc2025](https://github.com/yashkc2025)
* [extractor/globo:article] Remove false positives by [Bricio](https://github.com/Bricio)
* [extractor/Go] Extract timestamp by [ischmidt20](https://github.com/ischmidt20)
* [extractor/hidive] Fix cookie login when netrc is also given by [winterbird-code](https://github.com/winterbird-code)
* [extractor/html5] Separate into own extractor by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor/ina] Improve extractor by [elyse0](https://github.com/elyse0)
* [extractor/NaverNow] Change endpoint by [ping](https://github.com/ping)
* [extractor/ninegag] Extract uploader by [DjesonPV](https://github.com/DjesonPV)
* [extractor/NovaPlay] Fix extractor by [Bojidarist](https://github.com/Bojidarist)
* [extractor/orf:radio] Rewrite extractors
* [extractor/patreon] Fix and improve extractors by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor/rai] Fix RaiNews extraction by [nixxo](https://github.com/nixxo)
* [extractor/redbee] Unify and update extractors by [elyse0](https://github.com/elyse0)
* [extractor/stripchat] Fix _VALID_URL by [freezboltz](https://github.com/freezboltz)
* [extractor/tubi] Exclude playlists from playlist entries by [sqrtNOT](https://github.com/sqrtNOT)
* [extractor/tviplayer] Improve `_VALID_URL` by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/twitch] Extract chapters for single chapter VODs by [mpeter50](https://github.com/mpeter50)
* [extractor/vgtv] Support tv.vg.no by [sqrtNOT](https://github.com/sqrtNOT)
* [extractor/vidio] Support embed link by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/vk] Fix extractor by [Mehavoid](https://github.com/Mehavoid)
* [extractor/WASDTV:record] Fix `_VALID_URL`
* [extractor/xfileshare] Add Referer by [Galiley](https://github.com/Galiley)
* [extractor/YahooJapanNews] Fix extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/yandexmusic] Extract higher quality format
* [extractor/zee5] Update Device ID by [m4tu4g](https://github.com/m4tu4g)


### 2022.07.18

* Allow users to specify encoding in each config files by [Lesmiscore](https://github.com/Lesmiscore)
* Discard infodict from memory if no longer needed
* Do not allow extractors to return `None`
* Do not load system certificates when `certifi` is used
* Fix rounding of integers in format table
* Improve chapter sanitization
* Skip some fixup if remux/recode is needed by [Lesmiscore](https://github.com/Lesmiscore)
* Support `--no-progress` for `--wait-for-video`
* Fix bug in [612f2be](https://github.com/yt-dlp/yt-dlp/commit/612f2be5d3924540158dfbe5f25d841f04cff8c6)
* [outtmpl] Add alternate form `h` for HTML escaping
* [aes] Add multiple padding modes in CBC by [elyse0](https://github.com/elyse0)
* [extractor/common] Passthrough `errnote=False` to parsers
* [extractor/generic] Remove HEAD request
* [http] Ensure the file handle is always closed
* [ModifyChapters] Modify duration in infodict
* [options] Fix aliases to `--config-location`
* [utils] Fix `get_domain`
* [build] Consistent order for lazy extractors by [lamby](https://github.com/lamby)
* [build] Fix architecture suffix of executables by [odo2063](https://github.com/odo2063)
* [build] Improve `setup.py`
* [update] Do not check `_update_spec` when up to date
* [update] Prepare to remove Python 3.6 support
* [compat] Let PyInstaller detect _legacy module
* [devscripts/update-formulae] Do not change dependency section
* [test] Split download tests so they can be more easily run in CI
* [docs] Improve docstring of `download_ranges` by [FirefoxMetzger](https://github.com/FirefoxMetzger)
* [docs] Improve issue templates
* [build] Fix bug in [6d916fe](https://github.com/yt-dlp/yt-dlp/commit/6d916fe709a38e8c4c69b73843acf170b5165931)
* [cleanup, utils] Refactor parse_codecs
* [cleanup] Misc fixes and cleanup
* [extractor/acfun] Add extractors by [lockmatrix](https://github.com/lockmatrix)
* [extractor/Audiodraft] Add extractors by [Ashish0804](https://github.com/Ashish0804), [fstirlitz](https://github.com/fstirlitz)
* [extractor/cellebrite] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/detik] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/hytale] Add extractor by [llamasblade](https://github.com/llamasblade), [pukkandan](https://github.com/pukkandan)
* [extractor/liputan6] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/mocha] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/rtl.lu] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/rtvsl] Add extractor by [iw0nderhow](https://github.com/iw0nderhow), [pukkandan](https://github.com/pukkandan)
* [extractor/StarTrek] Add extractor by [scy](https://github.com/scy)
* [extractor/syvdk] Add extractor by [misaelaguayo](https://github.com/misaelaguayo)
* [extractor/theholetv] Add extractor by [dosy4ev](https://github.com/dosy4ev)
* [extractor/TubeTuGraz] Add extractor by [Ferdi265](https://github.com/Ferdi265), [pukkandan](https://github.com/pukkandan)
* [extractor/tviplayer] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/wetv] Add extractors by [elyse0](https://github.com/elyse0)
* [extractor/wikimedia] Add extractor by [EhtishamSabir](https://github.com/EhtishamSabir), [pukkandan](https://github.com/pukkandan)
* [extractor/youtube] Fix duration check for post-live manifestless mode
* [extractor/youtube] More metadata for storyboards by [ftk](https://github.com/ftk)
* [extractor/bigo] Fix extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/BiliIntl] Fix subtitle extraction by [MinePlayersPE](https://github.com/MinePlayersPE)
* [extractor/crunchyroll] Improve `_VALID_URL`
* [extractor/fifa] Fix extractor by [ischmidt20](https://github.com/ischmidt20)
* [extractor/instagram] Fix post/story extractors by [pritam20ps05](https://github.com/pritam20ps05), [pukkandan](https://github.com/pukkandan)
* [extractor/iq] Set language correctly for Korean subtitles
* [extractor/MangoTV] Fix subtitle languages
* [extractor/Netverse] Improve playlist extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/philharmoniedeparis] Fix extractor by [sqrtNOT](https://github.com/sqrtNOT)
* [extractor/Trovo] Fix extractor by [u-spec-png](https://github.com/u-spec-png)
* [extractor/twitch] Support storyboards for VODs by [ftk](https://github.com/ftk)
* [extractor/WatchESPN] Improve `_VALID_URL` by [IONECarter](https://github.com/IONECarter), [dirkf](https://github.com/dirkf)
* [extractor/WSJArticle] Fix video id extraction by [sqrtNOT](https://github.com/sqrtNOT)
* [extractor/Ximalaya] Fix extractors by [lockmatrix](https://github.com/lockmatrix)
* [cleanup, extractor/youtube] Fix tests by [sheerluck](https://github.com/sheerluck)


### 2022.06.29

* Fix `--downloader native`
* Fix `section_end` of clips
* Fix playlist error handling
* Sanitize `chapters`
* [extractor] Fix `_create_request` when headers is None
* [extractor] Fix empty `BaseURL` in MPD
* [ffmpeg] Write full output to debug on error
* [hls] Warn user when trying to download live HLS
* [options] Fix `parse_known_args` for `--`
* [utils] Fix inconsistent default handling between HTTP and HTTPS requests by [coletdjnz](https://github.com/coletdjnz)
* [build] Draft release until complete
* [build] Fix release tag commit
* [build] Standalone x64 builds for MacOS 10.9 by [StefanLobbenmeier](https://github.com/StefanLobbenmeier)
* [update] Ability to set a maximum version for specific variants
* [compat] Fix `compat.WINDOWS_VT_MODE`
* [compat] Remove deprecated functions from core code
* [compat] Remove more functions
* [cleanup, extractor] Reduce direct use of `_downloader`
* [cleanup] Consistent style for file heads
* [cleanup] Fix some typos by [crazymoose77756](https://github.com/crazymoose77756)
* [cleanup] Misc fixes and cleanup
* [extractor/Scrolller] Add extractor by [LunarFang416](https://github.com/LunarFang416)
* [extractor/ViMP] Add playlist extractor by [FestplattenSchnitzel](https://github.com/FestplattenSchnitzel)
* [extractor/fuyin] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/livestreamfails] Add extractor by [nomevi](https://github.com/nomevi)
* [extractor/premiershiprugby] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/steam] Add broadcast extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/youtube] Mark videos as fully watched by [Brett824](https://github.com/Brett824)
* [extractor/CWTV] Extract thumbnail by [ischmidt20](https://github.com/ischmidt20)
* [extractor/ViMP] Add thumbnail and support more sites by [FestplattenSchnitzel](https://github.com/FestplattenSchnitzel)
* [extractor/dropout] Support cookies and login only as needed by [pingiun](https://github.com/pingiun), [pukkandan](https://github.com/pukkandan)
* [extractor/ertflix] Improve `_VALID_URL`
* [extractor/lbry] Use HEAD request for redirect URL by [flashdagger](https://github.com/flashdagger)
* [extractor/mediaset] Improve `_VALID_URL`
* [extractor/npr] Implement [e50c350](https://github.com/yt-dlp/yt-dlp/commit/e50c3500b43d80e4492569c4b4523c4379c6fbb2) differently
* [extractor/tennistv] Rewrite extractor by [pukkandan](https://github.com/pukkandan), [zenerdi0de](https://github.com/zenerdi0de)

### 2022.06.22.1

* [build] Fix updating homebrew formula

### 2022.06.22

* [**Deprecate support for Python 3.6**](https://github.com/yt-dlp/yt-dlp/issues/3764#issuecomment-1154051119)
* **Add option `--download-sections` to download video partially**
    * Chapter regex and time ranges are accepted, e.g. `--download-sections *1:10-2:20`
* Add option `--alias`
* Add option `--lazy-playlist` to process entries as they are received
* Add option `--retry-sleep`
* Add slicing notation to `--playlist-items`
    * Adds support for negative indices and step
    * Add `-I` as alias for `--playlist-index`
    * Makes `--playlist-start`, `--playlist-end`, `--playlist-reverse`, `--no-playlist-reverse` redundant
* `--config-location -` to provide options interactively
* [build] Add Linux standalone builds
* [update] Self-restart after update
* Merge youtube-dl: Upto [commit/8a158a9](https://github.com/ytdl-org/youtube-dl/commit/8a158a9)
* Add `--no-update`
* Allow extractors to specify section_start/end for clips
* Do not print progress to `stderr` with `-q`
* Ensure pre-processor errors do not block video download
* Fix `--simulate --max-downloads`
* Improve error handling of bad config files
* Return an error code if update fails
* Fix bug in [3a408f9](https://github.com/yt-dlp/yt-dlp/commit/3a408f9d199127ca2626359e21a866a09ab236b3)
* [ExtractAudio] Allow conditional conversion
* [ModifyChapters] Fix repeated removal of small segments
* [ThumbnailsConvertor] Allow conditional conversion
* [cookies] Detect profiles for cygwin/BSD by [moench-tegeder](https://github.com/moench-tegeder)
* [dash] Show fragment count with `--live-from-start` by [flashdagger](https://github.com/flashdagger)
* [extractor] Add `_search_json` by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor] Add `default` parameter to `_search_json` by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor] Add dev option `--load-pages`
* [extractor] Handle `json_ld` with multiple `@type`s
* [extractor] Import `_ALL_CLASSES` lazily
* [extractor] Recognize `src` attribute from HTML5 media elements by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/generic] Revert e6ae51c123897927eb3c9899923d8ffd31c7f85d
* [f4m] Bugfix
* [ffmpeg] Check version lazily
* [jsinterp] Some optimizations and refactoring by [dirkf](https://github.com/dirkf), [pukkandan](https://github.com/pukkandan)
* [utils] Improve performance using `functools.cache`
* [utils] Send HTTP/1.1 ALPN extension by [coletdjnz](https://github.com/coletdjnz)
* [utils] `ExtractorError`: Fix `exc_info`
* [utils] `ISO3166Utils`: Add `EU` and `AP`
* [utils] `Popen`: Refactor to use contextmanager
* [utils] `locked_file`: Fix for PyPy on Windows
* [update] Expose more functionality to API
* [update] Use `.git` folder to distinguish `source`/`unknown`
* [compat] Add `functools.cached_property`
* [test] Fix `FakeYDL` signatures by [coletdjnz](https://github.com/coletdjnz)
* [docs] Improvements
* [cleanup, ExtractAudio] Refactor
* [cleanup, downloader] Refactor `report_progress`
* [cleanup, extractor] Refactor `_download_...` methods
* [cleanup, extractor] Rename `extractors.py` to `_extractors.py`
* [cleanup, utils] Don't use kwargs for `format_field`
* [cleanup, build] Refactor
* [cleanup, docs] Re-indent "Usage and Options" section
* [cleanup] Deprecate `YoutubeDL.parse_outtmpl`
* [cleanup] Misc fixes and cleanup by [Lesmiscore](https://github.com/Lesmiscore), [MrRawes](https://github.com/MrRawes), [christoph-heinrich](https://github.com/christoph-heinrich), [flashdagger](https://github.com/flashdagger), [gamer191](https://github.com/gamer191), [kwconder](https://github.com/kwconder), [pukkandan](https://github.com/pukkandan)
* [extractor/DailyWire] Add extractors by [HobbyistDev](https://github.com/HobbyistDev), [pukkandan](https://github.com/pukkandan)
* [extractor/fourzerostudio] Add extractors by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/GoogleDrive] Add folder extractor by [evansp](https://github.com/evansp), [pukkandan](https://github.com/pukkandan)
* [extractor/MirrorCoUK] Add extractor by [LunarFang416](https://github.com/LunarFang416), [pukkandan](https://github.com/pukkandan)
* [extractor/atscaleconfevent] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [extractor/freetv] Add extractor by [elyse0](https://github.com/elyse0)
* [extractor/ixigua] Add Extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/kicker.de] Add extractor by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/netverse] Add extractors by [HobbyistDev](https://github.com/HobbyistDev), [pukkandan](https://github.com/pukkandan)
* [extractor/playsuisse] Add extractor by [pukkandan](https://github.com/pukkandan), [sbor23](https://github.com/sbor23)
* [extractor/substack] Add extractor by [elyse0](https://github.com/elyse0)
* [extractor/youtube] **Support downloading clips**
* [extractor/youtube] Add `innertube_host` and `innertube_key` extractor args by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube] Add warning for PostLiveDvr
* [extractor/youtube] Bring back `_extract_chapters_from_description`
* [extractor/youtube] Extract `comment_count` from webpage
* [extractor/youtube] Fix `:ytnotifications` extractor by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube] Fix initial player response extraction by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [extractor/youtube] Fix live chat for videos with content warning by [coletdjnz](https://github.com/coletdjnz)
* [extractor/youtube] Make signature extraction non-fatal
* [extractor/youtube:tab] Detect `videoRenderer` in `_post_thread_continuation_entries`
* [extractor/BiliIntl] Fix metadata extraction
* [extractor/BiliIntl] Fix subtitle extraction by [HobbyistDev](https://github.com/HobbyistDev)
* [extractor/FranceCulture] Fix extractor by [aurelg](https://github.com/aurelg), [pukkandan](https://github.com/pukkandan)
* [extractor/PokemonSoundLibrary] Remove extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/StreamCZ] Fix extractor by [adamanldo](https://github.com/adamanldo), [dirkf](https://github.com/dirkf)
* [extractor/WatchESPN] Support free videos and BAM_DTC by [ischmidt20](https://github.com/ischmidt20)
* [extractor/animelab] Remove extractor by [gamer191](https://github.com/gamer191)
* [extractor/bloomberg] Change playback endpoint by [m4tu4g](https://github.com/m4tu4g)
* [extractor/ccc] Extract view_count by [vkorablin](https://github.com/vkorablin)
* [extractor/crunchyroll:beta] Fix extractor after API change by [Burve](https://github.com/Burve), [tejing1](https://github.com/tejing1)
* [extractor/curiositystream] Get `auth_token` from cookie by [mnn](https://github.com/mnn)
* [extractor/digitalconcerthall] Fix extractor by [ZhymabekRoman](https://github.com/ZhymabekRoman)
* [extractor/dropbox] Extract the correct `mountComponent`
* [extractor/dropout] Login is not mandatory
* [extractor/duboku] Fix for hostname change by [mozbugbox](https://github.com/mozbugbox)
* [extractor/espn] Add `WatchESPN` extractor by [ischmidt20](https://github.com/ischmidt20), [pukkandan](https://github.com/pukkandan)
* [extractor/expressen] Fix extractor by [aejdl](https://github.com/aejdl)
* [extractor/foxnews] Update embed extraction by [elyse0](https://github.com/elyse0)
* [extractor/ina] Fix extractor by [elyse0](https://github.com/elyse0)
* [extractor/iwara:user] Make paging better by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/jwplatform] Look for `data-video-jw-id`
* [extractor/lbry] Update livestream API by [flashdagger](https://github.com/flashdagger)
* [extractor/mediaset] Improve `_VALID_URL`
* [extractor/naver] Add `navernow` extractor by [ping](https://github.com/ping)
* [extractor/niconico:series] Fix extractor by [sqrtNOT](https://github.com/sqrtNOT)
* [extractor/npr] Use stream url from json-ld by [r5d](https://github.com/r5d)
* [extractor/pornhub] Extract `uploader_id` field by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/radiofrance] Add more radios by [bubbleguuum](https://github.com/bubbleguuum)
* [extractor/rumble] Detect JS embed
* [extractor/rumble] Extract subtitles by [fstirlitz](https://github.com/fstirlitz)
* [extractor/southpark] Add `southpark.lat` extractor by [darkxex](https://github.com/darkxex)
* [extractor/spotify:show] Fix extractor
* [extractor/tiktok] Detect embeds
* [extractor/tiktok] Extract `SIGI_STATE` by [dirkf](https://github.com/dirkf), [pukkandan](https://github.com/pukkandan), [sulyi](https://github.com/sulyi)
* [extractor/tver] Fix extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/vevo] Fix extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [extractor/yahoo:gyao] Fix extractor
* [extractor/zattoo] Fix live streams by [miseran](https://github.com/miseran)
* [extractor/zdf] Improve format sorting by [elyse0](https://github.com/elyse0)


### 2022.05.18

* Add support for SSL client certificate authentication by [coletdjnz](https://github.com/coletdjnz), [dirkf](https://github.com/dirkf)
    * Adds `--client-certificate`, `--client-certificate-key`, `--client-certificate-password`
* Add `--match-filter -` to interactively ask for each video
* `--max-downloads` should obey `--break-per-input`
* Allow use of weaker ciphers with `--legacy-server-connect`
* Don't imply `-s` for later stages of `-O`
* Fix `--date today`
* Fix `--skip-unavailable-fragments`
* Fix color in `-q -F`
* Fix redirect HTTP method handling by [coletdjnz](https://github.com/coletdjnz)
* Improve `--clean-infojson`
* Remove warning for videos with an empty title
* Run `FFmpegFixupM3u8PP` for live-streams if needed
* Show name of downloader in verbose log
* [cookies] Allow `cookiefile` to be a text stream
* [cookies] Report progress when importing cookies
* [downloader/ffmpeg] Specify headers for each URL by [elyse0](https://github.com/elyse0)
* [fragment] Do not change chunk-size when `--test`
* [fragment] Make single thread download work for `--live-from-start` by [Lesmiscore](https://github.com/Lesmiscore)
* [hls] Fix `byte_range` for `EXT-X-MAP` fragment by [fstirlitz](https://github.com/fstirlitz)
* [http] Fix retrying on read timeout by [coletdjnz](https://github.com/coletdjnz)
* [ffmpeg] Fix features detection
* [EmbedSubtitle] Enable for more video extensions
* [EmbedThumbnail] Disable thumbnail conversion for mkv by [evansp](https://github.com/evansp)
* [EmbedThumbnail] Do not obey `-k`
* [EmbedThumbnail] Do not remove id3v1 tags
* [FFmpegMetadata] Remove `\0` from metadata
* [FFmpegMetadata] Remove filename from attached info-json
* [FixupM3u8] Obey `--hls-prefer-mpegts`
* [Sponsorblock] Don't crash when duration is unknown
* [XAttrMetadata] Refactor and document dependencies
* [extractor] Document netrc machines
* [extractor] Update `manifest_url`s after redirect by [elyse0](https://github.com/elyse0)
* [extractor] Update dash `manifest_url` after redirects by [elyse0](https://github.com/elyse0)
* [extractor] Use `classmethod`/`property` where possible
* [generic] Refactor `_extract_rss`
* [utils] `is_html`: Handle double BOM
* [utils] `locked_file`: Ignore illegal seek on `truncate` by [jakeogh](https://github.com/jakeogh)
* [utils] `sanitize_path`: Fix when path is empty string
* [utils] `write_string`: Workaround newline issue in `conhost`
* [utils] `certifi`: Make sure the pem file exists
* [utils] Fix `WebSocketsWrapper`
* [utils] `locked_file`: Do not give executable bits for newly created files by [Lesmiscore](https://github.com/Lesmiscore)
* [utils] `YoutubeDLCookieJar`: Detect and reject JSON file by [Lesmiscore](https://github.com/Lesmiscore)
* [test] Convert warnings into errors and fix some existing warnings by [fstirlitz](https://github.com/fstirlitz)
* [dependencies] Create module with all dependency imports
* [compat] Split into sub-modules by [fstirlitz](https://github.com/fstirlitz), [pukkandan](https://github.com/pukkandan)
* [compat] Implement `compat.imghdr`
* [build] Add `make uninstall` by [MrRawes](https://github.com/MrRawes)
* [build] Avoid use of `install -D`
* [build] Fix `Makefile` by [putnam](https://github.com/putnam)
* [build] Fix `--onedir` on macOS
* [build] Add more test-runners
* [cleanup] Deprecate some compat vars by [fstirlitz](https://github.com/fstirlitz), [pukkandan](https://github.com/pukkandan)
* [cleanup] Remove unused code paths, extractors, scripts and tests by [fstirlitz](https://github.com/fstirlitz)
* [cleanup] Upgrade syntax (`pyupgrade`) and sort imports (`isort`)
* [cleanup, docs, build] Misc fixes
* [BilibiliLive] Add extractor by [HE7086](https://github.com/HE7086), [pukkandan](https://github.com/pukkandan)
* [Fifa] Add Extractor by [Bricio](https://github.com/Bricio)
* [goodgame] Add extractor by [nevack](https://github.com/nevack)
* [gronkh] Add playlist extractors by [hatienl0i261299](https://github.com/hatienl0i261299)
* [icareus] Add extractor by [tpikonen](https://github.com/tpikonen), [pukkandan](https://github.com/pukkandan)
* [iwara] Add playlist extractors by [i6t](https://github.com/i6t)
* [Likee] Add extractor by [hatienl0i261299](https://github.com/hatienl0i261299)
* [masters] Add extractor by [m4tu4g](https://github.com/m4tu4g)
* [nebula] Add support for subscriptions by [hheimbuerger](https://github.com/hheimbuerger)
* [Podchaser] Add extractors by [connercsbn](https://github.com/connercsbn)
* [rokfin:search] Add extractor by [P-reducible](https://github.com/P-reducible), [pukkandan](https://github.com/pukkandan)
* [youtube] Add `:ytnotifications` extractor by [krichbanana](https://github.com/krichbanana)
* [youtube] Add YoutubeStoriesIE (`ytstories:<channel UCID>`) by [coletdjnz](https://github.com/coletdjnz)
* [ZingMp3] Add chart and user extractors by [hatienl0i261299](https://github.com/hatienl0i261299)
* [adn] Update AES key by [elyse0](https://github.com/elyse0)
* [adobepass] Allow cookies for authenticating MSO
* [bandcamp] Exclude merch links by [Yipten](https://github.com/Yipten)
* [chingari] Fix archiving and tests
* [DRTV] Improve `_VALID_URL` by [vertan](https://github.com/vertan)
* [facebook] Improve thumbnail extraction by [Wikidepia](https://github.com/Wikidepia)
* [fc2] Stop heatbeating once FFmpeg finishes by [Lesmiscore](https://github.com/Lesmiscore)
* [Gofile] Fix extraction and support password-protected links by [mehq](https://github.com/mehq)
* [hotstar, cleanup] Refactor extractors
* [InfoQ] Don't fail on missing audio format by [evansp](https://github.com/evansp)
* [Jamendo] Extract more metadata by [evansp](https://github.com/evansp)
* [kaltura] Update API calls by [flashdagger](https://github.com/flashdagger)
* [KhanAcademy] Fix extractor by [rand-net](https://github.com/rand-net)
* [LCI] Fix extractor by [MarwenDallel](https://github.com/MarwenDallel)
* [lrt] Support livestreams by [GiedriusS](https://github.com/GiedriusS)
* [niconico] Set `expected_protocol` to a public field
* [Niconico] Support 2FA by [ekangmonyet](https://github.com/ekangmonyet)
* [Olympics] Fix format extension
* [openrec:movie] Enable fallback for /movie/ URLs
* [PearVideo] Add fallback for formats by [hatienl0i261299](https://github.com/hatienl0i261299)
* [radiko] Fix extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [rai] Add `release_year`
* [reddit] Prevent infinite loop
* [rokfin] Implement login by [P-reducible](https://github.com/P-reducible), [pukkandan](https://github.com/pukkandan)
* [ruutu] Support hs.fi embeds by [tpikonen](https://github.com/tpikonen), [pukkandan](https://github.com/pukkandan)
* [spotify] Detect iframe embeds by [fstirlitz](https://github.com/fstirlitz)
* [telegram] Fix metadata extraction
* [tmz, cleanup] Update tests by [diegorodriguezv](https://github.com/diegorodriguezv)
* [toggo] Fix `_VALID_URL` by [ca-za](https://github.com/ca-za)
* [trovo] Update to new API by [nyuszika7h](https://github.com/nyuszika7h)
* [TVer] Improve extraction by [Lesmiscore](https://github.com/Lesmiscore)
* [twitcasting] Pass headers for each formats by [Lesmiscore](https://github.com/Lesmiscore)
* [VideocampusSachsen] Improve extractor by [FestplattenSchnitzel](https://github.com/FestplattenSchnitzel)
* [vimeo] Fix extractors
* [wat] Fix extraction of multi-language videos and subtitles by [elyse0](https://github.com/elyse0)
* [wistia] Fix `_VALID_URL` by [dirkf](https://github.com/dirkf)
* [youtube, cleanup] Minor refactoring by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [youtube] Added piped instance urls by [JordanWeatherby](https://github.com/JordanWeatherby)
* [youtube] Deprioritize auto-generated thumbnails
* [youtube] Deprioritize format 22 (often damaged)
* [youtube] Fix episode metadata extraction
* [zee5] Fix extractor by [Ashish0804](https://github.com/Ashish0804)
* [zingmp3, cleanup] Refactor extractors


### 2022.04.08

* Use certificates from `certifi` if installed by [coletdjnz](https://github.com/coletdjnz)
* Treat multiple `--match-filters` as OR
* File locking improvements:
    * Do not lock downloading file on Windows
    * Do not prevent download if locking is unsupported
    * Do not truncate files before locking by [jakeogh](https://github.com/jakeogh), [pukkandan](https://github.com/pukkandan)
    * Fix non-blocking non-exclusive lock
* De-prioritize automatic-subtitles when no `--sub-lang` is given
* Exit after `--dump-user-agent`
* Fallback to video-only format when selecting by extension
* Fix `--abort-on-error` for subtitles
* Fix `--no-overwrite` for playlist infojson
* Fix `--print` with `--ignore-no-formats` when url is `None` by [flashdagger](https://github.com/flashdagger)
* Fix `--sleep-interval`
* Fix `--throttled-rate`
* Fix `autonumber`
* Fix case of `http_headers`
* Fix filepath sanitization in `--print-to-file`
* Handle float in `--wait-for-video`
* Ignore `mhtml` formats from `-f mergeall`
* Ignore format-specific fields in initial pass of `--match-filter`
* Protect stdout from unexpected progress and console-title
* Remove `Accept-Encoding` header from `std_headers` by [coletdjnz](https://github.com/coletdjnz)
* Remove incorrect warning for `--dateafter`
* Show warning when all media formats have DRM
* [downloader] Fix invocation of `HttpieFD`
* [http] Fix #3215
* [http] Reject broken range before request by [Lesmiscore](https://github.com/Lesmiscore), [Jules-A](https://github.com/Jules-A), [pukkandan](https://github.com/pukkandan)
* [fragment] Read downloaded fragments only when needed by [Lesmiscore](https://github.com/Lesmiscore)
* [http] Retry on more errors by [coletdjnz](https://github.com/coletdjnz)
* [mhtml] Fix fragments with absolute urls by [coletdjnz](https://github.com/coletdjnz)
* [extractor] Add `_perform_login` function
* [extractor] Allow control characters inside json
* [extractor] Support merging subtitles with data by [coletdjnz](https://github.com/coletdjnz)
* [generic] Extract subtitles from video.js by [Lesmiscore](https://github.com/Lesmiscore)
* [ffmpeg] Cache version data
* [FFmpegConcat] Ensure final directory exists
* [FfmpegMetadata] Write id3v1 tags
* [FFmpegVideoConvertor] Add more formats to `--remux-video`
* [FFmpegVideoConvertor] Ensure all streams are copied
* [MetadataParser] Validate outtmpl early
* [outtmpl] Fix replacement/default when used with alternate
* [outtmpl] Limit changes during sanitization
* [phantomjs] Fix bug
* [test] Add `test_locked_file`
* [utils] `format_decimal_suffix`: Fix for very large numbers by [s0u1h](https://github.com/s0u1h)
* [utils] `traverse_obj`: Allow filtering by value
* [utils] Add `filter_dict`, `get_first`, `try_call`
* [utils] ExtractorError: Fix for older Python versions
* [utils] WebSocketsWrapper: Allow omitting `__enter__` invocation by [Lesmiscore](https://github.com/Lesmiscore)
* [docs] Add an `.editorconfig` file by [fstirlitz](https://github.com/fstirlitz)
* [docs] Clarify the exact `BSD` license of dependencies by [MrRawes](https://github.com/MrRawes)
* [docs] Minor improvements by [pukkandan](https://github.com/pukkandan), [cffswb](https://github.com/cffswb), [danielyli](https://github.com/danielyli)
* [docs] Remove readthedocs
* [build] Add `requirements.txt` to pip distributions
* [cleanup, postprocessor] Create `_download_json`
* [cleanup, vimeo] Fix tests
* [cleanup] Misc fixes and minor cleanup
* [cleanup] Use `_html_extract_title`
* [AfreecaTV] Add `AfreecaTVUserIE` by [hatienl0i261299](https://github.com/hatienl0i261299)
* [arte] Add `format_note` to m3u8 formats
* [azmedien] Add TVO Online to supported hosts by [1-Byte](https://github.com/1-Byte)
* [BanBye] Add extractor by [mehq](https://github.com/mehq)
* [bilibili] Fix extraction of title with quotes by [dzek69](https://github.com/dzek69)
* [Craftsy] Add extractor by [Bricio](https://github.com/Bricio)
* [Cybrary] Add extractor by [aaearon](https://github.com/aaearon)
* [Huya] Add extractor by [hatienl0i261299](https://github.com/hatienl0i261299)
* [ITProTV] Add extractor by [aaearon](https://github.com/aaearon)
* [Jable] Add extractors by [mehq](https://github.com/mehq)
* [LastFM] Add extractors by [mehq](https://github.com/mehq)
* [Moviepilot] Add extractor by [panatexxa](https://github.com/panatexxa)
* [panopto] Add extractors by [coletdjnz](https://github.com/coletdjnz), [kmark](https://github.com/kmark)
* [PokemonSoundLibrary] Add extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [WasdTV] Add extractor by [un-def](https://github.com/un-def), [hatienl0i261299](https://github.com/hatienl0i261299)
* [adobepass] Fix Suddenlink MSO by [CplPwnies](https://github.com/CplPwnies)
* [afreecatv] Match new vod url by [wlritchi](https://github.com/wlritchi)
* [AZMedien] Support `tv.telezueri.ch` by [goggle](https://github.com/goggle)
* [BiliIntl] Support user-generated videos by [wlritchi](https://github.com/wlritchi)
* [BRMediathek] Fix VALID_URL
* [crunchyroll:playlist] Implement beta API by [tejing1](https://github.com/tejing1)
* [crunchyroll] Fix inheritance
* [daftsex] Fix extractor by [Soebb](https://github.com/Soebb)
* [dailymotion] Support `geo.dailymotion.com` by [hatienl0i261299](https://github.com/hatienl0i261299)
* [ellentube] Extract subtitles from manifest
* [elonet] Rewrite extractor by [Fam0r](https://github.com/Fam0r), [pukkandan](https://github.com/pukkandan)
* [fptplay] Fix metadata extraction by [hatienl0i261299](https://github.com/hatienl0i261299)
* [FranceCulture] Support playlists by [bohwaz](https://github.com/bohwaz)
* [go, viu] Extract subtitles from the m3u8 manifest by [fstirlitz](https://github.com/fstirlitz)
* [Imdb] Improve extractor by [hatienl0i261299](https://github.com/hatienl0i261299)
* [MangoTV] Improve extractor by [hatienl0i261299](https://github.com/hatienl0i261299)
* [Nebula] Fix bug in 52efa4b31200119adaa8acf33e50b84fcb6948f0
* [niconico] Fix extraction of thumbnails and uploader (#3266)
* [niconico] Rewrite NiconicoIE by [Lesmiscore](https://github.com/Lesmiscore)
* [nitter] Minor fixes and update instance list by [foghawk](https://github.com/foghawk)
* [NRK] Extract timestamp by [hatienl0i261299](https://github.com/hatienl0i261299)
* [openrec] Download archived livestreams by [Lesmiscore](https://github.com/Lesmiscore)
* [openrec] Refactor extractors by [Lesmiscore](https://github.com/Lesmiscore)
* [panopto] Improve subtitle extraction and support slides by [coletdjnz](https://github.com/coletdjnz)
* [ParamountPlus, CBS] Change VALID_URL by [Sipherdrakon](https://github.com/Sipherdrakon)
* [ParamountPlusSeries] Support multiple pages by [dodrian](https://github.com/dodrian)
* [Piapro] Extract description with break lines by [Lesmiscore](https://github.com/Lesmiscore)
* [rai] Fix extraction of http formas by [nixxo](https://github.com/nixxo)
* [rumble] unescape title
* [RUTV] Fix format sorting by [Lesmiscore](https://github.com/Lesmiscore)
* [ruutu] Detect embeds by [tpikonen](https://github.com/tpikonen)
* [tenplay] Improve extractor by [aarubui](https://github.com/aarubui)
* [TikTok] Fix URLs with user id by [hatienl0i261299](https://github.com/hatienl0i261299)
* [TikTokVM] Fix redirect to user URL
* [TVer] Fix extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [TVer] Support landing page by [vvto33](https://github.com/vvto33)
* [twitcasting] Don't return multi_video for archive with single hls manifest by [Lesmiscore](https://github.com/Lesmiscore)
* [veo] Fix `_VALID_URL`
* [Veo] Fix extractor by [i6t](https://github.com/i6t)
* [viki] Don't attempt to modify URLs with signature by [nyuszika7h](https://github.com/nyuszika7h)
* [viu] Fix bypass for preview by [zackmark29](https://github.com/zackmark29)
* [viu] Fixed extractor by [zackmark29](https://github.com/zackmark29), [pukkandan](https://github.com/pukkandan)
* [web.archive:youtube] Make CDX API requests non-fatal by [coletdjnz](https://github.com/coletdjnz)
* [wget] Fix proxy by [kikuyan](https://github.com/kikuyan), [coletdjnz](https://github.com/coletdjnz)
* [xnxx] Add `xnxx3.com` by [rozari0](https://github.com/rozari0)
* [youtube] **Add new age-gate bypass** by [zerodytrash](https://github.com/zerodytrash), [pukkandan](https://github.com/pukkandan)
* [youtube] Add extractor-arg to skip auto-translated subs
* [youtube] Avoid false positives when detecting damaged formats
* [youtube] Detect DRM better by [shirt](https://github.com/shirt-dev)
* [youtube] Fix auto-translated automatic captions
* [youtube] Fix pagination of `membership` tab
* [youtube] Fix uploader for collaborative playlists by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Improve video upload date handling by [coletdjnz](https://github.com/coletdjnz)
* [youtube:api] Prefer minified JSON response by [coletdjnz](https://github.com/coletdjnz)
* [youtube:search] Support hashtag entries by [coletdjnz](https://github.com/coletdjnz)
* [youtube:tab] Fix duration extraction for shorts by [coletdjnz](https://github.com/coletdjnz)
* [youtube:tab] Minor improvements
* [youtube:tab] Return shorts url if video is a short by [coletdjnz](https://github.com/coletdjnz)
* [Zattoo] Fix extractors by [goggle](https://github.com/goggle)
* [Zingmp3] Fix signature by [hatienl0i261299](https://github.com/hatienl0i261299)


### 2022.03.08.1

* [cleanup] Refactor `__init__.py`
* [build] Fix bug

### 2022.03.08

* Merge youtube-dl: Upto [commit/6508688](https://github.com/ytdl-org/youtube-dl/commit/6508688e88c83bb811653083db9351702cd39a6a) (except NDR)
* Add regex operator and quoting to format filters by [lukasfink1](https://github.com/lukasfink1)
* Add brotli content-encoding support by [coletdjnz](https://github.com/coletdjnz)
* Add pre-processor stage `after_filter`
* Better error message when no `--live-from-start` format
* Create necessary directories for `--print-to-file`
* Fill more fields for playlists by [Lesmiscore](https://github.com/Lesmiscore)
* Fix `-all` for `--sub-langs`
* Fix doubling of `video_id` in `ExtractorError`
* Fix for when stdout/stderr encoding is `None`
* Handle negative duration from extractor
* Implement `--add-header` without modifying `std_headers`
* Obey `--abort-on-error` for "ffmpeg not installed"
* Set `webpage_url_...` from `webpage_url` and not input URL
* Tolerate failure to `--write-link` due to unknown URL
* [aria2c] Add `--http-accept-gzip=true`
* [build] Update pyinstaller to 4.10 by [shirt](https://github.com/shirt-dev)
* [cookies] Update MacOS12 `Cookies.binarycookies` location by [mdpauley](https://github.com/mdpauley)
* [devscripts] Improve `prepare_manpage`
* [downloader] Do not use aria2c for non-native `m3u8`
* [downloader] Obey `--file-access-retries` when deleting/renaming by [ehoogeveen-medweb](https://github.com/ehoogeveen-medweb)
* [extractor] Allow `http_headers` to be specified for `thumbnails`
* [extractor] Extract subtitles from manifests for vimeo, globo, kaltura, svt by [fstirlitz](https://github.com/fstirlitz)
* [extractor] Fix for manifests without period duration by [dirkf](https://github.com/dirkf), [pukkandan](https://github.com/pukkandan)
* [extractor] Support `--mark-watched` without `_NETRC_MACHINE` by [coletdjnz](https://github.com/coletdjnz)
* [FFmpegConcat] Abort on `--simulate`
* [FormatSort] Consider `acodec`=`ogg` as `vorbis`
* [fragment] Fix bugs around resuming with Range by [Lesmiscore](https://github.com/Lesmiscore)
* [fragment] Improve `--live-from-start` for YouTube livestreams by [Lesmiscore](https://github.com/Lesmiscore)
* [generic] Pass referer to extracted formats
* [generic] Set rss `guid` as video id by [Bricio](https://github.com/Bricio)
* [options] Better ambiguous option resolution
* [options] Rename `--clean-infojson` to `--clean-info-json`
* [SponsorBlock] Fixes for highlight and "full video labels" by [nihil-admirari](https://github.com/nihil-admirari)
* [Sponsorblock] minor fixes by [nihil-admirari](https://github.com/nihil-admirari)
* [utils] Better traceback for `ExtractorError`
* [utils] Fix file locking for AOSP by [jakeogh](https://github.com/jakeogh)
* [utils] Improve file locking
* [utils] OnDemandPagedList: Do not download pages after error
* [utils] render_table: Fix character calculation for removing extra gap by [Lesmiscore](https://github.com/Lesmiscore)
* [utils] Use `locked_file` for `sanitize_open` by [jakeogh](https://github.com/jakeogh)
* [utils] Validate `DateRange` input
* [utils] WebSockets wrapper for non-async functions by [Lesmiscore](https://github.com/Lesmiscore)
* [cleanup] Don't pass protocol to `_extract_m3u8_formats` for live videos
* [cleanup] Remove extractors for some dead websites by [marieell](https://github.com/marieell)
* [cleanup, docs] Misc cleanup
* [AbemaTV] Add extractors by [Lesmiscore](https://github.com/Lesmiscore)
* [adobepass] Add Suddenlink MSO by [CplPwnies](https://github.com/CplPwnies)
* [ant1newsgr] Add extractor by [zmousm](https://github.com/zmousm)
* [bigo] Add extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [Caltrans] Add extractor by [Bricio](https://github.com/Bricio)
* [daystar] Add extractor by [hatienl0i261299](https://github.com/hatienl0i261299)
* [fc2:live] Add extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [fptplay] Add extractor by [hatienl0i261299](https://github.com/hatienl0i261299)
* [murrtube] Add extractor by [cyberfox1691](https://github.com/cyberfox1691)
* [nfb] Add extractor by [ofkz](https://github.com/ofkz)
* [niconico] Add playlist extractors and refactor by [Lesmiscore](https://github.com/Lesmiscore)
* [peekvids] Add extractor by [schn0sch](https://github.com/schn0sch)
* [piapro] Add extractor by [pycabbage](https://github.com/pycabbage), [Lesmiscore](https://github.com/Lesmiscore)
* [rokfin] Add extractor by [P-reducible](https://github.com/P-reducible), [pukkandan](https://github.com/pukkandan)
* [rokfin] Add stack and channel extractors by [P-reducible](https://github.com/P-reducible), [pukkandan](https://github.com/pukkandan)
* [ruv.is] Add extractor by [iw0nderhow](https://github.com/iw0nderhow)
* [telegram] Add extractor by [hatienl0i261299](https://github.com/hatienl0i261299)
* [VideocampusSachsen] Add extractors by [FestplattenSchnitzel](https://github.com/FestplattenSchnitzel)
* [xinpianchang] Add extractor by [hatienl0i261299](https://github.com/hatienl0i261299)
* [abc] Support 1080p by [Ronnnny](https://github.com/Ronnnny)
* [afreecatv] Support password-protected livestreams by [wlritchi](https://github.com/wlritchi)
* [ard] Fix valid URL
* [ATVAt] Detect geo-restriction by [marieell](https://github.com/marieell)
* [bandcamp] Detect acodec
* [bandcamp] Fix user URLs by [lyz-code](https://github.com/lyz-code)
* [bbc] Fix extraction of news articles by [ajj8](https://github.com/ajj8)
* [beeg] Fix extractor by [Bricio](https://github.com/Bricio)
* [bigo] Fix extractor to not to use `form_params`
* [Bilibili] Pass referer for all formats by [blackgear](https://github.com/blackgear)
* [Biqle] Fix extractor by [Bricio](https://github.com/Bricio)
* [ccma] Fix timestamp parsing by [nyuszika7h](https://github.com/nyuszika7h)
* [crunchyroll] Better error reporting on login failure by [tejing1](https://github.com/tejing1)
* [cspan] Support of C-Span congress videos by [Grabien](https://github.com/Grabien)
* [dropbox] fix regex by [zenerdi0de](https://github.com/zenerdi0de)
* [fc2] Fix extraction by [Lesmiscore](https://github.com/Lesmiscore)
* [fujitv] Extract resolution for free sources by [YuenSzeHong](https://github.com/YuenSzeHong)
* [Gettr] Add `GettrStreamingIE` by [i6t](https://github.com/i6t)
* [Gettr] Fix formats order by [i6t](https://github.com/i6t)
* [Gettr] Improve extractor by [i6t](https://github.com/i6t)
* [globo] Expand valid URL by [Bricio](https://github.com/Bricio)
* [lbry] Fix `--ignore-no-formats-error`
* [manyvids] Extract `uploader` by [regarten](https://github.com/regarten)
* [mildom] Fix linter
* [mildom] Rework extractors by [Lesmiscore](https://github.com/Lesmiscore)
* [mirrativ] Cleanup extractor code by [Lesmiscore](https://github.com/Lesmiscore)
* [nhk] Add support for NHK for School by [Lesmiscore](https://github.com/Lesmiscore)
* [niconico:tag] Add support for searching tags
* [nrk] Add fallback API
* [peekvids] Use JSON-LD by [schn0sch](https://github.com/schn0sch)
* [peertube] Add media.fsfe.org by [mxmehl](https://github.com/mxmehl)
* [rtvs] Fix extractor by [Bricio](https://github.com/Bricio)
* [spiegel] Fix `_VALID_URL`
* [ThumbnailsConvertor] Support `webp`
* [tiktok] Fix `vm.tiktok`/`vt.tiktok` URLs
* [tubitv] Fix/improve TV series extraction by [bbepis](https://github.com/bbepis)
* [tumblr] Fix extractor by [foghawk](https://github.com/foghawk)
* [twitcasting] Add fallback for finding running live by [Lesmiscore](https://github.com/Lesmiscore)
* [TwitCasting] Check for password protection by [Lesmiscore](https://github.com/Lesmiscore)
* [twitcasting] Fix extraction by [Lesmiscore](https://github.com/Lesmiscore)
* [twitch] Fix field name of `view_count`
* [twitter] Fix for private videos by [iphoting](https://github.com/iphoting)
* [washingtonpost] Fix extractor by [Bricio](https://github.com/Bricio)
* [youtube:tab] Add `approximate_date` extractor-arg
* [youtube:tab] Follow redirect to regional channel  by [coletdjnz](https://github.com/coletdjnz)
* [youtube:tab] Reject webpage data if redirected to home page
* [youtube] De-prioritize potentially damaged formats
* [youtube] Differentiate descriptive audio by language code
* [youtube] Ensure subtitle urls are absolute by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Escape possible `$` in `_extract_n_function_name` regex by [Lesmiscore](https://github.com/Lesmiscore)
* [youtube] Fix automatic captions
* [youtube] Fix n-sig extraction for phone player JS by [MinePlayersPE](https://github.com/MinePlayersPE)
* [youtube] Further de-prioritize 3gp format
* [youtube] Label original auto-subs
* [youtube] Prefer UTC upload date for videos by [coletdjnz](https://github.com/coletdjnz)
* [zaq1] Remove dead extractor by [marieell](https://github.com/marieell)
* [zee5] Support web-series by [Aniruddh-J](https://github.com/Aniruddh-J)
* [zingmp3] Fix extractor by [hatienl0i261299](https://github.com/hatienl0i261299)
* [zoom] Add support for screen cast by [Mipsters](https://github.com/Mipsters)


### 2022.02.04

* [youtube:search] Fix extractor by [coletdjnz](https://github.com/coletdjnz)
* [youtube:search] Add tests
* [twitcasting] Enforce UTF-8 for POST payload by [Lesmiscore](https://github.com/Lesmiscore)
* [mediaset] Fix extractor by [nixxo](https://github.com/nixxo)
* [websocket] Make syntax error in `websockets` module non-fatal

### 2022.02.03

* Merge youtube-dl: Upto [commit/78ce962](https://github.com/ytdl-org/youtube-dl/commit/78ce962f4fe020994c216dd2671546fbe58a5c67)
* Add option `--print-to-file`
* Make nested --config-locations relative to parent file
* Ensure `_type` is present in `info.json`
* Fix `--compat-options list-formats`
* Fix/improve `InAdvancePagedList`
* [downloader/ffmpeg] Handle unknown formats better
* [outtmpl] Handle `-o ""` better
* [outtmpl] Handle hard-coded file extension better
* [extractor] Add convenience function `_yes_playlist`
* [extractor] Allow non-fatal `title` extraction
* [extractor] Extract video inside `Article` json_ld
* [generic] Allow further processing of json_ld URL
* [cookies] Fix keyring selection for unsupported desktops
* [utils] Strip double spaces in `clean_html` by [dirkf](https://github.com/dirkf)
* [aes] Add `unpad_pkcs7`
* [test] Fix `test_youtube_playlist_noplaylist`
* [docs,cleanup] Misc cleanup
* [dplay] Add extractors for site changes by [Sipherdrakon](https://github.com/Sipherdrakon)
* [ertgr] Add  extractors by [zmousm](https://github.com/zmousm), [dirkf](https://github.com/dirkf)
* [Musicdex] Add extractors by [Ashish0804](https://github.com/Ashish0804)
* [YandexVideoPreview] Add extractor by [KiberInfinity](https://github.com/KiberInfinity)
* [youtube] Add extractor `YoutubeMusicSearchURLIE`
* [archive.org] Ignore unnecessary files
* [Bilibili] Add 8k support by [u-spec-png](https://github.com/u-spec-png)
* [bilibili] Fix extractor, make anthology title non-fatal
* [CAM4] Add thumbnail extraction by [alerikaisattera](https://github.com/alerikaisattera)
* [cctv] De-prioritize sample format
* [crunchyroll:beta] Add cookies support by [tejing1](https://github.com/tejing1)
* [crunchyroll] Fix login by [tejing1](https://github.com/tejing1)
* [doodstream] Fix extractor
* [fc2] Fix extraction by [Lesmiscore](https://github.com/Lesmiscore)
* [FFmpegConcat] Abort on --skip-download and download errors
* [Fujitv] Extract metadata and support premium by [YuenSzeHong](https://github.com/YuenSzeHong)
* [globo] Fix extractor by [Bricio](https://github.com/Bricio)
* [glomex] Simplify embed detection
* [GoogleSearch] Fix extractor
* [Instagram] Fix extraction when logged in by [MinePlayersPE](https://github.com/MinePlayersPE)
* [iq.com] Add VIP support by [MinePlayersPE](https://github.com/MinePlayersPE)
* [mildom] Fix extractor by [lazypete365](https://github.com/lazypete365)
* [MySpass] Fix video url processing by [trassshhub](https://github.com/trassshhub)
* [Odnoklassniki] Improve embedded players extraction by [KiberInfinity](https://github.com/KiberInfinity)
* [orf:tvthek] Lazy playlist extraction and obey --no-playlist
* [Pladform] Fix redirection to external player by [KiberInfinity](https://github.com/KiberInfinity)
* [ThisOldHouse] Improve Premium URL check by [Ashish0804](https://github.com/Ashish0804)
* [TikTok] Iterate through app versions by [MinePlayersPE](https://github.com/MinePlayersPE)
* [tumblr] Fix 403 errors and handle vimeo embeds by [foghawk](https://github.com/foghawk)
* [viki] Fix "Bad request" for manifest by [nyuszika7h](https://github.com/nyuszika7h)
* [Vimm] add recording extractor by [alerikaisattera](https://github.com/alerikaisattera)
* [web.archive:youtube] Add `ytarchive:` prefix and misc cleanup
* [youtube:api] Do not use seek when reading HTTPError response by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Fix n-sig for player e06dea74
* [youtube, cleanup] Misc fixes and cleanup


### 2022.01.21

* Add option `--concat-playlist` to **concat videos in a playlist**
* Allow **multiple and nested configuration files**
* Add more post-processing stages (`after_video`, `playlist`)
* Allow `--exec` to be run at any post-processing stage (Deprecates `--exec-before-download`)
* Allow `--print` to be run at any post-processing stage
* Allow listing formats, thumbnails, subtitles using `--print` by [pukkandan](https://github.com/pukkandan), [Zirro](https://github.com/Zirro)
* Add fields `video_autonumber`, `modified_date`, `modified_timestamp`, `playlist_count`, `channel_follower_count`
* Add key `requested_downloads` in the root `info_dict`
* Write `download_archive` only after all formats are downloaded
* [FfmpegMetadata] Allow setting metadata of individual streams using `meta<n>_` prefix
* Add option `--legacy-server-connect` by [xtkoba](https://github.com/xtkoba)
* Allow escaped `,` in `--extractor-args`
* Allow unicode characters in `info.json`
* Check for existing thumbnail/subtitle in final directory
* Don't treat empty containers as `None` in `sanitize_info`
* Fix `-s --ignore-no-formats --force-write-archive`
* Fix live title for multiple formats
* List playlist thumbnails in `--list-thumbnails`
* Raise error if subtitle download fails
* [cookies] Fix bug when keyring is unspecified
* [ffmpeg] Ignore unknown streams, standardize use of `-map 0`
* [outtmpl] Alternate form for `D` and fix suffix's case
* [utils] Add `Sec-Fetch-Mode` to `std_headers`
* [utils] Fix `format_bytes` output for Bytes by [pukkandan](https://github.com/pukkandan), [mdawar](https://github.com/mdawar)
* [utils] Handle `ss:xxx` in `parse_duration`
* [utils] Improve parsing for nested HTML elements by [zmousm](https://github.com/zmousm), [pukkandan](https://github.com/pukkandan)
* [utils] Use key `None` in `traverse_obj` to return as-is
* [extractor] Detect more subtitle codecs in MPD manifests by [fstirlitz](https://github.com/fstirlitz)
* [extractor] Extract chapters from JSON-LD by [iw0nderhow](https://github.com/iw0nderhow), [pukkandan](https://github.com/pukkandan)
* [extractor] Extract thumbnails from JSON-LD by [nixxo](https://github.com/nixxo)
* [extractor] Improve `url_result` and related
* [generic] Improve KVS player extraction by [trassshhub](https://github.com/trassshhub)
* [build] Reduce dependency on third party workflows
* [extractor,cleanup] Use `_search_nextjs_data`, `format_field`
* [cleanup] Minor fixes and cleanup
* [docs] Improvements
* [test] Fix TestVerboseOutput
* [afreecatv] Add livestreams extractor by [wlritchi](https://github.com/wlritchi)
* [callin] Add extractor by [foghawk](https://github.com/foghawk)
* [CrowdBunker] Add extractors by [Ashish0804](https://github.com/Ashish0804)
* [daftsex] Add extractors by [k3ns1n](https://github.com/k3ns1n)
* [digitalconcerthall] Add extractor by [teridon](https://github.com/teridon)
* [Drooble] Add extractor by [u-spec-png](https://github.com/u-spec-png)
* [EuropeanTour] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [iq.com] Add extractors by [MinePlayersPE](https://github.com/MinePlayersPE)
* [KelbyOne] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [LnkIE] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [MainStreaming] Add extractor by [coletdjnz](https://github.com/coletdjnz)
* [megatvcom] Add extractors by [zmousm](https://github.com/zmousm)
* [Newsy] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [noodlemagazine] Add extractor by [trassshhub](https://github.com/trassshhub)
* [PokerGo] Add extractors by [Ashish0804](https://github.com/Ashish0804)
* [Pornez] Add extractor by [mozlima](https://github.com/mozlima)
* [PRX] Add Extractors by [coletdjnz](https://github.com/coletdjnz)
* [RTNews] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [Rule34video] Add extractor by [trassshhub](https://github.com/trassshhub)
* [tvopengr] Add extractors by [zmousm](https://github.com/zmousm)
* [Vimm] Add extractor by [alerikaisattera](https://github.com/alerikaisattera)
* [glomex] Add extractors by [zmousm](https://github.com/zmousm)
* [instagram] Add story/highlight extractor by [u-spec-png](https://github.com/u-spec-png)
* [openrec] Add movie extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [rai] Add Raiplaysound extractors by [nixxo](https://github.com/nixxo), [pukkandan](https://github.com/pukkandan)
* [aparat] Fix extractor
* [ard] Extract subtitles by [fstirlitz](https://github.com/fstirlitz)
* [BiliIntl] Add login by [MinePlayersPE](https://github.com/MinePlayersPE)
* [CeskaTelevize] Use `http` for manifests
* [CTVNewsIE] Add fallback for video search by [Ashish0804](https://github.com/Ashish0804)
* [dplay] Migrate DiscoveryPlusItaly to DiscoveryPlus by [timendum](https://github.com/timendum)
* [dplay] Re-structure DiscoveryPlus extractors
* [Dropbox] Support password protected files and more formats by [zenerdi0de](https://github.com/zenerdi0de)
* [facebook] Fix extraction from groups
* [facebook] Improve title and uploader extraction
* [facebook] Parse dash manifests
* [fox] Extract m3u8 from preview by [ischmidt20](https://github.com/ischmidt20)
* [funk] Support origin URLs
* [gfycat] Fix `uploader`
* [gfycat] Support embeds by [coletdjnz](https://github.com/coletdjnz)
* [hotstar] Add extractor args to ignore tags by [Ashish0804](https://github.com/Ashish0804)
* [hrfernsehen] Fix ardloader extraction by [CreaValix](https://github.com/CreaValix)
* [instagram] Fix username extraction for stories and highlights by [nyuszika7h](https://github.com/nyuszika7h)
* [kakao] Detect geo-restriction
* [line] Remove `tv.line.me` by [sian1468](https://github.com/sian1468)
* [mixch] Add `MixchArchiveIE` by [Lesmiscore](https://github.com/Lesmiscore)
* [mixcloud] Detect restrictions by [llacb47](https://github.com/llacb47)
* [NBCSports] Fix extraction of platform URLs by [ischmidt20](https://github.com/ischmidt20)
* [Nexx] Extract more metadata by [MinePlayersPE](https://github.com/MinePlayersPE)
* [Nexx] Support 3q CDN by [MinePlayersPE](https://github.com/MinePlayersPE)
* [pbs] de-prioritize AD formats
* [PornHub,YouTube] Refresh onion addresses by [unit193](https://github.com/unit193)
* [RedBullTV] Parse subtitles from manifest by [Ashish0804](https://github.com/Ashish0804)
* [streamcz] Fix extractor by [arkamar](https://github.com/arkamar), [pukkandan](https://github.com/pukkandan)
* [Ted] Rewrite extractor by [pukkandan](https://github.com/pukkandan), [trassshhub](https://github.com/trassshhub)
* [Theta] Fix valid URL by [alerikaisattera](https://github.com/alerikaisattera)
* [ThisOldHouseIE] Add support for premium videos by [Ashish0804](https://github.com/Ashish0804)
* [TikTok] Fix extraction for sigi-based webpages, add API fallback by [MinePlayersPE](https://github.com/MinePlayersPE)
* [TikTok] Pass cookies to formats, and misc fixes by [MinePlayersPE](https://github.com/MinePlayersPE)
* [TikTok] Extract captions, user thumbnail by [MinePlayersPE](https://github.com/MinePlayersPE)
* [TikTok] Change app version by [MinePlayersPE](https://github.com/MinePlayersPE), [llacb47](https://github.com/llacb47)
* [TVer] Extract message for unaired live by [Lesmiscore](https://github.com/Lesmiscore)
* [twitcasting] Refactor extractor by [Lesmiscore](https://github.com/Lesmiscore)
* [twitter] Fix video in quoted tweets
* [veoh] Improve extractor by [foghawk](https://github.com/foghawk)
* [vk] Capture `clip` URLs
* [vk] Fix VKUserVideosIE by [Ashish0804](https://github.com/Ashish0804)
* [vk] Improve `_VALID_URL` by [k3ns1n](https://github.com/k3ns1n)
* [VrtNU] Handle empty title by [pgaig](https://github.com/pgaig)
* [XVideos] Check HLS formats by [MinePlayersPE](https://github.com/MinePlayersPE)
* [yahoo:gyao] Improved playlist handling by [hyano](https://github.com/hyano)
* [youtube:tab] Extract more playlist metadata by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [youtube:tab] Raise error on tab redirect by [krichbanana](https://github.com/krichbanana), [coletdjnz](https://github.com/coletdjnz)
* [youtube] Update Innertube clients by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Detect live-stream embeds
* [youtube] Do not return `upload_date` for playlists
* [youtube] Extract channel subscriber count by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Make invalid storyboard URL non-fatal
* [youtube] Enforce UTC, update innertube clients and tests by [coletdjnz](https://github.com/coletdjnz)
* [zdf] Add chapter extraction by [iw0nderhow](https://github.com/iw0nderhow)
* [zee5] Add geo-bypass


### 2021.12.27

* Avoid recursion error when re-extracting info
* [ffmpeg] Fix position of `--ppa`
* [aria2c] Don't show progress when `--no-progress`
* [cookies] Support other keyrings by [mbway](https://github.com/mbway)
* [EmbedThumbnail] Prefer AtomicParsley over ffmpeg if available
* [generic] Fix HTTP KVS Player by [git-anony-mouse](https://github.com/git-anony-mouse)
* [ThumbnailsConvertor] Fix for when there are no thumbnails
* [docs] Add examples for using `TYPES:` in `-P`/`-o`
* [PixivSketch] Add extractors by [nao20010128nao](https://github.com/nao20010128nao)
* [tiktok] Add music, sticker and tag IEs by [MinePlayersPE](https://github.com/MinePlayersPE)
* [BiliIntl] Fix extractor by [MinePlayersPE](https://github.com/MinePlayersPE)
* [CBC] Fix URL regex
* [tiktok] Fix `extractor_key` used in archive
* [youtube] **End `live-from-start` properly when stream ends with 403**
* [Zee5] Fix VALID_URL for tv-shows by [Ashish0804](https://github.com/Ashish0804)

### 2021.12.25

* [dash,youtube] **Download live from start to end** by [nao20010128nao](https://github.com/nao20010128nao), [pukkandan](https://github.com/pukkandan)
    * Add option `--live-from-start` to enable downloading live videos from start
    * Add key `is_from_start` in formats to identify formats (of live videos) that downloads from start
    * [dash] Create protocol `http_dash_segments_generator` that allows a function to be passed instead of fragments
    * [fragment] Allow multiple live dash formats to download simultaneously
    * [youtube] Implement fragment re-fetching for the live dash formats
    * [youtube] Re-extract dash manifest every 5 hours (manifest expires in 6hrs)
    * [postprocessor/ffmpeg] Add `FFmpegFixupDuplicateMoovPP` to fixup duplicated moov atoms
    * Known issues:
        * Ctrl+C doesn't work on Windows when downloading multiple formats
        * If video becomes private, download hangs
* [SponsorBlock] Add `Filler` and `Highlight` categories by [nihil-admirari](https://github.com/nihil-admirari), [pukkandan](https://github.com/pukkandan)
    * Change `--sponsorblock-cut all` to `--sponsorblock-cut default` if you do not want filler sections to be removed
* Add field `webpage_url_domain`
* Add interactive format selection with `-f -`
* Add option `--file-access-retries` by [ehoogeveen-medweb](https://github.com/ehoogeveen-medweb)
* [outtmpl] Add alternate forms `S`, `D` and improve `id` detection
* [outtmpl] Add operator `&` for replacement text by [PilzAdam](https://github.com/PilzAdam)
* [EmbedSubtitle] Disable duration check temporarily
* [extractor] Add `_search_nuxt_data` by [nao20010128nao](https://github.com/nao20010128nao)
* [extractor] Ignore errors in comment extraction when `-i` is given
* [extractor] Standardize `_live_title`
* [FormatSort] Prevent incorrect deprecation warning
* [generic] Extract m3u8 formats from JSON-LD
* [postprocessor/ffmpeg] Always add `faststart`
* [utils] Fix parsing `YYYYMMDD` dates in Nov/Dec by [wlritchi](https://github.com/wlritchi)
* [utils] Improve `parse_count`
* [utils] Update `std_headers` by [kikuyan](https://github.com/kikuyan), [fstirlitz](https://github.com/fstirlitz)
* [lazy_extractors] Fix for search IEs
* [extractor] Support default implicit graph in JSON-LD by [zmousm](https://github.com/zmousm)
* Allow `--no-write-thumbnail` to override `--write-all-thumbnail`
* Fix `--throttled-rate`
* Fix control characters being printed to `--console-title`
* Fix PostProcessor hooks not registered for some PPs
* Pre-process when using `--flat-playlist`
* Remove known invalid thumbnails from `info_dict`
* Add warning when using `-f best`
* Use `parse_duration` for `--wait-for-video` and some minor fix
* [test/download] Add more fields
* [test/download] Ignore field `webpage_url_domain` by [std-move](https://github.com/std-move)
* [compat] Suppress errors in enabling VT mode
* [docs] Improve manpage format by [iw0nderhow](https://github.com/iw0nderhow), [pukkandan](https://github.com/pukkandan)
* [docs,cleanup] Minor fixes and cleanup
* [cleanup] Fix some typos by [unit193](https://github.com/unit193)
* [ABC:iview] Add show extractor by [pabs3](https://github.com/pabs3)
* [dropout] Add extractor by [TwoThousandHedgehogs](https://github.com/TwoThousandHedgehogs), [pukkandan](https://github.com/pukkandan)
* [GameJolt] Add extractors by [MinePlayersPE](https://github.com/MinePlayersPE)
* [gofile] Add extractor by [Jertzukka](https://github.com/Jertzukka), [Ashish0804](https://github.com/Ashish0804)
* [hse] Add extractors by [cypheron](https://github.com/cypheron), [pukkandan](https://github.com/pukkandan)
* [NateTV] Add NateIE and NateProgramIE by [Ashish0804](https://github.com/Ashish0804), [Hyeeji](https://github.com/Hyeeji)
* [OpenCast] Add extractors by [bwildenhain](https://github.com/bwildenhain), [C0D3D3V](https://github.com/C0D3D3V)
* [rtve] Add `RTVEAudioIE` by [kebianizao](https://github.com/kebianizao)
* [Rutube] Add RutubeChannelIE by [Ashish0804](https://github.com/Ashish0804)
* [skeb] Add extractor by [nao20010128nao](https://github.com/nao20010128nao)
* [soundcloud] Add related tracks extractor by [Lapin0t](https://github.com/Lapin0t)
* [toggo] Add extractor by [nyuszika7h](https://github.com/nyuszika7h)
* [TrueID] Add extractor by [MinePlayersPE](https://github.com/MinePlayersPE)
* [audiomack] Update album and song VALID_URL by [abdullah-if](https://github.com/abdullah-if), [dirkf](https://github.com/dirkf)
* [CBC Gem] Extract 1080p formats by [DavidSkrundz](https://github.com/DavidSkrundz)
* [ceskatelevize] Fetch iframe from nextJS data by [mkubecek](https://github.com/mkubecek)
* [crackle] Look for non-DRM formats by [raleeper](https://github.com/raleeper)
* [dplay] Temporary fix for `discoveryplus.com/it`
* [DiscoveryPlusShowBaseIE] yield actual video id by [Ashish0804](https://github.com/Ashish0804)
* [Facebook] Handle redirect URLs
* [fujitv] Extract 1080p from `tv_android` m3u8 by [YuenSzeHong](https://github.com/YuenSzeHong)
* [gronkh] Support new URL pattern by [Sematre](https://github.com/Sematre)
* [instagram] Expand valid URL by [u-spec-png](https://github.com/u-spec-png)
* [Instagram] Try bypassing login wall with embed page by [MinePlayersPE](https://github.com/MinePlayersPE)
* [Jamendo] Fix use of `_VALID_URL_RE` by [jaller94](https://github.com/jaller94)
* [LBRY] Support livestreams by [Ashish0804](https://github.com/Ashish0804), [pukkandan](https://github.com/pukkandan)
* [NJPWWorld] Extract formats from m3u8 by [aarubui](https://github.com/aarubui)
* [NovaEmbed] update player regex by [std-move](https://github.com/std-move)
* [npr] Make SMIL extraction non-fatal by [r5d](https://github.com/r5d)
* [ntvcojp] Extract NUXT data by [nao20010128nao](https://github.com/nao20010128nao)
* [ok.ru] add mobile fallback by [nao20010128nao](https://github.com/nao20010128nao)
* [olympics] Add uploader and cleanup by [u-spec-png](https://github.com/u-spec-png)
* [ondemandkorea] Update `jw_config` regex by [julien-hadleyjack](https://github.com/julien-hadleyjack)
* [PlutoTV] Expand `_VALID_URL`
* [RaiNews] Fix extractor by [nixxo](https://github.com/nixxo)
* [RCTIPlusSeries] Lazy extraction and video type selection by [MinePlayersPE](https://github.com/MinePlayersPE)
* [redtube] Handle formats delivered inside a JSON by [dirkf](https://github.com/dirkf), [nixxo](https://github.com/nixxo)
* [SonyLiv] Add OTP login support by [Ashish0804](https://github.com/Ashish0804)
* [Steam] Fix extractor by [u-spec-png](https://github.com/u-spec-png)
* [TikTok] Pass cookies to mobile API by [MinePlayersPE](https://github.com/MinePlayersPE)
* [trovo] Fix inheritance of `TrovoChannelBaseIE`
* [TVer] Extract better thumbnails by [YuenSzeHong](https://github.com/YuenSzeHong)
* [vimeo] Extract chapters
* [web.archive:youtube] Improve metadata extraction by [coletdjnz](https://github.com/coletdjnz)
* [youtube:comments] Add more options for limiting number of comments extracted by [coletdjnz](https://github.com/coletdjnz)
* [youtube:tab] Extract more metadata from feeds/channels/playlists by [coletdjnz](https://github.com/coletdjnz)
* [youtube:tab] Extract video thumbnails from playlist by [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [youtube:tab] Ignore query when redirecting channel to playlist and cleanup of related code
* [youtube] Fix `ytsearchdate`
* [zdf] Support videos with different ptmd location by [iw0nderhow](https://github.com/iw0nderhow)
* [zee5] Support /episodes in URL


### 2021.12.01

* **Add option `--wait-for-video` to wait for scheduled streams**
* Add option `--break-per-input` to apply --break-on... to each input URL
* Add option `--embed-info-json` to embed info.json in mkv
* Add compat-option `embed-metadata`
* Allow using a custom format selector through API
* [AES] Add ECB mode by [nao20010128nao](https://github.com/nao20010128nao)
* [build] Fix MacOS Build
* [build] Save Git HEAD at release alongside version info
* [build] Use `workflow_dispatch` for release
* [downloader/ffmpeg] Fix for direct videos inside mpd manifests
* [downloader] Add colors to download progress
* [EmbedSubtitles] Slightly relax duration check and related cleanup
* [ExtractAudio] Fix conversion to `wav` and `vorbis`
* [ExtractAudio] Support `alac`
* [extractor] Extract `average_rating` from JSON-LD
* [FixupM3u8] Fixup MPEG-TS in MP4 container
* [generic] Support mpd manifests without extension by [shirt](https://github.com/shirt-dev)
* [hls] Better FairPlay DRM detection by [nyuszika7h](https://github.com/nyuszika7h)
* [jsinterp] Fix splice to handle float (for youtube js player f1ca6900)
* [utils] Allow alignment in `render_table` and add tests
* [utils] Fix `PagedList`
* [utils] Fix error when copying `LazyList`
* Clarify video/audio-only formats in -F
* Ensure directory exists when checking formats
* Ensure path for link files exists by [Zirro](https://github.com/Zirro)
* Ensure same config file is not loaded multiple times
* Fix `postprocessor_hooks`
* Fix `--break-on-archive` when pre-checking
* Fix `--check-formats` for `mhtml`
* Fix `--load-info-json` of playlists with failed entries
* Fix `--trim-filename` when filename has `.`
* Fix bug in parsing `--add-header`
* Fix error in `report_unplayable_conflict` by [shirt](https://github.com/shirt-dev)
* Fix writing playlist infojson with `--no-clean-infojson`
* Validate --get-bypass-country
* [blogger] Add extractor by [pabs3](https://github.com/pabs3)
* [breitbart] Add extractor by [Grabien](https://github.com/Grabien)
* [CableAV] Add extractor by [j54vc1bk](https://github.com/j54vc1bk)
* [CanalAlpha] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [CozyTV] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [CPTwentyFour] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [DiscoveryPlus] Add `DiscoveryPlusItalyShowIE` by [Ashish0804](https://github.com/Ashish0804)
* [ESPNCricInfo] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [LinkedIn] Add extractor by [u-spec-png](https://github.com/u-spec-png)
* [mixch] Add extractor by [nao20010128nao](https://github.com/nao20010128nao)
* [nebula] Add `NebulaCollectionIE` and rewrite extractor by [hheimbuerger](https://github.com/hheimbuerger)
* [OneFootball] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [peer.tv] Add extractor by [u-spec-png](https://github.com/u-spec-png)
* [radiozet] Add extractor by [0xA7404A](https://github.com/0xA7404A) (Aurora)
* [redgifs] Add extractor by [chio0hai](https://github.com/chio0hai)
* [RedGifs] Add Search and User extractors by [Deer-Spangle](https://github.com/Deer-Spangle)
* [rtrfm] Add extractor by [pabs3](https://github.com/pabs3)
* [Streamff] Add extractor by [cntrl-s](https://github.com/cntrl-s)
* [Stripchat] Add extractor by [zulaport](https://github.com/zulaport)
* [Aljazeera] Fix extractor by [u-spec-png](https://github.com/u-spec-png)
* [AmazonStoreIE] Fix regex to not match vdp urls by [Ashish0804](https://github.com/Ashish0804)
* [ARDBetaMediathek] Handle new URLs
* [bbc] Get all available formats by [nyuszika7h](https://github.com/nyuszika7h)
* [Bilibili] Fix title extraction by [u-spec-png](https://github.com/u-spec-png)
* [CBC Gem] Fix for shows that don't have all seasons by [makeworld-the-better-one](https://github.com/makeworld-the-better-one)
* [curiositystream] Add more metadata
* [CuriosityStream] Fix series
* [DiscoveryPlus] Rewrite extractors by [Ashish0804](https://github.com/Ashish0804), [pukkandan](https://github.com/pukkandan)
* [HotStar] Set language field from tags by [Ashish0804](https://github.com/Ashish0804)
* [instagram, cleanup] Refactor extractors
* [Instagram] Display more login errors by [MinePlayersPE](https://github.com/MinePlayersPE)
* [itv] Fix extractor by [staubichsauger](https://github.com/staubichsauger), [pukkandan](https://github.com/pukkandan)
* [mediaklikk] Expand valid URL
* [MTV] Improve mgid extraction by [Sipherdrakon](https://github.com/Sipherdrakon), [kikuyan](https://github.com/kikuyan)
* [nexx] Better error message for unsupported format
* [NovaEmbed] Fix extractor by [pukkandan](https://github.com/pukkandan), [std-move](https://github.com/std-move)
* [PatreonUser] Do not capture RSS URLs
* [Reddit] Add support for 1080p videos by [xenova](https://github.com/xenova)
* [RoosterTeethSeries] Fix for multiple pages by [MinePlayersPE](https://github.com/MinePlayersPE)
* [sbs] Fix for movies and livestreams
* [Senate.gov] Add SenateGovIE and fix SenateISVPIE by [Grabien](https://github.com/Grabien), [pukkandan](https://github.com/pukkandan)
* [soundcloud:search] Fix pagination
* [tiktok:user] Set `webpage_url` correctly
* [Tokentube] Fix description by [u-spec-png](https://github.com/u-spec-png)
* [trovo] Fix extractor by [nyuszika7h](https://github.com/nyuszika7h)
* [tv2] Expand valid URL
* [Tvplayhome] Fix extractor by [pukkandan](https://github.com/pukkandan), [18928172992817182](https://github.com/18928172992817182)
* [Twitch:vod] Add chapters by [mpeter50](https://github.com/mpeter50)
* [twitch:vod] Extract live status by [DEvmIb](https://github.com/DEvmIb)
* [VidLii] Add 720p support by [mrpapersonic](https://github.com/mrpapersonic)
* [vimeo] Add fallback for config URL
* [vimeo] Sort http formats higher
* [WDR] Expand valid URL
* [willow] Add extractor by [aarubui](https://github.com/aarubui)
* [xvideos] Detect embed URLs by [4a1e2y5](https://github.com/4a1e2y5)
* [xvideos] Fix extractor by [Yakabuff](https://github.com/Yakabuff)
* [youtube, cleanup] Reorganize Tab and Search extractor inheritances
* [youtube:search_url] Add playlist/channel support
* [youtube] Add `default` player client by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Add storyboard formats
* [youtube] Decrypt n-sig for URLs with `ratebypass`
* [youtube] Minor improvement to format sorting
* [cleanup] Add deprecation warnings
* [cleanup] Refactor `JSInterpreter._seperate`
* [Cleanup] Remove some unnecessary groups in regexes by [Ashish0804](https://github.com/Ashish0804)
* [cleanup] Misc cleanup


### 2021.11.10.1

* Temporarily disable MacOS Build

### 2021.11.10

* [youtube] **Fix throttling by decrypting n-sig**
* Merging extractors from [haruhi-dl](https://git.sakamoto.pl/laudom/haruhi-dl) by [selfisekai](https://github.com/selfisekai)
    * [extractor] Add `_search_nextjs_data`
    * [tvp] Fix extractors
    * [tvp] Add TVPStreamIE
    * [wppilot] Add extractors
    * [polskieradio] Add extractors
    * [radiokapital] Add extractors
    * [polsatgo] Add extractor by [selfisekai](https://github.com/selfisekai), [sdomi](https://github.com/sdomi)
* Separate `--check-all-formats` from `--check-formats`
* Approximate filesize from bitrate
* Don't create console in `windows_enable_vt_mode`
* Fix bug in `--load-infojson` of playlists
* [minicurses] Add colors to `-F` and standardize color-printing code
* [outtmpl] Add type `link` for internet shortcut files
* [outtmpl] Add alternate forms for `q` and `j`
* [outtmpl] Do not traverse `None`
* [fragment] Fix progress display in fragmented downloads
* [downloader/ffmpeg] Fix vtt download with ffmpeg
* [ffmpeg] Detect presence of setts and libavformat version
* [ExtractAudio] Rescale `--audio-quality` correctly by [CrypticSignal](https://github.com/CrypticSignal), [pukkandan](https://github.com/pukkandan)
* [ExtractAudio] Use `libfdk_aac` if available by [CrypticSignal](https://github.com/CrypticSignal)
* [FormatSort] `eac3` is better than `ac3`
* [FormatSort] Fix some fields' defaults
* [generic] Detect more json_ld
* [generic] parse jwplayer with only the json URL
* [extractor] Add keyword automatically to SearchIE descriptions
* [extractor] Fix some errors being converted to `ExtractorError`
* [utils] Add `join_nonempty`
* [utils] Add `jwt_decode_hs256` by [Ashish0804](https://github.com/Ashish0804)
* [utils] Create `DownloadCancelled` exception
* [utils] Parse `vp09` as vp9
* [utils] Sanitize URL when determining protocol
* [test/download] Fallback test to `bv`
* [docs] Minor documentation improvements
* [cleanup] Improvements to error and debug messages
* [cleanup] Minor fixes and cleanup
* [3speak] Add extractors by [Ashish0804](https://github.com/Ashish0804)
* [AmazonStore] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [Gab] Add extractor by [u-spec-png](https://github.com/u-spec-png)
* [mediaset] Add playlist support by [nixxo](https://github.com/nixxo)
* [MLSScoccer] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [N1] Add support for nova.rs by [u-spec-png](https://github.com/u-spec-png)
* [PlanetMarathi] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [RaiplayRadio] Add extractors by [frafra](https://github.com/frafra)
* [roosterteeth] Add series extractor
* [sky] Add `SkyNewsStoryIE` by [ajj8](https://github.com/ajj8)
* [youtube] Fix sorting for some videos
* [youtube] Populate `thumbnail` with the best "known" thumbnail
* [youtube] Refactor itag processing
* [youtube] Remove unnecessary no-playlist warning
* [youtube:tab] Add Invidious list for playlists/channels by [rhendric](https://github.com/rhendric)
* [Bilibili:comments] Fix infinite loop by [u-spec-png](https://github.com/u-spec-png)
* [ceskatelevize] Fix extractor by [flashdagger](https://github.com/flashdagger)
* [Coub] Fix media format identification by [wlritchi](https://github.com/wlritchi)
* [crunchyroll] Add extractor-args `language` and `hardsub`
* [DiscoveryPlus] Allow language codes in URL
* [imdb] Fix thumbnail by [ozburo](https://github.com/ozburo)
* [instagram] Add IOS URL support by [u-spec-png](https://github.com/u-spec-png)
* [instagram] Improve login code by [u-spec-png](https://github.com/u-spec-png)
* [Instagram] Improve metadata extraction by [u-spec-png](https://github.com/u-spec-png)
* [iPrima] Fix extractor by [stanoarn](https://github.com/stanoarn)
* [itv] Add support for ITV News by [ajj8](https://github.com/ajj8)
* [la7] Fix extractor by [nixxo](https://github.com/nixxo)
* [linkedin] Don't login multiple times
* [mtv] Fix some videos by [Sipherdrakon](https://github.com/Sipherdrakon)
* [Newgrounds] Fix description by [u-spec-png](https://github.com/u-spec-png)
* [Nrk] Minor fixes by [fractalf](https://github.com/fractalf)
* [Olympics] Fix extractor by [u-spec-png](https://github.com/u-spec-png)
* [piksel] Fix sorting
* [twitter] Do not sort by codec
* [viewlift] Add cookie-based login and series support by [Ashish0804](https://github.com/Ashish0804), [pukkandan](https://github.com/pukkandan)
* [vimeo] Detect source extension and misc cleanup by [flashdagger](https://github.com/flashdagger)
* [vimeo] Fix ondemand videos and direct URLs with hash
* [vk] Fix login and add subtitles by [kaz-us](https://github.com/kaz-us)
* [VLive] Add upload_date and thumbnail by [Ashish0804](https://github.com/Ashish0804)
* [VRT] Fix login by [pgaig](https://github.com/pgaig)
* [Vupload] Fix extractor by [u-spec-png](https://github.com/u-spec-png)
* [wakanim] Add support for MPD manifests by [nyuszika7h](https://github.com/nyuszika7h)
* [wakanim] Detect geo-restriction by [nyuszika7h](https://github.com/nyuszika7h)
* [ZenYandex] Fix extractor by [u-spec-png](https://github.com/u-spec-png)


### 2021.10.22

* [build] Improvements
    * Build standalone MacOS packages by [smplayer-dev](https://github.com/smplayer-dev)
    * Release windows exe built with `py2exe`
    * Enable lazy-extractors in releases
        * Set env var `YTDLP_NO_LAZY_EXTRACTORS` to forcefully disable this (experimental)
    * Clean up error reporting in update
    * Refactor `pyinst.py`, misc cleanup and improve docs
* [docs] Migrate issues to use forms by [Ashish0804](https://github.com/Ashish0804)
* [downloader] **Fix slow progress hooks**
    * This was causing HLS/DASH downloads to be extremely slow in some situations
* [downloader/ffmpeg] Improve simultaneous download and merge
* [EmbedMetadata] Allow overwriting all default metadata with `meta_default` key
* [ModifyChapters] Add ability for `--remove-chapters` to remove sections by timestamp
* [utils] Allow duration strings in `--match-filter`
* Add HDR information to formats
* Add negative option `--no-batch-file` by [Zirro](https://github.com/Zirro)
* Calculate more fields for merged formats
* Do not verify thumbnail URLs unless `--check-formats` is specified
* Don't create console for subprocesses on Windows
* Fix `--restrict-filename` when used with default template
* Fix `check_formats` output being written to stdout when `-qv`
* Fix bug in storyboards
* Fix conflict b/w id and ext in format selection
* Fix verbose head not showing custom configs
* Load archive only after printing verbose head
* Make `duration_string` and `resolution` available in --match-filter
* Re-implement deprecated option `--id`
* Reduce default `--socket-timeout`
* Write verbose header to logger
* [outtmpl] Fix bug in expanding environment variables
* [cookies] Local State should be opened as utf-8
* [extractor,utils] Detect more codecs/mimetypes
* [extractor] Detect `EXT-X-KEY` Apple FairPlay
* [utils] Use `importlib` to load plugins by [sulyi](https://github.com/sulyi)
* [http] Retry on socket timeout and show the last encountered error
* [fragment] Print error message when skipping fragment
* [aria2c] Fix `--skip-unavailable-fragment`
* [SponsorBlock] Obey `extractor-retries` and `sleep-requests`
* [Merger] Do not add `aac_adtstoasc` to non-hls audio
* [ModifyChapters] Do not mutate original chapters by [nihil-admirari](https://github.com/nihil-admirari)
* [devscripts/run_tests] Use markers to filter tests by [sulyi](https://github.com/sulyi)
* [7plus] Add cookie based authentication by [nyuszika7h](https://github.com/nyuszika7h)
* [AdobePass] Fix RCN MSO by [jfogelman](https://github.com/jfogelman)
* [CBC] Fix Gem livestream by [makeworld-the-better-one](https://github.com/makeworld-the-better-one)
* [CBC] Support CBC Gem member content by [makeworld-the-better-one](https://github.com/makeworld-the-better-one)
* [crunchyroll] Add season to flat-playlist
* [crunchyroll] Add support for `beta.crunchyroll` URLs and fix series URLs with language code
* [EUScreen] Add Extractor by [Ashish0804](https://github.com/Ashish0804)
* [Gronkh] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [hidive] Fix typo
* [Hotstar] Mention Dynamic Range in `format_id` by [Ashish0804](https://github.com/Ashish0804)
* [Hotstar] Raise appropriate error for DRM
* [instagram] Add login by [u-spec-png](https://github.com/u-spec-png)
* [instagram] Show appropriate error when login is needed
* [microsoftstream] Add extractor by [damianoamatruda](https://github.com/damianoamatruda), [nixklai](https://github.com/nixklai)
* [on24] Add extractor by [damianoamatruda](https://github.com/damianoamatruda)
* [patreon] Fix vimeo player regex by [zenerdi0de](https://github.com/zenerdi0de)
* [SkyNewsAU] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [tagesschau] Fix extractor by [u-spec-png](https://github.com/u-spec-png)
* [tbs] Add tbs live streams by [llacb47](https://github.com/llacb47)
* [tiktok] Fix typo and update tests
* [trovo] Support channel clips and VODs by [Ashish0804](https://github.com/Ashish0804)
* [Viafree] Add support for Finland by [18928172992817182](https://github.com/18928172992817182)
* [vimeo] Fix embedded `player.vimeo`
* [vlive:channel] Fix extraction by [kikuyan](https://github.com/kikuyan), [pukkandan](https://github.com/pukkandan)
* [youtube] Add auto-translated subtitles
* [youtube] Expose different formats with same itag
* [youtube:comments] Fix for new layout by [coletdjnz](https://github.com/coletdjnz)
* [cleanup] Cleanup bilibili code by [pukkandan](https://github.com/pukkandan), [u-spec-png](https://github.com/u-spec-png)
* [cleanup] Remove broken youtube login code
* [cleanup] Standardize timestamp formatting code
* [cleanup] Generalize `getcomments` implementation for extractors
* [cleanup] Simplify search extractors code
* [cleanup] misc


### 2021.10.10

* [downloader/ffmpeg] Fix bug in initializing `FFmpegPostProcessor`
* [minicurses] Fix when printing to file
* [downloader] Fix throttledratelimit
* [francetv] Fix extractor by [fstirlitz](https://github.com/fstirlitz), [sarnoud](https://github.com/sarnoud)
* [NovaPlay] Add extractor by [Bojidarist](https://github.com/Bojidarist)
* [ffmpeg] Revert "Set max probesize" - No longer needed
* [docs] Remove incorrect dependency on VC++10
* [build] Allow to release without changelog

### 2021.10.09

* Improved progress reporting
    * Separate `--console-title` and `--no-progress`
    * Add option `--progress` to show progress-bar even in quiet mode
    * Fix and refactor `minicurses` and use it for all progress reporting
    * Standardize use of terminal sequences and enable color support for windows 10
    * Add option `--progress-template` to customize progress-bar and console-title
    * Add postprocessor hooks and progress reporting
* [postprocessor] Add plugin support with option `--use-postprocessor`
* [extractor] Extract storyboards from SMIL manifests by [fstirlitz](https://github.com/fstirlitz)
* [outtmpl] Alternate form of format type `l` for `\n` delimited list
* [outtmpl] Format type `U` for unicode normalization
* [outtmpl] Allow empty output template to skip a type of file
* Merge webm formats into mkv if thumbnails are to be embedded
* [adobepass] Add RCN as MSO by [jfogelman](https://github.com/jfogelman)
* [ciscowebex] Add extractor by [damianoamatruda](https://github.com/damianoamatruda)
* [Gettr] Add extractor by [i6t](https://github.com/i6t)
* [GoPro] Add extractor by [i6t](https://github.com/i6t)
* [N1] Add extractor by [u-spec-png](https://github.com/u-spec-png)
* [Theta] Add video extractor by [alerikaisattera](https://github.com/alerikaisattera)
* [Veo] Add extractor by [i6t](https://github.com/i6t)
* [Vupload] Add extractor by [u-spec-png](https://github.com/u-spec-png)
* [bbc] Extract better quality videos by [ajj8](https://github.com/ajj8)
* [Bilibili] Add subtitle converter by [u-spec-png](https://github.com/u-spec-png)
* [CBC] Cleanup tests by [makeworld-the-better-one](https://github.com/makeworld-the-better-one)
* [Douyin] Rewrite extractor by [MinePlayersPE](https://github.com/MinePlayersPE)
* [Funimation] Fix for /v/ urls by [pukkandan](https://github.com/pukkandan), [Jules-A](https://github.com/Jules-A)
* [Funimation] Sort formats according to the relevant extractor-args
* [Hidive] Fix duplicate and incorrect formats
* [HotStarSeries] Fix cookies by [Ashish0804](https://github.com/Ashish0804)
* [LinkedInLearning] Add subtitles by [Ashish0804](https://github.com/Ashish0804)
* [Mediaite] Relax valid url by [coletdjnz](https://github.com/coletdjnz)
* [Newgrounds] Add age_limit and fix duration by [u-spec-png](https://github.com/u-spec-png)
* [Newgrounds] Fix view count on songs by [u-spec-png](https://github.com/u-spec-png)
* [parliamentlive.tv] Fix extractor by [u-spec-png](https://github.com/u-spec-png)
* [PolskieRadio] Fix extractors by [jakubadamw](https://github.com/jakubadamw), [u-spec-png](https://github.com/u-spec-png)
* [reddit] Add embedded url by [u-spec-png](https://github.com/u-spec-png)
* [reddit] Fix 429 by generating a random `reddit_session` by [AjaxGb](https://github.com/AjaxGb)
* [Rumble] Add RumbleChannelIE by [Ashish0804](https://github.com/Ashish0804)
* [soundcloud:playlist] Detect last page correctly
* [SovietsCloset] Add duration from m3u8 by [ChillingPepper](https://github.com/ChillingPepper)
* [Streamable] Add codecs by [u-spec-png](https://github.com/u-spec-png)
* [vidme] Remove extractor by [alerikaisattera](https://github.com/alerikaisattera)
* [youtube:tab] Fallback to API when webpage fails to download by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Fix non-fatal errors in fetching player
* Fix `--flat-playlist` when neither IE nor id is known
* Fix `-f mp4` behaving differently from youtube-dl
* Workaround for bug in `ssl.SSLContext.load_default_certs`
* [aes] Improve performance slightly by [sulyi](https://github.com/sulyi)
* [cookies] Fix keyring fallback by [mbway](https://github.com/mbway)
* [embedsubtitle] Fix error when duration is unknown
* [ffmpeg] Fix error when subtitle file is missing
* [ffmpeg] Set max probesize to workaround AAC HLS stream issues by [shirt](https://github.com/shirt-dev)
* [FixupM3u8] Remove redundant run if merged is needed
* [hls] Fix decryption issues by [shirt](https://github.com/shirt-dev), [pukkandan](https://github.com/pukkandan)
* [http] Respect user-provided chunk size over extractor's
* [utils] Let traverse_obj accept functions as keys
* [docs] Add note about our custom ffmpeg builds
* [docs] Write embedding and contributing documentation by [pukkandan](https://github.com/pukkandan), [timethrow](https://github.com/timethrow)
* [update] Check for new version even if not updateable
* [build] Add more files to the tarball
* [build] Allow building with py2exe (and misc fixes)
* [build] Use pycryptodomex by [shirt](https://github.com/shirt-dev), [pukkandan](https://github.com/pukkandan)
* [cleanup] Some minor refactoring, improve docs and misc cleanup


### 2021.09.25

* Add new option `--netrc-location`
* [outtmpl] Allow alternate fields using `,`
* [outtmpl] Add format type `B` to treat the value as bytes, e.g. to limit the filename to a certain number of bytes
* Separate the options `--ignore-errors` and `--no-abort-on-error`
* Basic framework for simultaneous download of multiple formats by [nao20010128nao](https://github.com/nao20010128nao)
* [17live] Add 17.live extractor by [nao20010128nao](https://github.com/nao20010128nao)
* [bilibili] Add BiliIntlIE and BiliIntlSeriesIE by [Ashish0804](https://github.com/Ashish0804)
* [CAM4] Add extractor by [alerikaisattera](https://github.com/alerikaisattera)
* [Chingari] Add extractors by [Ashish0804](https://github.com/Ashish0804)
* [CGTN] Add extractor by [chao813](https://github.com/chao813)
* [damtomo] Add extractor by [nao20010128nao](https://github.com/nao20010128nao)
* [gotostage] Add extractor by [poschi3](https://github.com/poschi3)
* [Koo] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [Mediaite] Add Extractor by [Ashish0804](https://github.com/Ashish0804)
* [Mediaklikk] Add Extractor by [tmarki](https://github.com/tmarki), [mrx23dot](https://github.com/mrx23dot), [coletdjnz](https://github.com/coletdjnz)
* [MuseScore] Add Extractor by [Ashish0804](https://github.com/Ashish0804)
* [Newgrounds] Add NewgroundsUserIE and improve extractor by [u-spec-png](https://github.com/u-spec-png)
* [nzherald] Add NZHeraldIE by [coletdjnz](https://github.com/coletdjnz)
* [Olympics] Add replay extractor by [Ashish0804](https://github.com/Ashish0804)
* [Peertube] Add channel and playlist extractors by [u-spec-png](https://github.com/u-spec-png)
* [radlive] Add extractor by [nyuszika7h](https://github.com/nyuszika7h)
* [SovietsCloset] Add extractor by [ChillingPepper](https://github.com/ChillingPepper)
* [Streamanity] Add Extractor by [alerikaisattera](https://github.com/alerikaisattera)
* [Theta] Add extractor by [alerikaisattera](https://github.com/alerikaisattera)
* [Yandex] Add ZenYandexIE and ZenYandexChannelIE by [Ashish0804](https://github.com/Ashish0804)
* [9Now] handle episodes of series by [dalanmiller](https://github.com/dalanmiller)
* [AnimalPlanet] Fix extractor by [Sipherdrakon](https://github.com/Sipherdrakon)
* [Arte] Improve description extraction by [renalid](https://github.com/renalid)
* [atv.at] Use jwt for API by [NeroBurner](https://github.com/NeroBurner)
* [brightcove] Extract subtitles from manifests
* [CBC] Fix CBC Gem extractors by [makeworld-the-better-one](https://github.com/makeworld-the-better-one)
* [cbs] Report appropriate error for DRM
* [comedycentral] Support `collection-playlist` by [nixxo](https://github.com/nixxo)
* [DIYNetwork] Support new format by [Sipherdrakon](https://github.com/Sipherdrakon)
* [downloader/niconico] Pass custom headers by [nao20010128nao](https://github.com/nao20010128nao)
* [dw] Fix extractor
* [Fancode] Fix live streams by [zenerdi0de](https://github.com/zenerdi0de)
* [funimation] Fix for locations outside US by [Jules-A](https://github.com/Jules-A), [pukkandan](https://github.com/pukkandan)
* [globo] Fix GloboIE by [Ashish0804](https://github.com/Ashish0804)
* [HiDive] Fix extractor by [Ashish0804](https://github.com/Ashish0804)
* [Hotstar] Add referer for subs by [Ashish0804](https://github.com/Ashish0804)
* [itv] Fix extractor, add subtitles and thumbnails by [coletdjnz](https://github.com/coletdjnz), [sleaux-meaux](https://github.com/sleaux-meaux), [Vangelis66](https://github.com/Vangelis66)
* [lbry] Show error message from API response
* [Mxplayer] Use mobile API by [Ashish0804](https://github.com/Ashish0804)
* [NDR] Rewrite NDRIE by [Ashish0804](https://github.com/Ashish0804)
* [Nuvid] Fix extractor by [u-spec-png](https://github.com/u-spec-png)
* [Oreilly] Handle new web url by [MKSherbini](https://github.com/MKSherbini)
* [pbs] Fix subtitle extraction by [coletdjnz](https://github.com/coletdjnz), [gesa](https://github.com/gesa), [raphaeldore](https://github.com/raphaeldore)
* [peertube] Update instances by [u-spec-png](https://github.com/u-spec-png)
* [plutotv] Fix extractor for URLs with `/en`
* [reddit] Workaround for 429 by redirecting to old.reddit.com
* [redtube] Fix exts
* [soundcloud] Make playlist extraction lazy
* [soundcloud] Retry playlist pages on `502` error and update `_CLIENT_ID`
* [southpark] Fix SouthParkDE by [coletdjnz](https://github.com/coletdjnz)
* [SovietsCloset] Fix playlists for games with only named categories by [ConquerorDopy](https://github.com/ConquerorDopy)
* [SpankBang] Fix uploader by [f4pp3rk1ng](https://github.com/f4pp3rk1ng), [coletdjnz](https://github.com/coletdjnz)
* [tiktok] Use API to fetch higher quality video by [MinePlayersPE](https://github.com/MinePlayersPE), [llacb47](https://github.com/llacb47)
* [TikTokUser] Fix extractor using mobile API by [MinePlayersPE](https://github.com/MinePlayersPE), [llacb47](https://github.com/llacb47)
* [videa] Fix some extraction errors by [nyuszika7h](https://github.com/nyuszika7h)
* [VrtNU] Handle login errors by [llacb47](https://github.com/llacb47)
* [vrv] Don't raise error when thumbnails are missing
* [youtube] Cleanup authentication code by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Fix `--mark-watched` with `--cookies-from-browser`
* [youtube] Improvements to JS player extraction and add extractor-args to skip it by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Retry on 'Unknown Error' by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Return full URL instead of just ID
* [youtube] Warn when trying to download clips
* [zdf] Improve format sorting
* [zype] Extract subtitles from the m3u8 manifest by [fstirlitz](https://github.com/fstirlitz)
* Allow `--force-write-archive` to work with `--flat-playlist`
* Download subtitles in order of `--sub-langs`
* Allow `0` in `--playlist-items`
* Handle more playlist errors with `-i`
* Fix `--no-get-comments`
* Fix `extra_info` being reused across runs
* Fix compat options `no-direct-merge` and `playlist-index`
* Dump files should obey `--trim-filename` by [sulyi](https://github.com/sulyi)
* [aes] Add `aes_gcm_decrypt_and_verify` by [sulyi](https://github.com/sulyi), [pukkandan](https://github.com/pukkandan)
* [aria2c] Fix IV for some AES-128 streams by [shirt](https://github.com/shirt-dev)
* [compat] Don't ignore `HOME` (if set) on windows
* [cookies] Make browser names case insensitive
* [cookies] Print warning for cookie decoding error only once
* [extractor] Fix root-relative URLs in MPD by [DigitalDJ](https://github.com/DigitalDJ)
* [ffmpeg] Add `aac_adtstoasc` when merging if needed
* [fragment,aria2c] Generalize and refactor some code
* [fragment] Avoid repeated request for AES key
* [fragment] Fix range header when using `-N` and media sequence by [shirt](https://github.com/shirt-dev)
* [hls,aes] Fallback to native implementation for AES-CBC and detect `Cryptodome` in addition to `Crypto`
* [hls] Byterange + AES128 is supported by native downloader
* [ModifyChapters] Improve sponsor chapter merge algorithm by [nihil-admirari](https://github.com/nihil-admirari)
* [ModifyChapters] Minor fixes
* [WebVTT] Adjust parser to accommodate PBS subtitles
* [utils] Improve `extract_timezone` by [dirkf](https://github.com/dirkf)
* [options] Fix `--no-config` and refactor reading of config files
* [options] Strip spaces and ignore empty entries in list-like switches
* [test/cookies] Improve logging
* [build] Automate more of the release process by [animelover1984](https://github.com/animelover1984), [pukkandan](https://github.com/pukkandan)
* [build] Fix sha256 by [nihil-admirari](https://github.com/nihil-admirari)
* [build] Bring back brew taps by [nao20010128nao](https://github.com/nao20010128nao)
* [build] Provide `--onedir` zip for windows
* [cleanup,docs] Add deprecation warning in docs for some counter intuitive behaviour
* [cleanup] Fix line endings for `nebula.py` by [glenn-slayden](https://github.com/glenn-slayden)
* [cleanup] Improve `make clean-test` by [sulyi](https://github.com/sulyi)
* [cleanup] Misc


### 2021.09.02

* **Native SponsorBlock** implementation by [nihil-admirari](https://github.com/nihil-admirari), [pukkandan](https://github.com/pukkandan)
    * `--sponsorblock-remove CATS` removes specified chapters from file
    * `--sponsorblock-mark CATS` marks the specified sponsor sections as chapters
    * `--sponsorblock-chapter-title TMPL` to specify sponsor chapter template
    * `--sponsorblock-api URL` to use a different API
    * No re-encoding is done unless `--force-keyframes-at-cuts` is used
    * The fetched sponsor sections are written to the infojson
    * Deprecates: `--sponskrub`, `--no-sponskrub`, `--sponskrub-cut`, `--no-sponskrub-cut`, `--sponskrub-force`, `--no-sponskrub-force`, `--sponskrub-location`, `--sponskrub-args`
* Split `--embed-chapters` from `--embed-metadata` (it still implies the former by default)
* Add option `--remove-chapters` to remove arbitrary chapters by [nihil-admirari](https://github.com/nihil-admirari), [pukkandan](https://github.com/pukkandan)
* Add option `--force-keyframes-at-cuts` for more accurate cuts when removing and splitting chapters by [nihil-admirari](https://github.com/nihil-admirari)
* Let `--match-filter` reject entries early
    * Makes redundant: `--match-title`, `--reject-title`, `--min-views`, `--max-views`
* [lazy_extractor] Improvements (It now passes all tests)
    * Bugfix for when plugin directory doesn't exist by [kidonng](https://github.com/kidonng)
    * Create instance only after pre-checking archive
    * Import actual class if an attribute is accessed
    * Fix `suitable` and add flake8 test
* [downloader/ffmpeg] Experimental support for DASH manifests (including live)
    * Your ffmpeg must have [this patch](https://github.com/FFmpeg/FFmpeg/commit/3249c757aed678780e22e99a1a49f4672851bca9) applied for YouTube DASH to work
* [downloader/ffmpeg] Allow passing custom arguments before `-i`
* [BannedVideo] Add extractor by [smege1001](https://github.com/smege1001), [blackjack4494](https://github.com/blackjack4494), [pukkandan](https://github.com/pukkandan)
* [bilibili] Add category extractor by [animelover1984](https://github.com/animelover1984)
* [Epicon] Add extractors by [Ashish0804](https://github.com/Ashish0804)
* [filmmodu] Add extractor by [mzbaulhaque](https://github.com/mzbaulhaque)
* [GabTV] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [Hungama] Fix `HungamaSongIE` and add `HungamaAlbumPlaylistIE` by [Ashish0804](https://github.com/Ashish0804)
* [ManotoTV] Add new extractors by [tandy1000](https://github.com/tandy1000)
* [Niconico] Add Search extractors by [animelover1984](https://github.com/animelover1984), [pukkandan](https://github.com/pukkandan)
* [Patreon] Add `PatreonUserIE` by [zenerdi0de](https://github.com/zenerdi0de)
* [peloton] Add extractor by [IONECarter](https://github.com/IONECarter), [capntrips](https://github.com/capntrips), [pukkandan](https://github.com/pukkandan)
* [ProjectVeritas] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [radiko] Add extractors by [nao20010128nao](https://github.com/nao20010128nao)
* [StarTV] Add extractor for `startv.com.tr` by [mrfade](https://github.com/mrfade), [coletdjnz](https://github.com/coletdjnz)
* [tiktok] Add `TikTokUserIE` by [Ashish0804](https://github.com/Ashish0804), [pukkandan](https://github.com/pukkandan)
* [Tokentube] Add extractor by [u-spec-png](https://github.com/u-spec-png)
* [TV2Hu] Fix `TV2HuIE` and add `TV2HuSeriesIE` by [Ashish0804](https://github.com/Ashish0804)
* [voicy] Add extractor by [nao20010128nao](https://github.com/nao20010128nao)
* [adobepass] Fix Verizon SAML login by [nyuszika7h](https://github.com/nyuszika7h), [ParadoxGBB](https://github.com/ParadoxGBB)
* [afreecatv] Fix adult VODs by [wlritchi](https://github.com/wlritchi)
* [afreecatv] Tolerate failure to parse date string by [wlritchi](https://github.com/wlritchi)
* [aljazeera] Fix extractor by [MinePlayersPE](https://github.com/MinePlayersPE)
* [ATV.at] Fix extractor for ATV.at by [NeroBurner](https://github.com/NeroBurner), [coletdjnz](https://github.com/coletdjnz)
* [bitchute] Fix test by [mahanstreamer](https://github.com/mahanstreamer)
* [camtube] Remove obsolete extractor by [alerikaisattera](https://github.com/alerikaisattera)
* [CDA] Add more formats by [u-spec-png](https://github.com/u-spec-png)
* [eroprofile] Fix page skipping in albums by [jhwgh1968](https://github.com/jhwgh1968)
* [facebook] Fix format sorting
* [facebook] Fix metadata extraction by [kikuyan](https://github.com/kikuyan)
* [facebook] Update onion URL by [Derkades](https://github.com/Derkades)
* [HearThisAtIE] Fix extractor by [Ashish0804](https://github.com/Ashish0804)
* [instagram] Add referrer to prevent throttling by [u-spec-png](https://github.com/u-spec-png), [kikuyan](https://github.com/kikuyan)
* [iwara.tv] Extract more metadata by [BunnyHelp](https://github.com/BunnyHelp)
* [iwara] Add thumbnail by [i6t](https://github.com/i6t)
* [kakao] Fix extractor
* [mediaset] Fix extraction for some videos by [nyuszika7h](https://github.com/nyuszika7h)
* [Motherless] Fix extractor by [coletdjnz](https://github.com/coletdjnz)
* [Nova] fix extractor by [std-move](https://github.com/std-move)
* [ParamountPlus] Fix geo verification by [shirt](https://github.com/shirt-dev)
* [peertube] handle new video URL format by [Chocobozzz](https://github.com/Chocobozzz)
* [pornhub] Separate and fix playlist extractor by [mzbaulhaque](https://github.com/mzbaulhaque)
* [reddit] Fix for quarantined subreddits by [ouwou](https://github.com/ouwou)
* [ShemarooMe] Fix extractor by [Ashish0804](https://github.com/Ashish0804)
* [soundcloud] Refetch `client_id` on 403
* [tiktok] Fix metadata extraction
* [TV2] Fix extractor by [Ashish0804](https://github.com/Ashish0804)
* [tv5mondeplus] Fix extractor by [korli](https://github.com/korli)
* [VH1,TVLand] Fix extractors by [Sipherdrakon](https://github.com/Sipherdrakon)
* [Viafree] Fix extractor and extract subtitles by [coletdjnz](https://github.com/coletdjnz)
* [XHamster] Extract `uploader_id` by [octotherp](https://github.com/octotherp)
* [youtube] Add `shorts` to `_VALID_URL`
* [youtube] Add av01 itags to known formats list by [blackjack4494](https://github.com/blackjack4494)
* [youtube] Extract error messages from HTTPError response by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Fix subtitle names
* [youtube] Prefer audio stream that YouTube considers default
* [youtube] Remove annotations and deprecate `--write-annotations` by [coletdjnz](https://github.com/coletdjnz)
* [Zee5] Fix extractor and add subtitles by [Ashish0804](https://github.com/Ashish0804)
* [aria2c] Obey `--rate-limit`
* [EmbedSubtitle] Continue even if some files are missing
* [extractor] Better error message for DRM
* [extractor] Common function `_match_valid_url`
* [extractor] Show video id in error messages if possible
* [FormatSort] Remove priority of `lang`
* [options] Add `_set_from_options_callback`
* [SubtitleConvertor] Fix bug during subtitle conversion
* [utils] Add `parse_qs`
* [webvtt] Fix timestamp overflow adjustment by [fstirlitz](https://github.com/fstirlitz)
* Bugfix for `--replace-in-metadata`
* Don't try to merge with final extension
* Fix `--force-overwrites` when using `-k`
* Fix `--no-prefer-free-formats` by [CeruleanSky](https://github.com/CeruleanSky)
* Fix `-F` for extractors that directly return url
* Fix `-J` when there are failed videos
* Fix `extra_info` being reused across runs
* Fix `playlist_index` not obeying `playlist_start` and add tests
* Fix resuming of single formats when using `--no-part`
* Revert erroneous use of the `Content-Length` header by [fstirlitz](https://github.com/fstirlitz)
* Use `os.replace` where applicable by; paulwrubel
* [build] Add homebrew taps `yt-dlp/taps/yt-dlp` by [nao20010128nao](https://github.com/nao20010128nao)
* [build] Fix bug in making `yt-dlp.tar.gz`
* [docs] Fix some typos by [pukkandan](https://github.com/pukkandan), [zootedb0t](https://github.com/zootedb0t)
* [cleanup] Replace improper use of tab in trovo by [glenn-slayden](https://github.com/glenn-slayden)


### 2021.08.10

* Add option `--replace-in-metadata`
* Add option `--no-simulate` to not simulate even when `--print` or `--list...` are used - Deprecates `--print-json`
* Allow entire infodict to be printed using `%()s` - makes `--dump-json` redundant
* Allow multiple `--exec` and `--exec-before-download`
* Add regex to `--match-filter`
* Add all format filtering operators also to `--match-filter` by [max-te](https://github.com/max-te)
* Add compat-option `no-keep-subs`
* [adobepass] Add MSO Cablevision by [Jessecar96](https://github.com/Jessecar96)
* [BandCamp] Add BandcampMusicIE by [Ashish0804](https://github.com/Ashish0804)
* [blackboardcollaborate] Add new extractor by [mzbaulhaque](https://github.com/mzbaulhaque)
* [eroprofile] Add album downloader by [jhwgh1968](https://github.com/jhwgh1968)
* [mirrativ] Add extractors by [nao20010128nao](https://github.com/nao20010128nao)
* [openrec] Add extractors by [nao20010128nao](https://github.com/nao20010128nao)
* [nbcolympics:stream] Fix extractor by [nchilada](https://github.com/nchilada), [pukkandan](https://github.com/pukkandan)
* [nbcolympics] Update extractor for 2020 olympics by [wesnm](https://github.com/wesnm)
* [paramountplus] Separate extractor and fix some titles by [shirt](https://github.com/shirt-dev), [pukkandan](https://github.com/pukkandan)
* [RCTIPlus] Support events and TV by [MinePlayersPE](https://github.com/MinePlayersPE)
* [Newgrounds] Improve extractor and fix playlist by [u-spec-png](https://github.com/u-spec-png)
* [aenetworks] Update `_THEPLATFORM_KEY` and `_THEPLATFORM_SECRET` by [wesnm](https://github.com/wesnm)
* [crunchyroll] Fix thumbnail by [funniray](https://github.com/funniray)
* [HotStar] Use API for metadata and extract subtitles by [Ashish0804](https://github.com/Ashish0804)
* [instagram] Fix comments extraction by [u-spec-png](https://github.com/u-spec-png)
* [peertube] Fix videos without description by [u-spec-png](https://github.com/u-spec-png)
* [twitch:clips] Extract `display_id` by [dirkf](https://github.com/dirkf)
* [viki] Print error message from API request
* [Vine] Remove invalid formats by [u-spec-png](https://github.com/u-spec-png)
* [VrtNU] Fix XSRF token by [pgaig](https://github.com/pgaig)
* [vrv] Fix thumbnail extraction by [funniray](https://github.com/funniray)
* [youtube] Add extractor-arg `include-live-dash` to show live dash formats
* [youtube] Improve signature function detection by [PSlava](https://github.com/PSlava)
* [youtube] Raise appropriate error when API pages can't be downloaded
* Ensure `_write_ytdl_file` closes file handle on error
* Fix `--compat-options filename` by [stdedos](https://github.com/stdedos)
* Fix issues with infodict sanitization
* Fix resuming when using `--no-part`
* Fix wrong extension for intermediate files
* Handle `BrokenPipeError` by [kikuyan](https://github.com/kikuyan)
* Show libraries present in verbose head
* [extractor] Detect `sttp` as subtitles in MPD by [fstirlitz](https://github.com/fstirlitz)
* [extractor] Reset non-repeating warnings per video
* [ffmpeg] Fix streaming `mp4` to `stdout`
* [ffpmeg] Allow `--ffmpeg-location` to be a file with different name
* [utils] Fix `InAdvancePagedList.__getitem__`
* [utils] Fix `traverse_obj` depth when `is_user_input`
* [webvtt] Merge daisy-chained duplicate cues by [fstirlitz](https://github.com/fstirlitz)
* [build] Use custom build of `pyinstaller` by [shirt](https://github.com/shirt-dev)
* [tests:download] Add batch testing for extractors (`test_YourExtractor_all`)
* [docs] Document which fields `--add-metadata` adds to the file
* [docs] Fix some mistakes and improve doc
* [cleanup] Misc code cleanup


### 2021.08.02

* Add logo, banner and donate links
* [outtmpl] Expand and escape environment variables
* [outtmpl] Add format types `j` (json), `l` (comma delimited list), `q` (quoted for terminal)
* [downloader] Allow streaming some unmerged formats to stdout using ffmpeg
* [youtube] **Age-gate bypass**
    * Add `agegate` clients by [pukkandan](https://github.com/pukkandan), [MinePlayersPE](https://github.com/MinePlayersPE)
    * Add `thirdParty` to agegate clients to bypass more videos
    * Simplify client definitions, expose `embedded` clients
    * Improve age-gate detection by [coletdjnz](https://github.com/coletdjnz)
    * Fix default global API key by [coletdjnz](https://github.com/coletdjnz)
    * Add `creator` clients for age-gate bypass using unverified accounts by [zerodytrash](https://github.com/zerodytrash), [coletdjnz](https://github.com/coletdjnz), [pukkandan](https://github.com/pukkandan)
* [adobepass] Add MSO Sling TV by [wesnm](https://github.com/wesnm)
* [CBS] Add ParamountPlusSeriesIE by [Ashish0804](https://github.com/Ashish0804)
* [dplay] Add `ScienceChannelIE` by [Sipherdrakon](https://github.com/Sipherdrakon)
* [UtreonIE] Add extractor by [Ashish0804](https://github.com/Ashish0804)
* [youtube] Add `mweb` client by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Add `player_client=all`
* [youtube] Force `hl=en` for comments by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Fix format sorting when using alternate clients
* [youtube] Misc cleanup by [pukkandan](https://github.com/pukkandan), [coletdjnz](https://github.com/coletdjnz)
* [youtube] Extract SAPISID only once
* [CBS] Add fallback by [llacb47](https://github.com/llacb47), [pukkandan](https://github.com/pukkandan)
* [Hotstar] Support cookies by [Ashish0804](https://github.com/Ashish0804)
* [HotStarSeriesIE] Fix regex by [Ashish0804](https://github.com/Ashish0804)
* [bilibili] Improve `_VALID_URL`
* [mediaset] Fix extraction by [nixxo](https://github.com/nixxo)
* [Mxplayer] Add h265 formats by [Ashish0804](https://github.com/Ashish0804)
* [RCTIPlus] Remove PhantomJS dependency by [MinePlayersPE](https://github.com/MinePlayersPE)
* [tenplay] Add MA15+ age limit by [pento](https://github.com/pento)
* [vidio] Fix login error detection by [MinePlayersPE](https://github.com/MinePlayersPE)
* [vimeo] Better extraction of original file by [Ashish0804](https://github.com/Ashish0804)
* [generic] Support KVS player (replaces ThisVidIE) by [rigstot](https://github.com/rigstot)
* Add compat-option `no-clean-infojson`
* Remove `asr` appearing twice in `-F`
* Set `home:` as the default key for `-P`
* [utils] Fix slicing of reversed `LazyList`
* [FormatSort] Fix bug for audio with unknown codec
* [test:download] Support testing with `ignore_no_formats_error`
* [cleanup] Refactor some code


### 2021.07.24

* [youtube:tab] Extract video duration early
* [downloader] Pass `info_dict` to `progress_hook`s
* [youtube] Fix age-gated videos for API clients when cookies are supplied by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Disable `get_video_info` age-gate workaround - This endpoint seems to be completely dead
* [youtube] Try all clients even if age-gated
* [youtube] Fix subtitles only being extracted from the first client
* [youtube] Simplify `_get_text`
* [cookies] bugfix for microsoft edge on macOS
* [cookies] Handle `sqlite` `ImportError` gracefully by [mbway](https://github.com/mbway)
* [cookies] Handle errors when importing `keyring`

### 2021.07.21

* **Add option `--cookies-from-browser`** to load cookies from a browser by [mbway](https://github.com/mbway)
    * Usage: `--cookies-from-browser BROWSER[:PROFILE_NAME_OR_PATH]`
    * Also added `--no-cookies-from-browser`
    * To decrypt chromium cookies, `keyring` is needed for UNIX and `pycryptodome` for Windows
* Add option `--exec-before-download`
* Add field `live_status`
* [FFmpegMetadata] Add language of each stream and some refactoring
* [douyin] Add extractor by [pukkandan](https://github.com/pukkandan), [pyx](https://github.com/pyx)
* [pornflip] Add extractor by [mzbaulhaque](https://github.com/mzbaulhaque)
* **[youtube] Extract data from multiple clients** by [pukkandan](https://github.com/pukkandan), [coletdjnz](https://github.com/coletdjnz)
    * `player_client` now accepts multiple clients
    * Default `player_client` = `android,web`
        * This uses twice as many requests, but avoids throttling for most videos while also not losing any formats
    * Music clients can be specifically requested and is enabled by default if `music.youtube.com`
    * Added `player_client=ios` (Known issue: formats from ios are not sorted correctly)
    * Add age-gate bypass for android and ios clients
* [youtube] Extract more thumbnails
    * The thumbnail URLs are hard-coded and their actual existence is tested lazily
    * Added option `--no-check-formats` to not test them
* [youtube] Misc fixes
    * Improve extraction of livestream metadata by [pukkandan](https://github.com/pukkandan), [krichbanana](https://github.com/krichbanana)
    * Hide live dash formats since they can't be downloaded anyway
    * Fix authentication when using multiple accounts by [coletdjnz](https://github.com/coletdjnz)
    * Fix controversial videos when requested via API by [coletdjnz](https://github.com/coletdjnz)
    * Fix session index extraction and headers for non-web player clients by [coletdjnz](https://github.com/coletdjnz)
    * Make `--extractor-retries` work for more errors
    * Fix sorting of 3gp format
    * Sanity check `chapters` (and refactor related code)
    * Make `parse_time_text` and `_extract_chapters` non-fatal
    * Misc cleanup and bug fixes by [coletdjnz](https://github.com/coletdjnz)
* [youtube:tab] Fix channels tab
* [youtube:tab] Extract playlist availability by [coletdjnz](https://github.com/coletdjnz)
* **[youtube:comments] Move comment extraction to new API** by [coletdjnz](https://github.com/coletdjnz)
    * Adds extractor-args `comment_sort` (`top`/`new`), `max_comments`, `max_comment_depth`
* [youtube:comments] Fix `is_favorited`, improve `like_count` parsing by [coletdjnz](https://github.com/coletdjnz)
* [BravoTV] Improve metadata extraction by [kevinoconnor7](https://github.com/kevinoconnor7)
* [crunchyroll:playlist] Force http
* [yahoo:gyao:player] Relax `_VALID_URL` by [nao20010128nao](https://github.com/nao20010128nao)
* [nebula] Authentication via tokens from cookie jar by [hheimbuerger](https://github.com/hheimbuerger), [TpmKranz](https://github.com/TpmKranz)
* [RTP] Fix extraction and add subtitles by [fstirlitz](https://github.com/fstirlitz)
* [viki] Rewrite extractors and add extractor-arg `video_types` to `vikichannel` by [zackmark29](https://github.com/zackmark29), [pukkandan](https://github.com/pukkandan)
* [vlive] Extract thumbnail directly in addition to the one from Naver
* [generic] Extract previously missed subtitles by [fstirlitz](https://github.com/fstirlitz)
* [generic] Extract everything in the SMIL manifest and detect discarded subtitles by [fstirlitz](https://github.com/fstirlitz)
* [embedthumbnail] Fix `_get_thumbnail_resolution`
* [metadatafromfield] Do not detect numbers as field names
* Fix selectors `all`, `mergeall` and add tests
* Errors in playlist extraction should obey `--ignore-errors`
* Fix bug where `original_url` was not propagated when `_type`=`url`
* Revert "Merge webm formats into mkv if thumbnails are to be embedded (#173)"
    * This was wrongly checking for `write_thumbnail`
* Improve `extractor_args` parsing
* Rename `NOTE` in `-F` to `MORE INFO` since it's often confused to be the same as `format_note`
* Add `only_once` param for `write_debug` and `report_warning`
* [extractor] Allow extracting multiple groups in `_search_regex` by [fstirlitz](https://github.com/fstirlitz)
* [utils] Improve `traverse_obj`
* [utils] Add `variadic`
* [utils] Improve `js_to_json` comment regex by [fstirlitz](https://github.com/fstirlitz)
* [webtt] Fix timestamps
* [compat] Remove unnecessary code
* [docs] fix default of multistreams


### 2021.07.07

* Merge youtube-dl: Upto [commit/a803582](https://github.com/ytdl-org/youtube-dl/commit/a8035827177d6b59aca03bd717acb6a9bdd75ada)
* Add `--extractor-args` to pass some extractor-specific arguments. See [readme](https://github.com/yt-dlp/yt-dlp#extractor-arguments)
    * Add extractor option `skip` for `youtube`, e.g. `--extractor-args youtube:skip=hls,dash`
    * Deprecates `--youtube-skip-dash-manifest`, `--youtube-skip-hls-manifest`, `--youtube-include-dash-manifest`, `--youtube-include-hls-manifest`
* Allow `--list...` options to work with `--print`, `--quiet` and other `--list...` options
* [youtube] Use `player` API for additional video extraction requests by [coletdjnz](https://github.com/coletdjnz)
    * **Fixes youtube premium music** (format 141) extraction
    * Adds extractor option `player_client` = `web`/`android`
        * **`--extractor-args youtube:player_client=android` works around the throttling** for the time-being
    * Adds extractor option `player_skip=config`
    * Adds age-gate fallback using embedded client
* [youtube] Choose correct Live chat API for upcoming streams by [krichbanana](https://github.com/krichbanana)
* [youtube] Fix subtitle names for age-gated videos
* [youtube:comments] Fix error handling and add `itct` to params by [coletdjnz](https://github.com/coletdjnz)
* [youtube_live_chat] Fix download with cookies by [siikamiika](https://github.com/siikamiika)
* [youtube_live_chat] use `clickTrackingParams` by [siikamiika](https://github.com/siikamiika)
* [Funimation] Rewrite extractor
    * Add `FunimationShowIE` by [Mevious](https://github.com/Mevious)
    * **Treat the different versions of an episode as different formats of a single video**
        * This changes the video `id` and will break break existing archives
        * Compat option `seperate-video-versions` to fall back to old behavior including using the old video ids
    * Support direct `/player/` URL
    * Extractor options `language` and `version` to pre-select them during extraction
        * These options may be removed in the future if we can extract all formats without additional network requests
        * Do not rely on these for format selection and use `-f` filters instead
* [AdobePass] Add Spectrum MSO by [kevinoconnor7](https://github.com/kevinoconnor7), [ohmybahgosh](https://github.com/ohmybahgosh)
* [facebook] Extract description and fix title
* [fancode] Fix extraction, support live and allow login with refresh token by [zenerdi0de](https://github.com/zenerdi0de)
* [plutotv] Improve `_VALID_URL`
* [RCTIPlus] Add extractor by [MinePlayersPE](https://github.com/MinePlayersPE)
* [Soundcloud] Allow login using oauth token by [blackjack4494](https://github.com/blackjack4494)
* [TBS] Support livestreams by [llacb47](https://github.com/llacb47)
* [videa] Fix extraction by [nyuszika7h](https://github.com/nyuszika7h)
* [yahoo] Fix extraction by [llacb47](https://github.com/llacb47), [pukkandan](https://github.com/pukkandan)
* Process videos when using `--ignore-no-formats-error` by [krichbanana](https://github.com/krichbanana)
* Fix `--throttled-rate` when using `--load-info-json`
* Fix `--flat-playlist` when entry has no `ie_key`
* Fix `check_formats` catching `ExtractorError` instead of `DownloadError`
* Fix deprecated option `--list-formats-old`
* [downloader/ffmpeg] Fix `--ppa` when using simultaneous download
* [extractor] Prevent unnecessary download of hls manifests and refactor `hls_split_discontinuity`
* [fragment] Handle status of download and errors in threads correctly; and minor refactoring
* [thumbnailsconvertor] Treat `jpeg` as `jpg`
* [utils] Fix issues with `LazyList` reversal
* [extractor] Allow extractors to set their own login hint
* [cleanup] Simplify format selector code with `LazyList` and `yield from`
* [cleanup] Clean `extractor.common._merge_subtitles` signature
* [cleanup] Fix some typos


### 2021.06.23

* Merge youtube-dl: Upto [commit/379f52a](https://github.com/ytdl-org/youtube-dl/commit/379f52a4954013767219d25099cce9e0f9401961)
* **Add option `--throttled-rate`** below which video data is re-extracted
* [fragment] **Merge during download for `-N`**, and refactor `hls`/`dash`
* [websockets] Add `WebSocketFragmentFD` by [nao20010128nao](https://github.com/nao20010128nao), [pukkandan](https://github.com/pukkandan)
* Allow `images` formats in addition to video/audio
* [downloader/mhtml] Add new downloader for slideshows/storyboards by [fstirlitz](https://github.com/fstirlitz)
* [youtube] Temporary **fix for age-gate**
* [youtube] Support ongoing live chat by [siikamiika](https://github.com/siikamiika)
* [youtube] Improve SAPISID cookie handling by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Login is not needed for `:ytrec`
* [youtube] Non-fatal alert reporting for unavailable videos page by [coletdjnz](https://github.com/coletdjnz)
* [twitcasting] Websocket support by [nao20010128nao](https://github.com/nao20010128nao)
* [mediasite] Extract slides by [fstirlitz](https://github.com/fstirlitz)
* [funimation] Extract subtitles
* [pornhub] Extract `cast`
* [hotstar] Use server time for authentication instead of local time
* [EmbedThumbnail] Fix for already downloaded thumbnail
* [EmbedThumbnail] Add compat-option `embed-thumbnail-atomicparsley`
* Expand `--check-formats` to thumbnails
* Fix id sanitization in filenames
* Skip fixup of existing files and add `--fixup force` to force it
* Better error handling of syntax errors in `-f`
* Use `NamedTemporaryFile` for `--check-formats`
* [aria2c] Lower `--min-split-size` for HTTP downloads
* [options] Rename `--add-metadata` to `--embed-metadata`
* [utils] Improve `LazyList` and add tests
* [build] Build Windows x86 version with py3.7 and remove redundant tests by [pukkandan](https://github.com/pukkandan), [shirt](https://github.com/shirt-dev)
* [docs] Clarify that `--embed-metadata` embeds chapter markers
* [cleanup] Refactor fixup


### 2021.06.09

* Fix bug where `%(field)d` in filename template throws error
* [outtmpl] Improve offset parsing
* [test] More rigorous tests for `prepare_filename`

### 2021.06.08

* Remove support for obsolete Python versions: Only 3.6+ is now supported
* Merge youtube-dl: Upto [commit/c2350ca](https://github.com/ytdl-org/youtube-dl/commit/c2350cac243ba1ec1586fe85b0d62d1b700047a2)
* [hls] Fix decryption for multithreaded downloader
* [extractor] Fix pre-checking archive for some extractors
* [extractor] Fix FourCC fallback when parsing ISM by [fstirlitz](https://github.com/fstirlitz)
* [twitcasting] Add TwitCastingUserIE, TwitCastingLiveIE by [pukkandan](https://github.com/pukkandan), [nao20010128nao](https://github.com/nao20010128nao)
* [vidio] Add VidioPremierIE and VidioLiveIE by [MinePlayersPE](Https://github.com/MinePlayersPE)
* [viki] Fix extraction from [ytdl-org/youtube-dl@59e583f](https://github.com/ytdl-org/youtube-dl/commit/59e583f7e8530ca92776c866897d895c072e2a82)
* [youtube] Support shorts URL
* [zoom] Extract transcripts as subtitles
* Add field `original_url` with the user-inputted URL
* Fix and refactor `prepare_outtmpl`
* Make more fields available for `--print` when used with `--flat-playlist`
* [utils] Generalize `traverse_dict` to `traverse_obj`
* [downloader/ffmpeg] Hide FFmpeg banner unless in verbose mode by [fstirlitz](https://github.com/fstirlitz)
* [build] Release `yt-dlp.tar.gz`
* [build,update] Add GNU-style SHA512 and prepare updater for similar SHA256 by [nihil-admirari](https://github.com/nihil-admirari)
* [pyinst] Show Python version in exe metadata by [nihil-admirari](https://github.com/nihil-admirari)
* [docs] Improve documentation of dependencies
* [cleanup] Mark unused files
* [cleanup] Point all shebang to `python3` by [fstirlitz](https://github.com/fstirlitz)
* [cleanup] Remove duplicate file `trovolive.py`


### 2021.06.01

* Merge youtube-dl: Upto [commit/d495292](https://github.com/ytdl-org/youtube-dl/commit/d495292852b6c2f1bd58bc2141ff2b0265c952cf)
* Pre-check archive and filters during playlist extraction
* Handle Basic Auth `user:pass` in URLs by [hhirtz](https://github.com/hhirtz) and [pukkandan](https://github.com/pukkandan)
* [archiveorg] Add YoutubeWebArchiveIE by [coletdjnz](https://github.com/coletdjnz) and [alex-gedeon](https://github.com/alex-gedeon)
* [fancode] Add extractor by [rhsmachine](https://github.com/rhsmachine)
* [patreon] Support vimeo embeds by [rhsmachine](https://github.com/rhsmachine)
* [Saitosan] Add new extractor by [llacb47](https://github.com/llacb47)
* [ShemarooMe] Add extractor by [Ashish0804](https://github.com/Ashish0804) and [pukkandan](https://github.com/pukkandan)
* [telemundo] Add extractor by [king-millez](https://github.com/king-millez)
* [SonyLIV] Add SonyLIVSeriesIE and subtitle support by [Ashish0804](https://github.com/Ashish0804)
* [Hotstar] Add HotStarSeriesIE by [Ashish0804](https://github.com/Ashish0804)
* [Voot] Add VootSeriesIE by [Ashish0804](https://github.com/Ashish0804)
* [vidio] Support login and premium videos by [MinePlayersPE](https://github.com/MinePlayersPE)
* [fragment] When using `-N`, do not keep the fragment content in memory
* [ffmpeg] Download and merge in a single step if possible
* [ThumbnailsConvertor] Support conversion to `png` and make it the default by [louie-github](https://github.com/louie-github)
* [VideoConvertor] Generalize with remuxer and allow conditional recoding
* [EmbedThumbnail] Embed in `mp4`/`m4a` using mutagen by [tripulse](https://github.com/tripulse) and [pukkandan](https://github.com/pukkandan)
* [EmbedThumbnail] Embed if any thumbnail was downloaded, not just the best
* [EmbedThumbnail] Correctly escape filename
* [update] replace self without launching a subprocess in windows
* [update] Block further update for unsupported systems
* Refactor `__process_playlist` by creating `LazyList`
* Write messages to `stderr` when both `quiet` and `verbose`
* Sanitize and sort playlist thumbnails
* Remove `None` values from `info.json`
* [extractor] Always prefer native hls downloader by default
* [extractor] Skip subtitles without URI in m3u8 manifests by [hheimbuerger](https://github.com/hheimbuerger)
* [extractor] Functions to parse `socket.io` response as `json` by [pukkandan](https://github.com/pukkandan) and [llacb47](https://github.com/llacb47)
* [extractor] Allow `note=False` when extracting manifests
* [utils] Escape URLs in `sanitized_Request`, not `sanitize_url`
* [hls] Disable external downloader for `webtt`
* [youtube] `/live` URLs should raise error if channel is not live
* [youtube] Bug fixes
* [zee5] Fix m3u8 formats' extension
* [ard] Allow URLs without `-` before id by [olifre](https://github.com/olifre)
* [cleanup] `YoutubeDL._match_entry`
* [cleanup] Refactor updater
* [cleanup] Refactor ffmpeg convertors
* [cleanup] setup.py


### 2021.05.20

* **Youtube improvements**:
    * Support youtube music `MP`, `VL` and `browse` pages
    * Extract more formats for youtube music by [craftingmod](https://github.com/craftingmod), [coletdjnz](https://github.com/coletdjnz) and [pukkandan](https://github.com/pukkandan)
    * Extract multiple subtitles in same language by [pukkandan](https://github.com/pukkandan) and [tpikonen](https://github.com/tpikonen)
    * Redirect channels that doesn't have a `videos` tab to their `UU` playlists
    * Support in-channel search
    * Sort audio-only formats correctly
    * Always extract `maxresdefault` thumbnail
    * Extract audio language
    * Add subtitle language names by [nixxo](https://github.com/nixxo) and [tpikonen](https://github.com/tpikonen)
    * Show alerts only from the final webpage
    * Add `html5=1` param to `get_video_info` page requests by [coletdjnz](https://github.com/coletdjnz)
    * Better message when login required
* **Add option `--print`**: to print any field/template
    * Makes redundant: `--get-description`, `--get-duration`, `--get-filename`, `--get-format`, `--get-id`, `--get-thumbnail`, `--get-title`, `--get-url`
* Field `additional_urls` to download additional videos from metadata using [`--parse-metadata`](https://github.com/yt-dlp/yt-dlp#modifying-metadata)
* Merge youtube-dl: Upto [commit/dfbbe29](https://github.com/ytdl-org/youtube-dl/commit/dfbbe2902fc67f0f93ee47a8077c148055c67a9b)
* Write thumbnail of playlist and add `pl_thumbnail` outtmpl key
* [embedthumbnail] Add `flac` support and refactor `mutagen` code by [pukkandan](https://github.com/pukkandan) and [tripulse](https://github.com/tripulse)
* [audius:artist] Add extractor by [king-millez](https://github.com/king-millez)
* [parlview] Add extractor by [king-millez](https://github.com/king-millez)
* [tenplay] Fix extractor by [king-millez](https://github.com/king-millez)
* [rmcdecouverte] Generalize `_VALID_URL`
* Add compat-option `no-attach-infojson`
* Add field `name` for subtitles
* Ensure `post_extract` and `pre_process` only run once
* Fix `--check-formats` when there is network error
* Standardize `write_debug` and `get_param`
* [options] Alias `--write-comments`, `--no-write-comments`
* [options] Refactor callbacks
* [test:download] Only extract enough videos for `playlist_mincount`
* [extractor] bugfix for when `compat_opts` is not given
* [build] Fix x86 build by [shirt](https://github.com/shirt-dev)
* [cleanup] code formatting, youtube tests and readme

### 2021.05.11
* **Deprecate support for Python versions < 3.6**
* **Subtitle extraction from manifests** by [fstirlitz](https://github.com/fstirlitz). See [be6202f](https://github.com/yt-dlp/yt-dlp/commit/be6202f12b97858b9d716e608394b51065d0419f) for details
* **Improve output template:**
    * Allow slicing lists/strings using `field.start:end:step`
    * A field can also be used as offset like `field1+num+field2`
    * A default value can be given using `field|default`
    * Prevent invalid fields from causing errors
* **Merge youtube-dl**: Upto [commit/a726009](https://github.com/ytdl-org/youtube-dl/commit/a7260099873acc6dc7d76cafad2f6b139087afd0)
* **Remove options** `-l`, `-t`, `-A` completely and disable `--auto-number`, `--title`, `--literal`, `--id`
* [Plugins] Prioritize plugins over standard extractors and prevent plugins from overwriting the standard extractor classes
* [downloader] Fix `quiet` and `to_stderr`
* [fragment] Ensure the file is closed on error
* [fragment] Make sure first segment is not skipped
* [aria2c] Fix whitespace being stripped off
* [embedthumbnail] Fix bug where jpeg thumbnails were converted again
* [FormatSort] Fix for when some formats have quality and others don't
* [utils] Add `network_exceptions`
* [utils] Escape URL while sanitizing
* [ukcolumn] Add Extractor
* [whowatch] Add extractor by [nao20010128nao](https://github.com/nao20010128nao)
* [CBS] Improve `_VALID_URL` to support movies
* [crackle] Improve extraction
* [curiositystream] Fix collections
* [francetvinfo] Improve video id extraction
* [generic] Respect the encoding in manifest
* [limelight] Obey `allow_unplayable_formats`
* [mediasite] Generalize URL pattern by [fstirlitz](https://github.com/fstirlitz)
* [mxplayer] Add MxplayerShowIE by [Ashish0804](https://github.com/Ashish0804)
* [nebula] Move to nebula.app by [Lamieur](https://github.com/Lamieur)
* [niconico] Fix HLS formats by [CXwudi](https://github.com/CXwudi), [tsukumijima](https://github.com/tsukumijima), [nao20010128nao](https://github.com/nao20010128nao) and [pukkandan](https://github.com/pukkandan)
* [niconico] Fix title and thumbnail extraction by [CXwudi](https://github.com/CXwudi)
* [plutotv] Extract subtitles from manifests
* [plutotv] Fix format extraction for some urls
* [rmcdecouverte] Improve `_VALID_URL`
* [sonyliv] Fix `title` and `series` extraction by [Ashish0804](https://github.com/Ashish0804)
* [tubi] Raise "no video formats" error when video url is empty
* [youtube:tab] Detect playlists inside community posts
* [youtube] Add `oembed` to reserved names
* [zee5] Fix extraction for some URLs by [Hadi0609](https://github.com/Hadi0609)
* [zee5] Fix py2 compatibility
* Fix `playlist_index` and add `playlist_autonumber`. See [#302](https://github.com/yt-dlp/yt-dlp/issues/302) for details
* Add experimental option `--check-formats` to test the URLs before format selection
* Option `--compat-options` to revert [some of yt-dlp's changes](https://github.com/yt-dlp/yt-dlp#differences-in-default-behavior)
    * Deprecates `--list-formats-as-table`, `--list-formats-old`
* Fix number of digits in `%(playlist_index)s`
* Fix case sensitivity of format selector
* Revert "[core] be able to hand over id and title using url_result"
* Do not strip out whitespaces in `-o` and `-P`
* Fix `preload_download_archive` writing verbose message to `stdout`
* Move option warnings to `YoutubeDL`so that they obey `--no-warnings` and can output colors
* Py2 compatibility for `FileNotFoundError`


### 2021.04.22
* **Improve output template:**
    * Objects can be traversed like `%(field.key1.key2)s`
    * An offset can be added to numeric fields as `%(field+N)s`
    * Deprecates `--autonumber-start`
* **Improve `--sub-langs`:**
    * Treat `--sub-langs` entries as regex
    * `all` can be used to refer to all the subtitles
    * language codes can be prefixed with `-` to exclude it
    * Deprecates `--all-subs`
* Add option `--ignore-no-formats-error` to ignore the "no video format" and similar errors
* Add option `--skip-playlist-after-errors` to skip the rest of a playlist after a given number of errors are encountered
* Merge youtube-dl: Upto [commit/7e8b3f9](https://github.com/ytdl-org/youtube-dl/commit/7e8b3f9439ebefb3a3a4e5da9c0bd2b595976438)
* [downloader] Fix bug in downloader selection
* [BilibiliChannel] Fix pagination by [nao20010128nao](https://github.com/nao20010128nao) and [pukkandan](https://github.com/pukkandan)
* [rai] Add support for http formats by [nixxo](https://github.com/nixxo)
* [TubiTv] Add TubiTvShowIE by [Ashish0804](https://github.com/Ashish0804)
* [twitcasting] Fix extractor
* [viu:ott] Fix extractor and support series by [lkho](https://github.com/lkho) and [pukkandan](https://github.com/pukkandan)
* [youtube:tab] Show unavailable videos in playlists by [coletdjnz](https://github.com/coletdjnz)
* [youtube:tab] Reload with unavailable videos for all playlists
* [youtube] Ignore invalid stretch ratio
* [youtube] Improve channel syncid extraction to support ytcfg by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Standardize API calls for tabs, mixes and search by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Bugfix in `_extract_ytcfg`
* [mildom:user:vod] Download only necessary amount of pages
* [mildom] Remove proxy completely by [fstirlitz](https://github.com/fstirlitz)
* [go] Fix `_VALID_URL`
* [MetadataFromField] Improve regex and add tests
* [Exec] Ensure backward compatibility when the command contains `%`
* [extractor] Fix inconsistent use of `report_warning`
* Ensure `mergeall` selects best format when multistreams are disabled
* Improve the yt-dlp.sh script by [fstirlitz](https://github.com/fstirlitz)
* [lazy_extractor] Do not load plugins
* [ci] Disable fail-fast
* [docs] Clarify which deprecated options still work
* [docs] Fix typos


### 2021.04.11
* Add option `--convert-thumbnails` (only jpg currently supported)
* Format selector `mergeall` to download and merge all formats
* Pass any field to `--exec` using similar syntax to output template
* Choose downloader for each protocol using `--downloader PROTO:NAME`
    * Alias `--downloader` for `--external-downloader`
    * Added `native` as an option for the downloader
* Merge youtube-dl: Upto [commit/4fb25ff](https://github.com/ytdl-org/youtube-dl/commit/4fb25ff5a3be5206bb72e5c4046715b1529fb2c7) (except vimeo)
* [DiscoveryPlusIndia] Add DiscoveryPlusIndiaShowIE by [Ashish0804](https://github.com/Ashish0804)
* [NFHSNetwork] Add extractor by [llacb47](https://github.com/llacb47)
* [nebula] Add extractor (watchnebula.com) by [hheimbuerger](https://github.com/hheimbuerger)
* [nitter] Fix extraction of reply tweets and update instance list by [B0pol](https://github.com/B0pol)
* [nitter] Fix thumbnails by [B0pol](https://github.com/B0pol)
* [youtube] Fix thumbnail URL
* [youtube] Parse API parameters from initial webpage by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Extract comments' approximate timestamp by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Fix alert extraction
* [bilibili] Fix uploader
* [utils] Add `datetime_from_str` and `datetime_add_months` by [coletdjnz](https://github.com/coletdjnz)
* Run some `postprocessors` before actual download
* Improve argument parsing for `-P`, `-o`, `-S`
* Fix some `m3u8` not obeying `--allow-unplayable-formats`
* Fix default of `dynamic_mpd`
* Deprecate `--all-formats`, `--include-ads`, `--hls-prefer-native`, `--hls-prefer-ffmpeg`
* [docs] Improvements

### 2021.04.03
* Merge youtube-dl: Upto [commit/654b4f4](https://github.com/ytdl-org/youtube-dl/commit/654b4f4ff2718f38b3182c1188c5d569c14cc70a)
* Ability to set a specific field in the file's metadata using `--parse-metadata`
* Ability to select n'th best format like `-f bv*.2`
* [DiscoveryPlus] Add discoveryplus.in
* [la7] Add podcasts and podcast playlists by [nixxo](https://github.com/nixxo)
* [mildom] Update extractor with current proxy by [nao20010128nao](https://github.com/nao20010128nao)
* [ard:mediathek] Fix video id extraction
* [generic] Detect Invidious' link element
* [youtube] Show premium state in `availability` by [coletdjnz](https://github.com/coletdjnz)
* [viewsource] Add extractor to handle `view-source:`
* [sponskrub] Run before embedding thumbnail
* [docs] Improve `--parse-metadata` documentation


### 2021.03.24.1
* Revert [commit/8562218](https://github.com/ytdl-org/youtube-dl/commit/8562218350a79d4709da8593bb0c538aa0824acf)

### 2021.03.24
* Merge youtube-dl: Upto 2021.03.25 ([commit/8562218](https://github.com/ytdl-org/youtube-dl/commit/8562218350a79d4709da8593bb0c538aa0824acf))
* Parse metadata from multiple fields using `--parse-metadata`
* Ability to load playlist infojson using `--load-info-json`
* Write current epoch to infojson when using `--no-clean-infojson`
* [youtube_live_chat] fix bug when trying to set cookies
* [niconico] Fix for when logged in by [CXwudi](https://github.com/CXwudi) and [xtkoba](https://github.com/xtkoba)
* [linuxacadamy] Fix login


### 2021.03.21
* Merge youtube-dl: Upto [commit/7e79ba7](https://github.com/ytdl-org/youtube-dl/commit/7e79ba7dd6e6649dd2ce3a74004b2044f2182881)
* Option `--no-clean-infojson` to keep private keys in the infojson
* [aria2c] Support retry/abort unavailable fragments by [damianoamatruda](https://github.com/damianoamatruda)
* [aria2c] Better default arguments
* [movefiles] Fix bugs and make more robust
* [formatSort] Fix `quality` being ignored
* [splitchapters] Fix for older ffmpeg
* [sponskrub] Pass proxy to sponskrub
* Make sure `post_hook` gets the final filename
* Recursively remove any private keys from infojson
* Embed video URL metadata inside `mp4` by [damianoamatruda](https://github.com/damianoamatruda) and [pukkandan](https://github.com/pukkandan)
* Merge `webm` formats into `mkv` if thumbnails are to be embedded by [damianoamatruda](https://github.com/damianoamatruda)
* Use headers and cookies when downloading subtitles by [damianoamatruda](https://github.com/damianoamatruda)
* Parse resolution in info dictionary by [damianoamatruda](https://github.com/damianoamatruda)
* More consistent warning messages by [damianoamatruda](https://github.com/damianoamatruda) and [pukkandan](https://github.com/pukkandan)
* [docs] Add deprecated options and aliases in readme
* [docs] Fix some minor mistakes

* [niconico] Partial fix adapted from [animelover1984/youtube-dl@b5eff52](https://github.com/animelover1984/youtube-dl/commit/b5eff52dd9ed5565672ea1694b38c9296db3fade) (login and smile formats still don't work)
* [niconico] Add user extractor by [animelover1984](https://github.com/animelover1984)
* [bilibili] Add anthology support by [animelover1984](https://github.com/animelover1984)
* [amcnetworks] Fix extractor by [2ShedsJackson](https://github.com/2ShedsJackson)
* [stitcher] Merge from youtube-dl by [nixxo](https://github.com/nixxo)
* [rcs] Improved extraction by [nixxo](https://github.com/nixxo)
* [linuxacadamy] Improve regex
* [youtube] Show if video is `private`, `unlisted` etc in info (`availability`) by [coletdjnz](https://github.com/coletdjnz) and [pukkandan](https://github.com/pukkandan)
* [youtube] bugfix for channel playlist extraction
* [nbc] Improve metadata extraction by [2ShedsJackson](https://github.com/2ShedsJackson)


### 2021.03.15
* **Split video by chapters**: using option `--split-chapters`
    * The output file of the split files can be set with `-o`/`-P` using the prefix `chapter:`
    * Additional keys `section_title`, `section_number`, `section_start`, `section_end` are available in the output template
* **Parallel fragment downloads** by [shirt](https://github.com/shirt-dev)
    * Use option `--concurrent-fragments` (`-N`) to set the number of threads (default 1)
* Merge youtube-dl: Upto [commit/3be0980](https://github.com/ytdl-org/youtube-dl/commit/3be098010f667b14075e3dfad1e74e5e2becc8ea)
* [zee5] Add Show Extractor by [Ashish0804](https://github.com/Ashish0804) and [pukkandan](https://github.com/pukkandan)
* [rai] fix drm check [nixxo](https://github.com/nixxo)
* [wimtv] Add extractor by [nixxo](https://github.com/nixxo)
* [mtv] Add mtv.it and extract series metadata by [nixxo](https://github.com/nixxo)
* [pluto.tv] Add extractor by [kevinoconnor7](https://github.com/kevinoconnor7)
* [youtube] Rewrite comment extraction by [coletdjnz](https://github.com/coletdjnz)
* [embedthumbnail] Set mtime correctly
* Refactor some postprocessor/downloader code by [pukkandan](https://github.com/pukkandan) and [shirt](https://github.com/shirt-dev)


### 2021.03.07
* [youtube] Fix history, mixes, community pages and trending by [pukkandan](https://github.com/pukkandan) and [coletdjnz](https://github.com/coletdjnz)
* [youtube] Fix private feeds/playlists on multi-channel accounts by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Extract alerts from continuation by [coletdjnz](https://github.com/coletdjnz)
* [cbs] Add support for ParamountPlus by [shirt](https://github.com/shirt-dev)
* [mxplayer] Rewrite extractor with show support by [pukkandan](https://github.com/pukkandan) and [Ashish0804](https://github.com/Ashish0804)
* [gedi] Improvements from youtube-dl by [nixxo](https://github.com/nixxo)
* [vimeo] Fix videos with password by [teesid](https://github.com/teesid)
* [lbry] Support `lbry://` url by [nixxo](https://github.com/nixxo)
* [bilibili] Change `Accept` header by [pukkandan](https://github.com/pukkandan) and [animelover1984](https://github.com/animelover1984)
* [trovo] Pass origin header
* [rai] Check for DRM by [nixxo](https://github.com/nixxo)
* [downloader] Fix bug for `ffmpeg`/`httpie`
* [update] Fix updater removing the executable bit on some UNIX distros
* [update] Fix current build hash for UNIX
* [docs] Include wget/curl/aria2c install instructions for Unix by [Ashish0804](https://github.com/Ashish0804)
* Fix some videos downloading with `m3u8` extension
* Remove "fixup is ignored" warning when fixup wasn't passed by user


### 2021.03.03.2
* [build] Fix bug

### 2021.03.03
* [youtube] Use new browse API for continuation page extraction by [coletdjnz](https://github.com/coletdjnz) and [pukkandan](https://github.com/pukkandan)
* Fix HLS playlist downloading by [shirt](https://github.com/shirt-dev)
* Merge youtube-dl: Upto [2021.03.03](https://github.com/ytdl-org/youtube-dl/releases/tag/2021.03.03)
* [mtv] Fix extractor
* [nick] Fix extractor by [DennyDai](https://github.com/DennyDai)
* [mxplayer] Add new extractor by [codeasashu](https://github.com/codeasashu)
* [youtube] Throw error when `--extractor-retries` are exhausted
* Reduce default of `--extractor-retries` to 3
* Fix packaging bugs by [hseg](https://github.com/hseg)


### 2021.03.01
* Allow specifying path in `--external-downloader`
* Add option `--sleep-requests` to sleep b/w requests
* Add option `--extractor-retries` to retry on known extractor errors
* Extract comments only when needed
* `--get-comments` doesn't imply `--write-info-json` if `-J`, `-j` or `--print-json` are used
* Fix `get_executable_path` by [shirt](https://github.com/shirt-dev)
* [youtube] Retry on more known errors than just HTTP-5xx
* [youtube] Fix inconsistent `webpage_url`
* [tennistv] Fix format sorting
* [bilibiliaudio] Recognize the file as audio-only
* [hrfensehen] Fix wrong import
* [viki] Fix viki play pass authentication by [RobinD42](https://github.com/RobinD42)
* [readthedocs] Improvements by [shirt](https://github.com/shirt-dev)
* [hls] Fix bug with m3u8 format extraction
* [hls] Enable `--hls-use-mpegts` by default when downloading live-streams
* [embedthumbnail] Fix bug with deleting original thumbnail
* [build] Fix completion paths, zsh pip completion install by [hseg](https://github.com/hseg)
* [ci] Disable download tests unless specifically invoked
* Cleanup some code and fix typos


### 2021.02.24
* Moved project to an organization [yt-dlp](https://github.com/yt-dlp)
* **Completely changed project name to yt-dlp** by [Pccode66](https://github.com/Pccode66) and [pukkandan](https://github.com/pukkandan)
    * Also, `youtube-dlc` config files are no longer loaded
* Merge youtube-dl: Upto [commit/4460329](https://github.com/ytdl-org/youtube-dl/commit/44603290e5002153f3ebad6230cc73aef42cc2cd) (except tmz, gedi)
* [Readthedocs](https://yt-dlp.readthedocs.io) support by [shirt](https://github.com/shirt-dev)
* [youtube] Show if video was a live stream in info (`was_live`)
* [Zee5] Add new extractor by [Ashish0804](https://github.com/Ashish0804) and [pukkandan](https://github.com/pukkandan)
* [jwplatform] Add support for `hyland.com`
* [tennistv] Fix extractor
* [hls] Support media initialization by [shirt](https://github.com/shirt-dev)
* [hls] Added options `--hls-split-discontinuity` to better support media discontinuity by [shirt](https://github.com/shirt-dev)
* [ffmpeg] Allow passing custom arguments before -i using `--ppa "ffmpeg_i1:ARGS"` syntax
* Fix `--windows-filenames` removing `/` from UNIX paths
* [hls] Show warning if pycryptodome is not found
* [docs] Improvements
    * Fix documentation of `Extractor Options`
    * Document `all` in format selection
    * Document `playable_in_embed` in output templates


### 2021.02.19
* Merge youtube-dl: Upto [commit/cf2dbec](https://github.com/ytdl-org/youtube-dl/commit/cf2dbec6301177a1fddf72862de05fa912d9869d) (except kakao)
* [viki] Fix extractor
* [niconico] Extract `channel` and `channel_id` by [kurumigi](https://github.com/kurumigi)
* [youtube] Multiple page support for hashtag URLs
* [youtube] Add more invidious instances
* [youtube] Fix comment extraction when comment text is empty
* Option `--windows-filenames` to force use of windows compatible filenames
* [ExtractAudio] Bugfix
* Don't raise `parser.error` when exiting for update
* [MoveFiles] Fix for when merger can't run
* Changed `--trim-file-name` to `--trim-filenames` to be similar to related options
* Format Sort improvements:
    * Prefer `vp9.2` more than other `vp9` codecs
    * Remove forced priority of `quality`
    * Remove unnecessary `field_preference` and misuse of `preference` from extractors
* Build improvements:
    * Fix hash output by [shirt](https://github.com/shirt-dev)
    * Lock Python package versions for x86 and use `wheels` by [shirt](https://github.com/shirt-dev)
    * Exclude `vcruntime140.dll` from UPX by [jbruchon](https://github.com/jbruchon)
    * Set version number based on UTC time, not local time
    * Publish on PyPi only if token is set
* [docs] Better document `--prefer-free-formats` and add `--no-prefer-free-format`


### 2021.02.15
* Merge youtube-dl: Upto [2021.02.10](https://github.com/ytdl-org/youtube-dl/releases/tag/2021.02.10) (except archive.org)
* [niconico] Improved extraction and support encrypted/SMILE movies by [kurumigi](https://github.com/kurumigi), [tsukumijima](https://github.com/tsukumijima), [bbepis](https://github.com/bbepis), [pukkandan](https://github.com/pukkandan)
* Fix HLS AES-128 with multiple keys in external downloaders by [shirt](https://github.com/shirt-dev)
* [youtube_live_chat] Fix by using POST API by [siikamiika](https://github.com/siikamiika)
* [rumble] Add support for video page
* Option `--allow-unplayable-formats` to allow downloading unplayable video formats
* [ExtractAudio] Don't re-encode when file is already in a common audio format
* [youtube] Fix search continuations
* [youtube] Fix for new accounts
* Improve build/updater: by [pukkandan](https://github.com/pukkandan) and [shirt](https://github.com/shirt-dev)
    * Fix SHA256 calculation in build and implement hash checking for updater
    * Exit immediately in windows once the update process starts
    * Fix updater for `x86.exe`
    * Updater looks for both `yt-dlp` and `youtube-dlc` in releases for future-proofing
    * Change optional dependency to `pycryptodome`
* Fix issue with unicode filenames in aria2c by [shirt](https://github.com/shirt-dev)
* Fix `allow_playlist_files` not being correctly passed through
* Fix for empty HTTP head requests by [shirt](https://github.com/shirt-dev)
* Fix `get_executable_path` in UNIX
* [sponskrub] Print ffmpeg output and errors to terminal
* `__real_download` should be false when ffmpeg unavailable and no download
* Show `exe`/`zip`/`source` and 32/64bit in verbose message


### 2021.02.09
* **aria2c support for DASH/HLS**: by [shirt](https://github.com/shirt-dev)
* **Implement Updater** (`-U`) by [shirt](https://github.com/shirt-dev)
* [youtube] Fix comment extraction
* [youtube_live_chat] Improve extraction
* [youtube] Fix for channel URLs sometimes not downloading all pages
* [aria2c] Changed default arguments to `--console-log-level=warn --summary-interval=0 --file-allocation=none -x16 -j16 -s16`
* Add fallback for thumbnails
* [embedthumbnail] Keep original thumbnail after conversion if write_thumbnail given
* [embedsubtitle] Keep original subtitle after conversion if write_subtitles given
* [pyinst.py] Move back to root dir
* [youtube] Simplified renderer parsing and bugfixes
* [movefiles] Fix compatibility with python2
* [remuxvideo] Fix validation of conditional remux
* [sponskrub] Don't raise error when the video does not exist
* [docs] Crypto is an optional dependency


### 2021.02.04
* Merge youtube-dl: Upto [2021.02.04.1](https://github.com/ytdl-org/youtube-dl/releases/tag/2021.02.04.1)
* **Date/time formatting in output template:**
    * You can use [`strftime`](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes) to format date/time fields. Example: `%(upload_date>%Y-%m-%d)s`
* **Multiple output templates:**
    * Separate output templates can be given for the different metadata files by using `-o TYPE:TEMPLATE`
    * The allowed types are: `subtitle|thumbnail|description|annotation|infojson|pl_description|pl_infojson`
* [youtube] More metadata extraction for channel/playlist URLs (channel, uploader, thumbnail, tags)
* New option `--no-write-playlist-metafiles` to prevent writing playlist metadata files
* [audius] Fix extractor
* [youtube_live_chat] Fix `parse_yt_initial_data` and add `fragment_retries`
* [postprocessor] Raise errors correctly
* [metadatafromtitle] Fix bug when extracting data from numeric fields
* Fix issue with overwriting files
* Fix "Default format spec" appearing in quiet mode
* [FormatSort] Allow user to prefer av01 over vp9 (The default is still vp9)
* [FormatSort] fix bug where `quality` had more priority than `hasvid`
* [pyinst] Automatically detect Python architecture and working directory
* Strip out internal fields such as `_filename` from infojson


### 2021.01.29
* **Features from [animelover1984/youtube-dl](https://github.com/animelover1984/youtube-dl)**: by [animelover1984](https://github.com/animelover1984) and [bbepis](https://github.com/bbepis)
    * Add `--get-comments`
    * [youtube] Extract comments
    * [billibilli] Added BiliBiliSearchIE, BilibiliChannelIE
    * [billibilli] Extract comments
    * [billibilli] Better video extraction
    * Write playlist data to infojson
    * [FFmpegMetadata] Embed infojson inside the video
    * [EmbedThumbnail] Try embedding in mp4 using ffprobe and `-disposition`
    * [EmbedThumbnail] Treat mka like mkv and mov like mp4
    * [EmbedThumbnail] Embed in ogg/opus
    * [VideoRemuxer] Conditionally remux video
    * [VideoRemuxer] Add `-movflags +faststart` when remuxing to mp4
    * [ffmpeg] Print entire stderr in verbose when there is error
    * [EmbedSubtitle] Warn when embedding ass in mp4
    * [anvato] Use NFLTokenGenerator if possible
* **Parse additional metadata**: New option `--parse-metadata` to extract additional metadata from existing fields
    * The extracted fields can be used in `--output`
    * Deprecated `--metadata-from-title`
* [Audius] Add extractor
* [youtube] Extract playlist description and write it to `.description` file
* Detect existing files even when using `recode`/`remux` (`extract-audio` is partially fixed)
* Fix wrong user config from v2021.01.24
* [youtube] Report error message from youtube as error instead of warning
* [FormatSort] Fix some fields not sorting from v2021.01.24
* [postprocessor] Deprecate `avconv`/`avprobe`.  All current functionality is left untouched. But don't expect any new features to work with avconv
* [postprocessor] fix `write_debug` to not throw error when there is no `_downloader`
* [movefiles] Don't give "cant find" warning when move is unnecessary
* Refactor `update-version`, `pyinst.py` and related files
* [ffmpeg] Document more formats that are supported for remux/recode


### 2021.01.24
* Merge youtube-dl: Upto [2021.01.24](https://github.com/ytdl-org/youtube-dl/releases/tag/2021.01.16)
* Plugin support ([documentation](https://github.com/yt-dlp/yt-dlp#plugins))
* **Multiple paths**: New option `-P`/`--paths` to give different paths for different types of files
    * The syntax is `-P "type:path" -P "type:path"`
    * Valid types are: home, temp, description, annotation, subtitle, infojson, thumbnail
    * Additionally, configuration file is taken from home directory or current directory
* Allow passing different arguments to different external downloaders
* [mildom] Add extractor by [nao20010128nao](https://github.com/nao20010128nao)
* Warn when using old style `--external-downloader-args` and `--post-processor-args`
* Fix `--no-overwrite` when using `--write-link`
* [sponskrub] Output `unrecognized argument` error message correctly
* [cbs] Make failure to extract title non-fatal
* Fix typecasting when pre-checking archive
* Fix issue with setting title on UNIX
* Deprecate redundant aliases in `formatSort`. The aliases remain functional for backward compatibility, but will be left undocumented
* [tests] Fix test_post_hooks
* [tests] Split core and download tests


### 2021.01.20
* [TrovoLive] Add extractor (only VODs)
* [pokemon] Add `/#/player` URLs
* Improved parsing of multiple postprocessor-args, add `--ppa` as alias
* [EmbedThumbnail] Simplify embedding in mkv
* [sponskrub] Encode filenames correctly, better debug output and error message
* [readme] Cleanup options


### 2021.01.16
* Merge youtube-dl: Upto [2021.01.16](https://github.com/ytdl-org/youtube-dl/releases/tag/2021.01.16)
* **Configuration files:**
    * Portable configuration file: `./yt-dlp.conf`
    * Allow the configuration files to be named `yt-dlp` instead of `youtube-dlc`. See [this](https://github.com/yt-dlp/yt-dlp#configuration) for details
* Add PyPI release


### 2021.01.14
* Added option `--break-on-reject`
* [roosterteeth.com] Fix for bonus episodes by [Zocker1999NET](https://github.com/Zocker1999NET)
* [tiktok] Fix for when share_info is empty
* [EmbedThumbnail] Fix bug due to incorrect function name
* [docs] Changed sponskrub links to point to [yt-dlp/SponSkrub](https://github.com/yt-dlp/SponSkrub) since I am now providing both linux and windows releases
* [docs] Change all links to correctly point to new fork URL
* [docs] Fixes typos


### 2021.01.12
* [roosterteeth.com] Add subtitle support by [samiksome](https://github.com/samiksome)
* Added `--force-overwrites`, `--no-force-overwrites` by [alxnull](https://github.com/alxnull)
* Changed fork name to `yt-dlp`
* Fix typos by [FelixFrog](https://github.com/FelixFrog)
* [ci] Option to skip
* [changelog] Added unreleased changes in blackjack4494/yt-dlc


### 2021.01.10
* [archive.org] Fix extractor and add support for audio and playlists by [wporr](https://github.com/wporr)
* [Animelab] Added by [mariuszskon](https://github.com/mariuszskon)
* [youtube:search] Fix view_count by [ohnonot](https://github.com/ohnonot)
* [youtube] Show if video is embeddable in info (`playable_in_embed`)
* Update version badge automatically in README
* Enable `test_youtube_search_matching`
* Create `to_screen` and similar functions in postprocessor/common


### 2021.01.09
* [youtube] Fix bug in automatic caption extraction
* Add `post_hooks` to YoutubeDL by [alexmerkel](https://github.com/alexmerkel)
* Batch file enumeration improvements by [glenn-slayden](https://github.com/glenn-slayden)
* Stop immediately when reaching `--max-downloads` by [glenn-slayden](https://github.com/glenn-slayden)
* Fix incorrect ANSI sequence for restoring console-window title by [glenn-slayden](https://github.com/glenn-slayden)
* Kill child processes when yt-dlc is killed by [Unrud](https://github.com/Unrud)


### 2021.01.08
* Merge youtube-dl: Upto [2021.01.08](https://github.com/ytdl-org/youtube-dl/releases/tag/2021.01.08) except stitcher ([1](https://github.com/ytdl-org/youtube-dl/commit/bb38a1215718cdf36d73ff0a7830a64cd9fa37cc), [2](https://github.com/ytdl-org/youtube-dl/commit/a563c97c5cddf55f8989ed7ea8314ef78e30107f))
* Moved changelog to separate file


### 2021.01.07-1
* [Akamai] fix by [nixxo](https://github.com/nixxo)
* [Tiktok] merge youtube-dl tiktok extractor by [GreyAlien502](https://github.com/GreyAlien502)
* [vlive] add support for playlists by [kyuyeunk](https://github.com/kyuyeunk)
* [youtube_live_chat] make sure playerOffsetMs is positive by [siikamiika](https://github.com/siikamiika)
* Ignore extra data streams in ffmpeg by [jbruchon](https://github.com/jbruchon)
* Allow passing different arguments to different postprocessors using `--postprocessor-args`
* Deprecated `--sponskrub-args`. The same can now be done using `--postprocessor-args "sponskrub:<args>"`
* [CI] Split tests into core-test and full-test


### 2021.01.07
* Removed priority of `av01` codec in `-S` since most devices don't support it yet
* Added `duration_string` to be used in `--output`
* Created First Release


### 2021.01.05-1
* **Changed defaults:**
    * Enabled `--ignore`
    * Disabled `--video-multistreams` and `--audio-multistreams`
    * Changed default format selection to `bv*+ba/b` when `--audio-multistreams` is disabled
    * Changed default format sort order to `res,fps,codec,size,br,asr,proto,ext,has_audio,source,format_id`
    * Changed `webm` to be more preferable than `flv` in format sorting
    * Changed default output template to `%(title)s [%(id)s].%(ext)s`
    * Enabled `--list-formats-as-table`


### 2021.01.05
* **Format Sort:** Added `--format-sort` (`-S`), `--format-sort-force` (`--S-force`) - See [Sorting Formats](README.md#sorting-formats) for details
* **Format Selection:** See [Format Selection](README.md#format-selection) for details
    * New format selectors: `best*`, `worst*`, `bestvideo*`, `bestaudio*`, `worstvideo*`, `worstaudio*`
    * Changed video format sorting to show video only files and video+audio files together
    * Added `--video-multistreams`, `--no-video-multistreams`, `--audio-multistreams`, `--no-audio-multistreams`
    * Added `b`,`w`,`v`,`a` as alias for `best`, `worst`, `video` and `audio` respectively
* Shortcut Options: Added `--write-link`, `--write-url-link`, `--write-webloc-link`, `--write-desktop-link` by [h-h-h-h](https://github.com/h-h-h-h) - See [Internet Shortcut Options](README.md#internet-shortcut-options) for details
* **Sponskrub integration:** Added `--sponskrub`, `--sponskrub-cut`, `--sponskrub-force`, `--sponskrub-location`, `--sponskrub-args` - See [SponSkrub Options](README.md#sponskrub-sponsorblock-options) for details
* Added `--force-download-archive` (`--force-write-archive`) by [h-h-h-h](https://github.com/h-h-h-h)
* Added `--list-formats-as-table`,  `--list-formats-old`
* **Negative Options:** Makes it possible to negate most boolean options by adding a `no-` to the switch. Usefull when you want to reverse an option that is defined in a config file
    * Added `--no-ignore-dynamic-mpd`, `--no-allow-dynamic-mpd`, `--allow-dynamic-mpd`, `--youtube-include-hls-manifest`, `--no-youtube-include-hls-manifest`, `--no-youtube-skip-hls-manifest`, `--no-download`, `--no-download-archive`, `--resize-buffer`, `--part`, `--mtime`, `--no-keep-fragments`, `--no-cookies`, `--no-write-annotations`, `--no-write-info-json`, `--no-write-description`, `--no-write-thumbnail`, `--youtube-include-dash-manifest`, `--post-overwrites`, `--no-keep-video`, `--no-embed-subs`, `--no-embed-thumbnail`, `--no-add-metadata`, `--no-include-ads`, `--no-write-sub`, `--no-write-auto-sub`, `--no-playlist-reverse`, `--no-restrict-filenames`, `--youtube-include-dash-manifest`, `--no-format-sort-force`, `--flat-videos`, `--no-list-formats-as-table`, `--no-sponskrub`, `--no-sponskrub-cut`, `--no-sponskrub-force`
    * Renamed: `--write-subs`, `--no-write-subs`, `--no-write-auto-subs`, `--write-auto-subs`. Note that these can still be used without the ending "s"
* Relaxed validation for format filters so that any arbitrary field can be used
* Fix for embedding thumbnail in mp3 by [pauldubois98](https://github.com/pauldubois98) ([ytdl-org/youtube-dl#21569](https://github.com/ytdl-org/youtube-dl/pull/21569))
* Make Twitch Video ID output from Playlist and VOD extractor same. This is only a temporary fix
* Merge youtube-dl: Upto [2021.01.03](https://github.com/ytdl-org/youtube-dl/commit/8e953dcbb10a1a42f4e12e4e132657cb0100a1f8) - See [blackjack4494/yt-dlc#280](https://github.com/blackjack4494/yt-dlc/pull/280) for details
    * Extractors [tiktok](https://github.com/ytdl-org/youtube-dl/commit/fb626c05867deab04425bad0c0b16b55473841a2) and [hotstar](https://github.com/ytdl-org/youtube-dl/commit/bb38a1215718cdf36d73ff0a7830a64cd9fa37cc) have not been merged
* Cleaned up the fork for public use


**Note**: All uncredited changes above this point are authored by [pukkandan](https://github.com/pukkandan)

### Unreleased changes in [blackjack4494/yt-dlc](https://github.com/blackjack4494/yt-dlc)
* Updated to youtube-dl release 2020.11.26 by [pukkandan](https://github.com/pukkandan)
* Youtube improvements by [pukkandan](https://github.com/pukkandan)
    * Implemented all Youtube Feeds (ytfav, ytwatchlater, ytsubs, ythistory, ytrec) and SearchURL
    * Fix some improper Youtube URLs
    * Redirect channel home to /video
    * Print youtube's warning message
    * Handle Multiple pages for feeds better
* [youtube] Fix ytsearch not returning results sometimes due to promoted content by [coletdjnz](https://github.com/coletdjnz)
* [youtube] Temporary fix for automatic captions - disable json3 by [blackjack4494](https://github.com/blackjack4494)
* Add --break-on-existing by [gergesh](https://github.com/gergesh)
* Pre-check video IDs in the archive before downloading by [pukkandan](https://github.com/pukkandan)
* [bitwave.tv] New extractor by [lorpus](https://github.com/lorpus)
* [Gedi] Add extractor by [nixxo](https://github.com/nixxo)
* [Rcs] Add new extractor by [nixxo](https://github.com/nixxo)
* [skyit] New skyitalia extractor by [nixxo](https://github.com/nixxo)
* [france.tv] Fix thumbnail URL by [renalid](https://github.com/renalid)
* [ina] support mobile links by [B0pol](https://github.com/B0pol)
* [instagram] Fix thumbnail extractor by [nao20010128nao](https://github.com/nao20010128nao)
* [SouthparkDe] Support for English URLs by [xypwn](https://github.com/xypwn)
* [spreaker] fix SpreakerShowIE test URL by [pukkandan](https://github.com/pukkandan)
* [Vlive] Fix playlist handling when downloading a channel by [kyuyeunk](https://github.com/kyuyeunk)
* [tmz] Fix extractor by [diegorodriguezv](https://github.com/diegorodriguezv)
* [ITV] BTCC URL update by [WolfganP](https://github.com/WolfganP)
* [generic] Detect embedded bitchute videos by [pukkandan](https://github.com/pukkandan)
* [generic] Extract embedded youtube and twitter videos by [diegorodriguezv](https://github.com/diegorodriguezv)
* [ffmpeg] Ensure all streams are copied by [pukkandan](https://github.com/pukkandan)
* [embedthumbnail] Fix for os.rename error by [pukkandan](https://github.com/pukkandan)
* make_win.bat: don't use UPX to pack vcruntime140.dll by [jbruchon](https://github.com/jbruchon)


### Changelog of [blackjack4494/yt-dlc](https://github.com/blackjack4494/yt-dlc) till release 2020.11.11-3

**Note**: This was constructed from the merge commit messages and may not be entirely accurate

* [bandcamp] fix failing test. remove subclass hack by [insaneracist](https://github.com/insaneracist)
* [bandcamp] restore album downloads by [insaneracist](https://github.com/insaneracist)
* [francetv] fix extractor by [Surkal](https://github.com/Surkal)
* [gdcvault] fix extractor by [blackjack4494](https://github.com/blackjack4494)
* [hotstar] Move to API v1 by [theincognito-inc](https://github.com/theincognito-inc)
* [hrfernsehen] add extractor by [blocktrron](https://github.com/blocktrron)
* [kakao] new apis by [blackjack4494](https://github.com/blackjack4494)
* [la7] fix missing protocol by [nixxo](https://github.com/nixxo)
* [mailru] removed escaped braces, use urljoin, added tests by [nixxo](https://github.com/nixxo)
* [MTV/Nick] universal mgid extractor + fix nick.de feed by [blackjack4494](https://github.com/blackjack4494)
* [mtv] Fix a missing match_id by [nixxo](https://github.com/nixxo)
* [Mtv] updated extractor logic & more by [blackjack4494](https://github.com/blackjack4494)
* [ndr] support Daserste ndr by [blackjack4494](https://github.com/blackjack4494)
* [Netzkino] Only use video id to find metadata by [TobiX](https://github.com/TobiX)
* [newgrounds] fix: video download by [insaneracist](https://github.com/insaneracist)
* [nitter] Add new extractor by [B0pol](https://github.com/B0pol)
* [soundcloud] Resolve audio/x-wav by [tfvlrue](https://github.com/tfvlrue)
* [soundcloud] sets pattern and tests by [blackjack4494](https://github.com/blackjack4494)
* [SouthparkDE/MTV] another mgid extraction (mtv_base) feed url updated by [blackjack4494](https://github.com/blackjack4494)
* [StoryFire] Add new extractor by [sgstair](https://github.com/sgstair)
* [twitch] by [geauxlo](https://github.com/geauxlo)
* [videa] Adapt to updates by [adrianheine](https://github.com/adrianheine)
* [Viki] subtitles, formats by [blackjack4494](https://github.com/blackjack4494)
* [vlive] fix extractor for revamped website by [exwm](https://github.com/exwm)
* [xtube] fix extractor by [insaneracist](https://github.com/insaneracist)
* [youtube] Convert subs when download is skipped by [blackjack4494](https://github.com/blackjack4494)
* [youtube] Fix age gate detection by [random-nick](https://github.com/random-nick)
* [youtube] fix yt-only playback when age restricted/gated - requires cookies by [blackjack4494](https://github.com/blackjack4494)
* [youtube] fix: extract artist metadata from ytInitialData by [insaneracist](https://github.com/insaneracist)
* [youtube] fix: extract mix playlist ids from ytInitialData by [insaneracist](https://github.com/insaneracist)
* [youtube] fix: mix playlist title by [insaneracist](https://github.com/insaneracist)
* [youtube] fix: Youtube Music playlists by [insaneracist](https://github.com/insaneracist)
* [Youtube] Fixed problem with new youtube player by [peet1993](https://github.com/peet1993)
* [zoom] Fix url parsing for url's containing /share/ and dots by [Romern](https://github.com/Romern)
* [zoom] new extractor by [insaneracist](https://github.com/insaneracist)
* abc by [adrianheine](https://github.com/adrianheine)
* Added Comcast_SSO fix by [merval](https://github.com/merval)
* Added DRM logic to brightcove by [merval](https://github.com/merval)
* Added regex for ABC.com site. by [kucksdorfs](https://github.com/kucksdorfs)
* alura by [hugohaa](https://github.com/hugohaa)
* Arbitrary merges by [fstirlitz](https://github.com/fstirlitz)
* ard.py_add_playlist_support by [martin54](https://github.com/martin54)
* Bugfix/youtube/chapters fix extractor by [gschizas](https://github.com/gschizas)
* bugfix_youtube_like_extraction by [RedpointsBots](https://github.com/RedpointsBots)
* Create build workflow by [blackjack4494](https://github.com/blackjack4494)
* deezer by [LucBerge](https://github.com/LucBerge)
* Detect embedded bitchute videos by [pukkandan](https://github.com/pukkandan)
* Don't install tests by [l29ah](https://github.com/l29ah)
* Don't try to embed/convert json subtitles generated by [youtube](https://github.com/youtube) livechat by [pukkandan](https://github.com/pukkandan)
* Doodstream by [sxvghd](https://github.com/sxvghd)
* duboku by [lkho](https://github.com/lkho)
* elonet by [tpikonen](https://github.com/tpikonen)
* ext/remuxe-video by [Zocker1999NET](https://github.com/Zocker1999NET)
* fall-back to the old way to fetch subtitles, if needed by [RobinD42](https://github.com/RobinD42)
* feature_subscriber_count by [RedpointsBots](https://github.com/RedpointsBots)
* Fix external downloader when there is no http_header by [pukkandan](https://github.com/pukkandan)
* Fix issue triggered by [tubeup](https://github.com/tubeup) by [nsapa](https://github.com/nsapa)
* Fix YoutubePlaylistsIE by [ZenulAbidin](https://github.com/ZenulAbidin)
* fix-mitele' by [DjMoren](https://github.com/DjMoren)
* fix/google-drive-cookie-issue by [legraphista](https://github.com/legraphista)
* fix_tiktok by [mervel-mervel](https://github.com/mervel-mervel)
* Fixed problem with JS player URL by [peet1993](https://github.com/peet1993)
* fixYTSearch by [xarantolus](https://github.com/xarantolus)
* FliegendeWurst-3sat-zdf-merger-bugfix-feature
* gilou-bandcamp_update
* implement ThisVid extractor by [rigstot](https://github.com/rigstot)
* JensTimmerman-patch-1 by [JensTimmerman](https://github.com/JensTimmerman)
* Keep download archive in memory for better performance by [jbruchon](https://github.com/jbruchon)
* la7-fix by [iamleot](https://github.com/iamleot)
* magenta by [adrianheine](https://github.com/adrianheine)
* Merge 26564 from [adrianheine](https://github.com/adrianheine)
* Merge code from [ddland](https://github.com/ddland)
* Merge code from [nixxo](https://github.com/nixxo)
* Merge code from [ssaqua](https://github.com/ssaqua)
* Merge code from [zubearc](https://github.com/zubearc)
* mkvthumbnail by [MrDoritos](https://github.com/MrDoritos)
* myvideo_ge by [fonkap](https://github.com/fonkap)
* naver by [SeonjaeHyeon](https://github.com/SeonjaeHyeon)
* ondemandkorea by [julien-hadleyjack](https://github.com/julien-hadleyjack)
* rai-update by [iamleot](https://github.com/iamleot)
* RFC: youtube: Polymer UI and JSON endpoints for playlists by [wlritchi](https://github.com/wlritchi)
* rutv by [adrianheine](https://github.com/adrianheine)
* Sc extractor web auth by [blackjack4494](https://github.com/blackjack4494)
* Switch from binary search tree to Python sets by [jbruchon](https://github.com/jbruchon)
* tiktok by [skyme5](https://github.com/skyme5)
* tvnow by [TinyToweringTree](https://github.com/TinyToweringTree)
* twitch-fix by [lel-amri](https://github.com/lel-amri)
* Twitter shortener by [blackjack4494](https://github.com/blackjack4494)
* Update README.md by [JensTimmerman](https://github.com/JensTimmerman)
* Update to reflect website changes. by [amigatomte](https://github.com/amigatomte)
* use webarchive to fix a dead link in README by [B0pol](https://github.com/B0pol)
* Viki the second by [blackjack4494](https://github.com/blackjack4494)
* wdr-subtitles by [mrtnmtth](https://github.com/mrtnmtth)
* Webpfix by [alexmerkel](https://github.com/alexmerkel)
* Youtube live chat by [siikamiika](https://github.com/siikamiika)
