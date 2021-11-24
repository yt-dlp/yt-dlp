# Changelog

<!--
# Instuctions for creating release

* Run `make doc`
* Update Changelog.md and CONTRIBUTORS
* Change "Merged with ytdl" version in Readme.md if needed
* Add new/fixed extractors in "new features" section of Readme.md
* Commit as `Release <version>`
* Push to origin/release using `git push origin master:release`
    build task will now run

-->


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
    * Enable lazy-extractors in releases. 
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
* [outtmpl] Add format type `B` to treat the value as bytes (eg: to limit the filename to a certain number of bytes)
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
* [build] Provide `--onedir` zip for windows by [pukkandan](https://github.com/pukkandan)
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
    * Add extractor option `skip` for `youtube`. Eg: `--extractor-args youtube:skip=hls,dash`
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
* [build,update] Add GNU-style SHA512 and prepare updater for simlar SHA256 by [nihil-admirari](https://github.com/nihil-admirari)
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
    * Changed video format sorting to show video only files and video+audio files together.
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


**PS**: All uncredited changes above this point are authored by [pukkandan](https://github.com/pukkandan)

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
* [generic] Detect embedded bitchute videos by [pukkandan](https://github.com/pukkandan)
* [generic] Extract embedded youtube and twitter videos by [diegorodriguezv](https://github.com/diegorodriguezv)
* [ffmpeg] Ensure all streams are copied by [pukkandan](https://github.com/pukkandan)
* [embedthumbnail] Fix for os.rename error by [pukkandan](https://github.com/pukkandan)
* make_win.bat: don't use UPX to pack vcruntime140.dll by [jbruchon](https://github.com/jbruchon)
