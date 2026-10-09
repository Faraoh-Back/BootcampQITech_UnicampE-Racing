-- ==========================================
-- DOMÍNIOS / ENUMERADORES
-- ==========================================
CREATE TABLE sample_entity_status(
    id		                        SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO sample_entity_status (enumerator) VALUES
('created'),
('pending'),
('success'),
('failed');

CREATE TABLE sample_entity(
    id                              SERIAL PRIMARY KEY,
    sample_entity_key               CHAR(36) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    sample_entity_data              JSONB NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    birthdate                       DATE NOT NULL,
    counter                         INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(sample_entity_key),
    UNIQUE(document_number),
    UNIQUE(email)
);

CREATE TABLE sample_entity_status_event(
    id                              SERIAL PRIMARY KEY,
    sample_entity_id                INTEGER NOT NULL REFERENCES sample_entity(id),
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE account_status (
    id          SERIAL PRIMARY KEY,
    enumerator  VARCHAR(50) NOT NULL UNIQUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO account_status (enumerator) VALUES
('PENDING'),
('APPROVED'),
('BLOCKED'),
('CANCELLED');

CREATE TABLE bank_slip_status (
    id          SERIAL PRIMARY KEY,
    enumerator  VARCHAR(50) NOT NULL UNIQUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO bank_slip_status (enumerator) VALUES
('PENDING'),
('PAID'),
('CANCELLED');

-- ==========================================
-- CORE DOMAIN
-- ==========================================
CREATE TABLE customer (
    id              SERIAL PRIMARY KEY,
    customer_key    CHAR(36) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    document_number VARCHAR(18) NOT NULL UNIQUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE app_user (
    id              SERIAL PRIMARY KEY,
    user_key        CHAR(36) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(100) NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE user_customer_access (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES app_user(id),
    customer_id     INTEGER NOT NULL REFERENCES customer(id),
    role            VARCHAR(20) NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unq_user_customer_access UNIQUE (user_id, customer_id),
    CONSTRAINT chk_user_customer_role CHECK (role IN ('OWNER', 'OPERATOR', 'VIEWER'))
);

CREATE TABLE user_session (
    id                  SERIAL PRIMARY KEY,
    session_key         CHAR(36) NOT NULL UNIQUE,
    user_id             INTEGER NOT NULL REFERENCES app_user(id),
    refresh_token_hash  CHAR(64) NOT NULL UNIQUE,
    device_name         VARCHAR(100),
    expires_at          TIMESTAMP NOT NULL,
    revoked_at          TIMESTAMP,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- A auditoria é uma cadeia append-only. Não há FK de ator de propósito:
-- eventos de serviço e usuários futuros precisam continuar verificáveis mesmo
-- se dados pessoais forem anonimizados em outra política.
CREATE TABLE audit_event (
    id               SERIAL PRIMARY KEY,
    actor_type       VARCHAR(20) NOT NULL,
    actor_key        VARCHAR(64) NOT NULL,
    action           VARCHAR(64) NOT NULL,
    resource_type    VARCHAR(64) NOT NULL,
    resource_key     CHAR(36) NOT NULL,
    request_id       VARCHAR(64) NOT NULL,
    origin           VARCHAR(255) NOT NULL,
    previous_summary JSONB,
    current_summary  JSONB,
    previous_hash    CHAR(64) NOT NULL,
    event_hash       CHAR(64) NOT NULL UNIQUE,
    event_datetime   TIMESTAMP NOT NULL,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_audit_actor_type CHECK (actor_type IN ('SERVICE', 'USER')),
    CONSTRAINT chk_audit_previous_hash CHECK (previous_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_audit_event_hash CHECK (event_hash ~ '^[0-9a-f]{64}$')
);

CREATE INDEX idx_audit_event_resource ON audit_event(resource_type, resource_key, id);

CREATE OR REPLACE FUNCTION reject_audit_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_event is append-only; use a compensating event';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_event_append_only
BEFORE UPDATE OR DELETE ON audit_event
FOR EACH ROW EXECUTE FUNCTION reject_audit_event_mutation();

CREATE TABLE account (
    id          SERIAL PRIMARY KEY,
    account_key CHAR(36) NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customer(id),
    status_id   INTEGER NOT NULL REFERENCES account_status(id),
    balance     BIGINT NOT NULL DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_account_balance_non_negative CHECK (balance >= 0)
);

CREATE TABLE account_status_event (
    id             SERIAL PRIMARY KEY,
    account_id     INTEGER NOT NULL REFERENCES account(id),
    status_id      INTEGER NOT NULL REFERENCES account_status(id),
    event_datetime TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE idempotency_key (
    id              SERIAL PRIMARY KEY,
    account_id      INTEGER NOT NULL REFERENCES account(id),
    idempotency_key VARCHAR(64) NOT NULL,
    scope           VARCHAR(40) NOT NULL,
    request_hash    CHAR(64) NOT NULL,
    response_status INTEGER,
    response_body   JSONB,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT unq_idempotency_account_scope_key UNIQUE (account_id, scope, idempotency_key)
);

CREATE TABLE transaction (
    id                      SERIAL PRIMARY KEY,
    transaction_key         CHAR(36) NOT NULL UNIQUE,
    operation_key           CHAR(36) NOT NULL,
    account_id              INTEGER NOT NULL REFERENCES account(id),
    counterparty_account_id INTEGER REFERENCES account(id),
    type                    VARCHAR(20) NOT NULL,
    amount                  BIGINT NOT NULL,
    balance_after           BIGINT NOT NULL,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_transaction_amount_not_zero CHECK (amount <> 0),
    CONSTRAINT chk_transaction_type CHECK (type IN (
        'DEPOSIT', 'WITHDRAWAL', 'TRANSFER_OUT', 'TRANSFER_IN', 
        'TRANSFER_FEE', 'ADVANCE_CREDIT', 'ADVANCE_FEE'
    ))
);

CREATE INDEX idx_transaction_account_created_id ON transaction (account_id, created_at DESC, id DESC);

CREATE TABLE credit_advance (
    id                 SERIAL PRIMARY KEY,
    credit_advance_key CHAR(36) NOT NULL UNIQUE,
    account_id         INTEGER NOT NULL REFERENCES account(id),
    gross_amount       BIGINT NOT NULL,
    fee_amount         BIGINT NOT NULL,
    net_amount         BIGINT NOT NULL,
    created_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_credit_advance_net_amount CHECK (net_amount = gross_amount - fee_amount)
);

CREATE TABLE billing_plan (
    id               SERIAL PRIMARY KEY,
    plan_key         CHAR(36) NOT NULL UNIQUE,
    account_id       INTEGER NOT NULL REFERENCES account(id),
    base_amount      BIGINT NOT NULL,
    first_due_date   DATE NOT NULL,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE bank_slip (
    id                 SERIAL PRIMARY KEY,
    slip_key           CHAR(36) NOT NULL UNIQUE,
    billing_plan_id    INTEGER NOT NULL REFERENCES billing_plan(id),
    credit_advance_id  INTEGER REFERENCES credit_advance(id),
    status_id          INTEGER NOT NULL REFERENCES bank_slip_status(id),
    installment_number INTEGER NOT NULL,
    batch_number       INTEGER NOT NULL DEFAULT 1,
    adjustment_rate    NUMERIC(12,8),
    amount             BIGINT NOT NULL,
    due_date           DATE NOT NULL,
    barcode            VARCHAR(60),
    created_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_bank_slip_amount_not_zero CHECK (amount <> 0),
    CONSTRAINT unq_bank_slip_plan_installment UNIQUE (billing_plan_id, installment_number)
);

CREATE TABLE bank_slip_status_event (
    id             SERIAL PRIMARY KEY,
    bank_slip_id   INTEGER NOT NULL REFERENCES bank_slip(id),
    status_id      INTEGER NOT NULL REFERENCES bank_slip_status(id),
    event_datetime TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);
