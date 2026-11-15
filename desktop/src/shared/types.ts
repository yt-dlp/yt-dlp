import type { Friendly, Stage } from './errors';
import type { ParsedArgs } from './command';
import type { OptionValues } from './schema';
import { defaultSimple, type SimpleChoices } from './simple';

export type JobState = 'queued' | 'scheduled' | 'running' | 'paused' | 'done' | 'error' | 'cancelled';

export interface JobProgress {
  percent?: number;
  downloaded?: number;
  total?: number;
  estimated?: boolean;
  speed?: number;
  eta?: number;
}

export interface Job {
  id: string;
  url: string;
  title: string;
  thumbnail?: string;
  uploader?: string;
  duration?: number;
  summary: string;
  values: OptionValues;
  extraArgs: string;
  state: JobState;
  stage: Stage;
  stageLabel?: string;
  progress: JobProgress;
  item?: { index: number; count: number; title?: string };
  files: string[];
  error?: Friendly;
  warnings: string[];
  /** what the engine printed that was not progress: results of print, JSON and list options */
  output: string;
  outputSize: number;
  note?: string;
  createdAt: number;
  startedAt?: number;
  finishedAt?: number;
  scheduledFor?: number;
  attempts: number;
  exitCode?: number | null;
  /** an output-only job (simulate, print, list) rather than a download */
  printOnly: boolean;
}

export interface JobSpec {
  url: string;
  title?: string;
  thumbnail?: string;
  uploader?: string;
  duration?: number;
  summary: string;
  values: OptionValues;
  extraArgs: string;
  scheduledFor?: number;
}

export interface Preset {
  id: string;
  name: string;
  note?: string;
  simple: Omit<SimpleChoices, 'folder'>;
  advanced: OptionValues;
  extraArgs: string;
  builtin?: boolean;
}

export type EngineChannel = 'stable' | 'nightly' | 'master' | 'fork' | 'custom';

export interface Settings {
  theme: 'system' | 'light' | 'dark';
  downloadFolder: string;
  maxParallel: number;
  simple: SimpleChoices;
  /** options applied to every download, underneath whatever a download sets itself */
  baseValues: OptionValues;
  engineChannel: EngineChannel;
  engineCustomSource: string;
  autoCheckEngine: boolean;
  autoUpdateApp: boolean;
  notifyOnFinish: boolean;
  autoRetry: number;
  logRetentionDays: number;
  welcomed: boolean;
  showInternalArgs: boolean;
  lastPresetId: string;
}

export const defaultSettings: Settings = {
  theme: 'system',
  downloadFolder: '',
  maxParallel: 3,
  simple: defaultSimple,
  baseValues: { '--ignore-config': '--ignore-config' },
  engineChannel: 'stable',
  engineCustomSource: '',
  autoCheckEngine: true,
  autoUpdateApp: true,
  notifyOnFinish: true,
  autoRetry: 1,
  logRetentionDays: 30,
  welcomed: false,
  showInternalArgs: false,
  lastPresetId: '',
};

export interface FormatInfo {
  id: string;
  ext: string;
  resolution: string;
  height?: number;
  fps?: number;
  vcodec?: string;
  acodec?: string;
  tbr?: number;
  size?: number;
  sizeApprox?: boolean;
  note: string;
  kind: 'video+audio' | 'video' | 'audio' | 'other';
}

export interface ProbeEntry { id?: string; title: string; url?: string; duration?: number; uploader?: string; thumbnail?: string; index: number }

export interface ProbeResult {
  ok: boolean;
  url: string;
  kind?: 'video' | 'playlist';
  title?: string;
  uploader?: string;
  duration?: number;
  thumbnail?: string;
  extractor?: string;
  webpageUrl?: string;
  live?: boolean;
  formats?: FormatInfo[];
  subtitles?: string[];
  autoSubtitles?: number;
  entries?: ProbeEntry[];
  count?: number;
  error?: Friendly;
  log?: string;
}

