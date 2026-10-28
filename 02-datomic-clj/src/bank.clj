(ns bank
  "Credit file in Datomic: system time (when did we know it?) comes for free.

  REPL-first: start Datomic with `docker compose up -d --wait`, start a REPL in this folder,
  then evaluate the forms in the `comment` block at the bottom, one by one."
  (:require [clojure.pprint :refer [print-table]]
            [datomic.api :as d]))

;; ---------------------------------------------------------------- schema
;; Just the business attributes. No history tables, valid_from columns, triggers or procedures.

(def schema
  [{:db/ident :customer/id    :db/valueType :db.type/string  :db/cardinality :db.cardinality/one
    :db/unique :db.unique/identity}
   {:db/ident :customer/risk  :db/valueType :db.type/keyword :db/cardinality :db.cardinality/one}
   {:db/ident :customer/limit :db/valueType :db.type/long    :db/cardinality :db.cardinality/one}
   ;; who and why are facts about a *transaction*, not about a customer
   {:db/ident :audit/by       :db/valueType :db.type/string  :db/cardinality :db.cardinality/one}
   {:db/ident :audit/reason   :db/valueType :db.type/string  :db/cardinality :db.cardinality/one}
   ;; replaying the story: transaction time is pinned (it can only move forward)
   {:db/id "datomic.tx" :db/txInstant #inst "2026-01-01T00:00:00Z"}])

;; ---------------------------------------------------------------- the story, as data

(def onboarding
  [{:customer/id "ACME"   :customer/risk :low    :customer/limit 1000000}
   {:customer/id "GLOBEX" :customer/risk :medium :customer/limit 500000}
   {:db/id "datomic.tx" :db/txInstant #inst "2026-01-10T09:00:00Z"
    :audit/by "alice" :audit/reason "onboarding"}])

(def limit-raise
  [[:db/add [:customer/id "ACME"] :customer/limit 2000000]
   {:db/id "datomic.tx" :db/txInstant #inst "2026-02-01T10:00:00Z"
    :audit/by "alice" :audit/reason "annual review"}])

(def kyc-correction
  [[:db/add [:customer/id "ACME"] :customer/risk :high]
   {:db/id "datomic.tx" :db/txInstant #inst "2026-04-07T14:00:00Z"
    :audit/by "bob" :audit/reason "KYC-123 adverse media dated 2026-01-20"}])

;; ---------------------------------------------------------------- the auditor's questions
;; None of them mentions time: time is chosen by the database value they run against.

(def report
  '[:find ?id ?risk ?limit
    :where [?c :customer/id ?id]
           [?c :customer/risk ?risk]
           [?c :customer/limit ?limit]])

(def audit-trail                        ; run against (d/history db)
  '[:find ?when ?attr ?v ?added ?by ?why
    :in $ ?id
    :where [?c :customer/id ?id]
           [?c ?a ?v ?tx ?added]
           [?a :db/ident ?attr]
           [?tx :db/txInstant ?when]
           [?tx :audit/by ?by]
           [?tx :audit/reason ?why]])

(def changed-since                      ; $ = now, $since = (d/since db t)
  '[:find ?id ?attr ?v ?when ?by
    :in $ $since
    :where [$since ?c ?a ?v ?tx true]
           [$ ?c :customer/id ?id]
           [$ ?a :db/ident ?attr]
           [$ ?tx :db/txInstant ?when]
           [$ ?tx :audit/by ?by]])

;; ---------------------------------------------------------------- helpers

(defn fresh-conn
  "Connection to a brand-new database with the schema. A new one per call, because the story
  pins transaction times and those can only move forward within a database."
  []
  (let [uri (str "datomic:dev://localhost:4334/bank-" (System/currentTimeMillis) "?password=datomic")]
    (d/create-database uri)
    (doto (d/connect uri) (-> (d/transact schema) deref))))

(defn table
  "Print a query result (a set of tuples) as a sorted table with the given column names."
  [cols rel]
  (print-table cols (sort-by (apply juxt cols) (map #(zipmap cols %) rel))))

;; ---------------------------------------------------------------- play

(comment
  (def conn (fresh-conn))

  ;; 2026-01-10  alice onboards two customers
  @(d/transact conn onboarding)

  ;; 2026-02-01  alice raises ACME's limit: a plain write, the database keeps history
  @(d/transact conn limit-raise)

  ;; 2026-03-31  Q1 report: run against ONE immutable database value
  (def filed (d/db conn))
  (def report-t (d/basis-t filed))          ; store this with the report
  (table [:customer :risk :limit] (d/q report filed))

  ;; 2026-04-07  bob: adverse media about ACME dated 2026-01-20 -> HIGH risk
  @(d/transact conn kyc-correction)

  ;; Auditor 1) reproduce the filed report exactly: same query, as-of its basis-t
  (table [:customer :risk :limit] (d/q report (d/as-of (d/db conn) report-t)))
  ;; ... and the value we reported from never changed: it is a value
  (= (d/q report filed) (d/q report (d/as-of (d/db conn) report-t)))
  (table [:customer :risk :limit] (d/q report (d/db conn)))  ; today

  ;; Auditor 2) full history of ACME: who changed what, when, why
  (table [:when :attr :value :added? :by :why]
         (d/q audit-trail (d/history (d/db conn)) "ACME"))

  ;; Auditor 3) what changed after the report was filed?
  (let [db (d/db conn)]
    (table [:customer :attr :new-value :when :by]
           (d/q changed-since db (d/since db report-t))))

  ;; Auditor 4) what was really true on 2026-03-31, with what we know today?
  (table [:customer :risk :limit]
         (d/q report (d/as-of (d/db conn) #inst "2026-03-31T18:00:00Z")))
  ;; Still :low. Datomic's time is *when we learned it*, not *when it was true*: the
  ;; 2026-01-20 date only survives in a free-text reason. That needs a second time axis.

  ;; ------------------------------------------------ more to play with

  ;; any entity at any point in time
  (d/pull (d/as-of (d/db conn) report-t) '[*] [:customer/id "ACME"])

  ;; transactions are entities too: the last one the report saw, with its who/why
  (d/pull (d/db conn) '[*] (d/t->tx report-t))

  ;; what-if, without writing anything: a speculative database value
  (table [:customer :risk :limit]
         (d/q report (:db-after (d/with (d/db conn)
                                        [[:db/add [:customer/id "GLOBEX"] :customer/risk :high]]))))

  ;; the raw facts (datoms) of ACME across all time: [attribute value t added?]
  (let [db (d/db conn)]
    (->> (d/datoms (d/history db) :eavt [:customer/id "ACME"])
         (map (fn [[_ a v tx added]] [(d/ident db a) v (d/tx->t tx) added]))))
  )
