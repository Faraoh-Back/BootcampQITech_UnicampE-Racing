# Entrega — artefatos, reprodução e confirmações externas

Data: 10/10/2026. Este registro fecha o trabalho automatizável da Rodada 5;
não substitui revisão do time, ensaio, publicação ou aceite da organização.
O solicitante excluiu integralmente a seção **9.5**: não foram implementadas
suas correções/hardening, inclusive líquido positivo da antecipação (P0.4).

## 1. O que entregar

| Artefato | Uso |
|---|---|
| [RFC_FINAL.pdf](RFC_FINAL.pdf) | RFC de quatro páginas, nas duas seções/cinco subseções oficiais |
| [RFC_FINAL.md](RFC_FINAL.md) | Fonte editável da síntese; todas as 28 rotas operacionais/produto e fluxos |
| [APRESENTACAO.pdf](APRESENTACAO.pdf) | Dez slides de defesa em formato 16:9 |
| [APRESENTACAO.md](APRESENTACAO.md) | Fonte editável dos slides |
| [DEFESA.md](DEFESA.md) | Roteiro de dez minutos, perguntas/respostas e registro de ensaio |
| [der-financeiro.svg](der-financeiro.svg) / [der-operacional.svg](der-operacional.svg) | DER vetorial, 23 entidades e todas as relações do DER canônico |
| [artefatos.json](artefatos.json) | SHA-256 das fontes, ferramentas, SVGs e PDFs para detectar desatualização |

A [RFC integral](../RFC.md) e [DECISOES](../DECISOES.md) continuam preservadas
como fontes detalhadas. A síntese não redefine contratos, não remove features
nem altera o desenho. As duas páginas de DER conservam tipos, campos e
cardinalidades em cartões com referências; não afirmam FK inexistente.
UK significa unicidade, não divulgação pública de e-mail/hash/documento.

## 2. Gerar novamente os PDFs

Dependências de documentação **não** entram em requirements/imagem da API.
Pré-requisitos adicionais só para editar/gerar: Node 20+, npm, Chromium e
fontes DejaVu Sans/Mono. PDFs versionados podem ser lidos sem instalar isso.

```bash
cd docs/entrega/tools
npm ci --ignore-scripts --no-audit --no-fund
npm run render
```

Outro caminho de Chromium:

```bash
CHROME_BIN=/caminho/para/chromium npm run render
```

O renderer usa arquivos locais, não navega na internet nem carrega CDN.
Chromium cria somente perfil temporário exclusivo e o remove ao terminar.
Ambientes que impeçam browser/namespace exigem autorização/configuração de
sandbox do host; não é alteração de segurança da API. Não recomenda executar
conteúdo não confiável com sandbox desativado.

O renderer recusa conteúdo além da área útil, exige quatro/dez páginas e
atualiza os hashes. Esses controles não substituem revisão visual: confira
cortes horizontais, acentos, tamanho de fonte, tabela e DER. Metadados/data e
fontes/versão do Chromium podem mudar os bytes do PDF; não se promete binário
reprodutível. Com uma fonte alterada, regenere ambos os PDFs antes dos testes.

Verificações locais:

```bash
pdfinfo docs/entrega/RFC_FINAL.pdf
pdfinfo docs/entrega/APRESENTACAO.pdf
cd baas-pme-api
./.venv/bin/python -m pytest tests -q -m static_guard
```

As quatro novas guardas de entrega falharam antes dos artefatos e ficaram
verdes depois: seções/rotas, DER, PDF/hashes e honestidade sobre P0.4. Resultado
local após a geração: **10 passed, 196 deselected**. Fontes/PDFs foram revistos
visualmente pelo agente; o aceite humano dos integrantes continua necessário.

## 3. Validar sem apagar o banco em desenvolvimento

O script cria clone local, checkout em `/tmp`, venv nova dentro da API e um
projeto Compose exclusivo. Publica API/DB/mock em 13000/15432/11080, usa somente
dados sintéticos e executa as seleções e a suíte inteira sequencialmente.
Depois consulta métricas e executa o benchmark de CPU/RAM já existente.

```bash
cd baas-pme-api
bash scripts/validate_delivery.sh --snapshot
```

`--snapshot` sobrepõe ao clone os arquivos de trabalho não ignorados; inclui
mudanças ainda não commitadas. **Não é clone do commit publicado.** Não copia
.env, venv, node_modules ou artefatos ignorados. Não modifica o índice nem faz
commit/push. Portas podem ser trocadas sem editar código:

```bash
DELIVERY_API_PORT=13001 DELIVERY_DB_PORT=15433 DELIVERY_MOCK_PORT=11081 \
  bash scripts/validate_delivery.sh --snapshot
```

Depois do commit final, use `--head` para validar somente a versão commitada:

```bash
bash scripts/validate_delivery.sh --head
```

Relatórios ficam em `baas-pme-api/artifacts/delivery/<UTC>/` (ignorados):
ambiente/commit/dirty, pip freeze/check, usuário do container, resultados e
JUnit por seleção/full, métricas Prometheus, benchmark e resultado final.
O checkout/venv são preservados para inspeção. O script remove somente
containers, rede e volumes do projeto criado por ele; os dados sintéticos
desse banco são descartados. O banco e containers originais não são alvos.

**Validação final concluída:** 10/10/2026, 07:30:27–07:33:26 UTC; base
`524c7608ba305978bae7c97ece7348b8961c8a6a`, 44 entradas dirty na origem.
Execução `20261010T073026Z`, saída 0; checkout preservado em
`/tmp/baas-delivery-YH8rXgJs/repository`. Resultados:

