import os
import glob
import re
import tarfile
import json
import logging
import shutil
import base64
from django.conf import settings
from datetime import datetime
from connectors.core.base_connector import ConnectorError, STATE_AVAILABLE
from connectors.models import Connector
from connectors.serializers import ConnectorDetailSerializer
from connectors.utils import insert_connector, validate_connector_operation_input
from connectors.core.constants import *
from connectors.utils import sync_ha_nodes_new

logger = logging.getLogger('connectors')


def get_connector_development_path(name, version):
    version = '%s' % (version.replace('.', '_'))
    return os.path.join(settings.CONNECTOR_DEVELOPMENT_DIR, ('%s_%s' % (name, version)))


def generate_connector_files(dest_path, info, forked_from, template=None, development=False):
    name = info.get('name', '')
    version = info.get('version', '')
    label = info.get('label', '')
    if info.get('operations') is None:
        info['operations'] = []
    try:
        if forked_from:
            ignore_file_list = ['__pycache__', 'info.json']
            # Create info.json file
            if development:
                connector_root_dir = settings.CONNECTOR_DEVELOPMENT_DIR
            else:
                connector_root_dir = settings.CONNECTORS_DIR
            connector_file_path = os.path.join(connector_root_dir, forked_from)
            copy_info = json.loads(get_file_content(os.path.join(connector_file_path, 'info.json')))
            info = create_image_file(dest_path, info, create_image=False)
            info.update(copy_info)
            info.update({
                "name": name,
                "version": version,
                "label": label
            })
            if 'fortinet' in info.get('publisher', '').lower() or 'cybersponse' in info.get('publisher', '').lower():
                info['publisher'] = ''
                info['cs_approved'] = False
            info = update_info_file_sequence(info)
            shutil.copytree(connector_file_path, dest_path, ignore=shutil.ignore_patterns(*ignore_file_list))
            create_file(os.path.join(dest_path, 'info.json'), json.dumps(info, indent=4))

        elif template:
            ignore_file_list = ['__pycache__', 'info.json']
            connector_root_dir = settings.CONNECTOR_TEMPLATE_DIR
            template_connector_path = os.path.join(connector_root_dir, template)
            if 'fortinet' in info.get('publisher', '').lower() or 'cybersponse' in info.get('publisher', '').lower():
                info['publisher'] = ''
                info['cs_approved'] = False
            shutil.copytree(template_connector_path, dest_path, ignore=shutil.ignore_patterns(*ignore_file_list))
            info = create_image_file(dest_path, info)
            info = update_info_file_sequence(info)
            create_file(os.path.join(dest_path, 'info.json'), json.dumps(info, indent=4))
            # Create py file for each operations
            update_operation_files(info.get('operations'), name, connector_path=dest_path, generate_operation_files=True)

        else:
            #Copy other files like playbook.json requeriments.txt
            ignore_file_list = ['__pycache__', 'info.json', 'connector.py', 'builtin.py', 'operations.py']
            shutil.copytree(os.path.join(settings.CONNECTOR_TEMPLATE_DIR, 'generic_template'), dest_path, ignore=shutil.ignore_patterns(*ignore_file_list))
            # Create info.json file
            create_folder(dest_path)
            info = create_image_file(dest_path, info)
            info = update_info_file_sequence(info)
            create_file(os.path.join(dest_path, 'info.json'), json.dumps(info, indent=4))
            # Create connector.py file
            connector_file_content = get_file_content(
                os.path.join(settings.CONNECTOR_TEMPLATE_DIR, *['generic_template', 'connector.py'])
            )
            connector_file_content = re.sub(r'Sample', name.capitalize().replace('-', '_'), connector_file_content)
            create_file(os.path.join(dest_path, "connector.py"), connector_file_content)
            # Create constants.py file
            create_constant_file(dest_path, name)
            # Create py file for each operations
            update_operation_files(info.get('operations'), name, connector_path=dest_path, generate_operation_files=True)


        return {"tree": folder_tree(dest_path)}, info
    except ConnectorError as e:
        raise ConnectorError(e)
    except Exception as err:
        error_message = 'Error occurred while generating and creating connector files'
        raise ConnectorError('{0}. ERROR :: {1}'.format(error_message, str(err)))


