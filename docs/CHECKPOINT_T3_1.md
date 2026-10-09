# Checkpoint T3.1 — RFC 2.8

Data da revisão original: 2026-10-03. Atualizações de S11, S12, S13, S14, S15 e T4.5: 2026-10-09.

## Escopo conferido

| Área | Evidência revisada | Resultado |
|---|---|---|
| Rotas entregues | `src/app.py`, resources, schemas e testes HTTP | Cliente, conta, bloqueio/cancelamento, transações, extrato, plano de boletos, reajuste, antecipação, cadastro de usuário e sessões estão registrados na RFC com os caminhos e métodos existentes. |
| Erros | `errors/`, handlers, `DECISOES.md` e testes | Os códigos `QIT001001`–`QIT001024` estão materializados conforme cada fluxo entregue. Todos preservam `{ title, description, translation, code }`. |
| DER e DDL | Models SQLAlchemy e `database/database.sql` | Chaves, FKs, restrições, lote 2, `adjustment_rate`, ledger, eventos e idempotência correspondem ao diagrama. |
| Dinheiro e concorrência | Controller/repository de transação e S7a–S7c | O saldo é protegido por `FOR NO KEY UPDATE` com recarga da entidade; há provas repetidas cinco vezes para saques, 40 transferências cruzadas, idempotência em 10 threads, antecipação simultânea e disputa do último saldo. |
| Conectores | Controllers de plano, conectores e MockServer | Lote 1 e lote 2 usam referências determinísticas; erros externos retornam `QIT001009` sem escrita parcial. |
| Identidade e autorização | DDL, `AuthController`, RBAC e testes HTTP | S11 entrega bcrypt, JWT curto, refresh rotativo por até 8 horas, sessões múltiplas revogáveis e papéis por PME. O `INTERNAL-TOKEN` permanece como fronteira serviço-a-serviço; um JWT, quando fornecido, exige papel sobre a conta. |
| Auditoria verificável | DDL, gatilho, exportação HTTP e testes | S12 grava `audit_event` na mesma transação do domínio, encadeia eventos por SHA-256 sob trava transacional, exporta a cadeia/checkpoint e recusa `UPDATE`/`DELETE` no banco. |
| Observabilidade | Logs, registry Prometheus, rota e testes HTTP | S13 entrega logs JSON correlacionados, conta/usuário mascarados, `/metrics` interno e métricas seguras de HTTP, QIT, conectores, replay, locks e sessões. |
| Timeouts e retentativa | Configuração, conectores, PostgreSQL, handlers e testes HTTP | S14 aplica conexão/leitura de 1 s/5 s, orçamento de requisição de 15 s e `lock_timeout`/`statement_timeout` transacionais de 2 s/10 s. Falha externa é `502 QIT001009`; timeout de banco é `503 QIT001024`, ambos correlacionáveis por `request_id`. |
| Outbox e alertas | DDL, worker, métricas, MockServer e testes | S15 grava `outbox_event` com bloqueio/cancelamento no mesmo commit, publica após o commit por worker separado com lease e backoff, e entrega `event_key` como chave idempotente. Métricas e regras de alerta cobrem fila, 5xx, conector e lock; CPU/memória usam métricas do runtime. |
| Benchmark de concorrência | Script, S7c, `docker stats` e `BENCHMARK.md` | T4.5 reutiliza 5×40 transferências cruzadas da S7c, captura host/imagens/versões, amostra containers ociosos e sob carga e registra método de comparação. A referência de 6,753 s é contextual, não SLO. |
| Testes | Suíte HTTP e guardião R1 | `pytest -q`: 143 testes aprovados após S15. |
| Evolução planejada | RFC 2.8, `DECISOES.md` e R5 | A entrega final (cobertura, pipeline e PDF) continua como roadmap, sem ser declarada implementada. |

## Itens deliberadamente futuros

- **T5.3:** PDF oficial da RFC. O plano já o posterga para a entrega final; não há template ou gerador no repositório neste momento.
- **R4.5 remanescente:** nenhum item. O Gate 3 opcional está evidenciado; S11, S12, S13, S14, S15 e T4.5 foram concluídas.

Com esses itens marcados como planejados na RFC e nas decisões, não há divergência conhecida entre a documentação e o código entregue.
