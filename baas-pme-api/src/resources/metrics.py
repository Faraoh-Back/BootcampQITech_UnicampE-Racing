from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST

from controllers.metrics_controller import MetricsController


class MetricsResource:
    def on_get(self) -> Response:
        return Response(
            content=MetricsController().render(),
            headers={"Content-Type": CONTENT_TYPE_LATEST},
        )
