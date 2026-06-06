def test_get_settings_unconfigured(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_post_settings_saves(client):
    payload = {
        "consumer_key": "ck",
        "consumer_secret": "cs",
        "access_token": "at",
        "access_token_secret": "ats",
    }
    response = client.post("/api/settings", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "saved"


def test_get_settings_after_save(client):
    client.post(
        "/api/settings",
        json={"consumer_key": "ck", "consumer_secret": "cs", "access_token": "at", "access_token_secret": "ats"},
    )
    response = client.get("/api/settings")
    data = response.json()
    assert data["configured"] is True
    assert data["consumer_key"] == "ck"
    assert data["access_token"] == "at"
    assert "consumer_secret" not in data
    assert "access_token_secret" not in data


def test_post_settings_overwrites(client):
    client.post(
        "/api/settings",
        json={"consumer_key": "ck1", "consumer_secret": "cs1", "access_token": "at1", "access_token_secret": "ats1"},
    )
    client.post(
        "/api/settings",
        json={"consumer_key": "ck2", "consumer_secret": "cs2", "access_token": "at2", "access_token_secret": "ats2"},
    )
    response = client.get("/api/settings")
    assert response.json()["consumer_key"] == "ck2"
