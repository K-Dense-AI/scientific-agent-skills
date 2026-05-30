# Designing Data-Intensive Applications (Martin Kleppmann, 2017)

**Thesis:** Most data-system problems are not compute-limited but rather reliability, scalability, and maintainability problems — and every architectural decision is a trade-off between these three forces, made concrete by understanding what actually happens inside storage engines, replication protocols, transaction isolation levels, and distributed coordination algorithms.

---

## What this book makes you good at

- Choosing the right database/storage engine for a workload (OLTP vs OLAP, LSM vs B-tree, relational vs document vs graph)
- Reasoning precisely about replication lag and which consistency guarantees you actually get
- Designing partitioning schemes that avoid hot spots and scale correctly
- Predicting which concurrency anomalies a given isolation level does and does not prevent
- Understanding what "ACID" and "eventual consistency" really mean (versus marketing usage)
- Making defensible decisions about linearizability vs causal consistency vs eventual consistency and their real performance costs
- Knowing when two-phase commit is necessary and when it kills availability
- Designing encoding/schema strategies for zero-downtime rolling upgrades

---

## Core principles (actionable)

### 1. Reliability, Scalability, Maintainability are distinct axes — don't conflate them

**Reliability** = the system continues to work correctly even when things go wrong. Distinguish *fault* (one component deviating from spec) from *failure* (system-wide service loss). Design to tolerate faults, not eliminate them: "Counter-intuitively, in such fault-tolerant systems, it can make sense to increase the rate of faults by triggering them deliberately — for example, by randomly killing individual processes without warning." (PAGE 27) Configuration errors by operators are the *leading* cause of outages, not hardware faults.

**Scalability** is not a one-dimensional label. "It is meaningless to say 'X is scalable' or 'Y doesn't scale'. Rather, discussing scalability means to discuss the question: if the system grows in a particular way, what are our options for coping with the growth?" (PAGE 31) Always identify your *load parameters* first (requests/sec, fan-out ratio, read:write ratio, cache hit rate). Twitter's canonical example: home-timeline reads at 300k/sec vs tweet writes at 4.6k/sec — the bottleneck is fan-out, not write volume, so move work to write time (precompute per-follower caches) rather than read time.

**Maintainability** decomposes into *Operability* (easy for ops teams), *Simplicity* (remove accidental complexity), *Evolvability* (easy to change). "The majority of the cost of software is not in its initial development, but in its ongoing maintenance." (PAGE 38)

### 2. Measure performance with percentiles, not averages

The arithmetic mean is a poor metric for response time. Use p50, p95, p99, p999. "Amazon describes response time requirements for internal services in terms of the 99.9th percentile, even though it only affects 1 in 1,000 requests. This is because the customers with the slowest requests are often those who have made many purchases — i.e. the most valuable customers." (PAGE 35) A 100ms increase in response time reduces Amazon sales by 1%.

Tail latencies amplify in fan-out architectures: if a request requires 100 backend calls, even p1 slow calls affect nearly every end-user request. Measure response times on the *client side*, not the server side. Never average percentiles — that is mathematically meaningless. Add histograms together instead.

Head-of-line blocking: one slow request holds up subsequent fast requests in a queue, inflating the observed p99 even when median is fine. Load-test clients must send requests *independently* of response time, or they will artificially shorten queues and underestimate tail latency.

### 3. Storage engines: LSM-trees vs B-trees — know what each optimizes

**Log-Structured / LSM-trees** (used by LevelDB, RocksDB, Cassandra, HBase, Lucene):
- All writes are appends → sequential I/O → high write throughput on both HDD and SSD
- Memtable (in-memory sorted tree) accumulates writes; flushed to SSTable segments on disk; background compaction merges segments
- Bloom filters prevent checking all segments for absent keys
- Trade-off: compaction can saturate disk bandwidth; read amplification on cold keys (check memtable + all segments); writes can be slower if compaction falls behind ingestion
- **Choose when:** write-heavy workloads, time-series, event logs

