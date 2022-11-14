import glob
import re
import tarfile
import tempfile

import pkg_resources
import requests

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.mixins import UpdateModelMixin, DestroyModelMixin, RetrieveModelMixin
from rest_framework.parsers import FileUploadParser
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from annotation.models import is_valid_annotation_name
from connectors.apps import configure_proxy
from connectors.core.connector import CustomConnectorException
from connectors.decorators import json_response
from connectors.helper import *
from connectors.models import Operation, Configuration, Role
from connectors.permissions import IsAgentAuthenticated
from connectors.serializers import ConnectorDetailSerializer, ConnectorListSerializer, ConnectorOperationSerializer, \
    ConnectorListConfigurationSerializer
from connectors.utils import broadcast_message, find_or_update_connector_with_rpm_fullname, download_connector_rpm, \
    identify_if_dependencies_installed
from connectors.utils import get_connector_path, get_configuration, get_operation, is_operation_param_valid, \
    get_previous_version_details, symlink_system_connector, check_broadcast_to_cluster, \
    connector_actions_serializer, insert_connector, is_replace, get_connector_or_latest, get_or_create_team_or_role
from connectors.utils import get_connector_version_or_latest, import_playbook, check_permission, sync_ha_nodes, \
    get_parsed_config, get_rbac_info, is_connector_installed
from audit.audit import audit_connector_functions
from integrations.crudhub import make_request
from postman.models import Agent, Tenant
from urllib3.exceptions import InsecureRequestWarning


class ConnectorList(ModelViewSet):
    serializer_class = ConnectorListSerializer
    filter_backends = (filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend,)
    ordering_fields = ('id', 'name', 'label')
    search_fields = ('$id', '$label')
    filter_fields = ('id', 'name', 'category', 'active', 'ingestion_supported', 'status', 'system')
    ordering = ('id',)

    def get_queryset(self):
        agent_id = self.request.GET.get('agent', settings.SELF_ID)
        queryset = Connector.objects.filter(agent_id=agent_id, development=False).defer('icon_large', 'configuration',
                                                                     'playbook_collections')
        if 'configured' in self.request.GET:
            configured = self.request.GET.get('configured')
            if configured.lower() == 'true':
                queryset = self.filter_queryset(
                    queryset=Connector.objects.filter(~Q(config_count=0), agent_id=agent_id, development=False))
            elif configured.lower() == 'false':
                queryset = self.filter_queryset(queryset=Connector.objects.filter(config_count=0, agent_id=agent_id, development=False))
        if CONNECTOR_TAG_FILTER in self.request.GET:
            tags = self.request.GET.get(CONNECTOR_TAG_FILTER)
            queryset = Connector.objects.filter(tags__contains=tags.split(','), agent_id=agent_id, development=False)
        return queryset


    def connector_action_details(self, request, *args, **kwargs):
        connector_name = self.kwargs.get('connector', None)
        connector_agent = request.GET.get('agent', settings.SELF_ID)
        connector_version = self.kwargs.get('version', None)
        operation_name = request.GET.get('operation', None)
        exclude = request.GET.get('exclude', '').split(',')
        teams = request.data.get('rbac_info', {}).get('teams', [])
        roles = request.data.get('rbac_info', {}).get('roles', [])
        connector_object= {}
        connector_fields = ['name', 'version', 'label', 'icon_large', 'config_count', 'agent_id', 'publisher', 'cs_approved']
        operation_fields = ['operation', 'title', 'visible', 'parameters']
        if isinstance(teams, str):
            teams = json.loads(teams)
        if isinstance(roles, str):
            roles = json.loads(roles)
        connector_querset = Connector.objects.filter(name=connector_name, version=connector_version, agent_id=connector_agent,
                                              development=False)
        if not connector_querset.exists():
            error_message = 'No matching connector by name {0} version {1} exists.'.format(connector_name, connector_version)
            return Response({"message": error_message}, status=status.HTTP_404_NOT_FOUND)

        connector = connector_querset.first()
        if operation_name:
            operation = connector.operations.filter(operation=operation_name).first()
            operation_data = ConnectorOperationSerializer(operation).data
            if not list(set(operation_data.get('roles')) & set(roles)) and operation_data.get('roles'):
                operation_data['has_permissions'] = False
            else:
                operation_data['has_permissions'] = True

            connector_object['operations'] = [operation_data]

        if 'configuration' not in exclude:
            config_query = connector.configuration.filter(Q(teams__isnull=True) | Q(teams__in=teams)).distinct()
            config_serializer = ConnectorConfigurationSerializer(config_query, many=True)
            connector_object['configurations'] = config_serializer.data

        for field in connector_fields:
            connector_object[field] = getattr(connector, field, None)

        return Response({"data": connector_object, "status": "Success"}, status=status.HTTP_200_OK)


    def connector_actions(self, request, *args, **kwargs):
        connector_agent = request.GET.get('agent', settings.SELF_ID)
        configured = request.GET.get('configured', 'all')
        ingestion_supported = True if request.GET.get('ingestion_supported') and request.GET.get('ingestion_supported').lower() == 'true' else False
        active = True if request.GET.get('active') and request.GET.get('active').lower() == 'true' else False
        exclude = request.GET.get('exclude', '').split(',')
        export = True if request.GET.get('$export') and request.GET.get('$export').lower() == 'true' else False
        connector_fields = ['name', 'version', 'label', 'icon_small', 'config_count', 'agent_id', 'active', 'status']
        operation_fields = ['operation', 'title', 'visible']
        connectors_data = []
        roles = request.data.get('rbac_info', {}).get('roles', [])
        teams = request.data.get('rbac_info', {}).get('teams', [])
        connector_filter = {'agent_id': connector_agent, 'development': False}
        if active:
            connector_filter.update({'active': True})
        if ingestion_supported:
            connector_filter.update({'ingestion_supported': True})
            connector_fields.append('icon_large')
        if isinstance(teams, str):
            teams = json.loads(teams)
        if isinstance(roles, str):
            roles = json.loads(roles)

        if configured.lower() == 'true':
            connectors = Connector.objects.filter(~Q(config_count=0), **connector_filter)
            configured = True
        elif configured.lower() == 'false':
            connectors = Connector.objects.filter(config_count=0, **connector_filter)
            configured = False
        else:
            connectors = Connector.objects.filter(**connector_filter)
            configured = False

        for connector in connectors:
            connector_object = {}
            if configured or 'configuration' not in exclude:
                config_query = connector.configuration.filter(Q(teams__isnull=True) | Q(teams__in=teams)).distinct()
                if not export:
                    config_serializer = ConnectorListConfigurationSerializer(config_query, many=True)
                else:
                    config_serializer = ConnectorConfigurationSerializer(config_query, many=True)
                connector_object['configuration'] = config_serializer.data

            if 'operation' not in exclude:
                allowed_operation_query = connector.operations.filter(Q(roles__isnull=True) | Q(roles__in=roles)).distinct()
                allowed_operations = ConnectorOperationSerializer(allowed_operation_query, many=True).data
                allowed_operation_ids = []
                for allowed_operation in allowed_operations:
                    allowed_operation['has_permissions'] = True
                    allowed_operation_ids.append(allowed_operation.get('id'))
                denied_operation_query = connector.operations.filter(Q(roles__isnull=False) & ~Q(roles__in=roles) & ~Q(id__in=allowed_operation_ids)).distinct()
                denied_operations = ConnectorOperationSerializer(denied_operation_query, many=True).data
                for denied_operation in denied_operations:
                    denied_operation['has_permissions'] = False
                connector_object['operations'] = allowed_operations + denied_operations

            if export:
                connector_serializer_data = ConnectorListSerializer(connector).data
                connector_serializer_data.pop('configuration', None)
                connector_object.update(connector_serializer_data)
            else:
                for field in connector_fields:
                    connector_object[field] = getattr(connector, field, None)
            if connector_object:
                connectors_data.append(connector_object)

        return Response({"data": connectors_data, "status": "Success"}, status=status.HTTP_200_OK)


