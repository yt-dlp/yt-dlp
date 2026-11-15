// Hand-written names and explanations for every control. The schema says what
// exists; this file says how to present it. A test fails if an engine option
// has no entry here, so new upstream options cannot slip through unlabelled.

export type Widget = 'text' | 'number' | 'select' | 'file' | 'folder' | 'password' | 'area';

export interface Meta {
  category: string;
  label: string;
  tip: string;
  widget?: Widget;
  placeholder?: string;
  /** fixed choices for a select, or suggestions for a text field */
  choices?: string[];
  suggest?: string[];
  /** labels for the members of a multi-flag switch */
  memberLabels?: Record<string, string>;
  /** names for each field of an option that takes several arguments */
  parts?: string[];
  /** runs as a one-off engine command instead of being part of a download */
  tool?: boolean;
}

export interface Category { id: string; label: string; blurb: string }

export const categories: Category[] = [
  { id: 'formats', label: 'Format and quality', blurb: 'Which streams to pick and how to rank them.' },
  { id: 'subtitles', label: 'Subtitles', blurb: 'Subtitle files, languages and formats.' },
  { id: 'selection', label: 'Playlists and filters', blurb: 'Which items of a playlist or channel to take, and rules for skipping.' },
  { id: 'output', label: 'Files and naming', blurb: 'Folders, file name templates and extra files written next to the media.' },
  { id: 'download', label: 'Download', blurb: 'Speed limits, retries, fragments and external downloaders.' },
  { id: 'network', label: 'Network', blurb: 'Proxy, addressing, region and request pacing.' },
  { id: 'auth', label: 'Sign-in and cookies', blurb: 'Accounts, passwords, browser cookies and certificates.' },
  { id: 'post', label: 'Conversion', blurb: 'Audio extraction, remuxing, re-encoding and ffmpeg.' },
  { id: 'metadata', label: 'Metadata and chapters', blurb: 'Tags, chapters and embedding.' },
  { id: 'thumbnails', label: 'Thumbnails', blurb: 'Cover images.' },
  { id: 'sponsorblock', label: 'SponsorBlock', blurb: 'Mark or cut sponsored segments on YouTube.' },
  { id: 'live', label: 'Live and scheduling', blurb: 'Live streams, premieres and waiting.' },
  { id: 'extractor', label: 'Sites and plugins', blurb: 'Per-site options, plugins and JavaScript runtimes.' },
  { id: 'logging', label: 'Simulate and print', blurb: 'Dry runs, printing fields, JSON output and log detail.' },
  { id: 'config', label: 'Config and workarounds', blurb: 'Config files, aliases, compatibility and odd fixes.' },
  { id: 'tools', label: 'Engine commands', blurb: 'One-off commands that do not download anything.' },
];

type Row = [id: string, label: string, tip: string, extra?: Partial<Meta>];
export const meta: Record<string, Meta> = {};
function section(category: string, rows: Row[]) {
  for (const [id, label, tip, extra] of rows) meta[id] = { category, label, tip, ...extra };
}

const WHEN = 'A stage name followed by a colon can go in front to choose when it runs: pre_process, after_filter, video, before_dl, post_process, after_move, after_video, playlist.';
const SB = 'sponsor, intro, outro, selfpromo, preview, filler, interaction, music_offtopic, hook, poi_highlight, chapter, all. Put a minus in front to leave one out, for example all,-preview.';

section('formats', [
  ['--format', 'Format', 'Which video and audio streams to download, written as a format selector. bv*+ba/b means best video plus best audio, or the best single file. Leave empty to let the engine choose the best.', { placeholder: 'bv*+ba/b', suggest: ['bv*+ba/b', 'best', 'bestaudio/best', 'bv*[height<=1080]+ba/b[height<=1080]', 'worst', 'mergeall'] }],
  ['--format-sort', 'Sort order', 'How to rank formats when deciding which is best, as a comma-separated list of fields. res:1080 prefers the largest resolution up to 1080p; vcodec:h264 prefers H.264.', { placeholder: 'res:1080,vcodec:h264', suggest: ['res:2160', 'res:1080', 'res:720', 'res:480', 'vcodec:h264,acodec:aac', 'ext', 'size', 'br', '+size'] }],
  ['--format-sort-reset', 'Reset sort order', 'Forget any sort order given earlier, for example one coming from a config file or a preset alias.'],
  ['--format-sort-force', 'Sort order overrides everything', 'Let your sort order outrank the built-in rules that normally come first, such as preferring formats that actually have video.'],
  ['--video-multistreams', 'Allow several video streams', 'Allow more than one video stream to be merged into a single file.'],
  ['--audio-multistreams', 'Allow several audio streams', 'Allow more than one audio stream to be merged into a single file, for example several languages.'],
  ['--prefer-free-formats', 'Prefer open formats', 'When two formats are the same quality, pick the open one (WebM, Opus) over the patented one (MP4, AAC).'],
  ['--check-formats', 'Check formats', 'Test that a format can really be downloaded before choosing it. Slower, but avoids picking a broken stream.', { memberLabels: { '--check-formats': 'Check the chosen formats', '--check-all-formats': 'Check every format', '--no-check-formats': 'Do not check' } }],
  ['--list-formats', 'List formats only', 'Print the table of available formats for each link and stop. Nothing is downloaded.'],
  ['--merge-output-format', 'Container when merging', 'File type to use when separate video and audio have to be joined. Several can be listed in order of preference, separated by slashes. Ignored when no merge is needed.', { suggest: ['mp4', 'mkv', 'webm', 'mov', 'avi', 'flv', 'mp4/mkv'] }],
]);

