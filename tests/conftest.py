import json
import pytest


class DummyRedis:
    """In-memory stub for Redis used in unit tests."""

    def __init__(self):
        self.published = []
        self.store = {}
        self.ttl_store = {}
        self.pubsub_obj = DummyPubSub(self)

    def publish(self, channel, data):
        self.published.append((channel, data))

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttl_store[key] = ttl

    def set(self, key, value, ex=None):
        self.store[key] = value
        if ex:
            self.ttl_store[key] = ex

    def get(self, key):
        return self.store.get(key)

    def ttl(self, key):
        return self.ttl_store.get(key, -2 if key not in self.ttl_store else 0)

    def pubsub(self):
        return self.pubsub_obj


def extract_payloads(dummy: DummyRedis):
    return [json.loads(data) for _, data in dummy.published]


class DummyPubSub:
    def __init__(self, parent):
        self.parent = parent
        self.channels = set()
        self.messages = []
        self.patterns = set()

    def subscribe(self, channel):
        self.channels.add(channel)

    def psubscribe(self, pattern):
        self.patterns.add(pattern)

    def listen(self):
        while self.messages:
            yield self.messages.pop(0)

    def push_message(self, channel, data, pmessage=False):
        msg_type = "pmessage" if pmessage else "message"
        self.messages.append({"type": msg_type, "data": data, "channel": channel})


@pytest.fixture
def dummy_redis():
    return DummyRedis()
