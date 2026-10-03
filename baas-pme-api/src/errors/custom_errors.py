from errors import QIException


class ExternalConnectorError(QIException):
    """Falha ao consultar um serviço externo indispensável ao fluxo."""

    code = "QIT001009"

    def __init__(self, service_name: str) -> None:
        title = "External service unavailable"
        http_status = 502
        description = f"The external service {service_name} returned an invalid response or is unavailable."
        translation = "O serviço externo está indisponível ou retornou uma resposta inválida."
        super().__init__(title, self.code, http_status, description, translation)


class CustomerNotFound(QIException):
    code = "QIT001001"

    def __init__(self, customer_key: str) -> None:
        title = "Customer not Found"
        http_status = 404
        description = f"Customer with key {customer_key} was not found."
        translation = f"O cliente com chave {customer_key} não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotFound(QIException):
    code = "QIT001002"

    def __init__(self, account_key: str) -> None:
        title = "Account not Found"
        http_status = 404
        description = f"Account with key {account_key} was not found."
        translation = f"A conta com chave {account_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotApproved(QIException):
    """A operação financeira só é permitida para contas aprovadas."""

    code = "QIT001006"

    def __init__(self, account_key: str) -> None:
        title = "Account not approved"
        http_status = 409
        description = f"Account with key {account_key} is not approved for this operation."
        translation = "A conta não está aprovada para esta operação."
        super().__init__(title, self.code, http_status, description, translation)


class BillingPlanNotFound(QIException):
    code = "QIT001013"

    def __init__(self, plan_key: str) -> None:
        title = "Billing plan not found"
        http_status = 404
        description = f"Billing plan with key {plan_key} was not found for this account."
        translation = "O plano de cobrança não foi encontrado para esta conta."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidFirstDueDate(QIException):
    code = "QIT001017"

    def __init__(self, first_due_date: str) -> None:
        title = "Invalid first due date"
        http_status = 422
        description = f"The first due date {first_due_date} cannot be in the past."
        translation = "O primeiro vencimento não pode estar no passado."
        super().__init__(title, self.code, http_status, description, translation)


class NotFoundSampleEntity(QIException):
    """Erro legado do recurso de exemplo, fora do catálogo BaaS PME."""

    code = "QIT002001"

    def __init__(self, sample_entity_key: str) -> None:
        title = "Entity not Found"
        http_status = 404
        description = f"Entity with key {sample_entity_key} was not found."
        translation = f"A entidade com chave {sample_entity_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class SampleEntityFinalStatus(QIException):
    code = "QIT002002"

    def __init__(self, old_status, new_status) -> None:
        title = "Entity cannot change status"
        http_status = 409
        description = f"Entity with status {old_status} cannot update to {new_status}."
        translation = "Essa entidade não pode ser atualizada."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumentNumber(QIException):
    """O CPF tem o formato certo e não existe.

    422, e não 400, de propósito: 400 quer dizer "não consegui ler o seu
    pedido". Aqui a API leu, entendeu, e o valor é que não pode existir —
    os dois últimos dígitos não batem com a conta. A diferença está
    explicada em src/utils/document_number.py.
    """

    code = "QIT001010"

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF or CNPJ."
        translation = "O CPF ou CNPJ informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):
    """Já existe um cadastro com este CPF.

    409 Conflict: o pedido está correto em si, e o que impede é o que já
    está no banco. É a mesma família do SampleEntityFinalStatus aqui em
    cima — conflito com o que já existe, não erro de quem pediu.
    """

    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = f"There is already an entity with the document number {document_number}."
        translation = "Já existe um cadastro com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedEmail(QIException):
    code = "QIT001004"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already an entity with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class UnderageSampleEntity(QIException):
    code = "QIT002003"

    def __init__(self, age, minimum_age) -> None:
        title = "Entity is underage"
        http_status = 422
        description = f"The entity is {age} years old, and the minimum is {minimum_age}."
        translation = f"É preciso ter pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBirthdate(QIException):
    """A data tem o formato certo e não existe no calendário.

    Existe porque o `pattern` do schema sabe contar dígitos, não dias:
    "2025-02-30" e "9999-99-99" passam pelo regex e morrem no
    `date.fromisoformat`. Sem esta classe, esse ValueError virava 500 —
    a API culpando a si mesma por um erro de quem chamou.
    """

    code = "QIT002004"

    def __init__(self, birthdate) -> None:
        title = "Invalid Birthdate"
        http_status = 422
        description = f"The birthdate {birthdate} is not a real date."
        translation = "A data de nascimento informada não existe."
        super().__init__(title, self.code, http_status, description, translation)
