from .update_alert_status import update_alert_status
from .get_events import get_events
from .add_comment_to_alert import add_comment_to_alert
from .get_alert import get_alert
from .list_alerts import list_alerts
from connectors.core.connector import get_logger, Connector
from .health_check import check

logger = get_logger("sekoiaio")


class Sekoiaio(Connector):
    def execute(self, config, operation, params, **kwargs):
        supported_operations = {
            "update_alert_status": update_alert_status,
            "get_events": get_events,
            "add_comment_to_alert": add_comment_to_alert,
            "get_alert": get_alert,
            "list_alerts": list_alerts,
        }
        return supported_operations[operation](config, params)

    def check_health(self, config):
        return check(config)
