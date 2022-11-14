def remote_agent_update_broadcast(agent_data, method, *args, **kwargs):
    pass


def allow_consume(message_json, *args, **kwargs):
    pass


class ConnectorAction:
    def __init__(self, *args, **kwargs):
        pass

    def _execute_connector_action(self, message_json, *args, **kwargs):
        pass

    def _execute_connector_health_check(self, message_json, destination_id, source_id, request_id, *args, **kwargs):
        pass

    def _execute_connector_agent_check(self, message_json, destination_id, source_id, request_id, *args, **kwargs):
        pass

    def _execute_connector_action_health_check_ack(self, message_json, destination_id, source_id, request_id, *args, **kwargs):
        pass

    def _execute_agent_health_check_ack(self, message_json, destination_id, source_id, request_id, *args, **kwargs):
        pass

    def _resume_remote_connector_agent_workflow(self, message_json, *args, **kwargs):
        pass

    def _handle_connector_install(self, message_json, destination_id, source_id, *args, **kwargs):
        pass

    def _handle_connector_update(self, message_json, destination_id, source_id, *args, **kwargs):
        pass

    def _handle_connector_uninstall(self, message_json, destination_id, source_id, *args, **kwargs):
        pass

    def _execute_connector_config_actions(self, message_json, destination_id, source_id, method, *args, **kwargs):
        pass

    def receiveRemoteConnectorExecutionRequest(self, message, *args, **kwargs):
        pass

    def _execute_agent_upgrade(self, data, destination_id, source_id, *args, **kwargs):
        pass

    def _execute_agent_upgrade_ack(self, message_json, destination_id, source_id, *args, **kwargs):
        pass

    def _execute_agent_collect_logs(self, message_json=None, destination_id=None, source_id=None, *args, **kwargs):
        pass

    def _execute_agent_collect_logs_ack(self, message_json, destination_id, source_id, *args, **kwargs):
        pass

    def _remote_agent_update_reciever(self, message_json, destination_id, source_id, *args, **kwargs):
        pass

    def receiveRemoteInstanceUpdateRequest(self, message, *args, **kwargs):
        pass

    def receiveRemoteConnectorInstructionRequest(self, message, *args, **kwargs):
        pass

    def _save_or_update_tenant_details(self, tenant, *args, **kwargs):
        pass

    def _save_or_update_agent_details(self, agent, tenants_uuid=None, old_data=None, *args, **kwargs):
        pass

    def _handle_disconnected_agent(self, agent, *args, **kwargs):
        pass

    def _delete_tenant_details(self, data, *args, **kwargs):
        pass

    def _delete_agent_details(self, data, *args, **kwargs):
        pass

    def receiveAgentRequestIntraCyOPs(self, message, *args, **kwargs):
        pass

    def receiveRemoteCHAPIResponse(self, message, *args, **kwargs):
        pass

