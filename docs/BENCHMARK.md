# Benchmark reproduzível de concorrência — T4.5

**Referência mais recente:** [seção 13](#13-fechamento-final-validação-anterior-ao-snapshot-de-preço),
10/10/2026, 09:07 UTC: 200 transferências corretas, parede **8,255 s**.
CPU/RAM, ambiente e limites estão junto dessa coleta. A linha de base da seção
5 e os registros 9–12 são históricos preservados, não resultados do código
final. A suíte de features e seus 260 testes pertencem a
[COBERTURA](COBERTURA.md#fechamento-final-snapshots-padrão-e-tarifa-extrema);
o benchmark é uma execução separada de cinco casos, não cinco features novas.

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
mudança alterou `database/database.sql`, um volume existente não é atualizado
só pelo build. Use a migração específica quando disponível (líquido positivo:
[README da API](../baas-pme-api/README.md#atualizar-banco-existente-líquido-positivo-da-antecipação)).
Alternativamente, recrie **somente um banco descartável** intencionalmente:

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

O loop espera um segundo **após** cada `docker stats --no-stream`; o comando
também leva tempo. Não é amostragem garantida a 1 Hz: o intervalo real deve
ser lido em `sampled_at_utc`, e picos curtos podem não ser vistos. A coleta
também tem overhead não isolado experimentalmente. Para investigação de produção, use Prometheus/cAdvisor com retenção e
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
| Carga | 5 repetições sequenciais de 40 transferências HTTP concorrentes = 200 operações no total; pico de concorrência = 40 |
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

Exemplo: depois de registrar pelo menos três execuções quentes equivalentes, uma
mediana local acima de 20% da mediana anterior deve abrir investigação. A
execução de 6,753 s registrada neste documento é uma linha de base individual,
não uma mediana nem um limiar de reprovação. Uma máquina com menos CPUs, cgroup
limitado ou Docker Desktop não é comparável por esse critério.

## 7. Falhas e diagnósticos rápidos

| Sintoma | Verificação | Próxima ação |
|---|---|---|
| API não fica saudável | `docker compose ps` e `docker compose logs api` | Corrija inicialização antes de medir. |
| Teste demora mais de 30 s | `docker compose logs api db`, `/metrics` e locks PostgreSQL | Procure regressão de ordem de locks/pool; não aumente o timeout para mascarar. |
| Falha de saldo ou status | `pytest-s7c.txt` e extrato da conta criada no teste | Trate como regressão funcional; não use média de duração. |
| Memória/CPU diferente | `environment.txt`, limites do Docker e processos externos | Refaça em host estável; compare apenas séries equivalentes. |
| Banco tem schema antigo | data da alteração de `database.sql` | Aplique a migração específica ou recrie somente um banco descartável, conforme seção 3. |
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

## 9. Execução de fechamento S16–S21

Uma nova execução local foi feita em **2026-10-10 01:24 UTC**, no commit
`f640832963a13fd626ebd0b575378c49d01b3851`, com três alterações documentais
locais no momento da coleta. O ambiente foi Linux x86_64, 16 CPUs lógicas, 15
GiB visíveis, Docker 29.5.3, Compose 5.1.4 e Python 3.11.2.

| Campo | Observação |
|---|---|
| Carga | 5 × 40 transferências cruzadas de 100 centavos; 200 operações |
| Correção | `5 passed in 9.45s`; `pytest_exit_code=0` |
| Duração de parede | **9,809 s** |
| Ocioso | API 0,28% / 92,37 MiB; PostgreSQL 0,21% / 45,68 MiB; MockServer 0,10% / 225,5 MiB |
| Pico amostrado | API 98,12% CPU / 111,7 MiB; PostgreSQL 58,70% CPU / 133 MiB; MockServer 9,73% CPU / 225,6 MiB |
| Artefatos locais | `baas-pme-api/artifacts/benchmarks/20261010T012431Z/` |

Esta coleta continua sendo uma observação única e local, não comparação direta
com a linha de base anterior nem SLO. Sua evidência importante é funcional: a
carga inteira terminou verde com a invariância de saldo verificada pelo teste.

## 10. Revisão completa de contratos e documentação

Executada em **2026-10-10 06:07 UTC**, base Git
`524c7608ba305978bae7c97ece7348b8961c8a6a` com **38 entradas locais modificadas/
novas** registradas pelo script. O benchmark inclui as alterações de produto
da revisão; não representa somente o código commitado. Ambiente: Linux
`6.1.0-49-amd64`, x86_64, 16 CPUs lógicas, 15 GiB visíveis, Docker 29.5.3,
Compose 5.1.4, Python 3.11.2.

| Campo | Observação |
|---|---|
| Carga | 5 × 40 transferências cruzadas; 200 operações; pico de 40 concorrentes |
| Correção | **5 passed in 11.48s**; `pytest_exit_code=0` |
| Parede ao redor do pytest | **12,381 s** |
| API ociosa | 0,35% CPU / 89,36 MiB |
| PostgreSQL ocioso | 0,00% CPU / 54,48 MiB |
| MockServer ocioso | 0,19% CPU / 259,9 MiB |
| Maior CPU amostrada | API **105,28%**; PostgreSQL **62,16%**; MockServer **17,83%** |
| Maior RAM amostrada | API **119,7 MiB**; PostgreSQL **137,5 MiB**; MockServer **259,9 MiB** |
| Amostras completas | Quatro snapshots dos três containers, em 06:07:34, :36, :40 e :43 UTC |
| Artefatos | `baas-pme-api/artifacts/benchmarks/20261010T060725Z/` |

A configuração normal do Compose foi restaurada pelo script, sem apagar
volumes. O percentual de CPU do runtime não é percentual normalizado da
capacidade total do host; um container pode superar 100%. RAM/CPU são máximos
observados, não picos garantidos.

Esta execução é mais demorada que as referências históricas. Não se afirma
ausência de regressão nem regressão confirmada por uma amostra: faltam
execuções repetidas com cache/carga externa controlados e limites equivalentes.
O resultado funcional comprovado é 200 operações corretas, sem deadlock no
cenário testado. A suíte completa de features/pipelines está em COBERTURA;
o benchmark não a substitui.

## 11. Validação de entrega em ambiente isolado

Em **2026-10-10 07:33 UTC**, o validador T5.5 executou a carga canônica em
clone local + snapshot, venv/banco novos e Compose exclusivo. Base Git
`524c7608ba305978bae7c97ece7348b8961c8a6a`; origem com 44 entradas dirty;
checkout do benchmark com 43 entradas dirty. Os arquivos não foram commitados
e não se tratou de clone remoto publicado ou VM limpa. Linux 6.1.0-49-amd64,
x86_64, 16 CPUs lógicas, 15 GiB visíveis, Docker 29.5.3, Compose 5.1.4,
Python 3.11.2. O host/Docker/cache são compartilhados com o ambiente original.

| Campo | Observação |
|---|---|
| Carga | 5 × 40 transferências cruzadas; 200 operações; pico de 40 concorrentes |
| Correção | **5 passed in 7.14s**; pytest_exit_code=0 |
| Parede ao redor de pytest | **7,506 s** |
| API ociosa | 0,24% CPU / 100,6 MiB |
| PostgreSQL ocioso | 0,02% CPU / 44,12 MiB |
| MockServer ocioso | 0,10% CPU / 242,4 MiB |
| Maior CPU amostrada | API **83,53%**; PostgreSQL **46,64%**; MockServer **12,24%** |
| Maior RAM amostrada | API **129,1 MiB**; PostgreSQL **124,7 MiB**; MockServer **242,4 MiB** |
| Amostras completas | Três snapshots dos três containers em 07:33:16, :19 e :22 UTC |
| Artefatos | `baas-pme-api/artifacts/delivery/20261010T073026Z/benchmark/` |
| Encerramento | Somente projeto descartável removido; containers originais intactos |

O benchmark passa a respeitar `SERVER_LOCALHOST`/`API_PORT` na consulta de
saúde; a validação usou 127.0.0.1:13000, sem assumir porta 3000. Não houve
mudança na carga financeira nem na semântica da S7c. Métricas Prometheus foram
consultadas depois da suíte completa e antes de a API ser recriada para o
benchmark; não são uma coleta contínua desta carga. Regras de alerta continuam
propostas, sem stack de coletores ou teste de notificação de alerta instalado.

A amostra é mais curta que a da seção 10, mas isso **não prova melhoria**:
cache, dados, disponibilidade do host e atividade concorrente variam. CPU/RAM
são máximos observados no espaçamento real de docker stats, não picos
garantidos. A evidência funcional é a invariância financeira em 200 chamadas;
capacidade sustentável/SLO continuam fora do escopo. Resultados de todas as
features/pipelines e limites do snapshot estão em COBERTURA/ENTREGA.

## 12. Líquido positivo: regressão completa e benchmark

**Marco intermediário**, anterior à validação antes do snapshot de preço e aos
cinco casos adicionais de tarifa extrema. Preservado para rastreabilidade;
usar §13 para a medição do código final.

Em **2026-10-10 08:42 UTC**, a carga foi repetida após implementar líquido
positivo da antecipação/cotação CREDIT_ADVANCE. O benchmark permanece o mesmo
cenário de transferência; **não** mede capacidade da antecipação. A regressão
de 255 testes, incluindo essa nova regra, está em COBERTURA.

Clone local + snapshot, base `160311850dbfbc9427ed7f5049047aada951e8b3`,
27 entradas dirty na coleta; não é execução do commit remoto publicado.
Projeto `baas-delivery-20261010t083920z-x8u6peuz`, portas 13000/15432/11080,
venv/banco novos; mesmo host/cache Docker e outros projetos locais ativos.
Linux 6.1.0-49-amd64, x86_64; 16 CPUs lógicas, 15 GiB; Docker 29.5.3,
Compose 5.1.4 e Python 3.11.2.

| Campo | Observação |
|---|---|
| Carga / correção | 5×40 transferências; 200 operações; **5 passed in 7.41s**, saída 0 |
| Parede ao redor do pytest | **7,753 s** |
| API pré-carga | 0,26% CPU / 90,67 MiB |
| PostgreSQL pré-carga | 6,64% CPU / 45,05 MiB |
| MockServer pré-carga | 0,16% CPU / 221,2 MiB |
| Maior CPU amostrada | API **75,16%**; PostgreSQL **47,03%**; MockServer **10,42%** |
| Maior RAM amostrada | API **116,9 MiB**; PostgreSQL **91,16 MiB**; MockServer **221,3 MiB** |
| Amostras completas | Três snapshots dos três containers, em 08:42:17, :19 e :23 UTC |
| Artefatos | `baas-pme-api/artifacts/delivery/20261010T083920Z/benchmark/` |
| Encerramento | Projeto descartável removido; ambiente original preservado |

A amostra chamada idle pelo script é somente **pré-carga**, sem janela de
estabilização; o PostgreSQL ainda pode executar trabalho posterior às suítes.
CPU/RAM são máximos observados, não picos garantidos. A diferença de duração
para medições anteriores não prova ganho/regressão, capacidade sustentável
ou SLO: é uma coleta única no host compartilhado.

GET `/metrics` foi consultado depois da regressão completa e antes da API
recriada para o benchmark. A exposition contém QIT001030 nas duas rotas e
retries sintéticos de deadlock/serialização; não é monitoração contínua do
benchmark nem alarmes instalados. O banco original recebeu somente a migração
de CHECKs já validada em isolamento, sem reset ou reprificação de históricos.

## 13. Fechamento final: validação anterior ao snapshot de preço

Depois de reproduzir o extremo de tarifa calculada acima de BIGINT, a
antecipação passou a recusar líquido não positivo antes de persistir o preço.
O snapshot usa a mesma política/tarifa calculada. A carga abaixo foi repetida
com esse código final, após **260 testes aprovados** (75.43 s). Não mede a
capacidade da antecipação nem conclui os limites numéricos gerais de P0.4.

Coleta **2026-10-10 09:07:16–09:07:31 UTC**, base `1603118`, 30 entradas
dirty. Projeto exclusivo `baas-p04-final-20261010085856`, banco criado novo,
venv existente da API; host/cache compartilhados, Linux 6.1.0-49-amd64,
x86_64, 16 CPUs/15 GiB, Docker 29.5.3, Compose 5.1.4, Python 3.11.2.
Não é o commit publicado nem um CI remoto da revisão nova.

| Campo | Observação |
|---|---|
| Correção | **5 passed in 7.89s**, saída 0; 200 transferências |
| Parede ao redor de pytest | **8,255 s** |
| Pré-carga API / PostgreSQL / MockServer | 0,23%/89,37 MiB; 0,00%/44,7 MiB; 0,13%/240,8 MiB |
| Maior CPU amostrada API / PostgreSQL / MockServer | **87,55% / 55,92% / 11,36%** |
| Maior RAM amostrada API / PostgreSQL / MockServer | **117,7 / 79,24 / 240,8 MiB** |
| Amostras completas | Três snapshots dos três containers, em 09:07:23, :26 e :29 UTC |
| Artefatos | `baas-pme-api/artifacts/p04/20261010085856-final/benchmark/` |
| Encerramento | Projeto/dados sintéticos descartados; banco original preservado |

`metrics-final.prom` foi obtido antes da recriação da API para a carga;
contém QIT001030 nas duas rotas e retries sintéticos, não uma série contínua
do benchmark. Pré-carga não é repouso estabilizado; máximos não são picos
garantidos. Os resultados intermediários de §12/anteriores permanecem
preservados; diferenças de tempo/CPU/RAM não provam melhoria ou regressão
sem repetições equivalentes. Não há SLO ou coletores/alarmes instalados.
