from rest_framework import serializers
from connectors.models import ExecuteAction
from postman.models import Tenant, Agent


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'


class AgentSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(many=True, read_only=True)
    class Meta:
        model = Agent
        fields = '__all__'


class ExecuteActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecuteAction
        fields = '__all__'
