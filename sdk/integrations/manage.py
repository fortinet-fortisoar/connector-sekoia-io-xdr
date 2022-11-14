#!/usr/bin/env python
""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import os
import sys


def main(args):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "integrations.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(args)


if __name__ == "__main__":
    main(sys.argv)

