-- Hand-made bitemporality in plain PostgreSQL, made to behave like XTDB:
--   * `customers` reads and writes like an ordinary table (plain INSERT / UPDATE / DELETE),
--   * every write keeps full history on both time axes,
--   * history itself cannot be rewritten, not even by a direct write to the history table.
-- Everything in this file is code YOU own, per table: write it, test it, review it, keep it right.

CREATE EXTENSION IF NOT EXISTS btree_gist;
DROP VIEW IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS customers_history CASCADE;

-- The clock. `app.now` exists only so the demo can replay January; in production this is now().
CREATE OR REPLACE FUNCTION app_now() RETURNS timestamptz LANGUAGE sql STABLE AS
  $$ SELECT coalesce(nullif(current_setting('app.now', true), '')::timestamptz, now()) $$;

-- Every version of every customer: when it was true (_valid_*) and when we believed it (_system_*).
-- NULL in a *_to column means "until further notice".
CREATE TABLE customers_history (
  _id          bigint      NOT NULL,
  name         text        NOT NULL,
  risk_rating  text        NOT NULL,
  _valid_from  timestamptz NOT NULL,
  _valid_to    timestamptz,
  _system_from timestamptz NOT NULL,
  _system_to   timestamptz,
  -- at most one belief per customer for any (valid instant, system instant)
  EXCLUDE USING gist (_id WITH =,
                      tstzrange(_valid_from, _valid_to) WITH &&,
                      tstzrange(_system_from, _system_to) WITH &&)
);

-- Guard: the history table is append-only. A new belief starts now (and now never goes
-- backwards); the only allowed change is retiring a current belief, now. Nothing else.
CREATE OR REPLACE FUNCTION customers_history_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'INSERT'
     AND NEW._system_from = app_now() AND NEW._system_to IS NULL
     AND NEW._system_from >= coalesce((SELECT max(_system_from) FROM customers_history), '-infinity')
  THEN RETURN NEW;
  ELSIF TG_OP = 'UPDATE'
     AND to_jsonb(NEW) - '_system_to' = to_jsonb(OLD) - '_system_to'
     AND OLD._system_to IS NULL AND NEW._system_to = app_now()
  THEN RETURN NEW;
  END IF;
  RAISE EXCEPTION 'customers_history is append-only: % rejected', TG_OP;
END $$;
CREATE TRIGGER guard BEFORE INSERT OR UPDATE OR DELETE ON customers_history
  FOR EACH ROW EXECUTE FUNCTION customers_history_guard();
CREATE TRIGGER guard_truncate BEFORE TRUNCATE ON customers_history
  FOR EACH STATEMENT EXECUTE FUNCTION customers_history_guard();

-- Time travel: what we believed at `known_at` about `valid_at`.
CREATE OR REPLACE FUNCTION customers_as_of(valid_at timestamptz, known_at timestamptz DEFAULT app_now())
RETURNS TABLE (_id bigint, name text, risk_rating text, _valid_from timestamptz)
LANGUAGE sql STABLE AS $$
  SELECT _id, name, risk_rating, _valid_from FROM customers_history
  WHERE _valid_from  <= valid_at AND (_valid_to  IS NULL OR _valid_to  > valid_at)
    AND _system_from <= known_at AND (_system_to IS NULL OR _system_to > known_at)
$$;

-- What we believe now about now: reads like an ordinary table.
CREATE VIEW customers AS SELECT * FROM customers_as_of(app_now());

-- Writes through the view, from a valid time on (INSERT: its _valid_from, default now;
-- UPDATE / DELETE: now) until further notice, keeping every earlier belief:
--   INSERT asserts the whole row (an upsert, like XTDB), UPDATE patches the changed columns
--   into every version from then on, DELETE retracts.
CREATE OR REPLACE FUNCTION customers_write() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  id  bigint      := CASE TG_OP WHEN 'DELETE' THEN OLD._id ELSE NEW._id END;
  t   timestamptz := CASE TG_OP WHEN 'INSERT' THEN coalesce(NEW._valid_from, app_now()) ELSE app_now() END;
  v   customers_history;
BEGIN
  IF TG_OP = 'UPDATE' AND (NEW._id, NEW._valid_from) IS DISTINCT FROM (OLD._id, OLD._valid_from) THEN
    RAISE EXCEPTION '_id and _valid_from are not updatable: to backdate, INSERT with _valid_from';
  END IF;
  -- 1. retire every current belief about this customer that is valid at or after t ...
  FOR v IN UPDATE customers_history SET _system_to = app_now()
           WHERE _id = id AND _system_to IS NULL AND (_valid_to IS NULL OR _valid_to > t)
           RETURNING *
  LOOP
    -- 2. ... re-assert the part before t unchanged ...
    IF v._valid_from < t THEN
      INSERT INTO customers_history VALUES (v._id, v.name, v.risk_rating, v._valid_from, t, app_now(), NULL);
    END IF;
    -- 3. ... and for UPDATE, the part from t on with the changed columns patched in (per column!)
    IF TG_OP = 'UPDATE' THEN
      INSERT INTO customers_history VALUES (v._id,
        CASE WHEN NEW.name IS DISTINCT FROM OLD.name THEN NEW.name ELSE v.name END,
        CASE WHEN NEW.risk_rating IS DISTINCT FROM OLD.risk_rating THEN NEW.risk_rating ELSE v.risk_rating END,
        greatest(v._valid_from, t), v._valid_to, app_now(), NULL);
    END IF;
  END LOOP;
  -- 4. INSERT asserts the new row from t on
  IF TG_OP = 'INSERT' THEN
    INSERT INTO customers_history VALUES (NEW._id, NEW.name, NEW.risk_rating, t, NULL, app_now(), NULL);
  END IF;
  RETURN CASE TG_OP WHEN 'DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER write INSTEAD OF INSERT OR UPDATE OR DELETE ON customers
  FOR EACH ROW EXECUTE FUNCTION customers_write();

-- Still not covered: a superuser can switch all of this off (DROP / DISABLE TRIGGER,
-- session_replication_role = replica); concurrent writers racing on the max(_system_from) check;
-- indexes serving both time axes; temporal foreign keys; and all of it again for every table.
