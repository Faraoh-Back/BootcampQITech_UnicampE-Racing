# Plano de execução: BaaS PME (fatias verticais, horas e trilhas paralelas)

## 0. Como ler este plano

- **Horas** são horas-pessoa para alguém confortável com Python, FastAPI e SQL, já incluindo 0,5h de revisão cruzada por fatia. Se for a primeira vez de alguém com Docker, SQLAlchemy ou concorrência, multiplique as tarefas dessa pessoa por 1,5.
- **Rodadas** substituem datas. Uma rodada termina quando as três trilhas terminam. O tempo de relógio de uma rodada é o da trilha mais longa.
- **Trilhas A, B e C** são papéis para um time de 3. Com 2 pessoas ou 1, veja a seção 8.
- **Fatia vertical** é uma funcionalidade completa, da rota ao banco, entregue com teste. Nenhuma camada é construída "para depois".
- **Gate** é um ponto de verificação. Só se passa para a rodada seguinte com o gate verde.
- Fonte das restrições R1 a R8: os PDFs de estudo. Confira com o enunciado oficial.

### Regras de trabalho do time (valem para todas as tarefas)

1. `main` sempre verde: `docker compose down -v && NIGHT_TIME_OVERRIDE=21:00 docker compose up --build` e `pytest` passando antes de qualquer merge. O override reproduz o perfil determinístico do CI para a regra noturna.
2. Branch curta por fatia (`feat/s3-deposito-saque`). Pull request pequeno, revisado por outra pessoa.
3. Commits separados por cor do TDD: `test(S3): vermelho ...`, depois `feat(S3): verde ...`, depois `refactor(S3): ...`. O histórico do git é a prova do TDD.
4. Arquivos compartilhados são onde nascem os conflitos. Evite assim: um arquivo de erros por domínio (`errors/account_errors.py`, `errors/billing_errors.py`), rotas novas só no fim de `src/app.py`, e `database.sql` e `models` escritos uma vez só (T1.1 e T1.2).
5. Teste nunca importa nada de `src/` (R1). Existe um teste guardião para isso (T0.5).
6. Dinheiro é sempre inteiro em centavos, em todas as camadas (R6). Nenhum identificador numérico do banco sai em resposta (R5).

### Template de uma fatia vertical (use em todas as fatias S)

| Etapa | Fatia das horas | O que fazer |
|---|---|---|
| Vermelho | 25% | Escrever os testes de caixa-preta da fatia. Rodar. Confirmar que falham pelo motivo certo (assert, não "conexão recusada" nem rota 404 por typo). Commit. |
| Verde | 50% | Schema JSON, resource, controller, repository, DTO, erros. O mínimo para passar. Um único `session.commit()`, no controller. |
| Refatorar | 15% | Remover duplicação, nomes, conferir que o resource cabe em 3 linhas e que o repository não decide nada. |
| RFC | 10% | Atualizar a linha da rota, o DER e o fluxo em `docs/RFC.md` e subir a versão se o desenho mudou. |

---

## 1. Decisões que o time fecha em 15 minutos (T0.2 as registra)

| # | Decisão | Recomendação |
|---|---|---|
| D1 | Valores fixos | Tarifa de transferência 100 centavos; taxa de antecipação 3% com *half-up* em inteiros; limite noturno 100000 centavos por saque ou transferência. Tudo em variável de ambiente. |
| D2 | Índices do reajuste | O plano antigo diz IPCA/Selic, a RFC diz IPCA/IGPM. Selic não é índice de inflação: fique com **IPCA e IGPM**. |
| D3 | Ciclo de vida de conta | Adicionar `PUT /account/{account_key}/block` e `PUT /account/{account_key}/cancel` na S2b. Transições: `APPROVED → BLOCKED`, `APPROVED → CANCELLED` e `BLOCKED → CANCELLED`; `CANCELLED` é final. A API registra evento em toda transição e devolve `409 QIT001019` se ela não for permitida. |
| D4 | Antecipação | Lastreada em `bank_slip_keys` (como na RFC v2), não em valor livre. |
| D5 | Formato da taxa do índice | Percentual em string: `"4.83"` significa 4,83%, fator `1 + 4.83/100`. |
| D6 | Contratos dos mocks | BankSlip: `POST /bank-slips` com `{external_reference, installments:[{installment_number, amount, due_date}]}` responde `200 {bank_slips:[{installment_number, barcode}]}`. Banco Central: `GET /index/{IPCA\|IGPM}` responde `200 {index, accumulated_rate}`. |
| D7 | Eventos visíveis por HTTP | O R4 (nada que entrou deixa de existir) só é testável em caixa-preta se os eventos saírem na resposta. `GET /account/{key}` devolve `status_events` da conta; `GET .../billing-plan/{key}` devolve `status_events` de cada boleto (cada item com `status` e `event_datetime`). Atualize a RFC. |
| D8 | Janela noturna no ambiente de avaliação | A regra de negócio padrão permanece 20:00–06:00 em `America/Sao_Paulo`, com limite de 100000 centavos. O teste da S7b deve controlar relógio ou subir a API com configuração de ambiente própria; não deve depender da hora da banca. |
| D9 | `RestConnector` | Confirme no repositório se a classe existe. Se existir, herde dela; se não, use `requests` direto em `src/connectors/`. |

---

## 2. Visão geral das rodadas

