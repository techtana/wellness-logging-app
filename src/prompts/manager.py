import json
import uuid
from pathlib import Path
from .defaults import DEFAULT_PROMPTS

DATA_DIR = Path(__file__).parents[2] / "data"


class PromptManager:
    def __init__(self, path: Path = None):
        self._path = path or DATA_DIR / "prompts.json"
        self._data = []
        self._load()

    def _load(self):
        if self._path.exists():
            with open(self._path) as f:
                self._data = json.load(f)
        else:
            self._data = [dict(p) for p in DEFAULT_PROMPTS]
            self._save()

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def list(self):
        return list(self._data)

    def get_by_id(self, prompt_id: str):
        return next((p for p in self._data if p["id"] == prompt_id), None)

    def get_session_prompts(self):
        enabled = [p for p in self._data if p.get("enabled", True)]
        return sorted(enabled, key=lambda p: p.get("order", 999))

    def create(self, category: str, clinical_text: str, rephrased_text: str = "", order: int = None):
        new_id = str(uuid.uuid4())[:8]
        if order is None:
            order = max((p.get("order", 0) for p in self._data), default=0) + 1
        prompt = {
            "id": new_id,
            "category": category,
            "clinical_text": clinical_text,
            "rephrased_text": rephrased_text or clinical_text,
            "enabled": True,
            "order": order,
        }
        self._data.append(prompt)
        self._save()
        return prompt

    def update(self, prompt_id: str, **kwargs):
        prompt = self.get_by_id(prompt_id)
        if not prompt:
            return None
        for k in ("category", "clinical_text", "rephrased_text", "enabled", "order"):
            if k in kwargs:
                prompt[k] = kwargs[k]
        self._save()
        return prompt

    def delete(self, prompt_id: str) -> bool:
        before = len(self._data)
        self._data = [p for p in self._data if p["id"] != prompt_id]
        if len(self._data) < before:
            self._save()
            return True
        return False

    def reset(self):
        self._data = [dict(p) for p in DEFAULT_PROMPTS]
        self._save()
