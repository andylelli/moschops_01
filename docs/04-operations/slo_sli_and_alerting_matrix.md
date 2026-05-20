# SLO, SLI, and Alerting Matrix

Version: 1.0  
Last updated: 2026-05-20

## Purpose
Define the operational measurements and alerts that must exist before controlled production use.

## SLIs
| SLI | Description | Measurement source |
|---|---|---|
| API availability | Successful backend request rate | Health endpoint and API logs |
| DB write health | Successful persistence rate | Database write logs |
| EA connectivity | EA-to-backend communication success | EA telemetry |
| Model-serving health | Successful inference availability | Model runtime logs |
| Risk-event rate | Count of vetoes and kill-switch events | Risk engine logs |

## SLO Targets
- API availability: 99.5% or better for operational windows.
- DB write health: 99.5% or better.
- EA connectivity: 99.0% or better.
- Model-serving health: 99.0% or better.

## Alert Rules
- Backend unreachable for more than one polling interval.
- Database write failures.
- Model-serving failures on mandatory AI strategies.
- Kill-switch activation.
- Repeated stale data beyond the freshness threshold.

## Operator Actions
- Acknowledge critical alerts.
- Follow the relevant runbook.
- Record resolution and follow-up actions.
