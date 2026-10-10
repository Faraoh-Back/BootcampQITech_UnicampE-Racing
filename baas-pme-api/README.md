# BaaS PME API

API do desafio QI Tech para uma pequena empresa cobrar mensalidades, movimentar
caixa e antecipar recebíveis. Valores monetários são sempre inteiros em
centavos e toda rota, exceto `/` e `/health_check`, exige `INTERNAL-TOKEN`.
Usuários remotos também podem enviar JWT em `Authorization: Bearer`; nesse caso
a sessão e o papel na PME são validados antes do acesso à conta.

Os contratos são mantidos em [../docs/RFC.md](../docs/RFC.md) e
[../docs/DECISOES.md](../docs/DECISOES.md). Eles são a referência para regras
de negócio, payloads, códigos `QIT` e respostas de erro.

## Subir a aplicação

Pré-requisitos: Docker Compose v2 e Python 3.11.

```bash
cd baas-pme-api
docker compose up -d --build
docker compose ps
```

Espere `api` e `db` ficarem `healthy`. A API estará em
`http://localhost:3000` e o MockServer em `http://localhost:1080`.

```bash
curl http://localhost:3000/health_check
```

## Executar os testes

Os testes de produto são de integração HTTP e usam a API, PostgreSQL e
MockServer do Compose. A suíte também contém contratos de infraestrutura para
triggers, locks e worker, que podem acessar PostgreSQL de forma controlada. A
execução completa inclui a regra noturna, portanto precisa
fixar a hora de teste antes do `pytest`:

```bash
NIGHT_TIME_OVERRIDE=21:00 docker compose up -d --build
./.venv/bin/python -m pytest -q
```

Esse é o mesmo perfil adotado pelo CI. A suíte atual tem 143 testes. Depois,
restaure o relógio normal com `docker compose up -d`.

## Benchmark de concorrência

Para repetir a carga S7c canônica (cinco repetições de 40 transferências
cruzadas), com duração, versões, amostras ociosas e `docker stats` sob carga:

```bash
./scripts/benchmark_concurrency.sh
```

O resultado fica em `artifacts/benchmarks/<UTC>/`, ignorado pelo Git por ser
dependente da máquina. Leia [../docs/BENCHMARK.md](../docs/BENCHMARK.md) antes
de comparar números: a referência é evidência contextual, não um SLO.

## Recriar o banco após alterar SQL

`database/database.sql` é copiado para a imagem do PostgreSQL durante o build.
Por isso, alterar apenas o arquivo não atualiza uma imagem já existente. O
comando necessário é:

```bash
docker compose down -v && docker compose up -d --build
```

`down -v` apaga os dados locais do banco; use apenas quando esse descarte for
intencional.

## Rotas do produto

| Método | Caminho | Finalidade |
|---|---|---|
| `POST` / `GET` | `/customer`, `/customer/{customer_key}` | Cadastro e consulta de cliente. |
| `POST` | `/user` | Cadastro de usuário e vínculo inicial com a PME. |
| `POST` | `/auth/login`, `/auth/refresh`, `/auth/logout` | Sessão por dispositivo, JWT curto, rotação de refresh e revogação individual. |
| `GET` | `/audit-events`, `/audit-events/checkpoint` | Exportação da trilha append-only e ponta da cadeia SHA-256. |
| `GET` | `/metrics` | Métricas Prometheus internas de operação. |
| `POST` / `GET` | `/account`, `/account/{account_key}` | Abertura e consulta de conta. |
| `PUT` | `/account/{account_key}/block`, `/cancel` | Ciclo de vida auditável da conta. |
| `POST` / `GET` | `/account/{account_key}/transaction`, `/transaction/{transaction_key}` | Depósito, saque, transferência e consulta de lançamento. |
| `GET` | `/account/{account_key}/transactions` | Extrato paginado. |
| `POST` / `GET` | `/account/{account_key}/billing-plan`, `/billing-plan/{plan_key}` | Emissão e consulta de boletos. |
| `POST` | `/account/{account_key}/billing-plan/{plan_key}/adjustment` | Emissão do lote reajustado. |
| `POST` | `/account/{account_key}/credit-advance` | Antecipação lastreada em boletos. |

Depósito, saque, transferência e antecipação exigem `Idempotency-Key`. Uma
repetição com o mesmo payload devolve `201` e `Idempotent-Replayed: true` sem
duplicar o ledger.

## Logs e métricas

Os logs da API são JSON no stdout, correlacionados por `request_id` e sem corpo
de requisição, token, e-mail ou documento. Chaves de conta e usuário aparecem
somente mascaradas. Para consultar métricas Prometheus localmente:

```bash
curl -H 'INTERNAL-TOKEN: default_token' http://localhost:3000/metrics
```

Os rótulos das métricas não incluem dados pessoais, UUIDs, IPs ou query
strings; use a rota-modelo, status e código QIT para agregação.

## Notificações confiáveis

Bloquear ou cancelar uma conta cria uma notificação na `outbox_event` no mesmo
commit do status e da auditoria. A requisição HTTP nunca chama webhook: o
processo separado faz isso depois. Para ativá-lo localmente:

```bash
docker compose --profile workers up -d outbox-worker
```

