'use strict';

const app = document.getElementById('app');
let libraryCache = null;
let pollTimer = null;

// ---------------------------------------------------------------- utilitaires

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));

const streamUrl = (path) => '/api/stream/' + path.split('/').map(encodeURIComponent).join('/');

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

async function getLibrary(force = false) {
  if (!libraryCache || force) libraryCache = await api('/api/library');
  return libraryCache;
}

// position de lecture et épisodes vus (localStorage)
const seen = () => new Set(JSON.parse(localStorage.getItem('anistream.seen') || '[]'));
const markSeen = (path) => {
  const s = seen(); s.add(path);
  localStorage.setItem('anistream.seen', JSON.stringify([...s]));
};
const savePos = (path, t) => localStorage.setItem('anistream.pos.' + path, String(t));
const getPos = (path) => parseFloat(localStorage.getItem('anistream.pos.' + path) || '0');

const fmtSpeed = (b) => b ? (b / 1048576).toFixed(1) + ' Mo/s' : '';
const fmtEta = (s) => s ? `~${Math.ceil(s / 60)} min restantes` : '';
const fmtDuration = (s) => {
  if (!s) return '';
  s = Math.round(s);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(sec).padStart(2, '0');
};

// ---------------------------------------------------------------- vues

async function viewLibrary() {
  const lib = await getLibrary(true);
  if (!lib.length) {
    app.innerHTML = `<h1>Bibliothèque</h1>
      <div class="empty">Aucune série pour l'instant.<br>
      Ajoute un premier épisode depuis l'onglet <a href="#/downloads">Téléchargements</a>.</div>`;
    return;
  }
  app.innerHTML = `<h1>Bibliothèque</h1><div class="grid">` + lib.map((s) => `
    <div class="card" data-series="${esc(s.name)}">
      <div class="cover" ${s.cover ? `style="background-image:url('${streamUrl(s.cover)}')"` : ''}>${s.cover ? '' : '🎬'}</div>
      <div class="meta">
        <div class="name" title="${esc(s.name)}">${esc(s.name)}</div>
        <div class="count">${s.episodes.length} épisode${s.episodes.length > 1 ? 's' : ''}</div>
      </div>
    </div>`).join('') + '</div>';
  app.querySelectorAll('.card').forEach((c) =>
    c.addEventListener('click', () => { location.hash = '#/series/' + encodeURIComponent(c.dataset.series); }));
}

async function viewSeries(name) {
  const lib = await getLibrary();
  const series = lib.find((s) => s.name === name);
  if (!series) { location.hash = '#/'; return; }
  const vus = seen();

  const groups = new Map();
  for (const ep of series.episodes) {
    const key = ep.season || '';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(ep);
  }

  let html = `<a class="back" href="#/">← Bibliothèque</a><h1>${esc(series.name)}</h1>`;
  for (const [season, eps] of groups) {
    if (season) html += `<h2>${esc(season)}</h2>`;
    html += '<div class="ep-list">' + eps.map((ep) => `
      <div class="ep" data-path="${esc(ep.path)}">
        <div class="thumb" ${ep.thumb ? `style="background-image:url('${streamUrl(ep.thumb)}')"` : ''}></div>
        <div class="ep-title">${esc(ep.title)}</div>
        ${vus.has(ep.path) ? '<span class="seen">✓ vu</span>' : ''}
        <button class="del" title="Supprimer l'épisode">🗑</button>
      </div>`).join('') + '</div>';
  }
  app.innerHTML = html;

  app.querySelectorAll('.ep').forEach((el) => {
    el.addEventListener('click', () => {
      location.hash = '#/watch/' + encodeURIComponent(el.dataset.path);
    });
    el.querySelector('.del').addEventListener('click', async (e) => {
      e.stopPropagation();
      if (!confirm('Supprimer cet épisode du disque ?')) return;
      await api('/api/media/' + el.dataset.path.split('/').map(encodeURIComponent).join('/'), { method: 'DELETE' });
      await getLibrary(true);
      viewSeries(name);
    });
  });
}

async function viewWatch(path) {
  const lib = await getLibrary();
  let series = null, ep = null, flat = [];
  for (const s of lib) {
    for (const e of s.episodes) {
      if (e.path === path) { series = s; ep = e; }
    }
  }
  if (!ep) { location.hash = '#/'; return; }
  flat = series.episodes;
  const idx = flat.findIndex((e) => e.path === path);
  const next = flat[idx + 1];

  const tracks = ep.subs.map((s, i) =>
    `<track kind="subtitles" label="${esc(s.lang)}" srclang="${esc(s.lang)}" src="${streamUrl(s.path)}" ${i === 0 ? 'default' : ''}>`).join('');

  app.innerHTML = `
    <a class="back" href="#/series/${encodeURIComponent(series.name)}">← ${esc(series.name)}</a>
    <div class="player-wrap">
      <video controls autoplay src="${streamUrl(ep.path)}" ${ep.thumb ? `poster="${streamUrl(ep.thumb)}"` : ''}>${tracks}</video>
      <div class="player-bar">
        <span class="title">${esc(ep.title)}</span>
        ${next ? `<a class="btn" href="#/watch/${encodeURIComponent(next.path)}">Épisode suivant →</a>` : ''}
      </div>
    </div>`;

  const video = app.querySelector('video');
  const resume = getPos(path);
  if (resume > 5) video.currentTime = resume;
  video.addEventListener('timeupdate', () => {
    if (video.currentTime > 0) savePos(path, video.currentTime);
    if (video.duration && video.currentTime / video.duration > 0.9) markSeen(path);
  });
  video.addEventListener('ended', () => {
    markSeen(path);
    savePos(path, 0);
    if (next) location.hash = '#/watch/' + encodeURIComponent(next.path);
  });
}

