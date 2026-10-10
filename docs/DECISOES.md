# DECISÕES FIXAS, CONTRATOS DE DADOS E CATÁLOGO DE ERROS (T0.2)

> **Documento de Alinhamento do Time (Trilhas A, B e C)**  
> **Objetivo:** Estabelecer todas as convenções, regras de negócio fixas, catálogo de erros e contratos de entrada/saída de cada endpoint. Este arquivo é o contrato de interface que permite que as três pessoas desenvolvam em paralelo sem bloqueios ou divergências.

> **Papel na entrega final:** este é o contrato detalhado e a fonte canônica de
> rotas, payloads, erros e regras. A RFC usa o modelo oficial e resume apenas o
> desenho, fluxos, evidências e trade-offs; README, Cobertura, Benchmark e
> Alertas guardam a evidência operacional. O payload QIT é um contrato próprio,
> não uma declaração de conformidade integral com RFC 9457.

---

## 1. Decisões Arquiteturais e de Negócio (D1 a D13)

> **Estado RFC 2.8:** D1–D13 estão implementadas; S15 materializou a outbox, o publicador e as regras operacionais de alerta, e a T4.5 entregou a evidência de benchmark reproduzível.

| # | Decisão | Definição Adotada | Justificativa / Regra Técnica |
|---|---|---|---|
| **D1** | **Precificação comercial versionada** | `pricing_policy` mantém tarifa fixa em centavos e/ou percentual em pontos-base para `TRANSFER`, `CREDIT_ADVANCE` e `BANK_SLIP_ISSUANCE`. Há políticas padrão sem PME e políticas específicas; a precedência é **PME específica vigente > padrão vigente**. O seed preserva o comportamento-base: transferência `100` centavos, antecipação `300` bps e emissão `0`. | Dinheiro e tarifa são `BIGINT`; percentual usa `Decimal` e arredondamento half-up, sem `float`. `pricing_snapshot` congela política, versão, base e tarifa no fato financeiro. Publicar preço cria nova versão e encerra a vigência anterior, sem alterar seus termos. `NIGHT_LIMIT_CENTS=100000`, `NIGHT_START="20:00"`, `NIGHT_END="06:00"` e `TIMEZONE="America/Sao_Paulo"` continuam sendo parâmetros regulatórios, não preço comercial. Estados/dupla aprovação são evolução S21. |
| **D2** | **Índices de Reajuste** | Aceitar exclusivamente **`IPCA`** e **`IGPM`**. | A Selic foi descartada porque é taxa básica de juros de política monetária, e não índice de inflação contratual para reajuste de cobrança/mensalidade. |
| **D3** | **Ciclo de Vida da Conta** | Rotas `PUT /account/{account_key}/block` e `PUT /account/{account_key}/cancel` (S2b). Transições permitidas: `APPROVED → BLOCKED`, `APPROVED → CANCELLED` e `BLOCKED → CANCELLED`. `CANCELLED` é final e irreversível. | Cada transição gera evento auditável. Operações financeiras só aceitam conta `APPROVED`; transição não permitida devolve `409 QIT001019`. |
| **D4** | **Modelo de Antecipação de Recebíveis** | Antecipação lastreada em **`bank_slip_keys`** (1 a 50 chaves por chamada). | Antecipação por valor arbitrário abre brecha para criar dinheiro sem lastro. Vincular às chaves dos boletos garante que cada boleto seja antecipado no máximo uma vez através do vínculo `bank_slip.credit_advance_id`. |
| **D5** | **Formato da Taxa do Banco Central** | Retornada em string percentual, ex: `"4.83"` (significa 4,83%). | O cálculo do novo valor utiliza `Decimal` com arredondamento *half-up* para centavos inteiros:<br>`fator = Decimal("1") + (Decimal(rate_str) / Decimal("100"))`<br>`novo_valor = int((Decimal(base_amount) * fator).quantize(Decimal("1"), rounding=ROUND_HALF_UP))` |
| **D6** | **Contratos dos Mocks (MockServer)** | Contratos fixos para os conectores externos: | **BankSlip Mock (`POST /bank-slips`):**<br>Entrada: `{ external_reference: str, installments: [{ installment_number: int, amount: int, due_date: "AAAA-MM-DD" }] }`<br>Saída: `200 { bank_slips: [{ installment_number: int, barcode: str }] }`<br><br>**CentralBank Mock (`GET /index/{IPCA\|IGPM}`):**<br>Saída: `200 { index: str, accumulated_rate: "4.83" }` |
| **D7** | **Histórico de Eventos Visível por HTTP (R4)** | `GET /account/{account_key}` expõe `status_events` da conta; `GET .../billing-plan/{plan_key}` expõe `status_events` dentro de cada boleto. | A regra R4 é verificável por HTTP porque os eventos são inspecionáveis. O formato atual é ISO 8601 sem offset, por exemplo `[{ "status": "APPROVED", "event_datetime": "2026-10-02T12:00:00.000000" }]`; consumidores não devem inferir fuso pelo texto. Evolução P1 prevê timestamps `TIMESTAMPTZ`/UTC explícitos. |
| **D8** | **Janela e Limite Noturno** | Saques e transferências noturnos têm limite de `100000` centavos (R$ 1.000,00), entre `20:00` e `06:00` do dia seguinte; depósito não é limitado. | A regra segue o limite padrão de transferências noturnas (Pix e TED) para pessoa física. A aplicação usa `TIMEZONE=America/Sao_Paulo`; somente no ambiente de teste, `NIGHT_TIME_OVERRIDE` fixa a hora sem permitir que o cliente HTTP a escolha. |
| **D9** | **Uso da classe base `RestConnector`** | Utilizar herança da classe existente em `src/connectors/rest_connector.py`. | Centraliza timeout separado de conexão (1 s) e leitura (5 s), limitado pelo orçamento da requisição, log padronizado de ida e volta e interpretação JSON com `Decimal`. O `INTERNAL-TOKEN` **não** é enviado automaticamente a APIs externas; somente um contrato explícito de serviço interno pode exigi-lo. |
| **D10** | **Identidade e sessões** | Um `app_user` pertence a uma PME (`customer`) por `user_customer_access`; portanto seu vínculo alcança as contas da PME. A senha usa bcrypt. Login cria sessão persistida por dispositivo, JWT de acesso de 15 minutos (configurável) e refresh token opaco, rotativo e válido por no máximo 8 horas. Papéis: `OWNER`, `OPERATOR`, `VIEWER`. | `INTERNAL-TOKEN` permanece a credencial serviço-a-serviço e não é login nem API Gateway. Em rotas financeiras, a ausência de `Authorization` preserva a chamada técnica interna; se `Authorization: Bearer <JWT>` vier, a sessão ativa e o papel sobre a conta são obrigatórios. `OWNER` administra ciclo de vida; `OWNER`/`OPERATOR` movimentam e emitem cobrança; os três podem consultar. |
| **D11** | **Auditoria verificável** | `audit_event` é uma cadeia global append-only: ator (`SERVICE` ou `USER`), ação, tipo/chave de recurso, `request_id`, IP de origem, resumo anterior/posterior, timestamp, `previous_hash` e `event_hash`. A cadeia começa em 64 zeros e usa SHA-256 sobre JSON canônico UTF-8. | A inserção adquire `pg_advisory_xact_lock`, evitando bifurcação sob concorrência; o evento entra na mesma transação do fato de negócio. Trigger PostgreSQL recusa `UPDATE`/`DELETE`; correção exige evento compensatório. `GET /audit-events` exporta os dados e `GET /audit-events/checkpoint` expõe a ponta para verificação externa. Isto não é blockchain: não há consenso distribuído nem imutabilidade contra um administrador do próprio banco. |
| **D12** | **Observabilidade e limites de espera** | Logs JSON no stdout com `request_id`, método, rota-modelo, status, duração, conta mascarada e usuário mascarado quando o JWT é válido. `GET /metrics` expõe Prometheus: requisições/latência, QIT, falhas de conectores, replay idempotente, duração de aquisição de travas e sessões ativas. Conectores têm conexão de 1 s e leitura de 5 s; cada transação PostgreSQL recebe `lock_timeout` de 2 s e `statement_timeout` de 10 s, todos limitados pelo orçamento de requisição de 15 s. | Rótulos são somente método, rota-modelo, status, código QIT, conector, escopo e operação: **nunca** e-mail, CPF/CNPJ, token, `request_id`, IP, chave de conta ou query string. Falha externa devolve `502 QIT001009`; espera/execução PostgreSQL esgotada devolve `503 QIT001024`, sempre correlacionável por `X-Request-ID`. Uma interrupção ou timeout no cliente não informa se houve commit: operação financeira só pode ser repetida com a mesma `Idempotency-Key`. |
| **D13** | **Alertas e notificações confiáveis** | Bloquear ou cancelar uma conta grava `outbox_event` na mesma transação do status e da auditoria. O worker separado reclama eventos por *lease*, faz `POST` ao webhook com `Idempotency-Key = event_key` e marca sucesso; falha preserva o evento, incrementa tentativa e agenda retentativa exponencial. | Não há chamada de e-mail/webhook dentro do controller antes do commit. A entrega é **pelo menos uma vez**: queda após o webhook aceitar pode reenviar a mesma chave, que o consumidor deve deduplicar. Métricas de outbox, HTTP 5xx, conector e lock alimentam regras Prometheus documentadas; CPU/memória dependem de coletor do runtime (ex.: cAdvisor), não da API. |