section('subtitles', [
  ['--write-subs', 'Save subtitles', 'Save subtitle files next to the video.'],
  ['--write-auto-subs', 'Save auto-generated captions', 'Also save machine-generated captions when the site offers them.'],
  ['--list-subs', 'List subtitles only', 'Print the subtitle languages available for each link and stop.'],
  ['--sub-format', 'Subtitle format', 'Preferred subtitle file format. Several can be listed in order of preference, separated by slashes.', { suggest: ['best', 'srt', 'vtt', 'ass', 'srt/best', 'ass/srt/best'] }],
  ['--sub-langs', 'Languages', 'Which subtitle languages to take, comma-separated. Patterns are allowed: en.* matches every English variant, all takes everything, and a minus in front leaves one out (all,-live_chat).', { placeholder: 'en.*,de', suggest: ['en.*', 'all', 'all,-live_chat', 'en.*,es.*,de,fr,ja'] }],
  ['--convert-subs', 'Convert subtitles to', 'Convert downloaded subtitles to another format.', { widget: 'select', choices: ['ass', 'lrc', 'srt', 'vtt', 'none'] }],
  ['--embed-subs', 'Embed subtitles', 'Put the subtitles inside the video file (MP4, WebM and MKV only) instead of keeping separate files.'],
]);

section('selection', [
  ['--yes-playlist', 'Download the whole playlist', 'When a link points at a video that is part of a playlist, turn this on to take the whole playlist or off to take just that video.'],
  ['--playlist-items', 'Items', 'Which items of a playlist to download, by position. 1,3,5-7 picks those; -5: means the last five; 1:10:2 means every second item up to 10.', { placeholder: '1:3,7,-5::2' }],
  ['--flat-playlist', 'List playlist without opening each item', 'Read only the playlist page and do not visit each video. Much faster for printing or listing, but the entries have little detail and nothing is downloaded from them.'],
  ['--playlist-random', 'Random order', 'Download playlist items in random order.'],
  ['--lazy-playlist', 'Process items as they arrive', 'Start working on playlist entries as soon as they are received instead of loading the whole list first. Turns off some playlist fields and random order.'],
  ['--min-filesize', 'Smallest file size', 'Skip anything smaller than this. Units like 50k or 44.6M are accepted.', { placeholder: '50k' }],
  ['--max-filesize', 'Largest file size', 'Skip anything larger than this. Units like 500M or 2G are accepted.', { placeholder: '2G' }],
  ['--date', 'Uploaded on', 'Only take videos uploaded on this date. Use YYYYMMDD, or relative forms like today-2weeks.', { placeholder: 'YYYYMMDD' }],
  ['--datebefore', 'Uploaded on or before', 'Only take videos uploaded on or before this date. Same formats as above.', { placeholder: 'YYYYMMDD' }],
  ['--dateafter', 'Uploaded on or after', 'Only take videos uploaded on or after this date. Same formats as above.', { placeholder: 'today-1month' }],
  ['--match-filters', 'Only download if', 'A rule every video must pass, comparing fields with numbers or text. duration>60 & like_count>?100 keeps videos over a minute with more than 100 likes (or an unknown count). Add several rules and a video passing any one of them is kept.', { placeholder: '!is_live & duration<3600' }],
  ['--no-match-filters', 'Clear download rules', 'Forget any "only download if" rules given earlier, for example from a config file.'],
  ['--break-match-filters', 'Stop the whole job unless', 'Like the rule above, but the first video that fails it ends the whole download instead of just being skipped.', { placeholder: 'upload_date>=20240101' }],
  ['--no-break-match-filters', 'Clear stop rules', 'Forget any "stop unless" rules given earlier.'],
  ['--age-limit', 'Age limit', 'Only take videos suitable for this age, in years.', { widget: 'number', placeholder: '18' }],
  ['--download-archive', 'Archive file', 'A text file that records every video downloaded. Anything already listed in it is skipped next time, which makes re-running a playlist or channel cheap.', { widget: 'file', placeholder: 'archive.txt' }],
  ['--no-download-archive', 'Do not use an archive', 'Ignore any archive file set earlier, for example in a config file.'],
  ['--force-write-archive', 'Record in archive even when simulating', 'Write entries to the archive as long as there are no errors, even when nothing is actually downloaded.'],
  ['--max-downloads', 'Stop after', 'Stop after this many files have been downloaded.', { widget: 'number', placeholder: 'number of files' }],
  ['--break-on-existing', 'Stop at the first item already in the archive', 'End the job as soon as a video turns up that is already recorded in the archive. Good for catching up on a channel.'],
  ['--break-per-input', 'Apply stop rules per link', 'Make the stop rules and "stop after" count start afresh for each link instead of ending everything.'],
  ['--skip-playlist-after-errors', 'Give up on a playlist after', 'Skip the rest of a playlist once this many items in it have failed.', { widget: 'number', placeholder: 'number of failures' }],
  ['--ignore-errors', 'When an item fails', 'What to do when one video in a playlist fails. By default the engine carries on with the next item.', { memberLabels: { '--ignore-errors': 'Carry on, and count the job as successful', '--no-abort-on-error': 'Carry on with the next item', '--abort-on-error': 'Stop the whole job' } }],
  ['--concat-playlist', 'Join playlist into one file', 'Join all the videos of a playlist into a single file. multi_video only does this for videos that the site itself splits into parts. All parts need the same codecs.', { widget: 'select' }],
]);

