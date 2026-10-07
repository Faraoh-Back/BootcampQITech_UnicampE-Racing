# Cobertura de Testes e Erros por Rota

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