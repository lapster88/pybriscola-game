"""Briscola game service: manages per-game servers and Redis IO."""

import json
import os
import random
import string
import time
import threading
from typing import Dict

import redis
from briscola import deck
from briscola.game import Game, trick_winner

REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
REDIS_PREFIX = 'game'
PROTOCOL_VERSION = os.environ.get('PROTOCOL_VERSION', '1.0.0')
HEARTBEAT_TTL = int(os.environ.get('HEARTBEAT_TTL_SECONDS', 20))
HEARTBEAT_INTERVAL = int(os.environ.get('HEARTBEAT_INTERVAL_SECONDS', 5))
STATE_TTL = int(os.environ.get('GAME_STATE_TTL_SECONDS', 3600))


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """Generate a random game id."""
    return ''.join(random.choice(chars) for _ in range(size))


def now_ms():
    """Current epoch milliseconds."""
    return int(time.time() * 1000)


class GameServer:
    """Per-game engine: consumes actions, publishes events/results, persists snapshots, writes heartbeat."""

    def __init__(self, game_id: str, redis_client: redis.Redis):
        self.game_id = game_id
        self.redis = redis_client
        self.game = Game()
        self.last_heartbeat = 0
        self.initialized = False

    def heartbeat(self):
        now = int(time.time())
        if now - self.last_heartbeat >= HEARTBEAT_INTERVAL:
            key = f"{REDIS_PREFIX}:{self.game_id}:heartbeat"
            self.redis.setex(key, HEARTBEAT_TTL, "alive")
            self.last_heartbeat = now

    def persist_state(self):
        key = f"{REDIS_PREFIX}:{self.game_id}:state"
        snapshot = self.build_snapshot()
        self.redis.set(key, json.dumps(snapshot), ex=STATE_TTL)
        return snapshot

    def build_snapshot(self, requesting_player_id=None, role=None):
        """Construct snapshot dict; include hand for owner unless observer."""
        trick = [
            {"player_id": pid, "card": {"suit": c.suit, "rank": c.rank}}
            for c, pid in self.game.current_trick
        ]
        snapshot = {
            "message_type": "sync",
            "game_id": self.game_id,
            "phase": self.game.state,
            "players": [
                {"player_id": p.id, "name": f"Player {p.id}", "seat": p.id}
                for p in self.game.players
            ],
            "scores": [
                {"player_id": p.id, "points": p.points} for p in self.game.players
            ],
            "current_player_id": self.game.current_player_id,
            "current_leader_id": self.game.current_leader_id,
            "trick": trick,
            "trick_history": [],
            "caller_id": self.game.bid_winner.id if self.game.bid_winner else None,
            "partner_id": self.game.partner.id if self.game.partner else None,
            "partner_rank": self.game.partner_rank,
            "trump_suit": self.game.partner_suit,
            "bids": [{"player_id": p.id, "bid": p.bid} for p in self.game.players],
        }
        if role != "observer" and requesting_player_id is not None:
            hand = [
                {"suit": c.suit, "rank": c.rank, "card_id": card_id(c)}
                for c in self.game.players[requesting_player_id].hand
            ]
            snapshot["hand"] = hand
        return snapshot

    def load_state(self, snapshot: dict):
        """Hydrate game state from snapshot (minimal for restart)."""
        if not snapshot:
            return
        self.game.state = snapshot.get("phase", self.game.state)
        self.game.current_player_id = snapshot.get("current_player_id", self.game.current_player_id)
        self.game.current_leader_id = snapshot.get("current_leader_id", self.game.current_leader_id)
        scores = snapshot.get("scores", [])
        for s in scores:
            pid = s.get("player_id")
            pts = s.get("points", 0)
            if pid is not None and pid < len(self.game.players):
                self.game.players[pid].points = pts
        bids = snapshot.get("bids", [])
        for b in bids:
            pid = b.get("player_id")
            bid_val = b.get("bid", -1)
            if pid is not None and pid < len(self.game.players):
                self.game.players[pid].bid = bid_val
        caller_id = snapshot.get("caller_id")
        if caller_id is not None and caller_id < len(self.game.players):
            self.game.bid_winner = self.game.players[caller_id]
        partner_id = snapshot.get("partner_id")
        if partner_id is not None and partner_id < len(self.game.players):
            self.game.partner = self.game.players[partner_id]
        self.game.partner_rank = snapshot.get("partner_rank")
        self.game.partner_suit = snapshot.get("trump_suit")

    def publish_event(self, payload: dict, action_id=None, player_id=None, role=None):
        envelope = {
            "message_type": payload.get("message_type"),
            "game_id": self.game_id,
            "action_id": action_id or payload.get("action_id"),
            "player_id": player_id,
            "role": role,
            "ts": now_ms(),
            "version": PROTOCOL_VERSION,
            "origin": "game",
            "payload": payload,
        }
        channel = f"{REDIS_PREFIX}.{self.game_id}.events"
        self.redis.publish(channel, json.dumps(envelope))

    def action_result(self, action_id, status, code=None, reason=None, effects=None, recovery=None, player_id=None, role=None):
        payload = {
            "message_type": "action.result",
            "action_id": action_id,
            "status": status,
            "code": code,
            "reason": reason,
            "effects": effects or {},
            "recovery": recovery,
        }
        self.publish_event(payload, action_id=action_id, player_id=player_id, role=role)

    def handle_action(self, envelope: dict):
        self.heartbeat()
        payload = envelope.get("payload", {})
        action_id = envelope.get("action_id") or payload.get("action_id") or id_generator()
        player_id = envelope.get("player_id")
        role = envelope.get("role")
        mtype = payload.get("message_type")

        if not self.initialized:
            self.game.start_game()
            self.game.deal_cards()
            self.initialized = True

        if mtype in ["join", "sync"]:
            snapshot = self.build_snapshot(requesting_player_id=player_id, role=role)
            self.action_result(action_id, "ok", effects={"snapshot": snapshot}, player_id=player_id, role=role)
            self.publish_event(snapshot, action_id=action_id, player_id=player_id, role=role)
            return

        try:
            if mtype == "bid":
                self.handle_bid(action_id, player_id, payload, role)
            elif mtype == "call-partner-rank":
                self.handle_call_rank(action_id, player_id, payload, role)
            elif mtype == "call-partner-suit":
                self.handle_call_suit(action_id, player_id, payload, role)
            elif mtype == "play":
                self.handle_play(action_id, player_id, payload, role)
            elif mtype == "reorder":
                self.handle_reorder(action_id, player_id, payload, role)
            else:
                self.action_result(
                    action_id,
                    "error",
                    code="invalid_action",
                    reason=f"Unknown message_type {mtype}",
                    recovery="noop",
                    player_id=player_id,
                    role=role,
                )
        except Exception as exc:  # broad, but defensive to avoid crashing loop
            self.action_result(
                action_id,
                "error",
                code="invalid_action",
                reason=str(exc),
                recovery="noop",
                player_id=player_id,
                role=role,
            )

    def handle_bid(self, action_id, player_id, payload, role):
        if self.game.state != "bid":
            self.action_result(
                action_id,
                "error",
                code="invalid_action",
                reason="Not in bid phase",
                recovery="noop",
                player_id=player_id,
                role=role,
            )
            return
        bid_val = payload.get("bid")
        state, winner_id, winning_bid = self.game.player_bid(player_id, bid_val)
        self.persist_state()
        effects = {"state": state, "winner_id": winner_id, "winning_bid": winning_bid}
        self.action_result(action_id, "ok", effects=effects, player_id=player_id, role=role)
        self.publish_event(
            {
                "message_type": "phase.change",
                "phase": state,
                "caller_id": winner_id,
            },
            action_id=action_id,
            player_id=player_id,
            role=role,
        )

    def handle_call_rank(self, action_id, player_id, payload, role):
        if self.game.state != "call-partner-rank":
            self.action_result(
                action_id,
                "error",
                code="invalid_action",
                reason="Not in call-partner-rank phase",
                recovery="noop",
                player_id=player_id,
                role=role,
            )
            return
        partner_rank = payload.get("partner_rank")
        state, partner_rank = self.game.call_partner_rank(partner_rank)
        self.persist_state()
        effects = {"state": state, "partner_rank": partner_rank}
        self.action_result(action_id, "ok", effects=effects, player_id=player_id, role=role)
        self.publish_event(
            {"message_type": "phase.change", "phase": state, "partner_rank": partner_rank},
            action_id=action_id,
            player_id=player_id,
            role=role,
        )

    def handle_call_suit(self, action_id, player_id, payload, role):
        if self.game.state != "call-partner-suit":
            self.action_result(
                action_id,
                "error",
                code="invalid_action",
                reason="Not in call-partner-suit phase",
                recovery="noop",
                player_id=player_id,
                role=role,
            )
            return
        partner_suit = payload.get("partner_suit")
        state, partner_suit, partner_id = self.game.call_partner_suit(partner_suit)
        self.persist_state()
        effects = {"state": state, "partner_suit": partner_suit, "partner_id": partner_id}
        self.action_result(action_id, "ok", effects=effects, player_id=player_id, role=role)
        self.publish_event(
            {
                "message_type": "phase.change",
                "phase": state,
                "partner_id": partner_id,
                "partner_rank": self.game.partner_rank,
                "trump_suit": partner_suit,
            },
            action_id=action_id,
            player_id=player_id,
            role=role,
        )
        # trick may have been won inside call_partner_suit
        if self.game.state == "trick-won":
            self.emit_trick_won(action_id, player_id, role)

    def handle_play(self, action_id, player_id, payload, role):
        if self.game.state not in [
            "play-first-trick",
            "play-tricks",
            "trick-won",
            "call-partner-suit",
        ]:
            self.action_result(
                action_id,
                "error",
                code="invalid_action",
                reason="Not in play phase",
                recovery="noop",
                player_id=player_id,
                role=role,
            )
            return
        card_payload = payload.get("card")
        card_obj = card_from_payload(card_payload)
        if card_obj not in self.game.players[player_id].hand:
            self.action_result(
                action_id,
                "error",
                code="invalid_card",
                reason="Card not in hand",
                recovery="retry",
                player_id=player_id,
                role=role,
            )
            return
        state, _, _ = self.game.play_card(player_id, card_obj)
        self.persist_state()
        trick_event = {
            "message_type": "trick.played",
            "game_id": self.game_id,
            "player_id": player_id,
            "card": {"suit": card_obj.suit, "rank": card_obj.rank},
            "trick": [
                {"player_id": pid, "card": {"suit": c.suit, "rank": c.rank}}
                for c, pid in self.game.current_trick
            ],
            "current_player_id": self.game.current_player_id,
        }
        self.publish_event(trick_event, action_id=action_id, player_id=player_id, role=role)
        if state == "trick-won":
            self.emit_trick_won(action_id, player_id, role)
        self.action_result(action_id, "ok", effects={"state": state}, player_id=player_id, role=role)

    def emit_trick_won(self, action_id, player_id, role):
        trick_cards = self.game.current_trick
        _, winner_id = trick_winner(trick_cards, self.game.partner_suit)
        points = sum(c.value for c, _ in trick_cards)
        scores = [{"player_id": p.id, "points": p.points} for p in self.game.players]
        event = {
            "message_type": "trick.won",
            "game_id": self.game_id,
            "winner_id": winner_id,
            "points": points,
            "trick_cards": [
                {"player_id": pid, "card": {"suit": c.suit, "rank": c.rank}}
                for c, pid in trick_cards
            ],
            "scores": scores,
            "current_player_id": self.game.current_player_id,
        }
        self.publish_event(event, action_id=action_id, player_id=player_id, role=role)
        self.persist_state()

    def handle_reorder(self, action_id, player_id, payload, role):
        new_order = payload.get("hand", [])
        player = self.game.players[player_id]
        ordered = []
        # Build card objects based on provided order
        for entry in new_order:
            if isinstance(entry, dict):
                c = card_from_payload(entry)
            else:
                c = card_from_id(entry)
            if c in player.hand and c not in ordered:
                ordered.append(c)
        # append any remaining cards not specified
        for c in player.hand:
            if c not in ordered:
                ordered.append(c)
        player.hand = ordered
        self.persist_state()
        hand_event = {
            "message_type": "hand.update",
            "game_id": self.game_id,
            "player_id": player_id,
            "hand": [
                {"suit": c.suit, "rank": c.rank, "card_id": card_id(c)}
                for c in ordered
            ],
        }
        self.publish_event(hand_event, action_id=action_id, player_id=player_id, role=role)
        self.action_result(
            action_id,
            "ok",
            effects={"hand": hand_event["hand"]},
            player_id=player_id,
            role=role,
        )


