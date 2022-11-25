from connectors.core.connector import Connector, get_logger

from .add_comment_to_alert import add_comment_to_alert
from .alerts_trigger import alerts_trigger
from .get_alert import get_alert
from .get_events import get_events
from .health_check import check
from .update_alert_status import update_alert_status

logger = get_logger("sekoiaio")


class SekoiaIO(Connector):
    def execute(self, config, operation, params, **kwargs):
        supported_operations = {
            "alerts_trigger": alerts_trigger,
            "update_alert_status": update_alert_status,
            "get_events": get_events,
            "add_comment_to_alert": add_comment_to_alert,
            "get_alert": get_alert,
        }
        return supported_operations[operation](config, params)

    def check_health(self, config: dict) -> str:
        return check(config)