**B-trees** (used by PostgreSQL, MySQL, SQLite, most traditional RDBMS):
- Update in-place with write-ahead log (WAL) for crash safety
- Each key exists in exactly one place → simpler transactional semantics, predictable read performance
- WAL shipping replication is tightly coupled to storage format version (zero-downtime upgrades harder)
- Trade-off: random writes → worse write amplification; background fragmentation
- **Choose when:** read-heavy OLTP, range scans needed, strong transactional guarantees

**Practical rule:** "An index is an additional structure that is derived from the primary data. Maintaining additional structures is overhead, especially on writes. Any kind of index usually slows down writes." (PAGE 92) Choose indexes deliberately using knowledge of query patterns.

### 4. OLTP vs OLAP: don't run analytics on your transactional store

OLTP: many small random-access queries on individual records, high write throughput, user-facing latency requirements. B-trees or LSM-trees, row-oriented.

OLAP/data warehousing: large sequential scans aggregating millions of rows, mostly reads, run by analysts not users. Use column-oriented storage: store each column's values contiguously. This dramatically reduces I/O for analytic queries (read only columns needed), enables vectorized processing, and enables per-column compression (bitmap indexes, run-length encoding). Star/snowflake schemas: fact table of events + dimension tables.

"The bottleneck for column-oriented storage is typically disk bandwidth, not CPU." Run columnar databases on separate infrastructure — the access patterns, hardware optimization, and schema design are fundamentally different.

### 5. Schema evolution requires explicit backward and forward compatibility design

**Backward compatibility:** new code can read data written by old code (usually achievable by keeping old fields/handling).
**Forward compatibility:** old code can read data written by new code (harder — old code must be able to skip/ignore unknown fields).

Both are needed simultaneously during rolling upgrades, when old and new binary versions coexist.

**Protobuf/Thrift:** Use numeric field tags (never change them). Add new fields as optional or with defaults. Never reuse a tag number after removal. You can rename fields safely (binary format uses tags, not names). Avro uses writer's schema + reader's schema resolution by field *name* — more friendly for dynamically-generated schemas (e.g., auto-generated from a relational schema) but schema must be stored alongside data or negotiated on connection.

**Never use language-specific serialization** (Java Serializable, Python pickle) for anything durable: it locks you to one language, creates security vulnerabilities via arbitrary class instantiation, and provides no compatibility story.

**JSON:** Good for inter-organization data exchange where agreement is hard. Limitations: no distinction between integer and float, no native binary, large numbers lose precision (>2^53), no schema enforcement by default. Use binary JSON (MessagePack, BSON) only for internal systems where human readability is not needed.

### 6. Replication: know exactly what guarantee each topology provides

**Single-leader (master-slave):** All writes go to leader; followers replicate. Simple, most RDBMS default.
- Synchronous follower: write not confirmed until follower acknowledges. Durable but blocks writes if follower is slow/down. In practice, use semi-synchronous (one synchronous + rest async).
- Asynchronous: leader can continue if followers lag. Eventual consistency — replication lag can be seconds to minutes.

**Replication lag anomalies** (all fixable at application layer if you know they exist):
- *Read-your-writes (read-after-write):* User writes to leader, immediately reads from lagging follower, sees their own write missing. Fix: route the user's own reads to the leader, or track user's last write timestamp and refuse serving stale replicas.
- *Monotonic reads:* User reads from fresh replica, then stale replica — data "goes backwards in time." Fix: always route a user's reads to the same replica (hash by user ID).
- *Consistent prefix reads:* In partitioned databases, causal ordering may be violated across partitions. Fix: route causally related writes to same partition.

**Multi-leader replication:** Useful for multi-datacenter (lower write latency, tolerates datacenter outage) and offline-capable clients. Big downside: write conflicts. Last-write-wins (LWW) loses data; CRDTs and operational transformation are safer but complex. "Multi-leader replication is often considered dangerous territory that should be avoided if possible." (PAGE 185)

