"""MongoDB-backed prompt manager."""
import json
import uuid
from pathlib import Path

from src.db import get_db
from .defaults import DEFAULT_PROMPTS

DATA_DIR = Path(__file__).parents[2] / "data"


def _clean(doc: dict) -> dict | None:
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


class PromptManager:
    def __init__(self, path: Path = None):
        self._legacy_path = path or DATA_DIR / "prompts.json"
        self._col = get_db()["prompts"]
        self._migrate_from_file()

    # ── One-time migration from prompts.json ─────────────────
    def _migrate_from_file(self):
        if self._col.count_documents({}) > 0:
            return
        source = []
        if self._legacy_path.exists():
            try:
                with open(self._legacy_path) as f:
                    source = json.load(f)
            except Exception:
                pass
        if not source:
            source = [dict(p) for p in DEFAULT_PROMPTS]
        for p in source:
            self._col.update_one(
                {"_id": p["id"]},
                {"$setOnInsert": {**p, "_id": p["id"]}},
                upsert=True,
            )

    # ── CRUD ─────────────────────────────────────────────────
    def list(self) -> list:
        return [_clean(d) for d in self._col.find({}, sort=[("order", 1)])]

    def get_by_id(self, prompt_id: str) -> dict | None:
        return _clean(self._col.find_one({"_id": prompt_id}))

    def get_session_prompts(self) -> list:
        return [
            _clean(d)
            for d in self._col.find({"enabled": True}, sort=[("order", 1)])
        ]

    def create(
        self,
        category: str,
        clinical_text: str,
        rephrased_text: str = "",
        order: int = None,
    ) -> dict:
        if order is None:
            last = self._col.find_one({}, sort=[("order", -1)], projection={"order": 1})
            order = (last["order"] + 1) if last else 1
        pid = str(uuid.uuid4())[:8]
        doc = {
            "_id": pid,
            "id": pid,
            "category": category,
            "clinical_text": clinical_text,
            "rephrased_text": rephrased_text or clinical_text,
            "enabled": True,
            "order": order,
        }
        self._col.insert_one(doc)
        return _clean(doc)

    def update(self, prompt_id: str, **kwargs) -> dict | None:
        fields = {
            k: kwargs[k]
            for k in ("category", "clinical_text", "rephrased_text", "enabled", "order")
            if k in kwargs
        }
        self._col.update_one({"_id": prompt_id}, {"$set": fields})
        return self.get_by_id(prompt_id)

    def delete(self, prompt_id: str) -> bool:
        return self._col.delete_one({"_id": prompt_id}).deleted_count > 0

    def reset(self):
        self._col.drop()
        for p in DEFAULT_PROMPTS:
            self._col.insert_one({**dict(p), "_id": p["id"]})
