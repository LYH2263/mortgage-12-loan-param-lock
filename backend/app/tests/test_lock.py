import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="mortgage-test-")
os.environ["DATA_DIR"] = _tmp

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import DB_PATH


@pytest.fixture(scope="module")
def client():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    with TestClient(app) as c:
        yield c


def test_list_has_unlocked_seed(client):
    items = client.get("/api/loans").json()["items"]
    assert len(items) >= 2
    assert all(l["locked"] is False for l in items)


def test_update_while_unlocked_takes_effect(client):
    lid = client.get("/api/loans").json()["items"][0]["id"]
    r = client.patch(f"/api/loans/{lid}", json={"principal": 900000, "annual_rate": 3.1, "months": 240})
    assert r.status_code == 200
    body = r.json()
    assert body["principal"] == 900000
    assert body["annual_rate"] == 3.1
    assert body["months"] == 240
    assert body["locked"] is False
    # 立即影响后续测算：以档案参数测算，月供随新参数变化
    sch = client.post("/api/schedule", json={
        "principal": body["principal"], "annual_rate": body["annual_rate"],
        "months": body["months"], "loan_id": lid, "persist": False,
    }).json()
    assert sch["locked"] is False
    assert sch["row_count"] == 240


def test_lock_toggle_roundtrip_and_no_history(client):
    lid = client.get("/api/loans").json()["items"][0]["id"]
    before = client.get("/api/history").json()["items"]
    r = client.post(f"/api/loans/{lid}/lock", json={"locked": True})
    assert r.status_code == 200 and r.json()["locked"] is True
    assert client.get(f"/api/loans/{lid}").json()["locked"] is True
    r = client.post(f"/api/loans/{lid}/lock", json={"locked": False})
    assert r.status_code == 200 and r.json()["locked"] is False
    after = client.get("/api/history").json()["items"]
    assert before == after  # 锁定/解锁不改写历史


def test_locked_rejects_param_change_with_named_fields(client):
    items = client.get("/api/loans").json()["items"]
    lid = items[1]["id"]
    client.post(f"/api/loans/{lid}/lock", json={"locked": True})
    original = client.get(f"/api/loans/{lid}").json()

    r = client.patch(f"/api/loans/{lid}", json={"principal": 500000, "annual_rate": 1.0, "months": 120})
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["locked"] is True
    assert detail["loan_id"] == lid
    assert detail["loan_name"] == original["name"]
    assert detail["read_only_fields"] == ["principal", "annual_rate", "months"]
    msg = detail["message"]
    assert str(lid) in msg and original["name"] in msg
    for f in ("principal", "annual_rate", "months"):
        assert f in msg

    # 单字段修改也须点名对应只读字段
    r = client.patch(f"/api/loans/{lid}", json={"annual_rate": 9.9})
    assert r.status_code == 409
    assert r.json()["detail"]["read_only_fields"] == ["annual_rate"]

    # 值确实未变
    unchanged = client.get(f"/api/loans/{lid}").json()
    assert unchanged["principal"] == original["principal"]
    assert unchanged["annual_rate"] == original["annual_rate"]
    assert unchanged["months"] == original["months"]


def test_locked_allows_readonly_calc_and_persist(client):
    lid = client.get("/api/loans").json()["items"][1]["id"]
    # 上一用例已锁定；显式再锁一次确保前置
    client.post(f"/api/loans/{lid}/lock", json={"locked": True})
    before = len(client.get("/api/history").json()["items"])

    r = client.post("/api/schedule", json={
        "principal": 800000, "annual_rate": 6.8, "months": 240,
        "loan_id": lid, "persist": True,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["locked"] is True
    assert body["run_id"] is not None
    after = client.get("/api/history").json()["items"]
    assert len(after) == before + 1
    assert after[0]["loan_id"] == lid


def test_unlocked_restores_update(client):
    lid = client.get("/api/loans").json()["items"][1]["id"]
    client.post(f"/api/loans/{lid}/lock", json={"locked": False})
    r = client.patch(f"/api/loans/{lid}", json={"months": 300})
    assert r.status_code == 200 and r.json()["months"] == 300


def test_unknown_loan_404(client):
    assert client.get("/api/loans/9999").status_code == 404
    assert client.patch("/api/loans/9999", json={"months": 12}).status_code == 404
    assert client.post("/api/loans/9999/lock", json={"locked": True}).status_code == 404
