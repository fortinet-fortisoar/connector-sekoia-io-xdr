""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import sys

from django.apps import AppConfig
from connectors.core.connector import logger
from connectors.proxy import configure_proxy
from django.conf import settings


class ConnectorsConfig(AppConfig):
    name = 'connectors'
    verbose_name = 'connectors'

    def ready(self):
        if 'uwsgi' in sys.argv:
            logger.info('Updating proxy settings for the environment')
            configure_proxy()
        if 'uwsgi' in sys.argv or (settings.LW_AGENT and 'runserver' in sys.argv):
            one_time_startup()


def one_time_startup():
    from multiprocessing import Process
    from connectors.utils import call_connectors_on_app_start_func
    p = Process(target=call_connectors_on_app_start_func)
    p.start()
