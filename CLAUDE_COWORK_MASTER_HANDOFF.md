# CLAUDE_COWORK_MASTER_HANDOFF

## Purpose

This is the single top-level handoff document for Claude COWORK.

It combines:
- project architecture understanding
- general code review findings
- security audit findings
- remediation priorities
- Sage-specific research, audit findings, batching, and acceptance criteria

Use this file as the starting point. Follow links to the detailed Sage documents when implementing Sage-specific fixes.

## Repository Overview

This project is a desktop Chia market-making bot with:
- a desktop shell and web UI
- a Flask API and SSE server
- a central trading loop
- SQLite-backed state
- wallet backends for both Chia and Sage

Primary files:
- [desktop_app.py](./desktop_app.py)
- [api_server.py](./api_server.py)
- [bot_loop.py](./bot_loop.py)
- [database.py](./database.py)
- [wallet.py](./wallet.py)
- [wallet_sage.py](./wallet_sage.py)
- [wallet_chia.py](./wallet_chia.py)
- [chia_node.py](./chia_node.py)

Important runtime characteristics:
- desktop mode runs Flask and UI locally
- API routes directly control bot lifecycle, wallet actions, config updates, logs, backups, and node/service operations
- Sage integration is implemented as an adapter layer in `wallet_sage.py`

## Highest Priority Problems Across The Codebase

### 1. Unauthenticated control API exposed on all interfaces
- Files:
  - [api_server.py](./api_server.py)
- Problem:
  - Flask binds to `0.0.0.0`
  - sensitive routes have no auth
  - remote callers can start/stop the bot, cancel offers, trigger coin prep, control Chia services, and shut down the app
- Priority:
  - Must fix before release

### 2. Config API can persist unsafe or dead settings
- Files:
  - [api_server.py](./api_server.py)
  - [config.py](./config.py)
- Problem:
  - generic config writes can rewrite network endpoint settings
  - some config keys written by the API are not actually consumed by runtime
- Priority:
  - Must fix before release

### 3. Broken or drifting adapter contracts
- Files:
  - [app_bridge.py](./app_bridge.py)
  - [wallet_sage.py](./wallet_sage.py)
  - [wallet_chia.py](./wallet_chia.py)
  - [database.py](./database.py)
- Problem:
  - broken bridge methods point at nonexistent functions
  - duplicate function definitions shadow earlier implementations
  - adapter behavior is inconsistent and fragile
- Priority:
  - Must fix soon

### 4. Polling/status paths perform side effects and expensive work
- Files:
  - [api_server.py](./api_server.py)
- Problem:
  - `/api/status` performs network calls and logs during polling
  - expensive operational endpoints have no rate limiting
- Priority:
  - Must fix soon

### 5. Sage integration has documented mismatches and missing safeguards
- Files:
  - [wallet_sage.py](./wallet_sage.py)
  - [chia_node.py](./chia_node.py)
- Problem:
  - missing explicit Sage lifecycle handling
  - duplicate endpoint helpers override documented behavior
  - offer, signing, readiness, and edge-case handling are incomplete
- Priority:
  - Must fix soon

## General Code Review Findings

### Critical

#### Config update path writes keys the runtime does not actually read
- Files:
  - [api_server.py](./api_server.py)
  - [config.py](./config.py)
- Examples:
  - `REQUOTE_COOLDOWN` vs `REQUOTE_COOLDOWN_SECS`
  - `ARB_THRESHOLD_BPS` vs `ARB_ALERT_THRESHOLD_BPS`
  - `OFFER_EXPIRY_MINUTES` vs `OFFER_EXPIRY_SECS`
- Required outcome:
  - one canonical config schema
  - reject dead or unknown keys

### High

#### `AppBridge` methods reference nonexistent APIs
- File:
  - [app_bridge.py](./app_bridge.py)
- Required outcome:
  - remove broken methods or remap them to real implementations

#### Duplicate definitions silently override earlier behavior
- Files:
  - [wallet_sage.py](./wallet_sage.py)
  - [wallet_chia.py](./wallet_chia.py)
  - [database.py](./database.py)
- Required outcome:
  - one implementation per public function name

#### Notification wiring is broken
- Files:
  - [desktop_app.py](./desktop_app.py)
  - [api_server.py](./api_server.py)
- Required outcome:
  - notifications must consume the actual `EventBus` interface correctly

### Medium

#### `api_server.py` is a monolith with duplicated business logic
- File:
  - [api_server.py](./api_server.py)
- Required outcome:
  - no broad refactor in one go
  - only extract or simplify when needed for a specific fix

#### Exception swallowing hides real failures
- Files:
  - multiple, especially API and desktop paths
- Required outcome:
  - do not add new blanket `except Exception: pass`
  - narrow catches when touching affected code

#### Test coverage is weak and skewed toward manual scripts
- Files:
  - multiple test scripts in repo root
- Required outcome:
  - add targeted unit/regression tests with each batch

## Security Findings

### Must fix before release

#### Bind API to localhost by default and add authentication
- File:
  - [api_server.py](./api_server.py)
- Required outcome:
  - default bind `127.0.0.1`
  - auth for operational routes
  - protection for mutating routes

