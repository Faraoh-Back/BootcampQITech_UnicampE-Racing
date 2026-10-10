# Documentação: onde buscar cada evidência

O produto ativo é `baas-pme-api/`; `bootcamp-biblioteca-api/` é um exercício
independente e suas três referências Markdown descrevem a biblioteca, não o
BaaS PME. `sample_entity` é legado ainda ativo na API, fora do produto financeiro.

O enquadramento adotado é **garantias verificadas e limitações conhecidas**.
DECISOES 3.5.1 registra a regra implementada de líquido positivo com exemplos
e `422 QIT001030`; COBERTURA registra os testes e o README da API, o upgrade
sem apagar histórico. P0.4 do plano está parcial: as outras fronteiras econômicas
continuam pendentes. Não confundir essa entrega específica com conclusão de 9.5.

Publicação e CI estão [confirmados por commit](entrega/ENTREGA.md#51-evidência-remota-confirmada)
para `1603118`. A confirmação não cobre alterações posteriores; clone independente,
revisão dos PDFs e ensaio serão realizados pelo grupo e continuam pendentes.

## Estado vigente — 10/10/2026

| Assunto | Referência vigente / limite |
|---|---|
| Arquitetura e apresentação | RFC 3.4 integral e síntese de quatro páginas; apresentação de dez slides; seções do modelo oficial preservadas |
| Contrato de antecipação | [DECISOES §3.5.1](DECISOES.md#351-líquido-positivo-regra-implementada-e-validada): líquido > 0 na criação/cotação CREDIT_ADVANCE; validação antes do snapshot de preço; 422/QIT001030; replay preservado |
| Resultado completo mais recente | [COBERTURA — relógio/bootstrap T5.10](COBERTURA.md#relógio-determinístico-e-bootstrap-automático--10102026); execuções anteriores permanecem datadas, não substituem esse fechamento |
| Medição de recursos mais recente | [BENCHMARK §14](BENCHMARK.md#14-t510-bootstrap-determinístico-e-modo-externo); transferência cruzada local, não capacidade da antecipação ou SLO |
| Reproduzir / atualizar banco existente | [README da API](../baas-pme-api/README.md); pytest prepara banco/portas/relógio isolados automaticamente; upgrade pontual sem apagar histórico |
| Pendências | [Rodada 5](PLANO_DE_EXECUCAO.md#9-rodada-5-entrega-9h) para aceite/clone/ensaio/publicação da revisão final; [9.5](PLANO_DE_EXECUCAO.md#95-garantias-verificadas-e-limitações-conhecidas-correções-e-hardening) para limites e hardening ainda não entregues |

Em caso de divergência, confira implementação/DDL e evidência datada; não
resolva o conflito apenas escolhendo a frase mais favorável. DECISOES define
o contrato, COBERTURA/BENCHMARK comprovam execuções e PLANO registra estado.
RFC e slides sintetizam essas referências, sem criar garantias adicionais.

| Documento | Função / autoridade | Quando consultar |
|---|---|---|
| [RFC](RFC.md) | Síntese arquitetural no modelo oficial: problema, solução, rotas, DER e fluxos | Defesa técnica e versão final para a banca |
| [Modelo oficial](bootcamp-rfc-modelo.md) | Estrutura e orientações fornecidas pela organização | Conferir seções fixas e preparar PDF de 2–4 páginas |
| [Entrega e artefatos](entrega/ENTREGA.md) | RFC de quatro páginas, apresentação, roteiro de defesa e execução isolada | Gerar/revisar PDFs, reproduzir validação e fechar confirmações humanas |
| [DECISOES](DECISOES.md) | Contrato detalhado vigente: decisões D1–D16, regras, payloads, erros e limites | Implementação/integração e explicação dos contratos |
| [README da API](../baas-pme-api/README.md) | Guia único de instalação, execução, camadas e comandos de validação | Subir o serviço, executar testes e localizar código |
| [COBERTURA](COBERTURA.md) | Matriz de features/erros/testes, resultados medidos e lacunas da revisão | Sustentar afirmações de qualidade com evidência |
| [BENCHMARK](BENCHMARK.md) | Método, ambiente, resultados e limites da medição local de concorrência | Citar desempenho sem prometer capacidade/SLO |
| [Regras de alerta — README da API](../baas-pme-api/README.md#regras-operacionais-de-alerta-s15) | Exemplos de regras operacionais, ainda sem stack coletor instalado | Planejar observabilidade produtiva, não provar alertas enviados |
| [PLANO_DE_EXECUCAO](PLANO_DE_EXECUCAO.md) | Histórico de tarefas, estado de entrega e backlog 9.5 | Saber o que está concluído, parcial ou futuro |
| [Checkpoint T3.1 — plano §13](PLANO_DE_EXECUCAO.md#13-checkpoint-histórico-t31) | Registro histórico da evolução, não especificação vigente | Entender marcos anteriores sem reutilizar contagens antigas |
| [Arquivo histórico consolidado](arquivo/HISTORICO.md) | Conteúdo anterior dos guias consolidados, preservado integralmente | Consulta histórica, não operação ou contrato atual |

## Como montar a versão final da RFC

1. Comece pelo modelo oficial; preserve exatamente suas duas seções e cinco
   subseções. O principal desafio técnico fica em **Fluxos**.
2. Use `DECISOES.md` para termos e contratos. Confira rotas em `src/app.py` e
   relacionamentos/restrições em `database/database.sql`; código divergente
   indica um achado, não autorização para inventar uma garantia documental.
3. Use `COBERTURA.md` para os resultados atuais, inclusive o tipo de teste.
   “Não importa src” e “somente HTTP” são evidências diferentes.
4. Use `BENCHMARK.md` para carga/ambiente/data e recursos observados. Uma
   execução local verde não é capacidade garantida de produção.
5. Consulte 9.5 do plano para não apresentar backlog como entregue; use
   a [seção de alertas do README da API](../baas-pme-api/README.md#regras-operacionais-de-alerta-s15)
   somente como proposta de monitoramento.
6. A síntese [RFC_FINAL.md](entrega/RFC_FINAL.md) preserva as seções/rotas e os
   fluxos; seu PDF e DER vetorial são gerados pelas ferramentas de entrega.
   Guardas conferem entidades/relações, páginas e hashes, mas a legibilidade
   ainda exige revisão visual. O conteúdo integral continua em RFC/DECISOES.

COBERTURA é a fonte canônica das contagens. Resumos no plano/entrega apontam
para a execução datada correspondente, sem tratar uma coleta como execução.
Os marcos
antigos de 143/155 testes e benchmarks anteriores permanecem identificados
como históricos. Não usar “100% seguro” como conclusão, mesmo após fechar
backlog. Garantias de imutabilidade, formato de erro, gateway e entrega externa
devem respeitar mecanismo, teste e fronteira realmente demonstrados.

## Consolidação dos guias — 10/10/2026

Foram reduzidos cinco arquivos Markdown, sem descarte de conteúdo. Os caminhos
anteriores abaixo são referências históricas, não arquivos a manter em paralelo.
Links e guardas documentais usam os destinos atuais; referências textuais antigas
no backlog 9.5 devem ser interpretadas por este mapa, sem alterar seu escopo.

| Caminho anterior | Destino atual |
|---|---|
| `entrega/DEFESA.md` | [ENTREGA §6 — defesa e ensaio](entrega/ENTREGA.md#6-defesa-técnica-e-ensaio) |
| `CHECKPOINT_T3_1.md` | [PLANO §13 — checkpoint histórico](PLANO_DE_EXECUCAO.md#13-checkpoint-histórico-t31) |
| `ALERTAS.md` | [README da API — regras de alerta](../baas-pme-api/README.md#regras-operacionais-de-alerta-s15) |
| `arquivo/COMO_INICIAR_T0_1.md`, `arquivo/ORGANIZACAO_API_ANTERIOR.md` e `COMO_INICIAR.md` | [HISTORICO — textos anteriores](arquivo/HISTORICO.md); operação vigente no [README da API](../baas-pme-api/README.md) |

RFC, DECISOES, PLANO, COBERTURA e BENCHMARK continuam separados porque mantêm
arquitetura, contratos, tarefas e evidências de naturezas distintas. RFC_FINAL
é síntese para a banca, não substituto da referência integral. PDFs, fontes,
SVGs, manifesto e ferramentas são necessários para reprodução da entrega.
