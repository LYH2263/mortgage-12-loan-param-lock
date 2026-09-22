import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATA_DIR"] = _tmp

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _new_loan(client, name="测试档案", principal=500000, rate=4.0, months=240):
    # 直接通过仓储建档，避免引入额外接口
    from app.db import connect
    conn = connect()
    cur = conn.execute(
        "INSERT INTO loans(name,principal,annual_rate,months,locked) VALUES (?,?,?,?,0)",
        (name, principal, rate, months),
    )
    conn.commit()
    lid = int(cur.lastrowid)
    conn.close()
    return lid


def test_loan_view_carries_locked_flag(client):
    lid = _new_loan(client)
    row = client.get(f"/api/loans/{lid}").json()
    assert row["locked"] is False
    items = client.get("/api/loans").json()["items"]
    assert any(x["id"] == lid and x["locked"] is False for x in items)


def test_unlocked_update_takes_effect_immediately(client):
    lid = _new_loan(client, name="可改档案", principal=500000, rate=4.0, months=240)
    before = client.post("/api/schedule", json={
        "principal": 500000, "annual_rate": 4.0, "months": 240,
        "loan_id": lid, "persist": False}).json()["monthly_payment"]
    r = client.patch(f"/api/loans/{lid}", json={"principal": 800000, "annual_rate": 3.2, "months": 360})
    assert r.status_code == 200
    assert r.json()["principal"] == 800000
    after = client.post("/api/schedule", json={
        "principal": 800000, "annual_rate": 3.2, "months": 360,
        "loan_id": lid, "persist": False}).json()["monthly_payment"]
    assert before != after
    # 档案本身参数也已落库
    got = client.get(f"/api/loans/{lid}").json()
    assert (got["principal"], got["annual_rate"], got["months"]) == (800000, 3.2, 360)


def test_locked_rejects_changed_fields_with_named_details(client):
    lid = _new_loan(client, name="锁定档案A", principal=500000, rate=4.0, months=240)
    r = client.post(f"/api/loans/{lid}/lock", json={"locked": True})
    assert r.status_code == 200 and r.json()["locked"] is True

    r = client.patch(f"/api/loans/{lid}", json={"principal": 600000})
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert str(lid) in detail and "锁定档案A" in detail
    assert "principal" in detail

    r = client.patch(f"/api/loans/{lid}", json={"annual_rate": 5.0, "months": 300})
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "annual_rate" in detail and "months" in detail
    assert str(lid) in detail

    # 提交与现值相同的字段不算修改，不应报错
    same = client.patch(f"/api/loans/{lid}", json={"principal": 500000, "annual_rate": 4.0, "months": 240})
    assert same.status_code == 200
    # 值确实没被改写
    got = client.get(f"/api/loans/{lid}").json()
    assert (got["principal"], got["annual_rate"], got["months"]) == (500000, 4.0, 240)


def test_locked_allows_readonly_calc_and_persist(client):
    lid = _new_loan(client, name="锁定档案B", principal=300000, rate=3.8, months=180)
    client.post(f"/api/loans/{lid}/lock", json={"locked": True})

    r = client.post("/api/schedule", json={
        "principal": 300000, "annual_rate": 3.8, "months": 180,
        "loan_id": lid, "persist": False})
    assert r.status_code == 200
    body = r.json()
    assert body["locked"] is True
    assert body["run_id"] is None

    r = client.post("/api/schedule", json={
        "principal": 300000, "annual_rate": 3.8, "months": 180,
        "loan_id": lid, "persist": True})
    assert r.status_code == 200
    body = r.json()
    assert body["locked"] is True
    assert isinstance(body["run_id"], int)


def test_unlock_restores_editing(client):
    lid = _new_loan(client, name="解锁档案", principal=400000, rate=4.1, months=200)
    client.post(f"/api/loans/{lid}/lock", json={"locked": True})
    r = client.patch(f"/api/loans/{lid}", json={"principal": 420000})
    assert r.status_code == 409
    client.post(f"/api/loans/{lid}/lock", json={"locked": False})
    r = client.patch(f"/api/loans/{lid}", json={"principal": 420000})
    assert r.status_code == 200
    assert client.get(f"/api/loans/{lid}").json()["locked"] is False


def test_lock_toggle_does_not_rewrite_history(client):
    from app.db import connect
    from app.repositories import runs
    lid = _new_loan(client, name="历史档案")
    conn = connect()
    before = len(runs.list_recent(conn, limit=100000))
    conn.close()

    client.post(f"/api/loans/{lid}/lock", json={"locked": True})
    client.post(f"/api/loans/{lid}/lock", json={"locked": False})

    conn = connect()
    after = runs.list_recent(conn, limit=100000)
    conn.close()
    assert len(after) == before
    # 既有历史记录内容未被触碰
    assert all(rec["loan_id"] != lid or rec["kind"] != "lock" for rec in after)


def test_lock_unknown_loan_404(client):
    assert client.post("/api/loans/999999/lock", json={"locked": True}).status_code == 404
    assert client.patch("/api/loans/999999", json={"principal": 1}).status_code == 404