section('output', [
  ['--paths', 'Folders', 'Where files are saved. A plain path sets the main folder. Put a type and a colon in front to send some files elsewhere, for example temp:/tmp/work or thumbnail:covers.', { widget: 'folder', placeholder: '[type:]folder' }],
  ['--output', 'File name template', 'How files are named, using fields in %(name)s form. %(title)s [%(id)s].%(ext)s is the default. A type and a colon in front sets the name for one kind of file, for example thumbnail:%(title)s/cover.%(ext)s.', { placeholder: '%(uploader)s/%(title)s [%(id)s].%(ext)s' }],
  ['--output-na-placeholder', 'Text for missing fields', 'What to write in a file name when a field has no value.', { placeholder: 'NA' }],
  ['--restrict-filenames', 'Plain ASCII file names', 'Keep file names to plain letters and digits, with no spaces or ampersands.'],
  ['--windows-filenames', 'Windows-safe file names', 'Make sure file names are valid on Windows, whatever system you are on.'],
  ['--trim-filenames', 'Longest file name', 'Cut file names (not counting the extension) to this many characters.', { widget: 'number', placeholder: 'characters' }],
  ['--no-overwrites', 'If the file already exists', 'By default an existing video is left alone and other files are overwritten.', { memberLabels: { '--no-overwrites': 'Never overwrite anything', '--force-overwrites': 'Overwrite video and all related files', '--no-force-overwrites': 'Keep the video, overwrite related files' } }],
  ['--continue', 'Resume partial downloads', 'Pick up a half-finished file where it stopped instead of starting again.'],
  ['--part', 'Use .part files while downloading', 'Write to a temporary .part file and rename it when complete. Turn off to write straight into the final file.'],
  ['--mtime', 'Set file date to upload date', 'Set the modified time of the file from the date the server reports.'],
  ['--write-description', 'Save description', 'Save the video description to a .description text file.'],
  ['--write-info-json', 'Save info JSON', 'Save everything the engine knows about the video to a .info.json file. This can contain personal details such as account names.'],
  ['--write-playlist-metafiles', 'Save playlist-level files', 'When saving descriptions or info JSON, also save them for the playlist itself.'],
  ['--clean-info-json', 'Strip private data from info JSON', 'Leave out file paths and other machine-specific details from the info JSON. Turn off to write everything.'],
  ['--write-comments', 'Fetch comments', 'Download the comments and include them in the info JSON. Can be slow on popular videos.'],
  ['--load-info-json', 'Load from info JSON', 'Download using a .info.json file saved earlier instead of visiting the page again. Links may have expired if the file is old.', { widget: 'file' }],
  ['--batch-file', 'Read links from file', 'A text file with one link per line. Lines starting with #, ; or ] are ignored.', { widget: 'file' }],
  ['--no-batch-file', 'Do not read links from a file', 'Ignore any link file set earlier.'],
  ['--write-link', 'Save a shortcut to the page', 'Save an internet shortcut in the format your system uses.'],
  ['--write-url-link', 'Save a Windows .url shortcut', 'Save a .url internet shortcut.'],
  ['--write-webloc-link', 'Save a macOS .webloc shortcut', 'Save a .webloc internet shortcut.'],
  ['--write-desktop-link', 'Save a Linux .desktop shortcut', 'Save a .desktop internet shortcut.'],
  ['--xattrs', 'Write extended attributes', 'Store the title, description and source link in the file system attributes of the file (Dublin Core and XDG standards).'],
]);

