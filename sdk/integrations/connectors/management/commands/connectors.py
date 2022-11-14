""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from connectors.views import import_connector
from connectors.helper import brodacast_connector_operation_message

class Command(BaseCommand):
    help = 'Installing connectors'

    def handle(self, *args, **options):
        try:
            for root, dirname, files in os.walk(settings.CONNECTORS_DIR):
                for file in files:
                    filename, file_extension = os.path.splitext(file)
                    if file_extension == '.tgz':
                        isReserved = False
                        if filename in settings.CONNECTORS_RESERVED:
                            isReserved = True
                        try:
                            result = import_connector(os.path.join(settings.CONNECTORS_DIR, '%s' % file), True, isReserved)
                            conn_id = result.get('id')
                        except Exception as exp:
                            self.stdout.write(
                                self.style.ERROR('Importing of connector %s failed: %s' % (file, str(exp))))
                            continue
        except Exception as exp:
            self.stdout.write(self.style.ERROR('Error importing all the connectors: %s' % str(exp)))
