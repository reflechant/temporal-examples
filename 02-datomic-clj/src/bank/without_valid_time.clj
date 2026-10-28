(ns bank.without-valid-time
  "Alice's risk rating in Datomic as it comes: system time only, no valid time modelled.
  Q2 (what did we believe then?) is free; Q1 (what was true then?) cannot be asked.

  REPL-first: start Datomic with `docker compose up -d --wait`, start a REPL in this folder,
  then evaluate the forms in the `comment` block at the bottom, one by one."
  (:require [datomic.api :as d]))

(def schema
  [{:db/ident :customer/name        :db/valueType :db.type/string  :db/cardinality :db.cardinality/one
    :db/unique :db.unique/identity}
   {:db/ident :customer/risk-rating :db/valueType :db.type/keyword :db/cardinality :db.cardinality/one}
   {:db/id "datomic.tx" :db/txInstant #inst "2025-12-31T00:00:00Z"}])       ; demo clock

(def record-alice
  [{:customer/name "Alice" :customer/risk-rating :low}
   {:db/id "datomic.tx" :db/txInstant #inst "2026-01-01T09:00:00Z"}])       ; demo clock

(def correct-alice                      ; "since 2026-01-01" has nowhere to go
  [{:customer/name "Alice" :customer/risk-rating :high}
   {:db/id "datomic.tx" :db/txInstant #inst "2026-01-15T10:00:00Z"}])       ; demo clock

(def rating
  '[:find ?c ?name ?rating
    :where [?c :customer/name ?name]
           [?c :customer/risk-rating ?rating]])

(defn fresh-conn
  "Connection to a brand-new database with the schema. A new one per call, because the story
  pins transaction times and those can only move forward within a database."
  []
  (let [uri (str "datomic:dev://localhost:4334/bank-" (System/currentTimeMillis) "?password=datomic")]
    (d/create-database uri)
    (doto (d/connect uri) (-> (d/transact schema) deref))))

(comment
  (def conn (fresh-conn))

  ;; 2026-01-01  the bank records Alice as LOW risk
  @(d/transact conn record-alice)

  ;; 2026-01-10  the bank approves a loan, based on LOW
  (def jan-10 #inst "2026-01-10T12:00:00Z")

  ;; 2026-01-15  the bank discovers Alice should have been HIGH since 2026-01-01
  @(d/transact conn correct-alice)

  ;; Q2: what did we believe on 2026-01-10?  The database as of then: built in.
  (d/q rating (d/as-of (d/db conn) jan-10))

  ;; Q1: what do we now believe was true on 2026-01-10?  Can't be asked: there is no date to
  ;; put in the query. The closest is "what do we believe now", which is about now:
  (d/q rating (d/db conn))
  ;; HIGH matches Q1 only because the correction still holds today. Asked about 2025-12-31,
  ;; before Alice was a customer, this is still the only query, and it still says HIGH.

  ;; ... and the database's own history says Alice became HIGH on 2026-01-15, not 2026-01-01:
  (d/q '[:find ?rating ?since
         :where [?c :customer/name "Alice"]
                [?c :customer/risk-rating ?rating ?tx true]
                [?tx :db/txInstant ?since]]
       (d/history (d/db conn)))
  ;; Answering Q1 means modelling valid time yourself: see bank.with-valid-time
  )
