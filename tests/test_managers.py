"""Unit tests for SessionManager, PromptManager, and KnowledgeBaseManager CRUD."""
import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path

from tests.conftest import make_col, KB_DOC, PROMPT_DOC, SAMPLE_TRANSCRIPT


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_session_manager(tmp_path, session_docs=None):
    col = make_col(session_docs or [])
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)
    with patch("src.sessions.manager.get_db", return_value=mock_db):
        from src.sessions.manager import SessionManager
        mgr = SessionManager(base_dir=tmp_path / "sessions")
    return mgr, col


def make_prompt_manager(prompt_docs=None):
    col = make_col(prompt_docs or [PROMPT_DOC])
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)
    with patch("src.prompts.manager.get_db", return_value=mock_db):
        from src.prompts.manager import PromptManager
        mgr = PromptManager()
    return mgr, col


def make_kb_manager(kb_docs=None):
    col = make_col(kb_docs or [KB_DOC])
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=col)
    with patch("src.knowledge_base.manager.get_db", return_value=mock_db):
        from src.knowledge_base.manager import KnowledgeBaseManager
        mgr = KnowledgeBaseManager()
    return mgr, col


# ── SessionManager ────────────────────────────────────────────────────────────

class TestSessionManager:

    def test_create_makes_audio_dir_and_returns_meta(self, tmp_path):
        mgr, col = make_session_manager(tmp_path)
        meta = mgr.create("sess_001")
        assert meta["session_id"] == "sess_001"
        assert meta["status"] == "in_progress"
        assert meta["turns"] == []
        assert (tmp_path / "sessions" / "sess_001" / "audio").is_dir()

    def test_create_writes_to_db(self, tmp_path):
        mgr, col = make_session_manager(tmp_path)
        mgr.create("sess_002")
        col.update_one.assert_called_once()
        filter_doc, update_doc = col.update_one.call_args[0]
        assert filter_doc == {"_id": "sess_002"}
        assert "$setOnInsert" in update_doc

    def test_get_returns_cleaned_doc(self, tmp_path):
        session_doc = {
            "_id": "sess_001", "session_id": "sess_001",
            "status": "complete", "turns": [], "bridge_note": None,
        }
        mgr, col = make_session_manager(tmp_path, [session_doc])
        col.find_one.return_value = dict(session_doc)
        result = mgr.get("sess_001")
        assert result["session_id"] == "sess_001"
        assert "_id" not in result

    def test_get_returns_none_when_not_found(self, tmp_path):
        mgr, col = make_session_manager(tmp_path)
        col.find_one.return_value = None
        assert mgr.get("ghost") is None

    def test_update_turns_writes_correct_fields(self, tmp_path):
        session_doc = {"_id": "s1", "session_id": "s1", "turns": [], "status": "in_progress"}
        mgr, col = make_session_manager(tmp_path, [session_doc])
        col.find_one.return_value = dict(session_doc)
        mgr.update("s1", turns=SAMPLE_TRANSCRIPT, status="complete")
        _, update_doc = col.update_one.call_args[0]
        set_fields = update_doc["$set"]
        assert "turns" in set_fields
        assert "status" in set_fields

    def test_update_with_no_valid_fields_skips_db_write(self, tmp_path):
        session_doc = {"_id": "s1", "session_id": "s1", "turns": []}
        mgr, col = make_session_manager(tmp_path, [session_doc])
        col.find_one.return_value = dict(session_doc)
        mgr.update("s1", unknown_field="ignored")
        col.update_one.assert_not_called()

    def test_delete_calls_db_and_returns_true(self, tmp_path):
        mgr, col = make_session_manager(tmp_path)
        col.delete_one.return_value = MagicMock(deleted_count=1)
        assert mgr.delete("sess_001") is True
        col.delete_one.assert_called_once_with({"_id": "sess_001"})

    def test_delete_nonexistent_returns_false(self, tmp_path):
        mgr, col = make_session_manager(tmp_path)
        col.delete_one.return_value = MagicMock(deleted_count=0)
        assert mgr.delete("ghost") is False

    def test_list_sessions_counts_client_turns_only(self, tmp_path):
        turns = [
            {"speaker": "therapist", "text": "Q1"},
            {"speaker": "client",    "text": "A1", "skipped": False},
            {"speaker": "therapist", "text": "Q2"},
            {"speaker": "client",    "text": "",   "skipped": True},   # skipped
        ]
        doc = {"_id": "s1", "session_id": "s1", "created_at": "2025-01-01T00:00:00",
               "status": "complete", "turns": turns, "analysis": None, "bridge_note": None}
        mgr, col = make_session_manager(tmp_path, [doc])
        col.find.side_effect = lambda *a, **kw: iter([dict(doc)])
        sessions = mgr.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["client_turns"] == 1   # skipped not counted

    def test_list_sessions_has_analysis_flag(self, tmp_path):
        doc = {"_id": "s1", "session_id": "s1", "created_at": "2025-01-01T00:00:00",
               "status": "complete", "turns": [], "analysis": {"insight": "x"}, "bridge_note": None}
        mgr, col = make_session_manager(tmp_path, [doc])
        col.find.side_effect = lambda *a, **kw: iter([dict(doc)])
        sessions = mgr.list_sessions()
        assert sessions[0]["has_analysis"] is True

    def test_transcript_text_includes_header_and_turns(self, tmp_path):
        turns = [
            {"speaker": "therapist", "text": "How are you?"},
            {"speaker": "client",    "text": "I feel okay.", "skipped": False},
        ]
        doc = {"_id": "s1", "session_id": "s1", "created_at": "2025-01-01T00:00:00",
               "status": "complete", "turns": turns, "bridge_note": None, "analysis": None}
        mgr, col = make_session_manager(tmp_path, [doc])
        col.find_one.return_value = dict(doc)
        text = mgr.transcript_text("s1")
        assert "ClinicalAI" in text
        assert "s1" in text
        assert "How are you?" in text
        assert "I feel okay." in text
        assert "[PROMPT 1]" in text
        assert "[RESPONSE]" in text

    def test_transcript_text_shows_skipped(self, tmp_path):
        turns = [
            {"speaker": "therapist", "text": "Q"},
            {"speaker": "client",    "text": "", "skipped": True},
        ]
        doc = {"_id": "s1", "session_id": "s1", "created_at": "2025-01-01T00:00:00",
               "status": "complete", "turns": turns, "bridge_note": None, "analysis": None}
        mgr, col = make_session_manager(tmp_path, [doc])
        col.find_one.return_value = dict(doc)
        text = mgr.transcript_text("s1")
        assert "(Skipped)" in text

    def test_transcript_text_returns_none_for_missing_session(self, tmp_path):
        mgr, col = make_session_manager(tmp_path)
        col.find_one.return_value = None
        assert mgr.transcript_text("ghost") is None

    def test_save_audio_writes_file(self, tmp_path):
        mgr, _ = make_session_manager(tmp_path)
        mgr.save_audio("sess_1", "q1.webm", b"fake-audio-data")
        audio_path = tmp_path / "sessions" / "sess_1" / "audio" / "q1.webm"
        assert audio_path.exists()
        assert audio_path.read_bytes() == b"fake-audio-data"

    def test_get_audio_path_returns_none_when_missing(self, tmp_path):
        mgr, _ = make_session_manager(tmp_path)
        assert mgr.get_audio_path("sess_1", "missing.webm") is None


