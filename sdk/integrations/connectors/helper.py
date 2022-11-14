import copy
import json
import os
import shutil
import subprocess
import time
import traceback
import uuid
from threading import Thread

from django.http import Http404
from rest_framework import status
from rest_framework.response import Response

from annotation.views import remove_connector_from_annotation
from audit.audit import publish_audit_and_notify, audit_connector_functions
from connectors.core.connector import logger, ConnectorError
from connectors.core.constants import *
from connectors.errors.error_constants import *
from connectors.models import Connector, Configuration, Operation, ExecuteAction, Team
from connectors.serializers import ConnectorConfigurationSerializer, ConnectorDetailSerializer
from connectors.utils import broadcast_message, validate_connector_operation_input
from connectors.utils import (omit_password, is_active_primary, get_response_primary, validate_config,
                              get_connector_instance, update_pwd_field, decrypt_password,
                              get_configuration, on_active_status_update, check_broadcast_to_cluster,
                              on_connector_delete, get_connector_path, insert_connector, encrypt_password,
                              get_or_create_team_or_role, get_update_list, sync_ha_nodes)
from integrations.crudhub import make_request
from postman.models import Agent
from postman.serializer import ExecuteActionSerializer
from postman.utils.constants import *


class SelfOperations():
    def create_connector_config(self, data, request=None):
        agent_obj = None
        teams = data.get("teams", [])
        error_message = None
        try:
            conn_obj_list = Connector.objects.filter(id=data.get('connector'))
            if not conn_obj_list:
                raise Connector.DoesNotExist
            else:
                conn_obj = conn_obj_list.first()

            agent_obj = conn_obj.agent
            # check if response should be fetched from primary
            # For Light Weight agent this shouldn't be called, so initializing it to false
            if not settings.LW_AGENT:
                ingestion_modes = conn_obj.metadata.get('ingestion_modes', [])
                is_primary, primary_node_id = is_active_primary()
                if not is_primary and NOTIFICATION_BASED_INGESTION in ingestion_modes:
                    request_uri = request.META['REQUEST_URI']
                    connector_response_json = get_response_primary(primary_node_id, request_uri, 'POST',
                                                                   json.dumps(data))
                    return Response(connector_response_json, status=status.HTTP_200_OK)

            config = data.get('config', {})
            if not data.get('config_id', None):
                data['config_id'] = str(uuid.uuid4())
            validate_config(config, conn_obj.config_schema)
            decrypted_config = copy.deepcopy(config)
            decrypted_config['config_id'] = data.get('config_id')
            decrypted_config['name'] = data.get('name')
            encrypt_password(conn_obj.config_schema, config)

            if data.get('default', False):
                Configuration.objects.filter(
                    connector=data.get('connector'),
                    agent_id=agent_obj.agent_id,
                    default=True).update(default=False)


            create_data = {
                'config_id': data.get('config_id'),
                'name': data.get('name', ''),
                'default': data.get('default', False),
                'config': config,
                'connector': data.get('connector'),
                'agent': data.get('agent', agent_obj.agent_id)
            }

            if teams:
                team_ids = get_or_create_team_or_role('team', teams)
                create_data.update({"team_ids":team_ids})

            configuration_serializer = ConnectorConfigurationSerializer(data=create_data)
            try:
                configuration_serializer.is_valid(raise_exception=True)
                configuration_serializer.save()
            except Exception as e:
                error_message = 'Bad request data for configuration create'
                index = str(e).find('string=')
                if index:
                    start_index = index + len('string=\'')
                    end_index = str(e).find('\'', start_index)
                    error_message = error_message + ', ' + str(e)[start_index:end_index]
                else:
                    error_message = error_message + 'Error:: Data missing or Unique constraint violated'
                raise ConnectorError(error_message)

            conn_instance = get_connector_instance(conn_obj.name, conn_obj.version, conn_obj)
            try:
                conn_instance.on_add_config(decrypted_config, conn_obj.active)
            except Exception as e:
                logger.error('Configuration add listener for the connector {0} failed with Error :: {1}'.format(
                    conn_obj.name, str(e)))

            result = {
                'configuration': configuration_serializer.data,
                'config_schema': conn_obj.config_schema}
            conn_obj_list.update(config_count=conn_obj.config_count + 1)

            broadcast_data = result['configuration']
            broadcast_data['connector_name'] = conn_obj.name
            broadcast_data['connector_version'] = conn_obj.version
            broadcast_data['status'] = {
                'status': REMOTE_STATUS.get('finished'),
                'message': 'Connector {0} version {1} as been configured successfully'.format(conn_obj.name,
                                                                                              conn_obj.version)
            }
            broadcast_message(broadcast_data, configure_connector_ack, 'receiveRemoteConnectorInstructionRequest',
                              'POST',
                              agent_obj)

            omit_password(result)

        except Connector.DoesNotExist:
            error_message = cs_integration_6.format(data.get('connector'))
            logger.error(error_message)
        except ConnectorError as e:
            error_message = str(e)
            logger.error(error_message)
        except Exception as e:
            error_message = cs_integration_7.format(conn_obj.name, conn_obj.version)
            logger.error('{0} ERROR:: {1}'.format(error_message, str(e)))

        if error_message:
            response_data = {'message': error_message}
            audit_status = 'failed'
            response_status = status.HTTP_400_BAD_REQUEST
            broadcast_data = data
            broadcast_data['status'] = {
                'status': REMOTE_STATUS.get('failed'),
                'message': error_message
            }
            broadcast_message(broadcast_data, configure_connector_ack, 'receiveRemoteConnectorInstructionRequest',
                              'POST', agent_obj)
        else:
            response_data = result['configuration']
            audit_status = 'success'
            response_status = status.HTTP_201_CREATED

        # ======== Auditing ========
        try:
            if not settings.LW_AGENT:
                rbac_info = request.data.get('rbac_info', {})
                audit_message = 'Config [{0}] Added To Connector [{1}] Version [{2}]'.format(data.get('name'), conn_obj.name, conn_obj.version)
                audit_connector_functions(response_data, 'create_config', audit_status, 'Connector', audit_message, rbac_info)
        except Exception as e:
            logger.exception(
                'Failed auditing configuration add operation for connector: {0}, version: {1}'.format(
                    conn_obj.name,
                    conn_obj.version))
        # ======== Auditing ========

        return Response(response_data, status=response_status)

    def update_connector_config(self, instance, data, partial=False, request=None):
        try:
            agent_obj = instance.agent
            conn_obj = Connector.objects.get(id=data.get('connector'))
            conn_instance = get_connector_instance(conn_obj.name, conn_obj.version, conn_obj)
            team_ids = []
            error_message = None

            # check if response should be fetched from primary
            if not settings.LW_AGENT:
                ingestion_modes = conn_obj.metadata.get('ingestion_modes', [])
                is_primary, primary_node_id = is_active_primary()
                if not is_primary and NOTIFICATION_BASED_INGESTION in ingestion_modes:
                    connector_response_json = get_response_primary(primary_node_id, request.META['REQUEST_URI'], 'PUT',
                                                                   json.dumps(data))
                    return Response(connector_response_json, status=status.HTTP_200_OK)

            config = data.get('config', {})
            teams = data.pop('teams', None)
            link_teams = data.pop('__link', {}).get('teams', [])
            unlink_teams = data.pop('__unlink', {}).get('teams', [])
            update_pwd_field(config, instance.config, conn_obj.config_schema)
            validate_config(config, conn_obj.config_schema)
            decrypted_config = copy.deepcopy(config)
            decrypted_config['config_id'] = data.get('config_id')
            decrypted_config['name'] = data.get('name')

            prev_config = instance.config
            decrypt_password(prev_config, conn_obj.config_schema)
            prev_config['config_id'] = instance.config_id
            prev_config['name'] = instance.name

            encrypt_password(conn_obj.config_schema, config)
            data['status'] = 1
            data['agent'] = agent_obj.agent_id
            data['remote_status'] = {}

            if data.get('default', False):
                Configuration.objects.filter(connector=data.get('connector'),
                                             agent_id=agent_obj.agent_id,
                                             default=True).update(default=False)

            if teams is not None:
                instance.teams.clear()
                team_ids = get_or_create_team_or_role('team', teams)
            if unlink_teams or link_teams:
                if link_teams:
                    link_teams = get_or_create_team_or_role('team', link_teams)
                if teams is None:
                    team_id_query = instance.teams.all().values('uuid')
                    for team_id in team_id_query:
                        team_ids.append(team_id.get('uuid'))
                team_ids = get_update_list(team_ids, link_teams, unlink_teams)
            if team_ids:
                data.update({'team_ids':team_ids})
            else:
                partial =True

            serializer = ConnectorConfigurationSerializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}
            conn_instance.on_update_config(prev_config, decrypted_config, conn_obj.active)

            result = {
                'configuration': serializer.data,
                'config_schema': conn_obj.config_schema}

            broadcast_data = result['configuration']

            broadcast_data['status'] = {
                'status': REMOTE_STATUS.get('finished'),
                'message': 'Configuration {0} has been updated successfully'.format(instance.name)
            }
            omit_password(result)
            broadcast_message(broadcast_data, configuration_update_ack,
                              'receiveRemoteConnectorInstructionRequest',
                              'PUT', agent_obj)

        except Connector.DoesNotExist:
            error_message = cs_integration_6.format(data.get('connector'))
            logger.error(error_message)
        except ConnectorError as e:
            error_message = str(e)
            logger.error(error_message)
        except Exception as e:
            error_message = cs_integration_7.format(conn_obj.name, conn_obj.version)
            logger.error('{0} ERROR:: {1}'.format(error_message, str(e)))

        if error_message:
            response_data = {'message': error_message}
            response_status = status.HTTP_400_BAD_REQUEST
            audit_status = 'failed'
            data.update({'config_id': instance.config_id, 'name': instance.name,
                         'agent': instance.agent.agent_id, 'config': instance.config})
            broadcast_data = data
            broadcast_data['status'] = {
                'status': REMOTE_STATUS.get('failed'),
                'message': error_message
            }
            broadcast_message(broadcast_data, configuration_update_ack, 'receiveRemoteConnectorInstructionRequest',
                              'PUT', agent_obj)
        else:
            response_data = result['configuration']
            audit_status = 'success'
            response_status = status.HTTP_201_CREATED

        # ======== Auditing ========
        try:
            if not settings.LW_AGENT:
                rbac_info = request.data.get('rbac_info', {})
                audit_message = 'Config [{0}] Updated In Connector [{1}] Version [{2}]'.format(data.get('name'), conn_obj.name, conn_obj.version)
                audit_connector_functions(response_data, 'update_config', audit_status, 'Connector', audit_message, rbac_info)
        except Exception as e:
            logger.exception(
                'Failed auditing configuration add operation for connector: {0}, version: {1}'.format(
                    conn_obj.name,
                    conn_obj.version))
        # ======== Auditing ========

        return Response(response_data, status=response_status)

    def delete_connector_config(self, instance, request=None):
        error_message = None
        try:
            agent_obj = instance.agent
            config = instance.config
            conn_obj_list = Connector.objects.filter(id=instance.connector.id)
            if not conn_obj_list and not conn_obj_list[0]:
                raise Connector.DoesNotExist
            else:
                conn_obj = conn_obj_list[0]

            conn_instance = get_connector_instance(conn_obj.name, conn_obj.version, conn_obj)
            # check if response should be fetched from primary
            if not settings.LW_AGENT:
                is_primary, primary_node_id = is_active_primary()
                ingestion_modes = conn_obj.metadata.get('ingestion_modes', [])
                if not is_primary and NOTIFICATION_BASED_INGESTION in ingestion_modes:
                    connector_response_json = get_response_primary(primary_node_id, request.META['REQUEST_URI'],
                                                                   'DELETE')
                    return Response(connector_response_json, status=status.HTTP_200_OK)

            decrypt_password(config, conn_obj.config_schema)
            config['config_id'] = instance.config_id
            config['name'] = instance.name

            config_id = instance.config_id
            config_name = instance.name
            instance.delete()
            broadcast_data = {'config_id': config_id, 'name': config_name, 'status': {
                'status': REMOTE_STATUS.get('finished'),
                'message': 'Configuration %s Successfully Deleted' % config_name
            }}

            broadcast_message(broadcast_data,
                              configuration_removed_ack, 'receiveRemoteConnectorInstructionRequest', 'DELETE',
                              agent_obj)

            conn_instance.on_delete_config(config)
            if conn_obj.config_count > 0:
                conn_obj_list.update(config_count=conn_obj.config_count - 1)
        except Connector.DoesNotExist:
            logger.error('Cannot find the connector with connector id {0}'.format(instance.connector.id))
            error_message = 'Cannot find the connector with connector id {0}'.format(instance.connector.id)
        except ConnectorError as e:
            error_message = str(e)
        except Exception as e:
            error_message = 'Error occurred while deleting the config ERROR :: {0}'.format(str(e))
            logger.error(error_message)

        if error_message:
            response_data = {'data':{'message': error_message}, 'status': status.HTTP_400_BAD_REQUEST}
            audit_status = 'failed'
            data = {'config_id': instance.config_id, 'name': instance.name,
                    'agent': instance.agent.agent_id, 'config': instance.config}
            broadcast_data = data
            broadcast_data['status'] = {
                'status': REMOTE_STATUS.get('failed'),
                'message': error_message
            }
            broadcast_message(broadcast_data, configuration_removed_ack, 'receiveRemoteConnectorInstructionRequest',
                              'DELETE', agent_obj)
        else:
            response_data = {'status': status.HTTP_204_NO_CONTENT}
            audit_status = 'success'

        # ======== Auditing ========
        try:
            if not settings.LW_AGENT:
                rbac_info = request.data.get('rbac_info', {})
                audit_message = 'Config [{0}] Deleted From Connector [{1}] Version [{2}]'.format(instance.name, conn_obj.name, conn_obj.version)
                audit_connector_functions(response_data, 'delete_config', audit_status, 'Connector', audit_message, rbac_info)
        except Exception as e:
            logger.exception(
                'Failed auditing configuration add operation for connector: {0}, version: {1}'.format(
                    conn_obj.name,
                    conn_obj.version))
        # ======== Auditing ========

        return Response(**response_data)

    def connector_install(self, data, request=None):
        validate_connector_operation_input(data)
        rpm_name = data.pop('rpm_name', '')
        rpm_full_name = data.get('rpm_full_name', '')
        connector = data.get('name', None)
        version = data.get('version', None)
        agent = data.get('agent', settings.SELF_ID)
        data['agent'] = agent
        rbac_info = {}

        if rpm_name or rpm_full_name:
            try:
                if not connector or not version:
                    return Response({'message': 'Invalid Input :: connector name or version was not provided.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                conn_instance = Connector.objects.filter(name=connector, version=version, agent=agent).first()
                if conn_instance and conn_instance.status == 'In-Progress':
                    message = 'Connector you are trying to install is already in progress state Connector :: {0} v{1}'.format(
                        connector, version)
                    brodacast_connector_operation_message(conn_instance.id, 'install', 'in-progress')
                    return Response({'message': message})
                elif conn_instance and conn_instance.status == 'Completed':
                    message = 'Connector you are trying to install is already installed Connector :: {0} v{1}'.format(
                        connector, version)
                    brodacast_connector_operation_message(conn_instance.id, 'install', 'Success')
                    return Response({'message': message})

                conn_data = data
                conn_data['status'] = 'In-Progress'
                # conn_data['remote_status'] = {'status': REMOTE_STATUS.get('in_progress')}
                serializer = ConnectorDetailSerializer(conn_instance, data=conn_data, partial=True)
                serializer.is_valid(raise_exception=True)
                conn_instance = serializer.save()

                from connectors.views import install_or_remove_connector
                process = Thread(target=install_or_remove_connector,
                                 args=[rpm_name, conn_instance.id, 'install', rpm_full_name])
                process.start()
                
                # ======== Auditing ========
                try:
                    if request:
                        rbac_info = request.data.get('rbac_info', {})
                    audit_message = 'Connector [{0}] Version [{1}] Install Started'.format(connector, version)
                    audit_connector_functions(data, 'install_start', 'started', 'Connectors', audit_message,
                                              rbac_info)
                except Exception as e:
                    logger.exception('Failed auditing start installation for connector: {0}, version: {1}'.format(
                        connector, version))
                # ======== Auditing ========

                return Response({'message': 'Installing connector {0} version {1}'.format(connector, version)})
            except Exception as e:
                # ToDo Add Broadcast
                logger.error('Error while installing the connector rpm Error :: {0}'.format(str(e)))
        else:
            message = 'Invalid Input :: No connector rpm name or rpm_full_name was provided'
            brodacast_connector_operation_message(None, 'install', 'failed', connector, version, agent, message)
            return Response({'message': message},
                            status=status.HTTP_400_BAD_REQUEST)

    def connector_delete(self, data, rbac_info={}):
        validate_connector_operation_input(data)
        rpm_name = data.pop('rpm_name', None)
        connector = data.get('name', None)
        version = data.get('version', None)
        agent = data.get('agent', settings.SELF_ID)
        if rpm_name:
            try:
                if not connector or not version:
                    return Response({'message': 'Invalid Input :: connector name or version was not provided.'},
                                    status=status.HTTP_400_BAD_REQUEST)
                if 'cyops-connector' not in rpm_name:
                    return Response({'message': 'Invalid Input :: rpm name provided was not for connector'},
                                    status=status.HTTP_400_BAD_REQUEST)

                conn_instance = Connector.objects.filter(name=connector, version=version, agent=agent).first()
                conn_data = data
                conn_data['status'] = REMOTE_STATUS.get('uninstall_in_progress')
                serializer = ConnectorDetailSerializer(conn_instance, data=conn_data, partial=True)
                serializer.is_valid(raise_exception=True)
                conn_instance = serializer.save()
                from connectors.views import install_or_remove_connector
                process = Thread(target=install_or_remove_connector, args=[rpm_name, conn_instance.id, 'remove'])
                process.start()

                # ======== Auditing ========
                try:
                    audit_message = 'Connector [{0}] Version [{1}] Uninstall Started'.format(connector, version)
                    audit_connector_functions(data, 'uninstall_start', 'started', 'Connectors', audit_message,
                                              rbac_info)
                except Exception as e:
                    logger.exception('Failed auditing start installation for connector: {0}, version: {1}'.format(
                        connector, version))
                # ======== Auditing ========

                return Response({'message': 'Uninstalling connector {0} version {1}'.format(connector, version)})
            except Exception as e:
                logger.error('Error while uninstalling the connector rpm Error :: {0}'.format(str(e)))
        else:
            message = 'Invalid Input :: No connector rpm name was provided'
            brodacast_connector_operation_message(None, 'remove', 'failed', connector, version, agent, message)
            return Response({'message': message},
                            status=status.HTTP_400_BAD_REQUEST)

    def connector_health_check(self, config_id, name, version, request=None, agent=None,
                               request_id=None):
        agent_obj = None
        config = None
        if not agent: agent = settings.SELF_ID
        try:
            agent_obj = Agent.objects.get(agent_id=agent)
            if not config_id:
                config_id = 'get_default_config'
            conn_obj = Connector.objects.get(name=name, version=version, agent=agent)

            config = get_configuration(**{'conn_id': conn_obj.id, 'config_id': config_id, 'decrypt': True,
                                          'config_schema': conn_obj.config_schema})
            connector = get_connector_instance(name, version, conn_obj)
            # check if response should be fetched from primary
            if not settings.LW_AGENT:
                is_primary, primaryNodeId = is_active_primary()
                ingestion_modes = conn_obj.metadata.get('ingestion_modes', [])
                if not is_primary and NOTIFICATION_BASED_INGESTION in ingestion_modes:
                    connector_response_json = get_response_primary(primaryNodeId, request.META['REQUEST_URI'])
                    return Response(connector_response_json, status=status.HTTP_200_OK)
            response = connector.verify_health(config,
                                               conn_obj.active)
            response['name'] = name
            response['version'] = version
            response['config_id'] = config.get('config_id')
            broadcast_data = response
            broadcast_data['_status'] = True
            broadcast_data['request_id'] = request_id
            broadcast_message(broadcast_data, health_check_ack, 'receiveRemoteConnectorExecutionRequest',
                              'GET', agent_obj)
            return Response(response, status=status.HTTP_200_OK)
        except Connector.DoesNotExist:
            message = 'Connector {0} with version {1} not found'.format(name, version)
            logger.error(message)
            health_status = {'status': REMOTE_STATUS.get('disconnected'), 'message': message}
            broadcast_data = {'name': name, 'version': version, 'status': health_status}
        except ConnectorError as e:
            stack_trace = traceback.format_exc()
            message = 'Error on health check of the connector {0} version {1}: {2}'.format(name, version, str(e))
            logger.exception('{0} ERROR {1}'.format(message, str(e)))
            broadcast_data = {'status': REMOTE_STATUS.get('disconnected'), 'message': message,
                              'stack_trace': stack_trace}
        except Exception as e:
            stack_trace = traceback.format_exc()
            message = 'Error on health check of the connector {0} version {1}'.format(name, version)
            broadcast_data = {'status': REMOTE_STATUS.get('disconnected'), 'message': message,
                              'stack_trace': stack_trace}
            logger.exception('{0} ERROR {1}'.format(message, str(e)))

        broadcast_data['config_id'] = config.get('config_id') if config else config_id
        broadcast_data['_status'] = False
        broadcast_data['request_id'] = request_id
        broadcast_message(broadcast_data, health_check_ack, 'receiveRemoteConnectorExecutionRequest', 'GET', agent_obj)
        return Response(broadcast_data, status=status.HTTP_400_BAD_REQUEST)

    def agent_health_check(self, data):
        agent_id = data.get('agent')
        agent_instance = Agent.objects.filter(agent_id=agent_id).first()
        if not agent_instance:
            return Response(status=status.HTTP_404_NOT_FOUND)
        health_check = {'version': settings.RELEASE_VERSION,
                        'sync_time': int(time.time()),
                        'health_status': {'status': 'Agent Available'}}
        broadcast_data = data
        broadcast_data['status'] = health_check
        broadcast_data['_status'] = True
        broadcast_message(broadcast_data, agent_health_check_ack, 'receiveRemoteConnectorExecutionRequest',
                          'GET', agent_instance)
        return health_check

    def connector_detail_update(self, data, instance, request=None, partial=False):
        agent_obj = instance.agent
        try:
            old_status = instance.active
            new_status = data.get('active', instance.active)
            ingestion_modes = instance.metadata.get('ingestion_modes', [])
            if old_status != new_status:
                # check if response should be fetched from primary
                if not settings.LW_AGENT:
                    is_primary, primaryNodeId = is_active_primary()
                    if not is_primary and NOTIFICATION_BASED_INGESTION in ingestion_modes:
                        connector_response_json = get_response_primary(primaryNodeId, request.META['REQUEST_URI'],
                                                                       'PUT',
                                                                       json.dumps(data))
                        return Response(connector_response_json, status=status.HTTP_200_OK)

            serializer = ConnectorDetailSerializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            if old_status != new_status:
                config = get_configuration(
                    **{'conn_id': instance.id, 'decrypt': True, 'config_schema': instance.config_schema,
                       'convert_to_dict': True})
                on_active_status_update(instance.name, instance.version, old_status, new_status, config)
            result = serializer.data
            broadcast_data = result
            broadcast_data['status'] = {
                'status': REMOTE_STATUS.get('finished'),
                'message': 'Connector {0} version {1} has been updated successfully'.format(instance.name,
                                                                                            instance.version)
            }
            omit_password(result)
            broadcast_message(broadcast_data, update_connector_ack,
                              'receiveRemoteConnectorInstructionRequest',
                              'PUT', agent_obj)
            return Response(result)

        except Exception as e:
            logger.exception('Error occurred while updating the connector ERROR :: {0}'.format(str(e)))
            broadcast_data = data
            broadcast_data['status'] = {
                'status': REMOTE_STATUS.get('failed'),
                'message': 'Error occurred while updating the connector ERROR :: {0}'.format(str(e))
            }
            broadcast_message(broadcast_data, update_connector_ack,
                              'receiveRemoteConnectorInstructionRequest',
                              'PUT', agent_obj)
            return Response({'message': 'Error occurred while updating the connector, please check the logs'},
                            status=status.HTTP_400_BAD_REQUEST)

    def connector_detail_delete(self, instance, remove_rpm, *args, **kwargs):
        broadcast_data = {}
        request = kwargs.get('request')
        rbac_info = {}
        if isinstance(request, dict):
            rbac_info = request.get('rbac_info', {})
        elif request:
            rbac_info = request.data.get('rbac_info', {})
        try:
            broadcast_data.update({
                'name': instance.name,
                'version': instance.version,
                'agent': instance.agent.agent_id,
                'upgrade_in_progress': instance.metadata.get('upgrade_in_progress', False)
            })
            agent_obj = instance.agent
            if instance.version:
                rpm_name = 'cyops-connector-' + instance.name + '-' + instance.version
            else:
                rpm_name = 'cyops-connector-' + instance.name
            remove_rpm = get_remove_rpm(remove_rpm, rpm_name)
            if bool(instance.system) and not kwargs.get('system_delete', False):
                return Response({
                    'message': 'Reserved connector \'%s\' cannot be deleted.' % instance.name},
                    status=status.HTTP_400_BAD_REQUEST)

            is_rpm_command, propagated, cluster_command = check_broadcast_to_cluster()
            is_rpm_command = kwargs.get('is_rpm_command', is_rpm_command)

            logger.info('is_rpm_command %s, propagated: %s, cluster_command %s', is_rpm_command, propagated,
                        cluster_command)

            if not settings.LW_AGENT and not is_rpm_command and remove_rpm:
                data = {'name': instance.name, 'version': instance.version, 'rpm_name': rpm_name,
                        'agent': instance.agent.agent_id}
                return self.connector_delete(data, rbac_info=rbac_info)

            try:
                configuration = get_configuration(
                    **{'conn_id': instance.id, 'decrypt': True, 'config_schema': instance.config_schema,
                       'convert_to_dict': True})
                on_connector_delete(instance.name, instance.version, configuration)
            except Exception as e:
                logger.exception('Error : %s', str(e))

            if propagated:
                path = get_connector_path(instance.name, instance.version)
                if os.path.exists(path):
                    shutil.rmtree(path)
                else:
                    logger.warn('Connector %s folder is not found', instance.name)

                if not is_rpm_command and remove_rpm:
                    delete_thread = Thread(target=remove_connector_rpm, args=[instance.name, instance.version])
                    delete_thread.start()
                return
            if not settings.LW_AGENT:
                try:
                    [make_request(collection.get('@id'), 'DELETE', settings.APPLIANCE_PUBLIC_KEY)
                     for collection in instance.playbook_collections]
                    [make_request(collection.get('image'), 'DELETE', settings.APPLIANCE_PUBLIC_KEY)
                     for collection in instance.playbook_collections if collection.get('image')]
                except Exception as e:
                    logger.warn('Error while deleting associated Playbook Collection : %s', str(e))

            try:
                operation_object = Operation.objects.filter(connector=instance.id).first()
                remove_connector_from_annotation(instance.id, operation_object.operation)
            except Exception as e:
                logger.warn('Error while removing connector %s from annotation(s): %s', instance.name, str(e))

            # for system connectors, there could be a dangling symlink
            # but since system connectors can only be replaced, and never deleted
            # the symlink_system_connector will delete the old link
            # remove symlink if system connector delete is supported in future
            path = get_connector_path(instance.name, instance.version)
            if os.path.exists(path):
                shutil.rmtree(path)
            else:
                logger.warn('Connector %s folder is not found', instance.name)


            # if same name and version connector exists in workspace
            # updating the installed status to False for same after uninstall of connector
            dev_instance = Connector.objects.filter(name=instance.name,
                                                    version=instance.version + settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX,
                                                    development=True)

            instance.delete()

            if dev_instance.exists():
                data = {
                    "installed": False
                }
                try:
                    serializer = ConnectorDetailSerializer(dev_instance.first(), data=data, partial=True)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                except Exception as e:
                    logger.warn('Error occurred while updating install status of dev connector Error:: %s'%str(e))

            metadata = instance.metadata
            if metadata.get('rpm_installed', False) and not is_rpm_command:
                delete_thread = Thread(target=remove_connector_rpm, args=[instance.name, instance.version])
                delete_thread.start()

            # publish as a cluster command:
            if not settings.LW_AGENT:
                try:
                    if cluster_command and not settings.LW_AGENT:
                        add_command_response = make_request('/api/auth/clustercommand/', 'POST',
                                                            {'commandId': 'connector-remove',
                                                             'command': cluster_command})
                        logger.info('result for publish of connector command: %s' % add_command_response)
                    elif not propagated and not is_rpm_command:
                        path = get_connector_path(instance.name, instance.version)
                        sync_ha_nodes(path, 'delete')
                except Exception as e:
                    raise ConnectorError('Failed to publish connector delete to cluster')

            broadcast_data['_status'] = True
            broadcast_data['status'] = {'status': REMOTE_STATUS.get('finished'),
                                        'message': 'connector delete successful'}
            broadcast_message(broadcast_data, uninstall_connector_ack, 'receiveRemoteConnectorInstructionRequest',
                              'GET', agent_obj)


            response_data = {'status': status.HTTP_204_NO_CONTENT}
            audit_status = 'success'
        except Exception as e:
            error_message = 'Error while deleting connector {0}v{1} ERROR:: {2}'.format(str(e))
            logger.exception(error_message)
            broadcast_data['_status'] = False
            broadcast_data['status'] = {'status': 'failure',
                                        'message': 'connector delete failed'}
            broadcast_message(broadcast_data, uninstall_connector_ack, 'receiveRemoteConnectorInstructionRequest',
                              'GET', agent_obj)
            response_data = {'data':{'message': error_message},'status': status.HTTP_400_BAD_REQUEST}
            audit_status = 'failed'

        # ======== Auditing ========
        try:
            audit_data = {
                'name': instance.name,
                'version': instance.version,
                'agent':instance.agent.agent_id
            }
            audit_data.update(response_data)
            audit_message_action = 'Uninstall Failed 'if audit_status == 'failed' else 'Uninstalled'
            audit_operation = 'uninstall_failed' if audit_status == 'failed' else 'uninstall_complete'
            audit_message = 'Connector [{0}] Version [{1}] {2}'.format(instance.name, instance.version, audit_message_action)
            audit_connector_functions(audit_data, audit_operation, audit_status, 'Connector', audit_message, rbac_info)
        except Exception as e:
            logger.exception(
                'Failed auditing configuration add operation for connector: {0}, version: {1}'.format(
                    instance.name,
                    instance.version))
        # ======== Auditing ========
        return Response(**response_data)

    def connector_install_ack(self, data, status):
        info = data.get('info', {})
        config = data.get('config', [])
        agent = data.get('agent')
        info['remote_status'] = status
        info['agent'] = agent

        # Connector is successful on remote
        if status.get('status') == REMOTE_STATUS.get('finished'):
            try:
                insert_connector(info, config=config, raise_exception=True)
            except Exception as e:
                error_message = 'Error occurred while updating the remote connector {0} of agent {1}'.format(
                    info.get('name'), agent)
                logger.error('{0} ERROR:: {1}'.format(error_message, str(e)))
        else:
            # Connector is failed on remote
            conn_instance = Connector.objects.filter(name=data.get('name', None),
                                                     version=data.get('version', None),
                                                     agent=data.get('agent', settings.SELF_ID)).first()

            if status.get('status') == REMOTE_STATUS.get('failed') and conn_instance.remote_status and \
                    conn_instance.remote_status.get('status') == REMOTE_STATUS.get('installation_in_progress'):
                status['status'] = REMOTE_STATUS.get('installation_failed')

            conn_instance.remote_status = status
            conn_instance.save()

        notify_message = 'Installed  connector {0} version {1} on agent {2}'.format(data.get('name'),
                                                                                    data.get('version'), agent)
        notify_data = {
            'data': data,
            'status': status,
            'message': notify_message,
            'agent_id': agent
        }
        publish_audit_and_notify(notify_data, 'Install', 'Connector', 'texchange.cyops.integration',
                                 'key.integration.notify', notify_message)

    def connector_uninstall_ack(self, data, status):
        name = data.get('name')
        version = data.get('version')
        agent = data.get('agent')
        connector_query = Connector.objects.filter(name=name, version=version, agent=agent)
        if connector_query.exists():
            try:
                if status.get('status') == REMOTE_STATUS.get('finished'):
                    connector_instance = connector_query.first()
                    connector_instance.metadata.update({'upgrade_in_progress': data.get('upgrade_in_progress')})
                    connector_instance.save(update_fields=['metadata'])
                    connector_query.delete()
                elif status.get('status') == REMOTE_STATUS.get('failed'):
                    conn_instance = connector_query.first()

                    if status.get('status') == REMOTE_STATUS.get('failed') and conn_instance.remote_status and \
                            conn_instance.remote_status.get('status') == REMOTE_STATUS.get(
                        'uninstall_in_progress'):
                        status['status'] = REMOTE_STATUS.get('uninstall_failed')

                    conn_instance.remote_status = status
                    conn_instance.save()
            except Exception as e:
                error_message = 'Error while deleting the connector {0} v{1} of  agent {2}'.format(name, version, agent)
                logger.error('{0} Error:: {1}'.format(error_message, str(e)))

            notify_message = 'Uninstalled  connector {0} version {1} on agent {2}'.format(name, version, agent)
            notify_data = {
                'data': data,
                'status': status,
                'message': notify_message,
                'agent_id': agent
            }
            publish_audit_and_notify(notify_data, 'Uninstall', 'Connector', 'texchange.cyops.integration',
                                     'key.integration.notify', notify_message)
        else:
            logger.warn(
                'Connector {0} version {1} on agent {2}  has already been uninstalled'.format(name, version, agent))

    def connector_update_ack(self, data, status):
        name = data.pop('name', None)
        version = data.pop('version', None)
        agent = data.pop('agent', None)
        connector_query = Connector.objects.filter(name=name, version=version, agent=agent)
        if connector_query.exists():
            try:
                connector_instance = connector_query.first()
                connector_instance.remote_status = status
                connector_instance.save()
            except Exception as e:
                error_message = 'Error while deleting the connector {0} v{1} on  agent {2}'.format(name, version, agent)
                logger.error('{0} Error:: {1}'.format(error_message, str(e)))

            notify_message = 'Updated  connector {0} version {1} on agent {2}'.format(name, version, agent)
            notify_data = {
                'data': data,
                'status': status,
                'message': notify_message,
                'agent_id': agent
            }
            publish_audit_and_notify(notify_data, 'Update', 'Connector', 'texchange.cyops.integration',
                                     'key.integration.notify', notify_message)
        else:
            logger.warn('Connector {0} version {1} on agent {2} has already been deleted'.format(name, version, agent))

    def connector_config_ack(self, data, status, method):
        config_id = data.get('config_id')
        agent = data.get('agent')
        name = data.get('name')
        version = data.get('version')
        config_instance = Configuration.objects.filter(config_id=config_id, agent=agent)
        try:
            if not config_instance.exists():
                logger.info('Connector configured at agent: {0}'.format(agent))
                data['remote_status'] = status
                data['status'] = 1 if data.get('remote_status', {}). \
                                          get('status') == REMOTE_STATUS.get('finished') else 0
                conn_obj = Connector.objects.filter(name=data.get('connector_name'),
                                                    version=data.get('connector_version'),
                                                    agent=agent).first()
                if conn_obj:
                    data['connector'] = conn_obj.pk
                else:
                    logger.error("Configuration received for connector {0} does not exist at master",
                                 data.get('connector_name'))
                    return
                configuration_serializer = ConnectorConfigurationSerializer(data=data)
            else:
                config_instance = config_instance.first()
                conn_obj = config_instance.connector
                config_data = {
                    'name': name,
                    'default': data.get('default', config_instance.default),
                    'remote_status': status
                }
                configuration_serializer = ConnectorConfigurationSerializer(config_instance, data=config_data, partial=True)


            if data.get('default', False):
                Configuration.objects.filter(
                    connector=conn_obj.id,
                    agent_id=agent,
                    default=True).update(default=False)

            configuration_serializer.is_valid(raise_exception=True)
            configuration_serializer.save()
            logger.info('Connector configuration saved')
            conn_obj.config_count = conn_obj.config_count + 1
            conn_obj.save()

            notify_message = 'Configuration connector {0} version {1} on agent {2}'.format(name, version, agent)
            notify_data = {
                'data': configuration_serializer.data,
                'status': status,
                'message': notify_message,
                'agent_id': agent
            }
            publish_audit_and_notify(notify_data, 'Create/Update', 'ConnectorConfiguration',
                                     'texchange.cyops.integration',
                                     'key.integration.notify', notify_message)
        except Exception as e:
            error_message = cs_integration_8.format(agent)
            logger.error('{0} ERROR:: {1}'.format(error_message, str(e)))

    def delete_connector_config_ack(self, data, status):
        config_id = data.get('config_id')
        config_instance = Configuration.objects.filter(config_id=config_id).first()
        agent = config_instance.agent
        if status.get('status') == REMOTE_STATUS.get('failed'):
            config_instance.remote_status = status
            config_instance.save()
        else:
            config_instance.connector.config_count = config_instance.connector.config_count - 1
            config_instance.connector.save()
            config_instance.delete()

        notify_message = 'Deleting Configuration connector configuration {0}'.format(config_id)
        notify_data = {
            'data': data,
            'status': status,
            'message': notify_message,
            'agent_id': agent.agent_id
        }
        publish_audit_and_notify(notify_data, 'DELETE', 'ConnectorConfiguration', 'texchange.cyops.integration',
                                 'key.integration.notify', notify_message)


class RemoteOperations():
    def create_connector_config(self, data, request=None):
        name = data.get('name', '')
        conn_name = data.get('connector_name')
        conn_version = data.get('connector_version')
        agent = data.get('agent')
        agent_obj = get_agent_obj(agent)
        teams = data.pop('teams', [])
        conn_instance = Connector.objects.filter(name=conn_name, version=conn_version, agent_id=agent).first()

        if not conn_instance:
            return Response({'message': 'Connector Does not exist'}, status=status.HTTP_404_NOT_FOUND)

        if conn_instance.remote_status.get('status') in ['in-progress', 'deletion-in-progress']:
            return Response({'message': 'Connector Installation in Progress, please try once ack recieved'},
                            status=status.HTTP_400_BAD_REQUEST)

        if conn_instance.remote_status.get('status') in ['failed']:
            return Response({'message': 'Connector installation failed on agent, please retry the installation'},
                            status=status.HTTP_400_BAD_REQUEST)

        config_id = data.get('config_id')
        config_instance = None
        remote_status = {
            'status': REMOTE_STATUS.get('in_progress'),
            'message': 'Configuration has been published to agent {0}'.format(agent)
        }
        if config_id:
            config_instance = Configuration.objects.filter(config_id=config_id).first()

        if config_instance and data.get('remote_status', {}).get('status') == REMOTE_STATUS.get('failed'):
            conn_config_obj = {
                'remote_status': remote_status
            }
        else:
            config = data.get('config')
            encrypt_password(conn_instance.config_schema, config)
            conn_config_obj = {
                'config_id': data.get('config_id', str(uuid.uuid4())),
                'name': name,
                'default': data.get('default', False),
                'config': config,
                'connector': conn_instance.id,
                'agent': agent,
                'remote_status': remote_status
            }
            if teams:
                team_ids = get_or_create_team_or_role('team', teams)
                conn_config_obj.update({'team_ids':team_ids})

        try:
            serializer = ConnectorConfigurationSerializer(config_instance, data=conn_config_obj)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            broadcast_data = serializer.data
            broadcast_data.update({'connector_name': conn_instance.name, 'connector_version': conn_instance.version})
            broadcast_message(broadcast_data, configure_connector, 'receiveRemoteConnectorInstructionRequest',
                                  'POST',
                                  agent_obj)
            audit_status = 'success'
            reponse_data = serializer.data
        except Exception as e:
            message = 'connector configuration failed: {0}'.format(str(e))
            audit_status = 'failed'
            reponse_data = {'message': message}

        try:
            audit_message = 'Configuration connector [{0}] version [{1}] on agent [{2}]'.format(conn_name, conn_version,
                                                                                                agent_obj.name if agent_obj else agent)
            audit_data = {
                'data': data,
                'status': audit_status
            }
            publish_audit_and_notify(audit_data, CONFIGURATION_AUDIT_OPERATIONS.get('create'), 'Connectors',
                                     'texchange.cyops.agent',
                                     'key.agent.audit',
                                     audit_message, request=request)
        except Exception as e:
            logger.exception(
                'Failed auditing configuration add operation for connector: {0}, version: {1}, agent: {2}'.format(
                    conn_name,
                    conn_version, agent))

        return Response(reponse_data,
                        status=status.HTTP_200_OK if audit_status == 'success' else status.HTTP_400_BAD_REQUEST)

    def update_connector_config(self, instance, data, partial=False, request=None):
        agent_obj = instance.agent
        teams = data.pop('teams', None)
        link_teams = data.pop('__link', {}).get('teams', [])
        unlink_teams = data.pop('__unlink', {}).get('teams', [])
        team_ids = []
        data.update({'remote_status': {'status': REMOTE_STATUS.get('in_progress')}})
        conn_instance = instance.connector
        encrypt_password(conn_instance.config_schema, data.get('config'))

        if teams is not None:
            instance.teams.clear()
            team_ids = get_or_create_team_or_role('team', teams)
        if unlink_teams or link_teams:
            if link_teams:
                link_teams = get_or_create_team_or_role('team', link_teams)
            if teams is None:
                team_id_query = instance.teams.all().values('uuid')
                for team_id in team_id_query:
                    team_ids.append(team_id.get('uuid'))
            team_ids = get_update_list(team_ids, link_teams, unlink_teams)
        if team_ids:
            data.update({'team_ids': team_ids})

        serializer = ConnectorConfigurationSerializer(instance, data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        broadcast_data = serializer.data
        broadcast_data.update({'connector_name': conn_instance.name, 'connector_version': conn_instance.version})
        broadcast_message(broadcast_data, configuration_update, 'receiveRemoteConnectorInstructionRequest', 'PUT',
                          agent_obj)

        audit_message = 'Updating Configuration of connector [{0}] version [{1}] on agent [{2}]'.format(
            conn_instance.name, conn_instance.version, agent_obj.name)
        audit_data = {
            'data': data,
            'status': 'Success'
        }
        publish_audit_and_notify(audit_data, CONFIGURATION_AUDIT_OPERATIONS.get('update'), 'Connectors',
                                 'texchange.cyops.agent',
                                 'key.agent.audit',
                                 audit_message, request=request)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete_connector_config(self, instance, request=None):
        agent_obj = instance.agent
        instance.remote_status = {'status': REMOTE_STATUS.get('deletion_in_progress')}
        instance.save()
        conn_instance = instance.connector
        broadcast_data = {'config_id': instance.config_id,
                          'connector_name': conn_instance.name,
                          'connector_version': conn_instance.version}
        broadcast_message(broadcast_data, configuration_removed, 'receiveRemoteConnectorInstructionRequest', 'DELETE',
                          agent_obj)

        audit_message = 'Deleting Configuration of connector [{0}] version [{1}] on agent [{2}]'.format(
            conn_instance.name, conn_instance.version, agent_obj.name)
        audit_data = {
            'data': broadcast_data,
            'status': 'Success'
        }
        publish_audit_and_notify(audit_data, CONFIGURATION_AUDIT_OPERATIONS.get('delete'), 'Connectors',
                                 'texchange.cyops.agent',
                                 'key.agent.audit',
                                 audit_message, request=request)

        serializer = ConnectorConfigurationSerializer(instance)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def connector_install(self, data, request=None):

        name = data.get('name')
        version = data.get('version')
        agent = data.get('agent', settings.SELF_ID)
        audit_action = data.get('_action', 'install')
        agent_obj = get_agent_obj(agent)
        conn_data = {
            'name': name,
            'rpm_name': data.get('rpm_name', ''),
            'rpm_full_name': data.get('rpm_full_name', None),
            'version': version,
            'agent': agent,
            'label': data.get('name'),
            'status': 'in-progress',
            'remote_status': {'status': REMOTE_STATUS.get('installation_in_progress')},
        }

        conn_instance = Connector.objects.filter(name=name, version=version, agent=agent).first()
        if conn_instance and conn_instance.remote_status.get('status') in ['in-progress', 'deletion-in-progress']:
            return Response({'message': 'Connector you are trying to install is already in progress'},
                            status=status.HTTP_200_OK)

        elif conn_instance and conn_instance.remote_status.get('status') == 'finished':
            message = 'Connector you are trying to install is already installed Connector :: {0} v{1}'.format(
                name, version)
            return Response({'message': message})

        serializer = ConnectorDetailSerializer(conn_instance, data=conn_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        conn_data = serializer.data
        conn_data.update({'rpm_name': data.get('rpm_name'), 'rpm_full_name': data.get('rpm_full_name')})
        broadcast_message(conn_data, install_connector, 'receiveRemoteConnectorInstructionRequest', 'POST',
                          agent_obj)

        audit_operation = 'Updating' if audit_action == 'upgrade' else 'Installing'
        audit_message = '{0} connector [{1}] version [{2}] on agent [{3}]'.format(audit_operation, name, version,
                                                                                  agent_obj.name)
        audit_data = {
            'data': conn_data,
            'status': 'Success'
        }
        publish_audit_and_notify(audit_data, CONNECTOR_AUDIT_OPERATIONS.get(audit_action), 'Connectors',
                                 'texchange.cyops.agent', 'key.agent.audit',
                                 audit_message, request=request)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def connector_detail_update(self, data, instance, request, partial=False):

        if instance.remote_status.get('status') != REMOTE_STATUS.get('finished'):
            return Response({'message': 'Connector Installation Failed or Ack not received'},
                            status=status.HTTP_400_BAD_REQUEST)
        agent_obj = instance.agent
        serializer = ConnectorDetailSerializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data.update({
            'connector_name': instance.name,
            'connector_version': instance.version,
            'agent_id': instance.agent.agent_id,
        })
        data.pop('rbac_info', None)
        broadcast_message(data, update_connector, 'receiveRemoteConnectorInstructionRequest', 'PUT', agent_obj)

        audit_message = 'Updating connector [{0}] version [{1}] on agent [{2}]'.format(instance.name, instance.version,
                                                                                       agent_obj.name)
        audit_data = {
            'data': data,
            'status': 'Success'
        }
        publish_audit_and_notify(audit_data, CONNECTOR_AUDIT_OPERATIONS.get("update"), 'Connectors',
                                 'texchange.cyops.agent', 'key.agent.audit',
                                 audit_message, request=request)

        return Response(status=status.HTTP_200_OK)

    def connector_detail_delete(self, instance, remove_rpm, *args, **kwargs):
        request = kwargs.get('request')
        agent_obj = instance.agent
        data = {
            'connector_name': instance.name,
            'connector_version': instance.version,
            'agent_id': instance.agent.agent_id,
            'remove_rpm': remove_rpm
        }

        broadcast_message(data, uninstall_connector, 'receiveRemoteConnectorInstructionRequest', 'DELETE',
                          agent_obj)

        instance.remote_status = {'status': REMOTE_STATUS.get('uninstall_in_progress')}
        instance.save()

        audit_message = 'Uninstalling  connector [{0}] version [{1}] on agent [{2}]'.format(instance.name,
                                                                                            instance.version,
                                                                                            agent_obj.name)
        audit_data = {
            'data': data,
            'status': 'Success'
        }
        publish_audit_and_notify(audit_data, CONNECTOR_AUDIT_OPERATIONS.get('delete'), 'Connectors',
                                 'texchange.cyops.agent', 'key.agent.audit',
                                 audit_message, request=request)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def connector_health_check(self, config_id, name, version, request=None, agent=None):
        if not agent: agent = settings.SELF_ID
        agent_instance = get_agent_obj(agent)
        conn_instance = Connector.objects.filter(name=name, version=version, agent=agent).first()
        heath_check = {
            'connector': conn_instance.id,
            'configuration': config_id,
            'agent': agent,
            'remote_status': {'status': 'in-progress'},
            'action': health_check
        }
        execute_action_instance = ExecuteAction.objects.filter(
            configuration=config_id, action=health_check) \
            .exclude(remote_status__status=REMOTE_STATUS.get('in_progress')).order_by('-id').first()

        serializer = ExecuteActionSerializer(data=heath_check)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        broadcast_data = serializer.data
        broadcast_data.update({'connector_name': conn_instance.name, 'connector_version': conn_instance.version,
                               'request_id': broadcast_data.get('id')})
        broadcast_message(broadcast_data, health_check, 'receiveRemoteConnectorExecutionRequest', 'GET',
                          agent_instance)
        response_data = serializer.data
        if execute_action_instance:
            response_data.update({
                'last_known_health_status': execute_action_instance.result,
                'last_known_health_status_time': execute_action_instance.modified
            })
        return Response(response_data, status=status.HTTP_200_OK)

    def agent_health_check(self, data):
        agent_id = data.get('agent', settings.SELF_ID)
        agent_instance = Agent.objects.filter(agent_id=agent_id).first()
        heath_check = {
            'agent': agent_id,
            'remote_status': {'status': 'in-progress'},
            'action': health_check
        }

        serializer = ExecuteActionSerializer(data=heath_check)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        broadcast_data = serializer.data
        broadcast_data.update({'agent': agent_id,
                               'request_id': broadcast_data.get('id')})
        broadcast_message(broadcast_data, agent_health_check, 'receiveRemoteConnectorExecutionRequest', 'GET',
                          agent_instance)
        return serializer.data

    def execute_connector_action(self, config_id, input_data, agent, request=None):
        agent_instance = get_agent_obj(agent)
        name = input_data.get('connector')
        version = input_data.get('version')
        conn_instance = Connector.objects.get(name=name, version=version, agent=agent)

        action_data = {
            'connector': conn_instance.id,
            'configuration': config_id,
            'agent': agent,
            'remote_status': 'in-progress',
            'action': execute_action,
            'request_payload': input_data
        }
        serializer = ExecuteActionSerializer(data=action_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        broadcast_data = serializer.data
        broadcast_data.update({'connector_name': conn_instance.name, 'connector_version': conn_instance.version,
                               'request_id': broadcast_data.get('id')})
        broadcast_message(broadcast_data, execute_action, 'receiveRemoteConnectorExecutionRequest', 'GET',
                          agent_instance)

        if input_data.get('audit', False):
            audit_message = 'Executing action [{0}] of connector [{1}] version [{2}] on agent [{3}]'.format(
                input_data.get('operation'),
                conn_instance.name,
                conn_instance.version,
                agent_instance.name)
            audit_data = {
                'data': serializer.data,
                'status': 'Success'
            }
            publish_audit_and_notify(audit_data, CONNECTOR_AUDIT_OPERATIONS.get('execute'), 'Connectors',
                                     'texchange.cyops.agent',
                                     'key.agent.audit',
                                     audit_message, request=request)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def agent_upgrade(self, agent_id, b_upgrade_file, hkey):
        agent_instance = Agent.objects.filter(agent_id=agent_id).first()
        action_data = {
            'agent': agent_id,
            'remote_status': 'in-progress',
            'action': agent_upgrade_request,
        }
        serializer = ExecuteActionSerializer(data=action_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        broadcast_data = serializer.data
        broadcast_data.update({
            'request_id': broadcast_data.get('id'),
            'upgrade_file_content': b_upgrade_file,
            'hkey': hkey,
            'action': agent_upgrade_request,
            'master_version': settings.RELEASE_VERSION,
            'name': agent_instance.name
        })
        broadcast_message(broadcast_data, agent_upgrade_request, 'receiveRemoteInstanceUpgradeRequest', None,
                          agent_instance)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def agent_log_collect(self, agent_instance):
        action_data = {
            'agent': agent_instance.agent_id,
            'remote_status': 'in-progress',
            'action': collect_app_log,
        }
        serializer = ExecuteActionSerializer(data=action_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        broadcast_data = serializer.data
        broadcast_data.update({
            'request_id': broadcast_data.get('id'),
            'action': collect_app_log,
        })
        broadcast_message(broadcast_data, collect_app_log, 'receiveRemoteInstanceUpgradeRequest', None,
                          agent_instance)

        return Response(serializer.data, status=status.HTTP_200_OK)


def get_configuration_obj(pk):
    try:
        if pk.isdigit():
            obj = Configuration.objects.filter(pk=pk).first()
        else:
            obj = Configuration.objects.filter(config_id=pk).first()
        return obj
    except Configuration.DoesNotExist:
        raise Http404('No matching config by id %s exists.' % pk)


def get_agent_obj(agent_id):
    return Agent.objects.filter(agent_id=agent_id).first()


def get_remove_rpm(remove_rpm, rpm_name):
    if remove_rpm:
        try:
            output = subprocess.check_output(['rpm', '-qia', '|', 'grep', str(rpm_name)])
            if rpm_name not in str(output):
                remove_rpm = False
        except subprocess.CalledProcessError:
            remove_rpm = False
    return remove_rpm


def remove_connector_rpm(connector_name, connector_version):
    rpm_name = 'cyops-connector-' + connector_name + '-' + connector_version
    try:
        cmd = ['sudo', 'csadm', 'package', 'remove', '--type', 'connector', '--name', str(rpm_name),
               '--no-interaction']
        remove_process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        output, err = remove_process.communicate()
        if err:
            raise Exception(err)
        elif output:
            logger.info(
                'Connector {0} v{1} rpm removed successfully OUTPUT :: {2}'.format(connector_name, connector_version,
                                                                                   output))
    except Exception as err:
        logger.error('Error while removing the connector rpm Error :: {0}'.format(str(err)))


def identify_executable_class(agent_obj):
    if not agent_obj or agent_obj.is_local:
        return SelfOperations()
    else:
        if agent_obj and agent_obj.allow_remote_operation:
            return RemoteOperations()
        else:
            return AllowRemoteOperation()


def brodacast_connector_operation_message(conn_id, command, status, name=None, version=None, agent_id=None,
                                          message=None):
    conn_object = Connector.objects.filter(id=conn_id).first()
    if conn_object:
        name = conn_object.name
        version = conn_object.version
        agent_id = conn_object.agent.agent_id
    else:
        return
    broadcast_data = {
        'name': name,
        'version': version,
        'status': {
            'status': REMOTE_STATUS.get('finished') if status == 'Success' else REMOTE_STATUS.get('failed'),
            'message': message if message else conn_object.install_result.get('message')
        },
        'command': command,
        'agent': agent_id,
    }
    ack_action = install_connector_ack if command == 'install' else uninstall_connector_ack

    if command == 'install' and status == 'Success':
        connector_path = get_connector_path(conn_object.name, conn_object.version)
        info_path = os.path.join(connector_path, 'info.json')
        with open(info_path) as jFile:
            info_content = json.load(jFile)
        if Configuration.objects.filter(connector=conn_object.id).exists():
            config_instance = Configuration.objects.filter(connector=conn_object.id)
            config_serializer = ConnectorConfigurationSerializer(config_instance, many=True)
            broadcast_data.update({'config': config_serializer.data})
        broadcast_data.update({'info': info_content})

    broadcast_message(broadcast_data, ack_action, 'receiveRemoteConnectorInstructionRequest', 'POST',
                      conn_object.agent)


class AllowRemoteOperation():
    def __getattr__(self, name):
        def forbid_remote_op(*args):
            return Response({'message': cs_integration_16}, status=status.HTTP_403_FORBIDDEN)

        return forbid_remote_op
