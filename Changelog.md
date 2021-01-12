# Changelog

<!--
# Instuctions for creating release

* Run `make doc`
* Update Changelog.md and Authors-Fork
* Commit to master as `Release <version>`
* Push to origin/release - build task will now run
* Update version.py and run `make issuetemplates`
* Commit to master as `[version] update`
* Push to origin/master
* Update changelog in /releases

-->


### 2021.01.10
* [archive.org] Fix extractor and add support for audio and playlists by @wporr
* [Animelab] Added by @mariuszskon
* [youtube:search] Fix view_count by @ohnonot
* [youtube] Show if video is embeddable in info
* Update version badge automatically in README
* Enable `test_youtube_search_matching`
* Create `to_screen` and similar functions in postprocessor/common


### 2021.01.09
* [youtube] Fix bug in automatic caption extraction
* Add `post_hooks` to YoutubeDL by @alexmerkel
* Batch file enumeration improvements by @glenn-slayden
* Stop immediately when reaching `--max-downloads` by @glenn-slayden
* Fix incorrect ANSI sequence for restoring console-window title by @glenn-slayden
* Kill child processes when yt-dlc is killed by @Unrud


### 2021.01.08
* **Merge youtube-dl:** Upto [2020.01.08](https://github.com/ytdl-org/youtube-dl/commit/bf6a74c620bd4d5726503c5302906bb36b009026)
    * Extractor stitcher ([1](https://github.com/ytdl-org/youtube-dl/commit/bb38a1215718cdf36d73ff0a7830a64cd9fa37cc), [2](https://github.com/ytdl-org/youtube-dl/commit/a563c97c5cddf55f8989ed7ea8314ef78e30107f)) have not been merged
* Moved changelog to seperate file


### 2021.01.07-1
* [Akamai] fix by @nixxo
* [Tiktok] merge youtube-dl tiktok extractor by @GreyAlien502
* [vlive] add support for playlists by @kyuyeunk
* [youtube_live_chat] make sure playerOffsetMs is positive by @siikamiika
* Ignore extra data streams in ffmpeg by @jbruchon
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
* **Shortcut Options:** Added `--write-link`, `--write-url-link`, `--write-webloc-link`, `--write-desktop-link` by @h-h-h-h - See [Internet Shortcut Options]README.md(#internet-shortcut-options) for details
* **Sponskrub integration:** Added `--sponskrub`, `--sponskrub-cut`, `--sponskrub-force`, `--sponskrub-location`, `--sponskrub-args` - See [SponSkrub Options](README.md#sponskrub-options-sponsorblock) for details
* Added `--force-download-archive` (`--force-write-archive`) by by h-h-h-h
* Added `--list-formats-as-table`,  `--list-formats-old`
* **Negative Options:** Makes it possible to negate most boolean options by adding a `no-` to the switch. Usefull when you want to reverse an option that is defined in a config file
    * Added `--no-ignore-dynamic-mpd`, `--no-allow-dynamic-mpd`, `--allow-dynamic-mpd`, `--youtube-include-hls-manifest`, `--no-youtube-include-hls-manifest`, `--no-youtube-skip-hls-manifest`, `--no-download`, `--no-download-archive`, `--resize-buffer`, `--part`, `--mtime`, `--no-keep-fragments`, `--no-cookies`, `--no-write-annotations`, `--no-write-info-json`, `--no-write-description`, `--no-write-thumbnail`, `--youtube-include-dash-manifest`, `--post-overwrites`, `--no-keep-video`, `--no-embed-subs`, `--no-embed-thumbnail`, `--no-add-metadata`, `--no-include-ads`, `--no-write-sub`, `--no-write-auto-sub`, `--no-playlist-reverse`, `--no-restrict-filenames`, `--youtube-include-dash-manifest`, `--no-format-sort-force`, `--flat-videos`, `--no-list-formats-as-table`, `--no-sponskrub`, `--no-sponskrub-cut`, `--no-sponskrub-force`
    * Renamed: `--write-subs`, `--no-write-subs`, `--no-write-auto-subs`, `--write-auto-subs`. Note that these can still be used without the ending "s"
* Relaxed validation for format filters so that any arbitrary field can be used
* Fix for embedding thumbnail in mp3 by @pauldubois98
* Make Twitch Video ID output from Playlist and VOD extractor same. This is only a temporary fix
* **Merge youtube-dl:** Upto [2020.01.03](https://github.com/ytdl-org/youtube-dl/commit/8e953dcbb10a1a42f4e12e4e132657cb0100a1f8) - See [blackjack4494/yt-dlc#280](https://github.com/blackjack4494/yt-dlc/pull/280) for details
    * Extractors [tiktok](https://github.com/ytdl-org/youtube-dl/commit/fb626c05867deab04425bad0c0b16b55473841a2) and [hotstar](https://github.com/ytdl-org/youtube-dl/commit/bb38a1215718cdf36d73ff0a7830a64cd9fa37cc) have not been merged
* Cleaned up the fork for public use


### Unreleased changes in [blackjack4494/yt-dlc](https://github.com/blackjack4494/yt-dlc)
* Updated to youtube-dl release 2020.11.26
* [youtube]
    * Implemented all Youtube Feeds (ytfav, ytwatchlater, ytsubs, ythistory, ytrec) and SearchURL
    * Fix ytsearch not returning results sometimes due to promoted content
    * Temporary fix for automatic captions - disable json3
    * Fix some improper Youtube URLs
    * Redirect channel home to /video
    * Print youtube's warning message
    * Multiple pages are handled better for feeds
* Add --break-on-existing by @gergesh
* Pre-check video IDs in the archive before downloading
* [bitwave.tv] New extractor
* [Gedi] Add extractor
* [Rcs] Add new extractor
* [skyit] Add support for multiple Sky Italia website and removed old skyitalia extractor
* [france.tv] Fix thumbnail URL
* [ina] support mobile links
* [instagram] Fix extractor
* [itv] BTCC new pages' URL update (articles instead of races)
* [SouthparkDe] Support for English URLs
* [spreaker] fix SpreakerShowIE test URL
* [Vlive] Fix playlist handling when downloading a channel
* [generic] Detect embedded bitchute videos
* [generic] Extract embedded youtube and twitter videos
* [ffmpeg] Ensure all streams are copied
* Fix for os.rename error when embedding thumbnail to video in a different drive
* make_win.bat: don't use UPX to pack vcruntime140.dll
