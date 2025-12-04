import json

from briscola_service import BriscolaService
from tests.conftest import DummyRedis, DummyPubSub


def test_service_restarts_on_missing_heartbeat(monkeypatch):
    dummy = DummyRedis()

    def pubsub(self):
        return DummyPubSub(self)

    dummy.pubsub = pubsub.__get__(dummy, DummyRedis)
    service = BriscolaService()
    service.redis = dummy

    # Seed a server
    service.ensure_server("ABC123")
    # Simulate expired heartbeat
    dummy.ttl_store[f"game:ABC123:heartbeat"] = -2
    # Kill thread
    #service.threads["ABC123"] = DummyThread(False)

    service.monitor_heartbeats(once=True)
    assert "ABC123" in service.threads
    # Thread created (may be daemon running server_loop); ensure object exists
    assert service.threads["ABC123"] is not None


def test_service_loads_snapshot_on_restart(monkeypatch):
    dummy = DummyRedis()
    snap = {"phase": "play-tricks", "scores": [{"player_id": 0, "points": 5}]}
    dummy.store["game:XYZ789:state"] = json.dumps(snap)
    service = BriscolaService()
    service.redis = dummy
    service.ensure_server("XYZ789")
    assert service.servers["XYZ789"].game.state == "play-tricks"
    assert service.servers["XYZ789"].game.players[0].points == 5


class DummyThread:
    def __init__(self, alive=True):
        self._alive = alive
        self.started = False

    def is_alive(self):
        return self._alive

    def start(self):
        self.started = True
