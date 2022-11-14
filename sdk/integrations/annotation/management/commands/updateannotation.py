""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from django.core.management.base import BaseCommand
from annotation.views import remove_connector_from_annotation, add_connector_in_annotation
from annotation.serializer import AnnotationDetailSerializer
from connectors.models import Connector


class Command(BaseCommand):

    help = 'Update annotation'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str)
        parser.add_argument('version', type=str)

    def handle(self, *args, **options):
        name = options.get('name')
        version = options.get('version')
        try:
            connnector_object = Connector.objects.get(name=name, version=version)
            serializer = AnnotationDetailSerializer(connnector_object)
            result = serializer.data
            remove_connector_from_annotation(result.get('id'), result.get('operations'))
            add_connector_in_annotation(result.get('id'), result)
        except:
            self.stdout.write(self.style.ERROR('Failed to update the annotation'))
        self.stdout.write(self.style.SUCCESS('Successfully updated annotation'))