---

### Limite entre contrato atual e evolução planejada

O catálogo e os contratos de rota abaixo descrevem a API implementada, inclusive
D10–D13. A outbox não expõe uma rota pública: é infraestrutura interna e seu
contrato de integração é o webhook versionado por `topic`, documentado na RFC.

---

## 2. Catálogo Oficial de Erros da Aplicação

Todas as respostas de erro retornam payload JSON padronizado:
```json
{
  "title": "Bad Request",
  "description": "Descrição técnica do erro.",
  "translation": "Descrição amigável em português.",
  "code": "QITxxxxxx"
}
```

| Código | HTTP Status | Nome do Erro / Exception | Descrição / Quando ocorre |
|---|---|---|---|
| **QIT000001** | `400 Bad Request` | `InvalidSchema` | Corpo da requisição fora do schema JSON esperado, campos ausentes ou tipos incompatíveis. |
| **QIT000002** | `403 Forbidden` | `ForbiddenNotInternal` | Cabeçalho `INTERNAL-TOKEN` ausente ou com token inválido. |
| **QIT001001** | `404 Not Found` | `CustomerNotFound` | `customer_key` não existe na base de dados. |
| **QIT001002** | `404 Not Found` | `AccountNotFound` | `account_key` de origem ou de destino não encontrada no banco de dados. |
| **QIT001003** | `409 Conflict` | `DuplicatedDocumentNumber` | Documento (CPF ou CNPJ) já cadastrado para outro cliente (`UNIQUE`). |
| **QIT001004** | `409 Conflict` | `DuplicatedEmail` | E-mail já cadastrado para outro cliente (`UNIQUE`). |
| **QIT001005** | `422 Unprocessable` | `InsufficientBalance` | Saldo é menor que o débito exigido: o valor no saque, ou valor mais tarifa na transferência. |
| **QIT001006** | `409 Conflict` | `AccountNotApproved` | Conta de origem ou destino não está com status `APPROVED` (ex: `PENDING` ou `BLOCKED`). |
| **QIT001007** | `422 Unprocessable` | `NightLimitExceeded` | Valor do saque ou da transferência ultrapassa o limite permitido para o horário noturno. |
| **QIT001008** | `409 Conflict` | `IdempotencyConflict` | Mesma `Idempotency-Key` reenviada com parâmetros ou corpo de requisição diferentes. |
| **QIT001009** | `502 Bad Gateway` | `ExternalConnectorError` | Conector externo (BankSlip ou Banco Central) retornou erro, timeout ou resposta inválida. |
| **QIT001010** | `422 Unprocessable` | `InvalidDocumentNumber` | CPF ou CNPJ sintaticamente inválido (dígitos verificadores matematicamente incorretos). |
| **QIT001011** | `404 Not Found` | `TransactionNotFound` | `transaction_key` inexistente ou pertencente a outra conta (não vazar existência). |
| **QIT001012** | `422 Unprocessable` | `SameAccountTransfer` | Conta de destino informada é idêntica à conta de origem em uma transferência. |
| **QIT001013** | `404 Not Found` | `BillingPlanNotFound` | `plan_key` inexistente ou pertencente a outra conta. |
| **QIT001014** | `409 Conflict` | `AdjustmentAlreadyApplied` | Lote 2 de parcelas reajustadas já foi emitido previamente para este plano de cobrança. |
| **QIT001015** | `404 Not Found` | `BankSlipNotFound` | Alguma das chaves informadas em `bank_slip_keys` não existe ou não pertence a esta conta. |
| **QIT001016** | `409 Conflict` | `BankSlipNotEligible` | Algum dos boletos solicitados para antecipação não está `PENDING` ou já foi antecipado. |
| **QIT001017** | `422 Unprocessable` | `InvalidFirstDueDate` | Data de primeiro vencimento informada no plano de cobrança está no passado. |
| **QIT001018** | `400 Bad Request` | `MissingIdempotencyKey` | Cabeçalho obrigatório `Idempotency-Key` não foi informado na requisição. |
| **QIT001019** | `409 Conflict` | `InvalidAccountStatusTransition` | Transição de status da conta não permitida, inclusive tentativa de alterar uma conta `CANCELLED`. |
| **QIT001020** | `401 Unauthorized` | `InvalidAccessToken` | JWT ausente, malformado, expirado, assinado de forma inválida, refresh token já rotacionado/expirado ou sessão revogada. |
| **QIT001021** | `401 Unauthorized` | `InvalidCredentials` | E-mail não cadastrado ou senha inválida no login; a resposta não revela qual dos dois falhou. |
| **QIT001022** | `403 Forbidden` | `AccountAccessForbidden` | Usuário autenticado não possui vínculo com a PME da conta, ou seu papel não autoriza a operação. |
| **QIT001023** | `409 Conflict` | `DuplicatedUserEmail` | E-mail já cadastrado em `app_user`. |
| **QIT001024** | `503 Service Unavailable` | `DatabaseOperationTimeout` | `lock_timeout` ou `statement_timeout` do PostgreSQL esgotado; a tentativa foi desfeita e pode ser repetida com segurança, observada a mesma `Idempotency-Key` nas operações financeiras. |
| **QIT001025** | `503 Service Unavailable` | `DatabaseTransientFailure` | Deadlock (`40P01`) ou falha de serialização (`40001`) persistiu após retentativas transacionais seguras; repita a operação financeira com a mesma `Idempotency-Key`. |

