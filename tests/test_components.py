"""Unit tests for KnowledgeBaseManager and AIAnalyzer new functionality:
- KBManager._augment_prompt()      (file content appended to system prompt)
- KBManager file CRUD methods
- KBManager.get_by_id_with_files()
- AIAnalyzer custom_instruction parameter (skips KB lookup when provided)
- AIAnalyzer graceful error handling (returns {} on provider failure)
"""
from unittest.mock import MagicMock, patch, call

import pytest


SAMPLE_TRANSCRIPT = [
    {"timestamp": 0, "speaker": "therapist", "text": "How are you feeling?"},
    {"timestamp": 1, "speaker": "client",    "text": "I feel anxious and tired."},
    {"timestamp": 2, "speaker": "therapist", "text": "Can you describe that more?"},
    {"timestamp": 3, "speaker": "client",    "text": "It is like a constant low-level dread."},
]


# ── KnowledgeBaseManager helpers ──────────────────────────────────────────────

def make_kb_manager():
    """Return a KnowledgeBaseManager with a fully mocked collection."""
    kb_col = MagicMock()
    kb_col.count_documents.return_value = 1  # skip migration
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=kb_col)

    with patch("src.knowledge_base.manager.get_db", return_value=mock_db):
        from src.knowledge_base.manager import KnowledgeBaseManager
        manager = KnowledgeBaseManager()
    return manager, kb_col


class TestKBManagerAugmentPrompt:

    def test_no_files_returns_unchanged(self):
        manager, _ = make_kb_manager()
        inst = {"id": "x", "prompt": "Base prompt.", "files": []}
        result = manager._augment_prompt(inst)
        assert result["prompt"] == "Base prompt."

    def test_single_file_appended_to_prompt(self):
        manager, _ = make_kb_manager()
        inst = {
            "id": "x",
            "prompt": "Analyze emotions.",
            "files": [{"filename": "ref.txt", "content_text": "Clinical notes here."}],
        }
        result = manager._augment_prompt(inst)
        assert "Analyze emotions." in result["prompt"]
        assert "REFERENCE MATERIALS" in result["prompt"]
        assert "ref.txt" in result["prompt"]
        assert "Clinical notes here." in result["prompt"]

    def test_multiple_files_all_included(self):
        manager, _ = make_kb_manager()
        inst = {
            "id": "x",
            "prompt": "Base.",
            "files": [
                {"filename": "a.txt", "content_text": "Content A"},
                {"filename": "b.txt", "content_text": "Content B"},
            ],
        }
        result = manager._augment_prompt(inst)
        assert "Content A" in result["prompt"]
        assert "Content B" in result["prompt"]

    def test_original_inst_dict_not_mutated(self):
        manager, _ = make_kb_manager()
        inst = {
            "id": "x",
            "prompt": "Original.",
            "files": [{"filename": "f.txt", "content_text": "extra"}],
        }
        original_prompt = inst["prompt"]
        manager._augment_prompt(inst)
        assert inst["prompt"] == original_prompt  # original not mutated

    def test_strip_files_removes_files_key(self):
        manager, _ = make_kb_manager()
        doc = {"id": "x", "prompt": "p", "files": [{"filename": "f.txt", "content_text": "x"}]}
        result = manager._strip_files(dict(doc))
        assert "files" not in result
        assert result["prompt"] == "p"