| Rodada | Trilha A (núcleo financeiro) | Trilha B (conectores e extras) | Trilha C (qualidade e documentação) | Relógio |
|---|---|---|---|---|
| **R0** Fundação | T0.1, T0.2 | T0.1, T0.3, T0.4 | T0.1, T0.5 | ~4h |
| **R1** Dados | T1.1 DDL, T1.2 models | T1.3 conectores, T1.4 helper do MockServer | S1 Cliente | ~5h |
| **R2** Dinheiro | S2 Conta, S3 Depósito e saque | S8 Plano de boletos, T2.1 componente de idempotência | S2b Bloqueio, S4 Extrato e R8 | ~7h |
| **R3** Transferência | S5 Transferência e tarifa | S9 Reajuste (lote 2) | S7a Concorrência (saque), T3.1 Checkpoint da RFC | ~5h |
| **R4** Garantias | S6 Idempotência nas rotas, S7b Limite noturno | S10 Antecipação | S7c Concorrência (transferência, idempotência, antecipação) | ~6h |
| **R4.5** Evolução operacional | S11 Identidade e autorização, S14 timeouts | S13 Observabilidade, S15 notificações | S12 Auditoria verificável, T4.5 benchmark | ~19h |
| **R5** Entrega | T5.2, T5.4, T5.5, T5.7, T5.8 | T5.3, T5.6, T5.7, T5.8 | T5.1, T5.6, T5.7, T5.8, T5.9 | ~9h |

Relógio acumulado previsto: R0 4h, R1 9h, R2 16h, R3 21h, R4 27h, R4.5 46h, R5 55h. A R4.5 é uma expansão opcional de produção; o núcleo do desafio permanece pronto no Gate 2.

### Gates e linha de corte

- **Gate 0** (fim da R0): as três máquinas sobem `docker compose up` com tudo `healthy`, `pytest` verde nos testes de fumaça e o PDF de teste da RFC sai com o diagrama renderizado.
- **Gate 1** (fim da R2): cliente, conta, depósito, saque, extrato paginado e a R8 verdes; plano de boletos funcionando contra o MockServer.
- **Gate 2** (fim da R4): núcleo completo, testes de concorrência e idempotência verdes, extras integrados.
- **Gate 3** (fim da R4.5, opcional): autenticação, auditoria, métricas e timeouts possuem contrato, testes e evidência operacional reproduzível.
- **Linha de corte:** se ao fim de qualquer rodada o tempo gasto passar de 1,3 vezes o previsto, corte nesta ordem: **S10, depois S9, depois S8** (e os conectores). Declare o que saiu em "fora do escopo" na RFC e redistribua a trilha B para S6, S7 e testes. Um sistema menor, correto e testado vale mais que um ambicioso pela metade.

### Mapa do plano antigo para este

| Plano antigo | Onde está agora |
|---|---|
| Fase 1 (SQL, Docker) | T0.4, T1.1 |
| Fase 2 (models, DTOs, repositórios) | T1.2 e dentro de cada fatia |
| Fase 3 (schemas, middlewares) | dentro de cada fatia; middlewares conferidos em T0.1 e T0.5 |
| Fase 4 (controllers) | S1, S2, S2b, S3, S5, S6, S7b |
| Fase 5 (conectores, extras) | T1.3, S8, S9, S10 |
| Fase 6 (testes) | dentro de **toda** fatia (TDD), mais T5.1 e T5.2 |
| Fase 7 (RFC) | T0.3, T3.1, T5.3 (a RFC vive o projeto todo) |

---

## 3. Rodada 0: Fundação (~4h)

### T0.1 Subir a base na máquina de cada pessoa (A, B e C, 1h cada)
- **Depende de:** nada. **Paralelo com:** tudo da R0.
- **Fazer:**
  1. Clonar o repositório-base e criar o repositório do time (público no dia da entrega; privado até lá).
  2. `cp .env.example .env`, `docker compose up --build`, esperar `healthy`, abrir `/health_check`.
  3. Criar venv, `pip install -r requirements-dev.txt`, rodar `pytest`.
  4. Rodar `docker compose down -v` e subir de novo (é assim que o schema é reaplicado: o script em `/docker-entrypoint-initdb.d` só roda com o volume vazio).
  5. Ler o caminho completo do exemplo `sample_entity`: `app.py`, `resource`, `schema`, `controller`, `repository`, `model`, `dto`. Conferir que a ordem dos middlewares não será mexida.
  6. Registrar problemas de Docker na sua máquina (é aqui que eles aparecem, e não na véspera).
- **Pronto quando:** cada pessoa tem print do `docker compose ps` com tudo `healthy` e do `pytest` verde.

### T0.2 Decisões fixas e contratos (A, 1h, com 15 min do time todo)
- **Fazer:** criar `docs/DECISOES.md` com D1 a D9 acima, o **catálogo de erros** (código, status, nome, quando) e o **formato de resposta de cada rota** (campos e tipos). D10–D13 serão acrescentadas na R4.5 como decisões planejadas, sem antecipar contratos inexistentes. Esse arquivo é o contrato que permite as três trilhas trabalharem sem esperar umas pelas outras. **Atualização:** S11 materializou D10, seus schemas, rotas, erros e testes; D11–D13 continuam planejadas.
- **Pronto quando:** as três pessoas leram e disseram "ok" no PR.

### T0.3 [Postergado para a Entrega / R5] RFC no modelo oficial da QI Tech e PDF
- **Status:** Postergado para o fechamento (T5.3 na Rodada 5).
- **Fazer:** Na etapa final, adaptar a RFC diretamente no formato/template oficial fornecido pela QI Tech e gerar o PDF final conforme as diretrizes do desafio.


### T0.4 Compose, mock e variáveis de ambiente (B, 1,5h)
- **Fazer:**
  1. Adicionar o serviço `mock` (MockServer) ao `docker-compose.yml`. A imagem pode não ter `curl`; se o `healthcheck` for complicado, use `depends_on: condition: service_started` e faça os testes esperarem `PUT /mockserver/status`.
  2. Conferir `depends_on: db: condition: service_healthy` para a API e o multi-stage do `Dockerfile` com `USER` não-root (se já existir no base, não mexa).
  3. `.env.example` e `.env` com: `INTERNAL_TOKEN`, `BANKSLIP_API_URL`, `CENTRAL_BANK_API_URL` (ambos apontando para `http://mock:1080`), `TRANSFER_FEE_CENTS=100`, `ADVANCE_FEE_PERCENT=3`, `NIGHT_START`, `NIGHT_END`, `NIGHT_LIMIT_CENTS` (valores da D8).
