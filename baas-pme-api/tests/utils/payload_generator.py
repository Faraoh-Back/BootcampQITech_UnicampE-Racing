from uuid import uuid4
from datetime import date, timedelta
from typing import List, Optional

from tests.utils.random_generator import RandomGenerator


class PayloadGenerator:
    # ── MÉTODOS LEGADOS / SAMPLE ENTITY ───────────────────────────
    @staticmethod
    def create_sample_entity_payload(
        hello: str = None,
        name: str = None,
        email: str = None,
        document_number: str = None,
        birthdate: str = None,
    ) -> dict:
        if hello is None:
            hello = "world"
        if name is None:
            name = "Maria da Silva"
        if email is None:
            email = f"maria.silva.{uuid4()}@exemplo.com.br"
        if document_number is None:
            document_number = RandomGenerator.generate_cpf()
        if birthdate is None:
            birthdate = "1990-05-17"

        return {
            "hello": hello,
            "name": name,
            "email": email,
            "document_number": document_number,
            "birthdate": birthdate,
        }

    @staticmethod
    def create_new_status_payload(new_status: str = None) -> dict:
        return {"status": new_status}

    # ── NOVOS MÉTODOS / BAAS PME ──────────────────────────────────
    @staticmethod
    def create_customer_payload(
        name: Optional[str] = None,
        email: Optional[str] = None,
        document_number: Optional[str] = None,
        is_cnpj: bool = True,
    ) -> dict:
        """Gera payload valido para cadastro de cliente PME."""
        if name is None:
            name = RandomGenerator.generate_name()
        if email is None:
            email = RandomGenerator.generate_email("cliente")
        if document_number is None:
            document_number = (
                RandomGenerator.generate_cnpj() if is_cnpj else RandomGenerator.generate_cpf()
            )

        return {
            "name": name,
            "email": email,
            "document_number": document_number,
        }

    @staticmethod
    def create_account_payload(customer_key: str) -> dict:
        """Gera payload para abertura de conta."""
        return {
            "customer_key": customer_key,
        }

    @staticmethod
    def create_transaction_payload(
        transaction_type: str = "DEPOSIT",
        amount: int = 50000,
        destination_account_key: Optional[str] = None,
    ) -> dict:
        """Gera payload para movimentações financeiras."""
        payload = {
            "type": transaction_type,
            "amount": amount,
        }
        if destination_account_key:
            payload["destination_account_key"] = destination_account_key
        return payload

    @staticmethod
    def create_billing_plan_payload(
        base_amount: int = 15000,
        first_due_date: Optional[str] = None,
    ) -> dict:
        """Gera payload para contratação de plano de cobrança."""
        if first_due_date is None:
            first_due_date = (date.today() + timedelta(days=30)).isoformat()
        return {
            "base_amount": base_amount,
            "first_due_date": first_due_date,
        }

    @staticmethod
    def create_adjustment_payload(index_code: str = "IPCA") -> dict:
        """Gera payload para reajuste do plano de cobrança."""
        return {
            "index_code": index_code,
        }

    @staticmethod
    def create_credit_advance_payload(bank_slip_keys: List[str]) -> dict:
        """Gera payload para antecipação de boletos."""
        return {
            "bank_slip_keys": bank_slip_keys,
        }
