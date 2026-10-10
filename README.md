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

`bootcamp-biblioteca-api/` é o projeto-base de outro exercício do Bootcamp; ele
não faz parte do deploy, dos testes ou do contrato do BaaS PME.
