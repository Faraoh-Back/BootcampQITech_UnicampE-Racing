# DECISÕES FIXAS, CONTRATOS DE DADOS E CATÁLOGO DE ERROS (T0.2)

> **Documento de Alinhamento do Time (Trilhas A, B e C)**  
> **Objetivo:** Estabelecer todas as convenções, regras de negócio fixas, catálogo de erros e contratos de entrada/saída de cada endpoint. Este arquivo é o contrato de interface que permite que os integrantes desenvolvam em paralelo sem bloqueios ou divergências; A, B e C são papéis do plano, não exigência de três autores.

> **Papel na entrega final:** este é o contrato detalhado e a fonte canônica de
> rotas, payloads, erros e regras. A RFC usa o modelo oficial e resume apenas o
> desenho, fluxos, evidências e trade-offs; README, COBERTURA, BENCHMARK e
> ENTREGA guardam a evidência operacional. As regras de alerta estão no README
> da API e não são um stack instalado. O payload QIT é um contrato próprio,
> não uma declaração de conformidade integral com RFC 9457.

---

## 1. Decisões Arquiteturais e de Negócio (D1 a D16)

> **Estado RFC 3.4:** D1–D16 têm implementação com os limites descritos abaixo. A regra de líquido positivo da D4, aprovada em 2026-10-10, agora é aplicada à antecipação e à cotação CREDIT_ADVANCE, com `422 QIT001030`, proteção SQL e testes. A D8 passa a ser validada por relógios fixos em infraestrutura isolada iniciada automaticamente pelo pytest. Isso conclui apenas a subparte autorizada de P0.4, não o restante da seção 9.5. O checkpoint histórico não substitui esta especificação atual.