- **Pronto quando:** `docker compose up` sobe `api`, `db` e `mock`, e `curl localhost:<porta>/health_check` responde `204`.

### T0.5 Infra de testes de caixa-preta (C, 2h)
- **Fazer:**
  - `tests/utils/request_generator.py`: classe que embrulha `requests` com URL base e `INTERNAL-TOKEN`, com um método por rota.
  - `tests/utils/payload_generator.py`: gerador de **CPF e CNPJ com dígitos verificadores válidos**, e-mail único com `uuid4`, nomes únicos. Sem isso os testes colidem entre execuções.
  - `tests/conftest.py`: `python-dotenv`, fixture que espera `/health_check`, fábricas `make_customer()` e `make_account()`.
  - `tests/test_r1_guard.py`: lê os arquivos de `tests/` com `ast` e falha se algum importar módulos de `src/`.
  - Testes de fumaça: `GET /` 200, `GET /health_check` 204, rota protegida sem token 403, com token errado 403.
- **Pronto quando:** com a API desligada os testes falham (vermelho); com ela de pé, passam. O teste guardião falha de propósito se você adicionar um `import` de `src` (teste e desfaça).

**Gate 0.**

---

## 4. Rodada 1: Dados (~5h)

### T1.1 DDL completo em `database/database.sql` (A, 2,5h)
- **Depende de:** T0.4. **Paralelo com:** T1.3, T1.4, S1 (parte vermelha).
- **Fazer:** as 12 tabelas do DER da RFC: `customer`, `account_status`, `account`, `account_status_event`, `idempotency_key`, `transaction`, `credit_advance`, `billing_plan`, `bank_slip_status`, `bank_slip`, `bank_slip_status_event` (e as de domínio que sobrarem). Detalhes que costumam esquecer:
  - `INSERT` dos enumeradores: `account_status` (PENDING, APPROVED, BLOCKED, CANCELLED) e `bank_slip_status` (PENDING, PAID, CANCELLED).
  - `document_number VARCHAR(18)` (o `CHAR(14)` do exemplo só cabe CPF; PME tem CNPJ).
  - `UNIQUE(account_id, scope, idempotency_key)` em `idempotency_key`; `UNIQUE(billing_plan_id, installment_number)` em `bank_slip`.
  - `CHECK (balance >= 0)`, `CHECK (amount <> 0)`, `CHECK (net_amount = gross_amount - fee_amount)`, `CHECK` do `type` do lançamento.
  - Índice `transaction(account_id, created_at DESC, id DESC)` para o extrato.
  - Todo `*_key` como `CHAR(36) NOT NULL UNIQUE`.
- **Pronto quando:** `docker compose down -v && up` aplica sem erro; `\d` no `psql` mostra tudo; um `INSERT` manual de saldo negativo é recusado pelo banco.

### T1.2 Models SQLAlchemy (A, 2h)
- **Depende de:** T1.1.
- **Fazer:** um model por tabela espelhando o SQL (tipos, `nullable`, FKs, `UniqueConstraint`), relacionamentos de status com `order_by` do evento. Sem `create_all`: o SQL é a fonte da verdade.
- **Pronto quando:** a API sobe; um script **descartável fora de `tests/`** consulta cada model sem erro.

### T1.3 Conectores externos (B, 3h)
- **Depende de:** T0.4, D6. **Paralelo com:** T1.1.
- **Fazer:** `BankSlipConnector.issue_batch(external_reference, installments)` e `CentralBankConnector.get_accumulated_rate(index_code)`. Regras: `timeout=5` obrigatório; qualquer falha (timeout, conexão, status diferente de 200, corpo que não é JSON, campo ausente) vira `ExternalConnectorError` (`502 QIT001009`); resposta interpretada com `json.loads(..., parse_float=Decimal)` (nunca `float`); URLs vêm de variável de ambiente. **Não envie o `INTERNAL-TOKEN` para API externa**: só para serviço interno cujo contrato exija.
- **Pronto quando:** um script descartável chama cada conector contra o mock rodando e cada falha vira a exceção certa. Os testes de verdade vêm nas fatias S8 a S10 (R1 proíbe teste que importe o conector).

### T1.4 Helper do MockServer para testes (B, 2h)
- **Fazer:** `tests/utils/mock_server.py`, usando `requests` na API do MockServer (`/mockserver/expectation`, `/mockserver/reset`, `/mockserver/verify`). Funções: `reset()`, `expect_bankslip_ok()`, `expect_bankslip_timeout()` (atraso maior que 5s), `expect_bankslip_status(500)`, `expect_bankslip_invalid_json()`, `expect_central_bank_rate(index, rate)`, `expect_central_bank_status(500)`, `verify_called(path, times)`.
- **Pronto quando:** cada expectativa foi confirmada com `curl` manual e o `reset()` limpa tudo entre testes.

### S1 Cliente (C, 4,5h)
- **Depende de:** T0.5 (vermelho já na R1), T1.1 e T1.2 (verde). **Paralelo com:** T1.1 a T1.4: escreva os testes primeiro.
- **Vermelho (testes):**
  - `POST /customer` 201 devolvendo só `customer_key` (R5: nenhum campo `id`).
  - 400 `QIT000001`: corpo vazio, JSON malformado, campo faltando, campo extra, tipo errado, máscara de documento errada.
  - 409 `QIT001003` documento repetido e 409 `QIT001004` e-mail repetido.
  - 422 `QIT001010` CPF e CNPJ com dígitos verificadores inválidos.
  - `GET /customer/{key}`: 200 com o formato combinado; 404 `QIT001001`.
  - 403 `QIT000002` sem token.
