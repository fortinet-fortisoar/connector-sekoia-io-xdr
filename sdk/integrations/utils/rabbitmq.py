""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import json, logging, pika


from django.conf import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisher:
    def __init__(self, connection=None):
        logger.info('Creating new connection before publish')
        self.connection = create_rabbitmq_connection(raise_ex=True)
        self.exchange_config = {
            'exchange_name': 'texchange.cyops.sdk',
            'exchange_type': 'topic',
            'durable': True,
            'passive': False,
            'auto_delete': False,
            'internal': False
        }

    def create_rmq_exchange(self, *args, **kwargs):
        channel = self.connection.channel()
        channel.exchange_declare(**self.exchange_config)
        channel.close()

    def publish(self, exchange_name, routing_key, body=None, content_type=None, retry_count=settings.PUBLISH_MESSAGE_RETRY_COUNT, delivery_mode=2):
        for i in range(0, retry_count):
            try:
                if body and isinstance(body, dict):
                    body = json.dumps(body)
                if self.connection and self.connection.is_closed == True:
                    logger.error('Creating new connection before publish')
                    self.connection = create_rabbitmq_connection(raise_ex=True)
                channel = self.connection.channel()
                channel.basic_publish(exchange=exchange_name,
                                routing_key=routing_key,
                                properties=pika.BasicProperties(content_type=content_type, delivery_mode=delivery_mode),
                                body=body
                                )
                channel.close()
                break
            except pika.exceptions.ChannelClosed as e:
                if e.reply_code == 404:
                    # Create exchange
                    self.create_rmq_exchange()
                    continue
                logger.exception('Error with RMQ server, check RMQ server status %s', str(e))
                logger.error('Could not publish message. Retry attempt %s', str(i))
            except pika.exceptions.ConnectionClosed as e:
                logger.exception('Error with RMQ server, check RMQ server status %s', str(e))
                logger.error('Could not publish message. Retry attempt %s', str(i))
            except Exception as e:
                logger.exception('Error while publishing massage to rabbitmq %s', str(e))
                logger.error('Could not publish message. Retry attempt %s', str(i))
            finally:
                if self.connection:
                    self.connection.close()


def create_rabbitmq_connection(raise_ex=False):
    try:
        logger.info('Reading rabbitmq config file')
        config_data_dict = settings.ALL_CONFIG.config
        credentials = pika.PlainCredentials(config_data_dict.get('cyops.rabbitmq.user'),
                                            config_data_dict.get('cyops.rabbitmq.password'))
        params = pika.ConnectionParameters(host=config_data_dict.get('cyops.rabbitmq.host'),
                                           port=int(config_data_dict.get('cyops.rabbitmq.port')),
                                           virtual_host=config_data_dict.get('cyops.rabbitmq.vhost'),
                                           credentials=credentials,
                                           connection_attempts=settings.CONNECTION_RETRY_COUNT,
                                           retry_delay=settings.CONNECTION_RETRY_DELAY,
                                           )
        connection = pika.BlockingConnection(params)
        logger.info('RabbitMQ connection established successfully')
        return connection
    except Exception as e:
        logger.exception("Error occurred while establishing RabbitMQ connection\n  ERROR :: {0}".format(str(e)))
        if raise_ex:
            raise ValueError({'message': "Error occurred while establishing RabbitMQ connection\n  ERROR :: {0}".format(str(e)), 'hide_trace': True})
