// Things the user can do to a download, shared by the queue, history and menus.
import type { FixId } from '../shared/errors';
import type { Job } from '../shared/types';
import { api, blankDraft, get, set, toast } from './state';
import { ask } from './ui';

const BROWSERS = ['firefox', 'chrome', 'edge', 'brave', 'chromium', 'opera', 'safari', 'vivaldi', 'whale'];

export function editJob(job: Job): void {
  const s = get();
  // The stored values are already the full set, so they go in as advanced values over a neutral base.
  const base = s.settings.baseValues;
  const advanced = Object.fromEntries(Object.entries(job.values).filter(([k, v]) => JSON.stringify(base[k]) !== JSON.stringify(v) && k !== '--paths'));
  const folder = Array.isArray(job.values['--paths']) ? String((job.values['--paths'] as string[])[0] ?? '') : s.settings.downloadFolder;
  set({
    view: 'new',
    draft: {
      ...blankDraft(s.settings), text: job.url, advanced, extraArgs: job.extraArgs, tab: 'advanced', editJobId: job.id,
      simple: { ...blankDraft(s.settings).simple, kind: 'video', quality: 'best', container: 'auto', metadata: false, thumbnail: false, subtitles: false, playlist: 'default', folder },
    },
    previews: { ...s.previews },
  });
}

export async function runFix(job: Job, fix: FixId): Promise<void> {
  switch (fix) {
    case 'pick-folder': {
      const folder = await api.pickFolder();
      if (!folder) return;
      await api.updateJob(job.id, { values: { ...job.values, '--paths': [folder] } }, true);
      return;
    }
    case 'browser-cookies':
      ask({
        title: 'Use cookies from a browser',
        body: 'Pick the browser where you are signed in to this site. The app reads its cookies for this download only. Close the browser first if the lookup fails.',
        choices: BROWSERS.map((b) => ({ value: b, label: b[0].toUpperCase() + b.slice(1) })),
        confirm: 'Use and retry',
        onConfirm: (browser) => { void api.updateJob(job.id, { values: { ...job.values, '--cookies-from-browser': browser } }, true); },
      });
      return;
    case 'check-links':
      ask({
        title: 'Edit link', input: { label: 'Link', value: job.url }, confirm: 'Save and retry',
        onConfirm: (url) => { if (url.trim()) void api.updateJob(job.id, { url: url.trim() }, true); },
      });
      return;
    case 'edit-options': editJob(job); return;
    default: {
      if (fix === 'update-engine') toast('Updating the engine. This can take a minute.');
      if (fix === 'install-ffmpeg') toast('Downloading ffmpeg. This can take a minute.');
      const r = await api.applyFix(job.id, fix);
      if (!r.ok) toast(r.message ?? 'That did not work.');
      else if (fix === 'retry-later') toast('Scheduled to retry in 15 minutes.');
      if (fix === 'update-engine' || fix === 'install-ffmpeg') set({ engine: await api.engineInfo() });
    }
  }
}

export async function redownload(job: Job): Promise<void> {
  await api.addJobs([{ url: job.url, title: job.title, thumbnail: job.thumbnail, uploader: job.uploader, duration: job.duration, summary: job.summary, values: job.values, extraArgs: job.extraArgs }]);
  set({ view: 'queue' });
}

export async function copyReport(job: Job): Promise<void> {
  await api.copyText(await api.jobReport(job.id));
  toast('Report copied. Passwords, cookies and your user name are left out.');
}

export async function jobMenu(job: Job, inHistory = false): Promise<void> {
  const active = job.state === 'running';
  const file = job.files[0];
  const picked = await api.popupMenu([
    ...(!inHistory ? [
      { id: 'pause', label: 'Pause', enabled: active || job.state === 'queued' || job.state === 'scheduled' },
      { id: 'resume', label: job.state === 'scheduled' ? 'Start Now' : 'Resume', enabled: job.state === 'paused' || job.state === 'scheduled' },
      { id: 'retry', label: job.state === 'done' ? 'Download Again' : 'Retry', enabled: ['error', 'cancelled', 'done'].includes(job.state) },
      { id: 'cancel', label: 'Cancel', enabled: ['running', 'queued', 'paused', 'scheduled'].includes(job.state) },
      { type: 'separator' as const },
    ] : [{ id: 'again', label: 'Download Again' }, { type: 'separator' as const }]),
    { id: 'open', label: 'Open File', enabled: !!file },
    { id: 'show', label: api.platform === 'darwin' ? 'Show in Finder' : 'Show in Folder', enabled: !!file },
    { type: 'separator' },
    { id: 'copy-url', label: 'Copy Link', enabled: !!job.url },
    { id: 'copy-cmd', label: 'Copy Command' },
    { id: 'report', label: 'Copy Problem Report' },
    { id: 'log', label: 'Open Log' },
    ...(!inHistory ? [{ id: 'edit', label: 'Edit Options…', enabled: !active }] : []),
    { type: 'separator' },
    { id: 'remove', label: inHistory ? 'Remove from History' : 'Remove from List' },
  ]);
  switch (picked) {
    case 'pause': case 'resume': case 'retry': case 'cancel': await api.jobAction([job.id], picked); break;
    case 'again': await redownload(job); break;
    case 'open': { const err = await api.openPath(file); if (err) toast('The file is no longer where it was saved.'); break; }
    case 'show': await api.showItem(file); break;
    case 'copy-url': await api.copyText(job.url); break;
    case 'copy-cmd': await api.copyText(await api.jobCommand(job.id, false)); toast('Command copied.'); break;
    case 'report': await copyReport(job); break;
    case 'log': set({ view: 'logs', logTarget: job.id }); break;
    case 'edit': editJob(job); break;
    case 'remove':
      if (inHistory) set({ history: await api.removeHistory([job.id]) });
      else await api.jobAction([job.id], 'remove');
      break;
  }
}