class ConnectorOperationView(ModelViewSet):
    model = Operation
    queryset = Operation.objects.all()
    serializer_class = ConnectorOperationSerializer
    filter_backends = (filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend,)
    ordering_fields = ('operation',)
    search_fields = ('$operation',)
    filter_fields = ('id', 'operation', 'agent')

    def operation_output_schema(self, request, *args, **kwargs):
        try:
            connector_name = self.kwargs.get('connector', None)
            connector_version = self.kwargs.get('version', 'latest')
            operation_name = request.data.get('operation', None)
            config_id = request.data.get('config', 'get_default_config')
            agent_id = request.data.get('agent')
            config_instance = None

            if not config_id == 'get_default_config':
                config_instance = Configuration.objects.filter(config_id=config_id).first()
                if config_instance:
                    agent_id = config_instance.agent_id

            if not agent_id:
                agent_id = settings.SELF_ID

            # Getting the connector with the given version or latest if given version not found
            # with respect to given agent or self if agent not provided.
            connector = get_connector_or_latest(connector_name, connector_version, agent_id=agent_id)
            if not connector:
                logger.warn('Connector with name {1} version {0} or latest version not found.'.format(connector_name,
                                                                                                      connector_version))
                return Response({"data": {"output_schema": {}}, "status": "Success"}, status=status.HTTP_200_OK)

            operation = get_operation(name=operation_name, conn_id=connector.id)

            if not config_instance and connector.config_count > -1:
                config_instance = Configuration.objects.get(connector=connector.id, default=True, agent_id=agent_id)

            api_output_schema = operation.get('api_output_schema', None)
            if api_output_schema:
                # For dynamic output schema by calling connector action
                output_schema = {}
                if not agent_id == settings.SELF_ID:
                    logger.warn("API based output schema is not supported for an agent configuration")
                else:
                    params = request.data.get('params', {})
                    input_data = {
                        "connector": connector_name,
                        "version": connector.version,
                        "params": params,
                        "operation": api_output_schema,
                        "config": config_instance.config_id if config_instance else None
                    }
                    try:
                        response, is_binary = ConnectorExecute.execute_connector_operation(input_data)
                        output_schema = response.get("data", {})
                    except Exception as e:
                        error_message = cs_integration_9.format(operation_name, connector_name, connector_version)
                        logger.warn("{0} ERROR: {1}".format(error_message, str(e)))
                response_data = {"output_schema": output_schema}
            elif operation.get('conditional_output_schema'):
                # For conditional output schema defined in info.json file
                response_data = {
                    "conditional_output_schema": operation.get('conditional_output_schema')
                }
            else:
                # For static output schema defined in info.json file
                response_data = {
                    "output_schema": operation.get('output_schema', {})
                }
            return Response({"data": response_data, "status": "Success"}, status=status.HTTP_200_OK)
        except Exception as e:
            error_message = cs_integration_9.format(operation_name, connector_name, connector_version)
            logger.error('{0} ERROR: {1}'.format(error_message, str(e)))
            return Response({'message': error_message}, status=status.HTTP_400_BAD_REQUEST)


class ConnectorConfigurationView(ModelViewSet):
    model = Configuration
    queryset = Configuration.objects.all()
    serializer_class = ConnectorConfigurationSerializer
    filter_backends = (filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend,)
    ordering_fields = ('config_id',)
    search_fields = ('$name', '$config_id',)
    filter_fields = ('id', 'name', 'config_id', 'connector', 'agent')
    old_data = {}

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_configuration_obj(pk)

    def create(self, request, *args, **kwargs):
        data = request.data
        _classObj = get_executable_class(data)
        return _classObj.create_connector_config(data, request)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = {"agent": instance.agent.agent_id}
        _classObj = get_executable_class(data)
        data = request.data
        return _classObj.update_connector_config(instance, data, partial, request)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        data = {"agent": instance.agent.agent_id}
        _classObj = get_executable_class(data)
        return _classObj.delete_connector_config(instance, request)


class ProxySettingView(APIView):
    @json_response
    def post(self, request):
        logger.info('Setting Proxy variables in env')
        configure_proxy(request.data)
        return Response()


class ConnectorInstall(APIView):
    @json_response
    def post(self, request):
        connector_response = []
        data = request.data
        connector = data.get('name')
        version = data.get('version')
        agent_ids = data.get('agent', settings.SELF_ID)
        if type(agent_ids) != list:
            _classObj = get_executable_class(data)
            return _classObj.connector_install(data, request)

        _classObj = RemoteOperations()
        for agent in agent_ids:
            data['agent'] = agent
            connector_response.append(_classObj.connector_install(data, request))
        return Response({'remote_status': {'status': REMOTE_STATUS.get('awaiting')},
                         'message': 'Installing connector {0} version {1}'.format(connector, version)})

    def put(self, request):
        request.data['_action'] = 'upgrade'
        return self.post(request)

    def delete(self, request):
        data = request.data
        _classObj = get_executable_class(data)
        return _classObj.connector_delete(data)


