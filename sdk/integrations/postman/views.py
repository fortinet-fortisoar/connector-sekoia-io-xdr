import hmac
import hashlib

import base64
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta

import yaml
from django.http import HttpResponse
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from connectors.core.constants import *
from connectors.helper import RemoteOperations
from connectors.models import Connector, Configuration, ExecuteAction
from connectors.permissions import IsAgentAuthenticated
from connectors.utils import manage_password
from connectors.views import AgentHealth
# Create your views here.
from integrations.crudhub import make_request
from postman.models import Tenant, Agent
from postman.serializer import TenantSerializer, ExecuteActionSerializer, AgentSerializer
from postman.utils.utility import load_agents_config
from connectors.serializers import ConnectorConfigurationAgentSerializer
from audit.audit import publish_audit_and_notify
import logging

logger = logging.getLogger('postman')


class TenantView(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    filter_backends = (filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend,)
    ordering_fields = ('name', 'uuid')
    search_fields = ('name', 'uuid')
    filter_fields = ('name', 'uuid')


class AgentView(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    filter_backends = (filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend,)
    ordering_fields = ('name', 'agent_id')
    search_fields = ('name', 'agent_id')
    permission_classes = [IsAdminUser]
    filter_fields = ('name', 'agent_id')


class ActionExecutionView(viewsets.ModelViewSet):
    model = ExecuteAction
    queryset = ExecuteAction.objects.all()
    serializer_class = ExecuteActionSerializer
    filter_backends = (filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend,)
    ordering_fields = ('id',)
    filter_fields = ('id',)

    def create(self, request, *args, **kwargs):
        try:

            data = request.data
            tenant_uuid = data.get('tenant')
            action = data.get('action')
            res = self._create(data)
            return Response(res)

        except Exception as e:
            return Response(
                {'message': 'Error occurred while requesting to execute action %s, for the tenant: %s, Error: %s' % (
                    action, tenant_uuid, str(e))},
                status=status.HTTP_400_BAD_REQUEST)

    def _create(self, data):
        tenant_uuid = data.get('tenant')
        connector_id = data.get('connector')
        config_id = data.get('configuration')
        action = data.get('action')
        request_payload = data.get('request_payload')

        conn_instance = Connector.objects.filter(id=connector_id).first()
        if conn_instance and conn_instance.status != 'completed':
            return Response(
                {'message': 'Connector Not Installed or Completed in remote instance, please try after some time'},
                status=status.HTTP_400_BAD_REQUEST)
        tenant_instance = Tenant.objects.filter(uuid=tenant_uuid).first()

        config_instnace = None
        if config_id:
            config_instnace = Configuration.objects.filter(config_id=config_id).first()

        if not tenant_instance:
            return Response({'message': 'Invalid Input :: Tenant: %s is not known to master.' % tenant_uuid},
                            status=status.HTTP_400_BAD_REQUEST)

        if not conn_instance:
            return Response({'message': 'Connector does not exists', }, status=status.HTTP_400_BAD_REQUEST)

        exc_data = {
            'request_id': '',
            'action': action,
            'status': 'in-progress',
            'request_payload': request_payload,
            'tenant': tenant_uuid,
            'connector': connector_id,
            'configuration': config_id
        }

        serializer = ExecuteActionSerializer(data=exc_data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        exc_data = serializer.data
        request_id = instance.id
        exc_data['request_id'] = request_id
        return exc_data

    def purge(self, request, *args, **kwargs):
        keep_days = request.data.get('keep_days', 1)
        queryset = ExecuteAction.objects.filter(created__lte=(datetime.now() - timedelta(days=keep_days)),
                                                remote_status__status__in=[REMOTE_STATUS.get('finished'),
                                                                           REMOTE_STATUS.get('failed')]
                                                )
        queryset._raw_delete(queryset.db)

        return Response({'message': 'Purged log successfully'})


class AgentInstallerView(APIView):

    def post(self, request, *agrs, **kwargs):
        data = request.data
        agent = data.get('agent')
        remote_upgrade = data.get('remote_upgrade', False)
        include_last_known_configurations = data.get('include_last_known_configurations', False)
        connectors = data.get('connectors', [])

        agent_obj = load_agents_config(agent_id=agent)

        if not agent_obj:
            return Response({'message': 'Agent %s does not exists.' % agent}, status=status.HTTP_400_BAD_REQUEST)

        agent_obj = agent_obj[0]

        if agent_obj.get('agentType', {}).get('@id') == settings.FSR_NODE:
            return Response(fsr_node_config(agent_obj))

        agent_instance = Agent.objects.filter(agent_id=agent).first()

        if not agent_instance:
            return Response({'message': 'Agent %s is not yet created in integration' % agent},
                            status=status.HTTP_400_BAD_REQUEST)

        path = AGENT_INSTALLER_DESTINATION_PATH + '/' + agent
        if os.path.exists(path):
            shutil.rmtree(path)
        shutil.copytree(AGENT_INSTALLER_SOURCE_PATH, path)

        prepare_connectors_json(path, agent_instance, connectors, include_last_known_configurations)
        yaml_read_and_replace(path, agent_obj)

        # Append helper file at end of file
        cmd = "tar -C " + path + " -czf - agent_helper.py >>" + path + "/setup.sh"
        output = execute_cmd(cmd)
        if type(output) == bool:
            return Response({"message": "Cannot tar helper file"}, status=status.HTTP_400_BAD_REQUEST)
        file_path = path + '/setup.sh'

        if remote_upgrade:
            upgrade_file = open(path + '/setup.sh', "rb")
            b_upgrade_file = upgrade_file.read()
            upgrade_file.close()
            key = agent + CONSTANT_PHRASE
            h = hmac.new(bytes(key, 'utf-8'), b_upgrade_file, hashlib.sha256)

            remote_operation = RemoteOperations()
            remote_operation.agent_upgrade(agent_id=agent,
                                           b_upgrade_file=base64.b64encode(b_upgrade_file),
                                           hkey=h.hexdigest())
            body = {
                'upgradeState': '3daa69fc-7c46-4447-be7e-eadad394acad',
                'upgradeMessage': None
            }
            response = make_request(agent_obj.get('@id'), 'PUT', body)
            publish_audit_and_notify({}, method='Upgrade', module='Agent',
                                     exchange='texchange.cyops.agent', routing_key='key.agent.audit',
                                     title="Agent [" + agent_obj.get('name', '') + "] upgrade started", request=request)
            return Response({'message': 'Agent upgrade initiated'}, status=status.HTTP_200_OK)

        try:
            with open(file_path, 'rb') as shfile:
                content = shfile.read()
            response = HttpResponse(content)
            response['content_type'] = 'application/text'
            response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(file_path)
            shutil.rmtree(path, ignore_errors=True)
            return response
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AgentActionView(APIView):
    permission_classes = [IsAgentAuthenticated]

    def post(self, request, *agrs, **kwargs):
        data = request.data
        agent = data.get('agent')
        action = data.get('action')

        agent_instance = Agent.objects.filter(agent_id=agent).first()
        if not agent_instance:
            return Response({'message': 'Agent %s is not yet created in integration' % agent},
                            status=status.HTTP_400_BAD_REQUEST)

        agent_obj = load_agents_config(agent_id=agent)
        if not agent_obj:
            return Response({'message': 'Cannot find agent with id: %s.' % agent}, status=status.HTTP_400_BAD_REQUEST)
        agent_obj = agent_obj[0]

        if action == log_collect:
            if agent_obj.get('agentType', {}).get('@id') == settings.FSR_NODE:
                return Response({"message": "Log collection allowed only for FSR Agent Node"},
                                status=status.HTTP_400_BAD_REQUEST)
            remote_operation = RemoteOperations()
            remote_operation.agent_log_collect(agent_instance=agent_instance)
            return Response({'message': 'Agent log collect initiated'}, status=status.HTTP_200_OK)
        return Response({'message': 'No matching action found'}, status=status.HTTP_400_BAD_REQUEST)


def fsr_node_config(agent_obj):
    # Self id will represent agentId
    # agentId here represent master id in context of agent
    pass


def yaml_read_and_replace(path, agent_obj):
    pass


def execute_cmd(cmd, ignore_failure=False):
    pipes = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    std_out, std_err = pipes.communicate()
    if (pipes.returncode != 0) and (not ignore_failure):
        # an error happened!
        return False
    ret = pipes.returncode
    std_out = std_out.strip().decode("utf-8")
    std_err = std_err.strip().decode("utf-8")
    return (ret, std_out, std_err)


def prepare_connectors_json(path, agent_instance, connectors, include_last_known_configurations):
    if include_last_known_configurations:
        # connectors instances bound with agent
        connector_instances = Connector.objects.filter(agent=agent_instance.agent_id)
        for connector in connector_instances:
            config_serializer = ConnectorConfigurationAgentSerializer(connector.configuration.all(), many=True)
            configurations = config_serializer.data
            connectors.append({
                'name': connector.name,
                'version': connector.version,
                'rpm_full_name': connector.rpm_full_name,
                'configurations': configurations
            })
    utility_connector_obj = Connector.objects.filter(name='cyops_utilities', agent=settings.SELF_ID).first()
    if utility_connector_obj:
        connectors.append({
            'name': utility_connector_obj.name,
            'version': utility_connector_obj.version,
            'rpm_full_name': utility_connector_obj.rpm_full_name}
        )

    with open(os.path.join(path, 'connectors.json'), 'w') as f:
        json.dump(connectors, f)
