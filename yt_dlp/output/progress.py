from .formatting import apply_progress_format
from .logging import LogLevel, default_logger
from .outputs import NULL_OUTPUT, StreamOutput
from ..utils import remove_end


class Progress:
    @classmethod
    def make_progress(cls, logger=default_logger, level=LogLevel.INFO,
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
        line = progress_dict.get('progress_idx') or 0
        apply_progress_format(progress_dict, self._progress.output.use_term_codes)

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

    def close(self):
        self._progress.close()
