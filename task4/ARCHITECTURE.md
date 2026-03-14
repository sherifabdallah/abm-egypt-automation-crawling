# Task 4 — System Architecture

## Overview

The diagram (`architecture_diagram.png`) illustrates a production-grade distributed system for large-scale web automation and crawling. It is designed for high throughput, fault tolerance, and observability.

---

## Layer-by-layer breakdown

### 1. Ingestion Layer
- Multiple clients (web UI, API consumers, cron scheduler, webhooks) submit crawl/automation jobs via HTTPS.
- An **API Gateway / Load Balancer** (nginx / AWS ALB) handles TLS termination, rate-limiting, and authentication before routing requests inward.

### 2. Message Queue — RabbitMQ Cluster
- All incoming jobs are published to a **RabbitMQ cluster** (primary + mirrored nodes).
- Separate queues segment workloads:
  - `crawl_queue` — raw crawl tasks
  - `scrape_queue` — structured scraping tasks
  - `retry_queue` — failed jobs awaiting re-attempt
  - `dead_letter_queue` — permanently failed jobs for investigation
- Topic and direct exchanges allow fine-grained routing.

### 3. Worker Pool (Horizontal Scaling)
- Workers are **stateless** Python processes running Playwright/httpx.
- They consume from RabbitMQ, execute tasks, and write results to the data layer.
- Kubernetes HPA (or Docker Swarm) auto-scales the pool from 2 to 20+ nodes based on queue depth and CPU metrics.
- Each worker type (Crawler, Scraper, Automation) is deployed as a separate Deployment/Service for independent scaling.

### 4. Data Layer
| Component | Role |
|---|---|
| PostgreSQL Primary | Write master — job metadata, results, audit log |
| PostgreSQL Replica | Read replica — analytics queries, reporting |
| Redis | Hot cache — deduplication bloom filter, session tokens |
| Object Store (S3/MinIO) | Raw HTML, screenshots, downloaded assets |

Replication uses streaming WAL (Patroni-managed failover).

### 5. Monitoring & Observability
| Tool | Purpose |
|---|---|
| Prometheus + Grafana | System health dashboards, queue depth, worker throughput |
| Alertmanager + PagerDuty | Threshold-based alerts routed to on-call engineers |
| ELK Stack (Elasticsearch, Logstash, Kibana) | Centralised error logging, full-text search over logs |
| Jaeger / Zipkin | Distributed tracing — trace a single job across all services |
| Datadog APM (optional) | Real-time current-load profiling and anomaly detection |

All workers and services emit structured JSON logs to Logstash and expose `/metrics` to Prometheus.

### 6. Failover & Recovery
| Mechanism | Detail |
|---|---|
| RabbitMQ Mirrored Queues | Broker crash triggers automatic mirror promotion; no messages lost |
| DB Automatic Failover | Patroni elects a new primary within ~30 s; app reconnects via pgBouncer |
| Worker Health Checks | Kubernetes liveness probes restart unhealthy pods automatically |
| Circuit Breaker (Tenacity) | Prevents cascading failures when external sites are down |
| Dead Letter Queue + Retry | Exponential back-off (1 s → 2 s → 4 s…), max 5 retries before DLQ |

### 7. Results & Delivery
- A thin **Results API** exposes job status and download endpoints.
- A **Webhook Dispatcher** notifies client callbacks on job completion.
- An **Export Service** generates CSV/JSON artefacts and delivers them to dashboards, data warehouses, or third-party systems.

---

## Key design decisions

1. **Decoupled via RabbitMQ** — producers and consumers scale independently without code changes.
2. **Stateless workers** — any worker can pick up any task; no sticky sessions required.
3. **Read replica** — offloads analytics from the write path, keeping write latency low.
4. **Separate dead-letter queue** — failed jobs are never silently dropped; they are inspectable and replayable.
5. **Observability as a first-class concern** — health, load, and errors are monitored at every layer with alerting and tracing.
