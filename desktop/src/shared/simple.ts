// Simple mode: a handful of plain choices that compile down to ordinary
// engine options. Advanced values are layered on top, so the command preview
// is always exactly what will run.

import type { OptionValues } from './schema';

export interface SimpleChoices {
  kind: 'video' | 'audio';
  quality: string;      // 'best' or a height such as '1080'
  container: string;    // 'auto' | 'mp4' | 'mkv' | 'webm'
  audioFormat: string;  // 'best' | 'mp3' | 'm4a' | 'opus' | 'flac' | 'wav'
  audioQuality: string; // '0' | '320K' | '192K' | '128K'
  subtitles: boolean;
  subtitleLangs: string;
  metadata: boolean;
  thumbnail: boolean;
  playlist: 'default' | 'all' | 'single';
  folder: string;
}

export const defaultSimple: SimpleChoices = {
  kind: 'video', quality: 'best', container: 'mp4', audioFormat: 'mp3', audioQuality: '0',
  subtitles: false, subtitleLangs: 'en.*', metadata: true, thumbnail: false, playlist: 'default', folder: '',
};

export const videoQualities = [
  ['best', 'Best available'], ['2160', '2160p (4K)'], ['1440', '1440p'], ['1080', '1080p'],
  ['720', '720p'], ['480', '480p'], ['360', '360p'],
] as const;
export const videoContainers = [
  ['auto', 'Whatever is best'], ['mp4', 'MP4 (plays everywhere)'], ['mkv', 'MKV'], ['webm', 'WebM'],
] as const;
export const audioFormats = [
  ['mp3', 'MP3'], ['m4a', 'M4A (AAC)'], ['opus', 'Opus'], ['flac', 'FLAC'], ['wav', 'WAV'], ['best', 'Original, no conversion'],
] as const;
export const audioQualities = [
  ['0', 'Best'], ['320K', '320 kbps'], ['192K', '192 kbps'], ['128K', '128 kbps'],
] as const;

export function simpleToValues(s: SimpleChoices): OptionValues {
  const v: OptionValues = {};
  if (s.kind === 'audio') {
    v['--format'] = 'bestaudio/best';
    v['--extract-audio'] = '--extract-audio';
    v['--audio-format'] = s.audioFormat;
    if (s.audioFormat !== 'best' && s.audioFormat !== 'flac' && s.audioFormat !== 'wav') v['--audio-quality'] = s.audioQuality;
  } else {
    const sort: string[] = [];
    if (s.quality !== 'best') sort.push(`res:${s.quality}`);
    if (s.container === 'mp4') sort.push('vcodec:h264', 'acodec:aac');
    if (s.container === 'webm') sort.push('vext:webm', 'aext:webm');
    if (sort.length) v['--format-sort'] = sort.join(',');
    if (s.container !== 'auto') v['--merge-output-format'] = s.container;
    if (s.container === 'mp4' || s.container === 'mkv') v['--remux-video'] = s.container;
    if (s.subtitles) {
      v['--write-subs'] = '--write-subs';
      v['--sub-langs'] = s.subtitleLangs || 'en.*';
      v['--embed-subs'] = '--embed-subs';
    }
  }
  if (s.metadata) v['--embed-metadata'] = '--embed-metadata';
  if (s.thumbnail) v['--embed-thumbnail'] = '--embed-thumbnail';
  if (s.playlist === 'all') v['--yes-playlist'] = '--yes-playlist';
  if (s.playlist === 'single') v['--yes-playlist'] = '--no-playlist';
  if (s.folder) v['--paths'] = [s.folder];
  return v;
}

/** Simple choices first, advanced values on top. Advanced always wins. */
export function effectiveValues(simple: SimpleChoices, advanced: OptionValues, base: OptionValues = {}): OptionValues {
  return { ...base, ...simpleToValues(simple), ...advanced };
}

export function describeSimple(s: SimpleChoices): string {
  if (s.kind === 'audio') {
    const f = audioFormats.find(([k]) => k === s.audioFormat)?.[1] ?? s.audioFormat;
    return s.audioFormat === 'best' ? 'Audio, original format' : `Audio, ${f}`;
  }
  const q = s.quality === 'best' ? 'best quality' : `${s.quality}p`;
  return `Video, ${q}${s.container === 'auto' ? '' : `, ${s.container.toUpperCase()}`}`;
}
