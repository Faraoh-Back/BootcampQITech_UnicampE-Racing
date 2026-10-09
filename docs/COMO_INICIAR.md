# Guia de Inicialização e Setup do Ambiente (T0.1)

Este guia foi feito para que qualquer membro do time consiga clonar o repositório e subir o ambiente local do **BaaS PME** em sua própria máquina do zero, garantindo que tudo funcione perfeitamente.

---

## 1. Pré-requisitos

Certifique-se de ter instalado na sua máquina:

- **Git**
- **Docker** e **Docker Compose** (plugin `docker compose` v2 ou superior)
- **Python 3.11** (com módulo `venv`)
- **Curl** ou navegador web (para testar os endpoints)

---

## 2. Visão Geral da Estrutura

Ao clonar o repositório, você encontrará a seguinte estrutura:

```text
.
├── baas-pme-api/           # Onde o sistema BaaS PME é de fato desenvolvido
├── bootcamp-biblioteca-api/# Projeto de exemplo/consulta da QI Tech com uso de libs
└── docs/                   # Documentação (RFC, Plano de Execução, Guias)
```

> **Atenção:** todo o trabalho de desenvolvimento e comandos Docker/Pytest serão feitos **dentro da pasta `baas-pme-api/`**.

---

## 3. Passo a Passo de Instalação (Task T0.1)

### Passo 1: Acesse a pasta do projeto
No terminal, entre no diretório da API:
```bash
cd baas-pme-api
```

### Passo 2: Crie o arquivo de variáveis de ambiente (`.env`)
Copie o arquivo de exemplo para criar o `.env` local:
```bash
cp .env.example .env
```
*(Os valores padrão já estão configurados para o ambiente de desenvolvimento local).*

### Passo 3: Suba os containers com Docker Compose
Execute o build e suba os containers em segundo plano (*detached mode*):
```bash
docker compose up -d --build
```

### Passo 4: Verifique se os serviços estão saudáveis (*healthy*)
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

## 4. Configuração do Python e Testes Locais

A arquitetura do projeto adota o seguinte modelo:
- A **API** e o **Banco de Dados PostgreSQL** rodam dentro do Docker.
- Os **Testes (`pytest`)** rodam na sua máquina host (fora do container), disparando requisições contra a API que está no Docker.

### Passo 5: Crie e ative a Virtual Environment (venv)
Ainda dentro de `baas-pme-api/`:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
*(No Windows PowerShell seria: `.venv\Scripts\Activate.ps1`)*

### Passo 6: Instale as dependências de desenvolvimento
```bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Passo 7: Execute os testes automatizados
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

---

## 5. Testando a Recriação Limpa do Banco (Passo Crítico)

Para garantir que o banco e o schema SQL são aplicados do zero corretamente:
```bash
# 1. Derruba os containers e apaga os volumes do banco
docker compose down -v

# 2. Reconstrói a imagem que contém o SQL e sobe novamente
docker compose up -d --build

# 3. Confere a saúde
docker compose ps

# 4. Roda os testes de novo
pytest
```
> **Por que isso é importante?** O PostgreSQL só executa o script de inicialização com o volume vazio, e o Docker só copia uma alteração de `database/database.sql` para a imagem em um novo build. Toda mudança no SQL exige `docker compose down -v && docker compose up -d --build`.

---

## 6. Comandos Úteis do Dia a Dia

| Ação | Comando |
|---|---|
| **Subir serviços em background** | `docker compose up -d` |
| **Ver logs em tempo real** | `docker compose logs -f api` |
| **Ver status e portas** | `docker compose ps` |
| **Parar os containers** | `docker compose stop` |
| **Parar e remover containers** | `docker compose down` |
| **Resetar banco de dados do zero** | `docker compose down -v` |
| **Rodar todos os testes** | `pytest` |
| **Rodar um arquivo específico de teste** | `pytest tests/integration/test_healthcheck.py` |
| **Rodar testes mostrando prints/logs** | `pytest -s -v` |

### Integração contínua

O workflow [BaaS PME CI](../.github/workflows/baas-pme-ci.yml) roda em todo `push` e `pull request`: valida o Compose, recria API, banco e MockServer, espera o health check, compila o código e executa `pytest`. A validação local equivalente é:

```bash
docker compose down -v
docker compose up -d --build
pytest -q
```

---

## 7. Dúvidas Frequentes e Problemas Conhecidos

### 1. "Estou vendo logs com `GET /health_check` a cada 3 segundos com portas variando"
**É normal!** O Docker Compose possui um healthcheck configurado para testar se a API continua respondendo a cada 3 segundos. As portas diferentes que aparecem no log são portas de cliente (efêmeras) abertas para cada chamada de checagem.

### 2. "Porta 3000 ou 5432 já está em uso na minha máquina"
Se você já tiver um Postgres ou outro serviço local usando essas portas:
- Edite o seu arquivo `.env`:
  ```ini
  API_PORT=3001
  DB_PORT=5433
  ```
- No caso do `pytest`, garanta que as variáveis de teste apontem para a porta configurada.

### 3. "Erro: Could not import module 'app' no Uvicorn"
- Verifique se os arquivos de código dentro de `src/` terminam com `.py` e não com `_py.txt`.
- Certifique-se de que está rodando o `docker compose` a partir da pasta `baas-pme-api/` e não de outro caminho.
- Se necessário, faça um build limpo: `docker compose build --no-cache`.

---

## 8. Critério de Conclusão da Tarefa T0.1

Para considerar a **T0.1** concluída na sua máquina:
1. Tirar print do terminal executando `docker compose ps` mostrando os containers `(healthy)`.
2. Tirar print do `pytest` com todos os testes passando em verde.