| Etapa | Resultado |
|---|---|
| Guardas estáticas | 10 passed, 1.10 s |
| API somente HTTP | 170 passed, 51.58 s |
| Infraestrutura | 26 passed, 9.06 s |
| Suíte inteira | **206 passed, 61.55 s** |
| Benchmark separado | 5 passed, 7.14 s; 200 transferências; parede 7,506 s |
| Métricas | exposition Prometheus obtida depois da suíte completa |
| Ambiente | venv nova/pip check, compileall e API não-root uid=100 |
| Finalização | projeto descartável removido; containers originais saudáveis com os mesmos IDs |

CPU/RAM amostradas e limites em [BENCHMARK §11](../BENCHMARK.md#11-validação-de-entrega-em-ambiente-isolado).
Matriz/contagens e evidências detalhadas em [COBERTURA](../COBERTURA.md).
metrics.prom registrou replays (4 antecipação/104 transação) e retries
(4 deadlock/4 serialização) ao longo da execução; counters são por processo,
e as contagens não são SLO nem um teste novo de produção. Consultar outbox e
sessões nesse instante não prova funcionamento de coletores/alarmes externos.

Tentativas iniciais foram interrompidas pela guarda de PDF ausente e por uma
asserção incorreta no smoke: `/mockserver/status` informa porta interna 1080,
não a porta publicada 11080. A asserção foi corrigida, sem mudar a API. Outra
tentativa teve 170 testes HTTP aprovados, mas foi interrompida após editar o
script enquanto ele ainda lia comandos; o corpo passou a ser carregado inteiro
antes de executar, e a execução final repetiu todas as etapas com sucesso.
Essas tentativas não são apresentadas como pipeline verde.

Esse procedimento prova bootstrap com banco/venv novos **no mesmo host e
Docker daemon**, com camadas de imagem/cache reutilizáveis. Não prova VM Linux
virgem, clone remoto, build sem cache ou usabilidade por pessoa independente.
Dependências transitivas podem evoluir: pip-freeze registra a resolução desta
execução, não substitui lock/migrations/controles produtivos do backlog.

## 4. Clone remoto por outra pessoa — ainda necessário

Após publicar o commit/artefatos finais, um integrante que não escreveu o
Compose deve executar numa máquina/VM Linux nova, seguindo somente o README:

```bash
git clone https://github.com/Faraoh-Back/BootcampQITech_UnicampE-Racing.git
cd BootcampQITech_UnicampE-Racing/baas-pme-api
docker compose up -d --build
docker compose ps
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements-dev.txt
NIGHT_TIME_OVERRIDE=21:00 docker compose up -d --build
./.venv/bin/python -m pytest tests -q -m static_guard
./.venv/bin/python -m pytest tests -q -m api_blackbox
./.venv/bin/python -m pytest tests -q -m infrastructure_contract
./.venv/bin/python -m pytest tests -q
```

Use banco descartável: suíte de infraestrutura/legado recria schema. Guardar
data, commit, máquina, versões, saídas e quem executou; concluir T5.5 só depois.
Não copiar segredos de desenvolvimento nem solicitar override financeiro em
produção. O relógio fixo pertence exclusivamente ao perfil de teste.

## 5. Ensaio e publicação — ações humanas/externalizadas

1. Abrir ambos os PDFs e revisar com os integrantes; confirmar autoria/data,
   legibilidade e que a síntese corresponde à versão entregue.
2. Seguir DEFESA e preencher o registro após ensaio real; não assinar resultado
   de alguém que ainda não respondeu às perguntas.
3. Selecionar os arquivos para o commit, revisar inclusive o índice já
   preparado pelo usuário; conferir que o modelo oficial, fontes, ferramentas,
   package-lock, SVGs, manifesto e PDFs estão incluídos. Não versionar caches,
   .env, dados ou node_modules. Não foi feito commit/push nesta rodada.
4. Publicar no remoto e confirmar que o Actions daquele commit passou. Não
   dizer que validação local equivale a execução remota do workflow.
5. Confirmar visibilidade pública sem login, commit final e acesso aos PDFs.
   Tornar privado → público exige decisão do responsável; esta rodada não
   alterou visibilidade/permissões e não publicou mudanças remotas.

| Confirmação | Responsável/data/commit | Estado |
|---|---|---|
| Aceite da RFC/apresentação pelo time | A preencher | Pendente |
| Clone remoto em Linux novo por outra pessoa | A preencher | Pendente |
| Ensaio completo de cada integrante | A preencher em DEFESA | Pendente |
| Commit/push e Actions remoto | A preencher | Pendente |
| Acesso anônimo aos artefatos finais | A preencher | Pendente |

A consulta inicial por ferramenta de navegação não retornou evidência
utilizável. A verificação complementar por `curl -q`, sem autenticação ou
configuração local de curl, obteve **HTTP 200** na
[API pública do repositório](https://api.github.com/repos/Faraoh-Back/BootcampQITech_UnicampE-Racing)
em 10/10/2026: acesso anônimo ao repositório foi confirmado. Isso não prova
que os novos PDFs/commit foram publicados. A consulta ao caminho
`contents/docs/entrega/RFC_FINAL.pdf?ref=main` retornou **HTTP 404**: este PDF
ainda não estava disponível na main remota no momento da checagem.
Aceite, ensaio, clone independente,
Actions e acesso aos artefatos finais continuam exigindo confirmação.
