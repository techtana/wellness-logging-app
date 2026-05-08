"""MongoDB-backed session manager. Audio files remain on disk."""
import json
import shutil
from datetime import datetime
from pathlib import Path

from src.db import get_db

DATA_DIR = Path(__file__).parents[2] / "data"


def _clean(doc: dict) -> dict:
    """Strip internal MongoDB _id before returning to callers."""
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


class SessionManager:
    def __init__(self, base_dir: Path = None):
        self._base = base_dir or (DATA_DIR / "sessions")
        self._base.mkdir(parents=True, exist_ok=True)
        self._col = get_db()["sessions"]
        self._migrate_from_files()

    # ── One-time migration from file-based sessions ─────────
    def _migrate_from_files(self):
        if self._col.count_documents({}) > 0:
            return
        imported = 0
        for d in self._base.iterdir():
            if not d.is_dir():
                continue
            p = d / "session.json"
            if not p.exists():
                continue
            try:
                with open(p, encoding="utf-8") as f:
                    meta = json.load(f)
                sid = meta.get("session_id") or d.name
                self._col.update_one(
                    {"_id": sid},
                    {"$setOnInsert": {**meta, "_id": sid}},
                    upsert=True,
                )
                imported += 1
            except Exception:
                pass
        if imported:
            import logging
            logging.getLogger(__name__).info(
                "Migrated %d sessions from disk to MongoDB", imported
            )

    # ── CRUD ────────────────────────────────────────────────
    def create(self, session_id: str) -> dict:
        (self._base / session_id / "audio").mkdir(parents=True, exist_ok=True)
        meta = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "status": "in_progress",
            "turns": [],
            "bridge_note": None,
            "analysis": None,
        }
        self._col.update_one(
            {"_id": session_id},
            {"$setOnInsert": {**meta, "_id": session_id}},
            upsert=True,
        )
        return meta

    def get(self, session_id: str) -> dict | None:
        return _clean(self._col.find_one({"_id": session_id}))

    def update(self, session_id: str, **kwargs) -> dict | None:
        fields = {
            k: kwargs[k]
            for k in ("turns", "bridge_note", "status", "analysis")
            if k in kwargs
        }
        if not fields:
            return self.get(session_id)
        self._col.update_one({"_id": session_id}, {"$set": fields})
        return self.get(session_id)

    def list_sessions(self) -> list:
        result = []
        for doc in self._col.find({}, sort=[("created_at", -1)]):
            turns = doc.get("turns", [])
            result.append({
                "session_id": doc["session_id"],
                "created_at": doc.get("created_at", ""),
                "status": doc.get("status", "unknown"),
                "client_turns": sum(
                    1 for t in turns
                    if t.get("speaker") == "client" and not t.get("skipped")
                ),
                "has_analysis": doc.get("analysis") is not None,
                "has_bridge": bool(doc.get("bridge_note")),
            })
        return result

    def delete(self, session_id: str) -> bool:
        result = self._col.delete_one({"_id": session_id})
        d = self._base / session_id
        if d.exists():
            shutil.rmtree(d)
        return result.deleted_count > 0

    # ── Audio (stays on disk) ────────────────────────────────
    def save_audio(self, session_id: str, filename: str, data: bytes) -> bool:
        audio_dir = self._base / session_id / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        with open(audio_dir / filename, "wb") as f:
            f.write(data)
        return True

    def get_audio_path(self, session_id: str, filename: str) -> Path | None:
        p = self._base / session_id / "audio" / filename
        return p if p.exists() else None

    def list_audio(self, session_id: str) -> list:
        audio_dir = self._base / session_id / "audio"
        if not audio_dir.exists():
            return []
        return sorted(f.name for f in audio_dir.iterdir() if f.is_file())

    # ── Derived views ────────────────────────────────────────
    def transcript_text(self, session_id: str) -> str | None:
        meta = self.get(session_id)
        if meta is None:
            return None
        lines = [
            "ClinicalAI — Session Transcript",
            f"Session: {meta['session_id']}",
        ]
        created = meta.get("created_at", "")
        if created:
            try:
                created = datetime.fromisoformat(created).strftime("%B %d, %Y  %H:%M")
            except Exception:
                pass
        lines += [f"Date: {created}", "", "=" * 50, ""]

        prompt_n = 1
        for turn in meta.get("turns", []):
            speaker = turn.get("speaker", "")
            text = turn.get("text", "")
            skipped = turn.get("skipped", False)
            if speaker == "therapist":
                lines.append(f"[PROMPT {prompt_n}]")
                lines.append(text)
                lines.append("")
            elif speaker == "client":
                lines.append("[RESPONSE]")
                lines.append("(Skipped)" if skipped else text)
                lines.append("")
                prompt_n += 1

        bridge = meta.get("bridge_note")
        if bridge:
            lines += ["=" * 50, "", "[CLOSING NOTE]", bridge, ""]

        return "\n".join(lines)
