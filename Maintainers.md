# Maintainers

This file lists the maintainers of yt-dlp and their major contributions. See the [Changelog](Changelog.md) for more details.

You can also find lists of all [contributors of yt-dlp](CONTRIBUTORS) and [authors of youtube-dl](https://github.com/ytdl-org/youtube-dl/blob/master/AUTHORS)

## Core Maintainers

Core Maintainers are responsible for reviewing and merging contributions, publishing releases, and steering the overall direction of the project.

**You can contact the core maintainers via `maintainers@yt-dlp.org`.** This email address is **NOT** a support channel. [Open an issue](https://github.com/yt-dlp/yt-dlp/issues/new/choose) if you need help or want to report a bug.

### [coletdjnz](https://github.com/coletdjnz)

[![gh-sponsor](https://img.shields.io/badge/_-Github-white.svg?logo=github&labelColor=555555&style=for-the-badge)](https://github.com/sponsors/coletdjnz)

* Overhauled the networking stack and implemented support for `requests` and `curl_cffi` (`--impersonate`) HTTP clients
* Reworked the plugin architecture to support installing plugins across all yt-dlp distributions (exe, pip, etc.)
* Implemented support for external JavaScript runtimes/engines
* Maintains support for YouTube
* Added and fixed support for various other sites

### [bashonly](https://github.com/bashonly)

* Rewrote and maintains the build/release workflows and the self-updater: executables, automated/nightly/master releases, `--update-to`
* Overhauled external downloader cookie handling
* Helped in implementing support for external JavaScript runtimes/engines
* Added `--cookies-from-browser` support for Firefox containers
* Maintains support for sites like YouTube, Vimeo, Twitter, TikTok, etc
* Added support for various sites


### [Grub4K](https://github.com/Grub4K)

[![gh-sponsor](https://img.shields.io/badge/_-Github-white.svg?logo=github&labelColor=555555&style=for-the-badge)](https://github.com/sponsors/Grub4K) [![ko-fi](https://img.shields.io/badge/_-Ko--fi-red.svg?logo=kofi&labelColor=555555&style=for-the-badge)](https://ko-fi.com/Grub4K)

* `--update-to`, self-updater rewrite, automated/nightly/master releases
* Reworked internals like `traverse_obj`, various core refactors and bugs fixes
* Implemented proper progress reporting for parallel downloads
* Implemented support for external JavaScript runtimes/engines
* Improved/fixed/added Bundestag, crunchyroll, pr0gramm, Twitter, WrestleUniverse etc


### [sepro](https://github.com/seproDev)

* UX improvements: Warn when ffmpeg is missing, warn when double-clicking exe
* Helped in implementing support for external JavaScript runtimes/engines
* Code cleanup: Remove dead extractors, mark extractors as broken, enable/apply ruff rules
* Improved/fixed/added ArdMediathek, DRTV, Floatplane, MagentaMusik, Naver, Nebula, OnDemandKorea, Vbox7 etc


## Inactive Core Maintainers

### [pukkandan](https://github.com/pukkandan)

[![ko-fi](https://img.shields.io/badge/_-Ko--fi-red.svg?logo=kofi&labelColor=555555&style=for-the-badge)](https://ko-fi.com/pukkandan)
[![gh-sponsor](https://img.shields.io/badge/_-Github-white.svg?logo=github&labelColor=555555&style=for-the-badge)](https://github.com/sponsors/pukkandan)

* Founder of the fork
* Lead Maintainer from 2021-2024


### [shirt](https://github.com/shirt-dev)

[![ko-fi](https://img.shields.io/badge/_-Ko--fi-red.svg?logo=kofi&labelColor=555555&style=for-the-badge)](https://ko-fi.com/shirt)

* Multithreading (`-N`) and aria2c support for fragment downloads
* Support for media initialization and discontinuity in HLS
* The self-updater (`-U`)


### [Ashish0804](https://github.com/Ashish0804)

[![ko-fi](https://img.shields.io/badge/_-Ko--fi-red.svg?logo=kofi&labelColor=555555&style=for-the-badge)](https://ko-fi.com/ashish0804)

* Added support for new websites BiliIntl, DiscoveryPlusIndia, OlympicsReplay, PlanetMarathi, ShemarooMe, Utreon, Zee5 etc
* Added playlist/series downloads for Hotstar, ParamountPlus, Rumble, SonyLIV, Trovo, TubiTv, Voot etc
* Improved/fixed support for HiDive, HotStar, Hungama, LBRY, LinkedInLearning, Mxplayer, SonyLiv, TV2, Vimeo, VLive etc

## Triage Maintainers

Triage Maintainers are frequent contributors who can manage issues and pull requests.

- [gamer191](https://github.com/gamer191)
- [garret1317](https://github.com/garret1317)
- [pzhlkj6612](https://github.com/pzhlkj6612)
- [DTrombett](https://github.com/dtrombett)
- [doe1080](https://github.com/doe1080)
- [grqz](https://github.com/grqz)
