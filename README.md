# Clinical Intelligence System

A local web application for analyzing therapy session transcripts and generating structured clinical insights. Supports audio transcription, AI-powered analysis via Claude / OpenAI / Ollama, and a therapist-managed knowledge base of analysis instructions.

---

## Features

- **Audio transcription** — drop an audio file or record live; transcribed with Whisper (local GPU/CPU) or OpenAI Whisper API
- **AI-powered analysis** — replace keyword matching with LLM-driven emotion, theme, and relational analysis
- **Knowledge base** — therapists edit the AI system prompts per analysis category directly in the UI
- **Multi-provider AI** — Claude, OpenAI, or Ollama (local); falls back to keyword analysis if no provider is set
- **Web UI** — single-page app with transcript builder, results tabs, KB editor, and settings modal

---

## Project Structure

```
wellness-logging-app/
├── src/
│   ├── api/
│   │   └── app.py                    # Flask API + all endpoints
│   ├── ingestion_layer/
│   │   └── parser.py                 # Transcript parsing and standardization
│   ├── processing_layer/             # Keyword-based analysis modules (fallback)
│   │   ├── sentiment_analysis.py
│   │   ├── thematic_extraction.py
│   │   ├── relational_dynamics.py
│   │   ├── turn_pattern_analyzer.py
│   │   ├── feedback_loop_analyzer.py
│   │   └── clinical_significance.py
│   ├── output_layer/
│   │   └── report.py                 # Report formatter
│   ├── ai/
│   │   ├── providers.py              # Claude / OpenAI / Ollama adapters
│   │   ├── analyzer.py               # AI-based analysis using KB instructions
│   │   └── settings.py               # Provider config (persisted to data/)
│   ├── knowledge_base/
│   │   ├── manager.py                # CRUD for analysis instructions
│   │   └── defaults.py               # Default prompts (seeded on first run)
│   ├── transcription/
│   │   ├── transcriber.py            # Whisper local + OpenAI transcription
│   │   └── settings.py               # Transcription config (persisted to data/)
│   ├── config.py
│   └── main.py                       # Analysis orchestrator
├── templates/
│   └── index.html                    # Web UI
├── static/
│   ├── app.js
│   └── styles.css
├── data/                             # Runtime state (gitignored for settings files)
│   ├── knowledge_base.json           # Editable analysis instructions
│   ├── ai_settings.json              # AI provider config (contains keys — gitignored)
│   └── transcription_settings.json  # Transcription config (gitignored)
├── tests/
│   └── test_analysis.py
├── test_whisper.py                   # Standalone Whisper smoke test
├── run.py
└── requirements.txt
```

---

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
cp .env.example .env

python run.py
```

Open `http://127.0.0.1:5000` in a browser.

```bash
# Custom host / port
python run.py --host 0.0.0.0 --port 8000 --debug
```

---

## Installation by Feature

### Core (always required)
```bash
pip install flask python-dotenv spacy nltk pandas scikit-learn numpy requests
```

### AI analysis — pick one or more
```bash
pip install anthropic          # Claude (recommended)
pip install openai             # OpenAI
# Ollama — no pip package; install from https://ollama.com then pull a model
```

### Local audio transcription (Whisper)
```bash
pip install faster-whisper

# Windows with NVIDIA GPU — also install the CUDA wheel:
pip install nvidia-cublas-cu12
```
> The first transcription downloads model weights (~1.6 GB for `large-v3-turbo`). CPU-only works without the CUDA wheel.

### Test Whisper independently
```bash
python test_whisper.py audio.mp3                          # auto-detect language, CPU
python test_whisper.py audio.mp3 large-v3-turbo en cuda  # GPU, skip language detection
```

---

## Configuration

### AI provider
Open the app → gear icon → **Settings** → select a provider and enter credentials. Settings are saved to `data/ai_settings.json`.

Alternatively set environment variables before starting the server:

