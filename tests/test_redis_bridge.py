import json

import pytest

from briscola_service import GameServer
from briscola import deck
from tests.conftest import DummyRedis, extract_payloads


def test_join_sync_snapshot(dummy_redis):
    server = GameServer("TEST01", dummy_redis)
    server.handle_action({"message_type": "join", "game_id": "TEST01", "payload": {"message_type": "join"}, "player_id": 0, "role": "player"})
    payloads = extract_payloads(dummy_redis)
    types = [p["message_type"] for p in payloads]
    assert "action.result" in types
    assert any(p["payload"]["message_type"] == "sync" for p in payloads)
    snapshot_events = [p for p in payloads if p["payload"].get("message_type") == "sync"]
    assert snapshot_events, "Sync snapshot not emitted"
    snap = snapshot_events[0]["payload"]
    assert snap["phase"] in ["bid", "call-partner-rank", "play-first-trick"]


def test_play_card_emits_trick_played(dummy_redis):
    server = GameServer("TEST01", dummy_redis)
    # init
    server.handle_action({"message_type": "join", "game_id": "TEST01", "payload": {"message_type": "join"}, "player_id": 0, "role": "player"})
    # move to play phase
    server.game.state = "play-first-trick"
    server.game.current_player_id = 0
    player0 = server.game.players[0]
    card = player0.hand[0]
    server.handle_action({
        "message_type": "play",
        "game_id": "TEST01",
        "player_id": 0,
        "role": "player",
        "payload": {
            "message_type": "play",
            "card": {"suit": card.suit, "rank": card.rank}
        }
    })
    payloads = extract_payloads(dummy_redis)
    trick_played = [p for p in payloads if p["payload"].get("message_type") == "trick.played"]
    assert trick_played, "trick.played not emitted"
    event = trick_played[0]["payload"]
    assert event["player_id"] == 0
    assert event["card"]["suit"] == card.suit
    assert event["card"]["rank"] == card.rank


def test_reorder_persists_order(dummy_redis):
    server = GameServer("TEST01", dummy_redis)
    server.handle_action({"message_type": "join", "game_id": "TEST01", "payload": {"message_type": "join"}, "player_id": 0, "role": "player"})
    player0 = server.game.players[0]
    # reverse hand order
    new_order = list(reversed([{"suit": c.suit, "rank": c.rank} for c in player0.hand]))
    server.handle_action({
        "message_type": "reorder",
        "game_id": "TEST01",
        "player_id": 0,
        "role": "player",
        "payload": {
            "message_type": "reorder",
            "hand": new_order
        }
    })
    payloads = extract_payloads(dummy_redis)
    hand_updates = [p for p in payloads if p["payload"].get("message_type") == "hand.update"]
    assert hand_updates, "hand.update not emitted"
    updated = hand_updates[0]["payload"]["hand"]
    assert updated[0]["suit"] == new_order[0]["suit"]
    assert updated[0]["rank"] == new_order[0]["rank"]
