#!/usr/bin/env bash
# T5.5: checkout/snapshot novo + venv nova + Compose isolado, nunca o banco local.
set -euo pipefail
# O corpo é carregado integralmente antes de executar; editar o arquivo de
# origem durante uma validação não muda os comandos que ela ainda leria.
validate_delivery() {
SOURCE_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")/../.." rev-parse --show-toplevel)"
MODE="${1:---snapshot}"
if [[ "$MODE" != --snapshot && "$MODE" != --head ]]; then
  echo 'Uso: bash scripts/validate_delivery.sh [--snapshot|--head]' >&2
  exit 2
fi
if [[ "$MODE" == --snapshot ]]; then
  for task_artifact in RFC_FINAL.pdf APRESENTACAO.pdf; do
    if [[ ! -s "$SOURCE_ROOT/docs/entrega/$task_artifact" ]]; then
      echo "Artefato ausente: docs/entrega/$task_artifact. Gere os PDFs antes da validação." >&2
      exit 2
    fi
  done
fi
TASK_DIR="$(mktemp -d /tmp/baas-delivery-XXXXXXXX)"
CHECKOUT="$TASK_DIR/repository"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_DIR="$SOURCE_ROOT/baas-pme-api/artifacts/delivery/$RUN_ID"
mkdir -p "$REPORT_DIR"
git clone --local --no-hardlinks "$SOURCE_ROOT" "$CHECKOUT"
if [[ "$MODE" == --snapshot ]]; then
  # Copia mecânica dos arquivos de trabalho rastreados/não ignorados. Não
  # transporta .git, .env, .venv, caches, node_modules ou artefatos ignorados.
  # É snapshot sobre clone local, NÃO clone do commit publicado no GitHub.
  (
    cd "$SOURCE_ROOT"
    git ls-files -z --cached --others --exclude-standard |
      while IFS= read -r -d '' task_file; do
        case "$task_file" in
          .git/*|*/.env|.env|*.pem|*.key|*.p12|*.pfx) continue ;;
        esac
        if [[ -f "$task_file" || -L "$task_file" ]]; then
          printf '%s\0' "$task_file"
        fi
      done |
      tar --null -T - -cf -
  ) | tar -xf - -C "$CHECKOUT"
fi
cd "$CHECKOUT/baas-pme-api"
export COMPOSE_FILE="$CHECKOUT/baas-pme-api/docker-compose.yml"
unset COMPOSE_PROFILES
export COMPOSE_PROJECT_NAME="baas-delivery-${RUN_ID,,}-${TASK_DIR##*-}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME,,}"
export API_PORT="${DELIVERY_API_PORT:-13000}"
export DB_PORT="${DELIVERY_DB_PORT:-15432}"
export MOCK_PORT="${DELIVERY_MOCK_PORT:-11080}"
export INTERNAL_TOKEN=default_token
export JWT_SECRET=local-development-jwt-secret-change-before-production
export APP_ENV=local SERVER_LOCALHOST=127.0.0.1 MOCK_HOST=127.0.0.1
export DATABASE_URL="postgresql+psycopg2://bootcamp:bootcamp@127.0.0.1:$DB_PORT/bootcamp"
export NIGHT_TIME_OVERRIDE=21:00
export BANKSLIP_API_URL=http://mock:1080 CENTRAL_BANK_API_URL=http://mock:1080
export NOTIFICATION_WEBHOOK_URL=http://mock:1080/notifications
export DATABASE_TRANSIENT_RETRY_MAX_ATTEMPTS=2 DATABASE_TRANSIENT_RETRY_BASE_DELAY_MS=25
export DATABASE_LOCK_TIMEOUT_MS=2000 DATABASE_STATEMENT_TIMEOUT_MS=10000 REQUEST_TIMEOUT_SECONDS=15
export NIGHT_START=20:00 NIGHT_END=06:00 NIGHT_LIMIT_CENTS=100000 TIMEZONE=America/Sao_Paulo

