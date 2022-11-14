""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import json
import os
import ast
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import viewsets
from annotation.models import Annotation
from annotation.serializer import AnnotationListSerializer, AnnotationDetailSerializer
from connectors.core.connector import logger
from rest_framework.response import Response
from connectors.models import Connector
from rest_framework.decorators import action
from rest_framework import status


class AnnotationView(viewsets.ModelViewSet):
    """
    A simple ViewSet for Annotation.
    """
    queryset = Annotation.objects.all()
    serializer_class = AnnotationListSerializer
    filter_backends = (filters.OrderingFilter,
                       filters.SearchFilter,
                       DjangoFilterBackend,)
    ordering_fields = ('id', 'name', 'category')
    search_fields = ('$name', '$id')
    filter_fields = ('id', 'name', 'category')

    """
    Retrieve a model instance.
    """

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        connectors = instance.connectors
        try:
            connectors = ast.literal_eval(connectors)
        except:
            pass
        res = {"data": [get_connectors_detail(conn, instance.name)
                        for conn in connectors if Connector.objects.filter(id=conn).exists()]}
        return Response(res)

    @action(detail=False)
    def categories(self, request, *args, **kwargs):
        try:
            with open(os.path.abspath(os.path.dirname(__file__) + '/fixtures/categories.json'), 'r') as json_data:
                return Response(json.loads(json_data.read()))
        except Exception as e:
            logger.warn('Error while loading annotations categories %s', str(e))
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def get_connectors_detail(conn_id, annotation):
    connector = Connector.objects.get(id=conn_id)
    serializer = AnnotationDetailSerializer(connector)
    result = serializer.data
    if not result.get("operations", None):
        return {}
    result['operations'] = [
            {
                'operation': op.get('operation'),
                'description': op.get('description'),
                'title': op.get('title')
             }
            for op in result.get('operations') if op.get('annotation', None) == annotation
        ]
    return result


# function to add connector in annotation model
def add_connector_in_annotation(conn_id, info):
    operations = info.get('operations')
    for op in operations:
        if op.get('annotation'):
            if op.get('category', 'miscellaneous').lower() not in ['investigation', 'remediation', 'containment', 'utilities', 'miscellaneous']:
                category = 'miscellaneous'
            else:
                category = op.get('category', 'miscellaneous').lower()
            if not Annotation.objects.filter(name=op.get('annotation')).exists():
                logger.info('Annotation %s does not exist in available annotation list. Creating new annotation %s' % (
                op.get('annotation'), op.get('annotation')))
                serializer = AnnotationListSerializer(
                    data={'name': op.get('annotation').lower(),
                          'category': category
                          }
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
            annotation_model = Annotation.objects.get(name=op.get('annotation'))
            if annotation_model.category != category:
                logger.info('Category Mismatch: Annotation %s already exist with category %s. Skipping annotation '
                            'tagging for action %s' %(annotation_model.name, annotation_model.category, op.get('title'))
                            )
                continue
            if not annotation_model.system:
                annotation_model.category = category
            connectors = annotation_model.connectors
            try:
                connectors = ast.literal_eval(connectors)
            except:
                pass
            if conn_id not in connectors and op.get('visible', True):
                connectors.append(conn_id)
                annotation_model.connectors = connectors
            annotation_model.save()


# function to remove connector from annotation model
def remove_connector_from_annotation(conn_id, operations):
    for op in operations:
        if type(op) == dict and op.get('annotation'):
            if Annotation.objects.filter(name=op.get('annotation')).exists():
                annotation_model = Annotation.objects.get(name=op.get('annotation'))
                connectors = [conn for conn in annotation_model.connectors if conn != conn_id]
                if len(connectors) is 0:
                    annotation_model.delete()
                else:
                    annotation_model.connectors = connectors
                    annotation_model.save()