- **Verde:** `post_customer.json` com `additionalProperties: false`; utilitário de validação de CPF e CNPJ; erros; ordem do controller: validar documento (422), duplicado por documento (409), duplicado por e-mail (409), criar, DTO, `commit`.
- **Pronto quando:** todos os testes acima verdes, `main` verde, RFC atualizada.

---

## 5. Rodada 2: Dinheiro (~7h)

### S2 Conta (A, 3h)
- **Depende de:** S1 e T1.2.
- **Vermelho:** `POST /account` 201 com `account_key`, `customer_key`, `status` `APPROVED`, `balance` 0 (inteiro); 404 `QIT001001`; 400 em corpo inválido; duas contas para o mesmo cliente funcionam; `GET /account/{key}` 200 (com `status_events` mostrando `PENDING` e depois `APPROVED`, D7) e 404 `QIT001002`.
- **Verde:** `post_account.json`; `AccountRepository` com `create`, `get_by_key`, `get_by_key_for_update` e **`get_by_keys_for_update` com `ORDER BY id`** (já pensando na transferência); `update_status` que grava o evento. O controller cria a conta e grava os dois eventos (`PENDING`, `APPROVED`), com status atual `APPROVED`.
- **Pronto quando:** testes verdes e `status_events` visível por HTTP (isso prova o R4).

### S3 Depósito e saque (A, 4h)
- **Depende de:** S2.
- **Vermelho:** `POST /account/{key}/transaction` com `DEPOSIT` e `WITHDRAWAL`: 201 com `transaction_key`, `type`, `amount`, `balance`; saldo conferido por `GET /account`; saque acima do saldo: 422 `QIT001005` e saldo inalterado; `amount` 0, negativo, `10.5`, `10.0`, string: 400; `type` inválido: 400; `destination_account_key` presente em depósito: 400; `TRANSFER` sem destino: 400 (schema com `if/then`); conta 404 `QIT001002`.
- **Verde:** `post_transaction.json`; `TransactionRepository.create_entry` (valor com sinal, `operation_key`, `balance_after`); controller: trava a conta (`FOR UPDATE`), confere `amount` inteiro (**`jsonschema` aceita `10.0` como inteiro**, então rejeite `float` no controller), confere saldo, lança, atualiza o cache do saldo, `commit` único. A integração da `Idempotency-Key` foi antecipada depois da S3 e é documentada na S6.
- **Pronto quando:** testes verdes e `CHECK (balance >= 0)` do banco comprovado por um teste que tenta estourar o saldo.

### S8 Plano de boletos, lote 1 (B, 5h)
- **Depende de:** S2, T1.3, T1.4. **Paralelo com:** S3.
- **Vermelho:** `POST /account/{key}/billing-plan` 201 com 12 boletos (parcelas 1 a 12, vencimentos mensais a partir de `first_due_date`, com ajuste de fim de mês: 31/01 vira 28 ou 29/02, valor `base_amount`, status `PENDING`, `barcode` vindo do mock); `GET .../billing-plan/{plan_key}` com `status_events` por boleto; 400 em corpo inválido; 422 `QIT001017` vencimento no passado; 404 conta; 404 `QIT001013` plano de outra conta; 502 `QIT001009` para timeout, status 500, JSON inválido e resposta sem códigos de barra. **Como provar que nada ficou gravado numa falha 502:** configure o mock para funcionar e repita; deve vir 201 com exatamente 12 boletos, sem duplicatas.
- **Verde:** `post_billing_plan.json`; `BillingPlanController` (chama o conector, só então grava plano, boletos e eventos, `commit` único); utilitário de soma de meses.
- **Pronto quando:** testes verdes, `verify` do mock confirma a `external_reference` enviada.

### T2.1 Componente de idempotência (B, 2h)
- **Depende de:** T1.2. **Paralelo com:** S3, S8.
- **Fazer:** `IdempotencyRepository.insert_or_get(account_id, scope, key, request_hash)` com `INSERT ... ON CONFLICT DO NOTHING RETURNING` seguido de `SELECT` se vier vazio (se outra transação ainda não confirmou, o `INSERT` espera no índice `UNIQUE`; se ela confirmar, cai no `SELECT`). Hash SHA-256 de JSON canônico (`sort_keys=True`, separadores fixos). Helper de controller que devolve "executar", "repetir resposta guardada" ou "conflito" (`QIT001008`), e método `store_response(status, body)`.
- **Pronto quando:** revisado por A (que vai usá-lo na S6). Os testes de verdade são os da S6 e S7c.

### S2b Bloqueio e cancelamento de conta (C, 2,5h)
- **Depende de:** S2.
- **Vermelho:** `PUT /account/{key}/block` 200 (status `BLOCKED`, evento novo em `status_events`); repetir ou bloquear conta fora de `APPROVED`: 409 `QIT001019`; `PUT .../cancel` 200 tanto de `APPROVED` quanto de `BLOCKED`, com evento `CANCELLED`; cancelar conta já cancelada: 409 `QIT001019`; 404 conta. Depois de bloqueada ou cancelada, depósito e saque respondem 409 `QIT001006` (acrescente esses casos aos testes da S3).
- **Verde:** máquina de estados no controller: `APPROVED → BLOCKED`, `APPROVED → CANCELLED`, `BLOCKED → CANCELLED`; `CANCELLED` não tem saída. O repository apenas grava o status e o evento.
- **Pronto quando:** `QIT001006` prova que conta não aprovada não movimenta valores e `QIT001019` prova as transições inválidas.

