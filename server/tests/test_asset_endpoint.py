import pytest

from app.storage import put_asset


@pytest.fixture
def uploaded_asset():
    key = "test-asset/sample.txt"
    put_asset(key, b"hello world", "text/plain")
    return key


async def test_asset_requires_auth(client, uploaded_asset):
    r = await client.get("/asset/test-asset/sample.txt")
    assert r.status_code == 401


async def test_asset_returns_content(client, uploaded_asset):
    r = await client.get(
        "/asset/test-asset/sample.txt",
        headers={"Authorization": "Bearer test-key-do-not-use-in-prod"},
    )
    assert r.status_code == 200
    assert r.content == b"hello world"
    assert "text/plain" in r.headers["content-type"]


async def test_asset_not_found(client):
    r = await client.get(
        "/asset/nonexistent/foo.png",
        headers={"Authorization": "Bearer test-key-do-not-use-in-prod"},
    )
    assert r.status_code == 404
