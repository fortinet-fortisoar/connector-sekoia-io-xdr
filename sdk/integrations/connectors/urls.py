""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from connectors import views

connector_detail = views.ConnectorDetail.as_view({
    'get': 'retrieve',
    'post': 'retrieve_post',
    'put': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    url(r'^connectors/$', views.ConnectorList.as_view({'get': 'list'})),
    url(r'^connectors/(?P<name>[^/]+)/(?P<version>[^/]+)/$', connector_detail),
    url(r'^connectors/agents/(?P<name>[^/]+)/(?P<version>[^/]+)/$', views.ConnectorDetail.as_view({'post': 'agents'})),
    url(r'^connectors/(?P<pk>[^/]+)/$', connector_detail),
    url(r'^connectors/help/doc/(?P<pk>[^/]+)/$', views.ConnectorDetail.as_view({'get': 'help'})),
    url(r'^connectors/healthcheck/(?P<name>[^/]+)/(?P<version>[^/]+)/$', views.ConnectorHealth.as_view()),
    url(r'^connectors/dependencies_check/(?P<name>[^/]+)/(?P<version>[^/]+)/$', views.ConnectorDependencies.as_view()),
    url(r'^agent-heartbeat/(?P<agent>[^/]+)/$', views.AgentHealth.as_view()),
    url(r'^execute/$', views.ConnectorExecute.as_view()),
    url(r'^import-connector/(?P<filename>[^/]+)/$', views.ConnectorImport.as_view()),
    url(r'^install-connector/$', views.ConnectorInstall.as_view()),
    url(r'^set/proxy/$', views.ProxySettingView.as_view()),
    url(r'^connector_details/$', views.ConnectorList.as_view({'post': 'connector_actions'})),
    url(r'^connector_details/(?P<connector>[^/]+)/(?P<version>[^/]+)/$', views.ConnectorList.as_view({'post': 'connector_action_details'})),
    url(r'^connector_output_schema/(?P<connector>[^/]+)/(?P<version>[^/]+)/$', views.ConnectorOperationView.as_view({'post': 'operation_output_schema'})),
    url(r'^connectors/operations/(?P<operation_id>[^/]+)/roles/', views.OperationRoleView.as_view())
]

urlpatterns = format_suffix_patterns(urlpatterns)
