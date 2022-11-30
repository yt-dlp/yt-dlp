import enum

from .hoodoo import Color, TermCode, Typeface, format_text
from ..utils import format_bytes, timetuple_from_msec, try_call


class ProgressStyle(enum.Enum):
    """ An Enum holding Styles for progress formatting """
    DOWNLOADED_BYTES = TermCode.make(Color.LIGHT | Color.BLUE)
    PERCENT = TermCode.make(Color.LIGHT | Color.BLUE)
    ETA = TermCode.make(Color.YELLOW)
    SPEED = TermCode.make(Color.GREEN)
    ELAPSED = TermCode.make(Typeface.BOLD, Color.WHITE)
    TOTAL_BYTES = TermCode.make()
    TOTAL_BYTES_ESTIMATE = TermCode.make()


def apply_progress_format(progress_dict, use_color=False):
    """
    Add formatted string entries to the progress dict

    This will add the formatted properties and default template.
    Optionally formats the entries with color codes.

    @param progress_dict    The progress dict to apply the formatting to.
    @param use_color        Use color codes for formatting.
    """
    default_template = format_and_get_default_template(progress_dict)
    if not default_template:
        return

    if use_color:
        for item in ProgressStyle:
            name = f'_{item.name.lower()}_str'
            if name not in progress_dict:
                continue
            progress_dict[name] = format_text(progress_dict[name], item.value)

    progress_dict['_default_template'] = default_template % progress_dict


def format_and_get_default_template(progress_dict):
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
            '_speed_str': format_speed(speed),
            '_total_bytes_str': format_bytes(progress_dict.get('total_bytes')),
            '_elapsed_str': format_seconds(progress_dict.get('elapsed')),
            '_percent_str': format_percent(1),
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
        '_eta_str': format_seconds(progress_dict.get('eta')),
        '_speed_str':
            format_speed(progress_dict.get('speed'))
            if progress_dict.get('speed_rate') is None
            else format_speed_rate(progress_dict['speed_rate']),
        '_percent_str': format_percent(try_call(
            lambda: current_bytes / progress_dict['total_bytes'],
            lambda: current_bytes / progress_dict['total_bytes_estimate'],
            lambda: 0)),
        '_total_bytes_str': format_bytes(progress_dict.get('total_bytes')),
        '_total_bytes_estimate_str': format_bytes(progress_dict.get('total_bytes_estimate')),
        '_downloaded_bytes_str': format_bytes(progress_dict.get('downloaded_bytes')),
        '_elapsed_str': format_seconds(progress_dict.get('elapsed')),
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


def format_seconds(seconds, eta=False):
    """ Format seconds as hours, minutes and seconds (width 8) """
    if seconds is None:
        return ' Unknown'
    time = timetuple_from_msec(int(seconds) * 1000)
    if time.hours > 99:
        return '--:--:--'
    if eta and not time.hours:
        return f'   {time.minutes:0>2}:{time.seconds:0>2}'
    return f'{time.hours:0>2}:{time.minutes:0>2}:{time.seconds:0>2}'


def format_percent(percent):
    """
    Format a percentage as string (width 6)

    Notice that 1.0 and not 100.0 is 100%.
    """
    return '  N/A%' if percent is None else f'{percent:>6.1%}'


def format_speed(speed):
    """ Format speed as a string /s (width 12) """
    return ' Unknown B/s' if speed is None else f'{format_bytes(speed):>10}/s'


def format_speed_rate(rate):
    """ Format speed rate as a string multiplier (width 5) """
    return ' ---x' if rate is None else f'{rate:>4.1f}x'
