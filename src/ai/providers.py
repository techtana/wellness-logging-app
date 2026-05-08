"""AI provider abstractions: Claude, OpenAI, Ollama"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AIResponse:
    def __init__(self, content: str, model: str = "", usage: dict = None):
        self.content = content
        self.model = model
        self.usage = usage or {}


class BaseAIProvider:
    def complete(self, system_prompt: str, user_message: str) -> AIResponse:
        raise NotImplementedError

    def complete_text(self, system_prompt: str, user_message: str) -> str:
        return self.complete(system_prompt, user_message).content.strip()

    def complete_json(self, system_prompt: str, user_message: str) -> dict:
        response = self.complete(system_prompt, user_message)
        content = response.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            content = "\n".join(lines[1:end])
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nSnippet: {content[:300]}")
            return {}


class ClaudeProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model = model

    def complete(self, system_prompt: str, user_message: str) -> AIResponse:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        client = anthropic.Anthropic(api_key=self.api_key)
        msg = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return AIResponse(
            content=msg.content[0].text,
            model=msg.model,
            usage={"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens}
        )


class OpenAIProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model

    def complete(self, system_prompt: str, user_message: str) -> AIResponse:
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        client = openai.OpenAI(api_key=self.api_key)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=4096,
            response_format={"type": "json_object"}
        )
        return AIResponse(
            content=resp.choices[0].message.content,
            model=resp.model,
            usage={"input_tokens": resp.usage.prompt_tokens, "output_tokens": resp.usage.completion_tokens}
        )

    def complete_text(self, system_prompt: str, user_message: str) -> str:
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        client = openai.OpenAI(api_key=self.api_key)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()


class OllamaProvider(BaseAIProvider):
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.2"):
        self.host = host.rstrip("/")
        self.model = model

    def complete(self, system_prompt: str, user_message: str) -> AIResponse:
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests package not installed.")
        resp = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "stream": False,
                "format": "json"
            },
            timeout=180
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        return AIResponse(content=content, model=self.model)

    def complete_text(self, system_prompt: str, user_message: str) -> str:
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests package not installed.")
        resp = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "stream": False,
            },
            timeout=180
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()


def create_provider(provider: str, **kwargs) -> Optional[BaseAIProvider]:
    if provider == "claude":
        return ClaudeProvider(api_key=kwargs.get("api_key", ""), model=kwargs.get("model", "claude-sonnet-4-6"))
    elif provider == "openai":
        return OpenAIProvider(api_key=kwargs.get("api_key", ""), model=kwargs.get("model", "gpt-4o"))
    elif provider == "ollama":
        return OllamaProvider(host=kwargs.get("host", "http://localhost:11434"), model=kwargs.get("model", "llama3.2"))
    return None