class BriscolaService:
    """Creates/manages per-game servers; per-game servers handle Redis IO themselves."""

    def __init__(self):
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self.servers: Dict[str, GameServer] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.stop_event = threading.Event()

    def ensure_server(self, game_id: str):
        server = GameServer(game_id, self.redis)
        # Attempt to load persisted state
        snap_key = f"{REDIS_PREFIX}:{game_id}:state"
        try:
            saved = self.redis.get(snap_key)
            if saved:
                server.load_state(json.loads(saved))
        except Exception as e:
            print(f"Failed to load snapshot for {game_id}: {e}")
        thread = threading.Thread(target=self.server_loop, args=(server,), daemon=True)
        self.servers[game_id] = server
        self.threads[game_id] = thread
        thread.start()

    def server_loop(self, server: GameServer):
        pubsub = self.redis.pubsub()
        channel = f"{REDIS_PREFIX}.{server.game_id}.actions"
        pubsub.subscribe(channel)
        print(f"Game server {server.game_id} listening on {channel}")
        for msg in pubsub.listen():
            if msg["type"] != "message":
                continue
            try:
                envelope = json.loads(msg["data"])
                server.handle_action(envelope)
            except Exception as exc:  # defensive
                print(f"Error handling action for {server.game_id}: {exc}")

    def run(self):
        action_thread = threading.Thread(target=self.monitor_actions, daemon=True)
        heartbeat_thread = threading.Thread(target=self.monitor_heartbeats, daemon=True)
        action_thread.start()
        heartbeat_thread.start()
        action_thread.join()

    def monitor_actions(self):
        pubsub = self.redis.pubsub()
        pubsub.psubscribe(f"{REDIS_PREFIX}.*.actions")
        print("Game service monitoring pattern game.*.actions")
        for msg in pubsub.listen():
            if self.stop_event.is_set():
                break
            if msg["type"] not in ("message", "pmessage"):
                continue
            try:
                envelope = json.loads(msg["data"])
                game_id = envelope.get("game_id")
                if not game_id:
                    continue
                first_time = game_id not in self.servers
                self.ensure_server(game_id)
                if first_time:
                    # re-publish the first message so the new server can consume it
                    channel = f"{REDIS_PREFIX}.{game_id}.actions"
                    self.redis.publish(channel, json.dumps(envelope))
            except Exception as exc:  # defensive
                print(f"Error monitoring actions: {exc}")

    def monitor_heartbeats(self, once: bool = False):
        """Monitor heartbeat keys and thread liveness; restart servers when needed."""
        while not self.stop_event.is_set():
            for game_id in list(self.servers.keys()):
                key = f"{REDIS_PREFIX}:{game_id}:heartbeat"
                ttl = self.redis.ttl(key)
                thread_alive = self.threads.get(game_id) and self.threads[game_id].is_alive()
                if (ttl == -2 or (ttl is not None and ttl <= 0)) or not thread_alive:
                    print(f"Heartbeat or thread failed for {game_id}, restarting server")
                    self.ensure_server(game_id)
            if once:
                break
            time.sleep(HEARTBEAT_INTERVAL)
def card_id(card: deck.Card):
    suit_index = deck.suits.index(card.suit)
    return suit_index * 10 + (card.rank - 1)


def card_from_id(card_id_val: int) -> deck.Card:
    suit_index = card_id_val // 10
    rank = (card_id_val % 10) + 1
    return deck.Card(deck.suits[suit_index], rank)


def card_from_payload(data: dict) -> deck.Card:
    return deck.Card(data["suit"], int(data["rank"]))


if __name__ == "__main__":
    BriscolaService().run()
