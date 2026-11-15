import { useEffect, useState } from 'preact/hooks';
import { buildOptionArgs } from '../../shared/command';
import { join } from '../../shared/shlex';
import { Advanced } from '../Advanced';
import { api, saveSettings, set, toast, useStore } from '../state';
import { ask, Btn, Check, Select, Tabs } from '../ui';

export function SettingsView() {
  const s = useStore();
  const st = s.settings;
  const [tab, setTab] = useState<'general' | 'defaults'>('general');
  useEffect(() => { void api.appVersion().then((appVersion) => set({ appVersion })); }, []);
  const up = s.appUpdate;
  const pick = async () => { const f = await api.pickFolder(st.downloadFolder); if (f) void saveSettings({ downloadFolder: f }); };
  const baseCount = Object.keys(st.baseValues).length;

  return (
    <div class="main">
      <div class="bar"><h1>Settings</h1></div>
      <Tabs value={tab} onChange={setTab} options={[['general', 'General'], ['defaults', `Options for every download${baseCount ? ` · ${baseCount}` : ''}`]] as const} />
      {tab === 'defaults' ? (
        <>
          <div class="banner">
            <span class="grow">These options are applied to every download, underneath whatever a download or preset sets itself. Currently: <span class="mono">{join(buildOptionArgs(st.baseValues)) || 'nothing'}</span></span>
            <Btn small onClick={() => ask({ title: 'Reset the options for every download', body: 'This goes back to the app’s starting point: only “Ignore yt-dlp config files” is on.', confirm: 'Reset', onConfirm: () => void saveSettings({ baseValues: { '--ignore-config': '--ignore-config' } }) })}>Reset</Btn>
          </div>
          <Advanced values={st.baseValues} extraArgs="" onChange={(baseValues) => saveSettings({ baseValues })} onExtra={() => toast('Extra arguments belong to a download or a preset.')} />
        </>
      ) : (
        <div class="scroll grow">
          <div class="page">
            <div class="section">
              <h3>Downloads</h3>
              <div class="field">
                <label>Save to</label>
                <div class="row" style={{ gap: 4 }}>
                  <input class="input grow" value={st.downloadFolder} aria-label="Download folder" onChange={(e) => saveSettings({ downloadFolder: (e.target as HTMLInputElement).value })} />
                  <Btn icon="folder" onClick={pick}>Choose</Btn>
                </div>
              </div>
              <div class="field">
                <label>At the same time</label>
                <Select label="Parallel downloads" value={String(st.maxParallel)} onChange={(v) => saveSettings({ maxParallel: Number(v) })} style={{ width: 140 }}
                  options={[1, 2, 3, 4, 5, 6, 8].map((n) => [String(n), n === 1 ? 'One download' : `${n} downloads`] as const)} />
                <span class="hint">More is not always faster. Sites slow down or block connections that ask for too much at once.</span>
              </div>
              <div class="field">
                <label>If the connection drops</label>
                <Select label="Automatic retries" value={String(st.autoRetry)} onChange={(v) => saveSettings({ autoRetry: Number(v) })} style={{ width: 220 }}
                  options={[['0', 'Stop and tell me'], ['1', 'Try once more by itself'], ['3', 'Try up to three more times']] as const} />
              </div>
              <div class="field"><span class="label">When a download ends</span><Check checked={st.notifyOnFinish} onChange={(notifyOnFinish) => saveSettings({ notifyOnFinish })}>Show a notification if the window is in the background</Check></div>
            </div>
            <div class="section">
              <h3>Appearance</h3>
              <div class="field">
                <label>Theme</label>
                <Select label="Theme" value={st.theme} onChange={(theme) => saveSettings({ theme: theme as never })} style={{ width: 220 }} options={[['system', 'Same as the system'], ['light', 'Light'], ['dark', 'Dark']] as const} />
              </div>
            </div>
            <div class="section">
              <h3>Updates</h3>
              <div class="field"><span class="label">App</span><Check checked={st.autoUpdateApp} onChange={(autoUpdateApp) => saveSettings({ autoUpdateApp })}>Download new versions of Dubdeck automatically</Check></div>
              <div class="field"><span class="label">Engine</span><Check checked={st.autoCheckEngine} onChange={(autoCheckEngine) => saveSettings({ autoCheckEngine })}>Check for a newer engine when the app starts</Check></div>
              <div class="field">
                <span class="label">Dubdeck {s.appVersion}</span>
                <div class="row">
                  <Btn icon="refresh" busy={up.state === 'checking'} disabled={up.state === 'unsupported'} onClick={() => api.appUpdateCheck()}>Check now</Btn>
                  {up.state === 'ready' ? <Btn kind="primary" onClick={() => api.appUpdateInstall()}>Restart to update to {up.version}</Btn> : null}
                  {up.state === 'available' && !st.autoUpdateApp ? <Btn kind="primary" onClick={() => api.appUpdateInstall()}>Download {up.version}</Btn> : null}
                  <span class={`small ${up.state === 'error' ? 'state-error' : 'dim'}`} role="status">
                    {up.state === 'current' ? 'You have the newest version.' : up.state === 'downloading' ? `Downloading… ${up.percent ?? 0}%` : up.state === 'available' ? `Version ${up.version} is available.` : up.message ?? ''}
                  </span>
                </div>
              </div>
              <div class="field"><span class="label" /><span class="small faint">Engine updates and their channel are on the Engine screen.</span></div>
            </div>
            <div class="section">
              <h3>Logs and privacy</h3>
              <div class="field">
                <label>Keep download logs for</label>
                <Select label="Log retention" value={String(st.logRetentionDays)} onChange={(v) => saveSettings({ logRetentionDays: Number(v) })} style={{ width: 140 }}
                  options={[['7', 'A week'], ['30', 'A month'], ['90', 'Three months'], ['0', 'Forever']] as const} />
                <span class="hint">Logs stay on this computer. Nothing is sent anywhere unless you copy a report yourself.</span>
              </div>
            </div>
            <div class="section">
              <h3>Help</h3>
              <div class="row"><Btn onClick={() => set({ welcome: true })}>Show the welcome guide again</Btn><Btn onClick={() => set({ view: 'help' })}>Open help</Btn></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
