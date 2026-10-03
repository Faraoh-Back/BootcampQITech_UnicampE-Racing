# DECISÕES FIXAS, CONTRATOS DE DADOS E CATÁLOGO DE ERROS (T0.2)

> **Documento de Alinhamento do Time (Trilhas A, B e C)**  
> **Objetivo:** Estabelecer todas as convenções, regras de negócio fixas, catálogo de erros e contratos de entrada/saída de cada endpoint. Este arquivo é o contrato de interface que permite que as três pessoas desenvolvam em paralelo sem bloqueios ou divergências.

---

## 1. Decisões Arquiteturais e de Negócio (D1 a D9)

> **Checkpoint RFC 2.1:** estão implementadas as decisões necessárias para cliente, conta, ciclo de vida, ledger, transferência, plano de boletos, reajuste, idempotência, limite noturno e antecipação lastreada em boletos.

| # | Decisão | Definição Adotada | Justificativa / Regra Técnica |
|---|---|---|---|
| **D1** | **Valores Fixos e Variáveis de Ambiente** | • Tarifa de transferência: `100` centavos (R$ 1,00)<br>• Taxa de antecipação: `3%`<br>• Limite noturno: `100000` centavos (R$ 1.000,00)<br>• Janela noturna padrão: 20:00 às 06:00 | Todos os valores monetários são inteiros em centavos. As variáveis de ambiente são:<br>`TRANSFER_FEE_CENTS=100`<br>`ADVANCE_FEE_PERCENT=3`<br>`NIGHT_LIMIT_CENTS=100000`<br>`NIGHT_START="20:00"`<br>`NIGHT_END="06:00"`<br>`TIMEZONE="America/Sao_Paulo"` |
| **D2** | **Índices de Reajuste** | Aceitar exclusivamente **`IPCA`** e **`IGPM`**. | A Selic foi descartada porque é taxa básica de juros de política monetária, e não índice de inflação contratual para reajuste de cobrança/mensalidade. |
| **D3** | **Ciclo de Vida da Conta** | Rotas `PUT /account/{account_key}/block` e `PUT /account/{account_key}/cancel` (S2b). Transições permitidas: `APPROVED → BLOCKED`, `APPROVED → CANCELLED` e `BLOCKED → CANCELLED`. `CANCELLED` é final e irreversível. | Cada transição gera evento auditável. Operações financeiras só aceitam conta `APPROVED`; transição não permitida devolve `409 QIT001019`. |
| **D4** | **Modelo de Antecipação de Recebíveis** | Antecipação lastreada em **`bank_slip_keys`** (1 a 50 chaves por chamada). | Antecipação por valor arbitrário abre brecha para criar dinheiro sem lastro. Vincular às chaves dos boletos garante que cada boleto seja antecipado no máximo uma vez através do vínculo `bank_slip.credit_advance_id`. |
| **D5** | **Formato da Taxa do Banco Central** | Retornada em string percentual, ex: `"4.83"` (significa 4,83%). | O cálculo do novo valor utiliza `Decimal` com arredondamento *half-up* para centavos inteiros:<br>`fator = Decimal("1") + (Decimal(rate_str) / Decimal("100"))`<br>`novo_valor = int((Decimal(base_amount) * fator).quantize(Decimal("1"), rounding=ROUND_HALF_UP))` |
| **D6** | **Contratos dos Mocks (MockServer)** | Contratos fixos para os conectores externos: | **BankSlip Mock (`POST /bank-slips`):**<br>Entrada: `{ external_reference: str, installments: [{ installment_number: int, amount: int, due_date: "AAAA-MM-DD" }] }`<br>Saída: `200 { bank_slips: [{ installment_number: int, barcode: str }] }`<br><br>**CentralBank Mock (`GET /index/{IPCA\|IGPM}`):**<br>Saída: `200 { index: str, accumulated_rate: "4.83" }` |
| **D7** | **Histórico de Eventos Visível por HTTP (R4)** | `GET /account/{account_key}` expõe `status_events` da conta; `GET .../billing-plan/{plan_key}` expõe `status_events` dentro de cada boleto. | A regra R4 (imutabilidade e auditabilidade: nada deixa de existir) só é testável em caixa-preta se os eventos históricos de status forem inspecionáveis via resposta HTTP. Formato: `[{ "status": "APPROVED", "event_datetime": "2026-10-02T12:00:00Z" }]`. |
| **D8** | **Janela e Limite Noturno** | Saques e transferências noturnos têm limite de `100000` centavos (R$ 1.000,00), entre `20:00` e `06:00` do dia seguinte; depósito não é limitado. | A regra segue o limite padrão de transferências noturnas (Pix e TED) para pessoa física. A aplicação usa `TIMEZONE=America/Sao_Paulo`; somente no ambiente de teste, `NIGHT_TIME_OVERRIDE` fixa a hora sem permitir que o cliente HTTP a escolha. |
| **D9** | **Uso da classe base `RestConnector`** | Utilizar herança da classe existente em `src/connectors/rest_connector.py`. | Centraliza timeout (5s padrão), log padronizado de ida e volta e interpretação JSON com `Decimal`. O `INTERNAL-TOKEN` **não** é enviado automaticamente a APIs externas; somente um contrato explícito de serviço interno pode exigi-lo. |

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
| **QIT001005** | `422 Unprocessable` | `InsufficientBalance` | Saldo da conta de origem é menor que o valor a debitar somado à tarifa. |
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
    "created_at": "2026-10-02T15:00:00Z"
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
    "created_at": "2026-10-02T15:00:00Z"
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
        "event_datetime": "2026-10-02T15:00:00Z"
      },
      {
        "status": "APPROVED",
        "event_datetime": "2026-10-02T15:00:01Z"
      }
    ],
    "created_at": "2026-10-02T15:00:00Z"
  }
  ```
- **Erros Possíveis:** `403 QIT000002`, `404 QIT001002`.

#### `PUT /account/{account_key}/block` (Decisão D3)
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "status": "BLOCKED",
    "updated_at": "2026-10-02T15:30:00Z"
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
    "updated_at": "2026-10-02T15:30:00Z"
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
    "created_at": "2026-10-02T15:10:00Z"
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
    "created_at": "2026-10-02T15:10:00Z"
  }
  ```
