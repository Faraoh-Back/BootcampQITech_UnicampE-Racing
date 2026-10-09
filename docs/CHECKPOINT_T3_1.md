# Checkpoint T3.1 — RFC 2.3

Data da revisão original: 2026-10-03. Atualização de S11: 2026-10-09.

## Escopo conferido

| Área | Evidência revisada | Resultado |
|---|---|---|
| Rotas entregues | `src/app.py`, resources, schemas e testes HTTP | Cliente, conta, bloqueio/cancelamento, transações, extrato, plano de boletos, reajuste, antecipação, cadastro de usuário e sessões estão registrados na RFC com os caminhos e métodos existentes. |
| Erros | `errors/`, handlers, `DECISOES.md` e testes | Os códigos `QIT001001`–`QIT001023` estão materializados conforme cada fluxo entregue. Todos preservam `{ title, description, translation, code }`. |
| DER e DDL | Models SQLAlchemy e `database/database.sql` | Chaves, FKs, restrições, lote 2, `adjustment_rate`, ledger, eventos e idempotência correspondem ao diagrama. |
| Dinheiro e concorrência | Controller/repository de transação e S7a–S7c | O saldo é protegido por `FOR NO KEY UPDATE` com recarga da entidade; há provas repetidas cinco vezes para saques, 40 transferências cruzadas, idempotência em 10 threads, antecipação simultânea e disputa do último saldo. |
| Conectores | Controllers de plano, conectores e MockServer | Lote 1 e lote 2 usam referências determinísticas; erros externos retornam `QIT001009` sem escrita parcial. |
| Identidade e autorização | DDL, `AuthController`, RBAC e testes HTTP | S11 entrega bcrypt, JWT curto, refresh rotativo por até 8 horas, sessões múltiplas revogáveis e papéis por PME. O `INTERNAL-TOKEN` permanece como fronteira serviço-a-serviço; um JWT, quando fornecido, exige papel sobre a conta. |
| Testes | Suíte HTTP e guardião R1 | `pytest -q`: 130 testes aprovados após S11. |
| Evolução planejada | RFC 2.3, `DECISOES.md` e R4.5 | Auditoria verificável, observabilidade, timeouts, outbox e benchmark continuam como roadmap, sem serem declarados implementados. |

## Itens deliberadamente futuros

- **T5.3:** PDF oficial da RFC. O plano já o posterga para a entrega final; não há template ou gerador no repositório neste momento.
- **R4.5 remanescente:** auditoria append-only, métricas, política de timeout, alertas e benchmark. O Gate 3 é opcional e posterior ao núcleo entregue no Gate 2; S11 já foi concluída.

Com esses itens marcados como planejados na RFC e nas decisões, não há divergência conhecida entre a documentação e o código entregue.
