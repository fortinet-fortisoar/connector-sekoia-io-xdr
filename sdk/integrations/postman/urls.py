from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from postman import views

urlpatterns = [
    url(r'^agent-installer/$', views.AgentInstallerView.as_view()),
    url(r'^agent-action/$', views.AgentActionView.as_view()),
    url(r'^action-log/purge/$', views.ActionExecutionView.as_view({'post': 'purge'})),
]

urlpatterns = format_suffix_patterns(urlpatterns)
