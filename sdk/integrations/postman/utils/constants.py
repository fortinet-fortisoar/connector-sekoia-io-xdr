import time

install_connector = 'install-connector'
install_connector_ack = 'install-connector-ack'

uninstall_connector = 'uninstall-connector'
uninstall_connector_ack = 'uninstall-connector-ack'

update_connector = 'update-connector'
update_connector_ack = 'update-connector-ack'

configure_connector = 'configure-connector'
configure_connector_ack = 'configure-connector-ack'

configuration_update = 'configure-update-connector'
configuration_update_ack = 'configure-update-connector-ack'

configuration_removed = 'configuration-removed'
configuration_removed_ack = 'configuration-removed-ack'

health_check = 'health-check'
health_check_ack = 'health-check-ack'

agent_health_check = 'agent-health-check'
agent_health_check_ack = 'agent-health-check-ack'

agent_upgrade_request = 'agent-upgrade-request'
agent_upgrade_request_ack = 'agent-upgrade-request-ack'

remote_agent_update_request = 'remote-agent-update-request'

collect_app_log = 'collect-app-log'
collect_app_log_ack = 'collect-app-log-ack'

log_path = '/var/log/cyops/cyops-integrations'
zip_path = '/opt/cyops-integrations/integrations/log'

execute_action = 'execute_action'
execute_action_ack = 'execute_action_ack'

agent_iri_prefix = '/api/3/agents/'

remote_node_unreachable = '/api/3/picklists/135030fa-1b0b-453d-9fed-df9be5d4397f'
confighealth_remote_connected = '/api/3/picklists/ab6a1713-9280-4619-9fbd-7694edad2159'

awaiting_remote_node_connection = '/api/3/picklists/b5566a53-7af5-48f6-9dbd-5bf5fc9f432b'

upgrade_script_path = '/opt/cyops-integrations/'

connection_verified_config_status = '23987b58-da1b-4905-a97c-5348829b5339'

UPGRADE_LOG_PATH = '/var/log/cyops/agent_upgrade_' + str(int(time.time())) + '.log'

cert_auth = '/api/3/picklists/6fe3b5bb-1c50-455e-b58a-7c2154f18643'