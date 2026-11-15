import { contextBridge, ipcRenderer, webUtils } from 'electron';

const methods = [
  'getSettings', 'setSettings', 'listPresets', 'savePreset', 'removePreset', 'probe', 'cancelProbe', 'listJobs', 'addJobs',
  'jobAction', 'updateJob', 'applyFix', 'clearFinished', 'listHistory', 'removeHistory', 'clearHistory', 'jobLog', 'jobOutput',
  'jobReport', 'jobCommand', 'listLogs', 'readLog', 'openLogsFolder', 'engineInfo', 'engineCheck', 'engineUpdate',
  'engineRevert', 'engineTool', 'installFfmpeg', 'appVersion', 'appUpdateCheck', 'appUpdateInstall', 'pickFolder',
  'pickFile', 'saveText', 'importConfig', 'showItem', 'openPath', 'openExternal', 'copyText', 'readClipboard', 'popupMenu',
] as const;

const channels = new Set(['jobs', 'engine-update', 'app-update', 'command', 'ffmpeg-progress']);

const api: Record<string, unknown> = {
  platform: process.platform,
  on(channel: string, cb: (...args: unknown[]) => void) {
    if (!channels.has(channel)) return () => {};
    const listener = (_e: unknown, ...args: unknown[]) => cb(...args);
    ipcRenderer.on(channel, listener);
    return () => ipcRenderer.removeListener(channel, listener);
  },
  pathForFile(file: File) { try { return webUtils.getPathForFile(file); } catch { return ''; } },
};
for (const m of methods) api[m] = (...args: unknown[]) => ipcRenderer.invoke('api', m, ...args);

contextBridge.exposeInMainWorld('api', api);