- **Erros Possíveis:** `403 QIT000002`, `404 QIT001002`, `404 QIT001011`.

#### `GET /account/{account_key}/transactions` (Extrato Paginado)
- **Query Params:** `page` (default 0), `limit` (default 10, max 100), `type` (opcional: `DEPOSIT`, `WITHDRAWAL`, `TRANSFER_IN`, `TRANSFER_OUT`, `TRANSFER_FEE`, `ADVANCE_CREDIT`, `ADVANCE_FEE`).
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
        "created_at": "2026-10-02T15:10:00Z"
      },
      {
        "transaction_key": "d2a0b331-87eb-1b13-8aea-3b7885ea8131",
        "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
        "type": "TRANSFER_OUT",
        "amount": -20000,
        "balance_after": 30000,
        "operation_key": "c9d1b5a0-5a1c-4be7-bd19-1e40f9552a79",
        "created_at": "2026-10-02T15:10:00Z"
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
        "batch_number": 1,
        "adjustment_rate": null,
        "amount": 15000,
        "due_date": "2026-11-10",
        "barcode": "34191.09008 00000.123456 7 8901234567890",
        "status": "PENDING"
      }
    ],
    "created_at": "2026-10-02T15:20:00Z"
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
    "created_at": "2026-10-02T15:20:00Z",
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
            "event_datetime": "2026-10-02T15:20:00Z"
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
    "created_at": "2026-10-02T15:25:00Z"
  }
  ```
- **Erros Possíveis:** `400 QIT000001`, `400 QIT001018`, `403 QIT000002`, `404 QIT001002`, `404 QIT001015`, `409 QIT001006`, `409 QIT001008`, `409 QIT001016`.