section('download', [
  ['--concurrent-fragments', 'Fragments at once', 'How many pieces of a fragmented (DASH or HLS) video to download at the same time. More is faster on good connections.', { widget: 'number', placeholder: '1' }],
  ['--limit-rate', 'Speed limit', 'Maximum download speed per second, for example 50K or 4.2M.', { placeholder: '4.2M' }],
  ['--throttled-rate', 'Restart if slower than', 'If the speed stays below this, assume the server is throttling and fetch the video data again, for example 100K.', { placeholder: '100K' }],
  ['--retries', 'Retries', 'How many times to retry a failed download. Write infinite to never give up.', { placeholder: '10' }],
  ['--file-access-retries', 'File access retries', 'How many times to retry when the file cannot be opened or written. Write infinite to never give up.', { placeholder: '3' }],
  ['--fragment-retries', 'Fragment retries', 'How many times to retry a single fragment. Write infinite to never give up.', { placeholder: '10' }],
  ['--retry-sleep', 'Wait between retries', 'Seconds to wait before a retry. A number, or linear=START[:END[:STEP]] or exp=START[:END[:BASE]]. A type and a colon in front limits it to http, fragment, file_access or extractor retries.', { placeholder: 'fragment:exp=1:20' }],
  ['--skip-unavailable-fragments', 'When a fragment is missing', 'What to do when a piece of a fragmented video cannot be downloaded.', { memberLabels: { '--skip-unavailable-fragments': 'Skip it and continue', '--abort-on-unavailable-fragments': 'Stop the download' } }],
  ['--keep-fragments', 'Keep fragment files', 'Leave the downloaded pieces on disk after they are joined.'],
  ['--buffer-size', 'Buffer size', 'Size of the download buffer, for example 1024 or 16K.', { placeholder: '1024' }],
  ['--resize-buffer', 'Adjust buffer size automatically', 'Let the buffer grow from its starting size as the download speeds up.'],
  ['--http-chunk-size', 'Chunk size', 'Download in chunks of this size, for example 10M. This gets round throttling on some servers. Experimental.', { placeholder: '10M' }],
  ['--hls-use-mpegts', 'Save HLS as MPEG-TS', 'Use the MPEG-TS container for HLS video so the file can be played while it is still downloading. On by default for live streams.'],
  ['--download-sections', 'Only these sections', 'Download part of a video. Use *10:15-inf for a time range, a chapter name pattern such as intro, or *from-url to follow a timestamp in the link. Needs ffmpeg.', { placeholder: '*10:15-20:00' }],
  ['--downloader', 'External downloader', 'Use another program to do the downloading: native, aria2c, axel, curl, ffmpeg, httpie or wget. A protocol and a colon in front limits it to that protocol (http, ftp, m3u8, dash, rstp, rtmp, mms).', { placeholder: '[protocol:]name', suggest: ['native', 'aria2c', 'ffmpeg', 'curl', 'wget', 'm3u8:native', 'dash,m3u8:native'] }],
  ['--downloader-args', 'External downloader arguments', 'Extra arguments to hand to an external downloader, written as NAME:ARGS. For ffmpeg, ffmpeg_i:ARGS sets input arguments and ffmpeg_o:ARGS sets output arguments.', { placeholder: 'aria2c:-x 8 -k 1M' }],
]);

section('network', [
  ['--proxy', 'Proxy', 'Send traffic through this HTTP, HTTPS or SOCKS proxy, for example socks5://user:pass@127.0.0.1:1080/. Two double quotes ("") means connect directly.', { placeholder: 'socks5://127.0.0.1:1080' }],
  ['--socket-timeout', 'Timeout', 'Seconds to wait for a response before giving up.', { widget: 'number', placeholder: 'seconds' }],
  ['--source-address', 'Bind to address', 'The local IP address to connect from, for machines with more than one.', { placeholder: 'IP address' }],
  ['--force-ipv4', 'IP version', 'Force all connections over IPv4 or IPv6.', { memberLabels: { '--force-ipv4': 'IPv4 only', '--force-ipv6': 'IPv6 only' } }],
  ['--impersonate', 'Impersonate a browser', 'Make requests look like they come from a real browser, which some sites require. Give a client such as chrome, chrome-110 or chrome:windows-10. An empty value picks any available target.', { placeholder: 'chrome', suggest: ['chrome', 'firefox', 'safari', 'edge'] }],
  ['--enable-file-urls', 'Allow file:// links', 'Allow links that point at files on this computer. Off by default for safety.'],
  ['--geo-verification-proxy', 'Proxy for region checks', 'A proxy used only for the requests that check where you are. Downloads still use the normal proxy.', { placeholder: 'http://host:port' }],
  ['--xff', 'Fake region header', 'How to fake the X-Forwarded-For header to get past region blocks: default (only where known to work), never, an IP block such as 203.0.113.0/24, or a two-letter country code.', { placeholder: 'default', suggest: ['default', 'never', 'US', 'GB', 'DE', 'JP'] }],
  ['--sleep-requests', 'Wait between requests', 'Seconds to pause between requests while reading pages.', { widget: 'number', placeholder: 'seconds' }],
  ['--sleep-interval', 'Wait before each download', 'Seconds to pause before each download. With a maximum set below, this is the shortest random pause.', { widget: 'number', placeholder: 'seconds' }],
  ['--max-sleep-interval', 'Longest random wait', 'The longest random pause before a download. Only used together with the wait above.', { widget: 'number', placeholder: 'seconds' }],
  ['--sleep-subtitles', 'Wait before each subtitle', 'Seconds to pause before downloading each subtitle file.', { widget: 'number', placeholder: 'seconds' }],
  ['--add-headers', 'Extra HTTP headers', 'A header to send with every request, written as Name:Value.', { placeholder: 'Referer:https://example.com/' }],
  ['--no-check-certificates', 'Skip HTTPS certificate checks', 'Do not verify the identity of HTTPS servers. Only use this on networks you trust.'],
  ['--prefer-insecure', 'Use plain HTTP for video info', 'Fetch video information over an unencrypted connection. Only supported for YouTube.'],
  ['--legacy-server-connect', 'Allow legacy TLS', 'Allow HTTPS connections to old servers that do not support secure renegotiation.'],
]);

