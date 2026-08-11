# E-Commerce Data Engineering Pipeline

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Prefect](https://img.shields.io/badge/Prefect-3.8-purple)
![dbt](https://img.shields.io/badge/dbt--core-latest-orange)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-red)

**Full-stack data engineering pipeline** — from API ingestion to business dashboard.

## Architecture

```
Open-Meteo API ──┐
CoinGecko API ───┼── Prefect Orchestrator ──► SQLite Data Warehouse ──► dbt Transform ──► Streamlit Dashboard
E-Com Simulator ─┘         │                         │                       │                    │
                     [Extract]                  [Load]                [Transform]           [Serve]
```

## Star Schema (7 tables)

| Table | Type | Records | Description |
|-------|------|---------|-------------|
| `dim_date` | Dimension | 3,653 | 10-year calendar (2023-2032) |
| `dim_city` | Dimension | 5 | US cities with coordinates |
| `dim_product` | Dimension | 50 | Electronics across 5 categories |
| `dim_customer` | Dimension | 500 | Customers with loyalty tiers |
| `dim_weather` | Dimension | — | Daily weather by city |
| `dim_crypto` | Dimension | — | BTC/ETH price snapshots |
| `fact_orders` | Fact | 155,000+ | Order line items |

## Tech Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Orchestration | **Prefect 3.x** | Task scheduling, retries, monitoring |
| Database | **SQLite + SQLAlchemy** | Data warehouse (swap to PostgreSQL via env var) |
| Transformation | **dbt-core + dbt-sqlite** | staging → intermediate → marts |
| Extraction | **Requests + Pandas** | API clients + data generation |
| Dashboard | **Streamlit + Plotly** | 5-page interactive analytics |
| Testing | **pytest + dbt tests** | Data quality validation |

## Project Structure

```
etl_pipeline_v2/
├── config/                 # Settings, DB connection
├── src/
│   ├── extract/            # API clients + data generator
│   ├── load/               # Staging + warehouse loaders
│   └── warehouse/          # ORM models + DDL
├── orchestration/
│   └── flows/              # Prefect flows (weather, crypto, orders, full pipeline)
├── dbt_project/
│   └── models/
│       ├── staging/        # 5 models (1:1 with source)
│       ├── intermediate/   # 3 models (joins + aggregations)
│       └── marts/          # 4 models (business-ready)
├── dashboard/
│   ├── app.py              # Main entry
│   └── pages/              # 5 interactive pages
├── seed_data.py            # Initialize dim_date + dim_city
└── requirements.txt
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database + seed data
python seed_data.py

# 3. Generate e-commerce data + load to warehouse
python -m src.extract.transaction_generator
python -m src.load.staging_to_warehouse

# 4. (Optional) Fetch real weather data
python -m src.extract.weather_api

# 5. Run full ETL pipeline
python -m orchestration.flows.run_full_pipeline

# 6. Launch dashboard
streamlit run dashboard/app.py
```

## dbt (Optional — requires dbt-sqlite)

```bash
cd dbt_project
dbt debug      # Verify connection
dbt run        # Build all models
dbt test       # Run data tests
dbt docs generate && dbt docs serve  # View documentation
```

## Key Features

- **2 real APIs** (Open-Meteo weather + CoinGecko crypto) — no API keys needed
- **Realistic e-commerce simulation** — seasonal patterns, weekend effects, payment mix
- **Full dbt pipeline** — staging → intermediate → marts with tests
- **Prefect orchestration** — retries, logging, task dependency management
- **RFM customer segmentation** — Champions, Loyal, Potential, At Risk, Lost
- **Weather impact analysis** — correlation of weather conditions with sales
- **Pipeline health monitoring** — data quality checks, freshness metrics

## Switching to PostgreSQL

```bash
# Set environment variable
export DATABASE_URL=postgresql://user:pass@localhost:5432/warehouse

# Install driver
pip install psycopg2-binary

# Change dbt profile to use postgres adapter
```

Everything else works the same — SQLAlchemy abstracts the database layer.

## Comparison

| | Old etl_pipeline | This Project |
|---|---|---|
| Code | 1 file, 205 lines | ~45 files, modular |
| Data | 1 web scrape | 2 APIs + generator |
| DB | 1 flat table | 7-table star schema |
| Transform | Pandas inline | dbt 3-layer |
| Schedule | Manual | Prefect automated |
| Dashboard | Static HTML | Streamlit interactive |
| Tests | None | pytest + dbt tests |
