""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import re
import os
import json
import shutil

from django.core.management import BaseCommand
from connectors.serializers import ConnectorDetailSerializer
from connectors.models import Connector
from connectors.views import import_connector
from connectors.serializers import ConnectorListSerializer
from django.conf import settings


class Command(BaseCommand):
    help = (
        "Helps to update all connector in the database from its latest info.json."
    )

    def is_replace(self, connector_name, compatible_version):
        compatible_version = compatible_version.strip()

        if compatible_version == 'ALL':
            return True

        if compatible_version == 'NULL':
            return False

        if not re.compile(r"[0-9]+.[0-9]+.[0-9]+$").match(compatible_version):
            raise Exception('Incorrect Compatible Version Information')
        connector_query = Connector.objects.filter(name=connector_name)
        connectors = ConnectorListSerializer(connector_query, many=True).data

        compatible_version_map = tuple(map(int, (compatible_version.split("."))))
        for connector in connectors:
            version = connector['version']
            if tuple(map(int, (version.split(".")))) < compatible_version_map:
                return False
        return True

    def handle(self, **options):
        try:
            connector_folder_mapping = {}
            connector_folder_regex = '.*_[0-9]_[0-9]_[0-9]'
            for folder_name in os.listdir(settings.CONNECTORS_DIR):
                if re.match(connector_folder_regex, folder_name):
                    conn_name = re.sub('_[0-9]_[0-9]_[0-9]', '', folder_name)
                    conn_version = re.findall('[0-9]_[0-9]_[0-9]', folder_name)[0]
                    if conn_name in connector_folder_mapping:
                        if int(conn_version.replace('_', '')) > int(connector_folder_mapping[conn_name].replace('_', '')):
                            connector_folder_mapping[conn_name] = conn_version
                    else:
                        connector_folder_mapping[conn_name] = conn_version
            for name, version in connector_folder_mapping.items():
                connector_instance = Connector.objects.filter(name=name).order_by('-version').first()
                replace = True
                isReserved = True
                if version.replace('_', '.') == connector_instance.version:
                    continue
                connector_base_path = '/opt/cyops-connector-' + name
                tgz_file_path = os.path.join(connector_base_path, name + '.tgz')
                if name not in settings.CONNECTORS_RESERVED:
                    compatibility_path = os.path.join(connector_base_path, 'compatibility.txt')
                    isReserved = False
                    folder_path = os.path.join(settings.CONNECTORS_DIR, name + '_' + version)
                    try:
                        with open(compatibility_path, 'r') as file_obj:
                            compatibility_version = file_obj.read()
                        replace = self.is_replace(name, compatibility_version)
                        if not replace:
                            shutil.rmtree(folder_path)
                    except Exception as e:
                        pass
                    pass
                import_connector(tgz_file_path, replace=replace, isReserved=isReserved)

            self.stdout.write(self.style.SUCCESS('Successfully re-imported all connectors'))

        except Exception as e:
                self.stdout.write(
                    self.style.ERROR('Error occurred while reimporting the connectors ERROR :: {0}'.format(str(e))))
