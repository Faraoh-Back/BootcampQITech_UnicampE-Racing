# Cobertura de Testes e Erros por Rota

> Revisão de entrega: 2026-10-10. Esta é a fonte de contagem/evidência atual,
> não uma alegação de cobertura de 100% de linhas ou de todas as combinações
> possíveis. As rotas são de um serviço modular, com contratos de infraestrutura
> executados separadamente dos testes estritamente HTTP.

**Enquadramento aprovado: garantias verificadas e limitações conhecidas.**
A regra de antecipação com líquido positivo foi aprovada após esta validação;
está documentada em DECISOES 3.5.1 e aguarda implementação/testes em P0.4.
Os resultados abaixo não demonstram uma recusa que ainda não foi implementada.

## Consolidação documental — 10/10/2026

Os guias foram reunidos nos destinos do [índice da documentação](README.md#consolidação-dos-guias--10102026),
reduzindo cinco arquivos Markdown sem descartar conteúdo. Foram acrescentadas
duas guardas: preservação das seções/históricos nos documentos canônicos e
resolução dos links locais/âncoras Markdown. Ambas falharam antes da migração;
a segunda também identificou dois links já quebrados no guia histórico de setup,
corrigidos ao reuni-lo em HISTORICO.

| Verificação desta rodada documental | Resultado |
|---|---|
| Guardas estáticas na `.venv` da API | **12 passed, 196 deselected**, 0.13 s |
| Coleta da suíte, sem executar cenários HTTP/SQL | **208 testes coletados**: 12 estáticos + 170 HTTP + 26 de infraestrutura |
| Artefatos regenerados | RFC com quatro páginas e apresentação com dez; sem overflow, DER e hashes conferidos pelas guardas |
| Preservação | Textos migrados comparados com as fontes anteriores; seção 9.5 do plano mantida literalmente |

Não houve mudança de código da API, DDL, regras financeiras, workflow ou carga
de benchmark. A suíte HTTP/infraestrutura e o benchmark **não foram reexecutados
nesta consolidação**: suas evidências permanecem na execução isolada abaixo.
Não apresentar a coleta de 208 testes como uma nova execução completa aprovada.

## Validação final da entrega em snapshot isolado

Executada em **2026-10-10 07:30:27–07:33:26 UTC**, por
`bash scripts/validate_delivery.sh --snapshot`: clone local com as alterações
de trabalho, venv/banco novos, Compose exclusivo e portas 13000/15432/11080.
Base `524c7608ba305978bae7c97ece7348b8961c8a6a`, 44 entradas modificadas/novas
na origem. Não é clone remoto do commit publicado nem teste humano em VM virgem.
Foram acrescentadas quatro guardas de entrega à revisão anterior de 202 testes;
nenhum comportamento financeiro/DDL ou item 9.5 foi implementado nesta rodada.

| Execução | Resultado |
|---|---|
| Suíte completa em venv nova | **206 passed in 61.55s** |
| API estritamente HTTP | **170 passed**, 51.58 s; 36 deselected |
| Contratos de infraestrutura | **26 passed**, 9.06 s; 180 deselected |
| Guardas estáticas | **10 passed**, 1.10 s; 196 deselected |
| Benchmark S7c separado | **5 passed in 7.14s**; parede **7,506 s**; 200 operações |
| Métricas | GET `/metrics` aprovado; exposition salva após a suíte e antes do benchmark |
| Compilação/dependências | compileall sem erro; pip check sem incompatibilidade na venv nova |
| Container API | uid=100(user), não-root; API/DB healthy e mock Up |
| Artefatos PDF | RFC com quatro páginas; apresentação com dez; DER vetorial, fonte e SHA-256; revisão visual pelo agente |
| Cleanup isolado | exit_code=0; só containers/rede/volumes descartáveis dessa execução removidos |
| Ambiente original | Containers originais saudáveis, mesmos IDs; banco original não foi alvo das suítes |

Artefatos: `baas-pme-api/artifacts/delivery/20261010T073026Z/`, ignorados pelo
Git, com ambiente/pip-freeze, resultados/JUnit, metrics.prom e benchmark.
Reprodução e confirmações humanas/externas em [ENTREGA](entrega/ENTREGA.md).
As durações não são SLO; a diferença para execuções anteriores não prova ganho
de desempenho. O mesmo host/Docker e caches de imagem foram reutilizados.

As novas guardas conferem seções/rotas no modelo oficial, todas as entidades e
relações do DER, PDF/páginas/hashes e que P0.4 não aparece como implementada.
Seu Red foi executado antes dos artefatos: quatro falhas por arquivos ainda
ausentes; Green com dez guardas. O teste de fumaça do MockServer foi corrigido
após reproduzir porta publicada 11080 versus escuta interna 1080. Falhas
intermediárias de artefato/script foram corrigidas e não são resultado final
verde nem defeito financeiro escondido; registro em ENTREGA.

## Revisão anterior de 10/10/2026 — 202 testes (preservada)

Executado em 2026-10-10, com Python de `baas-pme-api/.venv`, API real no
Compose e `NIGHT_TIME_OVERRIDE=21:00`. Partiu-se de 155 testes aprovados;
foram acrescentados 47 casos líquidos e reescrita a jornada de ponta a ponta.

| Execução | Resultado |
|---|---|
| Suíte completa final: `pytest tests -q` | **202 passed in 102.75s** |
| API estritamente HTTP: `-m api_blackbox` | **170 passed**, 89.26 s |
| Contratos de infraestrutura: `-m infrastructure_contract` | **26 passed**, 14.12 s |
| Guardas estáticas: `-m static_guard` | **6 passed**, 0.26 s, após a revisão final dos documentos |
| Carga canônica S7c | **5 passed in 11.48s**; 200 transferências, parede 12,381 s |
| Compilação | `compileall -q src tests` concluído sem erro |
| Compatibilidade de dependências | `pip check`: No broken requirements found |
| Integridade do diff | `git diff --check` sem erro |
| Containers finais | API/banco healthy, MockServer Up; API `uid=100(user)`, não-root; `pip check` da imagem sem incompatibilidade |

As durações de execuções separadas não somam necessariamente a duração do
conjunto. Cada categoria tem dependências/estado próprio; execute-as
sequencialmente. HTTP inclui casos legados selecionáveis por `legacy`.
O benchmark contém somente transferências cruzadas, não toda a concorrência
S7c. Recursos/ambiente e artefatos estão em BENCHMARK.

| Rota / Endpoint | Código QIT | Status HTTP | Descrição do Cenário | Arquivo de Teste |
|---|---|---|---|---|
| **Segurança / Global** | `Sucesso` | 204 | Healthcheck responde corretamente | `tests/integration/test_healthcheck.py` |
| **Segurança / Global** | `QIT000002` | 403 | `INTERNAL-TOKEN` ausente ou inválido | `tests/integration/test_smoke.py` |
| **Segurança / Global** | `QIT000404` | 404 | Caminho HTTP inexistente | `tests/integration/test_healthcheck.py` |
| **Segurança / Global** | `QIT000405` | 405 | Método HTTP não permitido | `tests/integration/test_healthcheck.py` |
| `POST /customer` | `Sucesso` | 201 | Cliente criado com sucesso | `tests/integration/customer/test_customer.py` |
| `POST /customer` | `QIT000001` | 400 | Payload fora do schema | `tests/integration/customer/test_customer.py` |
| `POST /customer` | `QIT001003` | 409 | Documento (CPF/CNPJ) duplicado | `tests/integration/customer/test_customer.py` |
| `POST /customer` | `QIT001004` | 409 | E-mail duplicado | `tests/integration/customer/test_customer.py` |
| `POST /customer` | `QIT001010` | 422 | CPF/CNPJ com dígitos inválidos | `tests/integration/customer/test_customer.py` |
| `GET /customer/{customer_key}` | `Sucesso` | 200 | Consulta de cliente existente | `tests/integration/customer/test_customer.py` |
| `GET /customer/{customer_key}` | `QIT001001` | 404 | Cliente não encontrado | `tests/integration/customer/test_customer.py` |
| `POST /account` | `Sucesso` | 201 | Conta criada com sucesso | `tests/integration/account/test_account.py` |
| `POST /account` | `QIT000001` | 400 | Payload fora do schema | `tests/integration/account/test_account.py` |
| `POST /account` | `QIT001001` | 404 | `customer_key` não existe | `tests/integration/account/test_account.py` |
| `GET /account/{account_key}` | `Sucesso` | 200 | Consulta de conta existente | `tests/integration/account/test_account.py` |
| `GET /account/{account_key}` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/account/test_account.py` |
| `PUT /account/{account_key}/block` | `Sucesso` | 200 | Conta bloqueada com sucesso | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/block` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/block` | `QIT001019` | 409 | Transição de status inválida | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/cancel` | `Sucesso` | 200 | Conta cancelada com sucesso | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/cancel` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/cancel` | `QIT001019` | 409 | Transição de status inválida | `tests/integration/account/test_account_lifecycle.py` |
| `POST /account/{account_key}/transaction` | `Sucesso` | 201 | Depósito/Saque/Transferência efetuada | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT000001` | 400 | Payload inválido ou tipo incorreto | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT001018` | 400 | Header `Idempotency-Key` ausente | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT001002` | 404 | Conta de origem/destino inexistente | `tests/integration/transaction/test_transfer.py` |
| `POST /account/{account_key}/transaction` | `QIT001006` | 409 | Conta bloqueada ou cancelada | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT001008` | 409 | Idempotency Key reutilizada com dados distintos | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT001005` | 422 | Saldo insuficiente | `tests/integration/transaction/test_transaction_concurrency.py` |
| `POST /account/{account_key}/transaction` | `QIT001007` | 422 | Limite noturno excedido | `tests/integration/transaction/test_night_limit.py` |
| `POST /account/{account_key}/transaction` | `QIT001012` | 422 | Origem e destino iguais em transferência | `tests/integration/transaction/test_transfer.py` |
| `GET /account/{account_key}/transaction/{transaction_key}` | `Sucesso` | 200 | Consulta de transação concluída | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transaction/{transaction_key}` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transaction/{transaction_key}` | `QIT001011` | 404 | Transação inexistente ou de outra conta | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transactions` | `Sucesso` | 200 | Extrato paginado retornado | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transactions` | `QIT000001` | 400 | Parâmetros de consulta inválidos | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transactions` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/transaction/test_transaction_statement.py` |
| `POST /account/{account_key}/billing-plan` | `Sucesso` | 201 | Plano de boletos gerado com sucesso | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan` | `QIT000001` | 400 | Payload inválido | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan` | `QIT001017` | 422 | Vencimento inicial no passado | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan` | `QIT001009` | 502 | Indisponibilidade do conector externo | `tests/integration/billing_plan/test_billing_plan.py` |
| `GET /account/{account_key}/billing-plan/{plan_key}` | `Sucesso` | 200 | Consulta do plano e status dos boletos | `tests/integration/billing_plan/test_billing_plan.py` |
| `GET /account/{account_key}/billing-plan/{plan_key}` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/billing_plan/test_billing_plan.py` |
| `GET /account/{account_key}/billing-plan/{plan_key}` | `QIT001013` | 404 | Plano inexistente ou de outra conta | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `Sucesso` | 201 | Reajuste aplicado com sucesso | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT000001` | 400 | Payload/Índice inválido | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT001013` | 404 | Plano inexistente ou de outra conta | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT001014` | 409 | Reajuste/Lote 2 já aplicado previamente | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT001009` | 502 | Conector externo (BCB/Boletos) indisponível | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/credit-advance` | `Sucesso` | 201 | Antecipação de crédito concluída | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT000001` | 400 | Payload inválido | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001018` | 400 | Header `Idempotency-Key` ausente | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001015` | 404 | Boleto inexistente ou de outra conta | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001006` | 409 | Conta não aprovada | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001008` | 409 | Idempotência com payload conflitante | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001016` | 409 | Boleto não elegível (não PENDING / já antecipado) | `tests/integration/credit_advance/test_credit_advance.py` |

---

## Observações sobre Erros Legados (`sample_entity`)

- **`QIT002001` a `QIT002004` e `QIT000010`**: Presentes nos arquivos de `tests/integration/sample_entity/`. São exclusivos das entidades de demonstração e não fazem parte das rotas e regras de negócio de produção do ecossistema BaaS PME.

---

## Entregas transversais e evolução comercial

| Rota / comportamento | Código / resultado | Evidência de teste |
|---|---|---|
| `POST /user`, `/auth/login`, `/auth/refresh`, `/auth/logout` | sessão, rotação, revogação, `QIT001020`–`QIT001023` | `tests/integration/auth/test_auth.py` |
| `GET /audit-events`, `/checkpoint` | cadeia SHA-256, append-only, checkpoint | `tests/integration/audit/test_audit.py` |
| `GET /metrics` | métricas sem PII e erros/latência/locks | `tests/integration/metrics/test_metrics.py` |
| Worker de outbox | lease, retry, entrega idempotente | `tests/integration/outbox/test_outbox.py` |
| Timeout/retry PostgreSQL | `QIT001024`, `QIT001025`; não repetir `422` | `tests/integration/timeouts/test_timeouts.py`, `tests/integration/transaction/test_transient_retry.py` |
| `POST /pricing-policy` | preço PME, fallback, nova versão, snapshots | `tests/integration/pricing/test_pricing_policy.py` |
| `POST /risk-policy` | `QIT001026`, `QIT001027`, teto diário concorrente | `tests/integration/risk_policy/test_risk_policy.py` |
| `POST /account/{key}/quote` | preço/risco vigente, expiração informativa e recálculo | `tests/integration/quote/test_quote.py` |
| `/policy-change-request` | draft, submissão, outro OWNER aprova, autoaprovação `QIT001029` | `tests/integration/policy_change_request/test_maker_checker.py` |
| Jornada PME | cobrança própria, antecipação única, crédito/tarifa no extrato | `tests/integration/credit_advance/test_receivables_flow.py`, `tests/test_pme_journey.py` |
| Guarda R1 | testes de produto não importam módulos internos `src/` | `tests/test_r1_guard.py` |

## Complemento do catálogo: códigos transversais e legado

Cada código de `DECISOES.md` tem cenário que o provoca: o núcleo está na
tabela inicial; os códigos restantes estão abaixo. A existência de um cenário
por código **não** prova cada código em cada rota nem toda a matriz de papéis.

| Código | HTTP | Rota / cenário | Teste que o provoca |
|---|---|---|---|
| `QIT001020` | 401 | JWT inválido; refresh reutilizado; proposta sem JWT | `auth/test_auth.py`, `policy_change_request/test_policy_contract.py` |
| `QIT001021` | 401 | Login com senha incorreta ou maior que 72 bytes UTF-8 | `auth/test_auth.py`, `auth/test_password_contract.py` |
| `QIT001022` | 403 | PME alheia/papel proibido em conta, cotação ou proposta | `auth/test_auth.py`, `quote/test_quote_authorization.py`, `policy_change_request/test_policy_contract.py` |
| `QIT001023` | 409 | E-mail de usuário duplicado | `auth/test_auth.py` |
| `QIT001024` | 503 | Transação com lock PostgreSQL retido por outra sessão | `timeouts/test_timeouts.py` (infraestrutura) |
| `QIT001025` | 503 | Deadlock/serialização persistente por SQLSTATE sintético | `transaction/test_transient_retry.py` (infraestrutura) |
| `QIT001026` | 409 | Produto desabilitado na política vigente | `risk_policy/test_risk_policy.py`, `policy_change_request/test_policy_governance.py` |
| `QIT001027` | 422 | Teto de valor, quantidade ou consumo diário excedido | `risk_policy/test_risk_policy.py`, `risk_policy/test_risk_atomicity.py` |
| `QIT001028` | 404 | Proposta inexistente na submissão/aprovação | `policy_change_request/test_policy_contract.py` |
| `QIT001029` | 409 | Autoaprovação, estado inválido, submissão por outro criador ou segunda aprovação concorrente | `policy_change_request/test_maker_checker.py`, `policy_change_request/test_policy_governance.py` |
| `QIT000500` | 500 | Falha inesperada injetada no INSERT de lançamento; corpo sanitizado, sem retry nem efeito financeiro | `transaction/test_transient_retry.py` (infraestrutura) |
| `QIT000010` | 400 | Intervalo invertido de datas na listagem legada | `sample_entity/test_sample_entities.py` (infraestrutura/legado) |
| `QIT002001` | 404 | Entidade legada inexistente | `sample_entity/test_sample_entity_get.py` |
| `QIT002002` | 409 | Alteração de entidade legada em estado final | `sample_entity/test_sample_entity_update.py` |
| `QIT002003` | 422 | Idade abaixo do mínimo no legado | `sample_entity/test_sample_entity_create.py` |
| `QIT002004` | 422 | Data impossível no legado | `sample_entity/test_sample_entity_create.py` |

Os caminhos abreviados nessa tabela são relativos a `tests/integration/`.
Há 39 códigos catalogados: 29 do produto, seis globais e quatro do legado.
`QIT000010` é um código global cujo cenário atual é do legado.

## Features e pipelines: o que a evidência comprova

| Feature / pipeline | Evidência e limite |
|---|---|
| S1–S2b: cadastro, conta e ciclo de vida | Sucesso/erros/UUID, eventos, bloqueio/cancelamento e impedimento de movimentação em conta não aprovada |
| S3–S6: depósito, saque, transferência, extrato e idempotência | Sinais do ledger, tarifa separada, saldo, 404 sem revelar lançamento de outra conta, paginação, replay, conflito e rollback |
| S7a–S7c: concorrência financeira | Saques disputando saldo, 40 transferências cruzadas, chave compartilhada, disputa entre saque/transferência e antecipação do mesmo lastro |
| S8–S10/S18: recebíveis | Lote 1/2, calendário de fim de mês, índice Decimal, erros offline do MockServer, propriedade/eligibilidade e antecipação única; não liquidação ou empréstimo |
| S11: identidade | Bcrypt, login, refresh rotativo, sessões múltiplas, logout, papéis e rejeição de senha acima de 72 bytes |
| S12: auditoria | Cadeia SHA-256 reconstruída por HTTP/checkpoint; trigger de UPDATE/DELETE verificada em contrato SQL; não proteção contra administrador |
| S13–S15: operação | Logs/métricas, isolamento de conta travada, timeout, interrupção do cliente, lease/retry de outbox; não stack de monitoramento instalado |
| S16: retry transacional | SQLSTATE `40P01` e `40001` injetados; nova tentativa tem um efeito; esgotamento/falha inesperada não grava saldo/ledger; regra de negócio não é repetida |
| S17/S19/S20: personalização | Precedência PME/padrão, versões/snapshots, tetos concorrentes, produto desabilitado, cotação informativa e autorização por PME |
| S21: maker-checker | Contrato aninhado estrito de preço/risco, segregação criador/aprovador, estado pendente não aplicável, três corridas com dois aprovadores e uma versão publicada |
| Jornada integrada T5.1 | Dois OWNERs publicam preço, emitem/reajustam, cotam/antecipam, transferem/sacam, percorrem quatro páginas, reconciliam oito lançamentos com saldo e bloqueiam/cancelam com trilha auditável |
| Pipeline CI | Compose/build → liveness → compileall → static_guard → api_blackbox → infrastructure_contract → logs na falha → cleanup; validado localmente, não execução remota do Actions nesta revisão |
| Consistência documental | Guardas estáticas de seções do modelo, todos os métodos/rotas registrados, códigos catalogados e 23 tabelas do produto no DER; não comparação completa de payloads/FKs nem validação visual de PDF |

## Revisão: correções com regressão comprovada

Foram reproduzidas dez falhas em 19 casos antes das correções de schema,
cotação e senha. O mesmo conjunto passou após implementá-las. Não se atribui
TDD retrospectivo ao histórico inteiro: o Red/Green aqui é da revisão.

- O JSON Schema agora exige `int` nativo, inclusive em políticas aninhadas:
  rejeita decimal JSON `10.0`, string e booleano antes de emissor/regra de negócio.
- Propostas reutilizam os schemas estritos de preço/risco, incluindo UUID e
  proibição de `customer_key` dentro da política.
- Cotações com JWT exigem vínculo/papel sobre a conta; JWT inválido não é ignorado.
- Bcrypt não recebe senha acima de 72 bytes UTF-8; não há truncamento silencioso.
- Helpers HTTP têm timeout e não imprimem falha esperada ao interpretar 204.
  O `.env` é carregado antes de helpers que capturam a credencial.
- Parâmetros de retry foram ligados ao Compose; constantes/env de preço
  obsoletos foram removidos. Tarifas continuam vindo do banco.
- requests 2.32.4 corrige o aviso específico de credenciais `.netrc`
  [do mantenedor](https://github.com/psf/requests/security/advisories/GHSA-9hjg-9r4m-mvj7).
  Isso não certifica a ausência de outras vulnerabilidades.

## Garantias verificadas e limitações conhecidas: lacunas pendentes

| Prioridade | Achado / próxima prova necessária | Plano |
|---|---|---|
| P0 | Recusa de antecipação com tarifa >= bruto: regra aprovada, implementação/testes pendentes. Cotação de transferência, limites BIGINT e índices <= -100% ainda exigem especificação/validação segura | P0.3/P0.4 |
| P0 | Ledger/eventos/snapshots ainda não têm proteção append-only SQL equivalente à auditoria; saldo é projeção sem rotina de reconciliação | P0.1/P0.2 |
| P1 | Token interno tem autoridade ampla, JWT é opcional fora de propostas, cadastro de OWNER e políticas diretas podem contornar segregação | P1.4/P1.8 |
| P1 | Faltam controles produtivos de abuso de login, rotação de chaves e gestão administrativa de sessões | P1.5 |
| P1 | Emissão externa antes da validação final pode criar boleto órfão; billing não tem idempotência de cliente e lote 2 faz I/O com lock de plano | P1.2 |
| P1 | Preço/risco contêm regras em repositories e auditoria executa SQL em utils | P1.7 |
| P1 | Orçamento de 15 s não é deadline global; virada diária de risco usa data do runtime; timestamps sem offset e bootstrap sem migrations | P1.3/P1.9 |
| P1 | Lease de lote de outbox pode vencer durante publicação; ack obsoleto não deve contar entrega; faltam dead-letter e operação de recuperação | P1.6 |
| P1 | Exportação completa da auditoria, cadeia global serializada e paginação offset não são provas de escalabilidade/snapshot estável sob novas escritas | P1.10 |
| P1 | Erros inesperados e exceções de bibliotecas podem escrever parâmetros SQL/URLs em traceback; logs normais sem body não equivalem a sanitização universal | P1.11 |
| P1 | Backup/restore e retomada financeira após perda de dados não foram comprovados pela revisão | P1.12 |
| P2 | PDFs foram gerados/revistos pelo agente; aceite do time, clone remoto/Linux novo por outra pessoa e execução remota do CI ainda não foram comprovados | T5.3/T5.5/P2.2 |
| P2 | Combinações de papel/rota/estado, expiração/calendário e quedas não são exaustivas; faltam capacidade sustentada e alertas efetivamente exercitados | P2.3/P2.4 |

Esses itens estão documentados como lacunas, não mascarados por testes verdes.
Também faltam testes de todas as transições/papéis em cada rota, expiração
temporal controlada de JWT/cotação, todos os modos de queda de worker/conector
e capacidade sustentada. R1 é defendida pela suíte HTTP; os testes que injetam
SQLSTATE são contratos de infraestrutura, não reprodução de um deadlock real.
