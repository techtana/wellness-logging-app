"""Integration tests for remaining API routes:
- /health
- /api/v1/settings/ai  and  /api/v1/settings/transcription
- /api/v1/sessions  (CRUD + audio + transcript + analysis)
- /api/v1/prompts   (CRUD + session + rephrase + reset)
- /api/v1/kb/instructions  (CRUD + reset)
- /api/v1/session/bridge
- /api/v1/analyze  (main analysis endpoint)
"""
import io
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import KB_DOC, PROMPT_DOC, SAMPLE_TRANSCRIPT, make_col


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:

    def test_health_returns_200(self, flask_client):
        client, _ = flask_client
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_body_has_required_keys(self, flask_client):
        client, _ = flask_client
        data = client.get("/health").get_json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "ai_provider" in data
        assert "timestamp" in data


# ── AI Settings ───────────────────────────────────────────────────────────────

class TestAISettings:

    def test_get_ai_settings_returns_200(self, flask_client):
        client, _ = flask_client
        resp = client.get("/api/v1/settings/ai")
        assert resp.status_code == 200

    def test_get_ai_settings_masks_api_keys(self, flask_client):
        client, _ = flask_client
        data = client.get("/api/v1/settings/ai").get_json()
        # Keys should be masked (empty or "****" suffix), never raw
        for provider in ("claude", "openai"):
            key = data.get(provider, {}).get("api_key", "")
            assert len(key) == 0 or "****" in key or len(key) <= 8

    def test_put_ai_settings_updates_provider(self, flask_client):
        client, _ = flask_client
        resp = client.put(
            "/api/v1/settings/ai",
            json={"provider": "none", "claude": {}, "openai": {}, "ollama": {}},
        )
        assert resp.status_code == 200
        assert resp.get_json()["provider"] == "none"

    def test_put_ai_settings_missing_body_returns_4xx(self, flask_client):
        client, _ = flask_client
        resp = client.put("/api/v1/settings/ai", data="", content_type="text/plain")
        assert resp.status_code in (400, 415)

    def test_get_transcription_settings_returns_200(self, flask_client):
        client, _ = flask_client
        resp = client.get("/api/v1/settings/transcription")
        assert resp.status_code == 200

    def test_put_transcription_settings_updates_provider(self, flask_client):
        client, _ = flask_client
        resp = client.put(
            "/api/v1/settings/transcription",
            json={"provider": "none", "whisper_local": {}, "openai": {}},
        )
        assert resp.status_code == 200


# ── Sessions API ──────────────────────────────────────────────────────────────

