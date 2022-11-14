""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand
from connectors.views import import_connector
from connectors.models import Connector
from connectors.utils import is_replace
from connectors.helper import brodacast_connector_operation_message

class Command(BaseCommand):
    help = 'Installing connectors from a given path'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, help='Path of the connector', )
        parser.add_argument('--name', type=str, help='Name of connector', )
        parser.add_argument('--compversion', type=str, help='Compatibility Version', default=None, )

    def handle(self, *args, **options):
        try:
            path = options.get('path')
            name = options.get('name')
            compversion = options.get('compversion')
            filename, file_extension = os.path.splitext(path)
            if file_extension == '.tgz':
                isReserved = False
                if filename in settings.CONNECTORS_RESERVED:
                    isReserved = True
                replace = is_replace(name, compversion)
                import_connector(path, replace, isReserved)
            else:
                self.stdout.write(self.style.ERROR('Error : connector must be in tgz format'))
        except Exception as exp:
            self.stdout.write(self.style.ERROR('Error importing the connector: %s' % str(exp)))