### S4 Extrato, consulta de lançamento e R8 (C, 4,5h)
- **Depende de:** S3 (escreva os testes antes, com dados criados por depósitos).
- **Vermelho:**
  - `GET .../transactions`: ordem decrescente por `created_at` e `id`; `limit` e `page` (padrão 10 e 0; teto 100); `is_last_page` verdadeiro só na última; extrato vazio devolve `data: []`; filtro `type`; `limit` 0, 101, `page` negativa e parâmetro desconhecido: 400 `QIT000001`; conta 404.
  - **Reconstrução:** a soma de `amount` de todas as páginas é igual ao `balance`; `balance_after` do mais recente é igual ao `balance`.
  - `GET .../transaction/{transaction_key}`: 200 e 404 `QIT001011`.
  - **R8:** lançamento da conta A consultado pela conta B responde **404 com o mesmo corpo** de um lançamento inexistente, nunca 403.
- **Verde:** paginação com o truque do `limit + 1` (busca uma linha a mais para saber `is_last_page`); DTO do lançamento (`transaction_key`, `type`, `amount`, `balance_after`, `operation_key`, `created_at`, e a chave da contraparte quando houver). **Confirme** que o handler de erros transforma o erro de validação de query do FastAPI (por padrão 422) em `400 QIT000001`; se não, registre o handler.
- **Pronto quando:** testes verdes e o teste de R8 é citável na defesa.

**Gate 1.**

---

## 6. Rodada 3: Transferência (~5h)

### S5 Transferência com tarifa (A, 5h)
- **Depende de:** S3, S4 (para conferir pelo extrato).
- **Vermelho:** `TRANSFER` 201; origem perde valor mais tarifa, destino ganha o valor; o extrato da origem tem `TRANSFER_OUT` e `TRANSFER_FEE`, o do destino `TRANSFER_IN`, as três com o mesmo `operation_key`; casos de borda: saldo igual ao valor (sem a tarifa) responde 422, saldo igual a valor mais tarifa responde 201 e deixa saldo 0; destino igual à origem 422 `QIT001012`; destino inexistente 404; destino ou origem bloqueados 409 `QIT001006`; **nenhuma escrita parcial** quando falha (saldos e extratos intactos).
- **Verde:** uma única consulta trava as duas contas com `FOR NO KEY UPDATE ORDER BY id` (compatível com a FK da reserva de idempotência); tarifa de `TRANSFER_FEE_CENTS`; três linhas no ledger com `balance_after`; atualiza os dois saldos; `commit` único.
- **Pronto quando:** testes verdes e a invariante "soma do extrato igual ao saldo" vale para as duas contas.

### S9 Reajuste e lote 2 (B, 5h)
- **Depende de:** S8. **Paralelo com:** S5.
- **Vermelho:** `POST .../billing-plan/{plan_key}/adjustment` 201 com parcelas 13 a 24; valor igual a `base × (1 + taxa/100)` arredondado *half-up*, com casos parametrizados (por exemplo taxa `"4.83"`, taxa `"0"`, e um caso de empate: base 1000 com taxa `"0.05"` resulta em 1000,5 que arredonda para 1001); `adjustment_rate` gravado; segunda chamada 409 `QIT001014`; plano de outra conta 404 `QIT001013`; `index_code` inválido 400; 502 `QIT001009` com o Banco Central fora e com o conector de boletos fora (depois de configurar o mock para funcionar, repetir dá 201, sem lote duplicado); `verify` confirma a mesma `external_reference` na repetição.
- **Verde:** `CentralBankConnector` lê a taxa **sem trava**; depois trava a linha do plano (`FOR UPDATE`), confere se o lote 2 existe, calcula em `Decimal` com `ROUND_HALF_UP`, chama o `BankSlipConnector` com referência determinística (`plan_key` e número do lote), grava boletos e eventos, `commit` único.
- **Pronto quando:** testes verdes.

### S7a Concorrência: saque na última vaga (C, 3h)
- **Implementação:** `tests/utils/concurrency.py` cria uma sessão HTTP por thread e sincroniza a partida com `threading.Barrier`; os testes de integração repetem cada cenário cinco vezes.
- **Depende de:** S3. **Paralelo com:** S5, S9.
- **Fazer:** `tests/utils/concurrency.py` com `run_parallel(n, fn)` usando `ThreadPoolExecutor`, `threading.Barrier` (todas as requisições largam juntas) e uma `requests.Session` por thread. Testes: saldo 100 e dois saques de 80 simultâneos: **exatamente** um 201 e um 422, saldo final 20; saldo 100 e dez saques de 30: exatamente três 201, saldo final 10. Cada teste repetido 5 vezes (`parametrize`) para pegar instabilidade.
- **Cuidado:** confira em `src/database.py` o `pool_size` e o `max_overflow`; com mais threads do que conexões, o teste pode falhar por esgotar o pool e não por bug de lock.
- **Pronto quando:** 5 repetições seguidas verdes; se instável, a causa foi achada, não escondida com `sleep`.

### T3.1 Checkpoint da RFC (C, 1,5h)
- **Status:** concluído no checkpoint original RFC 2.1 e consolidado na RFC 2.2 após S7c e o roadmap da R4.5.
- **Feito:** releitura de `docs/RFC.md` contra código, `DECISOES.md`, DDL, schemas e testes; revisão de rotas, códigos de erro, DER e fluxos; versão da RFC elevada para 2.1. O checkpoint registrou explicitamente o que ainda era futuro naquele momento. As entregas posteriores S7b, S10 e S7c estão documentadas como concluídas nas respectivas seções abaixo.
- **PDF:** adiado de propósito para T5.3, como já determina T0.3; ainda não existe template oficial nem gerador de PDF no repositório. Assim não há um PDF provisório a regenerar ou páginas a contar neste checkpoint.
- **Pronto quando:** nenhuma divergência conhecida entre RFC e código no escopo entregue; itens futuros explicitamente marcados como planejados.

