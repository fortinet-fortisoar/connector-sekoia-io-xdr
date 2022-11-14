import json
from threading import Thread

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from connectors.models import Connector, Configuration
from connectors.serializers import ConnectorConfigurationSerializer
from postman.models import Agent
from connectors.views import install_or_remove_connector

CONNECTOR_PATH = settings.DJANGO_ROOT


class Command(BaseCommand):
    help = 'Installing connectors on agent'

    def handle(self, *args, **options):
        try:
            connector_json = settings.CONNECTORS_JSON
            with open(CONNECTOR_PATH + '/connectors.json') as json_file:
                connector_to_install = json.load(json_file)
            if not connector_to_install: connector_to_install = []
            for connector in connector_to_install:
                rpm_full_name = connector.get('rpm_full_name')
                if not rpm_full_name:
                    rpm_key = connector.get('name') + '_' + connector.get('version')
                    rpm_full_name = connector_json.get(rpm_key, {}).get('rpm_full_name')
                    if not rpm_full_name:
                        self.stdout.write(self.style.ERROR('RPM full name not found for connector: %s'
                                                           % connector.get('name')))

                agent_obj = Agent.objects.filter(agent_id=settings.SELF_ID).first()

                conn_instance = Connector.objects.filter(name=connector.get('name'), version=connector.get('version'),
                                                         agent=agent_obj.agent_id).first()
                if not conn_instance:
                    conn_instance = Connector.objects.create(
                        name=connector.get('name'),
                        rpm_full_name=rpm_full_name,
                        version=connector.get('version'),
                        agent=agent_obj,
                        status="in-progress",
                        label=connector.get('name'),
                    )
                configs = connector.get('configurations', [])
                for config in configs:
                    if not Configuration.objects.filter(config_id=config.get('config_id')).exists():
                        config.pop(id, None)
                        config['connector'] = conn_instance.id
                        serializer = ConnectorConfigurationSerializer(data=config)
                        if serializer.is_valid():
                            serializer.save()

                rpm_name = 'cyops-connector' + '-' + connector.get('name')
                process = Thread(target=install_or_remove_connector,
                                 args=[rpm_name, conn_instance.id, 'install', conn_instance.rpm_full_name])
                process.start()

        except Exception as exp:
            self.stdout.write(self.style.ERROR('Error importing all the connectors: %s' % str(exp)))
