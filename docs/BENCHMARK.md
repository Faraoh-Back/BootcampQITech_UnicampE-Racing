# Benchmark reproduzível de concorrência — T4.5

## 1. Objetivo e limite da evidência

Este documento mede o cenário mais sensível de concorrência já provado pela
S7c: transferências A→B e B→A acontecendo ao mesmo tempo. Ele responde duas
perguntas diferentes, que não devem ser confundidas:

1. **Correção:** a carga termina sem deadlock e preserva o invariante de
   dinheiro. Isso é obrigatório e é decidido pelo teste.
2. **Comportamento operacional:** qual foi a duração de parede e qual foi a
   utilização observada dos containers nesta máquina. Isso é comparável apenas
   entre execuções de ambiente equivalente; não é capacidade garantida nem SLO
   de produção.

O benchmark não mede Internet, proxy, autenticação remota, e-mail/webhook,
Alertmanager nem throughput sustentável. Ele mede API, PostgreSQL e MockServer
locais pelo Docker Compose, com dados sintéticos e rede local. A CPU e memória
de container são observações do runtime, não uma métrica produzida pela API.

## 2. Carga canônica

O comando executa, sem modificar o teste de produto,
`TestAdvancedConcurrency.test_cross_transfers_finish_without_deadlock_and_preserve_total_minus_fees`.
O teste é a especificação executável da carga:

| Aspecto | Valor |
|---|---|
| Repetições | 5 (`pytest.mark.parametrize(range(5))`) |
| Requisições concorrentes por repetição | 40 `POST /account/{account_key}/transaction` |
| Direções | 20 A→B e 20 B→A |
| Valor por transferência | 100 centavos |
| Tarifa por transferência | 100 centavos |
| Sincronização | `threading.Barrier(40)`; todas as threads iniciam juntas |
| Limite de cada corrida | 30 segundos |
| Sucesso funcional | 40 respostas `201`; saldo final conjunto = `20000 - (40 × 100)` |
| Proteção exercitada | ordem determinística de locks, `FOR NO KEY UPDATE`, ledger e commit transacional |

Portanto, uma execução verde não diz apenas que “foi rápida”: confirma as cinco
vezes que não houve deadlock, perda de saldo ou tarifa omitida sob a disputa
cruzada real. Uma execução que excede o timeout ou que não preserva o invariante
é regressão funcional, independentemente de CPU ou duração.

## 3. Como repetir

Pré-requisitos: Docker Engine/Compose v2, Python 3.11 e dependências em
`baas-pme-api/.venv`. A partir da pasta `baas-pme-api`:

```bash
./scripts/benchmark_concurrency.sh
```

O script faz, nesta ordem:

1. valida que `.venv/bin/python` e Docker existem;
2. cria `artifacts/benchmarks/<UTC>/` (ignorado pelo Git);
3. registra commit, estado sujo, SO, CPUs lógicas, RAM, versões Docker/Compose
   e Python;
4. sobe/reconstrói o Compose com `NIGHT_TIME_OVERRIDE=21:00` e espera
   `/health_check`;
5. salva `docker stats --no-stream` ocioso para API, PostgreSQL e MockServer;
6. amostra os mesmos três containers em NDJSON durante a carga;
7. executa a carga S7c, mede a parede ao redor do `pytest` e salva sua saída;
8. restaura o Compose sem `NIGHT_TIME_OVERRIDE`.

O script não executa `docker compose down -v`: não apaga dados locais. Se a
mudança que está sendo avaliada alterou `database/database.sql`, recrie o banco
intencionalmente antes da medição:

```bash
docker compose down -v && docker compose up -d --build
./scripts/benchmark_concurrency.sh
```

Para salvar em outro lugar, por exemplo em um disco de CI, use:

```bash
BENCHMARK_OUTPUT_DIR=/tmp/baas-benchmark ./scripts/benchmark_concurrency.sh
```

## 4. Artefatos gerados e auditoria da medição

| Arquivo | Conteúdo | Uso correto |
|---|---|---|
| `environment.txt` | instante UTC, commit, dirty count, SO, CPU, RAM, versões e carga | Só compare execuções com contexto equivalente. |
| `compose-ps.txt` / `compose-images.txt` | serviços e imagens usados | Detecta imagem, porta ou serviço diferente. |
| `docker-stats-idle.txt` | uma amostra antes da carga | Referência de repouso, não pico. |
| `docker-stats-load.ndjson` | snapshots JSON com `sampled_at_utc` durante a carga | Máximo observado, não amostragem contínua de alta frequência. |
| `pytest-s7c.txt` | resultado de correção | Deve conter cinco testes aprovados. |
| `summary.txt` | saída do pytest e duração de parede em milissegundos | Número principal para série histórica local. |

`docker stats` é intencionalmente amostrado uma vez por segundo para não
concorrer de forma relevante com a carga. Por isso, picos curtos podem não ser
vistos. Para investigação de produção, use Prometheus/cAdvisor com retenção e
resolução adequadas; não extrapole este snapshot para um limite de capacidade.

