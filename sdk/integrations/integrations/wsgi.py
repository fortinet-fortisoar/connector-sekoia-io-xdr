""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """

import os

# Note this we need to set in the Application servers configuration.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "integrations.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()