def create_image_file(source_path, info, create_image=True):
    small_image = info.pop('icon_small_name', {})
    medium_image = info.pop('icon_medium_name', {})
    large_image = info.pop('icon_large_name', {})
    info.update({
        "icon_large_name": large_image.get('name', ''),
        "icon_medium_name": medium_image.get('name', ''),
        "icon_small_name": small_image.get('name', '')
    })
    if create_image:
        image_path = os.path.join(source_path, 'images')
        create_folder(image_path)
        if large_image.get('name', ''):
            create_file(os.path.join(image_path, large_image.get('name', '')), large_image.get('content', ''), 'wb')
        if small_image.get('name', ''):
            create_file(os.path.join(image_path, small_image.get('name', '')), small_image.get('content', ''), 'wb')
        if medium_image.get('name', ''):
            create_file(os.path.join(image_path, medium_image.get('name', '')), medium_image.get('content', ''), 'wb')
    return info


def create_operation_file(path, operation_name):
    if not os.path.exists(os.path.join(path, operation_name+'.py')):
        content = get_file_content(os.path.join(settings.CONNECTOR_TEMPLATE_DIR, *['generic_template', 'operations.py']))
        content = re.sub(r'sample', operation_name, content)
        create_file(os.path.join(path, operation_name+'.py'), content)


def create_constant_file(path, connector_name):
    content = get_file_content(os.path.join(settings.CONNECTOR_TEMPLATE_DIR, *['generic_template', 'constants.py']))
    content = re.sub(r'sample', connector_name.lower(), content)
    create_file(os.path.join(path, 'constants.py'), content)

def folder_content(path, result=None):
    r = result if result is not None else {}
    ignore_files = ["__pycache__"]
    files = glob.glob(path + '/*')
    for file in files:
        if not file.split('/')[-1] in ignore_files:
            if os.path.isdir(file):
                folder_content(file, r)
            else:
                # f_path = os.path.join(path, file.split('/')[-1])
                relative_file_path = file.split('/')[5:]
                seperator = "/"
                relative_file_path = "/{}".format(seperator.join(relative_file_path))
                r[relative_file_path] = get_file_content(file)
    return r


