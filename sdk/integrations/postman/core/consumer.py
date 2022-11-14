def start_consumer(agent_id, *args, **kwargs):
    pass


class Consumer:
    def __init__(self, config, *args, **kwargs):
        pass

    def __enter__(self, *args, **kwargs):
        pass

    def __exit__(self, *args, **kwargs):
        pass

    def prepare_consumers(self, queue_config, message_received_callback, *args, **kwargs):
        pass

    def start_consuming(self, *args, **kwargs):
        pass

    def stop_consuming(self, *args, **kwargs):
        pass

    def _create_exchange(self, channel, *args, **kwargs):
        pass

    def _create_queue(self, channel, queue_config, *args, **kwargs):
        pass

    def _create_connection(self, *args, **kwargs):
        pass

    def _consume_message(self, channel, method, properties, body, *args, **kwargs):
        pass

