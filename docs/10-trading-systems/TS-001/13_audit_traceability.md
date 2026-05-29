# 13 Audit and Traceability

System ID: TS-001
Version: 1.0
Last updated: 2026-05-27

## Required IDs
1. decisionId
2. signalId
3. tradeId
4. modelVersionId
5. featureSchemaVersion
6. runManifestId

## Evidence links
1. Strategy overview: [README.md](README.md)
2. Validation protocol: [06_validation_protocol.md](06_validation_protocol.md)
3. Promotion gates: [08_promotion_gates.md](08_promotion_gates.md)
4. Experiment log: [11_experiment_log.md](11_experiment_log.md)
5. Historical run evidence: [../../09-training-runs/runs/2026-05-27_19-43-historical-10y-2y/RUN_REPORT.md](../../09-training-runs/runs/2026-05-27_19-43-historical-10y-2y/RUN_REPORT.md)

## Traceability matrix
| Requirement | Evidence artifact | Verified by | Date | Status |
|---|---|---|---|---|
| Deterministic strategy behavior | 01_strategy_spec.md | Pending | 2026-05-27 | In progress |
| No-bending validation policy | 06_validation_protocol.md | Pending | 2026-05-27 | In progress |
| Promotion gate governance | 08_promotion_gates.md | Pending | 2026-05-27 | In progress |
| Incident readiness | 10_incident_runbook.md | Pending | 2026-05-27 | In progress |
| Run evidence retained | 11_experiment_log.md + run report link | Pending | 2026-05-27 | In progress |

## Retention and integrity
1. Store run artifacts under versioned run folders.
2. Preserve historical failures and rejected runs.
3. Maintain immutable references to approved run evidence.
