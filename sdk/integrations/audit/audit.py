def publish_audit_log(data, exchange_name=None, routing_key=None, retry_count=None, *args, **kwargs):
    pass


def publish_audit_and_notify(data, method, module, exchange, routing_key, title=None, request=None, rbac_info=None, entity_uuid=None, *args, **kwargs):
    pass


def audit_connector_action(audit_data, status, *args, **kwargs):
    pass


def audit_connector_functions(data, operation, status, module=None, audit_message=None, rbac_info=None, *args, **kwargs):
    pass


