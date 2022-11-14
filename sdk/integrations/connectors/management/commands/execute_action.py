import json
import sys
import base64
from django.core.management.base import BaseCommand
from connectors.views import ConnectorExecute

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--payload', help='base64/json payload', dest='payload', type=str, required=True, default=None)
        parser.add_argument('--connector-name', help='Connector name. For eg. smtp', dest='connector_name', type=str, required=False, default=None)
        parser.add_argument('--connector-action', help='Connector action/operation. For eg. send_email', dest='action_name', type=str, required='--connector-name' in sys.argv, default=None)
        parser.add_argument('--connector-version', help='Connector version. For eg. latest or 2.0.0', dest='connector_version', type=str, required=False, default="latest")

    def _prepare_payload(self, final_payload, *args, **kwargs):
        if kwargs['connector_name'] is not None:
            final_payload['connector'] = kwargs['connector_name']
        if kwargs['action_name'] is not None:
            final_payload['operation'] = kwargs['action_name']
        if kwargs['connector_version'] is not None:
            final_payload['version'] = kwargs['connector_version']
    
    def handle(self, *args, **kwargs):
        payload = kwargs['payload']
        is_json_payload = True
        # First check whether the payload is JSON format or not. This is required where
        # we want to simply put the payload which is not complicated. Converting to base64 for simple
        # payload will be unnecessary for caller.
        try:
           payload = json.loads(payload)
        except Exception as e:
            is_json_payload = False

        if not is_json_payload:
            try:
                payload = base64.b64decode(payload)
                payload = json.loads(payload)
            except Exception as e:
                self.stderr.write(self.style.ERROR(str(e)))
                exit(1)

        self._prepare_payload(payload, *args, **kwargs)
        ConnectorExecute.execute_connector_operation(payload)
