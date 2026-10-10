# BaaS PME — Bootcamp QI Tech 2026

Este repositório entrega o desafio **BaaS PME**: uma API para cadastro de
clientes, contas, transações, boletos, reajustes e antecipação de recebíveis.
O produto e seus contratos estão em [docs/RFC.md](docs/RFC.md) e
[docs/DECISOES.md](docs/DECISOES.md).

O plano de cobrança cria recebíveis que a própria PME cobrará de seus
pagadores; a antecipação usa somente esses boletos pendentes como lastro para
dar liquidez à PME. Não há produto de empréstimo ou baixa automática de boleto
neste escopo.

O serviço ativo está em [`baas-pme-api/`](baas-pme-api/). Entre nessa pasta e
siga o [README da API](baas-pme-api/README.md) para subir e testar o projeto.

O [índice da documentação](docs/README.md) separa contratos, evidências de
testes/benchmark, histórico e pendências da entrega.

Artefatos para a banca: [RFC em PDF — quatro páginas](docs/entrega/RFC_FINAL.pdf)
e [apresentação — dez slides](docs/entrega/APRESENTACAO.pdf). Fontes editáveis,
roteiro de defesa, geração e validação isolada estão no
[registro de entrega](docs/entrega/ENTREGA.md). Revisão do time, ensaio,
clone remoto independente e publicação precisam de confirmação humana.

A apresentação do produto é baseada em **garantias verificadas e limitações
conhecidas**, não em segurança absoluta. A regra aprovada de líquido positivo
na antecipação está documentada, com implementação pendente P0.4 do plano.

`bootcamp-biblioteca-api/` é o projeto-base de outro exercício do Bootcamp; ele
não faz parte do deploy, dos testes ou do contrato do BaaS PME.
