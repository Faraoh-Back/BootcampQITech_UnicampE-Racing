from controllers.base_controller import BaseController
from repositories.user_repository import UserRepository
from repositories.outbox_repository import OutboxRepository
from utils.metrics import render_metrics, set_active_sessions, set_outbox_state


class MetricsController(BaseController):
    """Atualiza gauges derivados do banco e exporta o registry Prometheus."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.user_repository = UserRepository(self.context)
        self.outbox_repository = OutboxRepository(self.session)

    def render(self) -> bytes:
        set_active_sessions(self.user_repository.count_active_sessions())
        set_outbox_state(*self.outbox_repository.metric_state())
        return render_metrics()
