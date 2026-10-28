(ns bank.with-valid-time
  "Alice's risk rating in Datomic, with valid time modelled by hand (`:customer/valid-from`).
  System time (what did we believe, when?) is built in; valid time (when was it true?) is not.

  REPL-first: start Datomic with `docker compose up -d --wait`, start a REPL in this folder,
  then evaluate the forms in the `comment` block at the bottom, one by one."
  (:require [datomic.api :as d]))

(def schema
  [{:db/ident :customer/name        :db/valueType :db.type/string  :db/cardinality :db.cardinality/one
    :db/unique :db.unique/identity}
   {:db/ident :customer/risk-rating :db/valueType :db.type/keyword :db/cardinality :db.cardinality/one}
   ;; valid time is NOT built in: modelled by hand. One value per entity only works for a single
   ;; "true since" date; real business-time history needs an entity per version.
   {:db/ident :customer/valid-from  :db/valueType :db.type/instant :db/cardinality :db.cardinality/one}
   {:db/id "datomic.tx" :db/txInstant #inst "2025-12-31T00:00:00Z"}])       ; demo clock

(def record-alice
  [{:customer/name "Alice" :customer/risk-rating :low :customer/valid-from #inst "2026-01-01T09:00:00Z"}
   {:db/id "datomic.tx" :db/txInstant #inst "2026-01-01T09:00:00Z"}])       ; demo clock

(def correct-alice
  [{:customer/name "Alice" :customer/risk-rating :high :customer/valid-from #inst "2026-01-01T00:00:00Z"}
   {:db/id "datomic.tx" :db/txInstant #inst "2026-01-15T10:00:00Z"}])       ; demo clock

;; Both questions use this one query. Which question it answers depends only on the
;; database value it runs against: now, or (d/as-of db t).
(def rating-on
  '[:find ?c ?name ?rating ?valid-from
    :in $ ?t
    :where [?c :customer/name ?name]
           [?c :customer/risk-rating ?rating]
           [?c :customer/valid-from ?valid-from]
           [(<= ?valid-from ?t)]])

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

  ;; Q1: what do we now believe was true on 2026-01-10?
  (d/q rating-on (d/db conn) jan-10)

  ;; Q2: what did we believe on 2026-01-10?
  (d/q rating-on (d/as-of (d/db conn) jan-10) jan-10)

  ;; Check: what do we now believe was true on 2025-12-31, before Alice was a customer? Nothing.
  (d/q rating-on (d/db conn) #inst "2025-12-31T12:00:00Z")
  )