| # | Decisão | Definição Adotada | Justificativa / Regra Técnica |
|---|---|---|---|
| **D1** | **Precificação comercial versionada** | `pricing_policy` mantém tarifa fixa em centavos e/ou percentual em pontos-base para `TRANSFER`, `CREDIT_ADVANCE` e `BANK_SLIP_ISSUANCE`. Há políticas padrão sem PME e políticas específicas; a precedência é **PME específica vigente > padrão vigente**. O seed preserva o comportamento-base: transferência `100` centavos, antecipação `300` bps e emissão `0`. | Dinheiro e tarifa são `BIGINT`; percentual usa `Decimal` e arredondamento half-up, sem `float`. `pricing_snapshot` congela política, versão, base e tarifa no fato financeiro. Publicar preço cria nova versão e encerra a vigência anterior, sem alterar seus termos. `NIGHT_LIMIT_CENTS=100000`, `NIGHT_START="20:00"`, `NIGHT_END="06:00"` e `TIMEZONE="America/Sao_Paulo"` continuam sendo parâmetros da regra noturna do produto, não preço comercial. S21 entrega dupla aprovação pelo fluxo de propostas; a publicação técnica direta permanece disponível e deve ser isolada na fronteira de serviço. |
| **D2** | **Índices de Reajuste** | Aceitar exclusivamente **`IPCA`** e **`IGPM`**. | A Selic foi descartada porque é taxa básica de juros de política monetária, e não índice de inflação contratual para reajuste de cobrança/mensalidade. |
| **D3** | **Ciclo de Vida da Conta** | Rotas `PUT /account/{account_key}/block` e `PUT /account/{account_key}/cancel` (S2b). Transições permitidas: `APPROVED → BLOCKED`, `APPROVED → CANCELLED` e `BLOCKED → CANCELLED`. `CANCELLED` é final e irreversível. | Cada transição gera evento auditável. Operações financeiras só aceitam conta `APPROVED`; transição não permitida devolve `409 QIT001019`. |
| **D4** | **Modelo de Antecipação de Recebíveis** | Antecipação lastreada em **`bank_slip_keys`** (1 a 50 chaves por chamada). Exigir `net_amount > 0`; tarifa maior ou igual ao bruto retorna `422 QIT001030` na execução e na cotação CREDIT_ADVANCE. | Lastro evita crédito por valor arbitrário; o vínculo `bank_slip.credit_advance_id` impede nova antecipação do mesmo boleto nos fluxos protegidos. Líquido positivo preserva o propósito de dar liquidez à PME, sem consumir recebível para receber zero ou perder saldo. Exemplos e critérios em 3.5.1. |
| **D5** | **Formato da Taxa do Banco Central** | Retornada em string percentual, ex: `"4.83"` (significa 4,83%). | O cálculo do novo valor utiliza `Decimal` com arredondamento *half-up* para centavos inteiros:<br>`fator = Decimal("1") + (Decimal(rate_str) / Decimal("100"))`<br>`novo_valor = int((Decimal(base_amount) * fator).quantize(Decimal("1"), rounding=ROUND_HALF_UP))` |
| **D6** | **Contratos dos Mocks (MockServer)** | Contratos fixos para os conectores externos: | **BankSlip Mock (`POST /bank-slips`):**<br>Entrada: `{ external_reference: str, installments: [{ installment_number: int, amount: int, due_date: "AAAA-MM-DD" }] }`<br>Saída: `200 { bank_slips: [{ installment_number: int, barcode: str }] }`<br><br>**CentralBank Mock (`GET /index/{IPCA\|IGPM}`):**<br>Saída: `200 { index: str, accumulated_rate: "4.83" }` |
| **D7** | **Histórico de Eventos Visível por HTTP (R4)** | `GET /account/{account_key}` expõe `status_events` da conta; `GET .../billing-plan/{plan_key}` expõe `status_events` dentro de cada boleto. | A regra R4 é verificável por HTTP porque os eventos são inspecionáveis. O formato atual é ISO 8601 sem offset, por exemplo `[{ "status": "APPROVED", "event_datetime": "2026-10-02T12:00:00.000000" }]`; consumidores não devem inferir fuso pelo texto. Evolução P1 prevê timestamps `TIMESTAMPTZ`/UTC explícitos. |
| **D8** | **Janela e Limite Noturno** | Saques e transferências noturnos têm limite de `100000` centavos (R$ 1.000,00), entre `20:00` e `06:00` do dia seguinte; depósito não é limitado. | É uma regra de negócio adotada para o desafio, inspirada no limite noturno para pessoa física; não representa implementação de Pix/TED nem certificação regulatória. A aplicação usa `TIMEZONE=America/Sao_Paulo`; somente no ambiente de teste, `NIGHT_TIME_OVERRIDE` fixa a hora sem permitir que o cliente HTTP a escolha. O pytest inicia Compose descartável com 21:00 e uma API secundária para fronteiras/horário diurno; o Compose normal mantém relógio real. |
| **D9** | **Uso da classe base `RestConnector`** | Utilizar herança da classe existente em `src/connectors/rest_connector.py`. | Centraliza timeout separado de conexão (1 s) e leitura (5 s), limitado pelo orçamento da requisição, log padronizado de ida e volta e interpretação JSON com `Decimal`. O `INTERNAL-TOKEN` **não** é enviado automaticamente a APIs externas; somente um contrato explícito de serviço interno pode exigi-lo. |
| **D10** | **Identidade e sessões** | Um `app_user` pertence a uma PME (`customer`) por `user_customer_access`; portanto seu vínculo alcança as contas da PME. A senha usa bcrypt. Login cria sessão persistida por dispositivo, JWT de acesso de 15 minutos (configurável) e refresh token opaco, rotativo e válido por no máximo 8 horas. Papéis: `OWNER`, `OPERATOR`, `VIEWER`. | `INTERNAL-TOKEN` permanece a credencial serviço-a-serviço e não é login nem API Gateway. Em rotas financeiras, a ausência de `Authorization` preserva a chamada técnica interna; se `Authorization: Bearer <JWT>` vier, a sessão ativa e o papel sobre a conta são obrigatórios. `OWNER` administra ciclo de vida; `OWNER`/`OPERATOR` movimentam e emitem cobrança; os três podem consultar. |
| **D11** | **Auditoria verificável** | `audit_event` é uma cadeia global append-only: ator (`SERVICE` ou `USER`), ação, tipo/chave de recurso, `request_id`, IP de origem, resumo anterior/posterior, timestamp, `previous_hash` e `event_hash`. A cadeia começa em 64 zeros e usa SHA-256 sobre JSON canônico UTF-8. | A inserção adquire `pg_advisory_xact_lock`, evitando bifurcação sob concorrência; o evento entra na mesma transação do fato de negócio. Trigger PostgreSQL recusa `UPDATE`/`DELETE`; correção exige evento compensatório. `GET /audit-events` exporta os dados e `GET /audit-events/checkpoint` expõe a ponta para verificação externa. Isto não é blockchain: não há consenso distribuído nem imutabilidade contra um administrador do próprio banco. |
| **D12** | **Observabilidade e limites de espera** | Logs JSON no stdout com `request_id`, método, rota-modelo, status, duração, conta mascarada e usuário mascarado quando o JWT é válido. `GET /metrics` expõe Prometheus: requisições/latência, QIT, falhas de conectores, replay idempotente, duração de aquisição de travas e sessões ativas. Conectores têm conexão de 1 s e leitura de 5 s; cada transação PostgreSQL recebe `lock_timeout` de 2 s e `statement_timeout` de 10 s, todos limitados pelo orçamento de requisição de 15 s. | Rótulos são somente método, rota-modelo, status, código QIT, conector, escopo e operação: **nunca** e-mail, CPF/CNPJ, token, `request_id`, IP, chave de conta ou query string. Falha externa devolve `502 QIT001009`; espera/execução PostgreSQL esgotada devolve `503 QIT001024`, sempre correlacionável por `X-Request-ID`. Uma interrupção ou timeout no cliente não informa se houve commit: operação financeira só pode ser repetida com a mesma `Idempotency-Key`. |
| **D13** | **Alertas e notificações confiáveis** | Bloquear ou cancelar uma conta grava `outbox_event` na mesma transação do status e da auditoria. O worker separado reclama eventos por *lease*, faz `POST` ao webhook com `Idempotency-Key = event_key` e marca sucesso; falha preserva o evento, incrementa tentativa e agenda retentativa exponencial. | Não há chamada de e-mail/webhook dentro do controller antes do commit. A entrega é **pelo menos uma vez**: queda após o webhook aceitar pode reenviar a mesma chave, que o consumidor deve deduplicar. Métricas de outbox, HTTP 5xx, conector e lock alimentam regras Prometheus documentadas; CPU/memória dependem de coletor do runtime (ex.: cAdvisor), não da API. |
| **D14** | **Risco e habilitação por PME** | `risk_policy` versão regras padrão ou específicas: habilitação de `TRANSFER`, `BILLING_PLAN` e `CREDIT_ADVANCE`; teto por transferência; teto diário de transferências; teto de valor e quantidade de boletos por antecipação. A regra específica vigente vence a padrão. | A decisão gera `risk_policy_snapshot` com versão e limites. Para transferência, `customer_daily_outgoing` é atualizado na mesma transação; uma trava advisory por PME/data serializa contas distintas da mesma PME. O consumo diário é o **valor principal transferido**, não a tarifa comercial, que é fato separado no ledger. Publicação encerra a vigência anterior e cria nova versão; S21 entrega aprovação maker-checker para propostas específicas de PME; as rotas técnicas diretas não exigem essa aprovação. |
| **D15** | **Cotação informativa, execução autoritativa** | `POST /account/{account_key}/quote` persiste por 60 segundos uma prévia de `TRANSFER`, `BILLING_PLAN` ou `CREDIT_ADVANCE`: bruto, tarifa, líquido, versões de preço/risco e limites. | A cotação não reserva saldo, limite, boleto, preço ou capacidade externa. As rotas financeiras não aceitam `quote_key` nem tarifa no payload: no commit elas recalculam preço e risco vigentes. Isso evita usar uma cotação expirada, manipulada ou de payload distinto como fonte de verdade. |
| **D16** | **Maker-checker de política por PME** | `policy_change_request` guarda a proposta de preço ou risco em `DRAFT`, depois `PENDING_APPROVAL`, e somente publica `ACTIVE` após outro `OWNER` da mesma PME aprovar. | A proposta pendente não cria nem altera `pricing_policy`/`risk_policy`, logo não pode afetar operação financeira. O criador não pode aprovar a própria proposta (`QIT001029`); `FOR UPDATE` na proposta faz duas aprovações concorrentes resultarem em uma publicação. Eventos de rascunho, submissão e aprovação entram na cadeia `audit_event` com ator JWT. |

