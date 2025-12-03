# Implementation Plan (pybriscola-game)

## Message Schema Alignment
- Accept commands with `message_type` + `action_id` (`bid`, `call-partner-rank`, `call-partner-suit`, `play`, `reorder`, `sync`).
- Emit `action.result` (ok/error with codes) and authoritative events (`trick.played`, `trick.won`, `phase.change`, `hand.update`, `score.update`).
- Cache results by `action_id` for idempotency.
- Error semantics and codes: `unauthorized`, `join_failed`, `duplicate_connection_handled`, `invalid_turn`, `invalid_card`, `invalid_bid`, `invalid_action`, `forbidden`, `desync`, `game_unavailable`, `routing_failed`; use `invalid_*` for rule/phase violations (recovery: retry/noop) and `desync` when client state mismatches server (recovery: sync).

## Game Server Wiring
- Finish play phase: validate turn/card, update trick, determine winners, update scores, set next player.
- Wire bidding/calling to include partner_rank/suit, trump setting; emit phase changes.
- Implement reorder handling to persist hand order for reconnects and echo via `hand.update`.
- Provide snapshot generator (player vs observer) per phase for join/sync/trick-won/end.
- Add durability (Option 1): after every successful `action.result`, persist full authoritative state to Redis (AOF enabled) keyed by `game:<id>:state`; optionally keep a short recent action log for debugging. On restart, reload state for a game_id, reattach, and emit a fresh `sync` to clients. Apply cleanup (TTL or delete) when a game ends, configurable per env (`GAME_STATE_TTL_SECONDS`, e.g., 1h dev, 12h prod).

## Integration with Web Layer
- Define clean interface for pybriscola-web via Redis channels (`game.<game_id>.actions` / `game.<game_id>.events`); consume actions, emit events/snapshots.
- Trust envelopes signed by web (claims: `game_id`, `player_id`, `role`, action metadata) with `action_id`, `ts`, `version`, `origin`; no need to re-verify client JWTs.
- Ensure observer mode never exposes hands.

## Testing
- Unit tests: trick winner, bidding/calling, play validation, reorder persistence, snapshots.
- Integration: mock websocket bridge covering full lifecycle (create → bid/call → play → trick resolution → end) and reconnect/sync.
- Heartbeats: emit periodic heartbeat (~5s) to `game:<id>:heartbeat` TTL key with TTL ~20s; game service monitors expiry and restarts the worker, reloading state and resuming events/sync.