## 5. Linha de base registrada

Executada em **2026-10-09 23:03 UTC**, no commit
`099e2899fb81d07d3ac5804f516d1b88f8730017`, com duas alterações locais de
instrumentação ainda não commitadas. O código de produto é o do commit; o
estado sujo corresponde ao script/ignore da própria T4.5. Resultado:

| Campo | Observação |
|---|---|
| Host | Linux `6.1.0-49-amd64`, x86_64 |
| CPU/RAM visíveis | 16 CPUs lógicas / 15 GiB |
| Runtime | Docker Engine 29.5.3; Docker Compose 5.1.4; Python 3.11.2 |
| Imagens | API 266 MB, PostgreSQL 451 MB, MockServer 214 MB |
| Carga | 5 × 40 transferências cruzadas = 200 transferências HTTP concorrentes no total |
| Resultado funcional | `5 passed in 6.36s` |
| Duração de parede do script de carga | **6.753 s** |
| API ociosa | 0,25% CPU, 88,48 MiB RAM na amostra |
| PostgreSQL ocioso | 4,87% CPU, 51,12 MiB RAM na amostra |
| MockServer ocioso | 0,10% CPU, 243 MiB RAM na amostra |
| Maior CPU observada durante a carga | API 89,25%; PostgreSQL 49,11%; MockServer 11,34% |
| Maior memória observada durante a carga | API 114 MiB; PostgreSQL 123,7 MiB; MockServer 243,1 MiB |

As amostras de carga foram duas, em 23:03:28 e 23:03:30 UTC. O artefato local
completo é `artifacts/benchmarks/20261009T230322Z/`; ele não entra no Git porque
inclui identificadores efêmeros dos containers e números que dependem da
máquina. Os números acima são uma referência contextual, não uma promessa de
latência.

## 6. Como interpretar uma nova execução

Use esta sequência, nesta ordem:

1. **Primeiro correção.** `pytest_exit_code` diferente de zero, timeout ou
   qualquer status que não seja 40×`201` é falha de engenharia, não “variação
   de benchmark”. Pare e investigue locks, ordem de contas, pool e logs por
   `request_id`.
2. **Depois comparabilidade.** Compare commit, código sujo, Docker/Compose,
   Python, CPU, RAM, imagens, serviços ativos e se havia carga externa. Se
   algum mudou, registre como nova linha de base.
3. **Por fim duração.** Faça pelo menos três execuções quentes na mesma
   máquina e compare a mediana. Como triagem local, aumento superior a 20% da
   mediana anterior merece investigação; não é reprovação automática sem
   controlar o ambiente.
4. **Leia recursos como hipótese.** CPU alta na API com PostgreSQL baixo sugere
   overhead HTTP/Python; PostgreSQL alto e lock lento sugere disputa/consulta;
   memória que cresce a cada repetição sugere vazamento. Confirme com logs,
   `baas_database_lock_wait_seconds` e consultas de banco antes de concluir.

Exemplo: contra esta referência, uma mediana local acima de aproximadamente
8,1 s (6,753 × 1,20) deve abrir investigação, desde que todas as condições da
tabela permaneçam equivalentes. Uma máquina com menos CPUs, cgroup limitado ou
Docker Desktop não é comparável por esse limiar.

## 7. Falhas e diagnósticos rápidos

| Sintoma | Verificação | Próxima ação |
|---|---|---|
| API não fica saudável | `docker compose ps` e `docker compose logs api` | Corrija inicialização antes de medir. |
| Teste demora mais de 30 s | `docker compose logs api db`, `/metrics` e locks PostgreSQL | Procure regressão de ordem de locks/pool; não aumente o timeout para mascarar. |
| Falha de saldo ou status | `pytest-s7c.txt` e extrato da conta criada no teste | Trate como regressão funcional; não use média de duração. |
| Memória/CPU diferente | `environment.txt`, limites do Docker e processos externos | Refaça em host estável; compare apenas séries equivalentes. |
| Banco tem schema antigo | data da alteração de `database.sql` | Execute o reset de volume descrito na seção 3. |
| Amostra de CPU parece baixa | confira quantidade de linhas NDJSON e duração | O benchmark é curto; amplie a carga apenas em uma experiência separada, documentada. |

## 8. Decisões metodológicas

- Foi escolhido o teste S7c, e não um gerador artificial, porque ele preserva
  a semântica financeira e verifica o saldo final.
- A duração é de parede da suíte de carga, incluindo criação das contas e
  depósitos necessários; isso representa a jornada de integração, não latência
  isolada de uma transferência.
- O MockServer permanece no Compose para manter a topologia real do ambiente,
  embora este cenário específico não emita boletos.
- Não há limiar absoluto de RPS ou milissegundo no contrato. Fixar um número
  sem hardware, limite de cgroup e carga controlada seria uma promessa falsa.
- A T4.5 fornece método e evidência; benchmarking de produção e capacidade
  sustentada continuam exigindo observabilidade contínua e plano de carga
  próprio.
