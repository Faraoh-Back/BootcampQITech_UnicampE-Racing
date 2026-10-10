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
[registro de entrega](docs/entrega/ENTREGA.md). Publicação/CI foram confirmados
para `1603118`; novas revisões precisam de novo CI. Revisão do time, ensaio e
clone remoto independente continuam sob responsabilidade do grupo.

A apresentação do produto é baseada em **garantias verificadas e limitações
conhecidas**, não em segurança absoluta. Antecipação/cotação CREDIT_ADVANCE
exigem líquido positivo, com `422 QIT001030`, CHECKs e testes HTTP/SQL;
as demais fronteiras de P0.4 do plano permanecem pendentes.
Regra, exemplos e limites estão em
[DECISOES §3.5.1](docs/DECISOES.md#351-líquido-positivo-regra-implementada-e-validada).
Para o resultado mais recente, use [COBERTURA](docs/COBERTURA.md); para recursos
medidos, [BENCHMARK §14](docs/BENCHMARK.md#14-t510-bootstrap-determinístico-e-modo-externo).

Com Docker disponível e dependências na `.venv`, `cd baas-pme-api` e
`./.venv/bin/python -m pytest -q` preparam automaticamente API/banco/mock
descartáveis, portas livres e relógios de teste: não depende da hora do avaliador
nem usa o banco de desenvolvimento. Método/limites no
[README da API](baas-pme-api/README.md#relógio-determinístico-e-isolamento-automático).

`bootcamp-biblioteca-api/` é o projeto-base de outro exercício do Bootcamp; ele
não faz parte do deploy, dos testes ou do contrato do BaaS PME.
