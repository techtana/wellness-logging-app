"""Shared pytest fixtures for API and component tests."""
import pytest
from unittest.mock import MagicMock, patch


# ── Reusable test data ────────────────────────────────────────────────────────

KB_DOC = {
    "_id": "inst-1", "id": "inst-1", "name": "Emotion Analysis",
    "category": "sentiment", "prompt": "Analyze emotions carefully.",
    "enabled": True, "files": [],
    "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00",
}

PROMPT_DOC = {
    "_id": "p1", "id": "p1", "category": "opening",
    "clinical_text": "How are you feeling today?",
    "rephrased_text": "How are you doing today?",
    "enabled": True, "order": 1,
}

SAMPLE_TRANSCRIPT = [
    {"timestamp": 0, "speaker": "therapist", "text": "How are you feeling today?"},
    {"timestamp": 1, "speaker": "client",    "text": "I have been feeling anxious and overwhelmed."},
    {"timestamp": 2, "speaker": "therapist", "text": "Can you tell me more about what is making you anxious?"},
    {"timestamp": 3, "speaker": "client",    "text": "Work has been stressful and I cannot seem to relax."},
]


# ── Mock collection factory ───────────────────────────────────────────────────

def make_col(docs=None):
    """Pymongo collection mock whose find() is re-iterable."""
    docs = list(docs or [])
    col = MagicMock()
    col.count_documents.return_value = len(docs)
    col.find.side_effect = lambda *a, **kw: iter([dict(d) for d in docs])
    col.find_one.return_value = dict(docs[0]) if docs else None
    col.insert_one.return_value = MagicMock(inserted_id=(docs[0]["_id"] if docs else "new"))
    col.update_one.return_value = MagicMock(modified_count=1)
    col.delete_one.return_value = MagicMock(deleted_count=1)
    return col


def make_mock_db(kb_docs=None, prompt_docs=None, session_docs=None):
    """Return (mock_db, collections_dict)."""
    kb_col       = make_col(kb_docs      or [KB_DOC])
    prompts_col  = make_col(prompt_docs  or [PROMPT_DOC])
    sessions_col = make_col(session_docs or [])

    mock_db = MagicMock()
    _cols = {
        "knowledge_base": kb_col,
        "prompts": prompts_col,
        "sessions": sessions_col,
    }
    mock_db.__getitem__ = MagicMock(side_effect=lambda name: _cols.get(name, MagicMock()))
    return mock_db, _cols


# ── Flask test client fixture ─────────────────────────────────────────────────

@pytest.fixture
def flask_client():
    """Yields (test_client, cols_dict) with MongoDB fully mocked."""
    mock_db, cols = make_mock_db()

    with patch("src.knowledge_base.manager.get_db", return_value=mock_db), \
         patch("src.prompts.manager.get_db",        return_value=mock_db), \
         patch("src.sessions.manager.get_db",       return_value=mock_db):
        from src.api.app import create_app
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client, cols
