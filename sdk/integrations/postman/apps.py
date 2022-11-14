import json
import sys
import uuid
from threading import Thread
from django.apps import AppConfig
from django.conf import settings
from connectors.core.connector import logger
from connectors.core.constants import VERSION_JSON_PATH
from postman.utils.helper import load_connectors_json


class PostmanConfig(AppConfig):
    name = 'postman'

    def ready(self):
        if 'makemigrations' in sys.argv or 'migrate' in sys.argv or 'loadannotation' in sys.argv:
            return

        from utils.config_parser import all_config
        from postman.utils.utility import load_agents_config, load_tenants_config, populate_agent_info
        from postman.models import Agent, Tenant

        populate_agent_info(Agent.objects.filter())
        if check_for_exit_command():
            return

        try:
            with open(VERSION_JSON_PATH) as json_file:
                data = json.load(json_file)
                settings.RELEASE_VERSION = data.get('version').split('-')[0]
        except Exception as e:
            settings.RELEASE_VERSION = 'Dev'

        if settings.LW_AGENT:
            settings.CONNECTORS_JSON = load_connectors_json()
            settings.MASTER_ID = all_config.get('cyops.instance.masterId')
            tenants = [{'tenantId': all_config.get('cyops.instance.agentId'),
                        'uuid': all_config.get('cyops.instance.tenantUuid'),
                        'active': True,
                        'role': 'self'}]
            save_or_update_tenants(tenants)
            agents = [{'agentId': all_config.get('cyops.instance.agentId'),
                       'tenants': ['/api/3/tenants/' + all_config.get('cyops.instance.tenantUuid')],
                       'uuid': all_config.get('cyops.instance.agentUuid'),
                       'active': True,
                       'isLocal': True,
                       'allowRemoteConnectorOperation': settings.ENABLE_REMOTE_CONNECTOR_OPERATION
                       },
                      {'agentId': all_config.get('cyops.instance.masterId'),
                       'tenants': ['/api/3/tenants/' + all_config.get('cyops.instance.tenantUuid')],
                       'uuid': str(uuid.uuid4()),
                       'active': True,
                       'isLocal': False
                       },
                      ]
            save_or_update_agents(agents)
        else:
            tenants = load_tenants_config()
            save_or_update_tenants(tenants)
            agents = load_agents_config()
            save_or_update_agents(agents)

        agents = Agent.objects.filter()
        tenants = Tenant.objects.filter()

        for agent in agents:
            if agent.is_local:
                settings.SELF_ID = agent.agent_id
            if agent.name == 'Master':
                settings.MASTER_ID = agent.agent_id
        for tenant in tenants:
            if tenant.role == 'master':
                settings.MASTER_ID = tenant.tenant_id

        broadcast_agent_service_status(all_config)

        if 'runserver' in sys.argv and '--noreload' in sys.argv:
            agents = Agent.objects.filter(is_local=True)
            start_agent(agents)


def broadcast_agent_service_status(all_config):
    try:
        from connectors.helper import SelfOperations
        classObj = SelfOperations()
        classObj.agent_health_check({"agent": settings.SELF_ID})
    except:
        pass


def broadcast_agent_update(agent_data):
    from postman.callbacks.integration_receiver import remote_agent_update_broadcast
    remote_agent_update_broadcast(agent_data, 'PUT')


def check_for_exit_command():
    exit_commands = ['setupsdk.py', 'execute_action']
    for argv in sys.argv:
        for exit_command in exit_commands:
            if exit_command in argv:
                return True


def save_or_update_tenants(tenants):
    from postman.models import Tenant
    for tenant in tenants:
        if tenant.get('role') == 'self' and Tenant.objects.filter(role='self').exists():
            tenant_obj = Tenant.objects.get(role='self')
            old_tenant_id = tenant_obj.tenant_id
            new_tenant_id = tenant.get('tenantId')
            if old_tenant_id != new_tenant_id:
                tenant_obj.tenant_id = new_tenant_id
                tenant_obj.save()

        elif Tenant.objects.filter(tenant_id=tenant.get('tenantId')).exists():
            tenant_instance = Tenant.objects.get(tenant_id=tenant.get('tenantId'))

        else:
            try:
                Tenant.objects.create(
                    name=tenant.get('name', 'Self'),
                    role=tenant.get('role', 'self'),
                    active=tenant.get('active', False),
                    tenant_id=tenant.get('tenantId'),
                    uuid=tenant.get('@id').split("/")[-1] if tenant.get('@id') else tenant.get('uuid'),
                    is_dedicated=tenant.get('isDedicated', True),
                )
            except Exception as e:
                logger.info("Exception occured while saving tenant %s", str(e))


