"""AI provider settings — persisted in data/ai_settings.json"""
import json
import os
from typing import Dict, Optional

from src.ai.providers import create_provider, BaseAIProvider

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_FILE = os.path.join(_ROOT, "data", "ai_settings.json")

_DEFAULT = {
    "provider": "none",
    "claude": {"api_key": "", "model": "claude-sonnet-4-6"},
    "openai": {"api_key": "", "model": "gpt-4o"},
    "ollama": {"host": "http://localhost:11434", "model": "llama3.2"}
}


class AISettings:
    def __init__(self, path: str = _DEFAULT_FILE):
        self._path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self._path):
            with open(self._path) as f:
                return json.load(f)
        data = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DEFAULT.items()}
        data["provider"] = os.getenv("AI_PROVIDER", "none")
        if os.getenv("ANTHROPIC_API_KEY"):
            data["claude"]["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        if os.getenv("OPENAI_API_KEY"):
            data["openai"]["api_key"] = os.getenv("OPENAI_API_KEY")
        if os.getenv("OLLAMA_HOST"):
            data["ollama"]["host"] = os.getenv("OLLAMA_HOST")
        if os.getenv("OLLAMA_MODEL"):
            data["ollama"]["model"] = os.getenv("OLLAMA_MODEL")
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)
        return data

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get_safe(self) -> Dict:
        """Settings with masked API keys for client display."""
        result = {k: (dict(v) if isinstance(v, dict) else v) for k, v in self._data.items()}
        for prov in ("claude", "openai"):
            key = result.get(prov, {}).get("api_key", "")
            result[prov]["api_key_set"] = bool(key)
            result[prov]["api_key"] = (key[:4] + "****") if key else ""
        return result

    def update(self, patch: Dict):
        if "provider" in patch:
            self._data["provider"] = patch["provider"]
        for prov in ("claude", "openai", "ollama"):
            if prov in patch:
                for k, v in patch[prov].items():
                    if k == "api_key" and (not v or "****" in str(v)):
                        continue  # keep existing key
                    self._data[prov][k] = v
        self._save()

    def create_provider(self) -> Optional[BaseAIProvider]:
        name = self._data.get("provider", "none")
        if name == "none":
            return None
        try:
            return create_provider(name, **self._data.get(name, {}))
        except Exception:
            return None
