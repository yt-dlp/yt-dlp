// ytcfg Extractor
//
// Mimics yt-dlp's YoutubeBaseInfoExtractor.extract_ytcfg():
//   1. download the watch page HTML (fetch of the current URL)
//   2. find the first  ytcfg.set({...});  call in the raw HTML
//   3. parse the captured JSON and console.log it
//
// Note: we deliberately re-fetch the HTML instead of reading window.ytcfg,
// both to match what yt-dlp does and because content scripts run in an
// isolated world where the page's ytcfg variable is not directly reachable.

'use strict';

const BUTTON_ID = 'ytcfg-extractor-btn';

// Same pattern as yt-dlp (_base.py extract_ytcfg), ported to JS.
// [\s\S] instead of a dotAll "." keeps it working across newlines,
// and the lazy +? makes it stop at the first "});" like the Python version.
const YTCFG_RE = /ytcfg\.set\s*\(\s*(\{[\s\S]+?\})\s*\)\s*;/;

function extractYtcfg(html) {
    const match = html.match(YTCFG_RE);
    if (!match) {
        return null;
    }
    return JSON.parse(match[1]);
}

async function onButtonClick(button) {
    const label = button.textContent;
    button.textContent = 'fetching…';
    button.disabled = true;
    try {
        // credentials:'include' sends your YouTube cookies, so the HTML is the
        // same one your logged-in session (and yt-dlp with --cookies) would get
        const response = await fetch(location.href, { credentials: 'include' });
        if (!response.ok) {
            throw new Error(`watch page request failed: HTTP ${response.status}`);
        }
        const html = await response.text();
        console.log(`[ytcfg-extractor] downloaded watch page: ${location.href} (${html.length} bytes)`);

        const ytcfg = extractYtcfg(html);
        if (!ytcfg) {
            console.warn('[ytcfg-extractor] no ytcfg.set({...}) call found in the page HTML');
            return;
        }

        console.log('[ytcfg-extractor] ytcfg:', ytcfg);
        // The keys yt-dlp actually consumes from this object:
        console.log('[ytcfg-extractor] INNERTUBE_CONTEXT:', ytcfg.INNERTUBE_CONTEXT);
        console.log('[ytcfg-extractor] PLAYER_JS_URL:', ytcfg.PLAYER_JS_URL);
        console.log('[ytcfg-extractor] visitorData:', ytcfg.INNERTUBE_CONTEXT?.client?.visitorData);
        console.log('[ytcfg-extractor] STS (signature timestamp):', ytcfg.STS);
    } catch (err) {
        console.error('[ytcfg-extractor] extraction failed:', err);
    } finally {
        button.textContent = label;
        button.disabled = false;
    }
}

function createButton() {
    const button = document.createElement('button');
    button.id = BUTTON_ID;
    button.textContent = 'Extract ytcfg';
    Object.assign(button.style, {
        position: 'absolute',
        top: '12px',
        left: '12px',
        zIndex: '9999',
        padding: '6px 12px',
        font: 'bold 13px/1.4 Roboto, Arial, sans-serif',
        color: '#fff',
        background: 'rgba(204, 0, 0, 0.9)',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        opacity: '0.85',
    });
    button.addEventListener('mouseenter', () => (button.style.opacity = '1'));
    button.addEventListener('mouseleave', () => (button.style.opacity = '0.85'));
    button.addEventListener('click', (e) => {
        e.stopPropagation();
        onButtonClick(button);
    });
    return button;
}

function placeButton() {
    // Only on watch pages, and only once
    if (!location.pathname.startsWith('/watch') || document.getElementById(BUTTON_ID)) {
        return;
    }
    const player = document.querySelector('#movie_player')
        || document.querySelector('ytd-player')
        || document.querySelector('#player');
    if (!player) {
        return;
    }
    // The player is position:relative, so an absolute child sits on the video
    player.appendChild(createButton());
}

// YouTube is a single-page app: video-to-video navigation never reloads the
// document, so run_at:document_idle alone isn't enough. YouTube fires its own
// event on every SPA navigation; the observer is a fallback for late-created
// player elements.
placeButton();
window.addEventListener('yt-navigate-finish', placeButton);
new MutationObserver(placeButton).observe(document.documentElement, {
    childList: true,
    subtree: true,
});
