import sys
import sysconfig
import os
import subprocess
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'yt_dlp', '_aes_native.c')
OUT_DIR = os.path.join(ROOT, 'yt_dlp')


def get_extra_compile_args():
    args = ['-O3', '-std=c99', '-Wall', '-Wextra', '-Wno-unused-parameter']
    if sys.platform == 'darwin':
        args += ['-mmacosx-version-min=10.15']
    return args


def get_extra_link_args():
    if sys.platform == 'win32':
        return []
    return []


def build():
    from setuptools import Extension, setup

    ext = Extension(
        'yt_dlp._aes_native',
        sources=[SRC],
        extra_compile_args=get_extra_compile_args(),
        extra_link_args=get_extra_link_args(),
    )

    setup(
        name='_aes_native',
        ext_modules=[ext],
        packages=[],
        py_modules=[],
        script_args=['build_ext', '--inplace'],
    )


if __name__ == '__main__':
    build()
