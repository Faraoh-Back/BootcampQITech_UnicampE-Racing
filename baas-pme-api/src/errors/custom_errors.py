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


class ProductNotEnabled(QIException):
    code = "QIT001026"

    def __init__(self, product: str) -> None:
        super().__init__(
            "Product not enabled", self.code, 409,
            f"The {product} product is not enabled for this customer.",
            "Este produto não está habilitado para esta PME.",
        )


class RiskLimitExceeded(QIException):
    code = "QIT001027"

    def __init__(self, limit_name: str) -> None:
        super().__init__(
            "Risk limit exceeded", self.code, 422,
            f"The requested operation exceeds the configured {limit_name}.",
            "A operação excede o limite de risco configurado.",
        )


class InsufficientBalance(QIException):
    """O débito solicitado não cabe no saldo disponível da conta."""

    code = "QIT001005"

    def __init__(self, account_key: str) -> None:
        title = "Insufficient balance"
        http_status = 422
        description = f"Account with key {account_key} does not have enough balance for this operation."
        translation = "A conta não possui saldo suficiente para esta operação."
        super().__init__(title, self.code, http_status, description, translation)


class NightLimitExceeded(QIException):
    """O valor excede o teto por operação dentro da janela noturna."""

    code = "QIT001007"

    def __init__(self) -> None:
        title = "Night limit exceeded"
        http_status = 422
        description = "The requested amount exceeds the limit for the night transfer window."
        translation = "O valor solicitado excede o limite permitido para o horário noturno."
        super().__init__(title, self.code, http_status, description, translation)


class SameAccountTransfer(QIException):
    """A transferência deve sempre envolver duas contas distintas."""

    code = "QIT001012"

    def __init__(self) -> None:
        title = "Same account transfer"
        http_status = 422
        description = "The destination account must be different from the origin account."
        translation = "A conta de destino deve ser diferente da conta de origem."
        super().__init__(title, self.code, http_status, description, translation)


class TransactionNotFound(QIException):
    """Não revela se a chave pertence a uma conta diferente (R8)."""

    code = "QIT001011"

    def __init__(self) -> None:
        title = "Transaction not found"
        http_status = 404
        description = "The transaction was not found for this account."
        translation = "O lançamento não foi encontrado para esta conta."
        super().__init__(title, self.code, http_status, description, translation)


class BillingPlanNotFound(QIException):
    code = "QIT001013"

    def __init__(self, plan_key: str) -> None:
        title = "Billing plan not found"
        http_status = 404
        description = f"Billing plan with key {plan_key} was not found for this account."
        translation = "O plano de cobrança não foi encontrado para esta conta."
        super().__init__(title, self.code, http_status, description, translation)


class AdjustmentAlreadyApplied(QIException):
    """Cada plano pode ter apenas um lote reajustado de boletos."""

    code = "QIT001014"

    def __init__(self) -> None:
        title = "Adjustment already applied"
        http_status = 409
        description = "The adjusted second batch was already issued for this billing plan."
        translation = "O lote reajustado de boletos já foi emitido para este plano de cobrança."
        super().__init__(title, self.code, http_status, description, translation)


class BankSlipNotFound(QIException):
    """Não revela qual boleto é inexistente ou pertence a outra conta."""

    code = "QIT001015"

    def __init__(self) -> None:
        title = "Bank slip not found"
        http_status = 404
        description = "One or more bank slips were not found for this account."
        translation = "Um ou mais boletos não foram encontrados para esta conta."
        super().__init__(title, self.code, http_status, description, translation)


class BankSlipNotEligible(QIException):
    """Um recebível já antecipado não pode gerar saldo novamente."""

    code = "QIT001016"

    def __init__(self) -> None:
        title = "Bank slip not eligible"
        http_status = 409
        description = "One or more bank slips are not eligible for credit advance."
        translation = "Um ou mais boletos não são elegíveis para antecipação."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidFirstDueDate(QIException):
    code = "QIT001017"

    def __init__(self, first_due_date: str) -> None:
        title = "Invalid first due date"
        http_status = 422
        description = f"The first due date {first_due_date} cannot be in the past."
        translation = "O primeiro vencimento não pode estar no passado."
        super().__init__(title, self.code, http_status, description, translation)


class IdempotencyConflict(QIException):
    """A chave foi reutilizada dentro do mesmo escopo, mas para outro pedido."""

    code = "QIT001008"

    def __init__(self) -> None:
        title = "Idempotency key conflict"
        http_status = 409
        description = "The Idempotency-Key was already used with a different request."
        translation = "A Idempotency-Key já foi usada com uma requisição diferente."
        super().__init__(title, self.code, http_status, description, translation)


class MissingIdempotencyKey(QIException):
    code = "QIT001018"

    def __init__(self) -> None:
        title = "Missing Idempotency-Key"
        http_status = 400
        description = "The Idempotency-Key header is required for this operation."
        translation = "O cabeçalho Idempotency-Key é obrigatório para esta operação."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidAccountStatusTransition(QIException):
    """A máquina de estados não permite a transição solicitada."""

    code = "QIT001019"

    def __init__(self, current_status: str, requested_status: str) -> None:
        title = "Invalid account status transition"
        http_status = 409
        description = (
            f"Account status cannot transition from {current_status} to {requested_status}."
        )
        translation = "A transição de status solicitada para a conta não é permitida."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidAccessToken(QIException):
    code = "QIT001020"

    def __init__(self) -> None:
        super().__init__(
            "Invalid access token",
            self.code,
            401,
            "The access token is invalid, expired or its session was revoked.",
            "O token de acesso é inválido, expirou ou sua sessão foi revogada.",
        )


class InvalidCredentials(QIException):
    code = "QIT001021"

    def __init__(self) -> None:
        super().__init__(
            "Invalid credentials",
            self.code,
            401,
            "The email or password is invalid.",
            "O e-mail ou a senha são inválidos.",
        )


class AccountAccessForbidden(QIException):
    code = "QIT001022"

    def __init__(self) -> None:
        super().__init__(
            "Account access forbidden",
            self.code,
            403,
            "The authenticated user does not have the required role for this account.",
            "O usuário autenticado não possui a permissão necessária para esta conta.",
        )


class DuplicatedUserEmail(QIException):
    code = "QIT001023"

    def __init__(self) -> None:
        super().__init__(
            "User email already registered",
            self.code,
            409,
            "There is already a user registered with this email.",
            "Já existe um usuário cadastrado com este e-mail.",
        )


class DatabaseOperationTimeout(QIException):
    """PostgreSQL cancelou lock ou statement antes de consumir workers."""

    code = "QIT001024"

    def __init__(self) -> None:
        super().__init__(
            "Database operation timed out",
            self.code,
            503,
            "The database exceeded its configured lock or statement timeout.",
            "A operação excedeu o tempo de espera configurado no banco. Tente novamente.",
        )


class DatabaseTransientFailure(QIException):
    """Falha transitória esgotou as tentativas seguras da operação."""

    code = "QIT001025"

    def __init__(self) -> None:
        super().__init__(
            "Transient database operation failed",
            self.code,
            503,
            "The database could not complete the operation after safe transient retries.",
            "O banco não concluiu a operação após retentativas seguras. Tente novamente com a mesma Idempotency-Key.",
        )


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
