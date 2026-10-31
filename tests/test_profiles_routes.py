import json
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_get_profiles_returns_env_profiles(client):
    res = client.get("/api/profiles")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    profiles = data["profiles"]
    assert "LM Studio (Local)" in profiles
    assert "Groq" in profiles
    assert "Mistral" in profiles
    assert "NVIDIA NIM" in profiles
    assert "Google Gemini" in profiles
    assert "OpenRouter" in profiles
    assert "Alibaba" in profiles
    assert "Z.ai" in profiles
    assert "OpenAI" in profiles
    assert "DeepSeek" in profiles


def test_save_and_delete_custom_profile(client):
    # Save a custom profile
    payload = {
        "name": "Test Custom Provider",
        "data": {
            "apiKey": "test-key-123",
            "apiBase": "http://test-provider.local/v1",
            "model": "test-model-v1",
            "provider": "openai",
            "streaming": True
        }
    }
    save_res = client.post("/api/profiles", json=payload)
    assert save_res.status_code == 200
    assert save_res.get_json()["status"] == "ok"

    # Verify it is in list
    get_res = client.get("/api/profiles")
    data = get_res.get_json()
    assert "Test Custom Provider" in data["profiles"]
    assert data["profiles"]["Test Custom Provider"]["apiKey"] == "test-key-123"

    # Set as active
    active_res = client.post("/api/profiles/active", json={"name": "Test Custom Provider"})
    assert active_res.status_code == 200
    assert active_res.get_json()["lastProfile"] == "Test Custom Provider"

    # Delete it
    del_res = client.delete("/api/profiles/Test%20Custom%20Provider")
    assert del_res.status_code == 200

    # Verify deleted
    get_res2 = client.get("/api/profiles")
    assert "Test Custom Provider" not in get_res2.get_json()["profiles"]