---

## 7. Rodada 4: Garantias (~6h)

### S6 Idempotência nas rotas (A, 3h, parcialmente antecipada)
- **Status atual:** concluída para a rota de transações. Depósito, saque e transferência exigem `Idempotency-Key`, fazem replay com `Idempotent-Replayed: true`, rejeitam corpo diferente com `QIT001008`, isolam chave por conta e removem a reserva quando a operação falha.
- **Evidência adicional:** transferência cobre replay sem segundo débito, conflito de payload e reutilização da mesma chave depois de falha de saldo insuficiente.
- **Integração concluída:** S10 reutiliza o mesmo componente na antecipação; S7c prova em dez requisições simultâneas que uma única chave gera um só lançamento e dez respostas idênticas.

### S7b Limite noturno (A, 2,5h)
- **Status:** concluída. `NightLimitExceeded` devolve `422 QIT001007` para saque ou transferência acima de `NIGHT_LIMIT_CENTS` dentro da janela; depósito não é limitado.
- **Implementação:** regra avaliada antes da trava de saldo, com relógio no `TIMEZONE`. `NIGHT_TIME_OVERRIDE` é exclusivo do ambiente de teste e fixa a hora para testes determinísticos, sem criar endpoint de controle de relógio.
- **Depende de:** S5.
- **Vermelho:** com relógio ou configuração controlada dentro da janela 20:00–06:00 e limite de 100000: saque ou transferência de 100000 resulta 201 e de 100001 resulta 422 `QIT001007`; depósito de qualquer valor não é limitado; o saldo e o extrato ficam intactos na falha.
- **Verde:** regra no controller, **antes** de qualquer trava (falha barata primeiro); janela, fuso (`America/Sao_Paulo`) e limite vindos do ambiente; só saque e transferência.
- **Pronto quando:** testes verdes e a decisão D8 documentada em README e RFC.

### S10 Antecipação lastreada em boletos (B, 6h)
- **Status:** concluída. A rota exige `Idempotency-Key`, trava conta e boletos em ordem, calcula taxa somente com inteiros, cria a antecipação, vincula os boletos e registra o crédito/taxa no ledger em um único commit.
- **Visibilidade:** `GET /billing-plan/{plan_key}` expõe `credit_advance_key` no boleto antecipado; o status permanece `PENDING`, pois antecipar não equivale a pagamento ou baixa.
- **Depende de:** S8, S6 (comece o vermelho e o verde sem idempotência e integre no fim).
- **Vermelho:** `POST .../credit-advance` 201 com `credit_advance_key`, `gross_amount`, `fee_amount`, `net_amount`, `balance`; taxa por inteiros *half-up* (boletos somando 10000 geram taxa 300; somando 1050 geram taxa 32); saldo sobe `net`; extrato tem `ADVANCE_CREDIT` e `ADVANCE_FEE`; `GET` do plano mostra o boleto antecipado; segundo pedido do mesmo boleto 409 `QIT001016`; boleto de outra conta ou inexistente 404 `QIT001015` com o mesmo corpo; lista com uma chave inválida **não aplica nada** nas demais (atomicidade); lista vazia, duplicada ou com mais de 50 chaves 400; sem header 400; conta bloqueada 409; repetição idempotente devolve a resposta original.
- **Verde:** trava a conta e depois os boletos (`ORDER BY id`); `fee = (gross * 3 + 50) // 100`; cria `credit_advance`, preenche `credit_advance_id`, lança as duas linhas do ledger e soma `net` ao saldo; `commit` único.
- **Pronto quando:** testes verdes.

### S7c Concorrência avançada (C, 4h)
- **Status:** concluída. Os cenários rodam por HTTP contra PostgreSQL real, com barreira para iniciar as threads juntas e timeout de 30 segundos; cada um é repetido cinco vezes.
- **Evidência:** 20 transferências A→B e 20 B→A concluem sem impasse, preservando a soma dos saldos menos 40 tarifas. Dez pedidos com a mesma chave retornam `201` e a mesma `transaction_key`, com uma única linha de saque. Duas antecipações do mesmo boleto retornam exatamente `201` e `409 QIT001016`; duas transferências que disputam 600 centavos para enviar 500 mais tarifa retornam `201` e `422 QIT001005`.
- **Infraestrutura de teste:** o pool SQLAlchemy comporta o pico de 40 requisições (10 conexões persistentes e até 40 temporárias), para que a prova meça as travas de domínio, e não a fila do pool.
- **Depende de:** S5, S6, S10 (escreva os testes antes de S10 acabar).
- **Fazer:**
  - Transferências cruzadas: 20 pares A→B e B→A ao mesmo tempo, com timeout de 30s no teste. Nenhuma pode travar, e a soma dos saldos finais é igual à soma inicial menos as tarifas.
  - Mesma `Idempotency-Key` em 10 threads: exatamente **um** conjunto de lançamentos e todas as respostas `201` com a mesma `transaction_key`.
  - Duas antecipações simultâneas do mesmo boleto (chaves diferentes): um 201 e um 409.
  - Duas transferências disputando o último saldo: um 201 e um 422.
- **Pronto quando:** 5 repetições seguidas verdes. **Atingido:** 20 testes verdes em 10,52s.

**Gate 2.**

---

## 8. Rodada 4.5: Evolução operacional e evidências (~19h, opcional)

Esta rodada não muda o critério de entrega do núcleo financeiro. Ela transforma
o protótipo em uma demonstração mais próxima de produção e deve começar somente
com o Gate 2 verde.

