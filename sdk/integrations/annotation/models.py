""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from django.db import models
from django.core.exceptions import ValidationError

from jsonfield import JSONField

class my_JSONField(JSONField):
    def value_to_string(self, obj):
        return self.value_from_object(obj)

import re


def is_valid_annotation_name(name, category=None):
    if not re.match('^[a-z0-9_]*$', name):
        raise ValidationError(
            'Annotation name %s is invalid.' %name
        )
    #commenting this for now to not fail connector's import due to category mismatch
    # if category and Annotation.objects.filter(name=name).exists() and Annotation.objects.get(name=name).category != category.lower():
    #     raise ValidationError(
    #         'Annotation with name %s already exist in category %s.' %(name, Annotation.objects.get(name=name).category)
    #     )


class Annotation(models.Model):
    """
    Annotation model
    """
    name = models.CharField(unique=True, max_length=100, validators=[is_valid_annotation_name])
    description = models.CharField(max_length=1000, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    system = models.BooleanField(default=False)
    connectors = my_JSONField(default=list)

    def __str__(self):
        return 'Annotation :: ' + self.name

