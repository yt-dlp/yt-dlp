# Changelog

<!--
# Instuctions for creating release

* Run `make doc`
* Update Changelog.md and CONTRIBUTORS
* Change "Based on ytdl" version in Readme.md if needed
* Commit as `Release <version>` and push to master
* Dispatch the workflow https://github.com/yt-dlp/yt-dlp/actions/workflows/build.yml on master
-->


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
* [utils] ExtractorError: Fix for older python versions
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
* **Deprecate support for python versions < 3.6**
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
    * Lock python package versions for x86 and use `wheels` by [shirt](https://github.com/shirt-dev)
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
* [pyinst] Automatically detect python architecture and working directory
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
