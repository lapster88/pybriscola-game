# AGENTS.md

Notes for automation/agent work in this repo:

- Add and run tests as you implement features (use pytest). Cover action handling, event emission, state persistence, and heartbeat logic; mock Redis where needed.
- Redis defaults: `REDIS_URL=redis://redis:6379/0`, protocol version `1.0.0`, heartbeat interval/TTL and `GAME_STATE_TTL_SECONDS` are env-configurable.
- Message contracts and flows are in `../pybriscola-web/docs/actions_events.md` and `../pybriscola-web/docs/architecture.md`; keep implementations aligned.
