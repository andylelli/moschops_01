# Security and Access Control

Version: 1.0  
Last updated: 2026-05-20

## Purpose
Define the minimum security and access expectations for the trading platform.

## Access Model
- Separate roles for product, backend, ML, ops, and platform administration.
- Least privilege for all service identities.
- No direct production write access from the UI.

## Secret Handling
- Store secrets outside source control.
- Rotate credentials by environment.
- Do not expose secret material in logs or client payloads.

## Environment Boundaries
- Separate dev, demo, pilot, and live environments.
- Promotion between environments requires explicit approval and validation.
- Live systems must fail closed on auth or integrity errors.

## Threat Model Baseline
- Unauthorized API access
- Credential leakage
- Tampered model artifacts
- Unsafe operator actions
- Data exfiltration from logs or dashboard payloads
