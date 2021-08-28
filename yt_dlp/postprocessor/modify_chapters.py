import heapq
import os
from collections import OrderedDict

from .common import PostProcessor
from .ffmpeg import (
    FFmpegPostProcessor,
    FFmpegSubtitlesConvertorPP
)
from .sponsorblock import SponsorBlockPP
from ..utils import (
    float_or_none,
    PostProcessingError,
    prepend_extension,
    traverse_obj,
)


class ModifyChaptersPP(FFmpegPostProcessor):
    def __init__(self, downloader, remove_chapters_patterns=None,
                 remove_sponsor_segments=None, force_keyframes=False):
        FFmpegPostProcessor.__init__(self, downloader)
        self._remove_chapters_patterns = set(remove_chapters_patterns or [])
        self._remove_sponsor_segments = set(remove_sponsor_segments or [])
        self._force_keyframes = force_keyframes

    @PostProcessor._restrict_to(images=False)
    def run(self, info):
        chapters, sponsor_chapters = self._mark_chapters_to_remove(
            info.get('chapters', []), info.get('sponsorblock_chapters', []))
        if not chapters and not sponsor_chapters:
            return [], info

        real_duration = self._get_real_video_duration(info['filepath'])
        if not chapters:
            chapters = [{'start_time': 0, 'end_time': real_duration, 'title': info['title']}]

        info['chapters'], cuts = self._remove_marked_arrange_sponsors(chapters + sponsor_chapters)
        if not cuts:
            return [], info

        if abs(real_duration - info['duration']) > 1:
            if abs(real_duration - info['chapters'][-1]['end_time']) < 1:
                self.to_screen('Already cut')
                return [], info
            if not info.get('__real_download'):
                self.report_error('Real and expected durations mismatch, probably the video '
                                  'was already cut. Refusing to cut the second time')

        concat_opts = self._make_concat_opts(cuts, real_duration)

        def remove_chapters(file, is_sub):
            return file, self.remove_chapters(file, cuts, concat_opts, self._force_keyframes and not is_sub)

        in_out_files = [remove_chapters(info['filepath'], False)]
        in_out_files.extend(remove_chapters(in_file, True) for in_file in self._get_supported_subs(info))

        # Renaming should only happen after all files are processed
        files_to_remove = []
        for in_file, out_file in in_out_files:
            uncut_file = prepend_extension(in_file, 'uncut')
            os.replace(in_file, uncut_file)
            os.replace(out_file, in_file)
            files_to_remove.append(uncut_file)

        return files_to_remove, info

    def _mark_chapters_to_remove(self, chapters, sponsor_chapters):
        if self._remove_chapters_patterns:
            warn_no_chapter_to_remove = True
            if not chapters:
                self.to_screen('Chapter information is unavailable')
                warn_no_chapter_to_remove = False
            for c in chapters:
                if any(regex.search(c['title']) for regex in self._remove_chapters_patterns):
                    c['remove'] = True
                    warn_no_chapter_to_remove = False
            if warn_no_chapter_to_remove:
                self.to_screen('There are no chapters matching the regex')

        if self._remove_sponsor_segments:
            warn_no_chapter_to_remove = True
            if not sponsor_chapters:
                self.to_screen('SponsorBlock information is unavailable')
                warn_no_chapter_to_remove = False
            for c in sponsor_chapters:
                if c['category'] in self._remove_sponsor_segments:
                    c['remove'] = True
                    warn_no_chapter_to_remove = False
            if warn_no_chapter_to_remove:
                self.to_screen('There are no matching SponsorBlock chapters')

        return chapters, sponsor_chapters

    def _get_real_video_duration(self, filename):
        duration = float_or_none(
            traverse_obj(self.get_metadata_object(filename), ('format', 'duration')))
        if duration is None:
            raise PostProcessingError('ffprobe returned empty duration')
        return duration

    def _get_supported_subs(self, info):
        for sub in (info.get('requested_subtitles') or {}).values():
            sub_file = sub.get('filepath')
            # The file might have been removed by --embed-subs
            if not sub_file or not os.path.exists(sub_file):
                continue
            ext = sub['ext']
            if ext not in FFmpegSubtitlesConvertorPP.SUPPORTED_EXTS:
                self.report_warning(f'Cannot remove chapters from external {ext} subtitles; "{sub_file}" is now out of sync')
                continue
            # TODO: create __real_download for subs?
            yield sub_file

    @staticmethod
    def _remove_marked_arrange_sponsors(chapters):
        # Store cuts separately, since adjacent and overlapping cuts must be merged.
        cuts = []

        def append_cut(c):
            assert 'remove' in c
            last_to_cut = cuts[-1] if cuts else None
            if last_to_cut and last_to_cut['end_time'] >= c['start_time']:
                last_to_cut['end_time'] = max(last_to_cut['end_time'], c['end_time'])
            else:
                cuts.append(c)
            return len(cuts) - 1

        def excess_duration(c):
            # Cuts that are completely within the chapter reduce chapters' duration.
            # Since cuts can overlap, excess duration may be less that the sum of cuts' durations.
            # To avoid that, chapter stores the index to the fist cut within the chapter,
            # instead of storing excess duration. append_cut ensures that subsequent cuts (if any)
            # will be merged with previous ones (if necessary).
            cut_idx, excess = c.pop('cut_idx', len(cuts)), 0
            while cut_idx < len(cuts):
                cut = cuts[cut_idx]
                if cut['start_time'] >= c['end_time']:
                    break
                if cut['end_time'] > c['start_time']:
                    excess += min(cut['end_time'], c['end_time'])
                    excess -= max(cut['start_time'], c['start_time'])
                cut_idx += 1
            return excess

        new_chapters = []

        def sponsor_categories(c):
            assert 'categories' in c
            return [cat for cat, _, _ in c['categories']]

        def append_chapter(c):
            assert 'remove' not in c
            length = c['end_time'] - c['start_time'] - excess_duration(c)
            if length <= 0:
                # Chapter is completely covered by cuts or sponsors.
                return
            start = new_chapters[-1]['end_time'] if new_chapters else 0
            c.update(start_time=start, end_time=start + length)
            # Merge adjacent identical sponsor chapters.
            if (new_chapters and 'categories' in new_chapters[-1] and 'categories' in c
                    and sponsor_categories(new_chapters[-1]) == sponsor_categories(c)):
                new_chapters[-1]['end_time'] = c['end_time']
            else:
                new_chapters.append(c)

        # Turn into a priority queue, index is a tie breaker.
        # Plain stack sorted by start_time is not enough: after splitting the chapter,
        # the part returned to the stack is not guaranteed to have start_time
        # less than or equal to the that of the stack's head.
        chapters = [(c['start_time'], i, c) for i, c in enumerate(chapters)]
        heapq.heapify(chapters)

        _, cur_i, cur_chapter = heapq.heappop(chapters)
        while chapters:
            _, i, c = heapq.heappop(chapters)
            # Non-overlapping chapters or cuts can be appended directly. However,
            # adjacent non-overlapping cuts must be merged, which is handled by append_cut.
            if cur_chapter['end_time'] <= c['start_time']:
                (append_chapter if 'remove' not in cur_chapter else append_cut)(cur_chapter)
                cur_i, cur_chapter = i, c
                continue

            # Eight possibilities for overlapping chapters: (cut, cut), (cut, sponsor),
            # (cut, normal), (sponsor, cut), (normal, cut), (sponsor, sponsor),
            # (sponsor, normal), and (normal, sponsor). There is no (normal, normal):
            # normal chapters are assumed not to overlap.
            if 'remove' in cur_chapter:
                # (cut, cut): adjust end_time.
                if 'remove' in c:
                    cur_chapter['end_time'] = max(cur_chapter['end_time'], c['end_time'])
                # (cut, sponsor/normal): chop the beginning of the later chapter
                # (if it's not completely hidden by the cut). Push to the priority queue
                # to restore sorting by start_time: with beginning chopped, c may actually
                # start later than the remaining chapters from the queue.
                elif cur_chapter['end_time'] < c['end_time']:
                    c['start_time'] = cur_chapter['end_time']
                    heapq.heappush(chapters, (c['start_time'], i, c))
            # (sponsor/normal, cut).
            elif 'remove' in c:
                # Chop the end of the current chapter if the cut is not contained within it.
                # Chopping the end doesn't break start_time sorting, no PQ push is necessary.
                if cur_chapter['end_time'] <= c['end_time']:
                    cur_chapter['end_time'] = c['start_time']
                    append_chapter(cur_chapter)
                    cur_i, cur_chapter = i, c
                    continue
                # Current chapter contains the cut within it. If the current chapter is
                # a sponsor chapter, check whether the categories before and after the cut differ.
                if 'categories' in cur_chapter:
                    after_c = dict(cur_chapter, start_time=c['end_time'], categories=[])
                    cur_cats = []
                    for cat_start_end in cur_chapter['categories']:
                        if cat_start_end[1] < c['start_time']:
                            cur_cats.append(cat_start_end)
                        if cat_start_end[2] > c['end_time']:
                            after_c['categories'].append(cat_start_end)
                    cur_chapter['categories'] = cur_cats
                    if cur_chapter['categories'] != after_c['categories']:
                        # Categories before and after the cut differ: push the after part to PQ.
                        heapq.heappush(chapters, (after_c['start_time'], cur_i, after_c))
                        cur_chapter['end_time'] = c['start_time']
                        append_chapter(cur_chapter)
                        cur_i, cur_chapter = i, c
                        continue
                # Either sponsor categories before and after the cut are the same or
                # we're dealing with a normal chapter. Just register an outstanding cut:
                # subsequent append_chapter will reduce the duration.
                cur_chapter.setdefault('cut_idx', append_cut(c))
            # (sponsor, sponsor): merge categories and adjust end_time.
            elif 'categories' in cur_chapter and 'categories' in c:
                cur_chapter['categories'].extend(c['categories'])
                cur_chapter['end_time'] = max(cur_chapter['end_time'], c['end_time'])
            # (sponsor, normal): if a normal chapter is not completely overlapped,
            # chop the beginning of it and push it to PQ.
            elif 'categories' in cur_chapter:
                if cur_chapter['end_time'] < c['end_time']:
                    c['start_time'] = cur_chapter['end_time']
                    heapq.heappush(chapters, (c['start_time'], i, c))
            # (normal, sponsor)
            else:
                assert 'categories' in c
                # If a sponsor chapter splits the normal one,
                # push the part after the sponsor to PQ.
                if cur_chapter['end_time'] > c['end_time']:
                    after_c = dict(cur_chapter, start_time=c['end_time'])
                    heapq.heappush(chapters, (after_c['start_time'], cur_i, after_c))
                # Sponsor chapter must inherit the cuts that the normal chapter
                # has accumulated within it.
                if 'cut_idx' in cur_chapter:
                    c['cut_idx'] = cur_chapter['cut_idx']
                cur_chapter['end_time'] = c['start_time']
                append_chapter(cur_chapter)
                cur_i, cur_chapter = i, c
        (append_chapter if 'remove' not in cur_chapter else append_cut)(cur_chapter)

        for c in new_chapters:
            if 'categories' in c:
                cats = sponsor_categories(c)
                # Overlapping sponsor chapters will have a title that looks like
                # '[SponsorBlock]: Sponsor/Interaction Remainder/Self-Promotion',
                # in the order in which the categories were encountered.
                # OrderedDict removes duplicates preserving the order.
                c['title'] = '[SponsorBlock]: ' + '/'.join(OrderedDict(
                    zip(cats, map(SponsorBlockPP.CATEGORIES.__getitem__, cats))).values())
                del c['categories']

        return new_chapters, cuts

    def remove_chapters(self, filename, ranges_to_cut, concat_opts, force_keyframes=False):
        in_file = filename
        out_file = prepend_extension(in_file, 'temp')
        if force_keyframes:
            in_file = self.force_keyframes(in_file, (t for r in ranges_to_cut for t in r))
        self.to_screen(f'Removing chapters from {filename}')
        self.concat_files([in_file] * len(concat_opts), out_file, concat_opts)
        if in_file != filename:
            os.remove(in_file)
        return out_file

    @staticmethod
    def _make_concat_opts(chapters_to_remove, duration):
        opts = [{}]
        for s in chapters_to_remove:
            # Do not create 0 duration chunk at the beginning.
            if s['start_time'] == 0:
                opts[-1]['inpoint'] = f'{s["end_time"]:.6f}'
                continue
            opts[-1]['outpoint'] = f'{s["start_time"]:.6f}'
            # Do not create 0 duration chunk at the end.
            if s['end_time'] != duration:
                opts.append({'inpoint': f'{s["end_time"]:.6f}'})
        return opts