export interface EngineInfo {
  version: string;
  source: 'updated' | 'bundled' | 'source' | 'missing';
  path: string;
  ffmpeg: { path: string; version: string; source: 'bundled' | 'installed' | 'system' | 'missing' };
  jsRuntime: string;
}

export interface EngineUpdateStatus {
  state: 'idle' | 'checking' | 'available' | 'current' | 'downloading' | 'installed' | 'error';
  latest?: string;
  current?: string;
  percent?: number;
  message?: string;
}

export interface AppUpdateStatus {
  state: 'idle' | 'checking' | 'available' | 'current' | 'downloading' | 'ready' | 'error' | 'unsupported';
  version?: string;
  percent?: number;
  message?: string;
}

export interface LogFile { name: string; path: string; size: number; modified: number; kind: 'app' | 'job' }

export interface ToolResult { code: number | null; output: string }

export interface MenuItemSpec { id?: string; label?: string; type?: 'separator'; enabled?: boolean; checked?: boolean }

export interface ConfigImport { path: string; parsed: ParsedArgs }

/** Everything the window can ask the main process to do. */
export interface Api {
  platform: string;
  pathForFile?(file: File): string;
  getSettings(): Promise<Settings>;
  setSettings(patch: Partial<Settings>): Promise<Settings>;
  listPresets(): Promise<Preset[]>;
  savePreset(p: Preset): Promise<Preset[]>;
  removePreset(id: string): Promise<Preset[]>;
  probe(url: string, values: OptionValues, extraArgs: string): Promise<ProbeResult>;
  cancelProbe(url: string): Promise<void>;
  listJobs(): Promise<Job[]>;
  addJobs(specs: JobSpec[]): Promise<void>;
  jobAction(ids: string[], action: 'pause' | 'resume' | 'cancel' | 'retry' | 'remove' | 'start'): Promise<void>;
  updateJob(id: string, patch: { values?: OptionValues; extraArgs?: string; url?: string }, retry: boolean): Promise<void>;
  applyFix(id: string, fix: string): Promise<{ ok: boolean; message?: string }>;
  clearFinished(): Promise<void>;
  listHistory(): Promise<Job[]>;
  removeHistory(ids: string[]): Promise<Job[]>;
  clearHistory(): Promise<Job[]>;
  jobLog(id: string): Promise<string>;
  jobOutput(id: string): Promise<string>;
  jobReport(id: string): Promise<string>;
  jobCommand(id: string, internal: boolean): Promise<string>;
  listLogs(): Promise<LogFile[]>;
  readLog(path: string): Promise<string>;
  openLogsFolder(): Promise<void>;
  engineInfo(): Promise<EngineInfo>;
  engineCheck(): Promise<EngineUpdateStatus>;
  engineUpdate(): Promise<EngineUpdateStatus>;
  engineRevert(): Promise<EngineInfo>;
  engineTool(args: string[]): Promise<ToolResult>;
  installFfmpeg(): Promise<{ ok: boolean; message?: string }>;
  appVersion(): Promise<string>;
  appUpdateCheck(): Promise<AppUpdateStatus>;
  appUpdateInstall(): Promise<void>;
  pickFolder(current?: string): Promise<string | null>;
  pickFile(opts?: { title?: string; filters?: { name: string; extensions: string[] }[] }): Promise<string | null>;
  saveText(defaultName: string, text: string): Promise<string | null>;
  importConfig(): Promise<ConfigImport | null>;
  showItem(path: string): Promise<void>;
  openPath(path: string): Promise<string>;
  openExternal(url: string): Promise<void>;
  copyText(text: string): Promise<void>;
  readClipboard(): Promise<string>;
  popupMenu(items: MenuItemSpec[]): Promise<string | null>;
  on(channel: 'jobs', cb: (jobs: Job[]) => void): () => void;
  on(channel: 'engine-update', cb: (s: EngineUpdateStatus) => void): () => void;
  on(channel: 'app-update', cb: (s: AppUpdateStatus) => void): () => void;
  on(channel: 'command', cb: (cmd: string, arg?: string) => void): () => void;
  on(channel: 'ffmpeg-progress', cb: (percent: number) => void): () => void;
}
