import json
import os
import logging
from django.conf import settings
from django.http import HttpResponse
from rest_framework import pagination
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.response import Response
from connector_development.utils import get_connector_development_path, folder_content, create_folder, \
    create_file, update_file, get_file_content, folder_tree, generate_connector_files, remove_folder, \
    create_tar, remove_file, update_modified_date, update_info_file, validate_development_info, check_file_traversal
from connectors.utils import get_connector_path, insert_connector, sync_ha_nodes, sync_ha_nodes_new
from connectors.views import import_connector
from connectors.models import Connector
from connectors.helper import SelfOperations
from connectors.core.base_connector import ConnectorError
from connectors.core.constants import *
from connectors.serializers import ConnectorDetailSerializer
from audit.audit import audit_connector_functions

logger = logging.getLogger('connectors')


class ConnectorDevelopment(ModelViewSet):
    queryset = Connector.objects.filter(development=True)
    serializer_class = ConnectorDetailSerializer
    filter_backends = (filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend,)
    search_fields = ('$id', '$label', '$name')
    filter_fields = ('label', 'name')

    def _create_connector(self, info, agent=None, rbac_info={}, *args, **kwargs):
        if not agent: agent = settings.SELF_ID
        name = info.get('name')
        version = info.get('version')
        if not settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX in version:
            version = version + settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX
        forked_from = info.get('forked_from', '')
        template = info.pop('template', '')
        development = info.pop('development', True)
        path = get_connector_development_path(name, version)

        if forked_from:
            if settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX in forked_from:
                audit_action = 'add_version'
            else:
                audit_action = 'clone'
        else:
            audit_action = 'create'
        audit_message = 'Connector [{0}] Version [{1}] Created'.format(name, version)

        try:
            # Check if connector name is reserved
            validate_development_info(info)

            if Connector.objects.filter(name=name, version=version, development=True, agent=agent).count():
                return Response(
                    {
                        "message": "Connector with name {0} version {1} already exists in connector workspace.".format(
                            name, info.get("version"))
                    },
                    status=status.HTTP_409_CONFLICT
                )
            connector_files, info = generate_connector_files(path, info, forked_from, template, development)
            info.update({
                'version': version,
                'development': True,
                'installed': False
            })
            result = insert_connector(info)
            connector_files.update(result)
            audit_connector_functions(result, audit_action, 'success', 'Connector', audit_message, rbac_info)
            sync_data = {
                'source' : {
                    'paths' : [path]
                }
            }
            sync_ha_nodes_new(sync_data, 'copy')
            return Response(connector_files, content_type="application/json")
        except ConnectorError as e:
            error_message = str(e)
            logger.exception(error_message)
            remove_folder(path)
        except Exception as e:
            error_message = "Error occurred while create the connector"
            logger.error("{0} ERROR: {1}".format(error_message, str(e)))
            remove_folder(path)

        audit_message = 'Connector [{0}] Version [{1}] Creation Failed'.format(name, version)
        audit_connector_functions({'message': error_message}, audit_action, 'failed', 'Connector', audit_message, rbac_info)
        return Response({'message': error_message}, status=status.HTTP_400_BAD_REQUEST)


    def create_connector(self, request, *args, **kwargs):
        info = request.data.get("info")
        rbac_info = request.data.get('rbac_info', {})
        return self._create_connector(info, request.data.get("agent", settings.SELF_ID), rbac_info= rbac_info, *args, **kwargs)

    def connector_details(self, request, *args, **kwargs):
        connector_id = kwargs.get("id")
        try:
            connector_instance = Connector.objects.get(id=connector_id)

            #get of non development connector
            if not connector_instance.development:
                connector_name = connector_instance.name
                connector_version = connector_instance.version
                if not settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX in connector_version:
                    connector_version = connector_version + settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX
                connector_instance_dev_query = Connector.objects.filter(name=connector_name, version=connector_version, development=True)
                if not connector_instance_dev_query.exists():
                    logger.info('Didn\'t found connector in workspace creating a clone')
                    serializer = ConnectorDetailSerializer(connector_instance)
                    create_data = serializer.data
                    forked_from = create_data.get('name') + '_' + create_data.get('version').replace('.', '_')
                    configuration = create_data.pop('config_schema', create_data.get('configuration'))
                    create_data.update({'forked_from': forked_from, 'configuration': configuration})
                    create_response = self._create_connector(create_data, *args, **kwargs)
                    return  create_response
                else:
                    connector_instance =  connector_instance_dev_query.first()

            serializer = ConnectorDetailSerializer(connector_instance)
            connector_data = serializer.data
            name = connector_data.get("name")
            version = connector_data.get("version")

            connector_path = get_connector_development_path(name, version) if connector_data.get('development') else get_connector_path(name, version)

            connector_data.update({
                "tree" : folder_tree(connector_path)
            })
            return Response(connector_data, status=status.HTTP_200_OK)
        except Exception as err:
            error_message = 'Error occurred while retrieving development connector details.'
            logger.exception('{0} Error :: {1}'.format(error_message, str(err)))
            return Response({"message":error_message}, status=status.HTTP_400_BAD_REQUEST)

    def connector_details_view(self, request, *args, **kwargs):
        connector_id = kwargs.get("id")
        try:
            connector_instance = Connector.objects.get(id=connector_id)
            serializer = ConnectorDetailSerializer(connector_instance)
            connector_data = serializer.data
            name = connector_data.get("name")
            version = connector_data.get("version")

            connector_path = get_connector_development_path(name, version) if connector_data.get(
                'development') else get_connector_path(name, version)

            connector_data.update({
                "tree": folder_tree(connector_path)
            })
            return Response(connector_data, status=status.HTTP_200_OK)
        except Exception as err:
            error_message = 'Error occurred while retrieving connector details.'
            logger.exception('{0} Error :: {1}'.format(error_message, str(err)))
            return Response({"message": error_message}, status=status.HTTP_400_BAD_REQUEST)

    def create_connector_files(self, request, *args, **kwargs):
        connector_id = kwargs.get("id")
        data = request.data
        file_data = data.get('fileData', [])
        updated_file_paths = []
        info_json_updated = False
        try:
            if not file_data:
                raise ConnectorError("Invalid input filepath and filecontent missing")
            if not isinstance(file_data, list):
                file_data = [file_data]
            connector_dev_instance = Connector.objects.get(id=connector_id)
            connector_name = connector_dev_instance.name
            connector_version = connector_dev_instance.version
            connector_path = get_connector_development_path(connector_name, connector_version)
            for file in file_data:
                file_name = file.get('xpath')
                file_content = file.get('fileContent')
                if file_name:
                    file_path = os.path.join(settings.CONNECTOR_DEVELOPMENT_DIR, *file_name.split('/'))
                    if "info.json" in file_name:
                        update_info_file(file_path, file_content, connector_dev_instance)
                        info_json_updated = True
                    else:
                        if isinstance(file_content, dict):
                            file_content = json.dumps(file_content)
                        if os.path.exists(file_path):
                            update_file(file_path, file_content)
                        else:
                            create_file(file_path, file_content)
                    updated_file_paths.append(file_path)
                else:
                    logger.warn("Invalid inputs for file name {0}".format(file_name))
            if not info_json_updated:
                update_modified_date(connector_dev_instance)
            sync_data = {
                'source': {
                    'paths': updated_file_paths
                }
            }
            sync_ha_nodes_new(sync_data, 'copy')
            return Response({"tree": folder_tree(connector_path), "status": "Success"}, status=status.HTTP_200_OK)
        except ConnectorError as e:
            logger.exception(str(e))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_message = "Error occurred while creating the files of connector"
            logger.exception("{0} ERROR: {1}".format(error_message, str(e)))
            return Response({'message': error_message}, status=status.HTTP_400_BAD_REQUEST)

    def delete_connector_files(self, request, *args, **kwargs):
        connector_id = kwargs.get('id')
        data = request.data
        file_data = data.get('fileData', [])
        if not isinstance(file_data, list):
            file_data = [file_data]
        try:
            connector_instance = Connector.objects.get(id=connector_id)
            connector_path = get_connector_development_path(connector_instance.name, connector_instance.version)
            deleted_file_paths = []
            for file in file_data:
                file_path = file.get('xpath', '')
                if file_path:
                    file_path = os.path.join(settings.CONNECTOR_DEVELOPMENT_DIR, *file_path.split('/'))
                    remove_file(file_path)
                    deleted_file_paths.append(file_path)
                else:
                    logger.warn("Invalid inputs for file path {0}".format(file_path))
            update_modified_date(connector_instance)
            sync_data = {
                'paths' : deleted_file_paths
            }
            sync_ha_nodes_new(sync_data, 'delete')
            return Response({"tree": folder_tree(connector_path), "status": "Success"}, status=status.HTTP_200_OK)
        except ConnectorError as e:
            logger.error(str(e))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_message = "Error occurred while deleting the files"
            logger.error("{0} ERROR: {1}".format(error_message, str(e)))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def rename_connector_files(self, request, *args, **kwargs):
        connector_id = kwargs.get('id')
        data = request.data
        file_data = data.get('fileData', {})
        old_file_path = file_data.get('oldFilePath', '')
        new_file_path = file_data.get('newFilePath', '')
        try:
            connector_instance = Connector.objects.get(id=connector_id)
            connector_path = get_connector_development_path(connector_instance.name, connector_instance.version)
            if old_file_path and new_file_path:
                new_file_path = os.path.join(settings.CONNECTOR_DEVELOPMENT_DIR, *new_file_path.split('/'))
                old_file_path = os.path.join(settings.CONNECTOR_DEVELOPMENT_DIR, *old_file_path.split('/'))
                check_file_traversal(new_file_path)
                check_file_traversal(old_file_path)
                os.rename(old_file_path, new_file_path)
            else:
                raise ConnectorError('Invalid input new or old file path not provided')
            update_modified_date(connector_instance)
            sync_data = {
                'source': old_file_path,
                'target': new_file_path
            }
            sync_ha_nodes_new(sync_data, 'rename')
            return Response({"tree": folder_tree(connector_path), "status": "Success"}, status=status.HTTP_200_OK)
        except ConnectorError as e:
            logger.error(str(e))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_message = "Error occurred while renaming the file {0}".format(old_file_path)
            logger.error("{0} ERROR: {1}".format(error_message, str(e)))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def create_connector_folder(self, request, *args, **kwargs):
        connector_id = kwargs.get('id')
        data = request.data
        folder_data = data.get('fileData', [])
        if not isinstance(folder_data, list):
            folder_data = [folder_data]
        try:
            connector_instance = Connector.objects.get(id=connector_id)
            connector_path = get_connector_development_path(connector_instance.name, connector_instance.version)
            created_folder_paths = []
            for folder in folder_data:
                folder_path = folder.get('xpath', '')
                folder_name = folder.get('folderName', '')
                if folder_name and folder_path:
                    folder_path = os.path.join(settings.CONNECTOR_DEVELOPMENT_DIR, *folder_path.split('/'))
                    create_folder(folder_path)
                    created_folder_paths.append(folder_path)
                else:
                    logger.warn("Invalid inputs for folder name {0} or folder path {1}".format(folder_name, folder_path))
            update_modified_date(connector_instance)
            sync_data = {
                'source': {
                    'paths' : created_folder_paths
                }
            }
            sync_ha_nodes_new(sync_data, 'copy')
            return Response({"tree": folder_tree(connector_path), "status": "Success"}, status=status.HTTP_200_OK)
        except ConnectorError as e:
            logger.error(str(e))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_message = "Error occurred while creating the folders"
            logger.error("{0} ERROR: {1}".format(error_message, str(e)))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete_connector_folder(self, request, *args, **kwargs):
        connector_id = kwargs.get('id')
        data = request.data
        folder_data = data.get('fileData', [])
        if not isinstance(folder_data, list):
            folder_data = [folder_data]
        try:
            connector_instance = Connector.objects.get(id=connector_id)
            connector_path = get_connector_development_path(connector_instance.name, connector_instance.version)
            deleted_folder_paths = []
            for folder in folder_data:
                folder_path = folder.get('xpath', '')
                if folder_path:
                    folder_path = os.path.join(settings.CONNECTOR_DEVELOPMENT_DIR, *folder_path.split('/'))
                    remove_folder(folder_path)
                    deleted_folder_paths.append(folder_path)
                else:
                    logger.warn("Invalid inputs for folder path {0}".format(folder_path))
            update_modified_date(connector_instance)
            sync_data = {
                'paths' : deleted_folder_paths
            }
            sync_ha_nodes_new(sync_data, 'delete')
            return Response({"tree": folder_tree(connector_path), "status": "Success"}, status=status.HTTP_200_OK)
        except ConnectorError as e:
            logger.error(str(e))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_message = "Error occurred while deleting the folders"
            logger.error("{0} ERROR: {1}".format(error_message, str(e)))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve_connector_files(self, request, *args, **kwargs):
        self.id = kwargs.get("id")
        file_data = request.data
        try:
            connector_instance = Connector.objects.get(id=self.id)
            serializer = ConnectorDetailSerializer(connector_instance)
            connector_data = serializer.data
            name = connector_data.get("name")
            version = connector_data.get("version")

            if connector_data.get('development'):
                connector_path = get_connector_development_path(name, version)
                connector_dir = settings.CONNECTOR_DEVELOPMENT_DIR
            else:
                connector_path = get_connector_path(name, version)
                connector_dir = settings.CONNECTORS_DIR

            if file_data.get("xpath"):
                abs_file_path = os.path.join(connector_dir, *file_data.get("xpath").split('/'))
                return Response({"fileContent": get_file_content(abs_file_path)})
            else:
                all_files_content = folder_content(connector_path)
                return Response(all_files_content)
        except ConnectorError as e:
            logger.error(str(e))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_message = "Error occurred while retrieving content of file {0}.".format(file_data.get("xpath"))
            logger.error("{0} ERROR: {1}".format(error_message, str(e)))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def publish(self, request, *args, **kwargs):
        connector_id = kwargs.get("id")
        discard = request.data.get("discard", False)
        replace = request.data.get("replace", False)
        rbac_info = request.data.get("rbac_info", {})
        try:
            connector_dev_instance = Connector.objects.get(id=connector_id)
            connector_name = connector_dev_instance.name
            connector_version = connector_dev_instance.version
            connector_dev_path = get_connector_development_path(connector_name, connector_version)

            tar_file_path = create_tar(connector_dev_path, connector_name)
            result = import_connector(tar_file_path, replace=replace, rbac_info=rbac_info, audit_operation='publish')
            data = {
                "installed":True
            }
            serializer = ConnectorDetailSerializer(connector_dev_instance, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            remove_file(tar_file_path)
            if discard:
                self_operation_obj= SelfOperations()
                self_operation_obj.connector_detail_delete(connector_dev_instance, remove_rpm=False, request={'rbac_info': rbac_info})

            return Response(result, status=status.HTTP_200_OK)
        except Connector.DoesNotExist:
            error_message = 'No matching connector by id {0} exists.'.format(connector_id)
            return Response({'message': error_message}, status=status.HTTP_400_BAD_REQUEST)
        except ConnectorError as e:
            error_message =  str(e)
        except Exception as e:
            error_message = 'Error occurred while publishing connector. ERROR :: {0}'.format(str(e))
            logger.exception(error_message)

        # ======== Auditing ========
        try:
            audit_message = 'Connector [{0}] Version [{1}] Publish Failed'.format(connector_dev_instance.name, connector_dev_instance.version)
            audit_connector_functions({'connector_id':connector_id}, 'publish', 'failed', 'Connector', audit_message, rbac_info)
        except Exception as e:
            logger.exception('Failed auditing connector publish for connector Error:: {0}'.format(str(e)))
        # ======== Auditing ========
        return Response({'message':error_message}, status=status.HTTP_400_BAD_REQUEST)

    def export(self, request, *args, **kwargs):
        connector_id = kwargs.get("id")
        try:
            connector_dev_instance = Connector.objects.get(id=connector_id)
            connector_name = connector_dev_instance.name
            connector_version = connector_dev_instance.version
            connector_dev_path = get_connector_path(connector_name, connector_version)
            tar_file_path = create_tar(connector_dev_path, connector_name)
            zip_file = open(tar_file_path, 'rb')
            response = HttpResponse(zip_file, content_type='application/gzip')
            filename = connector_name + 'tgz'
            response['Content-Disposition'] = 'attachment; filename="%s"' %filename
            remove_file(tar_file_path)
            return response
        except Connector.DoesNotExist:
            return Response({'message': 'No matching connector by id {0} exists.'.format(self.id)}, status=status.HTTP_400_BAD_REQUEST)
        except ConnectorError as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ConnectorTemplates(APIView): 
    def post(self, request):
        template = request.data.get("template")
        try:
            if template:
                file_path = os.path.join(settings.CONNECTOR_TEMPLATE_DIR, template.get("folder"), "info.json")
                f = open(file_path)
                result = json.load(f)
            else:
                result = settings.CONNECTOR_TEMPLATES

            return Response(result,status=status.HTTP_200_OK)
        except Exception as err:
            error_message = "Error occurred while retrieving connector templates"
            logger.error('{0} ERROR:: {1}'.format(error_message, str(err)))
            return Response({"message": str(err)}, status=status.HTTP_400_BAD_REQUEST)