# Connector development application
This application serves as the platform for development/execution of connectors.

### Table of Contents
**[Application Setup Instructions](#application-setup-instructions)**<br>
**[SDK Usage Instructions](#sdk-usage-instructions)**<br>
**[APIs](#apis)**<br>

## Application Setup Instructions


#### Install and create virtual-env with python 3.6+
```
pip -q install venvctrl virtualenv
virtualenv -p <path_to_python> ~/workspace/integrations-sdk/.env
eg: virtualenv -p /usr/local/bin/python3 ~/workspace/integration-sdk/.env
```

#### Activate and install requirement.txt
```
source ~/workspace/integration-sdk/.env/bin/activate
pip install -b ./tmp -r requirements.txt
```
####  setup the database
```
cd integrations
python setupsdk.py

```
####  Setting up Django Rest UI.
This is required if you wish to invoke the REST APIs via the Django User Interface
```
mkdir static
python manage.py collectstatic
```

Note: All the above steps are required only the first time the sdk is setup.

####  Starting the application server.
```
python manage.py runserver

By default, the server runs on port 8000 on the IP address 127.0.0.1. You can pass in an IP address and port number explicitly.
```

## SDK Usage Instructions

#### The sdk is now ready. Start using the script 'cs_sdk.py' to build and test connectors 
```
    Commands and there outputs are shown below:
    
    1) ./cs_sdk.py
        Looks like you are starting to write a new connector, run the following command to get started:
            cs_sdk.py --option create_template --name <connector_name> --version <connector_version>
        
        In addition, this utility can assist you to -
        Add/update the connector metadata, the configuration details and operations supported for the connector
        Register with the sdk and configure the connector
        List all connectors registered with the sdk
        Run health check on these installed connectors
        List the supported operations for a given connector
        List add configurations for a connector
        Execute an operation on a connector
        Unregister the connector
    
    Use the help command ‘./cs_sdk.py -h’ or ‘./cs_sdk.py --help’ for more details on the options.
    
    
    2) ./cs_sdk.py --option create_template --name <connector_name> --version <connector_version>
        By default, the connector directory gets generated in the same location as cs_sdk.py. If you wish to override, enter target directory:
    
    Upon completion:
       Well done! Your directory <directory name> is created. Use ‘--option add_info --name <connector_name> --version <connector_version>’ to add the connector metadata
    
    3) ./cs_sdk.py --option add_info --name <connector_name> --version <connector_version>
           Connector Name:
           Description:
           Version:
           Publisher:
           Category:
           Is the connector approved by Cybersponse (Y/Yes/N/No):
           Is the connector compatible with Cybersponse (Y/Yes/N/No):
           File path to a small icon for the connector:
           File path to a large icon for the connector:
    
    Upon completion:
       Well done! The connector info.json has been updated with the above information for the connector. Use ‘--option add_config_params --name <connector_name> --version <connector_version>’ to add the connector configuration parameters.
    
    4) ./cs_sdk.py --option add_config_params --name <connector_name> --version <connector_version>
        Field name:
        Is it a required field (Y/Yes/N/No):
        Is it a user-editable field (Y/Yes/N/No):
        Is it a field visible to the user (Y/Yes/N/No):
    
        Would you like to add another field (Y/Yes/N/No):
        Repeats till user enters no.
    
    Upon completion:
         Well done! The configuration input parameters have been added successfully.
         Implement the health check function for the connector at <connector_location>/health_check.py
    
         Use ‘--option add_operation --name <connector_name> --version <connector_version>’ to add operations on the connector.
    
    5) ./cs_sdk.py --option add_operation --name <connector_name> --version <connector_version>
        Operation name:
        Operation description:
        Is the operation enabled on the connector (Y/Yes/N/No):
        Below set of inputs is for the parameters of the connector
    
        Parameter name:
        Is a required parameter (Y/Yes/N/No):
        Is a visible parameter (Y/Yes/N/No):
        Is an editable parameter (Y/Yes/N/No):
        Default value for the parameter:
    
         Add another parameter? (Y/Yes/N/No):
    
    Repeats till no other param is to be added. Upon completion:
        Well done! The operation has been added. Add the operation’s implementation in <connector_location>/<operation_name>.py
```
    
#### For the subsequent operations of importing the connector and performing operations on it, you need the django server to be up.
See [Starting the application server](#starting-the-application-server) to start the django server.
``` 
    6) ./cs_sdk.py --option import --name <connector_name> --bundle <path to connector archive> --path <path to connector folder> 
    <path to connector archive>  - The .tgz file of the connector bundle
    Or
    <path to connector folder> - The absolute path to the connector folder. The sdk will create a tar and import.
    
    Upon completion:
       Well done! The connector has been successfully imported. 
       Use ‘--option configure --name <connector_name> --version <connector_version>’ to provide the configuration inputs and set up the connector.
       Use '--option remove --name <connector_name> --version <connector_version>' to remove the connector.
       Use '--option export --name <connector_name> --version <connector_version>' to export the connector into a .tgz.
       
    7) ./cs_sdk.py --option configure --name <connector_name> --version <connector_version>
    Field 1:
    Field 2: ....
    
    Upon completion:
       Well done! The connector has been configured. The check_health response is:
        <output from health check function>
       Use ‘--option check_health’ to check the connector health again
              ‘--option execute’ to execute any operation on the connector
              ‘--option list_operation’ to list operations available on any connector
              ‘--option list_connectors’ to list all imported connectors
              ‘--option list_configs’ to list all configurations added for an imported connector
    
    8) ./cs_sdk.py --option list_configs --name <connector_name> --version <connector_version>
    Lists all configurations added for a connector
    
    9) ./cs_sdk.py --option check_health --name <connector_name> --version <connector_version> --config <config_name>
    
    10) ./cs_sdk.py --option execute --name <connector_name> --version <connector_version> --config <config_name> --operation <operation_name>
    Field 1:
    Field 2: ....
    
    Upon completion:
     <output from the execute function>

    11) ./cs_sdk.py --option export --name <connector_name> --version <connector_version>
    Create a .tgz file from an imported connector
    
    12) ./cs_sdk.py --option remove --name <connector_name> --version <connector_version>
    Removes the connector from the sdk
    
    13) ./cs_sdk.py --option list_operations --name <connector_name> --version <connector_version>
    
    14) ./cs_sdk.py --option list_connectors 
```

## APIs