# ── PromptManager ─────────────────────────────────────────────────────────────

class TestPromptManager:

    def test_create_assigns_auto_order(self):
        last_prompt = {**PROMPT_DOC, "order": 3}
        mgr, col = make_prompt_manager([last_prompt])
        col.find_one.return_value = {"order": 3}
        col.insert_one.return_value = MagicMock()
        col.find_one.side_effect = None  # override side_effect to use return_value
        col.find_one.return_value = {"order": 3}

        p = mgr.create(category="custom", clinical_text="New Q?", rephrased_text="Easy Q?")
        inserted = col.insert_one.call_args[0][0]
        assert inserted["order"] == 4

    def test_create_uses_explicit_order(self):
        mgr, col = make_prompt_manager()
        col.insert_one.return_value = MagicMock()
        p = mgr.create(category="custom", clinical_text="Q?", rephrased_text="Q?", order=99)
        inserted = col.insert_one.call_args[0][0]
        assert inserted["order"] == 99

    def test_create_returns_doc_without_mongo_id(self):
        mgr, col = make_prompt_manager()
        col.find_one.return_value = None
        col.insert_one.return_value = MagicMock()
        p = mgr.create(category="opening", clinical_text="How are you?", rephrased_text="Hi?")
        assert "_id" not in p
        assert "id" in p
        assert p["category"] == "opening"
        assert p["enabled"] is True

    def test_get_by_id_returns_cleaned(self):
        mgr, col = make_prompt_manager()
        col.find_one.return_value = dict(PROMPT_DOC)
        result = mgr.get_by_id("p1")
        assert result["id"] == "p1"
        assert "_id" not in result

    def test_get_by_id_returns_none_for_missing(self):
        mgr, col = make_prompt_manager()
        col.find_one.return_value = None
        assert mgr.get_by_id("ghost") is None

    def test_list_returns_all_prompts(self):
        docs = [
            {**PROMPT_DOC, "_id": "p1", "id": "p1", "order": 1},
            {**PROMPT_DOC, "_id": "p2", "id": "p2", "order": 2},
        ]
        mgr, col = make_prompt_manager(docs)
        result = mgr.list()
        assert len(result) == 2
        assert all("_id" not in p for p in result)

    def test_get_session_prompts_passes_enabled_filter(self):
        mgr, col = make_prompt_manager()
        col.find.side_effect = lambda *a, **kw: iter([dict(PROMPT_DOC)])
        mgr.get_session_prompts()
        filter_arg = col.find.call_args[0][0]
        assert filter_arg.get("enabled") is True

    def test_update_sets_only_provided_fields(self):
        mgr, col = make_prompt_manager()
        col.find_one.return_value = dict(PROMPT_DOC)
        mgr.update("p1", order=7)
        _, update_doc = col.update_one.call_args[0]
        set_fields = update_doc["$set"]
        assert set_fields["order"] == 7
        assert "clinical_text" not in set_fields

    def test_update_returns_none_for_missing(self):
        mgr, col = make_prompt_manager()
        col.find_one.return_value = None
        result = mgr.update("ghost", order=1)
        assert result is None

    def test_delete_returns_true_on_success(self):
        mgr, col = make_prompt_manager()
        col.delete_one.return_value = MagicMock(deleted_count=1)
        assert mgr.delete("p1") is True

    def test_delete_returns_false_for_missing(self):
        mgr, col = make_prompt_manager()
        col.delete_one.return_value = MagicMock(deleted_count=0)
        assert mgr.delete("ghost") is False

    def test_reset_drops_and_reseeds(self):
        mgr, col = make_prompt_manager()
        mgr.reset()
        col.drop.assert_called_once()
        assert col.insert_one.call_count > 0


