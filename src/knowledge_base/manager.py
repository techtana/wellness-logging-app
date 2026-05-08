"""MongoDB-backed knowledge base manager for AI analysis instructions."""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from src.db import get_db
from src.knowledge_base.defaults import DEFAULT_INSTRUCTIONS

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LEGACY_FILE = os.path.join(_ROOT, "data", "knowledge_base.json")


def _clean(doc: dict) -> dict | None:
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


class KnowledgeBaseManager:
    def __init__(self, path: str = _LEGACY_FILE):
        self._legacy_path = path
        self._col = get_db()["knowledge_base"]
        self._migrate_from_file()

    # ── One-time migration ────────────────────────────────────
    def _migrate_from_file(self):
        if self._col.count_documents({}) > 0:
            return
        source = []
        if os.path.exists(self._legacy_path):
            try:
                with open(self._legacy_path) as f:
                    data = json.load(f)
                source = data.get("instructions", [])
            except Exception:
                pass
        if not source:
            now = datetime.now().isoformat()
            source = [{**dict(i), "created_at": now, "updated_at": now}
                      for i in DEFAULT_INSTRUCTIONS]
        for inst in source:
            self._col.update_one(
                {"_id": inst["id"]},
                {"$setOnInsert": {**inst, "_id": inst["id"], "files": []}},
                upsert=True,
            )

    # ── Internal helpers ──────────────────────────────────────
    def _augment_prompt(self, inst: Dict) -> Dict:
        """Append attached file content to the prompt for use as system prompt."""
        files = inst.get("files", [])
        if not files:
            return inst
        extra = "\n\n---\nREFERENCE MATERIALS:\n"
        for f in files:
            extra += f"\n## {f['filename']}\n{f['content_text']}\n"
        return {**inst, "prompt": inst["prompt"] + extra}

    def _strip_files(self, doc: Dict) -> Dict:
        if doc:
            doc.pop("files", None)
        return doc

    # ── CRUD ─────────────────────────────────────────────────
    def list(self) -> List[Dict]:
        return [self._strip_files(_clean(d)) for d in self._col.find({})]

    def get_instruction(self, category: str) -> Optional[Dict]:
        """Return instruction with file content appended (for AI analysis)."""
        doc = _clean(self._col.find_one({"category": category, "enabled": True}))
        return self._augment_prompt(doc) if doc else None

    def get_by_id(self, inst_id: str) -> Optional[Dict]:
        """Return instruction without file content (for display/edit)."""
        doc = _clean(self._col.find_one({"_id": inst_id}))
        return self._strip_files(doc) if doc else None

    def get_by_id_with_files(self, inst_id: str) -> Optional[Dict]:
        """Return instruction with file content appended (for custom re-analysis)."""
        doc = _clean(self._col.find_one({"_id": inst_id}))
        return self._augment_prompt(doc) if doc else None

    def create(self, name: str, category: str, prompt: str) -> Dict:
        now = datetime.now().isoformat()
        new_id = str(uuid.uuid4())
        inst = {
            "_id": new_id,
            "id": new_id,
            "name": name,
            "category": category,
            "prompt": prompt,
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "files": [],
        }
        self._col.insert_one(inst)
        return self._strip_files(_clean(inst))

    def update(self, inst_id: str, **kwargs) -> Optional[Dict]:
        fields = {
            k: kwargs[k]
            for k in ("name", "category", "prompt", "enabled")
            if k in kwargs
        }
        fields["updated_at"] = datetime.now().isoformat()
        self._col.update_one({"_id": inst_id}, {"$set": fields})
        return self.get_by_id(inst_id)

    def delete(self, inst_id: str) -> bool:
        return self._col.delete_one({"_id": inst_id}).deleted_count > 0

    def reset(self):
        now = datetime.now().isoformat()
        self._col.drop()
        for inst in DEFAULT_INSTRUCTIONS:
            doc = {**dict(inst), "created_at": now, "updated_at": now,
                   "_id": inst["id"], "files": []}
            self._col.insert_one(doc)

    # ── File attachments ──────────────────────────────────────
    def save_file(self, inst_id: str, filename: str, content_text: str,
                  file_type: str = "text") -> bool:
        """Upsert a file attachment on an instruction."""
        self._col.update_one({"_id": inst_id}, {"$pull": {"files": {"filename": filename}}})
        entry = {
            "filename": filename,
            "content_text": content_text,
            "file_type": file_type,
            "created_at": datetime.now().isoformat(),
        }
        result = self._col.update_one({"_id": inst_id}, {"$push": {"files": entry}})
        return result.modified_count > 0

    def list_files(self, inst_id: str) -> List[Dict]:
        """Return file metadata without content text."""
        doc = self._col.find_one({"_id": inst_id}, {"files": 1})
        if not doc:
            return []
        return [
            {"filename": f["filename"], "file_type": f.get("file_type", "text"),
             "created_at": f.get("created_at", "")}
            for f in doc.get("files", [])
        ]

    def delete_file(self, inst_id: str, filename: str) -> bool:
        result = self._col.update_one(
            {"_id": inst_id}, {"$pull": {"files": {"filename": filename}}}
        )
        return result.modified_count > 0
