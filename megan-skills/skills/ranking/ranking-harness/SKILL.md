---
name: ranking-harness
description: Token-light router for ranking work. Delegates Gift/ForMe/Talkstore ranking tasks to cde-ranking-skills and cde-skills without loading long procedures first.
---

# Ranking Harness

Use this skill for ranking questions when the exact domain workflow is not yet
clear. It is a router, not the source of ranking formulas or operational
commands.

## Routing

- New ranking service onboarding: delegate to `service-onboard`.
- Feature, signal, ES mapping, or weight changes: delegate to `feature-crud`.
- Iceberg to ES consistency: delegate to `ranking-data-verify`.
- Product score or feature lookup: delegate to `ranking-lookup`.
- Score formula drilldown: delegate to `score-drilldown`.
- ForMe Iceberg data or slot debugging: delegate to `forme-trino-lookup`.
- ForMe Redis, killer card, or user payload: delegate to `forme-redis-lookup`.
- Gift promotion builder index checks: delegate to `gift-promotion-builder`.
- Gift product missing CS: delegate to `gift-ranking-cs`.

## Minimal Intake

Before loading a delegated skill, identify:

- service: gift, forme, talkstore, brand, lux, or unknown
- phase/environment: dev, stage, prod, or unknown
- entity id: product id, user id, slot id, category id, or none
- layer: Airflow, Spark/Iceberg, ES, Redis, API, Admin UI, or unknown

## Memory

When a conclusion should survive the current session, add it to the session
note's `## Ontology Seeds` section with entities, tools, decisions, and todos.

See `references/cde-ranking-compact.md` for a compact map of the larger
cde-ranking wrappers.
