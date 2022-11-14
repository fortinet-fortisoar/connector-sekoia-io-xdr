""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import json
import re
from os.path import join, abspath, isfile, splitext
from os import pardir, makedirs, remove
import shutil
from sdk_utils import messages
from sdk_utils.sdkutil import config_util, get_input, get_input_with_validation, get_file_input, get_boolean

boolean_inputs = ['Yes', 'Y', 'yes', 'y', 'No', 'N', 'no', 'n']


def read_info_json(name, version):
    connector_path = config_util.get_connector_path(name, version)
    if not connector_path:
        return None
    info_json_path = join(connector_path, 'info.json')
    with open(info_json_path, "r") as info_json:
        data = json.load(info_json)
    return data


def write_info_json(name, version, data):
    info_json_path = join(config_util.get_connector_path(name, version), 'info.json')
    with open(info_json_path, "w") as info_json_updated:
        info_json_updated.write(json.dumps(data, indent=4))


def copy_connector_folder(name, version):
    if not re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*$").match(name):
        return messages.INVALID_CONNECTOR_NAME

    if not re.compile(r"[0-9]+.[0-9]+.[0-9]+$").match(version):
        return messages.INVALID_CONNECTOR_VERSION

    target_dir = input("By default, the connector directory gets generated in the same location as build.py. "
                       "If you wish to override, enter target directory: ")
    if not target_dir or str(target_dir).split() == '':
        path_connector = abspath(join(__file__, pardir, name))
    else:
        path_connector = join(target_dir, name)
    path_template = abspath(join(__file__, pardir, 'template'))
    shutil.copytree(path_template, path_connector)
    # remove the sample function
    fn_dummy_path = join(path_connector, 'fn_dummy.py')
    remove(fn_dummy_path)
    # add to config
    config_util.add_connector_config(name, version, path_connector)
    return messages.CREATE_FILES_COMPLETE.format(path_connector, name, version)


def copy_image(name, version, image_path, image_name ):
    images_folder = join(config_util.get_connector_path(name, version), 'images')
    makedirs(images_folder, exist_ok=True)
    filename, file_extension = splitext(image_path)
    image_name += file_extension
    target_image = join(images_folder, image_name)
    shutil.copy(image_path, target_image)
    return image_name


def add_connector_info(name, version):
    data = read_info_json(name, version)
    if data is None:
        return messages.CONNECTOR_NOT_FOUND.format(name, version)
    # get remaining inputs
    label = get_input('Connector Label: ')
    description = get_input('Description: ')
    publisher = get_input('Publisher: ')
    category = get_input('Category: ')
    help_online = input('Link to online connector documentation: ')
    help_file = input('Path to connector documentation pdf (Path must be relative to the connector folder): ')
    cs_approved = get_input('Is the connector approved by Fortinet (Y/Yes/N/No): ',
                            boolean_inputs)
    cs_compatible = get_input('Is the connector compatible with FortiSOAR (Y/Yes/N/No): ',
                              boolean_inputs)
    # TODO: validate inline that this file exists, otherwise prompt again
    small_icon_path = get_file_input('File path to a small icon for the connector: ')
    large_icon_path = get_file_input('File path to a large icon for the connector: ')

    is_cs_approved = get_boolean(cs_approved)
    is_cs_compatible = get_boolean(cs_compatible)

    # update the json
    data['name'] = name
    data['label'] = label
    data['description'] = description
    data['publisher'] = publisher
    data['cs_approved'] = is_cs_approved
    data['cs_compatible'] = is_cs_compatible
    data['version'] = version
    data['category'] = category

    if small_icon_path:
        small_icon_name = copy_image(name, version, small_icon_path, 'small_icon')
        data['icon_small_name'] = small_icon_name
    if large_icon_path:
        large_icon_name = copy_image(name, version, large_icon_path, 'large_icon')
        data['icon_large_name'] = large_icon_name
    if help_online:
        data['help_online'] = help_online
    if help_file:
        data['help_file'] = help_file
    write_info_json(name, version, data)
    return messages.ADD_INFO_COMPLETE.format(name, version)


