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
  const route = hash.startsWith('#/downloads') ? 'downloads' : 'library';
  document.querySelector(`nav a[data-nav="${route}"]`).classList.add('active');

  if (hash.startsWith('#/series/')) {
    viewSeries(decodeURIComponent(hash.slice('#/series/'.length)));
  } else if (hash.startsWith('#/watch/')) {
    viewWatch(decodeURIComponent(hash.slice('#/watch/'.length)));
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
