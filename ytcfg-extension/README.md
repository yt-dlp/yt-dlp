# ytcfg Extractor

A minimal Chrome/Chromium extension (Manifest V3) that reproduces what yt-dlp's
`YoutubeBaseInfoExtractor.extract_ytcfg()` does, from inside the browser:

1. Adds an **"Extract ytcfg"** button on top of the video player on every
   YouTube watch page.
2. On click, it **re-downloads the watch page HTML** with `fetch()`
   (cookies included — same document yt-dlp would receive).
3. Runs the same regex yt-dlp uses (`ytcfg\.set\s*\(\s*({...})\s*\)\s*;`)
   over the raw HTML to capture the first `ytcfg.set({...});` call.
4. `JSON.parse`s the capture and `console.log`s the full object, plus the
   keys yt-dlp actually cares about: `INNERTUBE_CONTEXT`, `PLAYER_JS_URL`,
   `visitorData` and `STS`.

## Install

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** and select this `ytcfg-extension/` folder

## Use

1. Open any YouTube video (`youtube.com/watch?v=...`)
2. Open DevTools (F12) → **Console** tab
3. Click the red **Extract ytcfg** button in the top-left corner of the player
4. The parsed ytcfg object is logged to the console — expand it to explore

## Notes

- The page is fetched fresh rather than reading `window.ytcfg`, both to match
  yt-dlp's behavior and because content scripts run in an isolated JS world
  where the page's `ytcfg` global isn't directly accessible.
- YouTube is a single-page app, so the button is re-injected on every
  `yt-navigate-finish` event (video-to-video navigation without page reload).
- The console output appears in the *page's* console because content scripts
  share the page's console.
