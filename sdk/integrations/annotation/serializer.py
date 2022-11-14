""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from rest_framework import serializers
from annotation.models import Annotation
from connectors.models import Connector
from connectors.serializers import ConnectorOperationSerializer
class AnnotationListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Annotation
        fields = ('id', 'name', 'category', 'system', 'connectors')


class AnnotationDetailSerializer(serializers.ModelSerializer):
    operations = ConnectorOperationSerializer(many=True, read_only=True)
    class Meta:
        model = Connector
        fields = ('id', 'name', 'version', 'label', 'icon_small', 'operations')

