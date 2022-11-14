""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import copy

from django.core.management import BaseCommand
from connectors.serializers import ConnectorDetailSerializer
from connectors.models import Connector
from connectors.views import update_connector, install_connector_packages


class Command(BaseCommand):
    help = (
        "Helps to update connector metadata in the database from the its latest info.json."
    )
    missing_args_message = "You must specify either the connector id/name-version or --migrate " \
                           "for reimporting all connectors."

    def add_arguments(self, parser):
        parser.add_argument('-c', '--conn_id', type=str, help='connector id')
        parser.add_argument('-n', '--name', type=str, help='connector name')
        parser.add_argument('-cv', '--conn_version', type=str, help='connector version')
        parser.add_argument(
            '-all',
            '--all',
            action='store_true',
            dest='all',
            help='Re-import connector info',
        )

    def handle(self, **options):

        try:
            conn_id = options.get('conn_id', None)
            name = options.get('name', None)
            version = options.get('conn_version', None)
            all = options.get('all', True)
            all_connnectors = []
            if conn_id:
                all_connnectors = Connector.objects.filter(id=conn_id)
            elif name and version:
                all_connnectors = Connector.objects.filter(name=name, version=version)
            elif all:
                all_connnectors = Connector.objects.all()
            else:
                self.stdout.write(self.style.ERROR(
                    'Name and Version are required or pass --all argument to reimport all connectors'))
            if all_connnectors:
                for connector in all_connnectors:
                    self.stdout.write('Re-Importing connector {0} v{1}'.format(connector.name, connector.version))
                    serializer = ConnectorDetailSerializer(connector)
                    connector_object = serializer.data
                    connector_object_copy = copy.deepcopy(connector_object)
                    config = connector_object.pop('configuration', [])
                    connector.delete()

                    try:
                        update_connector(connector=connector_object, configurations=config)
                        self.stdout.write(self.style.SUCCESS(
                            'Successfully re-imported connector {0} v{1}'.format(connector.name, connector.version)))
                        self.stdout.write('Installing dependant packages for connector {0} v{1}'.format(
                            connector.name, connector.version))
                        install_connector_packages(connector.name,connector.version)
                        self.stdout.write(self.style.SUCCESS(
                            'Successfully installed all the packages for connector {0} v{1}'.format(connector.name, connector.version)))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            'Error occurred while updating the connector data ERROR :: {0}'.format(str(e))))
                        serializer = ConnectorDetailSerializer(data=connector_object_copy)
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

        except Exception as e:
            self.stdout.write(self.style.ERROR('Error occurred while re-importing the connector data ERROR :: {0}'.format(str(e))))
