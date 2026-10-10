# Defesa técnica — roteiro e registro de ensaio

Material de apoio à T5.7; não é evidência de que alguém já ensaiou. Frase-guia:
**garantias verificadas e limitações conhecidas**. A regra de líquido positivo
está aprovada, **não implementada** (P0.4); toda a seção 9.5 foi excluída pelo
solicitante desta rodada. Não apresentar seus itens como resolvidos.

## 1. Roteiro de 10 minutos

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

## 2. Perguntas e respostas sustentáveis

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
ledger é a história assinada; account.balance é saldo materializado, protegido
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
líquido >0 mesmo com R$500 anteriores, mas não foi implementada; é P0.4.
Uma política fixa de R$120 pode ser válida para bruto R$1.000: a validação deve
ser por operação. Não demonstrar a recusa como feature entregue.

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
registrado. Esta rodada comprovou Red de quatro contratos de entrega antes
dos artefatos. Suíte verde não permite afirmar TDD retrospectivo das features.

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

## 3. Registro de ensaio — preencher após realizar

| Integrante | Data | Roteiro completo sem código? | Perguntas respondidas? | Dúvidas / ação |
|---|---|---|---|---|
| Cairê Belo | A preencher | Não comprovado | Não comprovado | A preencher |
| Pedro Campanha | A preencher | Não comprovado | Não comprovado | A preencher |

Conclusão de T5.7 depende deste registro humano; gerar o roteiro não conclui
o ensaio. Separar resposta errada de limite real, consultar contrato e repetir
a rodada de perguntas antes da apresentação.