def save_or_update_agents(agents):
    from postman.models import Agent, Tenant, Team
    from connectors.models import Connector, Configuration, ExecuteAction
    for agent in agents:
        broadcast_agent_update(agent)
        tenants_uuid = [tenant.split('/')[-1] for tenant in agent.get('tenants')]
        tenant_instances = Tenant.objects.filter(uuid__in=tenants_uuid)
        team_instances = []

        for owner in agent.get('owners', []):
            team_instances.append(Team.objects.update_or_create(uuid=owner.split('/')[-1]))
        teams = [teams[0] for teams in team_instances]

        if agent.get('isLocal') and Agent.objects.filter(is_local=True).exists():
            old_agent_id = Agent.objects.get(is_local=True).agent_id
            agent_obj = Agent.objects.get(is_local=True)
            if agent_obj.agent_id != agent.get('agentId'):
                Connector.objects.filter(agent_id=old_agent_id).update(agent_id=None)
                Configuration.objects.filter(agent_id=old_agent_id).update(agent_id=None)
                ExecuteAction.objects.filter(agent_id=old_agent_id).update(agent_id=None)
                agent_obj.agent_id = agent.get('agentId')
                config_status = agent.get('configstatus').get('@id') if isinstance(agent.get('configstatus'),
                                                                                   dict) else agent.get('configstatus')
                agent_obj.config_status = config_status
                agent_obj.version = settings.RELEASE_VERSION
                agent_obj.allow_remote_operation = agent.get('allowRemoteConnectorOperation', True)
                agent_obj.save()
                Connector.objects.filter(agent_id=None).update(agent_id=agent_obj.agent_id)
                Configuration.objects.filter(agent_id=None).update(agent_id=agent_obj.agent_id)
                ExecuteAction.objects.filter(agent_id=None).update(agent_id=agent_obj.agent_id)

        elif Agent.objects.filter(agent_id=agent.get('agentId')).exists():
            agent_obj = Agent.objects.get(agent_id=agent.get('agentId'))
            agent_obj.active = agent.get('active', False)
            agent_obj.version = settings.RELEASE_VERSION
            agent_obj.allow_remote_operation = agent.get('allowRemoteConnectorOperation', True)
            agent_obj.save()
        else:
            try:
                agent_obj = Agent.objects.create(
                    name=agent.get('name', 'Self'),
                    agent_id=agent.get('agentId'),
                    active=agent.get('active', False),
                    uuid=agent.get('@id').split('/')[-1] if agent.get('@id') else agent.get('uuid'),
                    version=settings.RELEASE_VERSION,
                    is_local=agent.get('isLocal', True),
                    config_status=agent.get('configstatus').get('@id') if isinstance(agent.get('configstatus'),
                                                                                     dict) else agent.get(
                        'configstatus'),
                    allow_remote_operation=agent.get('allowRemoteConnectorOperation', True)

                )
            except Exception as e:
                logger.info('Failed to create agent instance :%s', str(e))
                agent_obj = None
        if agent_obj and agent.get('isLocal'):
            agent_obj.version = settings.RELEASE_VERSION
            agent_obj.allow_remote_operation = agent.get('allowRemoteConnectorOperation', True)
            agent_obj.save()
            Connector.objects.filter(agent_id=None).update(agent_id=agent_obj.agent_id)
            Configuration.objects.filter(agent_id=None).update(agent_id=agent_obj.agent_id)
            ExecuteAction.objects.filter(agent_id=None).update(agent_id=agent_obj.agent_id)

        if agent_obj and tenant_instances:
            agent_obj.tenant.clear()
            agent_obj.tenant.add(*tenant_instances)
        if agent_obj and team_instances:
            agent_obj.team.clear()
            agent_obj.team.add(*teams)


def start_agent(agents):
    from postman.core.consumer import start_consumer
    from utils.config_parser import all_config
    if settings.LW_AGENT:
        for agent in agents:
            agent_id = agent.agent_id
            t = Thread(target=start_consumer, name=agent_id, args=(agent_id,))
            t.start()
    else:
        t = Thread(target=start_consumer, name='self', args=('self',))
        t.start()
    logger.info('Started all consumers successfully')
