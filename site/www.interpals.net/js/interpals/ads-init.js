/**
 * Header bidding glue: Prebid.js → Google Publisher Tag → Google Ad Manager.
 *
 * Reads JSON config from `window.__adsConfig` (emitted by adsHeadDefault.twig):
 *   {
 *     prebidUnits:  Prebid ad-unit definitions
 *     adSlots:      [{ slotId, gptName, sizes }]
 *     targeting:    { key: value | [values] } page-level GAM targeting
 *     refreshRate:  seconds, or null for no auto-refresh
 *   }
 *
 * Defines GPT slots, runs `pbjs.requestBids()`, sets winning bid targeting on
 * GPT, calls `googletag.pubads().refresh()`. Implements auto-refresh per
 * tier and exposes `window.adsRefresh()` for SPA route changes.
 */

(function () {
    'use strict';

    // SPA compatibility shim: aliased to the (possibly no-op) window.adsRefresh
    // below. Defined unconditionally so pages without ad slots — but with the
    // SPA shell — don't throw when useLoadMapping.ts calls reloadPubstream().
    window.adsRefresh = window.adsRefresh || function () {};
    window.reloadPubstream = window.adsRefresh;

    var config = window.__adsConfig || null;
    if (!config || !config.adSlots || !config.adSlots.length) {
        return;
    }

    var PREBID_TIMEOUT_MS = 1500;
    // Failsafe fires only if Prebid itself stalls and never invokes
    // bidsBackHandler. Sized just above PREBID_TIMEOUT_MS so a hung
    // auction doesn't hold the GAM request open longer than necessary.
    var FAILSAFE_TIMEOUT_MS = PREBID_TIMEOUT_MS + 200;
    var AD_NETWORK_PATH = '/1004604/';

    // Viewability gate for auto-refresh: require 50% of the slot to have
    // been within the viewport continuously for VIEWABILITY_DWELL_MS since
    // its last impression. Note: IntersectionObserver only checks viewport
    // intersection, not z-stack occlusion (a modal covering the slot still
    // counts as intersecting). For audited IAB MRC viewability we'd lean on
    // GAM Active View; this gate is a defensive proxy that matches the
    // refresh-not-billed behavior of the prior CPG bundle.
    var VIEWABILITY_THRESHOLD = 0.5;
    var VIEWABILITY_DWELL_MS = 1000;

    // Bidders authorized to drop iframe-based user-sync pixels. Explicit
    // allowlist (vs '*') so adding a bidder is a deliberate decision.
    var USER_SYNC_BIDDERS = ['sovrn', 'ix', 'rubicon', 'sharethrough'];

    var googletag = window.googletag = window.googletag || { cmd: [] };
    var pbjs = window.pbjs = window.pbjs || { que: [] };

    var definedSlots = [];
    var slotsByCode = {};
    var viewableState = {};   // slotId → { viewableSinceMs }
    var refreshTimer = null;
    var initialAuctionDone = false;

    googletag.cmd.push(function () {
        config.adSlots.forEach(function (slot) {
            var domEl = document.getElementById(slot.slotId);
            if (!domEl) return;

            var gptSlot = googletag
                .defineSlot(AD_NETWORK_PATH + slot.gptName, slot.sizes, slot.slotId);
            if (!gptSlot) return;

            gptSlot.addService(googletag.pubads());
            definedSlots.push(gptSlot);
            slotsByCode[slot.slotId] = gptSlot;
            observeViewability(slot.slotId, domEl);
        });

        // Page-level targeting via googletag.setConfig (the legacy
        // pubads().setTargeting per-key API is deprecated as of late 2024).
        if (config.targeting && Object.keys(config.targeting).length) {
            googletag.setConfig({ targeting: config.targeting });
        }

        googletag.pubads().enableSingleRequest();
        googletag.pubads().collapseEmptyDivs();
        googletag.pubads().disableInitialLoad();
        googletag.enableServices();

        definedSlots.forEach(function (slot) {
            googletag.display(slot);
        });
    });

    pbjs.que.push(function () {
        pbjs.setConfig({
            currency: { adServerCurrency: 'USD' },
            userSync: {
                syncEnabled: true,
                filterSettings: {
                    iframe: { bidders: USER_SYNC_BIDDERS, filter: 'include' }
                }
            },
            enableTIDs: true
        });
        if (config.prebidUnits && config.prebidUnits.length) {
            pbjs.addAdUnits(config.prebidUnits);
        }
    });

    function runAuction(adUnitCodes) {
        var failsafeFired = false;
        var auctionFinished = false;

        var failsafe = setTimeout(function () {
            failsafeFired = true;
            if (!auctionFinished) {
                sendBidsAndRefresh(adUnitCodes, { waitForPrebid: false });
            }
        }, FAILSAFE_TIMEOUT_MS);

        pbjs.que.push(function () {
            pbjs.requestBids({
                timeout: PREBID_TIMEOUT_MS,
                adUnitCodes: adUnitCodes,
                bidsBackHandler: function () {
                    auctionFinished = true;
                    clearTimeout(failsafe);
                    if (!failsafeFired) {
                        sendBidsAndRefresh(adUnitCodes);
                    }
                }
            });
        });
    }

    function sendBidsAndRefresh(adUnitCodes, options) {
        var waitForPrebid = !options || options.waitForPrebid !== false;

        if (waitForPrebid) {
            pbjs.que.push(function () {
                refreshGptSlots(adUnitCodes);
            });
            return;
        }

        refreshGptSlots(adUnitCodes);
    }

    function refreshGptSlots(adUnitCodes) {
        googletag.cmd.push(function () {
            if (typeof pbjs.setTargetingForGPTAsync === 'function') {
                try {
                    pbjs.setTargetingForGPTAsync(adUnitCodes);
                } catch (e) {
                    logError('setTargetingForGPTAsync failed', e);
                }
            }
            var slotsToRefresh = adUnitCodes
                .map(function (code) { return slotsByCode[code]; })
                .filter(Boolean);
            if (slotsToRefresh.length) {
                googletag.pubads().refresh(slotsToRefresh);
                // A refresh = new impression. Reset the dwell clock so the
                // next auto-refresh tick requires another viewable second.
                // If the slot is in-viewport, restart the clock from the
                // dispatch time; if it left the viewport, it stays at 0 until
                // the observer fires again.
                var now = Date.now();
                adUnitCodes.forEach(function (code) {
                    var state = viewableState[code];
                    if (state && state.viewableSinceMs) {
                        state.viewableSinceMs = now;
                    }
                });
            }
            initialAuctionDone = true;
        });
    }

    function refreshAll() {
        if (!definedSlots.length) return;
        var codes = config.adSlots.map(function (s) { return s.slotId; });
        runAuction(codes);
    }

    function refreshViewable() {
        if (!definedSlots.length) return;
        var now = Date.now();
        var codes = config.adSlots
            .map(function (s) { return s.slotId; })
            .filter(function (id) {
                var s = viewableState[id];
                return s && s.viewableSinceMs && (now - s.viewableSinceMs >= VIEWABILITY_DWELL_MS);
            });
        if (!codes.length) return;
        runAuction(codes);
    }

    function observeViewability(slotId, domEl) {
        viewableState[slotId] = { viewableSinceMs: 0 };
        if (!window.IntersectionObserver) {
            // Fallback: assume viewable so we don't suppress refresh
            // entirely on browsers without IntersectionObserver.
            viewableState[slotId].viewableSinceMs = 1;
            return;
        }
        var observer = new IntersectionObserver(function (entries) {
            var state = viewableState[slotId];
            if (!state) return;
            entries.forEach(function (entry) {
                // Use intersectionRatio rather than isIntersecting — the
                // latter is just "any overlap > 0" regardless of the
                // observer threshold (Chrome quirk in some cases).
                if (entry.intersectionRatio >= VIEWABILITY_THRESHOLD) {
                    // Stamp on enter; preserve existing stamp if already in
                    // viewport (IntersectionObserver can re-fire on viewport
                    // mutations without a real exit/enter cycle).
                    if (!state.viewableSinceMs) {
                        state.viewableSinceMs = Date.now();
                    }
                } else {
                    state.viewableSinceMs = 0;
                }
            });
        }, { threshold: VIEWABILITY_THRESHOLD });
        observer.observe(domEl);
    }

    function startAutoRefresh() {
        if (!config.refreshRate || config.refreshRate <= 0) return;
        if (refreshTimer) return;
        refreshTimer = setInterval(function () {
            if (document.hidden) return;
            if (!initialAuctionDone) return;
            refreshViewable();
        }, config.refreshRate * 1000);
    }

    function logError(message, error) {
        if (window.console && console.error) {
            console.error('[ads-init] ' + message, error);
        }
        if (window.Sentry && window.Sentry.captureException && error) {
            window.Sentry.captureException(error, { tags: { component: 'ads-init' } });
        }
    }

    var initialCodes = config.adSlots.map(function (s) { return s.slotId; });
    runAuction(initialCodes);
    startAutoRefresh();

    // SPA navigation hook — re-run the auction for currently-defined slots.
    // Replaces the no-op shim defined at the top of this IIFE.
    window.adsRefresh = function () {
        if (!initialAuctionDone) return;
        refreshAll();
    };
    window.reloadPubstream = window.adsRefresh;
})();