### Erros de infraestrutura HTTP

| Código | HTTP Status | Quando ocorre |
|---|---|---|
| **QIT000010** | `400 Bad Request` | Parâmetro de consulta semanticamente inválido, como intervalo de datas invertido. |
| **QIT000404** | `404 Not Found` | Caminho HTTP inexistente. |
| **QIT000405** | `405 Method Not Allowed` | Método HTTP não permitido para o caminho. |
| **QIT000500** | `500 Internal Server Error` | Falha inesperada não mapeada para um erro de domínio. |

### Erros legados do recurso de exemplo `sample_entity`

Esses códigos não pertencem ao domínio BaaS PME. Eles permanecem para que o recurso de exemplo e seus testes continuem funcionais, sem disputar os códigos reservados ao produto.

| Código | HTTP Status | Quando ocorre |
|---|---|---|
| **QIT002001** | `404 Not Found` | `sample_entity_key` inexistente. |
| **QIT002002** | `409 Conflict` | Tentativa de alterar uma Sample Entity em status final. |
| **QIT002003** | `422 Unprocessable` | Idade abaixo do mínimo no recurso de exemplo. |
| **QIT002004** | `422 Unprocessable` | Data de nascimento impossível no recurso de exemplo. |

---

## 3. Contratos de Entrada e Saída por Endpoint

