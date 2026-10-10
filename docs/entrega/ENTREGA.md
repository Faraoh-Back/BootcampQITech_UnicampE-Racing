# Entrega — artefatos, reprodução, defesa e confirmações externas

Data: 10/10/2026. Este registro fecha o trabalho automatizável da Rodada 5;
não substitui revisão do time, ensaio, publicação ou aceite da organização.
O solicitante excluiu inicialmente a seção **9.5** e depois autorizou
especificamente líquido positivo da antecipação/cotação CREDIT_ADVANCE.
Essa regra está implementada com 422/QIT001030, CHECKs, upgrade preservando
histórico e 52 testes novos; o restante de P0.4/9.5 continua pendente.

Publicação e CI foram posteriormente confirmados para o commit `1603118`;
a [evidência por commit](#51-evidência-remota-confirmada) distingue essa versão
das revisões seguintes. Revisão dos PDFs, clone independente e ensaio continuam
sob responsabilidade do grupo, sem resultado humano presumido.

Evidência da nova regra em [COBERTURA](../COBERTURA.md#líquido-positivo-implementação-e-redgreen--10102026);
upgrade de banco existente no [README da API](../../baas-pme-api/README.md#atualizar-banco-existente-líquido-positivo-da-antecipação).
As execuções anteriores abaixo são históricas; não comprovam a nova revisão.

O fechamento atual de infraestrutura/relógio está na [seção 3.3](#33-t510-relógio-determinístico-e-bootstrap-automático)
e [COBERTURA — T5.10](../COBERTURA.md#relógio-determinístico-e-bootstrap-automático--10102026):
289 testes/114.35 s, benchmark separado de 200 transferências/8,058 s.
A [seção 3.2](#32-fechamento-final-da-regra-aprovada) conserva o fechamento
anterior: 260 testes/75.43 s e benchmark separado de 200 transferências/8,255 s.
Esses números não são uma nova execução da RFC 3.4 nem CI da revisão atual.

Navegação: [artefatos](#1-o-que-entregar), [geração de PDFs](#2-gerar-novamente-os-pdfs),
[validação isolada](#3-validar-sem-apagar-o-banco-em-desenvolvimento),
[clone independente](#4-clone-remoto-por-outra-pessoa--ainda-necessário),
[publicação](#5-ensaio-e-publicação--ações-humanasexternalizadas),
[defesa e ensaio](#6-defesa-técnica-e-ensaio).

## 1. O que entregar

| Artefato | Uso |
|---|---|
| [RFC_FINAL.pdf](RFC_FINAL.pdf) | RFC de quatro páginas, nas duas seções/cinco subseções oficiais |
| [RFC_FINAL.md](RFC_FINAL.md) | Fonte editável da síntese; todas as 28 rotas operacionais/produto e fluxos |
| [APRESENTACAO.pdf](APRESENTACAO.pdf) | Dez slides de defesa em formato 16:9 |
| [APRESENTACAO.md](APRESENTACAO.md) | Fonte editável dos slides |
| [Defesa técnica e ensaio](#6-defesa-técnica-e-ensaio) | Roteiro de dez minutos, perguntas/respostas e registro de ensaio |
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
local na preparação original: **10 passed, 196 deselected**. Fontes/PDFs foram
revistos visualmente pelo agente; o aceite humano dos integrantes continua necessário.

Na consolidação de 10/10/2026, o roteiro antes separado passou para a
[seção 6](#6-defesa-técnica-e-ensaio). As duas novas guardas de organização/links
tiveram Red antes da migração e Green depois: **12 passed, 196 deselected**.
Os PDFs foram regenerados e seus hashes conferidos; a RFC integral mantém as
seções oficiais. A suíte daquele marco teve **208 testes coletados**, mas não foi
reexecutada naquela alteração exclusivamente documental. A validação isolada
de 206 testes abaixo permanece uma evidência histórica, não uma nova execução.
Registro atual em [COBERTURA](../COBERTURA.md#consolidação-documental--10102026).

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

**Validação histórica da entrega inicial:** 10/10/2026, 07:30:27–07:33:26 UTC; base
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

### 3.1 Revalidação com líquido positivo — 10/10/2026

Registro intermediário preservado. O fechamento com os cinco casos extras
de tarifa extrema e o snapshot validado antes da escrita está na seção 3.2.

Execução `20261010T083920Z`, **08:39:21–08:42:27 UTC**, saída 0; clone
local + snapshot de 27 alterações sobre `1603118`, não o commit publicado.
Código financeiro da implementação inicial da regra, antes do ajuste de
snapshot/tarifa extrema; venv/DDL/banco novos. Resultado:
**255 passed, 72.98 s**; seleções independentes: 12 estáticos (0.43 s),
203 HTTP (64.74 s), 40 infraestrutura (11.56 s). Compilação/pip check aprovados
e API não-root uid=100. Benchmark: 5 casos/200 transferências, parede 7,753 s;
métricas obtidas antes da recriação da API para a carga.

Relatórios em `baas-pme-api/artifacts/delivery/20261010T083920Z/`, checkout em
`/tmp/baas-delivery-x8U6PEUz/repository`. O projeto exclusivo foi removido pelo
script; o original permanece saudável com os mesmos IDs. A migração de líquido
positivo foi aplicada ao banco original, com 0 registros incompatíveis no
preflight e ambos os CHECKs confirmados como validados; nenhum dado financeiro
foi reescrito. As duas respostas antigas geradas no Red foram preservadas no
replay HTTP após o upgrade do banco sintético, antes do seu descarte.

Ajustes finais apenas de texto/PDF foram reconferidos na origem: **12 guardas
aprovadas**, rechecagens de 0.14–0.16 s, incluindo 422/líquido nas tabelas das
duas rotas; o código financeiro testado não mudou. PDF de quatro páginas
e apresentação de dez, sem overflow e com hashes conferidos. Esta revisão não
está publicada nem coberta pelo CI remoto de `1603118`. Evidência/limites em
[COBERTURA](../COBERTURA.md#regressão-completa-métricas-e-benchmark-desta-implementação)
e [BENCHMARK §12](../BENCHMARK.md#12-líquido-positivo-regressão-completa-e-benchmark).

### 3.2 Fechamento final da regra aprovada

Após reforçar a contagem de snapshots padrão (`customer_id IS NULL`), a
suíte intermediária passou novamente com 255 casos/73.47 s. Um novo Red
identificou 500 ao tentar persistir tarifa calculada acima de BIGINT antes
de recusar líquido negativo. Corrigida a ordem: calcular/validar no controller
e só então persistir o snapshot com a mesma política/tarifa, sem nova resolução.
Isso não entrega os limites numéricos gerais nem os demais itens de 9.5.

Foram acrescentados cinco casos: **52 cenários da regra aprovados, 14.82 s**;
suíte atual **260 passed, 75.43 s**, executada em 10/10/2026, 09:05:17–09:06:33
UTC, na `.venv` da API contra DDL/banco novos e projeto exclusivo. Distribuição:
206 HTTP, 42 infraestrutura, 12 estáticos; a execução completa incluiu todas
essas categorias e os PDFs disponíveis naquele marco. Fontes/artefatos alterados
depois são reconferidos pelas guardas documentais; não se inventam durações de
seleções independentes por marcador.

Benchmark do código final: **5 passed, 7.89 s**, 200 transferências, parede
**8,255 s**. Exposition obtida antes da API recriada para a carga: QIT001030
nas duas rotas, sem retry de negócio; CPU/RAM e limites em
[BENCHMARK §13](../BENCHMARK.md#13-fechamento-final-validação-anterior-ao-snapshot-de-preço).
Relatórios locais em `baas-pme-api/artifacts/p04/20261010085856-final/`.
Somente o projeto `baas-p04-final-20261010085856` e seus dados sintéticos foram
descartados; ambiente original preservado com CHECKs validados. Fontes/RFC
3.3/PDFs estão alinhados; publicação/CI da revisão nova e confirmações humanas
continuam pendentes, sem commit/push pelo agente.

### 3.3 T5.10: relógio determinístico e bootstrap automático

**2026-10-10 18:26:54–18:28:49 UTC:** **289 passed in 114.35s**, zero
falhas/erros/skips, na `.venv` existente. 220 asserções de produto HTTP,
42 contratos SQL/worker e 27 guardas estáticas; bootstrap Docker é preparação
de infraestrutura, não prova HTTP. Executou-se o comando pytest padrão com
variáveis conflitantes no shell; API principal em 21h e API auxiliar para
fronteiras/dia/replay. Nenhuma rota/regra/DDL financeira foi alterada.

Projeto `baas-pytest-e17f7ad40e0d43c98a5b5cde4ddea7fb`; base
`6e605c9c0ae3cb2121c4d61b4fc5b5d06115486f` + trabalho local, não commit
publicado. JUnit `artifacts/test-runs/full-final.xml`; diretório por UUID com
expositions de métricas principal/auxiliar e metadados sem credenciais.
Remoção foi conferida por `ps --all --quiet` e consulta ao Docker/rede;
containers originais conservaram IDs/uptime/relógio. Só dados sintéticos
descartáveis foram removidos; não houve reset do banco de desenvolvimento.

Uma primeira regressão passou 288/114.08 s, mas inspeção posterior encontrou
perfil opcional remanescente. Red/Green adicional motivou a 289ª guarda e
inclusão explícita do perfil em todo comando. Esses resíduos foram removidos
por seus UUIDs, e os metadados anteriores de cleanup não são prova completa.
Históricos permanecem em [COBERTURA](../COBERTURA.md#relógio-determinístico-e-bootstrap-automático--10102026).

Benchmark separado: 5×40, **5 passed/7.77 s**, parede **8,058 s**, três
snapshots CPU/RAM. Compose de teste sem reload: não comparar diretamente
com medições do perfil de desenvolvimento. Método/limites em
[BENCHMARK §14](../BENCHMARK.md#14-t510-bootstrap-determinístico-e-modo-externo).
Modo externo foi exercitado com outbox/worker e relógio (19/38.76 s, antes
da guarda adicional); após a correção, mais **5 passed/15.81 s** de worker,
testes originais e replay entre janelas, com cleanup de ambos os ambientes.

RFC 3.4/PDF de quatro páginas e apresentação de dez foram regenerados;
seções oficiais, rotas/DER, hashes, overflow e revisão visual conservados.
CI novo usa a mesma preparação padrão e publica JUnit/métricas/metadados;
a aprovação remota ainda depende de commit/push do grupo. Validador de
clone/venv nova **não** foi executado integralmente nesta rodada; aceite,
clone independente e ensaio continuam pendentes. Nenhum item restante de 9.5
foi implementado ou marcado como concluído.

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
./.venv/bin/python -m pytest tests -q -m static_guard
./.venv/bin/python -m pytest tests -q -m api_blackbox
./.venv/bin/python -m pytest tests -q -m infrastructure_contract
./.venv/bin/python -m pytest tests -q
```

Desde T5.10 os comandos pytest acima preparam automaticamente seus projetos
descartáveis, relógio fixo, portas livres, saúde e cleanup; não precisam de
`NIGHT_TIME_OVERRIDE` manual nem de `down -v` no projeto de desenvolvimento.
As seleções são execuções independentes sobre bancos novos. CI atual roda
guardas + suíte completa e preserva JUnit/métricas/metadados. Scripts de entrega
e benchmark, que já possuem Compose próprio, usam `--test-environment=external`;
fronteiras de relógio continuam isoladas, inclusive nesse modo. O setup manual
do produto permanece com relógio real. Referências:
[README](../../baas-pme-api/README.md#relógio-determinístico-e-isolamento-automático),
[T5.10](../PLANO_DE_EXECUCAO.md#t510-infraestrutura-automática-e-relógio-determinístico-ajuste-de-entrega).

O banco gerido é descartável: infraestrutura/legado recria schema. Guardar
data, commit, máquina, versões, saídas e quem executou; concluir T5.5 só depois.
Não copiar segredos de desenvolvimento nem solicitar override financeiro em
produção. O relógio fixo pertence exclusivamente ao perfil de teste.

## 5. Ensaio e publicação — ações humanas/externalizadas

1. Abrir ambos os PDFs e revisar com os integrantes; confirmar autoria/data,
   legibilidade e que a síntese corresponde à versão entregue.
2. Seguir a [defesa técnica](#6-defesa-técnica-e-ensaio) e preencher o registro após ensaio real; não assinar resultado
   de alguém que ainda não respondeu às perguntas.
3. Selecionar os arquivos para o commit, revisar inclusive o índice já
   preparado pelo usuário; conferir que o modelo oficial, fontes, ferramentas,
   package-lock, SVGs, manifesto e PDFs estão incluídos. Não versionar caches,
   .env, dados ou node_modules. O agente não faz commit/push automaticamente.
4. Após cada revisão, publicar no remoto e confirmar que o Actions daquele commit passou. Não
   dizer que validação local equivale a execução remota do workflow.
5. Confirmar visibilidade pública sem login, commit final e acesso aos PDFs.
   Tornar privado → público exige decisão do responsável; esta rodada não
   alterou visibilidade/permissões e não publicou mudanças remotas.

| Confirmação | Responsável/data/commit | Estado |
|---|---|---|
| Aceite da RFC/apresentação pelo time | A preencher | Pendente |
| Clone remoto em Linux novo por outra pessoa | A preencher | Pendente |
| Ensaio completo de cada integrante | A preencher na [seção 6.3](#63-registro-de-ensaio--preencher-após-realizar) | Pendente |
| Publicação e Actions remoto | Verificação anônima em 10/10/2026; commit `1603118`; evidência abaixo | Confirmado para esse commit; revalidar novas revisões |
| Acesso anônimo aos PDFs | Verificação anônima em 10/10/2026; commit `1603118`; bytes correspondentes às cópias locais verificadas | Confirmado para esse commit; revalidar novos PDFs |

**Verificação anterior à publicação — histórico preservado:** a consulta inicial
por ferramenta de navegação não retornou evidência
utilizável. A verificação complementar por `curl -q`, sem autenticação ou
configuração local de curl, obteve **HTTP 200** na
[API pública do repositório](https://api.github.com/repos/Faraoh-Back/BootcampQITech_UnicampE-Racing)
em 10/10/2026: acesso anônimo ao repositório foi confirmado. Isso não prova
que os novos PDFs/commit foram publicados. A consulta ao caminho
`contents/docs/entrega/RFC_FINAL.pdf?ref=main` retornou **HTTP 404**: este PDF
ainda não estava disponível na main remota no momento da checagem.
Naquele momento, aceite, ensaio, clone independente, Actions e acesso aos
artefatos finais ainda exigiam confirmação. A verificação posterior abaixo
resolve publicação/CI daquela versão, não as confirmações humanas do grupo.

### 5.1 Evidência remota confirmada

Consulta pública somente de leitura, sem autenticação, reconfirmada em
**10/10/2026**. Não houve mudança de visibilidade, execução manual de workflow
ou push pelo agente.

- **Commit verificado:** `160311850dbfbc9427ed7f5049047aada951e8b3`.
  A consulta à `main` retornou HTTP 200 e esse SHA, igual ao HEAD local no
  momento da verificação.
- **CI verificado:** [BaaS PME CI, execução 38036090796](https://github.com/Faraoh-Back/BootcampQITech_UnicampE-Racing/actions/runs/38036090796),
  iniciada em `2026-10-10T07:55:22Z`, com `head_sha` correspondente,
  `status=completed` e `conclusion=success`. O workflow executa guardas estáticas,
  testes HTTP e contratos de infraestrutura em etapas separadas. A confirmação
  do run não fornece novas durações/contagens por teste nem reexecuta o benchmark.
- **RFC publicada:** [RFC_FINAL.pdf no commit verificado](https://github.com/Faraoh-Back/BootcampQITech_UnicampE-Racing/blob/160311850dbfbc9427ed7f5049047aada951e8b3/docs/entrega/RFC_FINAL.pdf),
  HTTP 200, 166336 bytes; Git blob SHA
  `3bc2f2c4417f0f20dcb30bb3b44b4fea91bfda47`.
- **Apresentação publicada:** [APRESENTACAO.pdf no commit verificado](https://github.com/Faraoh-Back/BootcampQITech_UnicampE-Racing/blob/160311850dbfbc9427ed7f5049047aada951e8b3/docs/entrega/APRESENTACAO.pdf),
  HTTP 200, 102104 bytes; Git blob SHA
  `ee339f96f639de561950310c3b85cebe33a9523e`.

Os SHAs retornados pelo GitHub coincidiram com `git hash-object` dos PDFs locais
daquela versão. São identificadores de blobs Git, não os SHA-256 do manifesto.
CI em Ubuntu não substitui o clone/reprodução por integrante independente nem
o aceite/ensaio da equipe.

**Fronteira desta evidência:** novas alterações de código/documentos e PDFs regenerados
nesta rodada ainda precisam de commit/push e de CI da nova versão. O sucesso de
`1603118` não é automaticamente transferido para commits futuros; confirmar
também o acesso aos arquivos da revisão que efetivamente será submetida.

## 6. Defesa técnica e ensaio

**Defesa técnica — roteiro e registro de ensaio.** Conteúdo antes mantido em
`DEFESA.md`, reunido aqui em 10/10/2026. O conteúdo foi preservado na consolidação;
respostas sobre a regra posteriormente implementada e suas evidências foram
atualizadas, sem concluir as pendências humanas.

Material de apoio à T5.7; não é evidência de que alguém já ensaiou. Frase-guia:
**garantias verificadas e limitações conhecidas**. No marco original, líquido
positivo estava aprovado e não implementado; posteriormente foi autorizado e
entregue com 422/QIT001030. O restante da seção 9.5 continua excluído pelo
solicitante desta rodada. Não apresentar seus itens como resolvidos.

### 6.1 Roteiro de 10 minutos

| Tempo | Slide | Mensagem |
|---|---|---|
| 0:00–1:00 | 1–2 | PME cobra pagadores, antecipa recebíveis e paga fornecedores; não é empréstimo |
| 1:00–2:00 | 3 | Um serviço modular + worker + PostgreSQL + mocks; camadas e fronteiras |
| 2:00–4:00 | 4–5 | Desafio principal: saldo/ledger, ordem por ID, resposta perdida e replay |
| 4:00–5:30 | 6–7 | Personalização versionada, limites, quatro olhos, identidade e auditoria |
| 5:30–7:30 | 8–9 | Testes HTTP versus infraestrutura, jornada e benchmark contextual |
| 7:30–10:00 | 10 | Alternativas e limites conhecidos; abrir perguntas |

Ensaio sugerido: cada integrante apresenta todo o roteiro uma vez; na segunda
rodada, o outro interrompe com perguntas. Não dividir conhecimento por autor.

### 6.2 Perguntas e respostas sustentáveis

**Por que centavos inteiros?** Dinheiro tem contrato exato: 100 é R$1,00.
BIGINT não introduz a imprecisão binária de float. Taxas comerciais são bps
inteiros; índices vêm como string/Decimal; half-up define arredondamento.
Float de duração/CPU não é dinheiro. Limites de magnitude continuam backlog.

**Qual é o principal desafio?** Decidir sobre saldo/lastro protegido e confirmar
ledger/saldo/resposta idempotente juntos, mesmo com disputa e resposta perdida.
O teste mostra cenários exercitados, não prova matemática de todos os caminhos.

**O que é deadlock?** A segura A e espera B; B segura B e espera A. Há ciclo de
espera. Ordenar por ID crescente remove esse ciclo entre as contas: ambas
tentam primeiro a menor. Nunca dizer “IP crescente”. Também não dizer que
isso elimina todos os deadlocks de todas as tabelas do sistema.

**Por que FOR NO KEY UPDATE?** A movimentação muda saldo, não a chave da conta.
A trava continua exclusiva para atualizações concorrentes, mas é compatível
com KEY SHARE adquirido pela FK da reserva idempotente. A escolha evita um
conflito de upgrade desnecessário sem liberar duas decisões simultâneas.

**E A sem saldo esperando B transferir?** Responde 422 imediatamente depois
das validações aplicáveis; não retenta negócio. Se B creditar depois, A pode
expressar nova intenção. Isso é estado mudando, não exemplo de deadlock.

**Quando o controller retenta?** Só transação/antecipação idempotentes, em
40P01/40001. Faz rollback, descarta sessão abortada e repete a operação inteira
com mesma chave, até duas tentativas totais padrão. Não retenta 4xx ou emissão
externa; esgotamento é 503/QIT001025. Não repetir só a última query.

**Cliente desistiu antes da resposta: houve débito?** Pode ter ocorrido commit.
Reenvie mesmo corpo/chave e recupere resposta confirmada. Outro corpo dá 409;
novo UUID não é estratégia de recuperação, pois pode autorizar nova operação.

**Todo POST é idempotente?** Não. Transação e antecipação têm replay persistido.
Cadastro tem unicidade; lote 2/estado têm conflitos em repetição; quote cria
nova prévia; políticas diretas publicam nova versão. Não confundir esses casos.

**O banco é a fonte de verdade ou o saldo?** PostgreSQL contém fatos e projeção:
ledger é a história de valores com sinal contábil, não assinatura criptográfica;
account.balance é saldo materializado, protegido
na mesma transação. Testes reconciliam contas que criaram. Reconciliação
operacional periódica e proteção SQL universal do ledger ainda são backlog.

**O que acontece com dois saques disputando o último saldo?** Um confirma;
outro relê saldo depois da espera e recebe 422. Se uma tentativa falha, seus
lançamentos/snapshots/reserva não confirmam. Há testes reais com barreira.

**Taxa personalizada muda histórico?** Não pelo fluxo entregue: política
versionada, PME específica > padrão, snapshots retêm escolha/base/valor.
Fixo + percentual half-up; tarifa é lançamento separado. Proteção append-only
dos snapshots contra SQL privilegiado ainda não existe.

**Quote garante preço?** Não. É prévia persistida por 60s, sem reservar recursos.
Execução recalcula; cliente não escolhe tarifa nem força quote_key. Quando
preço muda, uma nova operação usa o vigente; replay mantém resultado antigo.

**Quatro olhos é impossível de contornar?** No fluxo de propostas, outro OWNER
precisa aprovar sob lock; autoaprovação e publicação duplicada são recusadas.
Rotas técnicas diretas de política contornam esse fluxo. Sem gateway/controle
produtivo, não prometer segregação universal de funções.

**Por que a tarifa de R$120 sobre bruto R$100 é problema?** Pode consumir lastro
e reduzir saldo prévio em vez de fornecer liquidez. A regra aprovada exige
líquido >0 mesmo com R$500 anteriores. Agora execução/cotação CREDIT_ADVANCE
retornam 422/QIT001030; saldo e boleto permanecem intactos. Essa subparte de
P0.4 foi autorizada e entregue; o restante segue pendente. Uma tarifa fixa de
R$120 continua válida para bruto R$1.000: validar por operação, não proibir a
política personalizada. Replay confirmado preserva resposta/preço originais.

**Plano e antecipação são o mesmo empréstimo?** Não. Plano emite recebível da
PME contra pagador externo; antecipação credita liquidez sobre esse recebível
e o vincula como lastro uma vez. Não existe financiamento sem lastro,
amortização, juros de empréstimo, boleto de devedor ou baixa automática.

**Commit falha depois de emitir boleto: emissão some?** Não. ACID vale localmente,
não desfaz o provedor. Falhas podem deixar emissão externa sem confirmação
local; há referência plano/lote, sem compensação/reserva persistida entregue.
Lote 2 ainda mantém trava durante I/O; recuperação é backlog, não exactly-once.

**JWT de 8h ou sessão de 8h?** Acesso curto (15min padrão); refresh opaco rotativo
limitado à sessão máxima de 8h. Dispositivos separados; revogação individual.
VIEWER lê/cota, OPERATOR movimenta, OWNER também muda estado. JWT presente é
validado; token interno continua amplo e dispensa JWT nas rotas de conta.

**UUID impede IDOR?** Sozinho não. Não expõe sequência interna, mas é preciso
autorização e vínculo. Consulta de lançamento exige pertencer à conta e usa
mesmo 404 para alheio/inexistente. Exportação administrativa de auditoria
expõe ID sequencial, exceção documentada à interpretação universal de R5.

**A auditoria é blockchain/imutável para qualquer pessoa?** Não. SHA-256
encadeado com serialização global detecta inconsistência; trigger impede
UPDATE/DELETE só de audit_event. Administrador pode mudar proteção e cadeia;
checkpoint HTTP não é assinatura/âncora independente. Não há consenso.

**Notificação pode repetir?** Sim, at-least-once. Outbox confirma com domínio;
worker reclama lease, envia event_key e registra ack. Queda após aceite ou
lease vencido pode repetir. Consumidor deduplica; dead-letter/autenticação
do envelope e cenários avançados de lease ficam no backlog.

**Testes são todos black-box?** Não importam src. A categoria api_blackbox é
somente HTTP contra containers; infrastructure_contract usa SQL/injeção/worker;
static_guard lê arquivos. Explicar separadamente o que cada evidência prova.

**Como provam TDD?** Só pelo Red/Green efetivamente executado e histórico
registrado. Na entrega inicial, quatro contratos falharam antes dos artefatos;
na consolidação, duas guardas falharam antes da migração documental. Na regra
de líquido positivo, foram reproduzidas cinco falhas HTTP antes de implementar;
o extremo de tarifa acima de BIGINT teve um Red adicional (500 em vez de 422)
antes de corrigir a ordem do snapshot. Green da regra: 52 casos; regressão
completa: 260. Seleções interrompidas não provam Red de todos esses casos;
suíte verde não permite afirmar TDD retrospectivo de todas as features.
Relatórios/comandos/contexto em [COBERTURA](../COBERTURA.md).

**Quanto a API aguenta?** Benchmark tem 5×40 chamadas cruzadas, não carga
sustentada. CPU/RAM/duração dependem do hardware e do estado. Informar data,
ambiente e método; não usar medição curta como capacidade contratual ou SLO.

**Já há alarmes em produção?** Há métricas e propostas de regras; não há
Prometheus/Alertmanager/cAdvisor neste Compose. Logs normais são correlacionados
e mascarados, mas tracebacks podem expor SQL/URLs. Orçamento não é deadline
global rígido; produção, TLS, backup e secrets seguem backlog excluído.

**Por que não microserviços por operação?** Fragmentariam a transação financeira
e exigiriam coordenação distribuída sem benefício demonstrado neste desafio.
Ganham quando domínios/equipes/deploys são independentes. O worker separado
desacopla webhook, mas compartilha banco/código, não é autonomia de domínio.

### 6.3 Registro de ensaio — preencher após realizar

| Integrante | Data | Roteiro completo sem código? | Perguntas respondidas? | Dúvidas / ação |
|---|---|---|---|---|
| Cairê Belo | A preencher | Não comprovado | Não comprovado | A preencher |
| Pedro Campanha | A preencher | Não comprovado | Não comprovado | A preencher |

Conclusão de T5.7 depende deste registro humano; gerar o roteiro não conclui
o ensaio. Separar resposta errada de limite real, consultar contrato e repetir
a rodada de perguntas antes da apresentação.
