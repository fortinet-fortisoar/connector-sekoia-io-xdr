""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """

from django.conf.urls import include, url
from rest_framework import routers
from rest_framework.urlpatterns import format_suffix_patterns
from connector_development.views import *

router = routers.DefaultRouter()

urlpatterns = [
    url(r'^connector/development/templates/$', ConnectorTemplates.as_view()),
    url(r'^connector/development/list/$', ConnectorDevelopment.as_view({"post": "list"})),
    url(r'^connector/development/entity/$', ConnectorDevelopment.as_view({"post": "create_connector"})),
    url(r'^connector/development/entity/(?P<id>\d+)/$', ConnectorDevelopment.as_view({"post": "connector_details"})),
    url(r'^connector/development/entity/(?P<id>\d+)/view/$', ConnectorDevelopment.as_view({"post": "connector_details_view"})),
    url(r'^connector/development/entity/(?P<id>\d+)/files/$', ConnectorDevelopment.as_view({"put": "create_connector_files", "post": "retrieve_connector_files"})),
    url(r'^connector/development/entity/(?P<id>\d+)/delete/files/$', ConnectorDevelopment.as_view({"post": "delete_connector_files"})),
    url(r'^connector/development/entity/(?P<id>\d+)/rename/files/$', ConnectorDevelopment.as_view({"post": "rename_connector_files"})),
    url(r'^connector/development/entity/(?P<id>\d+)/publish/$', ConnectorDevelopment.as_view({"post": "publish"})),
    url(r'^connector/development/entity/(?P<id>\d+)/folders/$', ConnectorDevelopment.as_view({"put": "create_connector_folder", "delete": "delete_connector_folder"})),
    url(r'^connector/development/entity/(?P<id>\d+)/rename/folders/$', ConnectorDevelopment.as_view({"post": "rename_connector_files"})),
    url(r'^connector/development/entity/(?P<id>\d+)/delete/folders/$', ConnectorDevelopment.as_view({"post": "delete_connector_folder"})),
    url(r'^connector/development/', include(router.urls)),
    url(r'^connector/development/entity/(?P<id>\d+)/export/$', ConnectorDevelopment.as_view({"get": "export"})),
]

# urlpatterns = format_suffix_patterns(urlpatterns)
