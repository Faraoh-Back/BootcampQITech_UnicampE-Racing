import pytest
import requests
from os import environ
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.request_generator import RequestGenerator
from tests.utils.mock_server import expect_bankslip_ok 

def test_pme_full_journey(make_account):
    # ------------------------------------------------------------------
    # 0. RESET DO MOCKSERVER (Requisito T5.1)
    # ------------------------------------------------------------------
    mock_host = environ.get("MOCKSERVER_HOST", "localhost")
    mock_port = environ.get("MOCKSERVER_PORT", "1080")
    reset_res = requests.put(f"http://{mock_host}:{mock_port}/mockserver/reset")
    assert reset_res.status_code == 200, "Falha ao resetar MockServer no início do teste"

    # ------------------------------------------------------------------
    # 1 e 2. CRIAR CLIENTE E CRIAR CONTA
    # ------------------------------------------------------------------
    # Usando a fixture de apoio
    account_info = make_account()
    assert account_info["status"] in (200, 201), "Falha na criação da conta"
    
    account_key = account_info["response"]["account_key"]
    
    # ------------------------------------------------------------------
    # 3. DEPOSITAR (Aporte inicial de R$ 10.000,00 -> 1.000.000 centavos)
    # ------------------------------------------------------------------
    deposit_payload = PayloadGenerator.create_transaction_payload(
        amount=1000000,  # Inteiro em centavos
        transaction_type="DEPOSIT"
    )
    status, res_deposit = RequestGenerator.POST_transaction(account_key, deposit_payload)
    assert status in (200, 201), f"Erro no depósito: {res_deposit}"
    print(f"[OK] Depósito de R$ 10.000,00 realizado.")
    # ------------------------------------------------------------------
    # 4. EMITIR PLANO DE BOLETOS
    # ------------------------------------------------------------------
    # Configura a expectativa de sucesso para emissão de boletos no MockServer
    expect_bankslip_ok()

    billing_plan_payload = PayloadGenerator.create_billing_plan_payload(
        base_amount=500000  # R$ 5.000,00 em centavos
    )
    status, res_plan = RequestGenerator.POST_billing_plan(account_key, billing_plan_payload)
    assert status in (200, 201), f"Erro na emissão do plano: {res_plan}"
    print(f"[OK] Plano de boletos emitido com sucesso.")

    # ------------------------------------------------------------------
    # 5. ANTECIPAR CRÉDITO
    # ------------------------------------------------------------------
    # Extrai as chaves dos boletos gerados pelo plano
    bank_slips = res_plan.get("bank_slips", [])
    bank_slip_keys = [
        bs.get("bank_slip_key") or bs.get("key") for bs in bank_slips
    ]

    advance_payload = PayloadGenerator.create_credit_advance_payload(
        bank_slip_keys=bank_slip_keys
    )
    status, res_advance = RequestGenerator.POST_credit_advance(account_key, advance_payload)
    assert status in (200, 201), f"Erro na antecipação: {res_advance}"
    print("[OK] Antecipação realizada com sucesso.")

    # ------------------------------------------------------------------
    # 6. CONSULTAR EXTRATO PAGINADO
    # ------------------------------------------------------------------
    # Usa page="0" para acessar a primeira página do extrato
    status, res_transactions = RequestGenerator.GET_transactions(
        account_key,
        params={"page": "0", "limit": "50"}
    )
    assert status == 200, f"Erro ao buscar extrato: {res_transactions}"
    print("[OK] Extrato consultado com sucesso.")

    # ------------------------------------------------------------------
    # 7. CONFERIR SOMA DO EXTRATO CONTRA O SALDO DA CONTA
    # ------------------------------------------------------------------
    transactions_list = res_transactions.get("data", [])
    assert len(transactions_list) > 0, "Lista de transações não deveria estar vazia"

    # Busca o saldo atualizado da conta
    status, res_account = RequestGenerator.GET_account(account_key)
    assert status == 200
    current_balance = res_account["balance"]

    # Tipos de transação que somam ao saldo (créditos)
    credit_types = {"DEPOSIT", "ADVANCE_CREDIT", "TRANSFER_IN"}

    # Calcula o somatório considerando créditos (+) e débitos (-)
    total_calculated = sum(
        t["amount"] if t.get("type") in credit_types or t.get("entry_type") == "credit" else -abs(t["amount"])
        for t in transactions_list
    )

    assert total_calculated == current_balance, f"Saldo divergente: calculado {total_calculated} vs conta {current_balance}"
    print("[OK] Soma do extrato confere com o saldo atual da conta.")