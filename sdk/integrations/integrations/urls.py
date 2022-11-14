""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from django.conf.urls import include, url
from rest_framework import routers

from annotation.views import AnnotationView
from connectors.views import ConnectorConfigurationView, ConnectorOperationView
from postman.views import TenantView, AgentView, ActionExecutionView

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'annotation', AnnotationView, basename='annotation')
router.register(r'configuration', ConnectorConfigurationView, basename='configuration')
router.register(r'operation', ConnectorOperationView, basename='operation')
router.register(r'tenant', TenantView, basename='tenant')
router.register(r'agent', AgentView, basename='agent')
router.register(r'remote-action-execution', ActionExecutionView, basename='remote-action-execution')

urlpatterns = [
    url(r'^integration/', include('connectors.urls')),
    url(r'^integration/', include('connector_development.urls')),
    url(r'^integration/', include(router.urls)),
    url(r'^integration/', include('postman.urls')),
]
