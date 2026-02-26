# Production Audit & Readiness Roadmap

This document anchors the Admin Audit Logs feature to enterprise production recommendations.

## 1) Dev/Test/Prod environments and CI/CD
- Added `APP_ENV` and audit-related environment configuration in `.env.example`.
- Added GitHub Actions pipeline in `.github/workflows/ci.yml` for automated test execution.
- Recommended next step: add a `deploy-staging` and `deploy-prod` workflow using protected environments and manual approval gates.

## 2) Modular services/functions
- Audit logic is isolated into `services/audit_service.py`.
- API boundary is isolated in `api/audit.py`.
- Data model is isolated in `models/audit_log.py`.

## 3) Enterprise reference generation
- Audit references follow normalized format: `AUD-YYYYMMDD-XXXXXXXX`.
- Request correlation uses `X-Request-ID` response headers for traceability.

## 4) Automated testing and monitoring
- Automated test coverage added for audit service reference generation and level normalization.
- Monitoring baseline implemented using persistent request audit logs with filters.
- Recommended next step: push logs to central sink (Azure Monitor/ELK) and add alerts on repeated 4xx/5xx spikes.

## 5) Governance, documentation and code reviews
- Added PR template with explicit production-impact and observability checks.
- This roadmap document formalizes expected controls for future changes.

## 6) Medium-term re-engineering plan
- Phase 1 (now): route-level audit logs + tab visibility.
- Phase 2 (next): domain event auditing (bookings, manifests, incidents) with explicit event contracts.
- Phase 3 (later): split domain modules into bounded services and move to event-driven processing where needed.

## 7) Secret/config management
- Configuration is environment-driven and no secrets are hardcoded in audit modules.
- Recommended next step: move all production secrets to Azure Key Vault and inject at runtime.
