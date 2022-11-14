""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import os
import shutil
import json

from django.core.management import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from connectors.serializers import ConnectorDetailSerializer
from connectors.utils import get_connector_path
from connectors.models import Connector


class Command(BaseCommand):
    help = (
        "Creates a connector directory structure for the given connector name in "
        "the connectors directory."
    )
    missing_args_message = "You must provide an connector name and version."

    def add_arguments(self, parser):
        parser.add_argument('name', type=str)
        parser.add_argument('version', type=str)

    def handle(self, **options):
        name = options.get('name')
        version = options.get('version')
        connector_path = get_connector_path(name, version)
        if os.path.exists(connector_path):
            self.stdout.write(self.style.ERROR('Connector \'%s/%s\' matches an active Connector.' % (name, version)))
            return
        os.makedirs(connector_path)
        self.copytree(os.path.join(settings.DJANGO_ROOT, 'connectors', 'core', 'templates'), connector_path)

        # Update the info.json with connector name and verion.
        # ToDo : not needed now
        info = open(os.path.join(connector_path, "info.json"), "r", encoding="utf-8")
        data = json.load(info)  # Read the JSON into the buffer
        info.close()  # Close the JSON file

        data["name"] = name
        data["version"] = version

        ## Save our changes to JSON file
        jsonFile = open(os.path.join(connector_path, "info.json"), "w+", encoding="utf-8")
        jsonFile.write(json.dumps(data, indent=2))
        jsonFile.close()

        try:
            Connector.objects.get(name=name, version=version)
        except ObjectDoesNotExist:
            serializer = ConnectorDetailSerializer(data={'name': name, 'version': version})
            serializer.is_valid(raise_exception=True)
            serializer.save()

    def copytree(self, src, dst, symlinks=False, ignore=None):
        for item in os.listdir(src):
            s = os.path.join(src, item)
            shutil.copy2(s, dst)
