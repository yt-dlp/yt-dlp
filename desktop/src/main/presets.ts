import { defaultSimple } from '../shared/simple';
import type { Preset } from '../shared/types';

const { folder: _folder, ...base } = defaultSimple;

export const builtinPresets: Preset[] = [
  { id: 'builtin-best-mp4', name: 'Best video, MP4', note: 'Highest quality that still plays everywhere.', builtin: true, simple: { ...base }, advanced: {}, extraArgs: '' },
  { id: 'builtin-1080-mp4', name: '1080p MP4', note: 'Full HD at most. Smaller files than best quality.', builtin: true, simple: { ...base, quality: '1080' }, advanced: {}, extraArgs: '' },
  { id: 'builtin-podcast-mp3', name: 'Podcast MP3', note: 'Speech-friendly MP3 at 128 kbps with cover art.', builtin: true, simple: { ...base, kind: 'audio', audioFormat: 'mp3', audioQuality: '128K', thumbnail: true }, advanced: {}, extraArgs: '' },
  { id: 'builtin-music-m4a', name: 'Music, M4A with cover', note: 'Best audio as M4A, tagged, with the thumbnail as cover.', builtin: true, simple: { ...base, kind: 'audio', audioFormat: 'm4a', audioQuality: '0', thumbnail: true }, advanced: {}, extraArgs: '' },
  { id: 'builtin-subs-720', name: '720p with subtitles', note: 'For lectures and talks. English subtitles embedded.', builtin: true, simple: { ...base, quality: '720', subtitles: true }, advanced: {}, extraArgs: '' },
  {
    id: 'builtin-channel-archive', name: 'Channel archive', builtin: true,
    note: 'Sorts files into a folder per uploader and remembers what it has, so running it again only fetches new uploads.',
    simple: { ...base, container: 'mkv', playlist: 'all' },
    advanced: {
      '--download-archive': 'archive.txt',
      '--output': ['%(uploader)s/%(upload_date>%Y-%m-%d)s %(title)s [%(id)s].%(ext)s'],
      '--ignore-errors': '--no-abort-on-error',
    },
    extraArgs: '',
  },
];

export function mergePresets(saved: Preset[]): Preset[] {
  const user = saved.filter((p) => !p.builtin);
  return [...builtinPresets, ...user];
}
