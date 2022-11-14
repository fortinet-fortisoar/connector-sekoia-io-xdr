""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from rest_framework import serializers
from connectors.models import Connector, Operation, Configuration, Role, Team
from django.db.models import Q
import json

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'

class DynamicFieldSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        context = kwargs.get('context', None)
        fields = None
        if context:
            fields = context.get('fields', None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class ConnectorListConfigurationSerializer(DynamicFieldSerializer):
    class Meta:
        model = Configuration
        fields = ('id', 'config_id', 'name')


class ConnectorListSerializer(serializers.ModelSerializer):
    configuration = ConnectorListConfigurationSerializer(many=True, read_only=True)
    class Meta:
        model = Connector
        fields = ('id', 'name', 'version', 'label', 'category', 'active', 'system', 'icon_small', 'icon_large',
                  'description', 'config_count', 'status', 'install_result', 'configuration', 'ingestion_supported', 'tags',
                  'agent', 'remote_status', 'development', 'created', 'modified')

class ConnectorConfigurationSerializer(serializers.ModelSerializer):
    team_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Team.objects.all(), source='teams', required=False, allow_null=True)
    class Meta:
        model = Configuration
        exclude = ('teams',)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['teams'] = ret.pop('team_ids', [])
        return ret

class ConnectorConfigurationAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        fields = ('id', 'config_id', 'name', 'default', 'config', 'connector', 'status', 'agent')


class ConnectorOperationSerializer(serializers.ModelSerializer):
    role_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=Role.objects.all(), source='roles', required=False, allow_null=True)
    class Meta:
        model = Operation
        exclude = ('roles',)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['roles'] = ret.pop('role_ids', [])
        metadata_fields = ret['metadata']
        for field, value in metadata_fields.items():
            if not ret.get(field, None):
                ret[field] = value
        ret.pop('metadata', None)
        return ret


class ConnectorDetailSerializer(serializers.ModelSerializer):
    configuration = serializers.SerializerMethodField('get_config_serializer')
    operations = ConnectorOperationSerializer(many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        self.teams = kwargs.pop('teams', [])
        super().__init__(*args, **kwargs)

    def get_config_serializer(self, obj):
        if isinstance(self.teams, str):
            self.teams = json.loads(self.teams)
        if self.teams:
            queryset = Configuration.objects.filter(Q(teams__isnull=True) | Q(teams__in=self.teams), connector=obj).distinct()
            serializer =  ConnectorConfigurationSerializer(queryset, many=True, read_only=True)
            return serializer.data
        else:
            queryset = Configuration.objects.filter(connector=obj)
            serializer =  ConnectorConfigurationSerializer(queryset, many=True, read_only=True)
            return serializer.data


    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret.pop('configuration_old', None)
        ret.pop('migrate', None)
        metadata_fields = ret['metadata']
        for field, value in metadata_fields.items():
            if not ret.get(field, None):
                ret[field] = value
        ret.pop('metadata', None)
        return ret

    class Meta:
        model = Connector
        fields = '__all__'
        read_only_fields = ()