#### Lock down config writes
- Files:
  - [api_server.py](./api_server.py)
  - [config.py](./config.py)
- Required outcome:
  - do not allow arbitrary HTTP writes to `.env`
  - block remote mutation of endpoint base URLs through generic config routes

#### Fix secret and TLS handling in Sage integration
- Files:
  - [wallet_sage.py](./wallet_sage.py)
  - [wallet_chia.py](./wallet_chia.py)
  - [sage_client_ssl/client.key](./sage_client_ssl/client.key)
  - [sage_client_ssl/client.crt](./sage_client_ssl/client.crt)
- Required outcome:
  - no secret key material stored under the project tree
  - no unverified TLS as the normal trust model

### Should fix soon

#### Protect operational read endpoints and SSE
- File:
  - [api_server.py](./api_server.py)
- Required outcome:
  - auth for logs, backups, wallet status, balances, SSE, and related routes

#### Add rate limiting and abuse protections
- File:
  - [api_server.py](./api_server.py)
- Required outcome:
  - throttle expensive endpoints
  - limit SSE fanout

## Sage-Specific Workstream

Start here for full Sage detail:
- [sage_docs/SAGE_MASTER_HANDOFF_FOR_CLAUDE.md](./sage_docs/SAGE_MASTER_HANDOFF_FOR_CLAUDE.md)

Supporting Sage docs:
- [sage_docs/SAGE_EXECUTIVE_SUMMARY.md](./sage_docs/SAGE_EXECUTIVE_SUMMARY.md)
- [sage_docs/SAGE_V4_MISMATCH_REPORT.md](./sage_docs/SAGE_V4_MISMATCH_REPORT.md)
- [sage_docs/SAGE_V4_PATCH_CHECKLIST.md](./sage_docs/SAGE_V4_PATCH_CHECKLIST.md)
- [sage_docs/SAGE_V4_ACCEPTANCE_CRITERIA.md](./sage_docs/SAGE_V4_ACCEPTANCE_CRITERIA.md)
- [sage_docs/SAGE_V4_REVIEW_RULES.md](./sage_docs/SAGE_V4_REVIEW_RULES.md)

Top Sage issues:
- missing explicit `initialize` lifecycle
- duplicate shadowing definitions for `get_pending_transactions()` and `get_spendable_coin_count()`
- `create_offer()` ignores `validate_only`
- request-only offer fee rule not enforced
- watch-only wallets not blocked from signing
- send paths lack caller-side network/address validation
- readiness logic invents `synced=None` semantics

Recommended first Sage batch:
- Pending and spendable endpoint corrections in [wallet_sage.py](./wallet_sage.py)

## Recommended Overall Implementation Order

### Phase 1: Immediate security boundary
1. Lock API binding down to localhost
2. Add auth/protection for mutating and operational routes
3. Lock down config writes and endpoint mutation

### Phase 2: Small contract fixes
1. Remove duplicate shadowing defs in wallet/database modules
2. Fix `AppBridge`
3. Fix notification wiring
4. Make `/api/status` read-only and low-cost

### Phase 3: Sage batches
1. Pending and spendable endpoint corrections
2. Cancel-offer success semantics
3. Offer creation contract fixes
4. Watch-only signing guardrails
5. Send-path address and network validation
6. Sync/readiness semantics
7. Startup lifecycle
8. Offer-lock reconciliation correctness

### Phase 4: Hardening and cleanup
1. Move secrets/runtime artifacts out of source tree where needed
2. Improve TLS trust handling
3. Add rate limiting and abuse controls
4. Add more regression coverage around config, polling, and adapter contracts

## Constraints For Claude

- Do not do broad refactors.
- Preserve public adapter shape unless clearly wrong.
- Preserve caller compatibility unless proven unnecessary.
- Do not invent Sage semantics.
- Use documented Sage endpoints where available.
- Keep changes batch-scoped.
- Add tests with each batch.
- Do not break non-Sage wallet behavior.
- Do not silently change response shapes used elsewhere in the bot unless a test-backed fix requires it.

## Top Testing Priorities

1. API auth and route protection tests
2. Config allowlist and dead-key rejection tests
3. `AppBridge` contract/parity tests
4. Duplicate-definition regression tests
5. `/api/status` non-mutating behavior tests
6. Sage adapter tests for:
   - pending endpoint usage
   - spendable count endpoint usage
   - `create_offer()` contract
   - watch-only signing guards
   - readiness semantics
   - send-path validation

## What Claude Must Not Accidentally Break

- the basic desktop launch flow
- existing bot lifecycle controls once properly protected
- non-Sage wallet behavior
- normal hot-wallet Sage trading behavior
- response shapes expected by the rest of the bot
- `get_pending_transactions()` semantics relied on by current callers:
  - returns a list
  - empty means no pending transactions

## Suggested Working Style For Claude

- Work one batch at a time.
- Start with the smallest safe batch in any area.
- Add tests before or with each patch.
- After each batch, stop and verify:
  - files changed are only the intended ones
  - public contracts were preserved
  - no new speculative behavior was introduced

Best first batch overall:
- API exposure/auth boundary if release safety is the priority

Best first Sage batch:
- pending and spendable endpoint corrections in `wallet_sage.py`
