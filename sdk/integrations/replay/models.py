""" Copyright start
  Copyright (C) 2008 - 2021 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from django.db import models
from django.db.models import JSONField
from postman.models import Agent


class ReplayLog(models.Model):
    """
    Log of unpublished data

    """
    callback_name = models.CharField(max_length=500)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, null=True, blank=True, to_field='agent_id')
    uuid = models.CharField(max_length=500, unique=True)
    data = JSONField(default=dict, blank=True, null=True)