section('auth', [
  ['--cookies-from-browser', 'Use cookies from browser', 'Borrow the login from a browser on this computer: brave, chrome, chromium, edge, firefox, opera, safari, vivaldi or whale. A profile name can follow a colon (firefox:work), and a Firefox container after two colons. Close the browser first if it keeps its cookie file locked.', { placeholder: 'firefox', suggest: ['brave', 'chrome', 'chromium', 'edge', 'firefox', 'opera', 'safari', 'vivaldi', 'whale'] }],
  ['--no-cookies-from-browser', 'Do not use browser cookies', 'Ignore any browser set earlier, for example in a config file.'],
  ['--cookies', 'Cookie file', 'A cookies.txt file in Netscape format to read cookies from. The engine also writes updated cookies back into it.', { widget: 'file', placeholder: 'cookies.txt' }],
  ['--no-cookies', 'Do not use a cookie file', 'Ignore any cookie file set earlier.'],
  ['--username', 'Username', 'Account name or email for sites that support signing in directly.'],
  ['--password', 'Password', 'Password for that account. It is passed to the engine for this download and kept out of logs and reports.', { widget: 'password' }],
  ['--twofactor', 'Two-factor code', 'The current code from your authenticator, for sites that ask for one.', { widget: 'password' }],
  ['--video-password', 'Video password', 'Password for a single protected video (Vimeo, Youku and others). Not your account password.', { widget: 'password' }],
  ['--netrc', 'Use .netrc file', 'Read logins from your .netrc file.'],
  ['--netrc-location', '.netrc location', 'Where the .netrc file is, if not in your home folder.', { widget: 'file' }],
  ['--netrc-cmd', '.netrc command', 'A command that prints login details in .netrc format, for example a password manager call. {} is replaced with the site name.', { placeholder: 'pass show {}' }],
  ['--ap-mso', 'TV provider', 'The identifier of your TV provider, for sites that need an Adobe Pass login. Use the engine command "List TV providers" to see them.'],
  ['--ap-username', 'TV provider username', 'Login for your TV provider account.'],
  ['--ap-password', 'TV provider password', 'Password for your TV provider account.', { widget: 'password' }],
  ['--client-certificate', 'Client certificate', 'A certificate file in PEM format, for servers that ask the client to identify itself. It may include the private key.', { widget: 'file' }],
  ['--client-certificate-key', 'Certificate private key', 'The private key file that belongs to the client certificate.', { widget: 'file' }],
  ['--client-certificate-password', 'Certificate key password', 'Password for the private key, if it is encrypted.', { widget: 'password' }],
  ['--mark-watched', 'Mark as watched', 'Tell the site you watched the video, the way the web page would. Only works when signed in.'],
]);