Ou processe somente um lote, útil para diagnóstico:

```bash
docker compose --profile workers run --rm outbox-worker --once
```

O webhook recebe `Idempotency-Key` igual ao `event_key`. A garantia é entrega
**pelo menos uma vez**: o consumidor deve deduplicar essa chave. Falhas ficam
na outbox com backoff exponencial; sucesso não é reenviado. As regras
Prometheus para 5xx, conectores, lock, fila e falhas de entrega estão em
[../docs/ALERTAS.md](../docs/ALERTAS.md).

## Timeouts e repetição segura

Chamadas externas usam 1 segundo para conexão e 5 segundos para leitura;
falhas nelas retornam `502 QIT001009`. A transação PostgreSQL recebe limites
locais de 2 segundos para trava e 10 segundos para execução; se esgotar,
retorna `503 QIT001024`. Cada resposta preserva `X-Request-ID` para
correlação. O orçamento de 15 segundos reduz esses limites quando necessário.

Deadlock ou falha de serialização do PostgreSQL recebe no máximo uma nova
tentativa interna, sempre em sessão/transação nova e com a mesma
`Idempotency-Key`. A API não retenta saldo insuficiente, limite noturno, status
inválido, erros de contrato ou chamadas externas. A métrica
`baas_database_transient_retries_total` registra apenas `deadlock` ou
`serialization`, sem PII.

Se o cliente perder ou interromper a resposta de uma operação financeira, não
deve criar outra chave: deve reenviar exatamente o mesmo payload com a mesma
`Idempotency-Key`. Assim a API devolve o resultado já confirmado ou conclui uma
única vez, sem duplicar o lançamento.

## Configuração

Os valores padrão do Compose permitem iniciar sem `.env`. Para personalizar,
copie `.env.example` para `.env`. As variáveis relevantes são:

| Variável | Padrão | Uso |
|---|---:|---|
| `INTERNAL_TOKEN` | `default_token` | Token interno das rotas protegidas. |
| `JWT_SECRET` | segredo local de desenvolvimento | Chave de assinatura HS256; defina valor secreto fora do repositório em produção. |
| `JWT_ACCESS_TOKEN_MINUTES` | `15` | Vida útil do JWT de acesso. |
| `JWT_SESSION_MAX_HOURS` | `8` | Vida máxima da sessão e de seus refresh tokens. |
| `TRANSFER_FEE_CENTS` | `100` | Tarifa por transferência. |
| `ADVANCE_FEE_PERCENT` | `3` | Taxa percentual da antecipação. |
| `NIGHT_START`, `NIGHT_END` | `20:00`, `06:00` | Janela de limite noturno. |
| `NIGHT_LIMIT_CENTS` | `100000` | Limite noturno por saque ou transferência. |
| `TIMEZONE` | `America/Sao_Paulo` | Fuso do relógio de produção. |
| `NIGHT_TIME_OVERRIDE` | vazio | Hora fixa exclusiva de testes. |
| `BANKSLIP_API_CONNECT_TIMEOUT_SECONDS`, `CENTRAL_BANK_API_CONNECT_TIMEOUT_SECONDS` | `1` | Prazo de conexão dos conectores externos. |
| `BANKSLIP_API_READ_TIMEOUT_SECONDS`, `CENTRAL_BANK_API_READ_TIMEOUT_SECONDS` | `5` | Prazo de leitura dos conectores externos. |
| `DATABASE_LOCK_TIMEOUT_MS` | `2000` | Espera máxima por trava PostgreSQL por transação. |
| `DATABASE_STATEMENT_TIMEOUT_MS` | `10000` | Execução máxima de comando PostgreSQL por transação. |
| `REQUEST_TIMEOUT_SECONDS` | `15` | Orçamento máximo aplicado aos pontos bloqueantes conhecidos. |
| `DATABASE_TRANSIENT_RETRY_MAX_ATTEMPTS` | `2` | Total de tentativas para `40P01`/`40001`. |
| `DATABASE_TRANSIENT_RETRY_BASE_DELAY_MS` | `25` | Base do backoff com jitter entre tentativas transitórias. |
| `NOTIFICATION_WEBHOOK_URL` | `http://mock:1080/notifications` | Webhook que recebe eventos da outbox; em produção, serviço de notificações. |
| `OUTBOX_POLL_INTERVAL_SECONDS` | `1` | Intervalo de consulta do worker. |
| `OUTBOX_LEASE_SECONDS` | `30` | Duração do lease que impede dois workers de publicar juntos. |
| `OUTBOX_RETRY_BASE_SECONDS` | `5` | Base do backoff exponencial após falha de entrega. |

## Estrutura

- `src/resources`: camada HTTP e validação de entrada;
- `src/controllers`: regras de negócio e commits;
- `src/repositories`: consultas e travas PostgreSQL;
- `src/models`: mapeamento SQLAlchemy;
- `src/schemas`: contratos JSON de entrada;
- `tests/integration`: testes de produto por HTTP e contratos de infraestrutura;
- `database/database.sql`: DDL inicial.

As rotas `sample_entity` e seus arquivos continuam no repositório apenas como
legado do projeto-base. Não pertencem ao contrato BaaS PME e não devem ser
usadas por integrações novas.
