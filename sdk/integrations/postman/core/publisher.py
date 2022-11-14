class Publisher:
    def __init__(self, config, connection=None, *args, **kwargs):
        pass

    def _create_connection(self, tenant_id, *args, **kwargs):
        pass

    def publish(self, message, tenant_id=None, content_type=None, delivery_mode=None, *args, **kwargs):
        pass