section('post', [
  ['--extract-audio', 'Audio only', 'Convert the download to an audio-only file. Needs ffmpeg.'],
  ['--audio-format', 'Audio format', 'Format for extracted audio. best keeps whatever the source used, with no re-encoding.', { suggest: ['best', 'mp3', 'm4a', 'opus', 'flac', 'wav', 'aac', 'alac', 'vorbis'] }],
  ['--audio-quality', 'Audio quality', 'Quality for converted audio. Either a number from 0 (best) to 10 (smallest) for variable bitrate, or a fixed bitrate such as 128K.', { suggest: ['0', '2', '5', '128K', '192K', '256K', '320K'] }],
  ['--remux-video', 'Remux to', 'Move the video into another container without re-encoding, when the streams allow it. Rules like aac>m4a/mov>mp4/mkv are accepted.', { suggest: ['mp4', 'mkv', 'webm', 'mov', 'avi', 'flv', 'gif', 'mka', 'm4a', 'mp3', 'ogg', 'opus', 'aac>m4a/mov>mp4/mkv'] }],
  ['--recode-video', 'Re-encode to', 'Re-encode the video into another format when needed. Slow, and loses a little quality. Same syntax as remux.', { suggest: ['mp4', 'mkv', 'webm', 'mov', 'avi', 'flv', 'gif'] }],
  ['--postprocessor-args', 'Post-processor arguments', 'Extra arguments for ffmpeg or another post-processor, written as NAME:ARGS. Names include Merger, ExtractAudio, VideoConvertor, Metadata, EmbedThumbnail, ffmpeg, ffmpeg_i and ffmpeg_o.', { placeholder: 'Merger+ffmpeg_i1:-v quiet' }],
  ['--keep-video', 'Keep the original after converting', 'Keep the source file after it has been converted or had audio extracted.'],
  ['--post-overwrites', 'Overwrite converted files', 'Replace files that a conversion step would produce if they already exist.'],
  ['--fixup', 'Fix known file faults', 'Whether to repair known problems in the downloaded file automatically.', { widget: 'select' }],
  ['--ffmpeg-location', 'ffmpeg location', 'Use this copy of ffmpeg instead of the one that comes with the app. Give the binary or the folder it is in.', { widget: 'file' }],
  ['--exec', 'Run a command', 'Run a command after each download, with the file path added at the end. Output template fields can be used. ' + WHEN, { placeholder: 'after_move:echo %(filepath)q' }],
  ['--no-exec', 'Clear commands', 'Forget any commands set earlier.'],
  ['--force-keyframes-at-cuts', 'Exact cuts', 'Re-encode around cut points so that sections and removed chapters start and end exactly. Slower, but avoids glitches at the cuts.'],
  ['--use-postprocessor', 'Use a post-processor plugin', 'Turn on a post-processor plugin by name, with optional settings: NAME:key=value;key=value. The when setting chooses the stage.', { placeholder: 'NAME:when=after_move' }],
]);

section('metadata', [
  ['--embed-metadata', 'Embed metadata', 'Write the title, uploader, date and so on into the file. Also embeds chapters and the info JSON where the format allows, unless those are turned off below.'],
  ['--embed-chapters', 'Embed chapters', 'Add chapter markers to the file.'],
  ['--embed-info-json', 'Attach info JSON', 'Attach the info JSON to MKV and MKA files.'],
  ['--parse-metadata', 'Extract fields', 'Fill in fields by reading them out of other fields, written as FROM:TO. title:%(artist)s - %(title)s splits a title into artist and title. ' + WHEN, { placeholder: 'title:%(artist)s - %(title)s' }],
  ['--replace-in-metadata', 'Find and replace in fields', 'Replace text in one or more fields using a regular expression. ' + WHEN, { parts: ['Fields', 'Find (regex)', 'Replace with'] }],
  ['--split-chapters', 'Split into one file per chapter', 'Cut the video into a separate file for each chapter. The chapter: output template names them.'],
  ['--remove-chapters', 'Remove chapters matching', 'Cut out chapters whose title matches this pattern. A time range with a star in front, like *10:15-15:00, removes that range.', { placeholder: 'regex or *start-end' }],
  ['--no-remove-chapters', 'Clear chapter removal', 'Forget any chapter removal set earlier.'],
]);

section('thumbnails', [
  ['--write-thumbnail', 'Save thumbnail', 'Save the cover image as a separate file.', { memberLabels: { '--write-thumbnail': 'Save the best thumbnail', '--write-all-thumbnails': 'Save every size', '--no-write-thumbnail': 'Do not save' } }],
  ['--list-thumbnails', 'List thumbnails only', 'Print the available thumbnails for each link and stop.'],
  ['--embed-thumbnail', 'Embed thumbnail', 'Use the thumbnail as the cover art inside the file.'],
  ['--convert-thumbnails', 'Convert thumbnails to', 'Convert thumbnails to another image format.', { suggest: ['jpg', 'png', 'webp'] }],
]);

section('sponsorblock', [
  ['--sponsorblock-mark', 'Mark as chapters', 'Create chapters for these kinds of segment: ' + SB, { placeholder: 'all,-preview', suggest: ['all', 'sponsor', 'default', 'all,-preview'] }],
  ['--sponsorblock-remove', 'Cut out', 'Remove these kinds of segment from the file: ' + SB.replace(', poi_highlight, chapter', '') + ' Needs ffmpeg.', { placeholder: 'sponsor', suggest: ['sponsor', 'default', 'all', 'sponsor,selfpromo,interaction'] }],
  ['--sponsorblock-chapter-title', 'Chapter title', 'Title template for the chapters SponsorBlock creates. Fields: start_time, end_time, category, categories, name, category_names.', { placeholder: '[SponsorBlock]: %(category_names)l' }],
  ['--no-sponsorblock', 'Turn SponsorBlock off', 'Turn off both marking and cutting, whatever was set earlier.'],
  ['--sponsorblock-api', 'API address', 'The SponsorBlock server to ask.', { placeholder: 'https://sponsor.ajay.app' }],
]);

