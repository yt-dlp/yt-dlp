from .enums import LogLevel, ProgressStyle
from .hoodoo import format_text
from .outputs import NULL_OUTPUT, StreamOutput
from ..utils import format_bytes, remove_end, timetuple_from_msec, try_call


class Progress:
    @classmethod
    def make_progress(cls, logger, level=LogLevel.INFO,
                      *, lines=1, preserve=True, newline=False):
        if logger.disable_progress:
            output = NULL_OUTPUT

        else:
            output = logger.mapping.get(level)
            if not isinstance(output, StreamOutput):
                newline = True

        return cls(output, lines=lines, preserve=preserve, newline=newline)

    def __init__(self, output, lines=1, preserve=True, newline=False):
        self.output = output
        self.maximum = lines - 1
        self.preserve = preserve
        self.newline = newline
        self._progress_lines = [None] * lines
        self._status_id = self.output.register_status(lines) if output else None

    def print(self, pos, text):
        if not self.output or pos > self.maximum:
            return

        self._progress_lines[pos] = text

        if self.newline:
            text = self._add_line_number(remove_end(text, '\n'), pos)
            self.output.log(f'{text}\n')
            return

        if not self.output.use_term_codes:
            text = self._add_line_number(text, pos)

        self.output.status(self._status_id, pos, text)

    def close(self):
        if self._status_id is None:
            return

        self.output.unregister_status(self._status_id)
        self._status_id = None
        if self.preserve and not self.newline:
            self.output.log('\n'.join(filter(None, self._progress_lines)))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _add_line_number(self, text, line):
        if self.maximum:
            return f'{line + 1}: {text}'
        return text