---

### Limite entre contrato atual e evolução planejada

**Enquadramento da entrega: garantias verificadas e limitações conhecidas.**
Cada garantia é vinculada a mecanismo, cenário de teste e fronteira de confiança;
não se afirma segurança absoluta, cobertura exaustiva ou proteção contra
administrador do banco. Backlog e decisões aprovadas ainda sem implementação
são identificados como pendentes, não garantias já aplicadas.

O catálogo e os contratos de rota abaixo descrevem a API implementada, inclusive
D10–D16 e a regra de líquido positivo da D4 detalhada em 3.5.1. Essa regra
está entregue; as demais fronteiras econômicas de P0.4 permanecem pendentes.
A outbox não expõe uma rota pública: seu webhook contém `event_key`,
`topic`, `aggregate_type`, `aggregate_key` e `payload`; o único tópico entregue
é `account.status_changed` (bloqueio/cancelamento). Não existe campo explícito
de versão do envelope, nem infraestrutura Prometheus/Alertmanager instalada.

O deploy contém **um serviço HTTP modular e um worker**, compartilhando banco
e código; não há API Gateway implementado ou decomposição em microserviços.
O `INTERNAL-TOKEN` concede autoridade técnica ampla, inclusive cadastro de
OWNER e publicação direta de preço/risco. JWT restringe somente as rotas que
executam autorização de conta e as propostas maker-checker; clientes remotos
devem entrar por uma fronteira que imponha JWT e nunca divulgue o token interno.
Esse gateway é dependência futura, não garantia desta entrega.

Dinheiro usa centavos inteiros `BIGINT`; porcentagens comerciais usam pontos-base
inteiros (`INTEGER`) e índices externos usam `Decimal`/`NUMERIC(12,8)` com
half-up. A restrição financeira a `float` não se aplica a segundos/latências.
O validador JSON exige `int` nativo para campos `integer`, inclusive aninhados.
Limites de overflow em somas e resultados derivados continuam sendo hardening.

A janela noturna D8 é uma **regra do produto deste desafio**, aplicada por
operação a saques/transferências de todas as contas; não é uma afirmação de
conformidade regulatória para Pix/TED. O consumo diário D14 inclui apenas o
principal das transferências, usa atualmente `date.today()` do runtime e não
inclui saques ou tarifas. Alinhar sua virada à configuração `TIMEZONE` é pendência.