{
  echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "mode=$MODE"
  echo "base_commit=$(git -C "$SOURCE_ROOT" rev-parse HEAD)"
  echo "source_dirty_entries=$(git -C "$SOURCE_ROOT" status --porcelain | wc -l | tr -d ' ')"
  echo "checkout=$CHECKOUT"
  echo "compose_project=$COMPOSE_PROJECT_NAME"
  echo "ports_api_db_mock=$API_PORT,$DB_PORT,$MOCK_PORT"
  echo "host=$(uname -srmo)"
  echo "docker=$(docker version --format '{{.Server.Version}}')"
  echo "compose=$(docker compose version --short)"
} > "$REPORT_DIR/environment.txt"

STARTED=0
cleanup() {
  task_exit=$?
  trap - EXIT
  task_cleanup=not_started
  if [[ "$STARTED" == 1 ]]; then
    docker compose ps > "$REPORT_DIR/compose-ps.txt" || true
    if [[ "$task_exit" != 0 ]]; then
      # Não exportar tracebacks potencialmente sensíveis como evidência pública.
      echo 'Falha: consulte os logs locais antes de compartilhar diagnóstico.' >&2
    fi
    # Projeto explicitamente criado aqui, banco descartável desta validação.
    if docker compose -p "$COMPOSE_PROJECT_NAME" down -v --remove-orphans; then
      task_cleanup=removed
    else
      task_cleanup=failed
      task_exit=1
    fi
  fi
  {
    echo "finished_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "exit_code=$task_exit"
    echo "checkout_preserved=$CHECKOUT"
    echo "isolated_environment_cleanup=$task_cleanup"
  } > "$REPORT_DIR/result.txt"
  echo "Relatório: $REPORT_DIR"
  echo "Checkout/venv preservados: $CHECKOUT"
  exit "$task_exit"
}
trap cleanup EXIT

python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements-dev.txt
./.venv/bin/python -m pip freeze > "$REPORT_DIR/pip-freeze.txt"
./.venv/bin/python -m pip check | tee "$REPORT_DIR/pip-check.txt"
docker compose config --quiet
STARTED=1
docker compose up -d --build
for _ in $(seq 1 60); do
  if curl --fail --silent "http://127.0.0.1:$API_PORT/health_check" >/dev/null; then break; fi
  sleep 1
done
curl --fail --silent "http://127.0.0.1:$API_PORT/health_check" >/dev/null
docker compose exec -T api id | tee "$REPORT_DIR/api-user.txt"
./.venv/bin/python -m compileall -q src tests
./.venv/bin/python -m pytest tests -q -m static_guard --junitxml="$REPORT_DIR/static.xml" | tee "$REPORT_DIR/static.txt"
# Este script já possui seu Compose descartável. O opt-in external evita
# iniciar um segundo ambiente principal; fronteiras de relógio ainda são isoladas.
./.venv/bin/python -m pytest tests -q --test-environment=external -m api_blackbox --junitxml="$REPORT_DIR/http.xml" | tee "$REPORT_DIR/http.txt"
./.venv/bin/python -m pytest tests -q --test-environment=external -m infrastructure_contract --junitxml="$REPORT_DIR/infrastructure.xml" | tee "$REPORT_DIR/infrastructure.txt"
./.venv/bin/python -m pytest tests -q --test-environment=external --junitxml="$REPORT_DIR/full.xml" | tee "$REPORT_DIR/full.txt"
curl --fail --silent -H 'INTERNAL-TOKEN: default_token' "http://127.0.0.1:$API_PORT/metrics" > "$REPORT_DIR/metrics.prom"
# A rotina existente já registra hardware, idle/load CPU/RAM e carga S7c.
BENCHMARK_OUTPUT_DIR="$REPORT_DIR/benchmark" bash scripts/benchmark_concurrency.sh
}
validate_delivery "$@"
