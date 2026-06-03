# cde-ranking Compact Map

This reference keeps Megan's wrapper small while preserving routing precision.
Load the delegated cde-ranking skill only after the minimal intake is known.

## High-Token Targets

- `service-onboard`: multi-repo onboarding across spec, batch, DAG, ES/Redis,
  API, and Admin UI. Use only when the request is about creating a new ranking
  service or extending a service across repositories.
- `ranking-data-verify`: Iceberg and ES consistency checks. Use when the user
  asks whether data matches across storage and search layers.
- `feature-crud`: ranking feature lifecycle. Use for new signals, mapping
  updates, score inputs, or schema changes.
- `forme-trino-lookup`: ForMe Iceberg and slot policy diagnosis. Use for
  discount slots, coupon mapping, and feature table questions.
- `forme-redis-lookup`: ForMe Redis payload and slot state. Use for killer card,
  user payload, and item/user slot lookups.

## Delegation Rule

Do not duplicate formulas, SQL, ES DSL, or command syntax in Megan wrappers.
Reference the canonical cde-ranking skill and keep Megan-specific notes limited
to trigger words, safety policy, memory capture, and final reporting style.