Todas as rotas (exceto `/` e `/health_check`) exigem o cabeçalho:
```http
INTERNAL-TOKEN: <token_configurado>
```

As rotas de identidade também exigem esse cabeçalho, pois são expostas atrás da
fronteira interna. Nas rotas financeiras e de consulta de conta, o cabeçalho
abaixo é opcional para o ator técnico, mas, quando presente, torna obrigatória
a autorização do usuário para a conta alvo:

```http
Authorization: Bearer <access_token_jwt>
```

Papéis: `OWNER` pode tudo na própria PME; `OPERATOR` cria transações, planos,
reajustes e antecipações; `VIEWER` somente consulta. Falha de token/sessão é
`401 QIT001020`; falta de vínculo ou papel insuficiente é `403 QIT001022`.

---

### 3.1. Clientes (`/customer`)

#### `POST /customer`
- **Cabeçalhos:** `INTERNAL-TOKEN`
- **Body de Entrada:**
  ```json
  {
    "name": "Academia Boa Forma Ltda",
    "email": "contato@boaforma.com.br",
    "document_number": "12.345.678/0001-90"
  }
  ```
- **Resposta Sucesso (`201 Created`):**
  ```json
  {
    "customer_key": "c9bf9e57-1685-4c89-bafb-ff5af830be8a"
  }
  ```
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `409 QIT001003`, `409 QIT001004`, `422 QIT001010`.

