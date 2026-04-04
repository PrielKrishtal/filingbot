# FilingBot

> Event-driven SEC insider trading intelligence pipeline with AI classification and on-demand RAG Q&A.

---

## What It Does

When a corporate insider (CEO, CFO, etc.) buys or sells stock, they must file a **Form 4** with the SEC within two business days. These filings are public — but buried in thousands of XML documents mixed with routine noise.

FilingBot automates the entire workflow:
1. **Polls** SEC EDGAR every 5 minutes for new Form 4 filings
2. **Classifies** each transaction with an LLM (genuine purchase vs. routine compensation noise)
3. **Enriches** high-value signals by downloading and RAG-indexing the company's latest 10-Q
4. **Alerts** users via Telegram with an AI summary + conversational Q&A over the financial report

---

## Architecture

```
[APScheduler] → edgar_poller → Redis:filing.raw
    → [Classification Worker] → Redis:filing.classified
    → [Enrichment Worker]     → Redis:filing.enriched
    → [Notification Worker]   → Telegram alert
    → [Telegram Bot]          ↔ RAG Q&A over ChromaDB
```

All stages are independent Docker containers communicating through **Redis Streams** with consumer groups and XACK — no message is ever silently dropped.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI (async) |
| Scheduler | APScheduler |
| Message Bus | Redis Streams (consumer groups + XACK) |
| Database | PostgreSQL + SQLAlchemy async + Alembic |
| LLM | Groq API — Llama 3.3 70B |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, local) |
| Vector DB | ChromaDB (one collection per company ticker) |
| Telegram | python-telegram-bot (async) |
| XML Parsing | lxml / XPath |
| PDF Parsing | PyMuPDF |
| Containers | Docker + Docker Compose |
| Testing | pytest + pytest-asyncio |
| Linting | ruff |
| CI | GitHub Actions |

---

## Key Engineering Decisions

- **Redis Streams** with consumer groups for at-least-once delivery — not Celery, not RabbitMQ
- **Dead-letter stream** (`filing.dead_letter`) for messages that fail after 3 retries
- **Idempotent ingestion** via `accession_number` unique constraint in PostgreSQL
- **Pipeline FSM**: `INGESTED → CLASSIFIED → ENRICHED → NOTIFIED → DONE` tracked per filing in DB
- **Pydantic validation at every boundary**: XML → model, LLM → result, Redis → worker
- **One ChromaDB collection per company ticker+period** — not a single global collection
- **Structured JSON logging** with `correlation_id = accession_number` across all workers
- **SEC EDGAR rate limit**: 10 req/s enforced via `asyncio.Semaphore`

---

## Project Structure

```
filingbot/
├── docker-compose.yml
├── core/                      # Common code imported by all services
│   ├── models/                # Pydantic: InsiderFiling, ClassificationResult, enums
│   ├── database/              # SQLAlchemy ORM models + async session + Alembic
│   ├── redis_client.py        # Stream helpers: publish, consume, ack, dead-letter
│   ├── config.py              # pydantic-settings + .env
│   └── logging_config.py      # Structured JSON logger with correlation_id
├── ingestion/                 # FastAPI + APScheduler + EDGAR poller
├── workers/
│   ├── classification/        # Groq prompt + Pydantic validation
│   ├── enrichment/            # 10-Q download + chunk + embed + ChromaDB
│   └── notification/          # Alert formatting + Telegram send
├── telegram_bot/              # Commands + RAG session handler
├── tests/
└── docs/FilingBot_TDD.pdf
```

---



*Portfolio project by Priel Krishtal — April 2026*