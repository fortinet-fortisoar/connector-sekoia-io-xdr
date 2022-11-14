""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end 
"""

from enum import Enum

from django.db import models
from jsonfield import JSONField

from postman.models import Agent


class my_JSONField(JSONField):
    def value_to_string(self, obj):
        return self.value_from_object(obj)


class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return [(x.value, x.name) for x in cls]

    @classmethod
    def list(cls):
        return [x.name for x in cls]


class Team(models.Model):
    uuid = models.CharField(max_length=100, unique=True, primary_key=True)


class Role(models.Model):
    uuid = models.CharField(max_length=100, unique=True, primary_key=True)


class Connector(models.Model):
    class Meta:
        unique_together = (('name', 'version', 'agent'),)

    name = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    label = models.CharField(max_length=500)
    configuration_old = my_JSONField(default=dict, blank=True, null=True)
    config_schema = my_JSONField(default=dict, blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    publisher = models.CharField(max_length=500, blank=True, null=True)
    active = models.BooleanField(default=True)
    cs_compatible = models.BooleanField(default=True)
    migrate = models.BooleanField(default=False)
    system = models.BooleanField(default=False)
    playbook_collections = my_JSONField(default=list, blank=True, null=True)
    icon_small = models.TextField(blank=True, null=True)
    icon_large = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    help_online = models.TextField(blank=True, null=True)
    help_file = models.TextField(blank=True, null=True)
    vendor_version = models.TextField(blank=True, null=True)
    metadata = my_JSONField(default=dict, blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    install_result = my_JSONField(default=dict, blank=True, null=True)
    config_count = models.IntegerField(default=0)
    ingestion_supported = models.BooleanField(default=False, blank=True, )
    cs_approved = models.BooleanField(default=False, blank=True, )
    tags = my_JSONField(default=list, blank=True, null=True)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, null=True, blank=True, to_field='agent_id')
    remote_status = my_JSONField(default=dict, blank=True, null=True)
    rpm_full_name = models.CharField(max_length=500, blank=True, null=True)
    development = models.BooleanField(default=False)
    installed = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    modified = models.DateTimeField(auto_now=True, blank=True, null=True)
    requirements_installed = models.CharField(max_length=50, blank=True, null=True)


class Configuration(models.Model):
    class Meta:
        unique_together = (('name', 'connector', 'agent'),)

    config_id = models.CharField(max_length=100, unique=True)
    status = models.IntegerField(default=1)
    name = models.CharField(max_length=100)
    default = models.BooleanField(default=False)
    config = my_JSONField(default=dict, blank=True, null=True)
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE, related_name='configuration')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, null=True, blank=True, to_field='agent_id')
    remote_status = my_JSONField(default=dict, blank=True, null=True)
    health_status = my_JSONField(default=dict, blank=True, null=True)
    teams = models.ManyToManyField(Team)


class Operation(models.Model):
    class Meta:
        unique_together = (('operation', 'connector'),)

    operation = models.CharField(max_length=100)
    description = models.CharField(max_length=1000, blank=True, null=True)
    title = models.CharField(max_length=100)
    output_schema = my_JSONField(default=dict, blank=True, null=True)
    parameters = my_JSONField(default=dict, blank=True, null=True)
    enabled = models.BooleanField(default=True)
    annotation = models.CharField(max_length=100, blank=True, null=True)
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE, related_name='operations')
    metadata = my_JSONField(default=dict, blank=True, null=True)
    visible = models.BooleanField(default=True)
    roles = models.ManyToManyField(Role)



class ExecuteAction(models.Model):
    result = my_JSONField(default=dict, blank=True, null=True)
    action = models.CharField(max_length=500, )
    remote_status = my_JSONField(default=dict, blank=True, null=True)
    request_payload = my_JSONField(default=dict, null=True, blank=True)

    connector = models.ForeignKey(Connector, on_delete=models.CASCADE, )
    configuration = models.ForeignKey(Configuration, on_delete=models.DO_NOTHING, blank=True, null=True,
                                      to_field='config_id')

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, null=True, blank=True, to_field='agent_id')

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    log_records = models.TextField(null=True, blank=True)