let lastSearch = { q: '', mode: 'videos', data: null };

async function viewSearch() {
  app.innerHTML = `
    <h1>Recherche</h1>
    <form class="dl-form search-form" id="search-form">
      <label>Animé ou série à chercher
        <input name="q" placeholder="One Piece épisode 1 vostfr…" required value="${esc(lastSearch.q)}">
      </label>
      <label>Type
        <select name="mode">
          <option value="videos" ${lastSearch.mode === 'videos' ? 'selected' : ''}>Vidéos / épisodes (tous sites)</option>
          <option value="playlists" ${lastSearch.mode === 'playlists' ? 'selected' : ''}>Playlists YouTube (saisons)</option>
        </select>
      </label>
      <button type="submit">Rechercher</button>
    </form>
    <div id="search-results"></div>
    <p class="hint">La recherche interroge YouTube, Google Vidéo et Yahoo (méta-moteurs couvrant de
    nombreux sites), BiliBili et NicoNico, puis yt-dlp télécharge depuis le site trouvé.
    Tu peux aussi coller directement une URL dans l'onglet Téléchargements.</p>`;

  document.getElementById('search-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target;
    const q = f.q.value.trim(), mode = f.mode.value;
    const box = document.getElementById('search-results');
    const btn = f.querySelector('button');
    btn.disabled = true;
    box.innerHTML = '<div class="empty">Recherche en cours sur tous les sites…</div>';
    try {
      const data = await api(`/api/search?q=${encodeURIComponent(q)}&mode=${mode}`);
      lastSearch = { q, mode, data };
      renderSearchResults(data);
    } catch (err) {
      box.innerHTML = `<div class="empty">Erreur : ${esc(err.message)}</div>`;
    } finally {
      btn.disabled = false;
    }
  });

  if (lastSearch.data) renderSearchResults(lastSearch.data);
}

function renderSearchResults(data) {
  const box = document.getElementById('search-results');
  if (!box) return;
  const bySite = new Map();
  for (const r of data.results) {
    if (!bySite.has(r.site)) bySite.set(r.site, []);
    bySite.get(r.site).push(r);
  }
  let html = '';
  if (data.failed_sources.length) {
    html += `<p class="hint">Sans réponse : ${data.failed_sources.map(esc).join(', ')}</p>`;
  }
  if (!data.results.length) {
    box.innerHTML = html + '<div class="empty">Aucun résultat.</div>';
    return;
  }
  for (const [site, results] of bySite) {
    html += `<h2>${esc(site)} (${results.length})</h2><div class="ep-list">` + results.map((r, i) => `
      <div class="result" data-url="${esc(r.url)}">
        <div class="ep result-row">
          <div class="ep-title">
            ${r.is_playlist ? '<span class="pill">playlist</span> ' : ''}${esc(r.title)}
            <div class="sub">${esc(r.source)}${r.uploader ? ' · ' + esc(r.uploader) : ''}${r.duration ? ' · ' + fmtDuration(r.duration) : ''}</div>
          </div>
          <a class="btn secondary" href="${esc(r.url)}" target="_blank" rel="noopener">Ouvrir</a>
          <button class="pick">Télécharger</button>
        </div>
        <form class="dl-form confirm-form" hidden>
          <label>Série (dossier)
            <input name="series" required value="${esc(data.query)}">
          </label>
          <label>Saison (optionnel)
            <input name="season" type="number" min="0" placeholder="1">
          </label>
          <button type="submit">Lancer</button>
        </form>
      </div>`).join('') + '</div>';
  }
  box.innerHTML = html;

  box.querySelectorAll('.result').forEach((el) => {
    const form = el.querySelector('.confirm-form');
    el.querySelector('.pick').addEventListener('click', () => { form.hidden = !form.hidden; });
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = form.querySelector('button');
      btn.disabled = true;
      try {
        await api('/api/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: el.dataset.url,
            series: form.series.value.trim(),
            season: form.season.value ? parseInt(form.season.value, 10) : null,
          }),
        });
        btn.textContent = 'Lancé ✓';
      } catch (err) {
        alert('Erreur : ' + err.message);
        btn.disabled = false;
      }
    });
  });
}

