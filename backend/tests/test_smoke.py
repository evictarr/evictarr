async def test_list_rules_on_empty_db(client):
    response = await client.get("/api/rules")
    assert response.status_code == 200
    assert response.json() == []
