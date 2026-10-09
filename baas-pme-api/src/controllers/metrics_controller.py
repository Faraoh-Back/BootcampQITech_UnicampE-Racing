from controllers.base_controller import BaseController
from repositories.user_repository import UserRepository
from utils.metrics import render_metrics, set_active_sessions


class MetricsController(BaseController):
    """Atualiza gauges derivados do banco e exporta o registry Prometheus."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.user_repository = UserRepository(self.context)

    def render(self) -> bytes:
        set_active_sessions(self.user_repository.count_active_sessions())
        return render_metrics()
