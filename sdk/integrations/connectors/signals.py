from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from connectors.core.connector import logger, ConnectorError
from connectors.models import Configuration, Connector
from data_import.models import DataImport
from integrations.crudhub import make_request
from connectors.core.connector import logger, ConnectorError


@receiver(pre_delete, sender=DataImport)
def clear_ingestion(sender, instance, **kwargs):
    sender_id = instance.id
    connector = instance.configuration.connector
    # if the deletion of the previous version of the connector is in progress due to connector upgrade
    # then we do not need to delete the entities attached with this configuration since we restore the configs after
    # connector upgrade
    if connector.metadata.get('upgrade_in_progress'):
        return
    config_id = instance.configuration.config_id
    _clean_ingestion_collection(config_id)
    _clean_macros(config_id)
    schedule_id = instance.metadata.get('scheduleId')
    if schedule_id: _clean_schedules(schedule_id)


def _clean_macros(config_id):
    try:
        macro_workflow_id = None
        macro_id = None
        response = make_request('/api/3/workflows?collection={}&recordTags=fetch'.format(config_id), 'GET')
        for workflow in response['hydra:member']:
            macro_workflow_id = workflow['@id']

        if macro_workflow_id:
            macro_id = make_request('/api/wf/api/dynamic-variable/?format=json&search={}'
                                    .format(macro_workflow_id.split('/')[-1].replace('-', '_')), 'GET')['hydra:member'][0][
                'id']
        if macro_id:
            make_request('/api/wf/api/dynamic-variable/{}/'.format(macro_id), 'DELETE')
    except Exception as e:
        logger.error('Error while deleting macro related to data ingestion for config id: %s', config_id)


def _clean_ingestion_collection(config_id):
    try:
        make_request('/api/3/delete/workflow_collections', 'DELETE', body={'ids': [config_id]})
    except Exception as e:
        logger.error('Error while deleting pb collection related to data ingestion for config id: %s', config_id)


def _clean_schedules(schedule_id):
    try:
        make_request('/api/wf/api/scheduled/{0}/?format=json'.format(schedule_id), 'DELETE')
    except Exception as e:
        logger.error('Error while deleting schedule related to data ingestion for config id: %s', schedule_id)

