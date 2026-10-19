{{ config(materialized='table') }}
-- One canonical order-level serving model; aggregates must retain this grain.
SELECT * FROM {{ ref('int_orders_enriched') }}