class TestKBManagerFileCRUD:

    def test_save_file_calls_pull_then_push(self):
        manager, kb_col = make_kb_manager()
        kb_col.update_one.return_value = MagicMock(modified_count=1)

        ok = manager.save_file("inst-1", "notes.txt", "Some content", "text")

        assert ok is True
        # Should call update_one twice: $pull then $push
        assert kb_col.update_one.call_count == 2
        pull_call, push_call = kb_col.update_one.call_args_list
        assert "$pull" in pull_call[0][1]
        assert "$push" in push_call[0][1]

    def test_save_file_returns_false_on_no_match(self):
        manager, kb_col = make_kb_manager()
        kb_col.update_one.return_value = MagicMock(modified_count=0)

        ok = manager.save_file("missing", "f.txt", "content")
        assert ok is False

    def test_list_files_returns_metadata_only(self):
        manager, kb_col = make_kb_manager()
        kb_col.find_one.return_value = {
            "_id": "inst-1",
            "files": [
                {"filename": "ref.txt", "file_type": "text", "content_text": "Secret", "created_at": "2025-01-01"},
                {"filename": "doc.pdf", "file_type": "pdf",  "content_text": "More secret", "created_at": "2025-01-02"},
            ],
        }
        files = manager.list_files("inst-1")

        assert len(files) == 2
        assert files[0]["filename"] == "ref.txt"
        assert files[1]["filename"] == "doc.pdf"
        # content_text must NOT be exposed
        for f in files:
            assert "content_text" not in f

    def test_list_files_returns_empty_for_missing_instruction(self):
        manager, kb_col = make_kb_manager()
        kb_col.find_one.return_value = None
        assert manager.list_files("ghost") == []

    def test_delete_file_returns_true_on_match(self):
        manager, kb_col = make_kb_manager()
        kb_col.update_one.return_value = MagicMock(modified_count=1)
        assert manager.delete_file("inst-1", "ref.txt") is True

    def test_delete_file_returns_false_on_no_match(self):
        manager, kb_col = make_kb_manager()
        kb_col.update_one.return_value = MagicMock(modified_count=0)
        assert manager.delete_file("inst-1", "ghost.txt") is False

    def test_get_by_id_with_files_augments_prompt(self):
        manager, kb_col = make_kb_manager()
        kb_col.find_one.return_value = {
            "_id": "inst-1", "id": "inst-1", "prompt": "Base prompt.",
            "files": [{"filename": "r.txt", "content_text": "Reference"}],
        }
        result = manager.get_by_id_with_files("inst-1")
        assert "Reference" in result["prompt"]
        assert "REFERENCE MATERIALS" in result["prompt"]

    def test_get_by_id_strips_files_from_result(self):
        manager, kb_col = make_kb_manager()
        kb_col.find_one.return_value = {
            "_id": "inst-1", "id": "inst-1", "prompt": "Base.",
            "files": [{"filename": "r.txt", "content_text": "x"}],
        }
        result = manager.get_by_id("inst-1")
        assert "files" not in result


# ── AIAnalyzer ────────────────────────────────────────────────────────────────

def make_analyzer():
    from src.ai.analyzer import AIAnalyzer
    provider = MagicMock()
    kb = MagicMock()
    return AIAnalyzer(provider, kb), provider, kb


