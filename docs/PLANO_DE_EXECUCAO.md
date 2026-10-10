# Plano de execução: BaaS PME (fatias verticais, horas e trilhas paralelas)

## 0. Como ler este plano

- **Horas** são horas-pessoa para alguém confortável com Python, FastAPI e SQL, já incluindo 0,5h de revisão cruzada por fatia. Se for a primeira vez de alguém com Docker, SQLAlchemy ou concorrência, multiplique as tarefas dessa pessoa por 1,5.
- **Rodadas** substituem datas. Uma rodada termina quando as três trilhas terminam. O tempo de relógio de uma rodada é o da trilha mais longa.
- **Trilhas A, B e C** são papéis do planejamento original para um time de 3, não exigência de três autores. Com 2 pessoas ou 1, veja a seção 11; aceite/ensaio valem para todos os integrantes reais.
- **Fatia vertical** é uma funcionalidade completa, da rota ao banco, entregue com teste. Nenhuma camada é construída "para depois".
- **Gate** é um ponto de verificação. Só se passa para a rodada seguinte com o gate verde.
- Fonte das restrições R1 a R8: os PDFs de estudo. Confira com o enunciado oficial.
- **Estado de entrega (2026-10-10):** S1–S21 possuem implementação/testes, com limites em RFC/DECISOES/COBERTURA. Listas “Fazer” preservam a intenção original e não provam conclusão integral. O estado de cada tarefa e o backlog 9.5 prevalecem; resultados atuais ficam em COBERTURA.
- **Referência vigente:** RFC 3.4; [bootstrap/relógio T5.10 e regressão atual](COBERTURA.md#relógio-determinístico-e-bootstrap-automático--10102026) e [benchmark T5.10](BENCHMARK.md#14-t510-bootstrap-determinístico-e-modo-externo). A publicação/CI de `1603118` precede as revisões seguintes; a revisão final ainda precisa ser publicada/validada no remoto pelo grupo.

### Regras de trabalho do time (valem para todas as tarefas)

1. `main` sempre verde: `./.venv/bin/python -m pytest tests -q` passando antes de qualquer merge. O bootstrap T5.10 prepara containers/banco/portas/horários de teste automaticamente, como no CI. Não exige override nem `down -v` sobre desenvolvimento; descarte manual de dados continua exigindo intenção explícita.
2. Branch curta por fatia (`feat/s3-deposito-saque`). Pull request pequeno, revisado por outra pessoa.
3. Commits separados por cor do TDD: `test(S3): vermelho ...`, depois `feat(S3): verde ...`, depois `refactor(S3): ...`. Histórico Git e registros de execução são evidências; não afirmar que todas as features seguiram esse ciclo apenas porque a suíte atual passa.
4. Arquivos compartilhados são onde nascem os conflitos. A recomendação inicial era separar erros por domínio (`errors/account_errors.py`, `errors/billing_errors.py`); a implementação mantém o catálogo em `errors/custom_errors.py` e os erros-base em `errors/base_error.py`. Coordenar alterações nesses arquivos e em `src/app.py`, DDL e models; eles evoluíram além de T1.1/T1.2 e não são arquivos congelados.
5. Teste nunca importa nada de `src/` (R1). Existe um teste guardião para isso (T0.5).
6. Dinheiro é sempre inteiro em centavos, em todas as camadas (R6). DTOs financeiros expõem UUID (R5); a exportação/checkpoint administrativo de auditoria expõe `audit_event_id` sequencial como exceção explícita, não garantia universal de R5.

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
| D1 | Precificação e regra noturna do produto | Tarifas são políticas versionadas em banco, específicas por PME ou padrão, em centavos/pontos-base; o seed mantém transferência de 100 centavos e antecipação de 300 bps. Limite noturno permanece 100000 centavos por saque ou transferência. |
| D2 | Índices do reajuste | O plano antigo diz IPCA/Selic, a RFC diz IPCA/IGPM. Selic não é índice de inflação: fique com **IPCA e IGPM**. |
| D3 | Ciclo de vida de conta | Adicionar `PUT /account/{account_key}/block` e `PUT /account/{account_key}/cancel` na S2b. Transições: `APPROVED → BLOCKED`, `APPROVED → CANCELLED` e `BLOCKED → CANCELLED`; `CANCELLED` é final. A API registra evento em toda transição e devolve `409 QIT001019` se ela não for permitida. |
| D4 | Antecipação | Lastreada em `bank_slip_keys`, não em valor livre. Após a evolução inicial, líquido > 0 na execução/cotação CREDIT_ADVANCE, com 422/QIT001030; exemplos em DECISOES 3.5.1. |
| D5 | Formato da taxa do índice | Percentual em string: `"4.83"` significa 4,83%, fator `1 + 4.83/100`. |
| D6 | Contratos dos mocks | BankSlip: `POST /bank-slips` com `{external_reference, installments:[{installment_number, amount, due_date}]}` responde `200 {bank_slips:[{installment_number, barcode}]}`. Banco Central: `GET /index/{IPCA\|IGPM}` responde `200 {index, accumulated_rate}`. |
| D7 | Eventos visíveis por HTTP | O R4 (nada que entrou deixa de existir) só é testável em caixa-preta se os eventos saírem na resposta. `GET /account/{key}` devolve `status_events` da conta; `GET .../billing-plan/{key}` devolve `status_events` de cada boleto (cada item com `status` e `event_datetime`). Atualize a RFC. |
| D8 | Janela noturna no ambiente de avaliação | A regra de negócio padrão permanece 20:00–06:00 em `America/Sao_Paulo`, com limite de 100000 centavos. O teste da S7b deve controlar relógio ou subir a API com configuração de ambiente própria; não deve depender da hora da banca. |
| D9 | `RestConnector` | A classe existe; conectores de índice e boleto herdam dela, com timeout/log/JSON Decimal centralizados. |

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
| **R4.75** API mais completa | S16 retry transacional, S17 precificação, S19 limites | S18 cobrança/antecipação, S20 cotação | T4.75 exemplos, S21 dupla aprovação | ~27h |
| **R5** Entrega | T5.2, T5.4, T5.5, T5.7, T5.8 | T5.3, T5.6, T5.7, T5.8 | T5.1, T5.6, T5.7, T5.8, T5.9 | ~9h |

Relógio acumulado previsto: R0 4h, R1 9h, R2 16h, R3 21h, R4 27h, R4.5 46h, R4.75 73h, R5 82h. R4.5 e R4.75 são expansões opcionais; o núcleo do desafio permanece pronto no Gate 2.

### Gates e linha de corte

- **Gate 0** (fim da R0): as máquinas do time sobem `docker compose up` com API/banco `healthy` e MockServer `Up`/respondendo ao status, `pytest` verde nos testes de fumaça e o PDF de teste da RFC sai com o diagrama renderizado.
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
  2. `cp .env.example .env`, `docker compose up --build`, esperar API/banco `healthy` e mock `Up`, abrir `/health_check` (204).
  3. Criar venv, `pip install -r requirements-dev.txt`, rodar `pytest`.
  4. Somente num banco descartável, rodar `docker compose down -v && docker compose up -d --build` (apaga dados; o script em `/docker-entrypoint-initdb.d` só roda com volume vazio, e o SQL precisa estar na imagem nova). Para banco existente, usar upgrade específico, quando disponível, sem reset; comandos no README da API.
  5. Ler o caminho completo do exemplo `sample_entity`: `app.py`, `resource`, `schema`, `controller`, `repository`, `model`, `dto`. Conferir que a ordem dos middlewares não será mexida.
  6. Registrar problemas de Docker na sua máquina (é aqui que eles aparecem, e não na véspera).
- **Pronto quando:** cada pessoa tem print do `docker compose ps` com API/banco `healthy` e MockServer `Up` e do `pytest` verde.

### T0.2 Decisões fixas e contratos (A, 1h, com 15 min do time todo)
- **Fazer:** criar `docs/DECISOES.md` com D1 a D9 acima, o **catálogo de erros** (código, status, nome, quando) e o **formato de resposta de cada rota** (campos e tipos). D10–D13 serão acrescentadas na R4.5 como decisões planejadas, sem antecipar contratos inexistentes. Esse arquivo é o contrato que permite as três trilhas trabalharem sem esperar umas pelas outras. **Atualização:** S11 materializou D10, S12 materializou D11, S13/S14 materializaram observabilidade e timeout da D12, e S15 materializou D13.
- **Pronto quando:** todos os integrantes leram e disseram "ok" no PR.

### T0.3 [Postergado para a Entrega / R5] RFC no modelo oficial da QI Tech e PDF
- **Status:** artefatos preparados no fechamento T5.3: RFC final de quatro páginas em `docs/entrega/RFC_FINAL.pdf`, com fonte editável e DER vetorial. Aceite dos integrantes ainda requer confirmação; a RFC integral permanece preservada.
- **Fazer:** Na etapa final, adaptar a RFC diretamente no formato/template oficial fornecido pela QI Tech e gerar o PDF final conforme as diretrizes do desafio.


### T0.4 Compose, mock e variáveis de ambiente (B, 1,5h)
- **Fazer:**
  1. Adicionar o serviço `mock` (MockServer) ao `docker-compose.yml`. A imagem pode não ter `curl`; se o `healthcheck` for complicado, use `depends_on: condition: service_started` e faça os testes esperarem `PUT /mockserver/status`.
  2. Conferir `depends_on: db: condition: service_healthy` para a API e o multi-stage do `Dockerfile` com `USER` não-root (se já existir no base, não mexa).
  3. `.env.example` e `.env` com: `INTERNAL_TOKEN`, `BANKSLIP_API_URL`, `CENTRAL_BANK_API_URL` (ambos apontando para `http://mock:1080`), `NIGHT_START`, `NIGHT_END`, `NIGHT_LIMIT_CENTS` e `TIMEZONE`. Tarifas deixaram de ser variáveis de ambiente na S17: são políticas versionadas em banco.
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
- **Fazer:** as 11 tabelas do núcleo inicial: `customer`, `account_status`, `account`, `account_status_event`, `idempotency_key`, `transaction`, `credit_advance`, `billing_plan`, `bank_slip_status`, `bank_slip`, `bank_slip_status_event`. As fatias posteriores ampliaram o produto para 23 entidades; o SQL também mantém três tabelas legadas herdadas da base. Detalhes que costumam esquecer:
  - `INSERT` dos enumeradores: `account_status` (PENDING, APPROVED, BLOCKED, CANCELLED) e `bank_slip_status` (PENDING, PAID, CANCELLED).
  - `document_number VARCHAR(18)` (o `CHAR(14)` do exemplo só cabe CPF; PME tem CNPJ).
  - `UNIQUE(account_id, scope, idempotency_key)` em `idempotency_key`; `UNIQUE(billing_plan_id, installment_number)` em `bank_slip`.
  - `CHECK (balance >= 0)`, `CHECK (amount <> 0)`, `CHECK (net_amount = gross_amount - fee_amount)`, `CHECK` do `type` do lançamento. Evolução posterior: `CHECK (net_amount > 0)` na antecipação e CHECK condicional CREDIT_ADVANCE na quote, com upgrade não destrutivo.
  - Índice `transaction(account_id, created_at DESC, id DESC)` para o extrato.
  - Chaves públicas das entidades como `CHAR(36) NOT NULL UNIQUE`; referências/agrupadores podem se repetir (`operation_key`, política nos snapshots), e `Idempotency-Key` é string com unicidade composta por conta/escopo.
- **Pronto quando:** num banco descartável, `docker compose down -v && docker compose up -d --build` aplica sem erro; `\d` no `psql` mostra tudo; um `INSERT` manual de saldo negativo é recusado pelo banco. Nunca usar reset como upgrade de dados reais.

### T1.2 Models SQLAlchemy (A, 2h)
- **Depende de:** T1.1.
- **Fazer:** um model por tabela espelhando o SQL (tipos, `nullable`, FKs, `UniqueConstraint`), relacionamentos de status com `order_by` do evento. Sem `create_all`: o SQL é a fonte da verdade.
- **Pronto quando:** a API sobe; um script **descartável fora de `tests/`** consulta cada model sem erro.

### T1.3 Conectores externos (B, 3h)
- **Depende de:** T0.4, D6. **Paralelo com:** T1.1.
- **Fazer:** `BankSlipConnector.issue_batch(external_reference, installments)` e `CentralBankConnector.get_accumulated_rate(index_code)`. Regras: timeout separado de conexão (1 s) e leitura (5 s), ambos configuráveis; qualquer falha (timeout, conexão, status diferente de 200, corpo que não é JSON, campo ausente) vira `ExternalConnectorError` (`502 QIT001009`); resposta interpretada com `json.loads(..., parse_float=Decimal)` (nunca `float`); URLs vêm de variável de ambiente. **Não envie o `INTERNAL-TOKEN` para API externa**: só para serviço interno cujo contrato exija.
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
- **Verde:** `post_transaction.json`; `TransactionRepository.create_entry` (valor com sinal, `operation_key`, `balance_after`); controller trava a conta (`FOR NO KEY UPDATE` na implementação atual), confere saldo, lança, atualiza o saldo materializado e faz `commit` único. O JSON Schema padrão admite `10.0` como inteiro matemático; a solução atual é `StrictValidator` central, exigindo `int` nativo antes do controller, que também preserva a checagem defensiva. A integração da `Idempotency-Key` foi antecipada depois da S3 e é documentada na S6.
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
- **Verde:** uma única consulta trava as duas contas com `FOR NO KEY UPDATE ORDER BY id` (compatível com a FK da reserva de idempotência); tarifa da `pricing_policy` vigente e snapshot aplicado; até três linhas no ledger com `balance_after`; atualiza os dois saldos; `commit` único.
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
- **Registro preservado:** [seção 13](#13-checkpoint-histórico-t31), reunida neste plano em 10/10/2026; não substitui contratos/evidências atuais.
- **Status:** concluído no checkpoint original RFC 2.1 e consolidado na RFC 2.2 após S7c e o roadmap da R4.5.
- **Feito:** releitura de `docs/RFC.md` contra código, `DECISOES.md`, DDL, schemas e testes; revisão de rotas, códigos de erro, DER e fluxos; versão da RFC elevada para 2.1. O checkpoint registrou explicitamente o que ainda era futuro naquele momento. As entregas posteriores S7b, S10 e S7c estão documentadas como concluídas nas respectivas seções abaixo.
- **PDF naquele checkpoint:** adiado de propósito para T5.3, como já determinava T0.3; naquele momento não existiam template oficial nem gerador de PDF no repositório. Hoje ambos existem e T5.3 registra o PDF final, sem transformar o checkpoint antigo em validação dessa versão.
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
- **Status:** concluída. A rota exige `Idempotency-Key`, trava conta e boletos em ordem, calcula tarifa comercial com inteiros/Decimal half-up (sem float monetário), cria a antecipação, vincula os boletos e registra crédito/tarifa positiva no ledger em um único commit. A regra posterior de líquido positivo agora antecede o snapshot de preço e a antecipação, com 422/QIT001030.
- **Visibilidade:** `GET /account/{account_key}/billing-plan/{plan_key}` expõe `credit_advance_key` no boleto antecipado; o status permanece `PENDING`, pois antecipar não equivale a pagamento ou baixa.
- **Depende de:** S8, S6 (comece o vermelho e o verde sem idempotência e integre no fim).
- **Vermelho:** `POST .../credit-advance` 201 com `credit_advance_key`, `gross_amount`, `fee_amount`, `net_amount`, `balance`; taxa por inteiros *half-up* (boletos somando 10000 geram taxa 300; somando 1050 geram taxa 32); saldo sobe `net`; extrato tem `ADVANCE_CREDIT` e `ADVANCE_FEE`; `GET` do plano mostra o boleto antecipado; segundo pedido do mesmo boleto 409 `QIT001016`; boleto de outra conta ou inexistente 404 `QIT001015` com o mesmo corpo; lista com uma chave inválida **não aplica nada** nas demais (atomicidade); lista vazia, duplicada ou com mais de 50 chaves 400; sem header 400; conta bloqueada 409; repetição idempotente devolve a resposta original.
- **Verde original:** trava a conta e depois os boletos (`ORDER BY id`); `fee = (gross * 3 + 50) // 100`; cria `credit_advance`, preenche `credit_advance_id`, lança crédito/tarifa e soma `net` ao saldo; `commit` único. **Evolução vigente:** S17 substituiu a tarifa fixa de 3% por política versionada (o seed mantém 300 bps), e P0.4 entregou líquido > 0. Tarifa zero não gera lançamento de valor zero; a fórmula atual é fixo + half-up(bruto×bps/10000).
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
- **Pronto quando:** 5 repetições seguidas verdes. **Atingido no marco original:** 20 testes verdes em 10,52s; regressões posteriores datadas em COBERTURA.

**Gate 2.**

---

## 8. Rodada 4.5: Evolução operacional e evidências (~19h, opcional)

Esta rodada não muda o critério de entrega do núcleo financeiro. Ela transforma
o protótipo em uma demonstração mais próxima de produção e deve começar somente
com o Gate 2 verde.

Contagens de 137/140/143 abaixo pertencem ao marco de 09/10/2026, antes da
classificação atual por marcadores. Não são contagens da suíte exclusivamente
HTTP vigente; a distribuição atual está em COBERTURA. “Concluída” descreve o
escopo demonstrativo e não implica gateway, coleta de alertas ou proteção
contra administração privilegiada do banco.

### S11 Identidade, sessões e autorização (A, 8h)
- **Status:** concluída em 2026-10-09. O marco de validação após S13 registrou 137 testes verdes.
- **Depende de:** Gate 2.
- **Fazer:** criar `user`, vínculo de usuário à PME/conta e `user_session`; cadastro, login, refresh e logout/revogação de uma sessão. Senhas somente com Argon2 ou bcrypt. Emitir JWT de acesso curto e refresh token rotativo com validade máxima de 8 horas; o `jti` e a sessão permitem vários dispositivos e revogação individual. Definir papéis mínimos (`OWNER`, `OPERATOR`, `VIEWER`) e verificar acesso à conta antes de rotas financeiras.
- **Não fazer:** substituir a autenticação por JWT de 8 horas sem sessão persistida, armazenar senha em texto, ou remover `INTERNAL-TOKEN` sem definir a fronteira serviço-a-serviço.
- **Pronto quando:** dois dispositivos do mesmo usuário funcionam; revogar um não invalida o outro; senha nunca aparece em resposta/log; usuário sem vínculo recebe resposta autorizada pelo contrato; todos os fluxos financeiros preservam idempotência.
- **Evidência entregue:** `app_user`, `user_customer_access` e `user_session`; bcrypt; JWT de acesso com 15 minutos padrão; refresh opaco rotativo limitado a 8 horas; `POST /user`, `/auth/login`, `/auth/refresh` e `/auth/logout`; `QIT001020`–`QIT001023`; testes cobrem rotação, múltiplos dispositivos, logout individual, papel `VIEWER`, ausência de vínculo e regressão de idempotência na suíte completa. O `INTERNAL-TOKEN` foi preservado como fronteira serviço-a-serviço; `Authorization` passa a exigir RBAC quando fornecido.

### S12 Auditoria append-only verificável (C, 6h)
- **Status:** concluída em 2026-10-09. Marco histórico: 137 testes verdes.
- **Depende de:** S11 para registrar ator; pode iniciar o DDL e os testes antes.
- **Fazer:** tabela `audit_event` com ator (usuário ou serviço), ação, tipo/chave do recurso, `request_id`, origem, timestamp, resumo anterior/posterior e hashes `previous_hash`/`event_hash`. Proibir `UPDATE` e `DELETE` no banco para essa tabela; correções usam evento compensatório. Exportar ou assinar checkpoints do hash para detectar adulteração fora do banco.
- **Não fazer:** chamar isso de blockchain nem permitir edição do histórico. Blockchain não é requisito para encadear hashes e provar violação.
- **Pronto quando:** criar, bloquear, cancelar, transferir e antecipar produzem eventos; tentativa de alterar/apagar evento é recusada; teste recalcula a cadeia de hashes e detecta adulteração.
- **Evidência entregue:** `audit_event`, índice por recurso e trigger PostgreSQL append-only; `AuditRecorder` inclui evento na mesma transação e serializa a cadeia com `pg_advisory_xact_lock`; ações de cliente, conta, transação, plano, antecipação e sessão são registradas com ator, `request_id`, origem e resumos seguros. `GET /audit-events` exporta a cadeia e `GET /audit-events/checkpoint` publica sua ponta. Testes recalculam SHA-256 de todos os eventos, provam eventos de criar/bloquear/cancelar/transferir/antecipar e confirmam que SQL direto não consegue atualizar nem apagar um evento.

### S13 Logs estruturados e métricas (B, 5h)
- **Status:** concluída em 2026-10-09. Marco histórico: 137 testes verdes.
- **Depende de:** Gate 2. **Paralelo com:** S11 e S12.
- **Fazer:** manter logs no stdout, mas em JSON com `request_id`, rota, status, duração, conta mascarada e usuário quando existir. Expor métricas Prometheus de requisições/latência, códigos QIT, falhas de conectores, replay idempotente, espera por lock e saldo de sessões. Documentar quais rótulos não podem conter dados pessoais.
- **Pronto quando:** uma requisição pode ser acompanhada pelo `request_id`; `/metrics` é consultável no ambiente de observabilidade; teste prova contador de replay e falha de conector.
- **Evidência entregue:** `prometheus-client` com registry própria e rota interna `GET /metrics`; logs JSON no stdout com correlação e identificadores mascarados; métricas de HTTP/latência, QIT, conectores, replay, aquisição de lock e sessões ativas. Rótulos são de baixa cardinalidade e não aceitam PII, tokens, UUIDs, IPs nem query string. Testes provam o incremento de replay e falha do BankSlipConnector e preservam `X-Request-ID` no fluxo de erro.

### S14 Timeouts e política de retentativa (A, 4h)
- **Status:** concluída em 2026-10-09. Marco histórico: 140 testes verdes.
- **Depende de:** Gate 2. **Paralelo com:** S13.
- **Fazer:** separar timeout de conexão e leitura dos conectores, configurar `lock_timeout` e `statement_timeout` do PostgreSQL e definir prazo máximo de requisição. Documentar o status de resposta para cada esgotamento e reforçar que transação financeira após timeout só pode ser reenviada com a mesma `Idempotency-Key`.
- **Pronto quando:** o MockServer prova o timeout de leitura; o timeout de conexão é configurado e tratado pela mesma classe-base de conector (um mock HTTP não consegue atrasar o handshake TCP); lock longo não esgota workers; resposta e logs preservam `request_id`; teste demonstra replay seguro após o cliente interromper a espera.
- **Evidência entregue:** conectores recebem 1 s para conexão e 5 s para leitura, sempre limitados pelo orçamento de 15 s; o MockServer prova o atraso de leitura e retorna `502 QIT001009`, enquanto falha de conexão é capturada pela mesma exceção `requests.RequestException`. Cada transação PostgreSQL recebe `lock_timeout=2 s` e `statement_timeout=10 s` via configuração local; esgotamento responde `503 QIT001024` com `X-Request-ID`. Contratos de infraestrutura seguram uma conta por SQL com `FOR UPDATE` e observam a API por HTTP: consulta não relacionada continua atendida; cliente que desiste antes do commit recupera, via mesma chave, um único lançamento. Não são testes estritamente HTTP e o orçamento não impõe deadline global rígido.

### S15 Alertas e notificações confiáveis (B, 5h)
- **Status:** concluída em 2026-10-09. Marco histórico: 143 testes verdes. Notificações/outbox entregues; regras de alerta são exemplos, sem stack de coletores instalado.
- **Depende de:** S12 e S13.
- **Fazer:** criar `outbox_event` na mesma transação do fato de negócio e um publicador separado. Alarmes operacionais cobrem aumento de `5xx`, falha de conector, lock lento e uso sustentado de recursos; notificações de domínio podem comunicar bloqueio/cancelamento ao responsável da PME.
- **Não fazer:** enviar e-mail ou webhook dentro do controller antes do commit, pois uma falha externa não pode desfazer ou duplicar uma operação financeira.
- **Pronto quando:** o commit cria o evento de saída junto com a mudança de domínio; publicação usa chave estável para deduplicação pelo consumidor; falha de entrega é retentável e observável. Aceite externo sem ack confirmado pode causar reentrega: at-least-once, não exatamente uma entrega.
- **Evidência entregue:** `outbox_event` é criado junto de bloqueio/cancelamento e da auditoria; `workers/outbox_publisher.py` roda separado (ou no perfil Compose `workers`), usa `FOR UPDATE SKIP LOCKED`, lease e backoff exponencial. O webhook recebe `Idempotency-Key=event_key`; sucesso confirmado no banco não volta à fila e falha mantém a linha para nova tentativa. `baas_outbox_pending_events`, `baas_outbox_retrying_events` e `baas_outbox_delivery_attempts_total` são derivados do estado persistido no `/metrics`, enquanto a [seção de alertas do README da API](../baas-pme-api/README.md#regras-operacionais-de-alerta-s15) fornece exemplos para 5xx, conectores, locks, outbox e recursos de container. Três contratos de infraestrutura (HTTP/MockServer + SQL/subprocesso do worker) provam commit conjunto, não republicação de sucesso confirmado e retentativa, não exactly-once externo nem disparo de alertas.

### T4.5 Benchmark reproduzível de concorrência (C, 2h)
- **Status:** concluída em 2026-10-09. A carga S7c canônica passou 5 vezes (40 transferências cruzadas por repetição) em 6,753 s de parede no ambiente de referência.
- **Depende de:** S13; pode ser antecipado como rascunho depois do Gate 2.
- **Fazer:** registrar em `docs/BENCHMARK.md` hardware/ambiente, versão do Compose, carga, número de threads, duração, resultado da S7c e leitura de CPU/memória via `docker stats`. Medir pelo menos cenário ocioso e as 40 transferências cruzadas.
- **Pronto quando:** outra pessoa consegue repetir o comando e distinguir limite da máquina de regressão de concorrência; a RFC cita o método, não números sem contexto.
- **Evidência entregue:** `scripts/benchmark_concurrency.sh` captura ambiente, imagens, amostra ociosa, snapshots NDJSON durante a carga, resultado do pytest e duração, sem apagar volume local. `docs/BENCHMARK.md` documenta carga, comandos, artefatos, referência contextual, critérios de comparação e diagnóstico. A RFC cita o método e seus limites, sem transformar a referência em SLO.

**Gate 3 (opcional).**

---

## 8.75 Rodada 4.75: Ajustes para deixar a API mais completa (~27h)

Esta rodada incorpora os aprendizados da defesa sem transformar decisão de
negócio em espera automática: retry só é permitido quando uma transação foi
desfeita por falha transitória de infraestrutura. Saldo insuficiente, limite
noturno, status inválido e boleto inelegível continuam sendo respostas finais
do pedido atual.

### T4.75 Exemplos práticos para RFC e defesa (C, 2h)
- **Status:** concluída em 2026-10-09. A RFC agora inclui exemplos de A→B/B→A como risco de ordem de travas, a diferença entre retry transitório e saldo insuficiente, os dois fluxos de boleto/antecipação, precificação/risco por PME, cotação informativa e maker-checker. A defesa deve dizer que lock é por ID interno crescente — nunca IP — e que mudança normal de saldo durante novas requisições não é deadlock.
- **Fazer:** inserir na RFC exemplos curtos de deadlock potencial A→B/B→A e sua prevenção por **ID interno crescente**, nunca IP; serialização de uma requisição esperando a primeira conta; diferença entre falha de negócio e infraestrutura; e separação entre cobrança da PME e antecipação.
- **Não fazer:** usar “A estava sem saldo, B transferiu e A passou depois” como exemplo de deadlock. Isso é mudança normal de estado, não ciclo de travas.
- **Pronto quando:** o time explica deadlock em menos de um minuto e não promete retry automático de `422` nem chama antecipação de empréstimo sem lastro.

### S16 Retentativa transacional apenas para falhas transitórias (A, 4h)
- **Status:** concluída em 2026-10-09. Operações idempotentes de transação e antecipação executam até duas tentativas para `40P01`/`40001`; cada retry descarta sessão abortada, recria controller/transação e preserva a chave idempotente. `QIT001025` representa esgotamento e `baas_database_transient_retries_total` registra somente `deadlock`/`serialization`. Dois testes provam um `40P01` sintético seguido de um único depósito e ausência de retry para `422 QIT001005`.
- **Depende de:** S6 e S14. **Fazer:** executor no controller que reinicia a operação inteira com sessão/transação nova, tentativas limitadas, backoff com jitter e a mesma `Idempotency-Key`, somente para deadlock PostgreSQL (`40P01`) ou falha de serialização (`40001`).
- **Não fazer:** retentar `400`, `401`, `403`, `404`, `409`, `422`, timeout de conector ou qualquer fluxo depois de I/O externo sem idempotência formal. `InsufficientBalance` deve responder imediatamente; crédito posterior exige nova intenção do cliente.
- **Cuidado:** rollback completo antes da próxima tentativa; nenhum lançamento, auditoria, outbox ou reserva idempotente pode vazar. Para conectores, retry só antes do I/O ou com referência externa comprovadamente idempotente.
- **Testar:** falha transitória na primeira tentativa resulta em um único `201`, único ledger/auditoria/outbox e mesmo `operation_key`; `422` não é repetido; esgotamento não deixa escrita parcial; S7c continua verde.
- **Pronto quando:** RFC e métricas descrevem retry como recuperação de infraestrutura, nunca como espera por dinheiro.

### S17 Precificação versionada e personalizada por PME (A e B, 6h)
- **Status:** concluída em 2026-10-09. `pricing_policy` define preço padrão ou específico por PME, e `pricing_snapshot` congela política, versão, base e tarifa calculada em cada operação. `POST /pricing-policy` publica a próxima versão imediatamente e encerra a vigência da anterior sem mudar seus termos. A precedência em execução é PME específica vigente, depois padrão vigente. Transferência, antecipação, lote 1 e lote 2 de boletos aplicam a política; lançamento de tarifa e auditoria retêm a evidência. A aprovação por dois atores foi implementada posteriormente em S21 no fluxo de propostas; as rotas diretas ainda permitem contorná-la.
- **Depende de:** S10, S12 e S16. **Fazer:** tabelas de política de preço por operação (`TRANSFER`, `CREDIT_ADVANCE`, `BANK_SLIP_ISSUANCE`), com valor fixo em centavos e/ou percentual em pontos-base, vigência, versão, estado e associação opcional por PME. A precedência é `PME específica > padrão vigente`.
- **Auditoria:** política publicada não é sobrescrita; correção gera versão nova. A operação guarda snapshot imutável da política, base de cálculo, taxa e valor aplicado no fato financeiro, e `audit_event` registra a escolha. Mudança futura de preço nunca altera histórico.
- **Regras:** valores em `BIGINT`; percentual em pontos-base ou `Decimal` controlado; arredondamento, vigência e proibição de sobreposição documentados. Emissão de boleto é cobrança explícita de serviço à PME, não valor do boleto do pagador.
- **Testar:** duas PMEs com preços distintos; padrão sem exceção; nova versão preservando histórico; transferência, antecipação e emissão auditáveis; nenhum `float`.
- **Pronto quando:** contratos comerciais diferenciados não exigem mudar variável de ambiente ou código, e é possível responder qual tarifa foi aplicada e por quê.

### S18 Dois fluxos explícitos: plano de cobrança e antecipação (B, 2h)
- **Status:** concluída em 2026-10-09. RFC, README e contratos distinguem o recebível que a PME emite para seu pagador da liquidez que a própria PME obtém ao antecipar um boleto pendente. O teste HTTP `test_receivables_flow.py` prova propriedade da PME, crédito/tarifa no extrato e a vedação de segunda antecipação. Não há produto de empréstimo neste escopo.
- **Fazer:** consolidar em RFC, README, contratos e apresentação: **Plano de cobrança** emite boletos da PME para seus próprios pagadores; **Antecipação de recebíveis** dá liquidez à PME sobre boletos pendentes já emitidos e vinculados como lastro.
- **Não fazer:** incluir contrato de empréstimo, principal sem lastro, juros parcelados, cronograma de amortização, boleto para devedor ou baixa automática. Isso é outro produto de crédito.
- **Testar:** jornada HTTP emite, seleciona boletos da própria PME, antecipa uma vez e mostra crédito/tarifa no extrato; documentos não usam “empréstimo” como sinônimo de antecipação.
- **Pronto quando:** um diagrama deixa claros PME, pagador do boleto e recebível que lastreia a liquidez.

### S19 Política de limites e habilitações por PME (A, 5h)
- **Status:** concluída em 2026-10-09. `risk_policy` e `risk_policy_snapshot` aplicam fallback padrão ou regra específica por PME para produtos, valor por transferência, consumo diário, valor de antecipação e número de boletos. `POST /risk-policy` publica nova versão e encerra a anterior. `customer_daily_outgoing` é protegido por trava advisory PME/data no mesmo commit da transferência; o teste concorrente prova que duas contas não consomem a última capacidade duas vezes.
- **Depende de:** S17. **Fazer:** criar política versionada por PME, com fallback padrão, para limite por transferência, teto diário de saída, teto de antecipação, máximo de boletos por antecipação e habilitação de produtos (`TRANSFER`, `BILLING_PLAN`, `CREDIT_ADVANCE`). Definir vigência, precedência e comportamento quando não houver política específica.
- **Integridade:** o consumo diário e a decisão de limite devem ser apurados/travados na mesma transação que lança dinheiro; duas requisições concorrentes não podem ultrapassar o teto em conjunto. A decisão aplicada, versão da política e valor consumido precisam ser auditáveis.
- **Não fazer:** controlar limite somente em cache, confiar em contador do cliente ou alterar retroativamente uma decisão passada. A regra noturna do produto continua independente, não substituível por contrato comercial; isso não comprova conformidade regulatória de Pix/TED.
- **Testar:** PMEs com limites diferentes; produto desabilitado retorna erro estável; duas transferências concorrentes disputam o último valor do teto; mudança de política só vigora na data definida; histórico mostra a versão aplicada.
- **Pronto quando:** risco e habilitação comercial variam por PME sem código condicional por cliente, preservando o mesmo rigor de lock, centavos e auditoria das transações.

### S20 Cotação de tarifas e previsibilidade para o integrador (B, 4h)
- **Status:** concluída em 2026-10-09. `POST /account/{account_key}/quote` calcula e persiste cotação informativa de 60 segundos para transferência, lote de cobrança e antecipação. Ela expõe bruto, tarifa, líquido, política comercial/risco e limites relevantes. A API deliberadamente **não aceita** `quote_key` na escrita financeira: toda execução recalcula as regras vigentes no commit, portanto alteração comercial, expiração ou payload diferente nunca força preço antigo nem permite tarifa fornecida pelo cliente.
- **Depende de:** S17 e S19. **Fazer:** expor consulta de cotação para transferência, emissão de boleto e antecipação, devolvendo valor bruto, tarifa, valor líquido quando aplicável, política/versão, limites relevantes e validade curta. A cotação é informativa; a execução recalcula a regra vigente ou aceita a cotação somente se ainda válida e vinculada ao mesmo payload.
- **Integridade atual:** a API nunca aceita tarifa ou `quote_key` como fonte de verdade. Expiração é informativa; execução recalcula preço/risco e grava snapshots da regra vigente, sem reaproveitar a cotação. Reutilização vinculante de cotação é alternativa não implementada.
- **Testar:** cotações de PMEs distintas, UUID e contrato estrito, JWT/papel/vínculo, alteração de preço, rejeição de `quote_key`/tarifa no payload e execução recalculada. Expiração temporal controlada ainda pode receber teste dedicado; não exigir preservação de tarifa informativa após publicação de política nova.
- **Pronto quando:** o integrador consegue mostrar custo antes de confirmar a operação, sem abrir brecha para manipular preço ou produzir divergência entre cotação, ledger e auditoria.

### S21 Aprovação em duas etapas para política comercial (C, 4h)
- **Status:** concluída em 2026-10-09. `policy_change_request` materializa `DRAFT → PENDING_APPROVAL → ACTIVE`; uma proposta específica de PME exige JWT de `OWNER`, e o aprovador deve ser outro usuário `OWNER`. Enquanto pendente, a alteração está somente em JSONB na proposta e não é selecionável por preço/risco; na aprovação, a versão publicada é criada e a chave fica ligada à proposta e à auditoria. As rotas diretas de política continuam como bootstrap técnico interno e contornam aprovação; sem gateway, o controle de quatro olhos é garantia apenas do fluxo de propostas. `RETIRED` não possui transição/rota entregue.
- **Depende de:** S17 e S19. **Fazer:** modelar ciclo de vida de política comercial e de risco: `DRAFT`, `PENDING_APPROVAL`, `ACTIVE` e `RETIRED`. O criador propõe versão, outro usuário autorizado aprova/publica, e a publicação respeita vigência. Registrar motivo, ator criador, ator aprovador, timestamps e versões no `audit_event`.
- **Não fazer:** permitir que o mesmo ator crie e aprove a própria alteração, sobrescrever política ativa ou tornar política pendente aplicável em operação financeira. Exceção operacional, se necessária, deve ser explícita, excepcional e auditada.
- **Testar:** segregação de funções; tentativa de autoaprovação rejeitada; política pendente não é selecionada; aprovação concorrente resulta em uma publicação (agora repetida três vezes para política de risco); encerramento de vigência não altera snapshots históricos; papéis sem autorização recebem erro estável.
- **Pronto quando:** uma condição comercial especial para uma PME passa por controle de quatro olhos (*maker-checker*), e a API consegue provar quem propôs, quem aprovou, quando entrou em vigor e quais operações a consumiram.

---

## 9. Rodada 5: Entrega (~9h)

### T5.1 Teste de pipeline da jornada da PME (C, 3h)
- **Status:** **concluída na revisão de 2026-10-10**. `tests/test_pme_journey.py` usa respostas exatas e o helper padrão do MockServer, percorre todo o extrato com limite de páginas/deduplicação e reconcilia oito lançamentos em quatro páginas. Inclui maker-checker de preço, emissão/reajuste, cotação/antecipação idempotente, transferência/saque e bloqueio/cancelamento auditável. Evidência datada em `COBERTURA.md`.
- **Fazer:** um teste de ponta a ponta: criar cliente, criar conta, depositar, emitir plano de boletos (expectativas no MockServer), antecipar, consultar extrato paginado, e conferir a soma do extrato contra o saldo.
- **Pronto quando:** roda verde do zero, com `reset()` do mock no início.

### T5.2 Varredura de cobertura de erros (A, 3h)
- **Status:** **matriz reconciliada na revisão de 2026-10-10**. `COBERTURA.md` relaciona os 40 códigos do catálogo a cenários/testes, distinguindo legado e infraestrutura; inclui `QIT001030` de líquido não positivo. O handler inesperado tem injeção controlada de falha com rollback e resposta sanitizada; `40P01`/`40001` são exercitados. Isso não prova cada combinação código–rota–papel; ampliar essas combinações permanece possível.
- **Fazer:** tabela em `docs/COBERTURA.md`: cada código `QIT` do catálogo e a rota, ligados ao teste que o provoca. Cada rota deve ter pelo menos um teste de sucesso e um de erro. Preencher o que faltar.
- **Pronto quando:** nenhum código do catálogo sem teste (ou removido da RFC com justificativa).

### T5.3 RFC final e PDF (B, 3h)
- **Status:** **artefatos concluídos em 2026-10-10; aceite do time pendente**. `docs/entrega/RFC_FINAL.md` e PDF de quatro páginas seguem o modelo oficial, versão 3.4, sem apagar a RFC integral/contratos. Conservam 28 rotas, 23 entidades, relações/cardinalidades e todos os fluxos S1–S21/pipelines, incluindo líquido positivo da antecipação/cotação, `QIT001030` e bootstrap/relógio de testes da T5.10. DER vetorial gerado da RFC integral; revisão visual pelo agente e validação automática de overflow, páginas e hashes. O restante de P0.4/9.5 permanece pendente. Revisão dos integrantes não foi inventada.
- **Fazer:** atualizar a RFC (rotas, DER, fluxos, alternativas descartadas no formato "descartada porque X, ganharia se Y", principal desafio); cortar para o limite de 2 a 4 páginas (sugestão: reduzir a tabela de rotas ao essencial, cortar uma alternativa, enxugar fluxos secundários); gerar o PDF final; conferir que o diagrama está legível.
- **Pronto quando:** PDF com as duas seções fixas, diagrama renderizado, tabela de rotas com erros e idempotência, e revisado por todos os integrantes.

### T5.4 README e `.env` (A, 1,5h)
- **Status:** **conteúdo concluído na revisão de 2026-10-10**. README reúne setup/venv, Compose, comandos das três suítes, worker, benchmark, limites e mapa RFC → código → testes. Guias duplicados foram consolidados, com os originais preservados em arquivo histórico. A comprovação independente de usabilidade continua em T5.5.
- **Fazer:** README com como subir (`docker compose up`), como testar (`pytest`), variáveis de ambiente e a decisão D8, estrutura de pastas e mapa da RFC para o código.
- **Pronto quando:** alguém que não participou consegue seguir só o README.

### T5.5 Teste de clone limpo em Linux (A, 1,5h)
- **Status:** **validação isolada concluída; critério independente parcial**. Snapshot `20261010T083920Z` comprovou venv/DDL/banco novos, seleções independentes e 255 testes. Após o ajuste de ordem do snapshot/tarifa extrema, fechamento em banco novo com a `.venv` existente: **260 passed, 75.43 s** (206 HTTP + 42 infraestrutura + 12 estáticos, todos na execução completa); métricas consultadas, benchmark 5×40 verde (parede 8,255 s). Históricos/limites preservados em COBERTURA/ENTREGA. Só projetos descartáveis removidos; banco original não foi alvo das suítes e recebeu somente o upgrade não destrutivo dos CHECKs. Não substitui clone remoto do commit final, VM virgem ou pessoa independente: essa confirmação continua pendente. `--head` poderá validar somente o conteúdo commitado após publicação.
- **Fazer:** numa máquina ou VM Linux **limpa** (a do jurado é Linux): `git clone` do repositório, **sem editar nada**, preparar `.venv` e executar `pytest`; T5.10 prepara automaticamente containers/banco/horário de teste. Para uso manual, `docker compose up --build` e esperar API/banco `healthy` e mock `Up`. O Compose tem padrões demonstrativos e `.env.example`; nunca versionar segredos reais. O aceite independente continua necessário.
- **Pronto quando:** tudo verde sem nenhum passo manual além dos comandos do README. Quem executa **não** pode ser quem escreveu o compose.

### T5.6 Apresentação em PDF (B e C, 2h cada)
- **Status:** **artefato concluído em 2026-10-10; aceite do time pendente**. `docs/entrega/APRESENTACAO.pdf` possui dez slides 16:9; fonte Markdown, ferramentas e manifesto acompanham o PDF. Inclui enredo, arquitetura, desafio financeiro, deadlock por ID (não IP), replay/retry, preço/risco/cotação/quatro olhos, identidade/auditoria/outbox, testes/pipeline, métricas/benchmark e alternativas/limitações. Revisão visual e overflow conferidos pelo agente; os integrantes ainda precisam aprovar.
- **Fazer:** a apresentação explica o sistema no lugar de vocês: o enredo da PME (cobra, recebe, antecipa, paga, audita), o ecossistema (API, banco, mock), a regra de negócio (o que o sistema permite, o que barra e por quê), o principal desafio com o diagrama de concorrência, e as decisões descartadas. Slides ou documento, em PDF.
- **Pronto quando:** PDF final revisado por todos os integrantes.

### T5.7 Ensaio da defesa (A, B e C, 2h cada)
- **Status:** **roteiro concluído; ensaio humano pendente**. a [seção de defesa do guia de entrega](entrega/ENTREGA.md#6-defesa-técnica-e-ensaio) organiza roteiro de dez minutos, perguntas/respostas sustentadas pelos contratos e folha de registro. Cada integrante deve apresentar e responder sem consultar código; os campos de aceite não foram preenchidos pelo agente.
- **Fazer:** lista de perguntas prováveis e ensaio cruzado: por que lock pessimista? por que a ordem de travas por `id`? o que acontece se o commit falha depois de o conector emitir? por que 404 e não 403? por que centavos? por que o saldo é cache e o ledger é a verdade? como provam que o teste é caixa-preta? por que `ON CONFLICT`? o que cortaram e por quê? Cada pessoa deve saber explicar **qualquer** decisão.
- **Pronto quando:** cada pessoa respondeu todas as perguntas da lista sem consultar o código.

### T5.8 Buffer de bugs (A, B e C, ~4h no total)
- **Status:** **aberto por definição**. Reservado para o que o clone limpo, a geração do PDF e o ensaio acharem; não deve ser convertido em funcionalidade nova.
- **Achado tratado na entrega inicial:** o smoke confundia porta publicada com porta interna do MockServer; validar em 11080 reproduziu a falha. A asserção passa a verificar a escuta interna 1080 definida no Compose. Benchmark agora consulta a porta API configurada, permitindo a execução isolada. Esse ajuste não alterou o comportamento financeiro; a implementação posterior de líquido positivo está registrada separadamente em P0.4.

### T5.9 Publicação (C, 0,25h)
- **Status:** **publicação/CI confirmados para `1603118` em 2026-10-10**. A `main` pública correspondeu ao HEAD local; o [BaaS PME CI](https://github.com/Faraoh-Back/BootcampQITech_UnicampE-Racing/actions/runs/38036090796) concluiu com sucesso nesse SHA. Ambos os PDFs retornaram HTTP 200 sem autenticação, com blobs iguais aos arquivos locais da versão verificada. [Evidência datada](entrega/ENTREGA.md#51-evidência-remota-confirmada). O agente não publicou mudanças nem alterou visibilidade. Novas revisões de código/documentos/PDFs precisam de novo commit/push, CI e verificação de acesso; o sucesso anterior não as cobre automaticamente. Clone, aceite e ensaio do grupo permanecem pendentes.
- Tornar o repositório **público**, abrir em janela anônima, conferir que o último commit é o esperado e que a RFC em PDF está no repositório ou anexada. O que estiver no repositório nessa data é o que a banca vê.

### T5.10 Infraestrutura automática e relógio determinístico (ajuste de entrega)

- **Status:** **implementada e validada localmente em 2026-10-10**: regressão
  final 289/114.35 s, métricas e cleanup real conferidos; benchmark 5×40
  verde/8,058 s, modo externo exercitado e reconferido depois do ajuste de
  cleanup. Publicação/CI remoto e aceite do grupo não presumidos.
- **Motivação:** execução local às 14h49 registrou duas falhas em testes que
  pressupunham noite. O CI antigo fixava 21:00, mas o pytest local dependia de
  preparação manual. Adaptar a expectativa ao relógio real ou dar skip
  esconderia a falta de prova noturna; fixar o Compose normal afetaria o produto.
- **Implementação:** `docker-compose.test.yml` independente, projeto UUID,
  portas locais livres e DB/mock novos; bootstrap gerido é padrão do pytest.
  API principal em 21:00; `api-clock` reutiliza imagem/banco da sessão para
  fronteiras/horário diurno. Nenhuma rota, regra de negócio ou DDL foi alterada.
- **Validação:** 14 cenários HTTP novos (12 fronteiras/valores e 2 replays
  dia→noite), além dos 2 originais; 15 guardas do bootstrap (portas, projeto,
  falhas, cleanup, restauração e segredo, inclusive perfil auxiliar remanescente). R1 passa a inspecionar `test_support`
  também. Prova Red do arquivo de infraestrutura ausente, seguida de Green;
  contagem/regressão/evidência atual em [COBERTURA](COBERTURA.md#relógio-determinístico-e-bootstrap-automático--10102026).
- **Pipeline/documentos:** CI usa static_guard + suíte completa gerida e salva
  JUnit/métricas/metadados; validador/benchmark já preparados usam opt-in
  `--test-environment=external` para não medir outro servidor. README, D8,
  RFC integral/síntese/slides e entrega atualizados, sem apagar históricos.
- **Pronto quando:** `.venv/bin/python -m pytest -q` passa sem API prévia nem
  variável de horário, incluindo fronteiras, sobre banco próprio; desenvolvimento
  preservado e cleanup confirmado. Publicação/CI remoto continuam em T5.9.
- **Limites:** Docker/permissão e dependências/imagens são pré-requisitos; execução
  sequencial. SIGKILL pode deixar recursos; imagens/cache permanecem. Não conclui
  hardening 9.5 nem a pendência de fuso do consumo diário de risco.

---

## 9.5 Garantias verificadas e limitações conhecidas: correções e hardening

Esta seção transforma achados em trabalho rastreável e é a fonte do backlog de correções/evolução produtiva. O enquadramento aprovado é **garantias verificadas e limitações conhecidas**, não proteção absoluta. Testes verdes sustentam os cenários cobertos, mas não anulam lacunas. A regra de líquido positivo da antecipação foi implementada em 2026-10-10 mediante autorização específica posterior à exclusão geral de 9.5. P0.4 fica **parcial**, com os demais limites/semânticas pendentes. Essa correção pontual não equivale à conclusão deste backlog nem autoriza seus outros itens.

Prioridade: **P0** trata lacunas atuais de integridade econômica/financeira e não deve ser tratado como melhoria cosmética pós-entrega; **P1** trata controles necessários antes da exposição produtiva; **P2** eleva evidência, operabilidade e qualidade da defesa. Concluir tarefas amplia garantias demonstráveis, sem certificar segurança absoluta. Alterações de DDL devem ser testadas por migrations e/ou recriação **intencional de banco local descartável**; `docker compose down -v && docker compose up -d --build` apaga dados e não é procedimento de upgrade produtivo.

| Lacuna discutida | Tarefas de correção / validação |
|---|---|
| Regra econômica de antecipação, cotação e cálculos extremos | P0.4; limites numéricos em P0.3 |
| Imutabilidade SQL incompleta, inclusive snapshots | P0.1; fronteira administrativa/checkpoint em P1.10 |
| Saldo materializado sem reconciliação operacional | P0.2 |
| Token interno amplo, JWT opcional e bypass de maker-checker | P1.4/P1.8; identidade em P1.5 |
| Emissão externa após rollback e reenvio de criação sem replay | P1.2 |
| Exposição de dados em logs de falha | P1.11 |
| Deadline, calendário de risco e recuperação de outbox | P1.9/P1.6 |
| Evolução segura de schema e recuperação de dados | P1.3/P1.12 |
| Camadas, auditoria/paginação e crescimento | P1.7/P1.10/P2.4 |
| Combinações não testadas e evidências de entrega | P2.3/P2.2; separação das suítes em P1.1 |

**Estado e conclusão:** salvo estado parcial já registrado, as tarefas abaixo
estão pendentes. Cada fechamento deve registrar commit, cenário Red/Green
quando aplicável, comando, resultado e atualização dos contratos. A aprovação
de uma decisão não substitui essa evidência nem permite marcar tarefa concluída.

### P0.1 Ledger e eventos financeiros append-only no banco (A, 4h)
- **Problema identificado:** atualmente `audit_event` possui trigger contra `UPDATE` e `DELETE`, mas `transaction`, `account_status_event`, `bank_slip_status_event`, `pricing_snapshot` e `risk_policy_snapshot` dependem da disciplina da aplicação. A credencial PostgreSQL local é privilegiada.
- **Fazer:** bloquear alteração/remoção de lançamentos, eventos e snapshots por trigger e privilégios mínimos; separar aplicação, proprietário/migrations e administração; recusar TRUNCATE/ALTER/DROP ao papel de aplicação. Correções de fatos financeiros devem ser compensatórias, não reescrita de histórico. Não bloquear a atualização legítima de saldo/estado atual nem confundir snapshots com encerramento permitido da vigência de políticas.
- **Testar:** contratos de infraestrutura devem tentar UPDATE/DELETE/TRUNCATE e alteração de schema com o papel real da aplicação; verificar snapshots e eventos além do ledger. Testes HTTP devem provar operações e correções autorizadas sem reescrever história.
- **Pronto quando:** a proteção append-only é demonstrada no banco contra o papel da aplicação; permissões e fronteira administrativa são documentadas. Não prometer imutabilidade contra superusuário/proprietário capaz de alterar a proteção.

### P0.2 Reconciliação entre saldo materializado e ledger (A, 4h)
- **Problema identificado:** `account.balance` é um cache materializado útil para saldo e concorrência, mas o banco não prova sozinho que ele corresponde à soma dos lançamentos.
- **Fazer:** definir formalmente quais tipos e sinais de `transaction` compõem o saldo; implementar consulta/rotina de reconciliação por conta, com resultado determinístico e métricas para divergências. Avaliar trigger de validação apenas se não comprometer desempenho e simplicidade; a rotina periódica é a linha mínima obrigatória.
- **Operação:** documentar agendamento, fronteira temporal consistente da leitura, alerta e runbook de investigação; conferir vínculos de lastro/snapshots e agrupamento de principal/tarifas por operation_key. Não corrigir divergência silenciosamente nem sobrescrever lançamento: correção financeira exige procedimento autorizado e auditável.
- **Testar:** criar contas com depósito, saque, transferência, tarifa e antecipação; provar que a reconciliação encontra saldo igual; em ambiente de teste, introduzir divergência controlada e provar detecção/alerta.
- **Pronto quando:** não se afirma “saldo nunca diverge do extrato” sem evidência verificável; a RFC passa a tratar saldo como projeção materializada reconciliável e informa como investigar/corrigir divergência.

### P0.3 Validação estrita de centavos e limites numéricos (A, 2h)
- **Estado:** tipo estrito corrigido em 2026-10-10 por validador central (incluindo `$ref`/políticas), com regressões HTTP. Limites superiores de BIGINT e resultados derivados continuam pendentes; a tarefa não está integralmente concluída.
- **Problema identificado:** transferências validam `type(amount) is int`, mas schemas JSON com `integer` podem aceitar `10.0` dependendo do validador. Em especial, revisar `base_amount` de planos de cobrança e todos os demais valores de entrada.
- **Fazer:** centralizar validação de centavos para exigir `int` nativo, rejeitar `float`, string numérica, `Decimal` serializado indevidamente, booleano e valores fora do intervalo permitido; manter taxas separadas de montantes e com regra de precisão documentada.
- **Testar:** para cada rota financeira, enviar `10.0`, `"10"`, `true`, negativo/zero quando não permitido e inteiro válido; apenas o inteiro válido pode chegar ao controller/repositório.
- **Pronto quando:** nenhum campo monetário atravessa a fronteira HTTP sem prova de ser inteiro em centavos; catálogo de erros e RFC registram o erro de contrato aplicável.

### P0.4 Semântica econômica e fronteiras de cálculo (A, 4h)
- **Estado:** **parcial**. Líquido positivo implementado e testado em 2026-10-10 por autorização específica: 36 casos HTTP + 16 SQL/migração, `422 QIT001030`, regra comum aos controllers, validação anterior ao snapshot de preço, CHECKs e upgrade que preserva histórico. Detalhes/exemplos em [DECISOES 3.5.1](DECISOES.md#351-líquido-positivo-regra-implementada-e-validada). As demais fronteiras econômicas continuam exigindo especificação; não foram implementadas nesta rodada.
- **Problema:** antes da correção, tarifa >= bruto podia confirmar antecipação sem liquidez ou resultar em 500 por CHECK de saldo. Essa parte foi corrigida. Cotação de transferência ainda calcula bruto menos tarifa; resultado negativo esbarra no CHECK da quote e pode gerar 500, não uma prévia negativa válida. Limites BIGINT e índices <= -100% também podem chegar a restrições SQL como 500.
- **Regra aprovada:** permitir antecipação somente com `gross_amount - fee_amount > 0`, após half-up, tanto na cotação CREDIT_ADVANCE quanto em nova execução; saldo existente não autoriza líquido zero/negativo. Para bruto R$ 100: tarifa R$ 3 permite líquido R$ 97; R$ 100/R$ 120 recusam líquido R$ 0/−R$ 20. A política fixa de R$ 120 pode continuar válida para bruto R$ 1.000; validar por operação.
- **Implementado para antecipação:** recusa antes de criar antecipação/vincular lastro/lançar dinheiro, com HTTP 422/QIT001030; não usa saldo insuficiente como explicação. CHECK de net_amount positivo e igualdade bruto−tarifa em antecipação, CHECK condicional em quote. Migração inspeciona legado e valida CHECKs quando possível; não reescreve fatos históricos. Operação no README da API; evidência em COBERTURA/ENTREGA.
- **Idempotência:** recusa desfaz efeitos e reserva; replay de sucesso preserva resposta original mesmo após nova política. Não repetir a recusa como falha transitória.
- **Outras decisões:** especificar representação de débito/crédito da cotação de transferência conforme sua execução, sem aplicar automaticamente a regra de líquido de antecipação. Definir limites monetários/derivados e a resposta para índices que produzam parcela não positiva; obter aprovação quando houver escolha de negócio.
- **Testado para antecipação:** tarifa fixa/percentual/combinada menor/igual/maior que bruto, um centavo líquido, arredondamento, seleção múltipla, saldo zero/suficiente, quote e execução. Ausência de alterações em saldo/extrato/lastro/snapshots/reserva/auditoria, replay e retomada segura; constraints em INSERT/UPDATE e upgrade idempotente com/sem legado. **Ainda testar/especificar:** índices-limite e valores próximos/acima de BIGINT sem 500 por contrato inválido, semântica de quote TRANSFER.
- **Pronto quando:** contrato, quote, execução, CHECKs e testes comprovam a regra aprovada e demais limites definidos. Estimativa inicial de 4h deve ser reavaliada conforme migração e amplitude dos casos; não é compromisso de duração.

### P1.1 Testes estritamente black-box separados de contratos de infraestrutura (C, 3h)
- **Estado:** marcadores, comandos, documentação e etapas CI separados em 2026-10-10, com execução local de cada seleção. Preservadas as duas evidências e a guarda estática. CI remoto confirmado para `1603118`, conforme T5.9; clone limpo independente continua pendente. Esta atualização registra evidência, sem concluir os demais itens desta tarefa ou implementar hardening.
- **Problema identificado:** a suíte não importa `src/`, o que é correto, mas alguns testes acessam PostgreSQL diretamente ou iniciam worker por subprocesso. Eles são excelentes testes de infraestrutura, porém não são caixa-preta sob a definição estrita de “somente HTTP”.
- **Fazer:** separar nomenclatura, diretórios e comandos: uma suíte `api_blackbox` exclusivamente HTTP contra containers e uma suíte `infrastructure_contract` para SQL direto, triggers, locks e workers. Preservar ambas; não reduzir cobertura para cumprir uma etiqueta.
- **Testar:** executar cada suíte isoladamente em clone/ambiente limpo e documentar dependências, reset do MockServer e critérios de falha.
- **Pronto quando:** README, RFC e apresentação afirmam precisamente o que cada suíte prova; a R1 pode ser defendida sem ambiguidade.

### P1.2 Emissão externa recuperável, idempotente e fora de locks críticos (A, 4h)
- **Problema identificado:** lote 2 mantém lock de plano durante emissão; lote 1/lote 2 podem emitir antes da validação final de saldo/status. Criar outro plano em reenvio produz nova referência: não existe replay persistido de criação para o cliente. Atomicidade PostgreSQL não desfaz efeito no provedor.
- **Fazer:** definir reserva persistida/estado de emissão com chave idempotente estável do cliente, verificar/registrar condições locais, confirmar reserva e chamar conector fora de locks críticos; finalizar com transação curta. Documentar mudanças de saldo/status entre etapas e como reconciliar/cancelar emissão externa não finalizada, conforme contrato realmente disponível no provedor.
- **Testar:** MockServer lento não mantém lock de domínio por toda a chamada; reenvios e corridas de lote 1/lote 2 não criam nova operação lógica. Cobrir timeout após aceite, queda antes da finalização, falha de commit, mudança de status/saldo e recuperação.
- **Pronto quando:** há caminho verificável de recuperação e rastreio de referência externa, sem boleto órfão invisível. Não prometer exactly-once externo sem suporte/deduplicação comprovados no provedor; os commits de reserva/finalização devem ser explicitados como desenho multifásico, não commit financeiro único fictício.

### P1.3 Banco e ciclo de mudança produtivos (A, 4h)
- **Estado:** upgrade SQL pontual de líquido positivo disponível e testado, sem reset; ferramenta/histórico geral de migrations e migração de timestamps permanecem pendentes. Um arquivo de upgrade não conclui esta tarefa.
- **Fazer:** migrar a evolução do DDL para ferramenta/versionamento de migrations; usar `TIMESTAMPTZ` em UTC nos timestamps novos e definir plano de migração dos existentes; revisar `CHECK`s de positividade, não negatividade e limites de `BIGINT` para os valores financeiros.
- **Testar:** ambiente vazio e upgrade de uma versão anterior; migração falha de maneira segura e não deixa schema parcialmente aplicado.
- **Pronto quando:** produção não depende de apagar volume com `down -v`; a documentação distingue claramente bootstrap local de evolução segura do banco.

### P1.4 Perfil de deploy seguro e fronteira interna (B, 4h)
- **Fazer:** criar configuração/perfil de produção sem `uvicorn --reload`, sem bind mount, sem tokens e segredos padrão, sem porta pública do PostgreSQL e com rede privada entre API, gateway e serviços internos. Exigir segredos por ambiente, limites de CPU/memória e health checks; restringir `INTERNAL-TOKEN` à fronteira gateway/serviço, nunca como credencial pública ampla.
- **Fronteira:** exigir TLS na entrada pública e validar autenticação serviço-a-serviço; distinguir liveness de readiness que verifica dependências essenciais. Gestão de segredos/rotação e autorização P1.8 complementam a rede privada; ela não basta sozinha.
- **Testar:** subida com variáveis obrigatórias ausentes deve falhar de forma explícita; perfil de produção não publica banco; chamadas internas e JWT mantêm suas fronteiras previstas.
- **Pronto quando:** README traz comandos distintos para desenvolvimento e produção demonstrativa, e a RFC não confunde defaults locais com controles de produção.

### P1.5 Segurança de identidade e sessões (A, 3h)
- **Fazer:** adicionar rate limit de login por IP e usuário, auditoria de falhas de autenticação, política de bloqueio/desafio progressivo, revogação administrativa de sessão e estratégia de rotação de segredo/chaves JWT.
- **Testar:** tentativa de força bruta é limitada sem revelar se o usuário existe; logout/revogação invalida refresh; rotação mantém somente a janela de compatibilidade documentada.
- **Pronto quando:** a ameaça de credencial roubada e abuso de login possui controles, métricas e alertas documentados.

### P1.6 Operação de falhas do outbox (B, 3h)
- **Problema identificado:** o lote padrão de dez eventos tem lease comum de 30 s e envio sequencial com leitura de até 5 s por evento; eventos finais podem perder lease. O worker ignora o retorno booleano do ack e pode contar publicação mesmo sem confirmar posse.
- **Fazer:** definir máximo de tentativas, estado terminal/dead-letter, motivo seguro da falha, procedimento de reprocessamento manual e alertas para backlog/idade do evento. Manter semântica at-least-once e chave idempotente do consumidor.
- **Complementar:** ajustar claim/renovação/tamanho de lote para o lease e duração de envio; validar lock_token no ack e contar sucesso somente quando ele for confirmado. Definir versionamento do envelope e autenticação do webhook, sem token/URL sensível em last_error; erro sanitizado segue P1.11.
- **Testar:** falha permanente não gera retry infinito; dois workers, lease expirado, ack obsoleto e queda após aceite preservam at-least-once com chave estável. Reprogramação autorizada não cria novo fato financeiro; métricas distinguem pendente, retry, posse perdida, publicação confirmada e dead-letter.
- **Pronto quando:** uma notificação que não pode ser entregue tem destino operacional visível e recuperável, sem comprometer o fato financeiro original.

### P1.7 Pureza das camadas (A, 3h)
- **Problema:** repositories de preço/risco calculam/decidem domínio; audit utils executa SQL.
- **Fazer:** mover regras puras para controller/domínio e consultas para repositories, preservando unidade transacional e locks; não mover commit para repository.
- **Testar:** mesmos contratos HTTP e infraestrutura permanecem verdes, com guarda arquitetural que detecte SQL fora da camada permitida.
- **Pronto quando:** a descrição de camadas corresponde ao código, sem prometer pureza antes da refatoração.

### P1.8 Fronteira de autorização e governança obrigatória (B, 3h)
- **Fazer:** definir perfis técnicos versus remotos, provisionamento de OWNER autorizado e quais clientes podem publicar políticas diretas. Gateway/credencial interna não podem permitir retirar JWT para escapar de RBAC; mudanças comerciais devem obedecer ao fluxo definido.
- **Testar:** matriz rota × papel × PME × ausência/invalidade/revogação de JWT, cadastro não autorizado e tentativa de contornar maker-checker.
- **Pronto quando:** a superfície pública não herda autoridade técnica ampla por conhecer INTERNAL-TOKEN.

### P1.9 Deadline e data de consumo diário (A, 3h)
- **Problema:** orçamento de 15 s limita esperas pontuais, não cancela a request inteira; timeout de pool/comandos sucessivos pode ultrapassá-lo. Risco diário usa data do runtime, enquanto regra noturna usa TIMEZONE.
- **Fazer:** definir deadline operacional e fronteiras de timeout sem tornar commit ambíguo; definir dia de negócio na configuração do produto.
- **Testar:** comandos externos/SQL sucessivos, saturação do pool, virada de dia/fuso e retomada com a mesma chave após interrupção.
- **Pronto quando:** documentação declara limites realmente impostos e consumo diário segue o calendário aprovado.

### P1.10 Auditoria e paginação sob crescimento (A, 3h)
- **Fazer:** exportação auditável paginada/cursor com limite, checkpoint externo persistido, revisão da serialização da cadeia global e extrato com fronteira estável sob escritas concorrentes; decidir/documentar a exceção sequencial audit_event_id.
- **Testar:** novas escritas entre páginas não omitem/duplicam registros no contrato escolhido; exportação limitada reconstrói a cadeia e detecta adulteração.
- **Pronto quando:** rastreabilidade não exige carregar toda a história em memória nem promete snapshot estável com offset livre.

### P1.11 Sanitização de logs de falha e do servidor (B, 3h)
- **Problema:** o middleware não escreve body, mas logger.exception/formatter e o log ASGI do Uvicorn podem incluir mensagens/parametrização SQL; exceções HTTP externas podem carregar URL e credenciais configuradas.
- **Fazer:** definir uma allowlist de campos de diagnóstico, excluir parâmetros/mensagens sensíveis e centralizar também logs do servidor; manter tipo, SQLSTATE seguro, localização e request_id sem expor dados pessoais.
- **Testar:** provocar erro SQL/HTTP com marcadores sintéticos de senha/e-mail/token e inspecionar stdout/stderr dos containers; nenhum marcador pode aparecer, inclusive no traceback ASGI.
- **Pronto quando:** a garantia de logs sem PII vale também para falhas inesperadas e bibliotecas, não apenas para request_completed.

### P1.12 Backup e recuperação verificável de dados (A/B, estimar)
- **Limitação:** volume persistente e testes verdes não demonstram recuperação após perda do banco; não há evidência de restore validado nesta revisão.
- **Fazer:** definir política de backup, retenção, criptografia/acesso e objetivos aprovados de recuperação (RPO/RTO); registrar procedimento de restore e reconciliação de saldo/ledger, cadeia auditável, idempotência e outbox após recuperação. Não assumir perda aceitável de dados financeiros sem decisão explícita.
- **Testar:** restaurar backup em banco isolado e verificar invariantes e cadeia/checkpoint; retomar replay e notificações sem criar nova operação financeira. Medir tempos e janela de dados realmente recuperados.
- **Pronto quando:** existe ensaio de recuperação reproduzível com evidência, limites e responsabilidades; backup não é apenas arquivo cuja leitura nunca foi testada.

### P2.1 Contrato de erros e cobertura documental (C, 2h)
- **Fazer:** decidir e documentar se o payload `{title, description, translation, code}` é contrato QIT próprio ou se a API adotará integralmente RFC 9457 (`type`, `title`, `status`, `detail`, `instance`). Não declarar conformidade parcial como total. Completar `docs/COBERTURA.md` para todos os códigos, inclusive autenticação e timeout, relacionando rota e teste.
- **Testar:** validar content type, corpo e código de cada erro catalogado; nenhum código publicado pode ficar sem cenário de teste ou justificativa explícita de remoção.
- **Pronto quando:** catálogo, handlers, RFC, cobertura e testes contam a mesma história.

### P2.2 Consolidação da entrega e defesa (C, 3h)
- **Enquadramento aprovado:** usar “garantias verificadas e limitações conhecidas” em RFC, decisões, README e apresentação. Cada garantia deve indicar mecanismo, teste e fronteira; cada pendência deve estar marcada como tal, inclusive regra aprovada sem implementação.
- **Fazer:** reconciliar o status real de T5.1 e outras tarefas já iniciadas com o plano; reduzir a RFC final ao formato oficial e limite exigido, preservando desafio principal, garantias verificáveis e alternativas descartadas; qualificar corretamente as evidências de benchmark e testes.
- **Testar:** revisão cruzada de documentação contra o repositório e execução de clone limpo. Toda afirmação forte — por exemplo, “imutável”, “black-box” ou “RFC 9457” — precisa apontar para garantia técnica ou ser reescrita com precisão.
- **Pronto quando:** não há divergência entre código, DDL, testes, README, RFC, `DECISOES.md`, `COBERTURA.md` e plano; a defesa consegue explicar limites conhecidos sem prometer uma garantia inexistente.

### P2.3 Matriz de fronteiras e recuperação além dos cenários atuais (C, estimar)
- **Limitação:** um teste por código e uma jornada integrada não cobrem todas as combinações de rota/papel/estado/falha. Os testes novos de P0/P1 devem fechar lacunas específicas, não somente aumentar a contagem.
- **Fazer:** manter matriz feature × caminho feliz/falha × mecanismo/evidência; ampliar rota/papel/PME, expiração de JWT/refresh/revogação, virada noturna/diária, cálculos extremos e queda de conector/worker. Controlar relógio/dados para não depender de hora real, sleeps longos ou datas fixas que vencem.
- **Cotação:** testar validade informativa e recálculo na execução, sem exigir reserva de preço nem inventar erro de cotação expirada em rotas que não aceitam quote_key.
- **Pipeline:** executar as suítes independentes em ambiente descartável/clone limpo, publicar resultado e logs sanitizados por etapa no CI; manter separação HTTP/infraestrutura. Não declarar Red retrospectivo de testes já verdes.
- **Pronto quando:** cada lacuna fechada tem cenário de regressão e evidência datada em COBERTURA; o restante fica explicitamente pendente.

### P2.4 Capacidade e observabilidade sustentadas (B/C, estimar)
- **Limitação:** o benchmark curto comprova correção de transferências cruzadas naquele ambiente; não valida throughput sustentável, auditoria crescente ou alertas enviados.
- **Fazer:** definir carga/hardware/cgroups comparáveis, executar repetições com condições de aquecimento controladas e avaliar latência, fila, pool, locks, auditoria/paginação e crescimento de memória. Instalar/configurar coletores de aplicação/worker/runtime e regras somente no perfil operacional escolhido.
- **Testar:** medir distribuição de latência e recursos sob carga prolongada; confirmar coleta por processo, perda/restart de séries e notificação de alertas com falhas controladas. Não usar uma amostra local para prometer SLO.
- **Pronto quando:** método, resultados, cardinalidade segura e alertas efetivamente exercitados estão registrados em BENCHMARK e na [seção de alertas do README da API](../baas-pme-api/README.md#regras-operacionais-de-alerta-s15) (antigo ALERTAS.md, consolidado); metas operacionais, se houver, têm aprovação e evidência.

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
| **Subtotal do núcleo e entrega originalmente estimados** | **99,5 (~100)** |
| R4.5 (S11–S15 e T4.5) | 30 |
| R4.75 (T4.75 e S16–S21) | 27 |
| **Total com expansões opcionais** | **156,5 (~157)** |

Esses números são estimativas históricas de planejamento, não horas efetivamente medidas. O backlog 9.5 é adicional e não está incluído. As alternativas abaixo referem-se somente ao núcleo, sem R4.5/R4.75.

- **Extras (boletos, reajuste, antecipação):** T1.3, T1.4, S8, S9 e S10 somam 21h. Sem eles, o total cai para ~80h.
- **Time de 2:** junte A e C (A fica com S2 a S6; C com S1, S2b, S4, S7a a S7c) e deixe B com os extras; ~50h por pessoa. Se apertar, aplique a linha de corte cedo.
- **Sozinho:** ~80h só com o núcleo. Corte os extras desde o início e declare-os fora do escopo.
- **Margem:** para o plano ampliado da seção 2, some 25% de folga ao relógio previsto (~82h → ~102,5h); a antiga estimativa ~36h → ~45h referia-se ao núcleo original.

---

## 12. Checklist final de entrega

- [x] R1: nenhum arquivo de `tests/` importa `src/` (teste guardião verde).
- [ ] R2: `docker compose up` sobe tudo sem passos manuais, em Linux limpo. **Parcial:** validação automatizada em clone local/snapshot, venv/banco novos e mesmo Docker daemon; clone remoto/VM e pessoa independentes ainda pendentes.
- [x] R3: todos os códigos publicados têm cenário associado na matriz. Isso não significa todas as falhas econômicas/combinações cobertas nem elimina `QIT000500`; ver P0.4.
- [x] R4: eventos de status e de auditoria são append-only na aplicação e visíveis pelos contratos previstos; não há `is_deleted` no domínio financeiro.
- [ ] R5 universal: DTOs financeiros usam UUID; exportação/checkpoint administrativo expõem ID sequencial. **Exceção documentada**, decisão de aderência literal pendente em P1.10.
- [x] R6 nos contratos testados: centavos inteiros, pontos-base inteiros e índice Decimal; validador rejeita `10.0`, strings e booleanos. Limites de magnitude/cálculos continuam P0.3/P0.4; latências podem usar float.
- [x] R7: RFC com decisões tomadas e descartadas ("ganharia se ...").
- [x] R8: lançamento de outra conta responde 404 com o mesmo corpo do inexistente, com teste.
- [x] Concorrência: suíte funcional cobre saque, transferência cruzada, idempotência simultânea e antecipação dupla. O benchmark mede **somente transferência cruzada**, cinco repetições de 40 chamadas (200 total); resultados datados em BENCHMARK.
- [x] RFC em PDF com 2 seções fixas, quatro páginas e DER vetorial renderizado; fontes preservadas, guardas/hash e revisão visual pelo agente. **Aceite do time pendente.**
- [x] Apresentação em PDF, dez slides 16:9, fontes editáveis e guardas/hash. **Aceite do time pendente.**
- [x] Repositório público, README e PDFs acessíveis sem autenticação; CI aprovado para `1603118`, conforme T5.9. **Por versão:** repetir publicação/CI/acesso após novas alterações e na revisão efetivamente submetida.
- [ ] Todos os integrantes sabem defender qualquer decisão. **Pendente:** ensaio cruzado.

## 13. Checkpoint histórico T3.1

Conteúdo antes mantido em `CHECKPOINT_T3_1.md`, incorporado em 10/10/2026.
Datas, resultados e ressalvas abaixo são preservados por marco; não atualizam
retroativamente as evidências nem concluem o backlog da seção 9.5.

**Atualização posterior ao registro:** T5.9 confirma publicação e CI de
`1603118`. Menções a publicação pendente no checkpoint abaixo retratam o marco
anterior; clone independente, aceite e ensaio continuam com o grupo.
Após esse marco, a RFC passou para 3.3: líquido positivo foi implementado com
QIT001030 e testes, por autorização específica. Menções abaixo à versão 3.2
e à regra pendente são históricas; os marcos antigos não provam a regra nova.

### Checkpoint T3.1 — registro histórico e reconciliação atual

Data da revisão original: 2026-10-03. Registro acumulado de S11–S21 e
T4.5/T4.75: 2026-10-10. A RFC naquele marco era 3.2; este checkpoint não substitui
os contratos de DECISOES nem as evidências datadas de COBERTURA.

O enquadramento é **garantias verificadas e limitações conhecidas**.
Naquele marco, a regra de líquido positivo foi aprovada, mas a validação
permanece pendente P0.4; os marcos de testes abaixo não a comprovam.

#### Escopo conferido

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
| Evolução e entrega | RFC 3.2, `DECISOES.md` e R5 | Jornada, matriz, README e separação da pipeline foram revisados; regra de líquido positivo está aprovada, com implementação pendente. RFC em PDF de quatro páginas e apresentação de dez slides possuem fontes/DER/hash e revisão visual pelo agente; aceite do time, clone remoto independente, ensaio e publicação continuam pendentes. |

#### Itens deliberadamente futuros

- **T5.3:** o [modelo oficial](bootcamp-rfc-modelo.md) existe e a RFC segue suas seções. A [síntese em PDF](entrega/RFC_FINAL.pdf) possui quatro páginas e DER vetorial, mantendo a RFC integral. Guardas/hash e revisão visual pelo agente foram executadas; aceite final dos integrantes ainda é necessário. Reprodução e demais confirmações em [ENTREGA](entrega/ENTREGA.md).
- **R4.5 e R4.75:** entregues. Além do Gate 3, preço/risco versionados, cotação informativa e propostas maker-checker possuem contratos, snapshots/auditoria e testes HTTP. O benchmark foi reexecutado no fechamento; seus artefatos e números contextualizados estão em `BENCHMARK.md`.

O checkpoint registra evidências por marco, não uma aprovação universal.
9.5 do plano contém hardening e também lacunas concretas de economia,
autorização e integração externa. Elas não são anuladas pelo resultado verde
dos cenários já cobertos. Consulte COBERTURA para a avaliação atual e DECISOES
para limites de imutabilidade, IDs administrativos, preços e JWT opcional.