### S11 Identidade, sessões e autorização (A, 8h)
- **Status:** concluída em 2026-10-09. A suíte HTTP soma 130 testes verdes.
- **Depende de:** Gate 2.
- **Fazer:** criar `user`, vínculo de usuário à PME/conta e `user_session`; cadastro, login, refresh e logout/revogação de uma sessão. Senhas somente com Argon2 ou bcrypt. Emitir JWT de acesso curto e refresh token rotativo com validade máxima de 8 horas; o `jti` e a sessão permitem vários dispositivos e revogação individual. Definir papéis mínimos (`OWNER`, `OPERATOR`, `VIEWER`) e verificar acesso à conta antes de rotas financeiras.
- **Não fazer:** substituir a autenticação por JWT de 8 horas sem sessão persistida, armazenar senha em texto, ou remover `INTERNAL-TOKEN` sem definir a fronteira serviço-a-serviço.
- **Pronto quando:** dois dispositivos do mesmo usuário funcionam; revogar um não invalida o outro; senha nunca aparece em resposta/log; usuário sem vínculo recebe resposta autorizada pelo contrato; todos os fluxos financeiros preservam idempotência.
- **Evidência entregue:** `app_user`, `user_customer_access` e `user_session`; bcrypt; JWT de acesso com 15 minutos padrão; refresh opaco rotativo limitado a 8 horas; `POST /user`, `/auth/login`, `/auth/refresh` e `/auth/logout`; `QIT001020`–`QIT001023`; testes cobrem rotação, múltiplos dispositivos, logout individual, papel `VIEWER`, ausência de vínculo e regressão de idempotência na suíte completa. O `INTERNAL-TOKEN` foi preservado como fronteira serviço-a-serviço; `Authorization` passa a exigir RBAC quando fornecido.

### S12 Auditoria append-only verificável (C, 6h)
- **Depende de:** S11 para registrar ator; pode iniciar o DDL e os testes antes.
- **Fazer:** tabela `audit_event` com ator (usuário ou serviço), ação, tipo/chave do recurso, `request_id`, origem, timestamp, resumo anterior/posterior e hashes `previous_hash`/`event_hash`. Proibir `UPDATE` e `DELETE` no banco para essa tabela; correções usam evento compensatório. Exportar ou assinar checkpoints do hash para detectar adulteração fora do banco.
- **Não fazer:** chamar isso de blockchain nem permitir edição do histórico. Blockchain não é requisito para encadear hashes e provar violação.
- **Pronto quando:** criar, bloquear, cancelar, transferir e antecipar produzem eventos; tentativa de alterar/apagar evento é recusada; teste recalcula a cadeia de hashes e detecta adulteração.

### S13 Logs estruturados e métricas (B, 5h)
- **Depende de:** Gate 2. **Paralelo com:** S11 e S12.
- **Fazer:** manter logs no stdout, mas em JSON com `request_id`, rota, status, duração, conta mascarada e usuário quando existir. Expor métricas Prometheus de requisições/latência, códigos QIT, falhas de conectores, replay idempotente, espera por lock e saldo de sessões. Documentar quais rótulos não podem conter dados pessoais.
- **Pronto quando:** uma requisição pode ser acompanhada pelo `request_id`; `/metrics` é consultável no ambiente de observabilidade; teste prova contador de replay e falha de conector.

### S14 Timeouts e política de retentativa (A, 4h)
- **Depende de:** Gate 2. **Paralelo com:** S13.
- **Fazer:** separar timeout de conexão e leitura dos conectores, configurar `lock_timeout` e `statement_timeout` do PostgreSQL e definir prazo máximo de requisição. Documentar o status de resposta para cada esgotamento e reforçar que transação financeira após timeout só pode ser reenviada com a mesma `Idempotency-Key`.
- **Pronto quando:** MockServer prova timeout de conexão/leitura; lock longo não esgota workers; resposta e logs preservam `request_id`; teste demonstra replay seguro após o cliente interromper a espera.

### S15 Alertas e notificações confiáveis (B, 5h)
- **Depende de:** S12 e S13.
- **Fazer:** criar `outbox_event` na mesma transação do fato de negócio e um publicador separado. Alarmes operacionais cobrem aumento de `5xx`, falha de conector, lock lento e uso sustentado de recursos; notificações de domínio podem comunicar bloqueio/cancelamento ao responsável da PME.
- **Não fazer:** enviar e-mail ou webhook dentro do controller antes do commit, pois uma falha externa não pode desfazer ou duplicar uma operação financeira.
- **Pronto quando:** o commit cria o evento de saída junto com a mudança de domínio; repetição do publicador é idempotente; falha de entrega é retentável e observável.

### T4.5 Benchmark reproduzível de concorrência (C, 2h)
- **Depende de:** S13; pode ser antecipado como rascunho depois do Gate 2.
- **Fazer:** registrar em `docs/BENCHMARK.md` hardware/ambiente, versão do Compose, carga, número de threads, duração, resultado da S7c e leitura de CPU/memória via `docker stats`. Medir pelo menos cenário ocioso e as 40 transferências cruzadas.
- **Pronto quando:** outra pessoa consegue repetir o comando e distinguir limite da máquina de regressão de concorrência; a RFC cita o método, não números sem contexto.

**Gate 3 (opcional).**

---

## 9. Rodada 5: Entrega (~9h)

### T5.1 Teste de pipeline da jornada da PME (C, 3h)
- **Fazer:** um teste de ponta a ponta: criar cliente, criar conta, depositar, emitir plano de boletos (expectativas no MockServer), antecipar, consultar extrato paginado, e conferir a soma do extrato contra o saldo.
- **Pronto quando:** roda verde do zero, com `reset()` do mock no início.