async function viewDownloads() {
  app.innerHTML = `
    <h1>Téléchargements</h1>
    <form class="dl-form" id="dl-form">
      <label>URL de l'épisode ou de la saison (playlist)
        <input name="url" placeholder="https://…" required>
      </label>
      <label>Série (dossier de la bibliothèque)
        <input name="series" placeholder="One Piece" required list="series-names">
      </label>
      <label>Saison (optionnel)
        <input name="season" type="number" min="0" placeholder="1">
      </label>
      <button type="submit">Télécharger</button>
      <datalist id="series-names"></datalist>
    </form>
    <div id="jobs"></div>
    <p class="hint">Fonctionne avec tous les sites supportés par yt-dlp (~1800). Les plateformes protégées
    par DRM (Crunchyroll, Netflix, ADN…) ne sont pas prises en charge.</p>`;

  getLibrary().then((lib) => {
    document.getElementById('series-names').innerHTML =
      lib.map((s) => `<option value="${esc(s.name)}">`).join('');
  }).catch(() => {});

  document.getElementById('dl-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target;
    const body = {
      url: f.url.value.trim(),
      series: f.series.value.trim(),
      season: f.season.value ? parseInt(f.season.value, 10) : null,
    };
    const btn = f.querySelector('button');
    btn.disabled = true;
    try {
      await api('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      f.url.value = '';
      renderJobs();
    } catch (err) {
      alert('Erreur : ' + err.message);
    } finally {
      btn.disabled = false;
    }
  });

  renderJobs();
}

const STATUS_LABEL = {
  queued: ["en file d'attente", 'status-active'],
  downloading: ['téléchargement', 'status-active'],
  processing: ['traitement (ffmpeg)…', 'status-active'],
  done: ['terminé ✓', 'status-done'],
  error: ['échec', 'status-error'],
};

async function renderJobs() {
  const box = document.getElementById('jobs');
  if (!box) return;
  let jobsList;
  try { jobsList = await api('/api/downloads'); } catch { return; }

  const active = jobsList.filter((j) => ['queued', 'downloading', 'processing'].includes(j.status)).length;
  const badge = document.getElementById('dl-badge');
  badge.hidden = active === 0;
  badge.textContent = active;

  if (!jobsList.length) {
    box.innerHTML = '<div class="empty">Aucun téléchargement.</div>';
  } else {
    const hasFinished = jobsList.some((j) => ['done', 'error'].includes(j.status));
    box.innerHTML = jobsList.slice().reverse().map((j) => {
      const [label, cls] = STATUS_LABEL[j.status] || [j.status, ''];
      const details = j.status === 'downloading'
        ? [j.progress != null ? j.progress + ' %' : '', fmtSpeed(j.speed), fmtEta(j.eta)].filter(Boolean).join(' · ')
        : (j.error || '');
      return `<div class="job">
        <div class="row">
          <span class="job-title">${esc(j.title || j.url)}</span>
          <span class="${cls}">${label}</span>
        </div>
        <div class="sub">${esc(j.series)}${j.season != null ? ' · Saison ' + j.season : ''}${details ? ' — ' + esc(details) : ''}</div>
        ${['downloading', 'processing'].includes(j.status)
          ? `<div class="progress"><div style="width:${j.progress || 0}%"></div></div>` : ''}
      </div>`;
    }).join('') + (hasFinished
      ? '<button class="secondary" id="clear-jobs">Effacer les terminés</button>' : '');
    const clear = document.getElementById('clear-jobs');
    if (clear) clear.addEventListener('click', async () => {
      await api('/api/downloads/clear', { method: 'POST' });
      renderJobs();
    });
  }
}

// ---------------------------------------------------------------- routeur

function router() {
  clearInterval(pollTimer);
  const hash = location.hash || '#/';
  document.querySelectorAll('nav a').forEach((a) => a.classList.remove('active'));
  const route = hash.startsWith('#/downloads') ? 'downloads'
    : hash.startsWith('#/search') ? 'search' : 'library';
  document.querySelector(`nav a[data-nav="${route}"]`).classList.add('active');

  if (hash.startsWith('#/series/')) {
    viewSeries(decodeURIComponent(hash.slice('#/series/'.length)));
  } else if (hash.startsWith('#/watch/')) {
    viewWatch(decodeURIComponent(hash.slice('#/watch/'.length)));
  } else if (hash.startsWith('#/search')) {
    viewSearch();
  } else if (hash.startsWith('#/downloads')) {
    viewDownloads();
    pollTimer = setInterval(renderJobs, 2000);
  } else {
    viewLibrary();
  }
}

window.addEventListener('hashchange', router);
router();
// met à jour le badge des téléchargements actifs même hors de l'onglet
setInterval(async () => {
  if (!document.getElementById('jobs')) {
    try {
      const jobsList = await api('/api/downloads');
      const active = jobsList.filter((j) => ['queued', 'downloading', 'processing'].includes(j.status)).length;
      const badge = document.getElementById('dl-badge');
      badge.hidden = active === 0;
      badge.textContent = active;
    } catch { /* serveur injoignable : on réessaiera */ }
  }
}, 5000);
