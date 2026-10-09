# Regras operacionais de alerta (S15)

Estas regras são entrada para Prometheus/Alertmanager; a API apenas expõe
`/metrics` e não tenta enviar alerta durante uma requisição financeira. Os
limiares são valores iniciais de desenvolvimento e devem ser calibrados com o
benchmark da T4.5 e o volume real.

```yaml
groups:
  - name: baas-pme-api
    rules:
      - alert: BaaSHighServerErrorRate
        expr: sum(rate(baas_http_requests_total{status=~"5.."}[5m])) / clamp_min(sum(rate(baas_http_requests_total[5m])), 1) > 0.05
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "Mais de 5% das respostas são 5xx" }

      - alert: BaaSConnectorFailures
        expr: sum(rate(baas_external_connector_failures_total[10m])) > 0.1
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "Conector externo falhando continuamente" }

      - alert: BaaSSlowDatabaseLock
        expr: histogram_quantile(0.95, sum(rate(baas_database_lock_wait_seconds_bucket[10m])) by (le)) > 1
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "p95 de aquisição de lock acima de um segundo" }

      - alert: BaaSOutboxBacklog
        expr: baas_outbox_pending_events > 100
        for: 15m
        labels: { severity: warning }
        annotations: { summary: "Fila de notificações pendentes cresce" }

      - alert: BaaSOutboxDeliveryFailures
        expr: baas_outbox_retrying_events > 0
        for: 10m
        labels: { severity: warning }
        annotations: { summary: "Webhook de notificação não está aceitando entregas" }
```

CPU e memória não são métricas corretas da aplicação: devem ser coletadas do
container pelo cAdvisor ou pelo runtime equivalente. Exemplos de regra, quando
essas séries estiverem disponíveis, são `container_cpu_usage_seconds_total` e
`container_memory_working_set_bytes`; os limites devem respeitar o limite de
recursos definido no deploy. Nenhuma regra inclui e-mail, CPF/CNPJ, token,
`request_id`, IP, UUID ou payload.
