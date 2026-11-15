// Turns engine output into something a person can act on.
//
// Every rule names what happened, the likely reason, things to try and any
// one-click fixes the app can offer. Raw engine text is only ever shown under
// "Show details".

export type Stage = 'starting' | 'info' | 'format' | 'download' | 'merge' | 'post' | 'write' | 'done';

export const stageLabels: Record<Stage, string> = {
  starting: 'Starting the engine',
  info: 'Fetching information',
  format: 'Selecting a format',
  download: 'Downloading',
  merge: 'Merging video and audio',
  post: 'Post-processing',
  write: 'Writing the file',
  done: 'Finished',
};

export type FixId =
  | 'retry' | 'update-engine' | 'switch-format' | 'pick-folder' | 'browser-cookies'
  | 'install-ffmpeg' | 'edit-options' | 'retry-later' | 'trim-names' | 'check-links';

export const fixLabels: Record<FixId, string> = {
  'retry': 'Try again',
  'update-engine': 'Update engine and retry',
  'switch-format': 'Retry with best available format',
  'pick-folder': 'Choose another folder',
  'browser-cookies': 'Use browser cookies',
  'install-ffmpeg': 'Install ffmpeg',
  'edit-options': 'Edit options',
  'retry-later': 'Retry in 15 minutes',
  'trim-names': 'Shorten file names and retry',
  'check-links': 'Edit link',
};

export interface Friendly {
  code: string;
  title: string;
  what: string;
  why: string;
  tryThis: string[];
  fixes: FixId[];
  stage: Stage;
  /** the engine line that matched, kept for the details panel */
  raw: string;
  known: boolean;
}

interface Rule {
  code: string;
  match: RegExp;
  title: string;
  what: string;
  why: string;
  tryThis: string[];
  fixes: FixId[];
  /** overrides the stage the job was in, when the message itself is more telling */
  stage?: Stage;
}