```env
AI_PROVIDER=claude          # claude | openai | ollama | none
ANTHROPIC_API_KEY=sk-ant-…
OPENAI_API_KEY=sk-…
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Transcription
Open **Settings** → Transcription Provider.

```env
TRANSCRIPTION_PROVIDER=whisper_local   # whisper_local | openai | none
WHISPER_MODEL=large-v3-turbo           # large-v3-turbo | large-v3 | medium | small | base
```

### Other options (`.env`)
```env
DEBUG=False
API_HOST=127.0.0.1
API_PORT=5000
EMOTION_INTENSITY_THRESHOLD=15.0
DOMINANT_THEME_THRESHOLD=0.3
MIN_THEME_INSTANCES=3
```

---

## Knowledge Base

The Knowledge Base tab in the UI lets therapists edit the AI system prompts used for each analysis category:

| Category | What it controls |
|---|---|
| `sentiment` | Emotion recognition rules and intensity scale |
| `themes` | Theme taxonomy and cognitive distortion definitions |
| `dynamics` | Therapeutic alliance model and communication styles |
| `clinical_report` | Report tone, intervention naming, red-flag criteria |

Instructions are stored in `data/knowledge_base.json` and seeded from defaults on first run. Use **Reset to defaults** to restore the originals.

---

## API Endpoints

### Analysis
```
POST /api/v1/analyze                  Analyze a single transcript
POST /api/v1/analyze/batch            Analyze multiple sessions
```

### Transcription
```
POST /api/v1/transcribe               Upload audio → transcription (JSON)
POST /api/v1/transcribe/stream        Upload audio → SSE progress stream
```

### Knowledge Base
```
GET  /api/v1/kb/instructions          List all instructions
POST /api/v1/kb/instructions          Create instruction
GET  /api/v1/kb/instructions/<id>     Get one
PUT  /api/v1/kb/instructions/<id>     Update
DELETE /api/v1/kb/instructions/<id>   Delete
POST /api/v1/kb/reset                 Reset to defaults
```

### Settings
```
GET  /api/v1/settings/ai              Get AI provider config
PUT  /api/v1/settings/ai              Update AI provider config
GET  /api/v1/settings/transcription   Get transcription config
PUT  /api/v1/settings/transcription   Update transcription config
```

### Misc
```
GET  /health
GET  /api/v1/docs
```

---

## Transcript Format

```json
POST /api/v1/analyze
{
    "transcript": [
        {"timestamp": 0,  "speaker": "therapist", "text": "How have you been feeling this week?"},
        {"timestamp": 5,  "speaker": "client",    "text": "Struggling with anxiety, especially at work."}
    ],
    "session_id": "session_001",
    "patient_id": "anonymous"
}
```

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | |
| `speaker` | No | `therapist`, `client`, or `other` |
| `timestamp` | No | Turn start in seconds |
| `duration` | No | Turn length in seconds |
| `confidence` | No | ASR confidence 0–1 |

Minimum: 2 distinct speakers, combined text ≥ 50 characters.

---

## Response Structure

```json
{
    "status": "success",
    "session_id": "session_001",
    "ai_enhanced": true,
    "analysis": {
        "sentiment_analysis": {},
        "thematic_analysis": {},
        "turn_patterns": {},
        "feedback_analysis": {},
        "relational_dynamics": {},
        "clinical_significance": {}
    },
    "insight_report": {
        "sections": {
            "executive_summary": {},
            "thematic_analysis": {},
            "emotional_mapping": {},
            "clinical_hypothesis": {},
            "relational_dynamics": {},
            "recommendations": {}
        }
    }
}
```

`ai_enhanced: true` means an AI provider was used. `false` means keyword-based fallback.

---

## Python Usage

```python
from src.main import TherapeuticCommunicationAnalyzer

# Keyword-based (no setup required)
analyzer = TherapeuticCommunicationAnalyzer()

# AI-powered
from src.ai.settings import AISettings
from src.ai.analyzer import AIAnalyzer
from src.knowledge_base.manager import KnowledgeBaseManager

ai_settings = AISettings()
kb = KnowledgeBaseManager()
provider = ai_settings.create_provider()
analyzer = TherapeuticCommunicationAnalyzer(
    ai_analyzer=AIAnalyzer(provider, kb) if provider else None
)

result = analyzer.analyze_session(
    transcript_data=[
        {"timestamp": 0,  "speaker": "therapist", "text": "How have you been feeling?"},
        {"timestamp": 8,  "speaker": "client",    "text": "Very anxious, especially at work."},
    ],
    session_id="session_001",
    patient_id="anonymous"
)

sections = result["insight_report"]["sections"]
print(sections["executive_summary"]["overall_tone_trajectory"])
print(sections["recommendations"]["next_session_focus"])
```

---

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=src
```

---

## Privacy

All patient identifiers should be anonymized before submission. Transcripts are processed in-memory with no persistence by default. API keys are stored in `data/ai_settings.json` (gitignored). For production use, add authentication, encrypted storage, and audit logging.

---

Version 2.0.0 | Updated 2026-05-03