class ConnectorImport(APIView):
    parser_classes = (FileUploadParser,)

    @json_response
    def post(self, request, filename):
        logger.info('Importing connector.')
        replace = False
        replace_str = request.GET.get('replace')
        rpm_installed = request.GET.get('rpm_installed')
        rpm_name = request.GET.get('rpm_name')
        rpm_full_name = request.GET.get('rpm_full_name')
        rbac_info = get_rbac_info(request)
        validate_connector_operation_input({"rpm_name":rpm_name, "rpm_full_name":rpm_full_name})
        if replace_str and (replace_str.lower() == 'true'):
            replace = True
        if rpm_installed:
            if rpm_installed.lower() == 'true':
                rpm_installed = True
            else:
                rpm_installed = False

        try:
            uploaded = request.FILES['file']
            filename = uploaded.name
        except Exception as exp:
            logger.error('{0} ERROR :: {1}'.format(cs_integration_1, str(exp)))
            return Response({'message': cs_integration_1}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # generate a hash and write the file to disk
            connectors_dir = os.path.join(tempfile.gettempdir(), 'connectors')
            if not os.path.exists(connectors_dir):
                os.mkdir(connectors_dir, 0o755)
            connector = os.path.join(connectors_dir, 'conn_%s%s' % (
                filename, settings.CONNECTORS_EXTENSION))
            with open(connector, 'wb') as f:
                for line in uploaded.readlines():
                    f.write(line)
            # Import connector
            # Delete uploaded file from REST call
            delete_uploaded_file = True
            result = import_connector(connector_path=connector,
                                      replace=replace,
                                      delete_uploaded_file=delete_uploaded_file,
                                      rpm_installed=rpm_installed,
                                      rpm_name=rpm_name,
                                      rpm_full_name=rpm_full_name,
                                      rbac_info=rbac_info
                                      )
            return Response(result)
        except ConnectorError as e:
            error_message = 'From the connector import exception handling %s' % str(e)
            logger.exception(error_message)
        except Exception as e:
            error_message = 'Error occurred while installing connector %s'% str(e)
            logger.exception(error_message)

        # ======== Auditing ========
        try:
            connector_name = rpm_name or rpm_full_name or filename
            audit_message = 'Connector [{0}] Install Failed'.format(connector_name)
            audit_data = {
                'data':{'message': error_message},
                'connector':connector_name
            }
            audit_connector_functions(audit_data, 'install_failed', 'install_failed', 'Connector', audit_message, rbac_info)
        except Exception as e:
            logger.exception(
                'Failed auditing configuration add operation for connector: {0}, version: {1}'.format(
                    result.get('name'), result.get('version')))
        # ======== Auditing ========
        return Response({'message': error_message}, status=status.HTTP_400_BAD_REQUEST)


class ConnectorDetail(RetrieveModelMixin,
                      UpdateModelMixin,
                      DestroyModelMixin,
                      GenericViewSet):
    queryset = Connector.objects.all()
    serializer_class = ConnectorDetailSerializer
    permission_classes = [IsAgentAuthenticated]

    def get_object(self):
        pk = self.kwargs.get('pk', None)
        if pk is not None:
            return super(ConnectorDetail, self).get_object()
        name = self.kwargs.get('name', None)
        version = self.kwargs.get('version')
        agent_id = self.request.query_params.get('agent', settings.SELF_ID) if hasattr(self,
                                                                                       'request') else settings.SELF_ID
        try:
            version = get_connector_version_or_latest(name, version, None, agent_id)
            connector = Connector.objects.get(name=name, version=version, agent_id=agent_id)
        except Connector.DoesNotExist:
            raise Http404('No matching connector by name %s exists.' % name)
        return connector

    def retrieve_post(self, request, *args, **kwargs):
        return self._retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        data.update({"agent": instance.agent.agent_id})
        _classObj = get_executable_class(data)
        return _classObj.connector_detail_update(data, instance, request, partial)

    def agents(self, request, *args, **kwargs):
        name = self.kwargs.get('name', None)
        team_uuid = []
        active = request.query_params.get('active', '')
        agent_version__gte = request.query_params.get('agent_version__gte', '0.0.0')
        query_dict = {
            'version__gte': agent_version__gte,
            'is_local': False
        }
        if active == 'true': query_dict.update({'active': True})

        agent_instances = Agent.objects.filter(**query_dict)

        if request.data.get('rbac_info', {}).get('teams'):
            team_uuid = json.loads(request.data.get('rbac_info', {}).get('teams'))

        connector_query_set = Connector.objects.filter(name=name, agent__in=agent_instances).order_by('agent__name')

        result = []
        for obj in connector_query_set:
            agent = obj.agent
            if team_uuid and not agent.team.filter(uuid__in=team_uuid).exists():
                continue
            connector = obj
            tenant_instances = Tenant.objects.filter(agent__in=[agent.id])
            tenants = [{'id': tenant.id, 'tenant_id': tenant.tenant_id, 'name': tenant.name}
                       for tenant in tenant_instances]
            data = {
                'id': agent.id,
                'agent': agent.agent_id,
                'agent_status': agent.active,
                'agent_name': agent.name,
                'agent_version': agent.version,
                'conn_id': connector.id,
                'conn_name': connector.name,
                'conn_version': connector.version,
                'active': connector.active,
                'allow_remote_operation': agent.allow_remote_operation,
                'system': connector.system,
                'remote_status': connector.remote_status,
                'status': connector.status,
                'tenants': tenants
            }
            result.append(data)
        return Response(result)

    def retrieve(self, request, *args, **kwargs):
        return Response({'Get method for this API is forbidden, Please use POST method for same API'})

    def _retrieve(self, request, *args, **kwargs):
        try:
            teams = request.data.get('rbac_info', {}).get('teams', [])
            instance = self.get_object()
            serializer = self.get_serializer(instance, teams=teams)
            result = serializer.data
            # Omit password field from configuration
            omit_password(result)
        except Http404 as err:
            logger.error(err)
            return Response({'message': str(err)},
                            status=status.HTTP_404_NOT_FOUND
                            )
        except Exception as exp:
            logger.exception('Retrieve:')
            return Response({'message': str(exp)},
                            status=status.HTTP_400_BAD_REQUEST
                            )
        return Response(result)

    @json_response
    def destroy(self, request, *args, **kwargs):
        remove_rpm = self.kwargs.pop('remove_rpm', True)
        instance = self.get_object()
        data = {"agent": instance.agent.agent_id}
        _classObj = get_executable_class(data)
        return _classObj.connector_detail_delete(instance, remove_rpm, request=request,
                                                 *args, **self.kwargs)


class ConnectorHealth(APIView):
    @json_response
    def get(self, request, name, version):
        logger.info('checking connector health')
        config_id = request.GET.get('config', 'get_default_config')
        config_instance = Configuration.objects.filter(config_id=config_id).first()

        if config_instance:
            agent_id = config_instance.agent.agent_id
        else:
            agent_id = settings.SELF_ID

        data = {"agent": agent_id}

        _classObj = get_executable_class(data)
        return _classObj.connector_health_check(config_id, name, version, request, agent_id)


class ConnectorDependencies(APIView):
    @json_response
    def get(self, request, name, version):
        agent = request.query_params.get('agent', settings.SELF_ID)
        logger.info('checking dependencies installed')
        conn_instance = Connector.objects.filter(name=name, version=version, agent=agent)
        if conn_instance:
            connector_obj = conn_instance.first()
            if connector_obj.requirements_installed == 'Completed':
                return Response({"dependencies_installed": True},
                                status=status.HTTP_200_OK)
            requirement_installed = identify_if_dependencies_installed(connector_obj.name, connector_obj.version, connector_obj)
            connector_obj.requirements_installed = 'Completed' if requirement_installed else 'Failed'
            connector_obj.save(update_fields=['requirements_installed'])
            return Response({"dependencies_installed": requirement_installed}, status=status.HTTP_200_OK)

    def post(self, request, name, version):
        agent = request.query_params.get('agent', settings.SELF_ID)
        logger.info('installing dependencies')
        conn_instance = Connector.objects.filter(name=name, version=version, agent=agent)
        if conn_instance:
            _install_connector_package(conn_instance.first())
            return Response({"status": "Initiated"}, status=status.HTTP_200_OK)
        return Response({"status": "No matching connector found"}, status=status.HTTP_404_NOT_FOUND)


class AgentHealth(APIView):
    @json_response
    def get(self, request, agent):
        logger.info('checking agent health')
        if agent and agent != 'all':
            data = {"agent": agent}
            _classObj = get_executable_class(data)
            return Response(_classObj.agent_health_check(data), status=status.HTTP_200_OK)
        _classObj = RemoteOperations()
        agent_list = Agent.objects.filter(is_local=False, active=True)
        for agent in agent_list:
            _classObj.agent_health_check({"agent": agent.agent_id})
        return Response({"message": "Agent health-check call initiated."})


class ConnectorExecute(APIView):
    @staticmethod
    def execute_connector_operation(input_data, name=None, version=None, agent_id=None):
        if not agent_id: agent_id = settings.SELF_ID
        if not (name or version):
            name = input_data.get('connector')
            version = get_connector_version_or_latest(name=name, version=input_data.get('version'), agent_id=agent_id)
        input_data['version'] = version
        validate_connector_operation_input({'name':name, 'version':version})
        operation = input_data.get('operation', '')
        params = input_data.get('params', {})
        env = input_data.get('env', {})
        input_data.pop('env', None)
        config_id = input_data.get('config', 'get_default_config')

        if not config_id:
            config_id = 'get_default_config'
        conn_obj = Connector.objects.get(name=name, version=version, agent_id=agent_id)

        if conn_obj.active:
            connector = get_connector_instance(name, version, conn_obj)

            operation = get_operation(operation, conn_obj.id)
            is_config_required = operation.get('is_config_required', True)
            config = get_configuration(**{'conn_id': conn_obj.id,
                                          'config_id': config_id,
                                          'decrypt': True,
                                          'config_schema': conn_obj.config_schema if is_config_required else {}})

            if config and not config.get('status', 0):
                message = 'The config {0} is partially configured and cannot be used for execution. ' \
                          'Complete and validate the connector configuration ' \
                          'by providing required inputs for the missing fields in the configuration.'

                logger.error(message.format(config.get('name')))
                raise ConnectorError(message.format(config.get('name')))

            params = is_operation_param_valid(operation, params)
            input_data['config'] = config
            input_data['params'] = params
            # change the handle operation params as there will no input validate check

            if input_data.get('audit', False):
                # audit_data contains the info about executed action
                # rbac_info it is been appended by CH for RBAC, contains user_iri and team_iri
                # audit_info it is add in body by UI for info on which record action was executed, contains record_iri
                audit_data = {
                    'connector': conn_obj.label,
                    'action': operation.get('title'),
                    'config': config.get('name'),
                    'version': version,
                    'params': params
                }
                input_data['rbac_info']['data'] = audit_data
                input_data['rbac_info'].update(input_data.get('audit_info'))

            secret_key = input_data.get('secret_key', '')
            if not secret_key == SEALAB_SECRET_KEY:
                try:
                    input_data['params'] = get_parsed_config(input_data.get('params'))
                except Exception as e:
                    pass
            response, is_binary = connector._handle_operation(input_data,
                                                              env=env
                                                              )
            return response, is_binary
        else:
            raise ConnectorError(cs_integration_4)

    def execute_connector_action(self, input_data, request=None):
        name = input_data.get('connector')
        version = input_data.get('version')
        env = input_data.get('env')
        request_id = input_data.get('request_id')
        config_id = input_data.get('config')
        agent_id = input_data.get('agent')
        if not agent_id: agent_id = settings.SELF_ID
        agent_instance = Agent.objects.get(agent_id=agent_id)
        pick_from_tenant = input_data.pop('pick_from_tenant', None)
        operation = input_data.get('operation', '')

        '''
        1. If Connector step has flag ‘pick_from_tenant’
            a. lookup tenant from record
            b. get all agents for the tenant
            c. get default config across these agents
            d. run if only one config found, error out in case of multiple

        2. Else if no ‘pick_from_tenant’
            a. lookup the config id. Run if found
            b. if config not found, see if agent id is defined
                b1. If agent id is not defined, lookup default config on self
                b2. If agent id is defined, it means connector was configured to run on an agent, and not self.
                Lookup default config across all agents other than self. Run if only one config found,
                error out for multiple
        3. In all above cases if connector with name and version does not exist, then find the latest version connector

        '''
        try:
            if pick_from_tenant:
                tenant_id = input_data.get('tenant')
                tenant_instance = Tenant.objects.filter(tenant_id=tenant_id).first()
                if not tenant_instance: raise ConnectorError(cs_integration_11)
                agent_instances = Agent.objects.filter(tenant__in=[tenant_instance.id]).values('agent_id')
                connector_pks = Connector.objects.filter(name=name, version=version, active=True,
                                                         agent_id__in=agent_instances).values('id')
                if not connector_pks:
                    connector_instances = [
                        Connector.objects.filter(name=name, active=True, agent_id=each_agent.get('agent_id')).order_by(
                            '-version').first() for
                        each_agent in agent_instances if
                        Connector.objects.filter(name=name, agent_id=each_agent.get('agent_id')).exists()]
                    if not connector_instances: raise ConnectionError(cs_integration_15.format(name))
                    connector_pks = [conn.id for conn in connector_instances]
                config_queryset = Configuration.objects.filter(default=True, agent_id__in=agent_instances,
                                                               connector_id__in=connector_pks)

            else:
                connector_instances = Connector.objects.filter(name=name, active=True, version=version)
                if not connector_instances.count():
                    connector_instances= Connector.objects.filter(name=name, active=True).order_by('-version')
                if not connector_instances.count():
                    raise ConnectionError(cs_integration_15.format(name))
                _config_queryset = Configuration.objects.filter(connector_id__in=connector_instances.values('id'))
                config_queryset = _config_queryset.filter(Q(config_id=config_id) | Q(name=config_id))

                if not config_queryset.count():
                    # if  there is no config found look for default config either at self
                    # or on all the agent expecting only one agent has marked a config default
                    # based on the agent id received
                    query = {'default': True}
                    if agent_id and agent_id != settings.SELF_ID:
                        agent_instances = Agent.objects.filter(is_local=False).values('agent_id')
                    else:
                        agent_instances = Agent.objects.filter(agent_id=settings.SELF_ID).values('agent_id')
                    query.update({'agent_id__in': agent_instances})
                    config_queryset = _config_queryset.filter(**query)

                elif config_queryset.count() > 1:
                    # apply agent query when there are multiple config present with same name
                    config_queryset = _config_queryset.filter(agent_id=agent_instance.agent_id)

            if config_queryset.count() == 1:
                config_instance = config_queryset.first()
                config_id = config_instance.config_id
                input_data['config'] = config_id
                agent_instance = config_instance.agent
                version = get_connector_version_or_latest(name=name, version=version, agent_id=agent_instance.agent_id)
                input_data['version'] = version
                connector_instance = Connector.objects.filter(name=name, version=version,
                                                              agent_id=agent_instance.agent_id).first()
                operation = get_operation(operation, connector_instance.id)
                if not operation.get('is_config_required', True):
                    config_instance = None
            else:
                config_instance = None
                if config_queryset.count() > 1:
                    raise ConnectorError(cs_integration_13)
                elif config_queryset.count() == 0:
                    version = get_connector_version_or_latest(name, version)
                    connector_instance = Connector.objects.filter(name=name, version=version, agent_id=agent_instance.agent_id).first()
                    if not connector_instance.active:
                        raise ConnectorError(cs_integration_17.format(connector_instance.name))
                    operation = get_operation(operation, connector_instance.id)
                    if connector_instance.config_schema:
                        if operation.get('is_config_required', True):
                            raise ConnectorError(cs_integration_12.format(config_id))

            team_uuid = []

            if input_data.get('rbac_info', {}).get('teams'):
                team_uuid = json.loads(input_data.get('rbac_info', {}).get('teams'))

            if agent_instance and team_uuid and not agent_instance.is_local and not agent_instance.team.filter(uuid__in=team_uuid).exists():
                return Response(status=status.HTTP_403_FORBIDDEN)

            if not agent_instance.active:
                return Response({'message': cs_integration_18.format(agent_instance.name)}, status=status.HTTP_400_BAD_REQUEST)

            if agent_instance and not agent_instance.is_local:
                if agent_instance.allow_remote_operation:
                    return RemoteOperations().execute_connector_action(config_id, input_data, agent_instance.agent_id,
                                                                   request=request)
                else:
                    return Response({'message': cs_integration_16}, status=status.HTTP_403_FORBIDDEN)

            check_permission(ConnectorConfigurationSerializer(config_instance).data if config_instance else {},
                             operation, input_data)

            # check if response should be fetched from primary
            if not settings.LW_AGENT:
                is_primary, primaryNodeId = is_active_primary()
                ingestion_modes = connector_instance.metadata.get('ingestion_modes', [])
                if not is_primary and NOTIFICATION_BASED_INGESTION in ingestion_modes:
                    connector_response_json = get_response_primary(primaryNodeId, request.META['REQUEST_URI'], 'POST',
                                                                   input_data)
                    return Response(connector_response_json, status=status.HTTP_200_OK)

            response, is_binary = ConnectorExecute.execute_connector_operation(input_data, name, version)
            broadcast_data = response
            broadcast_data['_status'] = True
            broadcast_data['request_id'] = request_id
            broadcast_message(broadcast_data, execute_action_ack, 'receiveRemoteConnectorExecutionRequest',
                              'POST', agent_instance)
            # removing this from connector response to avoid unwanted fields
            response.pop('_status', None)
            response.pop('request_id', None)
            if is_binary:
                return HttpResponse(content=response, content_type='application/octet-stream',
                                    status=status.HTTP_200_OK)
            else:
                return Response(response, status=status.HTTP_200_OK)

        except Connector.DoesNotExist:
            logger.error('Connnector {0} with version {1} not found'.format(name, version))
            broadcast_data = {'name': name, 'version': version,
                              'message': 'Could not find connector with the specified id or name',
                              'status': REMOTE_STATUS.get('failed')}
        except ConnectorError as e:
            logger.exception('Connector execution error stack trace')
            stack_trace = traceback.format_exc()
            message = '{0}  Connector :: {1}V{2}'.format(str(e), name, version)
            logger.error(message)
            broadcast_data = {'message': message, 'stack_trace': stack_trace, 'status': REMOTE_STATUS.get('failed')}

        except CustomConnectorException as exp:
            message = str(exp)
            logger.exception(message)
            return Response(
                {'message': message},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as exp:
            logger.exception('Connector execution error stack trace')
            stack_trace = traceback.format_exc()
            message = '{0} ERROR :: {1}'.format(cs_integration_5, str(exp))
            broadcast_data = {'message': message, 'stack_trace': stack_trace, 'status': REMOTE_STATUS.get('failed')}

        broadcast_data['_status'] = False
        broadcast_data['request_id'] = request_id
        if not broadcast_data.get('env'):
            broadcast_data['env'] = env
        broadcast_message(broadcast_data, execute_action_ack, 'receiveRemoteConnectorExecutionRequest',
                          'POST', agent_instance)
        return Response(broadcast_data, status=status.HTTP_400_BAD_REQUEST)

    @json_response
    def post(self, request):
        input_data = request.data
        secret_key = request.GET.get('secretKey', '') if request.GET.get('secretKey', '') == SEALAB_SECRET_KEY else ''
        input_data.update({"secret_key":secret_key})
        authorization = request.headers.get('forwarded-authorization') if hasattr(request, 'headers') else None
        if authorization:
            env = input_data.get('env', {})
            env.update({'authorization': authorization})
            input_data['env'] = env
        return self.execute_connector_action(input_data, request=request)


class OperationRoleView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        operation_id = kwargs.get("operation_id")
        roles = data.get("roles", [])
        try:
            operation_query_set = Operation.objects.filter(id=operation_id)
            if not operation_query_set.exists():
                raise Exception("Operation not found")
            operation_instance = operation_query_set.first()
            role_ids = get_or_create_team_or_role('role', roles)
            role_data = {'role_ids':role_ids}
            serializer = ConnectorOperationSerializer(operation_instance, role_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            error_message = "Error occurred while creating mapping of operation and roles"
            logger.error("{0} ERROR: {1}".format(error_message, str(e)))
            return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        data = request.data
        operation_id = kwargs.get('operation_id')
        roles = data.get("roles")
        link_roles = data.get("__link", {}).get("roles", [])
        unlink_roles = data.get("__unlink", {}).get("roles", [])
        role_ids = []
        try:
            operation_query_set = Operation.objects.filter(id=operation_id)
            if not operation_query_set.exists():
                raise Exception("Operation not found")
            operation_instance = operation_query_set.first()
            if not roles is None:
                operation_instance.roles.clear()
                role_ids = get_or_create_team_or_role('role', roles)
            if unlink_roles or link_roles:
                if link_roles:
                    link_roles = get_or_create_team_or_role('role', link_roles)
                if roles is None:
                    role_id_query = operation_instance.roles.all().values('uuid')
                    for role_id in role_id_query:
                        role_ids.append(role_id.get('uuid'))
                role_ids = get_update_list(role_ids, link_roles, unlink_roles)
            role_data = {'role_ids': role_ids}
            serializer = ConnectorOperationSerializer(operation_instance, role_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            error_message = "Error occurred while updating mapping of operation and roles"
            logger.error("{0} ERROR: {1}".format(error_message, str(e)))
            return Response(error_message, status=status.HTTP_400_BAD_REQUEST)


def get_executable_class(data):
    agent_id = data.get('agent', settings.SELF_ID)
    agent_obj = Agent.objects.filter(agent_id=agent_id).first()
    return identify_executable_class(agent_obj)


def install_or_remove_connector(rpm_name, conn_id, command='install', rpm_full_name=None):
    logger.info('connector %s started for rpm full name: %s', command, rpm_full_name)
    status = 'In-Progress'
    install_result = {}
    try:
        def get_truncate(value, chr_limit):
            if not type(value) == str:
                value = str(value)
            if len(value) > chr_limit:
                return value[-chr_limit:]
            return value

        my_env = os.environ.copy()
        conn_object = Connector.objects.filter(id=conn_id)
        connector_obj = conn_object.first()

        my_env['PATH'] = '/usr/sbin:/sbin:' + my_env['PATH']
        if not settings.LW_AGENT:
            yum_op_name = command
            cmd = ['sudo', 'csadm', 'package', yum_op_name, '--type',  'connector', '--name',  str(rpm_name), '--no-interaction']
            install_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=my_env)
            output, err = install_process.communicate(timeout=600)
            if err:
                raise Exception(err)
            elif output and command == 'install':
                try:
                    subprocess.check_output('rpm -qa | grep ' + str(rpm_name), shell=True)
                except subprocess.CalledProcessError:
                    raise Exception(output)
                logger.info(
                    'Connector {0} {1} command executed successfully. OUTPUT :: {2}'.format(rpm_name, command.title(),
                                                                                            output))
            if yum_op_name == 'install':
                requirement_installed = identify_if_dependencies_installed(connector_obj.name, connector_obj.version, connector_obj)
                connector_obj.requirements_installed = 'Completed' if requirement_installed else 'Failed'
                connector_obj.save(update_fields=['requirements_installed'])
        else:
            if command == 'install' and not rpm_full_name:
                rpm_full_name = find_or_update_connector_with_rpm_fullname(conn_object)
                if not rpm_full_name:
                    brodacast_connector_operation_message(conn_id, command, 'failed')
                    return False
            if command == 'install':
                status = _install_connector(rpm_full_name, rpm_name, my_env, connector_obj)
                requirement_installed = identify_if_dependencies_installed(connector_obj.name, connector_obj.version, connector_obj)
                connector_obj.requirements_installed = 'Completed' if requirement_installed else 'Failed'
                connector_obj.save(update_fields=['requirements_installed'])
                return status
            elif command == 'remove':
                return _remove_connector(rpm_name, my_env, conn_object.first())

    except subprocess.TimeoutExpired:
        if not conn_object[0].status == 'Completed':
            logger.error('Connector {0} Timed Out {1}'.format(command.title(), rpm_name))
            install_result['message'] = 'Connector {0} Timed Out'.format(command.title())
            install_result['output'] = ''
            status = 'Failed'
        else:
            logger.warn("Connector {0} subprocess got timeout before completing rpm process".format(command))
    except Exception as err:
        product_url = settings.PRODUCT_YUM_SERVER
        try:
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
            requests.get('https://' + product_url, verify=False)
        except Exception as e:
            err = cs_integration_14.format(product_url)
        logger.error('Connector {0} Failed With ERROR :: {1}'.format(command.title(), str(err)))
        error_message = get_truncate(err, 2000)
        install_result['message'] = 'Connector installation failed due to error: {0}'.format(error_message)
        install_result['output'] = error_message
        status = 'Failed'

    if command == 'install' and status == 'Failed':
        remote_status = install_result
        remote_status['status'] = 'failed'
        conn_object.update(status=status, install_result=install_result, remote_status=remote_status,
                           requirements_installed='Failed')
    try:
        if status == 'Failed':
            brodacast_connector_operation_message(conn_id, command, status)
    except Exception as e:
        error_message = 'Error occurred while broadcasting the {0} connector action {1} acknowledgement'.format(
            command, rpm_name)
        logger.error('{0} ERROR:: {1}'.format(error_message, str(e)))


def _remove_connector(rpm_name, my_env, conn_object):
    remove_process = subprocess.Popen(['sudo', '/bin/rpm', '-e', rpm_name, '--nodeps'],
                                      stdout=subprocess.PIPE,
                                      env=my_env,
                                      stderr=subprocess.DEVNULL)
    output, err = remove_process.communicate(timeout=600)
    if err:
        logger.exception('Exception Occurred while calling process {}'.format(str(err)))
    return SelfOperations().connector_detail_delete(conn_object, False)


def _install_connector(rpm_full_name, rpm_name, my_env, conn_object):
    '''
    Step 1. Download rpm using rpm_full_name from server
    Step 2. Try to Install the RPM via rpm -i command with --nodeps
    Step 3. Currently Fail for nginx and cyops-integrations dependency
    Step 4. In Step 3 tgz gets extracted from rpm at /opt/connector-name location
    Step 5. Call Install Connector via tgz command
    Step 6. Clean up the rpm and temp file
    '''
    status = 'Failed'
    try:
        downloaded_rpm_path = download_connector_rpm(rpm_full_name)
    except Exception as e:
        logger.exception('Error while downloading rpm %s: %s', rpm_full_name, str(e))
        raise e

    _install_rpm_dependencies(downloaded_rpm_path)

    remove_process = subprocess.Popen(['sudo', '/bin/rpm', '-e', rpm_name, '--nodeps'],
                                      stdout=subprocess.PIPE, env=my_env,
                                      stderr=subprocess.DEVNULL)
    remove_process.communicate(timeout=600)
    install_process = subprocess.Popen(['sudo', '/bin/rpm', '-U', downloaded_rpm_path, '--nodeps'],
                                       stdout=subprocess.PIPE, env=my_env,
                                       stderr=subprocess.DEVNULL)
    output, err = install_process.communicate(timeout=600)
    if err:
        logger.exception('Exception Occurred while calling process {}'.format(str(err)))
        clean_up_tmp_file(rpm_full_name, None)
        return status
    _rpm_name = 'cyops-connector-' + conn_object.name
    path = '/opt/' + _rpm_name
    conn_files = os.listdir(path)
    replace = True
    if 'compatibility.txt' in conn_files:
        with open(path + '/' + 'compatibility.txt', 'r') as compatibility:
            compatibility_version = compatibility.read().strip()
            replace = is_replace(conn_object.name, compatibility_version)
    file_name = [file for file in conn_files if file.endswith('.tgz')]
    if file_name:
        try:
            import_connector(path + '/' + file_name[0], replace, False)
            status = 'Success'
            _install_connector_package(conn_object)
        except Exception as e:
            logger.exception('Exception Occurred while installing connector {0}:  {1}'.format(_rpm_name, str(e)))
    clean_up_tmp_file(rpm_full_name, _rpm_name)
    return status


def clean_up_tmp_file(rpm_full_name=None, _rpm_name=None):
    tmp_file_path = os.path.join(settings.CONN_RPM_TEMP_DIR, rpm_full_name)
    if rpm_full_name and os.path.exists(tmp_file_path):
        os.remove(tmp_file_path)
    if _rpm_name and os.path.exists('/opt/' + _rpm_name):
        shutil.rmtree('/opt/' + _rpm_name, ignore_errors=True)


def _install_connector_package(conn_instance):
    install_connector_packages(conn_instance.name, conn_instance.version)


def _install_rpm_dependencies(downloaded_rpm_path):
    dependencies_to_install = []
    try:
        dependency_list = subprocess.run(['sudo', '/bin/rpm', '-qpR', downloaded_rpm_path],
                                         stdout=subprocess.PIPE).stdout.decode().split('\n')
        items_to_filter = ['/bin/sh', 'rpmlib', 'cyops']
        for each_dependency in dependency_list:
            is_to_filter_out = False
            for item in items_to_filter:
                if item in each_dependency:
                    is_to_filter_out = True
                    break
            if not is_to_filter_out and each_dependency:
                dependencies_to_install.append(each_dependency)
        logger.info('installing rpm dependencies: %s', dependencies_to_install)
        if dependencies_to_install:
            result = subprocess.run(['sudo', '/bin/yum', '-y', 'install', ' '.join(dependencies_to_install)], stdout=subprocess.PIPE).stdout.decode()
            logger.info('Rpm dependencies installation: %s', result)
    except Exception as e:
        logger.warn('Error while installing rpm dependencies: %s', dependencies_to_install)



def import_connector(connector_path, replace, isReserved=False, delete_uploaded_file=False, rbac_info={}, *args, **kwargs):
    # if its a cluster propagation command, db entry is not to be updated
    # check if there is a cluster command to install this connector
    rpm_installed, propagated, cluster_command = check_broadcast_to_cluster()
    rpm_installed = kwargs.get('rpm_installed', rpm_installed)
    rpm_name = kwargs.get('rpm_name', '')
    rpm_full_name = kwargs.get('rpm_full_name', '')
    audit_operation = kwargs.get('audit_operation', 'install_complete')
    if propagated:
        info = get_file_info(connector_path, replace, isReserved)
        install_connector_files(connector_path, info.get('name'), info.get('version'), replace)
        return ''

    # import previous version config if config schema is same
    info = validate_info(connector_path, replace, isReserved)
    try:
        config, prev_operation_role = get_previous_version_details(info, replace)
    except Exception as e:
        config = dict()
        prev_operation_role = dict()
        logger.warn('{0} ERROR :: {1}'.format(cs_integration_2, str(e)))

    # If Replace, remove all existing connectors
    data_ingestion = []
    if replace:
        connectors = Connector.objects.filter(name=info.get('name'), agent_id=settings.SELF_ID, status='Completed', development=False)
        for connector in connectors:
            connector.metadata.update({'upgrade_in_progress': True})
            connector.save(update_fields=['metadata'])
            remove_rpm = True
            if info.get('version') == connector.version:
                remove_rpm = False
            conn_detail_view = ConnectorDetail()
            conn_detail_view.kwargs = {'name': connector.name, 'version': connector.version, 'system_delete': True,
                                       'remove_rpm': remove_rpm, 'is_rpm_command': rpm_installed}
            conn_detail_view.destroy({'rbac_info': rbac_info})

    install_connector_files(connector_path, info.get('name'), info.get('version'), replace)
    playbook_collections = import_playbook(
        info.get('name'),
        info.get('label'),
        info.get('version'),
        info.get('icon_large_name'),
        info.get('override_playbook_info', True)
    )
    try:
        result = insert_connector(info=info, playbook_collections=playbook_collections, config=config,
                                  isReserved=isReserved, rpm_installed=rpm_installed, rpm_name=rpm_name,
                                  rpm_full_name=rpm_full_name, prev_operation_role=prev_operation_role)
        for di_obj in data_ingestion:
            di_obj.pk = None
            di_obj.save()

        conn_id = result.get('id')
        brodacast_connector_operation_message(conn_id, 'install', 'Success')
    except ConnectorError as e:
        if delete_uploaded_file: os.unlink(connector_path)
        raise ConnectorError(e)

    if delete_uploaded_file: os.unlink(connector_path)

    # publish as a cluster command:
    try:
        if cluster_command and not settings.LW_AGENT:
            add_command_response = make_request('/api/auth/clustercommand/', 'POST',
                                                {'commandId': 'connector-install', 'command': cluster_command})
            logger.info('result for publish of connector command: %s' % add_command_response)
        elif not rpm_installed and not propagated and not settings.LW_AGENT:
            path = get_connector_path(result.get('name', ''), result.get('version', ''))
            sync_ha_nodes(path, 'copy')
    except Exception as e:
        raise ConnectorError('Failed to publish connector install to cluster Error :: {0}'.format(str(e)))

    # ======== Auditing ========
    try:
        audit_message_action = 'Published' if audit_operation.lower() == 'publish' else 'Installed'
        audit_message = 'Connector [{0}] Version [{1}] {2}'.format(result.get('name'), result.get('version'), audit_message_action)
        audit_connector_functions(result, audit_operation, 'success', 'Connectors', audit_message, rbac_info)
    except Exception as e:
        logger.exception(
            'Failed auditing installation for connector: {0}, version: {1}'.format(
                result.get('name'), result.get('version')))
    # ======== Auditing ========
    return result


def install_connector_files(connector_path, name, version, replace=True):
    # remove previous folder if replace is true
    if replace:
        try:
            installed_connector_path = get_connector_path(name, '*')
            for path in glob.glob(installed_connector_path):
                shutil.rmtree(path)
        except Exception as e:
            logger.warn('Error while deleting connector: %s folder.', name)

    # extract it to connectors.
    tar = tarfile.open('%s' % (connector_path), 'r:gz')
    tar_extract_dir = os.path.join(settings.CONNECTORS_DIR, 'temp')
    os.makedirs(tar_extract_dir, exist_ok=True)
    tar.extractall(path=tar_extract_dir)
    tar.close()
    # rename version to folder.
    os.rename(os.path.join(tar_extract_dir, name),
              get_connector_path(name, version))

    # create symlink for system connector to latest version
    if name in settings.CONNECTORS_RESERVED:
        symlink_system_connector(name, version)


def update_connector(connector, configurations=[]):
    name = connector.get('name')
    version = connector.get('version')
    system = connector.get('system')
    playbook_collections = connector.get('playbook_collections')
    connector_path = get_connector_path(name, version)
    info_path = os.path.join(connector_path, 'info.json')
    try:
        with open(info_path) as json_file:
            info = json.load(json_file)
            if not info.get('name') == name or not info.get('version') == version:
                logger.error('Name or version mismatched in info file and database')
                raise ConnectorError('Name or version mismatched in info file and database')
    except Exception as e:
        logger.error('Error occurred while retrieving the info json ERROR :: {0}'.format(str(e)))
        raise ConnectorError('Error occurred while retrieving the info json ERROR :: {0}'.format(str(e)))

    insert_connector(info, playbook_collections, configurations, isReserved=system)


log_dir = os.path.dirname(settings.APP_LOG_FILE_PATH)


def get_file_info(filename, replace, isReserved=False, validate=True):
    try:
        with tarfile.open(filename) as td:
            contents = td.getnames()
    except:
        raise ConnectorError(
            'Error reading Connector package. File must be in .tgz format.')

    infonames = [fn for fn in contents if fn.endswith('/info.json')]
    if not len(infonames) == 1:
        raise ConnectorError(
            'Invalid connector structure :: info file of connector are either multiple or not provided.')

    conn_files = [fn for fn in contents if fn.endswith('/connector.py')]
    if not len(conn_files) == 1:
        raise ConnectorError(
            'Invalid connector structure :: connector.py file of connector either multiple or not provided.')

    try:
        with tarfile.open(filename, encoding='utf-8') as td:
            f = td.extractfile(infonames[0])
            info = json.loads(f.read().decode('utf-8'))
    except Exception as exp:
        raise ConnectorError('Error occurred while reading info file, inappropriate format for info block. ERROR :: {0}'
                             .format(str(exp)))
    if not validate:
        return info

    name = info.get('name', '')
    version = info.get('version', '')

    if not re.compile(r'[0-9]+.[0-9]+.[0-9]+$').match(version):
        raise ConnectorError('Invalid Inputs :: version field either is of invalid format or not provided.')

    if not re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*').match(name):
        raise ConnectorError('Invalid Inputs :: name field either is of invalid format or not provided.')

    if name + '/info.json' != infonames[0]:
        raise ConnectorError(
            'Name mismatch :: connector folder name and name in info.json should be same.')

    if not replace and os.path.exists(
            get_connector_path(name, version)):
        raise ConnectorError('Connector conflict :: Connector with same name is already active')
    return info


def validate_info(filename, replace, isReserved=False):
    info = get_file_info(filename, replace, isReserved)
    # validate annotation
    annotation_category_map = {}
    for op in info.get('operations', []):
        if op.get('annotation'):
            if op.get('annotation') in annotation_category_map and \
                    op.get('category', 'miscellaneous').lower() != annotation_category_map.get(
                op.get('annotation')):
                raise ConnectorError(
                    'Same annotation %s is defined in categories %s and %s. An annotation can be defined for only one \
                    category considering category as miscellaneous if not defined.' % (
                        op.get('annotation'),
                        op.get('category', 'miscellaneous'),
                        annotation_category_map.get(op.get('annotation'))
                    )
                )
            annotation_category_map.update({op.get('annotation'): op.get('category', 'miscellaneous').lower()})
            is_valid_annotation_name(op.get('annotation').lower(), op.get('category'))

    config_names = [each_field.get('name') for each_field in info.get('configuration', {}).get('fields', [])]
    if 'default' in config_names:
        logger.error('default is a reserved key in the connector config to specify whether a config is default or not. \
        It cannot be used in connector configuration schema.')
        raise ConnectorError('default is a reserved key in the connector config to specify whether a config is default or not. \
        It cannot be used in connector configuration schema.')

    if 'name' in config_names:
        logger.error('name is a reserved key in the connector config to specify whether a config is default or not. \
        It cannot be used in connector configuration schema.')
        raise ConnectorError('name is a reserved key in the connector config to specify whether a config is default or not. \
        It cannot be used in connector configuration schema.')

    return info


def install_connector_packages(connector_name, connector_version):
    file = get_connector_path(connector_name, connector_version)
    file = os.path.join(file, 'requirements.txt')
    if not os.path.exists(file):
        return
    command = ['/opt/cyops-integrations/.env/bin/pip', 'install', '-r', file]
    my_env = os.environ.copy()
    my_env['PATH'] = '/usr/sbin:/sbin:' + my_env['PATH']
    try:
        install_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=my_env)
        output, err = install_process.communicate()
        if err:
            raise Exception(err)
        elif output:
            logger.info('All the packages for connector installed successfully. OUTPUT :: {0}'.format(output))
    except Exception as e:
        logger.exception('Error in installing the packages of connector {0} v{1} ERROR:: {2}'.format(connector_name,
                                                                                                     connector_version,
                                                                                                     str(e)))
