import json

from django.conf import settings
from rest_framework.permissions import BasePermission

from postman.models import Agent


class IsAgentAuthenticated(BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET']:
            agent_id = request.query_params.get('agent')
            if agent_id and agent_id != settings.SELF_ID:
                return False
            return True
        if request.method in ['POST', 'PUT']:
            agent_id = request.query_params.get('agent', settings.SELF_ID)
            team_uuid = []
            if request.data.get('rbac_info', {}).get('teams'):
                team_uuid = json.loads(request.data.get('rbac_info', {}).get('teams'))
            if not agent_id or agent_id == settings.SELF_ID or not team_uuid:
                return True
            agent_instance = Agent.objects.filter(agent_id=agent_id).first()
            if agent_instance:
                return agent_instance.team.filter(uuid__in=team_uuid).exists()
        return True