# ── KnowledgeBaseManager ──────────────────────────────────────────────────────

class TestKBManagerCRUD:

    def test_create_returns_doc_without_files_key(self):
        mgr, col = make_kb_manager()
        col.insert_one.return_value = MagicMock()
        result = mgr.create("New Rule", "sentiment", "Analyze carefully.")
        assert "files" not in result
        assert result["name"] == "New Rule"
        assert result["category"] == "sentiment"
        assert result["enabled"] is True

    def test_create_stores_empty_files_array(self):
        mgr, col = make_kb_manager()
        col.insert_one.return_value = MagicMock()
        mgr.create("Rule", "themes", "p")
        inserted = col.insert_one.call_args[0][0]
        assert inserted["files"] == []

    def test_get_by_id_strips_files_key(self):
        mgr, col = make_kb_manager()
        col.find_one.return_value = {**KB_DOC, "files": [{"filename": "f.txt", "content_text": "x"}]}
        result = mgr.get_by_id("inst-1")
        assert "files" not in result

    def test_get_by_id_returns_none_for_missing(self):
        mgr, col = make_kb_manager()
        col.find_one.return_value = None
        assert mgr.get_by_id("ghost") is None

    def test_get_instruction_uses_category_and_enabled_filter(self):
        mgr, col = make_kb_manager()
        col.find_one.return_value = dict(KB_DOC)
        mgr.get_instruction("sentiment")
        filter_arg = col.find_one.call_args[0][0]
        assert filter_arg["category"] == "sentiment"
        assert filter_arg["enabled"] is True

    def test_get_instruction_augments_prompt_with_files(self):
        doc = {**KB_DOC, "files": [{"filename": "r.txt", "content_text": "Reference"}]}
        mgr, col = make_kb_manager([doc])
        col.find_one.return_value = dict(doc)
        result = mgr.get_instruction("sentiment")
        assert "Reference" in result["prompt"]

    def test_get_instruction_returns_none_when_not_found(self):
        mgr, col = make_kb_manager()
        col.find_one.return_value = None
        assert mgr.get_instruction("unknown_category") is None

    def test_update_sets_fields_and_updated_at(self):
        mgr, col = make_kb_manager()
        col.find_one.return_value = dict(KB_DOC)
        mgr.update("inst-1", name="Renamed", enabled=False)
        _, update_doc = col.update_one.call_args[0]
        set_fields = update_doc["$set"]
        assert set_fields["name"] == "Renamed"
        assert set_fields["enabled"] is False
        assert "updated_at" in set_fields

    def test_update_does_not_set_files_field(self):
        mgr, col = make_kb_manager()
        col.find_one.return_value = dict(KB_DOC)
        mgr.update("inst-1", name="Test")
        _, update_doc = col.update_one.call_args[0]
        assert "files" not in update_doc["$set"]

    def test_delete_returns_true_on_success(self):
        mgr, col = make_kb_manager()
        col.delete_one.return_value = MagicMock(deleted_count=1)
        assert mgr.delete("inst-1") is True

    def test_delete_returns_false_for_missing(self):
        mgr, col = make_kb_manager()
        col.delete_one.return_value = MagicMock(deleted_count=0)
        assert mgr.delete("ghost") is False

    def test_list_strips_files_from_all_items(self):
        docs = [
            {**KB_DOC, "_id": "i1", "id": "i1", "files": [{"filename": "f.txt", "content_text": "x"}]},
            {**KB_DOC, "_id": "i2", "id": "i2", "files": []},
        ]
        mgr, col = make_kb_manager(docs)
        result = mgr.list()
        assert len(result) == 2
        assert all("files" not in item for item in result)

    def test_reset_drops_and_reseeds_defaults(self):
        mgr, col = make_kb_manager()
        mgr.reset()
        col.drop.assert_called_once()
        assert col.insert_one.call_count > 0