#### `GET /customer/{customer_key}`
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "customer_key": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
    "name": "Academia Boa Forma Ltda",
    "email": "contato@boaforma.com.br",
    "document_number": "12.345.678/0001-90",
    "created_at": "2026-10-02T15:00:00.000000"
  }
  ```
- **Erros Possíveis:** `403 QIT000002`, `404 QIT001001`.

---

### 3.2. Contas (`/account`)

#### `POST /account`
- **Body de Entrada:**
  ```json
  {
    "customer_key": "c9bf9e57-1685-4c89-bafb-ff5af830be8a"
  }
  ```
- **Resposta Sucesso (`201 Created`):**
  ```json
  {
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "customer_key": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
    "status": "APPROVED",
    "balance": 0,
    "created_at": "2026-10-02T15:00:00.000000"
  }
  ```
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001001`.

#### `GET /account/{account_key}`
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "customer_key": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
    "status": "APPROVED",
    "balance": 150000,
    "status_events": [
      {
        "status": "PENDING",
        "event_datetime": "2026-10-02T15:00:00.000000"
      },
      {
        "status": "APPROVED",
        "event_datetime": "2026-10-02T15:00:01.000000"
      }
    ],
    "created_at": "2026-10-02T15:00:00.000000"
  }
  ```
- **Erros Possíveis:** `403 QIT000002`, `404 QIT001002`.

#### `PUT /account/{account_key}/block` (Decisão D3)
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "status": "BLOCKED",
    "updated_at": "2026-10-02T15:30:00.000000"
  }
  ```
- **Erros Possíveis:** `403 QIT000002`, `404 QIT001002`, `409 QIT001019`.