**Leaderless replication (Dynamo-style):** Quorum writes (w) + quorum reads (r) with n replicas: require w + r > n for reads to see fresh writes. Sloppy quorums help availability during network partitions but further weaken durability guarantees. Even with quorums, stale reads are possible (read repair and anti-entropy help eventually).

### 7. Partitioning: key-range vs hash, and the hot-spot dilemma

**Key-range partitioning:** Partition by sorted key ranges. Enables efficient range scans. Danger: hotspots if keys correlate with time (all writes go to today's partition). Fix: prefix key with a different high-cardinality field (e.g., sensor_name + timestamp instead of timestamp alone).

**Hash partitioning:** Hash of key determines partition. Evenly distributes load. Loses range scan ability (MongoDB scatter-gathers range queries to all partitions). Cassandra compromise: compound key — first column hashed for partition, remaining columns sorted within partition for range queries.

**Hotspot handling:** Even hash partitioning cannot help if all traffic goes to one key (celebrity user). Application-level solution: add a 2-digit random suffix to split the hot key across 100 partitions, then aggregate reads. Track which keys need splitting.

**Secondary indexes and partitioning:**
- *Document-based (local):* Each partition has its own secondary index covering its documents only. Writes are fast (update local index only). Reads require scatter-gather across all partitions. Used by MongoDB, Riak, Cassandra, Elasticsearch.
- *Term-based (global):* One global index, itself partitioned. Reads go to just the partition holding the index term. Writes are slower (must update multiple partitions). Used by DynamoDB global secondary indexes.

**Rebalancing:** Fixed number of partitions (pre-allocate more than nodes, reassign whole partitions when adding nodes) is simpler than dynamic splitting. Prefer manual approval of rebalancing plans — automatic rebalancing can cause cascading failures during already-stressed conditions.

### 8. Transactions: ACID is not what vendors claim

ACID = Atomicity, Consistency, Isolation, Durability. "ACID has unfortunately become mostly a marketing term." (PAGE 237) Consistency in ACID is an application invariant (not the database's job to enforce), not a distributed systems property.

**Atomicity** = abortability. If anything fails mid-transaction, all writes roll back. The defining feature is that the application can safely retry.

**Isolation levels — know which anomalies each prevents:**

| Level | Dirty reads | Dirty writes | Read skew | Lost updates | Write skew | Phantoms |
|---|---|---|---|---|---|---|
| Read committed | Prevented | Prevented | Not prevented | Not prevented | Not prevented | Not prevented |
| Snapshot isolation (MVCC) | Prevented | Prevented | Prevented | Depends on DB | Not prevented | Not prevented |
| Serializable | Prevented | Prevented | Prevented | Prevented | Prevented | Prevented |

Key anomalies to recognize:
- **Lost update:** Two transactions read-modify-write the same value. Second write clobbers first. Fix: atomic operations (`UPDATE SET value = value + 1`), explicit `SELECT FOR UPDATE`, or rely on database's automatic lost-update detection (PostgreSQL repeatable read catches it; MySQL/InnoDB does not).
- **Write skew:** Two transactions read overlapping data, then write to *different* objects based on that read, violating a multi-row invariant (doctor on-call example). Snapshot isolation does not prevent write skew — you need true serializable isolation or explicit `SELECT FOR UPDATE` on the read rows.
- **Phantom:** Write in one transaction changes the result of a search query in another. Materializing conflicts (create lock rows in advance) or serializable isolation are the fixes.

**Serializability implementations:**
1. *Actual serial execution* (VoltDB, Redis, Datomic): single thread, stored procedures, all data in memory. High throughput on one core; requires all data for a transaction to be in RAM.
2. *Two-phase locking (2PL):* Pessimistic. Read lock on all reads, write lock on all writes, held until commit. Writers block readers and vice versa. Predicate locks (or next-key locks) prevent phantoms. High overhead; deadlocks possible.
3. *Serializable Snapshot Isolation (SSI):* Optimistic. Transactions proceed without blocking; at commit time, database checks whether any stale reads were used (tracks read-write conflicts). Aborts losers. Lower overhead than 2PL. Used by PostgreSQL 9.1+.

**SSI vs 2PL:** SSI wins under low contention (optimistic pays off, no lock overhead). 2PL wins under high contention (many aborts in SSI). Note: SSI is NOT linearizable — it uses snapshots, so reads do not see the most recent committed writes.

### 9. Distributed systems: embrace partial failure as the baseline

A single computer is deterministic — it either works or crashes totally. Distributed systems are fundamentally different: *partial failures* are non-deterministic. A network request gives you no information whether the remote node received it, processed it, or just lost the response. "If you send a request to another node and don't receive a response, it is impossible to tell why." (PAGE 293)

**Networks:** Asynchronous packet networks have *unbounded delays*. There is no maximum delivery time. TCP hides packet loss but cannot remove delays. Queue-induced latency: switch queues, OS queue, VM pause, TCP flow control all contribute. Choose timeouts empirically; too short = false failures that cascade; too long = slow recovery.

**Clocks:** System (wall-clock) clocks are unreliable — NTP sync error can be 100ms or more, monotonically increasing clock can jump backwards after NTP correction. Monotonic clocks are reliable for measuring elapsed time but not for comparing events across nodes. Never use timestamps for distributed event ordering — use logical clocks (Lamport timestamps, version vectors). Lamport timestamps: (counter, node_id), where counter = max of seen counters + 1. They provide causal ordering but are a total order (can't distinguish concurrent from causally related operations). Version vectors distinguish concurrent from causally-ordered.

**Process pauses:** A thread can be stopped for an unbounded time by GC, OS scheduling, VM migration, page faults. This means a node cannot trust its own sense of time. A leader with an expired lease may believe it is still leader — "just because a node believes it is 'the leader' doesn't necessarily mean that a quorum of nodes agrees." (PAGE 294) Use fencing tokens (monotonically increasing per lock grant) to make stale leaders' writes rejectable.

### 10. Linearizability vs causal consistency — pick the right tool

**Linearizability** (strong consistency, external consistency): behave as if there is only one copy of the data; every operation appears atomic at a single point in time. Once a write completes, all subsequent reads from any client see that value. Required for: distributed locks/leader election, uniqueness constraints enforced on write, cross-channel coordination.

Cost: "Linearizability is slow — and this is true all the time, not only during a network fault." (PAGE 329) Response time proportional to network uncertainty. CAP theorem applies — under network partition, you cannot be both available and linearizable. Multi-region deployments often sacrifice linearizability for latency.

**Causal consistency:** Preserve causal order (cause before effect) but allow concurrent operations to be ordered arbitrarily. Much stronger than eventual consistency but weaker than linearizability. Key insight: "In many cases, systems that appear to require linearizability in fact only really require causal consistency, which can be implemented more efficiently." (PAGE 355) Causal consistency is the strongest model that does not slow down due to network delays and remains available under network failures.

**CAP theorem as commonly stated is misleading.** The real trade-off is not binary (C vs A) — it is a continuous spectrum where linearizability is expensive but achievable without partitions. Most systems sacrifice linearizability not for fault tolerance but for *performance*. "Many distributed databases that choose not to provide linearizable guarantees: they do so primarily to increase performance, not so much for fault tolerance." (PAGE 329)

**Total Order Broadcast:** A primitive stronger than causal consistency but that can implement linearizability. Delivers every message to every node in the same order; no message delivered twice. Used by ZooKeeper and etcd. Can implement a linearizable compare-and-set register on top of total order broadcast.

### 11. Two-phase commit (2PC) buys atomic distributed transactions at the cost of availability

2PC coordinator: phase 1 = ask all participants to prepare (write to durable log); phase 2 = if all say yes, commit (otherwise abort). If coordinator crashes *between* phases, participants are *in doubt* — they hold locks and cannot unilaterally proceed. They must wait for coordinator recovery. This is why 2PC is called a *blocking* protocol.

"In-doubt transactions are called 'orphaned' in practice; they block rows, partitions, and connections until the coordinator is restarted." This is a serious operational problem. Use 2PC only when you genuinely need atomic cross-system commits (e.g., writing to a database and a message queue atomically). Use idempotent operations + at-least-once delivery as an alternative when possible.

Fault-tolerant consensus algorithms (Raft, Paxos, Zab, Viewstamped Replication) do not have the coordinator single-point-of-failure problem — they use a quorum to commit. Consensus requires at least 2f+1 nodes to tolerate f failures.

---

## Chapter map

| Part/Chapter | Title | Problem solved |
|---|---|---|
| Part I | Foundations | Single-node data system fundamentals |
| Ch 1 | Reliable, Scalable, Maintainable Applications | Defines the three pillars; load parameters; percentiles |
| Ch 2 | Data Models and Query Languages | Relational vs document vs graph; SQL vs declarative vs MapReduce |
| Ch 3 | Storage and Retrieval | LSM-trees vs B-trees; OLTP vs OLAP; column stores |
| Ch 4 | Encoding and Evolution | Schema evolution; backward/forward compatibility; Avro/Protobuf/Thrift/JSON |
| Part II | Distributed Data | Multi-node data systems |
| Ch 5 | Replication | Single/multi-leader/leaderless replication; replication lag anomalies |
| Ch 6 | Partitioning | Sharding by key range vs hash; secondary indexes; rebalancing; request routing |
| Ch 7 | Transactions | ACID; isolation levels; lost updates; write skew; serializability (2PL, SSI) |
| Ch 8 | The Trouble with Distributed Systems | Partial failures; unreliable networks; unreliable clocks; process pauses |
| Ch 9 | Consistency and Consensus | Linearizability; CAP; causal consistency; total order broadcast; 2PC; consensus |
| Part III | Derived Data | Multi-system integration |
| Ch 10 | Batch Processing | Unix philosophy; MapReduce; dataflow; joins in batch |
| Ch 11 | Stream Processing | Event streams; CDC; event sourcing; stream joins; fault tolerance |

---

## Problem -> where to look

| Engineering problem | Chapter/Section | Approximate page |
|---|---|---|
| Choosing between document, relational, and graph databases | Ch 2: Relational Model vs Document Model; Graph-like Data Models | pp 26–62 |
| Understanding LSM-tree vs B-tree trade-offs for storage engine selection | Ch 3: SSTables and LSM-trees; B-trees | pp 74–82 |
| Designing column-oriented storage for analytic workloads | Ch 3: Column-oriented storage | pp 93–100 |
| Making schema changes without downtime during rolling upgrades | Ch 4: Field tags and schema evolution; Avro writer/reader schema | pp 116–124 |
| Diagnosing replication lag anomalies (stale reads, time going backwards) | Ch 5: Problems With Replication Lag | pp 155–161 |
| Choosing between single-leader, multi-leader, and leaderless replication | Ch 5: Multi-leader replication; Leaderless replication | pp 161–186 |
| Avoiding hot spots in partitioned databases | Ch 6: Partitioning by hash of key; Skewed workloads and relieving hot spots | pp 195–197 |
| Designing secondary indexes across a sharded database | Ch 6: Partitioning secondary indexes by document vs by term | pp 197–201 |
| Diagnosing concurrency bugs (lost update, write skew, phantom) | Ch 7: Preventing lost updates; Preventing write skew and phantoms | pp 233–242 |
| Choosing the right transaction isolation level | Ch 7: Weak isolation levels; Serializability | pp 224–257 |
| Understanding why distributed systems have non-deterministic failures | Ch 8: Faults and Partial Failures; Unreliable Networks; Unreliable Clocks | pp 265–302 |
| Deciding between linearizability and eventual/causal consistency | Ch 9: Linearizability; The cost of linearizability; Ordering and causality | pp 314–338 |
| Implementing atomic commit across multiple databases or services | Ch 9: Atomic commit and two-phase commit (2PC) | pp 344–355 |
| Understanding what CAP theorem actually says vs common misconceptions | Ch 9: The cost of linearizability | pp 326–329 |
| Building event-driven systems with change data capture | Ch 11: Change data capture; Event sourcing; State, streams, and immutability | pp 439–448 |

---

## Convergences & debates

### Where DDIA agrees with the other books in the set

**With The Pragmatic Programmer and SWE@Google:** Operational excellence matters. DDIA's operability principle — make routine tasks easy, prefer self-healing with manual override, provide good monitoring — aligns with Pragmatic's "tracer bullets" and SWE@Google's emphasis on observability and SLOs. Both DDIA and SWE@Google treat reliability as an engineering discipline with concrete metrics (SLOs, error budgets) rather than a vague aspiration.

**With all books on abstraction:** DDIA agrees with APOSD's deep-module principle — good abstractions hide complexity. SQL hiding B-trees and concurrency from application developers is cited as the canonical good abstraction. Transactions are praised for hiding error handling from application code.

**With Clean Code / Code Complete on simplicity:** Accidental complexity is the enemy. DDIA cites Moseley and Marks on accidental vs essential complexity, consistent with APOSD and Clean Code's shared horror of unnecessary complexity.

### Where DDIA disagrees or nuances the other books

**Against naive "ACID databases are safe" advice:** Many engineers assume any SQL database is ACID and therefore safe from concurrency bugs. DDIA firmly corrects this: Oracle 11g's "serializable" is actually snapshot isolation (weaker); MySQL's repeatable read does not detect lost updates; most production systems use read committed as default. "Even many popular relational database systems (which are usually considered 'ACID') use weak isolation, so they wouldn't necessarily have prevented these bugs." (PAGE 247) DDIA is far more specific about isolation level semantics than any general software engineering book.

**Against "eventual consistency is fine for everything" NoSQL hype:** DDIA documents the real anomalies (lost updates, write skew, stale reads) that occur with eventual consistency and leaderless replication, countering the 2010s NoSQL hype that transactions are unnecessary for scale. This is a direct counter-position to the "transactions are too expensive" claim.

**Against Clean Architecture's strict layering applied to data systems:** Clean Architecture prescribes clear dependency layers flowing inward. DDIA shows that data systems often violate clean layering for fundamental performance reasons — replication log format is tightly coupled to the storage engine (WAL shipping); column stores blur the line between storage and query processing; CDC treats the database log as an API. Kleppmann's message is that data-system architecture is driven by physical constraints (disk I/O, network delays, clock drift) more than by design principles.

**Nuances The Pragmatic Programmer on DRY:** Pragmatic Programmer's DRY ("every piece of knowledge must have a single authoritative source") is complicated in distributed systems: you often need to accept eventual inconsistency between replicas as a deliberate trade-off, meaning the "same" data legitimately exists in multiple inconsistent copies during normal operation. DRY is a code principle; data replication is a reliability principle; they serve different goals.

**Against Clean Code's implicit assumption of single-process correctness:** Clean Code's guidance (small functions, clear naming, test everything) assumes a single-threaded or at-most-concurrent single-process world. DDIA demonstrates that distributed systems introduce whole new correctness dimensions (partial failure, network non-determinism, clock skew) that clean unit-tested code cannot prevent. Correctness requires explicit reasoning about consistency models and failure modes, not just clean local code.

**With APOSD against premature abstraction:** DDIA warns throughout against misapplying distributed complexity when a single node suffices. "Stateless services scale out easily; taking stateful data from a single node to distributed introduces a lot of additional complexity. Common wisdom: keep your database on a single node until scaling cost or high-availability requirements force distribution." (PAGE 38) This aligns with APOSD's preference for deep, simple abstractions over premature decomposition.

**Against "one-size-fits-all" scalability patterns:** SWE@Google and many engineering blogs suggest canonical patterns (sharding, caching, async queues). DDIA insists "there is no such thing as a generic, one-size-fits-all scalable architecture (informally known as magic scaling sauce)." (PAGE 38) Every load parameter matters; architecture must match the specific read/write/data-volume/latency profile.
