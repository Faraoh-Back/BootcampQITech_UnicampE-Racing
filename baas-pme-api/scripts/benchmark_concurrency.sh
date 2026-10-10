#!/usr/bin/env bash
# Benchmark reproduzível da T4.5. Mede a carga S7c real, não uma simulação.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PYTHON_BIN="${PYTHON_BIN:-./.venv/bin/python}"
TEST_TARGET="tests/integration/transaction/test_advanced_concurrency.py::TestAdvancedConcurrency::test_cross_transfers_finish_without_deadlock_and_preserve_total_minus_fees"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="${BENCHMARK_OUTPUT_DIR:-artifacts/benchmarks/$RUN_ID}"
HEALTH_URL="http://${SERVER_LOCALHOST:-localhost}:${API_PORT:-3000}/health_check"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python do projeto não encontrado: $PYTHON_BIN" >&2
  echo "Crie o ambiente com: python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt" >&2
  exit 2
fi
if ! command -v docker >/dev/null; then
  echo "Docker é obrigatório para este benchmark." >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"
METADATA="$OUTPUT_DIR/environment.txt"
IDLE_STATS="$OUTPUT_DIR/docker-stats-idle.txt"
LOAD_STATS="$OUTPUT_DIR/docker-stats-load.ndjson"
PYTEST_OUTPUT="$OUTPUT_DIR/pytest-s7c.txt"
SUMMARY="$OUTPUT_DIR/summary.txt"

{
  echo "run_id=$RUN_ID"
  echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git_commit=$(git rev-parse HEAD 2>/dev/null || echo unavailable)"
  echo "git_dirty=$(git status --porcelain | wc -l | tr -d ' ')"
  echo "uname=$(uname -a)"
  echo "cpu_logical=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo unavailable)"
  echo "memory=$(free -h 2>/dev/null | awk '/Mem:/ {print $2}' || echo unavailable)"
  echo "docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo unavailable)"
  echo "compose_version=$(docker compose version --short 2>/dev/null || echo unavailable)"
  echo "python_version=$($PYTHON_BIN --version)"
  echo "test_target=$TEST_TARGET"
  echo "workload=5 repetitions x 40 crossed transfers; each transfer=100 cents; fee=100 cents"
  echo "timing=wall-clock around pytest; docker stats sampled while the test runs"
} > "$METADATA"

# A hora de teste precisa ser fixa para que regras noturnas não contaminem a
# comparação. Não removemos volumes: benchmark não deve apagar dados locais.
NIGHT_TIME_OVERRIDE=21:00 docker compose up -d --build
for _ in $(seq 1 30); do
  if curl --fail --silent "$HEALTH_URL" >/dev/null; then
    break
  fi
  sleep 1
done
curl --fail --silent "$HEALTH_URL" >/dev/null

docker compose ps > "$OUTPUT_DIR/compose-ps.txt"
docker compose images > "$OUTPUT_DIR/compose-images.txt"
docker stats --no-stream --format '{{json .}}' \
  "$(docker compose ps -q api)" "$(docker compose ps -q db)" "$(docker compose ps -q mock)" \
  > "$IDLE_STATS"

# Cada amostra é `docker stats --no-stream`; assim o arquivo fica em NDJSON
# limpo (o modo contínuo do Docker insere sequências de controle de terminal).
API_CONTAINER="$(docker compose ps -q api)"
DB_CONTAINER="$(docker compose ps -q db)"
MOCK_CONTAINER="$(docker compose ps -q mock)"
(
  while true; do
    SAMPLE_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    docker stats --no-stream --format '{{json .}}' \
      "$API_CONTAINER" "$DB_CONTAINER" "$MOCK_CONTAINER" \
      | sed "s|^|{\"sampled_at_utc\":\"$SAMPLE_TIME\",\"stats\":|; s|$|}|"
    sleep 1
  done
) > "$LOAD_STATS" 2> "$OUTPUT_DIR/docker-stats-load.stderr.log" &
STATS_PID=$!
cleanup() {
  kill "$STATS_PID" 2>/dev/null || true
  wait "$STATS_PID" 2>/dev/null || true
}
trap cleanup EXIT

START_NS="$(date +%s%N)"
set +e
"$PYTHON_BIN" -m pytest -q "$TEST_TARGET" | tee "$PYTEST_OUTPUT"
PYTEST_STATUS=${PIPESTATUS[0]}
set -e
END_NS="$(date +%s%N)"
cleanup
trap - EXIT

ELAPSED_MS=$(( (END_NS - START_NS) / 1000000 ))
{
  echo "finished_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "pytest_exit_code=$PYTEST_STATUS"
  echo "elapsed_ms=$ELAPSED_MS"
  echo "idle_stats_file=$IDLE_STATS"
  echo "load_stats_file=$LOAD_STATS"
  echo "pytest_output_file=$PYTEST_OUTPUT"
} > "$SUMMARY"

# Retorna a configuração normal, deixando o serviço pronto para uso manual.
docker compose up -d

cat "$SUMMARY"
if [[ "$PYTEST_STATUS" -ne 0 ]]; then
  exit "$PYTEST_STATUS"
fi
