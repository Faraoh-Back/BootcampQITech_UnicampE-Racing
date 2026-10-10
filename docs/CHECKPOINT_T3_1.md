# Checkpoint T3.1 — registro histórico e reconciliação atual

Data da revisão original: 2026-10-03. Registro acumulado de S11–S21 e
T4.5/T4.75: 2026-10-10. A RFC vigente é 3.2; este checkpoint não substitui
os contratos de DECISOES nem as evidências datadas de COBERTURA.

O enquadramento atual é **garantias verificadas e limitações conhecidas**.
A regra de líquido positivo na antecipação foi aprovada, mas a validação
permanece pendente P0.4; os marcos de testes abaixo não a comprovam.

## Escopo conferido

| Área | Evidência revisada | Resultado |
|---|---|---|
| Rotas entregues | `src/app.py`, resources, schemas e testes HTTP | Cliente, conta, bloqueio/cancelamento, transações, extrato, plano de boletos, reajuste, antecipação, cadastro de usuário e sessões estão registrados na RFC com os caminhos e métodos existentes. |
| Erros | `errors/`, handlers, `DECISOES.md` e testes | O marco até S15 tinha `QIT001001`–`QIT001024`; S16–S21 acrescentaram `QIT001025`–`QIT001029`. Todos preservam `{ title, description, translation, code }`; catálogo/matriz atuais em DECISOES/COBERTURA. |
| DER e DDL | Models SQLAlchemy e `database/database.sql` | Chaves, FKs, restrições, lote 2, `adjustment_rate`, ledger, eventos e idempotência correspondem ao diagrama. |
| Dinheiro e concorrência | Controller/repository de transação e S7a–S7c | O saldo é protegido por `FOR NO KEY UPDATE` com recarga da entidade; há provas repetidas cinco vezes para saques, 40 transferências cruzadas, idempotência em 10 threads, antecipação simultânea e disputa do último saldo. |
| Conectores | Controllers de plano, conectores e MockServer | A referência deriva do UUID do plano/lote; uma nova chamada de criação gera UUID novo. Erros externos retornam `QIT001009` sem escrita local parcial nos casos testados; emissão externa antes de falha local não é compensada. |
| Identidade e autorização | DDL, `AuthController`, RBAC e testes HTTP | S11 entrega bcrypt, JWT curto, refresh rotativo por até 8 horas, sessões múltiplas revogáveis e papéis por PME. O `INTERNAL-TOKEN` permanece como fronteira serviço-a-serviço; um JWT, quando fornecido, exige papel sobre a conta. |
| Auditoria verificável | DDL, gatilho, exportação HTTP e testes | S12 grava `audit_event` na mesma transação do domínio, encadeia eventos por SHA-256 sob trava transacional, exporta a cadeia/checkpoint e recusa `UPDATE`/`DELETE` no banco. |
| Observabilidade | Logs, registry Prometheus, rota e testes HTTP | S13 entrega logs JSON correlacionados, conta/usuário mascarados, `/metrics` interno e métricas seguras de HTTP, QIT, conectores, replay, locks e sessões. |
| Timeouts e retentativa | Configuração, conectores, PostgreSQL, handlers e testes | S14 limita conexão/leitura/lock/comando, sem deadline global. S16 repete a operação idempotente inteira em nova sessão somente para deadlock/serialização; falhas de negócio não são repetidas. |
| Outbox e alertas | DDL, worker, métricas, MockServer e testes | S15 grava outbox com bloqueio/cancelamento no mesmo commit; worker usa lease/backoff e chave de evento. Entrega é pelo menos uma vez. Regras de alerta são exemplos, não stack instalado; CPU/memória são amostras do runtime. |
| Benchmark de concorrência | Script, S7c, `docker stats` e `BENCHMARK.md` | T4.5 reutiliza 5×40 transferências cruzadas da S7c, captura host/imagens/versões, amostra containers ociosos e sob carga e registra método de comparação. A referência de 6,753 s é contextual, não SLO. |
| Testes | Suíte HTTP, infraestrutura e guardas estáticas | O marco histórico após S15 foi `143 passed`; após S21, `155 passed`. Contagens atuais e regressões da revisão ficam exclusivamente em COBERTURA. A guarda de imports não transforma testes SQL/worker em caixa-preta HTTP. |
| Evolução e entrega | RFC 3.2, `DECISOES.md` e R5 | Jornada, matriz, README e separação da pipeline foram revisados; regra de líquido positivo está aprovada, com implementação pendente. PDF/legibilidade, clone independente e apresentação continuam pendentes. |

## Itens deliberadamente futuros

- **T5.3:** o [modelo oficial](bootcamp-rfc-modelo.md) existe e a RFC segue suas seções. Geração/revisão visual do PDF de 2–4 páginas continuam pendentes.
- **R4.5 e R4.75:** entregues. Além do Gate 3, preço/risco versionados, cotação informativa e propostas maker-checker possuem contratos, snapshots/auditoria e testes HTTP. O benchmark foi reexecutado no fechamento; seus artefatos e números contextualizados estão em `BENCHMARK.md`.

O checkpoint registra evidências por marco, não uma aprovação universal.
9.5 do plano contém hardening e também lacunas concretas de economia,
autorização e integração externa. Elas não são anuladas pelo resultado verde
dos cenários já cobertos. Consulte COBERTURA para a avaliação atual e DECISOES
para limites de imutabilidade, IDs administrativos, preços e JWT opcional.
