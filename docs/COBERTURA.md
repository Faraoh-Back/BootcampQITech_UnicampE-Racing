# Cobertura de Testes e Erros por Rota

> Revisão de entrega: 2026-10-10. Esta é a fonte de contagem/evidência atual,
> não uma alegação de cobertura de 100% de linhas ou de todas as combinações
> possíveis. As rotas são de um serviço modular, com contratos de infraestrutura
> executados separadamente dos testes estritamente HTTP.

**Enquadramento aprovado: garantias verificadas e limitações conhecidas.**
A regra de antecipação com líquido positivo está implementada na execução e
cotação CREDIT_ADVANCE, com 422/QIT001030. Foram acrescentados 52 cenários:
36 HTTP e 16 contratos SQL/migração. Apenas esta subparte foi autorizada;
as demais lacunas P0.4/9.5 permanecem pendentes. Resultados anteriores são
preservados como históricos, sem atribuir-lhes cobertura da regra nova.
Suíte vigente após T5.10: **289 testes aprovados** — 220 HTTP, 42 contratos de
infraestrutura e 27 guardas estáticas. A regressão desta revisão é registrada
na seção de relógio abaixo; os 260 anteriores permanecem uma execução histórica.

Leitura recomendada: [relógio/fechamento atual](#relógio-determinístico-e-bootstrap-automático--10102026)
para o resultado completo mais recente; [features e pipelines](#features-e-pipelines-o-que-a-evidência-comprova)
para a matriz vigente; [lacunas](#garantias-verificadas-e-limitações-conhecidas-lacunas-pendentes)
para o que ainda não foi comprovado. Os marcos de 255/208/206/202 e anteriores
não são resultados da mesma versão nem novas medições desta revisão documental.

## Relógio determinístico e bootstrap automático — 10/10/2026

**T5.10, RFC 3.4.** As duas falhas locais registradas eram os cenários noturnos
executados sobre uma API com relógio real durante o dia. O CI anterior fixava
21:00; preparar manualmente o ambiente não garantia a execução local.
Não adaptamos as expectativas ao horário do host nem colocamos skips.

O pytest padrão agora inicia um projeto UUID exclusivo com Compose de teste
independente, portas livres locais, SQL atual, banco/MockServer novos e API em
21:00. Fronteiras usam uma segunda API da mesma imagem/banco; não existe controle
HTTP do relógio, import da aplicação ou mudança no Compose de desenvolvimento.
Bootstrap é infraestrutura; asserções financeiras são HTTP, contratos SQL/worker
e guardas estáticas continuam explicitamente classificados. Limite diário de
risco continua com a pendência de fuso já documentada: não foi alterado.

| Evidência | Resultado / alcance |
|---|---|
| Red do contrato de infraestrutura | 1 falha real: arquivo de Compose exclusivo ausente; sem executar operações no banco original |
| Cenários HTTP do relógio | **16 passed in 36.49s** na `.venv` existente: 2 originais + 12 fronteiras/valores + 2 replays dia→noite |
| Guardas novas do bootstrap | 15 casos: projeto/portas, comandos sem shell, falhas operacionais, segredo, restauração, cleanup mesmo se evidência falhar, proibição de reutilizar runtime encerrado e erro se restar container |
| Regressão completa final | **289 passed in 114.35s**, zero falhas/erros/skips, 18:26:54–18:28:49 UTC; `.venv` existente, bootstrap automático e shell com horário/janela/limite conflitantes |
| Contagem | 289 coletados; 220 `api_blackbox`, 42 `infrastructure_contract`, 27 `static_guard` |
| Métricas e cleanup | `/metrics` principal/última API de fronteira capturados; cleanup com perfil explícito + ausência de containers/rede conferida; counters de processos diferentes não são volume único |

Matriz temporal: 19:59 (dia), 20:00 (noite), 00:00 (noite), 05:59 (noite),
06:00 (dia), 12:00 (dia), em saque e transferência; cada caso prova 100000 e
100001 centavos, saldo incluindo tarifa, destino, extrato, depósito acima do
teto e rejeição sem efeito parcial. O replay confirmou uma operação de
100001 centavos de dia e recuperou-a à noite sem novo débito; nova chave à noite
é rejeitada com QIT001007. As 15 guardas novas são testes de infraestrutura
com dependências simuladas/inspeção estática, não evidência bancária HTTP.

O alvo temporal usou `baas-pytest-f4d8c8c9f41948a1bfd26eaa0f9b5ff9`;
JUnit local `artifacts/test-runs/night-clock.xml`. A regressão final usou
`baas-pytest-e17f7ad40e0d43c98a5b5cde4ddea7fb`; relatório
`artifacts/test-runs/full-final.xml`, métricas/metadados no diretório desse
projeto. Base Git `6e605c9c0ae3cb2121c4d61b4fc5b5d06115486f` + alterações locais,
não commit publicado. API/db/mock originais mantiveram IDs/uptime e relógio
real vazio; não foram alvo da suíte. Relatórios são ignorados pelo
Git; o CI novo os publica como artefato. Não há aprovação remota presumida:
novo commit/push/CI ainda cabem ao grupo. R1 agora inspeciona `test_support`
além de `tests/`. `--collect-only` e execução só de guardas não iniciam Docker.

Procedimento vigente e limites: [README da API](../baas-pme-api/README.md#relógio-determinístico-e-isolamento-automático).
Modo externo exige opt-in, banco descartável e relógio principal preparado;
validador/benchmark usam-no porque já possuem o servidor que estão medindo.
Teardown cobre conclusão/erros normais, não SIGKILL/queda do host. Nenhuma
feature financeira, rota, DDL ou item restante de 9.5 foi implementado aqui.

**Achado adicional do teardown:** uma primeira regressão passou com
**288 testes/114.08 s**, em 18:20:13–18:22:07 UTC, com variáveis conflitantes
no shell (`NIGHT_TIME_OVERRIDE=12:00`, `NIGHT_START=invalid`, limite `1`).
A inspeção posterior identificou que `down` sem ativar o perfil opcional
deixava `api-clock` e sua rede, apesar do retorno 0. O metadado `removed`
dessas primeiras sessões não comprova cleanup completo. Uma nova guarda
teve Red (não lançou erro com container remanescente) e Green após a correção:
perfil `clock` explícito em toda chamada e `ps --all --quiet` vazio antes
de registrar sucesso. Os três resíduos dessas sessões foram removidos por
projeto UUID exato, sem atingir desenvolvimento; dados sintéticos já haviam
sido descartados. O fechamento novo inclui essa 289ª guarda e verifica cleanup.

Métricas finais do principal: QIT001030 = 41 recusas de execução/12 de quote;
QIT001007 = 2 recusas; replay = 21 de antecipação/52 de transação; retries
sintéticos = 2 deadlock/2 serialização. A API auxiliar reinicia nas mudanças de
hora; seu último snapshot não resume todas as fronteiras. Esses counters
complementam as asserções, não são contagem de clientes nem monitoramento contínuo.
RFC 3.4/PDF de quatro páginas e apresentação de dez foram regenerados, com
hashes/overflow e revisão visual do fluxo final/slide de testes conferidos.

Compatibilidade externa também foi exercitada: **19 passed in 38.76s**
(outbox/worker + relógio), e benchmark separado **5 passed in 7.77s**,
200 transferências/parede **8,058 s**. CPU/RAM e diferença do perfil sem reload
em [BENCHMARK §14](BENCHMARK.md#14-t510-bootstrap-determinístico-e-modo-externo).
Isso não é execução integral do script de clone/venv nova nem aprovação remota.

Reconferência externa **após** a correção do teardown: **5 passed in 15.81s**,
worker/deduplicação, 2 testes originais e 2 replays dia→noite, com runtime novo
`baas-pytest-0f603fc9cb484bc3bf3906718123a847` e ambiente de fronteiras separado;
JUnit `artifacts/test-runs/external-final.xml`. Ambos foram removidos pelo
teardown com perfil/checagem de remanescentes, sem modificar desenvolvimento.

## Alinhamento documental posterior ao fechamento — 10/10/2026

**Registro histórico anterior à T5.10/RFC 3.4.** Rodada somente de documentação: regra de líquido positivo e ordem anterior ao
snapshot, contratos/exemplos, resultados atuais versus históricos, entrega/CI
por commit e limites de outbox/migrations foram reconciliados. Sem mudanças de
código da API, DDL, workflow ou implementação do restante de 9.5. Modelo oficial
preservado; registros antigos mantidos e identificados, sem reescrever resultados.

| Verificação desta rodada | Evidência |
|---|---|
| `.venv/bin/python -m pytest tests -q -m static_guard` | **12 passed, 248 deselected**; seções/rotas, erros, DER, hashes/páginas, consolidação, links/âncoras e R1 |
| Coleta sem execução financeira | **260 coletados**; seleções confirmam 206 HTTP, 42 infraestrutura e 12 estáticos |
| Artefatos regenerados | RFC 3.3 de quatro páginas/apresentação de dez; sem overflow, manifesto atualizado; revisão visual dos fluxos e slides alterados |
| Escopo de evidência | Suíte completa/benchmark/métricas **não reexecutados nesta rodada documental**; resultados financeiros mais recentes permanecem 260/75.43 s e benchmark separado de 8,255 s abaixo |

Relatório estático local em
`baas-pme-api/artifacts/p04/20261010085856-final/documentation-coherence.xml`,
ignorado pelo Git como os demais relatórios. Publicação/CI da revisão final e
aceite/clone/ensaio do grupo continuam pendentes.

## Líquido positivo: implementação e Red/Green — 10/10/2026

| Verificação específica inicial, antes dos cinco casos adicionais | Resultado |
|---|---|
| Red antes da implementação | 3 falhas de execução: líquido zero retornou 201; tarifa maior, sem saldo, retornou 500; tarifa de 100% retornou 201. Mais 2 falhas de quote: zero 201/negativo 500. Seleções interrompidas em 3/2 falhas, não são execução integral |
| Green HTTP | **33 passed**, 10.83 s, na `.venv` existente |
| Green PostgreSQL/upgrade | **14 passed**, 1.64 s, após corrigir um nome de tabela no próprio teste |
| Regra e rollback | Tarifas fixa/percentual/combinada, half-up, 1 centavo, seleção múltipla, saldo zero/suficiente, preço vigente/replay; sem consumo de saldo/lastro, snapshots, quote, auditoria ou reserva confirmados |
| Banco existente | Upgrade idempotente com e sem legado; NOT VALID rejeita novas gravações e preserva fatos antigos, inclusive zero/negativo. Sem legado, constraints validadas |

Projeto `baas-p04-net-20261010t082035z`, portas 13010/15442/11090; dados
sintéticos separados do banco de desenvolvimento. Relatórios locais em
`baas-pme-api/artifacts/p04/20261010T082035Z/` (ignorados pelo Git).
O Red produziu dois registros de antecipação e uma cotação sem líquido;
a migração real sobre esse banco preservou-os e protegeu novas gravações.
As duas provas de migração também usam schemas exclusivos, removidos ao final.
Essa compatibilidade não autoriza criar novas operações inválidas nem
reprificar respostas idempotentes antigas.

Após o upgrade, as **duas antecipações antigas de líquido zero** produzidas
no Red também tiveram replay conferido via HTTP: 201/corpo original,
`Idempotent-Replayed: true`, saldo/extrato/checkpoint inalterados. É uma
verificação complementar do legado sintético, não um caso acrescentado à
contagem de pytest (255 naquele marco, 260 no fechamento posterior).

### Fechamento final: snapshots padrão e tarifa extrema

A contagem SQL de rollback foi reforçada para incluir também snapshots de
políticas padrão (`customer_id IS NULL`). Uma reexecução intermediária passou
com **255 testes, 73.47 s**, antes de acrescentar os cinco casos seguintes.

O novo Red reproduziu tarifa fixa `9223372036854775807` + 1 bps sobre bruto
10000: o valor calculado ultrapassa BIGINT e o snapshot falhava com 500 antes
da comparação de líquido. O controller agora calcula/valida **antes** de
persistir preço e usa a mesma política/tarifa na criação do snapshot. A quote
já fazia a validação antes de sua gravação. Não foram definidos os limites
monetários gerais de P0.3/P0.4 nem alterada a semântica da quote TRANSFER.

| Verificação final em banco descartável novo | Resultado |
|---|---|
| Red adicional do extremo | 1 falha real por 500 em vez de 422; seleção interrompida na primeira falha |
| Green da regra completa | **52 passed**, 14.82 s: 36 HTTP + 16 SQL/migração |
| Suíte inteira atual | **260 passed in 75.43s**, 09:05:17–09:06:33 UTC; JUnit em horário local −03:00 |
| Classificação atual | 206 `api_blackbox`, 42 `infrastructure_contract`, 12 `static_guard`; executados juntos na suíte inteira, não novas medições isoladas por marcador |
| Métricas após Green + suíte | QIT001030: 82 recusas de execução/24 de quote; retries sintéticos: 2 deadlock/2 serialização; counters por processo, não clientes únicos |
| Benchmark do código final | **5 passed in 7.89s**, 200 transferências; parede **8,255 s** |
| PDFs/DDL | RFC 3.3, quatro páginas/23 entidades; apresentação dez; CHECKs no DER, hashes/links e catálogo de 40 erros aprovados |

Projeto final `baas-p04-final-20261010085856`, portas 13010/15442/11090;
teste na `.venv` existente da API. Relatórios/JUnit, métricas e benchmark em
`baas-pme-api/artifacts/p04/20261010085856-final/` (ignorados pelo Git).
O banco foi criado vazio para a verificação, depois preenchido por casos
sintéticos; foi removido somente após a coleta final. O ambiente original
não foi alvo dos testes. Código financeiro permaneceu igual entre a suíte
final e a carga. Método/CPU/RAM em [BENCHMARK §13](BENCHMARK.md#13-fechamento-final-validação-anterior-ao-snapshot-de-preço).

### Regressão completa, métricas e benchmark desta implementação

**Registro intermediário anterior ao ajuste do snapshot/tarifa extrema.**
Preservado para rastreabilidade; a evidência do código final é a seção acima.

Execução **2026-10-10 08:39:21–08:42:27 UTC**, pelo validador de entrega em
clone local + snapshot, `.venv`/banco novos e Compose exclusivo. Base Git
`160311850dbfbc9427ed7f5049047aada951e8b3`, 27 entradas modificadas/novas
na origem ao copiar o snapshot. O código financeiro é o da implementação inicial
da regra, anterior ao ajuste de ordem do snapshot e aos cinco casos extremos;
não é validação do commit publicado nem CI remoto da revisão nova.

| Etapa | Resultado |
|---|---|
| Suíte completa | **255 passed in 72.98s** |
| Somente HTTP (`api_blackbox`) | **203 passed**, 64.74 s; 52 deselected |
| Contratos SQL/worker (`infrastructure_contract`) | **40 passed**, 11.56 s; 215 deselected |
| Guardas documentais (`static_guard`) | **12 passed**, 0.43 s; 243 deselected |
| Guardas na origem após os ajustes finais de texto/PDF | **12 passed**, 243 deselected; rechecagens de 0.14–0.16 s, incluindo 422/líquido nas tabelas das duas rotas; não recontar como novos casos |
| Benchmark separado | **5 passed in 7.41s**, 200 transferências; parede **7,753 s** |
| Compilação/dependências | compileall sem erro; pip check sem incompatibilidade na venv nova e na existente |
| Container e bootstrap | uid=100(user), não-root; DDL novo, API/DB saudáveis e MockServer local |
| Métricas | exposition obtida antes do benchmark; QIT001030: 72 recusas de execução/20 de quote ao longo das seleções e suíte completa; retries sintéticos: 4 deadlock/4 serialização |
| Cleanup | saída 0, projeto exclusivo removido; checkout/relatórios preservados |
| Banco original | migração aplicada sem recriar volume; preflight: 0 antecipações/0 cotações incompatíveis; ambos os CHECKs confirmados como validados; mesmos IDs dos containers originais |

Artefatos locais ignorados:
`baas-pme-api/artifacts/delivery/20261010T083920Z/`. Checkout preservado:
`/tmp/baas-delivery-x8U6PEUz/repository`. A revisão final apenas do texto de
ressalva/PDF foi reconferida pelas guardas na origem; o código financeiro
testado não mudou. CPU/RAM e limites da coleta em
[BENCHMARK §12](BENCHMARK.md#12-líquido-positivo-regressão-completa-e-benchmark).
Counters são por processo, não clientes únicos ou SLO; os testes de recusa
conferem que QIT001030 não incrementa o retry transitório. Coletores/Alertmanager
não foram instalados. Todo resultado anterior abaixo permanece histórico.

## Evidência remota de publicação e CI — 10/10/2026

O [BaaS PME CI, execução 38036090796](https://github.com/Faraoh-Back/BootcampQITech_UnicampE-Racing/actions/runs/38036090796)
foi confirmado como `completed/success` para
`160311850dbfbc9427ed7f5049047aada951e8b3`, correspondente à `main` e ao HEAD
local no momento da consulta pública. Os PDFs dessa versão estavam acessíveis
sem autenticação e tinham blobs iguais aos arquivos locais verificados.
Método, tamanhos, identificadores e fronteira em [ENTREGA §5.1](entrega/ENTREGA.md#51-evidência-remota-confirmada).

Esta é evidência de execução remota do workflow, não uma nova medição local,
benchmark ou confirmação de ensaio/clone independente. Não atribui ao run
contagens/durações que não foram obtidas de seus logs. Alterações posteriores
no código/documentos/PDFs requerem publicação e CI da nova revisão. Esse run
anterior não comprova a implementação posterior de líquido positivo;
os números históricos abaixo permanecem preservados.

## Consolidação documental — 10/10/2026

Os guias foram reunidos nos destinos do [índice da documentação](README.md#consolidação-dos-guias--10102026),
reduzindo cinco arquivos Markdown sem descartar conteúdo. Foram acrescentadas
duas guardas: preservação das seções/históricos nos documentos canônicos e
resolução dos links locais/âncoras Markdown. Ambas falharam antes da migração;
a segunda também identificou dois links já quebrados no guia histórico de setup,
corrigidos ao reuni-lo em HISTORICO.

| Verificação desta rodada documental | Resultado |
|---|---|
| Guardas estáticas na `.venv` da API | **12 passed, 196 deselected**, 0.13 s |
| Coleta da suíte, sem executar cenários HTTP/SQL | **208 testes coletados**: 12 estáticos + 170 HTTP + 26 de infraestrutura |
| Artefatos regenerados | RFC com quatro páginas e apresentação com dez; sem overflow, DER e hashes conferidos pelas guardas |
| Preservação | Textos migrados comparados com as fontes anteriores; seção 9.5 do plano mantida literalmente |

Não houve mudança de código da API, DDL, regras financeiras, workflow ou carga
de benchmark. A suíte HTTP/infraestrutura e o benchmark **não foram reexecutados
nesta consolidação**: suas evidências permanecem na execução isolada abaixo.
Não apresentar a coleta de 208 testes como uma nova execução completa aprovada.

## Validação final da entrega em snapshot isolado

Executada em **2026-10-10 07:30:27–07:33:26 UTC**, por
`bash scripts/validate_delivery.sh --snapshot`: clone local com as alterações
de trabalho, venv/banco novos, Compose exclusivo e portas 13000/15432/11080.
Base `524c7608ba305978bae7c97ece7348b8961c8a6a`, 44 entradas modificadas/novas
na origem. Não é clone remoto do commit publicado nem teste humano em VM virgem.
Foram acrescentadas quatro guardas de entrega à revisão anterior de 202 testes;
nenhum comportamento financeiro/DDL ou item 9.5 foi implementado nesta rodada.

| Execução | Resultado |
|---|---|
| Suíte completa em venv nova | **206 passed in 61.55s** |
| API estritamente HTTP | **170 passed**, 51.58 s; 36 deselected |
| Contratos de infraestrutura | **26 passed**, 9.06 s; 180 deselected |
| Guardas estáticas | **10 passed**, 1.10 s; 196 deselected |
| Benchmark S7c separado | **5 passed in 7.14s**; parede **7,506 s**; 200 operações |
| Métricas | GET `/metrics` aprovado; exposition salva após a suíte e antes do benchmark |
| Compilação/dependências | compileall sem erro; pip check sem incompatibilidade na venv nova |
| Container API | uid=100(user), não-root; API/DB healthy e mock Up |
| Artefatos PDF | RFC com quatro páginas; apresentação com dez; DER vetorial, fonte e SHA-256; revisão visual pelo agente |
| Cleanup isolado | exit_code=0; só containers/rede/volumes descartáveis dessa execução removidos |
| Ambiente original | Containers originais saudáveis, mesmos IDs; banco original não foi alvo das suítes |

Artefatos: `baas-pme-api/artifacts/delivery/20261010T073026Z/`, ignorados pelo
Git, com ambiente/pip-freeze, resultados/JUnit, metrics.prom e benchmark.
Reprodução e confirmações humanas/externas em [ENTREGA](entrega/ENTREGA.md).
As durações não são SLO; a diferença para execuções anteriores não prova ganho
de desempenho. O mesmo host/Docker e caches de imagem foram reutilizados.

As novas guardas conferem seções/rotas no modelo oficial, todas as entidades e
relações do DER, PDF/páginas/hashes e, naquele marco, que P0.4 não aparecia
como implementada. A guarda atual distingue líquido positivo implementado
dos demais itens pendentes de 9.5.
Seu Red foi executado antes dos artefatos: quatro falhas por arquivos ainda
ausentes; Green com dez guardas. O teste de fumaça do MockServer foi corrigido
após reproduzir porta publicada 11080 versus escuta interna 1080. Falhas
intermediárias de artefato/script foram corrigidas e não são resultado final
verde nem defeito financeiro escondido; registro em ENTREGA.

## Revisão anterior de 10/10/2026 — 202 testes (preservada)

Executado em 2026-10-10, com Python de `baas-pme-api/.venv`, API real no
Compose e `NIGHT_TIME_OVERRIDE=21:00`. Partiu-se de 155 testes aprovados;
foram acrescentados 47 casos líquidos e reescrita a jornada de ponta a ponta.

| Execução | Resultado |
|---|---|
| Suíte completa final: `pytest tests -q` | **202 passed in 102.75s** |
| API estritamente HTTP: `-m api_blackbox` | **170 passed**, 89.26 s |
| Contratos de infraestrutura: `-m infrastructure_contract` | **26 passed**, 14.12 s |
| Guardas estáticas: `-m static_guard` | **6 passed**, 0.26 s, após a revisão final dos documentos |
| Carga canônica S7c | **5 passed in 11.48s**; 200 transferências, parede 12,381 s |
| Compilação | `compileall -q src tests` concluído sem erro |
| Compatibilidade de dependências | `pip check`: No broken requirements found |
| Integridade do diff | `git diff --check` sem erro |
| Containers finais | API/banco healthy, MockServer Up; API `uid=100(user)`, não-root; `pip check` da imagem sem incompatibilidade |

As durações de execuções separadas não somam necessariamente a duração do
conjunto. Cada categoria tem dependências/estado próprio; execute-as
sequencialmente. HTTP inclui casos legados selecionáveis por `legacy`.
O benchmark contém somente transferências cruzadas, não toda a concorrência
S7c. Recursos/ambiente e artefatos estão em BENCHMARK.

| Rota / Endpoint | Código QIT | Status HTTP | Descrição do Cenário | Arquivo de Teste |
|---|---|---|---|---|
| **Segurança / Global** | `Sucesso` | 204 | Healthcheck responde corretamente | `tests/integration/test_healthcheck.py` |
| **Segurança / Global** | `QIT000002` | 403 | `INTERNAL-TOKEN` ausente ou inválido | `tests/integration/test_smoke.py` |
| **Segurança / Global** | `QIT000404` | 404 | Caminho HTTP inexistente | `tests/integration/test_healthcheck.py` |
| **Segurança / Global** | `QIT000405` | 405 | Método HTTP não permitido | `tests/integration/test_healthcheck.py` |
| `POST /customer` | `Sucesso` | 201 | Cliente criado com sucesso | `tests/integration/customer/test_customer.py` |
| `POST /customer` | `QIT000001` | 400 | Payload fora do schema | `tests/integration/customer/test_customer.py` |
| `POST /customer` | `QIT001003` | 409 | Documento (CPF/CNPJ) duplicado | `tests/integration/customer/test_customer.py` |
| `POST /customer` | `QIT001004` | 409 | E-mail duplicado | `tests/integration/customer/test_customer.py` |
| `POST /customer` | `QIT001010` | 422 | CPF/CNPJ com dígitos inválidos | `tests/integration/customer/test_customer.py` |
| `GET /customer/{customer_key}` | `Sucesso` | 200 | Consulta de cliente existente | `tests/integration/customer/test_customer.py` |
| `GET /customer/{customer_key}` | `QIT001001` | 404 | Cliente não encontrado | `tests/integration/customer/test_customer.py` |
| `POST /account` | `Sucesso` | 201 | Conta criada com sucesso | `tests/integration/account/test_account.py` |
| `POST /account` | `QIT000001` | 400 | Payload fora do schema | `tests/integration/account/test_account.py` |
| `POST /account` | `QIT001001` | 404 | `customer_key` não existe | `tests/integration/account/test_account.py` |
| `GET /account/{account_key}` | `Sucesso` | 200 | Consulta de conta existente | `tests/integration/account/test_account.py` |
| `GET /account/{account_key}` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/account/test_account.py` |
| `PUT /account/{account_key}/block` | `Sucesso` | 200 | Conta bloqueada com sucesso | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/block` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/block` | `QIT001019` | 409 | Transição de status inválida | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/cancel` | `Sucesso` | 200 | Conta cancelada com sucesso | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/cancel` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/account/test_account_lifecycle.py` |
| `PUT /account/{account_key}/cancel` | `QIT001019` | 409 | Transição de status inválida | `tests/integration/account/test_account_lifecycle.py` |
| `POST /account/{account_key}/transaction` | `Sucesso` | 201 | Depósito/Saque/Transferência efetuada | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT000001` | 400 | Payload inválido ou tipo incorreto | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT001018` | 400 | Header `Idempotency-Key` ausente | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT001002` | 404 | Conta de origem/destino inexistente | `tests/integration/transaction/test_transfer.py` |
| `POST /account/{account_key}/transaction` | `QIT001006` | 409 | Conta bloqueada ou cancelada | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT001008` | 409 | Idempotency Key reutilizada com dados distintos | `tests/integration/transaction/test_transaction.py` |
| `POST /account/{account_key}/transaction` | `QIT001005` | 422 | Saldo insuficiente | `tests/integration/transaction/test_transaction_concurrency.py` |
| `POST /account/{account_key}/transaction` | `QIT001007` | 422 | Limite noturno excedido | `tests/integration/transaction/test_night_limit.py` |
| `POST /account/{account_key}/transaction` | `QIT001012` | 422 | Origem e destino iguais em transferência | `tests/integration/transaction/test_transfer.py` |
| `GET /account/{account_key}/transaction/{transaction_key}` | `Sucesso` | 200 | Consulta de transação concluída | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transaction/{transaction_key}` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transaction/{transaction_key}` | `QIT001011` | 404 | Transação inexistente ou de outra conta | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transactions` | `Sucesso` | 200 | Extrato paginado retornado | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transactions` | `QIT000001` | 400 | Parâmetros de consulta inválidos | `tests/integration/transaction/test_transaction_statement.py` |
| `GET /account/{account_key}/transactions` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/transaction/test_transaction_statement.py` |
| `POST /account/{account_key}/billing-plan` | `Sucesso` | 201 | Plano de boletos gerado com sucesso | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan` | `QIT000001` | 400 | Payload inválido | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan` | `QIT001017` | 422 | Vencimento inicial no passado | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan` | `QIT001009` | 502 | Indisponibilidade do conector externo | `tests/integration/billing_plan/test_billing_plan.py` |
| `GET /account/{account_key}/billing-plan/{plan_key}` | `Sucesso` | 200 | Consulta do plano e status dos boletos | `tests/integration/billing_plan/test_billing_plan.py` |
| `GET /account/{account_key}/billing-plan/{plan_key}` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/billing_plan/test_billing_plan.py` |
| `GET /account/{account_key}/billing-plan/{plan_key}` | `QIT001013` | 404 | Plano inexistente ou de outra conta | `tests/integration/billing_plan/test_billing_plan.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `Sucesso` | 201 | Reajuste aplicado com sucesso | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT000001` | 400 | Payload/Índice inválido | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT001002` | 404 | Conta não encontrada | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT001013` | 404 | Plano inexistente ou de outra conta | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT001014` | 409 | Reajuste/Lote 2 já aplicado previamente | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/billing-plan/{plan_key}/adjustment` | `QIT001009` | 502 | Conector externo (BCB/Boletos) indisponível | `tests/integration/billing_plan/test_billing_plan_adjustment.py` |
| `POST /account/{account_key}/credit-advance` | `Sucesso` | 201 | Antecipação de crédito concluída | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT000001` | 400 | Payload inválido | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001018` | 400 | Header `Idempotency-Key` ausente | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001015` | 404 | Boleto inexistente ou de outra conta | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001006` | 409 | Conta não aprovada | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001008` | 409 | Idempotência com payload conflitante | `tests/integration/credit_advance/test_credit_advance.py` |
| `POST /account/{account_key}/credit-advance` | `QIT001016` | 409 | Boleto não elegível (não PENDING / já antecipado) | `tests/integration/credit_advance/test_credit_advance.py` |

---

## Observações sobre Erros Legados (`sample_entity`)

- **`QIT002001` a `QIT002004` e `QIT000010`**: Presentes nos arquivos de `tests/integration/sample_entity/`. São exclusivos das entidades de demonstração e não fazem parte das rotas e regras de negócio de produção do ecossistema BaaS PME.

---

## Entregas transversais e evolução comercial

| Rota / comportamento | Código / resultado | Evidência de teste |
|---|---|---|
| `POST /user`, `/auth/login`, `/auth/refresh`, `/auth/logout` | sessão, rotação, revogação, `QIT001020`–`QIT001023` | `tests/integration/auth/test_auth.py` |
| `GET /audit-events`, `/checkpoint` | cadeia SHA-256, append-only, checkpoint | `tests/integration/audit/test_audit.py` |
| `GET /metrics` | métricas sem PII e erros/latência/locks | `tests/integration/metrics/test_metrics.py` |
| Worker de outbox | lease, retry, chave estável e não republicação de sucesso confirmado; entrega at-least-once exige deduplicação do consumidor | `tests/integration/outbox/test_outbox.py` (infraestrutura SQL/subprocesso + HTTP/MockServer) |
| Timeout/retry PostgreSQL | `QIT001024`, `QIT001025`; não repetir `422` | `tests/integration/timeouts/test_timeouts.py`, `tests/integration/transaction/test_transient_retry.py` |
| `POST /pricing-policy` | preço PME, fallback, nova versão, snapshots | `tests/integration/pricing/test_pricing_policy.py` |
| `POST /risk-policy` | `QIT001026`, `QIT001027`, teto diário concorrente | `tests/integration/risk_policy/test_risk_policy.py` |
| `POST /account/{key}/quote` | preço/risco vigente, expiração informativa e recálculo | `tests/integration/quote/test_quote.py` |
| `/policy-change-request` | draft, submissão, outro OWNER aprova, autoaprovação `QIT001029` | `tests/integration/policy_change_request/test_maker_checker.py` |
| Jornada PME | cobrança própria, antecipação única, crédito/tarifa no extrato | `tests/integration/credit_advance/test_receivables_flow.py`, `tests/test_pme_journey.py` |
| Líquido positivo na antecipação/cotação | `QIT001030`, arredondamento, 1 centavo, tarifa extrema antes do snapshot, ausência de efeitos, replay/recálculo; CHECKs e upgrade sem reescrever legado | `tests/integration/credit_advance/test_positive_net.py` (36 HTTP), `test_positive_net_database.py` (16 infraestrutura, incluindo snapshots padrão) |
| Guarda R1 | testes de produto não importam módulos internos `src/` | `tests/test_r1_guard.py` |

## Complemento do catálogo: códigos transversais e legado

Cada código de `DECISOES.md` tem cenário que o provoca: o núcleo está na
tabela inicial; os códigos restantes estão abaixo. A existência de um cenário
por código **não** prova cada código em cada rota nem toda a matriz de papéis.

| Código | HTTP | Rota / cenário | Teste que o provoca |
|---|---|---|---|
| `QIT001020` | 401 | JWT inválido; refresh reutilizado; proposta sem JWT | `auth/test_auth.py`, `policy_change_request/test_policy_contract.py` |
| `QIT001021` | 401 | Login com senha incorreta ou maior que 72 bytes UTF-8 | `auth/test_auth.py`, `auth/test_password_contract.py` |
| `QIT001022` | 403 | PME alheia/papel proibido em conta, cotação ou proposta | `auth/test_auth.py`, `quote/test_quote_authorization.py`, `policy_change_request/test_policy_contract.py` |
| `QIT001023` | 409 | E-mail de usuário duplicado | `auth/test_auth.py` |
| `QIT001024` | 503 | Transação com lock PostgreSQL retido por outra sessão | `timeouts/test_timeouts.py` (infraestrutura) |
| `QIT001025` | 503 | Deadlock/serialização persistente por SQLSTATE sintético | `transaction/test_transient_retry.py` (infraestrutura) |
| `QIT001026` | 409 | Produto desabilitado na política vigente | `risk_policy/test_risk_policy.py`, `policy_change_request/test_policy_governance.py` |
| `QIT001027` | 422 | Teto de valor, quantidade ou consumo diário excedido | `risk_policy/test_risk_policy.py`, `risk_policy/test_risk_atomicity.py` |
| `QIT001028` | 404 | Proposta inexistente na submissão/aprovação | `policy_change_request/test_policy_contract.py` |
| `QIT001029` | 409 | Autoaprovação, estado inválido, submissão por outro criador ou segunda aprovação concorrente | `policy_change_request/test_maker_checker.py`, `policy_change_request/test_policy_governance.py` |
| `QIT001030` | 422 | Nova antecipação/cotação CREDIT_ADVANCE com tarifa >= bruto, inclusive saldo suficiente; nenhuma alteração financeira confirmada | `credit_advance/test_positive_net.py`, `credit_advance/test_positive_net_database.py` (rollback SQL) |
| `QIT000500` | 500 | Falha inesperada injetada no INSERT de lançamento; corpo sanitizado, sem retry nem efeito financeiro | `transaction/test_transient_retry.py` (infraestrutura) |
| `QIT000010` | 400 | Intervalo invertido de datas na listagem legada | `sample_entity/test_sample_entities.py` (infraestrutura/legado) |
| `QIT002001` | 404 | Entidade legada inexistente | `sample_entity/test_sample_entity_get.py` |
| `QIT002002` | 409 | Alteração de entidade legada em estado final | `sample_entity/test_sample_entity_update.py` |
| `QIT002003` | 422 | Idade abaixo do mínimo no legado | `sample_entity/test_sample_entity_create.py` |
| `QIT002004` | 422 | Data impossível no legado | `sample_entity/test_sample_entity_create.py` |

Os caminhos abreviados nessa tabela são relativos a `tests/integration/`.
Há 40 códigos catalogados: 30 do produto, seis globais e quatro do legado.
`QIT000010` é um código global cujo cenário atual é do legado.

## Features e pipelines: o que a evidência comprova

| Feature / pipeline | Evidência e limite |
|---|---|
| S1–S2b: cadastro, conta e ciclo de vida | Sucesso/erros/UUID, eventos, bloqueio/cancelamento e impedimento de movimentação em conta não aprovada |
| S3–S6: depósito, saque, transferência, extrato e idempotência | Sinais do ledger, tarifa separada, saldo, 404 sem revelar lançamento de outra conta, paginação, replay, conflito e rollback |
| S7a–S7c: concorrência financeira | Saques disputando saldo, 40 transferências cruzadas, chave compartilhada, disputa entre saque/transferência e antecipação do mesmo lastro |
| S8–S10/S18: recebíveis | Lote 1/2, calendário de fim de mês, índice Decimal, erros offline do MockServer, propriedade/eligibilidade e antecipação única; não liquidação ou empréstimo |
| S11: identidade | Bcrypt, login, refresh rotativo, sessões múltiplas, logout, papéis e rejeição de senha acima de 72 bytes |
| S12: auditoria | Cadeia SHA-256 reconstruída por HTTP/checkpoint; trigger de UPDATE/DELETE verificada em contrato SQL; não proteção contra administrador |
| S13–S15: operação | Logs/métricas, isolamento de conta travada, timeout, interrupção do cliente, lease/retry de outbox; não stack de monitoramento instalado |
| S16: retry transacional | SQLSTATE `40P01` e `40001` injetados; nova tentativa tem um efeito; esgotamento/falha inesperada não grava saldo/ledger; regra de negócio não é repetida |
| S17/S19/S20: personalização | Precedência PME/padrão, versões/snapshots, tetos concorrentes, produto desabilitado, cotação informativa e autorização por PME |
| Regra posterior: antecipação com líquido positivo | Execução/cotação CREDIT_ADVANCE, QIT001030 antes do snapshot de preço/quote, rollback incluindo política padrão, um centavo líquido, preço vigente/replay; 36 HTTP + 16 SQL/migração. Não define cotação TRANSFER nem limites numéricos gerais |
| S21: maker-checker | Contrato aninhado estrito de preço/risco, segregação criador/aprovador, estado pendente não aplicável, três corridas com dois aprovadores e uma versão publicada |
| Jornada integrada T5.1 | Dois OWNERs publicam preço, emitem/reajustam, cotam/antecipam, transferem/sacam, percorrem quatro páginas, reconciliam oito lançamentos com saldo e bloqueiam/cancelam com trilha auditável |
| Relógio/bootstrap T5.10 | Projeto/banco/portas exclusivos, 21h no principal, fronteiras 20h/6h/meia-noite/dia, replay entre janelas, cleanup e restauração; sem alteração de desenvolvimento ou parâmetro de relógio por HTTP |
| Pipeline CI | Dependências/Compose/compilação → static_guard → suíte completa gerida (HTTP + contratos SQL/worker + estáticos) → JUnit/métricas/metadados → cleanup da sessão; workflow novo validado localmente, remoto confirmado somente para `1603118` da versão anterior |
| Consistência documental | Guardas estáticas de seções do modelo, todos os métodos/rotas registrados, códigos catalogados e 23 tabelas do produto no DER; não comparação completa de payloads/FKs nem validação visual de PDF |

## Revisão: correções com regressão comprovada

Foram reproduzidas dez falhas em 19 casos antes das correções de schema,
cotação e senha. O mesmo conjunto passou após implementá-las. Não se atribui
TDD retrospectivo ao histórico inteiro: o Red/Green aqui é da revisão.

- O JSON Schema agora exige `int` nativo, inclusive em políticas aninhadas:
  rejeita decimal JSON `10.0`, string e booleano antes de emissor/regra de negócio.
- Propostas reutilizam os schemas estritos de preço/risco, incluindo UUID e
  proibição de `customer_key` dentro da política.
- Cotações com JWT exigem vínculo/papel sobre a conta; JWT inválido não é ignorado.
- Bcrypt não recebe senha acima de 72 bytes UTF-8; não há truncamento silencioso.
- Helpers HTTP têm timeout e não imprimem falha esperada ao interpretar 204.
  O `.env` é carregado antes de helpers que capturam a credencial.
- Parâmetros de retry foram ligados ao Compose; constantes/env de preço
  obsoletos foram removidos. Tarifas continuam vindo do banco.
- requests 2.32.4 corrige o aviso específico de credenciais `.netrc`
  [do mantenedor](https://github.com/psf/requests/security/advisories/GHSA-9hjg-9r4m-mvj7).
  Isso não certifica a ausência de outras vulnerabilidades.

## Garantias verificadas e limitações conhecidas: lacunas pendentes

| Prioridade | Achado / próxima prova necessária | Plano |
|---|---|---|
| P0 | Líquido positivo da antecipação/cotação implementado; demais fronteiras pendentes: cotação de transferência, limites BIGINT e índices <= -100% ainda exigem especificação/validação segura | P0.3/P0.4 (parcial) |
| P0 | Ledger/eventos/snapshots ainda não têm proteção append-only SQL equivalente à auditoria; saldo é projeção sem rotina de reconciliação | P0.1/P0.2 |
| P1 | Token interno tem autoridade ampla, JWT é opcional fora de propostas, cadastro de OWNER e políticas diretas podem contornar segregação | P1.4/P1.8 |
| P1 | Faltam controles produtivos de abuso de login, rotação de chaves e gestão administrativa de sessões | P1.5 |
| P1 | Emissão externa antes da validação final pode criar boleto órfão; billing não tem idempotência de cliente e lote 2 faz I/O com lock de plano | P1.2 |
| P1 | Preço/risco contêm regras em repositories e auditoria executa SQL em utils | P1.7 |
| P1 | Orçamento de 15 s não é deadline global; virada diária de risco usa data do runtime; timestamps sem offset. Há upgrade SQL pontual de líquido positivo, não ferramenta/histórico geral de migrations | P1.3/P1.9 |
| P1 | Lease de lote de outbox pode vencer durante publicação; ack obsoleto não deve contar entrega; faltam dead-letter e operação de recuperação | P1.6 |
| P1 | Exportação completa da auditoria, cadeia global serializada e paginação offset não são provas de escalabilidade/snapshot estável sob novas escritas | P1.10 |
| P1 | Erros inesperados e exceções de bibliotecas podem escrever parâmetros SQL/URLs em traceback; logs normais sem body não equivalem a sanitização universal | P1.11 |
| P1 | Backup/restore e retomada financeira após perda de dados não foram comprovados pela revisão | P1.12 |
| P2 | PDFs gerados/revistos pelo agente; aceite do time, ensaio e clone remoto/Linux novo por outra pessoa pendentes. CI/publicação comprovados para `1603118`, não para a revisão posterior de líquido positivo/documentação | T5.3/T5.5/T5.7/T5.9/P2.2 |
| P2 | Combinações de papel/rota/estado, expiração/calendário e quedas não são exaustivas; faltam capacidade sustentada e alertas efetivamente exercitados | P2.3/P2.4 |

Esses itens estão documentados como lacunas, não mascarados por testes verdes.
Também faltam testes de todas as transições/papéis em cada rota, expiração
temporal controlada de JWT/cotação, todos os modos de queda de worker/conector
e capacidade sustentada. R1 é defendida pela suíte HTTP; os testes que injetam
SQLSTATE são contratos de infraestrutura, não reprodução de um deadlock real.
