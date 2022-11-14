from django.db import models
from jsonfield import JSONField


class my_JSONField(JSONField):
    def value_to_string(self, obj):
        return self.value_from_object(obj)
    
    
class Team(models.Model):
    uuid = models.CharField(max_length=100)


class Tenant(models.Model):
    class Meta:
        pass

    name = models.CharField(max_length=500)
    role = models.CharField(max_length=500, null=True, blank=True)
    active = models.BooleanField(default=False)
    tenant_id = models.CharField(max_length=1000, unique=True)
    uuid = models.CharField(max_length=500, unique=True)
    is_dedicated = models.BooleanField(default=False)


class Agent(models.Model):
    name = models.CharField(max_length=500)
    agent_id = models.CharField(max_length=1000, unique=True)
    tenant = models.ManyToManyField(Tenant)
    team = models.ManyToManyField(Team)
    active = models.BooleanField(default=False)
    uuid = models.CharField(max_length=500, unique=True)
    is_local = models.BooleanField(default=False)
    version = models.CharField(max_length=20, default='6.4.0')
    health_status = my_JSONField(default=dict, blank=True, null=True)
    sync_time = models.DateTimeField(blank=True, null=True)
    config_status = models.CharField(max_length=1000, blank=True, null=True)
    allow_remote_operation = models.BooleanField(default=True)