#### `PUT /account/{account_key}/cancel` (Decisão D3)
- **Regra:** aceita contas em `APPROVED` ou `BLOCKED`, muda o status para `CANCELLED` e registra o evento. `CANCELLED` não pode voltar a nenhum outro status.
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "status": "CANCELLED",
    "updated_at": "2026-10-02T15:30:00.000000"
  }
  ```
- **Erros Possíveis:** `403 QIT000002`, `404 QIT001002`, `409 QIT001019`.

---

### 3.3. Transações Financeiras (`/transaction`)

#### `POST /account/{account_key}/transaction`
- **Cabeçalhos Obrigatórios:** `INTERNAL-TOKEN`, `Idempotency-Key: <string de 1 a 64 caracteres>`
- **Body de Entrada (Exemplo Depósito / Saque):**
  ```json
  {
    "type": "DEPOSIT",
    "amount": 50000
  }
  ```
- **Body de Entrada (Exemplo Transferência):**
  ```json
  {
    "type": "TRANSFER",
    "amount": 20000,
    "destination_account_key": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
  }
  ```
- **Resposta Sucesso (`201 Created`):**
  ```json
  {
    "transaction_key": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
    "type": "TRANSFER",
    "amount": 20000,
    "fee_amount": 100,
    "balance": 29900,
    "created_at": "2026-10-02T15:10:00.000000"
  }
  ```
  *(Em repetição com mesma `Idempotency-Key` e mesmo payload: responde `201` com o mesmo corpo e cabeçalho `Idempotent-Replayed: true`)*.
- **Erros Possíveis:** `400 QIT000001`, `400 QIT001018`, `403 QIT000002`, `404 QIT001002`, `409 QIT001006`, `409 QIT001008`, `422 QIT001005`, `422 QIT001007`, `422 QIT001012`.

#### `GET /account/{account_key}/transaction/{transaction_key}`
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "transaction_key": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "type": "TRANSFER_OUT",
    "amount": 20000,
    "balance_after": 30000,
    "operation_key": "c9d1b5a0-5a1c-4be7-bd19-1e40f9552a79",
    "created_at": "2026-10-02T15:10:00.000000"
  }
  ```
- **Erros Possíveis:** `403 QIT000002`, `404 QIT001002`, `404 QIT001011`.

#### `GET /account/{account_key}/transactions` (Extrato Paginado)
- **Query Params:** `page` (default 0), `limit` (default 10, max 100), `type` (opcional: `DEPOSIT`, `WITHDRAWAL`, `TRANSFER_IN`, `TRANSFER_OUT`, `TRANSFER_FEE`, `ADVANCE_CREDIT`, `ADVANCE_FEE`, `BANK_SLIP_ISSUANCE_FEE`).
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "data": [
      {
        "transaction_key": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
        "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
        "type": "TRANSFER_FEE",
        "amount": -100,
        "balance_after": 29900,
        "operation_key": "c9d1b5a0-5a1c-4be7-bd19-1e40f9552a79",
        "created_at": "2026-10-02T15:10:00.000000"
      },
      {
        "transaction_key": "d2a0b331-87eb-1b13-8aea-3b7885ea8131",
        "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
        "type": "TRANSFER_OUT",
        "amount": -20000,
        "balance_after": 30000,
        "operation_key": "c9d1b5a0-5a1c-4be7-bd19-1e40f9552a79",
        "created_at": "2026-10-02T15:10:00.000000"
      }
    ],
    "page": 0,
    "limit": 10,
    "is_last_page": false
  }
  ```
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001002`.

---

### 3.4. Cobrança e Boletos (`/billing-plan`)

#### `POST /account/{account_key}/billing-plan`
- **Body de Entrada:**
  ```json
  {
    "base_amount": 15000,
    "first_due_date": "2026-11-10"
  }
  ```
- **Resposta Sucesso (`201 Created`):**
  ```json
  {
    "plan_key": "7b1c3e5a-4f8d-4a9c-9e2b-1a3d5e7f9a1b",
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "base_amount": 15000,
    "installments_count": 12,
    "bank_slips": [
      {
        "bank_slip_key": "11111111-2222-3333-4444-555555555555",
        "installment_number": 1,
        "amount": 15000,
        "due_date": "2026-11-10",
        "barcode": "34191.09008 00000.123456 7 8901234567890",
        "status": "PENDING"
      }
    ],
    "created_at": "2026-10-02T15:20:00.000000"
  }
  ```
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001002`, `409 QIT001006`, `422 QIT001017`, `502 QIT001009`.

#### `GET /account/{account_key}/billing-plan/{plan_key}`
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "plan_key": "7b1c3e5a-4f8d-4a9c-9e2b-1a3d5e7f9a1b",
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "base_amount": 15000,
    "first_due_date": "2026-11-10",
    "created_at": "2026-10-02T15:20:00.000000",
    "bank_slips": [
      {
        "bank_slip_key": "11111111-2222-3333-4444-555555555555",
        "installment_number": 1,
        "amount": 15000,
        "due_date": "2026-11-10",
        "barcode": "34191.09008 00000.123456 7 8901234567890",
        "status": "PENDING",
        "credit_advance_key": "9a8b7c6d-5e4f-3a2b-1c0d-e9f8a7b6c5d4",
        "status_events": [
          {
            "status": "PENDING",
            "event_datetime": "2026-10-02T15:20:00.000000"
          }
        ]
      }
    ]
  }
  ```
