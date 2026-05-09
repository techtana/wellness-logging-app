"""API endpoint tests for new functionality:
- POST /api/v1/analyze/section  (per-section re-analysis)
- GET  /api/v1/ollama/models    (Ollama model list)
- KB file CRUD endpoints
- Prompt order-only update (drag-drop persistence)
"""
import json
import io
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import KB_DOC, PROMPT_DOC, SAMPLE_TRANSCRIPT


# ── /api/v1/analyze/section ───────────────────────────────────────────────────

class TestAnalyzeSection:

    def test_missing_section_field_returns_400(self, flask_client):
        client, _ = flask_client
        resp = client.post(
            "/api/v1/analyze/section",
            json={"transcript": SAMPLE_TRANSCRIPT},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_missing_transcript_field_returns_400(self, flask_client):
        client, _ = flask_client
        resp = client.post(
            "/api/v1/analyze/section",
            json={"section": "sentiment"},
        )
        assert resp.status_code == 400

    def test_unknown_section_returns_400(self, flask_client):
        client, _ = flask_client
        with patch("src.ai.settings.AISettings.create_provider", return_value=MagicMock()):
            resp = client.post(
                "/api/v1/analyze/section",
                json={"section": "nonexistent", "transcript": SAMPLE_TRANSCRIPT},
            )
        assert resp.status_code == 400
        assert "Unknown section" in resp.get_json().get("error", "")

    def test_no_ai_provider_returns_503(self, flask_client):
        client, _ = flask_client
        with patch("src.ai.settings.AISettings.create_provider", return_value=None):
            resp = client.post(
                "/api/v1/analyze/section",
                json={"section": "sentiment", "transcript": SAMPLE_TRANSCRIPT},
            )
        assert resp.status_code == 503

    @pytest.mark.parametrize("section,ai_key", [
        ("sentiment",       "emotion_points"),
        ("themes",          "themes"),
        ("dynamics",        "speaker_profiles"),
    ])
    def test_valid_section_returns_200(self, flask_client, section, ai_key):
        client, _ = flask_client
        mock_provider = MagicMock()
        mock_provider.complete_json.return_value = {ai_key: [], "summary": {}}

        with patch("src.ai.settings.AISettings.create_provider", return_value=mock_provider):
            resp = client.post(
                "/api/v1/analyze/section",
                json={"section": section, "transcript": SAMPLE_TRANSCRIPT},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["section"] == section
        assert isinstance(data["result"], dict)

    def test_clinical_report_section_passes_context(self, flask_client):
        client, _ = flask_client
        mock_provider = MagicMock()
        mock_provider.complete_json.return_value = {"executive_summary": {}}

        with patch("src.ai.settings.AISettings.create_provider", return_value=mock_provider):
            resp = client.post(
                "/api/v1/analyze/section",
                json={
                    "section": "clinical_report",
                    "transcript": SAMPLE_TRANSCRIPT,
                    "session_id": "sess_test",
                    "sentiment": {"summary": {}},
                    "thematic": {},
                    "relational": {},
                },
            )
        assert resp.status_code == 200
        assert resp.get_json()["section"] == "clinical_report"

    def test_kb_id_resolves_custom_instruction(self, flask_client):
        """When kb_id is provided and found, the KB prompt is used as custom_instruction."""
        client, cols = flask_client
        # KB collection will return KB_DOC on find_one
        cols["knowledge_base"].find_one.return_value = dict(KB_DOC)

        mock_provider = MagicMock()
        mock_provider.complete_json.return_value = {"emotion_points": []}

        with patch("src.ai.settings.AISettings.create_provider", return_value=mock_provider):
            resp = client.post(
                "/api/v1/analyze/section",
                json={
                    "section": "sentiment",
                    "transcript": SAMPLE_TRANSCRIPT,
                    "kb_id": KB_DOC["id"],
                },
            )
        assert resp.status_code == 200
        # The system prompt sent to complete_json should contain the KB prompt text
        call_args = mock_provider.complete_json.call_args
        system_prompt = call_args[0][0]
        assert KB_DOC["prompt"] in system_prompt


# ── /api/v1/ollama/models ─────────────────────────────────────────────────────

class TestOllamaModels:

    def test_unreachable_ollama_returns_empty_list_with_200(self, flask_client):
        client, _ = flask_client
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            resp = client.get("/api/v1/ollama/models?host=http://localhost:11434")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["models"] == []
        assert "error" in data

    def test_ollama_returns_model_names(self, flask_client):
        client, _ = flask_client
        fake_response = json.dumps({
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"},
                {"name": "phi3"},
            ]
        }).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            resp = client.get("/api/v1/ollama/models")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["models"] == ["llama3.2", "mistral", "phi3"]

    def test_custom_host_is_used(self, flask_client):
        client, _ = flask_client
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            raise OSError("not running")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.get("/api/v1/ollama/models?host=http://my-server:11434")

        assert "my-server:11434" in captured.get("url", "")


# ── KB file CRUD ──────────────────────────────────────────────────────────────

class TestKBFiles:

    def test_list_files_returns_empty_for_new_instruction(self, flask_client):
        client, cols = flask_client
        # Must have non-_id/files keys so _clean+_strip_files returns a truthy dict
        cols["knowledge_base"].find_one.return_value = {
            **KB_DOC, "files": []
        }

        resp = client.get(f"/api/v1/kb/instructions/{KB_DOC['id']}/files")
        assert resp.status_code == 200
        assert resp.get_json()["files"] == []

    def test_list_files_not_found_returns_404(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find_one.return_value = None
        resp = client.get("/api/v1/kb/instructions/does-not-exist/files")
        assert resp.status_code == 404

    def test_upload_file_via_json_body(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find_one.return_value = dict(KB_DOC)

        resp = client.post(
            f"/api/v1/kb/instructions/{KB_DOC['id']}/files",
            json={"filename": "notes.txt", "content_text": "Clinical reference notes", "file_type": "text"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["filename"] == "notes.txt"
        assert data["ok"] is True

    def test_upload_file_via_multipart(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find_one.return_value = dict(KB_DOC)

        resp = client.post(
            f"/api/v1/kb/instructions/{KB_DOC['id']}/files",
            data={"file": (io.BytesIO(b"Reference text content"), "ref.txt")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert resp.get_json()["filename"] == "ref.txt"

    def test_upload_disallowed_file_type_returns_400(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find_one.return_value = dict(KB_DOC)

        resp = client.post(
            f"/api/v1/kb/instructions/{KB_DOC['id']}/files",
            data={"file": (io.BytesIO(b"some data"), "script.py")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.get_json().get("error", "")

    def test_upload_empty_file_returns_400(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find_one.return_value = dict(KB_DOC)

        resp = client.post(
            f"/api/v1/kb/instructions/{KB_DOC['id']}/files",
            json={"filename": "empty.txt", "content_text": "   "},
        )
        assert resp.status_code == 400

    def test_delete_file(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].update_one.return_value = MagicMock(modified_count=1)

        resp = client.delete(
            f"/api/v1/kb/instructions/{KB_DOC['id']}/files/notes.txt"
        )
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] is True

    def test_delete_nonexistent_file_returns_404(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].update_one.return_value = MagicMock(modified_count=0)

        resp = client.delete(
            f"/api/v1/kb/instructions/{KB_DOC['id']}/files/ghost.txt"
        )
        assert resp.status_code == 404


# ── Prompt order update (drag-drop persistence) ───────────────────────────────

class TestPromptOrderUpdate:

    def test_order_only_update_succeeds(self, flask_client):
        client, cols = flask_client
        updated_doc = {**PROMPT_DOC, "order": 5}
        cols["prompts"].find_one.return_value = dict(updated_doc)

        resp = client.put(
            f"/api/v1/prompts/{PROMPT_DOC['id']}",
            json={"order": 5},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["order"] == 5

    def test_order_update_does_not_overwrite_other_fields(self, flask_client):
        """A PATCH-style order-only PUT must not clear clinical_text etc."""
        client, cols = flask_client
        cols["prompts"].find_one.return_value = dict(PROMPT_DOC)

        resp = client.put(
            f"/api/v1/prompts/{PROMPT_DOC['id']}",
            json={"order": 3},
        )
        assert resp.status_code == 200
        # update_one should only set the `order` field
        call_args = cols["prompts"].update_one.call_args
        update_doc = call_args[0][1]  # second positional arg is the update op
        set_fields = update_doc.get("$set", {})
        assert "order" in set_fields
        assert "clinical_text" not in set_fields

    def test_order_update_nonexistent_prompt_returns_404(self, flask_client):
        client, cols = flask_client
        cols["prompts"].find_one.return_value = None

        resp = client.put("/api/v1/prompts/ghost-id", json={"order": 2})
        assert resp.status_code == 404
