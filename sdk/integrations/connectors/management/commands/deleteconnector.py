""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from django.core.management.base import BaseCommand
from connectors.views import ConnectorDetail


class Command(BaseCommand):
    help = 'Delete connector'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str)
        parser.add_argument('version', type=str)

    def handle(self, *args, **options):
        name = options.get('name')
        version = options.get('version')
        try:
            detail_view = ConnectorDetail()
            detail_view.kwargs = {'name': name, 'version': version, 'system_delete': True}
            response = detail_view.destroy(options)
            if response.status_code in [200, 204]:
                self.stdout.write(self.style.SUCCESS('Successfully deleted connector.'))
            else:
                self.stdout.write(self.style.ERROR('%s: %s' % (response.status_code, str(response.data))))
        except Exception as exp:
            self.stdout.write(self.style.ERROR('Failed to delete the connector: %s' % str(exp)))
