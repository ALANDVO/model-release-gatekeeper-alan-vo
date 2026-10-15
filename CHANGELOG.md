# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-15

### Added
- Candidate bundle export/import for environment portability: export complete candidate records (evaluations, approvals, manifests) as signed JSON bundles and import them into new environments with automatic ID remapping and conflict resolution
- New API endpoints: `GET /api/candidates/{id}/bundle` (viewer+) and `POST /api/candidates/import` (analyst+).
- BundleManager UI component integrated into CandidateDetail for one-click export/download and paste-to-import workflows.
- Backend test coverage for bundle round-trip including audit trail verification (BUNDLE_EXPORTED, BUNDLE_IMPORTED actions).

## [1.0.0] - 2026-10-08

### Added
- Initial production release of Model Release Gatekeeper.
- Substantive MLOps policy evaluation engine evaluating candidate models against multi-metric threshold suites (accuracy, latency p95/p99, hallucination rate, toxicity score, demographic parity).
- Multi-stakeholder review and cryptographic approval signing workflow with role-based sign-offs (ML Engineer, Safety Lead, Release Manager).
- Verifiable, tamper-evident release manifest export generating canonical SHA-256 digests and lineage manifests.
- Multi-provider LLM advisory engine supporting OpenAI-compatible, Anthropic, Gemini, and Ollama with error redaction and deterministic offline baseline.
- SPA PKCE client with in-memory token storage, Bearer-only backend API, Keycloak OIDC integration, and explicit local demo mode refused in production.
- Full React 19 + TypeScript + Vite frontend dashboard with interactive workflows, metrics charts, policy configuration, approval signatures, and manifest verification.
- Comprehensive test suites crossing real HTTP boundaries, OIDC state/PKCE rejection, cryptographic hashing, and mock LLM provider adapters.
- Docker containerization and Compose setup with Keycloak realm import and persistent volumes.