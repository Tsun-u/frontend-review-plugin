async def test_health_open(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_protected_no_auth(client):
    r = await client.get("/health/protected")
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "AUTH_FAILED"


async def test_protected_bad_token(client):
    r = await client.get("/health/protected", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


async def test_protected_good_token(client):
    r = await client.get(
        "/health/protected",
        headers={"Authorization": "Bearer test-key-do-not-use-in-prod"},
    )
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "auth": "verified"}