section('live', [
  ['--live-from-start', 'Record live streams from the beginning', 'Start from the first moment of a live stream instead of from now. Experimental; YouTube, Twitch and TVer only.'],
  ['--wait-for-video', 'Wait for scheduled streams', 'If a stream or premiere has not started, keep checking until it does. Give the seconds between checks, or a range such as 30-120.', { placeholder: '60' }],
  ['--no-wait-for-video', 'Do not wait', 'Fail straight away if the video is not available yet.'],
  ['--hls-split-discontinuity', 'Split HLS at ad breaks', 'Start a new format at each discontinuity in an HLS stream, such as an advert break.'],
]);

section('extractor', [
  ['--extractor-args', 'Site-specific options', 'Options for one site, written as SITE:key=value;key=value. For example youtube:player_client=web;skip=dash. See the engine documentation for what each site accepts.', { placeholder: 'youtube:player_client=web' }],
  ['--extractor-retries', 'Site error retries', 'How many times to retry when a site returns a known temporary error. Write infinite to never give up.', { placeholder: '3' }],
  ['--allow-dynamic-mpd', 'Dynamic DASH manifests', 'Whether to process DASH manifests that change over time.', { memberLabels: { '--allow-dynamic-mpd': 'Process them', '--ignore-dynamic-mpd': 'Ignore them' } }],
  ['--use-extractors', 'Limit to these sites', 'Only use the named site handlers, comma-separated. Patterns work: holodex.*,-youtube.*. all, default and generic are also accepted.', { placeholder: 'default,-generic' }],
  ['--default-search', 'Treat plain text as', 'What to do when something that is not a link is entered. ytsearch: searches YouTube, auto guesses, error refuses.', { suggest: ['auto', 'auto_warning', 'error', 'fixup_error', 'ytsearch', 'ytsearch5', 'gvsearch2'] }],
  ['--plugin-dirs', 'Plugin folders', 'Extra folders to load plugins from. default stands for the usual locations.', { widget: 'folder' }],
  ['--no-plugin-dirs', 'Clear plugin folders', 'Do not look for plugins anywhere, including the usual locations, unless folders are added after this.'],
  ['--js-runtimes', 'JavaScript runtimes', 'A JavaScript runtime the engine may use to solve site challenges: deno, node, quickjs or bun, optionally followed by a colon and its location. The app supplies its own built-in runtime unless you set one here.', { placeholder: 'deno:/path/to/deno' }],
  ['--no-js-runtimes', 'Clear JavaScript runtimes', 'Forget all runtimes, including the default, before any added above.'],
  ['--remote-components', 'Allow remote components', 'Let the engine fetch helper scripts it needs: ejs:npm (from npm; needs deno or bun) or ejs:github (from GitHub releases). Not needed with the bundled engine.', { suggest: ['ejs:github', 'ejs:npm'] }],
  ['--no-remote-components', 'Disallow remote components', 'Do not fetch anything, whatever was allowed earlier.'],
]);

