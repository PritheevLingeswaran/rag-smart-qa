# Security And Monitoring

## Security posture in this repo

- Structured error responses avoid leaking raw tracebacks to clients.
- Strict grounding and refusal logic reduce unsupported answer risk.
- API key authentication is available through `x-api-key` when `auth.enabled=true`.
- Header-based user identity is still supported for local/demo reviewer flows.
- In-memory rate limiting protects API routes per IP or user/IP key.
- CORS is driven from configured origins instead of unconditional wildcard defaults.
- Health/readiness checks make startup failures explicit instead of silent.

## Failure handling

- Empty retrieval results produce grounded refusals instead of fabricated answers.
- Whitespace-only queries and invalid payloads return structured `422` validation responses.
- Retrieval and generation stages have request-scoped timeout guards with degraded fallback responses.
- Citation persistence failures are logged and downgraded instead of crashing the request.
- Downstream retrieval/generation failures are counted in Prometheus and logged with request IDs.

## Monitoring

The repository now exposes production-style operational signals:

- Request IDs and correlation IDs on every HTTP response.
- Structured JSON logs with request context.
- Prometheus metrics endpoints at `/metrics` and `/api/v1/metrics`.

Tracked metrics include:

- request count
- HTTP latency
- retrieval latency
- generation latency
- retrieval score diagnostics
- request-stage errors
- refusals
- fallback/degraded responses
- auth failures
- rate-limit rejections
- grounded vs non-grounded answers
- token usage
- cost usage when available

## Production hardening still recommended

- Use a secrets manager instead of long-lived `.env` files.
- Replace local storage and SQLite if the deployment requires stronger durability or tenancy guarantees.
- Add stronger prompt-injection and content-scanning defenses around hostile uploads.
- Move from in-memory rate limiting to a shared store if you need multi-instance enforcement.

## What is intentionally not claimed

- Full distributed tracing
- Managed SIEM integration
- Secret rotation workflows
- Tenant-isolated security guarantees