- **Erros Possíveis:** `403 QIT000002`, `404 QIT001002`, `404 QIT001013`.

#### `POST /account/{account_key}/billing-plan/{plan_key}/adjustment`
- **Body de Entrada:**
  ```json
  {
    "index_code": "IPCA"
  }
  ```
- **Resposta Sucesso (`201 Created`):**
  ```json
  {
    "plan_key": "7b1c3e5a-4f8d-4a9c-9e2b-1a3d5e7f9a1b",
    "index_code": "IPCA",
    "accumulated_rate": "4.83",
    "adjusted_amount": 15725,
    "bank_slips": [
      {
        "bank_slip_key": "22222222-3333-4444-5555-666666666666",
        "installment_number": 13,
        "amount": 15725,
        "due_date": "2027-11-10",
        "barcode": "34191.09008 00000.789012 3 4567890123456",
        "status": "PENDING"
      }
    ]
  }
  ```
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001002`, `404 QIT001013`, `409 QIT001014`, `502 QIT001009`.

---

### 3.5. Antecipação de Recebíveis (`/credit-advance`)

#### `POST /account/{account_key}/credit-advance`
- **Cabeçalhos Obrigatórios:** `INTERNAL-TOKEN`, `Idempotency-Key: <uuid-ou-string>`
- **Body de Entrada:**
  ```json
  {
    "bank_slip_keys": [
      "11111111-2222-3333-4444-555555555555",
      "22222222-3333-4444-5555-666666666666"
    ]
  }
  ```
- **Resposta Sucesso (`201 Created`):**
  ```json
  {
    "credit_advance_key": "9a8b7c6d-5e4f-3a2b-1c0d-e9f8a7b6c5d4",
    "gross_amount": 30725,
    "fee_amount": 922,
    "net_amount": 29803,
    "balance": 59703,
    "bank_slip_keys": [
      "11111111-2222-3333-4444-555555555555",
      "22222222-3333-4444-5555-666666666666"
    ],
    "created_at": "2026-10-02T15:25:00.000000"
  }
  ```
- **Erros Possíveis:** `400 QIT000001`, `400 QIT001018`, `403 QIT000002`, `404 QIT001002`, `404 QIT001015`, `409 QIT001006`, `409 QIT001008`, `409 QIT001016`.

---

### 3.6. Identidade e sessões (`/user`, `/auth`)

#### `POST /user`
- **Cabeçalhos:** `INTERNAL-TOKEN`
- **Body de Entrada:** `customer_key`, `name`, `email`, `password` (8 a 72
  caracteres) e `role` opcional (`OWNER` por padrão; `OPERATOR` ou `VIEWER`).
- **Resposta Sucesso (`201 Created`):** `user_key`, `customer_key`, `role` e
  `created_at`. Senha e seu hash nunca são retornados.
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001001`,
  `409 QIT001023`.

#### `POST /auth/login`
- **Cabeçalhos:** `INTERNAL-TOKEN`
- **Body de Entrada:** `email`, `password`, `device_name` opcional.
- **Resposta Sucesso (`201 Created`):** `access_token` JWT, `refresh_token`
  opaco, `token_type: "Bearer"`, `expires_in` (segundos) e `session_key`.
  O access token dura 15 minutos por padrão e o refresh expira em no máximo 8
  horas desde o login.
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `401 QIT001021`.

#### `POST /auth/refresh`
- **Cabeçalhos:** `INTERNAL-TOKEN`
- **Body de Entrada:** `refresh_token`.
- **Resposta Sucesso (`201 Created`):** mesmo contrato do login, com novo
  refresh token. O token anterior deixa de funcionar na mesma transação.
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `401 QIT001020`.