class TestSessionsAPI:

    def _session_doc(self, sid="sess_001"):
        return {
            "_id": sid, "session_id": sid, "created_at": "2025-01-01T00:00:00",
            "status": "complete", "turns": SAMPLE_TRANSCRIPT,
            "bridge_note": "Great session.", "analysis": None,
        }

    def test_create_session_returns_201(self, flask_client):
        client, cols = flask_client
        cols["sessions"].find_one.return_value = None
        resp = client.post("/api/v1/sessions", json={"session_id": "sess_new"})
        assert resp.status_code in (200, 201)

    def test_create_session_idempotent_returns_existing(self, flask_client):
        client, cols = flask_client
        doc = self._session_doc()
        cols["sessions"].find_one.return_value = dict(doc)
        resp = client.post("/api/v1/sessions", json={"session_id": "sess_001"})
        assert resp.status_code == 200
        assert resp.get_json()["session_id"] == "sess_001"

    def test_list_sessions_returns_200(self, flask_client):
        client, cols = flask_client
        doc = self._session_doc()
        cols["sessions"].find.side_effect = lambda *a, **kw: iter([dict(doc)])
        resp = client.get("/api/v1/sessions")
        assert resp.status_code == 200
        assert "sessions" in resp.get_json()

    def test_get_session_found(self, flask_client):
        client, cols = flask_client
        doc = self._session_doc()
        cols["sessions"].find_one.return_value = dict(doc)
        resp = client.get("/api/v1/sessions/sess_001")
        assert resp.status_code == 200
        assert resp.get_json()["session_id"] == "sess_001"

    def test_get_session_not_found_returns_404(self, flask_client):
        client, cols = flask_client
        cols["sessions"].find_one.return_value = None
        resp = client.get("/api/v1/sessions/ghost")
        assert resp.status_code == 404

    def test_update_session_turns(self, flask_client):
        client, cols = flask_client
        doc = self._session_doc()
        cols["sessions"].find_one.return_value = dict(doc)
        resp = client.put(
            "/api/v1/sessions/sess_001",
            json={"turns": SAMPLE_TRANSCRIPT, "status": "complete"},
        )
        assert resp.status_code == 200

    def test_delete_session_returns_200(self, flask_client):
        client, cols = flask_client
        cols["sessions"].delete_one.return_value = MagicMock(deleted_count=1)
        resp = client.delete("/api/v1/sessions/sess_001")
        assert resp.status_code == 200

    def test_delete_session_not_found_returns_404(self, flask_client):
        client, cols = flask_client
        cols["sessions"].delete_one.return_value = MagicMock(deleted_count=0)
        resp = client.delete("/api/v1/sessions/ghost")
        assert resp.status_code == 404

    def test_save_analysis_updates_session(self, flask_client):
        client, cols = flask_client
        doc = self._session_doc()
        cols["sessions"].find_one.return_value = dict(doc)
        resp = client.put(
            "/api/v1/sessions/sess_001/analysis",
            json={"status": "success", "analysis": {}, "insight_report": {}},
        )
        assert resp.status_code == 200

    def test_upload_audio_returns_200(self, flask_client):
        client, cols = flask_client
        doc = self._session_doc()
        cols["sessions"].find_one.return_value = dict(doc)
        resp = client.post(
            "/api/v1/sessions/sess_001/audio/q1.webm",
            data={"audio": (io.BytesIO(b"fake-audio"), "q1.webm")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200

    def test_transcript_download_returns_text(self, flask_client):
        client, cols = flask_client
        doc = self._session_doc()
        cols["sessions"].find_one.return_value = dict(doc)
        resp = client.get("/api/v1/sessions/sess_001/transcript.txt")
        assert resp.status_code == 200
        assert b"ClinicalAI" in resp.data

    def test_transcript_download_not_found_returns_404(self, flask_client):
        client, cols = flask_client
        cols["sessions"].find_one.return_value = None
        resp = client.get("/api/v1/sessions/ghost/transcript.txt")
        assert resp.status_code == 404


# ── Prompts API ───────────────────────────────────────────────────────────────

class TestPromptsAPI:

    def test_list_prompts_returns_200(self, flask_client):
        client, cols = flask_client
        cols["prompts"].find.side_effect = lambda *a, **kw: iter([dict(PROMPT_DOC)])
        resp = client.get("/api/v1/prompts")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "prompts" in data
        assert isinstance(data["prompts"], list)

    def test_get_session_prompts_returns_enabled_only(self, flask_client):
        client, cols = flask_client
        cols["prompts"].find.side_effect = lambda *a, **kw: iter([dict(PROMPT_DOC)])
        resp = client.get("/api/v1/prompts/session")
        assert resp.status_code == 200
        assert "prompts" in resp.get_json()

    def test_create_prompt_returns_201(self, flask_client):
        client, cols = flask_client
        cols["prompts"].find_one.return_value = {"order": 1}
        cols["prompts"].insert_one.return_value = MagicMock()
        resp = client.post(
            "/api/v1/prompts",
            json={"clinical_text": "What are you most anxious about?",
                  "rephrased_text": "What worries you most right now?",
                  "category": "exploration"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["clinical_text"] == "What are you most anxious about?"

    def test_create_prompt_missing_clinical_text_returns_400(self, flask_client):
        client, _ = flask_client
        resp = client.post("/api/v1/prompts", json={"category": "opening"})
        assert resp.status_code == 400

    def test_get_prompt_returns_200(self, flask_client):
        client, cols = flask_client
        cols["prompts"].find_one.return_value = dict(PROMPT_DOC)
        resp = client.get(f"/api/v1/prompts/{PROMPT_DOC['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == "p1"

    def test_get_prompt_not_found_returns_404(self, flask_client):
        client, cols = flask_client
        cols["prompts"].find_one.return_value = None
        resp = client.get("/api/v1/prompts/ghost")
        assert resp.status_code == 404

    def test_delete_prompt_returns_200(self, flask_client):
        client, cols = flask_client
        cols["prompts"].delete_one.return_value = MagicMock(deleted_count=1)
        resp = client.delete(f"/api/v1/prompts/{PROMPT_DOC['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] is True

    def test_delete_prompt_not_found_returns_404(self, flask_client):
        client, cols = flask_client
        cols["prompts"].delete_one.return_value = MagicMock(deleted_count=0)
        resp = client.delete("/api/v1/prompts/ghost")
        assert resp.status_code == 404

    def test_reset_prompts_returns_200(self, flask_client):
        client, cols = flask_client
        cols["prompts"].find.side_effect = lambda *a, **kw: iter([])
        resp = client.post("/api/v1/prompts/reset")
        assert resp.status_code == 200
        assert "prompts" in resp.get_json()

    def test_rephrase_no_ai_provider_returns_503(self, flask_client):
        client, _ = flask_client
        with patch("src.ai.settings.AISettings.create_provider", return_value=None):
            resp = client.post(
                "/api/v1/prompts/rephrase",
                json={"clinical_text": "How are you feeling?"},
            )
        assert resp.status_code == 503

    def test_rephrase_missing_field_returns_400(self, flask_client):
        client, _ = flask_client
        resp = client.post("/api/v1/prompts/rephrase", json={})
        assert resp.status_code == 400

    def test_rephrase_with_ai_returns_rephrased(self, flask_client):
        client, _ = flask_client
        mock_provider = MagicMock()
        mock_provider.complete_text.return_value = "How have you been feeling lately?"
        with patch("src.ai.settings.AISettings.create_provider", return_value=mock_provider):
            resp = client.post(
                "/api/v1/prompts/rephrase",
                json={"clinical_text": "Describe your current affective state."},
            )
        assert resp.status_code == 200
        assert "rephrased_text" in resp.get_json()


# ── KB Instructions API ───────────────────────────────────────────────────────

class TestKBInstructionsAPI:

    def test_list_kb_instructions_returns_200(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find.side_effect = lambda *a, **kw: iter([dict(KB_DOC)])
        resp = client.get("/api/v1/kb/instructions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "instructions" in data
        assert isinstance(data["instructions"], list)

    def test_list_kb_instructions_does_not_include_files(self, flask_client):
        client, cols = flask_client
        doc_with_files = {**KB_DOC, "files": [{"filename": "r.txt", "content_text": "secret"}]}
        cols["knowledge_base"].find.side_effect = lambda *a, **kw: iter([dict(doc_with_files)])
        data = client.get("/api/v1/kb/instructions").get_json()
        for inst in data["instructions"]:
            assert "files" not in inst

    def test_create_kb_instruction_returns_201(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].insert_one.return_value = MagicMock()
        resp = client.post(
            "/api/v1/kb/instructions",
            json={"name": "New Rule", "category": "custom", "prompt": "Analyze themes."},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "New Rule"
        assert "files" not in data

    def test_create_kb_instruction_missing_fields_returns_400(self, flask_client):
        client, _ = flask_client
        resp = client.post(
            "/api/v1/kb/instructions",
            json={"name": "Incomplete"},  # missing category + prompt
        )
        assert resp.status_code == 400

    def test_get_kb_instruction_returns_200(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find_one.return_value = dict(KB_DOC)
        resp = client.get(f"/api/v1/kb/instructions/{KB_DOC['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == KB_DOC["id"]

    def test_get_kb_instruction_not_found_returns_404(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find_one.return_value = None
        resp = client.get("/api/v1/kb/instructions/ghost")
        assert resp.status_code == 404

    def test_update_kb_instruction_returns_200(self, flask_client):
        client, cols = flask_client
        updated_doc = {**KB_DOC, "name": "Renamed"}
        cols["knowledge_base"].find_one.return_value = dict(updated_doc)
        resp = client.put(
            f"/api/v1/kb/instructions/{KB_DOC['id']}",
            json={"name": "Renamed"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Renamed"

    def test_update_kb_instruction_not_found_returns_404(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find_one.return_value = None
        resp = client.put("/api/v1/kb/instructions/ghost", json={"name": "x"})
        assert resp.status_code == 404

    def test_delete_kb_instruction_returns_200(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].delete_one.return_value = MagicMock(deleted_count=1)
        resp = client.delete(f"/api/v1/kb/instructions/{KB_DOC['id']}")
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] is True

    def test_delete_kb_instruction_not_found_returns_404(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].delete_one.return_value = MagicMock(deleted_count=0)
        resp = client.delete("/api/v1/kb/instructions/ghost")
        assert resp.status_code == 404

    def test_reset_kb_returns_200(self, flask_client):
        client, cols = flask_client
        cols["knowledge_base"].find.side_effect = lambda *a, **kw: iter([])
        resp = client.post("/api/v1/kb/reset")
        assert resp.status_code == 200
        assert "instructions" in resp.get_json()


# ── Bridge note ───────────────────────────────────────────────────────────────

class TestBridgeNote:

    def test_missing_transcript_returns_400(self, flask_client):
        client, _ = flask_client
        resp = client.post("/api/v1/session/bridge", json={})
        assert resp.status_code == 400

    def test_no_ai_provider_returns_fallback(self, flask_client):
        client, _ = flask_client
        with patch("src.ai.settings.AISettings.create_provider", return_value=None):
            resp = client.post(
                "/api/v1/session/bridge",
                json={"transcript": SAMPLE_TRANSCRIPT},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "bridge_note" in data
        assert len(data["bridge_note"]) > 0

    def test_with_ai_returns_generated_note(self, flask_client):
        client, _ = flask_client
        mock_provider = MagicMock()
        mock_provider.complete_text.return_value = "You showed real courage today."
        with patch("src.ai.settings.AISettings.create_provider", return_value=mock_provider):
            resp = client.post(
                "/api/v1/session/bridge",
                json={"transcript": SAMPLE_TRANSCRIPT},
            )
        assert resp.status_code == 200
        assert resp.get_json()["bridge_note"] == "You showed real courage today."


# ── Main analysis endpoint ────────────────────────────────────────────────────

class TestAnalyzeEndpoint:

    def test_missing_transcript_returns_400(self, flask_client):
        client, _ = flask_client
        resp = client.post("/api/v1/analyze", json={"session_id": "s1"})
        assert resp.status_code == 400

    def test_missing_body_returns_4xx(self, flask_client):
        client, _ = flask_client
        resp = client.post("/api/v1/analyze", data="", content_type="text/plain")
        assert resp.status_code in (400, 415)

    def test_keyword_analysis_succeeds_without_ai(self, flask_client):
        """Keyword-based fallback analysis should work when no AI provider is set."""
        client, _ = flask_client
        with patch("src.ai.settings.AISettings.create_provider", return_value=None):
            resp = client.post(
                "/api/v1/analyze",
                json={"transcript": SAMPLE_TRANSCRIPT, "session_id": "s1"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "analysis" in data
        assert "insight_report" in data
        assert data["ai_enhanced"] is False

    def test_analysis_with_mocked_ai(self, flask_client):
        client, _ = flask_client
        mock_ai_result = {
            "emotion_points": [{"timestamp": "1", "emotion": "Anxious", "intensity": 60.0}],
            "summary": {"overall_sentiment": "Anxious", "average_intensity": 60.0,
                        "emotional_stability": "Stable", "emotion_distribution": {}},
            "significant_shifts": [],
        }
        mock_provider = MagicMock()
        mock_provider.complete_json.return_value = mock_ai_result
        with patch("src.ai.settings.AISettings.create_provider", return_value=mock_provider):
            resp = client.post(
                "/api/v1/analyze",
                json={"transcript": SAMPLE_TRANSCRIPT, "session_id": "s1"},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
