"""Knowledge base CRUD for AI analysis instructions."""
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from src.knowledge_base.defaults import DEFAULT_INSTRUCTIONS

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_FILE = os.path.join(_ROOT, "data", "knowledge_base.json")


class KnowledgeBaseManager:
    def __init__(self, path: str = _DEFAULT_FILE):
        self._path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self._path):
            with open(self._path) as f:
                return json.load(f)
        now = datetime.now().isoformat()
        data = {"instructions": []}
        for inst in DEFAULT_INSTRUCTIONS:
            entry = dict(inst)
            entry["created_at"] = now
            entry["updated_at"] = now
            data["instructions"].append(entry)
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)
        return data

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def list(self) -> List[Dict]:
        return self._data["instructions"]

    def get_instruction(self, category: str) -> Optional[Dict]:
        for inst in self._data["instructions"]:
            if inst.get("category") == category and inst.get("enabled", True):
                return inst
        return None

    def get_by_id(self, inst_id: str) -> Optional[Dict]:
        for inst in self._data["instructions"]:
            if inst["id"] == inst_id:
                return inst
        return None

    def create(self, name: str, category: str, prompt: str) -> Dict:
        inst = {
            "id": str(uuid.uuid4()),
            "name": name,
            "category": category,
            "prompt": prompt,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._data["instructions"].append(inst)
        self._save()
        return inst

    def update(self, inst_id: str, **kwargs) -> Optional[Dict]:
        for inst in self._data["instructions"]:
            if inst["id"] == inst_id:
                for k in ("name", "category", "prompt", "enabled"):
                    if k in kwargs:
                        inst[k] = kwargs[k]
                inst["updated_at"] = datetime.now().isoformat()
                self._save()
                return inst
        return None

    def delete(self, inst_id: str) -> bool:
        before = len(self._data["instructions"])
        self._data["instructions"] = [i for i in self._data["instructions"] if i["id"] != inst_id]
        if len(self._data["instructions"]) < before:
            self._save()
            return True
        return False

    def reset(self):
        now = datetime.now().isoformat()
        self._data = {"instructions": []}
        for inst in DEFAULT_INSTRUCTIONS:
            entry = dict(inst)
            entry["created_at"] = now
            entry["updated_at"] = now
            self._data["instructions"].append(entry)
        self._save()
