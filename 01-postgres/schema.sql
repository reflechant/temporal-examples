-- Hand-made bitemporal table in plain PostgreSQL.
-- Everything in this file is code YOU own: write it, test it, review it, keep it right
-- for every table that needs history.

CREATE EXTENSION IF NOT EXISTS btree_gist;

DROP TABLE IF EXISTS customer_version CASCADE;

CREATE TABLE customer_version (
  customer_id  text      NOT NULL,
  risk         text      NOT NULL,
  credit_limit numeric   NOT NULL,
  valid        tstzrange NOT NULL,  -- business time: when this was true in the real world
  recorded     tstzrange NOT NULL,  -- system time:   when the database believed it
  changed_by   text      NOT NULL,
  reason       text      NOT NULL,
  -- at most one belief per customer for any (business instant, system instant)
  EXCLUDE USING gist (customer_id WITH =, valid WITH &&, recorded WITH &&)
);

-- Change some attributes of a customer for a period of business time.
-- NULL arguments mean "keep the value of whatever version is being split".
-- p_now is a parameter only so the demo can replay a timeline; in production it is now().
CREATE OR REPLACE PROCEDURE set_customer(p_id text, p_risk text, p_limit numeric, p_valid tstzrange,
                                         p_by text, p_reason text, p_now timestamptz DEFAULT now())
LANGUAGE plpgsql AS $$
DECLARE v customer_version;
BEGIN
  -- 1. Retire every current belief that overlaps the period (never UPDATE values in place) ...
  FOR v IN UPDATE customer_version SET recorded = tstzrange(lower(recorded), p_now)
            WHERE customer_id = p_id AND upper_inf(recorded) AND valid && p_valid
           RETURNING *
  LOOP
    -- 2. ... re-assert the slice before the period, unchanged ...
    IF lower(v.valid) < lower(p_valid) THEN
      INSERT INTO customer_version VALUES (v.customer_id, v.risk, v.credit_limit,
        tstzrange(lower(v.valid), lower(p_valid)), tstzrange(p_now, NULL), v.changed_by, v.reason);
    END IF;
    -- 3. ... re-assert the slice after the period, unchanged ...
    IF NOT upper_inf(p_valid) AND (upper_inf(v.valid) OR upper(v.valid) > upper(p_valid)) THEN
      INSERT INTO customer_version VALUES (v.customer_id, v.risk, v.credit_limit,
        tstzrange(upper(p_valid), upper(v.valid)), tstzrange(p_now, NULL), v.changed_by, v.reason);
    END IF;
    -- 4. ... and assert the overlapping slice with the new values patched in.
    INSERT INTO customer_version VALUES (v.customer_id,
      coalesce(p_risk, v.risk), coalesce(p_limit, v.credit_limit),
      v.valid * p_valid, tstzrange(p_now, NULL), p_by, p_reason);
  END LOOP;
END $$;

-- Still missing for production: one such procedure per table (or dynamic SQL), inserting into
-- business-time gaps, permissions/triggers stopping plain UPDATE/DELETE, temporal foreign keys,
-- and indexes that serve both time axes.
