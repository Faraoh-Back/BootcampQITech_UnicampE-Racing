# Checkpoint T3.1 — RFC 2.1

Data da revisão: 2026-10-03.

## Escopo conferido

| Área | Evidência revisada | Resultado |
|---|---|---|
| Rotas entregues | `src/app.py`, resources, schemas e testes HTTP | Cliente, conta, bloqueio/cancelamento, transações, extrato, plano de boletos e reajuste estão registrados na RFC com os caminhos e métodos existentes. |
| Erros | `errors/`, handlers, `DECISOES.md` e testes | Os códigos implementados são `QIT001001`–`QIT001014` e `QIT001017`–`QIT001019`, conforme cada fluxo entregue. Todos preservam `{ title, description, translation, code }`. |
| DER e DDL | Models SQLAlchemy e `database/database.sql` | Chaves, FKs, restrições, lote 2, `adjustment_rate`, ledger, eventos e idempotência correspondem ao diagrama. |
| Dinheiro e concorrência | Controller/repository de transação e S7a | O saldo é protegido por `FOR NO KEY UPDATE` com recarga da entidade; os testes exercitam 2 e 10 saques simultâneos cinco vezes cada. |
| Conectores | Controllers de plano, conectores e MockServer | Lote 1 e lote 2 usam referências determinísticas; erros externos retornam `QIT001009` sem escrita parcial. |
| Testes | Suíte HTTP e guardião R1 | `pytest -q`: 101 testes aprovados após S7b. |

## Itens deliberadamente futuros

- **S10:** rota de antecipação, `QIT001015` e `QIT001016` ainda não existem no código.
- **S7c:** concorrência avançada de transferências, idempotência simultânea e antecipação.
- **T5.3:** PDF oficial da RFC. O plano já o posterga para a entrega final; não há template ou gerador no repositório neste momento.

Com esses itens marcados como planejados na RFC, não há divergência conhecida entre a documentação e o código entregue.
