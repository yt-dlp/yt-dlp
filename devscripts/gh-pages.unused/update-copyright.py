#!/usr/bin/env python3
# coding: utf-8

from __future__ import with_statement, unicode_literals

import datetime
import glob
import io  # For Python 2 compatibility
import os
import re

year = str(datetime.datetime.now().year)
for fn in glob.glob('*.html*'):
    with io.open(fn, encoding='utf-8') as f:
        content = f.read()
    newc = re.sub(r'(?P<copyright>Copyright © 2011-)(?P<year>[0-9]{4})', 'Copyright © 2011-' + year, content)
    if content != newc:
        tmpFn = fn + '.part'
        with io.open(tmpFn, 'wt', encoding='utf-8') as outf:
            outf.write(newc)
        os.rename(tmpFn, fn)