def create_folder(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except Exception as e:
        raise ConnectorError('Error while creating the folder {0}. ERROR :: {1}'.format(path, str(e)))


def remove_file(path):
    check_file_traversal(path)
    if os.path.exists(path):
        os.remove(path)


def remove_folder(path):
    check_file_traversal(path)
    if os.path.exists(path):
        shutil.rmtree(path)


def create_file(path, content, mode_type='w+'):
    img_file_ext = ["png", "jpg", "jpeg", "tiff", "bmp", "gif"]
    file_ext = path.split("/")[-1].split(".")[-1]
    try:
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            create_folder(directory)

        if file_ext.lower() in img_file_ext:
            content = re.sub('data:image\/[\w]+;base64,', '', content)
            content = base64.b64decode(content)
            mode_type = 'wb'

        f = open(path,  mode_type)
        f.write(content)
    except Exception as e:
        raise ConnectorError('Error while creating the file {0}. ERROR :: {1}'.format(path, str(e)))


def update_file(path, content):
    try:
        os.remove(path)
        create_file(path, content)
    except Exception as e:
        raise ConnectorError()


def get_file_content(path):
    img_file_ext = ["png", "jpg", "jpeg", "tiff", "bmp", "gif"]
    file_name = os.path.basename(path)
    file_ext = file_name.split(".")[-1]

    if not os.path.exists(path):
        raise ConnectorError('Cannot read file : {0}'.format(path))

    if file_ext in img_file_ext:
        try:
            with open(path, 'rb') as image_file:
                image_content = 'data:image/'+file_ext+';base64,' + (
                    base64.b64encode(image_file.read())).decode()
            return image_content
        except Exception as e:
            logger.warn('Error retrieving image content of {0}. ERROR :: {1}'.format(path, str(e)))
    else:
        try:
            with open(path, 'r') as file_obj:
                return file_obj.read()
        except Exception as e:
            err = str(e).replace(path, '')
            raise ConnectorError('Error occurred while retrieving content of {0}. ERROR :: {1}'.format(file_name, err))


def update_operation_files(operations, connector_name, connector_version='', connector_path='', generate_operation_files=False, old_operations=[]):
    operation_import_string = ""
    operation_mapping = ""
    if not connector_path:
        connector_path = get_connector_development_path(connector_name, connector_version)
    try:
        builtin_file_content = get_file_content(os.path.join(connector_path, 'builtins.py'))
        if '#FSR Autogenerated Content. DO NOT DELETE' in builtin_file_content:
            generate_operation_files = True
    except Exception as e:
        pass
    try:
        if generate_operation_files:
            operation_import_string = BUILTIN_PREFIX + '\n'
            new_operations = []
            deleted_operations = []
            for operation in operations:
                operation_name = operation.get('operation')
                if operation_name:
                    create_operation_file(connector_path, operation_name)
                    operation_import_string = operation_import_string + 'from .{0} import {0}\n'.format(operation_name)
                    operation_mapping = operation_mapping + '\'{0}\': {0}, '.format(operation_name)
                    new_operations.append(operation_name)
            if operation_import_string:
                operation_mapping = 'supported_operations = {{{0}}}'.format(operation_mapping)
                operation_import_string = '{0} \n{1}'.format(operation_import_string, operation_mapping)
                create_file(os.path.join(connector_path, 'builtins.py'), operation_import_string)
                for old_operation in old_operations:
                    if old_operation.operation and old_operation.operation not in new_operations:
                        deleted_operations.append(old_operation.operation)
            else:
                src_path = os.path.join(settings.CONNECTOR_TEMPLATE_DIR, *['generic_template', 'builtins.py'])
                des_path = os.path.join(connector_path, 'builtins.py')
                shutil.copyfile(src_path, des_path)
            if deleted_operations:
                all_removed_files = []
                for deleted_operation in deleted_operations:
                    remove_file_path = os.path.join(connector_path, deleted_operation+'.py')
                    remove_file(remove_file_path)
                    all_removed_files.append(remove_file_path)

                sync_data = {
                    'paths': all_removed_files
                }
                sync_ha_nodes_new(sync_data, 'delete')

    except Exception as e:
        raise ConnectorError('Error while updating operation files. Error :: {0}'.format(str(e)))


def is_image_updated(file_content, connector_instance):
    if not connector_instance:
        return False
    metadata = connector_instance.metadata
    small_icon = file_content.get('icon_small_name')
    medium_icon = file_content.get('icon_medium_name')
    large_icon = file_content.get('icon_large_name')
    if isinstance(small_icon, dict) and isinstance(medium_icon, dict) and isinstance(large_icon, dict):
        if not small_icon.get('content') == connector_instance.icon_small or not large_icon.get('content') == connector_instance.icon_large:
            return True
        if not small_icon.get('name') == metadata.get('icon_small_name') or not medium_icon.get('name') == metadata.get('icon_medium_name') \
                or not large_icon.get('name') == metadata.get('icon_large_name'):
            return True
    return False


def update_info_file(file_path, file_content, connector_dev_instance=None):
    try:
        file_content = validate_development_info(file_content)
        name = file_content.get('name')
        version = file_content.get('version')
        operations = file_content.get('operations', [])
        if settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX not in version:
            version = version + settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX
        if not Connector.objects.filter(name=name, version=version, development=True):
            raise ConnectorError('Could not find a connector matching the name or version in the Development Workspace. Checkout the connector into the workspace using the "Add Version" option before editing the name or version of the connector.')
        if is_image_updated(file_content, connector_dev_instance):
            file_content = create_image_file(file_path.replace('info.json', ''), file_content)
        file_content = update_info_file_sequence(file_content)
        update_file(file_path, json.dumps(file_content, indent=4))
        file_content.update({
            'version': version,
            'development': True
        })
        update_operation_files(operations, name, version, old_operations=connector_dev_instance.operations.all())
        insert_connector(file_content)
    except ConnectorError as e:
        raise ConnectorError(e)
    except Exception as e:
        raise ConnectorError('Error while updating info.json files. Error :: {0}'.format(str(e)))


def update_info_file_sequence(info):
    info_sequence = ['name', 'version', 'label', 'description', 'publisher', 'icon_small_name', 'icon_large_name']
    sequenced_info = {}
    for info_key in info_sequence:
        sequenced_info[info_key] = info.pop(info_key, '')
    sequenced_info.update(info)
    return sequenced_info


file_ext_list = {
    "py": "python",
    "json": "json",
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "txt": "text",
    "md": "markdown"
}


def folder_tree(path):
    parent_path = path.split("/")[5]
    ingnore_folders = ["__pycache__", ".DS_Store"]
    file_list = []
    tree = {
        parent_path: {
            'name': parent_path,
            'primaryFolder': True,
            'open': True,
            'setting': True,
            'type': 'folder',
            'files': {
                'info.json': {},
                'requirements.txt': {},
                'connector.py': {},
                'builtins.py': {},
                'utils.py':{},
                'constants.py': {},

            }
        }
    }

    def _file_list(path):
        if os.path.isdir(path):
            paths = [os.path.join(path, x) for x in os.listdir(path)]
            if (len(paths) > 0):
                for p in paths:
                    if ((p.split("/")[-1] not in ingnore_folders) and os.path.isdir(p)):
                        _file_list(p)
                    elif p.split("/")[-1] not in ingnore_folders:
                        file_path_array = p.split("/")[5:]
                        file_path = "/".join(file_path_array)
                        file_list.append(file_path)
            else:
                file_path_array = path.split("/")[5:]
                file_path = "/".join(file_path_array)
                file_list.append(file_path)

    _file_list(path)

    def _get_parent_path(path_array, name):
        path_list = []
        for i in path_array:
            if i == name:
                break
            else:
                path_list.append(i)
        path_list.append(name)
        return os.path.join(*path_list)

    def _folder_object(parent_path_array, file_name):
        return {
            "name": file_name,
            "type": "folder",
            "xpath": _get_parent_path(parent_path_array, file_name),
            "files": {}
        }

    def _file_object(parent_path_array, file_name):
        return {
            "name": file_name,
            "type": file_ext_list.get(file_name.split(".")[-1].lower(), 'text'),
            "xpath": _get_parent_path(parent_path_array, file_name)
        }

    def _add_tree(file_path_array, tree, parent_path_array):
        for i in range(len(file_path_array)):
            if i == 0:
                file_name = file_path_array[i]
                if file_path_array[i] in tree:

                    file_path_array = file_path_array[1:]

                    if 'files' in tree[file_name]:
                        _add_tree(file_path_array, tree[file_name]['files'], parent_path_array)
                    elif 'files' not in tree[file_name]:
                        tree[file_name].update(_file_object(parent_path_array, file_name))

                elif file_path_array[i] not in tree:
                    if (i != len(file_path_array) - 1):
                        tree[file_name] = {}
                        tree[file_name].update(_folder_object(parent_path_array, file_name))

                        file_path_array = file_path_array[1:]
                        _add_tree(file_path_array, tree[file_name]['files'], parent_path_array)

                    elif (i == len(file_path_array) - 1 and len(file_name.split(".")) > 1):
                        tree[file_name] = {}
                        tree[file_name].update(_file_object(parent_path_array, file_name))

                    elif (i == len(file_path_array) - 1 and len(file_name.split(".")) == 1):
                        tree[file_name] = {}
                        tree[file_name].update(_folder_object(parent_path_array, file_name))

    for item in file_list:
        _add_tree(item.split("/"), tree, item.split("/"))

    parent_folders = {}
    parent_files = {}
    for tree_key, tree_item in tree.get(parent_path, {}).get('files', {}).items():
        if tree_item.get('type') == 'folder':
            parent_folders[tree_key] = tree_item
        elif tree_item:
            parent_files[tree_key] = tree_item
    if parent_files:
        tree[parent_path]['files'] = parent_files
    if parent_folders:
        tree[parent_path]['files'].update(parent_folders)

    return tree


def create_tar(path, name):
    temp_file_loaction = os.path.join(settings.CONNECTOR_DEVELOPMENT_DIR, 'temp')
    create_folder(temp_file_loaction)
    tarlocation = os.path.join(temp_file_loaction, name + '.tgz')
    logger.info("Creating tar at %s" % tarlocation)
    with tarfile.open(tarlocation, "w:gz") as tar:
        tar.add(path, arcname=name)
    return tarlocation


def update_modified_date(connector_instance):
    data = {
        "modified": datetime.now().strftime("%d-%m-%YT%H:%M:%S")
    }
    serializer = ConnectorDetailSerializer(connector_instance, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

def validate_development_info(info):
    try:
        if not isinstance(info, str):
            info = json.dumps(info)
        info = json.loads(info)
    except Exception as e:
        raise ConnectorError('Invalid info json please check the syntax')
    name = info.get('name')
    version = info.get('version')
    label = info.get('label')
    if not name or not version or not label:
        raise  ConnectorError('Name or Version or Label missing in info json')
    validate_connector_operation_input({'name':name, 'version':version})
    if name in settings.CONNECTORS_RESERVED:
        raise ConnectorError(
            'A connector by the name "{0}" already exists in the FortiSOAR system connectors. Use a different connector name'.format(
                name))
    if name in settings.CONNECTORS_REPO_NAMES:
        raise ConnectorError(
            'A connector by the name "{0}" already exists in the FortiSOAR Connector Store. Use a different connector name'.format(
                name))
    return info


def check_file_traversal(file_path):
    working_directory = os.path.abspath(settings.CONNECTOR_DEVELOPMENT_DIR)
    requested_path = os.path.relpath(file_path, start=working_directory)
    requested_path = os.path.normpath(os.path.join(working_directory,
                                                   requested_path))
    common_prefix = os.path.commonprefix([requested_path, working_directory])
    if common_prefix is not working_directory:
        raise ConnectorError('Error occurred while traversing the file {0}, Please provide valid path.'.format(file_path))