# Documentação: onde buscar cada evidência

O produto ativo é `baas-pme-api/`; `bootcamp-biblioteca-api/` e `sample_entity`
são material-base, não features do BaaS PME.

O enquadramento adotado é **garantias verificadas e limitações conhecidas**.
DECISOES 3.5.1 registra a regra aprovada de líquido positivo com exemplos;
P0.4 do plano registra sua implementação pendente. Não confundir aprovação
documental com comportamento já validado na API.

| Documento | Função / autoridade | Quando consultar |
|---|---|---|
| [RFC](RFC.md) | Síntese arquitetural no modelo oficial: problema, solução, rotas, DER e fluxos | Defesa técnica e versão final para a banca |
| [Modelo oficial](bootcamp-rfc-modelo.md) | Estrutura e orientações fornecidas pela organização | Conferir seções fixas e preparar PDF de 2–4 páginas |
| [DECISOES](DECISOES.md) | Contrato detalhado vigente: decisões D1–D16, regras, payloads, erros e limites | Implementação/integração e explicação dos contratos |
| [README da API](../baas-pme-api/README.md) | Guia único de instalação, execução, camadas e comandos de validação | Subir o serviço, executar testes e localizar código |
| [COBERTURA](COBERTURA.md) | Matriz de features/erros/testes, resultados medidos e lacunas da revisão | Sustentar afirmações de qualidade com evidência |
| [BENCHMARK](BENCHMARK.md) | Método, ambiente, resultados e limites da medição local de concorrência | Citar desempenho sem prometer capacidade/SLO |
| [ALERTAS](ALERTAS.md) | Exemplos de regras operacionais, ainda sem stack coletor instalado | Planejar observabilidade produtiva, não provar alertas enviados |
| [PLANO_DE_EXECUCAO](PLANO_DE_EXECUCAO.md) | Histórico de tarefas, estado de entrega e backlog 9.5 | Saber o que está concluído, parcial ou futuro |
| [CHECKPOINT_T3_1](CHECKPOINT_T3_1.md) | Registro histórico da evolução, não especificação vigente | Entender marcos anteriores sem reutilizar contagens antigas |
| [COMO_INICIAR](COMO_INICIAR.md) e guia de organização | Links de compatibilidade para o README único | Encontrar o guia atual a partir de caminhos antigos |
| [Arquivo histórico](arquivo/) | Conteúdo anterior dos guias consolidados, preservado integralmente | Consulta histórica, não operação ou contrato atual |

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
   `ALERTAS.md` somente como proposta de monitoramento.
6. Renderize o DER e revise o PDF: número de páginas e legibilidade não são
   provados pelos testes estáticos de Markdown. Preserve todos os fluxos,
   resumindo-os e remetendo detalhes de contrato às fontes acima.

As contagens atuais ficam em COBERTURA, não repetidas em cada guia. Os marcos
antigos de 143/155 testes e benchmarks anteriores permanecem identificados
como históricos. Não usar “100% seguro” como conclusão, mesmo após fechar
backlog. Garantias de imutabilidade, formato de erro, gateway e entrega externa
devem respeitar mecanismo, teste e fronteira realmente demonstrados.
