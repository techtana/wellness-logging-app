"""Audio transcription — Whisper local (faster-whisper) or OpenAI cloud."""
import logging
import os
import sys
from typing import List, Dict, Generator

logger = logging.getLogger(__name__)


def _register_nvidia_dll_dirs():
    """Add nvidia CUDA wheel bin dirs to the Windows DLL search path.

    pip installs CUDA wheels under site-packages/nvidia/<pkg>/bin/ but does NOT
    add those paths to PATH, so ctranslate2 can't find cublas64_12.dll etc.
    We search sys.path (covers system Python, venvs, user installs equally)
    and register every nvidia/*/bin dir with os.add_dll_directory().
    """
    if sys.platform != "win32":
        return
    for sp in sys.path:
        nvidia_root = os.path.join(sp, "nvidia")
        if not os.path.isdir(nvidia_root):
            continue
        for pkg in os.listdir(nvidia_root):
            bin_dir = os.path.join(nvidia_root, pkg, "bin")
            if os.path.isdir(bin_dir):
                try:
                    os.add_dll_directory(bin_dir)
                    logger.debug(f"Registered DLL dir: {bin_dir}")
                except OSError:
                    pass


class TranscriptionResult:
    def __init__(self, text: str, language: str = "en", segments: List[Dict] = None):
        self.text = text
        self.language = language
        self.segments = segments or []


def _audio_duration(audio_path: str) -> float:
    """Return audio duration in seconds using PyAV (faster-whisper dependency)."""
    try:
        import av
        with av.open(audio_path) as container:
            if container.duration:
                return container.duration / 1_000_000.0  # microseconds → seconds
    except Exception:
        pass
    return 0.0


def _detect_device_label(requested: str) -> str:
    """Return a human-readable label for the device that will be used."""
    if requested == "cpu":
        return "CPU"
    if requested == "cuda":
        return "GPU (CUDA)"
    # "auto" — check whether CUDA is actually available
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "GPU (CUDA)"
    except Exception:
        pass
    return "CPU"


class WhisperLocalTranscriber:
    def __init__(self, model_size: str = "large-v3-turbo", device: str = "auto", compute_type: str = "auto"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError("faster-whisper is not installed. Run: pip install faster-whisper")
        _register_nvidia_dll_dirs()
        logger.info(f"Loading Whisper model '{self.model_size}' on device='{self.device}'...")
        # int8 is universally compatible; fp16/auto can crash on some GPU drivers
        compute = self.compute_type if self.compute_type != "auto" else "int8"
        self._model = WhisperModel(self.model_size, device=self.device, compute_type=compute)
        logger.info("Whisper model loaded.")

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        self._load()
        segments_gen, info = self._model.transcribe(audio_path, beam_size=5)
        texts, seg_list = [], []
        for s in segments_gen:
            texts.append(s.text.strip())
            seg_list.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        return TranscriptionResult(text=" ".join(texts), language=info.language, segments=seg_list)

    def transcribe_stream(self, audio_path: str) -> Generator[dict, None, None]:
        """Yield SSE-style dicts: info → segment… → done (or error)."""
        self._load()
        duration = _audio_duration(audio_path)
        device_label = _detect_device_label(self.device)

        yield {"type": "info", "device": device_label, "model": self.model_size, "duration": duration}

        try:
            segments_gen, info = self._model.transcribe(audio_path, beam_size=5)
            texts, seg_list = [], []
            for s in segments_gen:
                text = s.text.strip()
                texts.append(text)
                seg_list.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": text})
                yield {
                    "type": "segment",
                    "text": text,
                    "start": round(s.start, 2),
                    "end": round(s.end, 2),
                    "progress": round(s.end, 2),
                    "duration": duration,
                }
            yield {
                "type": "done",
                "text": " ".join(texts),
                "language": info.language,
                "segments": seg_list,
            }
        except Exception as e:
            yield {"type": "error", "message": str(e)}


class OpenAIWhisperTranscriber:
    def __init__(self, api_key: str, model: str = "whisper-1"):
        self.api_key = api_key
        self.model = model

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        client = openai.OpenAI(api_key=self.api_key)
        with open(audio_path, "rb") as f:
            resp = client.audio.transcriptions.create(
                model=self.model, file=f, response_format="verbose_json"
            )
        segments = [{"start": s.start, "end": s.end, "text": s.text} for s in getattr(resp, "segments", [])]
        return TranscriptionResult(text=resp.text, language=getattr(resp, "language", "en"), segments=segments)

    def transcribe_stream(self, audio_path: str) -> Generator[dict, None, None]:
        """OpenAI API has no streaming — yield info then block until done."""
        yield {"type": "info", "device": "Cloud (OpenAI)", "model": self.model, "duration": 0}
        try:
            result = self.transcribe(audio_path)
            yield {"type": "done", "text": result.text, "language": result.language, "segments": result.segments}
        except Exception as e:
            yield {"type": "error", "message": str(e)}


class TranscriptionService:
    def __init__(self, provider: str, **kwargs):
        self.provider = provider
        if provider == "whisper_local":
            self._impl = WhisperLocalTranscriber(
                model_size=kwargs.get("model_size", "large-v3-turbo"),
                device=kwargs.get("device", "auto"),
                compute_type=kwargs.get("compute_type", "auto"),
            )
        elif provider == "openai":
            self._impl = OpenAIWhisperTranscriber(
                api_key=kwargs.get("api_key", ""),
                model=kwargs.get("model", "whisper-1"),
            )
        else:
            raise ValueError(f"Unknown transcription provider: {provider}")

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        return self._impl.transcribe(audio_path)

    def transcribe_stream(self, audio_path: str) -> Generator[dict, None, None]:
        return self._impl.transcribe_stream(audio_path)
