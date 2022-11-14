import json
import logging
from os import listdir
from os.path import isfile, join
from django.apps import AppConfig
from django.conf import settings
from postman.utils.helper import load_connectors_repo_name

logger = logging.getLogger('connectors')


def load_connector_templates():
    try:
        template_list = []
        template_folders = [f for f in listdir(settings.CONNECTOR_TEMPLATE_DIR) if f != "generic_template"]
        for folder in template_folders:
            tmp = {}
            file_path = join(settings.CONNECTOR_TEMPLATE_DIR, folder, "info.json")
            try:
                with open(file_path, 'r') as image_file:
                    f = open(file_path)
                    info = json.load(f)
                tmp["name"] = info.get("name")
                tmp["label"] = info.get("label")
                tmp["folder"] = folder
                template_list.append(tmp)
            except Exception as e:
                logger.warn('Error retrieving template content of {0} ERROR :: {1}'.format(file_path, str(e)))
        
        settings.CONNECTOR_TEMPLATES = template_list
        settings.CONNECTORS_REPO_NAMES = load_connectors_repo_name()
    except Exception as err:
        logger.error("Connector Templates : Unable to load connector templates. Error: {0}".format(str(err)))

class ConnectorDevelopmentConfig(AppConfig):
    name = 'connector_development'

    def ready(self):
        load_connector_templates()

        