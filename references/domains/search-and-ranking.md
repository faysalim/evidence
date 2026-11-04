# Domain: search and ranking

Query understanding, an index that lags reality, relevance that is a claim rather than a feature, and facets
whose counts must agree with the results they promise.

## Do the thing

> Search returns results in 40ms and nothing errors. Create a document, search for it, and time how long
> until it appears. Then run a graded query set and compute precision at 10 against a human-labelled answer
> key — and check that each facet's count equals the number of results its filter actually returns. **A fast
> non-empty result list is this domain's HTTP 200. Relevance without a labelled query set is not a
> measurement, it is an opinion.**

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | relevance and scale claims | →9 | |
| 2 Primary product | query and results | own ×2 | split: retrieval and relevance vs filters, facets and pagination |
| 3 Control plane | index management, synonyms and ranking config, query analytics | own | |
| 4 Deployment | cluster, shards, replicas, resource limits | own | |
| 5 Entitlement | licensing | →4 | |
| 6 Secondary | ingestion connectors, client SDKs | own | |
| 7 Telemetry | click and query analytics — which feed ranking | →3 | |
| 8 Security | **document-level permissions at query time**, query-DSL injection | own | |
| 9 Documentation | the relevance claim, the freshness claim, the operator reference | own | |
| 10 State under fault | indexing lag, partial reindex, node loss, deletion propagation | own | |
| 11 Upgrade | reindex with a changed mapping, analyzer change, version upgrade | own | |
| 12 Experience | the user who finds nothing | own | |

**Usual set: 2×2,3,4,6,8,9,10,11,12 own + 1→9, 5→4, 7→3 = 10 agents.**

## Failure catalogue

A document created, updated and deleted, each followed immediately by a search · a reindex interrupted
halfway · a mapping or analyzer change without a reindex · queries returning zero, one, and a million
results · a misspelling, a transposition, a missing diacritic, a different unicode normalization · a query
in a language without spaces, and one that is right-to-left · a stop word as the whole query · a
1,000-character query · query-DSL syntax in the query string · pagination to page 500, and pagination while
documents are being inserted · a facet combination that should yield zero · a filter on an unindexed field ·
a user whose permissions change between the query and the click · a node lost mid-query · a synonym list
containing a cycle.

- **Published performance claim under saturation** (scope 8b): reproduce the claimed number on a
  stated rig, then measure the degradation curve at 10x and 100x that load. At saturation, establish
  whether it sheds load, queues unboundedly or loses data — queueing to out-of-memory is a
  durability defect wearing a performance costume.

## Defect classes to look for by name

**Deleted or access-revoked documents still returned** — the security case of index lag, and the one that
matters most · **permissions applied after ranking**, so a user is told "about 400 results" computed from
documents they cannot open: the count leaks their existence and is also simply a lie · a facet count that
disagrees with the filtered result count · pagination that loses or repeats items under concurrent writes ·
index freshness far worse than claimed, or unbounded during a reindex · **relevance regressed by a config
change with no evaluation**, which nobody can detect because the control does not exist · index-time and
query-time analysis mismatched, so an exact title does not match itself · unicode normalization or case
folding inconsistent between index and query · zero-result queries neither handled nor logged, so the
product can never learn what it cannot find · query-DSL injection from user input · a synonym or boost rule
silently shadowing a whole category.

## Evidence and severity

Two numbers, each with a denominator. **Relevance:** a graded query set — queries with human-labelled
relevant documents — scored as precision@k or nDCG, computed **before and after** any ranking change. Where
no labelled set exists, say so in Not Verified rather than asserting relevance is good. **Freshness:**
create-to-searchable latency as a distribution over *n* documents, never a single measurement.

Permissions are proved by the matrix, run as each role, checking **the count and the snippets as well as the
hits**. Record index version, mapping and analyzer config, ranking config, document count, and the query
verbatim with its parsed form where the product exposes one.

`evidence-standard.md` → *Authorization and permission matrices*, *Stateful systems under fault* (lag, node
loss), *Data pipeline runs* (ingestion reconciles exactly like a pipeline), *Migrations, upgrades and
restores* (a reindex is a migration).

| Observation | Severity |
|---|---|
| Documents surfaced to a user who may not see them — by hit, snippet or count | **critical** |
| Deletion not propagating to the index | **critical** — a leak, and an erasure obligation |
| Pagination losing items | **blocker** |
| Facet counts disagreeing with results | **blocker** — the product asserted a number |
| A relevance regression shipped with no evaluation | **blocker** — the control does not exist |
| Freshness materially worse than documented | **blocker** |
| Zero-result queries unlogged | **major** — and the cheapest fix in the domain |

## Experience

**Who the user is:** someone who does not know the vocabulary of the corpus and is typing their best guess.

**Where it lives:** the zero-result state; whether a misspelling recovers; whether facets are discoverable
and truthful; whether a snippet shows *why* a result matched; and whether the user can tell they are seeing
a filtered subset.

**First success is:** a user who does not know the right term finds the right document on the first screen,
in one query.

**Do the thing, for experience:**

> Search for a document using words that are *not in it* — a synonym, a misspelling, the words a newcomer
> would use. Then study the zero-result screen, because that is the screen the product shows most often to
> the people who have just arrived.

**Defect classes:** a zero-result dead end with no suggestion, no broadening and no route out · snippets
that do not contain the match, so relevance cannot be justified to the user · facet labels taken from an
internal taxonomy · a result count stated with false precision · sort and relevance silently fighting, where
choosing a sort discards ranking with no indication.

**Evidence note:** **the zero-result rate from real query logs** is this domain's first-run number. Either
it is already being collected or it is not — and if the product does not log zero-result queries, that
absence is itself the finding, because it means nobody can ever know.

## Domain gotchas

- Index your own corpus. A shared index is somebody's production data and reindexing it is destructive.
- **Relevance judgement without a labelled set is where this domain's reports go wrong.** Route a relevance
  opinion as a `DECIDE` memo, labelled as judgement per `experience.md`, rather than filing it as a defect.
- Report freshness as a distribution: the mean hides the tail, and the tail is what users notice.
- A reindex changes relevance and performance at the same time. Separate them, or the result cannot be
  interpreted.
- Analytics-driven ranking means **your own test queries pollute the ranking signal.** Use a separate index
  or a flagged client, and ledger it.
- Deep paging is often documented as unsupported past a depth. Read the limit before filing the finding.