### T5.2 Varredura de cobertura de erros (A, 3h)
- **Fazer:** tabela em `docs/COBERTURA.md`: cada código `QIT` do catálogo e a rota, ligados ao teste que o provoca. Cada rota deve ter pelo menos um teste de sucesso e um de erro. Preencher o que faltar.
- **Pronto quando:** nenhum código do catálogo sem teste (ou removido da RFC com justificativa).

### T5.3 RFC final e PDF (B, 3h)
- **Fazer:** atualizar a RFC (rotas, DER, fluxos, alternativas descartadas no formato "descartada porque X, ganharia se Y", principal desafio); cortar para o limite de 2 a 4 páginas (sugestão: reduzir a tabela de rotas ao essencial, cortar uma alternativa, enxugar fluxos secundários); gerar o PDF final; conferir que o diagrama está legível.
- **Pronto quando:** PDF com as duas seções fixas, diagrama renderizado, tabela de rotas com erros e idempotência, e revisado pelos três.

### T5.4 README e `.env` (A, 1,5h)
- **Fazer:** README com como subir (`docker compose up`), como testar (`pytest`), variáveis de ambiente e a decisão D8, estrutura de pastas e mapa da RFC para o código.
- **Pronto quando:** alguém que não participou consegue seguir só o README.

### T5.5 Teste de clone limpo em Linux (A, 1,5h)
- **Fazer:** numa máquina ou VM Linux **limpa** (a do jurado é Linux): `git clone` do repositório, **sem editar nada**, `docker compose up --build`, esperar `healthy`, `pip install -r requirements-dev.txt`, `pytest`. Se o `.env` for necessário, ele precisa estar versionado ou ter padrões no compose.
- **Pronto quando:** tudo verde sem nenhum passo manual além dos comandos do README. Quem executa **não** pode ser quem escreveu o compose.

### T5.6 Apresentação em PDF (B e C, 2h cada)
- **Fazer:** a apresentação explica o sistema no lugar de vocês: o enredo da PME (cobra, recebe, antecipa, paga, audita), o ecossistema (API, banco, mock), a regra de negócio (o que o sistema permite, o que barra e por quê), o principal desafio com o diagrama de concorrência, e as decisões descartadas. Slides ou documento, em PDF.
- **Pronto quando:** PDF final revisado pelos três.

### T5.7 Ensaio da defesa (A, B e C, 2h cada)
- **Fazer:** lista de perguntas prováveis e ensaio cruzado: por que lock pessimista? por que a ordem de travas por `id`? o que acontece se o commit falha depois de o conector emitir? por que 404 e não 403? por que centavos? por que o saldo é cache e o ledger é a verdade? como provam que o teste é caixa-preta? por que `ON CONFLICT`? o que cortaram e por quê? Cada pessoa deve saber explicar **qualquer** decisão.
- **Pronto quando:** cada pessoa respondeu todas as perguntas da lista sem consultar o código.

### T5.8 Buffer de bugs (A, B e C, ~4h no total)
- Reservado para o que o clone limpo e o ensaio acharem. Não gaste em funcionalidade nova.

### T5.9 Publicação (C, 0,25h)
- Tornar o repositório **público**, abrir em janela anônima, conferir que o último commit é o esperado e que a RFC em PDF está no repositório ou anexada. O que estiver no repositório nessa data é o que a banca vê.

---

## 10. Se travar: tarefas flexíveis sem dependência

Pegue uma destas quando estiver bloqueado esperando outra trilha:

| Tarefa | Horas |
|---|---|
| Escrever testes vermelhos da próxima fatia | 1 a 2 |
| Rascunhar os slides da apresentação | 1,5 |
| Montar a lista de perguntas da banca | 1 |
| Rascunhar o README | 1 |
| Revisão cruzada de um pull request aberto | 0,5 |
| Reler a RFC procurando contradições | 1 |
| Script para rodar o teste de clone limpo | 0,5 |

---

## 11. Totais e como comprimir

| Item | Horas-pessoa |
|---|---|
| R0 | 9 |
| R1 | 14 |
| R2 | 20,5 |
| R3 | 14,5 |
| R4 | 15,5 |
| R5 | 26 |
| **Total** | **~100** |

- **Extras (boletos, reajuste, antecipação):** T1.3, T1.4, S8, S9 e S10 somam 21h. Sem eles, o total cai para ~80h.
- **Time de 2:** junte A e C (A fica com S2 a S6; C com S1, S2b, S4, S7a a S7c) e deixe B com os extras; ~50h por pessoa. Se apertar, aplique a linha de corte cedo.
- **Sozinho:** ~80h só com o núcleo. Corte os extras desde o início e declare-os fora do escopo.
- **Margem:** some 25% de folga ao relógio previsto (de ~36h para ~45h).

---

## 12. Checklist final de entrega

- [ ] R1: nenhum arquivo de `tests/` importa `src/` (teste guardião verde).
- [ ] R2: `docker compose up` sobe tudo sem passos manuais, em Linux limpo.
- [ ] R3: cada falha tem código `QIT` específico, todos com teste.
- [ ] R4: nada some; eventos de status visíveis por HTTP; sem `is_deleted`.
- [ ] R5: nenhuma resposta traz `id` numérico do banco.
- [ ] R6: nenhum `float` em dinheiro, nem no `0.03`, nem na taxa do índice.
- [ ] R7: RFC com decisões tomadas e descartadas ("ganharia se ...").
- [ ] R8: lançamento de outra conta responde 404 com o mesmo corpo do inexistente, com teste.
- [ ] Concorrência: testes de saque, transferência cruzada, idempotência simultânea e antecipação dupla verdes em 5 repetições.
- [ ] RFC em PDF com 2 seções fixas, 2 a 4 páginas, diagrama renderizado.
- [ ] Apresentação em PDF.
- [ ] Repositório público no dia da entrega, README completo.
- [ ] Os três sabem defender qualquer decisão.
