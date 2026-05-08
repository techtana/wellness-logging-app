"""Transcription settings — persisted in data/transcription_settings.json"""
import json
import os
from typing import Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_FILE = os.path.join(_ROOT, "data", "transcription_settings.json")

_DEFAULT = {
    "provider": "none",
    "whisper_local": {"model_size": "large-v3-turbo", "device": "auto", "compute_type": "auto"},
    "openai": {"api_key": "", "model": "whisper-1"}
}


class TranscriptionSettings:
    def __init__(self, path: str = _DEFAULT_FILE):
        self._path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self._path):
            with open(self._path) as f:
                return json.load(f)
        data = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DEFAULT.items()}
        data["provider"] = os.getenv("TRANSCRIPTION_PROVIDER", "none")
        if os.getenv("WHISPER_MODEL"):
            data["whisper_local"]["model_size"] = os.getenv("WHISPER_MODEL")
        if os.getenv("OPENAI_API_KEY"):
            data["openai"]["api_key"] = os.getenv("OPENAI_API_KEY")
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)
        return data

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get_safe(self) -> Dict:
        result = {k: (dict(v) if isinstance(v, dict) else v) for k, v in self._data.items()}
        key = result.get("openai", {}).get("api_key", "")
        result["openai"]["api_key_set"] = bool(key)
        result["openai"]["api_key"] = (key[:4] + "****") if key else ""
        return result

    def update(self, patch: Dict):
        if "provider" in patch:
            self._data["provider"] = patch["provider"]
        for prov in ("whisper_local", "openai"):
            if prov in patch:
                for k, v in patch[prov].items():
                    if k == "api_key" and (not v or "****" in str(v)):
                        continue
                    self._data[prov][k] = v
        self._save()

    def create_service(self) -> Optional:
        from src.transcription.transcriber import TranscriptionService
        name = self._data.get("provider", "none")
        if name == "none":
            return None
        try:
            return TranscriptionService(provider=name, **self._data.get(name, {}))
        except Exception:
            return None