section('logging', [
  ['--simulate', 'Simulate', 'Go through the motions without downloading the video or writing anything to disk.'],
  ['--skip-download', 'Skip the video itself', 'Do everything except download the video. Related files such as subtitles, thumbnails and info JSON are still written.'],
  ['--ignore-no-formats-error', 'Carry on when there are no formats', 'Do not treat "no formats found" as an error. Useful for collecting metadata of videos that cannot be downloaded.'],
  ['--print', 'Print fields', 'Print a field name or output template for each video, then stop without downloading (add "Simulate: off" to download as well). The result appears in the Output tab of the download. ' + WHEN, { placeholder: '%(title)s — %(duration>%H:%M:%S)s' }],
  ['--print-to-file', 'Print fields to a file', 'Append a line to a file for each video. The first box is the template, the second the file name (which may itself be a template). ' + WHEN, { parts: ['Template', 'File'] }],
  ['--dump-json', 'Print JSON for each video', 'Print the full information about each video as a line of JSON, without downloading.'],
  ['--dump-single-json', 'Print JSON for each link', 'Print one JSON document per link. For a playlist, the whole playlist is one document.'],
  ['--quiet', 'Quiet', 'Print only errors and what you explicitly ask for. The app still shows progress.'],
  ['--no-warnings', 'Hide warnings', 'Leave warnings out of the log.'],
  ['--verbose', 'Verbose log', 'Write detailed debugging information to the log. Turn this on before reporting a problem.'],
  ['--newline', 'Progress on separate lines', 'Print each progress update on its own line. The app always does this internally so it can read progress.'],
  ['--progress', 'Show progress', 'Print progress lines. Turning this off removes progress from the log; the queue then shows activity without a percentage.'],
  ['--console-title', 'Progress in terminal title', 'Show progress in the title bar of a terminal window. Has no visible effect inside the app.'],
  ['--progress-template', 'Progress template', 'Format of the progress lines in the log. A type and a colon go in front: download, download-title, postprocess or postprocess-title. Setting download: yourself replaces the template the app reads, so the queue will show activity without a percentage.', { placeholder: 'download:%(progress._percent_str)s of %(info.title)s' }],
  ['--progress-delta', 'Progress interval', 'Seconds between progress updates in the log.', { widget: 'number', placeholder: 'seconds' }],
  ['--dump-pages', 'Dump pages to log', 'Write every downloaded page into the log, base64-encoded. For debugging site problems.'],
  ['--write-pages', 'Save pages to files', 'Save every downloaded page as a file in the download folder. For debugging site problems.'],
  ['--print-traffic', 'Log HTTP traffic', 'Write all HTTP requests and responses to the log. This can include cookies and tokens, so check before sharing.'],
  ['--color', 'Colour in output', 'Whether to use colour codes in output: always, auto, never or no_color, optionally for one stream (stdout: or stderr:). The app asks for none so logs stay readable.', { placeholder: 'never', suggest: ['always', 'auto', 'never', 'no_color', 'stderr:never'] }],
]);

section('config', [
  ['--ignore-config', 'Ignore yt-dlp config files', 'Do not read yt-dlp.conf files from your home or system folders. On by default in the app so downloads only depend on what you see here.'],
  ['--config-locations', 'Also read config file', 'A config file, or a folder containing yt-dlp.conf, to read options from. Use Import in the Presets screen instead if you want to see and edit the options.', { widget: 'file' }],
  ['--no-config-locations', 'Clear config file list', 'Forget any config locations given earlier and ignore the default ones.'],
  ['--alias', 'Define alias', 'Create your own option that stands for a string of other options. The first box is the alias name (--my-alias), the second the options it expands to. Use it from Extra arguments.', { parts: ['Alias', 'Options'] }],
  ['--preset-alias', 'Engine preset', 'Apply one of the engine\'s built-in option presets: mp3, aac, mp4, mkv or sleep.', { suggest: ['mp3', 'aac', 'mp4', 'mkv', 'sleep'] }],
  ['--compat-options', 'Compatibility options', 'Bring back behaviour from youtube-dl or older yt-dlp versions, comma-separated. Examples: filename, format-sort, no-live-chat, youtube-dl, 2022.', { placeholder: 'no-live-chat,filename' }],
  ['--cache-dir', 'Cache folder', 'Where the engine keeps small cache files. Defaults to a folder in your user cache directory.', { widget: 'folder' }],
  ['--no-cache-dir', 'Do not use a cache', 'Turn the cache off.'],
  ['--encoding', 'Text encoding', 'Force a text encoding for output. The app uses UTF-8 unless you set something else. Experimental.', { placeholder: 'utf-8' }],
  ['--bidi-workaround', 'Right-to-left text workaround', 'For terminals without bidirectional text support. Needs the bidiv or fribidi program.'],
]);

section('tools', [
  ['--help', 'Show command line help', 'Print the engine\'s full help text.', { tool: true }],
  ['--version', 'Show version', 'Print the engine version.', { tool: true }],
  ['--update', 'Update engine', 'Ask the engine to update itself to the latest release on its channel.', { tool: true }],
  ['--update-to', 'Update or downgrade to', 'Move the engine to a specific channel or version, written as CHANNEL@TAG. Channels: stable, nightly, master, or any owner/repository.', { tool: true, placeholder: 'stable@latest', suggest: ['stable@latest', 'nightly@latest', 'master@latest'] }],
  ['--list-extractors', 'List supported sites', 'Print the name of every site handler.', { tool: true }],
  ['--extractor-descriptions', 'Describe supported sites', 'Print a description of every site handler.', { tool: true }],
  ['--list-impersonate-targets', 'List browsers that can be impersonated', 'Print the browser identities available for impersonation.', { tool: true }],
  ['--rm-cache-dir', 'Clear engine cache', 'Delete every file in the engine cache. Fixes some stale-data problems.', { tool: true }],
  ['--ap-list-mso', 'List TV providers', 'Print every TV provider supported for Adobe Pass logins.', { tool: true }],
]);

/** A readable name for options that have no hand-written entry (future engine versions). */
export function fallbackLabel(id: string): string {
  const words = id.replace(/^--?/, '').split('-');
  return words.map((w, i) => (i === 0 ? w[0].toUpperCase() + w.slice(1) : w)).join(' ');
}
