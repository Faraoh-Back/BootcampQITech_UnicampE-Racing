-- Upgrade pontual: não reescreve dinheiro, lastro nem respostas idempotentes.
-- Executar com psql -v ON_ERROR_STOP=1. Bancos novos usam database.sql.
BEGIN;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '10s';

SELECT 'credit_advance' AS scope, count(*) AS legacy_non_positive
FROM credit_advance WHERE net_amount <= 0
UNION ALL
SELECT 'quote_credit_advance', count(*)
FROM quote WHERE operation = 'CREDIT_ADVANCE' AND net_amount <= 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'credit_advance'::regclass
          AND conname = 'chk_credit_advance_positive_net'
    ) THEN
        ALTER TABLE credit_advance ADD CONSTRAINT chk_credit_advance_positive_net
            CHECK (net_amount > 0) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'quote'::regclass
          AND conname = 'chk_quote_credit_advance_positive_net'
    ) THEN
        ALTER TABLE quote ADD CONSTRAINT chk_quote_credit_advance_positive_net
            CHECK (operation <> 'CREDIT_ADVANCE' OR net_amount > 0) NOT VALID;
    END IF;

    -- NOT VALID protege INSERT/UPDATE imediatamente, sem apagar o legado.
    IF NOT EXISTS (SELECT 1 FROM credit_advance WHERE net_amount <= 0) THEN
        ALTER TABLE credit_advance VALIDATE CONSTRAINT chk_credit_advance_positive_net;
    ELSE
        RAISE NOTICE 'Antecipações antigas não positivas preservadas; constraint NOT VALID protege novas gravações. Reconciliação depende de decisão explícita.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM quote WHERE operation = 'CREDIT_ADVANCE' AND net_amount <= 0) THEN
        ALTER TABLE quote VALIDATE CONSTRAINT chk_quote_credit_advance_positive_net;
    ELSE
        RAISE NOTICE 'Cotações antigas não positivas preservadas; constraint NOT VALID protege novas gravações.';
    END IF;
END;
$$;
COMMIT;