// Order matters: the first match wins, so specific rules come before general ones.
const rules: Rule[] = [
  {
    code: 'engine-missing',
    match: /ENOENT|engine binary not found|spawn .* EACCES|cannot execute binary/i,
    title: 'The download engine could not be started',
    what: 'The app could not run its yt-dlp engine.',
    why: 'The engine file is missing, was removed by security software, or is not allowed to run.',
    tryThis: ['Reinstall the engine from Settings, then Engine.', 'If antivirus software quarantined it, restore it and add an exception.'],
    fixes: ['update-engine'],
    stage: 'starting',
  },
  {
    code: 'needs-input',
    match: /EOFError|EOF when reading a line|getpass|Password: ?$/im,
    title: 'The engine wanted to ask a question',
    what: 'The engine stopped to ask for something, usually a password, and there is no terminal to type it into.',
    why: 'A username was given without its password, or an option asked to read from the keyboard.',
    tryThis: ['Fill in both Username and Password (or the TV provider pair) under Sign-in and cookies.', 'Or use cookies from your browser instead of a password.'],
    fixes: ['edit-options', 'browser-cookies'],
    stage: 'starting',
  },
  {
    code: 'bad-option',
    match: /^(?:yt-dlp|yt_dlp|__main__\.py|Usage:).*?error: |^yt-dlp: error:|invalid .* specified|no such option|option .* requires|wrong .* format|Invalid (?:format|filter|retry|playlist-items)|is not a valid (?!URL)/im,
    title: 'One of the options was not accepted',
    what: 'The engine refused to start because an option has a value it does not understand.',
    why: 'This usually comes from a typo in an advanced option or in the extra arguments.',
    tryThis: ['Open the options for this download and check the field named in the details.', 'Hover any option to see what it expects.'],
    fixes: ['edit-options'],
    stage: 'starting',
  },
  {
    code: 'ffmpeg-missing',
    match: /ffmpeg(?: or ffprobe)? (?:is )?not (?:found|installed)|ffprobe and ffmpeg not found|ffmpeg not found|ffprobe not found|requested merging of multiple formats but ffmpeg is not installed|install ffmpeg/i,
    title: 'ffmpeg is missing',
    what: 'The download needs ffmpeg to merge or convert the file, and it could not be found.',
    why: 'The copy that comes with the app is missing or the custom location in your options is wrong.',
    tryThis: ['Let the app install ffmpeg for you.', 'If you set "ffmpeg location" yourself, clear it or point it at a working copy.'],
    fixes: ['install-ffmpeg'],
    stage: 'post',
  },
  {
    code: 'disk-full',
    match: /No space left on device|Errno 28|not enough space on the disk|Disk quota exceeded|disk is full/i,
    title: 'The disk is full',
    what: 'There was not enough free space to save the file.',
    why: 'The drive holding the download folder (or the temporary folder) has run out of room.',
    tryThis: ['Free some space and try again. The part already downloaded is kept.', 'Or save to a different drive.'],
    fixes: ['pick-folder', 'retry'],
    stage: 'write',
  },
  {
    code: 'name-too-long',
    match: /File ?name too long|Errno 36|path .* too long|filename is too long/i,
    title: 'The file name is too long',
    what: 'The file could not be created because its name is longer than this system allows.',
    why: 'The title of the video is very long, or the folder path is deeply nested.',
    tryThis: ['Shorten file names. The app can set a 120-character limit and retry.', 'Or use a shorter file name template.'],
    fixes: ['trim-names', 'pick-folder'],
    stage: 'write',
  },
  {
    code: 'no-permission',
    match: /Permission denied|Errno 13|Access is denied|Read-only file system|Operation not permitted|unable to (?:open for writing|create directory|rename file)/i,
    title: 'The app is not allowed to write there',
    what: 'The file could not be saved to the chosen folder.',
    why: 'The folder is read-only, belongs to another user, or the file is open in another program.',
    tryThis: ['Pick a folder you own, such as Downloads.', 'Close any program that has the file open, then try again.'],
    fixes: ['pick-folder', 'retry'],
    stage: 'write',
  },
  {
    code: 'js-runtime',
    match: /No supported JavaScript runtime|JavaScript runtime .* (?:not|could not)|challenge solver .* (?:not|unavailable)|n challenge solving failed|Remote components? .* (?:skipped|not allowed)/i,
    title: 'A helper the engine needs is unavailable',
    what: 'This site needs a JavaScript runtime to work out the real video address, and the engine could not use one.',
    why: 'The built-in runtime was turned off in the options, or the engine is too old for the site.',
    tryThis: ['Clear the "JavaScript runtimes" options under Sites and plugins so the app can supply its own.', 'Update the engine.'],
    fixes: ['update-engine', 'edit-options'],
    stage: 'info',
  },
  {
    code: 'cookies-browser',
    match: /could not find .* cookies database|Could not copy .* cookie database|failed to decrypt|cannot decrypt|unsupported browser|unable to (?:read|open) .* cookie|keyring|Failed to load cookies|cookie.* (?:file|jar) .* (?:invalid|not.*Netscape)|does not look like a Netscape format/i,
    title: 'The cookies could not be read',
    what: 'The engine could not load the cookies you asked it to use.',
    why: 'The browser is running and has its cookie file locked, the profile name is wrong, or the cookie file is not in Netscape format.',
    tryThis: ['Close the browser completely and try again.', 'Try a different browser under Sign-in and cookies.', 'If you use a cookies.txt file, export it again with a "cookies.txt" browser extension.'],
    fixes: ['browser-cookies', 'retry'],
    stage: 'info',
  },
  {
    code: 'cookies-expired',
    match: /cookies are no longer valid|cookies? (?:have |has )?expired|account cookies|rotated in the browser/i,
    title: 'The saved login has expired',
    what: 'The site no longer accepts the cookies being used.',
    why: 'Cookies expire, and some sites replace them whenever the browser is used.',
    tryThis: ['Sign in to the site again in your browser, then retry.', 'If you use a cookies.txt file, export a fresh one.'],
    fixes: ['browser-cookies', 'retry'],
    stage: 'info',
  },
  {
    code: 'bad-login',
    match: /Unable to log ?in|Wrong (?:username|password|email)|Invalid (?:username|password|credentials|login)|incorrect (?:username|password)|login failed|Authentication failed|two-?factor|verification code|account .* (?:locked|disabled)/i,
    title: 'Signing in did not work',
    what: 'The site rejected the username, password or code.',
    why: 'The details are wrong, the two-factor code has expired, or the site blocks direct logins.',
    tryThis: ['Check the username and password under Sign-in and cookies.', 'Many sites only allow browser logins. Sign in with your browser and use its cookies instead.'],
    fixes: ['browser-cookies', 'edit-options'],
    stage: 'info',
  },
  {
    code: 'bot-check',
    match: /confirm you.?re not a bot|not a robot|captcha|unusual traffic|Cloudflare|challenge page|anti-bot/i,
    title: 'The site wants proof you are a person',
    what: 'The site blocked the request with a bot check.',
    why: 'Too many requests came from your network, or the site does not serve visitors who are not signed in.',
    tryThis: ['Use the cookies from a browser where you are signed in to this site.', 'Wait a while, or switch network.', 'Under Network, try "Impersonate a browser".'],
    fixes: ['browser-cookies', 'retry-later'],
    stage: 'info',
  },
  {
    code: 'age-restricted',
    match: /confirm your age|age[- ]restricted|age[- ]gated|inappropriate for some users|only available to users over|adult content|NSFW/i,
    title: 'This video is age-restricted',
    what: 'The site only shows this video to signed-in adults.',
    why: 'Without a login the site cannot check your age, so it refuses.',
    tryThis: ['Sign in to the site in your browser, then let the app use that browser\'s cookies.'],
    fixes: ['browser-cookies'],
    stage: 'info',
  },
  {
    code: 'members-only',
    match: /members[- ]only|Join this channel|available to (?:this channel's )?members|subscribers[- ]only|requires? (?:a )?(?:payment|purchase|subscription|premium)|premium (?:members|users|only)|paid content|rental|pay-per-view|only available for (?:registered|premium)/i,
    title: 'This video needs a membership',
    what: 'The video is limited to paying members or subscribers.',
    why: 'You are either not signed in, or the account does not have access.',
    tryThis: ['If your account has access, sign in with your browser and use its cookies.', 'Otherwise the video cannot be downloaded.'],
    fixes: ['browser-cookies'],
    stage: 'info',
  },
  {
    code: 'private',
    match: /Private video|video is private|This (?:video|content|playlist|post) is private|playlist is private|private (?:account|profile)|only visible to|Sign in if you've been granted access/i,
    title: 'This video is private',
    what: 'The owner has limited who can see it.',
    why: 'Private videos are only shown to accounts the owner has invited.',
    tryThis: ['If you have been given access, sign in with your browser and use its cookies.', 'Otherwise ask the owner for access.'],
    fixes: ['browser-cookies'],
    stage: 'info',
  },
  {
    code: 'login-required',
    match: /login required|log ?in to|sign in to|requires? (?:authentication|login|an account|you to (?:log|sign))|need to (?:log|sign) ?in|Use --cookies|--cookies-from-browser|registered users|not logged in|HTTP Error 401/i,
    title: 'You need to be signed in',
    what: 'The site will not show this without a login.',
    why: 'The content is limited to signed-in users.',
    tryThis: ['Sign in to the site in your browser, then let the app use that browser\'s cookies.', 'Some sites accept a username and password directly under Sign-in and cookies.'],
    fixes: ['browser-cookies', 'edit-options'],
    stage: 'info',
  },
  {
    code: 'geo-blocked',
    match: /available (?:in|from) your (?:country|location|region)|geo[- ]?(?:restrict|block)|blocked (?:it )?in your country|unavailable in your (?:country|region)|your (?:country|region|location) is not|georestricted|content is not available in this region/i,
    title: 'Not available in your region',
    what: 'The site blocks this video where you are.',
    why: 'The owner or the site has limited it to certain countries.',
    tryThis: ['Under Network, set a proxy or VPN located in a country where the video is available.', 'For some sites the "Fake region header" option is enough.'],
    fixes: ['edit-options'],
    stage: 'info',
  },
  {
    code: 'drm',
    match: /DRM[- ]protected|is DRM protected|uses DRM|Widevine|FairPlay|PlayReady/i,
    title: 'This video is copy-protected',
    what: 'The stream is encrypted with DRM, which the engine does not handle.',
    why: 'Paid streaming services protect their video this way.',
    tryThis: ['There is no setting that changes this. The video cannot be downloaded.'],
    fixes: [],
    stage: 'format',
  },
  {
    code: 'live-not-started',
    match: /will begin in|Premieres in|live event will|has not started|is not currently live|not live yet|is offline|scheduled (?:for|to)|upcoming/i,
    title: 'It has not started yet',
    what: 'This is a scheduled stream or premiere that is not live yet.',
    why: 'There is nothing to download until it begins.',
    tryThis: ['Turn on "Wait for scheduled streams" under Live and scheduling, and the app will start when it goes live.', 'Or schedule the download for later.'],
    fixes: ['edit-options', 'retry-later'],
    stage: 'info',
  },
  {
    code: 'removed',
    match: /Video unavailable|has been removed|no longer available|been (?:deleted|terminated|taken down)|does not exist|doesn't exist|account .* (?:terminated|suspended)|copyright (?:claim|grounds)|removed by the uploader|This content isn.t available|HTTP Error 40[4]|HTTP Error 410|Not Found/i,
    title: 'The video is gone',
    what: 'The site says this video does not exist or has been taken down.',
    why: 'It was deleted, the account was closed, or the link is mistyped.',
    tryThis: ['Open the link in your browser to check that it still plays.', 'Check the link for missing characters.'],
    fixes: ['check-links'],
    stage: 'info',
  },
  {
    code: 'unsupported-url',
    match: /Unsupported URL|is not a valid URL|No suitable extractor|no video (?:could be )?found|Unable to (?:handle|recognize) (?:request|URL)|not a recognized|Cannot (?:parse|find) .* in URL/i,
    title: 'That link is not something the engine can download',
    what: 'The engine does not know how to get a video from this address.',
    why: 'The site is not supported, the page has no video on it, or the link is incomplete.',
    tryThis: ['Use the address of the page the video plays on, not a search or home page.', 'Update the engine in case support was added recently.'],
    fixes: ['check-links', 'update-engine'],
    stage: 'info',
  },
  {
    code: 'format-unavailable',
    match: /Requested format is not available|No video formats found|no formats? (?:found|available)|format .* not available|Unable to find (?:a )?suitable format/i,
    title: 'That quality or format is not offered',
    what: 'None of the formats the site offers match what was asked for.',
    why: 'The video does not come in the chosen resolution or codec, or a custom format selector is too strict.',
    tryThis: ['Retry with the best available format.', 'Use "Formats" in the preview to see exactly what the site offers.'],
    fixes: ['switch-format', 'edit-options'],
    stage: 'format',
  },
  {
    code: 'rate-limited',
    match: /HTTP Error 429|Too Many Requests|rate[- ]?limit|temporarily blocked|try again later|This content isn't available, try again later/i,
    title: 'The site is turning you away for now',
    what: 'The site says too many requests have come from your connection.',
    why: 'Downloading a lot in a short time triggers this. It usually lifts by itself.',
    tryThis: ['Wait a while before trying again.', 'Under Network, add a wait between requests and lower parallel downloads in Settings.', 'Signing in with browser cookies can raise the limit.'],
    fixes: ['retry-later', 'browser-cookies'],
    stage: 'info',
  },
  {
    code: 'proxy',
    match: /ProxyError|Tunnel connection failed|Cannot connect to proxy|proxy .* (?:refused|unreachable|failed)|HTTP Error 407|SOCKS/i,
    title: 'The proxy is not working',
    what: 'The connection through your proxy failed.',
    why: 'The proxy address is wrong, it is offline, or it needs a username and password.',
    tryThis: ['Check the proxy address under Network, or clear it to connect directly.'],
    fixes: ['edit-options', 'retry'],
  },
  {
    code: 'tls',
    match: /CERTIFICATE_VERIFY_FAILED|SSL: |SSLError|certificate verify failed|TLS|handshake fail/i,
    title: 'A secure connection could not be made',
    what: 'The encrypted connection to the site failed.',
    why: 'The computer clock is wrong, security software or a company network is intercepting traffic, or the server is very old.',
    tryThis: ['Check that the date and time on this computer are right.', 'On a work or school network, ask whether HTTPS traffic is filtered.', 'For old servers, try "Allow legacy TLS" under Network.'],
    fixes: ['retry', 'edit-options'],
  },
  {
    code: 'network-down',
    match: /Temporary failure in name resolution|getaddrinfo failed|Name or service not known|nodename nor servname|Network is unreachable|No route to host|Failed to resolve|Could not resolve host|No address associated|Errno 11001|Errno -[23]|Errno 101|Unable to connect|urlopen error|TransportError|internet connection/i,
    title: 'No internet connection',
    what: 'The app could not reach the site.',
    why: 'The connection is down, or a firewall, VPN or DNS problem is blocking it.',
    tryThis: ['Check that other websites open.', 'If you use a VPN or proxy, check that it is connected.', 'Try again. Anything already downloaded is kept.'],
    fixes: ['retry'],
  },
  {
    code: 'connection-dropped',
    match: /timed out|Read timed out|Connection (?:reset|aborted|refused|closed)|RemoteDisconnected|IncompleteRead|Broken pipe|EOF occurred|Errno 104|Errno 110|Errno 10054|Errno 10060|giving up after \d+ (?:fragment )?retries|content too short/i,
    title: 'The connection kept dropping',
    what: 'The download was interrupted and the retries ran out.',
    why: 'The connection is unstable, or the server is slow or overloaded.',
    tryThis: ['Try again. The download resumes from where it stopped.', 'Under Download, raise the number of retries.'],
    fixes: ['retry'],
    stage: 'download',
  },
  {
    code: 'forbidden',
    match: /HTTP Error 403|Forbidden|access denied|not authorized/i,
    title: 'The site refused the request',
    what: 'The server answered "403 Forbidden".',
    why: 'Most often the site changed something and the engine needs updating. It can also mean the link expired or a login is needed.',
    tryThis: ['Update the engine and try again.', 'If that does not help, use cookies from a signed-in browser.'],
    fixes: ['update-engine', 'browser-cookies'],
  },
  {
    code: 'impersonate',
    match: /Impersonate target .* (?:is )?not available|no impersonate target|impersonation .* (?:unsupported|missing)|curl_cffi/i,
    title: 'Browser impersonation is unavailable',
    what: 'The site needs requests that look like a real browser, and this engine build cannot do that for the chosen target.',
    why: 'The impersonation library is missing or does not support the browser named in the options.',
    tryThis: ['Clear "Impersonate a browser" under Network, or pick a target from Engine commands, "List browsers that can be impersonated".'],
    fixes: ['edit-options'],
    stage: 'info',
  },
  {
    code: 'ffmpeg-failed',
    match: /Postprocessing:|ffmpeg exited with code|Conversion failed|Error (?:opening|while) (?:output|input|decoding|muxing)|Invalid data found when processing|audio conversion failed|Could not write header|ERROR: .*ffmpeg|ffprobe .* (?:failed|error)/i,
    title: 'Converting the file failed',
    what: 'The video downloaded, but ffmpeg could not finish converting or merging it.',
    why: 'The chosen container cannot hold these streams, the downloaded file is damaged, or custom ffmpeg arguments are wrong.',
    tryThis: ['Try again with MKV as the container, which accepts almost anything.', 'Remove any custom post-processor arguments.', 'The original download is usually still in the folder.'],
    fixes: ['retry', 'edit-options'],
    stage: 'post',
  },
  {
    code: 'site-changed',
    match: /Unable to extract|please report this issue|Confirm you are on the latest version|nsig extraction failed|Signature extraction failed|Failed to (?:parse|extract)|Unable to download (?:JSON|API|webpage|video info)|ExtractorError|RegexNotFoundError|KeyError|player response|Some formats may be missing|unexpected (?:response|format)|HTTP Error 5\d\d|HTTP Error 400/i,
    title: 'The site has changed and the engine could not keep up',
    what: 'The engine could not find the video data on the page.',
    why: 'Sites change often. The engine is updated to follow them, usually within days.',
    tryThis: ['Update the engine and try again.', 'If it is already up to date, the fix may not be released yet. Try again tomorrow.'],
    fixes: ['update-engine', 'retry'],
    stage: 'info',
  },
];

const STAGE_HINTS: [RegExp, Stage][] = [
  [/Requested format|format .* not available|No video formats/i, 'format'],
  [/Postprocessing|ffmpeg|ffprobe|Conversion|Merger/i, 'post'],
  [/unable to (?:open for writing|rename|create directory)|No space left|Permission denied|File ?name too long/i, 'write'],
  [/Unable to download (?:webpage|JSON|API)|Unable to extract|Unsupported URL/i, 'info'],
];

/** Pull the meaningful lines out of raw engine output. */
export function errorLines(output: string): string[] {
  return output.split(/\r?\n/).filter((l) => /^(?:ERROR|yt-dlp: error|Usage:.*error)|^\[\w+\] ERROR|Traceback \(most recent call last\)|^\w*Error: /.test(l.trim())).map((l) => l.trim());
}

export function translate(raw: string, stage: Stage = 'starting'): Friendly {
  const text = raw.trim();
  for (const rule of rules) {
    const m = rule.match.exec(text);
    if (!m) continue;
    const line = text.split(/\r?\n/).find((l) => rule.match.test(l)) ?? text.split(/\r?\n/)[0] ?? '';
    let resolved = rule.stage ?? stage;
    if (!rule.stage) for (const [re, s] of STAGE_HINTS) if (re.test(text)) { resolved = s; break; }
    return { code: rule.code, title: rule.title, what: rule.what, why: rule.why, tryThis: rule.tryThis, fixes: rule.fixes, stage: resolved, raw: line, known: true };
  }
  let resolved = stage;
  for (const [re, s] of STAGE_HINTS) if (re.test(text)) { resolved = s; break; }
  return {
    code: 'unknown',
    title: 'Something went wrong',
    what: `The download stopped while ${stageLabels[resolved].toLowerCase()}.`,
    why: 'The engine reported a problem the app does not recognise.',
    tryThis: ['Try again.', 'Update the engine, since most unexplained failures are fixed by a newer version.', 'If it keeps happening, open the details and copy the report.'],
    fixes: ['retry', 'update-engine'],
    stage: resolved,
    raw: text.split(/\r?\n/)[0] ?? '',
    known: false,
  };
}

/** A process that ended without the engine printing an error. */
export function translateExit(code: number | null, signal: string | null, stage: Stage): Friendly {
  if (code === 2) return translate('yt-dlp: error: invalid option', stage);
  const base = translate('', stage);
  return {
    ...base,
    code: 'crashed',
    title: 'The engine stopped unexpectedly',
    what: `The engine quit while ${stageLabels[stage].toLowerCase()}${signal ? ` (signal ${signal})` : code !== null ? ` (exit code ${code})` : ''}.`,
    why: 'It may have been closed by the system, run out of memory, or hit a bug.',
    tryThis: ['Try again. Partial downloads are kept and resumed.', 'Update the engine.'],
    raw: `exit code ${code ?? 'none'}, signal ${signal ?? 'none'}`,
  };
}

export const knownCodes = rules.map((r) => r.code);