class TestAIAnalyzerCustomInstruction:

    def test_custom_instruction_overrides_kb_lookup_for_emotions(self):
        analyzer, provider, kb = make_analyzer()
        provider.complete_json.return_value = {"emotion_points": [], "summary": {}}

        analyzer.analyze_emotions(SAMPLE_TRANSCRIPT, custom_instruction="Custom system prompt")

        kb.get_instruction.assert_not_called()
        system_arg = provider.complete_json.call_args[0][0]
        assert "Custom system prompt" in system_arg

    def test_custom_instruction_overrides_kb_lookup_for_themes(self):
        analyzer, provider, kb = make_analyzer()
        provider.complete_json.return_value = {"themes": []}

        analyzer.analyze_themes(SAMPLE_TRANSCRIPT, custom_instruction="Themes prompt")

        kb.get_instruction.assert_not_called()
        system_arg = provider.complete_json.call_args[0][0]
        assert "Themes prompt" in system_arg

    def test_custom_instruction_overrides_kb_lookup_for_dynamics(self):
        analyzer, provider, kb = make_analyzer()
        provider.complete_json.return_value = {"speaker_profiles": {}}

        analyzer.analyze_dynamics(SAMPLE_TRANSCRIPT, custom_instruction="Dynamics prompt")

        kb.get_instruction.assert_not_called()

    def test_custom_instruction_appends_json_directive(self):
        """The _JSON_INSTRUCTION suffix must still be appended."""
        analyzer, provider, kb = make_analyzer()
        provider.complete_json.return_value = {}

        analyzer.analyze_emotions(SAMPLE_TRANSCRIPT, custom_instruction="My prompt")

        system_arg = provider.complete_json.call_args[0][0]
        assert "JSON" in system_arg  # _JSON_INSTRUCTION contains "JSON"

    def test_no_custom_instruction_falls_back_to_kb(self):
        analyzer, provider, kb = make_analyzer()
        kb.get_instruction.return_value = {"prompt": "KB instruction text", "id": "kb-1"}
        provider.complete_json.return_value = {"emotion_points": []}

        analyzer.analyze_emotions(SAMPLE_TRANSCRIPT)

        kb.get_instruction.assert_called_once_with("sentiment")
        system_arg = provider.complete_json.call_args[0][0]
        assert "KB instruction text" in system_arg

    def test_no_custom_instruction_and_no_kb_returns_empty(self):
        analyzer, provider, kb = make_analyzer()
        kb.get_instruction.return_value = None  # no KB instruction configured

        result = analyzer.analyze_emotions(SAMPLE_TRANSCRIPT)

        assert result == {}
        provider.complete_json.assert_not_called()


class TestAIAnalyzerErrorHandling:

    def test_provider_exception_returns_empty_dict_for_emotions(self):
        analyzer, provider, kb = make_analyzer()
        kb.get_instruction.return_value = {"prompt": "p", "id": "x"}
        provider.complete_json.side_effect = RuntimeError("API unreachable")

        result = analyzer.analyze_emotions(SAMPLE_TRANSCRIPT)
        assert result == {}

    def test_provider_exception_returns_empty_dict_for_themes(self):
        analyzer, provider, kb = make_analyzer()
        kb.get_instruction.return_value = {"prompt": "p", "id": "x"}
        provider.complete_json.side_effect = ConnectionError("timeout")

        result = analyzer.analyze_themes(SAMPLE_TRANSCRIPT)
        assert result == {}

    def test_provider_exception_returns_empty_dict_for_dynamics(self):
        analyzer, provider, kb = make_analyzer()
        kb.get_instruction.return_value = {"prompt": "p", "id": "x"}
        provider.complete_json.side_effect = Exception("unknown error")

        result = analyzer.analyze_dynamics(SAMPLE_TRANSCRIPT)
        assert result == {}

    def test_provider_exception_returns_empty_dict_for_report(self):
        analyzer, provider, kb = make_analyzer()
        kb.get_instruction.return_value = {"prompt": "p", "id": "x"}
        provider.complete_json.side_effect = Exception("model overloaded")

        result = analyzer.generate_report_sections(
            SAMPLE_TRANSCRIPT, "sess_1", "anon", {}, {}, {}
        )
        assert result == {}

    def test_provider_none_response_returns_empty_dict(self):
        analyzer, provider, kb = make_analyzer()
        kb.get_instruction.return_value = {"prompt": "p", "id": "x"}
        provider.complete_json.return_value = None  # provider returned None

        result = analyzer.analyze_emotions(SAMPLE_TRANSCRIPT)
        assert result == {}

    def test_report_uses_custom_instruction(self):
        analyzer, provider, kb = make_analyzer()
        provider.complete_json.return_value = {"executive_summary": {}}

        analyzer.generate_report_sections(
            SAMPLE_TRANSCRIPT, "s1", "p1", {}, {}, {},
            custom_instruction="Report prompt",
        )

        kb.get_instruction.assert_not_called()
        system_arg = provider.complete_json.call_args[0][0]
        assert "Report prompt" in system_arg
