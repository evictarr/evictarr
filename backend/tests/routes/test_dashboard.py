async def test_watched_status_empty_when_no_rules(client):
    response = await client.get("/api/dashboard/watched-status")
    assert response.status_code == 200
    assert response.json() == {"approaching": [], "exempt": []}
