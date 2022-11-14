#!/usr/bin/env python
""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from os.path import abspath, dirname, join
from os import listdir, remove
import sys
import re
from manage import main

if __name__ == '__main__':
    # Fetch Django's project directory
    DJANGO_ROOT = dirname(abspath(__file__))
    APPS = [
        'postman',
        'connectors',
        'annotation'
    ]
    # remove old migrations file, if any
    for APP in APPS:
        APP_DIR = join(DJANGO_ROOT, APP)
        migrations_dir = join(APP_DIR, 'migrations')
        for f in listdir(migrations_dir):
            if re.search(".*_initial.py", f):
                remove(join(migrations_dir, f))

    # make migrations
    main(['', 'makemigrations'])

    # migrate
    main(['', 'migrate'])

    sys.exit(0)
