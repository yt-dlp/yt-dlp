import argparse
import datetime as dt
import functools
import re
import subprocess


def read_file(fname):
    with open(fname, encoding='utf-8') as f:
        return f.read()


def write_file(fname, content, mode='w'):
    with open(fname, mode, encoding='utf-8') as f:
        return f.write(content)


def read_version(fname='yt_dlp/version.py', varname='__version__'):
    """Get the version without importing the package"""
    items = {}
    exec(compile(read_file(fname), fname, 'exec'), items)
    return items[varname]


def calculate_version(version=None, fname='yt_dlp/version.py'):
    if version and '.' in version:
        return version

    revision = version
    version = dt.datetime.now(dt.timezone.utc).strftime('%Y.%m.%d')

    if revision:
        assert re.fullmatch(r'[0-9]+', revision), 'Revision must be numeric'
    else:
        old_version = read_version(fname=fname).split('.')
        if version.split('.') == old_version[:3]:
            revision = str(int(([*old_version, 0])[3]) + 1)

    return f'{version}.{revision}' if revision else version


def get_filename_args(has_infile=False, default_outfile=None):
    parser = argparse.ArgumentParser()
    if has_infile:
        parser.add_argument('infile', help='Input file')
    kwargs = {'nargs': '?', 'default': default_outfile} if default_outfile else {}
    parser.add_argument('outfile', **kwargs, help='Output file')

    opts = parser.parse_args()
    if has_infile:
        return opts.infile, opts.outfile
    return opts.outfile


def compose_functions(*functions):
    return lambda x: functools.reduce(lambda y, f: f(y), functions, x)


def run_process(*args, **kwargs):
    kwargs.setdefault('text', True)
    kwargs.setdefault('check', True)
    kwargs.setdefault('capture_output', True)
    if kwargs['text']:
        kwargs.setdefault('encoding', 'utf-8')
        kwargs.setdefault('errors', 'replace')
    return subprocess.run(args, **kwargs)
