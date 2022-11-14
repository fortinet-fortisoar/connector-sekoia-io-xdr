""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
WELCOME = "\nLooks like you are starting to write a new connector, run the following command to get started:\n\n" \
          "\t'cs_sdk.py --option create_template --name <connector_name> --version <connector_version>'\n\n" \
          "\tIn addition, this utility can assist you to -\n" \
          "\t1. Add/update the connector metadata, the configuration details and operations supported for the connector\n" \
          "\t2. Register with the sdk and configure the connector\n" \
          "\t3. List all connectors registered with the sdk\n" \
          "\t4. Run health check on these installed connectors\n" \
          "\t5. List the supported operations for a given connector\n" \
          "\t6. Execute an operation on a connector\n\n" \
          "Use the help command ‘./cs_sdk.py -h’ or ‘./cs_sdk.py --help’ for more details on the options.\n"

CREATE_FILES_COMPLETE = "Well done! Your directory {0} is created!\n " \
                        "Use ‘--option add_info --name {1} --version {2}’ to add the connector metadata\n"

ADD_INFO_COMPLETE = "Well done! The connector info.json has been updated with the above information for the connector!\n" \
                    "Use ‘--option add_config_params --name {0} --version {1}’ to add the connector configuration parameters.\n"

ADD_CONFIG_PARAMS_COMPLETE = "Well done! The configuration input parameters have been added successfully.\n" \
                             "Implement the health check function for the connector at {0}/health_check.py.\n" \
                             "Use ‘--option add_operation --name {1} --version {2}’ to add operations on the connector.\n"

ADD_OPERATION_COMPLETE = "Well done! The operation has been added. Add the operation’s implementation in {0} \n"

ADD_OPERATIONS_COMPLETE = "Use ‘--option import --name {0} --version {1}’ to import the connector with the sdk. Make sure to add" \
                          "the function implementations for the supported operations before importing the connector" \
                          "with the sdk.\n"

REGISTER_COMPLETE = "Well done! The connector has been successfully imported.\n\n" \
                    "Use ‘--option configure --name {0} --version {1}’ to provide the configuration inputs and set up the connector.\n" \
                    "Use '--option remove --name {0} --version {1}' to remove the connector.\n" \
                    "Use '--option export --name {0} --version {1}' to export the connector into a .tgz.\n" \

CONFIGURE_COMPLETE = "Well done! The connector has been configured.\n\n" \
                     "Use ‘--option check_health --name {0} --version {1} --config {2}’ to check the connector health again\n" \
                     "'--option execute --name {0} --version {1}’ to execute any operation on the connector\n" \
                     "'--option list_operations’ to list operations available on any connector\n" \
                     "'--option list_connectors’ to list all imported connectors\n" \
                     "‘--option list_configs’ to list all imported connectors\n"

CONFIGURE_FAILED = "Failed to add the connector configuration '{0}'\n"

CONNECTOR_NOT_FOUND = "Could not find a connector with name {0} and version {1}.\n"

INVALID_CONNECTOR_NAME = "Only alphabets, numbers and underscore are allowed for the connector name. The name must not start with a number\n"

INVALID_CONNECTOR_VERSION = "Version must be of the format x.y.z, where x,y,z are integers\n"