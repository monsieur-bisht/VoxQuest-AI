from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_gameplay_loop_and_dataset_export():
    start = client.post("/api/game/start")
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    turn = client.post(
        "/api/game/turn",
        json={
            "session_id": session_id,
            "transcript": "Investigate the tower",
            "expected_transcript": "Investigate the tower",
            "confidence": 0.93,
            "noise_level": "low",
            "accent_tag": "neutral",
        },
    )
    assert turn.status_code == 200
    body = turn.json()
    assert "narration" in body
    assert body["benchmark"]["wer"] == 0.0

    tag = client.post(
        "/api/dataset/tag",
        json={
            "session_id": session_id,
            "transcript": "Investigate the tower",
            "language_tag": "english",
            "noise_level": "low",
            "accent_tag": "neutral",
            "anonymized_audio_id": "sample-1",
        },
    )
    assert tag.status_code == 200

    export_json = client.get("/api/dataset/export?format=json")
    assert export_json.status_code == 200
    assert len(export_json.json()) >= 1

    export_csv = client.get("/api/dataset/export?format=csv")
    assert export_csv.status_code == 200
    assert "language_tag" in export_csv.text
