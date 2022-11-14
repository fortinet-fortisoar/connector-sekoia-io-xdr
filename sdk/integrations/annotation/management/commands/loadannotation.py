""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from django.core.management.base import BaseCommand
from annotation.models import Annotation
from annotation.fixtures.system_annotation import annotations
from annotation.serializer import AnnotationListSerializer


class Command(BaseCommand):

    help = 'Load Annotation'

    def handle(self, *args, **options):
        try:
            for annotation in annotations:
                if not Annotation.objects.filter(name=annotation.get('name')).exists():
                    serializer = AnnotationListSerializer(
                        data={'name': annotation.get('name'),
                              'description': annotation.get('description', ''),
                              'category': annotation.get('category', 'miscellaneous'),
                              'system': annotation.get('system', True)
                              }
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
        except Exception as e:
            return self.stdout.write(self.style.ERROR('Failed to update the annotation: %s' %str(e)))
        self.stdout.write(self.style.SUCCESS('Successfully updated annotation'))

