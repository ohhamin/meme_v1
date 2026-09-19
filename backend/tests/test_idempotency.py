import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from backend.app.services.idempotency import IdempotencyStore


def make_store(tmp_path):
    store = IdempotencyStore()
    store.path = tmp_path / "idempotency.json"
    store.config.idempotency_retention_days = 30
    return store


def test_idempotency_remember_blocks_duplicate(tmp_path):
    store = make_store(tmp_path)
    store.remember("request-1", "order-1")

    with pytest.raises(HTTPException) as exc:
        store.ensure_new("request-1")

    assert exc.value.status_code == 409


def test_idempotency_prunes_expired_entries(tmp_path):
    store = make_store(tmp_path)
    tz = ZoneInfo(store.config.app_timezone)
    old = datetime.now(tz) - timedelta(days=31)
    recent = datetime.now(tz) - timedelta(days=1)

    store.path.write_text(
        json.dumps(
            {
                "old": {
                    "order_id": "order-old",
                    "created_at": old.isoformat(),
                },
                "recent": {
                    "order_id": "order-recent",
                    "created_at": recent.isoformat(),
                },
            }
        ),
        encoding="utf-8",
    )

    assert store.prune() == 1
    data = json.loads(store.path.read_text(encoding="utf-8"))
    assert "old" not in data
    assert "recent" in data


def test_legacy_idempotency_format_is_migrated_and_retained(tmp_path):
    store = make_store(tmp_path)
    store.path.write_text(
        '{"legacy":"order-legacy"}',
        encoding="utf-8",
    )

    with pytest.raises(HTTPException):
        store.ensure_new("legacy")

    data = json.loads(store.path.read_text(encoding="utf-8"))
    assert data["legacy"]["order_id"] == "order-legacy"
    assert data["legacy"]["created_at"]