#### `POST /auth/logout`
- **Cabeçalhos:** `INTERNAL-TOKEN`, `Authorization: Bearer <access_token>`.
- **Resposta Sucesso:** `204 No Content`; revoga somente a sessão indicada no
  JWT, sem encerrar os demais dispositivos do usuário.
- **Erros Possíveis:** `403 QIT000002`, `401 QIT001020`.

---

### 3.7. Auditoria verificável (`/audit-events`)

#### `GET /audit-events`
- **Cabeçalhos:** `INTERNAL-TOKEN`.
- **Resposta Sucesso (`200 OK`):** `{ data, checkpoint }`, onde cada item de
  `data` contém ator, ação, recurso, `request_id`, origem, resumos,
  `previous_hash`, `event_hash` e `event_datetime`; `checkpoint` contém a
  ponta atual (`audit_event_id`, `event_hash`). Não há rota de alteração ou
  remoção de eventos.
- **Verificação externa:** comece com 64 caracteres `0`, confirme que o
  `previous_hash` de cada evento é o hash anterior e recalcule `event_hash`
  com SHA-256 do JSON canônico (`sort_keys`, separadores `,` e `:`, UTF-8) dos
  campos exportados, sem `audit_event_id` nem checkpoint.
- **Erros Possíveis:** `403 QIT000002`.

#### `GET /audit-events/checkpoint`
- **Cabeçalhos:** `INTERNAL-TOKEN`.
- **Resposta Sucesso (`200 OK`):** a ponta atual da cadeia. Para cadeia vazia,
  devolve `{"audit_event_id": null, "event_hash": "000...000"}`.
- **Erros Possíveis:** `403 QIT000002`.

---

### 3.8. Observabilidade (`/metrics`)

#### `GET /metrics`
- **Cabeçalhos:** `INTERNAL-TOKEN`.
- **Resposta Sucesso (`200 OK`):** texto no formato de exposição Prometheus.
  Métricas: `baas_http_requests_total`,
  `baas_http_request_duration_seconds`, `baas_qit_errors_total`,
  `baas_external_connector_failures_total`, `baas_idempotency_replays_total`,
  `baas_database_lock_wait_seconds` e `baas_active_user_sessions`.
- **Rótulos permitidos:** método, rota-modelo, status HTTP, código QIT,
  conector, escopo de idempotência e operação de lock. Não use dados pessoais,
  tokens, hashes, chaves UUID, IP ou query string como rótulo.
- **Erros Possíveis:** `403 QIT000002`.

---

### 3.9. Política comercial de preço (`/pricing-policy`)

#### `POST /pricing-policy`
- **Cabeçalhos:** `INTERNAL-TOKEN`.
- **Body de Entrada:**
  ```json
  {
    "customer_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "operation": "TRANSFER",
    "fixed_fee_cents": 7,
    "percentage_basis_points": 100
  }
  ```
  `customer_key` é opcional (ou `null`) para a política padrão. `operation`
  aceita `TRANSFER`, `CREDIT_ADVANCE` e `BANK_SLIP_ISSUANCE`; os dois valores
  monetários são inteiros não negativos. A tarifa efetiva é `fixa +
  round_half_up(base × bps / 10000)`. Em `BANK_SLIP_ISSUANCE`, uma chamada
  que emite um lote é uma operação: o componente fixo é cobrado uma vez por
  lote e o percentual incide sobre a soma dos valores dos boletos emitidos.
- **Resposta Sucesso (`201 Created`):** `policy_key`, `customer_key`,
  `operation`, `version`, `fixed_fee_cents`, `percentage_basis_points` e
  `effective_from`.
- **Semântica:** a publicação é serializada por PME/operação, encerra a
  vigência da versão anterior daquele mesmo escopo e cria outra linha. Em
  execução, a política específica vigente vence a padrão; cada operação grava
  um snapshot imutável, portanto uma alteração comercial não reprifica fatos
  anteriores. O endpoint é administrativo interno nesta etapa; estados e
  aprovação maker-checker pertencem à S21.
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001001`.
