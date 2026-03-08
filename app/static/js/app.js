/**
 * yt-dlp Desktop — Application Logic
 * Communicates with Python backend via pywebview JS bridge.
 */

(function () {
    'use strict';

    /* ==========================================
       State
       ========================================== */
    let currentInfo = null;
    let selectedFormatId = null;
    let progressInterval = null;
    let apiReady = false;

    /* ==========================================
       DOM References
       ========================================== */
    const qs = (sel) => document.querySelector(sel);
    const qsa = (sel) => document.querySelectorAll(sel);

    const urlInput = qs('#urlInput');
    const btnExtract = qs('#btnExtract');
    const btnPaste = qs('#btnPaste');
    const btnDownload = qs('#btnDownload');
    const btnSettings = qs('#btnSettings');
    const btnCloseSettings = qs('#btnCloseSettings');
    const btnSaveSettings = qs('#btnSaveSettings');
    const btnBrowseFolder = qs('#btnBrowseFolder');
    const btnClearHistory = qs('#btnClearHistory');
    const btnOpenFolder = qs('#btnOpenFolder');

    const loadingSection = qs('#loadingSection');
    const previewSection = qs('#previewSection');
    const downloadsSection = qs('#downloadsSection');
    const downloadsList = qs('#downloadsList');
    const emptyState = qs('#emptyState');
    const settingsModal = qs('#settingsModal');
    const formatList = qs('#formatList');

    /* ==========================================
       API Wrapper (waits for pywebview bridge)
       ========================================== */
    function waitForApi() {
        return new Promise((resolve) => {
            if (window.pywebview && window.pywebview.api) {
                apiReady = true;
                resolve();
                return;
            }
            window.addEventListener('pywebviewready', () => {
                apiReady = true;
                resolve();
            });
        });
    }

    async function api(method, ...args) {
        if (!apiReady) await waitForApi();
        const result = await window.pywebview.api[method](...args);
        return typeof result === 'string' ? JSON.parse(result) : result;
    }

    /* ==========================================
       Initialize
       ========================================== */
    async function init() {
        await waitForApi();
        loadConfig();
        refreshDownloads();
        startProgressPolling();
        bindEvents();
    }

    /* ==========================================
       Event Bindings
       ========================================== */
    function bindEvents() {
        // Extract
        btnExtract.addEventListener('click', handleExtract);
        urlInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') handleExtract();
        });

        // Paste
        btnPaste.addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                urlInput.value = text.trim();
                urlInput.focus();
            } catch {
                showToast('⚠️', 'Could not read clipboard');
            }
        });

        // Download
        btnDownload.addEventListener('click', handleDownload);

        // Settings
        btnSettings.addEventListener('click', () => settingsModal.style.display = 'flex');
        btnCloseSettings.addEventListener('click', () => settingsModal.style.display = 'none');
        settingsModal.addEventListener('click', (e) => {
            if (e.target === settingsModal) settingsModal.style.display = 'none';
        });
        btnSaveSettings.addEventListener('click', handleSaveSettings);
        btnBrowseFolder.addEventListener('click', handleBrowseFolder);

        // Clear History
        btnClearHistory.addEventListener('click', async () => {
            await api('clear_history');
            refreshDownloads();
        });

        // Open folder
        btnOpenFolder.addEventListener('click', () => api('open_folder'));

        // Update & Info buttons
        const btnCheckUpdate = qs('#btnCheckUpdate');
        const btnDoUpdate = qs('#btnDoUpdate');
        const btnInstallFFmpeg = qs('#btnInstallFFmpeg');

        if (btnCheckUpdate) btnCheckUpdate.addEventListener('click', checkForUpdates);
        if (btnDoUpdate) btnDoUpdate.addEventListener('click', handleUpdate);
        if (btnInstallFFmpeg) btnInstallFFmpeg.addEventListener('click', handleInstallFFmpeg);

        // Format tabs
        qsa('.format-tab').forEach((tab) => {
            tab.addEventListener('click', () => {
                qsa('.format-tab').forEach((t) => t.classList.remove('active'));
                tab.classList.add('active');
                filterFormats(tab.dataset.filter);
            });
        });

        // Load app info (versions, FFmpeg status)
        loadAppInfo();
    }

    /* ==========================================
       Extract Video Info
       ========================================== */
    async function handleExtract() {
        const url = urlInput.value.trim();
        if (!url) {
            showToast('⚠️', 'Please enter a URL');
            urlInput.focus();
            return;
        }

        previewSection.style.display = 'none';
        loadingSection.style.display = 'flex';
        btnExtract.disabled = true;

        try {
            const info = await api('extract_info', url);

            if (info.error) {
                showToast('❌', info.error);
                loadingSection.style.display = 'none';
                btnExtract.disabled = false;
                return;
            }

            currentInfo = info;
            renderPreview(info);
        } catch (err) {
            showToast('❌', 'Failed to extract video info');
        }

        loadingSection.style.display = 'none';
        btnExtract.disabled = false;
    }

    /* ==========================================
       Render Preview
       ========================================== */
    function renderPreview(info) {
        if (info.type === 'playlist') {
            // Simplified playlist display
            qs('#previewTitle').textContent = `📋 ${info.title} (${info.count} videos)`;
            qs('#previewChannel').textContent = 'Playlist';
            qs('#previewThumb').src = info.entries[0]?.thumbnail || '';
            qs('#previewDuration').textContent = `${info.count} videos`;
            qs('#previewViews').textContent = '';
            qs('#previewDate').textContent = '';
            formatList.innerHTML = '';
            selectedFormatId = 'best';
            previewSection.style.display = 'block';
            return;
        }

        // Single video
        qs('#previewTitle').textContent = info.title;
        qs('#previewChannel').textContent = info.uploader || '';
        qs('#previewThumb').src = info.thumbnail || '';
        qs('#previewDuration').textContent = formatDuration(info.duration);
        qs('#previewViews').textContent = info.view_count ? `${formatNumber(info.view_count)} views` : '';
        qs('#previewDate').textContent = info.upload_date ? formatDate(info.upload_date) : '';

        renderFormats(info.formats);
        previewSection.style.display = 'block';
    }

    /* ==========================================
       Render Formats
       ========================================== */
    function renderFormats(formats) {
        formatList.innerHTML = '';
        selectedFormatId = null;

        if (!formats || formats.length === 0) {
            formatList.innerHTML = '<p style="color:var(--text-muted);padding:12px;">No formats available</p>';
            return;
        }

        // Deduplicate and simplify format list
        const simplified = simplifyFormats(formats);

        simplified.forEach((f, i) => {
            const el = document.createElement('div');
            el.className = 'format-item';
            el.dataset.formatId = f.format_id;
            el.dataset.hasVideo = f.has_video;
            el.dataset.hasAudio = f.has_audio;

            const qualityClass = f.height >= 1080 ? 'quality-high'
                : f.height >= 480 ? 'quality-mid' : 'quality-low';

            el.innerHTML = `
                <div class="format-radio"></div>
                <span class="format-label">${f.label}</span>
                <span class="format-quality ${qualityClass}">${f.quality}</span>
                <span class="format-ext">${f.ext}</span>
                <span class="format-size">${formatBytes(f.filesize)}</span>
            `;

            el.addEventListener('click', () => {
                qsa('.format-item').forEach((item) => item.classList.remove('selected'));
                el.classList.add('selected');
                selectedFormatId = f.format_id;
            });

            // Auto-select first
            if (i === 0) {
                el.classList.add('selected');
                selectedFormatId = f.format_id;
            }

            formatList.appendChild(el);
        });
    }

    function simplifyFormats(formats) {
        const result = [];

        // Add "Best (auto)" as first option
        result.push({
            format_id: 'bestvideo+bestaudio/best',
            label: 'Best Quality (Auto)',
            quality: 'BEST',
            ext: 'mp4',
            filesize: 0,
            has_video: true,
            has_audio: true,
            height: 9999,
        });

        // Group key formats
        const seen = new Set();
        for (const f of formats) {
            const key = `${f.height || 0}-${f.has_video}-${f.has_audio}-${f.ext}`;
            if (seen.has(key)) continue;
            seen.add(key);

            let label, quality;
            if (f.has_video && f.has_audio) {
                label = `${f.resolution} • ${f.ext}`;
                quality = f.height ? `${f.height}p` : f.format_note || 'SD';
            } else if (f.has_video) {
                label = `${f.resolution} (video only) • ${f.ext}`;
                quality = f.height ? `${f.height}p` : 'Video';
            } else {
                const abr = f.tbr ? `${Math.round(f.tbr)}kbps` : '';
                label = `Audio ${abr} • ${f.ext}`;
                quality = abr || 'Audio';
            }

            result.push({
                format_id: f.format_id,
                label,
                quality,
                ext: f.ext,
                filesize: f.filesize,
                has_video: f.has_video,
                has_audio: f.has_audio,
                height: f.height || 0,
            });
        }

        return result.slice(0, 25); // Limit for UI performance
    }

    function filterFormats(filter) {
        qsa('.format-item').forEach((el) => {
            const hasVideo = el.dataset.hasVideo === 'true';
            const hasAudio = el.dataset.hasAudio === 'true';

            if (filter === 'all') {
                el.style.display = '';
            } else if (filter === 'video') {
                el.style.display = hasVideo ? '' : 'none';
            } else if (filter === 'audio') {
                el.style.display = (!hasVideo && hasAudio) ? '' : 'none';
            }
        });
    }

    /* ==========================================
       Download
       ========================================== */
    async function handleDownload() {
        if (!currentInfo) {
            showToast('⚠️', 'Extract a video first');
            return;
        }

        const format = selectedFormatId || 'best';
        const url = currentInfo.webpage_url || urlInput.value.trim();
        const title = currentInfo.title || '';
        const thumbnail = currentInfo.thumbnail || '';

        btnDownload.disabled = true;

        try {
            const result = await api('start_download', url, format, title, thumbnail);
            if (result.id) {
                showToast('🚀', 'Download started!');
                refreshDownloads();
            }
        } catch (err) {
            showToast('❌', 'Failed to start download');
        }

        btnDownload.disabled = false;
    }

    /* ==========================================
       Downloads List
       ========================================== */
    async function refreshDownloads() {
        try {
            const downloads = await api('get_downloads');
            renderDownloads(downloads);
        } catch {
            // API not ready yet
        }
    }

    function renderDownloads(downloads) {
        if (!downloads || downloads.length === 0) {
            downloadsList.innerHTML = '';
            downloadsList.appendChild(emptyState);
            emptyState.style.display = 'flex';
            return;
        }

        emptyState.style.display = 'none';

        // Preserve structure, update content
        downloadsList.innerHTML = '';
        downloads.forEach((dl) => {
            const el = document.createElement('div');
            el.className = 'download-item';
            el.id = `dl-${dl.id}`;

            const statusClass = `status-${dl.status}`;
            const showProgress = dl.status === 'downloading' || dl.status === 'pending';

            el.innerHTML = `
                <img class="dl-thumb" src="${dl.thumbnail || ''}" alt="" onerror="this.style.display='none'">
                <div class="dl-info">
                    <div class="dl-title">${escapeHtml(dl.title || dl.url)}</div>
                    <div class="dl-meta">
                        ${dl.speed ? `<span>⚡ ${dl.speed}</span>` : ''}
                        ${dl.eta ? `<span>⏱ ${dl.eta}</span>` : ''}
                        ${dl.filesize ? `<span>📦 ${dl.filesize}</span>` : ''}
                    </div>
                </div>
                ${showProgress ? `
                <div class="dl-progress-wrap">
                    <div class="dl-progress-bar">
                        <div class="dl-progress-fill" style="width:${dl.progress}%"></div>
                    </div>
                    <div class="dl-progress-text">${dl.progress.toFixed(1)}%</div>
                </div>
                ` : ''}
                <span class="dl-status ${statusClass}">${dl.status}</span>
                <div class="dl-actions">
                    ${dl.status === 'downloading' ? `
                        <button class="btn-icon" onclick="app.cancelDownload('${dl.id}')" title="Cancel">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    ` : ''}
                    ${dl.status === 'finished' || dl.status === 'error' || dl.status === 'cancelled' ? `
                        <button class="btn-icon" onclick="app.removeDownload('${dl.id}')" title="Remove">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                            </svg>
                        </button>
                    ` : ''}
                </div>
            `;

            downloadsList.appendChild(el);
        });
    }

    /* ==========================================
       Progress Polling
       ========================================== */
    function startProgressPolling() {
        progressInterval = setInterval(async () => {
            try {
                const active = await api('get_progress');
                if (active && active.length > 0) {
                    // Update in-place for smoother UX
                    active.forEach((dl) => {
                        const el = document.getElementById(`dl-${dl.id}`);
                        if (el) {
                            const fill = el.querySelector('.dl-progress-fill');
                            const text = el.querySelector('.dl-progress-text');
                            const meta = el.querySelector('.dl-meta');
                            if (fill) fill.style.width = `${dl.progress}%`;
                            if (text) text.textContent = `${dl.progress.toFixed(1)}%`;
                            if (meta) {
                                meta.innerHTML = `
                                    ${dl.speed ? `<span>⚡ ${dl.speed}</span>` : ''}
                                    ${dl.eta ? `<span>⏱ ${dl.eta}</span>` : ''}
                                    ${dl.filesize ? `<span>📦 ${dl.filesize}</span>` : ''}
                                `;
                            }
                        }
                    });
                } else {
                    // Check for status changes (finished, error)
                    refreshDownloads();
                }
            } catch {
                // Silently ignore polling errors
            }
        }, 800);
    }

    /* ==========================================
       Settings
       ========================================== */
    async function loadConfig() {
        try {
            const config = await api('get_config');
            qs('#settingOutputDir').value = config.output_dir || '';
            qs('#settingFormat').value = config.default_format || 'best';
            qs('#settingEmbedThumb').checked = config.embed_thumbnail !== false;
            qs('#settingEmbedMeta').checked = config.embed_metadata !== false;
            qs('#settingSubtitles').checked = config.write_subtitles || false;
        } catch {
            // Config not available yet
        }
    }

    async function handleSaveSettings() {
        const config = {
            output_dir: qs('#settingOutputDir').value,
            default_format: qs('#settingFormat').value,
            embed_thumbnail: qs('#settingEmbedThumb').checked,
            embed_metadata: qs('#settingEmbedMeta').checked,
            write_subtitles: qs('#settingSubtitles').checked,
        };

        try {
            const result = await api('update_config', JSON.stringify(config));
            if (result.success) {
                showToast('✅', 'Settings saved');
                settingsModal.style.display = 'none';
            }
        } catch {
            showToast('❌', 'Failed to save settings');
        }
    }

    async function handleBrowseFolder() {
        try {
            const result = await api('browse_folder');
            if (result.path) {
                qs('#settingOutputDir').value = result.path;
            }
        } catch {
            showToast('❌', 'Could not open folder picker');
        }
    }

    /* ==========================================
       App Info, Updates & Dependencies
       ========================================== */

    async function loadAppInfo() {
        try {
            const info = await api('get_app_info');
            const vBadge = qs('#versionBadge');
            const fBadge = qs('#ffmpegBadge');

            if (vBadge && info.ytdlp_version) {
                vBadge.textContent = `v${info.ytdlp_version}`;
            }

            if (fBadge) {
                if (info.ffmpeg_available) {
                    fBadge.textContent = '✔ FFmpeg';
                    fBadge.className = 'ffmpeg-badge available';
                } else {
                    fBadge.textContent = '✘ FFmpeg';
                    fBadge.className = 'ffmpeg-badge missing';
                    fBadge.title = 'FFmpeg not found — click to install';
                    fBadge.addEventListener('click', handleInstallFFmpeg);

                    // Show install button in settings
                    const btn = qs('#btnInstallFFmpeg');
                    if (btn) btn.style.display = 'inline-flex';
                }
            }

            // Also check for updates in background
            checkForUpdates();
        } catch {
            // API not ready yet
        }
    }

    async function checkForUpdates() {
        const statusEl = qs('#updateStatus');
        const textEl = qs('#updateText');
        const btnUpdate = qs('#btnDoUpdate');
        const btnInstall = qs('#btnInstallFFmpeg');

        if (textEl) textEl.textContent = 'Checking for updates...';
        if (statusEl) {
            statusEl.className = 'update-status';
        }

        try {
            const info = await api('check_update');

            if (info.available) {
                if (textEl) textEl.textContent = `Update available: ${info.current} → ${info.latest}`;
                if (statusEl) statusEl.className = 'update-status has-update';
                if (btnUpdate) btnUpdate.style.display = 'inline-flex';
            } else {
                if (textEl) textEl.textContent = `yt-dlp ${info.current || ''} — up to date ✔`;
                if (statusEl) statusEl.className = 'update-status up-to-date';
                if (btnUpdate) btnUpdate.style.display = 'none';
            }

            // Check FFmpeg
            const appInfo = await api('get_app_info');
            if (!appInfo.ffmpeg_available && btnInstall) {
                btnInstall.style.display = 'inline-flex';
            }
        } catch {
            if (textEl) textEl.textContent = 'Could not check for updates';
        }
    }

    async function handleUpdate() {
        const textEl = qs('#updateText');
        const btnUpdate = qs('#btnDoUpdate');

        if (textEl) textEl.textContent = 'Updating yt-dlp... please wait';
        if (btnUpdate) btnUpdate.disabled = true;

        try {
            const result = await api('do_update');
            if (result.success) {
                showToast('✅', `yt-dlp updated to ${result.version}`);
                if (textEl) textEl.textContent = `Updated to ${result.version} ✔ (restart app to apply)`;
                const statusEl = qs('#updateStatus');
                if (statusEl) statusEl.className = 'update-status up-to-date';
                if (btnUpdate) btnUpdate.style.display = 'none';

                // Update header badge
                const vBadge = qs('#versionBadge');
                if (vBadge && result.version) vBadge.textContent = `v${result.version}`;
            } else {
                showToast('❌', 'Update failed');
                if (textEl) textEl.textContent = 'Update failed — try again later';
            }
        } catch {
            showToast('❌', 'Update failed');
        } finally {
            if (btnUpdate) btnUpdate.disabled = false;
        }
    }

    async function handleInstallFFmpeg() {
        const btnInstall = qs('#btnInstallFFmpeg');
        const fBadge = qs('#ffmpegBadge');

        showToast('⏬', 'Downloading FFmpeg... this may take a minute');
        if (btnInstall) {
            btnInstall.textContent = 'Installing...';
            btnInstall.disabled = true;
        }

        try {
            const result = await api('install_ffmpeg_dep');
            if (result.success) {
                showToast('✅', 'FFmpeg installed successfully!');
                if (btnInstall) btnInstall.style.display = 'none';
                if (fBadge) {
                    fBadge.textContent = '✔ FFmpeg';
                    fBadge.className = 'ffmpeg-badge available';
                    fBadge.title = 'FFmpeg available';
                }
            } else {
                showToast('❌', 'FFmpeg install failed');
            }
        } catch {
            showToast('❌', 'FFmpeg install failed');
        } finally {
            if (btnInstall) {
                btnInstall.textContent = 'Install FFmpeg';
                btnInstall.disabled = false;
            }
        }
    }

    /* ==========================================
       Utilities
       ========================================== */
    function formatDuration(seconds) {
        if (!seconds) return '';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        return `${m}:${String(s).padStart(2, '0')}`;
    }

    function formatNumber(num) {
        if (!num) return '';
        if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
        if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
        if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
        return num.toString();
    }

    function formatDate(dateStr) {
        if (!dateStr || dateStr.length !== 8) return '';
        return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
    }

    function formatBytes(bytes) {
        if (!bytes) return '';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function showToast(icon, message) {
        const toast = qs('#toast');
        qs('#toastIcon').textContent = icon;
        qs('#toastMessage').textContent = message;
        toast.style.display = 'flex';
        toast.style.animation = 'none';
        toast.offsetHeight; // Force reflow
        toast.style.animation = 'slideUp 0.3s ease';
        clearTimeout(toast._timeout);
        toast._timeout = setTimeout(() => {
            toast.style.display = 'none';
        }, 3000);
    }

    /* ==========================================
       Public API (for inline onclick handlers)
       ========================================== */
    window.app = {
        cancelDownload: async (id) => {
            await api('cancel_download', id);
            refreshDownloads();
            showToast('🛑', 'Download cancelled');
        },
        removeDownload: async (id) => {
            await api('remove_download', id);
            refreshDownloads();
        },
    };

    /* ==========================================
       Boot
       ========================================== */
    init();

})();
