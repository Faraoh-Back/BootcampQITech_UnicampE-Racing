# Histórico dos guias consolidados

Consolidação: 10/10/2026. Os três textos abaixo são preservados integralmente;
foram ajustados apenas os níveis de títulos e os caminhos dos links para
continuarem navegáveis. Instruções, exemplos e estados antigos não representam
novas garantias da API. Para operar, use o [README vigente](../../baas-pme-api/README.md).

Não execute resets de volume a partir destes guias antigos para atualizar um
banco com dados a preservar. O upgrade pontual e as instruções atuais estão no
[README da API](../../baas-pme-api/README.md#atualizar-banco-existente-líquido-positivo-da-antecipação);
o [índice](../README.md) separa contrato vigente e evidências históricas.
O corpo dos três registros abaixo permanece preservado, sem atualizar suas
contagens ou atribuir-lhes validação das features posteriores.

## Origem e navegação

| Origem anterior | Conteúdo preservado |
|---|---|
| `docs/arquivo/COMO_INICIAR_T0_1.md` | [Guia de inicialização T0.1](#guia-de-inicialização-e-setup-do-ambiente-t01) |
| `docs/arquivo/ORGANIZACAO_API_ANTERIOR.md` | [Guia de organização](#como-o-baas-pme-é-organizado) |
| `docs/COMO_INICIAR.md` | [Antigo atalho para o guia vigente](#inicialização--guia-consolidado) |

## Guia de Inicialização e Setup do Ambiente (T0.1)

> **Arquivo histórico, preservado sem descarte de conteúdo.** Este guia foi
> consolidado no README da API em 2026-10-10. Comandos, status e links abaixo
> retratam a versão anterior e podem estar desatualizados. Use
> [o guia vigente](../../baas-pme-api/README.md), não este arquivo, para operar.

Este guia foi feito para que qualquer membro do time consiga clonar o repositório e subir o ambiente local do **BaaS PME** em sua própria máquina do zero, garantindo que tudo funcione perfeitamente.

---

### 1. Pré-requisitos

Certifique-se de ter instalado na sua máquina:

- **Git**
- **Docker** e **Docker Compose** (plugin `docker compose` v2 ou superior)
- **Python 3.11** (com módulo `venv`)
- **Curl** ou navegador web (para testar os endpoints)

---

### 2. Visão Geral da Estrutura

Ao clonar o repositório, você encontrará a seguinte estrutura:

```text
.
├── baas-pme-api/           # Onde o sistema BaaS PME é de fato desenvolvido
├── bootcamp-biblioteca-api/# Projeto de exemplo/consulta da QI Tech com uso de libs
└── docs/                   # Documentação (RFC, Plano de Execução, Guias)
```

> **Atenção:** todo o trabalho de desenvolvimento e comandos Docker/Pytest serão feitos **dentro da pasta `baas-pme-api/`**.

---

### 3. Passo a Passo de Instalação (Task T0.1)

#### Passo 1: Acesse a pasta do projeto
No terminal, entre no diretório da API:
```bash
cd baas-pme-api
```

#### Passo 2: Crie o arquivo de variáveis de ambiente (`.env`)
Copie o arquivo de exemplo para criar o `.env` local:
```bash
cp .env.example .env
```
*(Os valores padrão já estão configurados para o ambiente de desenvolvimento local).*

#### Passo 3: Suba os containers com Docker Compose
Execute o build e suba os containers em segundo plano (*detached mode*):
```bash
docker compose up -d --build
```

#### Passo 4: Verifique se os serviços estão saudáveis (*healthy*)
Aguarde alguns segundos e confira o status dos containers:
```bash
docker compose ps
```
Você deverá ver ambos os containers (`api-1` e `db-1`) com status **`Up ... (healthy)`**:
```text
NAME                IMAGE              STATUS
baas-pme-api-api-1  baas-pme-api-api   Up ... (healthy)
baas-pme-api-db-1   baas-pme-api-db    Up ... (healthy)
```

Teste a resposta do endpoint de saúde:
```bash
curl -i http://localhost:3000/health_check
```
> **Esperado:** Retorno HTTP `204 No Content` (ou `200`).

---

### 4. Configuração do Python e Testes Locais

A arquitetura do projeto adota o seguinte modelo:
- A **API** e o **Banco de Dados PostgreSQL** rodam dentro do Docker.
- Os **Testes (`pytest`)** rodam na sua máquina host (fora do container), disparando requisições contra a API que está no Docker.

#### Passo 5: Crie e ative a Virtual Environment (venv)
Ainda dentro de `baas-pme-api/`:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
*(No Windows PowerShell seria: `.venv\Scripts\Activate.ps1`)*

#### Passo 6: Instale as dependências de desenvolvimento
```bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

#### Passo 7: Execute os testes automatizados
Com os containers rodando e saudáveis, fixe a hora de teste para que os casos
de limite noturno não dependam do horário em que a suíte foi iniciada:
```bash
NIGHT_TIME_OVERRIDE=21:00 docker compose up -d --build
./.venv/bin/python -m pytest -q
```
Todos os testes do BaaS PME, incluindo transações, boletos, antecipação e concorrência, devem passar em verde.

> A variável fixa somente o relógio do container de teste; em uso normal,
> deixe-a vazia para usar `TIMEZONE=America/Sao_Paulo`. Após os testes, rode
> `docker compose up -d` para restaurar o comportamento normal.

Os limites padrão de espera já vêm no Compose: 1 s para conexão externa, 5 s
para leitura, 2 s para lock PostgreSQL e 10 s por comando SQL. Para investigar
um `503 QIT001024`, use o `X-Request-ID` da resposta junto dos logs JSON da API.
Depois de uma interrupção de rede em operação financeira, repita apenas com a
mesma `Idempotency-Key`.

#### Worker de notificações (opcional)

O perfil `workers` mantém o publicador de outbox separado da API HTTP. Para
ativá-lo, configure `NOTIFICATION_WEBHOOK_URL` para o serviço destinatário e
rode:

```bash
docker compose --profile workers up -d outbox-worker
```

Ele publica somente eventos confirmados de bloqueio/cancelamento e reenvia
falhas com a mesma `Idempotency-Key`; o destinatário deve deduplicar essa chave.

#### Benchmark reproduzível de concorrência

Com a `.venv` pronta e os containers disponíveis, rode de dentro de
`baas-pme-api/`:

```bash
./scripts/benchmark_concurrency.sh
```

O script fixa a janela noturna só durante a carga, executa cinco vezes as 40
transferências cruzadas da S7c, coleta `docker stats` e restaura a configuração
normal. A leitura correta dos arquivos em `artifacts/benchmarks/` e dos limites
de comparação está em [BENCHMARK.md](../BENCHMARK.md).

---

### 5. Testando a Recriação Limpa do Banco (Passo Crítico)

Para garantir que o banco e o schema SQL são aplicados do zero corretamente:
```bash
# 1. Derruba os containers e apaga os volumes do banco
docker compose down -v

# 2. Reconstrói a imagem que contém o SQL e sobe novamente
docker compose up -d --build

# 3. Confere a saúde
docker compose ps

# 4. Roda os testes de novo com o relógio determinístico
NIGHT_TIME_OVERRIDE=21:00 docker compose up -d --build
./.venv/bin/python -m pytest -q
```
> **Por que isso é importante?** O PostgreSQL só executa o script de inicialização com o volume vazio, e o Docker só copia uma alteração de `database/database.sql` para a imagem em um novo build. Toda mudança no SQL exige `docker compose down -v && docker compose up -d --build`.

---

### 6. Comandos Úteis do Dia a Dia

| Ação | Comando |
|---|---|
| **Subir serviços em background** | `docker compose up -d` |
| **Ver logs em tempo real** | `docker compose logs -f api` |
| **Ver status e portas** | `docker compose ps` |
| **Parar os containers** | `docker compose stop` |
| **Parar e remover containers** | `docker compose down` |
| **Resetar banco de dados do zero** | `docker compose down -v` |
| **Rodar todos os testes** | `./.venv/bin/python -m pytest -q` |
| **Rodar um arquivo específico de teste** | `./.venv/bin/python -m pytest tests/integration/test_healthcheck.py` |
| **Rodar testes mostrando prints/logs** | `./.venv/bin/python -m pytest -s -v` |

#### Integração contínua

O workflow [BaaS PME CI](../../.github/workflows/baas-pme-ci.yml) roda em todo `push` e `pull request`: valida o Compose, recria API, banco e MockServer, espera o health check, compila o código e executa `pytest`. A validação local equivalente é:

```bash
docker compose down -v
NIGHT_TIME_OVERRIDE=21:00 docker compose up -d --build
./.venv/bin/python -m pytest -q
```

---

### 7. Dúvidas Frequentes e Problemas Conhecidos

#### 1. "Estou vendo logs com `GET /health_check` a cada 3 segundos com portas variando"
**É normal!** O Docker Compose possui um healthcheck configurado para testar se a API continua respondendo a cada 3 segundos. As portas diferentes que aparecem no log são portas de cliente (efêmeras) abertas para cada chamada de checagem.

#### 2. "Porta 3000 ou 5432 já está em uso na minha máquina"
Se você já tiver um Postgres ou outro serviço local usando essas portas:
- Edite o seu arquivo `.env`:
  ```ini
  API_PORT=3001
  DB_PORT=5433
  ```
- No caso do `pytest`, garanta que as variáveis de teste apontem para a porta configurada.

#### 3. "Erro: Could not import module 'app' no Uvicorn"
- Verifique se os arquivos de código dentro de `src/` terminam com `.py` e não com `_py.txt`.
- Certifique-se de que está rodando o `docker compose` a partir da pasta `baas-pme-api/` e não de outro caminho.
- Se necessário, faça um build limpo: `docker compose build --no-cache`.

---

### 8. Critério de Conclusão da Tarefa T0.1

Para considerar a **T0.1** concluída na sua máquina:
1. Tirar print do terminal executando `docker compose ps` mostrando os containers `(healthy)`.
2. Tirar print do `pytest` com todos os testes passando em verde.

---

## Como o BaaS PME é organizado

> **Arquivo histórico, preservado sem descarte de conteúdo.** A orientação
> atual de camadas, módulos, SQL e testes foi reunida no
> [README da API](../../baas-pme-api/README.md). Afirmações deste guia anterior
> não substituem os limites documentados na RFC/DECISOES vigentes.

O caminho de uma requisição do produto é sempre:

```text
HTTP -> middleware -> resource -> controller -> repository -> PostgreSQL
```

Por exemplo, `POST /account/{account_key}/transaction` valida o JSON e os
headers no *resource*, decide as regras de saldo, tarifa e idempotência no
*controller*, e usa o *repository* para obter as travas no banco. O DTO monta
o JSON de resposta. Nenhum teste de integração importa `src`: ele conversa com
a aplicação pela rede.

### Onde alterar cada coisa

| Mudança | Arquivos principais |
|---|---|
| Contrato HTTP de entrada | `src/schemas/` e `src/resources/` |
| Regra de negócio | `src/controllers/` |
| Consulta, ordenação ou lock | `src/repositories/` |
| Tabela, coluna ou restrição | `database/database.sql` e `src/models/` |
| JSON de saída | `src/dtos/` |
| Erro de domínio | `src/errors/custom_errors.py`, `docs/DECISOES.md` e testes HTTP |
| Rota nova | resource correspondente e `src/app.py` |

Os contratos de produto não ficam apenas neste guia: a RFC descreve o desenho
e fluxos, e `DECISOES.md` mantém a especificação de payloads e erros.

### Banco e reconstrução

O DDL é executado somente quando o volume PostgreSQL nasce. Além disso,
`database.sql` é copiado para dentro da imagem no build. Portanto, após mudar
o SQL, recrie volume **e** imagem:

```bash
docker compose down -v && docker compose up -d --build
```

Isso descarta os dados locais. Para mudanças apenas em `src/`, o volume montado
e o `--reload` da API bastam.

### Concorrência e idempotência

Saldo e status são modificados com `FOR NO KEY UPDATE`; transferências travam
as duas contas por `id`, em ordem determinística. Antecipação trava os boletos
por `id`. A reserva de `Idempotency-Key` usa uma restrição `UNIQUE` no banco e
guarda a resposta confirmada para replay.

Os testes de `tests/integration/transaction/` cobrem saques simultâneos,
transferências cruzadas, reuso paralelo de chave idempotente, antecipações
concorrentes e disputa pelo último saldo.

### Legado do projeto-base

Arquivos e rotas `sample_entity` permanecem por compatibilidade com o template
do Bootcamp. Eles não compõem a API BaaS PME, sua RFC nem suas integrações.

---

## Inicialização — guia consolidado

O passo a passo vigente de instalação, `.venv`, Compose, portas, testes,
worker, benchmark e recriação segura do banco está no
[README da API](../../baas-pme-api/README.md).

Esta consolidação evita manter dois procedimentos operacionais divergentes.
O conteúdo anterior foi preservado no
[arquivo histórico T0.1](#guia-de-inicialização-e-setup-do-ambiente-t01); não use suas instruções
antigas como contrato atual.
