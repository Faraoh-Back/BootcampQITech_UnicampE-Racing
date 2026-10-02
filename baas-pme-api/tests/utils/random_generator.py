import random
from uuid import uuid4


class RandomGenerator:
    @staticmethod
    def generate_cpf(masked: bool = True) -> str:
        """Gera um CPF matematicamente valido, com ou sem mascara."""
        all_digits_are_equal = True
        while all_digits_are_equal:
            digits = [random.randrange(10) for _ in range(9)]
            if any(d != digits[0] for d in digits):
                all_digits_are_equal = False

        for position in [9, 10]:
            total = sum(digits[i] * (position + 1 - i) for i in range(position))
            remainder = total % 11
            digits.append(0 if remainder < 2 else 11 - remainder)

        cpf_str = "".join(str(d) for d in digits)
        if masked:
            return f"{cpf_str[0:3]}.{cpf_str[3:6]}.{cpf_str[6:9]}-{cpf_str[9:11]}"
        return cpf_str

    @staticmethod
    def generate_invalid_cpf(masked: bool = True) -> str:
        """Gera um CPF com digitos verificadores intencionalmente invalidos (para testar QIT001010)."""
        valid_cpf = RandomGenerator.generate_cpf(masked=False)
        # Inverte o ultimo digito para invalidar
        last_digit = str((int(valid_cpf[-1]) + 1) % 10)
        invalid_str = valid_cpf[:-1] + last_digit
        if masked:
            return f"{invalid_str[0:3]}.{invalid_str[3:6]}.{invalid_str[6:9]}-{invalid_str[9:11]}"
        return invalid_str

    @staticmethod
    def generate_cnpj(masked: bool = True) -> str:
        """Gera um CNPJ matematicamente valido, com ou sem mascara."""
        cnpj = [random.randrange(10) for _ in range(8)] + [0, 0, 0, 1]

        for _ in range(2):
            value = sum(v * (i % 8 + 2) for i, v in enumerate(reversed(cnpj)))
            digit = 11 - (value % 11)
            cnpj.append(digit if digit < 10 else 0)

        cnpj_str = "".join(str(x) for x in cnpj)
        if masked:
            return f"{cnpj_str[0:2]}.{cnpj_str[2:5]}.{cnpj_str[5:8]}/{cnpj_str[8:12]}-{cnpj_str[12:14]}"
        return cnpj_str

    @staticmethod
    def generate_invalid_cnpj(masked: bool = True) -> str:
        """Gera um CNPJ com digitos verificadores invalidos."""
        valid_cnpj = RandomGenerator.generate_cnpj(masked=False)
        last_digit = str((int(valid_cnpj[-1]) + 1) % 10)
        invalid_str = valid_cnpj[:-1] + last_digit
        if masked:
            return f"{invalid_str[0:2]}.{invalid_str[2:5]}.{invalid_str[5:8]}/{invalid_str[8:12]}-{invalid_str[12:14]}"
        return invalid_str

    @staticmethod
    def generate_email(prefix: str = "pme") -> str:
        """Gera um e-mail unico para evitar colisao de UNIQUE entre testes."""
        return f"{prefix}.{uuid4().hex[:10]}@exemplo.com.br"

    @staticmethod
    def generate_name(prefix: str = "PME") -> str:
        """Gera um nome empresarial unico."""
        return f"{prefix} Serviços {uuid4().hex[:6].upper()} Ltda"
