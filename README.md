<div align="center">

# YT-DLP
A command-line program to download videos from YouTube and many other [video platforms](supportedsites.md)

<!-- GHA doesn't have for-the-badge style
[![CI Status](https://github.com/yt-dlp/yt-dlp/workflows/Core%20Tests/badge.svg?branch=master)](https://github.com/yt-dlp/yt-dlp/actions)
-->
[![Release version](https://img.shields.io/github/v/release/yt-dlp/yt-dlp?color=brightgreen&label=Release&style=for-the-badge)](https://github.com/yt-dlp/yt-dlp/releases/latest)
[![License: Unlicense](https://img.shields.io/badge/License-Unlicense-blue.svg?style=for-the-badge)](LICENSE)
[![Doc Status](https://readthedocs.org/projects/yt-dlp/badge/?version=latest&style=for-the-badge)](https://yt-dlp.readthedocs.io)
[![Discord](https://img.shields.io/discord/807245652072857610?color=blue&label=discord&logo=discord&style=for-the-badge)](https://discord.gg/H5MNcFW63r)
[![Commits](https://img.shields.io/github/commit-activity/m/yt-dlp/yt-dlp?label=commits&style=for-the-badge)](https://github.com/yt-dlp/yt-dlp/commits)
[![Last Commit](https://img.shields.io/github/last-commit/yt-dlp/yt-dlp/master?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp/commits)
[![Downloads](https://img.shields.io/github/downloads/yt-dlp/yt-dlp/total?style=for-the-badge&color=blue)](https://github.com/yt-dlp/yt-dlp/releases/latest)
[![PyPi Downloads](https://img.shields.io/pypi/dm/yt-dlp?label=PyPi&style=for-the-badge)](https://pypi.org/project/yt-dlp)

</div>

yt-dlp is a [youtube-dl](https://github.com/ytdl-org/youtube-dl) fork based on the now inactive [youtube-dlc](https://github.com/blackjack4494/yt-dlc). The main focus of this project is adding new features and patches while also keeping up to date with the original project

* [NEW FEATURES](#new-features)
    * [Differences in default behavior](#differences-in-default-behavior)
* [INSTALLATION](#installation)
    * [Dependencies](#dependencies)
    * [Update](#update)
    * [Compile](#compile)
* [USAGE AND OPTIONS](#usage-and-options)
    * [General Options](#general-options)
    * [Network Options](#network-options)
    * [Geo-restriction](#geo-restriction)
    * [Video Selection](#video-selection)
    * [Download Options](#download-options)
    * [Filesystem Options](#filesystem-options)
    * [Thumbnail Options](#thumbnail-options)
    * [Internet Shortcut Options](#internet-shortcut-options)
    * [Verbosity and Simulation Options](#verbosity-and-simulation-options)
    * [Workarounds](#workarounds)
    * [Video Format Options](#video-format-options)
    * [Subtitle Options](#subtitle-options)
    * [Authentication Options](#authentication-options)
    * [Post-processing Options](#post-processing-options)
    * [SponSkrub (SponsorBlock) Options](#sponskrub-sponsorblock-options)
    * [Extractor Options](#extractor-options)
* [CONFIGURATION](#configuration)
    * [Authentication with .netrc file](#authentication-with-netrc-file)
* [OUTPUT TEMPLATE](#output-template)
    * [Output template and Windows batch files](#output-template-and-windows-batch-files)
    * [Output template examples](#output-template-examples)
* [FORMAT SELECTION](#format-selection)
    * [Filtering Formats](#filtering-formats)
    * [Sorting Formats](#sorting-formats)
    * [Format Selection examples](#format-selection-examples)
* [MODIFYING METADATA](#modifying-metadata)
    * [Modifying metadata examples](#modifying-metadata-examples)
* [PLUGINS](#plugins)
* [DEPRECATED OPTIONS](#deprecated-options)
* [MORE](#more)
</div>


# NEW FEATURES
The major new features from the latest release of [blackjack4494/yt-dlc](https://github.com/blackjack4494/yt-dlc) are:

* **[SponSkrub Integration](#sponskrub-sponsorblock-options)**: You can use [SponSkrub](https://github.com/yt-dlp/SponSkrub) to mark/remove sponsor sections in youtube videos by utilizing the [SponsorBlock](https://sponsor.ajay.app) API

* **[Format Sorting](#sorting-formats)**: The default format sorting options have been changed so that higher resolution and better codecs will be now preferred instead of simply using larger bitrate. Furthermore, you can now specify the sort order using `-S`. This allows for much easier format selection that what is possible by simply using `--format` ([examples](#format-selection-examples))

* **Merged with youtube-dl [commit/a726009](https://github.com/ytdl-org/youtube-dl/commit/a7260099873acc6dc7d76cafad2f6b139087afd0)**: (v2021.04.26) You get all the latest features and patches of [youtube-dl](https://github.com/ytdl-org/youtube-dl) in addition to all the features of [youtube-dlc](https://github.com/blackjack4494/yt-dlc)

* **Merged with animelover1984/youtube-dl**: You get most of the features and improvements from [animelover1984/youtube-dl](https://github.com/animelover1984/youtube-dl) including `--get-comments`, `BiliBiliSearch`, `BilibiliChannel`, Embedding thumbnail in mp4/ogg/opus, playlist infojson etc. Note that the NicoNico improvements are not available. See [#31](https://github.com/yt-dlp/yt-dlp/pull/31) for details.

* **Youtube improvements**:
    * All Youtube Feeds (`:ytfav`, `:ytwatchlater`, `:ytsubs`, `:ythistory`, `:ytrec`) works and supports downloading multiple pages of content
    * Youtube search (`ytsearch:`, `ytsearchdate:`) along with Search URLs work
    * Youtube mixes supports downloading multiple pages of content
    * Redirect channel's home URL automatically to `/video` to preserve the old behaviour

* **Split video by chapters**: Videos can be split into multiple files based on chapters using `--split-chapters`

* **Multi-threaded fragment downloads**: Download multiple fragments of m3u8/mpd videos in parallel. Use `--concurrent-fragments` (`-N`) option to set the number of threads used

* **Aria2c with HLS/DASH**: You can use `aria2c` as the external downloader for DASH(mpd) and HLS(m3u8) formats

* **New extractors**: AnimeLab, Philo MSO, Rcs, Gedi, bitwave.tv, mildom, audius, zee5, mtv.it, wimtv, pluto.tv, niconico users, discoveryplus.in, mediathek, NFHSNetwork, nebula, ukcolumn, whowatch, MxplayerShow

* **Fixed extractors**: archive.org, roosterteeth.com, skyit, instagram, itv, SouthparkDe, spreaker, Vlive, akamai, ina, rumble, tennistv, amcnetworks, la7 podcasts, linuxacadamy, nitter, twitcasting, viu, crackle, curiositystream, mediasite, rmcdecouverte, sonyliv, tubi

* **Subtitle extraction from manifests**: Subtitles can be extracted from streaming media manifests. See [be6202f12b97858b9d716e608394b51065d0419f](https://github.com/yt-dlp/yt-dlp/commit/be6202f12b97858b9d716e608394b51065d0419f) for details

* **Multiple paths and output templates**: You can give different [output templates](#output-template) and download paths for different types of files. You can also set a temporary path where intermediary files are downloaded to using `--paths` (`-P`)

* **Portable Configuration**: Configuration files are automatically loaded from the home and root directories. See [configuration](#configuration) for details

* **Output template improvements**: Output templates can now have date-time formatting, numeric offsets, object traversal etc. See [output template](#output-template) for details. Even more advanced operations can also be done with the help of `--parse-metadata`

* **Other new options**: `--sleep-requests`, `--convert-thumbnails`, `--write-link`, `--force-download-archive`, `--force-overwrites`, `--break-on-reject` etc

* **Improvements**: Multiple `--postprocessor-args` and `--downloader-args`, faster archive checking, more [format selection options](#format-selection) etc

* **Plugin extractors**: Extractors can be loaded from an external file. See [plugins](#plugins) for details

* **Self-updater**: The releases can be updated using `yt-dlp -U`


See [changelog](Changelog.md) or [commits](https://github.com/yt-dlp/yt-dlp/commits) for the full list of changes


**PS**: Some of these changes are already in youtube-dlc, but are still unreleased. See [this](Changelog.md#unreleased-changes-in-blackjack4494yt-dlc) for details

If you are coming from [youtube-dl](https://github.com/ytdl-org/youtube-dl), the amount of changes are very large. Compare [options](#options) and [supported sites](supportedsites.md) with youtube-dl's to get an idea of the massive number of features/patches [youtube-dlc](https://github.com/blackjack4494/yt-dlc) has accumulated.

### Differences in default behavior

Some of yt-dlp's default options are different from that of youtube-dl and youtube-dlc.

1. The options `--id`, `--auto-number` (`-A`), `--title` (`-t`) and `--literal` (`-l`), no longer work. See [removed options](#Removed) for details
1. `avconv` is not supported as as an alternative to `ffmpeg`
1. The default [output template](#output-template) is `%(title)s [%(id)s].%(ext)s`. There is no real reason for this change. This was changed before yt-dlp was ever made public and now there are no plans to change it back to `%(title)s.%(id)s.%(ext)s`. Instead, you may use `--compat-options filename`
1. The default [format sorting](sorting-formats) is different from youtube-dl and prefers higher resolution and better codecs rather than higher bitrates. You can use the `--format-sort` option to change this to any order you prefer, or use `--compat-options format-sort` to use youtube-dl's sorting order
1. The default format selector is `bv*+ba/b`. This means that if a combined video + audio format that is better than the best video-only format is found, the former will be prefered. Use `-f bv+ba/b` or `--compat-options format-spec` to revert this
1. Unlike youtube-dlc, yt-dlp does not allow merging multiple audio/video streams into one file by default (since this conflicts with the use of `-f bv*+ba`). If needed, this feature must be enabled using `--audio-multistreams` and `--video-multistreams`. You can also use `--compat-options multistreams` to enable both
1. `--ignore-errors` is enabled by default. Use `--abort-on-error` or `--compat-options abort-on-error` to abort on errors instead
1. When writing metadata files such as thumbnails, description or infojson, the same information (if available) is also written for playlists. Use `--no-write-playlist-metafiles` or `--compat-options no-playlist-metafiles` to not write these files
1. `--add-metadata` attaches the `infojson` to `mkv` files in addition to writing the metadata when used with `--write-infojson`. Use `--compat-options no-attach-info-json` to revert this
1. `playlist_index` behaves differently when used with options like `--playlist-reverse` and `--playlist-items`. See [#302](https://github.com/yt-dlp/yt-dlp/issues/302) for details. You can use `--compat-options playlist-index` if you want to keep the earlier behavior
1. The output of `-F` is listed in a new format. Use `--compat-options list-formats` to revert this
1. Youtube live chat (if available) is considered as a subtitle. Use `--sub-langs all,-live_chat` to download all subtitles except live chat. You can also use `--compat-options no-live-chat` to prevent live chat from downloading
1. Youtube channel URLs are automatically redirected to `/video`. Either append a `/featured` to the URL or use `--compat-options no-youtube-channel-redirect` to download only the videos in the home page
1. Unavailable videos are also listed for youtube playlists. Use `--compat-options no-youtube-unavailable-videos` to remove this

For ease of use, a few more compat options are available:
1. `--compat-options all` = Use all compat options
1. `--compat-options youtube-dl` = `--compat-options all,-multistreams`
1. `--compat-options youtube-dlc` = `--compat-options all,-no-live-chat,-no-youtube-channel-redirect`


# INSTALLATION
yt-dlp is not platform specific. So it should work on your Unix box, on Windows or on macOS

You can install yt-dlp using one of the following methods:
* Download the binary from the [latest release](https://github.com/yt-dlp/yt-dlp/releases/latest) (recommended method)
* Use [PyPI package](https://pypi.org/project/yt-dlp): `python3 -m pip install --upgrade yt-dlp`
* Use pip+git: `python3 -m pip install --upgrade git+https://github.com/yt-dlp/yt-dlp.git@release`
* Install master branch: `python3 -m pip install --upgrade git+https://github.com/yt-dlp/yt-dlp`

Note that on some systems, you may need to use `py` or `python` instead of `python3`

UNIX users (Linux, macOS, BSD) can also install the [latest release](https://github.com/yt-dlp/yt-dlp/releases/latest) one of the following ways:

```
sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp
```

```
sudo wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp
```

```
sudo aria2c https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
sudo chmod a+rx /usr/local/bin/yt-dlp
```

### DEPENDENCIES
Python versions 3.6+ (CPython and PyPy) are officially supported. Other versions and implementations may or maynot work correctly.

On windows, [Microsoft Visual C++ 2010 Redistributable Package (x86)](https://www.microsoft.com/en-us/download/details.aspx?id=26999) is also necessary to run yt-dlp. You probably already have this, but if the executable throws an error due to missing `MSVCR100.dll` you need to install it.

Although there are no other required dependencies, `ffmpeg` and `ffprobe` are highly recommended. Other optional dependencies are `sponskrub`, `AtomicParsley`, `mutagen`, `pycryptodome` and any of the supported external downloaders. Note that the windows releases are already built with the python interpreter, mutagen and pycryptodome included.

### UPDATE
You can use `yt-dlp -U` to update if you are using the provided release.
If you are using `pip`, simply re-run the same command that was used to install the program.

### COMPILE

**For Windows**:
To build the Windows executable, you must have pyinstaller (and optionally mutagen and pycryptodome)

    python3 -m pip install --upgrade pyinstaller mutagen pycryptodome

Once you have all the necessary dependencies installed, just run `py pyinst.py`. The executable will be built for the same architecture (32/64 bit) as the python used to build it.

You can also build the executable without any version info or metadata by using:

    pyinstaller.exe yt_dlp\__main__.py --onefile --name yt-dlp
    
Note that pyinstaller [does not support](https://github.com/pyinstaller/pyinstaller#requirements-and-tested-platforms) Python installed from the Windows store without using a virtual environment

**For Unix**:
You will need the required build tools: `python`, `make` (GNU), `pandoc`, `zip`, `nosetests`  
Then simply run `make`. You can also run `make yt-dlp` instead to compile only the binary without updating any of the additional files

**Note**: In either platform, `devscripts\update-version.py` can be used to automatically update the version number

# USAGE AND OPTIONS

    yt-dlp [OPTIONS] [--] URL [URL...]

`Ctrl+F` is your friend :D
<!-- Auto generated -->

## General Options:
    -h, --help                       Print this help text and exit
    --version                        Print program version and exit
    -U, --update                     Update this program to latest version. Make
                                     sure that you have sufficient permissions
                                     (run with sudo if needed)
    -i, --ignore-errors              Continue on download errors, for example to
                                     skip unavailable videos in a playlist
                                     (default) (Alias: --no-abort-on-error)
    --abort-on-error                 Abort downloading of further videos if an
                                     error occurs (Alias: --no-ignore-errors)
    --dump-user-agent                Display the current browser identification
    --list-extractors                List all supported extractors
    --extractor-descriptions         Output descriptions of all supported
                                     extractors
    --force-generic-extractor        Force extraction to use the generic
                                     extractor
    --default-search PREFIX          Use this prefix for unqualified URLs. For
                                     example "gvsearch2:" downloads two videos
                                     from google videos for youtube-dl "large
                                     apple". Use the value "auto" to let
                                     youtube-dl guess ("auto_warning" to emit a
                                     warning when guessing). "error" just throws
                                     an error. The default value "fixup_error"
                                     repairs broken URLs, but emits an error if
                                     this is not possible instead of searching
    --ignore-config, --no-config     Disable loading any configuration files
                                     except the one provided by --config-location.
                                     When given inside a configuration
                                     file, no further configuration files are
                                     loaded. Additionally, (for backward
                                     compatibility) if this option is found
                                     inside the system configuration file, the
                                     user configuration is not loaded
    --config-location PATH           Location of the main configuration file;
                                     either the path to the config or its
                                     containing directory
    --flat-playlist                  Do not extract the videos of a playlist,
                                     only list them
    --no-flat-playlist               Extract the videos of a playlist
    --mark-watched                   Mark videos watched (YouTube only)
    --no-mark-watched                Do not mark videos watched (default)
    --no-colors                      Do not emit color codes in output
    --compat-options OPTS            Options that can help keep compatibility
                                     with youtube-dl and youtube-dlc
                                     configurations by reverting some of the
                                     changes made in yt-dlp. See "Differences in
                                     default behavior" for details

## Network Options:
    --proxy URL                      Use the specified HTTP/HTTPS/SOCKS proxy.
                                     To enable SOCKS proxy, specify a proper
                                     scheme. For example
                                     socks5://127.0.0.1:1080/. Pass in an empty
                                     string (--proxy "") for direct connection
    --socket-timeout SECONDS         Time to wait before giving up, in seconds
    --source-address IP              Client-side IP address to bind to
    -4, --force-ipv4                 Make all connections via IPv4
    -6, --force-ipv6                 Make all connections via IPv6

## Geo-restriction:
    --geo-verification-proxy URL     Use this proxy to verify the IP address for
                                     some geo-restricted sites. The default
                                     proxy specified by --proxy (or none, if the
                                     option is not present) is used for the
                                     actual downloading
    --geo-bypass                     Bypass geographic restriction via faking
                                     X-Forwarded-For HTTP header
    --no-geo-bypass                  Do not bypass geographic restriction via
                                     faking X-Forwarded-For HTTP header
    --geo-bypass-country CODE        Force bypass geographic restriction with
                                     explicitly provided two-letter ISO 3166-2
                                     country code
    --geo-bypass-ip-block IP_BLOCK   Force bypass geographic restriction with
                                     explicitly provided IP block in CIDR
                                     notation

## Video Selection:
    --playlist-start NUMBER          Playlist video to start at (default is 1)
    --playlist-end NUMBER            Playlist video to end at (default is last)
    --playlist-items ITEM_SPEC       Playlist video items to download. Specify
                                     indices of the videos in the playlist
                                     separated by commas like: "--playlist-items
                                     1,2,5,8" if you want to download videos
                                     indexed 1, 2, 5, 8 in the playlist. You can
                                     specify range: "--playlist-items
                                     1-3,7,10-13", it will download the videos
                                     at index 1, 2, 3, 7, 10, 11, 12 and 13
    --match-title REGEX              Download only matching titles (regex or
                                     caseless sub-string)
    --reject-title REGEX             Skip download for matching titles (regex or
                                     caseless sub-string)
    --max-downloads NUMBER           Abort after downloading NUMBER files
    --min-filesize SIZE              Do not download any videos smaller than
                                     SIZE (e.g. 50k or 44.6m)
    --max-filesize SIZE              Do not download any videos larger than SIZE
                                     (e.g. 50k or 44.6m)
    --date DATE                      Download only videos uploaded in this date.
                                     The date can be "YYYYMMDD" or in the format
                                     "(now|today)[+-][0-9](day|week|month|year)(s)?"
    --datebefore DATE                Download only videos uploaded on or before
                                     this date. The date formats accepted is the
                                     same as --date
    --dateafter DATE                 Download only videos uploaded on or after
                                     this date. The date formats accepted is the
                                     same as --date
    --min-views COUNT                Do not download any videos with less than
                                     COUNT views
    --max-views COUNT                Do not download any videos with more than
                                     COUNT views
    --match-filter FILTER            Generic video filter. Specify any key (see
                                     "OUTPUT TEMPLATE" for a list of available
                                     keys) to match if the key is present, !key
                                     to check if the key is not present,
                                     key>NUMBER (like "view_count > 12", also
                                     works with >=, <, <=, !=, =) to compare
                                     against a number, key = 'LITERAL' (like
                                     "uploader = 'Mike Smith'", also works with
                                     !=) to match against a string literal and &
                                     to require multiple matches. Values which
                                     are not known are excluded unless you put a
                                     question mark (?) after the operator. For
                                     example, to only match videos that have
                                     been liked more than 100 times and disliked
                                     less than 50 times (or the dislike
                                     functionality is not available at the given
                                     service), but who also have a description,
                                     use --match-filter "like_count > 100 &
                                     dislike_count <? 50 & description"
    --no-match-filter                Do not use generic video filter (default)
    --no-playlist                    Download only the video, if the URL refers
                                     to a video and a playlist
    --yes-playlist                   Download the playlist, if the URL refers to
                                     a video and a playlist
    --age-limit YEARS                Download only videos suitable for the given
                                     age
    --download-archive FILE          Download only videos not listed in the
                                     archive file. Record the IDs of all
                                     downloaded videos in it
    --break-on-existing              Stop the download process when encountering
                                     a file that is in the archive
    --break-on-reject                Stop the download process when encountering
                                     a file that has been filtered out
    --skip-playlist-after-errors N   Number of allowed failures until the rest
                                     of the playlist is skipped
    --no-download-archive            Do not use archive file (default)

## Download Options:
    -N, --concurrent-fragments N     Number of fragments of a dash/hlsnative
                                     video that should be download concurrently
                                     (default is 1)
    -r, --limit-rate RATE            Maximum download rate in bytes per second
                                     (e.g. 50K or 4.2M)
    -R, --retries RETRIES            Number of retries (default is 10), or
                                     "infinite"
    --fragment-retries RETRIES       Number of retries for a fragment (default
                                     is 10), or "infinite" (DASH, hlsnative and
                                     ISM)
    --skip-unavailable-fragments     Skip unavailable fragments for DASH,
                                     hlsnative and ISM (default)
                                     (Alias: --no-abort-on-unavailable-fragment)
    --abort-on-unavailable-fragment  Abort downloading if a fragment is unavailable
                                     (Alias: --no-skip-unavailable-fragments)
    --keep-fragments                 Keep downloaded fragments on disk after
                                     downloading is finished
    --no-keep-fragments              Delete downloaded fragments after
                                     downloading is finished (default)
    --buffer-size SIZE               Size of download buffer (e.g. 1024 or 16K)
                                     (default is 1024)
    --resize-buffer                  The buffer size is automatically resized
                                     from an initial value of --buffer-size
                                     (default)
    --no-resize-buffer               Do not automatically adjust the buffer size
    --http-chunk-size SIZE           Size of a chunk for chunk-based HTTP
                                     downloading (e.g. 10485760 or 10M) (default
                                     is disabled). May be useful for bypassing
                                     bandwidth throttling imposed by a webserver
                                     (experimental)
    --playlist-reverse               Download playlist videos in reverse order
    --no-playlist-reverse            Download playlist videos in default order
                                     (default)
    --playlist-random                Download playlist videos in random order
    --xattr-set-filesize             Set file xattribute ytdl.filesize with
                                     expected file size
    --hls-use-mpegts                 Use the mpegts container for HLS videos;
                                     allowing some players to play the video
                                     while downloading, and reducing the chance
                                     of file corruption if download is
                                     interrupted. This is enabled by default for
                                     live streams
    --no-hls-use-mpegts              Do not use the mpegts container for HLS
                                     videos. This is default when not
                                     downloading live streams
    --downloader [PROTO:]NAME        Name or path of the external downloader to
                                     use (optionally) prefixed by the protocols
                                     (http, ftp, m3u8, dash, rstp, rtmp, mms) to
                                     use it for. Currently supports native,
                                     aria2c, avconv, axel, curl, ffmpeg, httpie,
                                     wget (Recommended: aria2c). You can use
                                     this option multiple times to set different
                                     downloaders for different protocols. For
                                     example, --downloader aria2c --downloader
                                     "dash,m3u8:native" will use aria2c for
                                     http/ftp downloads, and the native
                                     downloader for dash/m3u8 downloads
                                     (Alias: --external-downloader)
    --downloader-args NAME:ARGS      Give these arguments to the external
                                     downloader. Specify the downloader name and
                                     the arguments separated by a colon ":". You
                                     can use this option multiple times
                                     (Alias: --external-downloader-args)

## Filesystem Options:
    -a, --batch-file FILE            File containing URLs to download ('-' for
                                     stdin), one URL per line. Lines starting
                                     with '#', ';' or ']' are considered as
                                     comments and ignored
    -P, --paths TYPES:PATH           The paths where the files should be
                                     downloaded. Specify the type of file and
                                     the path separated by a colon ":". All the
                                     same types as --output are supported.
                                     Additionally, you can also provide "home"
                                     and "temp" paths. All intermediary files
                                     are first downloaded to the temp path and
                                     then the final files are moved over to the
                                     home path after download is finished. This
                                     option is ignored if --output is an
                                     absolute path
    -o, --output [TYPES:]TEMPLATE    Output filename template; see "OUTPUT
                                     TEMPLATE" for details
    --output-na-placeholder TEXT     Placeholder value for unavailable meta
                                     fields in output filename template
                                     (default: "NA")
    --restrict-filenames             Restrict filenames to only ASCII
                                     characters, and avoid "&" and spaces in
                                     filenames
    --no-restrict-filenames          Allow Unicode characters, "&" and spaces in
                                     filenames (default)
    --windows-filenames              Force filenames to be windows compatible
    --no-windows-filenames           Make filenames windows compatible only if
                                     using windows (default)
    --trim-filenames LENGTH          Limit the filename length (excluding
                                     extension) to the specified number of
                                     characters
    -w, --no-overwrites              Do not overwrite any files
    --force-overwrites               Overwrite all video and metadata files.
                                     This option includes --no-continue
    --no-force-overwrites            Do not overwrite the video, but overwrite
                                     related files (default)
    -c, --continue                   Resume partially downloaded files/fragments
                                     (default)
    --no-continue                    Do not resume partially downloaded
                                     fragments. If the file is not fragmented,
                                     restart download of the entire file
    --part                           Use .part files instead of writing directly
                                     into output file (default)
    --no-part                        Do not use .part files - write directly
                                     into output file
    --mtime                          Use the Last-modified header to set the
                                     file modification time (default)
    --no-mtime                       Do not use the Last-modified header to set
                                     the file modification time
    --write-description              Write video description to a .description
                                     file
    --no-write-description           Do not write video description (default)
    --write-info-json                Write video metadata to a .info.json file
                                     (this may contain personal information)
    --no-write-info-json             Do not write video metadata (default)
    --write-annotations              Write video annotations to a
                                     .annotations.xml file
    --no-write-annotations           Do not write video annotations (default)
    --write-playlist-metafiles       Write playlist metadata in addition to the
                                     video metadata when using --write-info-json,
                                     --write-description etc. (default)
    --no-write-playlist-metafiles    Do not write playlist metadata when using
                                     --write-info-json, --write-description etc.
    --clean-infojson                 Remove some private fields such as
                                     filenames from the infojson. Note that it
                                     could still contain some personal
                                     information (default)
    --no-clean-infojson              Write all fields to the infojson
    --get-comments                   Retrieve video comments to be placed in the
                                     .info.json file. The comments are fetched
                                     even without this option if the extraction
                                     is known to be quick
    --load-info-json FILE            JSON file containing the video information
                                     (created with the "--write-info-json"
                                     option)
    --cookies FILE                   File to read cookies from and dump cookie
                                     jar in
    --no-cookies                     Do not read/dump cookies (default)
    --cache-dir DIR                  Location in the filesystem where youtube-dl
                                     can store some downloaded information
                                     permanently. By default
                                     $XDG_CACHE_HOME/youtube-dl or
                                     ~/.cache/youtube-dl . At the moment, only
                                     YouTube player files (for videos with
                                     obfuscated signatures) are cached, but that
                                     may change
    --no-cache-dir                   Disable filesystem caching
    --rm-cache-dir                   Delete all filesystem cache files

## Thumbnail Options:
    --write-thumbnail                Write thumbnail image to disk
    --no-write-thumbnail             Do not write thumbnail image to disk
                                     (default)
    --write-all-thumbnails           Write all thumbnail image formats to disk
    --list-thumbnails                Simulate and list all available thumbnail
                                     formats

## Internet Shortcut Options:
    --write-link                     Write an internet shortcut file, depending
                                     on the current platform (.url, .webloc or
                                     .desktop). The URL may be cached by the OS
    --write-url-link                 Write a .url Windows internet shortcut. The
                                     OS caches the URL based on the file path
    --write-webloc-link              Write a .webloc macOS internet shortcut
    --write-desktop-link             Write a .desktop Linux internet shortcut

## Verbosity and Simulation Options:
    -q, --quiet                      Activate quiet mode
    --no-warnings                    Ignore warnings
    -s, --simulate                   Do not download the video and do not write
                                     anything to disk
    --ignore-no-formats-error        Ignore "No video formats" error. Usefull
                                     for extracting metadata even if the video
                                     is not actually available for download
                                     (experimental)
    --no-ignore-no-formats-error     Throw error when no downloadable video
                                     formats are found (default)
    --skip-download                  Do not download the video but write all
                                     related files (Alias: --no-download)
    -O, --print TEMPLATE             Simulate, quiet but print the given fields.
                                     Either a field name or similar formatting
                                     as the output template can be used
    -j, --dump-json                  Simulate, quiet but print JSON information.
                                     See "OUTPUT TEMPLATE" for a description of
                                     available keys
    -J, --dump-single-json           Simulate, quiet but print JSON information
                                     for each command-line argument. If the URL
                                     refers to a playlist, dump the whole
                                     playlist information in a single line
    --print-json                     Be quiet and print the video information as
                                     JSON (video is still being downloaded)
    --force-write-archive            Force download archive entries to be
                                     written as far as no errors occur, even if
                                     -s or another simulation option is used
                                     (Alias: --force-download-archive)
    --newline                        Output progress bar as new lines
    --no-progress                    Do not print progress bar
    --console-title                  Display progress in console titlebar
    -v, --verbose                    Print various debugging information
    --dump-pages                     Print downloaded pages encoded using base64
                                     to debug problems (very verbose)
    --write-pages                    Write downloaded intermediary pages to
                                     files in the current directory to debug
                                     problems
    --print-traffic                  Display sent and read HTTP traffic

## Workarounds:
    --encoding ENCODING              Force the specified encoding (experimental)
    --no-check-certificate           Suppress HTTPS certificate validation
    --prefer-insecure                Use an unencrypted connection to retrieve
                                     information about the video (Currently
                                     supported only for YouTube)
    --user-agent UA                  Specify a custom user agent
    --referer URL                    Specify a custom referer, use if the video
                                     access is restricted to one domain
    --add-header FIELD:VALUE         Specify a custom HTTP header and its value,
                                     separated by a colon ":". You can use this
                                     option multiple times
    --bidi-workaround                Work around terminals that lack
                                     bidirectional text support. Requires bidiv
                                     or fribidi executable in PATH
    --sleep-requests SECONDS         Number of seconds to sleep between requests
                                     during data extraction
    --sleep-interval SECONDS         Number of seconds to sleep before each
                                     download. This is the minimum time to sleep
                                     when used along with --max-sleep-interval
                                     (Alias: --min-sleep-interval)
    --max-sleep-interval SECONDS     Maximum number of seconds to sleep. Can
                                     only be used along with --min-sleep-interval
    --sleep-subtitles SECONDS        Number of seconds to sleep before each
                                     subtitle download

## Video Format Options:
    -f, --format FORMAT              Video format code, see "FORMAT SELECTION"
                                     for more details
    -S, --format-sort SORTORDER      Sort the formats by the fields given, see
                                     "Sorting Formats" for more details
    --S-force, --format-sort-force   Force user specified sort order to have
                                     precedence over all fields, see "Sorting
                                     Formats" for more details
    --no-format-sort-force           Some fields have precedence over the user
                                     specified sort order (default), see
                                     "Sorting Formats" for more details
    --video-multistreams             Allow multiple video streams to be merged
                                     into a single file
    --no-video-multistreams          Only one video stream is downloaded for
                                     each output file (default)
    --audio-multistreams             Allow multiple audio streams to be merged
                                     into a single file
    --no-audio-multistreams          Only one audio stream is downloaded for
                                     each output file (default)
    --prefer-free-formats            Prefer video formats with free containers
                                     over non-free ones of same quality. Use
                                     with "-S ext" to strictly prefer free
                                     containers irrespective of quality
    --no-prefer-free-formats         Don't give any special preference to free
                                     containers (default)
    --check-formats                  Check that the formats selected are
                                     actually downloadable (Experimental)
    -F, --list-formats               List all available formats of requested
                                     videos
    --merge-output-format FORMAT     If a merge is required (e.g.
                                     bestvideo+bestaudio), output to given
                                     container format. One of mkv, mp4, ogg,
                                     webm, flv. Ignored if no merge is required
    --allow-unplayable-formats       Allow unplayable formats to be listed and
                                     downloaded. All video post-processing will
                                     also be turned off
    --no-allow-unplayable-formats    Do not allow unplayable formats to be
                                     listed or downloaded (default)

## Subtitle Options:
    --write-subs                     Write subtitle file
    --no-write-subs                  Do not write subtitle file (default)
    --write-auto-subs                Write automatically generated subtitle file
                                     (Alias: --write-automatic-subs)
    --no-write-auto-subs             Do not write auto-generated subtitles
                                     (default) (Alias: --no-write-automatic-subs)
    --list-subs                      List all available subtitles for the video
    --sub-format FORMAT              Subtitle format, accepts formats
                                     preference, for example: "srt" or
                                     "ass/srt/best"
    --sub-langs LANGS                Languages of the subtitles to download (can
                                     be regex) or "all" separated by commas.
                                     (Eg: --sub-langs en.*,ja) You can prefix
                                     the language code with a "-" to exempt it
                                     from the requested languages. (Eg: --sub-
                                     langs all,-live_chat) Use --list-subs for a
                                     list of available language tags

## Authentication Options:
    -u, --username USERNAME          Login with this account ID
    -p, --password PASSWORD          Account password. If this option is left
                                     out, yt-dlp will ask interactively
    -2, --twofactor TWOFACTOR        Two-factor authentication code
    -n, --netrc                      Use .netrc authentication data
    --video-password PASSWORD        Video password (vimeo, youku)
    --ap-mso MSO                     Adobe Pass multiple-system operator (TV
                                     provider) identifier, use --ap-list-mso for
                                     a list of available MSOs
    --ap-username USERNAME           Multiple-system operator account login
    --ap-password PASSWORD           Multiple-system operator account password.
                                     If this option is left out, yt-dlp will ask
                                     interactively
    --ap-list-mso                    List all supported multiple-system
                                     operators

## Post-Processing Options:
    -x, --extract-audio              Convert video files to audio-only files
                                     (requires ffmpeg and ffprobe)
    --audio-format FORMAT            Specify audio format: "best", "aac",
                                     "flac", "mp3", "m4a", "opus", "vorbis", or
                                     "wav"; "best" by default; No effect without
                                     -x
    --audio-quality QUALITY          Specify ffmpeg audio quality, insert a
                                     value between 0 (better) and 9 (worse) for
                                     VBR or a specific bitrate like 128K
                                     (default 5)
    --remux-video FORMAT             Remux the video into another container if
                                     necessary (currently supported: mp4|mkv|flv
                                     |webm|mov|avi|mp3|mka|m4a|ogg|opus). If
                                     target container does not support the
                                     video/audio codec, remuxing will fail. You
                                     can specify multiple rules; eg.
                                     "aac>m4a/mov>mp4/mkv" will remux aac to
                                     m4a, mov to mp4 and anything else to mkv.
    --recode-video FORMAT            Re-encode the video into another format if
                                     re-encoding is necessary. The supported
                                     formats are the same as --remux-video
    --postprocessor-args NAME:ARGS   Give these arguments to the postprocessors.
                                     Specify the postprocessor/executable name
                                     and the arguments separated by a colon ":"
                                     to give the argument to the specified
                                     postprocessor/executable. Supported PP are:
                                     Merger, ExtractAudio, SplitChapters,
                                     Metadata, EmbedSubtitle, EmbedThumbnail,
                                     SubtitlesConvertor, ThumbnailsConvertor,
                                     VideoRemuxer, VideoConvertor, SponSkrub,
                                     FixupStretched, FixupM4a and FixupM3u8. The
                                     supported executables are: AtomicParsley,
                                     FFmpeg, FFprobe, and SponSkrub. You can
                                     also specify "PP+EXE:ARGS" to give the
                                     arguments to the specified executable only
                                     when being used by the specified
                                     postprocessor. Additionally, for
                                     ffmpeg/ffprobe, "_i"/"_o" can be appended
                                     to the prefix optionally followed by a
                                     number to pass the argument before the
                                     specified input/output file. Eg: --ppa
                                     "Merger+ffmpeg_i1:-v quiet". You can use
                                     this option multiple times to give
                                     different arguments to different
                                     postprocessors. (Alias: --ppa)
    -k, --keep-video                 Keep the intermediate video file on disk
                                     after post-processing
    --no-keep-video                  Delete the intermediate video file after
                                     post-processing (default)
    --post-overwrites                Overwrite post-processed files (default)
    --no-post-overwrites             Do not overwrite post-processed files
    --embed-subs                     Embed subtitles in the video (only for mp4,
                                     webm and mkv videos)
    --no-embed-subs                  Do not embed subtitles (default)
    --embed-thumbnail                Embed thumbnail in the audio as cover art
    --no-embed-thumbnail             Do not embed thumbnail (default)
    --add-metadata                   Write metadata to the video file
    --no-add-metadata                Do not write metadata (default)
    --parse-metadata FROM:TO         Parse additional metadata like title/artist
                                     from other fields; see "MODIFYING METADATA"
                                     for details
    --xattrs                         Write metadata to the video file's xattrs
                                     (using dublin core and xdg standards)
    --fixup POLICY                   Automatically correct known faults of the
                                     file. One of never (do nothing), warn (only
                                     emit a warning), detect_or_warn (the
                                     default; fix file if we can, warn
                                     otherwise)
    --ffmpeg-location PATH           Location of the ffmpeg binary; either the
                                     path to the binary or its containing
                                     directory
    --exec CMD                       Execute a command on the file after
                                     downloading and post-processing. Similar
                                     syntax to the output template can be used
                                     to pass any field as arguments to the
                                     command. An additional field "filepath"
                                     that contains the final path of the
                                     downloaded file is also available. If no
                                     fields are passed, "%(filepath)s" is
                                     appended to the end of the command
    --convert-subs FORMAT            Convert the subtitles to another format
                                     (currently supported: srt|ass|vtt|lrc)
                                     (Alias: --convert-subtitles)
    --convert-thumbnails FORMAT      Convert the thumbnails to another format
                                     (currently supported: jpg)
    --split-chapters                 Split video into multiple files based on
                                     internal chapters. The "chapter:" prefix
                                     can be used with "--paths" and "--output"
                                     to set the output filename for the split
                                     files. See "OUTPUT TEMPLATE" for details
    --no-split-chapters              Do not split video based on chapters
                                     (default)

## SponSkrub (SponsorBlock) Options:
[SponSkrub](https://github.com/yt-dlp/SponSkrub) is a utility to
    mark/remove sponsor segments from downloaded YouTube videos using
    [SponsorBlock API](https://sponsor.ajay.app)

    --sponskrub                      Use sponskrub to mark sponsored sections.
                                     This is enabled by default if the sponskrub
                                     binary exists (Youtube only)
    --no-sponskrub                   Do not use sponskrub
    --sponskrub-cut                  Cut out the sponsor sections instead of
                                     simply marking them
    --no-sponskrub-cut               Simply mark the sponsor sections, not cut
                                     them out (default)
    --sponskrub-force                Run sponskrub even if the video was already
                                     downloaded
    --no-sponskrub-force             Do not cut out the sponsor sections if the
                                     video was already downloaded (default)
    --sponskrub-location PATH        Location of the sponskrub binary; either
                                     the path to the binary or its containing
                                     directory

## Extractor Options:
    --extractor-retries RETRIES      Number of retries for known extractor
                                     errors (default is 3), or "infinite"
    --allow-dynamic-mpd              Process dynamic DASH manifests (default)
                                     (Alias: --no-ignore-dynamic-mpd)
    --ignore-dynamic-mpd             Do not process dynamic DASH manifests
                                     (Alias: --no-allow-dynamic-mpd)
    --hls-split-discontinuity        Split HLS playlists to different formats at
                                     discontinuities such as ad breaks
    --no-hls-split-discontinuity     Do not split HLS playlists to different
                                     formats at discontinuities such as ad
                                     breaks (default)
    --youtube-include-dash-manifest  Download the DASH manifests and related
                                     data on YouTube videos (default)
                                     (Alias: --no-youtube-skip-dash-manifest)
    --youtube-skip-dash-manifest     Do not download the DASH manifests and
                                     related data on YouTube videos
                                     (Alias: --no-youtube-include-dash-manifest)
    --youtube-include-hls-manifest   Download the HLS manifests and related data
                                     on YouTube videos (default)
                                     (Alias: --no-youtube-skip-hls-manifest)
    --youtube-skip-hls-manifest      Do not download the HLS manifests and
                                     related data on YouTube videos
                                     (Alias: --no-youtube-include-hls-manifest)

# CONFIGURATION

You can configure yt-dlp by placing any supported command line option to a configuration file. The configuration is loaded from the following locations:

1. **Main Configuration**: The file given by `--config-location`
1. **Portable Configuration**: `yt-dlp.conf` in the same directory as the bundled binary. If you are running from source-code (`<root dir>/yt_dlp/__main__.py`), the root directory is used instead.
1. **Home Configuration**: `yt-dlp.conf` in the home path given by `-P "home:<path>"`, or in the current directory if no such path is given
1. **User Configuration**:
    * `%XDG_CONFIG_HOME%/yt-dlp/config` (recommended on Linux/macOS)
    * `%XDG_CONFIG_HOME%/yt-dlp.conf`
    * `%APPDATA%/yt-dlp/config` (recommended on Windows)
    * `%APPDATA%/yt-dlp/config.txt`
    * `~/yt-dlp.conf`
    * `~/yt-dlp.conf.txt`

    Note that `~` points to `C:\Users\<user name>` on windows. Also, `%XDG_CONFIG_HOME%` defaults to `~/.config` if undefined
1. **System Configuration**: `/etc/yt-dlp.conf` or `/etc/yt-dlp.conf`

For example, with the following configuration file yt-dlp will always extract the audio, not copy the mtime, use a proxy and save all videos under `YouTube` directory in your home directory:
```
# Lines starting with # are comments

# Always extract audio
-x

# Do not copy the mtime
--no-mtime

# Use this proxy
--proxy 127.0.0.1:3128

# Save all videos under YouTube directory in your home directory
-o ~/YouTube/%(title)s.%(ext)s
```

Note that options in configuration file are just the same options aka switches used in regular command line calls; thus there **must be no whitespace** after `-` or `--`, e.g. `-o` or `--proxy` but not `- o` or `-- proxy`.

You can use `--ignore-config` if you want to disable all configuration files for a particular yt-dlp run. If `--ignore-config` is found inside any configuration file, no further configuration will be loaded. For example, having the option in the portable configuration file prevents loading of user and system configurations. Additionally, (for backward compatibility) if `--ignore-config` is found inside the system configuration file, the user configuration is not loaded.

### Authentication with `.netrc` file

You may also want to configure automatic credentials storage for extractors that support authentication (by providing login and password with `--username` and `--password`) in order not to pass credentials as command line arguments on every yt-dlp execution and prevent tracking plain text passwords in the shell command history. You can achieve this using a [`.netrc` file](https://stackoverflow.com/tags/.netrc/info) on a per extractor basis. For that you will need to create a `.netrc` file in your `$HOME` and restrict permissions to read/write by only you:
```
touch $HOME/.netrc
chmod a-rwx,u+rw $HOME/.netrc
```
After that you can add credentials for an extractor in the following format, where *extractor* is the name of the extractor in lowercase:
```
machine <extractor> login <login> password <password>
```
For example:
```
machine youtube login myaccount@gmail.com password my_youtube_password
machine twitch login my_twitch_account_name password my_twitch_password
```
To activate authentication with the `.netrc` file you should pass `--netrc` to yt-dlp or place it in the [configuration file](#configuration).

On Windows you may also need to setup the `%HOME%` environment variable manually. For example:
```
set HOME=%USERPROFILE%
```

# OUTPUT TEMPLATE

The `-o` option is used to indicate a template for the output file names while `-P` option is used to specify the path each type of file should be saved to.

**tl;dr:** [navigate me to examples](#output-template-examples).

The simplest usage of `-o` is not to set any template arguments when downloading a single file, like in `yt-dlp -o funny_video.flv "https://some/video"` (hard-coding file extension like this is _not_ recommended and could break some post-processing).

It may however also contain special sequences that will be replaced when downloading each video. The special sequences may be formatted according to [python string formatting operations](https://docs.python.org/2/library/stdtypes.html#string-formatting). For example, `%(NAME)s` or `%(NAME)05d`. To clarify, that is a percent symbol followed by a name in parentheses, followed by formatting operations.

The field names themselves (the part inside the parenthesis) can also have some special formatting:
1. **Object traversal**: The dictionaries and lists available in metadata can be traversed by using a `.` (dot) separator. You can also do python slicing using `:`. Eg: `%(tags.0)s`, `%(subtitles.en.-1.ext)`, `%(id.3:7:-1)s`. Note that the fields that become available using this method are not listed below. Use `-j` to see such fields
1. **Addition**: Addition and subtraction of numeric fields can be done using `+` and `-` respectively. Eg: `%(playlist_index+10)03d`, `%(n_entries+1-playlist_index)d`
1. **Date/time Formatting**: Date/time fields can be formatted according to [strftime formatting](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes) by specifying it separated from the field name using a `>`. Eg: `%(duration>%H-%M-%S)s`, `%(upload_date>%Y-%m-%d)s`, `%(epoch-3600>%H-%M-%S)s`
1. **Default**: A default value can be specified for when the field is empty using a `|` seperator. This overrides `--output-na-template`. Eg: `%(uploader|Unknown)s`

To summarize, the general syntax for a field is:
```
%(name[.keys][addition][>strf][|default])[flags][width][.precision][length]type
```

Additionally, you can set different output templates for the various metadata files separately from the general output template by specifying the type of file followed by the template separated by a colon `:`. The different file types supported are `subtitle`, `thumbnail`, `description`, `annotation`, `infojson`, `pl_description`, `pl_infojson`, `chapter`. For example, `-o '%(title)s.%(ext)s' -o 'thumbnail:%(title)s\%(title)s.%(ext)s'`  will put the thumbnails in a folder with the same name as the video.

The available fields are:

 - `id` (string): Video identifier
 - `title` (string): Video title
 - `url` (string): Video URL
 - `ext` (string): Video filename extension
 - `alt_title` (string): A secondary title of the video
 - `description` (string): The description of the video
 - `display_id` (string): An alternative identifier for the video
 - `uploader` (string): Full name of the video uploader
 - `license` (string): License name the video is licensed under
 - `creator` (string): The creator of the video
 - `release_date` (string): The date (YYYYMMDD) when the video was released
 - `timestamp` (numeric): UNIX timestamp of the moment the video became available
 - `upload_date` (string): Video upload date (YYYYMMDD)
 - `uploader_id` (string): Nickname or id of the video uploader
 - `channel` (string): Full name of the channel the video is uploaded on
 - `channel_id` (string): Id of the channel
 - `location` (string): Physical location where the video was filmed
 - `duration` (numeric): Length of the video in seconds
 - `duration_string` (string): Length of the video (HH:mm:ss)
 - `view_count` (numeric): How many users have watched the video on the platform
 - `like_count` (numeric): Number of positive ratings of the video
 - `dislike_count` (numeric): Number of negative ratings of the video
 - `repost_count` (numeric): Number of reposts of the video
 - `average_rating` (numeric): Average rating give by users, the scale used depends on the webpage
 - `comment_count` (numeric): Number of comments on the video (For some extractors, comments are only downloaded at the end, and so this field cannot be used)
 - `age_limit` (numeric): Age restriction for the video (years)
 - `is_live` (boolean): Whether this video is a live stream or a fixed-length video
 - `was_live` (boolean): Whether this video was originally a live stream
 - `playable_in_embed` (string): Whether this video is allowed to play in embedded players on other sites
 - `availability` (string): Whether the video is 'private', 'premium_only', 'subscriber_only', 'needs_auth', 'unlisted' or 'public'
 - `start_time` (numeric): Time in seconds where the reproduction should start, as specified in the URL
 - `end_time` (numeric): Time in seconds where the reproduction should end, as specified in the URL
 - `format` (string): A human-readable description of the format
 - `format_id` (string): Format code specified by `--format`
 - `format_note` (string): Additional info about the format
 - `width` (numeric): Width of the video
 - `height` (numeric): Height of the video
 - `resolution` (string): Textual description of width and height
 - `tbr` (numeric): Average bitrate of audio and video in KBit/s
 - `abr` (numeric): Average audio bitrate in KBit/s
 - `acodec` (string): Name of the audio codec in use
 - `asr` (numeric): Audio sampling rate in Hertz
 - `vbr` (numeric): Average video bitrate in KBit/s
 - `fps` (numeric): Frame rate
 - `vcodec` (string): Name of the video codec in use
 - `container` (string): Name of the container format
 - `filesize` (numeric): The number of bytes, if known in advance
 - `filesize_approx` (numeric): An estimate for the number of bytes
 - `protocol` (string): The protocol that will be used for the actual download
 - `extractor` (string): Name of the extractor
 - `extractor_key` (string): Key name of the extractor
 - `epoch` (numeric): Unix epoch when creating the file
 - `autonumber` (numeric): Number that will be increased with each download, starting at `--autonumber-start`
 - `playlist` (string): Name or id of the playlist that contains the video
 - `playlist_index` (numeric): Index of the video in the playlist padded with leading zeros according to the total length of the playlist
 - `playlist_id` (string): Playlist identifier
 - `playlist_title` (string): Playlist title
 - `playlist_uploader` (string): Full name of the playlist uploader
 - `playlist_uploader_id` (string): Nickname or id of the playlist uploader

Available for the video that belongs to some logical chapter or section:

 - `chapter` (string): Name or title of the chapter the video belongs to
 - `chapter_number` (numeric): Number of the chapter the video belongs to
 - `chapter_id` (string): Id of the chapter the video belongs to

Available for the video that is an episode of some series or programme:

 - `series` (string): Title of the series or programme the video episode belongs to
 - `season` (string): Title of the season the video episode belongs to
 - `season_number` (numeric): Number of the season the video episode belongs to
 - `season_id` (string): Id of the season the video episode belongs to
 - `episode` (string): Title of the video episode
 - `episode_number` (numeric): Number of the video episode within a season
 - `episode_id` (string): Id of the video episode

Available for the media that is a track or a part of a music album:

 - `track` (string): Title of the track
 - `track_number` (numeric): Number of the track within an album or a disc
 - `track_id` (string): Id of the track
 - `artist` (string): Artist(s) of the track
 - `genre` (string): Genre(s) of the track
 - `album` (string): Title of the album the track belongs to
 - `album_type` (string): Type of the album
 - `album_artist` (string): List of all artists appeared on the album
 - `disc_number` (numeric): Number of the disc or other physical medium the track belongs to
 - `release_year` (numeric): Year (YYYY) when the album was released

Available for `chapter:` prefix when using `--split-chapters` for videos with internal chapters:

 - `section_title` (string): Title of the chapter
 - `section_number` (numeric): Number of the chapter within the file
 - `section_start` (numeric): Start time of the chapter in seconds
 - `section_end` (numeric): End time of the chapter in seconds

Available only when used in `--print`:

 - `urls` (string): The URLs of all requested formats, one in each line
 - `filename` (string): Name of the video file. Note that the actual filename may be different due to post-processing. Use `--exec echo` to get the name after all postprocessing is complete

Each aforementioned sequence when referenced in an output template will be replaced by the actual value corresponding to the sequence name. Note that some of the sequences are not guaranteed to be present since they depend on the metadata obtained by a particular extractor. Such sequences will be replaced with placeholder value provided with `--output-na-placeholder` (`NA` by default).

For example for `-o %(title)s-%(id)s.%(ext)s` and an mp4 video with title `yt-dlp test video` and id `BaW_jenozKcj`, this will result in a `yt-dlp test video-BaW_jenozKcj.mp4` file created in the current directory.

For numeric sequences you can use numeric related formatting, for example, `%(view_count)05d` will result in a string with view count padded with zeros up to 5 characters, like in `00042`.

Output templates can also contain arbitrary hierarchical path, e.g. `-o '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s'` which will result in downloading each video in a directory corresponding to this path template. Any missing directory will be automatically created for you.

To use percent literals in an output template use `%%`. To output to stdout use `-o -`.

The current default template is `%(title)s [%(id)s].%(ext)s`.

In some cases, you don't want special characters such as 中, spaces, or &, such as when transferring the downloaded filename to a Windows system or the filename through an 8bit-unsafe channel. In these cases, add the `--restrict-filenames` flag to get a shorter title:

#### Output template and Windows batch files

If you are using an output template inside a Windows batch file then you must escape plain percent characters (`%`) by doubling, so that `-o "%(title)s-%(id)s.%(ext)s"` should become `-o "%%(title)s-%%(id)s.%%(ext)s"`. However you should not touch `%`'s that are not plain characters, e.g. environment variables for expansion should stay intact: `-o "C:\%HOMEPATH%\Desktop\%%(title)s.%%(ext)s"`.

#### Output template examples

Note that on Windows you need to use double quotes instead of single.

```bash
$ yt-dlp --get-filename -o '%(title)s.%(ext)s' BaW_jenozKc
youtube-dl test video ''_ä↭𝕐.mp4    # All kinds of weird characters

$ yt-dlp --get-filename -o '%(title)s.%(ext)s' BaW_jenozKc --restrict-filenames
youtube-dl_test_video_.mp4          # A simple file name

# Download YouTube playlist videos in separate directory indexed by video order in a playlist
$ yt-dlp -o '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s' https://www.youtube.com/playlist?list=PLwiyx1dc3P2JR9N8gQaQN_BCvlSlap7re

# Download YouTube playlist videos in separate directories according to their uploaded year
$ yt-dlp -o '%(upload_date>%Y)s/%(title)s.%(ext)s' https://www.youtube.com/playlist?list=PLwiyx1dc3P2JR9N8gQaQN_BCvlSlap7re

# Download all playlists of YouTube channel/user keeping each playlist in separate directory:
$ yt-dlp -o '%(uploader)s/%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s' https://www.youtube.com/user/TheLinuxFoundation/playlists

# Download Udemy course keeping each chapter in separate directory under MyVideos directory in your home
$ yt-dlp -u user -p password -P '~/MyVideos' -o '%(playlist)s/%(chapter_number)s - %(chapter)s/%(title)s.%(ext)s' https://www.udemy.com/java-tutorial/

# Download entire series season keeping each series and each season in separate directory under C:/MyVideos
$ yt-dlp -P "C:/MyVideos" -o "%(series)s/%(season_number)s - %(season)s/%(episode_number)s - %(episode)s.%(ext)s" https://videomore.ru/kino_v_detalayah/5_sezon/367617

# Stream the video being downloaded to stdout
$ yt-dlp -o - BaW_jenozKc
```

# FORMAT SELECTION

By default, yt-dlp tries to download the best available quality if you **don't** pass any options.
This is generally equivalent to using `-f bestvideo*+bestaudio/best`. However, if multiple audiostreams is enabled (`--audio-multistreams`), the default format changes to `-f bestvideo+bestaudio/best`. Similarly, if ffmpeg is unavailable, or if you use yt-dlp to stream to `stdout` (`-o -`), the default becomes `-f best/bestvideo+bestaudio`.

The general syntax for format selection is `-f FORMAT` (or `--format FORMAT`) where `FORMAT` is a *selector expression*, i.e. an expression that describes format or formats you would like to download.

**tl;dr:** [navigate me to examples](#format-selection-examples).

The simplest case is requesting a specific format, for example with `-f 22` you can download the format with format code equal to 22. You can get the list of available format codes for particular video using `--list-formats` or `-F`. Note that these format codes are extractor specific.

You can also use a file extension (currently `3gp`, `aac`, `flv`, `m4a`, `mp3`, `mp4`, `ogg`, `wav`, `webm` are supported) to download the best quality format of a particular file extension served as a single file, e.g. `-f webm` will download the best quality format with the `webm` extension served as a single file.

You can also use special names to select particular edge case formats:

 - `all`: Select all formats
 - `mergeall`: Select and merge all formats (Must be used with `--audio-multistreams`, `--video-multistreams` or both)
 - `b*`, `best*`: Select the best quality format irrespective of whether it contains video or audio
 - `w*`, `worst*`: Select the worst quality format irrespective of whether it contains video or audio
 - `b`, `best`: Select the best quality format that contains both video and audio. Equivalent to `best*[vcodec!=none][acodec!=none]`
 - `w`, `worst`: Select the worst quality format that contains both video and audio. Equivalent to `worst*[vcodec!=none][acodec!=none]`
 - `bv`, `bestvideo`: Select the best quality video-only format. Equivalent to `best*[acodec=none]`
 - `wv`, `worstvideo`: Select the worst quality video-only format. Equivalent to `worst*[acodec=none]`
 - `bv*`, `bestvideo*`: Select the best quality format that contains video. It may also contain audio. Equivalent to `best*[vcodec!=none]`
 - `wv*`, `worstvideo*`: Select the worst quality format that contains video. It may also contain audio. Equivalent to `worst*[vcodec!=none]`
 - `ba`, `bestaudio`: Select the best quality audio-only format. Equivalent to `best*[vcodec=none]`
 - `wa`, `worstaudio`: Select the worst quality audio-only format. Equivalent to `worst*[vcodec=none]`
 - `ba*`, `bestaudio*`: Select the best quality format that contains audio. It may also contain video. Equivalent to `best*[acodec!=none]`
 - `wa*`, `worstaudio*`: Select the worst quality format that contains audio. It may also contain video. Equivalent to `worst*[acodec!=none]`

For example, to download the worst quality video-only format you can use `-f worstvideo`. It is however recommended not to use `worst` and related options. When your format selector is `worst`, the format which is worst in all respects is selected. Most of the time, what you actually want is the video with the smallest filesize instead. So it is generally better to use `-f best -S +size,+br,+res,+fps` instead of `-f worst`. See [sorting formats](#sorting-formats) for more details.

You can select the n'th best format of a type by using `best<type>.<n>`. For example, `best.2` will select the 2nd best combined format. Similarly, `bv*.3` will select the 3rd best format that contains a video stream.

If you want to download multiple videos and they don't have the same formats available, you can specify the order of preference using slashes. Note that formats on the left hand side are preferred, for example `-f 22/17/18` will download format 22 if it's available, otherwise it will download format 17 if it's available, otherwise it will download format 18 if it's available, otherwise it will complain that no suitable formats are available for download.

If you want to download several formats of the same video use a comma as a separator, e.g. `-f 22,17,18` will download all these three formats, of course if they are available. Or a more sophisticated example combined with the precedence feature: `-f 136/137/mp4/bestvideo,140/m4a/bestaudio`.

You can merge the video and audio of multiple formats into a single file using `-f <format1>+<format2>+...` (requires ffmpeg installed), for example `-f bestvideo+bestaudio` will download the best video-only format, the best audio-only format and mux them together with ffmpeg. If `--no-video-multistreams` is used, all formats with a video stream except the first one are ignored. Similarly, if `--no-audio-multistreams` is used, all formats with an audio stream except the first one are ignored. For example, `-f bestvideo+best+bestaudio` will download and merge all 3 given formats. The resulting file will have 2 video streams and 2 audio streams. But `-f bestvideo+best+bestaudio --no-video-multistreams` will download and merge only `bestvideo` and `bestaudio`. `best` is ignored since another format containing a video stream (`bestvideo`) has already been selected. The order of the formats is therefore important. `-f best+bestaudio --no-audio-multistreams` will download and merge both formats while `-f bestaudio+best --no-audio-multistreams` will ignore `best` and download only `bestaudio`.

## Filtering Formats

You can also filter the video formats by putting a condition in brackets, as in `-f "best[height=720]"` (or `-f "[filesize>10M]"`).

The following numeric meta fields can be used with comparisons `<`, `<=`, `>`, `>=`, `=` (equals), `!=` (not equals):

 - `filesize`: The number of bytes, if known in advance
 - `width`: Width of the video, if known
 - `height`: Height of the video, if known
 - `tbr`: Average bitrate of audio and video in KBit/s
 - `abr`: Average audio bitrate in KBit/s
 - `vbr`: Average video bitrate in KBit/s
 - `asr`: Audio sampling rate in Hertz
 - `fps`: Frame rate

Also filtering work for comparisons `=` (equals), `^=` (starts with), `$=` (ends with), `*=` (contains) and following string meta fields:

 - `ext`: File extension
 - `acodec`: Name of the audio codec in use
 - `vcodec`: Name of the video codec in use
 - `container`: Name of the container format
 - `protocol`: The protocol that will be used for the actual download, lower-case (`http`, `https`, `rtsp`, `rtmp`, `rtmpe`, `mms`, `f4m`, `ism`, `http_dash_segments`, `m3u8`, or `m3u8_native`)
 - `format_id`: A short description of the format
 - `language`: Language code

Any string comparison may be prefixed with negation `!` in order to produce an opposite comparison, e.g. `!*=` (does not contain).

Note that none of the aforementioned meta fields are guaranteed to be present since this solely depends on the metadata obtained by particular extractor, i.e. the metadata offered by the website. Any other field made available by the extractor can also be used for filtering.

Formats for which the value is not known are excluded unless you put a question mark (`?`) after the operator. You can combine format filters, so `-f "[height<=?720][tbr>500]"` selects up to 720p videos (or videos where the height is not known) with a bitrate of at least 500 KBit/s. You can also use the filters with `all` to download all formats that satisfy the filter. For example, `-f "all[vcodec=none]"` selects all audio-only formats.

Format selectors can also be grouped using parentheses, for example if you want to download the best mp4 and webm formats with a height lower than 480 you can use `-f '(mp4,webm)[height<480]'`.

## Sorting Formats

You can change the criteria for being considered the `best` by using `-S` (`--format-sort`). The general format for this is `--format-sort field1,field2...`. The available fields are:

 - `hasvid`: Gives priority to formats that has a video stream
 - `hasaud`: Gives priority to formats that has a audio stream
 - `ie_pref`: The format preference as given by the extractor
 - `lang`: Language preference as given by the extractor
 - `quality`: The quality of the format as given by the extractor
 - `source`: Preference of the source as given by the extractor
 - `proto`: Protocol used for download (`https`/`ftps` > `http`/`ftp` > `m3u8_native` > `m3u8` > `http_dash_segments` > other > `mms`/`rtsp` > unknown > `f4f`/`f4m`)
 - `vcodec`: Video Codec (`av01` > `vp9.2` > `vp9` > `h265` > `h264` > `vp8` > `h263` > `theora` > other > unknown)
 - `acodec`: Audio Codec (`opus` > `vorbis` > `aac` > `mp4a` > `mp3` > `ac3` > `dts` > other > unknown)
 - `codec`: Equivalent to `vcodec,acodec`
 - `vext`: Video Extension (`mp4` > `webm` > `flv` > other > unknown). If `--prefer-free-formats` is used, `webm` is prefered.
 - `aext`: Audio Extension (`m4a` > `aac` > `mp3` > `ogg` > `opus` > `webm` > other > unknown). If `--prefer-free-formats` is used, the order changes to `opus` > `ogg` > `webm` > `m4a` > `mp3` > `aac`.
 - `ext`: Equivalent to `vext,aext`
 - `filesize`: Exact filesize, if know in advance. This will be unavailable for mu38 and DASH formats.
 - `fs_approx`: Approximate filesize calculated from the manifests
 - `size`: Exact filesize if available, otherwise approximate filesize
 - `height`: Height of video
 - `width`: Width of video
 - `res`: Video resolution, calculated as the smallest dimension.
 - `fps`: Framerate of video
 - `tbr`: Total average bitrate in KBit/s
 - `vbr`: Average video bitrate in KBit/s
 - `abr`: Average audio bitrate in KBit/s
 - `br`: Equivalent to using `tbr,vbr,abr`
 - `asr`: Audio sample rate in Hz

Note that any other **numerical** field made available by the extractor can also be used. All fields, unless specified otherwise, are sorted in descending order. To reverse this, prefix the field with a `+`. Eg: `+res` prefers format with the smallest resolution. Additionally, you can suffix a preferred value for the fields, separated by a `:`. Eg: `res:720` prefers larger videos, but no larger than 720p and the smallest video if there are no videos less than 720p. For `codec` and `ext`, you can provide two preferred values, the first for video and the second for audio. Eg: `+codec:avc:m4a` (equivalent to `+vcodec:avc,+acodec:m4a`) sets the video codec preference to `h264` > `h265` > `vp9` > `vp9.2` > `av01` > `vp8` > `h263` > `theora` and audio codec preference to `mp4a` > `aac` > `vorbis` > `opus` > `mp3` > `ac3` > `dts`. You can also make the sorting prefer the nearest values to the provided by using `~` as the delimiter. Eg: `filesize~1G` prefers the format with filesize closest to 1 GiB.

The fields `hasvid`, `ie_pref`, `lang` are always given highest priority in sorting, irrespective of the user-defined order. This behaviour can be changed by using `--force-format-sort`. Apart from these, the default order used is: `quality,res,fps,codec:vp9.2,size,br,asr,proto,ext,hasaud,source,id`. Note that the extractors may override this default order, but they cannot override the user-provided order.

If your format selector is `worst`, the last item is selected after sorting. This means it will select the format that is worst in all respects. Most of the time, what you actually want is the video with the smallest filesize instead. So it is generally better to use `-f best -S +size,+br,+res,+fps`.

**Tip**: You can use the `-v -F` to see how the formats have been sorted (worst to best).

## Format Selection examples

Note that on Windows you may need to use double quotes instead of single.

```bash
# Download and merge the best video-only format and the best audio-only format,
# or download the best combined format if video-only format is not available
$ yt-dlp -f 'bv+ba/b'

# Download best format that contains video,
# and if it doesn't already have an audio stream, merge it with best audio-only format
$ yt-dlp -f 'bv*+ba/b'

# Same as above
$ yt-dlp

# Download the best video-only format and the best audio-only format without merging them
# For this case, an output template should be used since
# by default, bestvideo and bestaudio will have the same file name.
$ yt-dlp -f 'bv,ba' -o '%(title)s.f%(format_id)s.%(ext)s'

# Download and merge the best format that has a video stream,
# and all audio-only formats into one file
$ yt-dlp -f 'bv*+mergeall[vcodec=none]' --audio-multistreams

# Download and merge the best format that has a video stream,
# and the best 2 audio-only formats into one file
$ yt-dlp -f 'bv*+ba+ba.2' --audio-multistreams


# The following examples show the old method (without -S) of format selection
# and how to use -S to achieve a similar but (generally) better result

# Download the worst video available (old method)
$ yt-dlp -f 'wv*+wa/w'

# Download the best video available but with the smallest resolution
$ yt-dlp -S '+res'

# Download the smallest video available
$ yt-dlp -S '+size,+br'



# Download the best mp4 video available, or the best video if no mp4 available
$ yt-dlp -f 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b'

# Download the best video with the best extension
# (For video, mp4 > webm > flv. For audio, m4a > aac > mp3 ...)
$ yt-dlp -S 'ext'



# Download the best video available but no better than 480p,
# or the worst video if there is no video under 480p
$ yt-dlp -f 'bv*[height<=480]+ba/b[height<=480] / wv*+ba/w'

# Download the best video available with the largest height but no better than 480p,
# or the best video with the smallest resolution if there is no video under 480p
$ yt-dlp -S 'height:480'

# Download the best video available with the largest resolution but no better than 480p,
# or the best video with the smallest resolution if there is no video under 480p
# Resolution is determined by using the smallest dimension.
# So this works correctly for vertical videos as well
$ yt-dlp -S 'res:480'



# Download the best video (that also has audio) but no bigger than 50 MB,
# or the worst video (that also has audio) if there is no video under 50 MB
$ yt-dlp -f 'b[filesize<50M] / w'

# Download largest video (that also has audio) but no bigger than 50 MB,
# or the smallest video (that also has audio) if there is no video under 50 MB
$ yt-dlp -f 'b' -S 'filesize:50M'

# Download best video (that also has audio) that is closest in size to 50 MB
$ yt-dlp -f 'b' -S 'filesize~50M'



# Download best video available via direct link over HTTP/HTTPS protocol,
# or the best video available via any protocol if there is no such video
$ yt-dlp -f '(bv*+ba/b)[protocol^=http][protocol!*=dash] / (bv*+ba/b)'

# Download best video available via the best protocol
# (https/ftps > http/ftp > m3u8_native > m3u8 > http_dash_segments ...)
$ yt-dlp -S 'proto'



# Download the best video with h264 codec, or the best video if there is no such video
$ yt-dlp -f '(bv*+ba/b)[vcodec^=avc1] / (bv*+ba/b)'

# Download the best video with best codec no better than h264,
# or the best video with worst codec if there is no such video
$ yt-dlp -S 'codec:h264'

# Download the best video with worst codec no worse than h264,
# or the best video with best codec if there is no such video
$ yt-dlp -S '+codec:h264'



# More complex examples

# Download the best video no better than 720p preferring framerate greater than 30,
# or the worst video (still preferring framerate greater than 30) if there is no such video
$ yt-dlp -f '((bv*[fps>30]/bv*)[height<=720]/(wv*[fps>30]/wv*)) + ba / (b[fps>30]/b)[height<=720]/(w[fps>30]/w)'

# Download the video with the largest resolution no better than 720p,
# or the video with the smallest resolution available if there is no such video,
# preferring larger framerate for formats with the same resolution
$ yt-dlp -S 'res:720,fps'



# Download the video with smallest resolution no worse than 480p,
# or the video with the largest resolution available if there is no such video,
# preferring better codec and then larger total bitrate for the same resolution
$ yt-dlp -S '+res:480,codec,br'
```

# MODIFYING METADATA

The metadata obtained the the extractors can be modified by using `--parse-metadata FROM:TO`. The general syntax is to give the name of a field or a template (with similar syntax to [output template](#output-template)) to extract data from, and the format to interpret it as, separated by a colon `:`. Either a [python regular expression](https://docs.python.org/3/library/re.html#regular-expression-syntax) with named capture groups or a similar syntax to the [output template](#output-template) (only `%(field)s` formatting is supported) can be used for `TO`. The option can be used multiple times to parse and modify various fields.

Note that any field created by this can be used in the [output template](#output-template) and will also affect the media file's metadata added when using `--add-metadata`.

You can also use this to change only the metadata that is embedded in the media file. To do this, set the value of the corresponding field with a `meta_` prefix. For example, any value you set to `meta_description` field will be added to the `description` field in the file. You can use this to set a different "description" and "synopsis", for example.

## Modifying metadata examples

Note that on Windows you may need to use double quotes instead of single.

```bash
# Interpret the title as "Artist - Title"
$ yt-dlp --parse-metadata 'title:%(artist)s - %(title)s'

# Regex example
$ yt-dlp --parse-metadata 'description:Artist - (?P<artist>.+)'

# Set title as "Series name S01E05"
$ yt-dlp --parse-metadata '%(series)s S%(season_number)02dE%(episode_number)02d:%(title)s'

# Set "comment" field in video metadata using description instead of webpage_url
$ yt-dlp --parse-metadata 'description:(?s)(?P<meta_comment>.+)' --add-metadata

```

# PLUGINS

Plugins are loaded from `<root-dir>/ytdlp_plugins/<type>/__init__.py`. Currently only `extractor` plugins are supported. Support for `downloader` and `postprocessor` plugins may be added in the future. See [ytdlp_plugins](ytdlp_plugins) for example.

**Note**: `<root-dir>` is the directory of the binary (`<root-dir>/yt-dlp`), or the root directory of the module if you are running directly from source-code (`<root dir>/yt_dlp/__main__.py`)

# DEPRECATED OPTIONS

These are all the deprecated options and the current alternative to achieve the same effect

#### Not recommended
While these options still work, their use is not recommended since there are other alternatives to achieve the same

    --get-description                --print description
    --get-duration                   --print duration_string
    --get-filename                   --print filename
    --get-format                     --print format
    --get-id                         --print id
    --get-thumbnail                  --print thumbnail
    -e, --get-title                  --print title
    -g, --get-url                    --print urls
    --all-formats                    -f all
    --all-subs                       --sub-langs all --write-subs
    --autonumber-size NUMBER         Use string formatting. Eg: %(autonumber)03d
    --autonumber-start NUMBER        Use internal field formatting like %(autonumber+NUMBER)s
    --metadata-from-title FORMAT     --parse-metadata "%(title)s:FORMAT"
    --hls-prefer-native              --downloader "m3u8:native"
    --hls-prefer-ffmpeg              --downloader "m3u8:ffmpeg"
    --list-formats-old               --compat-options list-formats (Alias: --no-list-formats-as-table)
    --list-formats-as-table          --compat-options -list-formats [Default] (Alias: --no-list-formats-old)
    --sponskrub-args ARGS            --ppa "sponskrub:ARGS"
    --test                           Used by developers for testing extractors. Not intended for the end user


#### Old aliases
These are aliases that are no longer documented for various reasons

    --avconv-location                --ffmpeg-location
    --cn-verification-proxy URL      --geo-verification-proxy URL
    --dump-headers                   --print-traffic
    --dump-intermediate-pages        --dump-pages
    --force-write-download-archive   --force-write-archive
    --load-info                      --load-info-json
    --no-split-tracks                --no-split-chapters
    --no-write-srt                   --no-write-subs
    --prefer-unsecure                --prefer-insecure
    --rate-limit RATE                --limit-rate RATE
    --split-tracks                   --split-chapters
    --srt-lang LANGS                 --sub-langs LANGS
    --trim-file-names LENGTH         --trim-filenames LENGTH
    --write-srt                      --write-subs
    --yes-overwrites                 --force-overwrites

#### No longer supported
These options may no longer work as intended

    --prefer-avconv                  avconv is not officially supported by yt-dlp (Alias: --no-prefer-ffmpeg)
    --prefer-ffmpeg                  Default (Alias: --no-prefer-avconv)
    -C, --call-home                  Not implemented
    --no-call-home                   Default
    --include-ads                    No longer supported
    --no-include-ads                 Default
    --youtube-print-sig-code         No longer supported

#### Removed
These options were deprecated since 2014 and have now been entirely removed

    --id                             -o "%(id)s.%(ext)s"
    -A, --auto-number                -o "%(autonumber)s-%(id)s.%(ext)s"
    -t, --title                      -o "%(title)s-%(id)s.%(ext)s"
    -l, --literal                    -o accepts literal names


# MORE
For FAQ, Developer Instructions etc., see the [original README](https://github.com/ytdl-org/youtube-dl#faq)
