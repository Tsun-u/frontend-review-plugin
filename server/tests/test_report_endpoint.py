async def test_report_404(client):
    r = await client.get(
        "/report/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": "Bearer test-key-do-not-use-in-prod"},
    )
    assert r.status_code == 404


async def test_report_bad_uuid(client):
    r = await client.get(
        "/report/not-a-uuid",
        headers={"Authorization": "Bearer test-key-do-not-use-in-prod"},
    )
    assert r.status_code == 400


async def test_report_requires_auth(client):
    r = await client.get("/report/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 401
