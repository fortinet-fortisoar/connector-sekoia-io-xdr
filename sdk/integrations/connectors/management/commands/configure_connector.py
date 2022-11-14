""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from django.core.management import BaseCommand
from django.conf import settings
from connectors.models import Connector
from connectors.serializers import ConnectorConfigurationSerializer
from connectors.utils import validate_config, encrypt_password
from connectors.core.connector import ConnectorError

import json

# ToDo Refactoring needed here
class Command(BaseCommand):
    help = (
        "Configures connector"
    )

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='name of the connector', )
        parser.add_argument('version', type=str, help='version of connector', )
        parser.add_argument('config', type=str, help='config',)
        parser.add_argument('agent', type=str, help='Agent', nargs='?', default=settings.SELF_ID)

    def handle(self, *args, **options):
        try:
            name = options.get('name')
            version = options.get('version')
            configuration = options.get('config')
            configuration = json.loads(configuration)
            agent = options.get('agent', settings.SELF_ID)
            connector = Connector.objects.filter(name=name, version=version, agent=agent)

            if not connector.exists():
                raise Connector.DoesNotExist

            connector_obj = connector.first()
            if not isinstance(configuration, list):
                configuration = [configuration]

            for config_each in configuration:
                config_name = config_each.get('name', '')
                config = config_each.get('config', {})
                validate_config(config, connector_obj.config_schema)
                encrypt_password(connector_obj.config_schema, config)
                config_each['connector'] = connector_obj.id
                config_each['agent'] = agent

            configuration_serializer = ConnectorConfigurationSerializer(data=configuration, many=True)
            configuration_serializer.is_valid(raise_exception=True)
            config_instance = configuration_serializer.save()
            connector.update(config_count=connector_obj.config_count+len(configuration))

            self.stdout.write(self.style.SUCCESS('Connector configuration added successfully'))

        except Connector.DoesNotExist:
            self.stdout.write(self.style.ERROR("Connnector {0} with version {1} not found".format(name, version)))
        except ConnectorError as e:
            self.stdout.write(self.style.ERROR(
                'Invalid configuration {0} provided ERROR :: {1}'.format(config_name, str(e))))
        except Exception as exp:
            self.stdout.write(self.style.ERROR('Error while configuring %s connector: %s' % (name, str(exp))))
