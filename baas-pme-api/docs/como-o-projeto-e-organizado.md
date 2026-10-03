# Como o BaaS PME é organizado

O caminho de uma requisição do produto é sempre:

```text
HTTP -> middleware -> resource -> controller -> repository -> PostgreSQL
```

Por exemplo, `POST /account/{account_key}/transaction` valida o JSON e os
headers no *resource*, decide as regras de saldo, tarifa e idempotência no
*controller*, e usa o *repository* para obter as travas no banco. O DTO monta
o JSON de resposta. Nenhum teste de integração importa `src`: ele conversa com
a aplicação pela rede.

## Onde alterar cada coisa

| Mudança | Arquivos principais |
|---|---|
| Contrato HTTP de entrada | `src/schemas/` e `src/resources/` |
| Regra de negócio | `src/controllers/` |
| Consulta, ordenação ou lock | `src/repositories/` |
| Tabela, coluna ou restrição | `database/database.sql` e `src/models/` |
| JSON de saída | `src/dtos/` |
| Erro de domínio | `src/errors/custom_errors.py`, `docs/DECISOES.md` e testes HTTP |
| Rota nova | resource correspondente e `src/app.py` |

Os contratos de produto não ficam apenas neste guia: a RFC descreve o desenho
e fluxos, e `DECISOES.md` mantém a especificação de payloads e erros.

## Banco e reconstrução

O DDL é executado somente quando o volume PostgreSQL nasce. Além disso,
`database.sql` é copiado para dentro da imagem no build. Portanto, após mudar
o SQL, recrie volume **e** imagem:

```bash
docker compose down -v && docker compose up -d --build
```

Isso descarta os dados locais. Para mudanças apenas em `src/`, o volume montado
e o `--reload` da API bastam.

## Concorrência e idempotência

Saldo e status são modificados com `FOR NO KEY UPDATE`; transferências travam
as duas contas por `id`, em ordem determinística. Antecipação trava os boletos
por `id`. A reserva de `Idempotency-Key` usa uma restrição `UNIQUE` no banco e
guarda a resposta confirmada para replay.

Os testes de `tests/integration/transaction/` cobrem saques simultâneos,
transferências cruzadas, reuso paralelo de chave idempotente, antecipações
concorrentes e disputa pelo último saldo.

## Legado do projeto-base

Arquivos e rotas `sample_entity` permanecem por compatibilidade com o template
do Bootcamp. Eles não compõem a API BaaS PME, sua RFC nem suas integrações.
