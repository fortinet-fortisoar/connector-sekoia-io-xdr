""" Copyright start
  Copyright (C) 2008 - 2021 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import uuid
import json
from replay.models import ReplayLog
from postman.models import Agent
from django.conf import settings


def save_into_fail_event_log(data, agent_id, callback_name, *args, **kwargs):
    agent_instance = Agent.objects.filter(agent_id=agent_id).first()
    try:
        data = json.loads(data)
    except:
        pass
    if agent_instance:
        ReplayLog.objects.create(
            **{
                'data': data,
                'agent_id': agent_id,
                'callback_name': callback_name,
                'uuid': str(uuid.uuid4())
            }
        )