def __add_or_replace_in_list(input_list, val, field_to_match):
    for n, element in enumerate(input_list):
        if element[field_to_match] == val[field_to_match]:
            print("warn: %s already exists..replacing..." % element[field_to_match])
            input_list[n] = val
            return
    input_list.append(val)


def add_config_params(name, version):
    data = read_info_json(name, version)
    if data is None:
        return messages.CONNECTOR_NOT_FOUND.format(name, version)
    # get existing config parameters
    if "configuration" in data and "fields" in data["configuration"]:
        existing_fields = data["configuration"]["fields"]
    else:
        existing_fields = []
        if "configuration" in data:
            data["configuration"]["fields"] = existing_fields
        else:
            data["configuration"] = {"fields": existing_fields}

    is_continue = True
    while is_continue:
        field_name = get_input('Field Name: ')
        field_title = get_input('Title: ')
        # TODO: add validation- name should not have spaces
        required = get_input('Is it a required field (Y/Yes/N/No): ', boolean_inputs)
        editable = get_input('Is it a user-editable field (Y/Yes/N/No): ', boolean_inputs)
        visible = get_input('Is it a field visible to the user (Y/Yes/N/No): ', boolean_inputs)
        # TODO: add validation against possible permutations of required/editable/visible
        # TODO: there should be a default value for the non-editable/non-visible but required values
        type = get_input('Field Type (text/password/checkbox/select/mutliselect/integer/'
                         'decimal/datetime/phone/email/file/richtext/json/textarea/image): ')
        is_required = get_boolean(required)
        is_editable = get_boolean(editable)
        is_visible = get_boolean(visible)
        fields_dict = {'title': field_title,
                       'name': field_name,
                       'required': is_required,
                       'editable': is_editable,
                       'visible': is_visible,
                       'type': type}
        if str(type) == 'select' or str(type) == 'multiselect':
            options = get_input('List of possible values (as an array, eg, ["A","B","C"]): ')
            fields_dict['options'] = options
        else:
            value = input('Default Value: ')
            if value:
                fields_dict['value'] = value
        # replace or add the field
        __add_or_replace_in_list(existing_fields, fields_dict, 'name')
        is_continue = get_boolean(get_input('\n\nWould you like to add another field (Y/Yes/N/No): ',
                                            boolean_inputs))
    write_info_json(name, version, data)
    return messages.ADD_CONFIG_PARAMS_COMPLETE.format(config_util.get_connector_path(name, version), name, version)


def add_function(name, version):
    data = read_info_json(name, version)
    if data is None:
        return messages.CONNECTOR_NOT_FOUND.format(name, version)
    if 'operations' in data:
        existing_operations = data['operations']
    else:
        existing_operations = []
        data['operations'] = existing_operations

    operation = get_input('Operation name: ')
    title = get_input('Operation title: ')
    description = get_input('Operation description: ')
    annotation = input('Operation annotation: ')
    category = input('Annotation category:')
    is_enabled = get_boolean(get_input('Is the operation enabled on the connector (Y/Yes/N/No): ', boolean_inputs))
    print('Below set of inputs is for the parameters of the connector\n')
    params = []
    operation_dict = {'operation': operation,
                      'title': title,
                      'description': description,
                      'enabled': is_enabled,
                      'parameters': params}
    if annotation:
        operation_dict['annotation'] = annotation
    if category:
        operation_dict['category'] = category
    is_add_param = get_boolean(get_input("\nAdd a parameter? (Y/Yes/N/No): ", boolean_inputs))
    while is_add_param:
        param_name = get_input('Parameter name: ')
        param_title = get_input('Title: ')
        is_required = get_boolean(get_input('Is a required parameter (Y/Yes/N/No): ', boolean_inputs))
        is_visible = get_boolean(get_input('Is a visible parameter (Y/Yes/N/No): ', boolean_inputs))
        is_editable = get_boolean(get_input('Is an editable parameter (Y/Yes/N/No): ', boolean_inputs))
        type = get_input('Field Type (text/password/checkbox/select/mutliselect/integer/'
                         'decimal/datetime/phone/email/file/richtext/json/textarea/image): ')
        param_dict = {'title': param_title,
                      'required': is_required,
                      'visible': is_visible,
                      'editable': is_editable,
                      'type': type,
                      'name': param_name}
        if str(type) == 'select' or str(type) == 'multiselect':
            options = get_input('List of possible values (as an array, eg, ["A","B","C"]): ')
            param_dict['options'] = options
        else:
            value = input('Default Value for the parameter: ')
            if value:
                param_dict['value'] = value
        params.append(param_dict)
        is_add_param = get_boolean(get_input("\nAdd another parameter? (Y/Yes/N/No): ", boolean_inputs))
    __add_or_replace_in_list(existing_operations, operation_dict, "operation")
    write_info_json(name, version, data)
    generate_from_json(name, version)
    # TODO: ensure op name does not have special chars or spaces etc
    filename = operation.lower().replace(' ', '_') + ".py"
    function_file_path = join(config_util.get_connector_path(name, version), filename)
    return messages.ADD_OPERATION_COMPLETE.format(function_file_path), True


