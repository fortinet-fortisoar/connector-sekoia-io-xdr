""" Copyright start
  Copyright (C) 2008 - 2021 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import json
import pika
import logging

from django.core.paginator import Paginator
from django.conf import settings
from replay.utils import threaded
from postman.utils.utility import get_peer_publish_action

from replay.models import ReplayLog

logger = logging.getLogger('replay')


def _replay_log(agent_id, callback_name, *args, **kwargs):
    from postman.core.publisher import Publisher
    logs = ReplayLog.objects.filter(agent_id=agent_id, callback_name=callback_name).order_by('id')
    while logs.count():
        paginator = Paginator(logs, settings.LOG_PAGINATION)
        for each_page in range(paginator.num_pages):
            logs = paginator.page(each_page + 1)
            for each_log in logs:
                pub_config = get_peer_publish_action(callback_name, agent_id)
                try:
                    publisher = Publisher(pub_config)
                    publisher.publish(message=json.dumps(each_log.data), tenant_id=agent_id, from_replay=True)
                    each_log.delete()
                except pika.exceptions.AMQPConnectionError as e:
                    # if connection is broken while replay of log  is on, then break the replication and return
                    logger.error('replay is halted due to connectivity issue with exchange')
                    return
                except Exception as e:
                    logger.error('Error while replaying data of callback %s to agent %s: %s', callback_name, agent_id,
                                 str(e))
                    return
        logs = ReplayLog.objects.filter(agent_id=agent_id, callback_name=callback_name).order_by('id')
    logger.info('Replay of failed events for %s is complete', callback_name)


@threaded
def replay_log(agent_id):
    publish_actions = settings.ALL_CONFIG.config.get('rabbitmq_cyops').get('peerPublishAction')
    for key, value in publish_actions.items():
        if value.get('onFailure', {}).get('replay', False):
            settings.REPLICATING_LOG[agent_id] = True
            _replay_log(agent_id, callback_name=key)
            settings.REPLICATING_LOG[agent_id] = False