class ProgressReporter:
    def __init__(self, ydl, prefix, *, lines=1, newline=False, preserve=False, disabled=False, templates={}):
        self._ydl = ydl
        self._progress = Progress.make_progress(ydl.logger, lines=lines, preserve=preserve, newline=newline)
        self._console = ydl.console
        self.disabled = disabled
        # Pass in a `progress_template` (`params.get('progress_template', {})`)
        self._screen_template = templates.get(prefix) or f'[{prefix}] %(progress._default_template)s'
        self._title_template = templates.get(f'{prefix}-title') or 'yt-dlp %(progress._default_template)s'
        self._finish_template = templates.get(f'{prefix}-finish') or f'[{prefix}] {prefix.capitalize()} completed'

    def report_progress(self, progress_dict):
        """
        Report the progress using data from the progress dict

        This will mutate the progress dict and add several items to it.

        @param progress_dict    The progress dict to report the progress on.
        """
        line = progress_dict.get('progress_idx') or 0
        self.apply_progress_format(progress_dict)

        if self.disabled:
            if progress_dict['status'] == 'finished':
                self._progress.print(line, self._finish_template)

            return

        progress_data = progress_dict.copy()
        progress_data = {
            'info': progress_data.pop('info_dict'),
            'progress': progress_data,
        }

        self._progress.print(line, self._ydl.evaluate_outtmpl(
            self._screen_template, progress_data))

        if self._console.allow_title_change:
            self._console.change_title(self._ydl.evaluate_outtmpl(
                self._title_template, progress_data))

    def apply_progress_format(self, progress_dict):
        """
        Add formatted string entries to the progress dict

        This will add the formatted properties and default template.
        Formats the entries with color codes if specified on the logger.

        @param progress_dict    The progress dict to apply the formatting to.
        """
        default_template = self.format_and_get_default_template(progress_dict)
        if not default_template:
            return

        if self._progress.output.use_term_codes:
            for name, value in ProgressStyle.items_:
                name = f'_{name.lower()}_str'
                if name not in progress_dict:
                    continue
                progress_dict[name] = format_text(progress_dict[name], value)

        progress_dict['_default_template'] = default_template % progress_dict

    @classmethod
    def format_and_get_default_template(cls, progress_dict):
        """
        Add formatted entries to the progress dict and return the default template

        This will add the string representation of certain properties to the dict.
        It also returns the optimal default template to use for this `progress_dict`.

        @param progress_dict    The progress dict to process.

        @returns                The optimal default template.
        """
        def has_field(*field_names):
            return all(progress_dict.get(field_name) is not None for field_name in field_names)

        if progress_dict['status'] == 'finished':
            speed = try_call(lambda: progress_dict['total_bytes'] / progress_dict['elapsed'])
            progress_dict.update({
                'speed': speed,
                '_speed_str': cls.format_speed(speed),
                '_total_bytes_str': format_bytes(progress_dict.get('total_bytes')),
                '_elapsed_str': cls.format_seconds(progress_dict.get('elapsed')),
                '_percent_str': cls.format_percent(1),
            })
            msg_template = '%(_percent_str)s'
            if has_field('total_bytes'):
                msg_template += ' of %(_total_bytes_str)s'
            if has_field('elapsed'):
                msg_template += ' in %(_elapsed_str)s'
            if has_field('speed'):
                msg_template += ' at %(_speed_str)s'

            return msg_template

        current_bytes = progress_dict.get('downloaded_bytes') or progress_dict.get('processed_bytes')

        progress_dict.update({
            '_eta_str': cls.format_seconds(progress_dict.get('eta')),
            '_speed_str':
                cls.format_speed(progress_dict.get('speed'))
                if progress_dict.get('speed_rate') is None
                else cls.format_speed_rate(progress_dict['speed_rate']),
            '_percent_str': cls.format_percent(try_call(
                lambda: current_bytes / progress_dict['total_bytes'],
                lambda: current_bytes / progress_dict['total_bytes_estimate'],
                lambda: 0)),
            '_total_bytes_str': format_bytes(progress_dict.get('total_bytes')),
            '_total_bytes_estimate_str': format_bytes(progress_dict.get('total_bytes_estimate')),
            '_downloaded_bytes_str': format_bytes(progress_dict.get('downloaded_bytes')),
            '_elapsed_str': cls.format_seconds(progress_dict.get('elapsed')),
        })

        if progress_dict['status'] not in ('downloading', 'processing'):
            return

        msg_template = (
            '%(_percent_str)s of %(_total_bytes_str)s at %(_speed_str)s ETA %(_eta_str)s'
            if has_field('total_bytes') else
            '%(_percent_str)s of ~%(_total_bytes_estimate_str)s at %(_speed_str)s ETA %(_eta_str)s'
            if has_field('total_bytes_estimate') else
            '%(_downloaded_bytes_str)s at %(_speed_str)s (%(_elapsed_str)s)'
            if has_field('downloaded_bytes', 'elapsed') else
            '%(_downloaded_bytes_str)s at %(_speed_str)s'
            if has_field('downloaded_bytes') else
            '%(_percent_str)s at %(_speed_str)s ETA %(_eta_str)s')

        if has_field('fragment_index', 'fragment_count'):
            msg_template += ' (frag %(fragment_index)d/%(fragment_count)d)'

        elif has_field('fragment_index'):
            msg_template += ' (frag %(fragment_index)d)'

        return msg_template

    @staticmethod
    def format_seconds(seconds, eta=False):
        """Format seconds as hours, minutes and seconds (width 8)"""
        if seconds is None:
            return ' Unknown'
        time = timetuple_from_msec(int(seconds) * 1000)
        if time.hours > 99:
            return '--:--:--'
        if eta and not time.hours:
            return f'   {time.minutes:0>2}:{time.seconds:0>2}'
        return f'{time.hours:0>2}:{time.minutes:0>2}:{time.seconds:0>2}'

    @staticmethod
    def format_percent(percent):
        """
        Format a percentage as string (width 6)

        Notice that 1 is 100% and not 100.
        """
        return '  N/A%' if percent is None else f'{percent:>6.1%}'

    @staticmethod
    def format_speed(speed):
        """Format speed as a string B/s (width 12)"""
        return ' Unknown B/s' if speed is None else f'{format_bytes(speed):>10}/s'

    @staticmethod
    def format_speed_rate(rate):
        """Format speed rate as a string multiplier (width 5)"""
        return ' ---x' if rate is None else f'{rate:>4.1f}x'

    def __enter__(self):
        self._progress.__enter__()
        return self

    def __exit__(self, *args):
        return self._progress.__exit__(*args)

    def close(self):
        self._progress.close()