def add_functions(name, version):
    is_continue = True
    while is_continue:
        try:
            message, status = add_function(name, version)
            if status:
                is_continue = get_boolean(get_input("\n\nAdd another operation on the connector? (Y/Yes/N/No): ",
                                                    boolean_inputs))
            else:
                is_continue = False
        except:
            is_continue = False
    return messages.ADD_OPERATIONS_COMPLETE.format(name, version)


def __get_imports(op_names):
    import_stmt = ""
    for op in op_names:
        import_stmt = import_stmt + "from ." + op + " import " + op + "\n"
    return import_stmt


def __create_function_file(name, version, op_names):
    template_fn_path = abspath(join(__file__, pardir, 'template', 'fn_dummy.py'))
    fn_dummy = open(template_fn_path, 'r')
    fn_code = fn_dummy.read()
    fn_dummy.close()

    for op_name in op_names:
        filename = op_name + ".py"
        function_file_path = join(config_util.get_connector_path(name, version), filename)
        # if the function file already exists,do not change it
        if not isfile(function_file_path):
            print("creating template file for function %s ..." % op_name)
            with open(function_file_path, 'w') as function_modified:
                fn_code_modified = fn_code.replace('function_template', op_name)
                fn_code_modified = fn_code_modified.replace('<connector_name>', name)
                function_modified.write(fn_code_modified)


def generate_from_json(name, version):
    # get the list of functions from info_json
    data = read_info_json(name, version)
    if data is None:
        return messages.CONNECTOR_NOT_FOUND.format(name, version)

    # overwrite the existing connector.py
    connector_file_path = join(config_util.get_connector_path(name, version), 'connector.py')
    template_connector_path = abspath(join(__file__, pardir, 'template', 'connector.py'))
    shutil.copyfile(template_connector_path, connector_file_path)

    connector_class_name = name.title().replace(' ', '')
    supported_operations = data["operations"]
    supported_ops_str_replaced = "supported_operations = {"
    supported_op_names = {}
    first = True
    for supported_op in supported_operations:
        op_name = supported_op["operation"]
        fn_name = op_name.lower().replace(' ', '_')
        supported_op_names[op_name] = fn_name
        if not first:
            supported_ops_str_replaced += ", "
        supported_ops_str_replaced += "'%s': %s" % (op_name, fn_name)
        first = False
    supported_ops_str_replaced += "}"
    supported_ops_str = re.compile("supported_operations = {.*}")

    # generate sample functions
    __create_function_file(name, version, supported_op_names.values())

    # TODO: generate health_check also with mandatory config params to state 'NotConfigured'
    # open connector file
    connector_org = open(connector_file_path, 'r')
    connector_code = connector_org.read()
    connector_org.close()
    # replace the content
    connector_code = __get_imports(supported_op_names.values()) + connector_code
    connector_code = connector_code.replace('class Template', 'class ' + connector_class_name)
    connector_code = connector_code.replace('connector_name', name)
    connector_code = re.sub(supported_ops_str, supported_ops_str_replaced, connector_code)

    with open(connector_file_path, 'w') as connector_modified:
        connector_modified.write(connector_code)
    return "Done. Add the implementation for the generated functions."
