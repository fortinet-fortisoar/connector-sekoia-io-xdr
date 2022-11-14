import json
from django.conf import settings
from utils.rabbitmq import RabbitMQPublisher


def publish_install_ack(routing_key, conn_object, status, source_id, destination_id, command):
    routing_key = 'route.integration.action.remoteconnectorinstructionrequest'
    rmq = RabbitMQPublisher()
    publish_data = {
        'data': conn_object,
        'destinationId': destination_id,
        'status': status,
        'sourceId': source_id,
        'action': settings.connector_install_ack,
        'command': command
    }
    rmq.publish("texchange.cyops.integration",
                routing_key,
                body=json.dumps(publish_data),
                content_type="application/json"
                )