**D8 — exemplo e prova sem depender do horário do avaliador:** com saldo
suficiente para principal e tarifa, uma transferência de R$ 1.000,01 às 19:59
pode ser confirmada; uma nova operação às 20:00 é recusada com QIT001007. Às
05:59 o teto ainda vale, às 06:00 já não vale. R$ 1.000,00 é permitido à noite:
a tarifa de transferência de R$ 1,00 não faz parte do principal limitado.
Depósito acima do teto continua permitido. A rejeição não grava débito/tarifa
nem consome a chave; replay confirmado de dia devolve a resposta original à
noite, sem segunda movimentação. Esses são cenários HTTP efetivamente testados,
não espera/retry de negócio para aguardar a virada do relógio.

O `pytest` padrão inicia `docker-compose.test.yml` com projeto UUID, portas
aleatórias locais e banco/MockServer novos; principal em 21:00 e `api-clock`
para 19:59/20:00/00:00/05:59/06:00/12:00. Configuração automática ocorre na
criação do container, não via parâmetro HTTP. O Compose de desenvolvimento
permanece com relógio real e não é reiniciado. Bootstrap Docker é evidência de
infraestrutura; testes do domínio continuam sem importar a aplicação e fazem
asserções por HTTP. Limites de cleanup e opção externa avançada constam no
[README](../baas-pme-api/README.md#relógio-determinístico-e-isolamento-automático);
resultado datado em [COBERTURA](COBERTURA.md#relógio-determinístico-e-bootstrap-automático--10102026).

`audit_event` recusa UPDATE/DELETE por trigger; ledger, eventos de status e
snapshots dependem de disciplina da aplicação. O usuário PostgreSQL local é
privilegiado e pode alterar schema/triggers. `audit_event_id` é sequencial,
exposto intencionalmente somente na exportação/checkpoint administrativo; os
DTOs financeiros expõem UUID. UUID dificulta enumeração, mas a proteção contra
IDOR vem de autorização e consultas vinculadas à conta.

Preço e risco ainda têm cálculo/validação de negócio dentro de repositories;
`utils/audit.py` executa SQL para encadear eventos. Separar essas responsabilidades
é pendência arquitetural. Um commit financeiro confirma fato, saldo, snapshots,
resposta idempotente e auditoria; o worker tem transações próprias de claim e ack.

Logs normais não incluem body e mascaram conta/usuário; isso não prova
sanitização universal. Tracebacks de erros inesperados (inclusive ASGI/Uvicorn)
podem incluir mensagem/parametrização SQL, e exceções externas podem conter
URLs. Hardening P1.11 exige uma allowlist de diagnóstico e testes de stdout/
stderr com marcadores sensíveis sintéticos. Resposta HTTP de erro inesperado
é sanitizada no cenário de infraestrutura já testado.

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

Catálogo vigente: **40 códigos**, sendo 30 do produto (`QIT001001`–`QIT001030`),
seis globais e quatro do legado. `QIT000010` é global, embora seu cenário de
teste atual pertença ao legado. A matriz de cenários está em
[COBERTURA](COBERTURA.md#complemento-do-catálogo-códigos-transversais-e-legado).

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
| **QIT001026** | `409 Conflict` | `ProductNotEnabled` | A política de risco vigente da PME desabilitou o produto solicitado (`TRANSFER`, `BILLING_PLAN` ou `CREDIT_ADVANCE`). |
| **QIT001027** | `422 Unprocessable` | `RiskLimitExceeded` | Valor por transferência, teto diário de transferências, valor de antecipação ou quantidade de boletos excede a política de risco vigente. |
| **QIT001028** | `404 Not Found` | `PolicyChangeRequestNotFound` | Proposta de alteração de política inexistente. |
| **QIT001029** | `409 Conflict` | `MakerCheckerViolation` | Autoaprovação, aprovação sem submissão, submissão por outro criador ou nova aprovação de proposta já ativa. |
| **QIT001030** | `422 Unprocessable` | `NonPositiveCreditAdvance` | Tarifa calculada maior ou igual ao bruto selecionado: nova antecipação ou cotação CREDIT_ADVANCE teria líquido zero/negativo, independentemente do saldo anterior. |

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

A cotação permite os três papéis, pois é uma prévia informativa. Cadastro/
consulta de cliente, abertura de conta, cadastro de usuário, políticas diretas,
exportação de auditoria e métricas são operações técnicas com token interno,
sem RBAC JWT próprio. `OWNER` não significa poder sobre outras PMEs.
Todos os endpoints que usam PostgreSQL podem devolver `503 QIT001024`;
transações e antecipações também podem devolver `503 QIT001025` após esgotar
retry de `40P01`/`40001`. `500 QIT000500` é contingência inesperada, não regra de negócio.

Os exemplos abaixo são ilustrativos, não uma sequência única de operações.
Arrays de boletos são abreviados a um item: o lote real retorna 12 novos
boletos; a consulta do plano retorna todos os boletos já emitidos. Valores de
data/chave devem ser ajustados ao cenário do integrador; a data de primeiro
vencimento não pode estar no passado. Nas listas por rota, acrescente os erros
transversais de autenticação/banco descritos acima.

---

### 3.1. Clientes (`/customer`)

#### `POST /customer`
- **Cabeçalhos:** `INTERNAL-TOKEN`
- **Body de Entrada:**
  ```json
  {
    "name": "Academia Boa Forma Ltda",
    "email": "contato@boaforma.com.br",
    "document_number": "12.345.678/0001-95"
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
    "document_number": "12.345.678/0001-95",
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
- **Erros Possíveis:** `400 QIT000001`, `400 QIT001018`, `403 QIT000002`, `404 QIT001002`, `409 QIT001006`, `409 QIT001008`, `422 QIT001005`, `422 QIT001007`, `422 QIT001012`; para TRANSFER, também `409 QIT001026` e `422 QIT001027` por habilitação/limites de risco.

#### `GET /account/{account_key}/transaction/{transaction_key}`
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "transaction_key": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "type": "TRANSFER_OUT",
    "amount": -20000,
    "balance_after": 30000,
    "operation_key": "c9d1b5a0-5a1c-4be7-bd19-1e40f9552a79",
    "counterparty_account_key": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
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
        "counterparty_account_key": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
        "created_at": "2026-10-02T15:10:00.000000"
      }
    ],
    "page": 0,
    "limit": 10,
    "is_last_page": false
  }
  ```
- **Campos dos lançamentos:** `amount` tem sinal contábil (débito negativo,
  crédito positivo); `balance_after` é o saldo após aquele lançamento.
  `counterparty_account_key` aparece somente em TRANSFER_OUT/TRANSFER_IN,
  quando há contraparte; o lançamento separado de tarifa não o inclui.
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
    "issuance_fee_amount": 0,
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
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001002`, `409 QIT001006`, `409 QIT001026`, `422 QIT001005` (saldo para a tarifa de emissão), `422 QIT001017`, `502 QIT001009`.

#### `GET /account/{account_key}/billing-plan/{plan_key}`
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "plan_key": "7b1c3e5a-4f8d-4a9c-9e2b-1a3d5e7f9a1b",
    "account_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "base_amount": 15000,
    "issuance_fee_amount": 0,
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
        "batch_number": 1,
        "adjustment_rate": null,
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
- **Campos do boleto na consulta:** `batch_number` identifica lote 1 ou 2;
  `adjustment_rate` é `null` no lote inicial e string percentual no reajustado.
  `credit_advance_key` aparece somente quando há vínculo de antecipação;
  antecipar não altera o status PENDING para PAID.
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
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001002`, `404 QIT001013`, `409 QIT001006`, `409 QIT001014`, `409 QIT001026`, `422 QIT001005` (saldo para a tarifa do lote), `502 QIT001009`.

---

### 3.5. Antecipação de Recebíveis (`/credit-advance`)

> **Fronteira de produto:** `billing-plan` representa a cobrança que a PME
> emissora fará aos seus próprios pagadores e cria recebíveis `PENDING`.
> `credit-advance` não cria um empréstimo: recebe chaves desses boletos,
> confirma que pertencem à conta solicitante e os vincula uma única vez como
> lastro para creditar liquidez à mesma PME. Pagador, baixa do boleto,
> principal livre, juros parcelados e amortização estão fora deste contrato.

#### `POST /account/{account_key}/credit-advance`
- **Cabeçalhos Obrigatórios:** `INTERNAL-TOKEN`, `Idempotency-Key: <string de 1 a 64 caracteres>` (UUID é aceito, mas não obrigatório).
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
- **Erros Possíveis:** `400 QIT000001`, `400 QIT001018`, `403 QIT000002`, `404 QIT001002`, `404 QIT001015`, `409 QIT001006`, `409 QIT001008`, `409 QIT001016`, `422 QIT001030` (além dos limites de produto/risco `QIT001026`/`QIT001027`).

#### 3.5.1. Líquido positivo: regra implementada e validada

**Decisão aprovada pelo responsável pelo produto em 2026-10-10:** uma nova
antecipação somente pode ser confirmada se entregar **pelo menos um centavo
líquido** à PME. Antecipar um recebível não deve consumir esse lastro para
entregar zero, nem reduzir um saldo que a PME já tinha.

**Estado desta decisão:** implementada em 2026-10-10, mediante autorização
específica posterior à exclusão geral da seção 9.5. A regra compartilhada em
`controllers/credit_advance_rules.py` protege criação e cotação CREDIT_ADVANCE;
ambas retornam **422/QIT001030** quando o líquido não é positivo. O restante
de P0.4/9.5 permanece pendente; não se estende esta regra à cotação TRANSFER.

O cálculo usa a soma de todos os boletos selecionados e a política vigente:

```text
gross_amount = soma dos valores dos boletos, em centavos inteiros
fee_amount = fixed_fee_cents
             + half_up(gross_amount × percentage_basis_points / 10000)
net_amount = gross_amount - fee_amount
permitir somente net_amount > 0
recusar se fee_amount >= gross_amount
```

O half-up é aplicado com Decimal ao componente percentual, produzindo
centavos inteiros. A comparação acontece **depois do arredondamento**:
comparar apenas o percentual não cobre tarifas fixas ou combinadas.
O limite é o bruto total da seleção, não o valor isolado de cada boleto.

**Exemplo prático: PME antecipa um boleto de R$ 100,00.** Estes valores são
cobertos pelos cenários HTTP da regra e pelos testes anteriores de tarifa de 3%.

| Bruto | Tarifa calculada | Líquido calculado | Resultado da regra implementada |
|---|---|---|---|
| R$ 100,00 (10000 centavos) | R$ 3,00 (300) | R$ 97,00 (9700) | Pode prosseguir, se lastro/risco/estado também forem válidos |
| R$ 100,00 (10000) | R$ 99,99 (9999) | R$ 0,01 (1) | Pode prosseguir: líquido estritamente positivo |
| R$ 100,00 (10000) | R$ 100,00 (10000) | R$ 0,00 (0) | 422/QIT001030: consome recebível sem dar liquidez |
| R$ 100,00 (10000) | R$ 120,00 (12000) | −R$ 20,00 (−2000) | 422/QIT001030: a antecipação reduziria dinheiro já existente |

**Por que o saldo disponível não resolve o último caso?** Com R$ 500,00
anteriores, creditar R$ 100,00 e cobrar R$ 120,00 deixaria R$ 480,00, além de
vincular o boleto como já antecipado. Os lançamentos poderiam ser matematicamente
coerentes e o saldo continuar positivo, mas a operação contrariaria o propósito
econômico do produto. Esse era um caminho possível antes da correção. Agora,
a API responde 422 e os R$ 500,00 permanecem intactos, assim como o boleto;
o teste também cobre saldo anterior zero. No passo Red, tarifa igual ao bruto
retornou 201 e tarifa maior, sem saldo anterior, retornou 500. A recusa explícita
agora antecede o lançamento, sem depender do CHECK de saldo não negativo.

**A regra não proíbe personalização de preços.** Uma tarifa fixa de R$ 120,00
pode ser economicamente válida para um bruto de R$ 1.000,00 (líquido R$ 880,00)
e inválida para R$ 100,00. Portanto, sua publicação não deve ser rejeitada
apenas por ultrapassar um boleto hipotético; cada operação deve validar o
resultado da política efetivamente escolhida.

**Comportamento implementado:**

1. Após validar/proteger lastro e resolver preço/risco vigentes, calcular o
   líquido e recusá-lo se não positivo, **antes** de criar a antecipação,
   vincular boletos ou lançar crédito/tarifa.
   A política é consultada e sua tarifa calculada **antes** de gravar o
   snapshot de preço; o snapshot usa exatamente essa escolha, sem nova
   resolução. Uma tarifa fixa BIGINT válida pode somar um percentual e
   ultrapassar BIGINT: se já inviabiliza o líquido, retorna QIT001030 antes
   de tentar persistir essa tarifa. Isso não define os limites numéricos
   gerais ainda pendentes em P0.3/P0.4.
2. Aplicar a mesma recusa à cotação `CREDIT_ADVANCE`; uma cotação não deve
   apresentar líquido zero/negativo como antecipação elegível. A execução
   continua recalculando a regra vigente, sem confiar em cotação antiga.
3. Responder **HTTP 422/QIT001030 — NonPositiveCreditAdvance**,
   mantendo `{ title, description, translation, code }` e `X-Request-ID`.
   Não reutilizar `InsufficientBalance`, pois a recusa vale mesmo com saldo
   disponível. É falha de negócio e não aciona retry de 40P01/40001.
4. Não confirmar efeito financeiro, consumo de lastro, snapshots ou reserva
   idempotente da tentativa recusada; não registrar evento de antecipação
   criada. Logs/métricas devem permitir correlacionar a recusa sem PII.
5. Preservar o replay de uma operação já confirmada: a mesma chave/corpo
   devolve a resposta original, sem recalcular para criar outro fato. Uma
   tentativa recusada pode usar a mesma chave/corpo após uma política válida
   entrar em vigor, pois não confirmou uma operação.
6. Complementar a validação no banco com `CHECK (net_amount > 0)` de
   antecipação, preservando `net_amount = gross_amount - fee_amount`.
   A cotação tem CHECK condicional apenas para CREDIT_ADVANCE. Models e DDL
   inicial reproduzem essas constraints. A migração pontual
   `database/migrations/20261010_positive_credit_advance_net.sql` inspeciona
   o histórico, instala CHECKs NOT VALID (protegem novas gravações) e os
   valida somente se não houver legado incompatível. Não apaga, reprifica
   ou corrige silenciosamente fatos; reconciliação exige procedimento autorizado.

**Critérios de aceitação:** testar tarifa menor/igual/maior que bruto,
líquido mínimo de um centavo, tarifa fixa/percentual/combinada, arredondamento,
saldo anterior zero e suficiente, múltiplos boletos, cotação/execução e replay.
Recusas devem deixar saldo/extrato/lastro inalterados; erro de negócio não deve
disparar retry transitório. As condições válidas continuam exigindo as demais
regras de propriedade, status e risco, não apenas líquido positivo.

**Resposta de recusa** (422; `X-Request-ID` no cabeçalho):

```json
{
  "title": "Non-positive credit advance",
  "description": "The credit advance fee must be lower than the gross amount.",
  "translation": "A antecipação deve gerar um valor líquido maior que zero; a tarifa deve ser menor que o valor bruto.",
  "code": "QIT001030"
}
```

**Evidência:** 36 cenários HTTP em `credit_advance/test_positive_net.py` e
16 contratos SQL/migração em `credit_advance/test_positive_net_database.py`.
Estes últimos não são classificados como caixa-preta HTTP. Conferem rollback
de snapshots, reserva idempotente, quote, ledger, saldo, lastro e auditoria;
constraints em INSERT/UPDATE, upgrade limpo, legado preservado e reexecução
idempotente da migração. A contagem de snapshots inclui o fallback
`customer_id IS NULL`. Resultados datados em COBERTURA; upgrade em README da API.

---

### 3.6. Identidade e sessões (`/user`, `/auth`)

#### `POST /user`
- **Cabeçalhos:** `INTERNAL-TOKEN`
- **Body de Entrada:** `customer_key`, `name`, `email`, `password` (mínimo 8
  caracteres e máximo **72 bytes UTF-8**) e `role` opcional (`OWNER` por padrão;
  `OPERATOR` ou `VIEWER`). Senha multibyte acima do limite retorna `400 QIT000001`
  no cadastro; no login retorna `401 QIT001021`, sem truncamento silencioso.
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
  ponta atual (`audit_event_id` sequencial administrativo, `event_hash`). A
  exportação atual não tem paginação e inclui todos os tenants. Não há rota de alteração ou
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
  `baas_database_lock_wait_seconds`, `baas_active_user_sessions`,
  `baas_database_transient_retries_total`, `baas_outbox_pending_events`,
  `baas_outbox_retrying_events` e `baas_outbox_delivery_attempts_total`.
  O registry HTTP é por processo e reinicia com a API; gauges de sessões e
  outbox são lidos do banco durante a coleta. Não há coletor CPU/RAM na API.
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
  aceita `TRANSFER`, `CREDIT_ADVANCE` e `BANK_SLIP_ISSUANCE`;
  `fixed_fee_cents` é montante em centavos inteiros não negativos e
  `percentage_basis_points` é taxa inteira de 0 a 10000 bps (não dinheiro).
  A tarifa efetiva é `fixa +
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
  aprovação maker-checker já foram entregues na S21. Esta rota direta continua
  sendo bootstrap técnico e **permite contornar** a dupla aprovação; restringi-la
  na fronteira de produção é requisito pendente.
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001001`.

---

### 3.10. Política de risco e produto (`/risk-policy`)

#### `POST /risk-policy`
- **Cabeçalhos:** `INTERNAL-TOKEN`.
- **Body de Entrada:**
  ```json
  {
    "customer_key": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "transfer_enabled": true,
    "billing_plan_enabled": true,
    "credit_advance_enabled": true,
    "max_transfer_amount": 500000,
    "daily_outgoing_limit": 1000000,
    "max_credit_advance_amount": 2000000,
    "max_advance_bank_slips": 20
  }
  ```
  `customer_key` ausente ou `null` cria a regra padrão. Valores monetários são
  centavos inteiros não negativos; `max_advance_bank_slips` está entre 1 e 50.
- **Resposta Sucesso (`201 Created`):** `policy_key`, `customer_key`,
  `version`, habilitações, quatro limites e `effective_from`.
- **Semântica:** a regra específica vigente vence a padrão. Publicar uma nova
  versão encerra a vigência anterior do mesmo escopo sem alterar seus termos.
  Transferências atualizam o consumo diário por PME dentro do mesmo commit;
  portanto duas contas da mesma PME não ultrapassam o teto em conjunto. A
  decisão e seu consumo antes/depois ficam em snapshot e no `audit_event`.
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001001`.

---

### 3.11. Cotação informativa (`/quote`)

#### `POST /account/{account_key}/quote`
- **Cabeçalhos:** `INTERNAL-TOKEN`; JWT opcional para ator técnico e obrigatório
  para autorização quando enviado (`OWNER`, `OPERATOR`, `VIEWER` da PME).
- **Body de Entrada:** para `TRANSFER`, `{ "operation": "TRANSFER",
  "amount": 20000 }`; para `BILLING_PLAN`, o mesmo formato com o valor de
  cada uma das 12 parcelas; para `CREDIT_ADVANCE`,
  `{ "operation": "CREDIT_ADVANCE", "bank_slip_keys": ["..."] }`.
- **Resposta Sucesso (`201 Created`):** `quote_key`, `operation`,
  `gross_amount`, `fee_amount`, `net_amount`, chave/versão de política de
  preço e risco, `expires_at` e `informative: true`. Transferência inclui
  consumo/restante diário; cobrança inclui `installments_count`; antecipação,
  `bank_slips_count`.
- **Semântica de segurança:** expira 60 segundos após criação e existe para
  rastreabilidade e interface do integrador. Não é reserva nem autorização:
  os endpoints de escrita não recebem `quote_key` e recalculam a decisão
  vigente no commit. O cliente nunca envia `fee_amount` como dado confiável.
- **Erros Possíveis:** `400 QIT000001`, `403 QIT000002`, `404 QIT001002`,
  `404 QIT001015`, `409 QIT001016`, `409 QIT001026`, `422 QIT001027`,
  `422 QIT001030` (somente CREDIT_ADVANCE).

---

### 3.12. Governança comercial (`/policy-change-request`)

#### `POST /policy-change-request`
- **Cabeçalhos:** `INTERNAL-TOKEN` e JWT de `OWNER` da PME.
- **Entrada:** `customer_key`, `policy_type` (`PRICING` ou `RISK`) e `policy`.
  O objeto `policy` reutiliza o schema estrito da publicação correspondente,
  sem `customer_key` aninhado: o tenant é determinado exclusivamente pela raiz.
- **Saída `201`:** `request_key`, `policy_type`, `status: "DRAFT"`,
  `published_policy_key: null`, `submitted_at: null`, `approved_at: null`.
- **Erros:** `400 QIT000001`, `401 QIT001020`, `403 QIT000002/QIT001022`,
  `404 QIT001001`. Não publica política nem altera tarifa/limite.

#### `PUT /policy-change-request/{request_key}/submit`
- **Entrada:** chave e JWT do criador OWNER; sem body de domínio.
- **Saída `200`:** mesmo DTO, `PENDING_APPROVAL` e `submitted_at` preenchido.
- **Erros:** `401 QIT001020`, `403 QIT000002/QIT001022`, `404 QIT001028`,
  `409 QIT001029` se não for rascunho ou ator não for criador.

#### `PUT /policy-change-request/{request_key}/approve`
- **Entrada:** chave e JWT de outro OWNER da mesma PME.
- **Saída `200`:** `ACTIVE`, `approved_at` e `published_policy_key` preenchidos;
  publica uma nova versão de preço ou risco no mesmo commit da aprovação.
- **Erros:** `401 QIT001020`, `403 QIT000002/QIT001022`, `404 QIT001028`,
  `409 QIT001029` para autoaprovação/estado incompatível. Duas aprovações
  concorrentes geram um `200` e um `409`, com uma única versão publicada.
- **Limites:** não existem rotas de editar/rejeitar/retirar uma proposta.
  `RETIRED` e `retired_at` existem no DDL, sem fluxo HTTP implementado. A
  exportação de auditoria identifica criador e aprovador; o DTO da proposta
  não retorna seus IDs internos. Sessão revogada nesse fluxo atualmente pode
  devolver `403 QIT001022`, diferença a alinhar com as rotas de conta (`401`).

## 4. Evidências, alternativas preservadas e referências técnicas

Os resultados atuais e a matriz de testes estão em [COBERTURA.md](COBERTURA.md).
O [checkpoint T3.1](PLANO_DE_EXECUCAO.md#13-checkpoint-histórico-t31), preservado na seção 13 do plano, é histórico, não catálogo vigente.

**Reajuste sob demanda versus agendado:** o reajuste agendado foi descartado
porque exigiria scheduler, política de execução/recuperação e controle temporal
não pedidos pelo desafio; ganharia se o produto exigisse atualização automática
em uma data contratual. O endpoint atual mantém o acionamento explícito,
consultando o índice e emitindo o lote 2 uma única vez no estado local.
Isso não garante exatamente uma emissão externa após queda entre conector e commit.

**Erros transversais:** todas as rotas protegidas podem responder
`403 QIT000002`; as rotas com JWT opcional validam-no quando fornecido,
podendo responder `401 QIT001020` ou `403 QIT001022`. O fluxo maker-checker
exige JWT. Operações de banco também podem retornar `503 QIT001024`
e operações cobertas pelo retry transacional, `503 QIT001025` ao esgotá-lo.
Cobrança/reajuste com emissão tarifada podem falhar por saldo insuficiente
(`422 QIT001005`) ou conta não aprovada (`409 QIT001006`); habilitação e
limites acrescentam `QIT001026`/`QIT001027` nos fluxos pertinentes.
As listas de erros por endpoint complementam, sem excluir, essas condições
transversais. As tabelas resumidas da RFC não substituem este catálogo.

**Segurança de dependências:** requests foi atualizado de 2.32.3 para 2.32.4
para corrigir o caso de vazamento de credenciais de `.netrc` por URL maliciosa
[documentado pelo mantenedor](https://github.com/psf/requests/security/advisories/GHSA-9hjg-9r4m-mvj7).
Isso corrige esse aviso específico, não substitui auditoria periódica de toda
árvore de dependências. `pip check` verifica compatibilidade, não CVEs.

Referências primárias para defender o contrato:

- [PostgreSQL: locks explícitos e compatibilidade de modos](https://www.postgresql.org/docs/16/explicit-locking.html): a ordenação reduz deadlocks entre contas; não promete ausência universal de deadlocks.
- [bcrypt: limite de senha](https://github.com/pyca/bcrypt#maximum-password-length): a API rejeita mais de 72 bytes UTF-8 antes do hash, em vez de truncar silenciosamente.
- [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html): o formato QIT foi mantido por decisão do time; não implementa integralmente Problem Details.
