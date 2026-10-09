"""Worker executável para publicar notificações depois do commit."""

import argparse
import time

from constants import DATABASE_URL, OUTBOX_POLL_INTERVAL_SECONDS
from utils.logger import setup_logging
from utils.outbox import OutboxPublisher


def main() -> None:
    parser = argparse.ArgumentParser(description="Publica eventos pendentes da outbox.")
    parser.add_argument("--once", action="store_true", help="Processa no máximo um lote e encerra.")
    parser.add_argument("--batch-size", type=int, default=10, help="Máximo de eventos por lote.")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    # O worker não serve HTTP nem assina JWT; exigir as credenciais da API
    # aqui o acoplaria à camada errada. Para publicar, ele só precisa do banco.
    if not DATABASE_URL:
        parser.error("DATABASE_URL must be configured")
    setup_logging()
    publisher = OutboxPublisher()
    while True:
        publisher.publish_once(args.batch_size)
        if args.once:
            return
        time.sleep(OUTBOX_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
